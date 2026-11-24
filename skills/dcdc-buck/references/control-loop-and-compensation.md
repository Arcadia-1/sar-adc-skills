# Control Loop, Small-Signal Averaging, Compensation & Protection

## 1. Voltage-Mode vs. Peak Current-Mode Control

| Feature | Voltage-Mode Control (VMC) | Peak Current-Mode Control (PCMC) |
|---|---|---|
| **Control-to-Output Plant** | 2nd-order $LC$ double pole at $f_{LC} = \frac{1}{2\pi\sqrt{LC}}$ ($-180^\circ$ phase drop!) | 1st-order dominant output pole $f_{p,\text{load}}$ + high-freq Ridley double pole at $f_{\text{sw}}/2$ |
| **Compensator Complexity** | **Type-III** (2 zeros + 3 poles) required to boost phase across $f_{LC}$ | **Type-II** (integrator + 1 zero + 1 HF pole) achieves $60^\circ\text{–}75^\circ$ PM cleanly |
| **Line Feedforward / PSRR** | None natively (depends entirely on loop gain; $V_{\text{in}}$ scales loop gain) | **Inherent input feedforward** (inductor ramp slope tracks $V_{\text{in}} - V_{\text{out}}$) |
| **Over-Current Protection** | Needs separate fast current-limit loop | **Inherent cycle-by-cycle peak current clamping** via `COMP` voltage clamp |
| **Subharmonic Instability** | Immune | Requires **slope compensation** ($m_a \ge 0.5 m_2$) for $D > 0.5$ |

Because of its simple Type-II compensation, built-in cycle-by-cycle OCP, and strong line rejection, **Peak Current-Mode Control (PCMC)** is the workhorse architecture for integrated synchronous Buck PMICs.

---

## 2. Subharmonic Oscillation & Slope Compensation

In an uncompensated PCMC loop, a small inductor current perturbation $\Delta I_0$ propagates from cycle $n$ to cycle $n+1$ as:

$$\Delta I_{n+1} = -\frac{m_2}{m_1} \Delta I_n = -\frac{D}{1 - D} \Delta I_n$$

Whenever $D > 0.5$, $\left|\Delta I_{n+1} / \Delta I_n\right| > 1$, causing alternating wide/narrow pulses at $f_{\text{sw}}/2$ (subharmonic oscillation). Adding an artificial stabilizing ramp of slope $m_a$ [V/s] to the sensed current voltage $R_{\text{sns}} i_L(t)$ modifies the perturbation ratio to:

$$\alpha = -\frac{m_2 - m_a}{m_1 + m_a}, \qquad m_1 = R_{\text{sns}} \frac{V_{\text{in}} - V_{\text{out}}}{L}, \qquad m_2 = R_{\text{sns}} \frac{V_{\text{out}}}{L}$$

- **Deadbeat damping:** $m_a = m_2$ forces $\alpha = 0$ (perturbation dies in 1 cycle).
- **Universal stability criterion (all $D < 1$):** Choose **$m_a \ge 0.5 m_2$** (typically $0.6\text{–}0.85 \, m_2$). Excessive $m_a \gg m_2$ degrades the converter back toward voltage-mode behavior, reducing line feedforward and lowering the current-limit threshold at high duty cycles.

For $V_{\text{out}} = 1.2\text{ V}$, $L = 2.2\;\mu\text{H}$, $R_{\text{sns}} = 1.0\;\Omega$: $m_2 = 0.545\;\text{V}/\mu\text{s}$, so $m_a = 0.45\;\text{V}/\mu\text{s}$ ($m_a / m_2 = 0.825$) eliminates subharmonic peaking across $V_{\text{in}} \in [2.7, 4.5]\text{ V}$ while preserving PCMC dynamics.

---

## 3. Continuous State-Space Averaged PCMC Model (Erickson-Maksimović / Ridley)

Switching converters cannot be analyzed directly with small-signal `ac` or `stb` without either PSS/PAC or an exact **continuous averaged model**. In CCM, the peak-to-average inductor current balance (Erickson-Maksimović) yields:

$$v_c = R_{\text{sns}} i_L + m_a T_{\text{sw}} d + \frac{R_{\text{sns}} T_{\text{sw}}}{2 L} \left[d^2 (V_{\text{in}} - V_{\text{sw}}) + (1 - d)^2 V_{\text{sw}}\right]$$

