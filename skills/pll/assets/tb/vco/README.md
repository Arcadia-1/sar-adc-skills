# Process-Independent VCO Testbench Suite (Spectre)

Standalone, PDK-agnostic Spectre RF testbenches and analyzer for LC-VCO and Ring-VCO characterization.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_vco_tuning_kvco.scs` | Staircase `VCTRL` transient + `va_phase_err_mon.va` | `f_min`, `f_max`, `tuning_range_pct`, `kvco_avg/min/max`, `monotonic` |
| `tb_vco_pss_pnoise.scs` | Autonomous `pss (OUTP OUTN)` + relative `pnoise` (`noiseout=[pm]`, requires `+aps`) | `f0_ghz`, `vdiff_pp_v`, `p_dc_mw`, `L(100k/1M/10M)`, `FoM`, `rms_jitter_fs` |
| `analyze_vco.py` | Standalone PSF ASCII analyzer (`tuning` and `pss_pnoise` modes) | JSON summary |

## DUT Interface Contract

Provide `models_corner.scs` (your PDK or repo-root `common/models_generic_bsim4.scs`) and `dut_subckt.scs`:

```spectre
subckt dut_vco VCTRL OUTP OUTN VDD VSS
    // instantiate your LC-VCO, Ring-VCO, or wrap ../../va/va_vco.va
ends dut_vco
```
