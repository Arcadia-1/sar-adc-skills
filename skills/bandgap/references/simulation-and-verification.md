# Bandgap Reference Spectre Verification Guide

## 1. Ready-to-Run Process-Independent Testbench Suite (`assets/tb/`)

All 3 standalone Spectre decks plug in external `models_corner.scs` + `dut_subckt.scs` (`subckt dut_bandgap VDD VREF VSS`) and are analyzed by [`../assets/tb/analyze_bandgap.py`](../assets/tb/analyze_bandgap.py):

1. **`tb_bgr_temp_line.scs`** — Two DC sweeps in one simulation:
   - `dc_temp`: sweeps `temp` from `-40°C` to `125°C` (`step=5°C`) $\to$ extracts `vref_nom_v`, `vref_min_v`, `vref_max_v`, `temp_peak_c`, and exact box-method **`tc_ppm_per_c`**.
   - `dc_line`: sweeps `vdd` from `0 V` to `1.2*vdd_nom` $\to$ extracts minimum supply headroom `vdd_min_v` (within 1% of nominal) and **`line_reg_mv_per_v`** across the regulated supply window.
2. **`tb_bgr_startup.scs`** — Power-up transient (`VDD` ramps `0 -> vdd_nom` over realistic `t_ramp = 10 us`, plus **zero initial condition check**!) $\to$ verifies immunity to the zero-current dead state, extracts **`t_startup_1pct_us`**, peak overshoot, and final settled `vref_final_v` (also check slow `t_ramp = 1 ms` and fast `t_ramp = 100 ns` edges across `ss`/`ff` and `-40°C`/`125°C`!).
3. **`tb_bgr_psrr_noise.scs`** — AC `PSRR(f)` (`1 Hz`–`100 MHz`) + integrated output `noise` (`10 Hz`–`10 MHz`, verifying total noise fits inside the ADC/LDO reference noise budget).

## 2. Critical Bandgap Verification Pitfalls

- **Always run startup at BOTH fast (`100 ns`) and slow (`1 ms`) `VDD` ramps AND verify the startup circuit actually turns OFF!** A startup circuit that leaks even `100 nA` at `ff`/`125°C` destroys temperature coefficient!
- **Run Monte Carlo mismatch (`N >= 200` points) across `-40°C`, `27°C`, `125°C`:** Untrimmed 3σ accuracy is typically dominated by opamp $V_{\text{os}}$; verify your trim range covers worst-case 3σ + process corners.
- **Check loop stability of the BGR core opamp (`stb`)!** Remember a bandgap loop has **both a negative feedback path AND a positive feedback path** (through the $1:M$ PNP ratio!). Ensure negative feedback always dominates ($R_2$ branch gain $>$ PTAT branch gain) and verify phase margin $\ge 60^\circ$!
