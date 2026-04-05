# SAR ADC Top-Level Integration Reference

This document describes how the major modules of a fully-differential SAR ADC connect and interact, using the taped-out SAR_11B_ZZS (TSMC 28nm HPC+, 0.9V, 11-bit) as the primary reference design. The goal is to provide enough detail to wire up a complete SAR ADC from individual module designs, or to write a top-level netlist from scratch.

---

## 1. Module Inventory

A fully-differential SAR ADC requires five functional blocks:

| Module | Instance(s) | Cell | Function |
|--------|------------|------|----------|
| Bootstrap | I7 | L4_BTS_X2 | Generates VBTSP, VBTSN gate voltages for CDAC sampling switches |
| CDAC (P-side) | I_CDACP | L4_CDAC | Samples VIP, performs charge redistribution on P-side |
| CDAC (N-side) | I_CDACN | L4_CDAC | Samples VIN, performs charge redistribution on N-side |
| Comparator | I_CMP | L4_COMPARATOR | Compares VTOPP vs VTOPN, outputs DCMPP/DCMPN |
| SAR Logic + DAC Switches | I_LOGIC | L4_LOGIC_SWI | Async latch chain, generates DCTRL, drives VBOT, outputs DOUT |

The bootstrap module L4_BTS_X2 contains two instances of LB_SAR_BTS (one per input channel).

---

## 2. Top-Level Signal Flow

```
External inputs:
  VIP, VIN        (differential analog input)
  CLKS             (sample clock)
  VREFP, VREFN     (reference voltages, typically VDD and VSS)
  TRIM_OS<3:0>     (comparator offset trim)
  RSTP             (reset, active polarity depends on logic)

Signal flow:

  VIP ──────┬──────────────────────────> I_CDACP.VIN    (direct connection)
            ├──────────────────────────> I_CDACN.VINB   (cross-connection!)
            └──> I7.VIP ──> I7.VBTSP ──> I_CDACP.VGBTS (bootstrap gate)

  VIN ──────┬──────────────────────────> I_CDACN.VIN    (direct connection)
            ├──────────────────────────> I_CDACP.VINB   (cross-connection!)
            └──> I7.VIN ──> I7.VBTSN ──> I_CDACN.VGBTS (bootstrap gate)

  I_CDACP.VTOP = VTOPP ──> I_CMP.VINP
  I_CDACN.VTOP = VTOPN ──> I_CMP.VINN

  I_CMP.DCMPP ──> I_LOGIC.DCMPP
  I_CMP.DCMPN ──> I_LOGIC.DCMPN

  I_LOGIC.CMPCK ──> I_CMP.CLK
  I_LOGIC.VBOTP<11:1> ──> I_CDACP.VBOT<11:1>
  I_LOGIC.VBOTN<11:1> ──> I_CDACN.VBOT<11:1>

  CLKS ──> I7.CLKS  (bootstrap clock)
  CLKS ──> I_LOGIC.CLKS  (SAR logic clock)

  I_LOGIC.DOUT<11:0> ──> external digital output
```

---

## 3. Critical Cross-Connections

### Differential CDAC Input Wiring

This is the most common wiring mistake. Each CDAC receives BOTH inputs, with opposite polarity:

```
I_CDACP:  VIN  = VIP    (positive input to P-side main switch)
          VINB = VIN    (negative input to P-side dummy switch)

I_CDACN:  VIN  = VIN    (negative input to N-side main switch)
          VINB = VIP    (positive input to N-side dummy switch)
```

The cross-connection serves two purposes:
1. The main sampling switch (M3) samples the correct polarity input
2. The dummy switch (M4, connected to VINB) provides complementary charge cancellation

### Bootstrap Output is Gate Voltage, Not Sampled Voltage

The bootstrap module outputs VBTSP and VBTSN, which are gate voltages (VIN + VDD). These connect to the CDAC's VGBTS port, which drives the gate of the internal sampling NMOS. The bootstrap does NOT output a sampled or buffered version of VIN.

```
I7.VBTSP = VBTSP ──> I_CDACP.VGBTS   (gate of M3 inside CDAC_P)
I7.VBTSN = VBTSN ──> I_CDACN.VGBTS   (gate of M3 inside CDAC_N)
```

