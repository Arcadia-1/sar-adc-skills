# Integer-N Charge-Pump PLL Design

## 1. Architecture & Operating Principle

A Type-II Integer-N CP-PLL locks $f_{\text{out}} = N \cdot f_{\text{ref}}$ using:
1. **Tri-state PFD:** Compares rising edges of `FREF` and `FDIV`, generating `UP` / `DN` pulses whose width difference equals the arrival-time error $\Delta t = \Delta\phi / (2\pi f_{\text{ref}})$.
2. **Charge Pump (CP):** Converts `UP`/`DN` into net charge $Q = I_{\text{cp}} \Delta t$ into the loop filter, giving linear phase detector gain $K_d = I_{\text{cp}} / (2\pi)\;[\text{A/rad}]$.
3. **Passive Loop Filter ($Z_{\text{LF}}(s)$):** Integrates charge on $C_1$, adds a stabilizing zero via $R$ in series with $C_1$, and suppresses control-voltage ripple via $C_2$ (2nd-order filter $\to$ 3rd-order PLL) and optional $R_3, C_3$ (3rd-order filter $\to$ 4th-order PLL).
4. **VCO + Integer-$N$ Divider:** VCO oscillates at $f_{\text{out}} = f_0 + K_{\text{VCO}} (V_{\text{ctrl}} - V_{\text{ctrl},0})$; divider outputs $f_{\text{div}} = f_{\text{out}} / N$.

---

## 2. Passive Loop Filter Sizing (Exact Phase-Margin Method)

### 2nd-Order Passive Filter ($R, C_1, C_2$ — 3rd-Order Type-II PLL)

$$Z_{\text{LF}}(s) = \frac{1 + s R C_1}{s (C_1 + C_2)\left(1 + s R \frac{C_1 C_2}{C_1 + C_2}\right)} = \frac{1 + s/\omega_z}{s (C_1 + C_2)(1 + s/\omega_{p2})}$$

where:
- Stabilizing zero: $\omega_z = \frac{1}{R C_1}$
- Ripple-suppression pole: $\omega_{p2} = \frac{C_1 + C_2}{R C_1 C_2} = \omega_z \left(1 + \frac{C_1}{C_2}\right)$
- Capacitor ratio: $b = \frac{C_1}{C_2} + 1 = \frac{\omega_{p2}}{\omega_z}$

**Maximum phase margin** occurs at the geometric mean frequency $\omega_u = \sqrt{\omega_z \omega_{p2}}$:

$$\text{PM}_{\max} = \arctan\left(\frac{b - 1}{2\sqrt{b}}\right) = \arctan\left(\sqrt{b}\right) - \arctan\left(\frac{1}{\sqrt{b}}\right)$$

### Step-by-Step Closed-Form Design Procedure

Given target unity-gain bandwidth $f_u = \omega_u / (2\pi)$ (choose $f_u \le f_{\text{ref}} / 10$, typically $f_{\text{ref}} / 15$–$f_{\text{ref}} / 20$), target phase margin $\text{PM}$ (typically $55^\circ\text{–}65^\circ$), $I_{\text{cp}}$, $K_{\text{VCO}}\;[\text{Hz/V}]$, and $N$:

1. **Choose pole/zero spread $b$ for desired $\text{PM}$:**
   - Solve $\gamma = \sqrt{b} = \tan(\text{PM}) + \sec(\text{PM})$ (e.g., $\text{PM} = 55^\circ \implies \gamma \approx 3.17, b \approx 10.1$; $\text{PM} = 60^\circ \implies \gamma \approx 3.73, b \approx 13.9$; $\text{PM} = 65^\circ \implies \gamma \approx 4.51, b \approx 20.3$).
2. **Place zero and ripple pole symmetrically around $\omega_u$:**
   $$\omega_z = \frac{\omega_u}{\gamma}, \qquad \omega_{p2} = \gamma \, \omega_u$$
3. **Compute $R$, $C_1$, and $C_2$ so $|L(j\omega_u)| = 1$:**
   - Since $|Z_{\text{LF}}(j\omega_u)| = \frac{R}{1 + C_2/C_1} \cdot \frac{\sqrt{1 + \gamma^2}}{\gamma \sqrt{1 + 1/\gamma^2}} = R \cdot \frac{b - 1}{b}$:
   $$R = \frac{N \, \omega_u}{I_{\text{cp}} \, K_{\text{VCO}}} \cdot \frac{b}{b - 1} \qquad (\text{with } K_{\text{VCO}} \text{ in Hz/V, since } K_d K_{\text{osc}} = \frac{I_{\text{cp}}}{2\pi} \cdot 2\pi K_{\text{VCO}} = I_{\text{cp}} K_{\text{VCO}})$$
   $$C_1 = \frac{1}{R \, \omega_z} = \frac{\gamma}{R \, \omega_u}, \qquad C_2 = \frac{C_1}{b - 1}$$
4. **Optional 3rd-order pole ($R_3, C_3$):**
   - Place $\omega_{p3} = 1 / (R_3 C_3) \approx (3\text{–}5)\,\omega_{p2}$ (keep $R_3 \ge 2 R$ and $C_3 \le C_2 / 3$ to avoid loading $C_2$) for an extra $-20\text{ dB/dec}$ reference-spur suppression at $f_{\text{ref}}$, budgeting $\sim 5^\circ\text{–}10^\circ$ extra PM loss.

