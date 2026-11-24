# Design And Tradeoffs

Use this file for spec-to-budget design flow, first-order noise and jitter equations, full-swing setup, sampling style, switching scheme, and redundancy decisions.

## Design Flow

Start by pinning down:
- resolution $N$,
- sample rate $f_s$ and sampling duty cycle $D_{\text{samp}}$ (giving conversion window $(1 - D_{\text{samp}})/f_s$),
- input-frequency range (DC to Nyquist $f_s/2$),
- SNDR / SNR / ENOB target,
- supply `VDD`, reference range `Vref`, and usable full swing,
- power and area targets.

Then build first-order budgets **before** discussing transistor sizes:
- LSB step $\Delta = V_{\text{fs}} / 2^N$,
- full-scale sine signal power $P_{\text{sig}} = V_{\text{fs}}^2 / 8$,
- quantization noise power $P_{n,q} = \Delta^2 / 12$,
- allowable $kT/C$ sampling noise power,
- allowable comparator noise power $\sigma_{\text{cmp}}^2$,
- aperture jitter noise ceiling at maximum $f_{\text{in}}$,
- per-bit timing budget.

## Key First-Order Equations

- **Ideal quantization SNR / ENOB:**
  $$\text{SNR}_q = 6.02 N + 1.76\text{ dB}, \qquad \text{ENOB} = \frac{\text{SNDR} - 1.76}{6.02}$$
- **Total input-referred noise power (uncorrelated sum):**
  $$\sigma_{\text{tot}}^2 = \frac{\Delta^2}{12} + \sigma_{kT/C}^2 + \sigma_{\text{cmp}}^2 + \sigma_{\text{jit}}^2$$
  where for a fully differential CDAC with capacitance $C_{\text{tot}}$ per side, $\sigma_{kT/C,\text{diff}}^2 = 2 kT / C_{\text{tot}}$.
- **Clock aperture jitter SNR ceiling** (for RMS jitter $\sigma_t$ at input frequency $f_{\text{in}}$):
  $$\text{SNR}_{\text{jit}} = -20\log_{10}(2\pi f_{\text{in}} \sigma_t)$$
  Jitter often dominates high-$f_{\text{in}}$ performance even when $kT/C$ and comparator noise meet spec.

## Full Swing And FFT Setup

- Identify the true usable full swing (accounting for top-plate parasitic attenuation $C_{\text{tot}} / (C_{\text{tot}} + C_p)$ and comparator offset) before running FFTs.
- Drive near but slightly below full scale (typically 85–95% FS) so minor parasitics do not cause hard clipping.

## Sampling Choice

### Top-Plate Sampling
- Simpler timing, fewer switches, saves one switching cycle (MSB can be evaluated immediately after sampling opens).
- Exposed to input-dependent switch charge injection, clock feedthrough, and top-plate parasitic swing attenuation.

### Bottom-Plate Sampling
- Opening the top-plate reference switch slightly *before* the input switch makes charge injection signal-independent, giving higher linearity.
- Requires extra non-overlapping clock phases and adds complexity/settling overhead.

## Switching Schemes

Switching is an architectural decision affecting common-mode motion, switching energy, reference demand, and switch complexity:
- **Conventional (trial-and-error):** Baseline; highest switching energy, constant common mode.
- **Monotonic (set-and-down):** Very simple, ~80%+ switching energy savings, no `Vcm` buffer needed; however, top-plate common mode ramps down toward $V_{\text{cm}} - V_{\text{ref}}/2$, shifting comparator speed/offset across bits.
- **Vcm-based:** Constant common mode and high energy efficiency, but requires a strong, low-impedance `Vcm` reference switch/driver.
- **Split-capacitor / bidirectional:** Preserves constant common mode without a dedicated `Vcm` rail at the cost of splitting each capacitor into two switched halves.

## Redundancy (Sub-Radix-2 or Extra Redundant Cycles)

Redundancy pays off whenever speed or settling is tight:
- Allows early bit decisions (MSB / MSB−1) to be made before full $N$-bit CDAC or reference settling completes; subsequent bit trials recover errors within the redundancy range.
- Relaxes reference recovery stress and intermediate comparator error tolerance.
- Costs 1–2 extra bit cycles and a small digital recombination adder.

## Design Philosophy

- Aim for a **noise-limited** SAR ADC, pushing harmonic distortion well below the noise floor.
- Identify the single dominant limiter (comparator noise, $kT/C$, CDAC settling, sampling THD, jitter, or slow-corner timing) before spending effort optimizing secondary blocks.
