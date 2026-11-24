# Bandgap Voltage Reference (BGR) Fundamentals

## 1. PTAT + CTAT Cancellation Principle

A silicon bandgap reference cancels the negative temperature slope of a diode/PNP base-emitter voltage $V_{BE}(T)$ (CTAT, $\approx -1.8\text{ to }-2.0\text{ mV/K}$) against a scaled positive-slope thermal voltage $\Delta V_{BE} = V_T \ln M = \frac{kT}{q} \ln M$ (PTAT, $+0.0862 \ln M\;\text{mV/K}$) between two matched BJTs/PNPs of emitter-area ratio $M$ (commonly $M = 8$, using a $3\times 3$ common-centroid array with the unit device in the center!):

$$V_{\text{ref}}(T) = V_{BE}(T) + K \cdot V_T \ln M \approx 1.20\text{–}1.25\text{ V}$$

- **Classic Kuijk / Brokaw voltage-mode BGR ($V_{\text{ref}} \approx 1.22\text{ V}$):**
  - Requires $V_{\text{DD}} \ge 1.4\text{–}1.5\text{ V}$; ratio $K = R_2 / R_1 \approx 10$ (for $M = 8$, $\ln 8 = 2.079$, so $K \cdot 0.0862 \cdot 2.079 \approx +1.8\text{ mV/K}$).
- **Banba sub-1 V current-mode BGR ($V_{\text{ref}} = \frac{R_3}{R_2}\left[V_{BE} + \frac{R_2}{R_1} V_T \ln M\right]$):**
  - Sums $I_{\text{CTAT}} = V_{BE}/R_2$ and $I_{\text{PTAT}} = (V_T \ln M)/R_1$ into a matched mirror and converts to any arbitrary scaled voltage $V_{\text{ref}} = I_{\text{sum}} R_3$ (e.g., `0.5 V–0.6 V`), operating cleanly down to $V_{\text{DD}} = 0.9\text{–}1.0\text{ V}$!

---

## 2. Temperature Coefficient (TC), Curvature & Error Sources

### Box-Method Temperature Coefficient
Measured across $[T_{\min}, T_{\max}]$ (typically $-40^\circ\text{C}$ to $+125^\circ\text{C}$, $\Delta T = 165^\circ\text{C}$):

$$\text{TC} = \frac{V_{\text{ref,max}} - V_{\text{ref,min}}}{V_{\text{ref,nom}} \cdot (T_{\max} - T_{\min})} \times 10^6 \quad [\text{ppm}/^\circ\text{C}]$$

### Inherent 2nd-Order Curvature
Because $V_{BE}(T)$ contains a nonlinear $-(\eta - 1) V_T \ln(T/T_0)$ term (where $\eta \approx 3.2\text{–}4.0$):
- A **1st-order compensated BGR** exhibits a downward concave parabola peaking near room temperature ($T_0 \approx 27^\circ\text{C}\text{–}40^\circ\text{C}$), with an intrinsic curvature floor of **$\sim 10\text{–}25\text{ ppm}/^\circ\text{C}$** over $-40^\circ\text{C}\dots 125^\circ\text{C}$.
- Sub-$5\text{ ppm}/^\circ\text{C}$ precision requires **2nd-order curvature compensation** (e.g., adding a $T \ln T$ or piecewise-linear correction current).

### Dominant Accuracy Killers
1. **Error-amplifier input offset ($V_{\text{os}}$):**
   - Offset directly adds to $\Delta V_{BE}$ and gets **amplified by $(1 + R_2/R_1) \approx 10\times$**!
   - A $3\text{ mV}$ opamp offset shifts $V_{\text{ref}}$ by **$30\text{ mV}$ ($\pm 2.5\%$)** AND introduces an uncompensated PTAT TC drift of $\sim 80\text{ ppm}/^\circ\text{C}$!
   - **Fixes:** Large-area PMOS input pair (low $1/f$ and small $\sigma_{V_{\text{os}}}$), big emitter ratio $M = 8\text{–}24$ (reduces required $K = R_2/R_1$), **chopping / auto-zeroing**, and resistor trimming.
2. **Resistor ratio & BJT mismatch:** Match $R_1, R_2, R_3$ from identical unit segments in common-centroid layout; use the same resistor type so their 1st-order resistor TCs cancel in ratios $R_2/R_1$ and $R_3/R_2$.
3. **Zero-current dead state (Startup circuit is MANDATORY!):**
   - Self-biased BGR loops have **two valid DC equilibrium points**: the desired operating point AND the trivial $I = 0, V_{\text{ref}} = 0$ dead state!
   - Always include an explicit startup circuit that injects current when $I_{\text{core}} \approx 0$ and **cleanly shuts completely off** (zero steady-state leakage!) once the core reaches nominal bias across all PVT corners.
