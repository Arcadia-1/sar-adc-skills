# On-Chip RC Relaxation Oscillator Design & First-Principles Theory

A process-independent engineering guide to **On-Chip RC Relaxation Oscillators** (1–50 MHz system clocks, IoT wakeup timers, and crystal-less MCU/SoC clock generators) — covering dual-capacitor ping-pong architectures, comparator propagation-delay error & cancellation, composite resistor temperature compensation, supply immunity, digital frequency trimming, cold-startup dynamics, and thermal period/C2C jitter budgets.

---

## 1. Architecture Comparison: Single-Cap vs. Dual-Cap Ping-Pong

| Topology | Mechanism | Duty Cycle | Reset-Time Error | Typical Accuracy (Trimmed, $-40\text{–}125^\circ\text{C}$) |
|---|---|---|---|---|
| **Single-Cap Hysteretic** | One capacitor charges/discharges between $V_H$ and $V_L$ (or charges & dumps) | Asymmetric if reset pulse is finite | Reset switch $R_{\text{on}} C$ adds directly to period | $\pm 3\% \text{–} \pm 8\%$ |
| **Dual-Cap (Ping-Pong) Switched-RC** | Two matched capacitors $C_A, C_B$ alternate: while $C_A$ ramps via $I_{\text{ref}}$ to $V_{\text{th}}$, $C_B$ fully resets to `VSS`, then roles swap | **Inherently $\approx 50\%$** (bounded only by $C_A/C_B$ mismatch) | **Zero** reset dead-time (reset occurs offline during opposite half-cycle) | **$\pm 0.5\% \text{–} \pm 2\%$** (with delay cancellation + composite $R$) |
| **RC Wien-Bridge / Phase-Shift** | Linear resonant RC filter + AGC loop | $50\%$ | None | $\pm 0.1\% \text{–} \pm 0.5\%$ (higher power & area) |

For crystal-less SoC/MCU system clocks ($4\text{–}32\text{ MHz}$), the **ratiometric dual-cap ping-pong relaxation oscillator** is the industrial workhorse: it runs at tens of microamps, wakes up in microseconds (vs. milliseconds for a quartz XO!), and needs zero external components.

---

## 2. First-Principles Period Equation & Ratiometric Cancellation

In a ratiometric switched-RC oscillator, a single reference current $I_{\text{ref}}$ (or voltage $V_{\text{ref}}$) simultaneously sets **both** the charging current $I_{\text{chg}} = V_{\text{ref}} / R_{\text{trim}}$ and the comparator threshold $V_{\text{th}} = \alpha V_{\text{ref}}$ (commonly $\alpha = 1$, or charging from $0$ to $V_{\text{ref}}$ through an RC step to $V_{\text{ref}} = V_{DD}(1 - e^{-1})$).

The half-period of each ping-pong phase is:

$$T_{\text{half}} = \frac{C_{\text{int}} V_{\text{th}}}{I_{\text{chg}}} + t_{\text{cmp}}(T, V_{DD}) = \alpha R_{\text{trim}}(T)\, C_{\text{int}}(T) + t_{\text{cmp}}(T, V_{DD})$$

Therefore, the oscillation frequency is:

$$f_{\text{osc}} = \frac{1}{2 \bigl[\alpha R_{\text{trim}}(T)\, C_{\text{int}}(T) + t_{\text{cmp}}(T, V_{DD})\bigr]}$$

Notice the critical insight: **$V_{\text{ref}}$ cancels out to first order!** Consequently, frequency stability over PVT is governed by **only three error sources**:
1. **Temperature drift of the $R \cdot C$ product** ($TC_1$, $TC_2$).
2. **Comparator propagation delay $t_{\text{cmp}}(T, V_{DD})$** (and its strong dependence on supply voltage and carrier mobility).
3. **Comparator input-referred offset $V_{\text{os}}$** (adds fractional error $V_{\text{os}} / V_{\text{th}}$, suppressed by chopping or auto-zeroing).

---

## 3. Temperature Compensation & Comparator-Delay Cancellation

### 3.1 Composite Resistor Zero-TC Network

Process capacitors (MIM or metal-fringe MOM) have tiny temperature coefficients ($|TC_C| \approx 10\text{–}40\text{ ppm/}^\circ\text{C}$), whereas single poly or diffusion resistors often exhibit $|TC_R| \approx 500\text{–}2000\text{ ppm/}^\circ\text{C}$.

Connecting a **positive-TC resistor** ($R_p$, $TC_{1p} > 0$) in series with a **negative-TC resistor** ($R_n$, $TC_{1n} < 0$) achieves first-order cancellation when:

