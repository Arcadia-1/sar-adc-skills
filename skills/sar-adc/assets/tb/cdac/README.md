# Process-Independent CDAC Testbench Suite (Spectre)

Standalone, PDK-agnostic Spectre testbenches and analyzer for verifying capacitive DAC static linearity (DNL/INL), common-mode shift, and worst-case MSB settling.

## Files

| File | Purpose | Key Metrics |
|---|---|---|
| `tb_cdac_static_dnl_inl.scs` | Sweeps all 512 unique 9-bit differential CDAC states via `va_code_ramp_10b.va` | `DNL_max/min`, `INL_max/min`, `full_scale_v`, `vcm_shift_mv` |
| `tb_cdac_settling.scs` | Worst-case MSB switch step transient | `delta_v_msb_v`, `delta_vcm_mv`, `t_settle_0p5lsb_ps` |
| `analyze_cdac.py` | Standalone PSF ASCII analyzer (`static` and `settling` modes) | JSON summary |

## DUT Interface Contract

Provide `models_corner.scs` and `dut_subckt.scs` defining:

```spectre
subckt dut_cdac VIP VIN CLKS \
    DCTRLP9 DCTRLP8 DCTRLP7 DCTRLP6 DCTRLP5 DCTRLP4 DCTRLP3 DCTRLP2 DCTRLP1 \
    DCTRLN9 DCTRLN8 DCTRLN7 DCTRLN6 DCTRLN5 DCTRLN4 DCTRLN3 DCTRLN2 DCTRLN1 \
    VCP VCN VDD VSS
    // instantiate your differential CDAC (or wrap ../../va/behavioral_10b/va_cdac_10b_diff.va)
ends dut_cdac
```

> **Note for non-reversible transistor switching arrays**: If your CDAC switches cannot toggle back to reset state without a fresh `CLKS` pulse, pulse `CLKS` before each code in `tb_cdac_static_dnl_inl.scs` (or apply a monotonic Gray/reset sequence).

## Typical Pass Criteria

- **Static linearity (10-bit)**: `|DNL| < 0.5 LSB`, `|INL| < 0.5–1.0 LSB` (without calibration); verify across Monte Carlo capacitor mismatch.
- **MSB settling**: `t_settle_0p5lsb < t_dac_budget` (with `> 20%` slow-corner margin; relaxed when sub-radix-2 redundancy absorbs early settling error).
- **Common-mode shift**: Near-zero for Vcm-based/split switching; expected `~Vref/2` downward ramp for monotonic switching (must stay inside comparator input CM range).
