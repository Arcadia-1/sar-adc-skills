# sar-adc-skills

Process-independent SAR ADC design knowledge base and verification toolkit for agentic IC design — covering system-level budgeting, circuit topologies, top-level integration, Verilog-A behavioral modeling, and standalone Spectre testbenches.

## What This Skill Covers

| Topic | Reference |
|-------|-----------|
| SAR operation, residue viewpoint, CDAC-centered architecture, sync vs. async | [core-architecture.md](sar-adc-skill/references/core-architecture.md) |
| Design flow, noise budgets (Q, kT/C, comparator, jitter), switching schemes, redundancy | [design-and-tradeoffs.md](sar-adc-skill/references/design-and-tradeoffs.md) |
| PVT vs. Monte Carlo, metastability, BER, reference path, input drive, supply integrity | [robustness-and-system.md](sar-adc-skill/references/robustness-and-system.md) |
| CDAC: charge redistribution, differential kT/C sizing, binary & sub-radix-2 arrays, switches | [cdac.md](sar-adc-skill/references/cdac.md) |
| Dynamic comparators: StrongARM & Miyahara two-stage, sizing, noise, offset, FoM1/FoM2 | [comparator.md](sar-adc-skill/references/comparator.md) |
| Bootstrapped sampling switch: gate boosting, `Ron` flatness, feedthrough, CDAC interface | [bootstrap_switch.md](sar-adc-skill/references/bootstrap_switch.md) |
| Sync & async SAR logic: latch chain, `NOR3` stop logic, `VALID_L`/`EN` race, switch polarity | [sar-logic.md](sar-adc-skill/references/sar-logic.md) |
| Top-level integration: module connectivity, polarity conventions, bring-up debug | [integration.md](sar-adc-skill/references/integration.md) |
| Spectre simulation: coherent sampling, `strobeonly`, `noiseruns=1`, ADCToolbox, Maestro pitfalls | [simulation-and-verification.md](sar-adc-skill/references/simulation-and-verification.md) |
| PMOS-pass LDO regulator: Miller compensation, DC/HF PSRR, noise, transient verification | [ldo.md](sar-adc-skill/references/ldo.md) |

Every circuit reference includes a **"How to Verify"** section with Spectre setup, analysis commands, metric extraction, and pass/fail criteria. All guides and testbenches are **100% process-independent** — plug in your own PDK models and DUT subcircuits.

## Bundled Assets

### Comparator Spectre Testbench Suite (`sar-adc-skill/assets/tb/comparator/`)

Standalone, process-independent Spectre testbenches and a Python runner for dynamic comparator characterization (verified against Cadence ADE Maestro):

- **`tb_cmp_pss_pnoise.scs`** — PSS + sampled full-spectrum PNOISE (`harms=100`, `autotstab=yes`, `noisetype=sampled`, `pm0 jitterevent`, exact `A_eff = V_OBSERVE / vidin` gain)
- **`tb_cmp_delay.scs`** — clock-to-Q propagation delay and energy per comparison
- **`tb_cmp_trannoise.scs`** — multi-cycle transient noise (`noiseruns=1`) with probit CDF extraction
- **`tb_cmp_offset.scs` + `cmp_bisect.va`** — single-run Verilog-A binary-search offset extraction
- **`run_cmp_tb.py`** — automated batch runner and FoM1/FoM2 summary table generator

See [assets/tb/comparator/README.md](sar-adc-skill/assets/tb/comparator/README.md) for the DUT pin contract and CLI usage.

### Verilog-A Behavioral Models (`sar-adc-skill/assets/va/`)

Baseline 4-bit Verilog-A models for phased verification (behavioral -> hybrid -> transistor-level): `L2_cdac_4b_ideal.va`, `L2_comparator_ideal.va`, `L2_logic_4b_sync.va`, `L3_logic_4b_async.va`, `_va_dac_4b.va`, `_va_dac_4b_se.va`, and `sar_4b_se_ideal.va`.

## Quick Start

Install as a skill for your AI coding agent:

```bash
# Symlink into your project's skills directory
ln -s /path/to/sar-adc-skills/sar-adc-skill .claude/skills/sar-adc
```

The skill activates on SAR ADC design questions — architecture, noise budgeting, CDAC switching, comparator noise/FoM, bootstrap sampling, async logic timing, Spectre simulation setup, or ENOB analysis.

## Repository Layout

```text
sar-adc-skill/
├── SKILL.md                      # Skill definition and read-order guide
├── agents/
│   └── openai.yaml               # Agent interface metadata
├── references/                   # 10 process-independent technical references
│   ├── core-architecture.md
│   ├── design-and-tradeoffs.md
│   ├── robustness-and-system.md
│   ├── cdac.md
│   ├── comparator.md
│   ├── bootstrap_switch.md
│   ├── sar-logic.md
│   ├── integration.md
│   ├── simulation-and-verification.md
│   └── ldo.md
├── assets/
│   ├── tb/comparator/            # Standalone Spectre comparator TB suite + runner
│   └── va/                       # Verilog-A behavioral models (4-bit SAR)
└── evals/
    └── evals.json                # Evaluation prompts for skill testing
```

## Design Depth

The skill supports the full design chain without locking into a specific foundry or PDK:

1. **Specs to budgets** — ENOB/SNDR target to quantization, kT/C, comparator, jitter, and timing allocation
2. **Architecture** — fully differential charge-redistribution CDAC, binary or redundant array, dynamic comparator, sync/async SAR
3. **Circuit implementation** — transistor topologies, first-order sizing rules, and common failure modes
4. **Integration** — module connectivity, differential polarity conventions, and phased bring-up
5. **Verification** — per-block (PSS+PNOISE, delay/energy, trannoise, offset, THD, DNL/INL, stability) and full-ADC (ENOB, SNDR, SFDR)

## Related Repositories

- [Arcadia-1/analog-circuit-skills](https://github.com/Arcadia-1/analog-circuit-skills) — transistor-level comparator and bootstrap switch skills with ngspice simulation
- [Arcadia-1/ADCToolbox](https://github.com/Arcadia-1/ADCToolbox) — ADC performance analysis (ENOB, SNDR, SFDR, DNL/INL)
- [Arcadia-1/virtuoso-bridge-lite](https://github.com/Arcadia-1/virtuoso-bridge-lite) — remote Cadence Virtuoso / Spectre simulation
