---
name: dcdc-buck
description: >
  Process-independent synchronous step-down Buck DC-DC converter design guide
  and 8-testbench industrial Spectre X verification suite. Covers CCM and DCM
  (ZCD) physics, inductor/capacitor/ESR filter sizing, 6-component power-loss
  budgeting, power-FET optimization, dead-time shoot-through vs. body-diode
  conduction tradeoffs, Peak Current-Mode Control (PCMC) with slope
  compensation, exact Erickson-Maksimovic/Ridley state-space averaged small-
  signal modeling, Type-II loop compensation, audio-susceptibility PSRR(f),
  coherent switching-spur FFT, cold soft-start inrush, load/line-step
  transients, and cycle-by-cycle OCP short-circuit recovery. Includes 3
  Verilog-A models and 8 standalone Spectre X decks. Use for any Buck DC-DC
  sizing, compensation, efficiency, dead-time, protection, or Spectre X
  verification task.
---

# Synchronous Buck DC-DC Converter Skill

A process-independent engineering guide and 8-testbench **Spectre X** verification suite for integrated synchronous step-down Buck DC-DC converters (`V_in = 3.3 V`, `V_out = 1.2 V`, `f_sw = 2 MHz`, `L = 2.2 uH`, `C_out = 10 uF`, `I_load = 5..500 mA`).

> **Related Power & Reference Skills:** For post-regulation linear stages downstream of a switching Buck rail, see `../ldo/SKILL.md`. For the on-chip bandgap reference supplying `VREF`, see `../bandgap/SKILL.md`.

## Read Order

- `references/buck-fundamentals-and-losses.md`
  Volt-second balance, inductor & output ripple equations, CCM/DCM boundary & ZCD, 6-component loss budget, optimal FET sizing, and dead-time shoot-through vs. body-diode physics.
- `references/control-loop-and-compensation.md`
  VMC vs. PCMC, subharmonic oscillation & slope compensation, exact Erickson-Maksimovic/Ridley averaged model, Type-II compensator sizing, load-step energy limits, PSRR, soft-start inrush, and OCP/LEB rules.
- `references/simulation-and-verification.md`
  Full 8-testbench Spectre X verification flow, fault-injection negative tests, BSIM4 transistor half-bridge plug-in contract, signoff pass criteria, worst-case corners, and common pitfalls.

## Bundled Assets

### Spectre X Testbenches (`assets/tb/`)
- `assets/tb/README.md` — Suite index, commands, and transistor-level plug-in subcircuit contracts
- `assets/tb/tb_buck_eff_ccm_dcm.scs` — 4-load `alter` + `tran` efficiency sweep (`20 mA` DCM to `500 mA` CCM)
- `assets/tb/tb_buck_ripple_sw.scs` — High-resolution steady-state CCM ripple & `SW` overshoot/undershoot with `l_par`
- `assets/tb/tb_buck_softstart_inrush.scs` — Cold `EN` soft-start ramp, inductor inrush peak, monotonicity & overshoot
- `assets/tb/tb_buck_load_line_tran.scs` — Fast DCM/CCM load step (`50 -> 400 -> 50 mA`) + line step (`3.3 -> 4.2 -> 3.3 V`)
- `assets/tb/tb_buck_loop_stb.scs` — 4-corner ($V_{\text{in}} \times I_{\text{load}}$) averaged `iprobe` `stb` loop stability
- `assets/tb/tb_buck_ocp_short.scs` — Hard `0.2 Ohm` output short-circuit cycle-by-cycle OCP clamp & recovery
- `assets/tb/tb_buck_psrr_noise.scs` — Averaged audio-susceptibility `PSRR(f)` (`ac`) + coherently strobed switching `VOUT` FFT
- `assets/tb/tb_buck_deadtime_shoot.scs` — 3-regime dead-time sweep (`-5 ns` shoot-through, `10 ns` optimal, `60 ns` body-diode loss)
- `assets/tb/analyze_buck.py` — Standalone zero-dependency PSF ASCII analyzer (`efficiency`, `ripple`, `softstart`, `tran`, `stb`, `ocp`, `psrr_spur`, `deadtime`)

### Verilog-A Behavioral Models (`assets/va/`)
- `assets/va/va_buck_power_stage.va` — Synchronous CMOS half-bridge with passive Miller $C_{gd}$/$C_{gs}$ drivers, square-law zero-leakage switches, body diodes, and monotonic ZCD for DCM
- `assets/va/va_buck_controller.va` — Peak Current-Mode (PCMC) PWM controller with soft-start, OTA error amplifier, slope compensation, LEB, cycle-by-cycle OCP, and configurable dead-time
- `assets/va/va_buck_avg_model.va` — Exact continuous state-space averaged PCMC Buck + Ridley $f_{\text{sw}}/2$ sampling double-pole for instant `dc`/`ac`/`stb`
