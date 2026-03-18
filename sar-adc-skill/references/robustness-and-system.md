# Robustness And System

Use this file for PVT, Monte Carlo interpretation, metastability, BER, references, input drive, supply design, and product-level concerns.

## PVT Thinking

- Separate local variation from global variation.
- Local variation matters strongly for matching-sensitive structures such as the CDAC.
- Global variation more directly affects speed, operating point, and timing.

Important practical warning:
- do not mechanically stack worst-case corners and local Monte Carlo pessimism in a way that becomes unrealistically conservative.

If the PDK provides global-only corners such as `SSG` or `FFG`, those are often better starting points for combined variation analysis.

## Margin Philosophy

Two valid strategies exist:
- leave conservative margin,
- or deliberately screen and bin slower parts.

That is both a circuit decision and a product decision.

## Metastability And BER

- In a well-designed ADC, catastrophic wrong-code events should mainly trace back to metastability.
- More available time is usually the cleanest mitigation.
- More time reduces the metastability tail exponentially.
- Loading latch nodes or adding poorly chosen detection structures can make BER worse rather than better.
- Async SAR often behaves better than sync SAR because time is shared rather than hard-sliced.

Also keep the MTF view in mind:
- a BER that looks numerically small can still imply frequent failure at high sample rate.

## Reference Path

Two common strategies:
- large decap to keep ripple small,
- or a fast reference buffer to recover quickly.

Tradeoffs:
- decap costs area and can ring with package inductance,
- buffer costs power and demands enough bandwidth and transient strength.

## Input Path

Check:
- source impedance,
- whether an input buffer or THA is required,
- settling accuracy inside the sample window,
- anti-alias filtering,
- amplitude and common-mode matching.

## Supply And Clock

- Supply integrity matters because ripple, IR drop, and inductive effects can hurt the system even when the core looks fine.
- Clock quality matters because jitter can become the dominant SNR ceiling at high input frequency.

## Product-Level Closure

A shippable ADC is not just the SAR core.

Real closure also includes:
- usable full swing,
- timing margin,
- reference recovery,
- sampling linearity,
- PVT coverage,
- BER,
- supply quality,
- input-drive assumptions,
- and peripheral integration.

Use this file when the user asks for:
- PVT interpretation,
- Monte Carlo realism,
- metastability and BER,
- reference strategy,
- input-drive strategy,
- or the difference between a teaching model and a product-level ADC.
