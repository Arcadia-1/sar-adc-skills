# Process-Independent LDO Testbench Suite (Spectre)

Standalone, PDK-agnostic Spectre testbenches and analyzer for verifying an ADC supply LDO regulator across stability, supply rejection, output noise, and fast load steps.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_ldo_stb.scs` | `dc` + `stb` (`iprobe`) | `dc_loop_gain_db`, `ugf_mhz`, `phase_margin_deg`, `gain_margin_db` |
| `tb_ldo_psrr_noise.scs` | `ac` + `noise` | `psrr_dc_db`, `psrr_1mhz_db`, `psrr_100mhz_db`, `psrr_min_db`, `output_noise_uvrms` |
| `tb_ldo_load_tran.scs` | `tran` load step | `load_reg_mv`, `undershoot_mv`, `overshoot_mv` |
| `analyze_ldo.py` | Standalone PSF ASCII analyzer (`stb`, `psrr_noise`, `load_tran`) | JSON summary |

## DUT Interface Contract

Provide `models_corner.scs` and `dut_subckt.scs` defining a 5-pin LDO with an explicit breakable feedback sense pin `FB_IN`:

```spectre
subckt dut_ldo VDD VREF VOUT FB_IN VSS
    // Tie FB_IN to the error-amplifier feedback input (or feedback divider input)
    // so tb_ldo_stb.scs can insert `IPRB (VOUT FB_IN) iprobe` cleanly.
ends dut_ldo
```

## Typical Pass Criteria (SAR ADC Clean Supply)

- **Stability (`ILOAD_MIN` to `ILOAD_MAX`, all PVT)**: `PM >= 60 deg` (`>= 45 deg` worst-case corner), `GM >= 10 dB`.
- **DC Loop Gain**: `T0 >= 40–60 dB` (keeps static load regulation and DC PSRR tight).
- **PSRR**: `>= 40 dB` at low frequency; verify decoupling capacitor `CLOAD` + `RESR` prevent peaking at the ADC clock frequency.
- **Transient Droop**: `undershoot_mv` stays well within comparator/CDAC supply headroom and recovers between bursts.
