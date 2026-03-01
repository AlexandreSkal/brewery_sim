# 🍺 IronForge Brewery

## Equipment UDT Library
**IO Structure per Equipment Type — Ignition UDT Configuration** **Version 3.0** — Updated: Included A900 MES Layer, Plant Meters, Labeler, and missing power/loss metrics.

---

### IO Type & Data Type Legend

| Type | Meaning | Data Type | Direction | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **DI** | Digital Input | Boolean | PLC ← Field | Discrete feedback from field devices |
| **DO** | Digital Output | Boolean | PLC → Field | Discrete command to actuators/MCC |
| **AI** | Analog Input | Float (EU) | PLC ← Transmitter | Process measurements in engineering units |
| **AO** | Analog Output | Float (EU) | PLC → Actuator | Setpoints and control outputs |
| **Fault DI**| Fault/Alarm DI | Int (0–3) ★ | PLC ← Field | 0=OK, 1=Warning, 2=Alarm, 3=Critical |
| **STR** | Fault Reason | String ★ | PLC internal | Text description of active fault. Suffix: _REASON |

---

### UDT Index

| # | UDT Name | Area | Description | IO Count |
| :--- | :--- | :--- | :--- | :--- |
| 1 | UDT_Silo | A100 — Milling | Malt silo with load cell, level switches and configurable switch setpoints. | 8 members |
| 2 | UDT_Mill | A100 — Milling | Roller mill motor with run feedback, fault severity and current monitoring. | 9 members |
| 3 | UDT_Auger | A100 — Milling | Screw conveyor (auger) for grist transfer with run feedback, fault severity and reason. | 5 members |
| 4 | UDT_GristCase | A100 — Milling | Grist case buffer vessel between mill and mash tun, with load cell and configurable LS_HI setpoint. | 6 members |
| 5 | UDT_HLT | A200 — Utilities | Hot Liquor Tank — heated water storage with level, temperature, power, setpoint and switch setpoints. | 11 members |
| 6 | UDT_CLT | A200 — Utilities | Cold Liquor Tank — chilled water storage with glycol cooling and switch setpoints. | 10 members |
| 7 | UDT_Boiler | A200 — Utilities | Steam boiler with pressure, temperature, flow, safety interlocks and fault severity. | 11 members |
| 8 | UDT_Chiller | A200 — Utilities | Glycol chiller with supply/return temps, flow, setpoint, fault severity and reason strings. | 14 members |
| 9 | UDT_ROSystem | A200 — Utilities | Reverse osmosis water treatment unit. | 6 members |
| 10 | UDT_MashTun | A300 — Brewhouse | Mash tun with temperature, level, pH, rake, transfer pump, fault severity and switch setpoints. | 19 members |
| 11 | UDT_LauterTun| A300 — Brewhouse | Lauter tun with rake (VFD), level, turbidity, wort brix, flow, fault severity and switch setpoints. | 16 members |
| 12 | UDT_Kettle | A300 — Brewhouse | Brew kettle with steam heating, level, temperature, power tracking, and switch setpoints. | 12 members |
| 13 | UDT_Whirlpool| A300 — Brewhouse | Whirlpool vessel for trub separation with pump, level, turbidity, fault severity and switch setpoints. | 12 members |
| 14 | UDT_HeatExchanger| A400 — Cooling | Plate heat exchanger for wort cooling with inlet/outlet temps, flow, O2 injection, fault severity. | 13 members |
| 15 | UDT_FermentationVessel | A500 — Ferm. | Cylindroconical FV with full quality suite, glycol control, PRV alarm, fault severity, switch setpoints. | 23 members |
| 16 | UDT_YeastBrink | A500 — Ferm. | Yeast propagation/storage vessel with temperature and level. | 2 members |
| 17 | UDT_CO2Recovery| A500 — Ferm. | CO2 recovery system — capture from FVs, compression and storage. | 3 members |
| 18 | UDT_BBT | A600 — Maturation| Bright Beer Tank — full quality suite with configurable switch setpoints and beer loss tracking. | 20 members |
| 19 | UDT_Centrifuge| A600 — Maturation| Centrifuge for beer clarification with fault severity. | 6 members |
| 20 | UDT_CartridgeFilter| A600 — Maturation| Cartridge filter with differential pressure, flow and fault severity. | 6 members |
| 21 | UDT_KegLine | A700 — Packaging| Kegging line with counter, fill pressure, temperature, power, losses, fault severity and reason string. | 12 members |
| 22 | UDT_CanLine | A700 — Packaging| Canning line with counter, inline DO, fill volume quality monitoring, fault severity and reason. | 9 members |
| 23 | UDT_Labeler ★ | A700 — Packaging| Labeling machine with run feedback, start command, fault severity and reason. | 4 members |
| 24 | UDT_CIPStation| A800 — CIP | CIP station with caustic, acid and rinse tanks, full quality monitoring, power, fault severity and reason. | 17 members |
| 25 | UDT_PlantMeters ★| A900 — Utilities| Global plant totalizers for water, steam, CO2, and electrical consumption. | 5 members |
| 26 | UDT_EnvironmentSensor ★| A900 — Utilities| Plant ambient temperature and humidity monitoring. | 2 members |
| 27 | UDT_MES_PlantOverview ★| A900 — MES | Global plant production, OEE, targets, and alarm metrics. | 10 members |
| 28 | UDT_MES_Brewhouse ★| A900 — MES | OEE, availability, and specific KPIs for Brewhouse lines. | 5 members |
| 29 | UDT_MES_Fermentation ★| A900 — MES | Aggregated metrics for the fermentation block. | 5 members |
| 30 | UDT_MES_Utilities ★| A900 — MES | Aggregated consumption metrics for water, steam, and electricity relative to production. | 6 members |

---