VIP and VIN connect directly to the CDAC sampling switch source terminals. There is no S&H buffer between input and CDAC.

### Comparator Sees Differential Top Plates

The comparator input is NOT VTOP vs VCM. It is the true differential pair:

```
I_CMP.VINP = VTOPP  (from I_CDACP.VTOP)
I_CMP.VINN = VTOPN  (from I_CDACN.VTOP)
```

### SAR Logic Generates Comparator Clock

The comparator clock (CMPCK) is generated internally by the SAR logic, not from an external source. This is the hallmark of asynchronous SAR operation:

```
I_LOGIC.CMPCK ──> I_CMP.CLK
```

The logic fires CMPCK after each bit's DAC settling is complete, then waits for the comparator decision before proceeding to the next bit.

---

## 4. Port Mapping Tables

### L3_SAR_11B External Ports

| Port | Direction | Description | Typical Connection |
|------|-----------|-------------|-------------------|
| VIP | inout | Positive differential input | Sine source, VDD/2 + signal |
| VIN | inout | Negative differential input | Sine source, VDD/2 - signal |
| VDD | inout | Supply | 0.9V |
| VSS | inout | Ground | 0V |
| VREFP | inout | Positive reference | VDD (0.9V) |
| VREFN | inout | Negative reference | VSS (0V) |
| CLKS | inout | Sample clock | External, pulse with duty ~25% |
| RSTP | inout | Reset | Active-low (inverted internally to RSTN) |
| TRIM_OS<3:0> | inout | Offset trim code | 4-bit binary, 7 = mid-code (nominal) |
| DOUT<11:0> | inout | Digital output | Latched on RSTP (=CLKS) rising edge |

### L4_CDAC Ports

| Port | Connected To (P-side) | Connected To (N-side) |
|------|----------------------|----------------------|
| VIN | VIP | VIN |
| VINB | VIN | VIP |
| VGBTS | VBTSP | VBTSN |
| VTOP | VTOPP (to I_CMP.VINP) | VTOPN (to I_CMP.VINN) |
| VBOT<11:1> | VBOTP<11:1> (from I_LOGIC) | VBOTN<11:1> (from I_LOGIC) |
| VREFP | VREFP | VREFP |
| VDD | VDD | VDD |
| VSS | VSS | VSS |

CDF parameter: `Cunit="3.3f"` (unit capacitance for simulation)

### L4_COMPARATOR Ports

| Port | Connected To |
|------|-------------|
| VINP | VTOPP |
| VINN | VTOPN |
| CLK | CMPCK (from I_LOGIC) |
| DCMPP | I_LOGIC.DCMPP |
| DCMPN | I_LOGIC.DCMPN |
| LM | noConn (monitor only) |
| LP | noConn (monitor only) |
| TRIM_OS<3:0> | External trim code |
| VDD | VDD |
| VSS | VSS |

CDF parameter: `td_cmp="30p"` (comparator delay for behavioral model)

### L4_BTS_X2 Ports

| Port | Connected To |
|------|-------------|
| VIP | VIP (external) |
| VIN | VIN (external) |
| CLKS | CLKS (external) |
| VBTSP | I_CDACP.VGBTS |
| VBTSN | I_CDACN.VGBTS |
| VDD | VDD |
| VSS | VSS |

Internally contains two LB_SAR_BTS instances:
- I0: VIN=VIP, VBST=VBTSP, CLK=CLKS
- I2: VIN=VIN, VBST=VBTSN, CLK=CLKS

### L4_LOGIC_SWI Ports

| Port | Connected To |
|------|-------------|
| CLKS | CLKS (external) |
| DCMPP | I_CMP.DCMPP |
| DCMPN | I_CMP.DCMPN |
| CMPCK | I_CMP.CLK |
| DCTRLP<11:0> | Internal (DFF input, MSB buffered via INVD4) |
| DCTRLN<11:0> | Internal (MSB buffered via INVD4) |
| VBOTP<11:1> | I_CDACP.VBOT<11:1> |
| VBOTN<11:1> | I_CDACN.VBOT<11:1> |
| DOUT<11:0> | External digital output |
| RSTP | External reset / DFF clock |
| VREFP | VREFP |
| VREFN | VREFN |
| VDD | VDD |
| VSS | VSS |

