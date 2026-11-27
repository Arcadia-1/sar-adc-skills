# ams-skills

Process-independent Analog & Mixed-Signal (AMS) IC design skills, Verilog-A behavioral model libraries, and standalone **Spectre X** testbench suites for agentic IC design.

> Formerly `sar-adc-skills` — organized into a clean, non-overlapping multi-skill AMS repository where every circuit domain is an independently installable AI agent skill sharing a unified, process-independent Spectre verification foundation.

## Included Skills (10 Domains)

See [`skills/README.md`](skills/README.md) for the full domain taxonomy and canonical directory contract.

| Domain | Skill | Coverage | Refs | Verilog-A | Spectre TBs | Evals |
|---|---|---|---|---|---|---|
| **Data Converters** | [**`skills/sar-adc/`**](skills/sar-adc/SKILL.md) | SAR ADC architecture, CDAC (binary & sub-radix-2), StrongARM & Miyahara comparators, bootstrapped switch, sync/async SAR logic, coherent FFT & ramp DNL/INL | 10 | 18 (`behavioral_10b/` + `tutorial_4b/` + block models) | 5 suites (`comparator`, `bootstrap`, `cdac`, `sar_logic`, `adc_top` — 20 `.scs` decks) | 34 |
| **Data Converters** | [**`skills/dac/`**](skills/dac/SKILL.md) | Current-Steering (segmented thermometer+binary, Pelgrom INL yield, $Z_{\text{out}}(f)$ Nyquist SFDR sweep, dynamic PSRR/jitter, output compliance, DWA/DEM mismatch shaping, glitch impulse) & R-2R Ladder DACs | 3 | 6 models | 2 suites (`current_steering`, `r2r` — 9 `.scs` decks) | 16 |
| **Clocking & RF** | [**`skills/pll/`**](skills/pll/SKILL.md) | Integer-N CP-PLL, Fractional-N $\Delta\Sigma$ (MASH 1-1-1) PLL, All-Digital PLL (TDC-ADPLL & Bang-Bang ADPLL), multi-band LC/Ring VCO & DCO, PFD/CP compliance, TSPC/MMD, AFC band-cal & lock-detect, ref-spur FFT, PSRR, noise budget & $N \times I_{\text{CP}}$ scaling | 7 | 12 models | 7 suites (`vco`, `pfd_cp`, `divider`, `tdc_dco`, `int_n_pll`, `frac_n_pll`, `adpll` — 17 `.scs` decks) | 22 |
| **Clocking & RF** | [**`skills/oscillator/`**](skills/oscillator/SKILL.md) | Fundamental-mode Pierce Crystal Oscillators (BVD model, Vittoz negative-$R$ & $C_0$ shunting, $\ge 5\times$ startup margin, drive level $P_{\text{xtal}} < 100\ \mu\text{W}$, $C_L$ pullability, full-$Q$ PSS+PNOISE) & On-Chip Dual-Cap RC Relaxation Oscillators (composite TC, comparator-delay cancellation, 5-bit trim & cold startup, period/C2C jitter & duty) | 3 | 2 models | 2 suites (`xo`, `rc_osc` — 7 `.scs` decks) | 12 |
| **Wireline / SerDes** | [**`skills/serdes/`**](skills/serdes/SKILL.md) | Causal lossy channels (`SDD21`/`SDD11`/`SCD21`/TDR/SBR/`nport` `.s4p`/FEXT-NEXT), CML/VML TX & 4-tap FFE, `R_term(V)`, CTLE/VGA peaking/`P1dB`/`HD3`/noise/offset cal, slicers (`trannoise`/`Clk-to-Q`/SH/VTF) & 3-tap DFE, SS-LMS, bridged T-coil ($2.83\times$ BW), CDR (BBPD/PI/JTF/JTOL), PAM4 (RLM/3-eye/1-tap DFE), half-rate DCD/IQ skew & `BER=1e-12` jitter bathtub, full link top | 6 | 15 models | 10 suites (`channel`, `tx_ffe`, `ctle_vga`, `slicer_dfe`, `sslms`, `tcoil`, `cdr`, `pam4`, `clocking_jitter`, `link_top` — 35 TB decks) | 37 |
| **Analog Core** | [**`skills/opamp-ota/`**](skills/opamp-ota/SKILL.md) | Single-ended & fully differential OpAmps/OTAs (5T, telescopic, folded cascode, 2-stage Miller + `R_z`, CMFB), 29-item industrial signoff suite (`iprobe`/Tian DM+CM `stb`, CMRR/4R-bridge/PSRR±/noise, multi-method ICMR/swing-vs-$R_L$/VIDR, $Z_{\text{out,DM}}$/$Z_{\text{out,CM}}$/OTA $g_m$, slew, coherent THD/$\text{BW}_{\text{full}}$, power-ramp & supply-surge) | 4 | 2 models | 2 suites (`single_ended`, `fully_diff` — 18 `.scs` decks) | 20 |
| **Power & Reference** | [**`skills/ldo/`**](skills/ldo/SKILL.md) | External-cap PMOS-pass, capless (OCL), and NMOS-pass LDOs: dropout, line/load reg, 9-pt ESR stability tunnel, soft-start/inrush, foldback OCP short recovery, large-signal dropout transient, PSRR(f)/$|Z_{\text{out}}(f)|$/noise, temp & shutdown leakage | 3 | 3 models | 1 suite (9 `.scs` decks) | 15 |
| **Power & Reference** | [**`skills/dcdc-buck/`**](skills/dcdc-buck/SKILL.md) | Synchronous Step-Down Buck DC-DC Converters: DCM/CCM efficiency & 6-term loss budget, ripple & SW stress, soft-start inrush, DCM/CCM load & line steps, PCMC slope comp & 4-corner averaged `stb`, cycle-by-cycle OCP short recovery, `PSRR(f)` & coherent switching-spur FFT, dead-time shoot-through vs. body-diode sweep | 3 | 3 models | 1 suite (8 `.scs` decks) | 12 |
| **Power & Reference** | [**`skills/bandgap/`**](skills/bandgap/SKILL.md) | Classic Kuijk/Brokaw (~1.22 V) & Banba sub-1 V bandgap references: PTAT+CTAT curvature TC (`ppm/C`), 5-bit digital trim, brownout/glitch dead-state recovery, EN startup turn-off audit, load/cap step, companion `I_PTAT`/`I_ZTC` bias & `V_os` TC sensitivity, `stb`, PSRR/noise | 2 | 3 models | 1 suite (9 `.scs` decks) | 15 |
| **Power & Reference** | [**`skills/supervisor/`**](skills/supervisor/SKILL.md) | Nano-power Power-On Reset (POR), 3-bit programmable Brown-Out Reset (BOR), ratiometric BJT/CMOS On-Chip Temperature Sensor, & hysteretic Over-Temperature Shutdown (TSD): thresholds/hysteresis, low-VDD clamp, 3-decade ramp rates, glitch immunity, `-40..125°C` 1-pt/2-pt curvature, `°C/V` PSRR, `mK_rms` noise & chopping | 3 | 2 models | 2 suites (`por_bor`, `temp_sensor` — 7 `.scs` decks) | 12 |

