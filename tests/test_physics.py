"""
Unit tests for brewery_simulator/physics.py

All functions under test are pure (no I/O, no shared state), so these are
classic white-box unit tests: fixed inputs, deterministic outputs, no mocks
needed.
"""
import random

import pytest

from brewery_simulator.physics import (
    approach,
    linear_ramp,
    fill_tank,
    drain_tank,
    add_noise,
    clamp,
    fermentation_brix,
    pressure_from_co2,
    turbidity_lauter,
)


class TestApproach:
    def test_moves_toward_setpoint(self):
        result = approach(current=10.0, setpoint=20.0, rate=0.5, dt=1.0)
        assert result == pytest.approx(15.0)

    def test_no_movement_when_at_setpoint(self):
        assert approach(current=20.0, setpoint=20.0, rate=0.5, dt=1.0) == 20.0

    def test_moves_downward_when_above_setpoint(self):
        result = approach(current=30.0, setpoint=10.0, rate=0.1, dt=1.0)
        assert result < 30.0
        assert result == pytest.approx(28.0)

    def test_zero_dt_means_no_change(self):
        assert approach(current=10.0, setpoint=99.0, rate=0.9, dt=0.0) == 10.0


class TestLinearRamp:
    def test_ramps_up_by_rate_times_dt(self):
        assert linear_ramp(current=0.0, target=10.0, rate=2.0, dt=1.0) == 2.0

    def test_ramps_down_by_rate_times_dt(self):
        assert linear_ramp(current=10.0, target=0.0, rate=2.0, dt=1.0) == 8.0

    def test_snaps_to_target_when_within_step(self):
        # delta (5*1=5) is larger than the remaining distance (2) -> snap
        assert linear_ramp(current=8.0, target=10.0, rate=5.0, dt=1.0) == 10.0

    def test_already_at_target(self):
        assert linear_ramp(current=5.0, target=5.0, rate=1.0, dt=1.0) == 5.0


class TestFillDrainTank:
    def test_fill_increases_level(self):
        assert fill_tank(level=50.0, rate=10.0, dt=1.0) == 60.0

    def test_fill_caps_at_default_100(self):
        assert fill_tank(level=95.0, rate=10.0, dt=1.0) == 100.0

    def test_fill_respects_custom_cap(self):
        assert fill_tank(level=45.0, rate=10.0, dt=1.0, cap=50.0) == 50.0

    def test_drain_decreases_level(self):
        assert drain_tank(level=50.0, rate=10.0, dt=1.0) == 40.0

    def test_drain_floors_at_default_zero(self):
        assert drain_tank(level=5.0, rate=10.0, dt=1.0) == 0.0

    def test_drain_respects_custom_floor(self):
        assert drain_tank(level=15.0, rate=10.0, dt=1.0, floor=10.0) == 10.0


class TestClamp:
    def test_within_range_unchanged(self):
        assert clamp(5.0, 0.0, 10.0) == 5.0

    def test_clamps_to_lower_bound(self):
        assert clamp(-5.0, 0.0, 10.0) == 0.0

    def test_clamps_to_upper_bound(self):
        assert clamp(15.0, 0.0, 10.0) == 10.0


class TestAddNoise:
    def test_zero_std_returns_exact_value(self):
        rng = random.Random(42)
        assert add_noise(100.0, std=0.0, rng=rng) == 100.0

    def test_deterministic_with_seeded_rng(self):
        # Same seed -> same sequence, so two independent RNGs must agree.
        rng_a = random.Random(1)
        rng_b = random.Random(1)
        assert add_noise(50.0, std=2.0, rng=rng_a) == add_noise(50.0, std=2.0, rng=rng_b)


class TestFermentationBrix:
    def test_returns_fg_when_duration_zero_or_negative(self):
        assert fermentation_brix(elapsed_s=100, og=14.0, fg=2.5, total_duration_s=0) == 2.5
        assert fermentation_brix(elapsed_s=100, og=14.0, fg=2.5, total_duration_s=-10) == 2.5

    def test_starts_near_og(self):
        # At t=0 the logistic curve isn't at its floor yet (s(0) = 1/(1+e^3.5) ~= 0.029),
        # so "near OG" here means "closer to OG than to FG", not within a tight epsilon.
        result = fermentation_brix(elapsed_s=0, og=14.0, fg=2.5, total_duration_s=1000)
        assert abs(result - 14.0) < abs(result - 2.5)
        assert result == pytest.approx(13.66, abs=0.01)

    def test_ends_near_fg(self):
        result = fermentation_brix(elapsed_s=1000, og=14.0, fg=2.5, total_duration_s=1000)
        assert result == pytest.approx(2.5, abs=0.05)

    def test_monotonically_decreasing(self):
        samples = [
            fermentation_brix(elapsed_s=t, og=14.0, fg=2.5, total_duration_s=1000)
            for t in range(0, 1001, 100)
        ]
        assert all(a >= b for a, b in zip(samples, samples[1:]))


class TestPressureFromCo2:
    def test_zero_brix_drop_gives_zero_pressure(self):
        assert pressure_from_co2(brix_drop=0.0, temp_c=20.0) == 0.0

    def test_higher_brix_drop_gives_more_pressure(self):
        low = pressure_from_co2(brix_drop=1.0, temp_c=20.0)
        high = pressure_from_co2(brix_drop=5.0, temp_c=20.0)
        assert high > low

    def test_result_is_clamped_to_2_5_bar_max(self):
        result = pressure_from_co2(brix_drop=1000.0, temp_c=50.0)
        assert result == 2.5

    def test_never_negative(self):
        assert pressure_from_co2(brix_drop=-5.0, temp_c=20.0) >= 0.0


class TestTurbidityLauter:
    def test_high_before_recirc(self):
        result = turbidity_lauter(elapsed_s=0, recirc_done=False, flow_rate=100.0)
        assert result == 800.0

    def test_decreases_over_time_before_recirc(self):
        early = turbidity_lauter(elapsed_s=0, recirc_done=False, flow_rate=100.0)
        later = turbidity_lauter(elapsed_s=100, recirc_done=False, flow_rate=100.0)
        assert later < early

    def test_floors_at_200_before_recirc(self):
        result = turbidity_lauter(elapsed_s=10_000, recirc_done=False, flow_rate=100.0)
        assert result == 200.0

    def test_drops_sharply_right_after_recirc(self):
        just_after = turbidity_lauter(elapsed_s=0, recirc_done=True, flow_rate=100.0)
        long_after = turbidity_lauter(elapsed_s=5000, recirc_done=True, flow_rate=100.0)
        assert just_after > long_after

    def test_higher_flow_rate_raises_floor(self):
        low_flow = turbidity_lauter(elapsed_s=5000, recirc_done=True, flow_rate=0.0)
        high_flow = turbidity_lauter(elapsed_s=5000, recirc_done=True, flow_rate=1000.0)
        assert high_flow > low_flow
