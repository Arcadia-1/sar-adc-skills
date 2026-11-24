# Robustness And System Closure

Use this file for PVT and Monte Carlo interpretation, metastability and BER, reference strategy, input drive, supply/clock integrity, and product-level closure.

## PVT And Monte Carlo Thinking

- **Separate global variation from local mismatch:**
  - Global corners (`ss`/`tt`/`ff`, voltage, temperature) primarily govern speed, operating points, and loop timing closure.
  - Local mismatch governs CDAC DNL/INL and comparator random offset.
- **Avoid unrealistic pessimism:** Mechanically stacking worst-case local+global corners (`SS` + full local Monte Carlo) double-counts variation. When the PDK provides global-only corners (`SSG`/`FFG`), combine those with local Monte Carlo instead.
- **Supply / margin strategy:** Leaving full timing margin at nominal `VDD` across `ss` is cleanest; when `ss` timing is marginally tight, document whether supply boost at slow corners (or speed binning) is an acceptable system-level knob — and keep post-layout RC slowdown (often 10–25%) in the margin budget from day one.

## Metastability And BER

- In a functionally verified SAR ADC, rare catastrophic code errors trace primarily to **comparator metastability** on near-zero residues.
- Metastability probability decays **exponentially** with available regeneration time:
  $$P_{\text{meta}} \propto \exp\!\left(-\frac{t_{\text{avail}}}{\tau}\right)$$
  giving the comparator more regeneration time (or smaller $\tau$) is the most effective lever.
- **Counterproductive "fixes":** Adding heavy metastability-detection circuitry onto the latch nodes increases $C_{\text{latch}}$ and $\tau$, often making BER *worse*.
- **Async advantage:** Asynchronous SAR naturally lets a single slow metastable bit borrow slack from the other $N-1$ fast bits, improving BER dramatically over fixed-slot synchronous SAR.
- **MTF reality check:** At 1 GS/s, a BER of $10^{-12}$ still means one error every ~17 minutes; size BER against target Mean Time to Failure (MTF), not an arbitrary number.

## Reference Path

Two primary strategies:
- **Large on-chip/off-chip decoupling capacitor:** Zero static power, but costs area and can ring with package/bondwire inductance (`L_pkg` + `C_decap`).
- **Fast reference buffer:** Active recovery between conversions and smaller area, at the cost of power and stability/noise co-design.

Check reference droop across a worst-case full-scale switching sequence (including input-dependent reference current, which turns into distortion!).

## Input Drive Path

Verify:
- Source impedance $R_s$ and sampling settling inside $T_{\text{sample}}$ (remember kickback from the sampling switch and CDAC back onto the driver!),
- Whether a wideband high-linearity input buffer / THA is needed (for high-$f_s$, low-distortion systems, buffer output impedance and metal routing resistance must stay very low),
- Anti-aliasing filter bandwidth and input amplitude/common-mode matching.

## Supply And Clock Integrity

- **Supply:** IR drop, bondwire $L\,di/dt$, and shared digital/analog rails inject deterministic spurs and degrade ENOB; decouple locally near comparator and SAR logic.
- **Clock:** At high $f_{\text{in}}$, aperture jitter imposes a hard SNR ceiling ($\text{SNR}_{\text{jit}} = -20\log_{10}(2\pi f_{\text{in}} \sigma_t)$) that no core improvement can overcome.

## Product-Level Closure Checklist

Moving from a schematic core to a shippable SAR ADC requires closing:
- usable full swing after top-plate parasitics,
- pre- and post-layout PVT timing margin (including slow corners and race margins),
- reference recovery and supply PSRR,
- sampling linearity up to Nyquist,
- CDAC mismatch DNL/INL and comparator offset/trim,
- metastability / BER target,
- clock jitter and input-driver co-simulation.
