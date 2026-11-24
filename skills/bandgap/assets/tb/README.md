# Process-Independent Bandgap Reference Spectre Testbench Suite

Standalone Spectre decks and zero-dependency analyzer for Kuijk/Brokaw and Banba sub-1 V bandgap voltage references.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_bgr_temp_line.scs` | `dc_temp` (`-40..125 C`) + `dc_line` (`0..1.4 V`) | `vref_27c_v`, `tc_box_ppm_per_c`, `temp_peak_c`, `vdd_min_1pct_v`, `line_reg_mv_per_v`, `iq_27c_ua` |
| `tb_bgr_startup.scs` | Power-up ramp `tran` (`ic VREF=0`) | `started_cleanly`, `vref_final_v`, `t_startup_1pct_us`, `overshoot_pct` |
| `tb_bgr_psrr_noise.scs` | `ac` + `noise` | `psrr_dc/10k/100k/1M_db`, `output_noise_uvrms` |
| `tb_bgr_stb.scs` | `iprobe` core-loop `stb` (`1 Hz..1 GHz`) | `net_negative_feedback`, `dc_loop_gain_db`, `ugf_hz`, `phase_margin_deg`, `gain_margin_db` |
| `analyze_bandgap.py` | Standalone PSF ASCII analyzer (`temp_line`, `startup`, `psrr_noise`, `stb`) | JSON summary |

## DUT Interface Contracts

```spectre
// 3-pin closed-loop BGR (temp_line, startup, psrr_noise)
subckt dut_bandgap VDD VREF VSS
    // instantiate your transistor BGR (or wrap ../va/va_bandgap.va)
ends dut_bandgap

// 5-pin breakable-loop BGR (tb_bgr_stb.scs)
subckt dut_bandgap_stb VDD VREF LOOP_OUT LOOP_IN VSS
    // expose opamp output (LOOP_OUT) and mirror/core drive (LOOP_IN)
    // (or wrap ../va/va_bgr_core.va)
ends dut_bandgap_stb
```
