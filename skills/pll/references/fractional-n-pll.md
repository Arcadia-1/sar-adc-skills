# Fractional-N $\Delta\Sigma$ PLL Design

## 1. Why Fractional-N?

In an Integer-N PLL, fine channel spacing $\Delta f = f_{\text{ref}}$ forces a tiny $f_{\text{ref}}$ and a huge division ratio $N = f_{\text{out}} / f_{\text{ref}}$, inflating in-band phase noise by $+20\log_{10} N$ and cramping loop bandwidth $f_{\text{BW}} \le f_{\text{ref}}/10$.

A **Fractional-N PLL** decouples channel resolution from $f_{\text{ref}}$ by dynamically dithering a **Multi-Modulus Divider (MMD)** between integer values around $N_{\text{int}}$ so the long-term average division ratio is:

$$N_{\text{eff}} = N_{\text{int}} + \alpha, \qquad \alpha = \frac{K_{\text{frac}}}{2^M} \in [0, 1)$$

This allows high $f_{\text{ref}}$ (tens to hundreds of MHz $\implies$ small $N$, low in-band noise, wide bandwidth, fast locking) while achieving arbitrarily fine frequency steps $\Delta f = f_{\text{ref}} / 2^M$.

---

## 2. MASH 1-1-1 $\Delta\Sigma$ Modulator & Noise Shaping

A naive 1st-order accumulator produces strong periodic fractional spurs at $f_{\text{frac}} = \alpha f_{\text{ref}}$. Standard RF/clocking Fractional-N PLLs use a **3rd-order MASH 1-1-1** (Multi-stAge noise SHaping: cascade of three 1st-order error-feedback accumulators with digital differentiators):

- **Guaranteed stability** (feedforward cascade of unconditionally stable 1st-order accumulators — no single-loop instability).
- **Output integer sequence:** $y[n] \in \{-3, -2, -1, 0, +1, +2, +3, +4\}$ (8 levels), so instantaneous divider modulus is $N[n] = N_{\text{int}} + y[n]$.
- **Frequency-domain quantization error transfer:** $E_y(z) = (1 - z^{-1})^3 E_3(z)$.
- **Phase-domain quantization noise PSD** (integrating frequency step error through $1/(1 - z^{-1})$ drops the shaping order by one, from $L$ to $L-1$):

$$S_{\phi,\Delta\Sigma}(f) = \frac{(2\pi)^2}{12 \, f_{\text{ref}}} \left[ 2 \sin\left(\frac{\pi f}{f_{\text{ref}}}\right) \right]^{2(L - 1)} \quad [\text{rad}^2/\text{Hz}]$$

For MASH 1-1-1 ($L = 3$):
- At $f \ll f_{\text{ref}}$: rises at $+40\text{ dB/dec}$ ($2(L-1) = 4$th power of frequency!).
- At $f = f_{\text{ref}}/2$: peaks at $\frac{(2\pi)^2}{12 f_{\text{ref}}} \cdot 2^4 = \frac{16 \pi^2}{3 f_{\text{ref}}}$.
- **Seeding / dithering rule:** Initialize the first accumulator's LSB to `1` (or inject 1-LSB LFSR dither) so rational fractions like $K_{\text{frac}}/2^M = 1/8$ or $1/4$ do not fall into short deterministic limit cycles that generate discrete fractional tones!

---

## 3. Loop Filter Order Requirement for $\Delta\Sigma$ Suppression

Because $S_{\phi,\Delta\Sigma}(f)$ rises at $+20(L-1)\text{ dB/dec}$ ($+40\text{ dB/dec}$ for MASH 1-1-1):
- The closed-loop PLL transfer $|H(j2\pi f)|^2$ **must roll off faster than $+40\text{ dB/dec}$** above $f_{\text{BW}}$ so the integrated $\Delta\Sigma$ quantization noise converges cleanly and stays below the VCO out-of-band floor.
- A **2nd-order passive filter** ($R, C_1, C_2$, 3rd-order PLL) gives $-40\text{ dB/dec}$ power roll-off above $\omega_{p2}$ (barely flat against MASH 1-1-1!).
- A **3rd-order passive filter** ($R, C_1, C_2, R_3, C_3$, 4th-order PLL) gives **$-60\text{ dB/dec}$** power roll-off above $\omega_{p3}$ — **strongly recommended** for MASH 1-1-1 Fractional-N PLLs!
- Rule of thumb for loop bandwidth: $f_{\text{BW}} \le f_{\text{ref}} / 30\text{–}f_{\text{ref}} / 50$ when targeting low-jitter MASH 1-1-1 without quantization-noise cancellation (DAC/DTC cancellation permits wider $f_{\text{BW}}$ up to $f_{\text{ref}}/15$).

