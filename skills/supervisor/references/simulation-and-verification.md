# Supervisor (POR/BOR & Temperature Sensor / TSD) Spectre X Verification Guide

End-to-end, process-independent Spectre X (`+preset=cx`) verification methodology for Power-On Reset / Brown-Out Reset supervisors (`assets/tb/por_bor/`, 4 decks) and On-Chip Temperature Sensor / Thermal Shutdown blocks (`assets/tb/temp_sensor/`, 3 decks), backed by zero-dependency PSF ASCII analyzers sharing [`common/psf_utils.py`](../../../common/psf_utils.py).

## 1. DUT Interface Contracts

Every testbench includes external `models_corner.scs` (your foundry corner, or repo-root [`common/models_generic_bsim4.scs`](../../../common/models_generic_bsim4.scs) / [`common/models_sky130_minimal.scs`](../../../common/models_sky130_minimal.scs) for open-source smoke verification) and `dut_subckt.scs`:

```spectre
// Suite 1: 4-pin POR/BOR Supervisor (assets/tb/por_bor/)
//   - VTRIM: analog 3-bit code 0..7 (nominal code = 3 -> V_POR+ = 1.05 V)
//   - RSTB : active-low reset output (0 V = asserted, VDD = released)
subckt dut_por_bor VDD VTRIM RSTB VSS
    // instantiate transistor POR/BOR (or wrap ../../va/va_por_bor.va)
ends dut_por_bor

// Suite 2: 7-pin On-Chip Temperature Sensor + TSD (assets/tb/temp_sensor/)
//   - CHOP   : dynamic offset chopping control (0 V = OFF, VDD = ON)
//   - VPTAT  : amplified PTAT voltage (alpha * delta-V_BE)
//   - VBE    : CTAT base-emitter (or subthreshold V_GS) voltage
//   - VTEMP  : ratiometric calibrated temperature output (~2.0 mV/K)
//   - TSD_OUT: active-high thermal shutdown alarm (0 V = normal, VDD = tripped)
subckt dut_tsens VDD CHOP VPTAT VBE VTEMP TSD_OUT VSS
    // instantiate transistor sensor + TSD (or wrap ../../va/va_temp_sensor_tsd.va)
ends dut_tsens
```

## 2. Suite 1: POR / BOR Testbenches (`assets/tb/por_bor/`)

Run with `spectre +preset=cx +mt=2 -format psfascii -raw <name>.raw <deck>.scs` and analyze with `analyze_por_bor.py`:

| # | Deck | Analyzer Subcommand | Stimulus & Key Extracted Metrics |
|---|---|---|---|
| 1 | `tb_por_thresholds_hys.scs` | `thresholds` | Slow triangular $V_{DD}$ ramp ($0 \to 1.8\text{ V}$ in $10\text{ ms}$, $2\text{ ms}$ flat plateau, $1.8 \to 0\text{ V}$ in $10\text{ ms}$). Extracts `v_por_rise_v`, `v_por_fall_v`, `v_hys_mv`, `max_glitch_low_vdd_mv`, `n_rise_edges`, plateau `iq_na`, `hys_pass`, `low_vdd_clamp_pass`. |
| 2 | `tb_por_ramp_rates.scs` | `ramps` | 3-decade `alter`-switched cold-boot ramps: `10 us` (`tran_fast`), `200 us` (`tran_med`), `4 ms` (`tran_slow`). Extracts per-ramp `v_release_v`, `t_rst_delay_us`, `low_vdd_glitch_mv`, `n_rise_edges`, `clean_release`, plus `t_rst_spread_us` & `all_clean_release`. |
| 3 | `tb_por_glitch_immunity.scs` | `glitch` | Regulated $1.8\text{ V}$ supply hit by 4 negative dips to $0.6\text{ V}$ of widths `0.5 us`, `1.5 us`, `5.0 us`, `15.0 us`. Extracts per-pulse `triggered`, `min_rstb_over_vdd`, `t_rst_recover_us`, `immune_short`, `detect_long`, `glitch_filter_pass`. |
| 4 | `tb_bor_multi_level.scs` | `bor_levels` | `alter` sweep over all 8 programmable 3-bit codes (`vtrim_code = 0..7`) with full triangle ramp per code. Extracts `v_bor_rise_v[0..7]`, `v_bor_fall_v[0..7]`, `v_hys_mv[0..7]`, `step_mv_per_lsb`, `dnl_max_lsb`, `inl_max_lsb`, `monotonic`, `iq_mean_na`. |

## 3. Suite 2: Temperature Sensor & TSD Testbenches (`assets/tb/temp_sensor/`)

