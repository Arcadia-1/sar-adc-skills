# LDO Spectre Verification Guide

## 1. Ready-to-Run Process-Independent Testbench Suite (`assets/tb/`)

All 9 standalone Spectre testbenches plug in external `models_corner.scs` + `dut_subckt.scs` (`subckt dut_ldo VDD VREF VOUT FB_IN VSS`, plus `subckt dut_ldo_en VDD VREF EN VOUT FB_IN VSS` for enable/shutdown decks) and are parsed by [`../assets/tb/analyze_ldo.py`](../assets/tb/analyze_ldo.py):

### Core Static, Stability, AC & Transient Suite (4 Decks)
1. **`tb_ldo_dc_reg_dropout.scs`** (`analyze_ldo.py dc_reg`) — Two DC sweeps in one run:
   - `dc_line`: sweeps `VDD` across dropout and regulation at `iload_max` $\to$ extracts **Dropout Voltage $V_{\text{DO}}$** (where `VOUT` falls $2\%$ below nominal) and **Line Regulation** $[\text{mV/V}]$.
   - `dc_load`: sweeps `ILOAD` from `iload_min` to `iload_max` at nominal `vdd_in` $\to$ extracts **Load Regulation** $[\text{mV/mA}]$, **Quiescent Current $I_Q$**, and peak current efficiency $\eta_I$.
2. **`tb_ldo_stb.scs`** (`analyze_ldo.py stb`) — Inserts `IPRB (VOUT FB_IN) iprobe` for exact Spectre `stb` loop stability (`T0`, `UGF`, `PM`, `GM`). Always check both `iload_min` and `iload_max` across PVT corners.
3. **`tb_ldo_psrr_zout_noise.scs`** (`analyze_ldo.py psrr_zout_noise`) — Two matched closed-loop replicas in one fast run:
   - Replica 1 (`ac` `mag=1` on `VDD` + `noise`): extracts **$\text{PSRR}(f)$** at DC, `100 kHz`, `1 MHz`, `100 MHz`, worst-case minimum, plus **integrated output RMS noise** (`10 Hz`–`100 MHz`).
   - Replica 2 (`ac` `1 A` AC current probe at `VOUT_Z`): extracts closed-loop output impedance **$|Z_{\text{out}}(f)|$** (DC, `1 MHz`, peak $|Z_{\text{out}}|$).
4. **`tb_ldo_load_line_tran.scs`** (`analyze_ldo.py tran`) — Sequential **Load-Step** (`iload_lo -> iload_hi -> iload_lo`) and **Line-Step** (`vdd_lo -> vdd_hi`) transient $\to$ undershoot, overshoot, and dynamic line-step glitch.

### Industrial Tapeout Signoff Extension Suite (5 Decks)
5. **`tb_ldo_startup_inrush.scs`** (`analyze_ldo.py startup`) — Drives `EN` rising (`0 -> VDD`) and falling (`VDD -> 0`) into `CLOAD` + `RESR` with a resistive load `RLOAD` (never an ideal `isource`, which would pull `VOUT < 0` when disabled!):
   - Extracts `t_start_90pct_us`, `t_settle_1pct_us`, `overshoot_mv` / `overshoot_pct`, `monotonic_startup`, **peak capacitive inrush current `i_inrush_peak_ma`**, and active discharge fall time `t_discharge_10pct_us`.
   - **Failure mode caught:** Disabling or under-sizing soft-start (`t_ss` too small) slams the pass transistor into current limit (`i_inrush_peak_ma` surges $>2\times$) and causes error-amplifier gate-windup overshoot when `VOUT` reaches `VREF`.
6. **`tb_ldo_ocp_foldback.scs`** (`analyze_ldo.py ocp`) — Combines a logarithmic DC load-resistance sweep (`0.5 Ohm .. 1 kOhm`) with a transient hard-short pulse (`0.5 Ohm` via a Spectre `relay` switch, then released back to nominal load):
   - Extracts peak knee current **`i_lim_peak_ma`**, foldback short-circuit current **`i_short_ma`**, **`foldback_ratio = i_short / i_lim_peak`**, latch-up-free recovery flag **`vout_recover_ok`**, and **`t_recover_us`**.
   - **Foldback latch-up rule:** When powering constant-current loads, keep $I_{\text{sc}} > I_{\text{load,max}}$; otherwise the constant-current load intersects the foldback branch near `VOUT = 0` and creates a stable latched-off state that prevents recovery.
