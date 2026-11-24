# Process-Independent VCO Testbench Suite (Spectre)

Standalone, PDK-agnostic Spectre RF & transient testbenches and analyzer for LC-VCO and Ring-VCO characterization, including multi-sub-band capacitor-bank overlap signoff.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_vco_tuning_kvco.scs` | Staircase `VCTRL` transient + `va_phase_err_mon.va` | `f_min`, `f_max`, `tuning_range_pct`, `kvco_avg/min/max`, `monotonic` |
| `tb_vco_pss_pnoise.scs` | Autonomous `pss (OUTP OUTN)` + relative `pnoise` (`noiseout=[pm]`, requires `+aps`) | `f0_ghz`, `vdiff_pp_v`, `p_dc_mw`, `L(100k/1M/10M)`, `FoM`, `rms_jitter_fs` |
| `tb_vco_capbank_overlap.scs` | 8-sub-band `alter` (`VCODE = 0..7`) × 7-pt `VCTRL` staircase transient | Per-band `K_VCO` & endpoint linearity `K_LIN (%)`, adjacent `overlap_pct`, `blind_hole_count`, `overlap_pass` |
| `analyze_vco.py` | Standalone PSF ASCII analyzer (`tuning`, `pss_pnoise`, and `capbank` modes) | JSON summary |

## DUT Interface Contracts

Provide `models_corner.scs` (your PDK or repo-root `common/models_generic_bsim4.scs`) and `dut_subckt.scs`:

### Single-Band VCO (`tb_vco_tuning_kvco.scs`, `tb_vco_pss_pnoise.scs`)
```spectre
subckt dut_vco VCTRL OUTP OUTN VDD VSS
    // instantiate your LC-VCO, Ring-VCO, or wrap ../../va/va_vco.va
ends dut_vco
```

### Multi-Sub-Band VCO (`tb_vco_capbank_overlap.scs`)
```spectre
subckt dut_vco_mb VCTRL VCODE OUTP OUTN VDD VSS
    // instantiate your switched-cap LC-VCO or wrap ../../va/va_vco_multiband.va
ends dut_vco_mb
```