---

## 4. The #1 Fractional-N Pitfall: Charge-Pump Nonlinearity & Noise Folding

Even if your linear loop filter suppresses $\Delta\Sigma$ quantization noise by 60 dB at $f_{\text{ref}}/2$, **any nonlinearity in the PFD/CP transfer curve** (principally Up vs. Down current mismatch $\Delta I = I_{\text{up}} - I_{\text{dn}}$ around $\Delta t = 0$) acts as a rectifier/mixer on the wide instantaneous $\Delta\Sigma$ phase swing ($\pm 3\text{–}4\,T_{\text{vco}}$):

1. **In-band noise folding:** High-frequency shaped $\Delta\Sigma$ noise mixes down to DC, raising the in-band phase-noise floor by **10–25 dB** — often completely dominating the PLL jitter!
2. **Fractional & Integer-Boundary Spurs (IBS):** When $\alpha = K_{\text{frac}}/2^M$ is very small (e.g., $\alpha = 1/1024$), the fundamental fractional frequency $\alpha f_{\text{ref}}$ falls **inside the loop bandwidth** ($< f_{\text{BW}}$), where the loop filter cannot attenuate it at all!

### Practical Mitigations
- **Constant static bleed / offset current ($I_{\text{offset}}$):** Inject a fixed DC bleed current at the CP output so the steady-state phase error shifts away from zero ($\Delta t_{\text{bias}} > \max|\Delta t_{\Delta\Sigma}| \approx 4 T_{\text{vco}}$). Then the CP always operates strictly on **one side** of the transfer curve (`UP`-only or `DN`-only) with a single constant slope $I_{\text{up}}$ or $I_{\text{dn}}$, eliminating the kink at $\Delta t = 0$! (Cost: higher reference spur at $f_{\text{ref}}$ and slightly higher CP noise — trade off carefully.)
- **Tight CP matching + output voltage tracking:** Use an opamp unity-gain replica buffer to hold the inactive CP branch at `VCTRL` (eliminating charge-sharing spikes).
- **Digital-to-Time Converter (DTC) / DAC quantization cancellation:** Cancels the deterministic MASH phase error before the PFD/CP, shrinking phase swing from $\pm 4 T_{\text{vco}}$ to $< 0.1 T_{\text{vco}}$ and dramatically relaxing both CP linearity and loop-filter roll-off.

---

## How to Verify a Fractional-N PLL

> **Ready-to-run process-independent Spectre testbenches:** See [`../assets/tb/frac_n_pll/`](../assets/tb/frac_n_pll/README.md) (`tb_frac_n_pll_lock.scs`, `analyze_frac_n_pll.py`), [`../assets/tb/divider/`](../assets/tb/divider/README.md) (`tb_div_func_mmd.scs`), and [`../assets/va/va_mmd_mash111.va`](../assets/va/va_mmd_mash111.va).

1. **Standalone MMD + MASH 1-1-1 Verification (`tb_div_func_mmd.scs`):**
   - Run for $\ge 256\text{–}1024$ divider output cycles and confirm the time-averaged division ratio matches $N_{\text{int}} + K_{\text{frac}}/2^M$ to $< 0.01\%$ and instantaneous moduli stay within $[N_{\text{int}} - 3, N_{\text{int}} + 4]$.
2. **Closed-Loop Fractional Lock (`tb_frac_n_pll_lock.scs`):**
   - Test a non-trivial prime fraction (e.g., $N_{\text{eff}} = 20 + 13/128 = 20.1015625$ at $f_{\text{ref}} = 50\text{ MHz} \implies f_{\text{out}} = 1.005078125\text{ GHz}$).
   - Verify frequency lock accuracy, `VCTRL` peak-to-peak $\Delta\Sigma$ ripple, and compare **matched CP ($\Delta I = 0$)** vs. **mismatched CP ($\Delta I = 5\%$)** to directly observe noise folding and fractional spurs!
3. **Integer-Boundary Spur (IBS) Stress:**
   - Set $\alpha$ so $\alpha f_{\text{ref}} \approx 0.3\,f_{\text{BW}}$ (inside loop bandwidth) and verify worst-case IBS level with realistic CP mismatch and VCO-to-ref coupling.
