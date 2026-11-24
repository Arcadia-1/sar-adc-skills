# Bandgap Voltage Reference (BGR) Fundamentals & Sizing

## 1. PTAT + CTAT Cancellation Principle

A silicon bandgap reference cancels the negative temperature slope of a diode/PNP base-emitter voltage $V_{BE}(T)$ (CTAT, $\approx -1.8\text{ to }-2.0\text{ mV/K}$) against a scaled positive-slope thermal voltage $\Delta V_{BE} = V_T \ln M = \frac{kT}{q} \ln M$ (PTAT, $+0.0862 \ln M\;\text{mV/K}$) between two matched vertical substrate PNPs (or lateral BJTs) of emitter-area ratio $M$ (commonly $M = 8$ in a $3\times 3$ common-centroid array with the unit device at the center, or $M = 24$ in a $5\times 5$ array to lower offset amplification):

$$V_{\text{ref}}(T) = V_{BE}(T) + K \cdot V_T \ln M \approx 1.20\text{–}1.25\text{ V}$$

### Core Architectures

| Architecture | Output Formula | Min $V_{\text{DD}}$ | Strengths & Tradeoffs |
|---|---|---|---|
| **Classic Kuijk / Brokaw** (voltage-mode) | $V_{\text{ref}} = V_{BE1} + \frac{R_2}{R_1} V_T \ln M \approx 1.22\text{ V}$ | $\ge 1.4\text{–}1.5\text{ V}$ | Minimal resistor branches, lower noise; cannot run at sub-1 V supplies |
| **Banba** (current-mode sub-1 V) | $V_{\text{ref}} = \frac{R_3}{R_2}\!\left[V_{BE1} + \frac{R_2}{R_1} V_T \ln M\right]$ | $\ge 0.9\text{–}1.0\text{ V}$ | Arbitrary scaled $V_{\text{ref}}$ (e.g. `0.5–0.6 V`); extra mirror & $R_2$ branches add noise and mismatch |
| **Resistorless / Sub-threshold CMOS** | $\Delta V_{GS}$ vs. $V_{GS}$ or hybrid BJT-MOS | $\ge 0.7\text{–}0.8\text{ V}$ | Ultra-low nA quiescent power; higher $3\sigma$ process spread (requires trimming) |

- For $M = 8$ ($\ln 8 = 2.0794$), $\frac{d\Delta V_{BE}}{dT} = +0.1792\text{ mV/K}$, so $K = R_2 / R_1 \approx 9.5\text{–}10.5$ balances $\frac{dV_{BE}}{dT} \approx -1.8\text{ mV/K}$.

---

## 2. Temperature Coefficient (TC), Curvature & Error Sources

### Box-Method Temperature Coefficient
Measured across $[T_{\min}, T_{\max}]$ (typically $-40^\circ\text{C}$ to $+125^\circ\text{C}$, $\Delta T = 165^\circ\text{C}$):

$$\text{TC} = \frac{V_{\text{ref,max}} - V_{\text{ref,min}}}{V_{\text{ref}}(27^\circ\text{C}) \cdot (T_{\max} - T_{\min})} \times 10^6 \quad [\text{ppm}/^\circ\text{C}]$$

### Inherent 2nd-Order Curvature (Tsividis Formula)
Exact silicon BJT physics gives:

$$V_{BE}(T) = V_{G0} - \frac{T}{T_0}\!\left[V_{G0} - V_{BE}(T_0)\right] - (\eta - \alpha) V_T \ln\!\left(\frac{T}{T_0}\right)$$

where $\eta \approx 3.2\text{–}4.0$ (process-dependent mobility exponent) and $\alpha = 1$ for PTAT collector bias current (leaving $-(\eta - 1)V_T \ln(T/T_0)$ curvature):
- A **1st-order compensated BGR** exhibits a downward concave parabola peaking near $T_0 \approx 27^\circ\text{C}\text{–}40^\circ\text{C}$, with an intrinsic curvature floor of **$\sim 10\text{–}25\text{ ppm}/^\circ\text{C}$** over $-40^\circ\text{C}\dots 125^\circ\text{C}$.
- Sub-$5\text{ ppm}/^\circ\text{C}$ precision requires **2nd-order curvature compensation** (e.g., piecewise-linear current injection at high/low $T$, $\Delta V_{BE}$ between PTAT-biased and CTAT-biased BJTs, or Malcovati/Rinćon-Mora nonlinear resistors).

### Dominant Accuracy Killers & Trimming Budget

