# Core Architecture

Use this file for SAR ADC operation, system structure, residue-voltage intuition, comparator role, and sync-versus-async timing basics.

## Why SAR ADC

- SAR is a strong entry point for ADC design because the architecture is structurally clear and still foundational in many modern hybrid ADCs.
- The central mental model is binary search.
- The more useful implementation-level explanation is residue based: the comparator sees the sampled differential input after CDAC correction, not just a generic threshold comparison.

## Practical Default Structure

- A practical SAR ADC is usually fully differential.
- A CDAC is usually preferred over a separate sample-and-hold plus DAC because it merges sampling and DAC adjustment into one charge-redistribution structure.
- The minimum useful block view is:
  - sampling front end,
  - CDAC,
  - comparator,
  - SAR logic and timing.

## Residue View

- Every bit decision updates bottom-plate states and moves the residue voltage.
- The residue view is often clearer than a pure threshold view because it explains why DAC switching matters after each comparison.
- A useful intuitive description is:
  sampled differential input minus CDAC-generated correction equals comparator residue.

## Comparator Role

- In SAR ADCs, the comparator is a clocked decision element, not just a static comparator.
- Fire and reset matter because incomplete reset can corrupt the next comparison.
- The main comparator concerns are:
  - input-referred noise,
  - decision speed,
  - offset,
  - metastability when residue becomes small.

## Sync Versus Async

### Synchronous SAR

- Each bit gets a fixed time slot.
- The design is easy to reason about.
- It is effectively designed around the worst-case bit.

### Asynchronous SAR

- Total conversion time is distributed dynamically.
- Easy decisions finish early.
- Hard decisions borrow more time.
- The async logic effectively owns comparator clocking.

Important timing idea:
- async timing is a state-sequenced loop, not just a faster clock style.
- the clock ring must not outrun DAC settling and comparator reset behavior.

## Behavioral-Model Insight

The source material also ties the theory to simple behavioral models:
- reset digital outputs on the sampling event,
- track the input during sampling,
- start conversion at the conversion edge,
- generate decisions step by step,
- update outputs with transition behavior.

Use this file when the user asks for:
- a clean explanation of SAR operation,
- residue-voltage intuition,
- why CDAC-centered implementations dominate,
- comparator role,
- or the conceptual difference between sync and async SAR.
