# CDAC (Capacitive DAC) Design Reference

The charge-redistribution CDAC is the core analog engine of a SAR ADC. It performs three functions in a single structure: sampling the input signal, storing the conversion residue, and implementing the DAC feedback. This eliminates the need for a separate sample-and-hold circuit and an explicit DAC — the capacitor array does it all. Understanding the CDAC is essential for achieving target resolution, noise floor, and linearity.

---

## 1. Charge Redistribution Principle

A charge-redistribution CDAC works by sampling the input voltage onto a capacitor array with a floating top plate, then selectively reconnecting bottom plates to reference voltages to perform binary search.

### Sampling Phase

During sampling, the top plate is connected to the input through a sampling switch, and all bottom plates are connected to a known voltage (typically VREFP for the positive side). Charge is stored on each capacitor:

```
Q_i = C_i × (VIN - VREFP)
```

When the sampling switch opens, the total charge on the top plate is frozen:

```
Q_total = Ctotal × (VIN - VREFP)
```

### Redistribution Phase

After sampling, bottom plates are selectively switched between VREFP and VREFN. Because charge is conserved on the floating top plate:

```
VTOP = VIN + VREFP - Vref × D / 2^N
```

where D is the decimal value of the digital code applied, Vref = VREFP - VREFN, and N is the number of bits. The comparator observes VTOP to decide each bit.

### Differential Operation

In a fully differential SAR ADC, two matched CDACs operate with complementary initial conditions:

```
P-side:  all bottom plates = VREFP  →  VTOPP = VIP + VREFP - Vref × DP / 2^N
N-side:  all bottom plates = VREFN  (equivalently, all DCTRL = HIGH)
         Actually: VTOPN = VIN + VREFP - Vref × DN / 2^N
```

With complementary codes (DN[i] = 1 - DP[i]), the differential step per bit is:

```
VTOPP - VTOPN = (VIP - VIN) - 2 × Vref × Ci / Ctotal
```

This doubles the effective signal swing compared to single-ended operation.

---

## 2. Capacitor Array Architectures

### Binary-Weighted Array

The simplest architecture: bit i has capacitance 2^i times the unit capacitor Cu. For an N-bit converter with bits 1 through N (bit N = MSB):

```
C_MSB = 2^(N-1) × Cu
C_LSB = 1 × Cu
C_dummy = 1 × Cu  (bottom plate tied to VREFP permanently)
Ctotal = 2^N × Cu  (including dummy)
```

Advantages: straightforward layout, one capacitor per bit weight. Disadvantage: the MSB capacitor is 2^(N-1) times the unit cap, which becomes impractical for high resolution (e.g., 14-bit requires 8192 Cu).

### Segmented (Split-Capacitor) Array

For resolution above 10 bits, the MSB portion can be implemented with a sub-DAC and attenuation capacitor, reducing the total capacitor count. The tradeoff is added complexity and a parasitic-sensitive bridge node.

### Reference Design Example: SAR_11B_ZZS Cap Array (L5_CAP_ARRAY)

The 11-bit ZZS design uses a binary-weighted array with bits 1 through 11, plus a dummy capacitor (I0). The unit cells come in two flavors:

| Cell | Capacitance | Construction |
|------|------------|--------------|
| LB_CUNIT_X1 | 200 aF | Single cap (C0, 200 aF) |
| LB_CUNIT_X3 | 600 aF (3 x 200 aF) | Three parallel caps (C0, C1, C2 = 200 aF each) |

The X3 unit cell uses three parallel unit caps for improved matching via averaging of random mismatch. This is a common technique: instead of one 600 aF cap, three 200 aF caps in parallel provide sqrt(3) better matching.

**Bit-to-capacitor mapping:**

| Bit | Instance | Type | Count | Total Cap |
|-----|----------|------|-------|-----------|
| Dummy | I0 | LB_CUNIT_X1 | 1 | 200 aF |
| 1 (LSB) | I1 | LB_CUNIT_X1 | 1 | 200 aF |
| 2 | I2<2:1> | LB_CUNIT_X1 | 2 | 400 aF |
| 3 | I3 | LB_CUNIT_X3 | 1 | 600 aF |
| 4 | I4<2:1> | LB_CUNIT_X3 | 2 | 1.2 fF |
| 5 | I5<4:1> | LB_CUNIT_X3 | 4 | 2.4 fF |
| 6 | I6<7:1> | LB_CUNIT_X3 | 7 | 4.2 fF |
| 7 | I7<14:1> | LB_CUNIT_X3 | 14 | 8.4 fF |
| 8 | I8<26:1> | LB_CUNIT_X3 | 26 | 15.6 fF |
| 9 | I9<48:1> | LB_CUNIT_X3 | 48 | 28.8 fF |
| 10 | I10<90:1> | LB_CUNIT_X3 | 90 | 54.0 fF |
| 11 (MSB) | I11<167:1> | LB_CUNIT_X3 | 167 | 100.2 fF |
| (dummy caps) | I12<9:1> | LB_CUNIT_X3 | 9 | 5.4 fF (to net2, unused) |

