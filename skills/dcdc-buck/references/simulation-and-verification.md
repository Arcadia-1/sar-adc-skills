# Synchronous Buck Spectre X Verification Guide

## 1. Ready-to-Run Process-Independent Testbench Suite (`assets/tb/`)

All 8 standalone Spectre X testbenches run out-of-the-box with the bundled Verilog-A models (`../va/`) using `spectre +preset=cx +mt=2 -format psfascii <deck.scs>`, and every PSF ASCII output is parsed by [`../assets/tb/analyze_buck.py`](../assets/tb/analyze_buck.py):

1. **`tb_buck_eff_ccm_dcm.scs`** (`analyze_buck.py efficiency`) — 4-load `alter` + `tran` sweep (`20 mA`, `100 mA`, `300 mA`, `500 mA`) spanning light-load **DCM** (with ZCD) to full-load **CCM**:
   - Integrates exact input power $P_{\text{in}} = \frac{1}{N T_{\text{sw}}} \int V_{\text{in}} (-I_{\text{VSUP}})\,dt$ and output power $P_{\text{out}} = \frac{1}{N T_{\text{sw}}} \int V_{\text{out}} I_{\text{load}}\,dt$ over an exact integer number of steady-state switching cycles (`N = 10`).
   - Extracts per-load `vout_avg_v`, `p_in_mw`, `p_out_mw`, `p_loss_mw`, **`eff_pct`**, `il_min_ma`, `il_max_ma`, **`mode` (`DCM` vs `CCM`)**, plus summary `eff_peak_pct`, `eff_light_load_pct`, and `eff_full_load_pct`.
2. **`tb_buck_ripple_sw.scs`** (`analyze_buck.py ripple`) — High-resolution steady-state CCM transient (`+preset=cx`, `maxstep=2n`, nominal `300 mA` load) with damped input power-loop parasitic inductance (`l_par = 1 nH`):
   - Extracts `vout_avg_v`, **`vout_ripple_pp_mv`**, `il_avg_ma`, **`il_ripple_pp_ma`** cross-checked directly against analytical $\Delta I_L = \frac{V_{\text{out}}(1 - D)}{L f_{\text{sw}}}$ (`il_ripple_theory_ma`, `il_ripple_err_pct`), `duty_cycle_meas` vs. `duty_cycle_ideal`, **`sw_overshoot_v`** (above `VIN`), and **`sw_undershoot_v`** (below `VSS` body-diode clamp).
3. **`tb_buck_softstart_inrush.scs`** (`analyze_buck.py softstart`) — Cold enable startup (`EN: 0 -> V_in` at `5 us`) from `VOUT = 0`, `I_L = 0` into a resistive load (never an ideal `isource`):
   - Extracts `vout_final_v`, `t_start_90pct_us`, `t_settle_1pct_us`, **`il_inrush_peak_ma`**, **`vout_overshoot_mv`** (`overshoot_pct`), and cycle-averaged **`monotonic_startup`**.
   - **Fault-injection check:** Shortening `t_ss` from `80 us` to `5 us` drives inductor inrush $> 2.5\times$ nominal directly into the `850 mA` OCP clamp and increases output overshoot $> 4\times$.
4. **`tb_buck_load_line_tran.scs`** (`analyze_buck.py tran`) — Sequential dynamic load step (`50 mA [DCM] -> 400 mA [CCM] -> 50 mA [DCM]` in `1 us`) followed by input line step (`3.3 V -> 4.2 V -> 3.3 V` in `2 us`):
   - Extracts `vout_nom_v`, **`load_undershoot_mv`**, **`load_overshoot_mv`**, **`t_recover_load_us`** ($\pm 1\%$ settling), and **`line_step_dev_mv`**.
