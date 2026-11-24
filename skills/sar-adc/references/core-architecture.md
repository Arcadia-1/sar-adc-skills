# Core Architecture

Use this file for SAR ADC operation, system structure, residue-voltage intuition, comparator role, and sync-versus-async timing basics.

## Why SAR ADC

- SAR is a strong entry point for ADC design because the architecture is structurally clear and still foundational in modern hybrid ADCs (pipelined-SAR, time-interleaved SAR, noise-shaping SAR).
- The central mental model is binary search.
- The more useful implementation-level explanation is **residue based**: the comparator sees the sampled differential input after CDAC correction, not just a generic threshold comparison.

## Practical Default Structure

- A practical SAR ADC is usually **fully differential**.
- A **CDAC** is usually preferred over a separate sample-and-hold plus DAC because it merges sampling, residue storage, and DAC adjustment into one charge-redistribution structure.
- The minimum useful block view is:
  - sampling front end (typically bootstrapped switches),
  - CDAC,
  - dynamic clocked comparator,
  - SAR logic and timing (sync or async).

## Residue View

- Every bit decision updates CDAC bottom-plate states and moves the top-plate residue voltage toward zero.
- The residue view explains why DAC switching scheme, common-mode motion, and settling accuracy matter after each comparison:
  $$\text{comparator residue} = \text{sampled differential input} - \text{CDAC correction}$$

## Comparator Role

- In SAR ADCs, the comparator is a **clocked dynamic decision element**, not a static continuous-time comparator.
- Both evaluation and reset matter: incomplete reset leaves residual voltage on internal nodes and corrupts the next comparison (memory effect / hysteresis).
- The four main comparator constraints are:
  - input-referred thermal noise,
  - decision + reset speed (including closed-loop `CMPCK` loading),
  - offset (DC shift; trim only if needed),
  - metastability when residue approaches zero.

## Sync Versus Async

### Synchronous SAR

- Each bit receives a fixed external clock slot (`BITCLK` $\ge (N+2)f_s$).
- Timing closure is straightforward, but every bit pays for the worst-case small-residue decision.

### Asynchronous SAR

- Total conversion time is shared dynamically across all $N$ bits: large-residue bits resolve quickly and donate slack to small-residue bits.
- No external high-frequency bit clock is required; the async logic owns comparator clocking (`CMPCK`).
- **Critical insight:** Async timing is a state-sequenced feedback loop, not just a faster clock — the self-timed ring must not outrun CDAC settling, comparator reset, or internal latch capture (`VALID_L` vs. `EN`).

## Behavioral-Model Pattern

The bundled Verilog-A baseline models (`assets/va/`) follow a direct event structure:
- reset digital states on the sampling clock edge,
- track/hold the input across the sampling event,
- step through decisions MSB-to-LSB (clocked externally for sync or self-timed on comparator edges for async),
- latch retimed outputs cleanly at end of conversion.
