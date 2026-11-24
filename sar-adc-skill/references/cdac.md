# CDAC (Capacitive DAC) Design Reference

The charge-redistribution CDAC is the core analog engine of a SAR ADC. It merges input sampling, residue storage, and binary/sub-radix DAC feedback into one capacitor array — eliminating a separate sample-and-hold and explicit DAC.

---

## 1. Charge Redistribution Principle

### Sampling Phase

During sampling (`CLKS = 1`), the top plate tracks $V_{\text{in}}$ through the sampling switch while all bottom plates connect to a fixed sampling voltage $V_{\text{bot,samp}}$ (commonly $V_{\text{refp}}$, $V_{\text{refn}}$, or $V_{\text{cm}}$). Total charge stored on the top plate is:

$$Q_{\text{samp}} = C_{\text{tot}} (V_{\text{in}} - V_{\text{bot,samp}}), \qquad C_{\text{tot}} = \sum_i C_i + C_{\text{dummy}}$$

When the sampling switch opens, the top plate floats and $Q_{\text{samp}}$ is conserved.

### Redistribution Phase

When bottom plates switch to $V_{\text{bot},i}$ (with total top-plate parasitic capacitance $C_p$ tied to AC ground):

$$V_{\text{top}} = V_{\text{in}} + \frac{1}{C_{\text{tot}} + C_p} \sum_{i} C_i \left(V_{\text{bot},i} - V_{\text{bot,samp}}\right)$$

**Concrete convention (bottom plates start at $V_{\text{refp}}$, switching bit $i$ moves $V_{\text{bot},i}$ to $V_{\text{refn}}$, $V_{\text{ref}} = V_{\text{refp}} - V_{\text{refn}}$):**

$$V_{\text{top}} = V_{\text{in}} - \frac{C_{\text{tot}}}{C_{\text{tot}} + C_p} \cdot V_{\text{ref}} \sum_{i} D_i \frac{C_i}{C_{\text{tot}}}$$

where $D_i \in \{0, 1\}$ indicates whether capacitor $C_i$ has been switched from $V_{\text{refp}}$ to $V_{\text{refn}}$. Notice that when $D_i = 0$ for all $i$, $V_{\text{top}} = V_{\text{in}}$ identically.

### Fully Differential Operation

Two matched CDACs sample $V_{\text{ip}}$ and $V_{\text{in}}$ respectively. After each comparator decision, the P-side and N-side switches move complementarily (for example, in monotonic switching, only the side with the higher top-plate voltage switches from $V_{\text{refp}}$ down to $V_{\text{refn}}$; in Vcm-based or bidirectional switching, one side steps up and the other steps down so common mode stays constant):

- **Monotonic (set-and-down):** Both sides start at $V_{\text{refp}}$. For each bit $i$, only one side's capacitor switches to $V_{\text{refn}}$ (changing $V_{\text{top,p}} - V_{\text{top,n}}$ by $\pm V_{\text{ref}} \cdot C_i / C_{\text{tot}}$). Simple and energy-efficient, but top-plate common mode drops from $V_{\text{cm}}$ toward $V_{\text{cm}} - V_{\text{ref}}/2$, which changes comparator input-pair overdrive and offset across bit cycles.
- **Vcm-based / Bidirectional:** Each bit switches from $V_{\text{cm}}$ to $V_{\text{refp}}$ on one side and $V_{\text{refn}}$ on the other (or splits each capacitor into two halves switched oppositely), changing $V_{\text{top,p}} - V_{\text{top,n}}$ by $\pm 2 V_{\text{ref}} \cdot C_i / C_{\text{tot}}$ while keeping top-plate common mode nearly constant.

Differential operation doubles the full-scale swing ($V_{\text{fs,diff}} = 2 V_{\text{ref}}$), suppresses even-order harmonics, and rejects common-mode charge injection and supply coupling.

---

## 2. Capacitor Array Architectures

