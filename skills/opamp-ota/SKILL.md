---
name: opamp-ota-skill
description: >
  Process-independent OpAmp & OTA design guide and Spectre verification toolkit.
  Covers single-ended and fully differential topologies (5T OTA, telescopic
  cascode, folded cascode, two-stage Miller with nulling resistor Rz, CMFB
  continuous-time & switched-cap loops), exact pole/zero & slew-rate/settling
  equations, thermal & 1/f noise budgeting, FoM_S/FoM_L, 2 behavioral Verilog-A
  models, and 5 standalone Spectre testbenches (iprobe stb, lossless Tian
  diff_stb_probe DM+CM stb, 4-replica DC-servo CMRR/PSRR+/PSRR-/noise, and
  large-signal slew/settling). Use for any analog amplifier sizing, stability,
  CMFB, noise, or Spectre verification task.
---

# OpAmp & OTA Skill

A process-independent engineering guide and Spectre verification toolkit for single-ended and fully differential operational amplifiers and OTAs.

## Read Order

- `references/ota-topologies-and-sizing.md`
  5T OTA, telescopic/folded cascode, two-stage Miller opamp (`R_z` nulling resistor, poles/zeros), slew rate, linear settling, thermal/$1/f$ noise, and $\text{FoM}_S/\text{FoM}_L$.
- `references/fully-diff-and-cmfb.md`
  Fully differential OTAs, continuous-time vs. switched-capacitor CMFB, CMFB stability pitfalls, and standalone Tian balun DM+CM `stb` probing.
- `references/simulation-and-verification.md`
  Spectre verification methodology, DC-servo CMRR/PSRR+/PSRR−/noise setup, saturation audit, and bundled testbench usage.

## Bundled Assets

### Spectre Testbenches (`assets/tb/`)
Plug in external `models_corner.scs` + `dut_subckt.scs` (or smoke-test with repo-root `common/models_generic_bsim4.scs`):
- `assets/tb/single_ended/` — `tb_ota_stb_ac.scs`, `tb_ota_cmrr_psrr_noise.scs`, `tb_ota_slew_settle.scs`, `analyze_ota.py`
- `assets/tb/fully_diff/` — `tb_fd_ota_dm_cm_stb.scs` (lossless Tian balun DM+CM `stb`), `tb_fd_ota_slew_settle.scs`, `analyze_fd_ota.py`

### Verilog-A Behavioral Models (`assets/va/`)
- `assets/va/va_ota_2stage.va` — 2-stage Miller opamp with `r_z`, slew limiting, rail clamp, finite CMRR/PSRR, white + $1/f$ noise
- `assets/va/va_ota_fd_cmfb.va` — fully differential OTA with independent DM + CMFB poles/gains and thermal noise
