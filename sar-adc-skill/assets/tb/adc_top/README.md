# Process-Independent Full SAR ADC Testbench Suite (Spectre)

Standalone, PDK-agnostic system-level Spectre testbenches and analyzer for phased SAR ADC verification (behavioral -> hybrid -> full transistor-level).

## Files

| File | Purpose | Key Metrics |
|---|---|---|
| `tb_sar_adc_fft.scs` | Coherent single-tone FFT (`strobeoutput=strobeonly`, `conservative`, optional `trannoise` with `noiseruns=1`) | `ENOB`, `SNDR`, `SNR`, `SFDR`, `THD`, `amp_dbfs`, clipping flag |
| `tb_sar_adc_ramp_dnl.scs` | Overdriven slow differential ramp sweep | Usable `VFS_diff`, missing codes, histogram `DNL` / `INL` |
| `analyze_adc_top.py` | Standalone PSF ASCII analyzer (`fft` and `ramp` modes) | JSON summary |

## DUT Interface Contract

Provide `models_corner.scs` and `dut_subckt.scs` defining a 10-bit fully differential SAR ADC:

```spectre
subckt dut_sar_adc VIP VIN CLKS \
    DOUT9 DOUT8 DOUT7 DOUT6 DOUT5 DOUT4 DOUT3 DOUT2 DOUT1 DOUT0 \
    VDD VSS
    // Phase 1 (behavioral): assemble va_cdac_10b_diff + va_cmp_dynamic + va_sar_logic_10b_async
    // Phase 2 (hybrid): swap one block at a time with your transistor subcircuit
    // Phase 3 (full): instantiate your complete transistor SAR ADC core
ends dut_sar_adc
```

## Notes

- Run Spectre with `+aps` (not `+mx`) to avoid ~0.3-bit ENOB degradation from coarse simulator tolerances.
- For deeper FFT diagnostics (harmonic spurs, noise-floor breakdown, INL-from-sine), export `CODE` directly to [ADCToolbox](https://github.com/Arcadia-1/ADCToolbox).
