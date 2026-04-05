# Comparator Theory Reference — StrongArm Dynamic Comparator

The StrongArm is a 9-transistor dynamic comparator that combines an integrating input stage with a cross-coupled regenerative latch, making it the dominant comparator topology in SAR ADC designs. It draws zero static current (switching only during the evaluation phase), delivers rail-to-rail output regeneration, and achieves near-kT/C noise floor — all properties that match the periodic, power-constrained operation of a successive-approximation loop. Output inverters buffer the internal latch nodes to drive the SAR logic without loading the sensitive regeneration nodes.

---

## Circuit Topology

StrongArm comparator — 9 core transistors plus output inverters.

```
Transistor  Type   Gate  Drain  Source  Role
──────────────────────────────────────────────────────────
M0          NMOS   CLK   VS     GND     Tail (evaluation switch)
M1          NMOS   INP   VXP    VS      Input pair (+)
M2          NMOS   INN   VXN    VS      Input pair (−)
M3          NMOS   VLN   VLP    VXP     NMOS latch (stacked on M1)
M4          NMOS   VLP   VLN    VXN     NMOS latch (stacked on M2)
M5          PMOS   VLN   VLP    VDD     PMOS latch (cross-coupled)
M6          PMOS   VLP   VLN    VDD     PMOS latch (cross-coupled)
M7–M10      PMOS   CLK   VX/VL  VDD     Reset (pull to VDD when CLK=0)
M11–M14     CMOS   VLP/VLN  OUTP/OUTN  Output inverters
```

**Critical connection:** M3 source = VXP (not GND). As VXP drops during integration, `Vgs_M3 = VLN − VXP` increases, so M3 turns on when VXP falls below VDD − Vth. Current path during evaluation: GND → M0 → M1 → VXP → M3 → VLP.

**Output polarity:** OUTP = NOT(VLP) = logic 1 when INP > INN.

---

## Transistor Sizing

All devices use minimum length (L = 45 nm is the reference node; scale proportionally). Widths below are the reference design values.

| Device | W (µm) | Design note |
|--------|--------|-------------|
| Tail M0 | 4.0 | Wider → faster integration; diminishing returns beyond ~4 µm |
| Input M1/M2 | 4.0 | Wider → lower noise, faster integration, but adds VX capacitance |
| NMOS latch M3/M4 | 1.0 | Wider adds drain capacitance; τ nearly flat (gm and C scale together) |
| PMOS latch M5/M6 | 2.0 | Wider → shorter τ up to ~4 µm, then saturates |
| Reset M7–M10 | 1.0 | Sets reset speed; rarely a bottleneck at GHz clock rates |
| Output inv PMOS | 2.0 | Output drive strength |
| Output inv NMOS | 1.0 | Output drive strength |

---

## Four Operating Phases

### Phase 1 — Reset (CLK = 0)

- Tail switch M0 is off; no current flows.
- Reset PMOS devices (M7–M10) pull all internal nodes (VXP, VXN, VLP, VLN) to VDD.
- Output inverters hold previous decision; outputs remain stable.

### Phase 2 — Evaluate (CLK rises, early)

- M0 turns on, connecting VS to GND.
- M1/M2 carry differential currents proportional to INP and INN.
- VXP and VXN begin to fall; the side with the larger gate voltage falls faster.
- VLP and VLN remain near VDD because M3/M4 are still weakly on (Vgs ≈ 0).

### Phase 3 — Latch (regeneration onset)

- As VXP (or VXN) drops sufficiently, the corresponding NMOS latch device (M3 or M4) enters saturation: `Vgs_M3 = VLN − VXP` grows positive.
- The cross-coupled PMOS pair M5/M6 and NMOS pair M3/M4 form a positive-feedback loop.
- The latch voltage difference ΔV = VLP − VLN grows exponentially with time constant τ = C_latch / (gm_p + gm_n).
- The side corresponding to the larger input falls to GND; the other rises back toward VDD.

### Phase 4 — Restore (CLK falls)

- M0 turns off; current ceases.
- Reset devices pull VX and VL nodes back to VDD, ready for the next cycle.
- The output inverters present a clean digital level to downstream logic throughout the entire clock period.

---

## Speed Theory

### Latch time constant

