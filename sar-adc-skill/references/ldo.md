# LDO Theory Reference for SAR ADC Power Delivery

A low-dropout (LDO) linear regulator sits between the raw supply and the SAR ADC's analog domain to decouple digital switching noise from sensitive circuitry. The SAR ADC presents an unusually demanding load: the CDAC switches charge in bursts at every bit-cycle, creating a periodic high-frequency current demand that rides on top of a near-static average. Without a clean, low-impedance supply, this burst current modulates VOUT and couples through the reference and supply rails of the comparator and CDAC, directly degrading ENOB. An LDO provides the high PSRR and low output impedance needed to absorb these transients without allowing supply noise to corrupt the conversion result.

---

## Why the SAR ADC Needs a Clean Supply

### PSRR Budget

Every millivolt of supply ripple that reaches VOUT appears as an equivalent input error. For an N-bit ADC with full-scale range VFS the 1-LSB threshold is VFS / 2^N. A 10-bit, 1 V full-scale converter has 1 LSB ≈ 1 mV; any supply coupling larger than half an LSB degrades linearity. The LDO must therefore provide enough PSRR at the frequencies where supply noise exists to keep the coupled error below ~0.5 LSB.

At the Nyquist frequency (fs/2) the PSRR requirement is tightest because comparator kickback and CDAC switching inject energy there. A practical target is PSRR ≥ 40–60 dB at fs/2, with the exact value set by the system noise budget allocated to supply coupling.

### Reference Noise Coupling

The voltage reference and the LDO output often share a common rail or are generated from the same supply. High-frequency noise on VREF directly sets the noise floor of the ADC. The LDO's output impedance determines how much CDAC switching current (which flows through the reference network) translates into VREF ripple.

### Digital Switching Noise

SAR logic toggles synchronously, causing supply current spikes at the clock frequency and its harmonics. These spikes appear as deterministic tones in the ADC output spectrum. The LDO, together with decoupling capacitors, must attenuate these tones to below the noise floor. The burst profile of CDAC switching — large current at the start of each bit-trial, tapering off — also demands low output impedance over a wide bandwidth so that the voltage droop during a burst remains below the PSRR budget allocation.

---

## Circuit Topology

PMOS-pass LDO with Miller-compensated two-stage error amplifier:

```
VIN ──► M2 (pass, PMOS) ──────────────────────────► VOUT
              ▲ gate = net3                              │
              │                                  R0 (R_FB_TOP)
         ┌────┴───────────────────────────┐           │
         │      Error Amplifier           │      net30 (V_fb)
         │                                │           │
         │  M3/M4 (PMOS current mirror)   │      R1 (R_FB_BOT)
         │     ▲             ▲            │           │
         │   M0(VREF)    M1(V_fb)  ←──── ┘          GND
         │   NMOS diff pair (non-inv / inv)
         │        │
         │   M5 (tail mirror, N×) ─── M6 (diode ref, 1×) ←── I_bias
         └────────────────────────────────────────────────────────────
Compensation: Rz + Cc from net3 → VOUT
  → introduces left-half-plane zero: fz = 1/(2π·Rz·Cc)
Output decoupling: CL on VOUT
```

**Topology constraints:**
- M0 = M1: identical sizes — matched differential pair
- M3 = M4: identical sizes — matched current mirror load
- M5 / M6: same L, W_M5 = N × W_M6 (mirror ratio N, default N = 10)

The feedback divider sets the regulated output voltage:

```
Vout = Vref × (R0 + R1) / R1
```

---

## Transistor Role Table

| Device | Type | Role | Key sizing lever |
|--------|------|------|-----------------|
| M0 | NMOS | Non-inverting input of diff pair (connects to VREF) | Long L for high gm·ro and matching |
| M1 | NMOS | Inverting input of diff pair (connects to V_fb) | Must match M0 exactly |
| M3 | PMOS | Current mirror load, output branch | Long L for high ro (high Av1) |
| M4 | PMOS | Current mirror load, diode-connected reference | Must match M3; sets Av1 via ro3∥ro4 |
| M5 | NMOS | Tail current mirror, scaled branch (N×) | Same L as M6; multiplier sets I_tail |
| M6 | NMOS | Tail bias reference, diode-connected (1×) | Long L reduces current mismatch |
| M2 | PMOS | Pass device — carries full load current | Wide W for low Vdrop; size sets Vout accuracy |
| Cc | — | Miller compensation capacitor | Sets GBW and dominant pole |
| Rz | — | Series compensation resistor | Places LHP zero to cancel ωp2 effect |

