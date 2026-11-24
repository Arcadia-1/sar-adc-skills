# SerDes Slicer & 3-Tap DFE Spectre X Testbench Suite

Process-independent Spectre X (`+preset=cx` / `+preset=ax`) decks and analyzer for CML/StrongARM data slicers (VTF, offset, hysteresis, transient-noise sensitivity) and closed-loop 3-tap Decision Feedback Equalizers.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_slicer_hys_vtf.scs` | Bidirectional triangle-ramp VTF sweep (`strobeoutput=strobeonly`) | `v_th_up_mv`, `v_th_dn_mv`, `offset_mv`, `hysteresis_mv`, `out_swing_diff_mv` |
| `tb_slicer_noise_tran.scs` | 300-cycle fixed-overdrive noise sensitivity `tran` (probit CDF inversion) | `p_one`, `z_probit`, `sigma_n_mvrms`, `ber_1e12_half_eye_mv` |
| `tb_dfe_3tap_eye.scs` | Closed-loop 3-tap DFE canceling a closed post-cursor ISI eye (`10 Gb/s` PRBS-7) | `before_dfe_eye` vs. `after_dfe_eye` (height/width), `bit_latency_ui`, `bit_errors` |
| `analyze_slicer_dfe.py` | Standalone PSF ASCII analyzer (`vtf`, `noise_tran`, `dfe_eye`) | JSON summary |

## DUT Interface Contracts

```spectre
// Clocked slicer / CML or StrongARM latch (tb_slicer_hys_vtf.scs, tb_slicer_noise_tran.scs)
subckt dut_slicer INP INN CLK VDD VSS DOUTP DOUTN
    // instantiate your transistor slicer (or wrap ../../va/va_slicer_cml.va)
ends dut_slicer

// Closed-loop 3-tap DFE + slicers (tb_dfe_3tap_eye.scs)
subckt dut_dfe_3tap INP INN CLK H1 H2 H3 VREF_ERR VDD VSS SUMP SUMN DOUTP DOUTN ERRP ERRN
    // instantiate your transistor DFE (or wrap ../../va/va_dfe_3tap.va)
ends dut_dfe_3tap
```
