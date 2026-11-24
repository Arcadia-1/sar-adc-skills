# Process-Independent Frequency Divider & MMD Testbench (Spectre)

Standalone Spectre testbench for verifying both Integer-N dividers and Fractional-N MASH 1-1-1 Multi-Modulus Dividers (MMD).

## Files

- **`tb_div_func_mmd.scs`** — Runs ~300 divided output cycles at `f_in = 1 GHz` (configurable).
- **`analyze_divider.py`** — Extracts exact long-term average division ratio `n_avg`, instantaneous modulus span `[n_min_inst, n_max_inst]`, and ppm error against `--n-expected`.

## DUT Interface Contract

```spectre
subckt dut_divider CLK_IN CLK_OUT VDD VSS
    // instantiate your transistor divider/MMD (or wrap ../../va/va_div_int.va / va_mmd_mash111.va)
ends dut_divider
```
