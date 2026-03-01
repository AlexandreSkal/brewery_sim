# 🍺 Brewery Simulator (v3.0)

**Industrial Brewery PLC/SCADA Simulator** — publishes **500+ IOs** to an MQTT5 broker and serves an **HTTP API**, simulating a full-scale craft brewery with dual production lines, 6 fermenters, packaging lines, and comprehensive real-time MES KPIs.

Built for **Ignition SCADA / HMI development** without needing physical hardware. It fully supports ISA-101 design principles, dynamic alarms, and UDT (User Defined Type) instantiation.

---

## 🏗️ Architecture

```text
config.toml + tags.toml
       ↓
 BreweryEngine
 ├─ MillingArea        (Area 100 — 2× Mill Lines + Grist Cases)
 ├─ UtilitiesArea      (Area 200 — HLT, Boiler, Chiller, RO)
 ├─ BrewhouseArea      (Area 300 — 2× Full Brewhouse Lines)
 ├─ CoolingArea        (Area 400 — 2× Heat Exchangers + Aeration)
 ├─ FermentationArea   (Area 500 — 6× FVs + CO2 Recovery)
 ├─ MaturationArea     (Area 600 — 2× BBT + Filter + Centrifuge)
 ├─ PackagingArea      (Area 700 — Kegging + Canning Lines + Labeler)
 ├─ CIPArea            (Area 800 — Central CIP Station)
 └─ MES & Meters       (Area 900 — OEE, KPIs, Batch metrics, Plant Totalizers)
       ↓
 MQTTPublisher → MQTT5 Broker → Ignition (MQTT Engine)
       ↓
 HTTP Fast API → localhost:8000 (External integrations)
```

**MQTT topic structure:**

```text
brewery/<area>/<TAG_NAME>          ← live values (JSON)
brewery/meta/<area>/<TAG_NAME>     ← tag metadata, retained (JSON)
```

**Payload examples:**

```json
{"tag":"AI_FV1_TT","value":19.87,"unit":"°C","ts":1708000000.123,"quality":"Good"}
{"tag":"DI_FV1_PRV","value":2,"unit":"","ts":1708000001.000,"quality":"Good"}  // Severity Int (0-3)
{"tag":"DI_FV1_PRV_REASON","value":"Pressure relief valve opened","unit":"str","ts":1708000001.000,"quality":"Good"}
```

---

## 🚀 Quick Start (Development)

```bash
# Install dependencies using uv
uv sync

# Real-time simulation + HTTP API on port 8000 (default)
uv run brewery-sim

# Fast mode — 1 sim-minute per real second
uv run brewery-sim --speed 60

# Turbo — 1 sim-hour per real second (great for testing all states quickly)
uv run brewery-sim --speed 3600

# Custom API port
uv run brewery-sim --api-port 9000

# Disable HTTP API
uv run brewery-sim --no-api

# Validate config without connecting to MQTT
uv run brewery-sim --dry-run

# List all tags in the system
uv run brewery-sim tags
```

---

## 🛠️ Production Deployment (Linux)

For running the simulator as a background service on a server (e.g., Oracle Cloud Linux ARM / Ubuntu), an installation script is provided.

```bash
# 1. Run the install script as root
sudo bash install.sh

# The script will:
# - Install system dependencies (python3, pip, curl, git)
# - Install the 'uv' package manager
# - Create a dedicated 'brewery' user
# - Setup the app in /opt/brewery-sim
# - Create and start the systemd service (brewery-sim.service)

# 2. Check the service status
systemctl status brewery-sim

# 3. View live logs
journalctl -u brewery-sim -f
```

---

## 📊 MES & Quality KPIs (Area 900)

The simulator includes a dedicated MES (Manufacturing Execution System) engine that calculates plant-wide metrics in real-time:

* **OEE (Overall Equipment Effectiveness):** Plant-wide, Brewhouse lines, and Packaging OEE.
* **Production Totals:** `MES_PLANT_HL_SHIFT`, `MES_PLANT_HL_DAILY`, `MES_PLANT_BATCH_TODAY`.
* **Utility Metrics:** Real-time ratios like `MES_UTIL_WATER_HL` (Water hl/hl), `MES_UTIL_KWH_HL` (Energy kWh/hl).
* **Quality Metrics:** Estimated ABV, attenuation averages, and CO2 recovery percentages.
* **Alarm Aggregation:** Active alarm counts per area for high-level dashboard visualization.

---

## ⚙️ Simulation Behaviour (V3 Features)

* **State Machines:** Each equipment has dedicated lifecycle states (e.g., FV: EMPTY → FILLING → LAG → ACTIVE → DIACETYL → COLD_CRASH → DRAIN).
* **Fault Propagation & Severity:** Faults are no longer just booleans. They output an Integer (`0=OK`, `1=Warning`, `2=Alarm`, `3=Critical`) alongside a dynamic String Reason tag explaining the exact fault (e.g., "Motor overload", "PRV opened").
* **Dynamic Setpoints:** Level switches now have configurable `_SP` tags (e.g., `AI_FV1_LS_HI_SP`), allowing the Ignition HMI to adjust the physical switch thresholds dynamically.
* **Physical Models:** First-order lag temperatures, S-curve fermentation attenuation, and pressure build-up from CO2 generation.
* **Staggered Starts:** Parallel lines start at different offsets so all process states are visible simultaneously on your SCADA.

---

## 🔌 Ignition SCADA Integration

1. Install the **MQTT Engine** module in your Ignition Gateway.
2. Point the MQTT Engine to your broker (`localhost:1883` or your server IP).
3. Subscribe to the `brewery/#` namespace.
4. Tags will auto-populate in the Tag Browser under `MQTT Engine/Edge Nodes/brewery/...`.
5. Use the UDT mappings below to build your data models.