## Shared Verification Foundation (`common/`)

All 10 skills share a single, zero-PDK verification core under [`common/`](common/README.md):

- **[`common/psf_utils.py`](common/psf_utils.py)** — Zero-dependency Python (`numpy` only) Spectre PSF ASCII parser (real `tran`/`dc`/`noise`/`pss`/`pnoise` + complex `ac`/`stb`/`sp`), `extract_uniform_strobe`, coherent single-tone FFT (`ENOB`/`SNDR`/`SNR`/`SFDR`/`THD`/`HD2`/`HD3`), coherent two-tone `IMD3`, endpoint `DNL`/`INL`, IEEE-1139 phase-noise-to-RMS-jitter integration, and SerDes `SBR`/`eye`/`mixed-mode S-param` extractors.
- **[`common/models_generic_bsim4.scs`](common/models_generic_bsim4.scs)**, **[`common/models_sky130_minimal.scs`](common/models_sky130_minimal.scs)**, & **[`common/models_asap7_minimal.scs`](common/models_asap7_minimal.scs)** — Open-source foundry-free BSIM4, SkyWater 130 nm silicon-calibrated BSIM4.5 (Apache-2.0), and ASAP7 7 nm FinFET BSIM-CMG (BSD-3-Clause) minimal TT Spectre models.
- **[`common/tb/`](common/tb/README.md)** — Universal foundry-free Spectre X utilities: NMOS/PMOS $g_m/I_D$ characterization (`tb_gmid_nmos_pmos.scs`), Spectre `montecarlo` mismatch offset template (`tb_mc_offset_template.scs`), PVT sweep + batched Monte Carlo wrapper with a MOS saturation audit (`tb_pvt_mc_wrapper_template.scs`, `analyze_op_region.py`), and 5-stage CMOS ring-oscillator PVT speed monitor (`tb_ring_process_mon.scs`).

