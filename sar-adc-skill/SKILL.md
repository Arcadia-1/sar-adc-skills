---
name: sar-adc-skill
description: Use this skill for SAR ADC architecture, CDAC operation, switching schemes, comparator design, sync or async SAR logic, top-plate or bottom-plate sampling, noise and ENOB budgeting, redundancy, PVT, metastability, peripheral design, and Verilog-A modeling for SAR ADCs.
---

# SAR ADC Skill

This skill is a compact engineering guide built from the `raw_materials/` course set.

Use it for:
- Explaining SAR ADC operation from system level to block level.
- Turning target specs into first-order design budgets.
- Comparing implementation choices such as sampling style, switching scheme, and sync versus async logic.
- Discussing practical robustness issues such as PVT, BER, metastability, references, and input drive.
- Extending the bundled Verilog-A models instead of rewriting behavioral models from scratch.

## Read Order

Use only the minimum reference needed for the user task:

- `references/core-architecture.md`
  Use for SAR operation, residue intuition, CDAC-centered architecture, comparator role, and the practical meaning of sync versus async timing.
- `references/design-and-tradeoffs.md`
  Use for design flow, full swing, quantization noise, kT/C, comparator noise, switching choices, top-plate versus bottom-plate sampling, and redundancy.
- `references/robustness-and-system.md`
  Use for PVT, Monte Carlo interpretation, metastability, BER, reference strategy, input path, supply design, and shippable-product concerns.

## Default Workflow

For design questions, follow this order:

1. Clarify the target:
   resolution, sample rate, input-frequency range, SNDR or ENOB target, power, supply, reference range, and whether the question is educational or tape-out oriented.
2. Build first-order budgets:
   full swing, LSB size, signal power, quantization noise, allowable kT/C noise, comparator noise, and timing margin.
3. Choose the structure:
   fully differential SAR, CDAC front end, dynamic comparator, and sync or async logic depending on timing pressure.
4. Identify the main limiter:
   comparator noise, CDAC settling, sampling linearity, reference recovery, jitter, slow-PVT timing, or metastability.
5. Only then move to circuit-level advice.

## Verilog-A Assets

The skill already includes baseline models in `assets/va/`:

- `L2_cdac_4b_ideal.va`
- `L2_comparator_ideal.va`
- `L2_logic_4b_sync.va`
- `L3_logic_4b_async.va`
- `_va_dac_4b.va`
- `_va_dac_4b_se.va`
- `sar_4b_se_ideal.va`

Use these as starting points for behavioral verification and system integration.

## Scope

### What This Skill Can Do

- Help design a SAR ADC from system-level targets down to first-order block-level decisions.
- Translate target specs into practical budgets for full swing, LSB, quantization noise, kT/C noise, comparator noise, and timing margin.
- Compare architectural choices such as top-plate versus bottom-plate sampling, switching schemes, and sync versus async logic.
- Explain practical robustness issues such as PVT sensitivity, metastability, BER, reference recovery, and input-drive constraints.
- Provide behavioral-model guidance and extend the bundled Verilog-A assets for system-level verification.

### What This Skill Cannot Do By Itself

- It does not replace transistor-level circuit design in a specific PDK.
- It does not produce a tape-out-ready ADC without additional circuit implementation, simulation, layout, and verification work.
- It is focused on SAR ADCs, not general ADC architecture design across flash, pipeline, delta-sigma, or other families.
- It should not pretend to give final device sizing, post-layout closure, or yield signoff unless the user also provides process-specific design context and expects a narrower answer.
- If the user needs concrete transistor-level circuit implementation, device sizing, or dedicated block-design workflow, direct them to search for a more specialized skill in the [`analog-circuit-skills` repository](https://github.com/Arcadia-1/analog-circuit-skills), especially for blocks such as comparators, bootstrap switches, or other analog building blocks.

### Expected Design Depth

- Default depth should be system level plus first-order circuit planning.
- It is appropriate to discuss CDAC sizing direction, comparator noise targets, timing flow, reference strategy, and verification planning.
- It is not appropriate to present hand-wavy transistor-level certainty where the materials only support architecture, budgeting, and behavioral guidance.

## Response Style

- Speak like a mixed-signal IC design engineer.
- Prefer quantified tradeoffs over generic advice.
- Separate architectural guidance, first-order hand calculation, implementation advice, and verification strategy.
- If a detail is not explicit in the source material, say that you are supplementing with general SAR ADC knowledge.
