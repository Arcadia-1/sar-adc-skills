# Fully Differential OTA + CMFB Spectre X Signoff Suite

Standalone, zero-`analogLib` Spectre X (`+preset=cx`) signoff testbenches and PSF ASCII analyzer characterizing differential-mode (DM) and common-mode feedback (CMFB) stability, rejection, linearity, transconductance, operating ranges, and power-supply integrity.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_fd_ota_dm_cm_stb.scs` | Simultaneous `stb_dm` + `stb_cm` via inline lossless reciprocal Tian balun (`diff_stb_probe`) | `T0_DM`, `UGF_DM`, `PM_DM`, `GM_DM` & `T0_CM`, `UGF_CM`, `PM_CM`, `GM_CM` |
| `tb_fd_ota_cmrr_psrr_noise.scs` | 4-replica `ac` + `noise` (`1 Hz..1 GHz`) | `A_cm->cm`, `CMRR_cm->dm`, `PSRR+/-(VDD/VSS->CM & DM)`, differential spot/white/`1/f`/integrated RMS noise |
| `tb_fd_ota_dc_signoff.scs` | `dc_op`, `dc_temp`, `dc_sweep`, `sweep_icmr_ac`, `dc_vdd` | `vos_dm`, `vocm_err`, temp drift, CL-hold & AC-6dB ICMR, diff & SE `vopp` vs `RL=1M/100k/10k/1k`, `VIDR` phase reversal, `vdd`/`temp` ranges |
| `tb_fd_ota_cl_zout_gm.scs` | `dc_gm` + `ac` (`1 Hz..10 GHz`) | Closed-loop `f_-3dB`/`f_0.1dB`/peaking/group delay, `Z_out,dm(f)` & CMFB `Z_out,cm(f)`, `R_O`, `R_ID`/`C_ID`, FD OTA `g_m`/`V_ID`/`I_OPP`/`g_m(f)` |
| `tb_fd_ota_slew_settle.scs` | Differential closed-loop step `tran` | `sr_diff_v_per_us`, `0.1%` & `0.01%` settling time, `vocm_max_disturbance_mv` |
| `tb_fd_ota_thd_fpbw.scs` | Coherently strobed differential sine `tran` | `thd_db`, `thd_pct`, `hd2_dbc`, `hd3_dbc`, `sfdr_db`, `sndr_db`, `v_od_pp_v`, `pass_thd_1pct` (`BW_full`) |
| `tb_fd_ota_power_ramp.scs` | `5 ms`/`10 ms` VDD ramp-up/down `tran` | `settled_vocm_err_mv`, `settled_vdiff_err_mv`, `oscillation_detected`, `pass` |
| `tb_fd_ota_supply_surge_cmstep.scs` | `±50 mV` VDD surge + `0.2 V` CM step `tran` | `surge_vocm/vdiff_peak_mv`, `cm_step_vocm/vdiff_peak_mv`, `cm_step_vocm_settle_1mv_ns` |
| `tb_fd_ota_sc_closed_loop.scs` | Switched-capacitor gain stage (`-cs/cf`, `cl`), 3 replicas: `stb_dm`/`stb_cm`, step `tran`, `noise` with a noiseless 10 MΩ summing-node DC path | In-circuit `T0`/`UGF`/`PM` of both loops, settling to a band around the actual final value, dynamic error at `t_eval`, static error `1/(1+T0)` (reported apart), integrated output/input noise, per-device noise shares |
| `tb_fd_ota_gain_swing.scs` | Resistive closed loop (`-rf/rs`) DC sweep of the input | Local open-loop gain `A(Vod)` from the summing nodes, swing where `A >= (1-err)/(err*beta)` (`199/beta` at 0.5 %), and the -6 dB-from-peak swing |
| `analyze_fd_ota.py` | Standalone PSF ASCII analyzer (10 subcommands) | JSON summary |

## DUT Interface Contract

```spectre
subckt dut_fd_ota VIP VIN VOCM VCM_FB VOP VON VDD VSS
    // instantiate your transistor FD-OTA + CMFB (or wrap ../../va/va_ota_fd_cmfb.va)
ends dut_fd_ota
```
