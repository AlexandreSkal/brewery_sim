# 🍺 Brewery Simulator

**Industrial Brewery PLC/SCADA Simulator** — publishes **335+ IOs** to an MQTT5 broker, simulating a full-scale craft brewery with dual production lines, 6 fermenters, packaging lines, and real-time MES KPIs.

Built for **Ignition SCADA / HMI development** without needing physical hardware.

---

## Architecture

```
config.toml + tags.toml
       ↓
  BreweryEngine
  ├─ MillingArea       (Area 100 — 2× Mill Lines)
  ├─ UtilitiesArea     (Area 200 — HLT, Boiler, Chiller, RO)
  ├─ BrewhouseArea     (Area 300 — 2× Full Brewhouse Lines)
  ├─ CoolingArea       (Area 400 — 2× Heat Exchangers + Aeration)
  ├─ FermentationArea  (Area 500 — 6× FVs + CO2 Recovery)
  ├─ MaturationArea    (Area 600 — 2× BBT + Filter + Centrifuge)
  ├─ PackagingArea     (Area 700 — Kegging + Canning Lines)
  ├─ CIPArea           (Area 800 — Central CIP Station)
  └─ MESCalculator     (Area MES — OEE, KPIs, batch metrics)
       ↓
  MQTTPublisher → MQTT5 Broker → Ignition
```

**MQTT topic structure:**
```
brewery/<area>/<TAG_NAME>          ← live values (JSON)
brewery/meta/<area>/<TAG_NAME>     ← tag metadata, retained (JSON)
```

**Payload format:**
```json
{"tag":"AI_FV1_TT","value":19.87,"unit":"°C","ts":1708000000.123,"quality":"Good"}
```

---

## Quick Start

```bash
# Install dependencies
uv sync

# Real-time (default)
uv run brewery-sim

# Fast mode — 1 sim-min per real second
uv run brewery-sim --speed 60

# Turbo — 1 sim-hour per real second (great for testing all states)
uv run brewery-sim --speed 3600

# Named presets: realtime | fast | turbo | warp
uv run brewery-sim --preset turbo

# Custom broker
uv run brewery-sim --host 192.168.1.50 --port 1883

# Validate config without connecting
uv run brewery-sim --dry-run

# List all 335 tags
uv run brewery-sim list-tags
uv run brewery-sim list-tags --area a500_fermentation --type AI
```

---

## IO Summary (335 tags)

| Area | DI | DO | AI | AO | Total |
|------|----|----|----|----|-------|
| 100 Milling | 14 | 4 | 6 | 0 | 24 |
| 200 Utilities | 15 | 7 | 17 | 5 | 44 |
| 300 Brewhouse L1+L2 | 32 | 12 | 30 | 6 | 80 |
| 400 HX & Aeration | 4 | 6 | 8 | 4 | 22 |
| 500 Fermentation 6×FV | 27 | 18 | 41 | 12 | 98 |
| 600 BBT & Filtration | 8 | 6 | 19 | 4 | 37 |
| 700 Packaging | 9 | 3 | 8 | 0 | 20 |
| 800 CIP | 5 | 2 | 7 | 2 | 16 |
| 900 Utility Meters | 0 | 0 | 7 | 0 | 7 |
| MES Calculated | 0 | 0 | 13 | 0 | 13 |

---

## MES KPIs

`MES_OEE_BH1/BH2`, `MES_OEE_PKG`, `MES_BH_EFF_L1/L2`, `MES_WATER_HL`, `MES_STEAM_HL`, `MES_KWH_HL`, `MES_CO2_RECOVERY`, `MES_BEER_LOSS_PCT`, `MES_PROD_TODAY_HL`, `MES_BATCH_COUNT`, `MES_ACTIVE_ALARMS`

---

## Simulation Behaviour

- **State machines** per equipment (e.g. FV: EMPTY→FILLING→LAG→ACTIVE→DIACETYL→COLD_CRASH→DRAIN)
- **Fault propagation**: random faults at configurable probability, auto-recovery after delay
- **Physical models**: first-order lag temperatures, S-curve fermentation attenuation, pressure from CO2
- **Staggered starts**: parallel lines start at offsets so all states are visible simultaneously
- **Speed control**: `--speed 1` = real-time, `--speed 3600` = 1 hour/second

---

## Mosquitto Quick Setup

```bash
# Docker
docker run -it -p 1883:1883 eclipse-mosquitto

# Verify messages
mosquitto_sub -h localhost -t "brewery/#" -v
```

## Ignition Integration

1. Install MQTT Engine module
2. Point to broker `localhost:1883`
3. Subscribe to `brewery/#`
4. Tags auto-populate the tag browser
5. `brewery/meta/<area>/<tag>` retained topics carry description, unit, min/max