7. **`tb_ldo_stb_esr_grid.scs`** (`analyze_ldo.py esr_grid`) — Executes a 9-point `alter` + `stb` matrix spanning **3 loads (`10 uA`, `1 mA`, `10 mA`) $\times$ 3 ESR values (`5 mOhm`, `200 mOhm`, `5 Ohm`)**:
   - Maps both boundaries of the classic external-cap **ESR stability tunnel**:
     - **Low-ESR boundary (`5 mOhm` / ceramic MLCC without series damping):** $f_{z,\text{ESR}} = \frac{1}{2\pi R_{\text{ESR}} C_L}$ sits far above UGF and fails to cancel the pass-gate pole $f_{p2}$, collapsing PM below $30^\circ$ at heavy load.
     - **Nominal ESR tunnel (`200 mOhm`):** $f_{z,\text{ESR}}$ boosts phase near UGF, maintaining $\text{PM} \ge 45^\circ\text{–}60^\circ$ across all three decades of load current.
     - **High-ESR boundary (`5 Ohm` / aged or cold-temperature tantalum cap):** $f_{z,\text{ESR}}$ drops too low, flattening loop gain and pushing UGF past the error-amp internal pole $f_{p3}$, again collapsing PM below $30^\circ$.
   - Extracts per-point `T0_db`, `ugf_mhz`, `pm_deg`, `gm_db`, global `pm_min_deg`, `worst_corner`, and explicit low/nominal/high ESR tunnel summaries.
8. **`tb_ldo_dropout_tran.scs`** (`analyze_ldo.py dropout_tran`) — Two large-signal dynamic supply transients via `alter`:
   - `tran_brownout`: Deep `VDD` brown-out dip down into triode dropout (`1.2 V -> 0.85 V -> 1.2 V`), capturing dropout tracking floor **`vout_min_dip_v`**, pass-gate windup recovery overshoot **`vout_recover_overshoot_mv`** upon leaving triode, and **`t_recover_1pct_us`**.
   - `tran_ripple`: Large-signal periodic `100 mVpp` sinusoidal supply ripple (`f_rip = 50 kHz`), directly measuring large-signal dynamic PSRR **`dyn_psrr_db`** without small-signal linearization assumptions.
9. **`tb_ldo_temp_shdn.scs`** (`analyze_ldo.py temp_shdn`) — Three DC signoff sweeps in one run:
   - `dc_temp`: Full `-40..125 C` active sweep $\to$ `vout_27c_v` and box temperature coefficient **`tc_ppm_per_c`**.
   - `dc_iq_load`: Multi-decade `10 uA .. 10 mA` load sweep $\to$ `iq_light_ua`, `iq_full_ua`, `current_eff_light_pct`, and `current_eff_full_pct`.
   - `dc_shdn_temp`: Disabled (`EN = 0`, `ILOAD = 0`) temperature sweep `-40..125 C` $\to$ **`i_shdn_27c_na`** and high-temperature leakage **`i_shdn_125c_ua`**.

---

## 2. Signoff Pass Criteria Checklist

| Metric | Typical Target | Corner to Watch |
|---|---|---|
| Phase Margin (`stb` / `esr_grid`) | $\ge 60^\circ$ nom, $\ge 45^\circ$ worst-case inside ESR tunnel (catch $< 30^\circ$ walls) | Capless: **lightest load $I_{\text{min}}$**, max $C_L$, `ss`/high-$T$; External-cap: **$I_{\text{max}}$ at $R_{\text{ESR,min}}$ & $R_{\text{ESR,max}}$** |
| Gain Margin (`stb` / `esr_grid`) | $\ge 10\text{ dB}$ | Heavy load $I_{\text{max}}$, `ff`/low-$T$, low-ESR corner |
| Dropout $V_{\text{DO}}$ (`dc_reg`) | $\le V_{\text{in,min}} - V_{\text{out}}$ | Heavy load $I_{\text{max}}$, `ss` / high-$T$ |
| Load/Line Regulation (`dc_reg`) | $< 1\text{–}5\text{ mV/mA}$, $< 5\text{ mV/V}$ | `ss`, low `VDD` (pass device near triode) |
| Load-Step Undershoot (`tran`) | $< 5\%\text{–}10\%$ of $V_{\text{out}}$ (or $< 0.5\text{ LSB}$ for ADC ref) | Fastest edge `tr`, $I_{\text{min}} \to I_{\text{max}}$ |
| Startup Inrush & Overshoot (`startup`) | Monotonic, overshoot $< 1\%\text{–}2\%$, $I_{\text{inrush}} < I_{\text{lim}}$ | Max $C_L$, fast `EN` edge, `ff`/low-$T$, min `t_ss` |
| Active Discharge (`startup`) | $t_{\text{disch,10\%}} \le$ system sequencing budget | Max $C_L$, `ss`/high-$T$ (highest $R_{\text{disch}}$) |
| OCP Foldback & Recovery (`ocp`) | $I_{\text{sc}} < I_{\text{lim,peak}}$ (e.g. $0.3\text{–}0.5\times$), clean recovery (`vout_recover_ok`) | `ff`/low-$T$ (max short power); `ss`/high-$T$ (latch-up check) |
| Brown-Out Recovery & Dyn PSRR (`dropout_tran`) | Overshoot $< 3\%\text{–}5\%$, $\text{PSRR}_{\text{dyn}}$ meets ripple budget | Fast `VDD` recovery edge, heavy load, `ff`/low-$T$ |
| Temp Drift & Shutdown Leakage (`temp_shdn`) | $\text{TC} < 30\text{–}50\text{ ppm/}^\circ\text{C}$, $I_{\text{shdn}}(125^\circ\text{C}) < 1\text{–}10\;\mu\text{A}$ | `ff` / **`125 C`** (exponential subthreshold & junction leakage!) |