$$\frac{R_p}{R_n} = -\frac{TC_{1n} + TC_C}{TC_{1p} + TC_C}$$

With first-order $TC_1$ nulled to within $\pm 15\text{–}30\text{ ppm/}^\circ\text{C}$, the remaining temperature drift is parabolic **second-order curvature** ($TC_2 \approx -0.3$ to $-0.6\text{ ppm/}^\circ\text{C}^2$):

$$\frac{\Delta(RC)}{(RC)_0} \approx TC_1 (T - T_0) + TC_2 (T - T_0)^2$$

Across the full automotive/industrial range ($-40^\circ\text{C}$ to $+125^\circ\text{C}$, $\Delta T = 165^\circ\text{C}$), a well-balanced composite resistor achieves **$0.4\%\text{–}0.8\%$ total RC drift** ($25\text{–}50\text{ ppm/}^\circ\text{C}$ box TC).

### 3.2 Comparator Propagation Delay — The Hidden PVT Killer

At $f_{\text{nom}} = 16\text{ MHz}$, the half-period is only $T_{\text{half}} = 31.25\text{ ns}$. A modest $2.0\text{ ns}$ comparator + latch delay accounts for **$6.4\%$ of the entire period**! Because $t_{\text{cmp}}$ scales roughly as:

$$t_{\text{cmp}}(T, V_{DD}) \approx t_{\text{cmp0}} \left(\frac{V_{DD,\text{nom}}}{V_{DD}}\right)^{\alpha_v} \bigl[1 + TC_{\text{cmp}}(T - T_0)\bigr]$$

with $\alpha_v \approx 1.0\text{–}1.5$ and $TC_{\text{cmp}} \approx +2000\text{–}3000\text{ ppm/}^\circ\text{C}$:
- **Uncompensated ($\eta_{\text{cancel}} = 0$)**: A $\pm 10\%$ $V_{DD}$ shift moves $f_{\text{osc}}$ by $\pm 0.8\%$ ($\sim 6\text{–}7\%/\text{V}$ supply sensitivity!), and temperature adds another $+2.5\%$ drift ($+150\text{ ppm/}^\circ\text{C}$).
- **With delay cancellation ($\eta_{\text{cancel}} = 0.80\text{–}0.95$)**:
  1. **Feed-forward / offset-compensated comparator (self-timed loop)**: An auxiliary integrator compares the average ramp voltage $\overline{V}_{\text{ramp}}$ against $\frac{1}{2} V_{\text{ref}}$ and lowers the dynamic threshold $V_{\text{th}} = V_{\text{ref}} - \Delta V_{\text{delay}}$ so that the ramp overshoots by exactly $t_{\text{cmp}} \cdot I/C$ and switches at $t = RC$!
  2. **Voltage-averaging / replica-delay feedback (Tokunaga / Cao architecture)**: Forces the time-averaged voltage across $R$ to equal $V_{\text{ref}}$, automatically absorbing comparator delay AND offset into the negative-feedback loop.
  3. **Local LDO supply regulation**: Powering the comparator and charging stage from a dedicated quiet internal LDO decouples $t_{\text{cmp}}$ from external $V_{DD}$ variations (reducing supply sensitivity to $< 1.0\%/\text{V}$).

---

## 4. Digital Frequency Trimming & Cold-Startup Dynamics

### 5-Bit / 6-Bit Process Trim Bank

Because absolute on-chip $R$ and $C$ vary by $\pm 15\text{–}20\%$ across process corners (`FF`/`SS` + resistor corners), every production RC oscillator includes a binary-weighted digital trim bank (e.g., 5-bit `VTRIM = 0..31` for $\pm 18\%$ range at $\sim 1.2\%/\text{LSB}$, or 6–8 bits when sub-$0.5\%$ factory calibration accuracy is required).

- **Conductance (parallel $R$ or binary current-DAC) trimming** yields a **linear, strictly monotonic $f(\text{code})$** characteristic:
  $$f(\text{code}) \approx f_{\text{nom}}\bigl[1 + k_{\text{trim}}(\text{code} - \text{code}_{\text{mid}})\bigr]$$
- **Capacitive binary-bank trimming** yields linear *period* $T(\text{code})$, so frequency step size slightly compresses at higher codes; always verify worst-case step size at the high-frequency extreme and verify monotonicity across all MSB transitions (`7->8`, `15->16`).

### Cold Startup (`EN` Rising Edge)

