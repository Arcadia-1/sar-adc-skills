# SerDes CTLE, VGA & Offset Calibration Spectre X Testbench Suite

Process-independent Spectre X (`+preset=cx` / `+preset=ax`) decks and analyzer for RX front-end CTLE/VGA peaking, combined channel+CTLE AC flatness, shaped output noise, channel eye opening, large-signal `P1dB`/`HD3`/`SFDR` linearity, and closed-loop offset calibration.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_ctle_ac_noise.scs` | Standalone differential `ac` (`1 MHz..100 GHz`) + `noise` | `dc_gain_db`, `peak_gain_db`, `peaking_db`, `f_peak_ghz`, `f_3db_ghz`, `out_noise_mvrms` |
| `tb_ctle_channel_ac.scs` | Combined `channel_diff_lossy.scs` + CTLE `ac` (`1 MHz..30 GHz`) | `ch_loss_5/10ghz_db`, `eq_dc/5/10ghz_db`, `eq_flatness_to_5ghz_db`, `eq_over_peaking_db`, `eq_f3db_ghz` |
| `tb_ctle_channel_eye.scs` | PRBS-7 eye + SBR before & after CTLE across `channel_diff_lossy.scs` | `before_ctle_eye` vs. `after_ctle_eye` (height/width), `before/after_ctle_sbr` |
| `tb_ctle_linearity_p1db.scs` | 8-point coherent large-signal sine amplitude sweep (`0.04..1.60 Vpp`, `outputstart` + `strobeonly`) | `in_p1db_vpp`, `in_p1db_dbm_100ohm`, `out_p1db_vpp`, `nom_hd3_dbc`, `nom_sfdr_db` |
| `tb_vga_offset_cal.scs` | Closed-loop digital offset calibration (`va_offset_cal_fsm.va`) | `converged`, `t_converge_ns`, `initial_out_offset_mv`, `residual_out_offset_mv`, `final_cal_code` |
| `analyze_ctle_vga.py` | Standalone PSF ASCII analyzer (`ac_noise`, `channel_ac`, `eye`, `offset_cal`, `linearity`) | JSON summary |

## DUT Interface Contract

```spectre
subckt dut_ctle_vga INP INN VBOOST VOFF_CAL VDD VSS OUTP OUTN
    // instantiate your transistor CTLE/VGA (or wrap ../../va/va_ctle_vga.va)
ends dut_ctle_vga
```
