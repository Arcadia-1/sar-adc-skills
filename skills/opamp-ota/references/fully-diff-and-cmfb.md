# Fully Differential OTAs & Common-Mode Feedback (CMFB)

## 1. Why Fully Differential?

Compared to a single-ended opamp, a fully differential OTA (`VIP`/`VIN` $\to$ `VOP`/`VON`):
- **Doubles usable output swing** ($V_{\text{out,diff,pp}} = 2 V_{\text{out,se,pp}}$), adding $+6\text{ dB}$ dynamic range at the same supply voltage.
- **Cancels even-order harmonic distortion (HD2, HD4)** and rejects common-mode supply/substrate/switch-charge-injection disturbances.
- **Requires an explicit Common-Mode Feedback (CMFB) loop:** Without CMFB, the output common-mode voltage $V_{\text{ocm}} = \frac{1}{2}(V_{\text{OP}} + V_{\text{ON}})$ floats between the high-impedance NMOS and PMOS current sources and slams into `VDD` or `VSS`!

---

## 2. Continuous-Time vs. Switched-Capacitor CMFB

| Feature | Continuous-Time CMFB | Switched-Capacitor (SC) CMFB |
|---|---|---|
| Sensing network | Matched resistive divider $R_{\text{cm}}$ (+ parallel $C_{\text{cm}}$ zero) or dual differential pair | Two clock phases charging $C_{\text{cm}}$ to $V_{\text{ocm,ref}} - V_{\text{bias}}$ |
| Output swing linearity | Resistive divider loads $R_{\text{out}}$ (reduces DC gain unless $R_{\text{cm}} \gg R_{\text{out}}$); diff-pair sensor clips on large differential swings! | **Zero resistive loading & linear across full rail-to-rail differential swing** |
| Power | Extra static error-amp current | Near-zero static power (dynamic charging only) |
| Clock requirement | None (continuous-time filters, LDO, CT-DSM) | Requires non-overlapping clocks (SC integrators, pipeline/SAR/DT-DSM) |

---

## 3. CMFB Stability — The Silent Failure Mode

A fully differential OTA has **two simultaneous feedback loops** that must BOTH be verified across PVT and capacitive loads:

1. **Differential-Mode (DM) loop:** Sets signal bandwidth $\text{GBW}_{\text{DM}}$, $\text{PM}_{\text{DM}} \ge 60^\circ$, and differential settling.
2. **Common-Mode (CM / CMFB) loop:** Sets common-mode rejection bandwidth $\text{GBW}_{\text{CM}}$ and $\text{PM}_{\text{CM}} \ge 60^\circ$.

### Key CMFB Design Rules
- **Size $\text{GBW}_{\text{CM}} \approx (0.5\text{–}1.5)\,\text{GBW}_{\text{DM}}$:** Too slow $\implies$ common-mode disturbances (e.g., clock feedthrough) linger and compress swing or convert to differential error; too fast $\implies$ risks instability from extra CMFB error-amp poles!
- **Watch the CMFB resistive sensor pole:** A resistive divider $R_{\text{cm}}$ + CMFB input cap $C_{\text{in,cm}}$ creates an extra pole at $\omega_{p,\text{sense}} = 2 / (R_{\text{cm}} C_{\text{in,cm}})$. Always add small feed-forward capacitors $C_{\text{cm}}$ in parallel with $R_{\text{cm}}$ to cancel that pole with a zero!
- **Two-stage fully differential OTAs:** Never feed CMFB from the 2nd-stage outputs all the way back to the 1st-stage tail unless carefully compensated (3-pole loop!). Prefer **local 1st-stage CMFB** + **separate 2nd-stage CMFB** (or feed-forward CMFB into the 2nd-stage current loads).

---

## 4. Measuring Both DM and CM Stability in Standalone Spectre

Use a lossless reciprocal Tian balun (`diff_stb_probe`, bundled in [`../assets/tb/fully_diff/tb_fd_ota_dm_cm_stb.scs`](../assets/tb/fully_diff/tb_fd_ota_dm_cm_stb.scs)) containing two native Spectre `iprobe` primitives (`IPRB_DM` and `IPRB_CM`) placed in the differential feedback paths:
- `stb_dm stb ... probe=I_PRB.IPRB_DM` extracts exact differential-mode $T_{\text{DM}}(s)$, $\text{UGF}_{\text{DM}}$, $\text{PM}_{\text{DM}}$, and $\text{GM}_{\text{DM}}$.
- `stb_cm stb ... probe=I_PRB.IPRB_CM` extracts exact common-mode $T_{\text{CM}}(s)$, $\text{UGF}_{\text{CM}}$, $\text{PM}_{\text{CM}}$, and $\text{GM}_{\text{CM}}$ — **in the exact same simulation, without breaking DC bias or loading either loop!**
