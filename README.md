# sar-adc-skills

Process-independent SAR ADC design knowledge base and Spectre verification toolkit for agentic IC design — covering system-level budgeting, circuit topologies, top-level integration, Verilog-A behavioral modeling, and standalone Spectre testbenches for every building block.

## What This Skill Covers

| Topic | Reference | Standalone Spectre TB |
|---|---|---|
| SAR operation, residue viewpoint, CDAC-centered architecture, sync vs. async | [core-architecture.md](sar-adc-skill/references/core-architecture.md) | — |
| Design flow, noise budgets (Q, kT/C, comparator, jitter), switching schemes, redundancy | [design-and-tradeoffs.md](sar-adc-skill/references/design-and-tradeoffs.md) | — |
| PVT vs. Monte Carlo, metastability, BER, reference path, input drive, supply integrity | [robustness-and-system.md](sar-adc-skill/references/robustness-and-system.md) | — |
| CDAC: charge redistribution, differential kT/C sizing, binary & sub-radix-2 arrays | [cdac.md](sar-adc-skill/references/cdac.md) | [assets/tb/cdac/](sar-adc-skill/assets/tb/cdac/README.md) |
| Dynamic comparators: StrongARM & Miyahara two-stage, sizing, noise, offset, FoM1/FoM2 | [comparator.md](sar-adc-skill/references/comparator.md) | [assets/tb/comparator/](sar-adc-skill/assets/tb/comparator/README.md) |
| Bootstrapped sampling switch: gate boosting, clocked `Ron` flatness, linearity | [bootstrap_switch.md](sar-adc-skill/references/bootstrap_switch.md) | [assets/tb/bootstrap/](sar-adc-skill/assets/tb/bootstrap/README.md) |
| Sync & async SAR logic: latch chain, `NOR3` stop logic, `VALID_L`/`EN` race | [sar-logic.md](sar-adc-skill/references/sar-logic.md) | [assets/tb/sar_logic/](sar-adc-skill/assets/tb/sar_logic/README.md) |
| PMOS-pass LDO regulator: Miller compensation, `stb`, DC/HF PSRR, noise, load step | [ldo.md](sar-adc-skill/references/ldo.md) | [assets/tb/ldo/](sar-adc-skill/assets/tb/ldo/README.md) |
| Top-level integration: module connectivity, polarity conventions, bring-up debug | [integration.md](sar-adc-skill/references/integration.md) | — |
| Spectre simulation: coherent FFT, `strobeonly`, `noiseruns=1`, ADCToolbox, Maestro pitfalls | [simulation-and-verification.md](sar-adc-skill/references/simulation-and-verification.md) | [assets/tb/adc_top/](sar-adc-skill/assets/tb/adc_top/README.md) |

All guides, Verilog-A models, and Spectre testbenches are **100% process-independent** — plug in your own PDK `models_corner.scs` + `dut_subckt.scs`, or smoke-test with the bundled synthetic BSIM4 model card in [assets/tb/common/](sar-adc-skill/assets/tb/common/README.md).

## Bundled Assets

### Per-Block Spectre Testbench Suite (`sar-adc-skill/assets/tb/`)

Every core SAR ADC block ships with standalone Spectre `.scs` decks and a zero-dependency Python PSF ASCII analyzer (`numpy` only):