Unlike a quartz crystal oscillator (which requires $0.5\text{–}5\text{ ms}$ to build stored energy in a $Q > 20{,}000$ resonator), an RC relaxation oscillator stores zero resonant history and wakes up as fast as its internal bias/reference settles:

- **Shutdown state (`EN = 0`)**: Bias current cut to leakage ($I_{\text{shdn}} < 100\text{ nA}$), both integrating capacitors pre-discharged to `VSS`, and output held cleanly at `VSS` (glitch-free).
- **Release & pull-in (`EN = 1`)**: As the internal reference/bias settles with time constant $\tau_{\text{start}}$, the first cycle often runs $5\text{–}15\%$ slower (first-cycle error) before pulling inside $\pm 1\%$ of steady-state frequency within **$3\text{–}10$ clock cycles** ($t_{\text{startup},1\%} \approx 0.3\text{–}1.0\ \mu\text{s}$ at $16\text{ MHz}$).
- **Clock-gating safeguard**: Gate the downstream SoC clock for $N_{\text{mask}} = 4\text{–}8$ internal cycles after `EN` rises so digital flip-flops never see a runt pulse or oversized first-cycle error!

---

## 5. Period Jitter, Cycle-to-Cycle Jitter, & Power Trade-Off

In an RC relaxation oscillator, timing jitter arises primarily from **thermal noise of the charging current/resistor integrated on $C_{\text{int}}$** and **wideband comparator input-referred voltage noise $v_{n,\text{cmp}}$** sampled at the ramp threshold crossing.

### Analytical Period Jitter & C2C Relationship

When a ramp of slope $S = I_{\text{chg}} / C_{\text{int}} = V_{\text{th}} / T_{\text{half}}$ crosses the noisy comparator threshold with RMS voltage noise $\sigma_v$, the timing uncertainty per half-cycle is $\sigma_{t,\text{half}} = \sigma_v / S$. Summing two uncorrelated half-cycles gives the **full-period RMS jitter**:

$$\sigma_{T,\text{per}} = \sqrt{2}\,\frac{\sigma_v}{V_{\text{th}}}\,T_{\text{half}} = \frac{T_{\text{per}}}{\sqrt{2}}\,\frac{\sigma_v}{V_{\text{th}}}$$

For wideband (white, cycle-to-cycle uncorrelated) comparator + charging thermal noise:
- **Cycle-to-cycle (C2C) RMS jitter** satisfies the exact statistical identity:
  $$\sigma_{T,\text{c2c}} = \sqrt{\text{Var}(T_{k+1} - T_k)} = \sqrt{2}\,\sigma_{T,\text{per}}$$
- **Checking the $\sigma_{T,\text{c2c}} / \sigma_{T,\text{per}}$ ratio in Spectre** is a powerful diagnostic:
  - Ratio $\approx \sqrt{2} \approx 1.414$: pure white thermal noise dominates (healthy comparator/resistor noise floor).
  - Ratio $\ll 1.414$: correlated low-frequency $1/f$ noise or periodic supply ripple is modulating the period!
  - Ratio $> 1.414$: alternating even/odd half-cycle mismatch or deterministic duty-cycle alternation.

### Jitter–Power Trade-Off & Duty Cycle Hygiene

- **Lowering $\sigma_{T,\text{per}}$ by $2\times$ costs $4\times$ power**: Because $\sigma_v^2 \propto kT / C$ or $kT / g_{m,\text{cmp}}$ while $I_{\text{chg}} = C V_{\text{th}} / T_{\text{half}}$, cutting RMS jitter in half requires $4\times$ larger $C_{\text{int}}$ and $4\times$ higher $I_{\text{chg}}$ (and $4\times$ higher comparator $g_m$).
- **Duty cycle error**: In a ping-pong dual-cap oscillator, $|D - 50\%| \approx \frac{1}{4}|\Delta C/C| + \frac{1}{2}|\Delta V_{\text{os}}/V_{\text{th}}|$. Matching $C_A$ and $C_B$ in a common-centroid unit array keeps duty-cycle error within $\pm 0.5\text{–}1.5\%$ without requiring an output divide-by-2 (which would double core power for the same output frequency).
- **Edge rise/fall times ($t_r$, $t_f$)**: Size the output buffer inverter chain so $10\%\text{–}90\%$ $t_r, t_f < 0.05\,T_{\text{per}}$ (e.g., $< 500\text{ ps}$ at $16\text{ MHz}$) to prevent downstream clock-tree noise amplification while avoiding excessive crowbar current on `VDD`.
