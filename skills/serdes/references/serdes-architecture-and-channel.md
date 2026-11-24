# High-Speed SerDes Architecture, Channel Loss & T-Coil Bandwidth Extension

## 1. End-to-End Wireline Transceiver Architecture

A high-speed NRZ/PAM4 serial link equalizes frequency-dependent PCB/backplane loss across three complementary stages:

```text
TX Data -> [TX FFE (Pre/Post)] -> [CML/VML Driver + T-Coil]
        -> [Lossy 100-ohm Differential Channel (SDD21 / SDD11)]
        -> [RX Termination + T-Coil] -> [CTLE + VGA + Offset Cal]
        -> [DFE Summer + Data/Error Slicers] -> [SS-LMS Adaptation & CDR]
```

| Equalization Block | Removes | Noise Amplification? | Peak-Swing Penalty? | Primary Constraint |
|---|---|---|---|---|
| **TX FFE** (3–4 tap FIR) | Pre-cursor ($h_{-1}$) & post-cursors ($h_1, h_2$) | **No** (acts before RX noise) | **Yes** ($\sum |w_k| = 1$ attenuates DC/main!) | Peak TX current / voltage headroom |
| **RX CTLE** (analog RC peaking) | Broadband high-freq channel loss & long ISI tail | **Yes** (boosts high-freq noise & crosstalk!) | No | Peaking vs. noise figure & linearity |
| **RX DFE** (nonlinear feedback) | Post-cursors ($h_1, h_2, \dots, h_N$) | **No** (noiseless digital decisions!) | No | **1-UI critical timing loop** ($t_{\text{ck}\to q} + t_{\text{sum}} < 1\text{ UI}$); error propagation |

- **Practical link-budget split (e.g., 15–30 dB loss at Nyquist $f_{\text{Nyq}} = f_b / 2$):**
  - Use **TX FFE** mainly to cancel **pre-cursor $h_{-1}$** (which DFE cannot touch!) and light $h_1$ de-emphasis (`3–6 dB`).
  - Use **CTLE** (`6–14 dB` peaking near $f_{\text{Nyq}}$) to cancel the smooth long-tail channel roll-off and open the eye enough for clean slicer decisions.
  - Use **DFE** (1–5 taps) to cancel sharp residual post-cursors ($h_1, h_2, h_3$) and reflections **without amplifying high-frequency RX noise**.

---

## 2. Channel Metrics: Mixed-Mode S-Parameters, SBR & Peak Distortion

### Mixed-Mode Differential S-Parameters (`SDD21`, `SDD11`)
For a 4-port differential channel with input pair `(1, 2)` and output pair `(3, 4)`:

$$S_{DD21} = \frac{1}{2}\left(S_{31} - S_{32} - S_{41} + S_{42}\right), \qquad S_{DD11} = \frac{1}{2}\left(S_{11} - S_{12} - S_{21} + S_{22}\right)$$

- **Nyquist frequency:** $f_{\text{Nyq}} = R_b / 2$ for NRZ (e.g., `5 GHz` for `10 Gb/s`, `14 GHz` for `28 Gb/s`), and $R_b / 4$ for PAM4 (`14 GHz` for `56 Gb/s PAM4` = `28 Gbaud`).
- **Insertion loss physics:** $\alpha(f) = \alpha_{\text{dc}} + \alpha_{\text{skin}}\sqrt{f} + \alpha_{\text{diel}} f$. Conductor skin effect scales as $\sqrt{f}$; FR4/Megtron dielectric loss scales linearly with $f$ and must be modeled causally (e.g., Djordjevic-Sarkar `fgdloss`/`fgdloss1` in Spectre `mtline`) so pulse responses never exhibit non-causal pre-ringing!
- **Return loss (`SDD11`):** Must stay well below `-10` to `-15 dB` up to Nyquist (and match TX/RX termination $Z_{\text{diff}} = 100\;\Omega$) to suppress multi-UI reflections that exceed DFE tap span.

