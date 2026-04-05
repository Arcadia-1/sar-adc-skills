# SAR Logic Implementation

Use this file for SAR logic architecture, async latch chain circuit implementation, DAC switch polarity convention, output latching, and Verilog-A behavioral model correspondence. Source material is the taped-out SAR_11B_ZZS (TSMC 28nm HPC+, 0.9V) and the bundled Verilog-A assets.

---

## 1. Total Architecture & Signal Interface

### Port Table

| Port | Dir | Description |
|------|-----|-------------|
| CLKS | input | Sample clock (external). Rising = enter sample. Falling = start conversion. |
| DCMPP, DCMPN | input | Comparator differential outputs |
| CMPCK | output | Comparator clock, generated internally by logic (async) or passed through (sync) |
| VBOTP\<11:1\>, VBOTN\<11:1\> | output | CDAC bottom plate voltages, driven to VREFP or VREFN each bit cycle |
| DOUT\<11:0\> | output | Final digital output, latched at end of conversion |
| RSTP | input | Global reset (active low in 11b ZZS) |
| VREFP, VREFN | inout | Reference voltages (0.9V / 0V in 11b ZZS) |

### Architecture Block Diagram

```
CLKS ──────────────────────────────────────────────┐
                                                    │
DCMPP ──┐                                          │
DCMPN ──┴──> [L5_LATCH_CELL<11>] ──ENB_NEXT──>    │
             [L5_LATCH_CELL<10>] ──ENB_NEXT──>     │
             ...                                    │
             [L5_LATCH_CELL<1>]  ──ENB_NEXT──>     │
             [L5_LATCH_CELL_LSB<0>]                 │
                    │DP/DN per bit                  │
                    ↓                               │
             [L5_DAC_SWI x2]                        │
             ├── VBOTP<11:1>  → CDAC_P bottom       │
             └── VBOTN<11:1>  → CDAC_N bottom       │
                                                    │
             CMPCK ──────────────────────────────── ┘
             (via BUFFD2 chain, driven by latch chain)

             DFF x12 (clocked by CLKS↑) → DOUT<11:0>
```

### When to Use Each Implementation

| Implementation | Use When |
|----------------|----------|
| Synchronous SAR | Medium speed, power-limited, easy timing closure |
| Asynchronous SAR (L5_LATCH_CELL chain) | High speed, dynamic time allocation per bit |

---

## 2. Full Conversion Timing

One complete conversion cycle, step by step:

```
CLKS ──────╮                              ╭─────
           │                              │
           ╰──────────────────────────────╯
           ↑CLKS↓                         ↑CLKS↑

CLKS↓:  Reset VBOTP/N to initial state (all VBOTP=VREFP, VBOTN=VREFN)
        Preset MSB: VBOTP<11>=VREFN, VBOTN<11>=VREFP
        bit_ptr = 11

  ──> CMPCK↑: Fire comparator for bit 11
  ──> Comparator decides (DCMPP or DCMPN wins)
  ──> Latch captures result: BP[11] = (DCMPP > DCMPN)
  ──> Update CDAC: complementary assignment for VBOTP/N[11]
  ──> CMPCK↓ then ↑: Fire comparator for bit 10
  ──> ... repeat for bits 10 down to 0 ...

CLKS↑:  Latch DOUT<11:0> = BP[11:0] via DFF
        Reset VBOTP/N to sample state
```

Key timing constraint (async): the logic delay from comparator output to CMPCK re-trigger must be longer than CDAC settling time. In 11b ZZS, `t_logic_delay ≈ 200 ps` is set by the buffer chain driving CMPCK.

---

## 3. Synchronous vs Asynchronous

### State Machine Comparison

| | Synchronous | Asynchronous |
|---|---|---|
| CMPCK source | External CLKC (fixed rate) | Internal, driven by latch chain |
| step decrement | On CLKC↑ | On comparator output reset (↓ edge) |
| Speed | Fixed per-bit slot = worst case | Dynamic: easy bits finish early |
| Timing risk | Wasted margin on easy bits | Ring must not outrun CDAC settling |
| Implementation | D-FF shift register | L5_LATCH_CELL cascade |

### Synchronous Pseudocode

```
on CLKS↑:  step = N;  clear all DCTRL, DOUT
on CLKC↑:  step = step - 1
on DCMPP↑: DOUT[step] = 1;  if step>0: DCTRLN[step] = 1
on DCMPN↑: if step>0: DCTRLP[step] = 1
```

### Asynchronous Pseudocode

