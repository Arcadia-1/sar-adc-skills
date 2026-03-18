# Design And Tradeoffs

Use this file for design flow, first-order budgeting, sampling style, switching, redundancy, and the most important non-idealities.

## Design Flow

Start with:
- resolution,
- sample rate,
- input-frequency range,
- SNDR, SNR, or ENOB target,
- supply and reference range,
- full swing,
- power target.

Then estimate:
- LSB size,
- signal power,
- quantization noise,
- allowable kT/C noise,
- allowable comparator noise,
- timing margin.

Do not jump into transistor-level discussion before these budgets are clear.

## First Noise Terms To Check

- Quantization noise:
  `P_n,q = Δ^2 / 12`
- Sampling kT/C noise:
  often one of the first true circuit limits as resolution rises.
- Comparator noise:
  increasing nominal resolution does not guarantee ENOB improvement if comparator noise remains too large.
- Jitter:
  important once input frequency becomes high enough to impose an SNR ceiling.

## Full Swing And FFT Setup

- Before FFT analysis, identify the true usable full swing.
- A practical setup is often near but below full scale, for example around 90 percent full scale.
- If clipping appears before the expected full-scale range, suspect top-plate parasitics and capacitive swing loss.

## Sampling Choice

### Top-plate sampling

- simpler,
- fewer clock phases,
- but more exposed to input-dependent charge injection and clock feedthrough,
- and more likely to lose usable swing through top-plate parasitics.

### Bottom-plate sampling

- better for linearity,
- less sensitive to input-dependent switching artifacts,
- but more complex and usually slower because of extra timing requirements.

## Switching Choice

Switching is an architectural choice because it affects:
- common-mode motion,
- switching energy,
- implementation complexity,
- reference and common-mode-driver requirements.

Useful high-level comparison:
- conventional switching is the baseline,
- monotonic reduces activity but is not automatically best overall,
- Vcm-based switching is elegant but demanding on the `Vcm` source,
- bidirectional switching is often a strong practical compromise.

## Redundancy

Redundancy helps when:
- settling is tight,
- comparison windows are narrow,
- offset or mismatch tolerance is needed,
- reference recovery is stressed,
- speed and robustness matter more than minimal logic complexity.

Its value is practical:
- it relaxes some intermediate decision precision requirements,
- and reduces timing and settling pressure.

## Design Philosophy

- A good SAR ADC should usually be noise-limited rather than distortion-limited.
- Distortion should preferably be pushed below the noise floor.
- The dominant limiter should be identified before optimization effort is spent.

Use this file when the user asks for:
- spec-to-budget design flow,
- ENOB or noise budgeting,
- full-swing setup,
- sampling-style choice,
- switching-style choice,
- or redundancy decisions.
