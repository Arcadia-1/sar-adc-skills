# Process-Independent Bootstrapped Switch Testbench Suite (Spectre)

Standalone, PDK-agnostic Spectre decks and analyzer for verifying SAR ADC sampling switches (bootstrapped NMOS vs. plain NMOS / transmission gate).

## Files

| File | Purpose | Key Metrics |
|---|---|---|
| `tb_boot_ron_sweep.scs` | Clocked multi-step `Ron(VIN)` sweep across `[0, VDD]` (properly precharges flying bootstrap cap `CB` every cycle!) | `ron_min`, `ron_max`, `ron_max_over_min`, `ron_variation_pct` |
| `tb_boot_tran_linearity.scs` | Coherent Nyquist-rate sine sampling onto `CL` (`strobeoutput=strobeonly`, `conservative`) | `SFDR`, `THD`, `SNDR`, `ENOB` |
| `analyze_bootstrap.py` | Standalone PSF ASCII analyzer (`ron` and `linearity` modes) | JSON summary |

## DUT Interface Contract

Provide `models_corner.scs` (your PDK corner or `../common/models_generic_bsim4.scs`) and `dut_subckt.scs` next to the staged testbench:

```spectre
subckt dut_bootstrap CLKS VIN VOUT VDD VSS
    // instantiate your bootstrapped switch here (CLKS=VDD -> ON, CLKS=0 -> OFF)
ends dut_bootstrap
```

## Typical Pass Criteria (10–12 bit SAR Front End)

- **`Ron` flatness (`0.05*VDD .. 0.95*VDD`)**: `ron_max_over_min < 1.25` (bootstrapped), compared to `> 5x` or cutoff for a plain NMOS switch near `VDD - Vth`.
- **Sampling settling**: `tau = Ron_max * CL <= T_track / (N + 2) / ln(2)` (e.g., `<= T_track / 8.3` for 10-bit 0.5-LSB accuracy).
- **Dynamic linearity**: `SFDR >= 6.02*N + 12 dB` (at least 10–12 dB margin above the target ADC quantization/thermal noise floor).
