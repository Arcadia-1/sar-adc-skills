---
name: bandgap-skill
description: >
  Process-independent Bandgap Voltage Reference (BGR) design guide and Spectre
  verification toolkit. Covers classic Kuijk/Brokaw (~1.22 V) and Banba sub-1 V
  current-mode architectures, PTAT + CTAT cancellation, box-method temperature
  coefficient (ppm/C), 2nd-order Tsividis curvature, opamp offset amplification,
  5-bit resistor trimming (DNL/INL & +/-3 sigma centering), PTAT/CTAT/ZTC bias
  current generation (compliance, r_o, PSRR), positive-vs-negative core-loop
  feedback stability, brownout/glitch/slow-ramp dead-state immunity, EN cycling
  and startup-branch zero-leakage signoff, buffered load regulation & cap-kick
  recovery, 3 Verilog-A BGR models (3-pin macro, 5-pin breakable dual-feedback
  core, and 8-pin full signoff SoC BGR with fault injection), and 9 standalone
  Spectre tapeout-signoff testbenches. Use for any bandgap reference sizing,
  TC/offset budgeting, startup/brownout debugging, or Spectre signoff task.
---

# Bandgap Reference Skill

A process-independent engineering guide and Spectre tapeout-signoff toolkit for classic (`~1.22 V`) and sub-1 V (`~0.5–0.6 V`) bandgap voltage references and companion PTAT/CTAT/ZTC bias current generators.

## Read Order

- `references/bandgap-fundamentals.md`
  PTAT + CTAT cancellation, Kuijk/Brokaw vs. Banba sub-1 V current-mode BGR, box-method TC, Tsividis 2nd-order curvature, opamp offset amplification & 5-bit trimming, positive-vs-negative dual-feedback stability, startup dead-state & brownout immunity, buffered load regulation, and companion PTAT/CTAT/ZTC bias mirrors.
- `references/simulation-and-verification.md`
  Full 9-testbench Spectre signoff methodology: temperature/line sweeps, fast/slow/brownout/glitch startup & zero-leakage audit, `EN` cycling, 5-bit trim linearity & `±3σ` centering, load regulation & cap-kick recovery, companion `IPTAT`/`IZTC` compliance/PSRR & `V_os` TC sensitivity, `iprobe` core-loop `stb`, PSRR/noise budgeting, and fault-injection negative testing.

## Bundled Assets

### Spectre Testbenches (`assets/tb/`)
- `assets/tb/tb_bgr_temp_line.scs` — `-40..125°C` temperature sweep (`TC [ppm/C]`) + `0..1.4 V` supply line sweep
- `assets/tb/tb_bgr_startup.scs` — Power-up ramp transient (`ic VREF=0`) verifying dead-state immunity & startup time
- `assets/tb/tb_bgr_psrr_noise.scs` — AC `PSRR(f)` + integrated output `noise`
- `assets/tb/tb_bgr_stb.scs` — `iprobe` core-loop `stb` verifying negative feedback dominance, `T0`, `UGF`, `PM`, and `GM`
- `assets/tb/tb_bgr_trim_range.scs` — 5-bit trim sweep (`0..31`) + `±3σ` offset corners (`alter`) extracting span, LSB, DNL/INL, monotonicity, and `< 0.5 LSB` centering error
- `assets/tb/tb_bgr_brownout_glitch.scs` — Stress transient with deep brownout dip (`1.2 V -> 0.35 V -> 1.2 V`), short negative supply glitch, and ultra-slow `500 us` power-up ramp (`ic VREF=0`)
- `assets/tb/tb_bgr_en_startup_leak.scs` — `EN` cycling (`OFF -> ON -> OFF -> ON`) auditing shutdown leakage, wakeup/re-enable times, startup kick peak, and steady-state startup turn-off (`ISTART_MON`)
- `assets/tb/tb_bgr_load_cap_step.scs` — DC source/sink load sweep (`-100 uA..+100 uA`) + transient load-current pulse step into `C_L = 50 pF` extracting `R_out,DC`, droop, overshoot, and `0.5%` recovery time
- `assets/tb/tb_bgr_bias_currents.scs` — `-40..125°C` temp sweep + `0..1.2 V` compliance sweep + AC current-mirror PSRR of companion `IPTAT` & `IZTC` + `±3 mV` opamp `V_os` TC-sensitivity audit
- `assets/tb/analyze_bandgap.py` — Standalone PSF ASCII analyzer (`temp_line`, `startup`, `psrr_noise`, `stb`, `trim`, `brownout`, `en_leak`, `load_step`, `bias_currents`)

### Verilog-A Models (`assets/va/`)
- `assets/va/va_bandgap.va` — 3-pin temperature-curved BGR macro-model using live `$temperature` with parabolic curvature, supply headroom turn-on, startup RC, PSRR, and white + $1/f$ noise
- `assets/va/va_bgr_core.va` — 5-pin breakable dual-feedback BGR core model (`LOOP_OUT`/`LOOP_IN`) explicitly modeling the unit-PNP positive branch vs. $M\times$ PNP $+ R_1$ negative branch for `stb` stability analysis
- `assets/va/va_bgr_signoff.va` — 8-pin full signoff SoC BGR model (`VDD, EN, VTRIM, VREF, IPTAT, IZTC, ISTART_MON, VSS`) with 5-bit trim, PTAT-amplified opamp offset, bistable dead-state startup (`startup_en`, `fault_startup_leak` fault switches), `EN` shutdown leakage, closed-loop output buffer, and companion `IPTAT`/`IZTC` mirrors with compliance & PSRR