### A100 — Milling

#### UDT_Silo
Malt silo with load cell, level switches and configurable switch setpoints.
Instance example: `IronForge/BreweryBH/Milling/MILL-A/Silo-A/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | LS_Hi | DI_{S}_LS_HI | High level switch | Boolean | 0/1 |
| DI | LS_Lo | DI_{S}_LS_LO | Low level switch | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | Weight | AI_{S}_WT | Weight via load cell (kg) | Float | 0–5000 kg |
| AI | Weight_LimH | AI_{S}_WT_LIM_H | Weight range high limit | Float | 5000 kg |
| AI | Weight_LimL | AI_{S}_WT_LIM_L | Weight range low limit | Float | 0 kg |
| **AO — Analog Outputs (Setpoints)** | | | | | |
| AO | LS_Hi_SP | AI_{S}_LS_HI_SP | Setpoint LS_HI activation (kg) | Float | 0–5000 kg |
| AO | LS_Lo_SP | AI_{S}_LS_LO_SP | Setpoint LS_LO activation (kg) | Float | 0–5000 kg |

#### UDT_Mill
Roller mill motor with run feedback, fault severity and current monitoring.
Instance example: `IronForge/BreweryBH/Milling/MILL-A/Mill-A/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | Running | DI_MILL_{X}_RUN | Running feedback from MCC | Boolean | 0/1 |
| DI | Fault | DI_MILL_{X}_FAULT | Motor fault severity | Int | 0–3 ★ |
| **DO — Digital Outputs** | | | | | |
| DO | Start | DO_MILL_{X}_RUN | Start command to MCC | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | Current | AI_MILL_{X}_CURR | Motor current (A) | Float | 0–50 A |
| AI | Curr_LimH | AI_MILL_{X}_CURR_LIM_H | Current range high | Float | 50 A |
| AI | Curr_LimL | AI_MILL_{X}_CURR_LIM_L | Current range low | Float | 0 A |
| **String — Fault Reason** | | | | | |
| STR | FaultReason | DI_MILL_{X}_FAULT_REASON | Fault description text | String | Text |
| STR | AugFaultRsn | DI_AUG_{X}_FAULT_REASON | Auger fault description text | String | Text |

#### UDT_Auger
Screw conveyor (auger) for grist transfer with run feedback, fault severity and reason.
Instance example: `IronForge/BreweryBH/Milling/MILL-A/Auger-A/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | Running | DI_AUG_{X}_RUN | Running feedback | Boolean | 0/1 |
| DI | Fault | DI_AUG_{X}_FAULT | Motor fault severity | Int | 0–3 ★ |
| **DO — Digital Outputs** | | | | | |
| DO | Start | DO_AUG_{X}_RUN | Start command | Boolean | 0/1 |
| **String — Fault Reason** | | | | | |
| STR | FaultReason | DI_AUG_{X}_FAULT_REASON | Fault description text | String | Text |

#### UDT_GristCase
Grist case buffer vessel between mill and mash tun, with load cell and configurable LS_HI setpoint.
Instance example: `IronForge/BreweryBH/Milling/MILL-A/GristCase-A/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | LS_Hi | DI_GRC_{X}_LS_HI | High level switch | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | Weight | AI_GRC_{X}_WT | Weight via load cell (kg) | Float | 0–500 kg |
| AI | Weight_LimH | AI_GRC_{X}_WT_LIM_H | Weight range high limit | Float | 500 kg |
| AI | Weight_LimL | AI_GRC_{X}_WT_LIM_L | Weight range low limit | Float | 0 kg |
| **AO — Analog Outputs (Setpoints)** | | | | | |
| AO | LS_Hi_SP | AI_GRC_{X}_LS_HI_SP | Setpoint LS_HI activation (kg) | Float | 0–500 kg |

---

### A200 — Utilities

#### UDT_HLT
Hot Liquor Tank — heated water storage with level, temperature, setpoint, power tracking and switch setpoints.
Instance example: `IronForge/BreweryBH/Utilities/HLT/HLT-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | LS_Hi | DI_{H}_LS_HI | High level switch | Boolean | 0/1 |
| DI | LS_Lo | DI_{H}_LS_LO | Low level switch | Boolean | 0/1 |
| **DO — Digital Outputs** | | | | | |
| DO | HeatEnable | DO_{H}_HEAT_EN | Enable heating element | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | Temp | AI_{H}_TT | Temperature (°C) | Float | 0–100°C |
| AI | Level | AI_{H}_LT | Level (mm) | Float | 0–2200 mm |
| AI | Level_LimH | AI_{H}_LT_LIM_H | Level range high | Float | 2200 mm |
| AI | Level_LimL | AI_{H}_LT_LIM_L | Level range low | Float | 0 mm |
| AI | PowerKW ★ | AI_ELEC_KW_{H} | HLT electrical consumption | Float | 0–50 kW |
| **AO — Analog Outputs** | | | | | |
| AO | TempSP | AO_{H}_HEAT_SP | Temperature setpoint (°C) | Float | 0–100°C |
| AO | LS_Hi_SP | AI_{H}_LS_HI_SP | Setpoint LS_HI activation (%) | Float | 0–100% |
| AO | LS_Lo_SP | AI_{H}_LS_LO_SP | Setpoint LS_LO activation (%) | Float | 0–100% |

#### UDT_CLT
Cold Liquor Tank — chilled water storage with glycol cooling and switch setpoints.
Instance example: `IronForge/BreweryBH/Utilities/CLT/CLT-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | LS_Hi | DI_CLT_LS_HI | High level switch | Boolean | 0/1 |
| DI | LS_Lo | DI_CLT_LS_LO | Low level switch | Boolean | 0/1 |
| **DO — Digital Outputs** | | | | | |
| DO | GlycolEn | DO_CLT_GLYCOL_EN | Enable glycol cooling | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | Temp | AI_CLT_TT | Temperature (°C) | Float | 0–20°C |
| AI | Level | AI_CLT_LT | Level (mm) | Float | 0–2000 mm |
| AI | Level_LimH | AI_CLT_LT_LIM_H | Level range high | Float | 2000 mm |
| AI | Level_LimL | AI_CLT_LT_LIM_L | Level range low | Float | 0 mm |
| **AO — Analog Outputs** | | | | | |
| AO | TempSP | AO_CLT_TEMP_SP | Temperature setpoint (°C) | Float | 0–15°C |
| AO | LS_Hi_SP | AI_CLT_LS_HI_SP | Setpoint LS_HI activation (%) | Float | 0–100% |
| AO | LS_Lo_SP | AI_CLT_LS_LO_SP | Setpoint LS_LO activation (%) | Float | 0–100% |

