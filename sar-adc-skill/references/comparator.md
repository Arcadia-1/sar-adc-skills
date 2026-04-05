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
