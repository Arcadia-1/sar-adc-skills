# Process-Independent Fractional-N $\Delta\Sigma$ PLL Testbench (Spectre)

Standalone Spectre testbench and analyzer for verifying Fractional-N MASH 1-1-1 CP-PLLs (3rd-order passive loop filter, fractional locking accuracy, $\Delta\Sigma$ control-voltage ripple, and CP mismatch noise-folding comparison).

## Files

- **`tb_frac_n_pll_lock.scs`** — Runs closed-loop fractional locking (default `f_ref = 50 MHz`, `N_eff = 20 + 13/128 = 20.1015625` $\to$ `1.005078125 GHz`).
- **`analyze_frac_n_pll.py`** — Extracts exact cycle-counted locked frequency, ppm error, `VCTRL` $\Delta\Sigma$ ripple (pp/rms), period jitter, and cycle-to-cycle jitter.

## DUT Interface Contract

```spectre
subckt dut_frac_n_pll FREF OUTP OUTN VCTRL VDD VSS
    // Phase 1: va_pfd + va_cp + 3rd-order filter (R1/C1/C2/R3/C3) + va_vco + va_mmd_mash111
    // Phase 3/4: swap individual blocks to transistor subcircuits
ends dut_frac_n_pll
```