#### UDT_Boiler
Steam boiler with pressure, temperature, flow, safety interlocks and fault severity.
Instance example: `IronForge/BreweryBH/Utilities/Steam/Boiler-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | Running | DI_BOILER_RUN | Boiler running feedback | Boolean | 0/1 |
| DI | Fault | DI_BOILER_FAULT | Boiler fault severity | Int | 0–3 ★ |
| DI | HiPressure | DI_STEAM_HI_PRESS | High pressure safety switch | Boolean | 0/1 |
| **DO — Digital Outputs** | | | | | |
| DO | Start | DO_BOILER_START | Start command | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | Pressure | AI_STEAM_PT | Steam pressure (bar) | Float | 0–10 bar |
| AI | Temp | AI_STEAM_TT | Steam temperature (°C) | Float | 0–180°C |
| AI | Flow | AI_STEAM_FLOW | Steam flow (kg/h) | Float | 0–500 kg/h |
| AI | Press_LimH | AI_STEAM_PT_LIM_H | Pressure range high | Float | 10 bar |
| **AO — Analog Outputs** | | | | | |
| AO | PressureSP | AO_STEAM_PRESS_SP | Pressure setpoint (bar) | Float | 0–10 bar |
| **String — Fault Reason** | | | | | |
| STR | FaultReason | DI_BOILER_FAULT_REASON | Fault description text | String | Text |

#### UDT_Chiller
Glycol chiller with supply/return temps, flow, setpoint, fault severity and reason strings.
Instance example: `IronForge/BreweryBH/Utilities/Glycol/Chiller-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | Running | DI_CHILLER_RUN | Chiller running | Boolean | 0/1 |
| DI | Fault | DI_CHILLER_FAULT | Chiller fault severity | Int | 0–3 ★ |
| DI | PumpRunning | DI_GLYCOL_PUMP_RUN | Glycol pump running | Boolean | 0/1 |
| DI | PumpFault | DI_GLYCOL_PUMP_FLT | Glycol pump fault severity | Int | 0–3 ★ |
| **DO — Digital Outputs** | | | | | |
| DO | Start | DO_CHILLER_START | Start chiller | Boolean | 0/1 |
| DO | PumpStart | DO_GLYCOL_PUMP_RUN | Start glycol pump | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | TempSupply | AI_GLYCOL_TT_SUP | Glycol supply temp (°C) | Float | -10–10°C |
| AI | TempReturn | AI_GLYCOL_TT_RET | Glycol return temp (°C) | Float | -5–15°C |
| AI | Flow | AI_GLYCOL_FLOW | Glycol flow (L/h) | Float | 0–1000 L/h |
| AI | PowerKW | AI_ELEC_KW_CHILLER | Electrical power (kW) | Float | 0–100 kW |
| **AO — Analog Outputs** | | | | | |
| AO | TempSP | AO_GLYCOL_TEMP_SP | Supply temp setpoint (°C) | Float | -10–0°C |
| **String — Fault Reason** | | | | | |
| STR | FaultReason | DI_CHILLER_FAULT_REASON | Chiller fault description | String | Text |
| STR | PumpFaultRsn | DI_GLYCOL_PUMP_FLT_REASON | Glycol pump fault description | String | Text |

