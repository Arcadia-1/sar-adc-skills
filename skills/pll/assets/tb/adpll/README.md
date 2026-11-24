# Process-Independent ADPLL Testbench (Spectre)

Standalone Spectre testbench and analyzer for closed-loop All-Digital PLL verification — supporting Integer-N TDC-ADPLL, Fractional-N TDC-ADPLL (with `va_mmd_mash111.va`), and Bang-Bang ADPLL (with `va_bbpd.va`).

## Files

- **`tb_adpll_lock.scs`** — Closed-loop ADPLL transient lock deck monitoring `FTW`, `TDC_OUT`, `F_INST`, and `OUTP`.
- **`analyze_adpll.py`** — Extracts exact cycle-counted locked frequency, ppm error, 0.2% settling time, steady-state `FTW` mean & peak-to-peak wander (limit-cycle check), `TDC_OUT` RMS, and period jitter.

## DUT Interface Contract

```spectre
subckt dut_adpll FREF OUTP OUTN FTW TDC_OUT VDD VSS
    // Phase 1: va_tdc (or va_bbpd) + va_dlf_pi + va_dco + va_div_int (or va_mmd_mash111)
    // Phase 3/4: swap TDC, DCO, divider, or digital filter to transistor/synthesized blocks
ends dut_adpll
```