During regeneration the differential latch voltage grows as:

```
ΔV(t) = ΔV₀ · exp(t / τ)
```

where the time constant is set by the total latch node capacitance and the combined regenerative transconductance of M3–M6:

```
τ = C_latch / (gm_latn + gm_latp)
```

Smaller τ is faster. Increasing W_lat_p (M5/M6) reduces τ up to the point where drain capacitance dominates. NMOS latch width has weak influence because gm and C scale proportionally.

### Comparison time

Tcmp is defined as the time from CLK rising edge to when the output crosses the logic threshold. It has two additive components:

```
Tcmp = T_int + T_regen
```

- **T_int**: integration phase duration, set primarily by tail current (W_tail) and input pair width (W_inp).
- **T_regen**: regeneration phase duration, proportional to τ · ln(V_swing / ΔV₀); ΔV₀ is the differential voltage at latch onset.

Larger input amplitude reduces Tcmp by providing a larger ΔV₀ at the start of regeneration.

### Figure of merit

```
FOM1 = E_cycle × σ²          (energy–noise product, J·V²)
FOM2 = FOM1 × Tcmp           (energy–noise–speed product, J·V²·s)
```

Lower FOM is better. These allow fair cross-topology comparisons independent of supply voltage and clock frequency.

---

## Noise Theory

### Noise injection model

Thermal noise of the input pair and latch devices is modeled as band-limited white noise injected at the two input nodes. The noise bandwidth is set wide enough (>> clock frequency) so that the injected voltages are decorrelated between successive clock cycles — each cycle sees an independent noise draw.

### Probit extraction method

Rather than computing noise analytically, σ_n is extracted from switching statistics:

1. Apply a fixed differential input voltage Vin_fixed (much smaller than σ_n is unknown, so choose a value in the transition region).
2. Run N clock cycles and count P₁ = fraction of cycles where OUTP = 1.
3. Invert the Gaussian CDF:

```
σ_n = Vin_fixed / Φ⁻¹(P₁)
```

where Φ⁻¹ is the inverse normal (probit) function. This single-point method is unbiased when Vin_fixed is within ±2σ_n of zero.

### Noise sources

- **Input pair M1/M2**: dominant at the moment of tail current onset; referred to input as `4kT·γ / gm_inp`.
- **Tail device M0**: common-mode noise; partially rejected by differential operation but residual appears as offset.
- **Latch M3–M6**: contribute during regeneration; effect is smaller because signal has already been amplified.

Increasing W_inp reduces input-referred noise (larger gm) at the cost of larger VX capacitance (slower integration).

---

## Offset Theory

### Systematic offset

Systematic offset arises from layout asymmetry and connection topology differences between the two signal paths. Sources include:

- Asymmetric parasitic capacitance on VXP vs VXN.
- Asymmetric interconnect resistance in the PMOS reset path.
- Body effect differences due to different substrate connections.

### Random (mismatch) offset

Random offset is dominated by threshold voltage mismatch of the input pair M1/M2:

```
σ_Vos ≈ AVt / √(W·L)
```

where AVt is the process mismatch coefficient (technology-dependent). Widening the input pair reduces random offset. The latch devices (M3–M6) contribute a secondary mismatch term that is divided by the effective gain at latch onset.

### Offset vs noise distinction

Offset is a fixed, cycle-independent shift of the comparator threshold — it causes a DC error in the SAR conversion that must be calibrated or trimmed. Noise is a cycle-to-cycle random perturbation that sets the probability of a wrong decision and limits ENOB directly via the σ_n term in the noise budget.

---

## Trade-off Table

| Action | τ (speed) | σ_n (noise) | Power | Notes |
|--------|-----------|-------------|-------|-------|
| ↑ W_tail (M0) | ↓ faster | ↓ slightly | ↑ | More integration current; returns diminish |
| ↑ W_inp (M1/M2) | mixed | ↓ lower | ↑ | Lower noise floor; extra VX cap slows onset |
| ↑ W_latn (M3/M4) | flat | negligible | ↑ small | gm and C cancel; rarely worth increasing |
| ↑ W_latp (M5/M6) | ↓ faster | negligible | ↑ | Strongest τ lever up to ~2× minimum width |
| ↑ W_reset (M7–M10) | — | — | ↑ small | Only matters if reset is incomplete before CLK rise |
| ↑ Output inv size | — | — | ↑ | Faster digital edge; no effect on analog decision |

