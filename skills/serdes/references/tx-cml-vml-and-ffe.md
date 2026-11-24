# SerDes TX Drivers (CML vs. VML/SST) & Feed-Forward Equalization (FFE)

## 1. CML vs. VML / SST Output Driver Comparison

| Metric | Current-Mode Logic (CML) TX | Voltage-Mode / Source-Series-Terminated (VML / SST) TX |
|---|---|---|
| **Static Power (for same $V_{\text{pp,diff}}$ into $100\;\Omega$)** | $I_{\text{tail}} = V_{\text{pp,diff}} / R_L$ (**4× higher current!** Half wasted in on-chip $50\;\Omega$ pull-up) | $I_{\text{avg}} = V_{\text{pp,diff}} / (4 R_L)$ (**4× lower power!**) |
| **Supply Voltage & Headroom** | Needs tail current source + diff pair + $I R_L$ drop ($V_{\text{DD}} \ge 1.0\text{–}1.2\text{ V}$) | Operates cleanly at low $V_{\text{DD}}$ (`0.8–1.0 V`); swing scales with $V_{\text{DD}}$ |
| **Output Return Loss ($S_{DD11}$)** | Naturally set by precision $50\;\Omega$ poly pull-up resistors (excellent wideband $S_{11}$) | Set by parallel unit-slice $R_{\text{on}} + R_{\text{series}}$ — requires PVT calibration (`ZQ` cal) to keep $S_{11} < -12\text{ dB}$ |
| **PSRR / Supply Noise** | High (tail current source isolates $V_{\text{DD}}$ ripple from differential output) | Poor DC PSRR — typically powered by a dedicated low-noise LDO (see [`skills/ldo/`](../../ldo/SKILL.md)) |
| **FFE Tap Implementation** | Simple current-DAC tail weighting (trivial continuous tap resolution!) | Reconfigurable parallel unit slices (discrete tap resolution, e.g., 24–64 slices) |

---

## 2. 4-Tap TX FFE Mathematics & Peak-Power Constraint

A 4-tap TX FFE forms a discrete-time FIR filter clocked at the symbol rate $f_b = 1/\text{UI}$:

$$y[k] = w_{-1}\,d[k+1] + w_0\,d[k] + w_1\,d[k-1] + w_2\,d[k-2]$$

- **Physical peak-swing / peak-current constraint:** Because the total TX driver current (CML) or total number of parallel slices (VML/SST) is fixed, tap weights **must satisfy**:
  $$|w_{-1}| + |w_0| + |w_1| + |w_2| = 1$$
- **De-emphasis ratio (in dB):** For a 2-tap FFE ($w_0 > 0, w_1 < 0$):
  $$\text{De-emphasis} = 20\log_{10}\!\left(\frac{|w_0| - |w_1|}{|w_0| + |w_1|}\right) = 20\log_{10}\!\left(1 - 2|w_1|\right)$$
  For example, $w_0 = 0.75, w_1 = -0.25$ yields $20\log_{10}(0.50) = \mathbf{-6.02\text{ dB}}$ DC attenuation relative to high-frequency transition bits — flattening `6 dB` of channel loss at the cost of halving the low-frequency swing!
- **Zero-Forcing (ZF) vs. MMSE tap calculation:**
  - Convolving channel SBR $\mathbf{h}$ with FFE vector $\mathbf{w}$ produces equalized cursors $\mathbf{h}_{\text{eq}} = \mathbf{h} * \mathbf{w}$.
  - Setting pre-cursor $h_{\text{eq},-1} = 0$ and 1st post-cursor $h_{\text{eq},1} = 0$ gives exact linear Zero-Forcing taps:
    $$w_{-1} \approx -\frac{h_{-1}}{h_0}\,w_0, \qquad w_1 \approx -\frac{h_1}{h_0}\,w_0$$
  - **Pitfall:** Over-allocating TX FFE (`> 8–10 dB` de-emphasis) crushes the main cursor $h_{\text{eq},0}$, shrinking SNR against RX thermal noise and slicer offset! Split equalization cleanly across TX FFE + RX CTLE + RX DFE.

---

## 3. TX Sizing & Verification Rules

1. **Termination & Output Capacitance (`tb_tx_s11.scs`):**
   - Keep parasitic output capacitance $C_{\text{pad}} + C_{\text{ESD}} + C_{\text{drain}}$ low enough that $S_{DD11}(f) \approx \frac{j\omega C_{\text{tot}} Z_0}{2 + j\omega C_{\text{tot}} Z_0}$ meets the mask (e.g., $<-12\text{ dB}$ at Nyquist $\implies C_{\text{tot}} \le \frac{1}{2\pi f_{\text{Nyq}} Z_0 \cdot 2}$ without a T-coil; add a bridged T-coil if ESD cap exceeds `~200 fF` at `>= 10 Gb/s`!).
2. **Pre-Driver Bandwidth & Duty-Cycle Distortion (DCD):**
   - Size CML/CMOS pre-driver fanout (`~3–4×` per stage) so `20–80%` rise/fall time at the TX output is $\le 0.25\text{–}0.35\,\text{UI}$ and DCD stays `< 1–2% UI`.
3. **Behavioral-to-Transistor Verification:**
   - Start with [`../assets/va/va_tx_ffe_4tap.va`](../assets/va/va_tx_ffe_4tap.va) in [`../assets/tb/tx_ffe/tb_tx_s11.scs`](../assets/tb/tx_ffe/tb_tx_s11.scs) and [`../assets/tb/tx_ffe/tb_tx_ffe_channel.scs`](../assets/tb/tx_ffe/tb_tx_ffe_channel.scs) to confirm target FFE tap weights and eye opening before swapping in transistor CML/VML slices.
