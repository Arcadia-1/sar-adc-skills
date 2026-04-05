# sar-adc-skills

Claude Code skill for SAR ADC design — from system-level architecture to transistor-level implementation and verification.

## What This Skill Covers

| Topic | Reference |
|-------|-----------|
| SAR operation, CDAC-centered architecture, sync vs async | `core-architecture.md` |
| Design flow, noise budgets, switching schemes, sampling | `design-and-tradeoffs.md` |
| PVT, metastability, BER, reference path, supply integrity | `robustness-and-system.md` |
| CDAC: charge redistribution, cap array, DAC switches, differential operation | `cdac.md` |
| StrongArm comparator: topology, sizing, offset trim, noise | `comparator.md` |
| Bootstrap switch: gate boosting, Ron flatness, integration with CDAC | `bootstrap_switch.md` |
| Async SAR logic: latch chain, DCTRL generation, DAC switch mapping | `sar-logic.md` |
| Top-level integration: module connectivity, signal flow, cross-connections | `integration.md` |
| Spectre simulation: coherent sampling, strobe, ADCToolbox, per-block verification | `simulation-and-verification.md` |
| LDO regulator for clean ADC supply | `ldo.md` |
| SAR_11B_ZZS taped-out reference design (TSMC 28nm, 11-bit, 250 MS/s) | `sar-adc-11b-zzs.md` |

Every module reference includes a **"How to Verify"** section with Spectre testbench setup, analysis commands, metric extraction, and pass/fail criteria.

## Quick Start

Install as a Claude Code skill:

```bash
# Symlink into your project's .claude/skills/
ln -s /path/to/sar-adc-skills/sar-adc-skill .claude/skills/sar-adc
```

The skill triggers on SAR ADC design questions — architecture, CDAC switching, comparator noise, bootstrap sampling, async logic, simulation setup, or ENOB analysis.

## Repository Layout

```
sar-adc-skill/
├── SKILL.md              # Skill definition and read-order guide
├── references/           # 11 technical references (111 KB total)
│   ├── core-architecture.md
│   ├── design-and-tradeoffs.md
│   ├── robustness-and-system.md
│   ├── cdac.md
│   ├── comparator.md
│   ├── bootstrap_switch.md
│   ├── sar-logic.md
│   ├── integration.md
│   ├── simulation-and-verification.md
│   ├── ldo.md
│   └── sar-adc-11b-zzs.md
├── assets/va/            # Verilog-A behavioral models (4-bit SAR)
└── evals/                # Evaluation prompts for skill testing
```

## Design Depth

The skill supports the full design chain:

1. **Specs to budgets** — ENOB target to noise/timing allocation
2. **Architecture** — fully differential, charge-redistribution CDAC, dynamic comparator, async/sync SAR
3. **Circuit implementation** — transistor topologies, sizing guidelines, PDK-aware examples (TSMC 28nm)
4. **Integration** — module connectivity, polarity conventions, differential cross-connections
5. **Verification** — per-block (PSS+Pnoise, THD, DNL/INL, timing) and full-ADC (ENOB, SNDR, SFDR)

Includes a taped-out 11-bit reference design (SAR_11B_ZZS) with complete module hierarchy, transistor sizing, and simulation parameters.

## Related Repositories

- [Arcadia-1/analog-circuit-skills](https://github.com/Arcadia-1/analog-circuit-skills) — transistor-level comparator and bootstrap switch skills with ngspice simulation
- [Arcadia-1/ADCToolbox](https://github.com/Arcadia-1/ADCToolbox) — ADC performance analysis (ENOB, SNDR, SFDR, DNL/INL)
- [Arcadia-1/virtuoso-bridge-lite](https://github.com/Arcadia-1/virtuoso-bridge-lite) — remote Cadence Virtuoso / Spectre simulation
