# SerDes Bridged T-Coil Bandwidth Extension Testbench Suite

Process-independent Spectre X (`+preset=cx`) testbench and analyzer verifying bridged T-coil bandwidth extension, input return loss (`S11`), and step response against a bare `R_L || C_L` ESD/pad load.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_tcoil_bw.scs` | Simultaneous `ac` (`10 MHz..100 GHz`) + `sp` (`S11`) + `tran` step | `bare_f3db_ghz`, `tcoil_f3db_ghz`, `bw_extension_ratio` (`~2.72x`), `tcoil_peaking_db`, `s11_worst_to_20ghz_db`, `tcoil_step_overshoot_pct` |
| `analyze_tcoil.py` | Standalone PSF ASCII analyzer | JSON summary |

## DUT Interface Contract

```spectre
subckt dut_tcoil IN MID OUT VSS
    // Example Butterworth bridged T-coil for R_L=50 ohm, C_L=500 fF (zeta=1/sqrt(2)):
    L1 (IN  MID) inductor  l=468.75p
    L2 (MID OUT) inductor  l=468.75p
    K1 mutual_inductor ind1=L1 ind2=L2 coupling=0.333333
    CB (IN  OUT) capacitor c=62.5f
ends dut_tcoil
```
