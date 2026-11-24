# Oscillator Spectre X & Spectre RF Simulation & Verification Guide

## 1. Ready-to-Run Process-Independent Testbench Suites (`assets/tb/`)

All 7 Spectre decks plug in external `models_corner.scs` + `dut_subckt.scs` (100% process-independent) and are analyzed by standalone Python scripts backed by [`common/psf_utils.py`](../../../common/psf_utils.py):

### Suite 1: Pierce Crystal Oscillator (`assets/tb/xo/`)
DUT contract: `subckt dut_xo_amp XI XO VDD VSS` (4-pin Pierce sustaining amplifier including internal DC self-bias feedback resistor `R_fb`, e.g., `1 MOhm`).

Default quartz resonator model: 24 MHz fundamental AT-cut BVD crystal (`L_m = 7.329368 mH`, `C_m = 6.0 fF`, `R_m = 40 Ohm`, `C_0 = 2.0 pF`, `C_L1 = C_L2 = 16 pF` -> `C_L = 8 pF`, `Q_u = 27,630`).

1. **[`tb_xo_neg_resistance.scs`](../assets/tb/xo/tb_xo_neg_resistance.scs)** + `analyze_xo.py neg_r` (`+preset=cx`):
   - Replaces the crystal motional arm (`L_m - C_m - R_m`) with a `1 A` AC current probe across `XI - XO_P` while preserving package shunt capacitance `C_0` and load caps `C_L1`, `C_L2`.
   - Sweeps `ac` across `1 MHz - 100 MHz` and extracts **`r_neg_at_f0_ohm`** (`-Re{Z_in(f0)}`), **`startup_margin_x`** (`|R_neg|/R_m`, target `>= 5x`), `c_eff_pf`, active negative-resistance band `[neg_r_fmin_mhz, neg_r_fmax_mhz]`, and `margin_pass`.
2. **[`tb_xo_startup_drive.scs`](../assets/tb/xo/tb_xo_startup_drive.scs)** + `analyze_xo.py startup` (`+aps`, `method=traponly`):
   - Closed-loop BVD transient with Q-scaling (`L_sim = L_m / q_scale`, `C_sim = C_m * q_scale`, default `q_scale = 20`) and a clean `20 ns` AC kick pulse (`IKICK`, zero DC disturbance). Preserves exact `R_m`, steady-state motional current `I_m,pk`, crystal drive power `P_xtal`, steady-state swings, duty cycle, and `I_DD`.
   - Extracts **`v_xi_pp_v`**, **`v_xo_pp_v`**, `i_mot_pk_ma`, **`p_xtal_uw`** (`0.5 * I_m,pk^2 * R_m`, must stay `< 100 uW`), `f_osc_mhz`, `duty_cycle_pct`, `t_startup_90pct_us` (unscaled equivalent `q_scale * t_sim`), `i_dd_ua`, and `drive_level_pass`.
3. **[`tb_xo_pullability_cload.scs`](../assets/tb/xo/tb_xo_pullability_cload.scs)** + `analyze_xo.py pullability` (`+preset=cx`):
   - 5-code `alter` sweep of symmetric load-cap bank `C_L1 = C_L2 = {10, 13, 16, 19, 22} pF` on the **full unscaled BVD crystal (`q_scale = 1`)**.
   - Inserts a `1 V` AC loop probe `VTEST` in series with `R_m - L_m - C_m` (zero DC impact because `C_m` blocks DC) and solves `Im{Z_loop(f_osc)} = 0` to `< 0.01 ppm` while simultaneously measuring per-code `startup_margin_x` (`|R_neg|/R_m`).
   - Extracts per-code `f_osc_mhz`, `df_ppm`, **`pull_range_ppm`**, `trim_step_ppm`, `pullability_ppm_per_pf`, `monotonic`, and **`worst_startup_margin_x`** at max `C_L`.
4. **[`tb_xo_pss_pnoise.scs`](../assets/tb/xo/tb_xo_pss_pnoise.scs)** + `analyze_xo.py pss_pnoise` (`+aps`):
   - True autonomous Harmonic-Balance PSS (`flexbalance=yes oscic=lin`) + relative single-sideband PM `pnoise` (`10 Hz - 1 MHz`) on the **full unscaled `Q = 27,630` quartz resonator (`q_scale = 1`)**.
   - Extracts `f_0_mhz`, `v_xo_pp_v`, `v_xi_pp_v`, `p_dc_uw`, **`pn_100hz_dbc`**, **`pn_1khz_dbc`**, **`pn_10khz_dbc`**, **`pn_100khz_dbc`**, and IEEE-1139 integrated **`j_rms_fs`** (`1 kHz - 1 MHz`).

### Suite 2: On-Chip RC Relaxation Oscillator (`assets/tb/rc_osc/`)
DUT contract: `subckt dut_rc_osc VDD EN VTRIM OUT VSS` (`VTRIM` encoded as integer-valued voltage `0..31` for 5-bit digital trim).

