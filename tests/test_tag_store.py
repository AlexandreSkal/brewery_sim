"""
Unit tests for brewery_simulator/tag_store.py (TagStore + TagState).

load_from_toml() is the only method that touches the filesystem; it is
exercised here against a small temp TOML file rather than the real
tags.toml, keeping the suite fast and independent of production data.
"""
import pytest

from brewery_simulator.tag_store import TagStore

SAMPLE_TOML = """
[tags.AI_TEST_TEMP]
type = "AI"
area = "100"
equipment = "TEST"
description = "Test analog tag"
unit = "degC"
min = 0
max = 100
initial = 20.0

[tags.DI_TEST_RUN]
type = "DI"
area = "100"
equipment = "TEST"
description = "Test digital tag"
unit = ""
initial = 0

[tags.DI_TEST_FAULT]
type = "DI"
area = "100"
equipment = "TEST"
description = "Test fault tag"
unit = ""
initial = 0

[tags.AI_TEST_LEVEL]
type = "AI"
area = "100"
equipment = "TANK1"
description = "Level in mm"
unit = "mm"
min = 0
max = 2000
initial = 0
"""


@pytest.fixture
def store(tmp_path):
    toml_path = tmp_path / "tags.toml"
    toml_path.write_text(SAMPLE_TOML)
    s = TagStore()
    s.load_from_toml(toml_path)
    return s


class TestLoadFromToml:
    def test_loads_all_tags(self, store):
        assert set(store.all_tags().keys()) == {
            "AI_TEST_TEMP", "DI_TEST_RUN", "DI_TEST_FAULT", "AI_TEST_LEVEL",
        }

    def test_analog_initial_value_is_float(self, store):
        assert store.get("AI_TEST_TEMP") == 20.0

    def test_digital_initial_value_is_bool(self, store):
        assert store.get("DI_TEST_RUN") is False


class TestGetSet:
    def test_set_then_get_analog(self, store):
        store.set("AI_TEST_TEMP", 55.5)
        assert store.get("AI_TEST_TEMP") == 55.5

    def test_set_clamps_analog_to_min_max(self, store):
        store.set("AI_TEST_TEMP", 9999.0)
        assert store.get("AI_TEST_TEMP") == 100.0
        store.set("AI_TEST_TEMP", -9999.0)
        assert store.get("AI_TEST_TEMP") == 0.0

    def test_set_digital_accepts_bool(self, store):
        store.set("DI_TEST_RUN", True)
        assert store.get("DI_TEST_RUN") is True

    def test_changed_flag_true_after_value_change(self, store):
        state = store.get_state("DI_TEST_RUN")
        assert state.changed is False
        store.set("DI_TEST_RUN", True)
        assert state.changed is True

    def test_changed_flag_false_when_value_unchanged(self, store):
        store.set("AI_TEST_TEMP", 20.0)  # same as initial
        assert store.get_state("AI_TEST_TEMP").changed is False


class TestLevelPercent:
    def test_set_level_pct_converts_to_mm(self, store):
        store.set_level_pct("AI_TEST_LEVEL", 50.0)
        assert store.get("AI_TEST_LEVEL") == 1000.0

    def test_get_level_pct_converts_back_from_mm(self, store):
        store.set_level_pct("AI_TEST_LEVEL", 25.0)
        assert store.get_level_pct("AI_TEST_LEVEL") == pytest.approx(25.0)

    def test_level_pct_clamped_to_tank_bounds(self, store):
        store.set_level_pct("AI_TEST_LEVEL", 150.0)
        assert store.get("AI_TEST_LEVEL") == 2000.0

    def test_get_level_pct_on_non_mm_tag_returns_raw_value(self, store):
        store.set("AI_TEST_TEMP", 42.0)
        assert store.get_level_pct("AI_TEST_TEMP") == 42.0


class TestFaultHelpers:
    def test_is_faulted_false_by_default(self, store):
        assert store.is_faulted("TEST") is False

    def test_is_faulted_true_when_fault_tag_set(self, store):
        store.set("DI_TEST_FAULT", True)
        assert store.is_faulted("TEST") is True

    def test_is_faulted_ignores_other_equipment(self, store):
        store.set("DI_TEST_FAULT", True)
        assert store.is_faulted("TANK1") is False


class TestSnapshot:
    def test_snapshot_returns_plain_value_dict(self, store):
        snap = store.snapshot()
        assert snap["AI_TEST_TEMP"] == 20.0
        assert snap["DI_TEST_RUN"] is False
