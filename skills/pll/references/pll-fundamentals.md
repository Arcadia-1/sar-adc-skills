# PLL Fundamentals & Architecture Selection

## 1. Phase-Domain Linear Model

Near lock (small phase error $|\Delta\phi| \ll \pi$), any charge-pump or digital PLL can be analyzed in the continuous-time phase domain ($s = j 2\pi f$) as long as the loop bandwidth satisfies the discrete-time sampling bound $f_{\text{BW}} \le f_{\text{ref}} / 10$ (Gardner stability limit).

- **Forward path:** Phase detector gain $K_d$ ($\text{A/rad}$ for CP-PLL, $\text{LSB/rad}$ for TDC-ADPLL) $\to$ loop filter $Z_{\text{LF}}(s)$ (or digital transfer $H_{\text{DLF}}(s)$) $\to$ oscillator integrator $\frac{K_{\text{osc}}}{s}$ (where $K_{\text{osc}} = 2\pi K_{\text{VCO}}\;[\text{rad/s/V}]$ or $2\pi K_{\text{DCO}}\;[\text{rad/s/LSB}]$).
- **Feedback path:** Frequency division by $N$ (an ideal phase divider of gain $1/N$).

The open-loop gain is:

$$L(s) = \frac{K_d \, Z_{\text{LF}}(s) \, K_{\text{osc}}}{N \, s}$$

The closed-loop reference-to-output phase transfer function is:

$$H_{\text{ref}}(s) = \frac{\Phi_{\text{out}}(s)}{\Phi_{\text{ref}}(s)} = N \cdot \frac{L(s)}{1 + L(s)} = N \cdot H(s)$$

where $H(s) = \frac{L(s)}{1 + L(s)}$ is the unity-DC-gain low-pass loop transfer function, and $1 - H(s) = \frac{1}{1 + L(s)}$ is the complementary high-pass error transfer function.

---

## 2. Type-I vs. Type-II Loops

- **Type-I PLL** (one integrator in $L(s)$, from the VCO alone):
  - Requires a non-zero static phase error $\phi_e = \Delta\omega / (K_d K_{\text{osc}}/N)$ to hold any VCO control voltage away from its free-running point.
  - Tradeoff between ripple filtering (needs low-pass pole) and stability severely restricts acquisition range and bandwidth.
- **Type-II PLL** (two integrators in $L(s)$: VCO + integrating capacitor $C_1$ in a CP-PLL, or digital accumulator $\beta/(1 - z^{-1})$ in an ADPLL):
  - **Zero static phase error** across PVT and frequency channels (assuming zero CP leakage/mismatch).
  - Requires a stabilizing **left-half-plane zero** $\omega_z = 1 / (R C_1)$ (analog) or proportional path $\alpha$ (digital) to restore phase margin before unity gain.
  - Standard workhorse for Integer-N CP-PLLs, Fractional-N CP-PLLs, and TDC-based ADPLLs.

---

## 3. Noise Transfer Functions & Optimal Bandwidth

Each noise source sees a distinct transfer function to the PLL output phase $\Phi_{\text{out}}(f)$:

| Noise Source | Transfer to Output $\Phi_{\text{out}}$ | Shaping | Dominant Frequency Region |
|---|---|---|---|
| Reference clock $\Phi_{\text{ref}}$ | $N \cdot H(s)$ | Low-pass ($+20\log_{10} N$ in-band gain) | In-band ($f < f_{\text{BW}}$) |
| PFD + CP current $I_{n,\text{cp}}$ | $\frac{N}{K_d} H(s)$ | Low-pass | In-band ($f < f_{\text{BW}}$) |
| Divider phase noise $\Phi_{\text{div}}$ | $N \cdot H(s)$ | Low-pass | In-band ($f < f_{\text{BW}}$) |
| TDC quantization / noise (ADPLL) | $N \cdot H(s)$ | Low-pass | In-band ($f < f_{\text{BW}}$) |
| Loop filter resistor $R$ thermal noise | $\frac{K_{\text{osc}}/s}{1 + L(s)}$ | Band-pass (peaks near $f_{\text{BW}}$) | Around $f_{\text{BW}}$ |
| $\Delta\Sigma$ quantization noise (Frac-N) | $H(s)$ (divided by $N$, then $\times N$) | High-pass shaped $(1 - z^{-1})^L \cdot H(s)$ | Near $f_{\text{BW}}$ to $f_{\text{ref}}/2$ |
| VCO / DCO free-running noise $\Phi_{\text{osc}}$ | $1 - H(s)$ | High-pass | Out-of-band ($f > f_{\text{BW}}$) |