5. **`tb_buck_loop_stb.scs`** (`analyze_buck.py stb`) — Continuous state-space averaged PCMC Buck (`va_buck_avg_model.va`) with `IPRB (VOUT FB_TOP) iprobe` `stb` swept via `alter` across **4 $V_{\text{in}} \times I_{\text{load}}$ CCM corners** (`2.7 V / 100 mA`, `3.3 V / 100 mA`, `3.3 V / 500 mA`, `4.5 V / 500 mA`):
   - Extracts per-corner `dc_loop_gain_db`, **`f_crossover_khz`**, **`phase_margin_deg`**, **`gain_margin_db`**, plus worst-case `pm_min_deg`, `gm_min_db`, and `stb_pass`.
   - **Fault-injection check:** Misplacing the Type-II zero (`r_comp=50 c_comp=500p c_hf=100p`) collapses worst-case phase margin below $10^\circ$ (`stb_pass = false`).
6. **`tb_buck_ocp_short.scs`** (`analyze_buck.py ocp`) — Steady-state `300 mA` operation hit by a hard `0.2 Ohm` output short via a Spectre `relay` (`t = 40..80 us`) and released back to `4.0 Ohm`:
   - Extracts **`il_ocp_peak_ma`** (verifying cycle-by-cycle clamping at `i_ocp`), **`vout_short_mv`**, latch-up-free **`vout_recover_ok`**, and **`t_recover_us`**.
7. **`tb_buck_psrr_noise.scs`** (`analyze_buck.py psrr_spur`) — Two-part run combining:
   - (a) `ac_psrr`: Small-signal averaged input-to-output audio susceptibility `PSRR(f)` (`100 Hz – 10 MHz`), extracting `psrr_dc_db`, `psrr_10khz_db`, **`psrr_fc_min_db`**, `f_psrr_min_khz`, and `psrr_1mhz_db`.
   - (b) `tran_spur`: Coherently strobed switching `VOUT_SW` transient (`f_s = 64 MHz`, `strobeperiod = 15.625 ns`, `N = 1024` = 32 exact cycles after settling) extracting zero-leakage FFT tones **`spur_fsw_dbv`/`mvrms`** (`2 MHz`), **`spur_2fsw_dbv`/`mvrms`** (`4 MHz`), and `vout_ripple_rms_mv`.
8. **`tb_buck_deadtime_shoot.scs`** (`analyze_buck.py deadtime`) — Open-loop half-bridge sweep via `alter` across **3 dead-time regimes** (`-5 ns` overlap shoot-through, `+10 ns` optimal non-overlapping, `+60 ns` excessive body-diode freewheeling) with `t_stop = 100 us` (ensuring $> 5$ open-loop $LC$ settling time constants so zero capacitor charging energy corrupts $P_{\text{loss}}$!):
   - Extracts per-regime `i_shoot_peak_ma`, `p_sw_loss_mw`, `eff_pct`, `sw_min_v`, and `deadtime_safe`.
   - Plug-and-play `subckt dut_halfbridge (VIN SW GH GL VSS)` contract lets you drop in a real transistor-level BSIM4 / PDK CMOS half-bridge + tapered gate drivers (including realistic `ad`/`as`/`pd`/`ps` diffusion areas for true silicon body-diode conduction and junction capacitance) to cross-verify shoot-through spikes and dead-time efficiency penalties directly on silicon FET models.

---

## 2. Signoff Pass Criteria & Corner Priorities

