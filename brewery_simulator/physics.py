"""
brewery_simulator/physics.py
Lightweight physical model helpers.
All functions are pure / stateless — they take current state and return new value.
"""
from __future__ import annotations

import math
import random


def approach(current: float, setpoint: float, rate: float, dt: float) -> float:
    """
    First-order lag: exponential approach toward setpoint.
    rate: fraction of error closed per second (e.g. 0.002 = 0.2%/s)
    """
    error = setpoint - current
    return current + error * rate * dt


def linear_ramp(current: float, target: float, rate: float, dt: float) -> float:
    """Move toward target at constant rate (units/second)."""
    delta = rate * dt
    if abs(target - current) <= delta:
        return target
    return current + math.copysign(delta, target - current)


def fill_tank(level: float, rate: float, dt: float, cap: float = 100.0) -> float:
    """Increase tank level (%) at given rate (%/s), capped at cap."""
    return min(cap, level + rate * dt)


def drain_tank(level: float, rate: float, dt: float, floor: float = 0.0) -> float:
    """Decrease tank level (%) at given rate (%/s), floored at floor."""
    return max(floor, level - rate * dt)


def add_noise(value: float, std: float, rng: random.Random) -> float:
    """Add Gaussian noise."""
    return value + rng.gauss(0.0, std)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def fermentation_brix(
    elapsed_s: float,
    og: float,
    fg: float,
    total_duration_s: float,
) -> float:
    """
    S-curve Brix drop: fast start, slow middle, plateau at FG.
    elapsed_s: seconds since start of active fermentation
    """
    if total_duration_s <= 0:
        return fg
    t = clamp(elapsed_s / total_duration_s, 0.0, 1.0)
    # Logistic-like curve
    s = 1.0 / (1.0 + math.exp(-10 * (t - 0.35)))
    return og - (og - fg) * s


def pressure_from_co2(brix_drop: float, temp_c: float) -> float:
    """
    Approximate tank pressure from CO2 produced (bar).
    brix_drop: °Plato dropped since pitching
    temp_c: beer temperature
    """
    co2_factor = brix_drop * 0.47  # rough g/L CO2 per °P
    # Henry's law rough approximation: higher temp = more pressure
    henry = 0.00393 * math.exp(0.0267 * temp_c)
    return clamp(co2_factor * henry, 0.0, 2.5)


def turbidity_lauter(
    elapsed_s: float,
    recirc_done: bool,
    flow_rate: float,
) -> float:
    """
    Turbidity starts high, drops exponentially after recirculation.
    """
    if not recirc_done:
        return clamp(800.0 - elapsed_s * 2.0, 200.0, 800.0)
    # After recirc: exponential clearance, slightly worse at high flow
    base = 80.0 + flow_rate * 0.05
    decay = math.exp(-elapsed_s / 900.0)
    return clamp(base + 300.0 * decay, base, 500.0)
