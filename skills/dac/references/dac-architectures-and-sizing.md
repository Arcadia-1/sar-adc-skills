# DAC Architectures, Static Yield & System Budgets

## 1. Architecture Selection Matrix

| Architecture | Typical Resolution & Rate | Output Interface | Inherent Monotonicity? | Primary Limiters & Use Cases |
|---|---|---|---|---|
| **Current-Steering (CS-DAC)** | 10–16 bit, 50 MS/s–10 GS/s | Differential current into $50\;\Omega$ | Only thermometer portion | Unit-cell $Z_{\text{out}}(f)$ (HD3), Pelgrom current mismatch (INL), switch skew (glitch); RF/wireless/wireline/video transmitters |
| **R-2R Ladder** (voltage or current mode) | 8–12 bit, 1–50 MS/s | Single-ended voltage or virtual-ground opamp | No (MSB 2R mismatch!) | Resistor matching, switch $R_{\text{on}}$ scaling (must scale $W$ by $2^k$ in binary legs!), RC settling; trim/bias/instrumentation |
| **Resistor-String (Kelvin)** | 6–10 bit (or 12b 2-stage), <10 MS/s | Voltage tap (needs buffer) | **Yes** (always monotonic!) | $2^N$ switches & tap capacitance (area explodes for $N > 10$); LCD/display drivers, trim DACs, coarse sub-DACs |
| **Capacitive DAC (CDAC)** | 8–14 bit, switched-cap | Charge redistribution | With thermometer/redundancy | $kT/C$, top-plate parasitic, switch settling; embedded in SAR/pipeline ADCs (see [`skills/sar-adc/references/cdac.md`](../../sar-adc/references/cdac.md)) |
| **Oversampled $\Delta\Sigma$ DAC** | 16–24 bit, audio–10 MHz BW | 1-bit or multi-bit + analog LPF | 1-bit is inherently linear! | Clock jitter (especially 1-bit!), multi-bit element mismatch (solved via **DWA / DEM**), reconstruction filter |

---

## 2. Segmentation Trade-Off (Thermometer vs. Binary)

A pure binary $N$-bit DAC switches up to $2^{N-1}$ unit elements simultaneously at the mid-scale major carry (`0111...1 -> 1000...0`), creating maximum DNL sensitivity and maximum glitch impulse. A pure thermometer DAC needs $2^N - 1$ decoders and switch drivers (prohibitive for $N \ge 10$).

**Segmented CS-DAC ($N = M_{\text{therm}} + B_{\text{bin}}$):**
- Upper $M$ bits drive $2^M - 1$ equally weighted thermometer cells (each of weight $2^B I_{\text{lsb}}$).
- Lower $B$ bits drive binary-weighted cells ($2^{B-1}, \dots, 1 \times I_{\text{lsb}}$).
- **Major-carry DNL variance** drops by $2^M$ relative to pure binary:
  $$\sigma_{\text{DNL,max}} \approx \sqrt{2^{B+1} - 1}\,\frac{\sigma_I}{I_{\text{lsb}}} \quad\text{(vs. }\sqrt{2^N - 1}\,\frac{\sigma_I}{I_{\text{lsb}}}\text{ for pure binary)}$$
- **Glitch impulse** at worst-case code transition also drops by $\sim 2^M$ because only a single thermometer unit switches alongside the $B$ binary bits!
- **Note on INL:** Segmentation **improves DNL and glitch dramatically, but does NOT reduce worst-case INL**! Mid-scale INL still sums $2^{N-1}$ independent unit current sources regardless of decoding.
- **Practical sweet spot:** $M = 5\text{–}7$ thermometer bits for 10–14 bit CS-DACs (e.g., `6+4` for 10-bit = 63 therm + 4 binary; `7+5` or `6+6` for 12-bit).

---

## 3. Pelgrom Mismatch & INL Yield Sizing

