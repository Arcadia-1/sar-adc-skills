# Process-Independent ADPLL TDC & DCO Testbench Suite (Spectre)

Standalone Spectre decks and analyzer for characterizing ADPLL Time-to-Digital Converters (TDC) and Digitally Controlled Oscillators (DCO).

## Files

| File | Purpose | Key Metrics |
|---|---|---|
| `tb_tdc_transfer.scs` | Detuned beat-sweep across `[-400 ps, +400 ps]` in `10 ps` steps | `t_res_meas_ps`, `offset_ps`, `dnl_abs_max_lsb`, `inl_abs_max_lsb`, `monotonic` |
| `tb_dco_tuning.scs` | 9-point `FTW` staircase + `va_phase_err_mon.va` | `f_min_mhz`, `f_max_mhz`, `k_dco_avg/min/max_khz_per_lsb`, `monotonic` |
| `analyze_tdc_dco.py` | Standalone PSF ASCII analyzer (`tdc` and `dco` modes) | JSON summary |

## DUT Interface Contracts

```spectre
subckt dut_tdc FREF FDIV TDC_OUT VDD VSS
    // instantiate your TDC (or wrap ../../va/va_tdc.va)
ends dut_tdc

subckt dut_dco FTW OUTP OUTN VDD VSS
    // instantiate your DCO (or wrap ../../va/va_dco.va)
ends dut_dco
```
