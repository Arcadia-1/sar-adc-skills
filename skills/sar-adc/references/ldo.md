# LDO Theory & Verification Reference for SAR ADC Power Delivery

A low-dropout (LDO) linear regulator decouples the SAR ADC's analog and reference domains from noisy system supplies. Because a SAR ADC draws periodic high-frequency current bursts during CDAC switching and comparator firing, the LDO must combine adequate loop bandwidth, low output impedance (assisted by on-chip decoupling), and high PSRR up to $f_s/2$.

---

## 1. Why the SAR ADC Needs a Clean Supply

- **PSRR budget:** Any supply ripple reaching `VOUT` or `VREF` adds directly to the conversion error. For an $N$-bit ADC with full-scale $V_{\text{FS}}$, keeping supply-coupled error below $\sim 0.5\text{ LSB} = V_{\text{FS}}/2^{N+1}$ typically requires **40–60 dB PSRR** across low-to-mid frequencies, with on-chip decoupling capacitance `CL` shunting high-frequency ripple beyond the LDO unity-gain bandwidth.
- **Burst load transients:** Each bit trial pulls a short charge burst through `VREF`/`VDD`. The resulting voltage droop is $\Delta V_{\text{out}} \approx \Delta I_{\text{burst}} \cdot |Z_{\text{out}}(f_{\text{switch}})|$ and must settle before the next bit comparison (or stay within redundancy/LSB budget).

---

## 2. Circuit Topology

Standard PMOS-pass LDO with a Miller-compensated single-stage error amplifier:

```
VIN ──► M2 (PMOS pass device) ─────────────────────────► VOUT
              ▲ gate = net_g                                │
              │                                       R0 (R_FB_TOP)
         ┌────┴─────────────────────────────┐               │
         │         Error Amplifier          │          V_fb
         │  M3 / M4 (PMOS mirror load)      │               │
         │     ▲              ▲             │         R1 (R_FB_BOT)
         │   M0 (VREF)     M1 (V_fb)  ◄─────┘               │
         │   NMOS differential pair                        VSS
         │        │
         │   M5 (tail, N×) ─── M6 (diode ref, 1×) ◄── I_bias
         └──────────────────────────────────┘
Compensation: series Rz + Cc from net_g to VOUT
Output decoupling: CL (+ parasitic ESR) on VOUT
```

**Matching constraints:** `M0 = M1` (matched diff pair), `M3 = M4` (matched current mirror), `M5/M6` share the same $L$ with $W_{M5} = N_{\text{mir}} \cdot W_{M6}$.

$$V_{\text{out}} = V_{\text{ref}} \cdot \frac{R_0 + R_1}{R_1}, \qquad \beta = \frac{R_1}{R_0 + R_1} = \frac{V_{\text{ref}}}{V_{\text{out}}}$$

---

## 3. Initial Sizing Methodology

Given targets **$(V_{\text{ref}}, V_{\text{in}}, V_{\text{out}}, I_{\text{load}}, C_{\text{load}})$**:

1. **Feedback divider (`R0`, `R1`):** Allocate $I_{\text{div}} \approx 0.5\text{–}1\% \cdot I_{\text{load}}$ (or lower for ultra-low-power designs), giving $R_1 = V_{\text{ref}} / I_{\text{div}}$ and $R_0 = (V_{\text{out}} - V_{\text{ref}}) / I_{\text{div}}$.
2. **Pass PMOS (`M2`):** Start near minimum $L$ (or slightly above $L_{\min}$ if higher $r_{o2}$ / PSRR is needed) and scale total width (multi-finger) to deliver $I_{\text{load,max}}$ at minimum dropout $V_{\text{in,min}} - V_{\text{out}}$ while keeping `M2` in saturation.
3. **Bias mirror (`M5`, `M6`):** Choose $I_{\text{bias}}$ and mirror ratio $N_{\text{mir}}$ to set error-amp tail current $I_{\text{tail}} = N_{\text{mir}} I_{\text{bias}}$. Use long $L$ ($\ge 4 L_{\min}$) for low current mismatch.
4. **Error-amp diff pair (`M0`, `M1`) & load (`M3`, `M4`):** Use long $L$ ($\ge 2\text{–}4 L_{\min}$) for high intrinsic gain $A_{v1} = g_{m1}(r_{o1} \parallel r_{o3})$, low $1/f$ noise, and low offset.
5. **Compensation (`Cc`, `Rz`):** Size `Cc` to set unity-gain bandwidth $\text{GBW} \approx \beta g_{m1} / C_c$ well below the non-dominant output pole $\omega_{p2}$, and choose nulling resistor $R_z > 1/g_{m2}$ to move the right-half-plane Miller zero into the left half-plane ($\omega_z = -1/[(R_z - 1/g_{m2}) C_c]$) near $\omega_{p2}$ to boost phase margin to $\ge 45\text{–}60^\circ$ across the full load-current range (including light load!).

