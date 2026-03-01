"""
brewery_simulator/tag_store.py
Central in-memory store for all IO tag values.

Level tags (unit="mm") store real physical millimetre readings.
The simulator converts internal 0-100% to mm using min_val/max_val as
the physical tank height range declared in tags.toml.

Every _LT tag has a companion _LT_MIN and _LT_MAX tag (static, published once)
so Ignition can build the percentage UDT expression without hardcoding numbers.
"""
from __future__ import annotations

import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TagMeta:
    name: str
    area: str
    io_type: str          # DI | DO | AI | AO
    description: str
    unit: str
    equipment: str
    min_val: float = 0.0
    max_val: float = 1.0
    initial: Any = 0.0


@dataclass
class TagState:
    meta: TagMeta
    value: Any
    prev_value: Any = None
    last_changed: float = field(default_factory=time.monotonic)
    last_published: float = 0.0

    @property
    def changed(self) -> bool:
        return self.value != self.prev_value

    def clamp(self) -> None:
        if self.meta.io_type in ("AI", "AO"):
            self.value = max(self.meta.min_val, min(self.meta.max_val, float(self.value)))


class TagStore:
    """Central tag store."""

    def __init__(self) -> None:
        self._tags: dict[str, TagState] = {}

    def load_from_toml(self, path: Path) -> None:
        with open(path, "rb") as f:
            data = tomllib.load(f)

        for tag_name, props in data.get("tags", {}).items():
            raw_initial = props.get("initial", 0)
            raw_unit = props.get("unit", "")
            # str tags (reason strings) — skip float conversion
            is_str_tag = isinstance(raw_initial, str)
            meta = TagMeta(
                name=tag_name,
                area=props.get("area", "unknown"),
                io_type=props.get("type", "AI"),
                description=props.get("description", ""),
                unit=raw_unit,
                equipment=props.get("equipment", ""),
                min_val=float(props.get("min", 0)),
                max_val=float(props.get("max", 1)),
                initial=raw_initial,
            )
            initial_val: Any = raw_initial
            if is_str_tag:
                pass  # keep as string
            elif meta.io_type in ("DI", "DO"):
                initial_val = bool(int(initial_val))
            else:
                initial_val = float(initial_val)

            self._tags[tag_name] = TagState(
                meta=meta,
                value=initial_val,
                prev_value=initial_val,
                last_changed=time.monotonic(),
            )

    # ── Access ───────────────────────────────────────────────────────────────

    def get(self, tag: str) -> Any:
        return self._tags[tag].value

    def set(self, tag: str, value: Any) -> None:
        state = self._tags[tag]
        state.prev_value = state.value
        if isinstance(state.meta.initial, str) or isinstance(value, str):
            # string tag (e.g. fault reason)
            state.value = str(value)
        elif state.meta.io_type in ("DI", "DO"):
            state.value = int(value) if isinstance(value, int) and not isinstance(value, bool) else bool(value)
        else:
            state.value = float(value)
            state.clamp()
        if state.changed:
            state.last_changed = time.monotonic()

    def set_level_pct(self, tag: str, pct: float) -> None:
        """
        Set a level tag that uses mm as engineering unit.
        pct: 0.0–100.0 → mapped to [meta.min_val, meta.max_val] mm.
        The % → mm conversion happens here so all simulation code
        can still work in 0-100% internally.
        """
        state = self._tags[tag]
        if state.meta.unit == "mm":
            mm = state.meta.min_val + (pct / 100.0) * (state.meta.max_val - state.meta.min_val)
            state.prev_value = state.value
            state.value = round(max(state.meta.min_val, min(state.meta.max_val, mm)), 1)
            if state.changed:
                state.last_changed = time.monotonic()
        else:
            self.set(tag, pct)

    def get_level_pct(self, tag: str) -> float:
        """
        Return level as 0-100% regardless of whether the tag is stored in mm or %.
        """
        state = self._tags[tag]
        if state.meta.unit == "mm":
            span = state.meta.max_val - state.meta.min_val
            if span <= 0:
                return 0.0
            return (float(state.value) - state.meta.min_val) / span * 100.0
        return float(state.value)

    def get_state(self, tag: str) -> TagState:
        return self._tags[tag]

    def all_tags(self) -> dict[str, TagState]:
        return self._tags

    def snapshot(self) -> dict[str, Any]:
        return {k: v.value for k, v in self._tags.items()}

    # ── Fault helpers ─────────────────────────────────────────────────────────

    def is_faulted(self, equipment: str) -> bool:
        for tag, state in self._tags.items():
            if state.meta.equipment == equipment and ("FAULT" in tag or "FLT" in tag):
                if state.value:
                    return True
        return False

    def set_equipment_running(self, equipment: str, running: bool) -> None:
        for tag, state in self._tags.items():
            if state.meta.equipment == equipment:
                if tag.endswith("_RUN") and state.meta.io_type in ("DI", "DO"):
                    self.set(tag, running)