# LDO Regulator Architectures & Sizing

## 1. Topology Selection

| Architecture | External Cap $C_L$ | Dropout $V_{\text{DO}}$ | Stability Challenge | HF PSRR & Load Transient | Best Fit |
|---|---|---|---|---|---|
| **External-Cap PMOS-Pass LDO** | Large ($1\text{–}10\;\mu\text{F}$ + ESR) | Low ($100\text{–}200\text{ mV}$) | Dominant pole at output; needs ESR zero window across $I_{\text{min}}\dots I_{\text{max}}$ | Excellent HF shunt from huge $C_L$ | Off-chip PMIC / board-level quiet analog rails |
| **Capless (OCL) PMOS-Pass LDO** | None (on-chip $5\text{–}100\text{ pF}$ only) | Low ($100\text{–}250\text{ mV}$) | Dominant pole at EA output (`Miller` / `Ahuja` / `FVF`); **light load is worst-case PM**! | Relies on wide loop BW + fast slew/undershoot enhancement | On-chip SoC domains (SAR ADC, PLL/VCO, RF LNA) |
| **NMOS-Pass Source-Follower LDO** | Optional (small) | High ($V_{\text{th}} + V_{\text{ov}}$ unless charge-pumped gate) | **Intrinsically stable** (low output impedance $1/g_{m,\text{pass}}$ pushes output pole very high!) | Fast load transient & superior mid-band PSRR | High-headroom digital/PLL rails or charge-pumped low-dropout |

---

## 2. Pass Transistor & Dropout Sizing

For a PMOS pass transistor operating at worst-case minimum input voltage $V_{\text{in,min}} = V_{\text{out}} + V_{\text{DO}}$ and maximum load current $I_{\text{load,max}}$:

- **Saturation boundary:** Keep $|V_{\text{ds}}| = V_{\text{DO}} \ge |V_{\text{dsat}}|$ so pass-device $r_{o,\text{pass}}$ does not collapse into triode (which destroys DC loop gain and DC PSRR!).
- **Triode dropout resistance:** $R_{\text{on,pass}} = \frac{1}{\mu_p C_{\text{ox}} (W/L) (V_{\text{in,min}} - |V_{\text{th},p}|)} \le \frac{V_{\text{DO}}}{I_{\text{load,max}}}$.
- **Tradeoff on $W_{\text{pass}}$:** Increasing $W_{\text{pass}}$ lowers dropout $V_{\text{DO}}$ and raises $g_{m,\text{pass}}$, but increases gate capacitance $C_{g,\text{pass}} \propto W L$, which pulls the error-amp pole inward, degrades slew rate at the pass gate during load steps, and increases $C_{gd}$ feedthrough from `VDD` to `VOUT`.
- **Quiescent current & current efficiency:**
  $$\eta_I = \frac{I_{\text{load}}}{I_{\text{load}} + I_Q}$$
  Always specify $I_Q$ at zero/light load and verify power-supply efficiency $\eta_P = \frac{V_{\text{out}}}{V_{\text{in}}} \eta_I$.

---

## 3. Regulation & Accuracy Equations

With feedback divider ratio $\beta = \frac{R_2}{R_1 + R_2}$ ($V_{\text{out}} = V_{\text{ref}} / \beta$) and DC loop gain $T_0 = \beta \, A_{\text{ea}} \, g_{m,\text{pass}} (r_{o,\text{pass}} \parallel R_L)$:

- **Load Regulation:**
  $$\frac{\Delta V_{\text{out}}}{\Delta I_{\text{load}}} = R_{\text{out,CL}}(0) = \frac{r_{o,\text{pass}}}{1 + T_0} \quad [\text{mV/mA}]$$
- **Line Regulation:**
  $$\frac{\Delta V_{\text{out}}}{\Delta V_{\text{in}}} = \frac{1}{\text{PSRR}(0)} \approx \frac{1}{1 + T_0} \quad [\text{mV/V}]$$
- **DC Accuracy Budget:** Combine bandgap $V_{\text{ref}}$ tolerance, error-amp input offset ($V_{\text{os}} / \beta$), resistor divider mismatch, and static load/line error.
