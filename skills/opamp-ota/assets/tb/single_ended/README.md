# Single-Ended OpAmp / OTA Spectre Testbench Suite

Process-independent Spectre decks and zero-dependency analyzer for single-ended 5T OTAs, cascode OTAs, and two-stage Miller opamps.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_ota_stb_ac.scs` | `dc` + `stb` (`iprobe`) | `a0_db`, `ugf_mhz`, `phase_margin_deg`, `gain_margin_db`, `p_dc_mw`, `fom_s` |
| `tb_ota_cmrr_psrr_noise.scs` | 4-replica DC-servo `ac` + `noise` | `cmrr_dc/1MHz`, `psrr_p_dc/1MHz`, `psrr_n_dc/1MHz`, spot & integrated input-referred noise |
| `tb_ota_slew_settle.scs` | Unity-gain large-signal step `tran` | `sr_pos`, `sr_neg`, `overshoot_pct`, `0.1%` & `0.01%` settling time, `fom_l` |
| `analyze_ota.py` | Standalone PSF ASCII analyzer | JSON summary |

## DUT Interface Contract

```spectre
subckt dut_ota VIP VIN VOUT VDD VSS
    // instantiate your transistor OpAmp/OTA (or wrap ../../va/va_ota_2stage.va)
ends dut_ota
```
