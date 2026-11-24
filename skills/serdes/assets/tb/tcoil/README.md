# SerDes Bridged T-Coil & RX Front-End Spectre X Testbench Suite

Process-independent Spectre X (`+preset=cx`) testbenches and analyzer verifying bridged T-coil bandwidth extension, input return loss (`S11`), step response against a bare `R_L || C_L` ESD/pad load, and 4-port differential RX front-end mixed-mode `SDD11` / `SCD11` / `SCD21` / `SDC21` mode conversion under P/N mismatch.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_tcoil_bw.scs` | Simultaneous `ac` (`10 MHz..100 GHz`) + `sp` (`S11`) + `tran` step | `bare_f3db_ghz`, `tcoil_f3db_ghz`, `bw_extension_ratio` (`~2.83x`), `tcoil_peaking_db`, `s11_worst_to_20ghz_db`, `tcoil_step_overshoot_pct` |
| `tb_rx_frontend_sdd11_scd21.scs` | 4-port RX input network `sp` (`10 MHz..25 GHz`, ESD + T-coil + termination + configurable P/N mismatch) | `sdd11_worst_to_10/20ghz_db`, `scd11_10ghz_db`, `sdd21_10ghz_db`, `scd21_10ghz_db`, `sdc21_10ghz_db` |
| `analyze_tcoil.py` | Standalone PSF ASCII analyzer (`--mode bw` default, `--mode rx_frontend`) | JSON summary |

## DUT Interface Contracts

```spectre
// Single-ended bridged T-coil (tb_tcoil_bw.scs)
subckt dut_tcoil IN MID OUT VSS
    // Example Butterworth bridged T-coil for R_L=50 ohm, C_L=500 fF (zeta=1/sqrt(2)):
    L1 (IN  MID) inductor  l=468.75p
    L2 (MID OUT) inductor  l=468.75p
    K1 mutual_inductor ind1=L1 ind2=L2 coupling=0.333333
    CB (IN  OUT) capacitor c=62.5f
ends dut_tcoil

// 4-port differential RX front-end (tb_rx_frontend_sdd11_scd21.scs)
subckt dut_rx_frontend INP INN OUTP OUTN VSS
    // built-in parameterized ESD + T-coil + mismatch network (or swap extracted network)
ends dut_rx_frontend
```