All guides, Verilog-A models, and Spectre testbenches are **100% process-independent** and verified with **Spectre X (`+preset=cx` / `+preset=ax`)** — plug in your own PDK `models_corner.scs` + `dut_subckt.scs` for real process sizing and signoff.

## Quick Start

Install all 10 skills (or only the domains you need) using [`scripts/install_skills.sh`](scripts/install_skills.sh):

```bash
# Install all skills into .claude/skills (default)
./scripts/install_skills.sh

# Or install a subset into Codex / Antigravity / Claude skills directory
./scripts/install_skills.sh --target ~/.codex/skills sar-adc dac serdes bandgap
```

Run the offline multi-skill validation suite (hierarchy contract, leak scan, schema, links, `ahdl_include` paths, Python syntax, CLI `--help` & unit tests):

```bash
python3 -B scripts/validate_repo.py
```

## Skill Details

### 1. SAR ADC Skill (`skills/sar-adc/`)
- **References**: [core-architecture.md](skills/sar-adc/references/core-architecture.md), [design-and-tradeoffs.md](skills/sar-adc/references/design-and-tradeoffs.md), [robustness-and-system.md](skills/sar-adc/references/robustness-and-system.md), [cdac.md](skills/sar-adc/references/cdac.md), [comparator.md](skills/sar-adc/references/comparator.md), [bootstrap_switch.md](skills/sar-adc/references/bootstrap_switch.md), [sar-logic.md](skills/sar-adc/references/sar-logic.md), [ldo.md](skills/sar-adc/references/ldo.md), [integration.md](skills/sar-adc/references/integration.md), [simulation-and-verification.md](skills/sar-adc/references/simulation-and-verification.md).
- **Spectre TBs** ([index](skills/sar-adc/assets/tb/README.md)): [comparator/](skills/sar-adc/assets/tb/comparator/README.md), [bootstrap/](skills/sar-adc/assets/tb/bootstrap/README.md), [cdac/](skills/sar-adc/assets/tb/cdac/README.md), [sar_logic/](skills/sar-adc/assets/tb/sar_logic/README.md), [adc_top/](skills/sar-adc/assets/tb/adc_top/README.md).
- **Verilog-A** ([index](skills/sar-adc/assets/va/README.md)): 6 10-bit non-ideality-injectable models (`behavioral_10b/`) + 7 baseline 4-bit tutorial models (`tutorial_4b/`).

### 2. DAC Skill (`skills/dac/`)
- **References**: [dac-architectures-and-sizing.md](skills/dac/references/dac-architectures-and-sizing.md), [current-steering-and-dynamic.md](skills/dac/references/current-steering-and-dynamic.md), [simulation-and-verification.md](skills/dac/references/simulation-and-verification.md).
- **Spectre TBs** ([index](skills/dac/assets/tb/README.md)): [current_steering/](skills/dac/assets/tb/current_steering/README.md) (7 `.scs` decks) & [r2r/](skills/dac/assets/tb/r2r/README.md) (2 `.scs` decks).
- **Verilog-A**: `va_dac_cs_10b`, `va_dac_cs_dem_10b`, `va_dac_clk_jitter`, `va_dac_r2r_8b`, `va_dac_ramp_gen_10b`, `va_dac_sine_gen_10b`.

