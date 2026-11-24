---
name: opamp-ota-skill
description: >
  Process-independent OpAmp & OTA design guide and Spectre X signoff toolkit.
  Covers single-ended and fully differential topologies (5T OTA, telescopic
  cascode, folded cascode, two-stage Miller with nulling resistor Rz, CMFB
  continuous-time & switched-cap loops), exact pole/zero & slew-rate/settling
  equations, thermal & 1/f noise budgeting, FoM_S/FoM_L, 2 behavioral Verilog-A
  models, and 16 standalone Spectre X testbenches covering a full 29-item
  industrial characterization matrix (iprobe & lossless Tian diff_stb_probe
  DM+CM stb, 5-replica DC-servo CMRR/4R-bridge/PSRR+/PSRR-/noise, multi-method
  ICMR & swing-vs-RL & VIDR phase reversal, closed-loop AC/group-delay/Zout/
  Zout_cm/Zin/OTA gm, large-signal slew/settling, coherent THD/HD2/HD3/BW_full,
  power-ramp & supply-surge/CM-step robustness). Use for any analog amplifier
  sizing, stability, CMFB, noise, or Spectre X signoff verification task.
---

# OpAmp & OTA Skill

A process-independent engineering guide and **Spectre X (`+preset=cx`)** signoff verification toolkit for single-ended and fully differential operational amplifiers and OTAs.

## Read Order

- `references/ota-topologies-and-sizing.md`
  5T OTA, telescopic/folded cascode, two-stage Miller opamp (`R_z` nulling resistor, poles/zeros), slew rate, linear settling, thermal/$1/f$ noise, and $\text{FoM}_S/\text{FoM}_L$.
- `references/fully-diff-and-cmfb.md`
  Fully differential OTAs, continuous-time vs. switched-capacitor CMFB, CMFB stability pitfalls, and standalone Tian balun DM+CM `stb` probing.
- `references/signoff-testbench-methodology.md`
  Complete 29-item / 36-metric industrial signoff matrix (SE & FD), multi-definition ICMR reconciliation, 4-resistor CMRR bridge artifacts on high-$R_{\text{out}}$ OTAs, OTA $g_m(f)$ sensing, FD symmetry pitfalls, coherent THD/$\text{BW}_{\text{full}}$, and supply-integrity verification.
- `references/simulation-and-verification.md`
  Spectre X (`+preset=cx`) verification guide, complete deck/analyzer summary, and quick simulation pitfall checklist.

## Bundled Assets

### Spectre X Signoff Testbenches (`assets/tb/`)
Plug in external `models_corner.scs` + `dut_subckt.scs` (or smoke-test with repo-root `common/models_generic_bsim4.scs` / bundled Verilog-A models):
- `assets/tb/single_ended/` — 8 `.scs` decks (`tb_ota_stb_ac.scs`, `tb_ota_cmrr_psrr_noise.scs`, `tb_ota_dc_signoff.scs`, `tb_ota_cl_zout_gm.scs`, `tb_ota_slew_settle.scs`, `tb_ota_thd_fpbw.scs`, `tb_ota_power_ramp.scs`, `tb_ota_supply_surge_cmstep.scs`) + `analyze_ota.py`
- `assets/tb/fully_diff/` — 8 `.scs` decks (`tb_fd_ota_dm_cm_stb.scs`, `tb_fd_ota_cmrr_psrr_noise.scs`, `tb_fd_ota_dc_signoff.scs`, `tb_fd_ota_cl_zout_gm.scs`, `tb_fd_ota_slew_settle.scs`, `tb_fd_ota_thd_fpbw.scs`, `tb_fd_ota_power_ramp.scs`, `tb_fd_ota_supply_surge_cmstep.scs`) + `analyze_fd_ota.py`

### Verilog-A Behavioral Models (`assets/va/`)
- `assets/va/va_ota_2stage.va` — 2-stage Miller opamp with `r_z`, slew limiting, smooth rail clamp, finite ICMR & VDD turn-on, offset/tempco, CMRR/PSRR+/PSRR−, input capacitance, and white + $1/f$ noise
- `assets/va/va_ota_fd_cmfb.va` — fully differential OTA with independent DM + CMFB poles/gains, finite ICMR & VDD turn-on, CM→CM & supply→CM feedthrough, smooth rail clamp, and white + $1/f$ noise
