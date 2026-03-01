"""
brewery_simulator/fault_codes.py

Alarm code definitions and reason texts per equipment type.

Severity scale:
    0 = No alarm   — reason: "No fault"
    1 = Low        — informational, equipment still running
    2 = Medium     — degraded operation, attention required
    3 = High       — equipment stopped or safety risk

Usage:
    from brewery_simulator.fault_codes import pick_fault, clear_fault

    code, reason = pick_fault("MILL", rng)
    store.set("DI_MILL_A_FAULT", code)
    store.set("DI_MILL_A_FAULT_REASON", reason)

    code, reason = clear_fault()
    store.set("DI_MILL_A_FAULT", code)
    store.set("DI_MILL_A_FAULT_REASON", reason)
"""
from __future__ import annotations
import random

# ── Alarm reason tables ───────────────────────────────────────────────────────
# Each key maps to a list of (severity, reason_text) tuples.
# pick_fault() draws one randomly, weighted so severity 3 is rarer.

FAULT_REASONS: dict[str, list[tuple[int, str]]] = {

    "MILL": [
        (1, "Motor current slightly above nominal — check roller gap"),
        (1, "Vibration sensor reading elevated — bearing wear suspected"),
        (1, "Roller speed deviation detected — belt tension check required"),
        (1, "Grist particle size out of range — roller adjustment needed"),
        (2, "Motor overload — current exceeded 110% for more than 5 seconds"),
        (2, "Bearing temperature high — lubrication required"),
        (2, "Feed rate imbalance between left and right roller"),
        (2, "Grist case back-pressure detected — auger may be blocked"),
        (3, "Motor thermal protection tripped — cooling required before restart"),
        (3, "Emergency stop activated at local panel"),
        (3, "Drive inverter fault — communication lost with VFD"),
        (3, "Foreign object detected in roller gap — hard stop triggered"),
    ],

    "AUGER": [
        (1, "Motor current slightly above nominal — check for partial blockage"),
        (1, "Speed feedback deviating from setpoint — VFD check recommended"),
        (1, "Grist spillage sensor triggered — inspection recommended"),
        (1, "Coupling vibration elevated — alignment check required"),
        (2, "Motor overload — conveyor partially blocked"),
        (2, "Auger tube temperature high — possible friction buildup"),
        (2, "Drive belt slipping — tension adjustment required"),
        (2, "Grist case overfill — auger paused to prevent overflow"),
        (3, "Motor thermal protection tripped — hard stop"),
        (3, "Emergency stop activated — foreign object in conveyor"),
        (3, "Drive motor stalled — jam detected"),
        (3, "Torque limit exceeded — full blockage, manual clearance required"),
    ],

    "BOILER": [
        (1, "Steam pressure approaching high limit — 85% of setpoint"),
        (1, "Feedwater conductivity slightly elevated — check water treatment"),
        (1, "Flue gas temperature above nominal — burner tuning recommended"),
        (1, "Blowdown valve slow to close — maintenance scheduled"),
        (2, "Feedwater flow reduced — check supply pump"),
        (2, "Burner ignition delayed — check gas pressure"),
        (2, "Steam pressure oscillating — PID tuning required"),
        (2, "Low water level alarm — feedwater control fault"),
        (3, "High pressure safety switch tripped — steam vented to atmosphere"),
        (3, "Burner lockout — multiple failed ignition attempts"),
        (3, "Low-low water level — boiler shut down, manual reset required"),
        (3, "Flue gas high temperature — emergency shutdown"),
    ],

    "RO": [
        (1, "Permeate TDS slightly above setpoint — membrane performance check"),
        (1, "Feed pressure 10% below nominal — pre-filter check required"),
        (1, "Recovery rate below target — check reject valve position"),
        (1, "Conductivity trending upward — scheduled membrane cleaning due"),
        (2, "High differential pressure across membrane — fouling detected"),
        (2, "Feed pump flow reduced — impeller wear suspected"),
        (2, "Permeate pH out of range — chemical dosing fault"),
        (2, "UV sterilizer lamp failure — downstream quality risk"),
        (3, "Feed pump motor fault — RO system offline"),
        (3, "High pressure relief valve opened — overpressure event"),
        (3, "Membrane integrity failure — bypass to drain activated"),
        (3, "Chemical dosing pump fault — process water quality unsafe"),
    ],

    "GLYCOL_PUMP": [
        (1, "Flow rate 5% below setpoint — check for air in system"),
        (1, "Inlet pressure slightly low — expansion tank check recommended"),
        (1, "Motor current elevated — impeller inspection due"),
        (1, "Glycol concentration below target — top-up required"),
        (2, "Flow rate 15% below setpoint — partial blockage suspected"),
        (2, "Pump cavitation detected — suction pressure low"),
        (2, "Motor temperature high — cooling airflow restricted"),
        (2, "Seal leakage detected — maintenance required"),
        (3, "Motor thermal protection tripped — pump offline"),
        (3, "Loss of flow — system header pressure collapsed"),
        (3, "Motor phase loss — VFD protection activated"),
        (3, "Catastrophic seal failure — glycol loss to drain"),
    ],

    "CHILLER": [
        (1, "Suction pressure slightly low — refrigerant charge check"),
        (1, "Condenser approach temperature elevated — fouling suspected"),
        (1, "Compressor current slightly above nominal"),
        (1, "Glycol supply temperature 0.5°C above setpoint"),
        (2, "High discharge pressure — condenser fouling confirmed"),
        (2, "Low suction pressure alarm — possible refrigerant leak"),
        (2, "Compressor overload — capacity reduced to 60%"),
        (2, "Glycol supply temperature 2°C above setpoint — cooling deficit"),
        (3, "Compressor high pressure safety tripped — unit offline"),
        (3, "Low refrigerant level — leak detected, shutdown for safety"),
        (3, "Compressor motor fault — chiller offline"),
        (3, "Freeze protection tripped — glycol outlet below -8°C"),
    ],

    "RAKE": [
        (1, "Rake torque slightly elevated — grain bed compaction detected"),
        (1, "Rake speed deviating from setpoint — VFD check recommended"),
        (1, "Rake arm position sensor intermittent fault"),
        (1, "Grain bed depth uneven — rake path adjustment suggested"),
        (2, "Rake torque high — stuck in compacted grain layer"),
        (2, "VFD overcurrent — speed reduced to 50%"),
        (2, "Rake arm collision detected — obstructed path"),
        (2, "Motor bearing temperature high — lubrication required"),
        (3, "Rake motor thermal protection tripped"),
        (3, "Hard stop — rake arm jammed, manual intervention required"),
        (3, "Gearbox oil temperature critical — immediate shutdown"),
        (3, "Emergency stop activated at vessel panel"),
    ],

    "PUMP": [
        (1, "Flow rate 5% below setpoint — check suction strainer"),
        (1, "Motor current slightly elevated — impeller wear possible"),
        (1, "Outlet pressure slightly below nominal"),
        (1, "Vibration level elevated — coupling alignment check"),
        (2, "Cavitation detected — suction pressure low"),
        (2, "Flow rate 20% below setpoint — strainer blocked"),
        (2, "Motor temperature high — cooling fan failure"),
        (2, "Seal drip rate above limit — mechanical seal worn"),
        (3, "Motor thermal protection tripped — pump offline"),
        (3, "Loss of prime — pump running dry"),
        (3, "Discharge pressure exceeded — check downstream valves"),
        (3, "Motor phase loss — VFD fault"),
    ],

    "HX_PUMP": [
        (1, "Wort inlet flow 5% below setpoint"),
        (1, "Cooling water inlet pressure low — check supply"),
        (1, "Wort outlet temperature 1°C above target"),
        (1, "Pump vibration slightly elevated"),
        (2, "Wort flow reduced 20% — strainer partially blocked"),
        (2, "Cooling water flow insufficient — heat transfer degraded"),
        (2, "Wort outlet temperature 3°C above target — quality risk"),
        (2, "Motor overload — wort viscosity high"),
        (3, "Pump motor fault — heat exchanger offline"),
        (3, "Total loss of wort flow — product at risk"),
        (3, "Wort outlet temperature critical — pitching temperature exceeded"),
        (3, "Motor thermal protection tripped"),
    ],

    "FV_PRV": [
        (1, "PRV opened briefly — minor pressure spike, self-corrected"),
        (1, "Vessel pressure approaching PRV setpoint — monitor CO2 evolution"),
        (1, "PRV seat showing minor weep — inspection due"),
        (1, "CO2 evolution rate above expected for fermentation stage"),
        (2, "PRV opened and held — sustained over-pressure condition"),
        (2, "Spunding valve unable to maintain setpoint — PRV as backup"),
        (2, "Pressure control loop hunting — PID retuning required"),
        (2, "CO2 vent line partially blocked — back-pressure building"),
        (3, "PRV stuck open — pressure relief uncontrolled, product loss"),
        (3, "Over-pressure event — vessel pressure exceeded 2.8 bar"),
        (3, "CO2 recovery line blocked — venting to atmosphere"),
        (3, "Fermentation runaway — temperature and pressure both critical"),
    ],

    "CENTRIFUGE": [
        (1, "Outlet turbidity slightly above target — feed rate adjustment"),
        (1, "Bowl vibration slightly elevated — balance check recommended"),
        (1, "Motor current 5% above nominal"),
        (1, "Solids ejection cycle frequency above expected — high trub load"),
        (2, "Bowl imbalance detected — speed reduced to 70%"),
        (2, "Outlet turbidity above limit — product quality at risk"),
        (2, "CIP cycle overdue — efficiency degrading"),
        (2, "Feed flow rate inconsistent — upstream pump fault"),
        (3, "High vibration emergency stop — bowl severely imbalanced"),
        (3, "Motor thermal protection tripped — centrifuge offline"),
        (3, "Gearbox oil pressure low — immediate shutdown"),
        (3, "Bowl speed runaway — overspeed protection activated"),
    ],

    "FILTER_PUMP": [
        (1, "Differential pressure approaching change-out limit"),
        (1, "Flow rate 5% below setpoint — filter loading"),
        (1, "Filter cartridge life at 75% — plan replacement"),
        (1, "Pump vibration slightly elevated"),
        (2, "Differential pressure high — cartridge replacement due"),
        (2, "Flow rate 25% below setpoint — filter almost blocked"),
        (2, "Motor current elevated — high back-pressure from filter"),
        (2, "Bypass valve opened automatically — pressure relief"),
        (3, "Filter cartridge ruptured — turbidity spike downstream"),
        (3, "Pump motor fault — filtration offline"),
        (3, "Maximum differential pressure exceeded — emergency bypass"),
        (3, "Motor thermal protection tripped"),
    ],

    "KEG_LINE": [
        (1, "Fill pressure slightly below setpoint — CO2 supply check"),
        (1, "Keg counter mismatch — sensor intermittent"),
        (1, "Fill temperature 0.5°C above target"),
        (1, "Labeler label stock low — replenishment required"),
        (2, "Fill pressure out of range — CO2 regulator fault"),
        (2, "Keg leak detected — reject gate activated"),
        (2, "Conveyor jam — line stopped automatically"),
        (2, "Fill temperature above limit — product quality risk"),
        (3, "Line emergency stop — operator activated"),
        (3, "CO2 supply pressure lost — filling halted"),
        (3, "Filler head seal failure — uncontrolled product loss"),
        (3, "Conveyor drive motor fault — line offline"),
    ],

    "CAN_LINE": [
        (1, "Fill volume deviation 2mL above target — flowmeter check"),
        (1, "Inline DO slightly elevated — O2 pickup check"),
        (1, "Seamer chuck wear — seal inspection due"),
        (1, "Can sensor intermittent — count reliability reduced"),
        (2, "Fill volume out of spec — reject gate active"),
        (2, "Dissolved O2 above limit — product shelf life at risk"),
        (2, "Seamer fault — double-seam integrity compromised"),
        (2, "Can jam at filler — line stopped"),
        (3, "Line emergency stop — operator activated"),
        (3, "Seamer catastrophic fault — all cans rejected"),
        (3, "Loss of fill flow — CO2 or beer supply interrupted"),
        (3, "Can filler drive motor fault — line offline"),
    ],

    "LABELER": [
        (1, "Label stock at 20% — replenishment required soon"),
        (1, "Label registration offset detected — minor calibration"),
        (1, "Glue temperature slightly below setpoint"),
        (1, "Label application rate inconsistent — sensor check"),
        (2, "Label stock empty — labeler stopped"),
        (2, "Label skew detected — product cosmetic non-conformance"),
        (2, "Glue pump fault — labels not adhering"),
        (2, "Label jam in magazine — manual clearance required"),
        (3, "Labeler drive motor fault — line downstream stopped"),
        (3, "Emergency stop activated"),
        (3, "Glue system fire suppression triggered"),
        (3, "Label vision system failure — 100% reject gate active"),
    ],

    "CIP_PUMP": [
        (1, "CIP flow rate 5% below setpoint — check circuit valves"),
        (1, "Caustic concentration slightly low — check dosing pump"),
        (1, "Return conductivity below expected — rinse extension triggered"),
        (1, "CIP temperature 2°C below setpoint — heating lag"),
        (2, "CIP flow rate 20% below setpoint — partial valve blockage"),
        (2, "Caustic tank level low — refill required"),
        (2, "Return pH not reaching neutral — extended rinse activated"),
        (2, "CIP temperature below limit — sanitization efficacy at risk"),
        (3, "CIP pump motor fault — cleaning cycle aborted"),
        (3, "Caustic tank empty — CIP sequence halted"),
        (3, "High pressure event in CIP circuit — pump offline"),
        (3, "Motor thermal protection tripped — manual reset required"),
    ],
}

