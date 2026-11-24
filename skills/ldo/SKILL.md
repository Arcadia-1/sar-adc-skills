---
name: ldo-skill
description: >
  Process-independent LDO linear voltage regulator design guide and Spectre
  verification toolkit. Covers external-cap PMOS-pass, output-capacitorless
  (capless/OCL), and NMOS-pass LDO architectures, dropout and pass-device
  sizing, light-load stability and ESR/Miller compensation, DC/mid-band/HF
  PSRR pathways, output impedance |Zout(f)|, noise decomposition, 2 Verilog-A
  macro-models (PMOS-pass with physical dropout + capless), and 4 standalone
  Spectre testbenches (DC line/load reg & dropout, iprobe stb, PSRR/Zout/noise,
  load & line step transient). Use for any LDO sizing, stability, PSRR, or
  Spectre verification task.
---

# LDO Regulator Skill

A process-independent engineering guide and full Spectre verification suite for PMOS-pass, capless (OCL), and NMOS-pass LDO regulators powering analog/mixed-signal domains (SAR ADCs, PLLs/VCOs, RF blocks, SoC rails).

## Read Order

- `references/ldo-architectures-and-sizing.md`
  External-cap vs. capless PMOS vs. NMOS-pass topologies, dropout sizing, quiescent current & efficiency, and line/load regulation formulas.
- `references/stability-psrr-noise.md`
  Pole-zero map, light-load stability trap, three-regime PSRR physics, and output noise decomposition.
- `references/simulation-and-verification.md`
  Full Spectre verification methodology, corner priorities, and signoff pass criteria.

## Bundled Assets

### Spectre Testbenches (`assets/tb/`)
- `assets/tb/tb_ldo_dc_reg_dropout.scs` — DC line regulation, load regulation, dropout voltage $V_{\text{DO}}$, and $I_Q$
- `assets/tb/tb_ldo_stb.scs` — `iprobe` loop stability (`T0`, `UGF`, `PM`, `GM`) across `iload_min..iload_max`
- `assets/tb/tb_ldo_psrr_zout_noise.scs` — Simultaneous AC `PSRR(f)`, closed-loop $|Z_{\text{out}}(f)|$, and integrated output `noise`
- `assets/tb/tb_ldo_load_line_tran.scs` — Sequential load-step and line-step transient
- `assets/tb/analyze_ldo.py` — Standalone PSF ASCII analyzer

### Verilog-A Models (`assets/va/`)
- `assets/va/va_ldo_pmos.va` — PMOS-pass LDO with physical triode dropout knee, Miller + `r_z`, white + $1/f$ noise, and breakable `FB_IN`
- `assets/va/va_ldo_capless.va` — On-chip capless (OCL) LDO macro-model