```
on CLKS↑:  step = N-1;  clear all DCTRL
on CLKC↑:  CMPCK = 1                          // first trigger only
on DCMPP↑ or DCMPN↑:                          // comparator decided
    CMPCK = 0                                  // close comparator
    DOUT[step] = (DCMPP > DCMPN)
    if step >= 1:
        if DOUT[step]: DCTRLN[step] = 1
        else:          DCTRLP[step] = 1
on DCMPP↓ or DCMPN↓:                          // comparator reset complete
    step = step - 1
    if step >= 0: CMPCK = 1                    // trigger next bit
```

---

## 4. Async Chain Core: L5_LATCH_CELL

The fundamental building block. 11 instances cascade from MSB (bit 11) to LSB (bit 0). The LSB uses L5_LATCH_CELL_LSB (slightly modified termination).

### Per-Cell Timing Sequence

```
① ENB_PRE goes LOW  (from previous cell, or CLKS for cell 11)
② NOR3 → EN = HIGH  (enabled only when: prev done AND comparator valid)
③ DCMPP/DCMPN drive M6/M9 gates  (comparator already fired via CMPCK)
④ One side pulls down → cross-couple regenerates
⑤ DP, DN settle to complementary logic values
⑥ NAND2 detects DP≠DN → RDY = LOW
⑦ NAND2 → ENB_NEXT goes LOW  → triggers next latch cell
⑧ ENB_NEXT also drives CMPCK → comparator fires for next bit
```

### Transistor Role Table

| Transistor | Type | Role |
|------------|------|------|
| M6 | nch_ulvt_mac | DCMPP input path into latch |
| M9 | nch_ulvt_mac | DCMPN input path into latch |
| M7, M8 | nch_ulvt_mac | Cross-couple pull-down (regeneration) |
| M2, M5 | pch_ulvt_mac | Pull-up load |
| M3, M10 | pch_ulvt_mac | Reset pull-up (force both sides HIGH on reset) |
| M0 | nch_ulvt_mac | Enable path (gated by EN) |
| M1 | nch_ulvt_mac | Reset pull-down |
| M12, M14 | nch_ulvt_mac | DP/DN output driver |
| M11, M13 | pch_ulvt_mac | DP/DN pull-up |

All transistors: `nch_ulvt_mac` / `pch_ulvt_mac` (ultra-low Vth for speed at 0.9V).

### Standard Cell Control Logic

| Cell | Type | Function |
|------|------|----------|
| I15 | NR3D0 (NOR3) | EN = NOR(ENB_PRE, RSTN_GLB_B, VALID_B) — gates latch until previous bit done |
| I4 | ND2D0 (NAND2) | RDY = NAND(DP, DN_B) — detects regeneration complete |
| I26 | ND2D0 (NAND2) | ENB_NEXT = NAND(RDY_B, ...) — propagates enable to next cell |
| I25 | INVD0 | RSTN = INV(ENB_PRE) — local reset from previous enable |
| C0, C10 | cap | Stabilization on DPB/DNB nodes |

The NOR3 enable gate is the key robustness element: the latch will not activate until the previous cell has completed AND the comparator is in a valid state. This prevents metastability propagation.

### Timing Constraint

```
t_latch_regen + t_NAND + t_buffer_CMPCK < t_CDAC_settle

In 11b ZZS (28nm, 0.9V): total async loop ≈ 200–300 ps per bit
```

If CMPCK re-fires before CDAC settles, the comparator sees residual charge redistribution → bit error. Add decoupling caps (DCAP4/DCAP8) near logic supply rails to absorb switching transients.

---

## 5. DAC Switch & DCTRL Polarity

### Circuit: Complementary Pass Gate (L5_DAC_SWI)

Two transistors per bit, no inverter needed:

```
         VREFP
           │
    M1 (pch_mac): G = DCTRL[i]
           │
    ────── VBOT[i] ──────
           │
    M0 (nch_mac): G = DCTRL[i]
           │
         VREFN
```

Same DCTRL drives both gates simultaneously:

| DCTRL | PMOS M1 | NMOS M0 | VBOT | Effect on VTOP |
|-------|---------|---------|------|----------------|
| LOW | ON (Vgs = −VDD) | OFF | VREFP | Initial / sample state |
| HIGH | OFF | ON (Vgs = +VDD) | VREFN | Set bit → VTOP decreases |

Uses `nch_mac` / `pch_mac` (standard Vth, not ulvt) — better matching and lower leakage on bottom plates.