1. **Error-amplifier input offset ($V_{\text{os}}$) — #1 Error Source!**
   $$V_{\text{ref}} = V_{BE1} + \left(1 + \frac{R_2}{R_1}\right)\!\left(\Delta V_{BE} + V_{\text{os}}\right) \quad\text{(Kuijk)}$$
   - Offset is **amplified by $(1 + R_2/R_1) \approx 10\text{–}11\times$**!
   - A $3\text{ mV}$ opamp offset shifts $V_{\text{ref}}$ by **$30\text{ mV}$ ($\pm 2.5\%$)** AND degrades TC by **$\sim 80\text{ ppm}/^\circ\text{C}$** (because a temperature-independent $V_{\text{os}}$ shifts the balance point away from the zero-TC peak!).
   - **Mitigations:** Large-area PMOS diff pair (low $\sigma_{V_{\text{os}}}$ & low $1/f$ noise), larger emitter ratio $M = 8\text{–}24$ (shrinks $K = R_2/R_1$), **dynamic chopping / auto-zeroing**, and resistor trimming.
2. **Resistor ratio & BJT mismatch:** Build $R_1, R_2, R_3$ from identical unit resistor segments in common-centroid layout using the **same resistor layer** so 1st-order resistor TC cancels in $R_2/R_1$ and $R_3/R_2$.
3. **Resistor trimming strategy:**
   - **Trim $R_1$ (or $R_2$) to zero out TC** (adjusts the PTAT/CTAT slope ratio, centering the parabola peak at $T_0$); **trim $R_3$** (in Banba) to calibrate the absolute $V_{\text{ref}}$ level independently without disturbing TC!
   - Size trim range $\ge \pm 4\sigma$ of combined process + mismatch spread (typically $\pm 3\%\text{–}5\%$ with 4–6 bits of trim).

---

## 3. Dual-Feedback Loop Stability (Positive vs. Negative Feedback!)

A self-biased bandgap core simultaneously has **two feedback paths** from the current-mirror drive back to the error-amplifier inputs:
- **Positive feedback path (unit PNP $Q_1$):** small-signal impedance $r_{e1} = \frac{V_T}{I_b}$ $\implies T_+(s) = +A_{\text{op}}(s) g_{m,\text{mir}} r_{e1}$.
- **Negative feedback path ($M\times$ PNP $Q_2 + R_1$):** small-signal impedance $R_1 + r_{e2} = R_1 + \frac{V_T}{I_b}$ $\implies T_-(s) = -A_{\text{op}}(s) g_{m,\text{mir}} (R_1 + r_{e2})$.

At DC (when $I_{Q1} = I_{Q2} = I_b$), $r_{e1} = r_{e2}$, so the net loop gain is:

$$T_{\text{net}}(0) = T_-(0) + T_+(0) = -A_{\text{op}}(0)\,g_{m,\text{mir}}\,R_1$$

**Critical Stability Traps:**
1. **Swapped polarity:** Wiring $Q_1$ to the inverting input and $Q_2 + R_1$ to the non-inverting input makes $|T_+| > |T_-|$ — the circuit latches to a rail or dead state!
2. **High-frequency negative-path roll-off:** Because $Q_2$ has $M\times$ larger emitter/junction area ($C_{j,Q2} \approx M C_{j,Q1}$) AND sits behind $R_1$, the negative-feedback node can roll off at a **lower pole frequency** than the positive-feedback node! Near unity-gain frequency, $|T_+(j\omega)|$ can approach $|T_-(j\omega)|$, collapsing phase margin!
   - **Fixes:** Make the opamp internal Miller pole strongly dominant, add a matching small capacitor on the $Q_1$ node if needed, and **always run Spectre `stb` across PVT** using [`../assets/tb/tb_bgr_stb.scs`](../assets/tb/tb_bgr_stb.scs).

---

## 4. Startup Circuit & Zero-Current Dead State

Self-biased BGR loops always have **two valid DC operating points**: the desired bandgap point AND the trivial $I = 0, V_{\text{ref}} = 0$ dead state.
- Add a dedicated **startup circuit** that senses the dead state (e.g., PMOS mirror gate stuck near `VDD`), injects a small kick current into the core, and **shuts off cleanly with zero steady-state leakage** once $I_{\text{core}}$ reaches nominal bias.
- Even `100 nA` of residual startup leakage at `ff`/`125°C` skews the $1:M$ current ratio and ruins temperature coefficient!

---

## 5. Deriving PTAT, CTAT, and ZTC Bias Currents

Once a clean Banba/Kuijk core is regulated, you get three fundamental analog bias currents almost for free:
- **$I_{\text{PTAT}} = \frac{V_T \ln M}{R_1}$:** Ideal for biasing differential pairs and OTAs at **constant $g_m$** (in weak inversion, $g_m = I/(n V_T)$ becomes temperature-independent!).
- **$I_{\text{CTAT}} = \frac{V_{BE}}{R_2}$:** Directly available from the Banba CTAT resistor branch.
- **$I_{\text{ZTC}} = I_{\text{PTAT}} + I_{\text{CTAT}} = \frac{V_{\text{ref}}}{R_{\text{ext}}}$:** Zero-temperature-coefficient bias current (limited only by the TC of $R_{\text{ext}}$; use a zero-TC composite poly/diffusion resistor or external precision resistor for constant-current DACs and relaxation oscillators).