Analyze with `analyze_temp_sensor.py`:

| # | Deck | Analyzer Subcommand | Stimulus & Key Extracted Metrics |
|---|---|---|---|
| 5 | `tb_tsens_linearity.scs` | `linearity` | Full $-40..125^\circ\text{C}$ (`step=1 C`) DC temperature sweep with `CHOP = VDD`. Extracts `vbe_slope_mv_per_c`, `vptat_slope_mv_per_c`, `sens_mv_per_c`, `err_raw_max_abs_c`, `err_1pt_27c_max_abs_c`, `err_2pt_max_abs_c`, `err_2pt_half_span_c` ($\pm^\circ\text{C}$ bow), `iq_27c_ua`. |
| 6 | `tb_tsens_psrr_noise.scs` | `psrr_noise` | 4-stage signoff deck: local $25..29^\circ\text{C}$ slope (`dc_chop1`), $V_{DD} = 1.62..1.98\text{ V}$ sweep (`dc_vdd`), $1\text{ Hz}..100\text{ kHz}$ `noise_chop1`, then `alter` `CHOP = 0` (`dc_chop0` + `noise_chop0`). Extracts `supply_sens_c_per_v`, `psrr_dc_db`, `temp_noise_mk_rms`, `err_unchopped_c` vs. `err_chopped_c`, `chop_suppression_x` ($> 10\times$), `chop_pass`. |
| 7 | `tb_tsens_thermal_alarm.scs` | `tsd` | Consecutive rising (`25 -> 160 C`, `step=0.25`) and falling (`160 -> 25 C`, `step=-0.25`) native Spectre DC sweeps with `prevoppoint=yes`. Extracts `t_trip_c`, `t_release_c`, `t_hys_c`, `tsd_tripped`, `tsd_released`, `hys_pass`. |

## 4. Common Spectre Verification Traps & Best Practices

1. **Always use relative `RSTB - 0.5*VDD` crossings for POR/BOR thresholds.**
   A fixed threshold (such as `0.9 V`) completely misses low BOR codes (`V_BOR+ = 0.90 V` or `0.85 V`) because `RSTB` only swings up to the instantaneous `VDD` at the moment of release. Evaluating `RSTB - 0.5 * VDD = 0` (for `VDD >= 0.25 V`) works identically across all 8 BOR codes and CMOS rail-tracking outputs.
2. **Audit the final rising edge (`rise_x[-1]`) so cold-boot glitches do not masquerade as `V_POR+`.**
   If a faulty POR has a `380 mV` low-$V_{DD}$ bump at `VDD = 0.45 V`, that glitch crosses `0.5 * VDD`. Anchoring `V_POR+` on the final release edge and scanning `[0.02 V, V_POR+ - 50 mV]` captures the true `380 mV` peak and reports `n_rise_edges > 1`, failing `low_vdd_clamp_pass` unambiguously.
3. **Distinguish rail tracking from true reset assertion during glitch immunity tests.**
   During a rejected negative $V_{DD}$ dip ($1.8\text{ V} \to 0.6\text{ V}$), a non-triggered active-high CMOS driver pulls `RSTB` along with `VDD` down to `0.6 V` (`RSTB / VDD ~ 1.0`), whereas a triggered reset actively clamps `RSTB` to `0 V` (`RSTB / VDD ~ 0.0`) and holds it low across the `t_rst` recovery timer. Evaluating `min(RSTB / max(VDD, 0.1)) < 0.5` cleanly separates rejected dips from real brown-out assertions.
4. **Measure quiescent $I_q$ on a flat DC $V_{DD}$ plateau, never during a ramp.**
   On a fast ramp, displacement current $C_L \cdot dV_{DD}/dt$ through decoupling and load capacitance easily dwarfs a $150\text{ nA}$ nano-power supervisor. Both `tb_por_thresholds_hys.scs` and `tb_bor_multi_level.scs` insert a flat `VDD = vdd_nom` plateau so `analyze_por_bor.py` extracts pure static `iq_na`.
5. **Preserve bistable hysteresis in DC thermal sweeps with `prevoppoint=yes`.**
   In `tb_tsens_thermal_alarm.scs`, starting `dc_up` at $25^\circ\text{C}$ (unique root `TSD_OUT = 0`) and `dc_dn` at $160^\circ\text{C}$ (unique root `TSD_OUT = VDD`) with `prevoppoint=yes` tracks both branches of a hysteretic thermal comparator natively through Spectre's `temp` parameter—no synthetic thermal input port is required, so the exact same deck signs off transistor-level TSD circuits.