Note: the instance counts for bits 3-11 use X3 units. For bit 3: 1 X3 = 3 Cu = 600 aF. For bit 11 (MSB): 167 X3 = 501 Cu. The ideal binary weight for bit 11 would be 2^10 = 1024 Cu, but using X3 cells: 1024/3 = 341.3, so the actual count of 167 suggests either a smaller Cu multiplier or a different total normalization. The CDF parameter `Cunit="3.3f"` at the L4_CDAC level is the total unit capacitance parameter passed to simulation.

The dummy capacitor I0 has its bottom plate permanently connected to VREFP. The additional dummy instances I12<9:1> have their bottom plates connected to floating nets (net2<0:8>, via noConn), serving as layout fill for matching symmetry.

---

## 3. Unit Capacitor Sizing

### kT/C Noise Floor

The fundamental noise limit of a sampling capacitor is:

```
Vn_rms = sqrt(kT / C)
```

For an N-bit ADC with full-scale range Vfs, the LSB is Vfs/2^N. The noise must be well below 1 LSB:

```
sqrt(kT / C) < Vfs / (2^N × K)
```

where K is typically 4-6 for adequate noise margin. Solving for C:

```
C > K^2 × kT × 2^(2N) / Vfs^2
```

For 11 bits, VDD = 0.9V, T = 300K, K = 4: C > 16 × 4.14e-21 × 4.19e6 / 0.81 = 0.34 fF. The ZZS design uses Cu = 200 aF with total array cap much larger than this minimum, providing comfortable noise margin.

### Matching Requirements

Capacitor mismatch limits DNL. For an N-bit DAC, the MSB capacitor matching must satisfy:

```
sigma(C_MSB) / C_MSB < 1 / (2^N × sqrt(2))
```

Using parallel unit cells (e.g., X3 construction) and common-centroid layout improves matching. The X3 cell in ZZS achieves better matching than a single larger cap by averaging three independent unit cells.

---

## 4. Sampling Switch Design

### Why Bootstrap Gate Voltage Drives Internal NMOS

A critical architectural decision: the bootstrap circuit does NOT output a sampled voltage. It outputs a gate voltage VGBTS = VIN + VDD that drives an NMOS sampling switch internal to the CDAC. The input signal VIN connects directly to the NMOS source.

```
CDAC ports:
  VIN   → M3 source (sampling NMOS)
  VGBTS → M3 gate   (bootstrap output)
  VTOP  → M3 drain  (connects to cap array top plate)
```

This ensures constant Vgs = VDD across the full input range, eliminating signal-dependent Ron and achieving linearity beyond 10 bits.

### Reference Design: L4_CDAC Sampling Switch

The ZZS CDAC (L4_CDAC) contains two NMOS switches at the transistor level:

| Transistor | Type | Gate | Drain | Source | Role | W | L | Fingers |
|-----------|------|------|-------|--------|------|---|---|---------|
| M3 | nch_mac | VGBTS | VTOP | VIN | Main sampling switch | 5u | 30n | 10 |
| M4 | nch_mac | net1 | VTOP | VINB | Dummy switch (charge cancel) | 5u | 30n | 10 |

Both use `nch_mac` (standard Vth), not `nch_ulvt_mac`. Standard Vth provides better matching and lower leakage compared to ultra-low Vth, which matters for charge retention on the top plate during conversion.

### Dummy Switch for Differential Charge Cancellation

M4 is the dummy switch: same size as M3, with its source connected to VINB (the complementary input). Its gate is driven by net1, which is generated by a cascode structure (M2 + M5):

```
M5: nch_ulvt_mac, G=VDD, D=net2, S=VSS  (W=4u, L=30n, NF=8)
M2: nch_ulvt_mac, G=VDD, D=net1, S=net2  (W=4u, L=30n, NF=8)
```

M2 and M5 form a cascode with gates tied to VDD. This generates a controlled gate voltage (net1) for M4 that tracks approximately VDD/2 to mid-rail, ensuring M4 is in a similar operating region as M3 during transitions. When the sampling switch M3 turns off, its charge injection error is partially cancelled by M4's complementary charge injection (since VINB moves opposite to VIN in differential operation).

---

## 5. Bottom-Plate DAC Switches (L5_DAC_SWI)

### Complementary Pass Gate Topology

Each bit uses one NMOS and one PMOS transistor sharing the same DCTRL gate signal:

```
         VREFP
           |
    M_pmos: G = DCTRL[i], S = VREFP, D = VBOT[i]
           |
    ────── VBOT[i] ──────
           |
    M_nmos: G = DCTRL[i], S = VREFN, D = VBOT[i]
           |
         VREFN
```

