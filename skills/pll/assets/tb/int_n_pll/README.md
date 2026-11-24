# Process-Independent Integer-N CP-PLL Testbench Suite (Spectre)

Standalone Spectre testbenches and analyzer for Type-II Integer-N charge-pump PLL linear loop closure and nonlinear transient lock verification.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_int_n_pll_ac_loop.scs` | Phase-domain `stb` (`iprobe`) + `ac` | `fu_mhz`, `phase_margin_deg`, `cl_peaking_db`, `cl_bw_3db_mhz` |
| `tb_int_n_pll_lock.scs` | Closed-loop nonlinear lock `tran` | `f_locked_mhz`, `freq_err_ppm`, `t_settle_0p1pct_us`, `vctrl_ripple_pp_mv`, `est_ref_spur_dbc` |
| `analyze_int_n_pll.py` | Standalone PSF ASCII analyzer (`ac_loop` and `lock` modes) | JSON summary |

## DUT Interface Contract (`tb_int_n_pll_lock.scs`)

```spectre
subckt dut_int_n_pll FREF OUTP OUTN VCTRL VDD VSS
    // Phase 1: assemble va_pfd + va_cp + passive R1/C1/C2 + va_vco + va_div_int
    // Phase 3/4: swap blocks incrementally to transistor subcircuits
ends dut_int_n_pll
```