### Binary-Weighted Array

For an $N$-bit array with bits $1 \dots N$ (bit $N$ = MSB) plus one unit dummy capacitor permanently tied to a fixed reference:

$$C_i = 2^{i-1} C_u \quad (i = 1 \dots N), \qquad C_{\text{dummy}} = C_u, \qquad C_{\text{tot}} = \left(1 + \sum_{i=1}^{N} 2^{i-1}\right) C_u = 2^N C_u$$

- **Pros:** Exact binary weights, simple digital output (no digital recombination), straightforward common-centroid layout.
- **Cons:** Total capacitance doubles with each added bit ($2^{10} = 1024\,C_u$ for 10 bits, $2^{14} = 16384\,C_u$ for 14 bits), increasing area, sampling power, and reference switching energy.

### Sub-Radix-2 Redundant Array

Instead of radix $2.0$, successive bit weights grow by radix $r \in [1.8, 1.95]$ (for example, an 11-bit converter using 11–12 bit trials with weights like `1, 2, 3, 6, 12, 21, 42, 78, 144, 270, 501` units — radix $\approx 1.86$ — built from parallel sub-units such as `1×` and `3×` unit cells).

- **Pros:** Earlier bit decisions can tolerate DAC settling errors, reference droop, or comparator noise up to the redundancy range, and later trials recover the error cleanly.
- **Cons:** Requires 1–2 extra bit cycles and a small digital adder/LUT to combine redundant bit weights into a binary code.

### Segmented (Split-Capacitor) Array

Above ~10–12 bits, an attenuation (bridge) capacitor splits the array into MSB and LSB sub-DACs, sharply reducing total unit count. The trade-off is high sensitivity to parasitic capacitance on the LSB sub-DAC top plate, which alters the effective bridge ratio and requires layout care or calibration.

---

## 3. Unit Capacitor Sizing

### $kT/C$ Sampling Noise Floor

- **Single-ended** ($V_{\text{fs}} = V_{\text{ref}}$, noise variance $kT / C_{\text{tot}}$):
  $$\sqrt{\frac{kT}{C_{\text{tot}}}} \le \frac{V_{\text{fs}}}{2^N \cdot K} \implies C_{\text{tot}} \ge \frac{K^2 \cdot kT \cdot 2^{2N}}{V_{\text{fs}}^2}$$
- **Fully differential** ($V_{\text{fs,diff}} = 2 V_{\text{ref}}$, two independent sampling caps give differential noise variance $2 kT / C_{\text{tot}}$):
  $$\sqrt{\frac{2kT}{C_{\text{tot}}}} \le \frac{V_{\text{fs,diff}}}{2^N \cdot K} \implies C_{\text{tot}} \ge \frac{2 K^2 \cdot kT \cdot 2^{2N}}{V_{\text{fs,diff}}^2}$$

where $K$ sets the thermal-noise margin relative to 1 LSB ($K = \sqrt{12} \approx 3.46$ equals quantization noise; $K = 4\text{–}6$ keeps $kT/C$ comfortably below quantization noise).

**Worked example ($N = 11$, $V_{\text{ref}} = 0.9\text{ V}$, $T = 300\text{ K}$, $kT = 4.14 \times 10^{-21}\text{ J}$, $K = 4$):**
- **Differential** ($V_{\text{fs,diff}} = 1.8\text{ V}$, $1\text{ LSB} = 0.879\text{ mV}$, $\Delta/\sqrt{12} = 0.254\text{ mV}$):
  $$C_{\text{tot}} \ge \frac{2 \times 16 \times 4.14 \times 10^{-21} \times 4.194 \times 10^6}{1.8^2} \approx 172\text{ fF per side}$$
  At $C_{\text{tot}} \approx 205\text{ fF}$ per side, $v_{n,\text{rms,diff}} = \sqrt{2kT/C_{\text{tot}}} \approx 0.201\text{ mV}$ (0.23 LSB, comfortably below quantization noise).
