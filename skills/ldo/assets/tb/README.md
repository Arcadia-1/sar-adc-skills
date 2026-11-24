# Process-Independent LDO Spectre Testbench Suite

Full 9-deck industrial signoff Spectre testbench suite for external-cap, capless (OCL), and enabled PMIC LDO regulators.

## Files

| File | Analysis | Analyzer Subcommand | Key Metrics |
|---|---|---|---|
| `tb_ldo_dc_reg_dropout.scs` | `dc_line` + `dc_load` | `dc_reg` | `dropout_mv`, `line_reg_mv_per_v`, `load_reg_mv_per_ma`, `iq_ua`, `current_eff_max_pct` |
| `tb_ldo_stb.scs` | `dc` + `stb` (`iprobe`) | `stb` | `dc_loop_gain_db`, `ugf_mhz`, `phase_margin_deg`, `gain_margin_db` |
| `tb_ldo_psrr_zout_noise.scs` | 2-replica `ac` + `noise` | `psrr_zout_noise` | `psrr_dc/100k/1M/100M/min`, `zout_dc/1M/peak`, `output_noise_uvrms` |
| `tb_ldo_load_line_tran.scs` | Load-step + line-step `tran` | `tran` | `load_undershoot_mv`, `load_overshoot_mv`, `line_step_glitch_mv` |
| `tb_ldo_startup_inrush.scs` | `EN` rise/fall `tran` | `startup` | `t_start_90pct_us`, `t_settle_1pct_us`, `overshoot_mv/pct`, `monotonic_startup`, `i_inrush_peak_ma`, `t_discharge_10pct_us` |
| `tb_ldo_ocp_foldback.scs` | `dc_iv` + `tran_short` | `ocp` | `i_lim_peak_ma`, `i_short_ma`, `foldback_ratio`, `vout_recover_ok`, `t_recover_us` |
| `tb_ldo_stb_esr_grid.scs` | 9-point `alter` + `stb` | `esr_grid` | Per-corner `T0_db`, `ugf_mhz`, `pm_deg`, `gm_db`, `pm_min_deg`, `worst_corner`, low/high-ESR tunnel boundaries |
| `tb_ldo_dropout_tran.scs` | `tran_brownout` + `tran_ripple` | `dropout_tran` | `vout_min_dip_v`, `vout_recover_overshoot_mv`, `t_recover_1pct_us`, `dyn_psrr_db` |
| `tb_ldo_temp_shdn.scs` | `dc_temp` + `dc_iq_load` + `dc_shdn_temp` | `temp_shdn` | `vout_27c_v`, `tc_ppm_per_c`, `iq_light/full_ua`, `current_eff_light/full_pct`, `i_shdn_27c_na`, `i_shdn_125c_ua` |
| `analyze_ldo.py` | Standalone PSF ASCII analyzer | 9 subcommands above | Zero-dependency JSON summary |

## DUT Interface Contracts

```spectre
// 5-pin LDO exposing breakable FB_IN (used by dc_reg_dropout, stb, psrr_zout_noise,
// load_line_tran, ocp_foldback, stb_esr_grid, dropout_tran)
subckt dut_ldo VDD VREF VOUT FB_IN VSS
    // Expose FB_IN so tb_ldo_stb.scs / tb_ldo_stb_esr_grid.scs can insert `iprobe`.
    // When wrapping ../va/va_ldo_signoff.va, tie EN internally to VDD.
ends dut_ldo

// 6-pin enabled LDO (used by startup_inrush and temp_shdn)
subckt dut_ldo_en VDD VREF EN VOUT FB_IN VSS
    // Exposes active-high EN for soft-start/active-discharge and EN=0 shutdown leakage.
    // Wrap ../va/va_ldo_signoff.va or a transistor-level LDO with enable/discharge logic.
ends dut_ldo_en
```