5. **[`tb_rc_osc_temp_vdd.scs`](../assets/tb/rc_osc/tb_rc_osc_temp_vdd.scs)** + `analyze_rc_osc.py temp_vdd` (`+preset=cx`):
   - 7-corner `alter` transient sweep: 5 temperatures (`-40, 0, 27, 85, 125 C`) at nominal `VDD` + 3 supplies (`0.9, 1.0, 1.1 * VDD`) at `27 C`.
   - Extracts `f_nom_mhz`, **`temp_drift_pct`**, **`tc_ppm_per_c`**, **`vdd_sens_pct_per_v`**, and `total_pvt_spread_pct`.
6. **[`tb_rc_osc_trim_startup.scs`](../assets/tb/rc_osc/tb_rc_osc_trim_startup.scs)** + `analyze_rc_osc.py trim_startup` (`+preset=cx`):
   - Part A: 8-code `VTRIM` sweep (`0, 4, 8, 12, 16, 20, 24, 31`) verifying `trim_range_pct`, `trim_step_pct_per_lsb`, and `monotonic`.
   - Part B: `EN` rising-edge cold startup from shutdown (`EN = 0`) measuring **`t_startup_1pct_us`**, `startup_cycles_to_1pct`, `first_cycle_err_pct`, `i_dd_ua`, and `i_shdn_na`.
7. **[`tb_rc_osc_jitter_duty.scs`](../assets/tb/rc_osc/tb_rc_osc_jitter_duty.scs)** + `analyze_rc_osc.py jitter_duty` (`+preset=cx`):
   - Long steady-state transient (`30 us`, `> 450` cycles at `16 MHz`) with thermal jitter active.
   - Extracts `n_cycles`, `f_mean_mhz`, **`period_jitter_rms_ps`**, `period_jitter_pp_ps`, **`c2c_jitter_rms_ps`**, `c2c_to_per_ratio`, **`duty_mean_pct`**, `duty_err_pct`, `t_r_ps`, `t_f_ps`, and `jitter_pass`.

---

## 2. Behavioral Verilog-A Library (`assets/va/`)

- **[`va_xo_amp.va`](../assets/va/va_xo_amp.va)**: Zero-hidden-state $C^\infty$ smooth Pierce sustaining amplifier (`gm`, `i_max`, `r_out`, `r_fb`, `c_in`, `c_out`, softplus rail clamps, `gamma_noise` thermal + `kf_flicker` $1/f$ noise) — works natively across DC, AC, TRAN, and autonomous PSS + PNOISE.
- **[`va_rc_osc.va`](../assets/va/va_rc_osc.va)**: Dual-cap switched-RC relaxation oscillator modeling residual RC temperature curvature (`tc1_rc`, `tc2_rc`), supply- and temperature-dependent comparator delay (`t_cmp0`, `delay_cancel_eff`), 5-bit conductance trim (`VTRIM`), passive RC cold-startup bias settling (`tau_start`), cap-pair duty asymmetry (`duty_asym`), and exact `@(timer)` Gaussian period jitter (`jitter_rms`).

---

## 3. Verified Reference Benchmarks (Behavioral & Open-Source Transistor Cross-Check)

All 7 testbenches, 2 fault-injection negative tests, and an open-source transistor-level 1.8 V CMOS Pierce inverter (`common/models_sky130_minimal.scs`, `L = 0.5 um` with self-limiting supply resistor `RLIM = 2.5 kOhm` + `RD = 250 Ohm`) verify cleanly with zero errors:

| Testbench / Case | Key Verified Metrics | Status |
|---|---|---|
| `xo/tb_xo_neg_resistance` (VA) | `R_neg(24 MHz) = 363.4 Ohm`, `margin = 9.08x`, `C_eff = 9.42 pF` | PASS (`>= 5x`) |
| `xo/tb_xo_neg_resistance` (Fault: starved `gm`) | `R_neg(24 MHz) = 59.7 Ohm`, `margin = 1.49x` | CAUGHT (`margin_pass = false`) |
| `xo/tb_xo_startup_drive` (VA, `q_scale=20`) | `V_XI,pp = 1.03 V`, `P_xtal = 51.0 uW`, `duty = 50.0%`, `t_90 = 723 us` | PASS (`< 100 uW`) |
| `xo/tb_xo_pullability_cload` (VA) | `f_nom = 24.0076 MHz`, `pull = 280.1 ppm`, `monotonic`, `worst margin = 5.52x` | PASS |
| `xo/tb_xo_pss_pnoise` (VA, full `Q=27.6k`) | `L(100/1k/10k/100k) = -133.4 / -153.1 / -163.3 / -163.7 dBc/Hz`, `J_rms = 61.7 fs` | PASS |
| Transistor CMOS Pierce XO cross-check (`neg_r` / `startup` / `pss_pnoise`) | `margin = 5.27x`, `P_xtal = 92.5 uW`, `L(100/1k/10k/100k) = -126.6 / -151.8 / -161.7 / -169.9 dBc/Hz`, `J_rms = 28.9 fs` (`237 uW`) | PASS |
| `rc_osc/tb_rc_osc_temp_vdd` (VA) | `f_nom = 16.00 MHz`, `temp_drift = 0.58%` (`34.9 ppm/C`), `vdd_sens = 0.97 %/V`, `PVT = 0.61%` | PASS |
| `rc_osc/tb_rc_osc_trim_startup` (VA) | `trim_range = 36.8%` (`1.19 %/LSB`, monotonic), `t_start,1% = 0.48 us` (`6` cycles), `I_dd = 60.1 uA`, `I_shdn = 50 nA` | PASS |
| `rc_osc/tb_rc_osc_jitter_duty` (VA) | `471` cycles, `sigma_per = 24.5 ps`, `sigma_c2c = 33.8 ps` (`1.38x`), `duty = 50.20%`, `t_r/t_f = 240 ps` | PASS |
| `rc_osc/tb_rc_osc_jitter_duty` (Fault: `180 ps`) | `sigma_per = 176.4 ps`, `sigma_c2c = 243.7 ps` | CAUGHT (`jitter_pass = false`) |