---

## Initial Sizing Methodology

Given user specs: **Vref**, **Vin**, **Vout**, **Iload**, **Cload**.

### Step 1 — Feedback Resistors R0, R1

From the regulation condition:

```
R0 / R1 = Vout/Vref − 1

Select I_div = 1% × Iload   (current through divider)
→ R0 + R1 = Vout / I_div
→ R1 = Vref / I_div
→ R0 = (Vout − Vref) / I_div
```

### Step 2 — Pass Transistor M2 (PMOS)

M2 must supply the full Iload with a small drain-source voltage (low dropout). Start with minimum L for lowest Vdrop, then scale total W to achieve sufficient gm2 and the required Vout accuracy. Increase the multiplier (number of parallel fingers) until DC output voltage is within ±1% of target.

**DC iteration rule**: if Vout_sim < 0.99 × Vout_target, increase M2 multiplier; if Vout_sim > 1.01 × Vout_target, decrease it.

### Step 3 — Bias Current Mirror M5 / M6 (NMOS)

```
Ibias = Iload / 1000          (e.g. 100 µA for Iload = 100 mA)
I_tail = Ibias × N_mirror     (default N = 10)
```

Use a long L for M6 to reduce current mismatch from channel-length modulation (ΔI/I ∝ 1/L).

### Step 4 — Differential Pair M0 / M1 (NMOS, matched)

Use a long L (≥ 2× Lmin) for high intrinsic gain (gm·ro) and good matching. This directly determines offset, noise, and regulation accuracy.

### Step 5 — Current Mirror Load M3 / M4 (PMOS, matched)

Use a very long L (≥ 4× Lmin) for high ro, which maximises first-stage gain Av1 = gm1 × (ro1 ∥ ro3). High Av1 is the primary driver of loop gain and therefore load regulation.

### Step 6 — Compensation Network

```
Cc (initial) ≈ Cload / 5000
Rz: choose so that ωz ≈ GBW
```

The zero at ωz = 1/(Rz · Cc) should approximately cancel the phase loss from the output pole ωp2 at the gain crossover frequency.

---

## Theoretical Formulas

### Key Small-Signal Quantities

```
β   = R1 / (R0 + R1) = Vref / Vout        (feedback factor)
Av1 = gm1 × (ro1 ∥ ro3)                   (error-amp first-stage DC gain)
gm  = √(2 · µ · Cox · (W/L) · Id)         → increase via W; reduce Id to lower noise
ro  ∝ 1 / (λ · Id)                        → increase via longer L
```

### Loop Gain and GBW

**DC loop gain:**
```
T0 = β × Av1 × gm2 × ro2
```

**Gain-bandwidth product:**
```
GBW ≈ β × gm1 / Cc
```

### Poles and Zero

| Frequency | Expression | Notes |
|-----------|-----------|-------|
| ωp1 (dominant) | ≈ 1 / (T0 · ro2 · CL) | Set by CL and loop gain; very low frequency |
| ωp2 (output) | ≈ gm2 / CL | Push out by increasing gm2 or reducing CL |
| ωz (compensation zero) | ≈ −1 / [(Rz − 1/gm2) · Cc] | Place near GBW to recover phase |
| ωp3 (parasitic) | ≈ −1 / (Rz · CS) | Target ωp3 ≥ 2 × GBW |

where `CS = (Cn · Cc · CL) / (Cn · Cc + Cn · CL + Cc · CL)` and Cn is the gate capacitance of M2.

**Stability target:** ωz ≈ GBW and ωp3 ≥ 2 × GBW, giving phase margin ≥ 45–60°.

