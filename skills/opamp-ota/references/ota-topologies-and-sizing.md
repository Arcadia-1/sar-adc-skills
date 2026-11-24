# OpAmp & OTA Topologies and Sizing

## 1. Topology Selection Matrix

| Topology | DC Gain $A_0$ | Output Swing | Speed / GBW | Noise Efficiency | Compensation | Best Fit |
|---|---|---|---|---|---|---|
| **5T OTA** (1-stage diff pair + mirror) | 25–40 dB ($g_m r_o$) | Good ($V_{\text{DD}} - 2 V_{\text{ov}}$) | High (self-comp by $C_L$) | High | Load cap $C_L$ | Low-gain buffers, LDO error amp, auxiliary loops |
| **Telescopic Cascode** | 55–75 dB ($(g_m r_o)^2$) | Tight ($V_{\text{DD}} - 5 V_{\text{ov}}$) | **Highest** (single stage) | **Best** (fewest noisy devices) | Load cap $C_L$ | High-speed SC integrators when headroom permits |
| **Folded Cascode** | 55–75 dB ($(g_m r_o)^2$) | Wide ($V_{\text{DD}} - 4 V_{\text{ov}}$) | High | Moderate (extra folding bias noise) | Load cap $C_L$ | Low-voltage single-stage SC/pipeline/DSM stages |
| **Two-Stage Miller OpAmp** | 70–100 dB ($(g_m r_o)^2$) | **Rail-to-rail** ($V_{\text{DD}} - 2 V_{\text{ov}}$) | Moderate (limited by $p_2$ & $z_{\text{RHP}}$) | High (set by 1st stage) | Miller $C_c$ + nulling $R_z$ | High-gain resistive/capacitive loads, BGR, LDO |
| **Dynamic Amp (FIA / Ringamp)** | 30–60 dB | Rail-to-rail (Ringamp) | Very high | **Ultra-low power** (dynamic) | Dynamic / dead-zone | Pipeline-SAR residue amplification |

---

## 2. Two-Stage Miller OpAmp Core Equations

For an NMOS/PMOS input stage ($g_{m1}, R_{o1}$) driving a common-source second stage ($g_{m2}, R_{o2}$) with load $C_L$, Miller capacitor $C_c$, and series nulling resistor $R_z$:

- **DC open-loop gain:** $A_0 = (g_{m1} R_{o1})(g_{m2} R_{o2})$
- **Gain-bandwidth product:** $\text{GBW} = \frac{g_{m1}}{2\pi C_c}$
- **Dominant pole:** $\omega_{p1} \approx \frac{1}{R_{o1} \, g_{m2} R_{o2} \, C_c}$
- **Non-dominant output pole:** $\omega_{p2} \approx \frac{g_{m2}}{C_L + C_{p1}(1 + C_L/C_c)} \approx \frac{g_{m2}}{C_L}$ (for $C_L, C_c \gg C_{p1}$)
- **Miller zero (with nulling resistor $R_z$):**
  $$\omega_z = \frac{1}{C_c (R_z - 1/g_{m2})}$$
  - $R_z = 0 \implies$ **RHP zero** at $+g_{m2}/C_c$ (adds $-45^\circ$ phase lag at $\omega_z$, hurting phase margin!).
  - $R_z = 1/g_{m2} \implies \omega_z \to \infty$ (cancels the RHP zero completely).
  - $R_z = \frac{1}{g_{m2}}\left(1 + \frac{C_L + C_c}{C_c}\right) \implies$ places a **LHP zero** right on top of $\omega_{p2}$ to cancel it, pushing effective non-dominant pole out to $\omega_{p3} \approx 1 / (R_z C_{p1})$!
- **Phase margin rule (for unity-gain $\beta = 1$, $\text{PM} \ge 60^\circ$ with $R_z = 1/g_{m2}$):**
  $$\frac{\omega_{p2}}{\omega_u} \ge 2.2\text{–}3.0 \implies \frac{g_{m2}}{C_L} \ge (2.2\text{–}3.0) \frac{g_{m1}}{C_c}$$
  (For $C_c \approx 0.25\text{–}0.35\,C_L$, this typically requires $g_{m2} \approx (6\text{–}10)\,g_{m1}$.)

---

## 3. Slew Rate, Settling Time & Noise

- **Slew rate (Two-Stage Miller):**
  $$\text{SR} = \min\left(\frac{I_{\text{tail}}}{C_c}, \; \frac{I_{D2,\text{max}} - I_{\text{tail}}}{C_L + C_c}\right)$$
  Always size the 2nd-stage bias current $I_{D2} > I_{\text{tail}} (1 + C_L/C_c)$ (or use a Class-AB output stage) so the output never slews slower than the internal Miller node!
- **Closed-loop linear settling time (feedback factor $\beta$, $N$-bit accuracy $\epsilon = 2^{-(N+1)}$):**
  $$t_{\text{settle}} = t_{\text{slew}} + \frac{\ln(1/\epsilon)}{2\pi \beta \, \text{GBW}}$$
  - For 10-bit ($0.05\%$ error): $\ln(2000) \approx 7.6$ time constants; for 12-bit ($0.012\%$): $9.0$ time constants.
  - **Optimal settling phase margin:** $\text{PM} \approx 65^\circ\text{–}72^\circ$ gives minimal ringing and fastest $0.01\%$ settling (higher PM overdamps and slows settling; $\text{PM} < 55^\circ$ rings!).
- **Input-referred thermal noise (5T / 1st stage of Miller):**
  $$S_{v,\text{in,th}} = \frac{8 k T \gamma}{g_{m1}}\left(1 + \frac{g_{m,\text{load}}}{g_{m1}}\right)$$
  Keep $(g_m/I_D)_1$ high (weak/moderate inversion, $g_m/I_D \approx 14\text{–}20\text{ V}^{-1}$) and $(g_m/I_D)_{\text{load}}$ low (strong inversion, $g_m/I_D \approx 6\text{–}10\text{ V}^{-1}$) so $g_{m,\text{load}} / g_{m1} \ll 1$!
- **Input-referred $1/f$ noise & offset:** Both scale as $1 / \sqrt{WL}$; choose large $W_1 L_1$ and long $L_{\text{load}}$ (and PMOS input pairs where flicker noise $K_p < K_n$ in bulk CMOS).

---

## 4. Standard Figures of Merit

- **Small-signal FoM:** $\text{FoM}_S = \frac{\text{GBW}\;[\text{MHz}] \cdot C_L\;[\text{pF}]}{I_{\text{DD}}\;[\text{mA}]}$ (units: $\text{MHz}\cdot\text{pF/mA}$).
- **Large-signal FoM:** $\text{FoM}_L = \frac{\text{SR}\;[\text{V}/\mu\text{s}] \cdot C_L\;[\text{pF}]}{I_{\text{DD}}\;[\text{mA}]}$ (units: $(\text{V}/\mu\text{s})\cdot\text{pF/mA}$).
