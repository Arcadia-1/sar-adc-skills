---
name: sar-adc-skill
description: >
  Process-independent SAR ADC engineering guide and verification toolkit.
  Covers SAR ADC system architecture, CDAC charge redistribution and switching
  schemes (binary and sub-radix-2 redundant), sync and async SAR logic,
  top-plate vs bottom-plate sampling, noise and ENOB budgeting, PVT,
  metastability, reference/input/supply paths, and Verilog-A behavioral
  modeling (4-bit tutorial and 10-bit non-ideality-injectable models). Also
  covers core analog submodules and ready-to-run process-independent Spectre
  testbenches for every block: dynamic comparators (StrongARM & Miyahara,
  PSS+PNOISE/delay/trannoise/offset/FoM), bootstrapped sampling switches,
  CDAC (static DNL/INL & settling), SAR logic (timing & race), LDO regulators
  (stb/PSRR/noise/load-step), and full SAR ADC (coherent FFT & ramp DNL/INL).
  Use for any SAR ADC design, sizing budget, submodule analysis, debugging, or
  Spectre verification task.
---

# SAR ADC Skill

A process-independent engineering guide and verification toolkit for SAR ADC design, from system-level budgets down to block-level circuits, top-level integration, Verilog-A behavioral models, and standalone Spectre testbenches for every building block.

Use it for:
- Explaining SAR ADC operation from system level to transistor-level building blocks.
- Turning target specs into quantified first-order budgets (swing, LSB, quantization, kT/C, comparator noise, jitter, timing).
- Comparing implementation choices: sampling style, binary vs. sub-radix-2 redundant CDAC, switching scheme, StrongARM vs. Miyahara comparator, and sync vs. async logic.
- Diagnosing practical robustness issues: PVT corners vs. Monte Carlo, metastability/BER, reference recovery, input drive, and async timing races.
- Setting up Spectre verification using the bundled Verilog-A library (`assets/va/`) and per-block process-independent Spectre testbenches (`assets/tb/`).

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
  CDAC charge-redistribution equations, differential vs. single-ended kT/C sizing, binary and sub-radix-2 redundant arrays, DAC switches, dummy feedthrough compensation, and static/settling verification (`assets/tb/cdac/`).
- `references/comparator.md`
  StrongARM and Miyahara two-stage dynamic comparators, operating phases, sizing rules, offset trim, closed-loop `CMPCK` loading, exact PSS+PNOISE gain (`V_OBSERVE / vidin`) with `harms >= 100` and `autotstab=yes`, trannoise cross-check, and FoM1/FoM2 definitions (`assets/tb/comparator/`).
- `references/bootstrap_switch.md`
  Bootstrapped sampling switch topology, gate-overdrive derivation, `CB >= 5 * Cgg` sizing rule, clocked `Ron` flatness, clock feedthrough, and coherent sampling linearity verification (`assets/tb/bootstrap/`).
- `references/sar-logic.md`
  Full conversion timing, sync vs. async state machines, dynamic latch chain, `NOR3` completion stop logic, `VALID_L`-vs-`EN` race analysis, clock-ring sizing, DAC switch polarity conventions, and closed-loop timing verification (`assets/tb/sar_logic/`).
- `references/ldo.md`
  PMOS-pass LDO for clean ADC supplies: topology, Miller compensation with nulling resistor, DC/HF PSRR, noise budgeting, and `stb`/PSRR/noise/load-step verification (`assets/tb/ldo/`).

### Integration & Verification
- `references/integration.md`
  Top-level signal flow, bus and differential polarity conventions, bootstrap-CDAC-comparator-logic cross-connections, common integration failure modes, and bring-up checklist.
- `references/simulation-and-verification.md`
  Spectre simulation setup: coherent sampling, `strobeoutput=strobeonly` (`strobedelay < strobeperiod` and strobe-grid filtering), `aps` vs. `mx` accuracy, `noiseruns=1`, 1-sample FFT alignment, ADCToolbox metric extraction, ADE Maestro netlist pitfalls, and phased verification (`assets/tb/adc_top/`).

## Default Workflow

For design questions, follow this order:

1. **Clarify the target:** resolution, sample rate, input-frequency range, SNDR/ENOB target, power, supply, reference range, and educational vs. silicon-implementation depth.
2. **Build first-order budgets:** full swing, LSB size, signal power, quantization noise, allowable kT/C noise, comparator noise, aperture jitter, and timing margin.
3. **Choose the structure:** fully differential CDAC front end, binary vs. redundant array, StrongARM vs. Miyahara comparator, and sync vs. async logic.
4. **Identify the main limiter:** comparator noise, CDAC settling, sampling linearity, reference recovery, clock jitter, slow-PVT timing, or metastability.
5. **Move to circuit-level and verification advice:** block sizing direction, critical timing/noise checks, and standalone Spectre testbench setup.

## Bundled Assets

### Process-Independent Spectre Testbenches (`assets/tb/`)
Every fundamental SAR ADC building block has standalone Spectre decks and a zero-dependency Python PSF ASCII analyzer — plug in your own `models_corner.scs` + `dut_subckt.scs` (or smoke-test using the repo-root `common/models_generic_bsim4.scs`):

