# Bandgap Reference Spectre Verification Guide

## 1. Ready-to-Run Process-Independent Testbench Suite (`assets/tb/`)

All 4 standalone Spectre decks plug in external `models_corner.scs` + `dut_subckt.scs` and are analyzed by [`../assets/tb/analyze_bandgap.py`](../assets/tb/analyze_bandgap.py):

| Testbench | DUT Contract | Analyses & Extracted Metrics |
|---|---|---|
| [`tb_bgr_temp_line.scs`](../assets/tb/tb_bgr_temp_line.scs) | `dut_bandgap VDD VREF VSS` | `dc_temp` (`-40..125°C`, step `5°C`) + `dc_line` (`0..1.4 V`): `vref_27c_v`, `vref_min/max_v`, `temp_peak_c`, exact box-method `tc_box_ppm_per_c`, `vdd_min_1pct_v`, `line_reg_mv_per_v`, `iq_27c_ua` |
| [`tb_bgr_startup.scs`](../assets/tb/tb_bgr_startup.scs) | `dut_bandgap VDD VREF VSS` | Power-up ramp `tran` (`ic VREF=0`, `t_ramp=10u` default): verifies dead-state immunity (`started_cleanly`), `vref_final_v`, `t_startup_1pct_us`, `overshoot_pct` |
| [`tb_bgr_psrr_noise.scs`](../assets/tb/tb_bgr_psrr_noise.scs) | `dut_bandgap VDD VREF VSS` | `ac` (`1 Hz..100 MHz`) + `noise` (`10 Hz..10 MHz`): `psrr_dc/10k/100k/1M_db`, `output_noise_uvrms` |
| [`tb_bgr_stb.scs`](../assets/tb/tb_bgr_stb.scs) | `dut_bandgap_stb VDD VREF LOOP_OUT LOOP_IN VSS` | `iprobe` `stb` (`1 Hz..1 GHz`): `net_negative_feedback`, `dc_loop_gain_db`, `ugf_hz`, `phase_margin_deg`, `gain_margin_db` |

### Behavioral Models (`assets/va/`)
- [`va_bandgap.va`](../assets/va/va_bandgap.va): 3-pin macro-model (`VDD, VREF, VSS`) with live `$temperature` Tsividis parabolic curvature, headroom turn-on, startup RC, PSRR, and white + $1/f$ noise.
- [`va_bgr_core.va`](../assets/va/va_bgr_core.va): 5-pin dual-feedback core model (`VDD, VREF, LOOP_OUT, LOOP_IN, VSS`) explicitly modeling the unit-PNP positive branch vs. $M\times$ PNP $+ R_1$ negative branch for `tb_bgr_stb.scs` (including `c_neg_par` and `swap_pol` fault injection).

---

## 2. Signoff Checklist & Critical Verification Pitfalls

1. **Startup across ramp-rate extremes AND steady-state zero-leakage audit:**
   - Test **fast (`100 ns`), nominal (`10 us`), and ultra-slow (`1 ms–10 ms`)** `VDD` ramps across `ss`/`-40°C`, `tt`/`27°C`, and `ff`/`125°C`, with `ic` forcing internal mirror/core nodes to the dead state (`I = 0`).
   - Also test a **brownout dip** (`VDD` drops below `vdd_min` then recovers) — some capacitor-coupled startup circuits fire once on cold boot but fail on brownout recovery!
   - Inspect startup-branch current at `t = t_stop` at `ff`/`125°C`: confirm $|I_{\text{start,leak}}| < 0.01\% \cdot I_{\text{core}}$ so startup never corrupts TC.
2. **Core loop stability (`tb_bgr_stb.scs`) across PVT + load cap:**
   - Insert `iprobe` between opamp output (`LOOP_OUT`) and the current-mirror/core drive (`LOOP_IN`) without disturbing DC bias.
   - Verify `net_negative_feedback == True`, DC loop gain $\ge 45\text{–}60\text{ dB}$, phase margin $\ge 60^\circ$, and gain margin $\ge 10\text{ dB}$ across all corners (check `ss`/`-40°C` and `ff`/`125°C` where $r_e = V_T/I_b$ and $g_m$ shift!).
3. **Monte Carlo mismatch (`N >= 200`) at `-40°C`, `27°C`, and `125°C`:**
   - Measure both untrimmed $3\sigma$ $V_{\text{ref}}$ accuracy and $3\sigma$ box-method TC.
   - Verify that opamp offset $V_{\text{os}}$ dominates (if not, check BJT/resistor sizing) and that your trim range covers $3\sigma$ mismatch + worst-case global process corners (`ss`/`ff` + resistor corners).
4. **PSRR & Output Noise vs. Downstream Consumer:**
   - Confirm low-frequency PSRR ($\ge 60\text{ dB}$) and high-frequency supply rejection (add an RC low-pass filter on `VREF` or cascode the PMOS mirrors if supply ripple couples into a sensitive LDO/ADC/PLL).
   - Integrate `noise` across the downstream system bandwidth (e.g., `10 Hz` to LDO GBW or ADC $f_s/2$) and ensure BGR noise is well below the system floor.