6. **Account for timer-induced apparent threshold shift on fast ramps.**
   A release delay $t_{\text{rst}}$ shifts apparent release voltage during a linear ramp of slew rate $S = dV_{DD}/dt$ by $\Delta V_{\text{app}} = S \cdot t_{\text{rst}}$. Use slow ramps ($S \cdot t_{\text{rst}} < 5\text{ mV}$, e.g., $10\text{ ms}$ ramp for $t_{\text{rst}} = 20\,\mu\text{s}$) when characterizing static $V_{\text{POR}+}$, and use `tb_por_ramp_rates.scs` to verify `t_rst` stability across decades.

## 5. Reference Verification Matrix & Negative-Test Benchmarks

Verified live with Spectre X (`+preset=cx`) across behavioral Verilog-A models (`va_por_bor.va`, `va_temp_sensor_tsd.va`), three deliberate fault-injection negative tests, and two transistor-level open-source BSIM4.5 CMOS cross-checks:

| Test Case | DUT Configuration | Key Verified Metrics | Expected Verdict |
|---|---|---|---|
| **TB1 (`thresholds`)** | `va_por_bor` (code 3) | `V_POR+ = 1.054 V`, `V_POR- = 0.950 V`, `V_hys = 104.1 mV`, `glitch = 0.0 mV`, `I_q = 150.2 nA` | `pass = true` |
| **TB1 (Transistor Cross-Check)** | 1.8 V CMOS hysteretic POR (`models_sky130_minimal.scs`) | `V_POR+ = 1.373 V`, `V_POR- = 1.293 V`, `V_hys = 80.0 mV`, `glitch = 0.02 mV`, `I_q = 933.7 nA` | `pass = true` |
| **TB1 (Negative Fault)** | `va_por_bor` (`fault_low_vdd_glitch=1`) | `max_glitch_low_vdd_mv = 379.0 mV`, `n_rise_edges = 2` | `low_vdd_clamp_pass = false` |
| **TB2 (`ramps`)** | `va_por_bor` (`10 us` / `200 us` / `4 ms`) | `t_rst = 20.17 / 20.20 / 20.26 us` (`spread = 0.09 us`), `glitch = 0.0 mV` | `all_clean_release = true` |
| **TB3 (`glitch`)** | `va_por_bor` (`tau_glitch = 3.5 us`) | `0.5 us` & `1.5 us` rejected (`RSTB/VDD = 0.94`); `5 us` & `15 us` assert + `20.1 us` recovery | `glitch_filter_pass = true` |
| **TB3 (Negative Fault)** | `va_por_bor` (`tau_glitch = 10 ns`) | `0.5 us` & `1.5 us` spikes falsely trigger `RSTB = 0` | `immune_short = false` |
| **TB4 (`bor_levels`)** | `va_por_bor` (`code = 0..7`) | `0.905..1.257 V` rise, `50.28 mV/LSB`, `DNL = 0.034 LSB`, `V_hys = 105.1 mV`, `I_q = 150.2 nA` | `monotonic = true` |
| **TB5 (`linearity`)** | `va_temp_sensor_tsd` (`-40..125 C`) | `S = 2.009 mV/C`, `err_raw = 1.42 C`, `err_1pt = 1.28 C`, `err_2pt = +/-0.46 C` (`0.63 C` LS max) | Textbook 2nd-order BJT bow |
| **TB5 (Transistor Cross-Check)** | Subthreshold CMOS `V_GS/dV_GS` (`models_sky130_minimal.scs`) | `V_GS = 0.503 V` (`-0.99 mV/C`), `S = 1.275 mV/C`, `err_2pt = +/-2.10 C` (`I_q = 180 nA`) | Confirms larger MOS $n(T)$ bow |
| **TB6 (`psrr_noise`)** | `va_temp_sensor_tsd` (`CHOP=1` vs `0`) | `supply_sens = 0.45 C/V`, `noise = 18.2 mK_rms`, `err_unchop = +3.32 C` vs `err_chop = +0.10 C` (`33.0x`) | `chop_pass = true` |
| **TB7 (`tsd`)** | `va_temp_sensor_tsd` (`t_hys = 15 C`) | `T_trip = 134.88 C`, `T_release = 120.13 C`, `T_hys = 14.75 C` | `hys_pass = true` |
| **TB7 (Negative Fault)** | `va_temp_sensor_tsd` (`t_hys = 0 C`) | `T_trip = 135.00 C`, `T_release = 135.00 C`, `T_hys = 0.00 C` | `hys_pass = false` |