---

## 5. Module Hierarchy

```
L3_SAR_11B
├── I7: L4_BTS_X2
│   ├── I0: LB_SAR_BTS  (for VIP → VBTSP)
│   └── I2: LB_SAR_BTS  (for VIN → VBTSN)
├── I_CDACP: L4_CDAC
│   ├── M3: nch_mac  (sampling switch, G=VGBTS, S=VIN)
│   ├── M4: nch_mac  (dummy switch, G=net1, S=VINB)
│   ├── M2, M5: nch_ulvt_mac  (cascode for dummy gate)
│   └── I93: L5_CAP_ARRAY
│       ├── I0: LB_CUNIT_X1  (dummy cap, BOT=VREFP)
│       ├── I1: LB_CUNIT_X1  (bit 1)
│       ├── I2<2:1>: LB_CUNIT_X1  (bit 2)
│       ├── I3..I11: LB_CUNIT_X3  (bits 3-11, scaled counts)
│       └── I12<9:1>: LB_CUNIT_X3  (layout dummy caps)
├── I_CDACN: L4_CDAC  (same structure, opposite input polarity)
├── I_CMP: L4_COMPARATOR
│   ├── Tail: M88 (nch_ulvt, W=2u, NF=4)
│   ├── Input pair: M0/M1 (nch_ulvt, W=16u, NF=32)
│   ├── NMOS latch: M45/M6 (nch_ulvt, W=4u, NF=8)
│   ├── PMOS latch: M48/M49 (pch_ulvt, W=4u, NF=8)
│   ├── PMOS reset: M4/M5/M7/M50 (pch_ulvt, W=2u, NF=4)
│   ├── Cross-connect reset: M79 (pch_ulvt, W=500n, NF=1)
│   ├── Buffer: M10/M16 + M19/M21 (inverters for LM→net1, LP→net2)
│   ├── Output: M78/M106 + M77/M105 (DCMPP, DCMPN drivers)
│   ├── Offset trim: M107-M110/M118-M120/M117 (on VINP side)
│   ├── Dummy trim: M121-M128/M122-M125 (on VINN side)
│   ├── ESD clamps: M2/M23 (nch_ehvt, L=1u)
│   └── Stabilization caps: C0-C12
└── I_LOGIC: L4_LOGIC_SWI
    ├── I_LATCH_CELL<11>: L5_LATCH_CELL  (MSB)
    ├── I_LATCH_CELL<10:1>: L5_LATCH_CELL  (bits 10-1)
    ├── I_LATCH_CELL<0>: L5_LATCH_CELL_LSB  (LSB)
    ├── I0: L5_DAC_SWI  (P-side DAC switches, DCTRLP → VBOTP)
    ├── I1: L5_DAC_SWI  (N-side DAC switches, DCTRLN → VBOTN)
    ├── I26<11:0>: DFQD1BWP12T30P140  (output DFFs)
    ├── I35/I36: INVD4BWP12T30P140  (MSB DCTRL buffers)
    ├── CMPCK generation: I2→I4→I5→I6 (NAND/NOR/BUF chain)
    ├── RSTN generation: I9→I11→I13 (NOR/BUF chain)
    ├── VALID generation: I2→I3 (NAND/BUF)
    ├── Decoupling: I39<36:1>, I37<4:1> (DCAP4), I38<10:1> (DCAP8)
    └── GATE/STOP logic: I24, I25 (NOR/NAND for conversion end)
```

---

## 6. Comparator Polarity and Logic Interface

### Important: DCMPP Falls When VINP > VINN

The StrongArm comparator resets both outputs (DCMPP, DCMPN) to VDD during CLK=low. During evaluation (CLK=high), one output falls to VSS while the other stays near VDD. The output that falls corresponds to the winning input:

```
VINP > VINN  →  DCMPP falls (goes low), DCMPN stays high
VINP < VINN  →  DCMPN falls (goes low), DCMPP stays high
```

