# Current-Steering DAC Dynamic Linearity, Output Impedance & Glitch Control

While DC mismatch caps low-frequency SFDR, high-speed Current-Steering DAC (CS-DAC) dynamic linearity (`SFDR`, `HD2`, `HD3`, `IMD3`) is almost universally governed by **code-dependent output impedance $Z_{\text{out}}(f)$**, **switch-pair dynamics**, and **switching timing skew / glitch impulse**.

---

## 1. Finite Unit-Cell Output Impedance $Z_{\text{unit}}(f)$ vs. SFDR / HD2 / HD3

When $k$ of the $N_{\text{tot}} = 2^N - 1$ unit current cells steer to `IOUTP` and $(N_{\text{tot}} - k)$ steer to `IOUTN` (each driving a load resistor $R_L$), the active cells place their parallel output impedance $Z_{\text{unit}}(f) / k$ in shunt with $R_L$:

$$V_{\text{out,p}}(k) = \frac{k\,I_{\text{lsb}}\,R_L}{1 + k\,\dfrac{R_L}{Z_{\text{unit}}(f)}}, \qquad V_{\text{out,n}}(k) = \frac{(N_{\text{tot}} - k)\,I_{\text{lsb}}\,R_L}{1 + (N_{\text{tot}} - k)\,\dfrac{R_L}{Z_{\text{unit}}(f)}}$$

Expanding $V_{\text{diff}}(k) = V_{\text{out,p}}(k) - V_{\text{out,n}}(k)$ around mid-scale yields the classic **Lin & Bult / Van den Bosch impedance-SFDR equations**:

- **Single-ended output (HD2-limited):**
  $$\text{HD}_2 \approx \frac{N_{\text{tot}}\,R_L}{4\,|Z_{\text{unit}}(f)|}$$
- **Differential output (even harmonics cancel ideally; HD3-limited!):**
  $$\text{HD}_3 \approx \left(\frac{N_{\text{tot}}\,R_L}{4\,|Z_{\text{unit}}(f)|}\right)^2$$
- **Differential two-tone $\text{IMD}_3$:** Tracks $3\times$ the third-order compression term ($\text{IMD}_3 \approx \text{HD}_3 + 9.5\text{ dB}$ at equal tone amplitude, or $-6\text{ dB}$ lower per tone when backed off by `6 dB` for two equal tones!).

### Numerical Example (10-bit CS-DAC, $N_{\text{tot}} = 1023$, $R_L = 50\;\Omega$, target $\text{HD}_3 < -72\text{ dBc}$):
- Need $\frac{N_{\text{tot}} R_L}{4 |Z_{\text{unit}}|} < 10^{-72/40} = 0.01585 \implies |Z_{\text{unit}}(f_{\text{sig}})| > \frac{1023 \times 50}{4 \times 0.01585} \approx \mathbf{807\text{ k}\Omega}$!
- At `100 MHz`, a unit-cell output impedance of `807 kΩ` allows a **maximum parasitic capacitance per unit cell of only $C_{\text{unit}} < \frac{1}{2\pi \cdot 100\text{ MHz} \cdot 807\text{ k}\Omega} \approx 2.0\text{ fF}$!**
- **Takeaway:**
  1. Always cascode the unit current source (`r_cell ≈ g_m,cas * r_o,cas * r_o,cs`) to reach `MΩ`-class DC resistance!
  2. Above the cascode pole $f_p = \frac{1}{2\pi r_{\text{cell}} C_{\text{unit}}}$, $|Z_{\text{unit}}(f)| \approx \frac{1}{2\pi f C_{\text{unit}}}$ drops at $-20\text{ dB/dec}$, so **differential HD3 degrades at $-40\text{ dB/dec}$** (and any P/N mismatch HD2 degrades at $-20\text{ dB/dec}$)!
  3. Keep the switch transistors **minimum channel length $L_{\min}$** (smallest $C_{gd}, C_{db}$) and add a **thick/bleeder cascode** or **always-on dummy impedance** if RF-band SFDR is dominated by $C_{\text{unit}}$.

---

## 2. Differential Switch Pair & Crossing-Point Control

