# SAR ADC Top-Level Integration Reference

This reference describes how the five core blocks of a fully differential, asynchronous charge-redistribution SAR ADC wire together, the polarity and cross-connection invariants that must hold, and how to assemble a clean top-level testbench.

---

## 1. Block Inventory

| Block | Instances | Role |
|---|---|---|
| Dual Bootstrap | `I_BTS` (2× single-channel bootstrap) | Generates boosted gate drives `VBTSP`, `VBTSN` ($\approx V_{\text{in}} + V_{\text{DD}}$) for the CDAC sampling switches |
| CDAC (P-side) | `I_CDACP` | Samples `VIP`, holds top-plate residue `VTOPP`, redistributes charge via `VBOTP` |
| CDAC (N-side) | `I_CDACN` | Samples `VIN`, holds top-plate residue `VTOPN`, redistributes charge via `VBOTN` |
| Dynamic Comparator | `I_CMP` | Compares `VTOPP` vs. `VTOPN` on `CMPCK` rising edge; outputs `DCMPP`/`DCMPN` |
| SAR Logic + DAC Drivers | `I_LOGIC` | Self-timed async sequencer (`CMPCK`, bit latches, DAC switch drivers `VBOTP`/`VBOTN`, retimed `DOUT`) |

---

## 2. Top-Level Signal Flow

```
External inputs:
  VIP, VIN          differential analog input centered at Vcm (~VDD/2)
  CLKS              sampling clock (~20-25% high = sample, 75-80% low = convert)
  VREFP, VREFN      reference rails (often VDD and VSS)
  TRIM_OS<K-1:0>    optional comparator offset trim code (mid-code nominal)

Signal wiring:

  VIP ────┬──────────────────────────────► I_CDACP.VIN   (main sampling switch source)
          ├──────────────────────────────► I_CDACN.VINB  (cross-connected feedthrough dummy!)
          └──► I_BTS.VIP ──► I_BTS.VBTSP ─► I_CDACP.VGBTS (boosted gate drive)

  VIN ────┬──────────────────────────────► I_CDACN.VIN   (main sampling switch source)
          ├──────────────────────────────► I_CDACP.VINB  (cross-connected feedthrough dummy!)
          └──► I_BTS.VIN ──► I_BTS.VBTSN ─► I_CDACN.VGBTS (boosted gate drive)

  I_CDACP.VTOP (VTOPP) ──────────────────► I_CMP.VIP
  I_CDACN.VTOP (VTOPN) ──────────────────► I_CMP.VIN

  I_CMP.DCMPP, DCMPN ────────────────────► I_LOGIC.DCMPP, DCMPN
  I_LOGIC.CMPCK ─────────────────────────► I_CMP.CMPCK

  I_LOGIC.VBOTP<M:1> ────────────────────► I_CDACP.VBOT<M:1>
  I_LOGIC.VBOTN<M:1> ────────────────────► I_CDACN.VBOT<M:1>

  CLKS ──────────────────────────────────► I_BTS.CLKS, I_LOGIC.CLKS
  I_LOGIC.DOUT<N-1:0> ───────────────────► digital output (retimed on EOC / CLKS↑)
```

---

## 3. Non-Negotiable Wiring & Polarity Invariants

1. **Cross-connect `VIN` and `VINB` at the two CDACs:**
   - `I_CDACP`: `VIN = VIP`, `VINB = VIN`
   - `I_CDACN`: `VIN = VIN`, `VINB = VIP`
   The main switch samples the true input while the always-off dummy switch cancels hold-mode capacitive feedthrough using the opposite input.
2. **Bootstrap outputs drive gates only (`VGBTS`):**
   `VIP` and `VIN` go directly to the CDAC sampling switch source terminals; `VBTSP`/`VBTSN` go strictly to `VGBTS`.
3. **True differential comparator input:**
   Wire `VTOPP` to `I_CMP.VIP` and `VTOPN` to `I_CMP.VIN` (never single-ended `VTOP` vs. `VCM`).
