# SerDes Sign-Sign LMS Adaptive Equalization Testbench Suite

Process-independent Spectre X (`+preset=cx` / `+preset=ax`) decks and analyzer verifying both concurrent VGA + 3-tap DFE adaptation and transition-filtered (`edge_only=1`) CTLE peaking boost adaptation.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_sslms_adapt.scs` | 1600-UI PRBS-9 concurrent VGA gain + 3-tap DFE (`h1, h2, h3`) adaptation | Converged `gain`, `h1/h2/h3` vs. ground truth, `done_flags`, raw vs. converged eye |
| `tb_sslms_ctle_boost.scs` | 1200-UI PRBS-9 transition-filtered (`edge_only=1`) CTLE `VBOOST` adaptation on passive `mtline` channel | `vboost_init/final_v`, `done`, `t_converge_ns`, raw vs. adapted CTLE eye height & width |
| `analyze_sslms.py` | Standalone PSF ASCII analyzer (`--mode dfe` or `--mode ctle_boost`) | JSON summary |

## DUT Interface Contracts

```spectre
// For tb_sslms_adapt.scs
subckt dut_sslms_dfe INP INN CLK H1 H2 H3 VREF_ERR VDD VSS SUMP SUMN DOUTP DOUTN ERRP ERRN ... ends

// For tb_sslms_ctle_boost.scs
subckt dut_ctle_vga INP INN VBOOST VOFF_CAL VDD VSS OUTP OUTN ... ends
```