Inside each unit current cell, a differential switch pair (`MSW_P`, `MSW_N`) steers $I_{\text{cell}}$ between `IOUTP` and `IOUTN` from a shared common-source node `VS`:

- **Simultaneous-OFF catastrophe:** If both gate drives cross below $V_S + V_{\text{th}}$ (for NMOS switches) or above $V_S - |V_{\text{th}}|$ (for PMOS switches), **both switches briefly turn OFF**, forcing the tail current source/cascode to collapse into triode! When one switch turns back ON, charging `C_VS` creates a huge code-dependent current glitch and strong HD2/HD3!
- **Fix — Low-crossing-point (PMOS) / High-crossing-point (NMOS) switch drivers:**
  - Design the differential latch/driver immediately before the switch pair so the complementary gate waveforms **cross cleanly inside the both-ON region** (e.g., crossing at $\sim 35\%\text{–}40\%$ of swing for PMOS switches, or $\sim 60\%\text{–}65\%$ for NMOS switches) — guaranteeing `VS` barely moves (`< 20–50 mV`) during switching!
  - **Reduced gate swing:** Limit switch gate swing to just enough to turn the OFF switch firmly below subthreshold while keeping the ON switch in saturation/moderate overdrive, minimizing $C_{gd}$ clock feedthrough onto `IOUTP`/`IOUTN`!
  - **Local retiming latches:** Place a dedicated master-slave latch right next to every switch cell driven by a balanced H-tree clock to minimize inter-cell timing skew $\Delta t_{\text{skew}}$!

---

## 3. Glitch Impulse Energy & Dynamic Linearization Techniques

### Major-Carry Glitch Impulse
If the MSB switches at $t_0 + \Delta t_{\text{skew}}$ while the lower binary bits switch at $t_0$ during the major-carry transition (`0111...1 -> 1000...0`), the output briefly collapses by up to full-scale $V_{\text{FS}}$ for duration $|\Delta t_{\text{skew}}|$, producing a **glitch impulse energy**:

$$E_{\text{glitch}} = \int |V_{\text{diff}}(t) - V_{\text{step,ideal}}(t)|\,dt \approx V_{\text{FS}}\,|\Delta t_{\text{skew}}| \quad [\text{pV}\cdot\text{s}]$$

- Even `100 ps` of unsegmented MSB skew on a `1 Vpp` DAC yields **$100\text{ pV}\cdot\text{s}$** of code-dependent glitch — severely degrading wideband SFDR!
- **Mitigations (in order of effectiveness):**
  1. **Thermometer segmentation ($M = 5\text{–}7$ bits):** Reduces worst-case glitch impulse by $2^M$ ($32\text{–}128\times$!).
  2. **Balanced local retiming + crossing-point drivers:** Cuts $\Delta t_{\text{skew}}$ to `< 5–10 ps`.
  3. **Return-to-Zero (RZ) output stage:** Shorts or redirects DAC current to a dump node during the switching instant (`t_switch`), hiding transition glitches completely at the cost of `-6 dB` fundamental output power (50% duty cycle) and higher jitter sensitivity.
  4. **Dynamic Element Matching (DEM) / Data-Weighted Averaging (DWA):** Randomly rotates or cyclically shifts which thermometer unit cells are selected each clock cycle, scrambling static current-source mismatch harmonics into white or high-pass-shaped noise — boosting SFDR by `15–25 dB`!

---

## 4. Layout & Gradient Cancellation Rules

1. **$Q^2$ Random-Walk / Common-Centroid Current-Source Matrix:** Distribute every unit current cell across four quadrants to cancel both linear ($x, y$) and quadratic ($x^2, y^2$) process, thermal, and IR-drop gradients across the array.
2. **Split Supply Domains:** Physically separate the quiet analog current-source array supply (`VDDA_CS`) from the noisy digital decoder/latch/switch-driver supply (`VDDD_SW`), and surround the array with dummy current cells on all four sides.
3. **Symmetrical Output Bus Routing:** Route `IOUTP` and `IOUTN` identically (matched length, shielding, and parasitic capacitance) to preserve even-order HD2 cancellation!