### Polarity Convention (Critical)

```
Setting a bit (BP[i]=1):
  VBOTP[i] = VREFN  →  CDAC_P top plate decreases
  VBOTN[i] = VREFP  →  CDAC_N top plate increases
  Net differential: VTOPP − VTOPN decreases by 2 × Vref × Ci/Ctotal
```

**This is opposite to some textbook conventions where setting a bit raises VTOP.** In ZZS, a HIGH DCTRL means VREFN (GND), which pulls VTOP down. The positive side (P) and negative side (N) CDACs are always driven complementarily.

### Charge Redistribution (after sampling)

```
VTOPP = VIN_P + VREFP − Vref × Σ(BP[i] × Ci) / Ctotal
VTOPN = VIN_N + VREFP − Vref × Σ(BN[i] × Ci) / Ctotal

Differential residue:
  VTOPP − VTOPN = (VIN_P − VIN_N) − Vref × Σ((BP[i]−BN[i]) × Ci) / Ctotal
```

Since BN[i] = 1 − BP[i], the differential step per bit = `2 × Vref × Ci / Ctotal`.

---

## 6. Output Latching

### DFF Array

12× `DFQD1BWP12T30P140` (standard cell D flip-flop, 12T track, 28nm digital library).

```
D input:  DCTRLP<11:0>   (from latch cell DP outputs)
Clock:    CLKS rising edge
Q output: DOUT<11:0>
```

DCTRLP is used (not DCTRLN) because the positive side encoding directly maps to the binary output: BP[i]=1 means the bit was set.

### MSB Buffer

DCTRLP\<11\> and DCTRLN\<11\> pass through INVD4 buffers (I35, I36) before driving DAC switches, due to higher fan-out on the MSB.

### DOUT Mapping

| DOUT bit | Maps to | Weight |
|----------|---------|--------|
| DOUT\<11\> | BP[11], MSB | 2^10 |
| DOUT\<10\> | BP[10] | 2^9 |
| ... | ... | ... |
| DOUT\<1\> | BP[1] | 2^0 |
| DOUT\<0\> | 0 (LSB, no DAC switch) | — |

DOUT\<0\> is always 0 in this implementation — the LSB latch cell captures the final residue sign but is not used for CDAC control.

---

## 7. Verilog-A Behavioral Model Correspondence

The file `sar_logic_11b_diff.va` (in `sar_adc_10b/veriloga/`) is a synchronous behavioral equivalent. Key event-to-hardware mapping:

| Verilog-A `@` event | Hardware equivalent |
|---------------------|---------------------|
| `cross(V(CLKS), -1)` | CLKS↓ → start conversion, preset MSB |
| `cross(V(CLKS), +1)` | CLKS↑ → DFF latches DOUT, reset to sample state |
| `cross(V(CMPCK), -1)` | CMPCK↓ → read comparator result (StrongArm resetting) |
| `BP[bit_ptr] = 1` | L5_LATCH_CELL DP goes HIGH, DCTRL HIGH |
| `V(VBOTP[i]) = VREFN` | L5_DAC_SWI NMOS on, VBOT = VREFN |

### Reading the Comparator in Verilog-A

```verilog-a
// On CMPCK↓: StrongArm is resetting, outputs returning to VDD
// Read DCMPP vs DCMPN voltage at this moment:
if (V(DCMPP, VSS) < V(DCMPN, VSS))
    BP[bit_ptr] = 1;   // DCMPP fell during evaluation → VTOPP > VTOPN → keep bit
else
    BP[bit_ptr] = 0;
```

This corresponds to: the side that fell during StrongArm evaluation is the winner. At reset moment, the loser is still near VDD, the winner already pulled down.

### Async vs Behavioral Model

The `L3_logic_4b_async.va` (in skill assets) captures the same flow for 4 bits with explicit `@(cross(..., +1) or cross(..., -1))` events mimicking the latch chain behavior. For 11-bit behavioral work, use `sar_logic_11b_diff.va` as the starting point.

---

## Usage Guide

| Goal | Read |
|------|------|
| Understand SAR logic architecture and signal flow | Sections 1–3 |
| Implement latch chain in schematic | Sections 4–5 |
| Connect logic to CDAC and latch output | Sections 5–6 |
| Debug behavioral simulation (Verilog-A) | Section 7 |
| Full implementation reference | All sections |

---

## 8. DCTRL-to-VBOT Signal Chain and Initial State

### From Latch Cell to DAC Switch to CDAC Bottom Plate