### Load Regulation

Output impedance determines how much Vout shifts with load current:

```
Zout(s) ≈ (1 + s · Cc · (ro1 ∥ ro3)) / (β · Av1 · gm2)
```

At DC, Zout → 1 / (β · Av1 · gm2), so high loop gain minimises the static output error.

### Line Regulation

How much Vout shifts with Vin variation:

```
ΔVout / ΔVin ≈ 1 / (β · Av1 · gm2 · ro2)
```

High loop gain and high pass-device output resistance ro2 improve line regulation. At high frequencies the error amplifier cannot respond fast enough, and line regulation degrades.

---

## PSRR: Formula and Intuition

```
PSRR(s) ≈ [gm2 · (ro1 ∥ ro3) · s · Cc + 1/ro2] / (β · Av1 · gm2)
```

**DC PSRR** is dominated by the loop gain: PSRR(0) ≈ T0 / (gm2 · ro2). High Av1 and high gm2 improve DC PSRR.

**High-frequency PSRR degradation** is caused by the pass device M2. At frequencies above the loop gain bandwidth, the error amplifier can no longer actively correct for supply variation. VIN couples directly to VOUT through M2's drain-source channel and gate-drain capacitance Cgd2. Because M2 is a common-source stage with its gate driven by a slow error amp at high frequencies, it behaves like a low-resistance path between VIN and VOUT with approximately:

```
PSRR_HF ≈ gm2 · ro2 / (1 + gm2 · ro2)  →  close to unity (0 dB) at very high f
```

In practice, the output decoupling capacitor CL provides a low-impedance path to ground at high frequencies and partially restores PSRR, but the fundamental limit comes from the pass device. This is why active supply pre-regulation or cascode pass devices are used in high-PSRR designs.

**Tuning PSRR:**

| Action | Effect |
|--------|--------|
| ↑ Av1 (↑W1 or ↓L1) | ↑ DC PSRR |
| ↑ gm2 (↑W2) | ↑ DC PSRR |
| ↑ ro2 (↑L2) | ↑ DC PSRR |
| ↑ Cc | ↑ mid-frequency PSRR (trades against load regulation at high freq) |

---

## Noise Referred to Output

### Thermal Noise

```
Vn²_out = (1/β²) × [4kT(R0 ∥ R1) + 8kTγ · (gm1 + gm4) / gm1²]
```

The first term is resistor divider noise; the second is transistor channel noise from the differential pair (M0/M1) and mirror load (M3/M4). Both are divided by β², so a larger feedback factor (output closer to Vref) reduces referred noise.

### Flicker (1/f) Noise

```
Vn²_out = (2K / β² · Cox · f) × [1/(W1 · L1) + (1/(W4 · L4)) · (gm4/gm1)²]
        ≈ (2K / β² · Cox · f) × [1/(W1 · L1) + µp · L1 / (µn · W1 · L4²)]
```

Flicker noise dominates at low frequencies. Increasing the area of the differential pair (W1 · L1) and mirror load (W4 · L4) reduces it. The crossover from 1/f to thermal noise defines the 1/f corner frequency.

### Noise Optimization

| Frequency range | Primary actions |
|-----------------|----------------|
| Low freq (1/f dominant) | ↑ W1 (best with L1 also ↑ proportionally); ↑ L4 |
| High freq (thermal dominant) | ↑ gm1 (↑W1); ↓ gm4 (↓W4 or ↑L4) |

---

## Compensation Trade-off: Cc vs Phase Margin vs Output Pole

The Miller capacitor Cc creates the dominant pole at ωp1 ≈ GBW/T0 (very low frequency) and sets the gain crossover at GBW ≈ β · gm1 / Cc.

| Adjustment | PM | PSRR | Load Reg (HF) | GBW |
|------------|----|----|----|----|
| ↑ Cc | ↑ (GBW↓, more phase margin) | ↓ (high-freq rejection worsens) | ↓ | ↓ |
| ↓ Cc | ↓ | ↑ | ↑ | ↑ |
| ↑ Rz | Move ωz toward GBW (corrects PM) | Marginal effect | Minor | — |
| ↓ Rz | ωz moves away from GBW | — | — | — |