### 3. PLL Skill (`skills/pll/`)
- **References**: [pll-fundamentals.md](skills/pll/references/pll-fundamentals.md), [integer-n-pll.md](skills/pll/references/integer-n-pll.md), [fractional-n-pll.md](skills/pll/references/fractional-n-pll.md), [adpll.md](skills/pll/references/adpll.md), [vco-and-dco.md](skills/pll/references/vco-and-dco.md), [pfd-cp-divider.md](skills/pll/references/pfd-cp-divider.md), [simulation-and-verification.md](skills/pll/references/simulation-and-verification.md).
- **Spectre TBs** ([index](skills/pll/assets/tb/README.md)): [vco/](skills/pll/assets/tb/vco/README.md), [pfd_cp/](skills/pll/assets/tb/pfd_cp/README.md), [divider/](skills/pll/assets/tb/divider/README.md), [tdc_dco/](skills/pll/assets/tb/tdc_dco/README.md), [int_n_pll/](skills/pll/assets/tb/int_n_pll/README.md), [frac_n_pll/](skills/pll/assets/tb/frac_n_pll/README.md), [adpll/](skills/pll/assets/tb/adpll/README.md).
- **Verilog-A**: `va_pfd`, `va_cp`, `va_vco`, `va_vco_multiband`, `va_bandcal_lockdet`, `va_div_int`, `va_mmd_mash111`, `va_tdc`, `va_dco`, `va_dlf_pi`, `va_bbpd`, `va_phase_err_mon`.

### 4. SerDes / Wireline Skill (`skills/serdes/`)
- **References**: [serdes-architecture-and-channel.md](skills/serdes/references/serdes-architecture-and-channel.md), [tx-cml-vml-and-ffe.md](skills/serdes/references/tx-cml-vml-and-ffe.md), [rx-ctle-vga-and-offset.md](skills/serdes/references/rx-ctle-vga-and-offset.md), [dfe-slicer-and-sslms.md](skills/serdes/references/dfe-slicer-and-sslms.md), [cdr-pam4-and-clocking.md](skills/serdes/references/cdr-pam4-and-clocking.md), [simulation-and-verification.md](skills/serdes/references/simulation-and-verification.md).
- **Spectre X TBs** ([index](skills/serdes/assets/tb/README.md)): [channel/](skills/serdes/assets/tb/channel/README.md), [tx_ffe/](skills/serdes/assets/tb/tx_ffe/README.md), [ctle_vga/](skills/serdes/assets/tb/ctle_vga/README.md), [slicer_dfe/](skills/serdes/assets/tb/slicer_dfe/README.md), [sslms/](skills/serdes/assets/tb/sslms/README.md), [tcoil/](skills/serdes/assets/tb/tcoil/README.md), [cdr/](skills/serdes/assets/tb/cdr/README.md), [pam4/](skills/serdes/assets/tb/pam4/README.md), [clocking_jitter/](skills/serdes/assets/tb/clocking_jitter/README.md), [link_top/](skills/serdes/assets/tb/link_top/README.md).
- **Verilog-A**: `va_prbs_gen`, `va_tx_ffe_4tap`, `va_ctle_vga`, `va_slicer_cml`, `va_dfe_3tap`, `va_sslms_adapt`, `va_offset_cal_fsm`, `va_channel_isi`, `va_bbpd_serdes`, `va_phase_interp`, `va_cdr_loop`, `va_pam4_gen`, `va_pam4_tx`, `va_pam4_dfe_slicer`, `va_clk_dcd_iq`.