| Metric | Typical Signoff Target | Worst-Case PVT / Operating Corner |
|---|---|---|
| **Peak & Full-Load Efficiency** (`efficiency`) | $\eta_{\text{peak}} \ge 88\text{–}93\%$, $\eta_{\text{full}} \ge 85\text{–}90\%$ | `ss` / high-$T$ (highest $R_{\text{on}}$ & $R_{\text{DCR}}$); light load at high $V_{\text{in}}$ |
| **Output Ripple $\Delta V_{\text{out,pp}}$** (`ripple`) | $< 1\%\text{–}2\%$ of $V_{\text{out}}$ (e.g., $< 10\text{–}20\text{ mV}_{\text{pp}}$) | Max $V_{\text{in}}$ (max $\Delta I_L$), min $C_{\text{out}}$ (DC bias derating!), max $R_{\text{ESR}}$ (cold $T$) |
| **SW Overshoot / Undershoot** (`ripple`) | $V_{\text{SW,max}} < V_{\text{BV,FET}}$, $V_{\text{SW,min}} > -1.0\text{ V}$ | Max $V_{\text{in}}$, max $I_{\text{load}}$, `ff`/low-$T$ (fastest `di/dt`), max package $L_{\text{par}}$ |
| **Soft-Start Inrush & Overshoot** (`softstart`) | Monotonic, overshoot $< 2\%$, $I_{\text{inrush}} < 0.7 \, I_{\text{OCP}}$ | Max $C_{\text{out}}$, min $t_{\text{ss}}$, light load, `ff`/low-$T$ |
| **Load-Step Droop / Overshoot** (`tran`) | $\Delta V < \pm 3\%\text{–}5\%$ of $V_{\text{out}}$ | Min $C_{\text{out}}$, max $L$, max $R_{\text{ESR}}$, `ss`/high-$T$ (lowest $g_{m,\text{ea}}$) |
| **Loop Phase & Gain Margin** (`stb`) | $\text{PM} \ge 50^\circ\text{–}60^\circ$ nom ($\ge 45^\circ$ WC), $\text{GM} \ge 10\text{ dB}$ | Min $V_{\text{in}}$ (highest $D$, worst Ridley $Q_p$) & max $V_{\text{in}}$; min/max $C_{\text{out}}$ & $R_{\text{ESR}}$ |
| **OCP Hard Short & Recovery** (`ocp`) | $I_{L,\text{pk}} \le I_{\text{OCP,max}}$, clean `vout_recover_ok` | Max $V_{\text{in}}$, `ff`/low-$T$ (test $t_{\text{LEB}}$ runaway limit!) |
| **PSRR & Switching Spur** (`psrr_spur`) | Meets downstream analog/RF rail spur mask | Min $V_{\text{in}}$ (min PSRR), max $V_{\text{in}}$ (max switching spur) |
| **Dead-Time Safety** (`deadtime`) | `deadtime_safe = true` (zero shoot-through) | `ff`/low-$T$ (fastest turn-on, shoot-through); `ss`/high-$T$ (longest dead-time, body-diode loss) |

---

## 3. Common Verification Pitfalls

1. **Non-integer-cycle power averaging:** Computing efficiency over an arbitrary window (`41.23 us .. 45.0 us`) includes fractional switching cycles and corrupts $\eta$ by $\pm 5\%$. Always integrate over an exact integer multiple of $T_{\text{sw}}$ after full settling.
2. **Unsettled open-loop $LC$ ringing in dead-time sweeps:** Measuring $P_{\text{in}} - P_{\text{out}}$ while `VOUT` is still drifting by even $10\text{ mV}$ over $5\;\mu\text{s}$ adds/subtracts $C_{\text{out}} V_{\text{out}} (dV/dt) \approx 20\text{–}40\text{ mW}$ of false loss. Always settle for $\ge 5 \tau_{LC}$ (e.g., $100\;\mu\text{s}$).
3. **Missing diffusion area `ad`/`as` in BSIM4 power-FET netlists:** Leaving `ad = as = 0` disables the MOSFET drain-bulk body diode in SPICE/Spectre, causing `SW` to fly to unrealistically large negative voltages during dead-time instead of clamping at $-0.75\text{ V}$.
4. **Ideal `isource` load during cold soft-start:** An ideal current sink pulls `VOUT` negative before `EN` rises; always use a passive resistive load `RLOAD` (or gated load) for startup and shutdown verification.
5. **Non-coherent FFT sampling of switching ripple:** Use `strobeperiod = T_sw / M` with `strobeoutput=strobeonly` and `extract_uniform_strobe()` so $f_{\text{sw}}$ and its harmonics land on exact FFT bins with zero spectral leakage.