### Single-Bit Response (SBR / Pulse Response $h(t)$) & Peak Distortion Eye
Injecting an isolated `1-UI` bipolar pulse produces sampled cursors $h_k = h(t_{\text{peak}} + k\cdot\text{UI})$:
- **$h_0$**: main cursor (signal amplitude)
- **$h_{-1}, h_{-2}$**: pre-cursor ISI (must be equalized by TX FFE or CTLE — DFE is causal and cannot cancel pre-cursors!)
- **$h_1, h_2, \dots$**: post-cursor ISI
- **Worst-Case Peak-Distortion Analysis (PDA) NRZ eye height:**
  $$V_{\text{eye,PDA}} = 2\!\left(|h_0| - \sum_{k \neq 0} |h_k|\right)$$
  If $\sum_{k\neq 0}|h_k| > |h_0|$, the unequalized eye is completely **closed** ($V_{\text{eye,PDA}} \le 0$) and requires FFE/CTLE/DFE before any slicer can recover data.

### Time-Domain Reflectometry (TDR)
Launching a fast differential step of incident amplitude $V_{\text{inc}}$ through matched $Z_{0,\text{diff}} = 100\;\Omega$ directly maps impedance discontinuities vs. distance via:

$$\rho(t) = \frac{V_{\text{in}}(t) - V_{\text{inc}}}{V_{\text{inc}}}, \qquad Z_{\text{TDR}}(t) = Z_{0,\text{diff}}\,\frac{1 + \rho(t)}{1 - \rho(t)}$$

---

## 3. Bridged T-Coil Bandwidth Extension (ESD / Pad Cap Absorption)

At `10–56 Gb/s`, ESD + pad + input-stage capacitance ($C_L \approx 200\text{–}600\text{ fF}$) shunting a $50\;\Omega$ termination creates a harsh pole $f_{-3\text{dB}} = \frac{1}{2\pi R_L C_L}$ (only `6.4 GHz` for $500\text{ fF}$!) and ruins high-frequency `S11`.

A **constant-resistance bridged T-coil** splits $L_1 = L_2 = L$ around center tap `MID` (where $C_L$ connects!), couples $L_1, L_2$ series-aiding with mutual coupling $k = M/L$, and bridges `IN -> OUT` with $C_B$:

$$L_1 = L_2 = \frac{C_L R_L^2}{4}\!\left(1 + \frac{1}{4\zeta^2}\right), \qquad k = \frac{4\zeta^2 - 1}{4\zeta^2 + 1}, \qquad C_B = \frac{C_L}{16\zeta^2}$$

| Damping $\zeta$ | Response Type | Coupling $k$ | $L_1 = L_2$ | $C_B$ | BW Boost vs. Bare $R_L \parallel C_L$ | Step Overshoot |
|---|---|---|---|---|---|---|
| $1/\sqrt{2} \approx 0.707$ | **Maximally-flat (Butterworth)** | **$1/3$ (`0.333`)** | $0.375\,C_L R_L^2$ | $C_L / 8$ | **$2.83\times$ ($\sqrt{8}$)** | $\sim 4.3\%$ |
| $\sqrt{3}/2 \approx 0.866$ | **Linear-phase (Bessel)** | **$1/2$ (`0.500`)** | $0.333\,C_L R_L^2$ | $C_L / 12$ | **$2.72\times$** | $< 1\%$ |
| $0.58$ | Slight peaking (`~0.8 dB`) | `0.15` | $0.436\,C_L R_L^2$ | $0.186\,C_L$ | **$2.95\times$** | $\sim 10\%$ |

- **Exact constant resistance:** At ALL frequencies $s$, $Z_{\text{in}}(s) \equiv R_L$ identically (ideal $S_{11} \to -\infty$!) while simultaneously extending `-3 dB` bandwidth at the protected ESD/RX node `MID` by **$2.72\times$ (Bessel) to $2.83\times$ (Butterworth)**!
- Verify directly using [`../assets/tb/tcoil/tb_tcoil_bw.scs`](../assets/tb/tcoil/tb_tcoil_bw.scs).