---

## 4. Critical Spectre Oscillator Verification Pitfalls

1. **NEVER put `ic=` on the series motional inductor `LM` of a quartz BVD crystal (`RM-LM-CM`):** Because `CM` is an open circuit at DC, forcing a non-zero DC inductor current through `LM` drives `LM` current into `gmin` (`1e-12 S`), charging the internal node `M3` to hundreds or thousands of volts at `t = 0` and creating a violent non-physical discharge spike! Always start transient crystal simulations with a brief AC current pulse `IKICK` across `XI - XO_P` (zero DC perturbation), and use Harmonic-Balance `pss` (`flexbalance=yes oscic=lin`) for steady-state RF analysis.
2. **Spectre X `+preset=cx` overrides `method=traponly` to `gear2only` and ignores `maxstep` — killing high-$Q$ crystal startup!** Gear-2 backward differentiation introduces artificial numerical damping that overwhelms a high-$Q$ quartz resonator's negative resistance, causing valid oscillators to decay to zero! Always run `tb_xo_startup_drive.scs` with **`+aps`** (which honors `method=traponly` and `maxstep <= T_0 / 40`) so numerical integration damping is strictly zero.
3. **NEVER Q-scale a crystal during `pss + pnoise`!** Q-scaling (`L_m / k`, `C_m * k`) is an indispensable speedup for transient startup envelope and drive-level checks (`tb_xo_startup_drive.scs`), but Leeson phase noise scales as $1 / Q_L^2$ ($-20 \log_{10} Q_L$). Scaling $Q$ down by $20\times$ artificially degrades phase noise by **$+26\text{ dB}$**! Always run `tb_xo_pss_pnoise.scs` at `q_scale = 1` using `flexbalance=yes oscic=lin`, which converges on full `Q > 25,000` resonators in `~1–2 s`.
4. **Always keep crystal shunt capacitance `C_0` inside `tb_xo_neg_resistance.scs`:** Omitting `C_0` measures $Z_{\text{amp}}$ rather than Vittoz's true motional-port impedance $Z_{\text{in}}$, overestimating startup margin by $30\text{–}60\%$ and completely hiding the high-$g_m$ $C_0$-shunting collapse!
5. **Check startup margin at maximum `C_L` trim code (`worst_startup_margin_x`), not just nominal `C_L`:** Because $|R_{\text{neg}}| \propto 1 / (C_0 + C_L)^2$, a Pierce core with $9\times$ margin at nominal $C_L = 8\text{ pF}$ can drop below $5\times$ at the top of its trim bank! Always check `tb_xo_pullability_cload.scs` across the entire trim range and worst-case SS/hot corner.
6. **Zero hidden states in behavioral XO models for `pss + pnoise`:** Avoid `@(cross)`, `idtmod`, or stateful `@(initial_step)` variables in Verilog-A sustaining amplifier models intended for Spectre RF `pss`; use smooth $C^\infty$ algebraic + `ddt` equations (like `va_xo_amp.va`) and replace `abs(x)` with `sqrt(x*x + eps)` so Newton-Raphson Jacobians remain exact everywhere.
7. **Always verify $\sigma_{T,\text{c2c}} / \sigma_{T,\text{per}} \approx \sqrt{2}$ in RC oscillator jitter runs:** Capture $\ge 400$ settled cycles in `tb_rc_osc_jitter_duty.scs` (`+preset=cx`). If $\sigma_{\text{c2c}} / \sigma_{\text{per}}$ deviates far below $1.414$, inspect for slow drift, power-supply ripple, or incomplete startup settling; if far above $1.414$, check alternating ping-pong cap mismatch.
