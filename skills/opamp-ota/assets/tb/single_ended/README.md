# Single-Ended OpAmp / OTA Spectre X Signoff Suite

Process-independent Spectre X (`+preset=cx`) signoff decks and zero-dependency PSF ASCII analyzer for single-ended 5T OTAs, telescopic/folded cascode OTAs, two-stage Miller, and multi-stage opamps.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_ota_stb_ac.scs` | `dc` + `stb` (`iprobe`) | `a0_db`, `ugf_mhz`, `phase_margin_deg`, `gain_margin_db`, `idd_ua`, `p_dc_mw`, `fom_s` |
| `tb_ota_cmrr_psrr_noise.scs` | 5-replica `ac` + `noise` (`1 Hz..1 GHz`) | `cmrr_dc/1MHz`, `cmrr_4r_dc/1MHz`, `psrr_p/n`, white floor, `1/f` corner, RMS out/in & avg noise density |
| `tb_ota_dc_signoff.scs` | `dc_op`, `dc_temp`, `dc_sweep`, `sweep_icmr_ac`, `dc_vdd` | `vos_mv`, `alpha_vos`, follower/4R-bridge/AC-6dB ICMR, `vopp` vs `RL=1M/100k/10k/1k`, `VIDR` phase reversal, `vdd`/`temp` operating ranges |
| `tb_ota_cl_zout_gm.scs` | `dc_gm` + `ac` (`1 Hz..10 GHz`) | Closed-loop `f_-3dB`/`f_0.1dB`/peaking/group delay, `Z_out(f)`, `R_O`, `R_ID`/`C_ID`, OTA `g_m`/`V_ID`/`I_OPP`/`g_m(f)` (short & loaded) |
| `tb_ota_slew_settle.scs` | Unity-gain step `tran` (configurable `r_src`) | `sr_pos`, `sr_neg`, `overshoot_pct`, `0.1%` & `0.01%` settling time, `fom_l` |
| `tb_ota_thd_fpbw.scs` | Coherently strobed sine `tran` (follower + inv `-1`) | `thd_db`, `thd_pct`, `hd2_dbc`, `hd3_dbc`, `sfdr_db`, `sndr_db`, `vout_pp_v`, `pass_thd_1pct` (`BW_full`) |
| `tb_ota_power_ramp.scs` | `5 ms`/`10 ms` VDD ramp-up/down `tran` | `settled_err_mv`, `max_active_ramp_dev_mv`, `oscillation_detected`, `pass` |
| `tb_ota_supply_surge_cmstep.scs` | `±50 mV` VDD surge + `0.2 V` CM step `tran` | `supply_surge_peak_mv`, `cm_step_peak_mv`, `cm_step_settle_1mv_ns` |
| `analyze_ota.py` | Standalone PSF ASCII analyzer (8 subcommands) | JSON summary |

## DUT Interface Contract

```spectre
subckt dut_ota VIP VIN VOUT VDD VSS
    // instantiate your transistor OpAmp/OTA (or wrap ../../va/va_ota_2stage.va)
ends dut_ota
```