The complete signal path from comparator decision to CDAC feedback:

```
Comparator decides → DCMPP/DCMPN

L5_LATCH_CELL[i]:
  DCMPP/DCMPN inputs → cross-couple regeneration → DP[i], DN[i]
  
  DP[i] = DCTRLP[i]  (directly connected for bits 10:1)
  DN[i] = DCTRLN[i]  (directly connected for bits 10:1)

  For bit 11 (MSB): DP/DN pass through INVD4 buffers (I35/I36)
    I35: net5 (=DP from cell 11) → ZN = DCTRLP<11>
    I36: net8 (=DN from cell 11) → ZN = DCTRLN<11>
    Note: the INVD4 inverts, so DCTRLP<11> = NOT(DP<11>)

L5_DAC_SWI (two instances: I0 for P-side, I1 for N-side):
  I0: DCTRL<11:1> = DCTRLP<11:1> → VBOT<11:1> = VBOTP<11:1>
  I1: DCTRL<11:1> = DCTRLN<11:1> → VBOT<11:1> = VBOTN<11:1>

  Per bit:
    DCTRL[i] = LOW  → PMOS on → VBOT[i] = VREFP
    DCTRL[i] = HIGH → NMOS on → VBOT[i] = VREFN

L4_CDAC:
  VBOT<11:1> connects to L5_CAP_ARRAY bottom plates
  Charge redistributes → VTOP changes → comparator sees new residue
```

### Initial State at Conversion Start

When CLKS falls (start conversion), the SAR logic resets all latch cells. The initial state of the DAC control signals:

```
P-side:
  All DCTRLP<10:1> = LOW  (latch cells reset: DP=LOW, DN=LOW)
  DCTRLP<11> = HIGH (MSB buffer inverts: DP=LOW → INVD4 → DCTRLP=HIGH)
  
  Wait — this needs careful analysis. The MSB cell DP initially resets to LOW.
  I35 inverts: DCTRLP<11> = NOT(DP<11>) = NOT(LOW) = HIGH
  
  So VBOTP<11> = VREFN (NMOS on), VBOTP<10:1> = VREFP (PMOS on)
  
  This means the MSB is initially "set" (preset) at the start of conversion.

N-side:
  All DCTRLN<10:1> = LOW  (latch cells reset: DN=LOW)
  DCTRLN<11> = HIGH (MSB buffer inverts: DN=LOW → INVD4 → DCTRLN=HIGH)
  
  So VBOTN<11> = VREFN (NMOS on), VBOTN<10:1> = VREFP (PMOS on)
```

The MSB preset is a standard SAR technique: the first bit trial starts with the MSB already set, so the comparator immediately evaluates whether to keep or clear it.

### DCMPP/DCMPN Swap at MSB

A critical wiring detail in L4_LOGIC_SWI: the MSB latch cell (I_LATCH_CELL<11>) has its comparator inputs **swapped**:

```
I_LATCH_CELL<11>:
  DCMPP port = DCMPN net  (comparator's negative output)
  DCMPN port = DCMPP net  (comparator's positive output)
```

This swap implements the correct sign convention for the first bit trial. Without it, the MSB decision would be inverted. Bits 10 down to 0 receive DCMPP/DCMPN with normal (unswapped) polarity.

### DFF Output Latching

At the end of conversion (CLKS/RSTP rising edge), the 12 DFFs (I26<11:0>, DFQD1BWP12T30P140) capture the final state:

```
DFF inputs:  D = DCTRLP<11:0>
DFF clock:   CP = RSTP (derived from CLKS)
DFF outputs: Q = DOUT<11:0>
```

DCTRLP is used (not DCTRLN) because the positive-side code directly encodes the binary output. DOUT<0> comes from the LSB latch cell's DP output; since there is no DAC switch for bit 0, it captures only the final residue sign.

### L5_DAC_SWI Complete Switch Sizing

The DAC switch module contains 11 NMOS + 11 PMOS switches (bits 11 down to 1). The switch widths scale with bit weight for matched RC settling:

| Bit | NMOS Instance | NMOS W | NMOS NF | PMOS Instance | PMOS W | PMOS NF |
|-----|--------------|--------|---------|--------------|--------|---------|
| 11 (MSB) | M0 | 6.4u | 16 | M1 | 8.32u | 16 |
| 10 | M2 | 3.2u | 8 | M3 | 4.16u | 8 |
| 9 | M5 | 1.6u | 4 | M4 | 2.08u | 4 |
| 8 | M6 | 800n | 2 | M7 | 1.04u | 2 |
| 7 | M8 | 400n | 1 | M9 | 520n | 1 |
| 6-1 | M10<5:0> | 200n | 1 | M11<5:0> | 260n | 1 |