#### UDT_ROSystem
Reverse osmosis water treatment unit.
Instance example: `IronForge/BreweryBH/Utilities/RO/RO-System/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | Running | DI_RO_RUN | RO system running | Boolean | 0/1 |
| DI | Fault | DI_RO_FAULT | RO system fault | Boolean | 0/1 |
| **DO — Digital Outputs** | | | | | |
| DO | Start | DO_RO_START | Start RO system | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | TDS | AI_WATER_TDS | Total dissolved solids (ppm) | Float | 0–500 ppm |
| AI | pH | AI_WATER_PH | Water pH | Float | 5–9 pH |
| AI | FlowIn | AI_WATER_FLOW_IN | Inlet water flow (L/h) | Float | 0–2000 L/h |

---

### A300 — Brewhouse

#### UDT_MashTun
Mash tun with temperature, level, pH, rake, transfer pump, fault severity and switch setpoints.
Instance example: `IronForge/BreweryBH/Brewhouse/BH-L1/MT-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | LS_Hi | DI_MT{N}_LS_HI | High level switch | Boolean | 0/1 |
| DI | LS_Lo | DI_MT{N}_LS_LO | Low level switch | Boolean | 0/1 |
| DI | RakeRunning | DI_MT{N}_RAKE_RUN | Rake running feedback | Boolean | 0/1 |
| DI | RakeFault | DI_MT{N}_RAKE_FLT | Rake fault severity | Int | 0–3 ★ |
| DI | PumpRunning | DI_PMP_MT{N}_RUN | Transfer pump running | Boolean | 0/1 |
| DI | PumpFault | DI_PMP_MT{N}_FLT | Transfer pump fault severity | Int | 0–3 ★ |
| **DO — Digital Outputs** | | | | | |
| DO | RakeStart | DO_MT{N}_RAKE_RUN | Start rake | Boolean | 0/1 |
| DO | HeatEnable | DO_MT{N}_HEAT_EN | Enable heating | Boolean | 0/1 |
| DO | PumpStart | DO_MT{N}_PUMP_RUN | Start transfer pump | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | Temp | AI_MT{N}_TT | Temperature (°C) | Float | 0–100°C |
| AI | Level | AI_MT{N}_LT | Level (mm) | Float | 0–2200 mm |
| AI | Level_LimH | AI_MT{N}_LT_LIM_H | Level range high | Float | 2200 mm |
| AI | Level_LimL | AI_MT{N}_LT_LIM_L | Level range low | Float | 0 mm |
| AI | pH | AI_MT{N}_PH | Mash pH | Float | 4–8 pH |
| **AO — Analog Outputs** | | | | | |
| AO | TempSP | AO_MT{N}_HEAT_SP | Temperature setpoint (°C) | Float | 0–100°C |
| AO | LS_Hi_SP | AI_MT{N}_LS_HI_SP | Setpoint LS_HI activation (%) | Float | 0–100% |
| AO | LS_Lo_SP | AI_MT{N}_LS_LO_SP | Setpoint LS_LO activation (%) | Float | 0–100% |
| **String — Fault Reason** | | | | | |
| STR | RakeFaultRsn | DI_MT{N}_RAKE_FLT_REASON | Rake fault description | String | Text |
| STR | PmpFaultRsn | DI_PMP_MT{N}_FLT_REASON | Pump fault description | String | Text |

#### UDT_LauterTun
Lauter tun with rake (VFD), level, turbidity, wort brix, flow, fault severity and switch setpoints.
Instance example: `IronForge/BreweryBH/Brewhouse/BH-L1/LT-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | LS_Hi | DI_LT{N}_LS_HI | High level switch | Boolean | 0/1 |
| DI | LS_Lo | DI_LT{N}_LS_LO | Low level switch | Boolean | 0/1 |
| DI | RakeRunning | DI_LT{N}_RAKE_RUN | Rake running feedback | Boolean | 0/1 |
| DI | RakeFault | DI_LT{N}_RAKE_FLT | Rake fault severity | Int | 0–3 ★ |
| **DO — Digital Outputs** | | | | | |
| DO | RakeStart | DO_LT{N}_RAKE_RUN | Start rake | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | Temp | AI_LT{N}_TT | Temperature (°C) | Float | 0–100°C |
| AI | Level | AI_LT{N}_LT | Level (mm) | Float | 0–1800 mm |
| AI | Level_LimH | AI_LT{N}_LT_LIM_H | Level range high | Float | 1800 mm |
| AI | Level_LimL | AI_LT{N}_LT_LIM_L | Level range low | Float | 0 mm |
| AI | Turbidity | AI_LT{N}_TURB | Wort turbidity (NTU) | Float | 0–1000 NTU |
| AI | WortFlow | AI_LT{N}_FLOW | Wort flow to kettle (L/h) | Float | 0–1000 L/h |
| AI | WortBrix ★ | AI_WORT{N}_BRIX | Wort density inline (°P) | Float | 0–30 °P |
| **AO — Analog Outputs** | | | | | |
| AO | RakeSpeedSP | AO_LT{N}_RAKE_SPD | Rake speed setpoint (VFD %) | Float | 0–100% |
| AO | LS_Hi_SP | AI_LT{N}_LS_HI_SP | Setpoint LS_HI activation (%) | Float | 0–100% |
| AO | LS_Lo_SP | AI_LT{N}_LS_LO_SP | Setpoint LS_LO activation (%) | Float | 0–100% |
| **String — Fault Reason** | | | | | |
| STR | RakeFaultRsn | DI_LT{N}_RAKE_FLT_REASON | Rake fault description | String | Text |

#### UDT_Kettle
Brew kettle with steam heating, level, temperature, power tracking, and switch setpoints.
Instance example: `IronForge/BreweryBH/Brewhouse/BH-L1/KT-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | LS_Hi | DI_KT{N}_LS_HI | High level switch | Boolean | 0/1 |
| DI | LS_Lo | DI_KT{N}_LS_LO | Low level switch | Boolean | 0/1 |
| **DO — Digital Outputs** | | | | | |
| DO | HeatEnable | DO_KT{N}_HEAT_EN | Enable steam heating | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | Temp | AI_KT{N}_TT | Temperature (°C) | Float | 0–120°C |
| AI | Level | AI_KT{N}_LT | Level (mm) | Float | 0–2400 mm |
| AI | Level_LimH | AI_KT{N}_LT_LIM_H | Level range high | Float | 2400 mm |
| AI | Level_LimL | AI_KT{N}_LT_LIM_L | Level range low | Float | 0 mm |
| AI | SteamFlow | AI_KT{N}_STEAM_FLOW | Steam consumed (kg/h) | Float | 0–300 kg/h |
| AI | PowerKW ★ | AI_ELEC_KW_BH{N} | Brewhouse electrical consumption | Float | 0–100 kW |
| **AO — Analog Outputs** | | | | | |
| AO | HeatSP | AO_KT{N}_HEAT_SP | Heating power setpoint (%) | Float | 0–100% |
| AO | LS_Hi_SP | AI_KT{N}_LS_HI_SP | Setpoint LS_HI activation (%) | Float | 0–100% |
| AO | LS_Lo_SP | AI_KT{N}_LS_LO_SP | Setpoint LS_LO activation (%) | Float | 0–100% |

