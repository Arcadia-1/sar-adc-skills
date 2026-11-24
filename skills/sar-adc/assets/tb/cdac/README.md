# Process-Independent CDAC Testbench Suite (Spectre)

Standalone, PDK-agnostic Spectre testbenches and analyzer for verifying capacitive DAC static linearity (DNL/INL), common-mode shift, worst-case MSB settling, sub-radix-2 redundancy recovery, and foreground digital weight calibration.

## Files

| File | Purpose | Key Metrics |
|---|---|---|
| `tb_cdac_static_dnl_inl.scs` | Sweeps all 512 unique 9-bit differential CDAC states via `va_code_ramp_10b.va` | `DNL_max/min`, `INL_max/min`, `full_scale_v`, `vcm_shift_mv` |
| `tb_cdac_settling.scs` | Worst-case MSB switch step transient | `delta_v_msb_v`, `delta_vcm_mv`, `t_settle_0p5lsb_ps` |
| `tb_cdac_mismatch_redundancy.scs` | 11-trial sub-radix-2 redundant CDAC (`+56 LSB` MSB margin) with injected MSB error + capacitor mismatch (`dm10..dm7`) | Redundancy `ENOB` & ramp `missing_codes`, uncalibrated vs. foreground least-squares calibrated `INL`/`SFDR`/`ENOB` & estimated `%` mismatch |
| `analyze_cdac.py` | Standalone PSF ASCII analyzer (`static`, `settling`, and `mismatch_cal` modes) | JSON summary |

## DUT Interface Contracts

### Standard 10-bit Binary CDAC (`dut_cdac`)

Provide `models_corner.scs` and `dut_subckt.scs` defining:

```spectre
subckt dut_cdac VIP VIN CLKS \
    DCTRLP9 DCTRLP8 DCTRLP7 DCTRLP6 DCTRLP5 DCTRLP4 DCTRLP3 DCTRLP2 DCTRLP1 \
    DCTRLN9 DCTRLN8 DCTRLN7 DCTRLN6 DCTRLN5 DCTRLN4 DCTRLN3 DCTRLN2 DCTRLN1 \
    VCP VCN VDD VSS
    // instantiate your differential CDAC (or wrap ../../va/behavioral_10b/va_cdac_10b_diff.va)
ends dut_cdac
```

### 11-Trial Sub-Radix-2 Redundant CDAC (`dut_cdac_red`)

Used by `tb_cdac_mismatch_redundancy.scs` (10 switched bit pairs `[10:1]`, nominal weights `{232, 128, 72, 40, 22, 12, 6, 4, 2, 1}`):

```spectre
subckt dut_cdac_red VIP VIN CLKS \
    DCTRLP10 DCTRLP9 DCTRLP8 DCTRLP7 DCTRLP6 DCTRLP5 DCTRLP4 DCTRLP3 DCTRLP2 DCTRLP1 \
    DCTRLN10 DCTRLN9 DCTRLN8 DCTRLN7 DCTRLN6 DCTRLN5 DCTRLN4 DCTRLN3 DCTRLN2 DCTRLN1 \
    VCP VCN VDD VSS
    // wrap va_cdac_10b_redundant (passing dm10_pct..dm7_pct and v_msb_err) or your transistor redundant CDAC
ends dut_cdac_red
```

> **Note for non-reversible transistor switching arrays**: If your CDAC switches cannot toggle back to reset state without a fresh `CLKS` pulse, pulse `CLKS` before each code in `tb_cdac_static_dnl_inl.scs` (or apply a monotonic Gray/reset sequence).

## Typical Pass Criteria

- **Static linearity (10-bit)**: `|DNL| < 0.5 LSB`, `|INL| < 0.5–1.0 LSB` (without calibration); verify across Monte Carlo capacitor mismatch.
- **MSB settling**: `t_settle_0p5lsb < t_dac_budget` (with `> 20%` slow-corner margin; relaxed when sub-radix-2 redundancy absorbs early settling error).
- **Redundancy & foreground calibration**: Zero missing codes under MSB decision errors within `+/-R_MSB` (`+/-56 LSB` here); foreground sine-wave least-squares calibration recovers `INL < 0.25 LSB` and `SFDR` by `> 20 dB` under `2–3%` MSB capacitor mismatch.
- **Common-mode shift**: Near-zero for Vcm-based/split switching; expected `~Vref/2` downward ramp for monotonic switching (must stay inside comparator input CM range).
