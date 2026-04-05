# SAR_11B_ZZS — Taped-Out 11-bit Reference Design (TSMC 28nm HPC+)

# SAR_11B_ZZS Reference Design

Taped-out 11-bit SAR ADC. TSMC 28nm HPC+ (CRN28HPC+ULL), VDD=0.9V.
Extracted from Virtuoso schematic via virtuoso-bridge.

## Architecture Overview

Fully differential, asynchronous, charge-redistribution SAR ADC.

```
VIP ──┬──> CDAC_P ──> VTOPP ──┐
      │                        ├──> StrongArm ──> DCMPP/DCMPN
VIN ──┼──> CDAC_N ──> VTOPN ──┘         ↑ CMPCK (from logic)
      │                                 │
CLKS ─┴──> Bootstrap ──> VBTSP/VBTSN    │
                                        │
           Async SAR Logic ─────────────┘
             ├── VBOTP/VBOTN → CDAC bottom plates
             └── DOUT<11:0>
```

### Key Design Decisions
1. **Fully differential** — comparator senses VTOPP vs VTOPN, not VTOP vs VCM
2. **Asynchronous SAR** — CMPCK generated internally, no external bit clock
3. **Bootstrap = gate voltage only** — outputs VGBTS=VIN+VDD to CDAC internal switch
4. **VIN direct to CDAC** — no separate S&H module
5. **Complementary pass gate DAC switches** — 2 transistors/bit, no inverter needed

## Module Reference

Detailed implementation of each module is in `references/`:

| Module | File | Description |
|--------|------|-------------|
| Bootstrap | [bootstrap.md](references/bootstrap.md) | Gate voltage generator (LB_SAR_BTS) |
| CDAC | [cdac.md](references/cdac.md) | Sampling switch + cap array + DAC switches |
| Comparator | [comparator.md](references/comparator.md) | StrongArm with offset trim |
| SAR Logic | [sar-logic.md](references/sar-logic.md) | Async latch chain + DCTRL generation |
| Integration | [integration.md](references/integration.md) | Top-level connectivity + testbench |

## Quick Sizing Reference

| Parameter | Value |
|-----------|-------|
| Unit cap (Cu) | 200 aF (LB_CUNIT_X1) |
| Unit cap x3 | 3 × 200 aF = 600 aF (LB_CUNIT_X3) |
| Total CDAC cap | ~1024 × Cu ≈ 205 fF per side |
| Sampling NMOS | nch_mac (not ulvt), gate=VGBTS |
| Comparator input pair | nch_ulvt_mac W=16u NF=32 |
| Comparator tail | nch_ulvt_mac W=2u NF=4 |
| DAC switch NMOS | nch_mac (per bit, width varies) |
| DAC switch PMOS | pch_mac (per bit, width varies) |
| Bootstrap cap | cfmom_2t (PDK MOM cap) |

## DAC Switch Polarity Convention

**Critical for correct operation:**
- DCTRL=LOW → PMOS on → bottom plate = VREFP (initial/sample state)
- DCTRL=HIGH → NMOS on → bottom plate = VREFN
- Setting a bit **decreases** VTOP by Vref × Ci/Ctotal

---

## Complete Module Hierarchy

```
L3_SAR_11B  (top-level SAR ADC)
│
├── I7: L4_BTS_X2  (dual bootstrap switch)
│   ├── I0: LB_SAR_BTS  (VIP → VBTSP)
│   │   ├── M0-M5: switching transistors
│   │   ├── M20-M25: control transistors
│   │   └── C1: cfmom_2t (bootstrap capacitor)
│   └── I2: LB_SAR_BTS  (VIN → VBTSN)
│
├── I_CDACP: L4_CDAC  (P-side CDAC)
│   ├── M3: nch_mac W=5u NF=10 (sampling switch, G=VGBTS)
│   ├── M4: nch_mac W=5u NF=10 (dummy switch, G=net1)
│   ├── M2, M5: nch_ulvt_mac W=4u NF=8 (cascode for dummy gate)
│   └── I93: L5_CAP_ARRAY
│       ├── I0: LB_CUNIT_X1 (dummy, BOT=VREFP)
│       ├── I1: LB_CUNIT_X1 (bit 1, 200aF)
│       ├── I2<2:1>: LB_CUNIT_X1 (bit 2, 2×200aF)
│       ├── I3: LB_CUNIT_X3 (bit 3, 3×200aF)
│       ├── I4<2:1>..I11<167:1>: LB_CUNIT_X3 (bits 4-11)
│       └── I12<9:1>: LB_CUNIT_X3 (layout dummy, floating BOT)
│
├── I_CDACN: L4_CDAC  (N-side CDAC, same structure)
│
├── I_CMP: L4_COMPARATOR  (StrongArm + offset trim)
│   ├── M88: tail (nch_ulvt W=2u NF=4)
│   ├── M0, M1: input pair (nch_ulvt W=16u NF=32)
│   ├── M45, M6: NMOS cross-couple (nch_ulvt W=4u NF=8)
│   ├── M48, M49: PMOS cross-couple (pch_ulvt W=4u NF=8)
│   ├── M4, M5, M7, M50: reset PMOS (pch_ulvt W=2u NF=4)
│   ├── M79: cross-connect reset (pch_ulvt W=500n NF=1)
│   ├── M10/M19, M16/M21: buffer inverters (W=500n)
│   ├── M106/M78, M105/M77: output inverters (W=1.5u NF=3)
│   ├── M107-M110 + M117-M120: VINP-side offset trim (binary 1x-8x)
│   ├── M121-M128 + M122-M125: VINN-side dummy trim
│   ├── M2, M23: ESD clamps (nch_ehvt W=500n L=1u)
│   └── C0-C12: stabilization caps (3.7fF-12fF)
│
└── I_LOGIC: L4_LOGIC_SWI  (async logic + DAC switches)
    ├── I_LATCH_CELL<11>: L5_LATCH_CELL (MSB, DCMPP/DCMPN swapped)
    ├── I_LATCH_CELL<10:1>: L5_LATCH_CELL (×10)
    ├── I_LATCH_CELL<0>: L5_LATCH_CELL_LSB (has RDY output)
    ├── I0: L5_DAC_SWI (P-side, DCTRLP → VBOTP)
    ├── I1: L5_DAC_SWI (N-side, DCTRLN → VBOTN)
    ├── I35, I36: INVD4 (MSB DCTRL buffers, invert DP/DN)
    ├── I26<11:0>: DFQD1 (output DFFs, clocked by RSTP)
    ├── I2: ND2D0, I4: NR2D0, I5: BUFFD0, I6: BUFFD2 (CMPCK chain)
    ├── I9: NR2D0, I11: NR2D1, I13: BUFFD2 (RSTN generation)
    ├── I3: BUFFD2 (VALID generation)
    ├── I24: NR2D0, I25: ND2D0 (GATE/STOP end-of-conversion)
    └── I37-I39: DCAP4/DCAP8 (decoupling, 50 instances total)
```

