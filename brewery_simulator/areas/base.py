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

    def _trigger_fault(self, fault_tag: str, reason_tag: str, equip_key: str) -> None:
        """
        Set fault code (Int 1-3) and matching reason string.
        Severity 0 = no alarm, 1 = low, 2 = medium, 3 = high.
        Reason tag is only written if it exists in the store.
        """
        from brewery_simulator.fault_codes import pick_fault
        code, reason = pick_fault(equip_key, self.rng)
        self.store.set(fault_tag, code)
        if reason_tag in self.store.all_tags():
            self.store.set(reason_tag, reason)

    def _clear_fault(self, fault_tag: str, reason_tag: str) -> None:
        """Clear fault: code=0, reason='No fault'."""
        self.store.set(fault_tag, 0)
        if reason_tag in self.store.all_tags():
            self.store.set(reason_tag, "No fault")