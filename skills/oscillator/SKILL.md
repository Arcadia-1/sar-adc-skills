---
name: oscillator
description: >
  Process-independent Crystal Oscillator (Pierce XO) and On-Chip RC Relaxation
  Oscillator design guide, Verilog-A behavioral model library, and standalone
  Spectre X / Spectre RF verification toolkit. Covers Butterworth-Van Dyke (BVD)
  quartz resonator modeling, Vittoz negative-resistance theory (gm_crit, gm_opt,
  C0 shunting), startup margin (|R_neg|/R_m >= 5x) & time constant, crystal
  drive level P_xtal (< 100 uW), symmetric load-cap trim pullability [ppm],
  full-Q autonomous Harmonic-Balance PSS + PNOISE & Leeson phase-noise/jitter
  optimization, plus dual-cap ping-pong RC relaxation oscillators, composite
  resistor TC compensation, comparator propagation-delay cancellation, 5-bit
  digital frequency trimming, cold-startup settling, and period/C2C thermal
  jitter budgets. Includes 2 Verilog-A models (`va_xo_amp`, `va_rc_osc`) and 7
  standalone Spectre decks across `xo/` and `rc_osc/` with zero-dependency PSF
  analyzers. Use for any crystal oscillator, Pierce XO, RC relaxation
  oscillator, negative-resistance, crystal drive-level, pullability, phase
  noise, or on-chip clock generator design or verification task.
---

# Crystal Oscillator (XO) & RC Relaxation Oscillator Skill

A process-independent engineering guide, Verilog-A behavioral model library, and standalone **Spectre X / Spectre RF** verification toolkit for fundamental-mode **Pierce Crystal Oscillators (XO)** and **On-Chip Dual-Cap RC Relaxation Oscillators**.

## Read Order

- `references/crystal-oscillator-xo.md`
  Butterworth–Van Dyke (BVD) quartz model, Vittoz small-signal negative resistance $-R_{\text{neg}}(\omega)$ with $C_0$ shunting, $g_{m,\text{crit}}$ & $g_{m,\text{opt}}$, startup margin ($\ge 5\times$) and $\tau_{\text{start}}$, crystal drive power $P_{\text{xtal}} < 100\ \mu\text{W}$, load-capacitance pullability ($\text{ppm/pF}$), Leeson phase noise, squaring buffer, and XO layout checklist.
- `references/rc-relaxation-oscillator.md`
  Single-cap vs. dual-cap ping-pong architectures, ratiometric $V_{\text{ref}}$ cancellation, composite positive+negative-TC resistor networks, comparator propagation-delay $t_{\text{cmp}}(T, V_{DD})$ error & cancellation loops, 5-bit digital trimming, cold `EN` startup dynamics, and analytical period vs. cycle-to-cycle ($\sqrt{2}$) thermal jitter budgets.
- `references/simulation-and-verification.md`
  Spectre X & Spectre RF testbench usage, verified behavioral & CMOS transistor benchmarks, and critical pitfalls (avoiding `ic=` on series `LM`, avoiding `+preset=cx` Gear-2 damping during high-$Q$ startup, full-$Q$ `flexbalance=yes oscic=lin` PSS+PNOISE, retaining $C_0$ in negative-resistance checks, and verifying max-$C_L$ margin).

## Bundled Assets

### Spectre Testbench Suites (`assets/tb/`)
Plug in external `models_corner.scs` + `dut_subckt.scs` (see `assets/tb/README.md`):
- `assets/tb/xo/` — 4 signoff decks (`subckt dut_xo_amp XI XO VDD VSS`): `tb_xo_neg_resistance.scs` (small-signal `-Re{Z_in(f)}` & `|R_neg|/R_m` startup margin with `C_0`), `tb_xo_startup_drive.scs` (`method=traponly` Q-scaled BVD startup envelope, swing & crystal drive level `P_xtal`), `tb_xo_pullability_cload.scs` (5-code `C_L` trim sweep on full-Q BVD solving exact `Im{Z_loop}=0` pullability `[ppm]` & worst-case margin), `tb_xo_pss_pnoise.scs` (full-Q autonomous Harmonic-Balance `pss + pnoise` SSB phase noise `L(df)` & RMS jitter `[fs]`), and `analyze_xo.py`
- `assets/tb/rc_osc/` — 3 signoff decks (`subckt dut_rc_osc VDD EN VTRIM OUT VSS`): `tb_rc_osc_temp_vdd.scs` (5-temp `-40..125 C` & 3-supply `0.9..1.1 VDD` PVT sweep), `tb_rc_osc_trim_startup.scs` (8-code 5-bit `VTRIM` sweep & `EN` rising-edge cold startup `1%` settling), `tb_rc_osc_jitter_duty.scs` (450+ cycle RMS/C2C period jitter, duty cycle & `10%-90%` edge times), and `analyze_rc_osc.py`

### Verilog-A Behavioral Models (`assets/va/`)
- `assets/va/va_xo_amp.va` — Zero-hidden-state $C^\infty$ smooth Pierce sustaining amplifier (`gm`, `i_max`, `r_out`, `r_fb`, `c_in`, `c_out`, thermal + `1/f` noise) supporting DC, AC, TRAN, and autonomous PSS + PNOISE
- `assets/va/va_rc_osc.va` — Dual-cap switched-RC relaxation oscillator (`tc1_rc`, `tc2_rc`, supply/temp-dependent `t_cmp0` with `delay_cancel_eff`, 5-bit `VTRIM`, cold-startup bias node `tau_start`, `duty_asym`, and exact `@(timer)` Gaussian `jitter_rms`)

> **LC-VCO, Ring-VCO, & DCO inside PLLs:** For RF/microwave tuning oscillators (`K_VCO`, multi-sub-band cap-bank overlap, FoM), see [`skills/pll/`](../pll/SKILL.md) (`../pll/references/vco-and-dco.md` and `../pll/assets/tb/vco/`).