| Directory | Testbenches & Analyzer | Key Extracted Metrics |
|---|---|---|
| `common/` | `psf_utils.py`, `models_generic_bsim4.scs` | Real + complex PSF ASCII parser, `extract_uniform_strobe`, coherent FFT, DNL/INL, generic BSIM4 demo card |
| `comparator/` | `tb_cmp_pss_pnoise.scs`, `tb_cmp_delay.scs`, `tb_cmp_trannoise.scs`, `tb_cmp_offset.scs`, `cmp_bisect.va`, `run_cmp_tb.py` | Input-referred RMS noise, `t_cmp`, `t_rst`, regeneration `tau`, `E_cmp`, `FoM1`, `FoM2`, offset/hysteresis |
| `bootstrap/` | `tb_boot_ron_sweep.scs`, `tb_boot_tran_linearity.scs`, `analyze_bootstrap.py` | Clocked flying-cap `Ron(VIN)` flatness, Nyquist sampled `SFDR`, `THD`, `SNDR`, `ENOB` |
| `cdac/` | `tb_cdac_static_dnl_inl.scs`, `tb_cdac_settling.scs`, `analyze_cdac.py` | 512-state static `DNL`/`INL`, common-mode shift `Vcm`, worst-case MSB `0.5 LSB` settling time |
| `sar_logic/` | `tb_sar_logic_timing.scs`, `analyze_sar_logic.py` | 4-frame closed-loop timing (incl. `0.1 mV` metastability stress), exact `N` `CMPCK` count, `EOC` stop, code error |
| `ldo/` | `tb_ldo_stb.scs`, `tb_ldo_psrr_noise.scs`, `tb_ldo_load_tran.scs`, `analyze_ldo.py` | DC loop gain `T0`, `UGF`, `PM`, `GM`, `PSRR(f)`, integrated output noise, load-step droop |
| `adc_top/` | `tb_sar_adc_fft.scs`, `tb_sar_adc_ramp_dnl.scs`, `analyze_adc_top.py` | Coherent `ENOB`/`SNDR`/`SNR`/`SFDR`/`THD`, clipping flag, ramp `DNL`/`INL`, missing codes, usable full swing |

### Verilog-A Behavioral Library (`sar-adc-skill/assets/va/`)

14 Spectre-verified Verilog-A models (plus `cmp_bisect.va` under `assets/tb/comparator/`):

- **10-bit & non-ideality-injectable models** (Phase 1–3 behavioral & hybrid verification): `va_cmp_dynamic.va` (offset, Gaussian thermal noise, logarithmic metastability delay), `va_cdac_10b_diff.va` (Vcm-based/monotonic, `c_par_ratio`, `dm_msb`, `tau_settle`), `va_sar_logic_10b_async.va`, `va_dac_10b_diff.va`, `va_bootstrap_sw.va`, `va_code_ramp_10b.va`, `va_ldo_ideal.va`.
- **4-bit tutorial baseline models**: `L2_cdac_4b_ideal.va`, `L2_comparator_ideal.va`, `L2_logic_4b_sync.va`, `L3_logic_4b_async.va`, `_va_dac_4b.va`, `_va_dac_4b_se.va`, `sar_4b_se_ideal.va`.

## Quick Start

Install as a skill for your AI coding agent:

```bash
# Symlink into your project's skills directory
ln -s /path/to/sar-adc-skills/sar-adc-skill .claude/skills/sar-adc
```

Validate repository integrity offline:

```bash
python3 scripts/validate_repo.py
```

## Repository Layout

```text
sar-adc-skill/
├── SKILL.md                      # Skill definition and read-order guide
├── agents/
│   └── openai.yaml               # Agent interface metadata
├── references/                   # 10 process-independent technical references
├── assets/
│   ├── tb/                       # Per-block standalone Spectre testbenches + analyzers
│   │   ├── common/               # Shared PSF parser + synthetic BSIM4 demo card
│   │   ├── comparator/           # PSS+PNOISE, delay, trannoise, offset bisection
│   │   ├── bootstrap/            # Clocked Ron sweep + coherent sampling FFT
│   │   ├── cdac/                 # Static DNL/INL + MSB settling
│   │   ├── sar_logic/            # Closed-loop timing & metastability race check
│   │   ├── ldo/                  # stb, AC PSRR + noise, load-step transient
│   │   └── adc_top/              # Full-ADC coherent FFT + ramp DNL/INL
│   └── va/                       # 14 Verilog-A behavioral models (10-bit & 4-bit)
└── evals/
    └── evals.json                # Evaluation prompts for skill testing
scripts/
└── validate_repo.py              # Offline CI validation (leaks, links, YAML/JSON, helpers)
```

## Related Repositories

- [Arcadia-1/analog-circuit-skills](https://github.com/Arcadia-1/analog-circuit-skills) — transistor-level comparator and bootstrap switch skills with ngspice simulation
- [Arcadia-1/ADCToolbox](https://github.com/Arcadia-1/ADCToolbox) — ADC performance analysis (ENOB, SNDR, SFDR, DNL/INL)
- [Arcadia-1/virtuoso-bridge-lite](https://github.com/Arcadia-1/virtuoso-bridge-lite) — remote Cadence Virtuoso / Spectre simulation