For an $N$-bit current-steering DAC with independent unit current-source relative standard deviation $\sigma_I / I_{\text{unit}}$, the maximum INL distribution across the $2^N$ codes reaches its peak variance at mid-scale ($\sigma_{\text{INL,mid}} = \frac{1}{2}\sqrt{2^N - 1}\,\frac{\sigma_I}{I_{\text{unit}}}$). For a target parametric yield $Y$ (using Van den Bosch's verified INL yield criterion):

$$\frac{\sigma_I}{I_{\text{unit}}} \le \frac{\text{INL}_{\text{spec}}}{C(Y)\,\sqrt{2^{N-1}}}$$

where $C(Y) \approx 2.0$ for 95% yield, $2.6$ for 99% yield, and **$3.0\text{–}3.3$ for 99.7% yield** on $\text{INL}_{\text{spec}} = 0.5\text{ LSB}$!

**Numerical Example (10-bit CS-DAC, 99.7% INL $< 0.5\text{ LSB}$ yield):**
- $\sqrt{2^9} = 22.63$, $C \approx 3.0 \implies \frac{\sigma_I}{I_{\text{unit}}} \le \frac{0.5}{3.0 \times 22.63} \approx \mathbf{0.73\%}$.
- Linking to Pelgrom's mismatch law for a saturated MOS current source biased at overdrive $V_{\text{ov}} = V_{GS} - V_{\text{th}}$:
  $$\left(\frac{\sigma_I}{I}\right)^2 = \frac{1}{WL}\left[A_\beta^2 + \frac{4 A_{VT}^2}{V_{\text{ov}}^2}\right] \implies (WL)_{\text{unit}} \ge \frac{A_\beta^2 + 4 A_{VT}^2 / V_{\text{ov}}^2}{(\sigma_I / I_{\text{unit}})^2}$$
- **Key sizing lever:** Raising current-source overdrive $V_{\text{ov}}$ (typically `200–350 mV` when supply headroom permits) quadratically shrinks the area $(WL)_{\text{unit}}$ required to meet INL yield — trading compliance headroom directly against silicon area and parasitic wiring capacitance!

---

## 4. R-2R Ladder Sizing Pitfalls

For an $N$-bit voltage-mode R-2R ladder:
- Open-circuit Thevenin output is $V_{\text{out}}(k) = V_{\text{ref}} \cdot k / 2^N$ with **code-independent output resistance $R_{\text{out}} = R$** (assuming ideal zero-resistance switches!).
- **Switch $R_{\text{on}}$ trap:** Any uncompensated switch resistance $R_{\text{sw}}$ in series with the `2R` shunt legs breaks the `1:2` ladder ratio!
  - Either keep $R_{\text{sw}} \ll 2R / 2^N$ (requiring $R_{\text{sw}} < R / 512$ for 10 bits — huge switches or high $R$!), **or** pre-subtract $R_{\text{sw}}$ from the `2R` poly resistor (`2R - R_sw`) and match switch widths to resistor tracking across PVT (still limited by switch-to-resistor PVT mismatch!).
- **Current-mode R-2R** ties the ladder output to a virtual-ground opamp summing node (`V_out = -I_out * R_fb`), keeping switch source voltages constant at `V_cm` so switch $R_{\text{on}}$ is signal-independent, at the expense of opamp GBW/slew/noise!

---

## 5. Zero-Order Hold (ZOH) Sinc Roll-Off, Noise & Clock Jitter

### ZOH Sinc Attenuation & Spectral Images
A conventional NRZ DAC holds each sample constant for $T_s = 1/f_s$, multiplying its output spectrum by:

$$H_{\text{ZOH}}(f) = \text{sinc}\!\left(\frac{f}{f_s}\right) = \frac{\sin(\pi f / f_s)}{\pi f / f_s}$$

- At Nyquist ($f = f_s/2$), ZOH causes **$20\log_{10}(2/\pi) = -3.92\text{ dB}$** droop (compensated in digital pre-emphasis FIR filter when needed).
- Spectral images appear at $k f_s \pm f_{\text{sig}}$ ($k = 1, 2, \dots$) and must be attenuated by an analog reconstruction filter (or exploited intentionally in **RF / mixing-mode DACs** operating in the 2nd/3rd Nyquist zone!).

### Quantization, Thermal Noise & Jitter Ceilings
- **Ideal quantization SQNR:** $\text{SQNR} = 6.02 N + 1.76\text{ dB}$ (with full-scale digital sine; note that in a **two-tone test**, each tone sits at $-6\text{ dBFS}$ so the summed peak never clips!).
- **Clock jitter SNR ceiling (identical physics to ADC aperture jitter!):**
  $$\text{SNR}_{\text{jit}} = -20\log_{10}\!\left(2\pi f_{\text{sig}} \sigma_t\right)$$
  For example, a `100 MHz` output tone requiring $\text{SNR}_{\text{jit}} \ge 70\text{ dB}$ demands $\sigma_t \le \mathbf{0.50\text{ ps}_{\text{rms}}}$!
- **Output Noise Spectral Density (NSD):** Commonly specified in `dBm/Hz` into $50\;\Omega$ (differential $100\;\Omega$) for RF/wireline DACs:
  $$\text{NSD}_{\text{quant}} \approx P_{\text{FS,dBm}} - (6.02 N + 1.76) - 10\log_{10}(f_s / 2)$$
  Ensure total current-source thermal noise stays below the quantization + target NSD floor.