#### UDT_Whirlpool
Whirlpool vessel for trub separation with pump, level, turbidity, fault severity and switch setpoints.
Instance example: `IronForge/BreweryBH/Brewhouse/BH-L1/WP-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | LS_Hi | DI_WP{N}_LS_HI | High level switch | Boolean | 0/1 |
| DI | LS_Lo | DI_WP{N}_LS_LO | Low level switch | Boolean | 0/1 |
| DI | PumpRunning | DI_PMP_WP{N}_RUN | Pump running feedback | Boolean | 0/1 |
| DI | PumpFault | DI_PMP_WP{N}_FLT | Pump fault severity | Int | 0–3 ★ |
| **DO — Digital Outputs** | | | | | |
| DO | PumpStart | DO_WP{N}_PUMP_RUN | Start pump | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | Temp | AI_WP{N}_TT | Temperature (°C) | Float | 0–100°C |
| AI | Level | AI_WP{N}_LT | Level (mm) | Float | 0–1200 mm |
| AI | Level_LimH | AI_WP{N}_LT_LIM_H | Level range high | Float | 1200 mm |
| AI | Turbidity | AI_WP{N}_TURB | Post-whirlpool turbidity (NTU) | Float | 0–500 NTU |
| **AO — Analog Outputs** | | | | | |
| AO | LS_Hi_SP | AI_WP{N}_LS_HI_SP | Setpoint LS_HI activation (%) | Float | 0–100% |
| AO | LS_Lo_SP | AI_WP{N}_LS_LO_SP | Setpoint LS_LO activation (%) | Float | 0–100% |
| **String — Fault Reason** | | | | | |
| STR | PmpFaultRsn | DI_PMP_WP{N}_FLT_REASON | Pump fault description | String | Text |

---

### A400 — Cooling & Aeration

#### UDT_HeatExchanger
Plate heat exchanger for wort cooling with inlet/outlet temps, flow, O2 injection, fault severity and reason.
Instance example: `IronForge/BreweryBH/Cooling-Aeration/HX-L1/HX-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | PumpRunning | DI_HX{N}_PMP_RUN | Wort pump running | Boolean | 0/1 |
| DI | PumpFault | DI_HX{N}_PMP_FLT | Wort pump fault severity | Int | 0–3 ★ |
| **DO — Digital Outputs** | | | | | |
| DO | WortPump | DO_HX{N}_PMP_WORT | Start wort pump | Boolean | 0/1 |
| DO | WaterPump | DO_HX{N}_PMP_WATER | Start cooling water pump | Boolean | 0/1 |
| DO | O2Valve | DO_O2_VALVE_L{N} | Open O2 aeration valve | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | TempIn | AI_HX{N}_TT_IN | Wort inlet temp (°C) | Float | 60–100°C |
| AI | TempOut | AI_HX{N}_TT_OUT | Wort outlet temp (°C) | Float | 5–30°C |
| AI | WortFlow | AI_HX{N}_FLOW_WORT | Wort flow (L/h) | Float | 0–1000 L/h |
| AI | O2_ppm | AI_HX{N}_O2_PPM | Dissolved O2 post-aeration (ppm) | Float | 0–20 ppm |
| **AO — Analog Outputs** | | | | | |
| AO | WaterFlowSP | AO_HX{N}_WATER_FLOW | Cooling water valve SP (%) | Float | 0–100% |
| AO | O2FlowSP | AO_O2_FLOW_L{N} | O2 flow setpoint (L/h) | Float | 0–100 L/h |
| **String — Fault Reason** | | | | | |
| STR | PmpFaultRsn | DI_HX{N}_PMP_FLT_REASON | Pump fault description | String | Text |

---

### A500 — Fermentation

#### UDT_FermentationVessel
Cylindroconical FV with full quality suite, glycol control, PRV alarm, fault severity, configurable switch setpoints and reason strings.
Instance example: `IronForge/BreweryBH/Fermentation/FV-BLOCK/FV-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | LS_Hi | DI_FV{N}_LS_HI | High level switch | Boolean | 0/1 |
| DI | LS_Lo | DI_FV{N}_LS_LO | Low level switch | Boolean | 0/1 |
| DI | PRV_Open | DI_FV{N}_PRV | PRV open alarm severity | Int | 0–3 ★ |
| DI | GlycolOpen | DI_FV{N}_GLY_RUN | Glycol valve open feedback | Boolean | 0/1 |
| **DO — Digital Outputs** | | | | | |
| DO | GlycolEn | DO_FV{N}_GLY_EN | Enable glycol cooling | Boolean | 0/1 |
| DO | CO2Vent | DO_FV{N}_CO2_VENT | Open CO2 vent valve | Boolean | 0/1 |
| DO | Spunding | DO_FV{N}_SPUND | Open spunding valve | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | Temp | AI_FV{N}_TT | Beer temperature (°C) | Float | -5–30°C |
| AI | Pressure | AI_FV{N}_PT | Vessel pressure (bar) | Float | 0–3 bar |
| AI | pH | AI_FV{N}_PH | Beer pH | Float | 3–7 pH |
| AI | Brix | AI_FV{N}_BRIX | Density inline (°Plato) | Float | 0–30°P |
| AI | CO2_ppm | AI_FV{N}_CO2_PPM | Dissolved CO2 (g/L) | Float | 0–8 g/L |
| AI | Level | AI_FV{N}_LT | Level (mm) | Float | 0–4500 mm |
| AI | Level_LimH | AI_FV{N}_LT_LIM_H | Level range high | Float | 4500 mm |
| AI | Level_LimL | AI_FV{N}_LT_LIM_L | Level range low | Float | 0 mm |
| **AO — Analog Outputs** | | | | | |
| AO | TempSP | AO_FV{N}_TEMP_SP | Temperature setpoint (°C) | Float | -5–30°C |
| AO | PressureSP | AO_FV{N}_PRESS_SP | Spunding pressure SP (bar) | Float | 0–2 bar |
| AO | LS_Hi_SP | AI_FV{N}_LS_HI_SP | Setpoint LS_HI activation (%) | Float | 0–100% |
| AO | LS_Lo_SP | AI_FV{N}_LS_LO_SP | Setpoint LS_LO activation (%) | Float | 0–100% |
| **String — Fault Reason** | | | | | |
| STR | PRV_Reason | DI_FV{N}_PRV_REASON | PRV alarm description | String | Text |
| STR | FaultReason | DI_FV{N}_FAULT_REASON | General fault description | String | Text |

#### UDT_YeastBrink
Yeast propagation/storage vessel with temperature and level.
Instance example: `IronForge/BreweryBH/Fermentation/YEAST/Brink-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | LevelSwitch | DI_YB{N}_LS | Level switch | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | Temp | AI_YB{N}_TT | Temperature (°C) | Float | 0–20°C |

