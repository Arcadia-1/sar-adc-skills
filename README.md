# ams-skills

Process-independent Analog & Mixed-Signal (AMS) IC design skills, Verilog-A behavioral model libraries, and standalone Spectre testbench suites for agentic IC design.

> Formerly `sar-adc-skills` — expanded into a multi-skill AMS repository where every circuit domain is an independently installable AI agent skill sharing a unified, process-independent Spectre verification foundation.

## Included Skills

| Skill | Coverage | References | Verilog-A | Spectre TBs | Evals |
|---|---|---|---|---|---|
| [**`skills/sar-adc/`**](skills/sar-adc/SKILL.md) | SAR ADC architecture, CDAC (binary & sub-radix-2), StrongARM & Miyahara comparators, bootstrapped switch, sync/async SAR logic, top-level integration & coherent FFT verification | 10 guides | 14 models (4b & 10b) + `cmp_bisect.va` | 6 suites (`comparator`, `bootstrap`, `cdac`, `sar_logic`, `ldo`, `adc_top`) | 28 |
| [**`skills/pll/`**](skills/pll/SKILL.md) | Integer-N CP-PLL, Fractional-N $\Delta\Sigma$ (MASH 1-1-1) PLL, All-Digital PLL (TDC-ADPLL & Bang-Bang ADPLL), LC/Ring VCO & DCO, tri-state PFD/CP, MMD dividers, autonomous PSS+PNOISE & RMS jitter | 7 guides | 10 models | 7 suites (`vco`, `pfd_cp`, `divider`, `tdc_dco`, `int_n_pll`, `frac_n_pll`, `adpll`) | 16 |
| [**`skills/opamp-ota/`**](skills/opamp-ota/SKILL.md) | Single-ended & fully differential OpAmps/OTAs (5T, telescopic, folded cascode, 2-stage Miller + `R_z`, CMFB), `iprobe` & lossless Tian balun DM+CM `stb`, DC-servo CMRR/PSRR±/noise, slew & settling | 3 guides | 2 models | 2 suites (`single_ended`, `fully_diff` — 5 `.scs` decks) | 12 |
| [**`skills/ldo/`**](skills/ldo/SKILL.md) | External-cap PMOS-pass, capless (OCL), and NMOS-pass LDOs: dropout, line/load regulation, light-load stability (`stb`), PSRR(f), $|Z_{\text{out}}(f)|$, output noise, load & line step transients | 3 guides | 2 models | 1 full suite (4 `.scs` decks) | 10 |
| [**`skills/bandgap/`**](skills/bandgap/SKILL.md) | Classic Kuijk/Brokaw (~1.22 V) & Banba sub-1 V bandgap references: PTAT+CTAT cancellation, 2nd-order curvature TC (`ppm/C`), startup dead-state immunity, PSRR & output noise | 2 guides | 1 model | 1 full suite (3 `.scs` decks) | 8 |

## Shared Verification Foundation (`common/`)

All 5 skills share a single, zero-PDK verification core under [`common/`](common/README.md):

