---
name: dac-skill
description: >
  Process-independent Digital-to-Analog Converter (DAC) design guide and Spectre
  verification toolkit. Covers Current-Steering DACs (segmented thermometer +
  binary, Pelgrom INL yield, Lin & Bult unit-cell output impedance Zout(f) vs.
  HD2/HD3 SFDR, switch crossing-point control, major-carry glitch impulse energy,
  RZ/DEM/DWA linearization, Q^2 random-walk layout), R-2R Ladder DACs, Resistor-
  String DACs, ZOH sinc roll-off & clock jitter budgets, 6 Verilog-A models
  (10-bit CS-DAC with r_cell/c_cell/t_skew/dm_msb, 10-bit segmented DWA/DEM
  CS-DAC with per-cell mismatch, PSRR, compliance & clock sampling, rising-edge
  clock jitter injector, 8-bit R-2R, ramp & coherent single/two-tone digital
  generators), and 9 standalone Spectre signoff testbenches (static DNL/INL,
  coherent single-tone SFDR/ENOB & two-tone IMD3, major-carry glitch impulse
  [pV*s] & 0.5-LSB settling, multi-frequency SFDR(f_in) sweep, dynamic supply
  PSRR & clock jitter sensitivity, output compliance & load-mismatch HD2, and
  DWA/DEM mismatch linearization, plus 2 R-2R decks). Use for any DAC
  architecture, mismatch yield, dynamic SFDR/IMD3, DEM/DWA, compliance, PSRR,
  jitter, glitch debugging, or Spectre verification task.
---

# Digital-to-Analog Converter (DAC) Skill

A process-independent engineering guide, Verilog-A behavioral model library, and standalone Spectre verification toolkit for high-speed Current-Steering DACs and R-2R Ladder DACs.

## Read Order

- `references/dac-architectures-and-sizing.md`
  Architecture selection matrix (Current-Steering, R-2R, Resistor-String, CDAC, $\Delta\Sigma$), thermometer+binary segmentation tradeoffs, Pelgrom INL yield sizing, R-2R switch-$R_{\text{on}}$ pitfalls, ZOH sinc attenuation, NSD, and clock-jitter ceilings.
- `references/current-steering-and-dynamic.md`
  Unit-cell output impedance $Z_{\text{unit}}(f)$ vs. single-ended HD2 and differential HD3/IMD3, cascode sizing, switch-pair crossing-point drivers, major-carry glitch impulse energy, RZ/DEM/DWA linearization, and $Q^2$ random-walk layout.
- `references/simulation-and-verification.md`
  Spectre static DNL/INL sweeps, coherent single-tone SFDR & two-tone IMD3 setup, `osr=1` vs. oversampled continuous-time FFT, major-carry glitch impulse extraction, and common Spectre verification traps.

## Bundled Assets

### Spectre Testbench Suites (`assets/tb/`)
Plug in external `models_corner.scs` + `dut_subckt.scs` (see `assets/tb/README.md`):
- `assets/tb/current_steering/` — 7 signoff decks: `tb_dac_static_dnl_inl.scs` (1024-code static DNL/INL), `tb_dac_dynamic_sfdr.scs` (coherent single-tone SFDR/HD2/HD3/ENOB & two-tone IMD3), `tb_dac_glitch_settle.scs` (major-carry `511 <-> 512` glitch impulse `[pV*s]` & `0.5 LSB` settling), `tb_dac_sfdr_vs_fin.scs` (4-frequency coherent Nyquist `SFDR(f_in)` & `Z_out(f)` roll-off sweep), `tb_dac_psrr_jitter.scs` (dynamic supply PSRR, `f_out +/- f_rip` sidebands & calibrated RMS clock-jitter sensitivity), `tb_dac_output_compliance.scs` (DC compliance headroom, `R_out` & `0% vs 2%` load-mismatch `HD2`), `tb_dac_dem_mismatch.scs` (static thermometer vs. first-order DWA/DEM mismatch shaping), and `analyze_cs_dac.py`
- `assets/tb/r2r/` — 2 signoff decks: `tb_r2r_static.scs` (256-code static DNL/INL), `tb_r2r_settle.scs` (full-scale & major-carry settling), and `analyze_r2r.py`

### Verilog-A Behavioral Models (`assets/va/`)
- `assets/va/va_dac_cs_10b.va` — 10-bit differential CS-DAC with code-dependent `r_cell`/`c_cell` (physical HD3!), MSB mismatch `dm_msb`, switching skew `t_skew` (physical major-carry glitch!), compliance clamp, and thermal noise
- `assets/va/va_dac_cs_dem_10b.va` — 10-bit segmented (4-bit thermometer MSB + 6-bit binary LSB) CS-DAC with per-cell mismatch array (`sigma_cell`, `seed`), switchable first-order DWA/DEM (`DEM_EN` / `dem_en`), charge-conserving `r_cell`/`c_cell` impedance, smooth `v_comp_max` compliance knee, supply modulation (`psrr_g`, `psrr_asym`), and rising-edge clock sampling (`clk_en`, `duty_hd2_k`)
- `assets/va/va_dac_clk_jitter.va` — Causal rising-edge Gaussian RMS clock jitter injector (`t_jitter_rms`) for dynamic DAC jitter verification
- `assets/va/va_dac_r2r_8b.va` — 8-bit voltage-mode R-2R ladder DAC with constant `r_unit + r_sw`, MSB mismatch `dm_msb`, and output cap `c_out`
- `assets/va/va_dac_ramp_gen_10b.va` — Clocked sequential 10-bit code ramp generator (`DIN[9:0]`, `CODE_MON`)
- `assets/va/va_dac_sine_gen_10b.va` — Clocked 10-bit coherent single-tone & two-tone IMD3 digital generator (`DIN[9:0]`, `CODE_MON`)

> **Capacitive DAC (CDAC) inside SAR ADCs:** For charge-redistribution CDACs, see [`skills/sar-adc/`](../sar-adc/SKILL.md) (`../sar-adc/references/cdac.md` and `../sar-adc/assets/tb/cdac/`).