- **Single-ended** ($V_{\text{fs}} = 0.9\text{ V}$): requires $2\times$ larger capacitance per side ($\approx 343\text{ fF}$) for the same $K$ because the full-scale swing is halved.

### Matching Requirements

Capacitor mismatch limits static linearity (DNL/INL). At the worst-case mid-scale MSB transition (half the array switches against the other half), the 1-sigma DNL in LSBs scales as:

$$\sigma_{\text{DNL,MSB}} \approx \sqrt{2^N} \cdot \frac{\sigma_u}{C_u} \text{ LSB}$$

For $\sigma_{\text{DNL,MSB}} < 0.2\text{–}0.3\text{ LSB}$, unit capacitor relative matching $\sigma_u / C_u$ must scale down as $2^{-N/2}$. Building larger weights from identical parallel unit cells (e.g., 1× and 3× MOM/MIM units) in a common-centroid array with perimeter layout dummies is standard practice.

---

## 4. Sampling Switch & Dummy Feedthrough Cancellation

### Bootstrap Integration

The bootstrap circuit outputs a **boosted gate drive** `VGBTS ≈ VIN + VDD` — not a sampled voltage. The analog input connects directly to the source of the CDAC's internal NMOS sampling switch:

- **Main sampling switch (MS):** Gate = `VGBTS`, Source = `VIN`, Drain = `VTOP`. Prefer a **standard-Vth** (rather than ultra-low-Vth) NMOS when conversion time is long, to minimize off-state subthreshold leakage off the floating top plate during conversion.
- **Cross-connected dummy switch (MD):** Same size as MS, Drain = `VTOP`, Source = `VINB` (the complementary differential input), Gate tied to `VSS` (always OFF). Because `VIN` keeps swinging during the hold/conversion phase, the off-state overlap/feedthrough capacitance of MS couples input changes onto `VTOP`, degrading high-frequency SFDR. Tying an identical always-off dummy switch from `VTOP` to `VINB` injects equal and opposite capacitive feedthrough, cancelling the error to first order.

---

## 5. Bottom-Plate DAC Switches

### Complementary CMOS Switch (2-Transistor Pass Gate)

Each bit's bottom plate can be driven between `VREFP` and `VREFN` by a single PMOS + NMOS pair sharing one control line `DCTRL[i]`:

```
         VREFP
           |
     PMOS (G = DCTRL[i], S = VREFP, D = VBOT[i])
           |
    ────── VBOT[i] ──────
           |
     NMOS (G = DCTRL[i], S = VREFN, D = VBOT[i])
           |
         VREFN
```

| `DCTRL[i]` | PMOS | NMOS | `VBOT[i]` | Effect on `VTOP` (from `VREFP` initial state) |
|---|---|---|---|---|
| LOW (`0`) | ON | OFF | `VREFP` | Initial / sample state |
| HIGH (`VDD`) | OFF | ON | `VREFN` | `VTOP` steps down by $V_{\text{ref}} \cdot C_i / (C_{\text{tot}} + C_p)$ |

- **Sizing rule:** Scale switch width proportionally to the bit capacitance $C_i$ (clamped at minimum practical width for the lower LSBs) so every bit shares a uniform $R_{\text{on}} C_i$ settling time constant. Size PMOS $\approx 1.3\text{–}1.5\times$ wider than NMOS (depending on process $\mu_n/\mu_p$) for balanced rise/fall transitions.
- **Vth choice:** Prefer standard-Vth devices for lower leakage and better matching on the bottom-plate reference rails.

---

## 6. Parasitic Capacitance Impact

