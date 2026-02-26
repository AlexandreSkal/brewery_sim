"""
brewery_simulator/publisher.py

MQTT publisher — bare value payloads, no envelope.

Topic structure:
  brewery/<area>/<TAG_NAME>   →  raw value (float as "1234.5678", bool as "1"/"0")

LIM_H / LIM_L tags are published alongside their parent analog tags,
so Ignition receives them as regular retained tags and can use them
in UDT expressions to compute percentage without hardcoding ranges.

No metadata / cfg topics — descriptions live in tags.toml only.
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import aiomqtt

if TYPE_CHECKING:
    from brewery_simulator.config import MqttConfig
    from brewery_simulator.tag_store import TagStore

logger = logging.getLogger(__name__)


def _encode_value(value) -> bytes:
    """Encode a single value as raw bytes — no JSON wrapper."""
    if isinstance(value, bool):
        return b"1" if value else b"0"
    if isinstance(value, float):
        return f"{value:.4f}".encode()
    return str(value).encode()


class MQTTPublisher:

    def __init__(self, mqtt_cfg: "MqttConfig", store: "TagStore") -> None:
        self.cfg = mqtt_cfg
        self.store = store

    def _make_client(self) -> aiomqtt.Client:
        kwargs = dict(
            hostname  = self.cfg.host,
            port      = self.cfg.port,
            keepalive = self.cfg.keepalive,
            identifier= self.cfg.client_id,
            protocol  = (aiomqtt.ProtocolVersion.V5
                         if self.cfg.protocol == 5
                         else aiomqtt.ProtocolVersion.V311),
        )
        if self.cfg.username:
            kwargs["username"] = self.cfg.username
            kwargs["password"] = self.cfg.password or None
        if self.cfg.tls_enabled:
            import ssl
            ctx = ssl.create_default_context()
            if self.cfg.tls_ca_certs:
                ctx.load_verify_locations(self.cfg.tls_ca_certs)
            if self.cfg.tls_certfile and self.cfg.tls_keyfile:
                ctx.load_cert_chain(self.cfg.tls_certfile, self.cfg.tls_keyfile)
            kwargs["tls_context"] = ctx
        return aiomqtt.Client(**kwargs)

    async def publish_all(self, client: aiomqtt.Client) -> int:
        """Publish every tag value. Returns count published."""
        root = self.cfg.topic_root
        count = 0
        for tag_name, state in self.store.all_tags().items():
            topic = f"{root}/{state.meta.area}/{tag_name}"
            await client.publish(
                topic, _encode_value(state.value),
                qos=self.cfg.qos, retain=self.cfg.retain,
            )
            state.last_published = time.monotonic()
            count += 1
        return count

    async def publish_changed(self, client: aiomqtt.Client, heartbeat_interval: float) -> int:
        """Publish only changed tags + heartbeat. Returns count."""
        root = self.cfg.topic_root
        now  = time.monotonic()
        count = 0
        for tag_name, state in self.store.all_tags().items():
            # LIM tags are static — only publish on heartbeat, never as "changed"
            is_lim = tag_name.endswith(("_LIM_H", "_LIM_L"))
            force = (now - state.last_published) >= heartbeat_interval
            if not (state.changed or force) or (is_lim and not force):
                continue
            topic = f"{root}/{state.meta.area}/{tag_name}"
            await client.publish(
                topic, _encode_value(state.value),
                qos=self.cfg.qos, retain=self.cfg.retain,
            )
            state.prev_value  = state.value
            state.last_published = now
            count += 1
        return count

    async def run_forever(
        self,
        store: "TagStore",
        tick_fn,
        heartbeat_interval: float,
        publish_on_change: bool,
    ) -> None:
        """Connect, publish full snapshot, then loop forever."""
        reconnect_delay = 5
        while True:
            try:
                async with self._make_client() as client:
                    logger.info("Connected to MQTT broker %s:%d",
                                self.cfg.host, self.cfg.port)
                    await self.publish_all(client)   # full snapshot including LIM tags
                    while True:
                        await tick_fn(client, heartbeat_interval, publish_on_change)
            except aiomqtt.MqttError as e:
                logger.warning("MQTT error: %s — retrying in %ds", e, reconnect_delay)
                import asyncio
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60)
            except Exception as e:
                logger.exception("Unexpected error in MQTT loop: %s", e)
                import asyncio
                await asyncio.sleep(reconnect_delay)
