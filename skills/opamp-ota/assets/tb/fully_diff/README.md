# Fully Differential OTA + CMFB Spectre Testbench Suite

Standalone, zero-`analogLib` Spectre testbenches for characterizing both differential-mode (DM) and common-mode (CMFB) stability and large-signal differential settling.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_fd_ota_dm_cm_stb.scs` | Simultaneous `stb_dm` + `stb_cm` via inline lossless reciprocal Tian balun (`diff_stb_probe`) | `T0_DM`, `UGF_DM`, `PM_DM`, `GM_DM` & `T0_CM`, `UGF_CM`, `PM_CM`, `GM_CM` |
| `tb_fd_ota_slew_settle.scs` | Differential closed-loop step `tran` | `sr_diff_v_per_us`, `0.1%` & `0.01%` settling time, `vocm_max_disturbance_mv` |
| `analyze_fd_ota.py` | Standalone PSF ASCII analyzer | JSON summary |

## DUT Interface Contract

```spectre
subckt dut_fd_ota VIP VIN VOCM VCM_FB VOP VON VDD VSS
    // instantiate your transistor FD-OTA + CMFB (or wrap ../../va/va_ota_fd_cmfb.va)
ends dut_fd_ota
```