| DCTRL | PMOS (Vgs) | NMOS (Vgs) | VBOT | Notes |
|-------|-----------|-----------|------|-------|
| LOW (0) | ON (Vgs = -VDD) | OFF | VREFP | Initial/sample state |
| HIGH (VDD) | OFF | ON (Vgs = +VDD) | VREFN | Bit set -> VTOP decreases |

No inverter is needed because the same DCTRL signal naturally turns on complementary devices.

### Switch Sizing: Width Scales with Bit Weight

The switch width scales proportionally to the capacitance it drives, maintaining matched RC time constants across all bits. This ensures uniform settling time.

**Reference design switch sizing (L5_DAC_SWI):**

| Bit | NMOS W | NMOS NF | PMOS W | PMOS NF | Cap Weight |
|-----|--------|---------|--------|---------|------------|
| 11 (MSB) | 6.4u | 16 | 8.32u | 16 | 1024 Cu |
| 10 | 3.2u | 8 | 4.16u | 8 | 512 Cu |
| 9 | 1.6u | 4 | 2.08u | 4 | 256 Cu |
| 8 | 800n | 2 | 1.04u | 2 | 128 Cu |
| 7 | 400n | 1 | 520n | 1 | 64 Cu |
| 6-1 | 200n | 1 | 260n | 1 | 32-1 Cu |

The PMOS is approximately 1.3x wider than the NMOS to compensate for lower hole mobility, achieving matched pull-up and pull-down times.

The switches use `nch_mac` / `pch_mac` (standard Vth) rather than ultra-low Vth. This provides better matching and lower leakage on the bottom plates, which is important because leakage during conversion corrupts the stored charge.

---

## 6. Initial State and Conversion Flow

### Differential Initial Conditions

At the start of conversion (CLKS falls), the SAR logic resets all DAC switches:

```
P-side (I_CDACP):
  All DCTRLP = LOW  →  all VBOTP = VREFP
  
N-side (I_CDACN):
  All DCTRLN = HIGH →  all VBOTN = VREFN
```

This establishes the starting voltage on the top plates. After sampling:

```
VTOPP = VIP  (since all bottom plates = VREFP, same as during sampling)
VTOPN = VIN  (since all bottom plates = VREFN, fully switched from sampling state)
```

Wait -- the actual initial state depends on the implementation. In ZZS, the initial reset forces all DCTRLP = LOW (VBOTP = VREFP) and all DCTRLN = LOW (VBOTN = VREFP). But the complementary operation means that when DCTRLP goes HIGH to set a bit on the P-side, the corresponding DCTRLN stays LOW (or vice versa), creating the differential feedback.

### Bit Trial Sequence

For each bit i from MSB to LSB:

1. **Preset**: Set DCTRLP[i] = HIGH (VBOTP[i] = VREFN), DCTRLN[i] = LOW (VBOTN[i] = VREFP)
2. **Compare**: Fire comparator, observe VTOPP vs VTOPN
3. **Decide**: If VTOPP > VTOPN, keep the bit (DCTRLP[i] stays HIGH). If VTOPP < VTOPN, clear the bit (DCTRLP[i] = LOW, restore VBOTP[i] = VREFP).

---

## 7. Parasitic Capacitance Impact

### Top-Plate Parasitic

The top plate accumulates parasitic capacitance from:
- Sampling switch drain junction (M3, M4)
- Cap array top-plate wiring
- Comparator input gate capacitance

This parasitic Cp adds to the total capacitance seen at VTOP:

```
VTOP_actual = VIN + (Ctotal / (Ctotal + Cp)) × (VREFP - Vref × D / 2^N - VREFP)
```

The factor Ctotal/(Ctotal+Cp) attenuates the DAC step size, effectively reducing the full-scale range. If Cp is a significant fraction of Ctotal, the bit weights are no longer binary, causing INL errors.

### Bottom-Plate Parasitic

Bottom-plate parasitics from switch junctions and wiring add to each bit's capacitance. Since they scale with switch size (which scales with bit weight), the relative error is approximately constant across bits and does not significantly impact linearity.

### Mitigation

- Make Ctotal >> Cp (use sufficiently large unit capacitors)
- In the ZZS comparator, input caps C9 and C10 (5 fF each) are explicitly shown, representing the expected loading
- Layout: minimize top-plate routing, use metal shields between top-plate and bottom-plate wiring

---

## 8. Design Checklist

