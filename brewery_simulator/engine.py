"""
brewery_simulator/engine.py
Main simulation engine + asyncio entrypoint.

Runs two concurrent tasks in the same event loop:
  1. Simulation tick loop + MQTT publisher
  2. FastAPI HTTP control plane (uvicorn)
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from pathlib import Path

from brewery_simulator.config import load_config
from brewery_simulator.tag_store import TagStore
from brewery_simulator.publisher import MQTTPublisher
from brewery_simulator.areas.all_areas import (
    MillingArea, UtilitiesArea, BrewhouseArea, CoolingArea,
    FermentationArea, MaturationArea, PackagingArea, CIPArea,
)

logger = logging.getLogger(__name__)


class BreweryEngine:
    """
    Core simulation engine.
    Exposes `paused` and `speed` as mutable attributes so the API
    can change them live without any locking (asyncio is single-threaded).
    """

    def __init__(
        self,
        config_path: Path,
        tags_path: Path,
        speed: float | None = None,
        api_host: str = "0.0.0.0",
        api_port: int = 8000,
        api_enabled: bool = True,
    ) -> None:
        self.cfg = load_config(config_path)
        self.store = TagStore()
        self.store.load_from_toml(tags_path)

        self.speed     = speed if speed is not None else self.cfg.sim.default_speed
        self.paused    = False
        self.api_host  = api_host
        self.api_port  = api_port
        self.api_enabled = api_enabled

        seed = self.cfg.sim.random_seed
        self.rng = random.Random(seed if seed != 0 else None)

        merged_cfg = {"process": self.cfg.process, "physics": self.cfg.physics}

        self._areas = [
            MillingArea(self.store, merged_cfg, self.rng),
            UtilitiesArea(self.store, merged_cfg, self.rng),
            BrewhouseArea(self.store, merged_cfg, self.rng),
            CoolingArea(self.store, merged_cfg, self.rng),
            FermentationArea(self.store, merged_cfg, self.rng),
            MaturationArea(self.store, merged_cfg, self.rng),
            PackagingArea(self.store, merged_cfg, self.rng),
            CIPArea(self.store, merged_cfg, self.rng),
        ]

        self.publisher    = MQTTPublisher(self.cfg.mqtt, self.store)
        self._tick_count  = 0
        self._started_at  = time.monotonic()
        self._last_stats  = time.monotonic()

    # ── Simulation tick ───────────────────────────────────────────────────────

    def _advance(self, dt_sim: float) -> None:
        for area in self._areas:
            try:
                area.tick(dt_sim)
            except Exception as e:
                logger.exception("Error in %s.tick(): %s", area.__class__.__name__, e)

    async def _tick_and_publish(
        self, client, heartbeat_interval: float, publish_on_change: bool
    ) -> None:
        tick_real = self.cfg.sim.tick_interval
        t0 = time.monotonic()

        if not self.paused:
            dt_sim = tick_real * self.speed
            self._advance(dt_sim)
            self._tick_count += 1

            if publish_on_change:
                n = await self.publisher.publish_changed(client, heartbeat_interval)
            else:
                n = await self.publisher.publish_all(client)

            if time.monotonic() - self._last_stats >= 30:
                sim_h = self._tick_count * dt_sim / 3600
                logger.info(
                    "Tick #%d | speed=%.0fx | sim_time=%.1fh | published %d tags",
                    self._tick_count, self.speed, sim_h, n,
                )
                self._last_stats = time.monotonic()

        elapsed = time.monotonic() - t0
        await asyncio.sleep(max(0.0, tick_real - elapsed))

    # ── API task ──────────────────────────────────────────────────────────────

    async def _run_api(self) -> None:
        import uvicorn
        from brewery_simulator.api import create_app
        fastapi_app = create_app(self)
        config = uvicorn.Config(
            fastapi_app,
            host=self.api_host,
            port=self.api_port,
            log_level="warning",   # uvicorn access logs are noisy — keep quiet
            loop="none",           # use the existing asyncio loop
        )
        server = uvicorn.Server(config)
        logger.info("API available at http://%s:%d/docs", self.api_host, self.api_port)
        await server.serve()

    # ── Main entrypoint ───────────────────────────────────────────────────────

    async def run(self) -> None:
        logger.info(
            "Brewery Simulator starting | speed=%.0fx | tags=%d | broker=%s:%d",
            self.speed,
            len(self.store.all_tags()),
            self.cfg.mqtt.host,
            self.cfg.mqtt.port,
        )

        tasks = [
            asyncio.create_task(
                self.publisher.run_forever(
                    self.store,
                    self._tick_and_publish,
                    self.cfg.sim.heartbeat_interval,
                    self.cfg.sim.publish_on_change,
                ),
                name="mqtt-loop",
            )
        ]

        if self.api_enabled:
            tasks.append(asyncio.create_task(self._run_api(), name="api"))

        # Run both tasks — if either crashes, cancel the other
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in pending:
            task.cancel()
        for task in done:
            if task.exception():
                raise task.exception()
