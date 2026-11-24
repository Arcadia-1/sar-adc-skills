# Bandgap Reference Spectre Verification Guide

## 1. Ready-to-Run Process-Independent Signoff Testbench Suite (`assets/tb/`)

All **9 standalone Spectre decks** plug in external `models_corner.scs` + `dut_subckt.scs` and are analyzed by [`../assets/tb/analyze_bandgap.py`](../assets/tb/analyze_bandgap.py):

| Testbench | DUT Contract | Analyses & Extracted Metrics |
|---|---|---|
| [`tb_bgr_temp_line.scs`](../assets/tb/tb_bgr_temp_line.scs) | `dut_bandgap` (3-pin) | `dc_temp` (`-40..125°C`, step `5°C`) + `dc_line` (`0..1.4 V`): `vref_27c_v`, `vref_min/max_v`, `temp_peak_c`, exact box-method `tc_box_ppm_per_c`, `vdd_min_1pct_v`, `line_reg_mv_per_v`, `iq_27c_ua` |
| [`tb_bgr_startup.scs`](../assets/tb/tb_bgr_startup.scs) | `dut_bandgap` (3-pin) | Power-up ramp `tran` (`ic VREF=0`, `t_ramp=10u` default): `started_cleanly`, `vref_final_v`, `t_startup_1pct_us`, `overshoot_pct` |
| [`tb_bgr_psrr_noise.scs`](../assets/tb/tb_bgr_psrr_noise.scs) | `dut_bandgap` (3-pin) | `ac` (`1 Hz..100 MHz`) + `noise` (`10 Hz..10 MHz`): `psrr_dc/10k/100k/1M_db`, `output_noise_uvrms` |
| [`tb_bgr_stb.scs`](../assets/tb/tb_bgr_stb.scs) | `dut_bandgap_stb` (5-pin) | `iprobe` `stb` (`1 Hz..1 GHz`): `net_negative_feedback`, `dc_loop_gain_db`, `ugf_hz`, `phase_margin_deg`, `gain_margin_db` |
| [`tb_bgr_trim_range.scs`](../assets/tb/tb_bgr_trim_range.scs) | `dut_bandgap_signoff` (8-pin) | 5-bit trim DC sweep (`0..31`) at nominal & `±3σ` offset corners (`alter` on `vos_inj`): `vref_min/max_v`, `trim_span_mv`, `lsb_step_mv`, `dnl_max_lsb`, `inl_max_lsb`, `monotonic`, `trimmed_err_mv`, `trim_centers_3sigma` |
| [`tb_bgr_brownout_glitch.scs`](../assets/tb/tb_bgr_brownout_glitch.scs) | `dut_bandgap_signoff` (8-pin) | Dual stress `tran` (`ic VREF=0`): mid-op deep brownout dip (`1.2 V -> 0.35 V -> 1.2 V`) + `2 us` negative supply glitch, then `alter` to `500 us` ultra-slow ramp: `recovered_after_dip`, `t_recover_1pct_us`, `vref_post_dip_v`, `slow_ramp_started`, `dead_state_free` |
| [`tb_bgr_en_startup_leak.scs`](../assets/tb/tb_bgr_en_startup_leak.scs) | `dut_bandgap_signoff` (8-pin) | `EN` cycling `OFF -> ON -> OFF -> ON` monitoring `VSUP:p`, `VREF`, and `VISTART:p`: `i_shdn_na`, `t_en_wakeup_1pct_us`, `t_re_enable_us`, `i_startup_peak_ua`, `i_startup_steady_na`, `startup_turnoff_pass` |
| [`tb_bgr_load_cap_step.scs`](../assets/tb/tb_bgr_load_cap_step.scs) | `dut_bandgap_signoff` (8-pin) | DC sink/source sweep (`-100 uA..+100 uA`) + `0 -> +100 uA -> 0` load step into `C_L = 50 pF`: `load_reg_mv_per_ma`, `r_out_dc_ohm`, `step_droop_mv`, `step_overshoot_mv`, `t_recover_0p5pct_us` |
| [`tb_bgr_bias_currents.scs`](../assets/tb/tb_bgr_bias_currents.scs) | `dut_bandgap_signoff` (8-pin) | `-40..125°C` temp sweep + `0..1.2 V` compliance sweep + `ac` PSRR of `IPTAT`/`IZTC` + `±3 mV` `V_os` perturbation (`alter`): `iptat_27c_ua`, `iptat_tc_ppm_per_c`, `iztc_27c_ua`, `iztc_tc_ppm_per_c`, `compliance_min_v`, `bias_psrr_dc_db`, `vos_tc_sensitivity_ppm_per_mv` |

### Behavioral Models (`assets/va/`)
- [`va_bandgap.va`](../assets/va/va_bandgap.va): 3-pin macro-model (`VDD, VREF, VSS`) with live `$temperature` Tsividis parabolic curvature, headroom turn-on, startup RC, PSRR, and white + $1/f$ noise.
- [`va_bgr_core.va`](../assets/va/va_bgr_core.va): 5-pin dual-feedback core model (`VDD, VREF, LOOP_OUT, LOOP_IN, VSS`) explicitly modeling the unit-PNP positive branch vs. $M\times$ PNP $+ R_1$ negative branch for `tb_bgr_stb.scs` (including `c_neg_par` and `swap_pol` fault injection).
- [`va_bgr_signoff.va`](../assets/va/va_bgr_signoff.va): 8-pin full signoff SoC BGR model (`VDD, EN, VTRIM, VREF, IPTAT, IZTC, ISTART_MON, VSS`) with 5-bit trim (`dnl_msb_lsb`), PTAT-dependent opamp offset (`v_os_err`), true bistable startup dynamics (`startup_en=0` dead-state fault & `fault_startup_leak=1` leaky-startup fault), `EN` shutdown leakage, closed-loop output buffer (`r_out_dc`/`r_out_hf`), and companion `IPTAT`/`IZTC` mirrors with compliance headroom, `r_o`, and frequency-dependent PSRR.