| Item | Guideline |
|------|-----------|
| Unit cap size | Set by kT/C noise and matching, not by area alone |
| Unit cell construction | Use parallel sub-units (e.g., X3) for matching improvement |
| Sampling switch Vth | Standard Vth (nch_mac), not ultra-low Vth |
| Sampling switch W/L | Large enough for adequate settling (Ron x Csample << Tsample/5) |
| Dummy switch | Match sampling switch exactly; gate driven by cascode |
| DAC switch type | Standard Vth (nch_mac / pch_mac) for matching and low leakage |
| DAC switch scaling | Width proportional to bit weight; PMOS ~1.3x NMOS |
| Dummy cap | One unit cap with bottom plate permanently on VREFP |
| Top-plate parasitic | Must be << Ctotal; verify with extracted layout |
| VGBTS connection | Bootstrap GATE output only; VIN goes directly to switch source |

---

## How to Verify a CDAC

### Static Linearity (DNL/INL)

The most critical CDAC test — verifies that all bit weights are correct.

- Apply all 2^N codes sequentially by driving the bottom-plate switches with an ideal SAR controller (Verilog-A behavioral logic works well here).
- At each code, wait for VTOP to settle completely, then measure the DC voltage.
- Compute the actual step size at each code transition: `step[i] = VTOP[i] - VTOP[i-1]`.
- Compute the ideal LSB: `LSB_ideal = (VTOP_max - VTOP_min) / (2^N - 1)`.
- DNL = `(step_actual / LSB_ideal) - 1` at each code.
- INL = cumulative sum of DNL (endpoint fit).
- Pass criteria: |DNL| < 0.5 LSB and |INL| < 1 LSB across all codes.
- Alternative approach: apply a slow ramp input and use a behavioral SAR to generate codes automatically — this tests the CDAC in a more realistic operating context.
- For large arrays (> 10 bits), focus detailed checking on the MSB and MSB-1 transitions where mismatch has the largest absolute impact.

### Settling Time Per Bit

Each bit decision in the SAR loop requires the CDAC to settle before the comparator fires.

- Switch one bit at a time (e.g., toggle DCTRL from LOW to HIGH), and measure the time for VTOP to settle within 0.5 LSB of its final value.
- The MSB settles slowest because it has the largest capacitor and produces the largest voltage step on VTOP.
- Settling time must be less than one SAR bit-clock period (for sync SAR) or less than the async loop delay (for async SAR).
- Test both rising (VREFN to VREFP) and falling (VREFP to VREFN) transitions — they may have different settling times due to asymmetric switch Ron (NMOS vs. PMOS pull paths).
- Use transient analysis with `maxstep` set small enough (< 5 ps) to resolve the settling tail.

### Charge Injection and Clock Feedthrough

When the sampling switch opens, channel charge splits between the source and drain, creating a voltage error on VTOP.

- Measure the VTOP change (pedestal) at the moment VGBTS goes low (switch opens).
- For single-ended operation: this pedestal is signal-dependent and directly limits achievable ENOB.
- For differential operation: verify that the common-mode injection cancels — the pedestal on VTOPP should approximately equal the pedestal on VTOPN (within 0.5 LSB).
- The residual differential pedestal after cancellation sets the effective offset of the CDAC, which the SAR loop can tolerate as long as it is less than 0.5 LSB.

### Parasitic Capacitance Impact on Bit Weights

Top-plate parasitic capacitance attenuates all DAC steps uniformly, but bottom-plate and routing parasitics can change individual bit weights.

- Compare actual bit weights (measured VTOP step sizes from the DNL test) against ideal binary weights.
- Compute the weight error for each bit: `error[i] = actual_weight[i] / ideal_weight[i] - 1`.
- If the weight error exceeds 0.5 LSB at any bit, the ADC will have missing codes at that transition.
- Parasitic impact is worst for lower bits (where the unit capacitor is smallest relative to the parasitic).
- Mitigation: increase Cu, use shielded routing, or apply digital calibration post-silicon.

### Total Capacitance Measurement (DC + AC)

Verify the actual total CDAC capacitance (including parasitics) using a simple DC + AC simulation. This catches routing parasitic and fringe capacitance that the schematic doesn't show.

**Testbench:**
```
// Connect all bottom plates to VSS, measure current into VTOP
V_TOP (vtop 0) vsource dc=VDD/2 mag=1 type=dc    // DC bias + AC stimulus
V_BOT (vss 0) vsource dc=0 type=dc

// Connect all CDAC bottom plates to VSS
// (set all CTRL = HIGH so NMOS switches connect to VREFN = VSS)

dcOp dc                          // DC operating point
ac ac start=1M stop=10G          // AC sweep

save V_TOP:1                     // save current into top plate
```

**Extraction:** At each frequency, `C_total = I_ac / (2π × f × V_ac)`. The capacitance should be flat across frequency (until self-resonance) and match the designed value `(2^N + 1) × Cu`. Any deviation reveals parasitic capacitance from switches, routing, or substrate coupling.

**Per-bit capacitance:** Repeat with only one bit's bottom plate connected to the AC source (others grounded) to measure individual bit capacitances. Compare against binary weighting ratios.