All NMOS: `nch_mac` (standard Vth), L=30n. All PMOS: `pch_mac` (standard Vth), L=30n.

The PMOS/NMOS width ratio is approximately 1.3x (e.g., 8.32u/6.4u = 1.3, 260n/200n = 1.3), compensating for the mobility difference to achieve symmetric pull-up/pull-down timing.

### CMPCK Generation Chain

The comparator clock is generated from the latch chain completion signals through a buffer chain:

```
DCMPP AND DCMPN → I2 (ND2D0, NAND) → net2
net2 → I3 (BUFFD2) → VALID
net2 NOR STOP → I4 (NR2D0) → net3
net3 → I5 (BUFFD0) → net4
net4 → I6 (BUFFD2) → CMPCK
```

The NAND gate I2 detects when both comparator outputs have returned to their reset state (both high = both comparator decisions captured). The NOR gate I4 gates this with the STOP signal (which goes high when all bits are done). The buffer chain (I5 → I6) adds controlled delay to ensure CDAC settling before the next comparison fires.

### Decoupling Capacitors

The logic module includes substantial decoupling:
- I39<36:1>: 36 instances of DCAP4 (standard cell decoupling caps)
- I37<4:1>: 4 instances of DCAP4
- I38<10:1>: 10 instances of DCAP8 (larger decoupling caps, placed near latch cells)

These absorb switching transients from the digital logic, preventing supply noise from coupling into the sensitive comparator and CDAC through shared VDD/VSS rails.

---

## How to Verify SAR Logic

### Full-Code Functional Test

The baseline sanity check — verify that the logic produces all expected output codes.

- Apply a slow ramp input covering the full analog input range (0 to VREF) through a behavioral (ideal) comparator and CDAC. This isolates the logic from analog imperfections.
- Capture DOUT at every conversion cycle.
- Verify: output code increases monotonically with increasing input.
- Verify: all 2^N codes appear at least once (no missing codes).
- If codes are missing, check the DCTRL-to-VBOT mapping and the latch cell enable chain for stuck or swapped signals.
- For differential designs, also verify that the code is centered at mid-scale when VIP = VIN (zero differential input).

### Timing Verification

For asynchronous SAR logic, the self-timed loop must complete all N bit decisions within one conversion period.

- Measure the per-bit decision delay: from CMPCK rising edge to comparator decision (DCMPP/DCMPN valid) to DCTRL update to the next CMPCK rising edge.
- Total conversion time = sum of all per-bit delays + sampling phase duration.
- This total must be less than 1/Fs with margin (typically < 80% of the full clock period).
- For synchronous SAR: each bit decision must complete within one BITCLK period. Measure the critical path from BITCLK edge through comparator, latch, and DAC switch settling.
- Watch for the MSB and LSB extremes: the MSB has the largest CDAC step (longest settling), while the LSB may have the smallest comparator overdrive (longest regeneration time).

### DCTRL-to-VBOT Signal Integrity

The DAC switch outputs must be clean digital levels — any glitch or incomplete transition corrupts the CDAC charge.

- Verify VBOT swings rail-to-rail between VREFP and VREFN at each bit transition.
- Check transition time (10%-90%) — it should be short relative to the bit period but not so fast that it causes excessive ringing on the bottom-plate node.
- Verify complementary operation: when DCTRLP[i] goes HIGH (VBOTP = VREFN), DCTRLN[i] must go LOW (VBOTN = VREFP) simultaneously. Any skew between the P and N sides creates a transient common-mode disturbance at the comparator input.
- Inspect the MSB transition especially carefully — it drives the largest switch and capacitor, and any glitch has the largest impact on VTOP.

### Reset and Initialization

Correct reset behavior is essential for cycle-to-cycle repeatability.

- After each conversion completes (CLKS rises), verify that all DCTRLP signals return to their initial state (LOW for bits 10:1, HIGH for the MSB if the MSB is preset via an inverting buffer).
- Verify that DCTRLN signals also return to their initial state.
- Check that the latch cells fully reset: both DP and DN should return to LOW (or their defined reset state) before the next conversion begins.
- If using an asynchronous design, verify that the CMPCK generator stops after the LSB decision and does not produce spurious pulses during the sampling phase.
