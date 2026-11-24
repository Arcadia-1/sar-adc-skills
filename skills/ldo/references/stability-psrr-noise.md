# LDO Stability, PSRR & Output Noise

## 1. Pole-Zero Map & the Light-Load Stability Trap

For a Miller-compensated capless PMOS-pass LDO (error-amp output impedance $R_{o1}$, Miller cap $C_c$ + nulling resistor $R_z$, pass transconductance $g_{m2} \propto \sqrt{I_{\text{load}}}$ or $\propto I_{\text{load}}$ in weak inversion, load cap $C_L$):

- **Dominant pole (EA output):** $\omega_{p1} \approx \frac{1}{R_{o1} \, g_{m2} (r_{o2} \parallel R_L) \, C_c}$
- **Unity-gain frequency:** $\omega_u \approx \frac{\beta \, g_{m1}}{C_c}$ (nearly independent of $I_{\text{load}}$!)
- **Non-dominant output pole:** $\omega_{p2} \approx \frac{g_{m2}}{C_L}$
- **Miller zero:** $\omega_z = \frac{1}{C_c (R_z - 1/g_{m2})}$

**Why light load ($I_{\text{load}} = I_{\text{min}}$) is the #1 stability failure mode:**
- As $I_{\text{load}} \to I_{\text{min}}$, $g_{m2}$ drops dramatically ($\propto \sqrt{I_{\text{load}}}$ or $\propto I_{\text{load}}$), dragging $\omega_{p2} = g_{m2}/C_L$ straight down toward (or below!) $\omega_u$, collapsing phase margin!
- **Fixes:** (1) Enforce a minimum internal bleed load (e.g., feedback divider current $I_{\text{fb}} \ge 10\text{–}50\;\mu\text{A}$), (2) use Ahuja / cascode compensation to decouple $\omega_{p2}$ from $C_{g2}$, or (3) track bias current dynamically with $I_{\text{load}}$.

---

## 2. PSRR Across Frequency (Three Distinct Regimes)

1. **DC / Low Frequency ($f < f_{p1}$):**
   - If the error-amp output load is referenced to `VDD` (standard PMOS current mirror) so `VG` tracks `VDD` at DC, supply ripple couples mainly through $r_{o,\text{pass}}$, giving $\text{PSRR}(0) \approx 1 + T_0$.
   - If the EA output is ground-referenced, `VDD` modulates $V_{\text{sg}}$ directly through $g_{m,\text{pass}}$, cutting DC PSRR down to $\sim A_{\text{ea}}$!
2. **Mid-Band ($f_{p1} < f < f_u$):**
   - Loop gain $|T(f)|$ rolls off at $-20\text{ dB/dec}$, so $\text{PSRR}(f)$ degrades at $-20\text{ dB/dec}$ toward a worst-case **PSRR minimum near $f_u$** (where phase lag can even cause slight peaking if PM is low!).
3. **High Frequency ($f > f_u$):**
   - The feedback loop is open; supply rejection is governed purely by passive capacitive division between $C_{gd,\text{pass}} / r_{o,\text{pass}}$ and the output decoupling capacitor $C_L$ (with its series ESR $R_{\text{ESR}}$!). Above $f_{\text{ESR}} = 1/(2\pi R_{\text{ESR}} C_L)$, ESR caps HF PSRR at $R_{\text{ESR}} / (R_{\text{ESR}} + r_{o,\text{pass}})$.

---

## 3. Output Noise Decomposition

Total output noise PSD within the loop bandwidth ($f < f_u$) is:

$$S_{v,\text{out}}(f) \approx \frac{1}{\beta^2}\left(S_{v,\text{ref}}(f) + S_{v,\text{ea,in}}(f)\right) + 4 k T R_1 \left(1 + \frac{R_1}{R_2}\right)$$

- Reference noise $S_{v,\text{ref}}$ is amplified by $1/\beta$ (filter `VREF` with an RC low-pass filter if low output noise is critical!).
- Keep feedback resistors $R_1, R_2$ small enough that divider thermal noise stays well below $S_{v,\text{ea,in}}/\beta^2$.
