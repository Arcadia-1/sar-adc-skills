---
name: ldo-skill
description: >
  Process-independent LDO linear voltage regulator design guide and industrial
  Spectre verification toolkit. Covers external-cap PMOS-pass, output-capacitorless
  (capless/OCL), and NMOS-pass LDO architectures, dropout and pass-device sizing,
  light-load stability and 2D Load x ESR stability tunnels, DC/mid-band/HF and
  large-signal dynamic PSRR, output impedance |Zout(f)|, noise decomposition,
  soft-start inrush and active discharge, foldback over-current protection,
  temperature drift and shutdown leakage, 3 Verilog-A macro-models (PMOS-pass,
  capless, and full signoff model), and 9 standalone Spectre testbenches. Use for
  any LDO sizing, compensation, stability, PSRR, protection, or Spectre signoff task.
---

# LDO Regulator Skill

A process-independent engineering guide and 9-testbench Spectre signoff suite for PMOS-pass, capless (OCL), and NMOS-pass LDO regulators powering analog/mixed-signal domains (SAR ADCs, PLLs/VCOs, RF blocks, SoC rails).

## Read Order

- `references/ldo-architectures-and-sizing.md`
  External-cap vs. capless PMOS vs. NMOS-pass topologies, dropout sizing, quiescent current & efficiency, and line/load regulation formulas.
- `references/stability-psrr-noise.md`
  Pole-zero map, light-load stability trap, three-regime PSRR physics, and output noise decomposition.
- `references/simulation-and-verification.md`
  Full 9-testbench Spectre signoff methodology, ESR stability tunnel physics, foldback latch-up rules, brown-out recovery, corner priorities, and pass criteria.

## Bundled Assets

### Spectre Testbenches (`assets/tb/`)
- `assets/tb/tb_ldo_dc_reg_dropout.scs` — DC line regulation, load regulation, dropout voltage $V_{\text{DO}}$, and $I_Q$
- `assets/tb/tb_ldo_stb.scs` — `iprobe` loop stability (`T0`, `UGF`, `PM`, `GM`) across `iload_min..iload_max`
- `assets/tb/tb_ldo_psrr_zout_noise.scs` — Simultaneous AC `PSRR(f)`, closed-loop $|Z_{\text{out}}(f)|$, and integrated output `noise`
- `assets/tb/tb_ldo_load_line_tran.scs` — Sequential load-step and line-step transient
- `assets/tb/tb_ldo_startup_inrush.scs` — `EN` soft-start ramp, capacitive inrush peak, monotonicity, overshoot, and `EN` falling active discharge
- `assets/tb/tb_ldo_ocp_foldback.scs` — DC foldback `I-V` sweep (`i_lim_peak`, `i_short`, foldback ratio) + hard-short transient recovery
- `assets/tb/tb_ldo_stb_esr_grid.scs` — 9-point 2D Load (`10 uA`, `1 mA`, `10 mA`) $\times$ ESR (`5 mOhm`, `200 mOhm`, `5 Ohm`) stability tunnel (`alter` + `stb`)
- `assets/tb/tb_ldo_dropout_tran.scs` — Deep `VDD` brown-out dip into dropout & triode-exit recovery overshoot + large-signal `100 mVpp` dynamic PSRR
- `assets/tb/tb_ldo_temp_shdn.scs` — `-40..125 C` temperature drift, multi-decade $I_Q(I_{\text{load}})$ efficiency, and `EN = 0` shutdown leakage across temperature
- `assets/tb/analyze_ldo.py` — Standalone PSF ASCII analyzer (`dc_reg`, `stb`, `psrr_zout_noise`, `tran`, `startup`, `ocp`, `esr_grid`, `dropout_tran`, `temp_shdn`)

### Verilog-A Models (`assets/va/`)
- `assets/va/va_ldo_pmos.va` — PMOS-pass LDO with physical triode dropout knee, Miller + `r_z`, white + $1/f$ noise, and breakable `FB_IN`
- `assets/va/va_ldo_capless.va` — On-chip capless (OCL) LDO macro-model
- `assets/va/va_ldo_signoff.va` — Full signoff PMOS-pass LDO with `EN`, soft-start ramp (`t_ss`), active discharge (`r_disch`), smooth foldback OCP (`i_lim`, `i_sc`), load-dependent EKV $g_m(I)/r_o(I)$, EA slew limiting, tempco (`tc_vout`, `tc_iq`), and Arrhenius shutdown leakage (`i_shdn`)
