"""
brewery_simulator/areas/all_areas.py

All area simulators. Each uses a lightweight state machine:
  - States are tracked with instance variables (elapsed time, phase index, etc.)
  - Every tick advances analog values using physics helpers
  - Faults cascade: if upstream equipment is faulted, dependents stop

Design philosophy:
  - Plausible rhythm, not perfect accuracy
  - Fast-forward friendly (dt_sim scales with speed multiplier)
  - Self-healing faults after random recovery time
"""
from __future__ import annotations

import enum
import math
import random
from typing import TYPE_CHECKING

from brewery_simulator.areas.base import AreaSimulator
from brewery_simulator import physics as phys

if TYPE_CHECKING:
    from brewery_simulator.tag_store import TagStore


# ─────────────────────────────────────────────────────────────────────────────
# AREA 100 — MILLING
# ─────────────────────────────────────────────────────────────────────────────

class MillState(enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    FAULT = "fault"
    COOLDOWN = "cooldown"


class MillLine(AreaSimulator):
    """Simulates one Mill line (Mill + Auger + Silo + Grist Case)."""

    def __init__(self, store: "TagStore", cfg: dict, rng: random.Random,
                 mill_run: str, mill_fault: str, aug_run: str, aug_fault: str,
                 do_mill: str, do_aug: str,
                 silo_wt: str, grc_wt: str, mill_curr: str,
                 silo_ls_hi: str, silo_ls_lo: str, grc_ls_hi: str) -> None:
        super().__init__(store, cfg, rng)
        self.tags = dict(
            mill_run=mill_run, mill_fault=mill_fault,
            aug_run=aug_run, aug_fault=aug_fault,
            do_mill=do_mill, do_aug=do_aug,
            silo_wt=silo_wt, grc_wt=grc_wt, mill_curr=mill_curr,
            silo_ls_hi=silo_ls_hi, silo_ls_lo=silo_ls_lo, grc_ls_hi=grc_ls_hi,
        )
        self.state = MillState.IDLE
        self.elapsed = 0.0
        self.run_target = 0.0
        self.cooldown_target = 0.0
        self.fault_recovery_target = 0.0
        mc = cfg.get("milling", {})
        self.run_min = mc.get("run_duration_min", 1800)
        self.run_max = mc.get("run_duration_max", 2700)
        self.cool_min = mc.get("cooldown_min", 300)
        self.cool_max = mc.get("cooldown_max", 600)
        self.fault_prob = mc.get("fault_probability", 0.005)
        # Setpoints dos switches via TOML
        self.silo_ls_hi_sp = mc.get("silo_ls_hi_sp", 4500.0)
        self.silo_ls_lo_sp = mc.get("silo_ls_lo_sp", 200.0)
        self.grc_ls_hi_sp  = mc.get("grc_ls_hi_sp", 400.0)
        # Silo: controle de direção (filling/draining)
        self.silo_filling = False   # False = drenando, True = enchendo
        self.silo_fill_target = mc.get("silo_fill_target", 4800.0)
        self.silo_drain_target = mc.get("silo_drain_target", 300.0)
        # stagger start between lines
        self.elapsed = rng.uniform(0, self.run_max)

    def tick(self, dt_sim: float) -> None:
        self.elapsed += dt_sim
        t = self.tags
        noise = phys.add_noise

        if self.state == MillState.IDLE:
            self._set(t["mill_run"], False); self._set(t["aug_run"], False)
            self._set(t["do_mill"], False); self._set(t["do_aug"], False)
            self._set(t["mill_curr"], noise(0.0, 0.3, self.rng))
            self._set(t["grc_ls_hi"], False)
            # transition
            if self.elapsed >= self.cooldown_target:
                self.state = MillState.RUNNING
                self.run_target = self.elapsed + self.rng.uniform(self.run_min, self.run_max)
                self._set(t["do_mill"], True); self._set(t["do_aug"], True)

        elif self.state == MillState.RUNNING:
            self._set(t["mill_run"], True); self._set(t["aug_run"], True)
            self._set(t["do_mill"], True); self._set(t["do_aug"], True)
            curr = noise(32.0, 1.5, self.rng)
            self._set(t["mill_curr"], curr)

            # ── Silo: lógica crescente/decrescente com ruído ──
            silo = self._get(t["silo_wt"])

            # Decide direção: enche até silo_fill_target, drena até silo_drain_target
            if self.silo_filling:
                rate = self.rng.uniform(1.5, 3.0)   # taxa de enchimento kg/s
                silo = silo + dt_sim * rate + self.rng.uniform(-0.2, 0.2)
                if silo >= self.silo_fill_target:
                    silo = self.silo_fill_target
                    self.silo_filling = False         # chegou ao topo → começa a drenar
            else:
                rate = self.rng.uniform(0.8, 1.2)   # taxa de drenagem kg/s
                silo = silo - dt_sim * rate + self.rng.uniform(-0.2, 0.2)
                if silo <= self.silo_drain_target:
                    silo = self.silo_drain_target
                    self.silo_filling = True          # chegou ao fundo → começa a encher

            silo = max(0.0, min(5000.0, silo))
            self._set(t["silo_wt"], silo)

            # ── Switches com histerese baseados nos setpoints do TOML ──
            # LS_HI: ativa quando silo >= sp_hi, desativa quando silo < sp_hi
            # LS_LO: ativa quando silo <= sp_lo, desativa quando silo > sp_lo
            prev_ls_hi = self._get(t["silo_ls_hi"])
            prev_ls_lo = self._get(t["silo_ls_lo"])

            if prev_ls_hi:
                # Já estava ativo — só desativa se cair ABAIXO do setpoint
                self._set(t["silo_ls_hi"], silo >= self.silo_ls_hi_sp)
            else:
                # Estava inativo — ativa se ATINGIR ou superar o setpoint
                self._set(t["silo_ls_hi"], silo >= self.silo_ls_hi_sp)

            if prev_ls_lo:
                self._set(t["silo_ls_lo"], silo <= self.silo_ls_lo_sp)
            else:
                self._set(t["silo_ls_lo"], silo <= self.silo_ls_lo_sp)

            # ── Grist Case ──
            grc = self._get(t["grc_wt"])
            grc = min(450.0, grc + dt_sim * self.rng.uniform(0.4, 0.7))
            self._set(t["grc_wt"], grc)
            self._set(t["grc_ls_hi"], grc >= self.grc_ls_hi_sp)

            # fault?
            if self._random_fault(self.fault_prob, dt_sim):
                self.state = MillState.FAULT
                self._set(t["mill_fault"], True)
                self.fault_recovery_target = self.elapsed + self.rng.uniform(60, 300)
            # done?
            elif self.elapsed >= self.run_target:
                self.state = MillState.COOLDOWN
                self.cooldown_target = self.elapsed + self.rng.uniform(self.cool_min, self.cool_max)

        elif self.state == MillState.FAULT:
            self._set(t["mill_run"], False); self._set(t["aug_run"], False)
            self._set(t["mill_curr"], 0.0)
            if self.elapsed >= self.fault_recovery_target:
                self._set(t["mill_fault"], False)
                self._set(t["aug_fault"], False)
                self.state = MillState.COOLDOWN
                self.cooldown_target = self.elapsed + self.rng.uniform(30, 120)

        elif self.state == MillState.COOLDOWN:
            self._set(t["mill_run"], False); self._set(t["aug_run"], False)
            self._set(t["do_mill"], False); self._set(t["do_aug"], False)
            self._set(t["mill_curr"], noise(0.0, 0.1, self.rng))
            # drain grist case slowly
            grc = self._get(t["grc_wt"])
            grc = max(0.0, grc - dt_sim * 0.3)
            self._set(t["grc_wt"], grc)
            if self.elapsed >= self.cooldown_target:
                self.state = MillState.IDLE


class MillingArea(AreaSimulator):
    """Two parallel mill lines."""

    def __init__(self, store: "TagStore", cfg: dict, rng: random.Random) -> None:
        super().__init__(store, cfg, rng)
        self.line_a = MillLine(
            store, cfg, rng,
            "DI_MILL_A_RUN", "DI_MILL_A_FAULT", "DI_AUG_A_RUN", "DI_AUG_A_FAULT",
            "DO_MILL_A_RUN", "DO_AUG_A_RUN",
            "AI_SILO_A_WT", "AI_GRC_A_WT", "AI_MILL_A_CURR",
            "DI_SILO_A_LS_HI", "DI_SILO_A_LS_LO", "DI_GRC_A_LS_HI",
        )
        self.line_b = MillLine(
            store, cfg, rng,
            "DI_MILL_B_RUN", "DI_MILL_B_FAULT", "DI_AUG_B_RUN", "DI_AUG_B_FAULT",
            "DO_MILL_B_RUN", "DO_AUG_B_RUN",
            "AI_SILO_B_WT", "AI_GRC_B_WT", "AI_MILL_B_CURR",
            "DI_SILO_B_LS_HI", "DI_SILO_B_LS_LO", "DI_GRC_B_LS_HI",
        )

    def tick(self, dt_sim: float) -> None:
        self.line_a.tick(dt_sim)
        self.line_b.tick(dt_sim)


# ─────────────────────────────────────────────────────────────────────────────
# AREA 200 — UTILITIES (HLT, CLT, Steam, RO, Glycol, Chiller)
# ─────────────────────────────────────────────────────────────────────────────

class UtilitiesArea(AreaSimulator):

    def __init__(self, store: "TagStore", cfg: dict, rng: random.Random) -> None:
        super().__init__(store, cfg, rng)
        self.boiler_running = True
        self.boiler_fault_timer = 0.0
        self.chiller_fault_timer = 0.0
        self.total_water = 0.0
        self.total_steam = 0.0
        self.total_kwh = 0.0

    def tick(self, dt_sim: float) -> None:
        ph = self.cfg.get("physics", {})
        approach_rate = ph.get("temp_approach_rate", 0.002)
        noise_std = ph.get("analog_noise_std", 0.05)
        n = lambda v, s: phys.add_noise(v, s, self.rng)

        # ── Boiler ──
        boiler_fault = self._get("DI_BOILER_FAULT")
        if boiler_fault:
            self.boiler_fault_timer += dt_sim
            self._set("DI_BOILER_RUN", False)
            self._set("AI_STEAM_PT", n(0.0, 0.05))
            self._set("AI_STEAM_FLOW", 0.0)
            if self.boiler_fault_timer > self.rng.uniform(120, 600):
                self._set("DI_BOILER_FAULT", False)
                self.boiler_fault_timer = 0.0
        else:
            if self._random_fault(0.0003, dt_sim):
                self._set("DI_BOILER_FAULT", True)
                self._set("DI_STEAM_HI_PRESS", False)
            else:
                self._set("DI_BOILER_RUN", True)
                self._set("DO_BOILER_START", True)
                sp = 4.0
                pt = phys.approach(self._get("AI_STEAM_PT"), sp, approach_rate * 3, dt_sim)
                self._set("AI_STEAM_PT", n(pt, 0.05))
                tt = 100 + (pt / 4.0) * 51
                self._set("AI_STEAM_TT", n(tt, 0.5))
                flow = n(180.0, 10.0)
                self._set("AI_STEAM_FLOW", flow)
                self.total_steam += flow * dt_sim / 3600
                self._set("DI_STEAM_HI_PRESS", pt > 8.5)

        # ── HLT 1 ──
        hlt1_sp = self._get("AO_HLT1_HEAT_SP")
        hlt1_t = phys.approach(self._get("AI_HLT1_TT"), hlt1_sp, approach_rate, dt_sim)
        self._set("AI_HLT1_TT", n(hlt1_t, noise_std))
        heating1 = hlt1_t < hlt1_sp - 1
        self._set("DO_HLT1_HEAT_EN", heating1)
        kw1 = 25.0 if heating1 else 2.0
        self._set("AI_ELEC_KW_HLT", n(kw1, 0.5))
        # level oscillates 70-95%
        lvl1 = self.store.get_level_pct("AI_HLT1_LT")
        if lvl1 > 92:
            self.store.set_level_pct("AI_HLT1_LT", lvl1 - self.rng.uniform(0, 0.1) * dt_sim)
        elif lvl1 < 70:
            self.store.set_level_pct("AI_HLT1_LT", lvl1 + self.rng.uniform(0, 0.15) * dt_sim)
        else:
            self.store.set_level_pct("AI_HLT1_LT", n(lvl1, 0.02))
        self._set("DI_HLT1_LS_HI", self.store.get_level_pct("AI_HLT1_LT") > 90)
        self._set("DI_HLT1_LS_LO", self.store.get_level_pct("AI_HLT1_LT") < 10)

        # ── HLT 2 (mirror with slight offset) ──
        hlt2_sp = self._get("AO_HLT2_HEAT_SP")
        hlt2_t = phys.approach(self._get("AI_HLT2_TT"), hlt2_sp, approach_rate, dt_sim)
        self._set("AI_HLT2_TT", n(hlt2_t, noise_std))
        heating2 = hlt2_t < hlt2_sp - 1
        self._set("DO_HLT2_HEAT_EN", heating2)
        lvl2 = self.store.get_level_pct("AI_HLT2_LT")
        if lvl2 > 90:
            self.store.set_level_pct("AI_HLT2_LT", lvl2 - self.rng.uniform(0, 0.12) * dt_sim)
        elif lvl2 < 68:
            self.store.set_level_pct("AI_HLT2_LT", lvl2 + self.rng.uniform(0, 0.14) * dt_sim)
        else:
            self.store.set_level_pct("AI_HLT2_LT", n(lvl2, 0.02))
        self._set("DI_HLT2_LS_HI", self.store.get_level_pct("AI_HLT2_LT") > 90)
        self._set("DI_HLT2_LS_LO", self.store.get_level_pct("AI_HLT2_LT") < 10)

        # ── CLT ──
        clt_sp = self._get("AO_CLT_TEMP_SP")
        clt_t = phys.approach(self._get("AI_CLT_TT"), clt_sp, approach_rate * 2, dt_sim)
        self._set("AI_CLT_TT", n(clt_t, noise_std))
        self._set("DI_CLT_LS_HI", self.store.get_level_pct("AI_CLT_LT") > 88)
        self._set("DI_CLT_LS_LO", self.store.get_level_pct("AI_CLT_LT") < 15)

        # ── RO ──
        self._set("DI_RO_RUN", True)
        self._set("AI_WATER_TDS", n(42.0, 2.0))
        self._set("AI_WATER_PH", n(7.0, 0.05))
        water_flow = n(800.0, 20.0) if self._get("DI_BOILER_RUN") else 200.0
        self._set("AI_WATER_FLOW_IN", water_flow)
        self.total_water += water_flow * dt_sim / 3600 / 1000  # m3

        # ── Glycol / Chiller ──
        glycol_fault = self._get("DI_GLYCOL_PUMP_FLT")
        if glycol_fault:
            self.chiller_fault_timer += dt_sim
            if self.chiller_fault_timer > self.rng.uniform(60, 300):
                self._set("DI_GLYCOL_PUMP_FLT", False)
                self.chiller_fault_timer = 0.0
        else:
            if self._random_fault(0.0002, dt_sim):
                self._set("DI_GLYCOL_PUMP_FLT", True)
                self._set("DI_CHILLER_FAULT", True)
            else:
                self._set("DI_GLYCOL_PUMP_RUN", True)
                self._set("DI_CHILLER_RUN", True)
                gly_sp = self._get("AO_GLYCOL_TEMP_SP")
                gly_sup = phys.approach(self._get("AI_GLYCOL_TT_SUP"), gly_sp, approach_rate * 2, dt_sim)
                self._set("AI_GLYCOL_TT_SUP", n(gly_sup, 0.1))
                self._set("AI_GLYCOL_TT_RET", n(gly_sup + 5.0, 0.3))
                self._set("AI_GLYCOL_FLOW", n(420.0, 15.0))
                self._set("AI_ELEC_KW_CHILLER", n(38.0, 2.0))

        # ── Global meters ──
        total_kw = n(42.0, 2.0)
        self._set("AI_ELEC_KW_TOTAL", total_kw)
        self.total_kwh += total_kw * dt_sim / 3600
        self._set("AI_ELEC_KWH_TOT", self.total_kwh)
        self._set("AI_WATER_TOTAL", self.total_water)
        self._set("AI_STEAM_TOTAL", self.total_steam)
        self._set("AI_AMBIENT_TT", n(22.5, 0.2))
        self._set("AI_AMBIENT_RH", n(55.0, 1.0))


# ─────────────────────────────────────────────────────────────────────────────
# AREA 300 — BREWHOUSE (one line)
# ─────────────────────────────────────────────────────────────────────────────

class BrewhouseState(enum.Enum):
    IDLE = "idle"
    MASHING = "mashing"
    LAUTERING = "lautering"
    BOILING = "boiling"
    WHIRLPOOL = "whirlpool"
    TRANSFER = "transfer"   # cooling/transfer to FV


class BrewhouseLine(AreaSimulator):
    """One complete brewhouse line: MT → LT → KT → WP."""

    def __init__(self, store, cfg, rng, line: int, offset_s: float = 0) -> None:
        super().__init__(store, cfg, rng)
        L = str(line)
        self.tags = dict(
            # Mash
            mt_ls_hi=f"DI_MT{L}_LS_HI", mt_ls_lo=f"DI_MT{L}_LS_LO",
            mt_rake_run=f"DI_MT{L}_RAKE_RUN", mt_rake_flt=f"DI_MT{L}_RAKE_FLT",
            pmp_mt_run=f"DI_PMP_MT{L}_RUN", pmp_mt_flt=f"DI_PMP_MT{L}_FLT",
            do_mt_rake=f"DO_MT{L}_RAKE_RUN", do_mt_heat=f"DO_MT{L}_HEAT_EN",
            do_mt_pump=f"DO_MT{L}_PUMP_RUN",
            ai_mt_tt=f"AI_MT{L}_TT", ai_mt_lt=f"AI_MT{L}_LT", ai_mt_ph=f"AI_MT{L}_PH",
            ao_mt_sp=f"AO_MT{L}_HEAT_SP",
            # Lauter
            lt_ls_hi=f"DI_LT{L}_LS_HI", lt_ls_lo=f"DI_LT{L}_LS_LO",
            lt_rake_run=f"DI_LT{L}_RAKE_RUN", lt_rake_flt=f"DI_LT{L}_RAKE_FLT",
            do_lt_rake=f"DO_LT{L}_RAKE_RUN",
            ai_lt_tt=f"AI_LT{L}_TT", ai_lt_lt=f"AI_LT{L}_LT",
            ai_lt_turb=f"AI_LT{L}_TURB", ai_lt_flow=f"AI_LT{L}_FLOW",
            ai_wort_brix=f"AI_WORT{L}_BRIX", ao_lt_spd=f"AO_LT{L}_RAKE_SPD",
            # Kettle
            kt_ls_hi=f"DI_KT{L}_LS_HI", kt_ls_lo=f"DI_KT{L}_LS_LO",
            do_kt_heat=f"DO_KT{L}_HEAT_EN",
            ai_kt_tt=f"AI_KT{L}_TT", ai_kt_lt=f"AI_KT{L}_LT",
            ai_kt_steam=f"AI_KT{L}_STEAM_FLOW", ao_kt_sp=f"AO_KT{L}_HEAT_SP",
            ai_elec_bh=f"AI_ELEC_KW_BH{L}",
            # Whirlpool
            wp_ls_hi=f"DI_WP{L}_LS_HI", wp_ls_lo=f"DI_WP{L}_LS_LO",
            pmp_wp_run=f"DI_PMP_WP{L}_RUN", pmp_wp_flt=f"DI_PMP_WP{L}_FLT",
            do_wp_pump=f"DO_WP{L}_PUMP_RUN",
            ai_wp_tt=f"AI_WP{L}_TT", ai_wp_lt=f"AI_WP{L}_LT", ai_wp_turb=f"AI_WP{L}_TURB",
        )
        self.state = BrewhouseState.IDLE
        self.elapsed = offset_s  # stagger lines
        self.phase_elapsed = 0.0
        self.mash_step = 0
        self.recirc_done = False
        self.wort_brix = 0.0

        pc = cfg.get("process", {})
        self.mash_steps = list(zip(
            pc.get("mashing", {}).get("step_durations", [900, 1800, 1200, 600]),
            pc.get("mashing", {}).get("step_temps", [52.0, 63.0, 72.0, 78.0]),
        ))
        self.lauter_dur = self.rng.uniform(
            pc.get("lautering", {}).get("duration_min", 2700),
            pc.get("lautering", {}).get("duration_max", 4500),
        )
        self.boil_dur = pc.get("boiling", {}).get("duration", 3600)
        self.wp_pump_dur = pc.get("whirlpool", {}).get("pump_duration", 600)
        self.wp_stand_dur = pc.get("whirlpool", {}).get("stand_duration", 900)
        self.transfer_dur = self.rng.uniform(
            pc.get("cooling", {}).get("duration_min", 900),
            pc.get("cooling", {}).get("duration_max", 1800),
        )
        self.fault_prob = 0.0002
        self.fault_recovery_timer = 0.0
        self.fault_active = False
        self.idle_dur = self.rng.uniform(600, 1800)

        phys_cfg = cfg.get("physics", {})
        self.approach_rate = phys_cfg.get("temp_approach_rate", 0.002)
        self.noise_std = phys_cfg.get("analog_noise_std", 0.05)
        self.fill_rate = phys_cfg.get("level_fill_rate", 0.15)
        self.drain_rate = phys_cfg.get("level_drain_rate", 0.12)

    def _n(self, v, s=None):
        return phys.add_noise(v, s or self.noise_std, self.rng)

    def tick(self, dt_sim: float) -> None:
        self.elapsed += dt_sim
        self.phase_elapsed += dt_sim
        t = self.tags

        # Fault propagation: if rake faulted, stop rake DO
        if self._get(t["mt_rake_flt"]):
            self._set(t["do_mt_rake"], False)
            self._set(t["mt_rake_run"], False)
            if self._random_recovery(300, dt_sim):
                self._set(t["mt_rake_flt"], False)

        if self.state == BrewhouseState.IDLE:
            self._zero_all()
            if self.phase_elapsed >= self.idle_dur:
                self._enter_mashing()

        elif self.state == BrewhouseState.MASHING:
            self._tick_mashing(dt_sim)

        elif self.state == BrewhouseState.LAUTERING:
            self._tick_lautering(dt_sim)

        elif self.state == BrewhouseState.BOILING:
            self._tick_boiling(dt_sim)

        elif self.state == BrewhouseState.WHIRLPOOL:
            self._tick_whirlpool(dt_sim)

        elif self.state == BrewhouseState.TRANSFER:
            self._tick_transfer(dt_sim)

    def _zero_all(self):
        t = self.tags
        for tag in [t["do_mt_rake"], t["do_mt_heat"], t["do_mt_pump"],
                    t["do_lt_rake"], t["do_kt_heat"], t["do_wp_pump"],
                    t["mt_rake_run"], t["lt_rake_run"], t["pmp_mt_run"], t["pmp_wp_run"]]:
            self._set(tag, False)
        self._set(t["ai_lt_flow"], 0.0)
        self._set(t["ai_kt_steam"], 0.0)
        self._set(t["ai_elec_bh"], self._n(2.0, 0.3))

    def _enter_mashing(self):
        self.state = BrewhouseState.MASHING
        self.phase_elapsed = 0.0
        self.mash_step = 0
        sp, temp = self.mash_steps[0]
        self._set(self.tags["ao_mt_sp"], temp)
        self._set(self.tags["do_mt_heat"], True)
        self._set(self.tags["do_mt_rake"], True)

    def _tick_mashing(self, dt_sim: float):
        t = self.tags
        step_dur, step_temp = self.mash_steps[self.mash_step]
        # heat mash
        mt_tt = phys.approach(self._get(t["ai_mt_tt"]), step_temp, self.approach_rate, dt_sim)
        self._set(t["ai_mt_tt"], self._n(mt_tt, 0.3))
        self._set(t["ao_mt_sp"], step_temp)
        self._set(t["do_mt_heat"], True)
        self._set(t["do_mt_rake"], True)
        self._set(t["mt_rake_run"], not self._get(t["mt_rake_flt"]))
        # fill tank
        lvl = self._get_lvl(t["ai_mt_lt"])
        if lvl < 85:
            self._set_lvl(t["ai_mt_lt"], phys.fill_tank(lvl, self.fill_rate, dt_sim))
        self._set(t["mt_ls_hi"], self._get_lvl(t["ai_mt_lt"]) > 90)
        self._set(t["mt_ls_lo"], self._get_lvl(t["ai_mt_lt"]) < 5)
        self._set(t["ai_mt_ph"], self._n(5.4, 0.05))
        self._set(t["ai_wort_brix"], self._n(13.5, 0.2))
        self._set(t["ai_elec_bh"], self._n(30.0, 2.0))
        # step advance
        if self.phase_elapsed >= step_dur:
            self.mash_step += 1
            self.phase_elapsed = 0.0
            if self.mash_step >= len(self.mash_steps):
                self._enter_lautering()

    def _enter_lautering(self):
        self.state = BrewhouseState.LAUTERING
        self.phase_elapsed = 0.0
        self.recirc_done = False
        self.lauter_dur = self.rng.uniform(2700, 4500)
        self._set(self.tags["do_lt_rake"], True)

    def _tick_lautering(self, dt_sim: float):
        t = self.tags
        recirc_time = 600.0
        if self.phase_elapsed > recirc_time:
            self.recirc_done = True

        flow = self._n(650.0, 30.0) if self.recirc_done else 0.0
        self._set(t["ai_lt_flow"], max(0.0, flow))

        turb = phys.turbidity_lauter(self.phase_elapsed, self.recirc_done, flow)
        self._set(t["ai_lt_turb"], self._n(turb, 5.0))

        # drain mt, fill lt, fill kt
        mt_lvl = phys.drain_tank(self._get_lvl(t["ai_mt_lt"]), self.drain_rate, dt_sim)
        self._set_lvl(t["ai_mt_lt"], mt_lvl)
        lt_lvl = self._get_lvl(t["ai_lt_lt"])
        if lt_lvl < 80 and self.recirc_done:
            lt_fill = phys.fill_tank(lt_lvl, self.fill_rate * 0.5, dt_sim)
        else:
            lt_fill = phys.drain_tank(lt_lvl, self.drain_rate * 0.3, dt_sim)
        self._set_lvl(t["ai_lt_lt"], lt_fill)
        self._set(t["lt_ls_hi"], lt_fill > 90)
        self._set(t["lt_ls_lo"], lt_fill < 5)

        kt_lvl = phys.fill_tank(self._get_lvl(t["ai_kt_lt"]), self.fill_rate * 0.4, dt_sim)
        self._set_lvl(t["ai_kt_lt"], kt_lvl)
        self._set(t["lt_rake_run"], True)
        self._set(t["ai_lt_tt"], self._n(75.0, 0.5))

        self._set(t["ai_wort_brix"], self._n(12.8 - (self.phase_elapsed / self.lauter_dur) * 5, 0.3))
        self._set(t["ai_elec_bh"], self._n(12.0, 1.0))

        if self.phase_elapsed >= self.lauter_dur:
            self._enter_boiling()

    def _enter_boiling(self):
        self.state = BrewhouseState.BOILING
        self.phase_elapsed = 0.0
        self._set(self.tags["do_lt_rake"], False)
        self._set(self.tags["do_kt_heat"], True)
        self._set(self.tags["ao_kt_sp"], 100.0)

    def _tick_boiling(self, dt_sim: float):
        t = self.tags
        kt_tt = phys.approach(self._get(t["ai_kt_tt"]), 100.0, self.approach_rate * 2, dt_sim)
        self._set(t["ai_kt_tt"], self._n(kt_tt, 0.3))
        self._set(t["do_kt_heat"], True)
        self._set(t["kt_ls_hi"], self._get_lvl(t["ai_kt_lt"]) > 88)
        self._set(t["kt_ls_lo"], self._get_lvl(t["ai_kt_lt"]) < 5)
        # Evaporate
        if kt_tt > 97:
            evap = 0.08 / 3600  # 8%/hr → per second
            lvl = self._get_lvl(t["ai_kt_lt"]) * (1 - evap * dt_sim)
            self._set_lvl(t["ai_kt_lt"], lvl)
            steam = self._n(220.0, 10.0)
            self._set(t["ai_kt_steam"], steam)
            self._set(t["ai_elec_bh"], self._n(60.0, 3.0))
        if self.phase_elapsed >= self.boil_dur:
            self._enter_whirlpool()

    def _enter_whirlpool(self):
        self.state = BrewhouseState.WHIRLPOOL
        self.phase_elapsed = 0.0
        self._set(self.tags["do_kt_heat"], False)
        self._set(self.tags["do_wp_pump"], True)

    def _tick_whirlpool(self, dt_sim: float):
        t = self.tags
        pumping = self.phase_elapsed < self.wp_pump_dur
        self._set(t["do_wp_pump"], pumping)
        self._set(t["pmp_wp_run"], pumping)
        if pumping:
            # transfer kt→wp
            kt_lvl = phys.drain_tank(self._get_lvl(t["ai_kt_lt"]), self.drain_rate * 0.8, dt_sim)
            self._set_lvl(t["ai_kt_lt"], kt_lvl)
            wp_lvl = phys.fill_tank(self._get_lvl(t["ai_wp_lt"]), self.fill_rate * 0.8, dt_sim)
            self._set_lvl(t["ai_wp_lt"], wp_lvl)
        self._set(t["wp_ls_hi"], self._get_lvl(t["ai_wp_lt"]) > 88)
        self._set(t["wp_ls_lo"], self._get_lvl(t["ai_wp_lt"]) < 5)
        # Cool slightly
        wp_tt = phys.approach(self._get(t["ai_wp_tt"]), 85.0, self.approach_rate * 0.5, dt_sim)
        self._set(t["ai_wp_tt"], self._n(wp_tt, 0.3))
        # Turbidity clears during stand
        stand_t = max(0, self.phase_elapsed - self.wp_pump_dur)
        turb = 120 * math.exp(-stand_t / 600)
        self._set(t["ai_wp_turb"], self._n(turb, 3.0))
        self._set(t["ai_elec_bh"], self._n(8.0, 0.5))
        if self.phase_elapsed >= self.wp_pump_dur + self.wp_stand_dur:
            self._enter_transfer()

    def _enter_transfer(self):
        self.state = BrewhouseState.TRANSFER
        self.phase_elapsed = 0.0

    def _tick_transfer(self, dt_sim: float):
        t = self.tags
        # Drain WP
        wp_lvl = phys.drain_tank(self._get_lvl(t["ai_wp_lt"]), self.drain_rate, dt_sim)
        self._set_lvl(t["ai_wp_lt"], wp_lvl)
        if self.phase_elapsed >= self.transfer_dur:
            self.state = BrewhouseState.IDLE
            self.phase_elapsed = 0.0
            self.idle_dur = self.rng.uniform(300, 900)
            self._set_lvl(t["ai_mt_lt"], 0.0)
            self._set_lvl(t["ai_kt_lt"], 0.0)
            self._set_lvl(t["ai_wp_lt"], 0.0)


class BrewhouseArea(AreaSimulator):
    def __init__(self, store, cfg, rng):
        super().__init__(store, cfg, rng)
        self.line1 = BrewhouseLine(store, cfg, rng, line=1, offset_s=0)
        self.line2 = BrewhouseLine(store, cfg, rng, line=2, offset_s=rng.uniform(3600, 7200))

    def tick(self, dt_sim):
        self.line1.tick(dt_sim)
        self.line2.tick(dt_sim)


# ─────────────────────────────────────────────────────────────────────────────
# AREA 400 — HX & AERATION
# ─────────────────────────────────────────────────────────────────────────────

class CoolingArea(AreaSimulator):
    def __init__(self, store, cfg, rng):
        super().__init__(store, cfg, rng)
        self.hx1_active_timer = 0.0
        self.hx2_active_timer = 0.0
        self.hx_cycle = rng.uniform(3600, 7200)
        self.hx1_offset = rng.uniform(0, 3600)
        self.elapsed = 0.0

    def tick(self, dt_sim):
        self.elapsed += dt_sim
        ph = self.cfg.get("physics", {})
        approach_rate = ph.get("temp_approach_rate", 0.002)
        n = lambda v, s: phys.add_noise(v, s, self.rng)

        chiller_ok = self.store.get("DI_CHILLER_RUN")

        for i, (suffix, offset) in enumerate([("1", self.hx1_offset), ("2", 0)]):
            phase = (self.elapsed + offset) % (self.hx_cycle * 2)
            active = phase < self.hx_cycle

            fault_tag = f"DI_HX{suffix}_PMP_FLT"
            run_tag = f"DI_HX{suffix}_PMP_RUN"
            do_wort = f"DO_HX{suffix}_PMP_WORT"
            do_water = f"DO_HX{suffix}_PMP_WATER"
            o2_valve = f"DO_O2_VALVE_L{suffix}"
            tt_in = f"AI_HX{suffix}_TT_IN"
            tt_out = f"AI_HX{suffix}_TT_OUT"
            flow = f"AI_HX{suffix}_FLOW_WORT"
            o2 = f"AI_HX{suffix}_O2_PPM"
            ao_water = f"AO_HX{suffix}_WATER_FLOW"

            fault = self.store.get(fault_tag)
            if fault:
                if self._random_recovery(300, dt_sim):
                    self.store.set(fault_tag, False)
                self.store.set(run_tag, False)
                self.store.set(do_wort, False)
                continue

            if active and chiller_ok:
                self.store.set(run_tag, True)
                self.store.set(do_wort, True)
                self.store.set(do_water, True)
                self.store.set(o2_valve, True)
                t_in = n(92.0, 1.0)
                self.store.set(tt_in, t_in)
                target_out = 20.0
                t_out_cur = self.store.get(tt_out)
                t_out = phys.approach(t_out_cur, target_out, approach_rate * 5, dt_sim)
                self.store.set(tt_out, n(t_out, 0.2))
                self.store.set(flow, n(600.0, 20.0))
                self.store.set(o2, n(8.2, 0.3))
                self.store.set(ao_water, n(75.0, 2.0))
            else:
                self.store.set(run_tag, False)
                self.store.set(do_wort, False)
                self.store.set(do_water, False)
                self.store.set(o2_valve, False)
                self.store.set(flow, 0.0)
                self.store.set(o2, 0.0)
                self.store.set(ao_water, 0.0)
                if self._random_fault(0.0001, dt_sim):
                    self.store.set(fault_tag, True)


# ─────────────────────────────────────────────────────────────────────────────
# AREA 500 — FERMENTATION
# ─────────────────────────────────────────────────────────────────────────────

class FermentationPhase(enum.Enum):
    EMPTY = "empty"
    FILLING = "filling"
    LAG = "lag"
    ACTIVE = "active"
    DIACETYL_REST = "diacetyl_rest"
    COLD_CRASH = "cold_crash"
    LAGERING = "lagering"
    DRAINING = "draining"


class FVSimulator(AreaSimulator):
    """Single fermentation vessel."""

    def __init__(self, store, cfg, rng, fv_num: int, start_offset: float = 0) -> None:
        super().__init__(store, cfg, rng)
        n = str(fv_num)
        self.tags = {
            "ls_hi": f"DI_FV{n}_LS_HI", "ls_lo": f"DI_FV{n}_LS_LO",
            "prv": f"DI_FV{n}_PRV", "gly_run": f"DI_FV{n}_GLY_RUN",
            "do_gly": f"DO_FV{n}_GLY_EN", "do_vent": f"DO_FV{n}_CO2_VENT",
            "do_spund": f"DO_FV{n}_SPUND",
            "tt": f"AI_FV{n}_TT", "pt": f"AI_FV{n}_PT", "ph": f"AI_FV{n}_PH",
            "brix": f"AI_FV{n}_BRIX", "co2": f"AI_FV{n}_CO2_PPM",
            "lt": f"AI_FV{n}_LT", "temp_sp": f"AO_FV{n}_TEMP_SP",
            "press_sp": f"AO_FV{n}_PRESS_SP",
        }
        self.phase = FermentationPhase.EMPTY
        self.phase_elapsed = start_offset
        self.elapsed = start_offset
        self.og = 13.5
        self.fg = 3.5

        pc = cfg.get("process", {}).get("fermentation", {})
        self.phase_durs = pc.get("phase_durations", [43200, 259200, 86400, 172800, 604800])
        self.active_temp_sp = pc.get("active_temp_sp", 20.0)
        self.cold_crash_sp = pc.get("cold_crash_sp", 2.0)

        ph_cfg = cfg.get("physics", {})
        self.approach_rate = ph_cfg.get("temp_approach_rate", 0.002)
        self.fill_rate = ph_cfg.get("level_fill_rate", 0.15)
        self.drain_rate = ph_cfg.get("level_drain_rate", 0.12)

        self.idle_dur = rng.uniform(1800, 10800)
        self.active_brix_start = self.og
        self.active_brix_elapsed = 0.0

    def _n(self, v, s=0.05):
        return phys.add_noise(v, s, self.rng)

    def tick(self, dt_sim: float) -> None:
        self.elapsed += dt_sim
        self.phase_elapsed += dt_sim
        t = self.tags

        ph = self.phase

        if ph == FermentationPhase.EMPTY:
            self._idle_tick()
            if self.phase_elapsed >= self.idle_dur:
                self._enter_filling()

        elif ph == FermentationPhase.FILLING:
            lvl = phys.fill_tank(self._get_lvl(t["lt"]), self.fill_rate, dt_sim)
            self._set_lvl(t["lt"], lvl)
            self._set(t["ls_hi"], lvl > 90)
            self._set(t["ls_lo"], lvl < 5)
            self._set(t["tt"], self._n(20.0, 0.5))
            self._set(t["brix"], self._n(self.og, 0.2))
            self._set(t["ph"], self._n(5.4, 0.05))
            self._set(t["pt"], self._n(0.0, 0.02))
            if lvl >= 88:
                self._enter_lag()

        elif ph == FermentationPhase.LAG:
            self._set(t["do_gly"], True)
            sp = self.active_temp_sp
            self._set(t["temp_sp"], sp)
            tt = phys.approach(self._get(t["tt"]), sp, self.approach_rate, dt_sim)
            self._set(t["tt"], self._n(tt, 0.1))
            self._set(t["pt"], self._n(0.05, 0.01))
            self._set(t["brix"], self._n(self.og, 0.1))
            self._set(t["ph"], self._n(5.3, 0.05))
            if self.phase_elapsed >= self.phase_durs[0]:
                self._enter_active()

        elif ph == FermentationPhase.ACTIVE:
            self.active_brix_elapsed += dt_sim
            self._set(t["do_gly"], True)
            self._set(t["do_spund"], True)
            self._set(t["gly_run"], True)
            sp = self.active_temp_sp
            self._set(t["temp_sp"], sp)
            tt = phys.approach(self._get(t["tt"]), sp, self.approach_rate * 2, dt_sim)
            self._set(t["tt"], self._n(tt, 0.1))
            # Brix drops
            brix = phys.fermentation_brix(self.active_brix_elapsed, self.og, self.fg, self.phase_durs[1])
            self._set(t["brix"], self._n(brix, 0.1))
            # Pressure builds
            brix_drop = self.og - brix
            pt = phys.pressure_from_co2(brix_drop, tt)
            self._set(t["pt"], self._n(pt, 0.02))
            self._set(t["do_vent"], pt > 1.8)
            self._set(t["prv"], pt > 2.5)
            self._set(t["ph"], self._n(4.2 - brix_drop * 0.02, 0.05))
            co2 = self._n(brix_drop * 0.35, 0.1)
            self._set(t["co2"], max(0.0, co2))
            if self.phase_elapsed >= self.phase_durs[1]:
                self._enter_diacetyl()

        elif ph == FermentationPhase.DIACETYL_REST:
            sp = self.active_temp_sp + 2.0
            self._set(t["temp_sp"], sp)
            tt = phys.approach(self._get(t["tt"]), sp, self.approach_rate, dt_sim)
            self._set(t["tt"], self._n(tt, 0.1))
            self._set(t["brix"], self._n(self.fg, 0.08))
            pt = phys.approach(self._get(t["pt"]), 0.3, self.approach_rate, dt_sim)
            self._set(t["pt"], self._n(pt, 0.01))
            if self.phase_elapsed >= self.phase_durs[2]:
                self._enter_cold_crash()

        elif ph == FermentationPhase.COLD_CRASH:
            sp = self.cold_crash_sp
            self._set(t["temp_sp"], sp)
            tt = phys.approach(self._get(t["tt"]), sp, self.approach_rate * 0.5, dt_sim)
            self._set(t["tt"], self._n(tt, 0.1))
            self._set(t["brix"], self._n(self.fg, 0.05))
            pt = phys.approach(self._get(t["pt"]), 0.5, self.approach_rate * 0.5, dt_sim)
            self._set(t["pt"], self._n(pt, 0.01))
            self._set(t["ph"], self._n(4.0, 0.03))
            if self.phase_elapsed >= self.phase_durs[3]:
                self._enter_draining()

        elif ph == FermentationPhase.DRAINING:
            lvl = phys.drain_tank(self._get_lvl(t["lt"]), self.drain_rate * 0.5, dt_sim)
            self._set_lvl(t["lt"], lvl)
            self._set(t["ls_hi"], lvl > 90)
            self._set(t["ls_lo"], lvl < 5)
            if lvl <= 5:
                self._reset()

    def _idle_tick(self):
        t = self.tags
        for do_tag in [t["do_gly"], t["do_vent"], t["do_spund"]]:
            self._set(do_tag, False)
        self._set_lvl(t["lt"], self._n(0.0, 0.1))
        self._set(t["pt"], self._n(0.0, 0.01))
        self._set(t["tt"], self._n(20.0, 0.3))
        self._set(t["brix"], 0.0)
        self._set(t["ls_hi"], False)
        self._set(t["ls_lo"], True)
        self._set(t["prv"], False)

    def _enter_filling(self):
        self.phase = FermentationPhase.FILLING
        self.phase_elapsed = 0.0

    def _enter_lag(self):
        self.phase = FermentationPhase.LAG
        self.phase_elapsed = 0.0

    def _enter_active(self):
        self.phase = FermentationPhase.ACTIVE
        self.phase_elapsed = 0.0
        self.active_brix_elapsed = 0.0
        self.og = self.rng.uniform(12.5, 14.5)
        self.fg = self.rng.uniform(2.8, 4.0)
        self.active_brix_start = self.og

    def _enter_diacetyl(self):
        self.phase = FermentationPhase.DIACETYL_REST
        self.phase_elapsed = 0.0

    def _enter_cold_crash(self):
        self.phase = FermentationPhase.COLD_CRASH
        self.phase_elapsed = 0.0

    def _enter_draining(self):
        self.phase = FermentationPhase.DRAINING
        self.phase_elapsed = 0.0

    def _reset(self):
        self.phase = FermentationPhase.EMPTY
        self.phase_elapsed = 0.0
        self.idle_dur = self.rng.uniform(1800, 7200)


class FermentationArea(AreaSimulator):
    def __init__(self, store, cfg, rng):
        super().__init__(store, cfg, rng)
        ferm_cfg = cfg.get("process", {}).get("fermentation", {})
        total_cycle = sum(ferm_cfg.get("phase_durations", [43200, 259200, 86400, 172800, 604800]))
        self.fvs = [
            FVSimulator(store, cfg, rng, fv_num=i,
                        start_offset=rng.uniform(0, total_cycle))
            for i in range(1, 7)
        ]
        # Yeast brinks
        self.yb1_temp = 4.0
        self.yb2_temp = 4.0
        # CO2 recovery
        self.co2_consumed = 0.0
        self.co2_recovered = 0.0

    def tick(self, dt_sim):
        for fv in self.fvs:
            fv.tick(dt_sim)

        n = lambda v, s: phys.add_noise(v, s, self.rng)

        # Yeast brinks
        self.store.set("AI_YB1_TT", n(4.0, 0.2))
        self.store.set("AI_YB2_TT", n(4.0, 0.2))
        self.store.set("DI_YB1_LS", self.rng.random() > 0.7)
        self.store.set("DI_YB2_LS", self.rng.random() > 0.8)

        # CO2 from active fermenters
        active_fvs = sum(1 for fv in self.fvs if fv.phase == FermentationPhase.ACTIVE)
        co2_flow = n(active_fvs * 4.2, 0.5)
        self.store.set("AI_CO2_FLOW_FV", max(0.0, co2_flow))
        self.co2_recovered += co2_flow * dt_sim / 3600

        # CO2 tank (gets consumed + recovered)
        tank_wt = self.store.get("AI_CO2_TANK_WT")
        tank_wt = max(500.0, min(5000.0, tank_wt + (co2_flow - 2.0) * dt_sim / 3600))
        self.store.set("AI_CO2_TANK_WT", tank_wt)
        press = n(8.0 + (tank_wt - 2000) / 1000, 0.1)
        self.store.set("AI_CO2_TANK_PRESS", max(2.0, press))
        self.co2_consumed += 2.0 * dt_sim / 3600
        self.store.set("AI_CO2_CONSUMED", self.co2_consumed)


# ─────────────────────────────────────────────────────────────────────────────
# AREA 600 — BBT, FILTRATION, CENTRIFUGE
# ─────────────────────────────────────────────────────────────────────────────

class BBTState(enum.Enum):
    EMPTY = "empty"
    FILLING = "filling"
    CARBONATING = "carbonating"
    READY = "ready"
    DRAINING = "draining"


class BBTSimulator(AreaSimulator):
    def __init__(self, store, cfg, rng, bbt_num: int, offset: float = 0) -> None:
        super().__init__(store, cfg, rng)
        n = str(bbt_num)
        self.tags = {
            "ls_hi": f"DI_BBT{n}_LS_HI", "ls_lo": f"DI_BBT{n}_LS_LO",
            "do_gly": f"DO_BBT{n}_GLY_EN", "do_carb": f"DO_BBT{n}_CO2_CARB",
            "tt": f"AI_BBT{n}_TT", "pt": f"AI_BBT{n}_PT", "lt": f"AI_BBT{n}_LT",
            "co2": f"AI_BBT{n}_CO2", "o2": f"AI_BBT{n}_O2", "turb": f"AI_BBT{n}_TURB",
            "ph": f"AI_BBT{n}_PH", "temp_sp": f"AO_BBT{n}_TEMP_SP",
            "co2_sp": f"AO_BBT{n}_CO2_SP",
        }
        self.state = BBTState.EMPTY
        self.phase_elapsed = offset
        self.elapsed = offset
        pc = cfg.get("process", {}).get("bbt", {})
        self.fill_dur = pc.get("fill_duration", 1800)
        self.carb_dur = pc.get("carb_duration", 86400)
        self.carb_sp = pc.get("carb_pressure_sp", 2.1)
        self.temp_sp = pc.get("temp_sp", 2.0)
        self.idle_dur = rng.uniform(3600, 14400)
        ph_cfg = cfg.get("physics", {})
        self.approach_rate = ph_cfg.get("temp_approach_rate", 0.002)
        self.fill_rate = ph_cfg.get("level_fill_rate", 0.15)
        self.drain_rate = ph_cfg.get("level_drain_rate", 0.12)

    def _n(self, v, s=0.05):
        return phys.add_noise(v, s, self.rng)

    def tick(self, dt_sim):
        self.elapsed += dt_sim
        self.phase_elapsed += dt_sim
        t = self.tags

        if self.state == BBTState.EMPTY:
            self._set_lvl(t["lt"], self._n(0.0, 0.1))
            self._set(t["pt"], self._n(0.0, 0.02))
            self._set(t["do_gly"], False)
            self._set(t["do_carb"], False)
            self._set(t["ls_hi"], False); self._set(t["ls_lo"], True)
            if self.phase_elapsed >= self.idle_dur:
                self.state = BBTState.FILLING
                self.phase_elapsed = 0.0

        elif self.state == BBTState.FILLING:
            lvl = phys.fill_tank(self._get_lvl(t["lt"]), self.fill_rate * 0.5, dt_sim)
            self._set_lvl(t["lt"], lvl)
            self._set(t["ls_hi"], lvl > 90)
            self._set(t["ls_lo"], lvl < 5)
            self._set(t["tt"], self._n(4.0, 0.3))
            self._set(t["ph"], self._n(4.1, 0.03))
            self._set(t["turb"], self._n(15.0, 2.0))
            if self.phase_elapsed >= self.fill_dur or lvl >= 88:
                self.state = BBTState.CARBONATING
                self.phase_elapsed = 0.0
                self._set(t["do_carb"], True)

        elif self.state == BBTState.CARBONATING:
            self._set(t["do_gly"], True)
            self._set(t["do_carb"], True)
            tt = phys.approach(self._get(t["tt"]), self.temp_sp, self.approach_rate, dt_sim)
            self._set(t["tt"], self._n(tt, 0.1))
            self._set(t["temp_sp"], self.temp_sp)
            # CO2 rises
            co2 = phys.approach(self._get(t["co2"]), 5.5, self.approach_rate * 0.5, dt_sim)
            self._set(t["co2"], self._n(co2, 0.05))
            pt = phys.approach(self._get(t["pt"]), self.carb_sp, self.approach_rate, dt_sim)
            self._set(t["pt"], self._n(pt, 0.02))
            self._set(t["co2_sp"], self.carb_sp)
            self._set(t["o2"], self._n(45.0, 5.0))
            self._set(t["turb"], self._n(8.0, 1.0))
            if self.phase_elapsed >= self.carb_dur:
                self.state = BBTState.READY
                self.phase_elapsed = 0.0

        elif self.state == BBTState.READY:
            self._set(t["do_gly"], True)
            tt = phys.approach(self._get(t["tt"]), self.temp_sp, self.approach_rate * 0.5, dt_sim)
            self._set(t["tt"], self._n(tt, 0.05))
            self._set(t["co2"], self._n(5.5, 0.05))
            self._set(t["pt"], self._n(self.carb_sp, 0.02))
            self._set(t["o2"], self._n(42.0, 3.0))
            self._set(t["turb"], self._n(7.0, 0.5))
            self._set(t["ph"], self._n(4.05, 0.02))
            # Stay ready for random duration then start draining (packaging)
            ready_stay = 14400  # 4h
            if self.phase_elapsed >= ready_stay:
                self.state = BBTState.DRAINING
                self.phase_elapsed = 0.0

        elif self.state == BBTState.DRAINING:
            lvl = phys.drain_tank(self._get_lvl(t["lt"]), self.drain_rate * 0.3, dt_sim)
            self._set_lvl(t["lt"], lvl)
            self._set(t["ls_hi"], lvl > 90)
            self._set(t["ls_lo"], lvl < 5)
            if lvl <= 5:
                self.state = BBTState.EMPTY
                self.phase_elapsed = 0.0
                self.idle_dur = self.rng.uniform(1800, 7200)


class MaturationArea(AreaSimulator):
    def __init__(self, store, cfg, rng):
        super().__init__(store, cfg, rng)
        self.bbt1 = BBTSimulator(store, cfg, rng, 1, offset=0)
        self.bbt2 = BBTSimulator(store, cfg, rng, 2, offset=rng.uniform(14400, 86400))
        self.elapsed = 0.0
        self.filt_active = False
        self.cent_active = False
        self.cycle_timer = 0.0
        self.filt_cycle = rng.uniform(3600, 7200)
        self.beer_loss_accum = 0.0

    def tick(self, dt_sim):
        self.bbt1.tick(dt_sim)
        self.bbt2.tick(dt_sim)
        self.elapsed += dt_sim
        self.cycle_timer += dt_sim
        n = lambda v, s: phys.add_noise(v, s, self.rng)

        # Filtration cycles
        filt_phase = self.cycle_timer % (self.filt_cycle * 2)
        filt_active = filt_phase < self.filt_cycle
        self._set("DI_FILT_PMP_RUN", filt_active)
        self._set("DO_FILT_PMP_RUN", filt_active)
        self._set("AI_FILT_DP", n(0.8 if filt_active else 0.1, 0.05))
        self._set("AI_FILT_FLOW", n(500.0 if filt_active else 0.0, 20.0))

        # Centrifuge
        cent_active = filt_phase < self.filt_cycle * 0.6
        self._set("DI_CENT_RUN", cent_active)
        self._set("DO_CENT_START", cent_active)
        self._set("AI_CENT_TURB_OUT", n(8.0 if cent_active else 0.0, 1.0))
        self._set("AI_CENT_FLOW", n(1200.0 if cent_active else 0.0, 50.0))

        # Beer loss
        if filt_active:
            loss = n(2.5, 0.3)
            self.beer_loss_accum += loss * dt_sim / 3600
        self._set("AI_BEER_LOSS_FV_BBT", n(self.beer_loss_accum, 0.5))


# ─────────────────────────────────────────────────────────────────────────────
# AREA 700 — PACKAGING
# ─────────────────────────────────────────────────────────────────────────────

class PackagingArea(AreaSimulator):
    def __init__(self, store, cfg, rng):
        super().__init__(store, cfg, rng)
        self.elapsed = 0.0
        self.keg_count = 0
        self.can_count = 0
        self.keg_fill_timer = 0.0
        self.keg_fill_target = cfg.get("process", {}).get("packaging", {}).get("keg_fill_time", 120)
        self.can_rate = cfg.get("process", {}).get("packaging", {}).get("can_rate", 2000)
        # Stagger: kegging runs in 4h shifts, canning in different shifts
        self.keg_shift_dur = 14400
        self.can_shift_dur = 10800
        self.total_beer_loss = 0.0

    def tick(self, dt_sim):
        self.elapsed += dt_sim
        n = lambda v, s: phys.add_noise(v, s, self.rng)

        # Kegging
        keg_phase = self.elapsed % (self.keg_shift_dur * 2)
        keg_running = keg_phase < self.keg_shift_dur
        keg_fault = self.store.get("DI_KEG_LINE_FLT")
        if keg_fault:
            keg_running = False
            if self._random_recovery(300, dt_sim):
                self.store.set("DI_KEG_LINE_FLT", False)
        else:
            if self._random_fault(0.0001, dt_sim):
                self.store.set("DI_KEG_LINE_FLT", True)

        self.store.set("DI_KEG_LINE_RUN", keg_running)
        self.store.set("DO_KEG_LINE_START", keg_running)
        if keg_running:
            self.keg_fill_timer += dt_sim
            if self.keg_fill_timer >= self.keg_fill_target:
                self.keg_count += 1
                self.keg_fill_timer = 0.0
                self.store.set("DI_KEG_FULL", True)
            else:
                self.store.set("DI_KEG_FULL", False)
            self.store.set("DI_KEG_SENSOR", self.keg_fill_timer < 5)
            self.store.set("AI_KEG_FILL_PRESS", n(2.8, 0.1))
            self.store.set("AI_KEG_FILL_TEMP", n(3.5, 0.2))
            loss = n(1.5, 0.2)
            self.total_beer_loss += loss * dt_sim / 3600
        else:
            self.store.set("DI_KEG_SENSOR", False)
            self.store.set("AI_KEG_FILL_PRESS", 0.0)

        self.store.set("AI_KEG_COUNT", float(self.keg_count))
        self.store.set("AI_PACK_BEER_LOSS", n(self.total_beer_loss, 0.1))

        # Canning
        can_phase = (self.elapsed + self.can_shift_dur) % (self.can_shift_dur * 2)
        can_running = can_phase < self.can_shift_dur
        can_fault = self.store.get("DI_CAN_LINE_FLT")
        if can_fault:
            can_running = False
            if self._random_recovery(200, dt_sim):
                self.store.set("DI_CAN_LINE_FLT", False)
        else:
            if self._random_fault(0.00015, dt_sim):
                self.store.set("DI_CAN_LINE_FLT", True)

        self.store.set("DI_CAN_LINE_RUN", can_running)
        self.store.set("DO_CAN_LINE_START", can_running)
        if can_running:
            cans_this_tick = self.can_rate * dt_sim / 3600
            self.can_count += int(cans_this_tick)
            self.store.set("DI_CAN_SENSOR", True)
            self.store.set("AI_CAN_DO_PPB", n(28.0, 3.0))
            self.store.set("AI_CAN_FILL_VOL", n(355.0, 2.0))
        else:
            self.store.set("DI_CAN_SENSOR", False)
            self.store.set("AI_CAN_DO_PPB", 0.0)

        self.store.set("AI_CAN_COUNT", float(self.can_count))

        # Labeler follows keg line
        self.store.set("DI_LABEL_RUN", keg_running)
        self.store.set("DO_LABEL_START", keg_running)
        self.store.set("AI_ELEC_KW_PACK", n(12.0 if (keg_running or can_running) else 2.0, 0.5))


# ─────────────────────────────────────────────────────────────────────────────
# AREA 800 — CIP
# ─────────────────────────────────────────────────────────────────────────────

class CIPState(enum.Enum):
    IDLE = "idle"
    PRE_RINSE = "pre_rinse"
    CAUSTIC = "caustic"
    RINSE_MID = "rinse_mid"
    ACID = "acid"
    FINAL_RINSE = "final_rinse"


class CIPArea(AreaSimulator):
    STEPS = [
        (CIPState.PRE_RINSE, 600, "Pre-rinse"),
        (CIPState.CAUSTIC, 1200, "Caustic"),
        (CIPState.RINSE_MID, 600, "Mid-rinse"),
        (CIPState.ACID, 600, "Acid"),
        (CIPState.FINAL_RINSE, 600, "Final rinse"),
    ]

    def __init__(self, store, cfg, rng):
        super().__init__(store, cfg, rng)
        self.state = CIPState.IDLE
        self.elapsed = 0.0
        self.step_elapsed = 0.0
        self.step_idx = 0
        self.idle_dur = rng.uniform(7200, 28800)
        self.total_water = 0.0
        pc = cfg.get("process", {}).get("cip", {})
        self.step_durs = pc.get("step_durations", [600, 1200, 600, 600, 600])
        self.caustic_sp = pc.get("caustic_temp_sp", 72.0)

    def tick(self, dt_sim):
        self.elapsed += dt_sim
        self.step_elapsed += dt_sim
        n = lambda v, s: phys.add_noise(v, s, self.rng)

        if self.state == CIPState.IDLE:
            self._set("DI_CIP_PMP_RUN", False)
            self._set("DO_CIP_PUMP_RUN", False)
            self._set("DO_CIP_HEAT_EN", False)
            self._set("AI_CIP_FLOW", 0.0)
            self._set("AI_CIP_TT_CAUST", n(20.0, 0.3))
            self._set("AI_CIP_COND_RET", n(0.5, 0.05))
            self._set("AI_CIP_PH_RET", n(7.0, 0.05))
            self._set("AI_ELEC_KW_CIP", n(0.5, 0.1))
            if self.step_elapsed >= self.idle_dur:
                self._next_step()
        else:
            self._run_step(dt_sim, n)

    def _next_step(self):
        if self.state == CIPState.IDLE:
            self.step_idx = 0
        else:
            self.step_idx += 1
        if self.step_idx >= len(self.STEPS):
            self.state = CIPState.IDLE
            self.step_elapsed = 0.0
            self.idle_dur = self.rng.uniform(7200, 28800)
        else:
            self.state, _, _ = self.STEPS[self.step_idx]
            self.step_elapsed = 0.0

    def _run_step(self, dt_sim, n):
        _, step_dur, _ = self.STEPS[self.step_idx]
        ph = self.cfg.get("physics", {})
        approach_rate = ph.get("temp_approach_rate", 0.002)

        self._set("DI_CIP_PMP_RUN", True)
        self._set("DO_CIP_PUMP_RUN", True)
        flow = n(320.0, 15.0)
        self._set("AI_CIP_FLOW", flow)
        self.total_water += flow * dt_sim / 3600
        self._set("AI_CIP_WATER_TOT", self.total_water)

        if self.state == CIPState.CAUSTIC:
            self._set("DO_CIP_HEAT_EN", True)
            temp = phys.approach(self._get("AI_CIP_TT_CAUST"), self.caustic_sp, approach_rate * 3, dt_sim)
            self._set("AI_CIP_TT_CAUST", n(temp, 0.3))
            self._set("AI_CIP_COND_RET", n(45.0, 2.0))
            self._set("AI_CIP_PH_RET", n(12.5, 0.1))
            self._set("AI_ELEC_KW_CIP", n(22.0, 1.0))
        elif self.state in (CIPState.PRE_RINSE, CIPState.RINSE_MID, CIPState.FINAL_RINSE):
            self._set("DO_CIP_HEAT_EN", False)
            prog = self.step_elapsed / step_dur
            temp = phys.approach(self._get("AI_CIP_TT_CAUST"), 20.0, approach_rate * 2, dt_sim)
            self._set("AI_CIP_TT_CAUST", n(temp, 0.3))
            cond = n(0.5 + (1 - prog) * 10, 0.3)
            self._set("AI_CIP_COND_RET", max(0.5, cond))
            ph_val = n(7.0 + (1 - prog) * 5, 0.1)
            self._set("AI_CIP_PH_RET", min(12.5, ph_val))
            self._set("AI_ELEC_KW_CIP", n(2.0, 0.2))
        elif self.state == CIPState.ACID:
            self._set("AI_CIP_PH_RET", n(3.5, 0.1))
            self._set("AI_CIP_COND_RET", n(8.0, 0.5))
            self._set("AI_ELEC_KW_CIP", n(3.0, 0.3))

        if self.step_elapsed >= step_dur:
            self._next_step()


# ─────────────────────────────────────────────────────────────────────────────
# MES CALCULATED TAGS
# ─────────────────────────────────────────────────────────────────────────────

class MESCalculator(AreaSimulator):
    """
    MES KPI Calculator — Area a900_mes
    Publica em brewery/a900_mes/<TAG>

    Legado (compatibilidade)   : MES_OEE_*  MES_WATER_HL  MES_ACTIVE_ALARMS ...
    Dashboard 1 - Plant Overview : MES_PLANT_*
    Dashboard 2 - Producao & OEE : MES_MILL_*  MES_BH1_*  MES_BH2_*
                                   MES_FERM_*  MES_PKG_*
    Dashboard 3 - Utilities/Qual : MES_UTIL_*  MES_QUAL_*
    """

    def __init__(self, store, cfg, rng, fermentation_area: FermentationArea,
                 packaging_area: PackagingArea, utilities_area: UtilitiesArea) -> None:
        super().__init__(store, cfg, rng)
        self.ferm = fermentation_area
        self.pkg  = packaging_area
        self.util = utilities_area

        # OEE accumulators
        self.elapsed           = 0.0
        self.bh1_run_time      = 0.0;  self.bh1_fault_time  = 0.0
        self.bh2_run_time      = 0.0;  self.bh2_fault_time  = 0.0
        self.pkg_run_time      = 0.0;  self.pkg_fault_time  = 0.0
        self.mill_run_time     = 0.0;  self.mill_fault_time = 0.0
        self.util_fault_time   = 0.0

        # Producao acumulada
        self.batches_today     = 0
        self.batch_timer       = 0.0
        self.batch_interval    = 3600 * 8      # 1 batch por 8h sim
        self.hl_acc            = 0.0
        self.prev_keg          = 0.0
        self.prev_can          = 0.0

        # Turno (8h) e dia (24h)
        self.shift_timer       = 0.0;  self.shift_interval = 3600 * 8
        self.day_timer         = 0.0;  self.day_interval   = 3600 * 24
        self.shift_num         = 1
        self.shift_hl          = 0.0;  self.shift_hl_prev  = 0.0
        self.daily_hl          = 0.0;  self.daily_hl_prev  = 0.0
        self.daily_batches     = 0
        self.daily_alarms_max  = 0

        # Historico qualidade (ultimas 6 bateladas)
        self.q_att = [78.0 + i * 0.4 for i in range(6)]
        self.q_abv = [5.0  + i * 0.1 for i in range(6)]
        self.q_co2 = [5.3  + i * 0.02 for i in range(6)]

        # Targets configuráveis
        self.tgt_hl_shift  = 120.0
        self.tgt_oee       = 80.0
        self.tgt_water_hl  = 3.5
        self.tgt_kwh_hl    = 55.0

        # OEE coerente — cada área tem seu próprio "OEE alvo" que oscila
        # lentamente entre OEE_MIN e OEE_MAX via random walk.
        # A × P × Q são sempre derivados do OEE resultante, garantindo que
        # a multiplicação seja exata.
        self.OEE_MIN   = 77.0   # % — pior valor aceitável
        self.OEE_MAX   = 96.0   # % — melhor valor aceitável
        # Intervalo típico de cada componente (usado na decomposição)
        self.AVAIL_MIN = 0.88;  self.AVAIL_MAX = 1.00
        self.PERF_MIN  = 0.85;  self.PERF_MAX  = 0.98
        self.QUAL_MIN  = 0.95;  self.QUAL_MAX  = 0.995
        # Estado do random walk por área (começa no meio do range)
        self.oee_bh1_rw  = 87.0
        self.oee_bh2_rw  = 85.0
        self.oee_pkg_rw  = 83.0
        self.oee_mill_rw = 89.0
        # Velocidade do random walk (% por segundo de sim)
        self.OEE_DRIFT   = 0.02

    # ── helpers ────────────────────────────────────────────────────────────
    def _s(self, tag, val):    self.store.set(tag, val)
    def _g(self, tag):         return self.store.get(tag)
    def _n(self, v, s):        return phys.add_noise(v, s, self.rng)
    def _cl(self, v, lo, hi):  return max(lo, min(hi, v))

    def _count_fv_active(self):
        return sum(1 for i in range(1, 7) if self._g(f"AI_FV{i}_LT") > 100)

    def _fv_mean(self, suffix):
        vals = [self._g(f"AI_FV{i}_{suffix}") for i in range(1, 7)
                if self._g(f"AI_FV{i}_LT") > 100]
        return sum(vals) / len(vals) if vals else 0.0

    def _bbt_ready(self):
        return sum(1 for i in range(1, 3)
                   if self._g(f"AI_BBT{i}_LT") > 500 and self._g(f"AI_BBT{i}_CO2") > 4.5)

    def _oee_walk(self, current, dt_sim):
        """Random walk no range [OEE_MIN, OEE_MAX] com reversão à média."""
        mid   = (self.OEE_MIN + self.OEE_MAX) / 2
        # Força de reversão proporcional ao desvio da média
        pull  = (mid - current) * 0.0001
        step  = self.rng.gauss(0, self.OEE_DRIFT) * dt_sim + pull * dt_sim
        return self._cl(current + step, self.OEE_MIN, self.OEE_MAX)

    def _decompose_oee(self, oee_pct):
        """
        Distribui OEE% em Avail, Perf e Qual garantindo A × P × Q = OEE exato.

        Estratégia sem clamp que quebre a identidade:
          1. Sorteia Avail dentro de um range seguro
          2. Sorteia Perf dentro de um range seguro
          3. Qual = OEE / (Avail × Perf) — calculada exata
          4. Os ranges de Avail e Perf são definidos de forma que
             Qual resultante SEMPRE fique em [QUAL_MIN, QUAL_MAX]
             sem precisar de clamp extra.
        """
        oee = oee_pct / 100.0

        # ── Range de Avail e Perf que garante Qual dentro do limite ──────
        # Qual = oee / (A × P)
        # Qual_max = QUAL_MAX  →  A × P >= oee / QUAL_MAX
        # Qual_min = QUAL_MIN  →  A × P <= oee / QUAL_MIN
        ap_min = oee / self.QUAL_MAX   # produto mínimo de A×P
        ap_max = oee / self.QUAL_MIN   # produto máximo de A×P

        # Clampa ap dentro do possível dado os ranges individuais
        ap_min = self._cl(ap_min, self.AVAIL_MIN * self.PERF_MIN,
                                  self.AVAIL_MAX * self.PERF_MAX)
        ap_max = self._cl(ap_max, ap_min,
                                  self.AVAIL_MAX * self.PERF_MAX)

        # Sorteia o produto A×P alvo dentro do range permitido
        # Usa proporção do OEE para dar naturalidade (OEE alto → A×P mais alto)
        t    = (oee_pct - self.OEE_MIN) / max(1e-6, self.OEE_MAX - self.OEE_MIN)
        ap_t = ap_min + t * (ap_max - ap_min)
        ap   = self._cl(self.rng.gauss(ap_t, (ap_max - ap_min) * 0.1),
                        ap_min, ap_max)

        # Distribui ap entre Avail e Perf dentro dos ranges individuais
        # Avail recebe a maior parte (tipicamente > Perf em cervejarias)
        avail_ideal = self._cl(ap ** 0.45, self.AVAIL_MIN, self.AVAIL_MAX)
        avail       = self._cl(
            self.rng.gauss(avail_ideal, 0.005),
            self.AVAIL_MIN, self.AVAIL_MAX)

        # Perf é determinado: P = ap / A (sem clamp extra que quebre ap)
        perf = ap / max(avail, 1e-6)

        # Se Perf saiu do range individual, ajusta Avail para compensar
        # mas mantém ap fixo → Qual não muda
        if perf > self.PERF_MAX:
            perf  = self.PERF_MAX
            avail = ap / perf
        elif perf < self.PERF_MIN:
            perf  = self.PERF_MIN
            avail = ap / perf

        avail = self._cl(avail, self.AVAIL_MIN, self.AVAIL_MAX)
        perf  = ap / max(avail, 1e-6)   # recalcula para manter ap exato

        # Qual é a folga — exata por construção
        qual = oee / max(avail * perf, 1e-9)
        qual = self._cl(qual, self.QUAL_MIN, self.QUAL_MAX)

        # Ajuste final: reconstrói Perf de Qual para garantir identidade
        # A × P × Q = oee  →  P = oee / (A × Q)
        perf = oee / max(avail * qual, 1e-9)
        perf = self._cl(perf, self.PERF_MIN, self.PERF_MAX)

        return avail * 100, perf * 100, qual * 100

    def _active_alarms(self):
        return sum(1 for tag, st in self.store.all_tags().items()
                   if ("FAULT" in tag or "FLT" in tag or "PRV" in tag)
                   and isinstance(st.value, (int, float, bool)) and st.value)

    def _alarms_by_area(self):
        d = dict(milling=0, utilities=0, brewhouse=0, fermentation=0, packaging=0)
        for tag, st in self.store.all_tags().items():
            if ("FAULT" in tag or "FLT" in tag or "PRV" in tag) and st.value:
                a = st.meta.area
                if   "mill"  in a: d["milling"]      += 1
                elif "util"  in a: d["utilities"]    += 1
                elif "brew"  in a: d["brewhouse"]    += 1
                elif "ferm"  in a: d["fermentation"] += 1
                elif "pack"  in a: d["packaging"]    += 1
        return d

    def tick(self, dt_sim):
        self.elapsed     += dt_sim
        self.shift_timer += dt_sim
        self.day_timer   += dt_sim
        self.batch_timer += dt_sim
        n  = self._n
        cl = self._cl

        # ── Reset turno 8h ─────────────────────────────────────────────────
        if self.shift_timer >= self.shift_interval:
            self.shift_timer   = 0.0
            self.shift_hl_prev = self.shift_hl
            self.shift_hl      = 0.0
            self.shift_num     = (self.shift_num % 3) + 1

        # ── Reset dia 24h ──────────────────────────────────────────────────
        if self.day_timer >= self.day_interval:
            self.day_timer        = 0.0
            self.daily_hl_prev    = self.daily_hl
            self.daily_hl         = 0.0
            self.daily_batches    = 0
            self.daily_alarms_max = 0

        # ── Batch counter + atualiza historico qualidade ───────────────────
        if self.batch_timer >= self.batch_interval:
            self.batches_today += 1
            self.daily_batches += 1
            self.batch_timer    = 0.0
            og  = max(10.0, self._fv_mean("BRIX"))
            fg  = og * self.rng.uniform(0.24, 0.28)
            att = cl((og - fg) / max(0.1, og) * 100, 60, 90)
            abv = cl((og - fg) * 0.131, 3.0, 9.0)
            self.q_att = self.q_att[1:] + [att]
            self.q_abv = self.q_abv[1:] + [abv]
            self.q_co2 = self.q_co2[1:] + [n(5.3, 0.1)]

        # ── Producao acumulada ─────────────────────────────────────────────
        keg = self.pkg.keg_count
        can = self.pkg.can_count
        dhl = (max(0, keg - self.prev_keg) * 0.02
               + max(0, can - self.prev_can) * 0.000355)
        self.hl_acc   += dhl
        self.shift_hl += dhl
        self.daily_hl += dhl
        self.prev_keg  = keg
        self.prev_can  = can
        prod_hl = max(0.1, self.hl_acc)

        # ── OEE — random walk por área + decomposição coerente A×P×Q ──────
        # Cada área tem um OEE "alvo" que oscila lentamente (77–96%).
        # A, P e Q são derivados do OEE de forma que A × P × Q = OEE exato.
        # Faults do processo puxam o OEE para baixo (−2 a −5 pp por falha ativa).

        def _fault_penalty(fault_tags):
            return sum(2.5 for t in fault_tags if self._g(t))

        bh1_penalty  = _fault_penalty(["DI_MT1_RAKE_FLT", "DI_PMP_MT1_FLT"])
        bh2_penalty  = _fault_penalty(["DI_MT2_RAKE_FLT", "DI_PMP_MT2_FLT"])
        pkg_penalty  = _fault_penalty(["DI_KEG_LINE_FLT", "DI_CAN_LINE_FLT"])
        mill_penalty = _fault_penalty(["DI_MILL_A_FAULT", "DI_MILL_B_FAULT"])

        # Avança random walk e aplica penalidade de fault
        self.oee_bh1_rw  = self._oee_walk(self.oee_bh1_rw,  dt_sim)
        self.oee_bh2_rw  = self._oee_walk(self.oee_bh2_rw,  dt_sim)
        self.oee_pkg_rw  = self._oee_walk(self.oee_pkg_rw,  dt_sim)
        self.oee_mill_rw = self._oee_walk(self.oee_mill_rw, dt_sim)

        oee_bh1  = cl(self.oee_bh1_rw  - bh1_penalty,  self.OEE_MIN, self.OEE_MAX)
        oee_bh2  = cl(self.oee_bh2_rw  - bh2_penalty,  self.OEE_MIN, self.OEE_MAX)
        oee_pkg  = cl(self.oee_pkg_rw  - pkg_penalty,  self.OEE_MIN, self.OEE_MAX)
        oee_mill = cl(self.oee_mill_rw - mill_penalty, self.OEE_MIN, self.OEE_MAX)
        oee_plt  = cl((oee_bh1 + oee_bh2 + oee_pkg + oee_mill) / 4,
                       self.OEE_MIN, self.OEE_MAX)

        # Decomposição: A, P, Q individuais por área — A × P × Q = OEE exato
        avail_bh1, perf_bh1, qual_bh1   = self._decompose_oee(oee_bh1)
        avail_bh2, perf_bh2, qual_bh2   = self._decompose_oee(oee_bh2)
        avail_pkg, perf_pkg, qual_pkg    = self._decompose_oee(oee_pkg)
        avail_mill, perf_mill, qual_mill = self._decompose_oee(oee_mill)

        # Planta: média das áreas, com A×P×Q próprio coerente com oee_plt
        avail_plt, perf_plt, qual_plt    = self._decompose_oee(oee_plt)

        # Aliases legados (usados no resto do tick e nos tags legados)
        a_bh1  = avail_bh1 / 100
        a_bh2  = avail_bh2 / 100
        a_pkg  = avail_pkg / 100
        a_mill = avail_mill / 100
        a_plt  = avail_plt  / 100
        perf   = perf_plt   / 100
        qual   = qual_plt   / 100

        # ── Utilities ──────────────────────────────────────────────────────
        t_water  = self._g("AI_WATER_TOTAL")
        t_kwh    = self._g("AI_ELEC_KWH_TOT")
        t_steam  = self._g("AI_STEAM_TOTAL")
        kw_hlt   = self._g("AI_ELEC_KW_HLT")
        kw_bh    = self._g("AI_ELEC_KW_BH1") + self._g("AI_ELEC_KW_BH2")
        kw_chill = self._g("AI_ELEC_KW_CHILLER")
        kw_pack  = self._g("AI_ELEC_KW_PACK")
        kw_total = kw_hlt + kw_bh + kw_chill + kw_pack
        water_hl = t_water / prod_hl
        kwh_hl   = t_kwh   / prod_hl
        steam_hl = t_steam / 1000 / prod_hl

        # ── CO2 + Beer loss ────────────────────────────────────────────────
        co2_rec  = self.ferm.co2_recovered
        co2_con  = max(0.001, self.ferm.co2_consumed)
        co2_pct  = cl(co2_rec / co2_con * 100, 0, 100)
        loss_pct = cl((self._g("AI_BEER_LOSS_FV_BBT") + self.pkg.total_beer_loss)
                      / max(1, prod_hl * 100) * 100, 0, 20)

        # ── Qualidade ──────────────────────────────────────────────────────
        avg_att = sum(self.q_att) / 6
        avg_abv = sum(self.q_abv) / 6
        avg_co2 = sum(self.q_co2) / 6

        # ── Fermentacao ────────────────────────────────────────────────────
        fv_active   = self._count_fv_active()
        fv_avg_temp = self._fv_mean("TT")
        fv_avg_brix = self._fv_mean("BRIX")
        fv_avg_co2  = self._fv_mean("CO2_PPM")
        bbt_ready   = self._bbt_ready()

        # ── Alarmes ────────────────────────────────────────────────────────
        alarms    = self._active_alarms()
        alm_areas = self._alarms_by_area()
        self.daily_alarms_max = max(self.daily_alarms_max, alarms)

        # ── Metas turno ────────────────────────────────────────────────────
        shift_pct = cl(self.shift_hl / max(0.1, self.tgt_hl_shift) * 100, 0, 150)
        daily_pct = cl(self.daily_hl / max(0.1, self.tgt_hl_shift * 3) * 100, 0, 150)

        # ── Brewhouse legado ───────────────────────────────────────────────
        brix1 = self._g("AI_WORT1_BRIX")
        brix2 = self._g("AI_WORT2_BRIX")
        eff1  = (n(75.0, 1.5) if brix1 <= 0
                 else cl((brix1 / 13.5) * 75 + n(0, 1), 0, 100))
        eff2  = (n(74.5, 1.5) if brix2 <= 0
                 else cl((brix2 / 13.5) * 75 + n(0, 1), 0, 100))

        # ══════════════════════════════════════════════════════════════════
        # LEGADO — mantém compatibilidade com tags existentes
        # ══════════════════════════════════════════════════════════════════
        self._s("MES_OEE_BH1",       round(oee_bh1,  2))
        self._s("MES_OEE_BH2",       round(oee_bh2,  2))
        self._s("MES_OEE_PKG",       round(oee_pkg,  2))
        self._s("MES_BH_EFF_L1",     eff1)
        self._s("MES_BH_EFF_L2",     eff2)
        self._s("MES_WATER_HL",      n(water_hl, 0.1))
        self._s("MES_STEAM_HL",      n(steam_hl, 0.5))
        self._s("MES_KWH_HL",        n(kwh_hl,   0.2))
        self._s("MES_CO2_RECOVERY",  n(co2_pct,  1.0))
        self._s("MES_BEER_LOSS_PCT", n(loss_pct, 0.1))
        self._s("MES_PROD_TODAY_HL", n(prod_hl,  0.5))
        self._s("MES_ACTIVE_ALARMS", float(alarms))
        self._s("MES_BATCH_COUNT",   float(self.batches_today))

        # ══════════════════════════════════════════════════════════════════
        # DASHBOARD 1 — Plant Overview
        # Tópico: brewery/a900_mes/MES_PLANT_*
        # ══════════════════════════════════════════════════════════════════

        # Producao turno / dia / sessao
        self._s("MES_PLANT_HL_SHIFT",        n(self.shift_hl,      0.3))
        self._s("MES_PLANT_HL_SHIFT_PREV",   n(self.shift_hl_prev, 0.3))
        self._s("MES_PLANT_HL_DAILY",        n(self.daily_hl,      0.5))
        self._s("MES_PLANT_HL_DAILY_PREV",   n(self.daily_hl_prev, 0.5))
        self._s("MES_PLANT_HL_SESSION",      n(prod_hl,            0.5))
        self._s("MES_PLANT_SHIFT_NUM",       float(self.shift_num))
        self._s("MES_PLANT_SHIFT_PCT",       n(shift_pct,          0.5))
        self._s("MES_PLANT_DAILY_PCT",       n(daily_pct,          0.5))
        self._s("MES_PLANT_TARGET_HL_SHIFT", self.tgt_hl_shift)
        self._s("MES_PLANT_BATCH_TODAY",     float(self.daily_batches))
        self._s("MES_PLANT_BATCH_TOTAL",     float(self.batches_today))

        # OEE planta (A x P x Q — coerentes: A × P × Q = OEE exato)
        self._s("MES_PLANT_OEE",             round(oee_plt,  2))
        self._s("MES_PLANT_OEE_TARGET",      self.tgt_oee)
        self._s("MES_PLANT_AVAIL",           round(avail_plt,2))
        self._s("MES_PLANT_PERF",            round(perf_plt, 2))
        self._s("MES_PLANT_QUAL",            round(qual_plt, 2))

        # Alarmes por area
        self._s("MES_PLANT_ALARMS_ACTIVE",   float(alarms))
        self._s("MES_PLANT_ALARMS_DAILY",    float(self.daily_alarms_max))
        self._s("MES_PLANT_ALM_MILLING",     float(alm_areas["milling"]))
        self._s("MES_PLANT_ALM_UTILITIES",   float(alm_areas["utilities"]))
        self._s("MES_PLANT_ALM_BREWHOUSE",   float(alm_areas["brewhouse"]))
        self._s("MES_PLANT_ALM_FERM",        float(alm_areas["fermentation"]))
        self._s("MES_PLANT_ALM_PACKAGING",   float(alm_areas["packaging"]))

        # Qualidade / sustentabilidade resumo
        self._s("MES_PLANT_BEER_LOSS_PCT",   n(loss_pct, 0.1))
        self._s("MES_PLANT_CO2_RECOVERY",    n(co2_pct,  1.0))

        # ══════════════════════════════════════════════════════════════════
        # DASHBOARD 2 — Producao & OEE por area
        # Tópico: brewery/a900_mes/MES_{AREA}_*
        # ══════════════════════════════════════════════════════════════════

        # Milling
        self._s("MES_MILL_OEE",         round(oee_mill,  2))
        self._s("MES_MILL_AVAIL",       round(avail_mill,2))
        self._s("MES_MILL_A_RUN",       1.0 if self._g("DI_MILL_A_RUN")   else 0.0)
        self._s("MES_MILL_B_RUN",       1.0 if self._g("DI_MILL_B_RUN")   else 0.0)
        silo_a = self._g("AI_SILO_A_WT")
        silo_b = self._g("AI_SILO_B_WT")
        self._s("MES_MILL_SILO_A_WT",   n(silo_a, 0.5))
        self._s("MES_MILL_SILO_B_WT",   n(silo_b, 0.5))
        self._s("MES_MILL_SILO_A_PCT",  n(cl(silo_a / 5000 * 100, 0, 100), 0.3))
        self._s("MES_MILL_SILO_B_PCT",  n(cl(silo_b / 5000 * 100, 0, 100), 0.3))

        # Brewhouse Linha 1
        self._s("MES_BH1_OEE",          round(oee_bh1,  2))
        self._s("MES_BH1_AVAIL",        round(avail_bh1,2))
        self._s("MES_BH1_MT_TEMP",      n(self._g("AI_MT1_TT"),    0.2))
        self._s("MES_BH1_KT_TEMP",      n(self._g("AI_KT1_TT"),    0.2))
        self._s("MES_BH1_WORT_BRIX",    n(self._g("AI_WORT1_BRIX"),0.1))
        self._s("MES_BH1_KW",           n(self._g("AI_ELEC_KW_BH1"), 1.0))
        self._s("MES_BH1_EFF",          eff1)

        # Brewhouse Linha 2
        self._s("MES_BH2_OEE",          round(oee_bh2,  2))
        self._s("MES_BH2_AVAIL",        round(avail_bh2,2))
        self._s("MES_BH2_MT_TEMP",      n(self._g("AI_MT2_TT"),    0.2))
        self._s("MES_BH2_KT_TEMP",      n(self._g("AI_KT2_TT"),    0.2))
        self._s("MES_BH2_WORT_BRIX",    n(self._g("AI_WORT2_BRIX"),0.1))
        self._s("MES_BH2_KW",           n(self._g("AI_ELEC_KW_BH2"), 1.0))
        self._s("MES_BH2_EFF",          eff2)

        # Fermentacao resumo
        self._s("MES_FERM_FV_ACTIVE",   float(fv_active))
        self._s("MES_FERM_FV_IDLE",     float(6 - fv_active))
        self._s("MES_FERM_AVG_TEMP",    n(fv_avg_temp, 0.1))
        self._s("MES_FERM_AVG_BRIX",    n(fv_avg_brix, 0.05))
        self._s("MES_FERM_AVG_CO2",     n(fv_avg_co2,  0.2))
        self._s("MES_FERM_BBT_READY",   float(bbt_ready))

        # Fermentacao per FV (FV1-6)
        for i in range(1, 7):
            self._s(f"MES_FERM_FV{i}_ACTIVE",
                    1.0 if self._g(f"AI_FV{i}_LT") > 100 else 0.0)
            self._s(f"MES_FERM_FV{i}_BRIX",
                    n(self._g(f"AI_FV{i}_BRIX"), 0.05))
            self._s(f"MES_FERM_FV{i}_TEMP",
                    n(self._g(f"AI_FV{i}_TT"), 0.1))
            self._s(f"MES_FERM_FV{i}_PRESS",
                    n(self._g(f"AI_FV{i}_PT"), 0.01))

        # Packaging
        keg_hl = keg * 0.02
        can_hl = can * 0.000355
        self._s("MES_PKG_OEE",           round(oee_pkg,  2))
        self._s("MES_PKG_AVAIL",         round(avail_pkg,2))
        self._s("MES_PKG_KEG_RUN",       1.0 if self._g("DI_KEG_LINE_RUN") else 0.0)
        self._s("MES_PKG_CAN_RUN",       1.0 if self._g("DI_CAN_LINE_RUN") else 0.0)
        self._s("MES_PKG_KEG_COUNT",     float(keg))
        self._s("MES_PKG_CAN_COUNT",     float(can))
        self._s("MES_PKG_HL_KEG",        n(keg_hl, 0.1))
        self._s("MES_PKG_HL_CAN",        n(can_hl, 0.05))
        self._s("MES_PKG_HL_TOTAL",      n(keg_hl + can_hl, 0.1))
        self._s("MES_PKG_BEER_LOSS_PCT", n(loss_pct, 0.1))

        # ══════════════════════════════════════════════════════════════════
        # DASHBOARD 3 — Utilities & Qualidade
        # Tópico: brewery/a900_mes/MES_UTIL_*  MES_QUAL_*
        # ══════════════════════════════════════════════════════════════════

        # Consumos especificos vs metas
        self._s("MES_UTIL_WATER_HL",     n(water_hl,  0.1))
        self._s("MES_UTIL_KWH_HL",       n(kwh_hl,    0.2))
        self._s("MES_UTIL_STEAM_HL",     n(steam_hl,  0.5))
        self._s("MES_UTIL_TARGET_WATER", self.tgt_water_hl)
        self._s("MES_UTIL_TARGET_KWH",   self.tgt_kwh_hl)
        self._s("MES_UTIL_WATER_PCT",
                n(cl(water_hl / self.tgt_water_hl * 100, 0, 200), 0.5))
        self._s("MES_UTIL_KWH_PCT",
                n(cl(kwh_hl   / self.tgt_kwh_hl   * 100, 0, 200), 0.5))

        # Potencia instantanea por area
        self._s("MES_UTIL_KW_HLT",       n(kw_hlt,   0.5))
        self._s("MES_UTIL_KW_BH",        n(kw_bh,    1.0))
        self._s("MES_UTIL_KW_CHILLER",   n(kw_chill, 1.0))
        self._s("MES_UTIL_KW_PACK",      n(kw_pack,  0.5))
        self._s("MES_UTIL_KW_TOTAL",     n(kw_total, 1.5))

        # Totais acumulados na sessao
        self._s("MES_UTIL_WATER_TOTAL",  n(t_water, 0.2))
        self._s("MES_UTIL_STEAM_TOTAL",  n(t_steam, 1.0))
        self._s("MES_UTIL_KWH_TOTAL",    n(t_kwh,   0.5))

        # Status utilities
        self._s("MES_UTIL_BOILER_RUN",   1.0 if self._g("DI_BOILER_RUN")  else 0.0)
        self._s("MES_UTIL_CHILLER_RUN",  1.0 if self._g("DI_CHILLER_RUN") else 0.0)
        self._s("MES_UTIL_GLYCOL_TEMP",  n(self._g("AI_GLYCOL_TT_SUP"), 0.05))
        self._s("MES_UTIL_STEAM_PRESS",  n(self._g("AI_STEAM_PT"),       0.02))

        # Qualidade media ultimas bateladas
        self._s("MES_QUAL_AVG_ATT",      n(avg_att, 0.3))
        self._s("MES_QUAL_AVG_ABV",      n(avg_abv, 0.05))
        self._s("MES_QUAL_AVG_CO2",      n(avg_co2, 0.03))
        self._s("MES_QUAL_BEER_LOSS",    n(loss_pct, 0.1))
        self._s("MES_QUAL_CO2_RECOVERY", n(co2_pct,  1.0))

        # Qualidade inline por FV
        for i in range(1, 7):
            self._s(f"MES_QUAL_FV{i}_ABV",
                    n(cl(self.q_abv[i - 1], 0, 10), 0.05))
            self._s(f"MES_QUAL_FV{i}_BRIX",
                    n(self._g(f"AI_FV{i}_BRIX"), 0.05))