The key insight is that Cc creates a trade-off between stability (larger Cc) and high-frequency rejection (smaller Cc). The compensation zero from Rz cancels the phase loss caused by ωp2 without moving the gain crossover, so tuning Rz is the primary tool for phase margin adjustment once Cc is set.

Output pole ωp2 ≈ gm2/CL moves with both the pass device transconductance and the load capacitance. A larger CL (heavier decoupling) pushes ωp2 inward, making stability harder and requiring either more Cc or a higher gm2.

---

## Trade-off Table: Tuning Each Device

| Adjustment | Improves | Degrades |
|-----------|----------|---------|
| ↑ W1 (diff pair wider) | Load reg (LF+HF), Line reg, PSRR, Noise, Offset | PM (GBW↑ → less phase margin) |
| ↓ L1 (diff pair shorter) | gm1↑, Load reg (LF), Line reg (LF) | gm·ro↓ (Av1↓), 1/f noise↑, Offset |
| ↑ W2 (pass transistor wider) | Output accuracy, Load/Line reg, PSRR | ωp3↓ (Cgg2↑ → PM↓) |
| ↓ W2 and ↓ L2 (same ratio) | ωp3↑ (PM↑) | gm2↓ (regulation↓) |
| ↑ L4 (load mirror longer) | Av1↑, 1/f noise↓, Offset, PSRR | Speed (pole at mirror node slows) |
| ↑ Cc | PM (GBW↓) | PSRR (↓), Load reg (HF↓) |
| ↓ Cc | PSRR, Load reg (HF) | PM↓ |
| ↑ Rz | ωz↑ → adjust PM correction | ωp3↓ (through CS path) |
| ↓ Rz | ωp3↑ | ωz↓ → may lose PM correction |

**Decision rule:** identify the spec with the least margin, then select the adjustment that improves it without pushing a near-failing spec into violation.

---

## Context for SAR ADC Use

### Required PSRR at fs/2

For a 10-bit SAR ADC with fs = 100 MS/s and VFS = 1 V, the target at fs/2 = 50 MHz is:

- 1 LSB ≈ 1 mV
- Supply noise budget ≈ 0.5 LSB ≈ 0.5 mV (allowing 6 dB margin)
- If board-level supply has 10 mV ripple at 50 MHz: PSRR ≥ 26 dB minimum, ≥ 40 dB with guard-band

In practice, 40–60 dB PSRR at fs/2 is a common design target. At DC and low frequencies the loop gain provides 60–80 dB, degrading toward 0 dB at frequencies well above the LDO bandwidth (~1–10 MHz for a typical LDO). The output CL provides additional attenuation beyond the LDO bandwidth.

### Burst Current from CDAC Switching

At the start of each bit-trial the SAR switches a subset of CDAC capacitors, injecting a charge packet into VOUT. The current pulse has:

- **Amplitude**: proportional to CDAC total capacitance × VLSB / τ_switch, where τ_switch is the switch on-time (nanosecond scale)
- **Duration**: one bit-cycle (1/(N · fs) for synchronous SAR)
- **Repetition**: fs for the largest cap switch (MSB), faster for lower bits in asynchronous architectures

The LDO must supply this burst without allowing VOUT to droop by more than ~0.5 LSB. The output impedance Zout at the switching frequency directly sets the droop:

```
ΔVout ≈ ΔI_burst × Zout(f_switch)
```

For a 10-bit, 100 MS/s SAR with 1 pF CDAC and 1 V swing, ΔI_burst ≈ 100 µA; requiring ΔVout < 0.5 mV demands Zout < 5 Ω at the switching frequency. This is achievable with a large CL and a fast error amplifier, but it requires careful co-design of the LDO bandwidth and decoupling capacitor placement.

An on-chip decoupling capacitor placed directly at the CDAC supply node reduces the effective impedance seen by the burst current and relaxes the LDO transient requirement.