- **[`common/psf_utils.py`](common/psf_utils.py)** — Zero-dependency Python (`numpy` only) Spectre PSF ASCII parser (handles real `tran`/`dc`/`noise`/`pss`/`pnoise` and complex `ac`/`stb` traces), `extract_uniform_strobe` (filters Spectre's off-grid `t=0`/`t=t_stop` endpoints), coherent FFT (`ENOB`/`SNDR`/`SNR`/`SFDR`/`THD`), endpoint `DNL`/`INL`, and IEEE-1139 phase-noise-to-RMS-jitter integration.
- **[`common/models_generic_bsim4.scs`](common/models_generic_bsim4.scs)** — Synthetic, foundry-free Spectre BSIM4 model pair (`nch` / `pch`) with thermal noise enabled for out-of-the-box smoke verification when no PDK is attached.

All guides, Verilog-A models, and Spectre testbenches are **100% process-independent** — plug in your own PDK `models_corner.scs` + `dut_subckt.scs` for real process sizing and signoff.

## Quick Start

Install any individual skill (or all 5) for your AI coding agent:

```bash
# Install individual skills as needed
ln -s /path/to/ams-skills/skills/sar-adc   .claude/skills/sar-adc
ln -s /path/to/ams-skills/skills/pll       .claude/skills/pll
ln -s /path/to/ams-skills/skills/opamp-ota .claude/skills/opamp-ota
ln -s /path/to/ams-skills/skills/ldo       .claude/skills/ldo
ln -s /path/to/ams-skills/skills/bandgap   .claude/skills/bandgap
```

Run the offline multi-skill validation suite (leak scan, schema, links, `ahdl_include` paths, Python syntax & unit tests):

```bash
python3 -B scripts/validate_repo.py
```

## Skill Details

### 1. SAR ADC Skill (`skills/sar-adc/`)
- **References**: [core-architecture.md](skills/sar-adc/references/core-architecture.md), [design-and-tradeoffs.md](skills/sar-adc/references/design-and-tradeoffs.md), [robustness-and-system.md](skills/sar-adc/references/robustness-and-system.md), [cdac.md](skills/sar-adc/references/cdac.md), [comparator.md](skills/sar-adc/references/comparator.md), [bootstrap_switch.md](skills/sar-adc/references/bootstrap_switch.md), [sar-logic.md](skills/sar-adc/references/sar-logic.md), [ldo.md](skills/sar-adc/references/ldo.md), [integration.md](skills/sar-adc/references/integration.md), [simulation-and-verification.md](skills/sar-adc/references/simulation-and-verification.md).
- **Spectre TBs**: [comparator/](skills/sar-adc/assets/tb/comparator/README.md), [bootstrap/](skills/sar-adc/assets/tb/bootstrap/README.md), [cdac/](skills/sar-adc/assets/tb/cdac/README.md), [sar_logic/](skills/sar-adc/assets/tb/sar_logic/README.md), [ldo/](skills/sar-adc/assets/tb/ldo/README.md), [adc_top/](skills/sar-adc/assets/tb/adc_top/README.md).
- **Verilog-A**: 7 10-bit non-ideality-injectable models + 7 baseline 4-bit tutorial models.

### 2. PLL Skill (`skills/pll/`)
- **References**: [pll-fundamentals.md](skills/pll/references/pll-fundamentals.md), [integer-n-pll.md](skills/pll/references/integer-n-pll.md), [fractional-n-pll.md](skills/pll/references/fractional-n-pll.md), [adpll.md](skills/pll/references/adpll.md), [vco-and-dco.md](skills/pll/references/vco-and-dco.md), [pfd-cp-divider.md](skills/pll/references/pfd-cp-divider.md), [simulation-and-verification.md](skills/pll/references/simulation-and-verification.md).
- **Spectre TBs**: [vco/](skills/pll/assets/tb/vco/README.md), [pfd_cp/](skills/pll/assets/tb/pfd_cp/README.md), [divider/](skills/pll/assets/tb/divider/README.md), [tdc_dco/](skills/pll/assets/tb/tdc_dco/README.md), [int_n_pll/](skills/pll/assets/tb/int_n_pll/README.md), [frac_n_pll/](skills/pll/assets/tb/frac_n_pll/README.md), [adpll/](skills/pll/assets/tb/adpll/README.md).
- **Verilog-A**: `va_pfd`, `va_cp`, `va_vco`, `va_div_int`, `va_mmd_mash111`, `va_tdc`, `va_dco`, `va_dlf_pi`, `va_bbpd`, `va_phase_err_mon`.

### 3. OpAmp & OTA Skill (`skills/opamp-ota/`)
- **References**: [ota-topologies-and-sizing.md](skills/opamp-ota/references/ota-topologies-and-sizing.md), [fully-diff-and-cmfb.md](skills/opamp-ota/references/fully-diff-and-cmfb.md), [simulation-and-verification.md](skills/opamp-ota/references/simulation-and-verification.md).
- **Spectre TBs**: [single_ended/](skills/opamp-ota/assets/tb/single_ended/README.md) (`stb`, 4-replica DC-servo CMRR/PSRR±/noise, slew/settling) & [fully_diff/](skills/opamp-ota/assets/tb/fully_diff/README.md) (lossless Tian balun DM+CMFB `stb`, diff slew/settling).
- **Verilog-A**: `va_ota_2stage`, `va_ota_fd_cmfb`.

### 4. LDO Regulator Skill (`skills/ldo/`)
- **References**: [ldo-architectures-and-sizing.md](skills/ldo/references/ldo-architectures-and-sizing.md), [stability-psrr-noise.md](skills/ldo/references/stability-psrr-noise.md), [simulation-and-verification.md](skills/ldo/references/simulation-and-verification.md).
- **Spectre TBs**: [assets/tb/](skills/ldo/assets/tb/README.md) (`tb_ldo_dc_reg_dropout.scs`, `tb_ldo_stb.scs`, `tb_ldo_psrr_zout_noise.scs`, `tb_ldo_load_line_tran.scs`, `analyze_ldo.py`).
- **Verilog-A**: `va_ldo_pmos`, `va_ldo_capless`.

### 5. Bandgap Reference Skill (`skills/bandgap/`)
- **References**: [bandgap-fundamentals.md](skills/bandgap/references/bandgap-fundamentals.md), [simulation-and-verification.md](skills/bandgap/references/simulation-and-verification.md).
- **Spectre TBs**: [assets/tb/](skills/bandgap/assets/tb/README.md) (`tb_bgr_temp_line.scs`, `tb_bgr_startup.scs`, `tb_bgr_psrr_noise.scs`, `analyze_bandgap.py`).
- **Verilog-A**: `va_bandgap`.

## Repository Layout

```text
ams-skills/
├── common/                       # Shared PSF parser + synthetic BSIM4 demo card
├── skills/
│   ├── sar-adc/                  # SAR ADC (10 refs, 14 VA, 6 TB suites, 28 evals)
│   ├── pll/                      # PLL: Int-N, Frac-N, ADPLL (7 refs, 10 VA, 7 TB suites, 16 evals)
│   ├── opamp-ota/                # OpAmp/OTA & CMFB (3 refs, 2 VA, 2 TB suites, 12 evals)
│   ├── ldo/                      # LDO Regulators (3 refs, 2 VA, 4 TBs, 10 evals)
│   └── bandgap/                  # Bandgap References (2 refs, 1 VA, 3 TBs, 8 evals)
├── scripts/
│   └── validate_repo.py          # Multi-skill offline CI validator
└── .github/workflows/
    └── validate.yml              # GitHub Actions validation workflow
```

## Related Repositories

- [Arcadia-1/awesome-ams-skills](https://github.com/Arcadia-1/awesome-ams-skills) — Curated portal of AMS IC design agent skills
- [Arcadia-1/virtuoso-bridge-lite](https://github.com/Arcadia-1/virtuoso-bridge-lite) — Remote Cadence Virtuoso / Spectre automation bridge
- [Arcadia-1/ADCToolbox](https://github.com/Arcadia-1/ADCToolbox) — ADC characterization, diagnosis, and calibration toolbox
- [Arcadia-1/analog-circuit-skills](https://github.com/Arcadia-1/analog-circuit-skills) — Open-source ngspice + PTM single-block analog circuit skills (zero commercial license)
- [Arcadia-1/circuits-and-systems-classroom](https://github.com/Arcadia-1/circuits-and-systems-classroom) — Interactive web classroom and mathematical derivations for AMS circuits & systems
