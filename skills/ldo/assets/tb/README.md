# Process-Independent LDO Spectre Testbench Suite

Full signoff-style Spectre testbench set for external-cap and capless LDO regulators.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_ldo_dc_reg_dropout.scs` | `dc_line` + `dc_load` | `dropout_mv`, `line_reg_mv_per_v`, `load_reg_mv_per_ma`, `iq_ua`, `current_eff_max_pct` |
| `tb_ldo_stb.scs` | `dc` + `stb` (`iprobe`) | `dc_loop_gain_db`, `ugf_mhz`, `phase_margin_deg`, `gain_margin_db` |
| `tb_ldo_psrr_zout_noise.scs` | 2-replica `ac` + `noise` | `psrr_dc/100k/1M/100M/min`, `zout_dc/1M/peak`, `output_noise_uvrms` |
| `tb_ldo_load_line_tran.scs` | Load-step + line-step `tran` | `load_undershoot_mv`, `load_overshoot_mv`, `line_step_glitch_mv` |
| `analyze_ldo.py` | Standalone PSF ASCII analyzer | JSON summary |

## DUT Interface Contract

```spectre
subckt dut_ldo VDD VREF VOUT FB_IN VSS
    // Expose FB_IN so tb_ldo_stb.scs can insert `IPRB (VOUT FB_IN) iprobe` cleanly.
ends dut_ldo
```
