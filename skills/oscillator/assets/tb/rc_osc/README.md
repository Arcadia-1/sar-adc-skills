# On-Chip RC Relaxation Oscillator Spectre Testbench Suite

Process-independent **Spectre X** testbenches and zero-dependency PSF analyzer for dual-cap / switched-RC on-chip relaxation oscillators (default `16 MHz`, `1.2 V`, 5-bit digital frequency trim `VTRIM = 0..31`, comparator-delay cancellation).

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_rc_osc_temp_vdd.scs` | 7-corner `alter` transient sweep: 5 temperatures (`-40, 0, 27, 85, 125 C`) at `VDD` + 3 supplies (`0.9, 1.0, 1.1 * VDD`) at `27 C` | `f_nom_mhz`, `temp_drift_pct`, `tc_ppm_per_c`, `vdd_sens_pct_per_v`, `total_pvt_spread_pct` |
| `tb_rc_osc_trim_startup.scs` | Part A: 8-code `VTRIM` sweep (`0, 4, 8, 12, 16, 20, 24, 31`); Part B: `EN` rising-edge cold startup from shutdown (`EN=0`) | `trim_range_pct`, `trim_step_pct_per_lsb`, `monotonic`, `t_startup_1pct_us`, `startup_cycles_to_1pct`, `first_cycle_err_pct`, `i_dd_ua`, `i_shdn_na` |
| `tb_rc_osc_jitter_duty.scs` | Long steady-state transient (`30 us`, `> 450` cycles at `16 MHz`, `+preset=cx`) with thermal jitter enabled | `n_cycles`, `f_mean_mhz`, `period_jitter_rms_ps`, `period_jitter_pp_ps`, `c2c_jitter_rms_ps`, `duty_mean_pct`, `duty_err_pct`, `t_r_ps`, `t_f_ps`, `jitter_pass` |
| `analyze_rc_osc.py` | Standalone PSF ASCII analyzer (`temp_vdd`, `trim_startup`, `jitter_duty`) | JSON summary |

## DUT Interface Contract

Provide `models_corner.scs` and `dut_subckt.scs` implementing a 5-pin RC relaxation oscillator (`VTRIM` is encoded as an integer-valued voltage `0..31` representing the 5-bit digital trim code):

```spectre
subckt dut_rc_osc VDD EN VTRIM OUT VSS
    // Instantiate your transistor dual-cap RC relaxation oscillator,
    // or wrap ../../va/va_rc_osc.va
ends dut_rc_osc
```

### Usage Examples

```bash
spectre +preset=cx -format psfascii -raw tv.raw tb_rc_osc_temp_vdd.scs
python3 analyze_rc_osc.py temp_vdd tv.raw --vdd-nom 1.2

spectre +preset=cx -format psfascii -raw ts.raw tb_rc_osc_trim_startup.scs
python3 analyze_rc_osc.py trim_startup ts.raw --t-en 200e-9

spectre +preset=cx -format psfascii -raw jit.raw tb_rc_osc_jitter_duty.scs
python3 analyze_rc_osc.py jitter_duty jit.raw --max-jitter-ps 80
```
