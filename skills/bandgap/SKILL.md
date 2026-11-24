---
name: bandgap-skill
description: >
  Process-independent Bandgap Voltage Reference (BGR) design guide and Spectre
  verification toolkit. Covers classic Kuijk/Brokaw (~1.22 V) and Banba sub-1 V
  current-mode architectures, PTAT + CTAT cancellation, box-method temperature
  coefficient (ppm/C), 2nd-order curvature, opamp offset amplification, startup
  dead-state prevention, a temperature-curved Verilog-A BGR model, and 3
  standalone Spectre testbenches (temp/line sweeps, power-up startup dead-state
  check, AC PSRR + integrated output noise). Use for any bandgap reference
  sizing, TC/offset budgeting, startup debugging, or Spectre verification task.
---

# Bandgap Reference Skill

A process-independent engineering guide and Spectre verification toolkit for classic and sub-1 V bandgap voltage references.

## Read Order

- `references/bandgap-fundamentals.md`
  PTAT + CTAT cancellation, Brokaw/Kuijk vs. Banba sub-1 V current-mode BGR, box-method TC, 2nd-order curvature floor, opamp offset amplification, and startup dead-state prevention.
- `references/simulation-and-verification.md`
  Spectre temperature/line sweep, fast/slow ramp startup & dead-state audit, PSRR/noise, and positive-vs-negative feedback loop stability checks.

## Bundled Assets

### Spectre Testbenches (`assets/tb/`)
- `assets/tb/tb_bgr_temp_line.scs` — `-40..125 C` temperature sweep (`TC [ppm/C]`) + `0..1.4 V` supply line sweep
- `assets/tb/tb_bgr_startup.scs` — Power-up ramp transient (`ic VREF=0`) verifying dead-state immunity & startup time
- `assets/tb/tb_bgr_psrr_noise.scs` — AC `PSRR(f)` + integrated output `noise`
- `assets/tb/analyze_bandgap.py` — Standalone PSF ASCII analyzer

### Verilog-A Model (`assets/va/`)
- `assets/va/va_bandgap.va` — Temperature-curved BGR macro-model using live `$temperature` with realistic parabolic curvature, supply turn-on headroom, startup RC, PSRR, and white + $1/f$ noise