#### UDT_CO2Recovery
CO2 recovery system — capture from FVs, compression and storage.
Instance example: `IronForge/BreweryBH/Fermentation/CO2-REC/CO2-Tank/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AI — Analog Inputs** | | | | | |
| AI | TankPressure | AI_CO2_TANK_PRESS | CO2 tank pressure (bar) | Float | 0–20 bar |
| AI | TankWeight | AI_CO2_TANK_WT | CO2 tank weight (kg) | Float | 0–5000 kg |
| AI | RecoveryFlow | AI_CO2_FLOW_FV | CO2 recovery flow (kg/h) | Float | 0–50 kg/h |

---

### A600 — Maturation

#### UDT_BBT
Bright Beer Tank — full quality suite with configurable switch setpoints and beer loss tracking.
Instance example: `IronForge/BreweryBH/Maturation/BBT/BBT-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | LS_Hi | DI_BBT{N}_LS_HI | High level switch | Boolean | 0/1 |
| DI | LS_Lo | DI_BBT{N}_LS_LO | Low level switch | Boolean | 0/1 |
| **DO — Digital Outputs** | | | | | |
| DO | GlycolEn | DO_BBT{N}_GLY_EN | Enable glycol cooling | Boolean | 0/1 |
| DO | CO2Carb | DO_BBT{N}_CO2_CARB | Open CO2 carbonation valve | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | Temp | AI_BBT{N}_TT | Temperature (°C) | Float | 0–20°C |
| AI | Pressure | AI_BBT{N}_PT | Pressure (bar) | Float | 0–4 bar |
| AI | Level | AI_BBT{N}_LT | Level (mm) | Float | 0–3200 mm |
| AI | Level_LimH | AI_BBT{N}_LT_LIM_H | Level range high | Float | 3200 mm |
| AI | Level_LimL | AI_BBT{N}_LT_LIM_L | Level range low | Float | 0 mm |
| AI | CO2_gL | AI_BBT{N}_CO2 | Dissolved CO2 (g/L) | Float | 0–8 g/L |
| AI | O2_ppb | AI_BBT{N}_O2 | Total packaged O2 (ppb) | Float | 0–500 ppb |
| AI | Turbidity | AI_BBT{N}_TURB | Turbidity (EBC) | Float | 0–100 EBC |
| AI | pH | AI_BBT{N}_PH | Beer pH | Float | 3–7 pH |
| AI | BeerLoss ★ | AI_BEER_LOSS_FV_BBT | Losses FV→BBT (L) | Float | 0–200 L |
| **AO — Analog Outputs** | | | | | |
| AO | TempSP | AO_BBT{N}_TEMP_SP | Temperature setpoint (°C) | Float | 0–10°C |
| AO | CO2_SP | AO_BBT{N}_CO2_SP | Carbonation pressure SP (bar) | Float | 0–3 bar |
| AO | LS_Hi_SP | AI_BBT{N}_LS_HI_SP | Setpoint LS_HI activation (%) | Float | 0–100% |
| AO | LS_Lo_SP | AI_BBT{N}_LS_LO_SP | Setpoint LS_LO activation (%) | Float | 0–100% |
| **String — Fault Reason** | | | | | |
| STR | FaultReason | DI_BBT{N}_FAULT_REASON | BBT fault description | String | Text |

#### UDT_Centrifuge
Centrifuge for beer clarification with fault severity.
Instance example: `IronForge/BreweryBH/Maturation/FILTER/Centrifuge-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | Running | DI_CENT_RUN | Running feedback | Boolean | 0/1 |
| DI | Fault | DI_CENT_FAULT | Fault severity | Int | 0–3 ★ |
| **DO — Digital Outputs** | | | | | |
| DO | Start | DO_CENT_START | Start command | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | TurbOut | AI_CENT_TURB_OUT | Outlet turbidity (NTU) | Float | 0–200 NTU |
| AI | Flow | AI_CENT_FLOW | Flow rate (L/h) | Float | 0–2000 L/h |
| **String — Fault Reason** | | | | | |
| STR | FaultReason | DI_CENT_FAULT_REASON | Fault description | String | Text |

#### UDT_CartridgeFilter
Cartridge filter with differential pressure, flow and fault severity.
Instance example: `IronForge/BreweryBH/Maturation/FILTER/CartridgeFilter-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | PumpRunning | DI_FILT_PMP_RUN | Filter pump running | Boolean | 0/1 |
| DI | PumpFault | DI_FILT_PMP_FLT | Filter pump fault severity | Int | 0–3 ★ |
| **DO — Digital Outputs** | | | | | |
| DO | PumpStart | DO_FILT_PMP_RUN | Start filter pump | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | DeltaP | AI_FILT_DP | Differential pressure (bar) | Float | 0–5 bar |
| AI | Flow | AI_FILT_FLOW | Flow rate (L/h) | Float | 0–1000 L/h |
| **String — Fault Reason** | | | | | |
| STR | PmpFaultRsn | DI_FILT_PMP_FLT_REASON | Pump fault description | String | Text |

