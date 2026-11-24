# Process-Independent SAR Logic Testbench Suite (Spectre)

Standalone, PDK-agnostic closed-loop timing and race verification testbench for synchronous or asynchronous SAR logic.

## Files

| File | Purpose | Key Checks |
|---|---|---|
| `tb_sar_logic_timing.scs` | Multi-frame closed-loop test pairing your SAR logic with `va_cmp_dynamic.va` and `va_cdac_10b_diff.va` (including a `0.1 mV` near-metastable MSB frame) | Exact `N` `CMPCK` pulses, clean `EOC` / `NOR3` stop, `t_conv`, timing slack, decoded code error |
| `analyze_sar_logic.py` | Standalone PSF ASCII analyzer | Per-frame JSON pass/fail report |

## DUT Interface Contract

Provide `models_corner.scs` and `dut_subckt.scs` defining:

```spectre
subckt dut_sar_logic CLKS DCMPP DCMPN CMPCK EOC \
    DOUT9 DOUT8 DOUT7 DOUT6 DOUT5 DOUT4 DOUT3 DOUT2 DOUT1 DOUT0 \
    DCTRLP9 DCTRLP8 DCTRLP7 DCTRLP6 DCTRLP5 DCTRLP4 DCTRLP3 DCTRLP2 DCTRLP1 \
    DCTRLN9 DCTRLN8 DCTRLN7 DCTRLN6 DCTRLN5 DCTRLN4 DCTRLN3 DCTRLN2 DCTRLN1 \
    VDD VSS
    // instantiate your transistor SAR logic (or wrap ../../va/behavioral_10b/va_sar_logic_10b_async.va)
ends dut_sar_logic
```

## Recommended Stress Sweeps

1. **Fast comparator (`cmp_td_min=15p`, `cmp_td_rst=10p`) at FF/high-VDD**: exposes `VALID_L`-vs-`EN` race conditions (double-firing or skipped bit tokens).
2. **Slow comparator (`cmp_td_min=120p`, `cmp_tau=35p`) at SS/low-VDD**: verifies `t_conv < (ts - t_track)` with positive timing slack.
3. **Near-metastable input (`Frame 2: Vid = +0.1 mV`)**: verifies bit-time borrowing in async loops without hang or false `EOC`.