### Sanity Check (Worked Example)
- $f_{\text{ref}} = 50\text{ MHz}$, $N = 20$ ($f_{\text{out}} = 1.0\text{ GHz}$), $I_{\text{cp}} = 100\;\mu\text{A}$, $K_{\text{VCO}} = 200\text{ MHz/V}$, target $f_u = 2.0\text{ MHz}$ ($\omega_u = 1.257\times 10^7\text{ rad/s}$), $\text{PM} = 60^\circ$ ($b \approx 13.9, \gamma \approx 3.73$):
  - $R = \frac{20 \times 1.257\times 10^7}{10^{-4} \times 2\times 10^8} \cdot \frac{13.9}{12.9} \approx 13.5\text{ k}\Omega$
  - $C_1 = \frac{3.73}{13.5\times 10^3 \times 1.257\times 10^7} \approx 22.0\text{ pF}$, $C_2 = \frac{22.0\text{ pF}}{12.9} \approx 1.7\text{ pF}$.
  - Verify thermal noise of $R$: $\sqrt{4kTR} \approx 15\text{ nV}/\sqrt{\text{Hz}} \implies$ at $f_u = 2\text{ MHz}$, $\mathcal{L}_R \approx 10\log_{10}\left(\frac{4kTR \cdot K_{\text{VCO}}^2}{2 f_u^2}\right) \approx -119\text{ dBc/Hz}$. If too high, scale $I_{\text{cp}}$ up and $R$ down proportionally (area scales up with $C_1 \propto I_{\text{cp}}$).

---

## 3. Reference Spurs & Static Phase Offset

In lock, three non-idealities force periodic charge pulses onto `VCTRL` at $f_{\text{ref}}$, modulating the VCO into sidebands at $f_{\text{out}} \pm k f_{\text{ref}}$:

1. **Loop-filter / varactor leakage current $I_{\text{leak}}$:**
   - Requires a static phase offset $\Delta t_{\text{leak}} = \frac{I_{\text{leak}}}{I_{\text{cp}}} T_{\text{ref}}$ so CP replenishes the lost charge every reference cycle.
   - Resulting first reference spur (2nd-order filter):
     $$\text{Spur}_{\text{ref}} \approx 20\log_{10}\left(\frac{I_{\text{leak}} \, K_{\text{VCO}}}{2 f_{\text{ref}}^2 \, C_2}\right) \quad [\text{dBc}]$$
2. **Charge-pump Up/Down current mismatch $\Delta I / I_{\text{cp}}$ during PFD reset pulse $t_{\text{rst}}$:**
   - Static phase offset $\Delta t_{\text{mis}} \approx \frac{\Delta I}{I_{\text{cp}}} t_{\text{rst}}$.
   - Keep $t_{\text{rst}}$ just wide enough to eliminate the dead zone (typically $50\text{–}150\text{ ps}$) and match $I_{\text{up}} / I_{\text{dn}}$ within $< 2\%\text{–}5\%$.
3. **Switch charge injection & clock feedthrough** on `UP`/`DN` switching transitions.

For narrowband FM modulation with peak sinusoidal control ripple $V_{\text{ripple}}$ at $f_{\text{ref}}$:

$$\text{Spur}_{\text{ref}} = 20\log_{10}\left(\frac{K_{\text{VCO}} \, V_{\text{ripple}}}{2 f_{\text{ref}}}\right) \quad [\text{dBc}]$$

---

## 4. Settling Time & Cycle Slipping

- **Linear settling** (small frequency step $\Delta f$): $t_{\text{settle}} \approx \frac{\ln(\Delta f / f_{\text{err}})}{\zeta \omega_n} \approx \frac{4\text{–}6}{2\pi f_u}$ (typically $3\text{–}10$ loop time constants).
- **Nonlinear cycle slipping** (large step $|\Delta\phi| > 2\pi$): PFD wraps modulo $2\pi$ and saturates at average current $\approx \pm I_{\text{cp}}/2$, slowing acquisition. Keep initial coarse VCO bank calibration within a few percent of target frequency before releasing fine-loop lock.

---

## How to Verify an Integer-N PLL

> **Ready-to-run process-independent Spectre testbenches:** See [`../assets/tb/int_n_pll/`](../assets/tb/int_n_pll/README.md) (`tb_int_n_pll_ac_loop.scs`, `tb_int_n_pll_lock.scs`, `analyze_int_n_pll.py`) and the behavioral Verilog-A building blocks [`va_pfd.va`](../assets/va/va_pfd.va), [`va_cp.va`](../assets/va/va_cp.va), [`va_vco.va`](../assets/va/va_vco.va), [`va_div_int.va`](../assets/va/va_div_int.va), and [`va_phase_err_mon.va`](../assets/va/va_phase_err_mon.va).

1. **Phase-Domain AC Loop Analysis (`tb_int_n_pll_ac_loop.scs`):**
   - Extract open-loop $f_u$, phase margin $\text{PM}$ (target $55^\circ\text{–}65^\circ$), gain margin $\text{GM} \ge 10\text{ dB}$, closed-loop peaking ($< 1.5\text{–}2\text{ dB}$), and verify in-band / VCO noise transfer functions before running long transients.
2. **Closed-Loop Lock Transient (`tb_int_n_pll_lock.scs`):**
   - Release the loop from an intentional frequency offset (e.g., $\pm 10\%$ off target) and measure settling time to within $< 0.1\%$ of $N f_{\text{ref}}$, overshoot on `VCTRL`, steady-state frequency error, and peak-to-peak `VCTRL` ripple at $f_{\text{ref}}$ (translating directly to reference spur).
3. **PVT & Corner Closure:**
   - Sweep $K_{\text{VCO}}$ extremes (typically $\pm 30\text{–}50\%$ across PVT and tuning range) + $I_{\text{cp}}$ + $R, C$ process corners to confirm $\text{PM} \ge 45^\circ$ and $f_u \le f_{\text{ref}}/10$ across every corner.