### 5. OpAmp & OTA Skill (`skills/opamp-ota/`)
- **References**: [ota-topologies-and-sizing.md](skills/opamp-ota/references/ota-topologies-and-sizing.md), [fully-diff-and-cmfb.md](skills/opamp-ota/references/fully-diff-and-cmfb.md), [signoff-testbench-methodology.md](skills/opamp-ota/references/signoff-testbench-methodology.md), [simulation-and-verification.md](skills/opamp-ota/references/simulation-and-verification.md).
- **Spectre X Signoff TBs** ([index](skills/opamp-ota/assets/tb/README.md)): [single_ended/](skills/opamp-ota/assets/tb/single_ended/README.md) (8 `.scs` decks) & [fully_diff/](skills/opamp-ota/assets/tb/fully_diff/README.md) (10 `.scs` decks).
- **Verilog-A**: `va_ota_2stage`, `va_ota_fd_cmfb`.

### 6. LDO Regulator Skill (`skills/ldo/`)
- **References**: [ldo-architectures-and-sizing.md](skills/ldo/references/ldo-architectures-and-sizing.md), [stability-psrr-noise.md](skills/ldo/references/stability-psrr-noise.md), [simulation-and-verification.md](skills/ldo/references/simulation-and-verification.md).
- **Spectre TBs**: [assets/tb/](skills/ldo/assets/tb/README.md) (9 `.scs` decks: DC reg/dropout, `stb`, 9-pt ESR tunnel, PSRR/`|Zout|`/`noise`, load/line step, soft-start/inrush, foldback OCP, dropout transient, temp/shutdown + `analyze_ldo.py`).
- **Verilog-A**: `va_ldo_pmos`, `va_ldo_capless`, `va_ldo_signoff`.

### 7. Synchronous Buck DC-DC Converter Skill (`skills/dcdc-buck/`)
- **References**: [buck-fundamentals-and-losses.md](skills/dcdc-buck/references/buck-fundamentals-and-losses.md), [control-loop-and-compensation.md](skills/dcdc-buck/references/control-loop-and-compensation.md), [simulation-and-verification.md](skills/dcdc-buck/references/simulation-and-verification.md).
- **Spectre X TBs**: [assets/tb/](skills/dcdc-buck/assets/tb/README.md) (`tb_buck_eff_ccm_dcm.scs`, `tb_buck_ripple_sw.scs`, `tb_buck_softstart_inrush.scs`, `tb_buck_load_line_tran.scs`, `tb_buck_loop_stb.scs`, `tb_buck_ocp_short.scs`, `tb_buck_psrr_noise.scs`, `tb_buck_deadtime_shoot.scs`, `analyze_buck.py`).
- **Verilog-A**: `va_buck_power_stage`, `va_buck_controller`, `va_buck_avg_model`.

### 8. Bandgap Reference Skill (`skills/bandgap/`)
- **References**: [bandgap-fundamentals.md](skills/bandgap/references/bandgap-fundamentals.md), [simulation-and-verification.md](skills/bandgap/references/simulation-and-verification.md).
- **Spectre TBs**: [assets/tb/](skills/bandgap/assets/tb/README.md) (9 `.scs` decks: temp/line, startup, PSRR/noise, `stb`, 5-bit trim, brownout/glitch, EN startup-leak audit, load/cap step, companion `I_PTAT`/`I_ZTC` bias + `analyze_bandgap.py`).
- **Verilog-A**: `va_bandgap`, `va_bgr_core`, `va_bgr_signoff`.

### 9. Supervisor (POR/BOR & Temperature Sensor / TSD) Skill (`skills/supervisor/`)
- **References**: [por-bor-design.md](skills/supervisor/references/por-bor-design.md), [temperature-sensor-and-tsd.md](skills/supervisor/references/temperature-sensor-and-tsd.md), [simulation-and-verification.md](skills/supervisor/references/simulation-and-verification.md).
- **Spectre X TBs** ([index](skills/supervisor/assets/tb/README.md)): [por_bor/](skills/supervisor/assets/tb/por_bor/README.md) (4 decks: thresholds/hysteresis, 3-decade ramps, glitch immunity, 3-bit BOR levels) & [temp_sensor/](skills/supervisor/assets/tb/temp_sensor/README.md) (3 decks: `-40..125°C` linearity/curvature, supply sensitivity/noise/chopping, hysteretic TSD).
- **Verilog-A**: `va_por_bor`, `va_temp_sensor_tsd`.

