---
name: bandgap-skill
description: >
  Process-independent Bandgap Voltage Reference (BGR) design guide and Spectre
  verification toolkit. Covers classic Kuijk/Brokaw (~1.22 V) and Banba sub-1 V
  current-mode architectures, PTAT + CTAT cancellation, box-method temperature
  coefficient (ppm/C), 2nd-order Tsividis curvature, opamp offset amplification,
  resistor trimming, PTAT/CTAT/ZTC bias current generation, positive-vs-negative
  core-loop feedback stability, startup dead-state prevention, 2 Verilog-A BGR
  models (3-pin macro + 5-pin breakable dual-feedback core), and 4 standalone
  Spectre testbenches (temp/line sweeps, power-up startup dead-state check,
  AC PSRR + output noise, and iprobe core-loop stb). Use for any bandgap
  reference sizing, TC/offset budgeting, startup debugging, or Spectre
  verification task.
---

# Bandgap Reference Skill

A process-independent engineering guide and Spectre verification toolkit for classic (`~1.22 V`) and sub-1 V (`~0.5–0.6 V`) bandgap voltage references and PTAT/CTAT/ZTC bias generators.

## Read Order

- `references/bandgap-fundamentals.md`
  PTAT + CTAT cancellation, Kuijk/Brokaw vs. Banba sub-1 V current-mode BGR, box-method TC, Tsividis 2nd-order curvature, opamp offset amplification & trimming, positive-vs-negative dual-feedback stability, startup dead-state immunity, and PTAT/CTAT/ZTC bias currents.
- `references/simulation-and-verification.md`
  Spectre temperature/line sweeps, fast/slow/brownout startup & zero-leakage audit, `iprobe` core-loop `stb`, Monte Carlo trim verification, and PSRR/noise budgeting.

## Bundled Assets

### Spectre Testbenches (`assets/tb/`)
- `assets/tb/tb_bgr_temp_line.scs` — `-40..125°C` temperature sweep (`TC [ppm/C]`) + `0..1.4 V` supply line sweep
- `assets/tb/tb_bgr_startup.scs` — Power-up ramp transient (`ic VREF=0`) verifying dead-state immunity & startup time
- `assets/tb/tb_bgr_psrr_noise.scs` — AC `PSRR(f)` + integrated output `noise`
- `assets/tb/tb_bgr_stb.scs` — `iprobe` core-loop `stb` verifying negative feedback dominance, `T0`, `UGF`, `PM`, and `GM`
- `assets/tb/analyze_bandgap.py` — Standalone PSF ASCII analyzer (`temp_line`, `startup`, `psrr_noise`, `stb`)

### Verilog-A Models (`assets/va/`)
- `assets/va/va_bandgap.va` — 3-pin temperature-curved BGR macro-model using live `$temperature` with parabolic curvature, supply headroom turn-on, startup RC, PSRR, and white + $1/f$ noise
- `assets/va/va_bgr_core.va` — 5-pin breakable dual-feedback BGR core model (`LOOP_OUT`/`LOOP_IN`) explicitly modeling the unit-PNP positive branch vs. $M\times$ PNP $+ R_1$ negative branch for `stb` stability analysis
