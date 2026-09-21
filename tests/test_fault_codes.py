"""
Unit tests for brewery_simulator/fault_codes.py

pick_fault() is randomized (weighted by severity), so tests use a seeded
random.Random for determinism and also verify the statistical shape of the
weighting (severity 1 should be drawn far more often than severity 3) over a
large sample, which is the actual behavior this module exists to guarantee.
"""
import random

from brewery_simulator.fault_codes import FAULT_REASONS, clear_fault, pick_fault


class TestClearFault:
    def test_returns_zero_code_and_no_fault_text(self):
        assert clear_fault() == (0, "No fault")


class TestPickFaultUnknownEquipment:
    def test_unknown_key_returns_low_severity_placeholder(self):
        rng = random.Random(1)
        code, reason = pick_fault("NOT_A_REAL_EQUIPMENT", rng)
        assert code == 1
        assert reason == "Unspecified fault"


class TestPickFaultKnownEquipment:
    def test_deterministic_with_seeded_rng(self):
        rng_a = random.Random(7)
        rng_b = random.Random(7)
        assert pick_fault("MILL", rng_a) == pick_fault("MILL", rng_b)

    def test_returns_valid_severity_and_matching_reason(self):
        rng = random.Random(3)
        code, reason = pick_fault("BOILER", rng)
        assert code in (1, 2, 3)
        valid_reasons_for_severity = [
            text for sev, text in FAULT_REASONS["BOILER"] if sev == code
        ]
        assert reason in valid_reasons_for_severity

    def test_every_defined_equipment_key_produces_a_valid_fault(self):
        rng = random.Random(0)
        for equipment_key in FAULT_REASONS:
            code, reason = pick_fault(equipment_key, rng)
            assert code in (1, 2, 3)
            assert isinstance(reason, str) and reason

    def test_severity_1_is_drawn_more_often_than_severity_3(self):
        # _SEVERITY_WEIGHTS = {1: 0.50, 2: 0.35, 3: 0.15} — over a large sample
        # low-severity faults must dominate high-severity ones.
        rng = random.Random(2024)
        counts = {1: 0, 2: 0, 3: 0}
        for _ in range(2000):
            code, _ = pick_fault("PUMP", rng)
            counts[code] += 1
        assert counts[1] > counts[2] > counts[3]