---

## Port Mapping Table (L3_SAR_11B)

| External Port | Direction | I_CMP | I_LOGIC | I_CDACP | I_CDACN | I7 (BTS) |
|--------------|-----------|-------|---------|---------|---------|----------|
| VIP | inout | -- | -- | VIN | VINB | VIP |
| VIN | inout | -- | -- | VINB | VIN | VIN |
| VDD | inout | VDD | VDD | VDD | VDD | VDD |
| VSS | inout | VSS | VSS | VSS | VSS | VSS |
| VREFP | inout | -- | VREFP | VREFP | VREFP | -- |
| VREFN | inout | -- | VREFN | -- | -- | -- |
| CLKS | inout | -- | CLKS | -- | -- | CLKS |
| RSTP | inout | -- | RSTP | -- | -- | -- |
| TRIM_OS<3:0> | inout | TRIM_OS<3:0> | -- | -- | -- | -- |
| DOUT<11:0> | inout | -- | DOUT<11:0> | -- | -- | -- |

### Internal Cross-Connections

| Signal | From | To | Notes |
|--------|------|----|-------|
| VTOPP | I_CDACP.VTOP | I_CMP.VINP | P-side top plate → comparator + input |
| VTOPN | I_CDACN.VTOP | I_CMP.VINN | N-side top plate → comparator - input |
| VBTSP | I7.VBTSP | I_CDACP.VGBTS | Bootstrap gate voltage for P-side |
| VBTSN | I7.VBTSN | I_CDACN.VGBTS | Bootstrap gate voltage for N-side |
| CMPCK | I_LOGIC.CMPCK | I_CMP.CLK | SAR logic fires comparator |
| DCMPP | I_CMP.DCMPP | I_LOGIC.DCMPP | Comparator decision (positive) |
| DCMPN | I_CMP.DCMPN | I_LOGIC.DCMPN | Comparator decision (negative) |
| VBOTP<11:1> | I_LOGIC.VBOTP<11:1> | I_CDACP.VBOT<11:1> | DAC feedback to P-side |
| VBOTN<11:1> | I_LOGIC.VBOTN<11:1> | I_CDACN.VBOT<11:1> | DAC feedback to N-side |
| DCTRLP<11:0> | I_LOGIC internal | noConn (external) | Monitor only |
| DCTRLN<11:0> | I_LOGIC internal | noConn (external) | Monitor only |
| LM, LP | I_CMP.LM, I_CMP.LP | noConn | Latch monitor outputs |

---

## Simulation Parameters (Reference Testbench _TB_SAR)

| Parameter | Value | Description |
|-----------|-------|-------------|
| Fs | 250 MHz | Sample rate |
| N | 128 | FFT points / conversion cycles |
| N_extra | 5 | Extra settling cycles before measurement |
| cycle | 11 | Input signal cycles in N samples |
| Fin | 21.484 MHz | Input frequency (= cycle/N × Fs, coherent) |
| AIN1 | 0.85 V | Differential input amplitude |
| VDD | 0.9 V | Supply voltage |
| VTEST | 0.9 V | DC test voltage (for step response) |
| TRIM_OS | 7 | Offset trim mid-code (4-bit, range 0-15) |
| t_end | 532 ns | Simulation duration (= (N+N_extra)/Fs) |

### Input Signal Setup

```
Differential sine (coherent sampling):
  V20: VIP = VDD/2 + (AIN1/2) × sin(2π × Fin × t)
  V21: VIN = VDD/2 - (AIN1/2) × sin(2π × Fin × t)

Sample clock:
  V22 → BUFFD4 → CLKS
  Period = 1/Fs = 4 ns, pulse width ≈ 1 ns (25% duty), tr = tf = 10 ps

References:
  VREFP = VDD = 0.9V (via _TU_REF_GEN, zero-ohm resistor to VDD source)
  VREFN = 0V          (via _TU_REF_GEN, zero-ohm resistor to ground)
```

### Process and Models

```
PDK: TSMC 28nm HPC+ ULL (CRN28HPC+ULL v1.8)
Corner: TT (typical-typical)
Model sections: pre_simu, noise_worst, ttmacro_mos_moscap, tt_res_bip_dio_disres,
                tt_mom, tt_ind_jvar, tt_r_metal
Standard cells: tcbn28hpcplusbwp12t30p140 (12-track, 30-pitch, 140-height)
```