# Severity weights: low faults more common than high
_SEVERITY_WEIGHTS = {1: 0.50, 2: 0.35, 3: 0.15}


def pick_fault(equipment_key: str, rng: random.Random) -> tuple[int, str]:
    """
    Pick a random fault code (1-3) and matching reason for the given equipment.
    Returns (code, reason_text).
    """
    reasons = FAULT_REASONS.get(equipment_key, [])
    if not reasons:
        return (1, "Unspecified fault")

    # Group by severity
    by_sev: dict[int, list[str]] = {1: [], 2: [], 3: []}
    for sev, text in reasons:
        by_sev[sev].append(text)

    # Pick severity first
    sevs = [s for s in [1, 2, 3] if by_sev[s]]
    weights = [_SEVERITY_WEIGHTS[s] for s in sevs]
    total = sum(weights)
    weights = [w / total for w in weights]

    r = rng.random()
    cumulative = 0.0
    chosen_sev = sevs[-1]
    for sev, w in zip(sevs, weights):
        cumulative += w
        if r <= cumulative:
            chosen_sev = sev
            break

    reason = rng.choice(by_sev[chosen_sev])
    return (chosen_sev, reason)


def clear_fault() -> tuple[int, str]:
    """Return the cleared state: code=0, reason='No fault'."""
    return (0, "No fault")