---

### A700 — Packaging

#### UDT_KegLine
Kegging line with counter, fill pressure, temperature, power, losses, fault severity and reason string.
Instance example: `IronForge/BreweryBH/Packaging/KEG/KegFiller-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | Running | DI_KEG_LINE_RUN | Line running | Boolean | 0/1 |
| DI | Fault | DI_KEG_LINE_FLT | Line fault severity | Int | 0–3 ★ |
| DI | KegPresent | DI_KEG_SENSOR | Keg positioned sensor | Boolean | 0/1 |
| DI | KegFull | DI_KEG_FULL | Keg full (pressure sensor) | Boolean | 0/1 |
| **DO — Digital Outputs** | | | | | |
| DO | Start | DO_KEG_LINE_START | Start line | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | KegCount | AI_KEG_COUNT | Kegs filled (pulse counter) | Float | kegs/h |
| AI | FillPressure | AI_KEG_FILL_PRESS | Fill pressure (bar) | Float | 0–5 bar |
| AI | FillTemp | AI_KEG_FILL_TEMP | Fill temperature (°C) | Float | 0–15°C |
| AI | BeerLoss ★ | AI_PACK_BEER_LOSS | Beer losses in packaging (L/h) | Float | 0–50 L/h |
| AI | PowerKW ★ | AI_ELEC_KW_PACK | Packaging electrical consumption | Float | 0–50 kW |
| **String — Fault Reason** | | | | | |
| STR | FaultReason | DI_KEG_LINE_FLT_REASON | Fault description | String | Text |

#### UDT_CanLine
Canning line with counter, inline DO, fill volume quality monitoring, fault severity and reason.
Instance example: `IronForge/BreweryBH/Packaging/CAN/CanFiller-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | Running | DI_CAN_LINE_RUN | Line running | Boolean | 0/1 |
| DI | Fault | DI_CAN_LINE_FLT | Line fault severity | Int | 0–3 ★ |
| DI | CanSensor | DI_CAN_SENSOR | Can passing sensor | Boolean | 0/1 |
| **DO — Digital Outputs** | | | | | |
| DO | Start | DO_CAN_LINE_START | Start line | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | CanCount | AI_CAN_COUNT | Cans filled (pulse counter) | Float | cans/h |
| AI | DO_ppb | AI_CAN_DO_PPB | Dissolved O2 inline (ppb) | Float | 0–200 ppb |
| AI | FillVolume | AI_CAN_FILL_VOL | Volume per can (mL) | Float | 330–500 mL |
| **String — Fault Reason** | | | | | |
| STR | FaultReason | DI_CAN_LINE_FLT_REASON | Fault description | String | Text |

#### UDT_Labeler
Labeling machine with run feedback, start command, fault severity and reason.
Instance example: `IronForge/BreweryBH/Packaging/LABELER/Labeler-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | Running | DI_LABEL_RUN | Labeler running feedback | Boolean | 0/1 |
| DI | Fault ★ | DI_LABEL_FLT | Labeler fault severity | Int | 0–3 ★ |
| **DO — Digital Outputs** | | | | | |
| DO | Start | DO_LABEL_START | Start labeler | Boolean | 0/1 |
| **String — Fault Reason ★ NEW** | | | | | |
| STR | FaultReason ★| DI_LABEL_FLT_REASON | Labeler fault description | String | Text |

---

### A800 — CIP

#### UDT_CIPStation
CIP station with caustic, acid and rinse tanks, full quality monitoring, power, fault severity and reason.
Instance example: `IronForge/BreweryBH/CIP/CIP-STN/CIPPump/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DI — Digital Inputs** | | | | | |
| DI | PumpRunning | DI_CIP_PMP_RUN | CIP pump running | Boolean | 0/1 |
| DI | PumpFault | DI_CIP_PMP_FLT | CIP pump fault severity | Int | 0–3 ★ |
| DI | CausticLevel | DI_CIP_CAUST_LS | Caustic tank level switch | Boolean | 0/1 |
| DI | AcidLevel | DI_CIP_ACID_LS | Acid tank level switch | Boolean | 0/1 |
| DI | RinseLevel | DI_CIP_RINSE_LS | Rinse tank level switch | Boolean | 0/1 |
| **DO — Digital Outputs** | | | | | |
| DO | HeatEnable ★ | DO_CIP_HEAT_EN | Enable CIP caustic heating | Boolean | 0/1 |
| **AI — Analog Inputs** | | | | | |
| AI | CausticTemp | AI_CIP_TT_CAUST | Caustic solution temp (°C) | Float | 0–90°C |
| AI | Conductivity | AI_CIP_COND_RET | Return conductivity (mS/cm) | Float | 0–100 mS/cm |
| AI | ReturnPH | AI_CIP_PH_RET | Return pH | Float | 0–14 pH |
| AI | Flow | AI_CIP_FLOW | CIP flow (L/h) | Float | 0–500 L/h |
| AI | CausticLevel_pct | AI_CIP_CAUST_LT | Caustic tank level (%) | Float | 0–100% |
| AI | WaterTotal ★ | AI_CIP_WATER_TOT | CIP water volume totalizer (L) | Float | 0–5000 L |
| AI | PowerKW ★ | AI_ELEC_KW_CIP | CIP electrical consumption (kW) | Float | 0–30 kW |
| **AO — Analog Outputs** | | | | | |
| AO | TempSP | AO_CIP_TEMP_SP | Caustic temp setpoint (°C) | Float | 0–80°C |
| AO | FlowSP | AO_CIP_FLOW_SP | CIP flow setpoint (L/h) | Float | 0–500 L/h |
| **String — Fault Reason** | | | | | |
| STR | PmpFaultRsn | DI_CIP_PMP_FLT_REASON | Pump fault description | String | Text |