---

## 4. Small-Signal Formulas & Trade-Offs

### Loop Gain, Poles, and Zero

$$T_0 = \beta \cdot A_{v1} \cdot g_{m2} r_{o2}, \qquad A_{v1} = g_{m1}(r_{o1} \parallel r_{o3}), \qquad \text{GBW} \approx \frac{\beta g_{m1}}{C_c}$$

| Pole / Zero | Approximate Expression | Design Note |
|---|---|---|
| Dominant pole $\omega_{p1}$ | $\approx \dfrac{1}{A_{v1} g_{m2} r_{o2} (r_{o1}\parallel r_{o3}) C_c}$ (Miller-multiplied) | Sets DC-to-GBW roll-off ($\omega_{p1} \approx \text{GBW}/T_0$) |
| Output pole $\omega_{p2}$ | $\approx \dfrac{g_{m2}}{C_L}$ (when $C_L \gg C_c$) | Moves inward at **light load** ($g_{m2} \propto \sqrt{I_{\text{load}}}$ drops) — always check light-load stability! |
| Compensation zero $\omega_z$ | $= -\dfrac{1}{(R_z - 1/g_{m2}) C_c}$ | RHP if $R_z = 0$; LHP when $R_z > 1/g_{m2}$ |
| High-freq pole $\omega_{p3}$ | $\approx \dfrac{1}{R_z C_S}$, $C_S \approx C_{g2} \parallel C_c$ | Keep $\omega_{p3} \ge 2\text{–}3 \times \text{GBW}$ |

### Regulation & PSRR

- **DC output impedance (load regulation):** $Z_{\text{out}}(0) \approx \dfrac{1}{\beta A_{v1} g_{m2}}$
- **DC line regulation:** $\dfrac{\Delta V_{\text{out}}}{\Delta V_{\text{in}}} \approx \dfrac{1}{T_0}$ (ignoring supply feedthrough of the error-amp bias/mirror).
- **PSRR across frequency:**
  - **At DC:** $\text{PSRR}(0) \approx T_0$ (higher $A_{v1}$, $g_{m2}$, and $r_{o2}$ improve DC PSRR).
  - **Mid-band (above $\omega_{p1}$, below GBW):** Loop gain rolls off at $-20\text{ dB/dec}$, so PSRR degrades accordingly.
  - **High frequency (above GBW):** The error amp loses control. Supply ripple couples through `M2` ($r_{o2}$ and $C_{gd2}$), so supply-to-output transfer approaches $g_{m2} r_{o2} / (1 + g_{m2} r_{o2}) \approx 1$ (0 dB rejection) unless shunted to ground by the low impedance of `CL` ($1/(\omega C_L)$) or isolated by a cascode/pre-regulator.

### Output-Referred Noise

- **Thermal noise PSD:**
  $$S_{v,\text{out,th}} \approx \frac{1}{\beta^2}\left[4kT(R_0 \parallel R_1) + \frac{8kT\gamma}{g_{m1}}\left(1 + \frac{g_{m4}}{g_{m1}}\right)\right]$$
- **Flicker ($1/f$) noise PSD:**
  $$S_{v,\text{out},1/f}(f) \approx \frac{2K}{\beta^2 C_{\text{ox}} f}\left[\frac{1}{W_1 L_1} + \frac{1}{W_4 L_4}\left(\frac{g_{m4}}{g_{m1}}\right)^2\right]$$