---

## 2. Tapeout Signoff Checklist & Critical Verification Pitfalls

1. **Startup across ramp-rate extremes, brownout recovery & steady-state zero-leakage audit:**
   - Run [`tb_bgr_brownout_glitch.scs`](../assets/tb/tb_bgr_brownout_glitch.scs) across `ss`/`-40°C`, `tt`/`27°C`, and `ff`/`125°C` with `ic VREF=0`. Confirm **both** mid-operation deep brownout recovery (`1.2 V -> 0.35 V -> 1.2 V`, `recovered_after_dip == True`) and ultra-slow `500 us` ramp ignition (`slow_ramp_started == True`, `dead_state_free == True`).
   - Run [`tb_bgr_en_startup_leak.scs`](../assets/tb/tb_bgr_en_startup_leak.scs) across `OFF -> ON -> OFF -> ON` cycles: confirm shutdown current `i_shdn_na` meets sleep budget (`EN = 0`), cold enable and re-enable settle cleanly, and steady-state startup-branch current (`i_startup_steady_na` via `ISTART_MON`) shuts completely off (`< 10 nA`, `< 0.01%` of core bias) so startup leakage never degrades TC at `ff`/`125°C`.
   - **Negative-test verification:** Validate your testbench catches real bugs by setting `startup_en=0` in `va_bgr_signoff.va` (must flag `recovered_after_dip = false`, `slow_ramp_started = false`) and `fault_startup_leak=1` (must flag `i_startup_steady_na > 1000 nA`, `startup_turnoff_pass = false`).
2. **Core loop stability (`tb_bgr_stb.scs`) across PVT + load cap:**
   - Insert `iprobe` between opamp output (`LOOP_OUT`) and the current-mirror/core drive (`LOOP_IN`) without disturbing DC bias.
   - Verify `net_negative_feedback == True`, DC loop gain $\ge 45\text{–}60\text{ dB}$, phase margin $\ge 60^\circ$, and gain margin $\ge 10\text{ dB}$ across all corners (check `ss`/`-40°C` and `ff`/`125°C` where $r_e = V_T/I_b$ and $g_m$ shift).
3. **5-bit trim linearity, monotonicity & `±3σ` process/offset centering (`tb_bgr_trim_range.scs`):**
   - Sweep all 32 trim codes (`0..31`) and verify `monotonic == True`, `dnl_max_lsb < 0.5 LSB`, `inl_max_lsb < 0.5 LSB`, and total trim span $\ge \pm 4\%$ (covering global corners + `3σ` Monte Carlo mismatch).
   - Confirm worst-case `-3σ` and `+3σ` offset shifts trim back within `< 0.5 LSB` (`trim_centers_3sigma == True`) without saturating at code `0` or `31`.
4. **Output buffer DC load regulation & switched-cap kick recovery (`tb_bgr_load_cap_step.scs`):**
   - Sweep DC load current bipolar (`-100 uA..+100 uA`) to verify both sourcing and sinking headroom (`r_out_dc_ohm`, `load_reg_mv_per_ma`).
   - Apply a fast load-current pulse into `C_L = 50 pF` and verify dynamic droop, release overshoot, and `0.5%` settling time meet the downstream ADC/LDO sampling budget.
5. **Companion `IPTAT`/`IZTC` bias currents & opamp `V_os` TC-sensitivity audit (`tb_bgr_bias_currents.scs`):**
   - Verify `IPTAT` exhibits clean `+3300 ppm/°C` linear PTAT slope across `-40..125°C` while `IZTC` holds `< 80–100 ppm/°C`.
   - Sweep output pin compliance (`0..1.2 V`) to verify `compliance_min_v <= 0.25 V` and output impedance `r_o >= 1 MOhm`, and inspect normalized current-mode `bias_psrr_dc_db` (cascode mirrors if un-cascoded simple mirrors fall below `40–60 dB`).
   - Perturb opamp input offset by `±3 mV` (`vos_inj`) and quantify both `vos_vref_gain_v_per_v` and `vos_tc_sensitivity_ppm_per_mv` (`~25 ppm/°C/mV`) to size input-pair area and chopping requirements.
6. **PSRR & Output Noise vs. Downstream Consumer (`tb_bgr_psrr_noise.scs`):**
   - Confirm low-frequency PSRR ($\ge 60\text{ dB}$) and high-frequency supply rejection (add an RC low-pass filter on `VREF` or cascode the PMOS mirrors if supply ripple couples into a sensitive LDO/ADC/PLL).
   - Integrate `noise` across the downstream system bandwidth (e.g., `10 Hz` to LDO GBW or ADC $f_s/2$) and ensure BGR noise is well below the system floor.