---

## SAR_11B_ZZS Implementation Details (L4_COMPARATOR)

The following section documents the actual transistor-level implementation from the taped-out SAR_11B_ZZS design (TSMC 28nm HPC+, VDD=0.9V). This comparator is a modified StrongArm with offset trim capability, output buffers, and ESD protection.

### Complete Transistor List

The comparator contains 29 transistors, 8 capacitors, and associated pins. All NMOS/PMOS use `nch_ulvt_mac` / `pch_ulvt_mac` (ultra-low Vth for maximum speed at 0.9V), except the ESD clamps which use `nch_ehvt_mac` (extra-high Vth).

#### Core StrongArm (9 transistors)

| Transistor | Type | G | D | S | W | L | NF | Role |
|-----------|------|---|---|---|---|---|-----|------|
| M88 | nch_ulvt | CLK | VS | VSS | 2u | 30n | 4 | Tail current switch |
| M0 | nch_ulvt | VINP | VN1 | VS | 16u | 30n | 32 | Input pair (positive) |
| M1 | nch_ulvt | VINN | VP1 | VS | 16u | 30n | 32 | Input pair (negative) |
| M45 | nch_ulvt | LP | LM | VN1 | 4u | 30n | 8 | NMOS cross-couple (stacked on M0) |
| M6 | nch_ulvt | LM | LP | VP1 | 4u | 30n | 8 | NMOS cross-couple (stacked on M1) |
| M48 | pch_ulvt | LP | LM | VDD | 4u | 30n | 8 | PMOS cross-couple latch |
| M49 | pch_ulvt | LM | LP | VDD | 4u | 30n | 8 | PMOS cross-couple latch |
| M4 | pch_ulvt | CLK | VN1 | VDD | 2u | 30n | 4 | Reset (pull VN1 to VDD) |
| M5 | pch_ulvt | CLK | VP1 | VDD | 2u | 30n | 4 | Reset (pull VP1 to VDD) |

#### Reset and Latch Output (5 transistors)

| Transistor | Type | G | D | S | W | L | NF | Role |
|-----------|------|---|---|---|---|---|-----|------|
| M7 | pch_ulvt | CLK | LP | VDD | 2u | 30n | 4 | Reset LP to VDD |
| M50 | pch_ulvt | CLK | LM | VDD | 2u | 30n | 4 | Reset LM to VDD |
| M79 | pch_ulvt | CLK | LP | LM | 500n | 30n | 1 | Cross-connect reset (equalizes LP/LM) |

#### Output Buffer (DCMPP/DCMPN drivers, 8 transistors)

The latch nodes LM and LP drive output inverters to produce buffered DCMPP and DCMPN:

| Transistor | Type | G | D | S | W | L | NF | Role |
|-----------|------|---|---|---|---|---|-----|------|
| M10 | nch_ulvt | LM | net1 | VSS | 500n | 30n | 1 | Buffer NMOS (LM side) |
| M19 | pch_ulvt | LM | net1 | VDD | 500n | 30n | 1 | Buffer PMOS (LM side) |
| M106 | nch_ulvt | net1 | DCMPP | VSS | 1.5u | 30n | 3 | Output NMOS (DCMPP) |
| M78 | pch_ulvt | net1 | DCMPP | VDD | 1.5u | 30n | 3 | Output PMOS (DCMPP) |
| M16 | nch_ulvt | LP | net2 | VSS | 500n | 30n | 1 | Buffer NMOS (LP side) |
| M21 | pch_ulvt | LP | net2 | VDD | 500n | 30n | 1 | Buffer PMOS (LP side) |
| M105 | nch_ulvt | net2 | DCMPN | VSS | 1.5u | 30n | 3 | Output NMOS (DCMPN) |
| M77 | pch_ulvt | net2 | DCMPN | VDD | 1.5u | 30n | 3 | Output PMOS (DCMPN) |

Buffer chain: LM → inverter (M10+M19) → net1 → inverter (M106+M78) → DCMPP. Two inverter stages means DCMPP has the same polarity as LM. Similarly, LP → net2 → DCMPN.