The SAR logic latch cells read DCMPP/DCMPN directly. Note a critical detail in the ZZS implementation: at the MSB latch cell (I_LATCH_CELL<11>), the comparator outputs are **swapped**:

```
I_LATCH_CELL<11>:  DCMPP port = DCMPN net,  DCMPN port = DCMPP net
```

This swap at the MSB implements the correct sign convention for the first bit trial. For bits 10 down to 0, DCMPP/DCMPN connect with normal polarity.

---

## 7. Testbench Setup (Reference: _TB_SAR)

### Input Sources

```
Differential sine input:
  V20: VIP = VDD/2 + (AIN1/2) × sin(2π × Fin × t)    (vsin, acm=+1)
  V21: VIN = VDD/2 - (AIN1/2) × sin(2π × Fin × t)    (vsin, acm=-1)

  where Fin = cycle/N × Fs  (coherent sampling)
```

### Clock Generation

```
V22: vpulse, v1=0, v2=VDD, per=1/Fs, pw=1/Fs/4 - 50p, tr=tf=10p
     → buffered through BUFFD4 (I235) → CLKS

Duty cycle: ~25% high (sample phase is short relative to conversion)
```

### Reference Voltages

```
I233: _TU_REF_GEN
  VREFP = VDD (via R0 to VDD source)
  VREFN = 0   (via R1 to ground source)
```

### Simulation Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Fs | 250 MHz | Sample rate |
| N | 128 | Number of FFT points (conversion cycles) |
| N_extra | 5 | Extra settling cycles |
| cycle | 11 | Input signal cycles within N samples |
| AIN1 | 0.85 | Differential input amplitude (V) |
| VDD | 0.9 | Supply voltage |
| VTEST | 0.9 | Test voltage for DC sweeps |
| TRIM_OS | 7 | Offset trim (mid-code for nominal) |
| t_end | (N + N_extra) / Fs | Simulation end time |
| Fin | cycle/N × Fs = 11/128 × 250M = 21.484 MHz | Input frequency (coherent) |

### Additional Testbench Components

- `I_DAC` (_VA_DAC_11B): Verilog-A ideal DAC for monitoring reconstructed analog output (AOUT), clocked by CLKS
- `I110` (_va_d2b_encoder_4b): Converts TRIM_OS integer parameter to 4-bit binary for TRIM_OS<3:0> pins
- `V10`, `V12`: Alternative DC test sources (vpulse, for step-response or DC-sweep testing)

### RSTP Connection

In the testbench, RSTP is left as an iopin but is connected to the DFF clock inside the logic. In the ZZS implementation, RSTP is derived from CLKS internally (via the I12 inverter chain producing RSTP from the NOR-based reset logic). The DFFs (I26<11:0>) are clocked by RSTP, which triggers on the rising edge to latch DOUT at the end of conversion.

---

## 8. Common Integration Mistakes

| Mistake | Consequence | How to Avoid |
|---------|-------------|--------------|
| CDAC VIN/VINB not cross-connected | Both CDACs sample same polarity | Check: I_CDACP.VINB = VIN, I_CDACN.VINB = VIP |
| Bootstrap output treated as sampled voltage | Missing sampling switch, no CDAC function | VBST goes to VGBTS (gate), VIN goes directly to CDAC |
| Comparator driven by VTOP vs VCM | Single-ended comparison, 6dB signal loss | Wire VTOPP to VINP, VTOPN to VINN |
| CMPCK from external clock | Synchronous operation (slower, wastes time) | Let SAR logic generate CMPCK internally |
| Same DCTRL polarity to both CDACs | No differential feedback | P-side uses DCTRLP, N-side uses DCTRLN (complementary) |
| VREFN not connected to logic | DAC switches cannot pull to VREFN | I_LOGIC needs both VREFP and VREFN |
| DOUT latched on wrong clock edge | Captures mid-conversion data | Latch on RSTP (CLKS rising edge), after conversion completes |
| TRIM_OS not connected | Comparator offset may cause MSB error | Connect to mid-code (7 for 4-bit) or calibration output |
