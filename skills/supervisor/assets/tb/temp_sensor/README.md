# On-Chip Temperature Sensor & TSD Spectre X Testbench Suite

Process-independent Spectre X (`+preset=cx`) decks and zero-dependency PSF ASCII analyzer for ratiometric BJT/CMOS temperature sensors and hysteretic Over-Temperature Shutdown (TSD) comparators.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_tsens_linearity.scs` | `-40..125 C` (`step=1 C`) `dc_temp` sweep (`CHOP = VDD`) | `vbe_slope_mv_per_c`, `vptat_slope_mv_per_c`, `sens_mv_per_c`, `err_raw_max_abs_c`, `err_1pt_27c_max_abs_c`, `err_2pt_max_abs_c`, `err_2pt_half_span_c`, `iq_27c_ua` |
| `tb_tsens_psrr_noise.scs` | `dc_chop1`, `dc_vdd` (`1.62..1.98 V`), `noise_chop1` (`1 Hz..100 kHz`), `alter` `CHOP=0` (`dc_chop0` + `noise_chop0`) | `supply_sens_c_per_v`, `psrr_dc_db`, `temp_noise_mk_rms`, `err_unchopped_c`, `err_chopped_c`, `chop_suppression_x`, `chop_pass` |
| `tb_tsens_thermal_alarm.scs` | Consecutive `dc_up` (`25..160 C`) & `dc_dn` (`160..25 C`) with `prevoppoint=yes` | `t_trip_c`, `t_release_c`, `t_hys_c`, `tsd_tripped`, `tsd_released`, `hys_pass` |
| `analyze_temp_sensor.py` | Standalone PSF ASCII analyzer (`linearity`, `psrr_noise`, `tsd`) | JSON summary |

## DUT Interface Contract

Provide `models_corner.scs` (your PDK corner or repo-root `common/models_generic_bsim4.scs` / `common/models_sky130_minimal.scs`) and `dut_subckt.scs`:

```spectre
// 7-pin Temperature Sensor + Over-Temperature Shutdown (TSD) contract
//   - CHOP   : dynamic offset chopping control (0 V = OFF, VDD = ON)
//   - VPTAT  : amplified PTAT voltage (alpha * delta-V_BE)
//   - VBE    : CTAT BJT V_BE (or subthreshold CMOS V_GS) voltage
//   - VTEMP  : ratiometric calibrated output (~2.0 mV/K)
//   - TSD_OUT: active-high thermal shutdown flag (0 V = normal, VDD = tripped)
subckt dut_tsens VDD CHOP VPTAT VBE VTEMP TSD_OUT VSS
    // instantiate your transistor sensor + TSD (or wrap ../../va/va_temp_sensor_tsd.va)
ends dut_tsens
```
