# ams-skills

Process-independent Analog & Mixed-Signal (AMS) IC design skills, Verilog-A behavioral model libraries, and standalone Spectre testbench suites for agentic IC design.

> Formerly `sar-adc-skills` — expanded into a multi-skill AMS repository where each circuit domain is an independently installable AI agent skill sharing a unified, process-independent Spectre verification foundation.

## Included Skills

| Skill | Coverage | References | Verilog-A | Spectre TBs | Evals |
|---|---|---|---|---|---|
| [**`skills/sar-adc/`**](skills/sar-adc/SKILL.md) | SAR ADC architecture, CDAC (binary & sub-radix-2), StrongARM & Miyahara comparators, bootstrapped switch, sync/async SAR logic, LDO, top-level integration & coherent FFT verification | 10 guides | 14 models (4b & 10b) + `cmp_bisect.va` | 6 suites (`comparator`, `bootstrap`, `cdac`, `sar_logic`, `ldo`, `adc_top`) | 28 |
| [**`skills/pll/`**](skills/pll/SKILL.md) | Integer-N CP-PLL, Fractional-N $\Delta\Sigma$ (MASH 1-1-1) PLL, All-Digital PLL (TDC-ADPLL & Bang-Bang ADPLL), LC/Ring VCO & DCO, tri-state PFD/CP, MMD dividers, autonomous PSS+PNOISE & RMS jitter | 7 guides | 10 models | 7 suites (`vco`, `pfd_cp`, `divider`, `tdc_dco`, `int_n_pll`, `frac_n_pll`, `adpll`) | 16 |

## Shared Verification Foundation (`common/`)

All skills share a single, zero-PDK verification core under [`common/`](common/README.md):

- **[`common/psf_utils.py`](common/psf_utils.py)** — Zero-dependency Python (`numpy` only) Spectre PSF ASCII parser (handles real `tran`/`dc`/`noise`/`pss`/`pnoise` and complex `ac`/`stb` traces), `extract_uniform_strobe` (filters Spectre's off-grid `t=0`/`t=t_stop` endpoints), coherent FFT (`ENOB`/`SNDR`/`SNR`/`SFDR`/`THD`), endpoint `DNL`/`INL`, and IEEE-1139 phase-noise-to-RMS-jitter integration.
- **[`common/models_generic_bsim4.scs`](common/models_generic_bsim4.scs)** — Synthetic, foundry-free Spectre BSIM4 model pair (`nch` / `pch`) with thermal noise enabled for out-of-the-box smoke verification when no PDK is attached.

All guides, Verilog-A models, and Spectre testbenches are **100% process-independent** — plug in your own PDK `models_corner.scs` + `dut_subckt.scs` for real process sizing and signoff.

## Quick Start

Install any individual skill (or all of them) for your AI coding agent:

```bash
# Install the SAR ADC skill
ln -s /path/to/ams-skills/skills/sar-adc .claude/skills/sar-adc

# Install the PLL skill (Integer-N, Fractional-N, ADPLL)
ln -s /path/to/ams-skills/skills/pll .claude/skills/pll
```

Run the offline repository validation suite (leak scan, schema, links, `ahdl_include` paths, Python syntax & unit tests):

```bash
python3 -B scripts/validate_repo.py
```

## Skill Details

### 1. SAR ADC Skill (`skills/sar-adc/`)

- **References (`skills/sar-adc/references/`)**: [core-architecture.md](skills/sar-adc/references/core-architecture.md), [design-and-tradeoffs.md](skills/sar-adc/references/design-and-tradeoffs.md), [robustness-and-system.md](skills/sar-adc/references/robustness-and-system.md), [cdac.md](skills/sar-adc/references/cdac.md), [comparator.md](skills/sar-adc/references/comparator.md), [bootstrap_switch.md](skills/sar-adc/references/bootstrap_switch.md), [sar-logic.md](skills/sar-adc/references/sar-logic.md), [ldo.md](skills/sar-adc/references/ldo.md), [integration.md](skills/sar-adc/references/integration.md), [simulation-and-verification.md](skills/sar-adc/references/simulation-and-verification.md).
- **Spectre Testbenches (`skills/sar-adc/assets/tb/`)**: [comparator/](skills/sar-adc/assets/tb/comparator/README.md), [bootstrap/](skills/sar-adc/assets/tb/bootstrap/README.md), [cdac/](skills/sar-adc/assets/tb/cdac/README.md), [sar_logic/](skills/sar-adc/assets/tb/sar_logic/README.md), [ldo/](skills/sar-adc/assets/tb/ldo/README.md), [adc_top/](skills/sar-adc/assets/tb/adc_top/README.md).
- **Verilog-A Library (`skills/sar-adc/assets/va/`)**: 10-bit non-ideality-injectable models (`va_cmp_dynamic`, `va_cdac_10b_diff`, `va_sar_logic_10b_async`, `va_dac_10b_diff`, `va_bootstrap_sw`, `va_code_ramp_10b`, `va_ldo_ideal`) plus 7 baseline 4-bit tutorial models.

### 2. PLL Skill (`skills/pll/`)

- **References (`skills/pll/references/`)**: [pll-fundamentals.md](skills/pll/references/pll-fundamentals.md), [integer-n-pll.md](skills/pll/references/integer-n-pll.md), [fractional-n-pll.md](skills/pll/references/fractional-n-pll.md), [adpll.md](skills/pll/references/adpll.md), [vco-and-dco.md](skills/pll/references/vco-and-dco.md), [pfd-cp-divider.md](skills/pll/references/pfd-cp-divider.md), [simulation-and-verification.md](skills/pll/references/simulation-and-verification.md).
- **Spectre Testbenches (`skills/pll/assets/tb/`)**: [vco/](skills/pll/assets/tb/vco/README.md), [pfd_cp/](skills/pll/assets/tb/pfd_cp/README.md), [divider/](skills/pll/assets/tb/divider/README.md), [tdc_dco/](skills/pll/assets/tb/tdc_dco/README.md), [int_n_pll/](skills/pll/assets/tb/int_n_pll/README.md), [frac_n_pll/](skills/pll/assets/tb/frac_n_pll/README.md), [adpll/](skills/pll/assets/tb/adpll/README.md).
- **Verilog-A Library (`skills/pll/assets/va/`)**: `va_pfd`, `va_cp`, `va_vco`, `va_div_int`, `va_mmd_mash111`, `va_tdc`, `va_dco`, `va_dlf_pi`, `va_bbpd`, and `va_phase_err_mon`.

## Repository Layout

```text
ams-skills/
├── common/                       # Shared PSF parser + synthetic BSIM4 demo card
│   ├── psf_utils.py
│   └── models_generic_bsim4.scs
├── skills/
│   ├── sar-adc/                  # SAR ADC skill (10 refs, 14 VA, 6 TB suites, 28 evals)
│   └── pll/                      # PLL skill: Int-N, Frac-N, ADPLL (7 refs, 10 VA, 7 TB suites, 16 evals)
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