Crucially, the bracket derivative with respect to $d$ vanishes identically at DC steady state ($D V_{\text{in}} = V_{\text{sw}}$), guaranteeing a strictly monotonic, globally unique operating point while capturing exact modulator gain $F_m = \frac{1}{m_a T_{\text{sw}}}$, input feedforward $k_f$, and output feedback $k_r$.

### Control-to-Output Transfer Function $G_{vc}(s)$
Combining the averaged power stage with Ridley's discrete-time sampling double-pole $H_s(s)$ at $f_{\text{sw}}/2$:

$$G_{vc}(s) = \frac{\hat{v}_{\text{out}}(s)}{\hat{v}_c(s)} \approx \frac{R_{\text{load}}}{R_{\text{sns}} \left[1 + \frac{R_{\text{load}}}{L f_{\text{sw}}}(m_c D' - 0.5)\right]} \cdot \frac{1 + s R_{\text{ESR}} C_{\text{out}}}{1 + s / \omega_{p,\text{load}}} \cdot \frac{1}{1 + \frac{s}{\omega_n Q_p} + \frac{s^2}{\omega_n^2}}$$

where:
- Dominant output pole: $\omega_{p,\text{load}} \approx \frac{1}{R_{\text{load}} C_{\text{out}}} + \frac{m_c D' - 0.5}{L C_{\text{out}} f_{\text{sw}}}$
- Output capacitor ESR zero: $f_{z,\text{ESR}} = \frac{1}{2\pi R_{\text{ESR}} C_{\text{out}}}$ (e.g., $1.06\text{ MHz}$ for $10\;\mu\text{F} / 15\;\text{m}\Omega$)
- Ridley sampling double-pole: $\omega_n = \pi f_{\text{sw}}$ ($f_n = f_{\text{sw}}/2 = 1.0\text{ MHz}$) with damping quality factor:
  $$Q_p = \frac{1}{\pi (m_c D' - 0.5)}, \qquad m_c = 1 + \frac{m_a}{m_1}, \qquad D' = 1 - D$$

Notice the key physical insight: if slope compensation $m_a$ is insufficient as $D \to 0.5^+$, $m_c D' \to 0.5$, driving $Q_p \to \infty$ and producing a sharp resonant peak at $f_{\text{sw}}/2$ that destroys gain margin and triggers subharmonic oscillation!

---

## 4. Step-by-Step Type-II OTA Compensator Design

With a transconductance error amplifier ($g_{m,\text{ea}}, r_{o,\text{ea}}$) driving a series $R_c$–$C_c$ branch in parallel with a high-frequency filter capacitor $C_{\text{hf}}$ on `COMP`, and feedback divider ratio $\beta = V_{\text{ref}} / V_{\text{out}}$:

$$H_{\text{comp}}(s) \approx \frac{g_{m,\text{ea}}}{s (C_c + C_{\text{hf}})} \cdot \frac{1 + s R_c C_c}{1 + s R_c \frac{C_c C_{\text{hf}}}{C_c + C_{\text{hf}}}}$$

1. **Choose target crossover frequency $f_c$:** Set $f_c \le f_{\text{sw}} / 10$ (e.g., $120\text{–}160\text{ kHz}$ for $f_{\text{sw}} = 2\text{ MHz}$) to avoid excessive phase lag from the Ridley sampling pole at $f_{\text{sw}}/2$.
2. **Set mid-band resistor $R_c$ for unity gain at $f_c$:** At $f_c \gg f_{p,\text{load}}$, $|G_{vc}(f_c)| \approx \frac{1}{2\pi f_c R_{\text{sns}} C_{\text{out}}}$, so:
   $$R_c = \frac{2\pi f_c R_{\text{sns}} C_{\text{out}}}{\beta \, g_{m,\text{ea}}}$$
   (For $f_c = 145\text{ kHz}$, $R_{\text{sns}} = 1\;\Omega$, $C_{\text{out}} = 10\;\mu\text{F}$, $\beta = 0.5$, $g_{m,\text{ea}} = 400\;\mu\text{S}$: $R_c \approx 47\;\text{k}\Omega$.)
3. **Place compensator zero $f_{z,c}$ near worst-case load pole:**
   $$C_c = \frac{1}{2\pi f_{z,c} R_c}, \qquad f_{z,c} \approx (0.05\text{–}0.15) f_c$$
   ($C_c = 330\text{ pF} \implies f_{z,c} = 10.3\text{ kHz}$, providing $+85^\circ$ phase boost at $f_c$.)
4. **Place high-frequency pole $f_{p,\text{hf}}$ to attenuate switching ripple & cancel $f_{z,\text{ESR}}$:**
   $$C_{\text{hf}} = \frac{1}{2\pi f_{p,\text{hf}} R_c}, \qquad f_{p,\text{hf}} \approx \min\!\left(f_{z,\text{ESR}}, \; \frac{f_{\text{sw}}}{3}\right)$$
   ($C_{\text{hf}} = 5\text{ pF} \implies f_{p,\text{hf}} = 677\text{ kHz}$, keeping $GM \ge 10\text{–}15\text{ dB}$ and $PM \approx 72^\circ$ across all $V_{\text{in}} \times I_{\text{load}}$ corners.)

**Failure mode:** Omitting $R_c$ or misplacing $f_{z,c} \gg f_c$ removes the Type-II phase boost; the integrator ($-90^\circ$) plus output load pole ($-90^\circ$) collapses phase margin below $10^\circ\text{–}20^\circ$, producing violent load-step ringing.

---

## 5. Dynamic Response, PSRR, Soft-Start & Short-Circuit Protection

### Load-Step Undershoot & Overshoot
For a fast load step $\Delta I_{\text{load}}$:
- **Loop-bandwidth-limited droop:** $\Delta V_{\text{under}} \approx \frac{\Delta I_{\text{load}}}{2\pi f_c C_{\text{out}}} + \Delta I_{\text{load}} R_{\text{ESR}}$.
- **Inductor-slew-limited energy dump (step-down):** Even if the loop immediately commands $D = 0$, stored magnetic energy $\frac{1}{2} L \Delta I_{\text{load}}^2$ must transfer into $C_{\text{out}}$:
  $$\Delta V_{\text{over,min}} = \frac{L \, \Delta I_{\text{load}}^2}{2 C_{\text{out}} V_{\text{out}}}$$
  No amount of loop bandwidth can beat this physical inductor-energy floor without reducing $L$ or increasing $C_{\text{out}}$.

### Audio Susceptibility ($\text{PSRR}$) & Switching Spurs
- **Audio susceptibility $\text{PSRR}(f) = -20\log_{10}|v_{\text{out}}(f)/v_{\text{in}}(f)|$:** At DC and low frequencies, high loop gain $T(s)$ plus PCMC line feedforward yields $60\text{–}95\text{ dB}$ rejection. PSRR reaches its minimum near crossover $f_c$ to $f_{\text{sw}}/2$ (typically $25\text{–}55\text{ dB}$), then rises again above $f_{LC}$ until the ESR zero flattens the $LC$ filter attenuation.
- **Switching spurs ($f_{\text{sw}}, 2 f_{\text{sw}}, \dots$):** Measure via **coherent strobe-sampled transient FFT** (`strobeperiod = T_sw / M`, e.g., $M = 32$ samples/cycle over $N = 1024$ samples = 32 exact cycles) to avoid window leakage and read exact RMS tone levels in `dBV` / `mVrms`.

### Soft-Start Inrush & Cycle-by-Cycle OCP
- **Soft-start inrush:** Ramping the internal reference linearly over $t_{\text{ss}}$ limits capacitive charging current into $C_{\text{out}}$ to $I_{\text{cap}} = C_{\text{out}} V_{\text{out}} / t_{\text{ss}}$, giving peak inductor inrush:
  $$I_{L,\text{inrush,pk}} \approx I_{\text{load}} + C_{\text{out}} \frac{V_{\text{out}}}{t_{\text{ss}}} + \frac{\Delta I_L}{2}$$
  Too-small $t_{\text{ss}}$ slams the inductor into `i_ocp` ($>2\times$ nominal inrush) and winds up the `COMP` capacitor, causing severe output overshoot upon reaching regulation.
- **Hard short-circuit & LEB constraint:** Cycle-by-cycle peak current limiting clamps `I_L` at `i_ocp` every switching cycle. Verify that the **leading-edge blanking time $t_{\text{LEB}}$** (minimum on-time $D_{\text{min}} = t_{\text{LEB}} f_{\text{sw}}$) does not violate volt-second balance during a dead short ($V_{\text{in}} D_{\text{min}} < I_{\text{ocp}}(R_{\text{short}} + R_{\text{DCR}} + R_{\text{on,LS}})$); otherwise inductor current ratchets upward cycle-by-cycle and requires **frequency foldback** or **hiccup mode** to prevent thermal runaway.