#### Output Polarity (Critical)

During reset (CLK=low), M4/M5/M7/M50 pull VN1, VP1, LP, LM all to VDD. The output inverter chain then drives DCMPP and DCMPN to VDD (through two inversions: VDD → net1=low → DCMPP=high? No -- let us trace carefully:

- LM = VDD → M10 on, M19 off → net1 = VSS → M106 off, M78 on → DCMPP = VDD
- LP = VDD → M16 on, M21 off → net2 = VSS → M105 off, M77 on → DCMPN = VDD

So during reset: **both DCMPP and DCMPN are at VDD**.

During evaluation (CLK=high), suppose VINP > VINN:
- M0 draws more current than M1 → VN1 falls faster → VN1 low, VP1 stays high
- Cross-couple: M45 (G=LP) with source VN1 falling → eventually LP falls, LM rises (positive feedback)
- Result: LM → VDD, LP → VSS
- LM=VDD → net1=VSS → DCMPP=VDD (stays high? No...)

Actually, the latch nodes LM and LP are the regenerative outputs. With VINP > VINN:
- VN1 falls → M45 (G=LP, S=VN1) current increases → LM pulled down
- Actually M45: G=LP, D=LM, S=VN1. If VN1 drops, Vgs_M45 = LP - VN1 increases, M45 turns on harder pulling LM down
- M6: G=LM, D=LP, S=VP1. LM dropping means less Vgs for M6, so LP stays high
- Cross-couple PMOS: M48 (G=LP, D=LM), M49 (G=LM, D=LP). LM dropping → M49 Vgs more negative → M49 on → LP pulled to VDD
- Final: LM=VSS, LP=VDD

Output: LM=VSS → M10 off, M19 on → net1=VDD → M106 on, M78 off → **DCMPP=VSS (falls)**
LP=VDD → M16 on, M21 off → net2=VSS → M105 off, M77 on → **DCMPN=VDD (stays high)**

**Summary: VINP > VINN → DCMPP falls to VSS, DCMPN stays at VDD. Both outputs reset to VDD during CLK=low.**

This is important for the SAR logic: the latch cells detect which output **fell** during evaluation to determine the comparison result.

### Offset Trim Implementation

The comparator includes binary-weighted cascode trim pairs for offset correction. The trim transistors are split between the VINP side (active trim) and the VINN side (matched dummies):

#### VINP-side trim transistors (active, gated by TRIM_OS)

| Transistor | Type | G | D | S | W | NF | Trim Bit | Weight |
|-----------|------|---|---|---|---|-----|----------|--------|
| M109 | nch_ulvt | VINP | VN1 | net3 | 500n | 1 | -- | 1x (cascode top) |
| M117 | nch_ulvt | TRIM_OS<0> | net3 | VS | 500n | 1 | bit 0 | 1x (cascode bottom) |
| M110 | nch_ulvt | VINP | VN1 | net9 | 1u | 2 | -- | 2x (cascode top) |
| M120 | nch_ulvt | TRIM_OS<1> | net9 | VS | 1u | 2 | bit 1 | 2x (cascode bottom) |
| M108 | nch_ulvt | VINP | VN1 | net7 | 2u | 4 | -- | 4x (cascode top) |
| M119 | nch_ulvt | TRIM_OS<2> | net7 | VS | 2u | 4 | bit 2 | 4x (cascode bottom) |
| M107 | nch_ulvt | VINP | VN1 | net5 | 4u | 8 | -- | 8x (cascode top) |
| M118 | nch_ulvt | TRIM_OS<3> | net5 | VS | 4u | 8 | bit 3 | 8x (cascode bottom) |

Each pair forms a cascode: the top transistor has VINP on its gate (part of the input differential pair), and the bottom transistor is gated by the trim bit. When TRIM_OS[i] is high, the bottom device conducts, adding its current to the VINP-side tail current, which shifts the comparator trip point.

#### VINN-side dummy transistors (always on or off, for matching)

| Transistor | Type | G | D | S | W | NF | Weight |
|-----------|------|---|---|---|---|-----|--------|
| M121 | nch_ulvt | VINN | VP1 | net14 | 500n | 1 | 1x (cascode top) |
| M122 | nch_ulvt | VDD | net14 | VS | 500n | 1 | 1x (cascode bottom, always on) |
| M128 | nch_ulvt | VINN | VP1 | net11 | 1u | 2 | 2x (cascode top) |
| M123 | nch_ulvt | VDD | net11 | VS | 1u | 2 | 2x (cascode bottom, always on) |
| M127 | nch_ulvt | VINN | VP1 | net12 | 2u | 4 | 4x (cascode top) |
| M124 | nch_ulvt | VDD | net12 | VS | 2u | 4 | 4x (cascode bottom, always on) |
| M126 | nch_ulvt | VINN | VP1 | net13 | 4u | 8 | 8x (cascode top) |
| M125 | nch_ulvt | **VSS** | net13 | VS | 4u | 8 | 8x (cascode bottom, always **off**) |

The VINN-side dummies match the VINP-side trim transistors in size and topology. Their cascode bottoms have gates tied to VDD (always on) for bits 0-2, providing a fixed current that the VINP-side trim adjusts against. For bit 3 (MSB), the dummy bottom M125 has gate=VSS (always off), meaning the default state (TRIM_OS=0) has zero trim current on the VINP side for all bits, and zero on the VINN MSB dummy. The mid-code TRIM_OS=7 (0111) turns on bits 0-2 on the VINP side, balancing against the always-on bits 0-2 on the VINN side.

### ESD Protection Clamps

| Transistor | Type | G | D | S/B | W | L | Role |
|-----------|------|---|---|-----|---|---|------|
| M2 | nch_ehvt | VN1 | VSS | VSS | 500n | 1u | ESD clamp on VN1 node |
| M23 | nch_ehvt | VP1 | VSS | VSS | 500n | 1u | ESD clamp on VP1 node |

These extra-high Vth (ehvt) NMOS devices with long channel (L=1u) act as gate-oxide protection clamps. Under normal operation they are off (VN1/VP1 swing between VSS and VDD, well below the ehvt threshold). During an ESD event, the high voltage turns them on, clamping the node.

### Stabilization Capacitors

| Cap | Nodes | Value | Purpose |
|-----|-------|-------|---------|
| C6 | VS - VSS | 12 fF | Tail node decoupling |
| C0 | VP1 - VSS | 5 fF | Integration node stabilization |
| C7 | VN1 - VSS | 5 fF | Integration node stabilization |
| C8 | CLK - VSS | 3.7 fF | Clock input filtering |
| C9 | VINN - VSS | 5 fF | Input loading (represents expected parasitic) |
| C10 | VINP - VSS | 5 fF | Input loading (represents expected parasitic) |
| C11 | LM - VSS | 8 fF | Latch node stabilization |
| C12 | LP - VSS | 8 fF | Latch node stabilization |

The latch node caps (C11, C12 = 8 fF) slow down regeneration slightly but improve robustness against metastability by ensuring adequate energy storage during the latch transition. The input caps (C9, C10) model the expected CDAC top-plate parasitic loading.

### SR Latch Requirement

The StrongArm outputs (DCMPP, DCMPN) are valid only during the evaluation phase. During reset (CLK=low), both return to VDD, losing the decision. The SAR logic must capture the decision before reset occurs. In the ZZS implementation, the asynchronous latch cells (L5_LATCH_CELL) serve this role: they detect the falling edge of DCMPP or DCMPN during evaluation and latch the result, holding it through the subsequent reset phase. An explicit SR latch is not needed because the latch cell topology includes cross-coupled regeneration that holds state after the comparator resets.

---

## How to Verify a StrongArm Comparator

### Quick Transient Check (sanity first)

Before running any noise analysis, run a short transient (5-10 CLK cycles) to confirm basic function:

- When CLK rises (evaluation): one of DCMPP/DCMPN should fall to VSS, the other stays at VDD.
- When CLK falls (reset): both DCMPP and DCMPN return to VDD.
- Inspect internal latch nodes LP/LM — they should show clean regeneration (one rail-to-rail swing per cycle, no ringing or incomplete settling).
- If both outputs stay at VDD during evaluation, the input pair is not conducting — check tail bias and input common mode.

### PSS + Pnoise Flow (standard noise characterization)

The industry-standard method for dynamic comparator noise uses periodic steady-state (PSS) followed by periodic noise (Pnoise) analysis. PSS finds the steady-state waveform under clocked operation; Pnoise then computes the sampled noise referred to the comparator input.

**Spectre analysis statements:**

```spectre
pss pss fund=CLK_FREQ harms=10 errpreset=conservative autotstab=yes saveinit=yes
pnoise pnoise start=0 stop=BW pnoisemethod=fullspectrum noisetype=sampled measurement=[pm0]
pm0 jitterevent trigger=[INST.LP INST.LM] triggerthresh=50m triggernum=1 triggerdir=rise target=[INST.LP INST.LM]
```

- `fund=CLK_FREQ`: the comparator clock rate (e.g., 1G for 1 GHz).
- `stop=BW`: noise bandwidth, typically CLK_FREQ/2 (Nyquist).
- `noisetype=sampled`: computes the noise folded by the periodic operation (critical for clocked circuits).
- `pnoisemethod=fullspectrum`: accounts for noise folding from all harmonics.
- The jitter event `pm0` uses LP and LM (internal latch nodes) as triggers, not the buffered DCMPP/DCMPN outputs. LP/LM are the regeneration nodes where the actual noise-to-timing conversion occurs — the output buffers add deterministic delay but no additional noise information.
- `triggerthresh=50m`: the threshold voltage (50 mV) at which LP/LM crossings are detected.
- `triggerdir=rise`: detects the rising transition of the winning latch node.

### Testbench Setup

**Input biasing (differential DC):**

```
VINP = Vcm + Vid/2
VINN = Vcm - Vid/2
```

where Vcm is the input common mode (typically VDD/2) and Vid is a small differential input (typically 1 mV) that biases the comparator into its linear gain region for noise extraction.

**Clock source:** `vpulse` at the target clock rate, with fast edges (rise/fall = 10 ps or less).

**Save list:** Save only the signals needed — `DCMPN DCMPP LP LM V0:p` (V0:p is the supply source current terminal for power measurement). Use `saveOptions options save=selected` to avoid bloating PSF files.

**Multi-corner sweep:** Parameterize VDD for corner analysis: `VDD=0.81:0.09:0.99` sweeps VDD from 0.81V to 0.99V in 90 mV steps (low/nominal/high supply). Run PSS+Pnoise at each corner.

### Metric Extraction from PSS+Pnoise Results

- **Power:** From the saved supply current (V0:p), integrate over one clock period: `P = -avg(V0:p) * VDD`. The negative sign accounts for current flowing out of the positive terminal.
- **Comparison delay (Tcmp):** From PSS waveforms, find the first crossing of `(DCMPN - DCMPP)` through VDD/2 after the CLK rising edge. This is the total delay from clock to valid digital output.
- **Input-referred noise:** Integrate the Pnoise output spectrum from DC to BW. The Pnoise result is timing jitter at the latch nodes; divide by the comparator voltage-to-time gain (slope of LP/LM at the trigger crossing, typically ~50 V/ns for a fast comparator) to refer back to the input. Alternatively, if Pnoise reports voltage noise directly at the output, divide by the comparator gain (~50x from input to normalized output).
- **FOM1 = noise^2 x power** (noise-power product, V^2 x W). Lower is better.
- **FOM2 = noise^2 x power x Tcmp** (noise-power-speed product, V^2 x W x s). Includes speed in the comparison.

### Offset Trim Verification

For comparators with binary-weighted offset trim (e.g., 4-bit trim with codes 0-15):

- Sweep the trim code across its full range (0 to 2^N - 1).
- Use a Verilog-A encoder (e.g., `_VA_D2B_ENCODER_4B`) to convert the integer sweep variable to N-bit digital signals driving the trim transistor gates.
- Add an offset voltage source in series with one input: `V_offset dc=0.5*post*offset` where `post` is 0 or 1 (enable/disable) and `offset` is the applied offset in volts.
- At each trim code, run transient or PSS and measure the output decision probability vs. input offset.
- The trim step size should be approximately uniform and cover at least +/- 3 sigma of the expected random offset.
- Pass criterion: monotonic shift of the comparator trip point with trim code, step size within 20% of the design target.