- Shared `common/` (repo root) — `psf_utils.py` (standalone real + complex PSF ASCII parser, `extract_uniform_strobe`, coherent FFT, endpoint DNL/INL) and `models_generic_bsim4.scs` (synthetic foundry-free BSIM4 smoke model card)
- `assets/tb/comparator/` — `tb_cmp_pss_pnoise.scs` (`harms=100`, `autotstab=yes`, `noisetype=sampled`, `pm0 jitterevent`), `tb_cmp_delay.scs`, `tb_cmp_trannoise.scs`, `tb_cmp_offset.scs` + `cmp_bisect.va`, `run_cmp_tb.py`
- `assets/tb/bootstrap/` — `tb_boot_ron_sweep.scs` (clocked flying-cap `Ron(VIN)` sweep), `tb_boot_tran_linearity.scs` (coherent Nyquist sampling FFT), `analyze_bootstrap.py`
- `assets/tb/cdac/` — `tb_cdac_static_dnl_inl.scs` (512-state transfer sweep), `tb_cdac_settling.scs` (MSB 0.5-LSB settling), `analyze_cdac.py`
- `assets/tb/sar_logic/` — `tb_sar_logic_timing.scs` (4-frame closed-loop timing & near-metastable stress), `analyze_sar_logic.py`
- `assets/tb/ldo/` — `tb_ldo_stb.scs` (`iprobe` loop stability), `tb_ldo_psrr_noise.scs` (AC PSRR + output noise), `tb_ldo_load_tran.scs` (load-step droop), `analyze_ldo.py`
- `assets/tb/adc_top/` — `tb_sar_adc_fft.scs` (coherent ENOB/SNDR/SFDR/THD), `tb_sar_adc_ramp_dnl.scs` (ramp DNL/INL & usable full-swing check), `analyze_adc_top.py`

### Verilog-A Behavioral Library (`assets/va/`)
Extend these Spectre-verified behavioral models for Phase 1–3 verification instead of rewriting from scratch:

**10-bit & non-ideality-injectable behavioral models (hybrid / system verification):**
- `assets/va/va_cmp_dynamic.va` — dynamic comparator with `vos`, Gaussian `vnoise_rms`, and logarithmic regeneration/metastability delay
- `assets/va/va_cdac_10b_diff.va` — 10-bit differential CDAC (Vcm-based or monotonic, `c_par_ratio`, `dm_msb`, 1-pole `tau_settle`)
- `assets/va/va_sar_logic_10b_async.va` — 10-bit self-timed async SAR logic with `EOC` completion stop and glitch-free latched `DOUT[9:0]`
- `assets/va/va_dac_10b_diff.va` — 10-bit ideal mid-rise differential reconstruction DAC (`AOUT` + exact integer `CODE`)
- `assets/va/va_bootstrap_sw.va` — bootstrapped (`mode=0`) vs. plain NMOS (`mode=1`) sampling switch
- `assets/va/va_code_ramp_10b.va` — 10-bit static code sweep generator for CDAC DNL/INL tests
- `assets/va/va_ldo_ideal.va` — PMOS-pass LDO macro-model with breakable `FB_IN` for `iprobe` `stb`, realistic PSRR, and white noise

**4-bit tutorial baseline models:**
- `assets/va/L2_cdac_4b_ideal.va`, `assets/va/L2_comparator_ideal.va`, `assets/va/L2_logic_4b_sync.va`, `assets/va/L3_logic_4b_async.va`, `assets/va/_va_dac_4b.va`, `assets/va/_va_dac_4b_se.va`, `assets/va/sar_4b_se_ideal.va`

## Scope

### What This Skill Can Do
- Guide SAR ADC design from system targets to first-order block budgets and circuit topologies.
- Quantify tradeoffs across sampling styles, CDAC switching schemes, redundancy, comparator architectures, and sync/async timing.
- Diagnose circuit and simulation bugs (polarity inversions, async race conditions, FFT/strobe setup, PSS+PNOISE pitfalls).
- Provide reusable, Spectre-verified, process-independent Verilog-A behavioral models and standalone Spectre testbenches for every core SAR ADC block.

### What This Skill Cannot Do By Itself
- It is intentionally process-independent and does not ship proprietary PDK models, foundry cells, or final tape-out signoff sizing.
- It focuses on SAR ADCs rather than flash, pipeline, or delta-sigma architectures.
- For PDK-specific device sizing, post-layout extraction, or live Cadence Virtuoso/Spectre execution, pair this skill with your process documentation and EDA automation skills (e.g., `spectre` / `virtuoso`).

## Response Style

- Speak like a mixed-signal IC design engineer.
- Prefer quantified tradeoffs and explicit formulas over generic qualitative advice.
- Separate architectural guidance, first-order hand calculation, circuit implementation advice, and verification strategy.
- State clearly when an assumption or number depends on a specific technology node or PDK not supplied by the user.