---

### A900 — Utilities & Meters

#### UDT_PlantMeters
Global plant totalizers for water, steam, CO2, and electrical consumption.
Instance example: `IronForge/BreweryBH/Utilities/METERS/PlantMeters/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AI — Analog Inputs** | | | | | |
| AI | PowerKW | AI_ELEC_KW_TOTAL | Total plant electrical consumption | Float | 0–500 kW |
| AI | EnergyKWh | AI_ELEC_KWH_TOT | Accumulated total energy | Float | 0–999999 kWh |
| AI | WaterTotal | AI_WATER_TOTAL | Total water consumed | Float | 0–9999 m³ |
| AI | SteamTotal | AI_STEAM_TOTAL | Total steam consumed | Float | 0–99999 kg |
| AI | CO2Consumed | AI_CO2_CONSUMED | Total CO2 consumed | Float | 0–9999 kg |

#### UDT_EnvironmentSensor
Plant ambient temperature and humidity monitoring.
Instance example: `IronForge/BreweryBH/Utilities/ENV/EnvSensor-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AI — Analog Inputs** | | | | | |
| AI | AmbientTemp | AI_AMBIENT_TT | Ambient temperature | Float | 0–50 °C |
| AI | Humidity | AI_AMBIENT_RH | Relative humidity | Float | 0–100 % |

---

### A900 — MES Layer

#### UDT_MES_PlantOverview
Global plant production, OEE, targets, and alarm metrics.
Instance example: `IronForge/BreweryBH/MES/Plant/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AI — Analog Inputs** | | | | | |
| AI | HL_Shift | MES_PLANT_HL_SHIFT | HL produced current shift | Float | 0–500 hl |
| AI | HL_Daily | MES_PLANT_HL_DAILY | HL produced today | Float | 0–1500 hl |
| AI | ShiftNum | MES_PLANT_SHIFT_NUM | Current shift number (1/2/3) | Float | 1–3 |
| AI | DailyPct | MES_PLANT_DAILY_PCT | Pct daily production target | Float | 0–150 % |
| AI | BatchToday | MES_PLANT_BATCH_TODAY | Batches completed today | Float | 0–10 |
| AI | OEE | MES_PLANT_OEE | Global plant OEE | Float | 0–100 % |
| AI | AlarmsActive | MES_PLANT_ALARMS_ACTIVE | Active alarms count | Float | 0–100 |
| AI | BeerLossPct | MES_PLANT_BEER_LOSS_PCT | Total beer loss pct | Float | 0–20 % |
| **AO — Analog Outputs (Setpoints)** | | | | | |
| AO | Target_HL_Shift | MES_PLANT_TARGET_HL_SHIFT | Shift production target | Float | 0–500 hl |
| AO | OEE_Target | MES_PLANT_OEE_TARGET | Plant OEE target | Float | 0–100 % |

#### UDT_MES_Brewhouse
OEE, availability, and specific KPIs for Brewhouse lines.
Instance example: `IronForge/BreweryBH/MES/Brewhouse/Line-1/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AI — Analog Inputs** | | | | | |
| AI | OEE | MES_BH{N}_OEE | Brewhouse line OEE | Float | 0–100 % |
| AI | Availability | MES_BH{N}_AVAIL | Brewhouse availability | Float | 0–100 % |
| AI | MashTemp | MES_BH{N}_MT_TEMP | Mash Tun temperature | Float | 0–100 °C |
| AI | WortBrix | MES_BH{N}_WORT_BRIX | Wort brix line | Float | 0–30 °P |
| AI | PowerKW | MES_BH{N}_KW | Electrical consumption | Float | 0–150 kW |

#### UDT_MES_Fermentation
Aggregated metrics for the fermentation block.
Instance example: `IronForge/BreweryBH/MES/Fermentation/Block/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AI — Analog Inputs** | | | | | |
| AI | FvActive | MES_FERM_FV_ACTIVE | Active FVs count | Float | 0–6 |
| AI | FvIdle | MES_FERM_FV_IDLE | Idle FVs count | Float | 0–6 |
| AI | AvgTemp | MES_FERM_AVG_TEMP | Avg temp active FVs | Float | -5–30 °C |
| AI | AvgBrix | MES_FERM_AVG_BRIX | Avg brix active FVs | Float | 0–20 °P |
| AI | BBTsReady | MES_FERM_BBT_READY | BBTs ready for packaging | Float | 0–2 |

#### UDT_MES_Utilities
Aggregated consumption metrics for water, steam, and electricity relative to production.
Instance example: `IronForge/BreweryBH/MES/Utilities/`

| Type | UDT Member | Tag Suffix | Description | Data Type | Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AI — Analog Inputs** | | | | | |
| AI | WaterPerHL | MES_UTIL_WATER_HL | Water consumption hl/hl | Float | 0–10 hl/hl |
| AI | KwhPerHL | MES_UTIL_KWH_HL | Energy consumption kWh/hl | Float | 0–200 kWh/hl |
| AI | SteamPerHL | MES_UTIL_STEAM_HL | Steam consumption kg/hl | Float | 0–50 kg/hl |
| AI | TotalKW | MES_UTIL_KW_TOTAL | Total plant power | Float | 0–600 kW |
| **AO — Analog Outputs (Setpoints)** | | | | | |
| AO | TargetWater | MES_UTIL_TARGET_WATER | Target water hl/hl | Float | 0–10 hl/hl |
| AO | TargetKwh | MES_UTIL_TARGET_KWH | Target energy kWh/hl | Float | 0–200 kWh/hl |