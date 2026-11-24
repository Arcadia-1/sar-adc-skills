---
name: sar-adc-skill
description: >
  Process-independent SAR ADC engineering guide and verification toolkit.
  Covers SAR ADC system architecture, CDAC charge redistribution and switching
  schemes (binary and sub-radix-2 redundant), sync and async SAR logic,
  top-plate vs bottom-plate sampling, noise and ENOB budgeting, PVT,
  metastability, reference/input/supply paths, and Verilog-A behavioral
  modeling. Also covers core analog submodules: dynamic comparators (StrongARM
  and Miyahara two-stage topology, noise, offset, sizing, FoM, and standalone
  Spectre PSS+PNOISE / delay / trannoise / offset testbenches), bootstrapped
  sampling switches, LDO regulators, top-level integration, and Spectre
  verification with ADCToolbox (coherent sampling, strobeonly, trannoise,
  phased behavioral-to-transistor flow). Use for any SAR ADC design, sizing
  budget, submodule analysis, debugging, or Spectre verification task.
---

# SAR ADC Skill

A process-independent engineering guide and verification toolkit for SAR ADC design, from system-level budgets down to block-level circuits, top-level integration, and Spectre verification.

Use it for:
- Explaining SAR ADC operation from system level to transistor-level building blocks.
- Turning target specs into quantified first-order budgets (swing, LSB, quantization, kT/C, comparator noise, jitter, timing).
- Comparing implementation choices: sampling style, binary vs. sub-radix-2 redundant CDAC, switching scheme, StrongARM vs. Miyahara comparator, and sync vs. async logic.
- Diagnosing practical robustness issues: PVT corners vs. Monte Carlo, metastability/BER, reference recovery, input drive, and async timing races.
- Setting up Spectre verification using the bundled Verilog-A models (`assets/va/`) and process-independent comparator testbench suite (`assets/tb/comparator/`).

## Read Order

Read only the minimum reference needed for the user's task:

### System & Architecture
- `references/core-architecture.md`
  SAR residue-voltage operation, CDAC-centered architecture, comparator role, and sync vs. async timing fundamentals.
- `references/design-and-tradeoffs.md`
  Specs-to-budget design flow, full swing, quantization / kT/C / comparator / jitter noise budgeting, switching schemes, top-plate vs. bottom-plate sampling, and redundancy.
- `references/robustness-and-system.md`
  PVT vs. local Monte Carlo, metastability and BER, reference decap vs. buffer, input path/drive, supply isolation, and product-level closure.

### Submodules
- `references/cdac.md`
  CDAC charge-redistribution equations, differential vs. single-ended kT/C sizing, binary and sub-radix-2 redundant arrays, DAC switches, dummy feedthrough compensation, and static/dynamic verification.
- `references/comparator.md`
  StrongARM and Miyahara two-stage dynamic comparators, operating phases, sizing rules, offset trim, closed-loop `CMPCK` loading, exact PSS+PNOISE gain (`V_OBSERVE / vidin`) with `harms >= 100` and `autotstab=yes`, trannoise cross-check, and FoM1/FoM2 definitions. Paired with `assets/tb/comparator/`.
- `references/bootstrap_switch.md`
  Bootstrapped sampling switch topology, gate-overdrive derivation, `CB >= 5 * Cgg` sizing rule, `Ron` flatness, clock feedthrough, and linearity verification.
- `references/sar-logic.md`
  Full conversion timing, sync vs. async state machines, dynamic latch chain, `NOR3` completion stop logic, `VALID_L`-vs-`EN` race analysis, clock-ring sizing, DAC switch polarity conventions, and Verilog-A correspondence.
- `references/ldo.md`
  PMOS-pass LDO for clean ADC supplies: topology, Miller compensation with nulling resistor, DC/HF PSRR, noise budgeting, and stability/transient verification.

### Integration & Verification
- `references/integration.md`
  Top-level signal flow, bus and differential polarity conventions, bootstrap-CDAC-comparator-logic cross-connections, common integration failure modes, and bring-up checklist.
