# SerDes Sign-Sign LMS Adaptive Equalization Testbench Suite

Process-independent Spectre X (`+preset=cx` / `+preset=ax`) testbench and analyzer verifying concurrent live adaptation of VGA gain (`W_GAIN`) and 3-tap DFE coefficients (`W_H1`, `W_H2`, `W_H3`) with majority-vote decimation and convergence-freeze (`DONE`).

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_sslms_adapt.scs` | 1600-UI PRBS-9 closed-loop transient adaptation (`10 Gb/s`) | Converged `gain`, `h1/h2/h3` vs. ground truth, `done_flags`, raw vs. converged eye height & width |
| `analyze_sslms.py` | Standalone PSF ASCII analyzer | JSON summary |

## DUT Interface Contract

```spectre
subckt dut_sslms_dfe INP INN CLK H1 H2 H3 VREF_ERR VDD VSS SUMP SUMN DOUTP DOUTN ERRP ERRN
    // instantiate your DFE + data/error slicers (or wrap ../../va/va_dfe_3tap.va)
ends dut_sslms_dfe
```
