# SerDes CTLE, VGA & Offset Calibration Spectre Testbench Suite

Process-independent Spectre X (`+preset=cx` / `+preset=ax`) decks and analyzer for RX front-end CTLE/VGA frequency response, shaped output noise, channel-plus-CTLE eye opening, and closed-loop offset calibration.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_ctle_ac_noise.scs` | Differential `ac` (`1 MHz..40 GHz`) + `noise` (`100 kHz..20 GHz`) | `dc_gain_db`, `peak_gain_db`, `peaking_db`, `f_peak_ghz`, `f_3db_ghz`, `out_noise_mvrms` |
| `tb_ctle_channel_eye.scs` | PRBS-7 eye + SBR before & after CTLE across `channel_diff_lossy.scs` | `before_ctle_eye` vs. `after_ctle_eye` (height/width), `before/after_ctle_sbr` |
| `tb_vga_offset_cal.scs` | Closed-loop digital offset calibration (`va_offset_cal_fsm.va`) | `converged`, `t_converge_ns`, `initial_out_offset_mv`, `residual_out_offset_mv`, `final_cal_code` |
| `analyze_ctle_vga.py` | Standalone PSF ASCII analyzer (`ac_noise`, `eye`, `offset_cal`) | JSON summary |

## DUT Interface Contract

```spectre
subckt dut_ctle_vga INP INN VBOOST VOFF_CAL VDD VSS OUTP OUTN
    // instantiate your transistor CTLE/VGA (or wrap ../../va/va_ctle_vga.va)
ends dut_ctle_vga
```
