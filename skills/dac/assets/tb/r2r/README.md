# R-2R Ladder DAC Spectre Testbench Suite

Process-independent Spectre decks and zero-dependency analyzer for 8-bit voltage-mode (or buffered current-mode) R-2R ladder DACs.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_r2r_static.scs` | 256-code sequential sweep (`strobeoutput=strobeonly`) | `full_scale_v`, `lsb_mv`, `zero_code_mv`, `gain_err_pct`, `dnl_max/min`, `inl_max/min`, `monotonic` |
| `tb_r2r_settle.scs` | Full-scale (`0 -> 255`) + major-carry (`127 -> 128`) settling `tran` | `fs_step_v`, `fs_t_settle_0p5lsb_ns`, `mc_step_mv`, `mc_t_settle_0p5lsb_ns` |
| `analyze_r2r.py` | Standalone PSF ASCII analyzer (`static`, `settle`) | JSON summary |

## DUT Interface Contract

Provide `models_corner.scs` and `dut_subckt.scs` defining:

```spectre
subckt dut_r2r_dac DIN7 DIN6 DIN5 DIN4 DIN3 DIN2 DIN1 DIN0 VREF VSS VOUT
    // instantiate your transistor/resistor R-2R DAC (or wrap ../../va/va_dac_r2r_8b.va)
ends dut_r2r_dac
```
