"""
brewery_simulator/areas/base.py
Base class for all area simulators.
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from brewery_simulator.tag_store import TagStore


class AreaSimulator(ABC):
    """
    Base class for an area simulator.
    Each area owns a set of tags and advances them each tick.
    dt_sim: simulated seconds elapsed since last tick.
    """

    def __init__(self, store: "TagStore", cfg: dict, rng: random.Random) -> None:
        self.store = store
        self.cfg = cfg
        self.rng = rng

    @abstractmethod
    def tick(self, dt_sim: float) -> None:
        """Advance simulation by dt_sim simulated seconds."""
        ...

    # ── Convenience helpers ───────────────────────────────────────────────────

    def _get(self, tag: str):
        return self.store.get(tag)

    def _set(self, tag: str, value) -> None:
        self.store.set(tag, value)

    def _noise(self, std: float = 0.05) -> float:
        return self.rng.gauss(0.0, std)


    def _set_lvl(self, tag: str, pct: float) -> None:
        """Set a level tag by percentage (0-100). Converts to mm if unit=mm."""
        self.store.set_level_pct(tag, pct)

    def _get_lvl(self, tag: str) -> float:
        """Get a level tag as percentage (0-100), regardless of mm or %."""
        return self.store.get_level_pct(tag)

    def _random_fault(self, prob_per_sec: float, dt: float) -> bool:
        """Return True if a random fault should occur this tick."""
        return self.rng.random() < (prob_per_sec * dt)

    def _random_recovery(self, mean_seconds: float, dt: float) -> bool:
        """Return True if a fault should self-recover this tick."""
        if mean_seconds <= 0:
            return False
        rate = 1.0 / mean_seconds
        return self.rng.random() < (rate * dt)