4. **Feedback sign closure (verify before full FFT!):**
   Trace a positive differential input ($V_{\text{ip}} > V_{\text{in}} \implies V_{\text{top,p}} > V_{\text{top,n}}$) all the way around the loop:
   - Comparator decision must cause the CDAC switch update to **reduce** $V_{\text{top,p}} - V_{\text{top,n}}$ (negative feedback driving residue toward zero!).
   - If the loop instead *increases* $|V_{\text{top,p}} - V_{\text{top,n}}|$, the ADC rails to `000...0` / `111...1` (only 2 output codes). Swap `DCMPP`/`DCMPN` (or swap `VBOTP`/`VBOTN` polarity) so the loop closes negatively.
5. **Comparator reset polarity must match SAR latch polarity:**
   - Active-low dynamic SAR latches (`DOP`/`DON` precharged to `VDD`, NMOS pass gates) require `DCMPP = DCMPN = VDD` during `CMPCK = 0` (2 output inverters on StrongARM; 1 output inverter on Miyahara).
6. **Power/ground and reference partitioning:**
   Keep noisy digital SAR logic rails (`VDD_DIG`/`VSS_DIG`) separated or well-decoupled from sensitive analog/reference rails (`VREFP`/`VREFN`, `VDD_CMP`) to prevent switching droop from modulating the CDAC reference.

---

## 4. Top-Level Port Summary

| Port | Direction | Connection / Notes |
|---|---|---|
| `VIP`, `VIN` | Input | Differential analog input centered at $V_{\text{cm}}$ |
| `CLKS` | Input | Sampling clock (period $1/f_s$, ~20–25% high) |
| `VREFP`, `VREFN` | Inout | Positive and negative CDAC reference rails |
| `VDD`, `VSS` | Inout | Analog/digital supplies (optionally split into `VDDA`/`VDDD`) |
| `DOUT<N-1:0>` | Output | Retimed digital output bus (MSB = bit $N-1$, LSB = bit $0$) |
| `TRIM_OS<K-1:0>` | Input | Optional offset trim code (tie to mid-code nominally) |

---

## 5. Top-Level Testbench Checklist

When wiring `_tb_sar` for full-ADC verification:
- **Coherent differential sine source:** `VIP = Vcm + (A/2)*sin(2*pi*Fin*t)`, `VIN = Vcm - (A/2)*sin(2*pi*Fin*t)`, `Fin = (M/N)*Fs` with $M, N$ coprime and $A \approx 0.85\text{–}0.95\,V_{\text{fs,diff}}$.
- **Buffered realistic `CLKS` edge:** Drive `CLKS` with realistic rise/fall (e.g., `10 ps`) or through a clock buffer matching the target clock tree.
- **Reference network:** Start with ideal low-impedance `VREFP`/`VREFN` in Phase 1–3, then add realistic series impedance / bondwire inductance + on-chip decap in Phase 4 to check reference recovery.
- **Reconstruction DAC / `CODE` monitor:** Attach a behavioral ideal DAC (such as `assets/va/behavioral_10b/va_dac_10b_diff.va` or `assets/va/tutorial_4b/_va_dac_4b.va`) clocked on the retimed output strobe for quick waveform inspection, and run `adctoolbox.analyze_spectrum()` on strobed outputs (`strobeoutput=strobeonly`).

---

## 6. Common Integration Failure Modes

| Mistake | Observable Symptom | Fix |
|---|---|---|
| `VIN`/`VINB` not cross-connected on CDACs | Poor high-frequency SFDR / common-mode feedthrough | Wire `I_CDACP.VINB = VIN` and `I_CDACN.VINB = VIP` |
| Positive feedback in comparator → logic → CDAC loop | Only 2 codes (`0` and full-scale) | Trace sign for `VIP > VIN` and ensure `VTOPP - VTOPN` shrinks on each trial |
| `DOUT` bus bit order reversed in Spectre | Sawtooth / scrambled FFT noise floor | Match Spectre's MSB-first `[N-1:0]` port expansion |
| Output DFFs clocked mid-conversion | Corrupted LSBs / noisy spectrum | Clock output DFFs on `STOP` rising edge (or `CLKS` rising edge if latches hold) |
| `CMPCK` exceeds conversion window at `ss` | Undecided LSBs or 1-cycle-late codes | Check `T_conv` vs. $(1 - D_{\text{samp}})/f_s$ at `ss` and resize clock ring / comparator |
| Unconnected or floating `VREFN` on DAC drivers | Bottom plates stuck high | Tie both `VREFP` and `VREFN` into DAC switch block |