- **Top-plate parasitic $C_p$** (switch drain junctions + top-plate routing + comparator input capacitance): attenuates all DAC steps uniformly by $C_{\text{tot}} / (C_{\text{tot}} + C_p)$. Linear fixed $C_p$ causes a gain/full-scale reduction (not INL), whereas **voltage-dependent** junction/gate capacitance on `VTOP` creates harmonic distortion and INL. Keep $C_{\text{tot}} \gg C_p$ and shield top-plate routing cleanly.
- **Bottom-plate parasitic:** Driven by low-impedance DAC switches, so bottom-plate-to-substrate capacitance slows settling slightly and increases switching power, but does **not** alter the final settled charge ratio on `VTOP` (provided settling completes). Cross-coupling capacitance directly from bottom plates to the top plate *does* alter individual bit weights and must be extracted and verified post-layout.

---

## 7. Design Checklist

| Item | Guideline |
|---|---|
| Total capacitance $C_{\text{tot}}$ | Satisfy both differential $kT/C$ noise and mismatch $\sigma_u / C_u$ budgets |
| Unit cell & layout | Parallel identical unit cells in common-centroid layout + perimeter dummies |
| Sampling switch | Standard-Vth NMOS driven by `VGBTS = VIN + VDD`; $R_{\text{on}} C_{\text{tot}} \ll T_{\text{sample}} / 5$ |
| Feedthrough dummy | Match sampling switch on `VTOP`–`VINB` with gate tied off (`VSS`) |
| DAC switches | Standard-Vth CMOS inverter-style drivers; width scaled with bit weight; PMOS $\sim 1.3\text{–}1.5\times$ NMOS |
| Top-plate parasitic | Minimize $C_p / C_{\text{tot}}$; verify extracted bit weights post-layout |

---

## How to Verify a CDAC

### 1. Static Linearity (DNL / INL)

- Drive all $2^N$ codes (or all key major-carry transitions for $N > 10$) using ideal switches/control, wait for full settling at each code, and record settled $V_{\text{top,p}} - V_{\text{top,n}}$.
- Compute actual steps `step[k] = Vdiff[k] - Vdiff[k-1]`, endpoint ideal LSB `(Vdiff_max - Vdiff_min) / (2^N - 1)`, `DNL[k] = step[k]/LSB - 1`, and cumulative `INL`.
- **Pass criteria:** $|\text{DNL}| < 0.5\text{ LSB}$ and $|\text{INL}| < 1\text{ LSB}$ (tighter pre-layout to leave margin for mismatch and extracted parasitics).

### 2. Per-Bit Settling Time

- Toggle each bit individually (especially MSB and MSB−1) in both directions (`VREFN → VREFP` and `VREFP → VREFN`) with `maxstep` $\le 5\text{ ps}$.
- Measure time to settle within $0.5\text{ LSB}$ (or within redundancy tolerance for sub-radix-2).
- **Pass criterion:** Settling time $<$ async loop delay (or $<$ one sync bit-clock slot) with corner margin.

### 3. Sampling Pedestal & Feedthrough Cancellation

- Open the sampling switch while holding differential inputs at several DC levels and measure the jump on `VTOPP`, `VTOPN`, and `VTOPP - VTOPN`.
- In hold mode, apply a fast sine on `VIP`/`VIN` and verify that the dummy switch keeps differential feedthrough onto `VTOPP - VTOPN` well below 0.5 LSB.

### 4. Total & Per-Bit Extracted Capacitance (DC + AC)

```spectre
// Tie all bottom plates to AC ground (0) and drive VTOP with a 1 V AC source
V_TOP (vtop 0) vsource dc=vdd/2 mag=1 type=dc
dcOp dc
ac ac start=1M stop=10G
save V_TOP:p
```

Extract $C_{\text{tot,eff}} = |I_{\text{ac}}| / (2\pi f \cdot V_{\text{ac}})$ in the flat mid-band region. Repeat by driving one bottom plate with AC while grounding all other bottom plates and `VTOP` (measuring current into `VTOP`) to extract exact per-bit coupling weights and verify ratios against the intended binary or sub-radix-2 weights.
