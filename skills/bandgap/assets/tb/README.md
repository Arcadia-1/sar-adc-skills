# Process-Independent Bandgap Reference Spectre Testbench Suite

Standalone Spectre decks and zero-dependency analyzer for Kuijk/Brokaw and Banba sub-1 V bandgap voltage references.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_bgr_temp_line.scs` | `dc_temp` (`-40..125 C`) + `dc_line` (`0..1.4 V`) | `vref_27c_v`, `tc_box_ppm_per_c`, `temp_peak_c`, `vdd_min_1pct_v`, `line_reg_mv_per_v`, `iq_27c_ua` |
| `tb_bgr_startup.scs` | Power-up ramp `tran` (`ic VREF=0`) | `started_cleanly`, `vref_final_v`, `t_startup_1pct_us`, `overshoot_pct` |
| `tb_bgr_psrr_noise.scs` | `ac` + `noise` | `psrr_dc/10k/100k/1M`, `output_noise_uvrms` |
| `analyze_bandgap.py` | Standalone PSF ASCII analyzer | JSON summary |

## DUT Interface Contract

```spectre
subckt dut_bandgap VDD VREF VSS
    // instantiate your transistor BGR (or wrap ../va/va_bandgap.va)
ends dut_bandgap
```
