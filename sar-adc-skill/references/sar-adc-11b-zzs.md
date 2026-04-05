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