### 10. Oscillator Skill (`skills/oscillator/`)
- **References**: [crystal-oscillator-xo.md](skills/oscillator/references/crystal-oscillator-xo.md), [rc-relaxation-oscillator.md](skills/oscillator/references/rc-relaxation-oscillator.md), [simulation-and-verification.md](skills/oscillator/references/simulation-and-verification.md).
- **Spectre X / RF TBs** ([index](skills/oscillator/assets/tb/README.md)): [xo/](skills/oscillator/assets/tb/xo/README.md) (4 `.scs` decks + `analyze_xo.py`) & [rc_osc/](skills/oscillator/assets/tb/rc_osc/README.md) (3 `.scs` decks + `analyze_rc_osc.py`).
- **Verilog-A**: `va_xo_amp`, `va_rc_osc`.

## Repository Layout

```text
ams-skills/
├── common/                       # Shared PSF parser, open-source Sky130/ASAP7/BSIM4 models & universal TBs
├── scripts/
│   ├── validate_repo.py          # Multi-skill offline CI validator & contract checker
│   └── install_skills.sh         # One-command symlink installer for AI agents
├── skills/
│   ├── README.md                 # Domain taxonomy & canonical skill layout contract
│   ├── sar-adc/                  # [Data Converters] SAR ADC (5 TB suites, 20 decks, 18 VA models)
│   ├── dac/                      # [Data Converters] Current-Steering & R-2R DAC (2 TB suites, 9 decks, 6 VA)
│   ├── pll/                      # [Clocking & RF]   Int-N, Frac-N, ADPLL (7 TB suites, 17 decks, 12 VA)
│   ├── oscillator/               # [Clocking & RF]   Pierce XO & RC Relaxation Oscillator (2 TB suites, 7 decks, 2 VA)
│   ├── serdes/                   # [Wireline/SerDes] Channel, TX FFE, CTLE, DFE, SS-LMS, T-coil, CDR, PAM4, Jitter, Link Top (10 TB suites, 35 decks, 15 VA)
│   ├── opamp-ota/                # [Analog Core]     OpAmp/OTA & CMFB (2 TB suites, 18 decks, 2 VA)
│   ├── ldo/                      # [Power & Ref]     LDO Regulators (9 TBs, 3 VA)
│   ├── dcdc-buck/                # [Power & Ref]     Synchronous Step-Down Buck DC-DC (8 TBs, 3 VA)
│   ├── bandgap/                  # [Power & Ref]     Bandgap References (9 TBs, 3 VA)
│   └── supervisor/               # [Power & Ref]     POR/BOR & Temp Sensor / TSD (2 TB suites, 7 decks, 2 VA)
└── .github/workflows/
    └── validate.yml              # GitHub Actions validation workflow
```

## Related Repositories

- [Arcadia-1/awesome-ams-skills](https://github.com/Arcadia-1/awesome-ams-skills) — Curated portal of AMS IC design agent skills
- [Arcadia-1/virtuoso-bridge-lite](https://github.com/Arcadia-1/virtuoso-bridge-lite) — Remote Cadence Virtuoso / Spectre automation bridge
- [Arcadia-1/ADCToolbox](https://github.com/Arcadia-1/ADCToolbox) — ADC characterization, diagnosis, and calibration toolbox
- [Arcadia-1/analog-circuit-skills](https://github.com/Arcadia-1/analog-circuit-skills) — Open-source ngspice + PTM single-block analog circuit skills (zero commercial license)
- [Arcadia-1/circuits-and-systems-classroom](https://github.com/Arcadia-1/circuits-and-systems-classroom) — Interactive web classroom and mathematical derivations for AMS circuits & systems
