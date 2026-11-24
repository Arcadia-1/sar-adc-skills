# Process-Independent Bandgap Reference Spectre Testbench Suite

Standalone Spectre signoff decks (9 total) and zero-dependency PSF ASCII analyzer for Kuijk/Brokaw and Banba sub-1 V bandgap voltage references and companion PTAT/ZTC bias current generators.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_bgr_temp_line.scs` | `dc_temp` (`-40..125 C`) + `dc_line` (`0..1.4 V`) | `vref_27c_v`, `tc_box_ppm_per_c`, `temp_peak_c`, `vdd_min_1pct_v`, `line_reg_mv_per_v`, `iq_27c_ua` |
| `tb_bgr_startup.scs` | Power-up ramp `tran` (`ic VREF=0`) | `started_cleanly`, `vref_final_v`, `t_startup_1pct_us`, `overshoot_pct` |
| `tb_bgr_psrr_noise.scs` | `ac` + `noise` | `psrr_dc/10k/100k/1M_db`, `output_noise_uvrms` |
| `tb_bgr_stb.scs` | `iprobe` core-loop `stb` (`1 Hz..1 GHz`) | `net_negative_feedback`, `dc_loop_gain_db`, `ugf_hz`, `phase_margin_deg`, `gain_margin_db` |
| `tb_bgr_trim_range.scs` | 5-bit `dc` sweep (`0..31`) + `+/-3 sigma` `alter` corners | `vref_min/max_v`, `trim_span_mv`, `lsb_step_mv`, `dnl_max_lsb`, `inl_max_lsb`, `monotonic`, `trimmed_err_mv` |
| `tb_bgr_brownout_glitch.scs` | Dual `tran` (`1.2->0.35->1.2 V` dip + glitch, `500 us` slow ramp) | `recovered_after_dip`, `t_recover_1pct_us`, `vref_post_dip_v`, `slow_ramp_started`, `dead_state_free` |
| `tb_bgr_en_startup_leak.scs` | `EN` `OFF->ON->OFF->ON` `tran` + `ISTART_MON` ammeter | `i_shdn_na`, `t_en_wakeup_1pct_us`, `t_re_enable_us`, `i_startup_peak_ua`, `i_startup_steady_na`, `startup_turnoff_pass` |
| `tb_bgr_load_cap_step.scs` | `dc` load sweep (`-100..+100 uA`) + `tran` pulse into `50 pF` | `load_reg_mv_per_ma`, `r_out_dc_ohm`, `step_droop_mv`, `step_overshoot_mv`, `t_recover_0p5pct_us` |
| `tb_bgr_bias_currents.scs` | `-40..125 C` `dc` + `0..1.2 V` compliance + `ac` PSRR + `+/-3 mV` `V_os` | `iptat_27c_ua`, `iptat_tc_ppm_per_c`, `iztc_27c_ua`, `iztc_tc_ppm_per_c`, `compliance_min_v`, `bias_psrr_dc_db`, `vos_tc_sensitivity_ppm_per_mv` |
| `analyze_bandgap.py` | Standalone PSF ASCII analyzer (`temp_line`, `startup`, `psrr_noise`, `stb`, `trim`, `brownout`, `en_leak`, `load_step`, `bias_currents`) | JSON summary |

## DUT Interface Contracts

```spectre
// 1. 3-pin closed-loop BGR (temp_line, startup, psrr_noise)
subckt dut_bandgap VDD VREF VSS
    // instantiate your transistor BGR (or wrap ../va/va_bandgap.va)
ends dut_bandgap

// 2. 5-pin breakable-loop BGR (tb_bgr_stb.scs)
subckt dut_bandgap_stb VDD VREF LOOP_OUT LOOP_IN VSS
    // expose opamp output (LOOP_OUT) and mirror/core drive (LOOP_IN)
    // (or wrap ../va/va_bgr_core.va)
ends dut_bandgap_stb

// 3. 8-pin full signoff SoC BGR (trim, brownout, en_leak, load_step, bias_currents)
//    - VTRIM: analog trim code 0..31 (mid-code = 16)
//    - IPTAT / IZTC: companion NMOS current-sink mirror outputs (biased at v_comp)
//    - ISTART_MON: startup-branch current monitor tied to 0 V ammeter VISTART
//    - Optional global parameter `vos_inj` injects opamp input offset in trim & bias TBs
subckt dut_bandgap_signoff VDD EN VTRIM VREF IPTAT IZTC ISTART_MON VSS
    // instantiate your transistor signoff BGR (or wrap ../va/va_bgr_signoff.va)
ends dut_bandgap_signoff
```