- Maximize $W_1, L_1, L_4$ (and keep $g_{m4}/g_{m1}$ small) to suppress low-frequency noise; maximize $g_{m1}$ for thermal noise.

### Device Tuning Summary

| Adjustment | Improves | Degrades |
|---|---|---|
| ↑ $W_1$ (diff pair) | Load/line reg, DC PSRR, noise, offset | Phase margin (GBW ↑) |
| ↑ $L_1, L_4$ | $A_{v1}$, $1/f$ noise, offset, DC PSRR | Mirror/internal pole frequency |
| ↑ $W_2$ (pass PMOS) | Dropout, $g_{m2}$, DC reg | $C_{g2}$ ↑ ($\omega_{p3}$ ↓, area ↑) |
| ↑ $C_c$ | Phase margin (GBW ↓) | Mid-band PSRR, transient speed |
| Tune $R_z$ ($> 1/g_{m2}$) | Places LHP zero to recover phase margin | Excess $R_z$ pulls $\omega_{p3}$ inward |
| ↑ $C_L$ | High-freq PSRR, burst droop | Pulls $\omega_{p2}$ inward (harder stability at light load) |

---

## How to Verify an LDO

> **Ready-to-run process-independent LDO Spectre testbenches & Verilog-A models:** To avoid duplicate testbenches across skills, all standalone LDO verification assets live in the canonical [`skills/ldo/`](../../ldo/SKILL.md) skill — see [`skills/ldo/assets/tb/`](../../ldo/assets/tb/README.md) (`tb_ldo_dc_reg_dropout.scs`, `tb_ldo_stb.scs`, `tb_ldo_psrr_zout_noise.scs`, `tb_ldo_load_line_tran.scs`, `analyze_ldo.py`) and the PMOS-pass / capless Verilog-A models [`va_ldo_pmos.va`](../../ldo/assets/va/va_ldo_pmos.va) and [`va_ldo_capless.va`](../../ldo/assets/va/va_ldo_capless.va).

1. **DC Operating Point, Line & Load Regulation:**
   - Sweep $I_{\text{load}}$ from $I_{\text{min}}$ (light load) to $I_{\text{max}}$ (full load) and $V_{\text{in}}$ from $V_{\text{in,min}}$ to $V_{\text{in,max}}$ across PVT.
   - Verify `VOUT` accuracy (typically within $\pm 1\%$), dropout headroom, quiescent current $I_Q$, and that every device (`M0`–`M6`, `M2`) stays in saturation.
2. **Loop Stability (`stb` analysis):**
   - Insert an `iprobe` in the feedback loop (e.g., between `VOUT` and `R0`) and run Spectre `stb` across **light load, nominal load, and max load**, plus PVT and `CL` extremes.
   - **Pass criteria:** DC loop gain $T_0 \ge 50\text{–}60\text{ dB}$, phase margin $\text{PM} \ge 45\text{–}60^\circ$, gain margin $\ge 10\text{ dB}$ at **all** load currents (light load is usually worst-case!).
3. **AC PSRR & Output Impedance:**
   - Apply AC `mag=1` on `VIN` (`ac start=1 stop=10G`) and plot $\text{PSRR}(f) = -20\log_{10}|V_{\text{out}}(f)/V_{\text{in}}(f)|$. Check PSRR at DC, 1 MHz, and $f_s/2$.
   - Inject AC `1 A` current probe at `VOUT` to plot $|Z_{\text{out}}(f)|$ and confirm $|Z_{\text{out}}(f_{\text{switch}})|$ meets the burst droop budget.
4. **Transient Load-Step & CDAC Burst Droop:**
   - Apply fast current pulses mimicking CDAC bit-switching bursts (and a full $I_{\text{min}} \leftrightarrow I_{\text{max}}$ step).
   - Verify peak droop/overshoot $< 0.5\text{ LSB}$ (or within reference budget) and well-damped recovery (no ringing).
5. **Output Noise (`noise` analysis):**
   - Integrate `noise` PSD over the ADC signal bandwidth (e.g. `10 Hz` to $f_s/2$) and confirm integrated RMS noise fits inside the supply/reference noise budget.