- `references/simulation-and-verification.md`
  Spectre simulation setup: coherent sampling, `strobeoutput=strobeonly`, `aps` vs. `mx` accuracy, `noiseruns=1`, 1-sample FFT alignment, ADCToolbox metric extraction, ADE Maestro netlist pitfalls, comparator PSS+PNOISE/FoM workflow, and phased verification (behavioral -> hybrid -> transistor-level).

## Default Workflow

For design questions, follow this order:

1. **Clarify the target:** resolution, sample rate, input-frequency range, SNDR/ENOB target, power, supply, reference range, and educational vs. silicon-implementation depth.
2. **Build first-order budgets:** full swing, LSB size, signal power, quantization noise, allowable kT/C noise, comparator noise, aperture jitter, and timing margin.
3. **Choose the structure:** fully differential CDAC front end, binary vs. redundant array, StrongARM vs. Miyahara comparator, and sync vs. async logic.
4. **Identify the main limiter:** comparator noise, CDAC settling, sampling linearity, reference recovery, clock jitter, slow-PVT timing, or metastability.
5. **Move to circuit-level and verification advice:** block sizing direction, critical timing/noise checks, and Spectre testbench setup.

## Bundled Assets

### Comparator Spectre Testbench Suite (`assets/tb/comparator/`)
Process-independent standalone Spectre decks and Python runner — plug in your own process model file and comparator DUT subcircuit:

- `assets/tb/comparator/tb_cmp_pss_pnoise.scs` — PSS + sampled full-spectrum PNOISE (`harms=100`, `autotstab=yes`, `noisetype=sampled`, `pm0 jitterevent`, exact `V_OBSERVE / vidin` gain)
- `assets/tb/comparator/tb_cmp_delay.scs` — clock-to-Q delay and energy per comparison across `vidin`
- `assets/tb/comparator/tb_cmp_trannoise.scs` — transient-noise CDF probit verification (`noiseruns=1`, multi-cycle)
- `assets/tb/comparator/tb_cmp_offset.scs` + `cmp_bisect.va` — single-run Verilog-A binary-search offset extraction
- `assets/tb/comparator/run_cmp_tb.py` — automated runner, waveform/noise parser, and FoM1/FoM2 summary
- `assets/tb/comparator/README.md` — DUT port contract, usage examples, and configuration guide

### Verilog-A Behavioral Models (`assets/va/`)
Baseline 4-bit behavioral models for phased verification and top-level bring-up (extend rather than rewrite from scratch):

- `assets/va/L2_cdac_4b_ideal.va` — differential 4-bit ideal CDAC
- `assets/va/L2_comparator_ideal.va` — clocked ideal comparator
- `assets/va/L2_logic_4b_sync.va` — synchronous 4-bit SAR logic
- `assets/va/L3_logic_4b_async.va` — asynchronous 4-bit SAR logic
- `assets/va/_va_dac_4b.va` — 4-bit differential ideal reconstruction DAC
- `assets/va/_va_dac_4b_se.va` — 4-bit single-ended ideal reconstruction DAC
- `assets/va/sar_4b_se_ideal.va` — standalone single-ended 4-bit behavioral SAR ADC

## Scope

### What This Skill Can Do
- Guide SAR ADC design from system targets to first-order block budgets and circuit topologies.
- Quantify tradeoffs across sampling styles, CDAC switching schemes, redundancy, comparator architectures, and sync/async timing.
- Diagnose circuit and simulation bugs (polarity inversions, async race conditions, FFT/strobe setup, PSS+PNOISE pitfalls).
- Provide reusable, process-independent Verilog-A behavioral models and Spectre comparator testbenches.

### What This Skill Cannot Do By Itself
- It is intentionally process-independent and does not ship proprietary PDK models, foundry cells, or final tape-out signoff sizing.
- It focuses on SAR ADCs rather than flash, pipeline, or delta-sigma architectures.
- For PDK-specific device sizing, post-layout extraction, or live Cadence Virtuoso/Spectre execution, pair this skill with your process documentation and EDA automation skills (e.g., `spectre` / `virtuoso`).

## Response Style

- Speak like a mixed-signal IC design engineer.
- Prefer quantified tradeoffs and explicit formulas over generic qualitative advice.
- Separate architectural guidance, first-order hand calculation, circuit implementation advice, and verification strategy.
- State clearly when an assumption or number depends on a specific technology node or PDK not supplied by the user.