**Optimal loop bandwidth ($f_{\text{BW,opt}}$):**
- **Too narrow $f_{\text{BW}}$:** VCO/DCO $1/f^3$ and $1/f^2$ phase noise is under-suppressed; slow frequency locking.
- **Too wide $f_{\text{BW}}$:** In-band reference, CP, TDC, and Frac-N $\Delta\Sigma$ quantization noise flood the output; approaches the discrete-time stability limit $f_{\text{ref}}/10$.
- **Minimum RMS jitter rule:** Place $f_{\text{BW,opt}}$ near the **intersection frequency** where the extrapolated in-band noise floor (referred to the output: $N^2 S_{\phi,\text{inband}}$) crosses the free-running VCO/DCO phase noise $\mathcal{L}_{\text{osc}}(f)$ — subject to reference-spur and $\Delta\Sigma$-noise attenuation constraints.

---

## 4. Phase Noise to RMS Jitter Conversion

Given single-sideband phase noise $\mathcal{L}(\Delta f)$ in $\text{dBc/Hz}$ integrated over $[f_{\text{low}}, f_{\text{high}}]$ (e.g., `10 kHz` to `40 MHz` or `100 kHz` to $f_{\text{out}}/2$):

$$\sigma_\phi = \sqrt{2 \int_{f_{\text{low}}}^{f_{\text{high}}} 10^{\mathcal{L}(f)/10}\, df} \quad [\text{rad}_{\text{rms}}]$$

$$\sigma_t = \frac{\sigma_\phi}{2\pi f_{\text{out}}} \quad [\text{s}_{\text{rms}}]$$

- Factor of $2$ accounts for both upper and lower sidebands around the carrier.
- **Quick sanity check:** At $f_{\text{out}} = 2.4\text{ GHz}$, an integrated DSB noise of $-40\text{ dBc}$ ($\sigma_\phi = 0.01\text{ rad} = 0.573^\circ$) corresponds to $\sigma_t = 0.01 / (2\pi \cdot 2.4\times 10^9) \approx 663\text{ fs}_{\text{rms}}$.
- Distinguish **three jitter definitions** carefully:
  - **Absolute (integrated) phase jitter $\sigma_t$:** Critical for RF LO EVM, SerDes clock synthesis, and high-$f_{\text{in}}$ ADC sampling clocks ($\text{SNR}_{\text{jitter}} = -20\log_{10}(2\pi f_{\text{in}} \sigma_t)$).
  - **Period jitter $\sigma_{\text{per}}$:** Variation of single cycle duration $T_k - \bar{T}$ (weights high-offset noise by $4\sin^2(\pi f T_0)$ — matters for digital setup/hold timing).
  - **Cycle-to-cycle jitter $\sigma_{\text{c2c}}$:** Variation of adjacent cycles $T_{k+1} - T_k$ (weights by $16\sin^4(\pi f T_0)$).

---

## 5. Architecture Selection: Integer-N vs. Fractional-N vs. ADPLL

| Criterion | Integer-N CP-PLL | Fractional-N CP-PLL ($\Delta\Sigma$) | ADPLL (TDC or Bang-Bang) |
|---|---|---|---|
| Frequency step $\Delta f$ | $f_{\text{ref}}$ (coarse; forcing small $f_{\text{ref}}$ raises $N$ and ruins in-band noise!) | $f_{\text{ref}} / 2^M$ (sub-Hz resolution at high $f_{\text{ref}}$) | $f_{\text{ref}} / 2^M$ (digital FCW) |
| Division ratio $N$ | High if fine step needed ($\implies +20\log_{10} N$ noise penalty) | Low (high $f_{\text{ref}}$ independent of channel spacing) | Low (high $f_{\text{ref}}$) |
| Area (loop filter) | Large passive MOM/MIM cap $C_1$ | Large passive cap $C_1$ + 3rd pole $C_3$ | **Compact digital filter** (scales cleanly with advanced CMOS) |
| Dominant spurs | Reference spurs at $\pm k f_{\text{ref}}$ | Integer-boundary spurs (IBS) + fractional spurs from CP nonlinearity | TDC nonlinearity spurs + DCO quantization spurs / BB limit cycles |
| Key design bottleneck | CP mismatch, leakage, $C_1$ area vs. $f_{\text{BW}}$ | CP linearity (preventing $\Delta\Sigma$ noise folding!) | TDC resolution $\Delta t_{\text{res}}$ & DCO fine step $K_{\text{DCO}}$ |
| Best fit | Fixed-frequency clock multiplier (e.g., SerDes, ADC clock, high $f_{\text{ref}}$) | RF frequency synthesizer requiring low phase noise + fine channel spacing | Scaled digital CMOS SoC, fast gear-shifting / digital calibration / modulation |
