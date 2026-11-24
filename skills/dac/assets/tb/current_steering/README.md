# Current-Steering DAC Spectre Testbench Suite

Process-independent Spectre decks and zero-dependency analyzer for 10-bit differential current-steering DACs.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_dac_static_dnl_inl.scs` | 1024-code sequential sweep (`strobeoutput=strobeonly`) | `full_scale_v`, `lsb_mv`, `dnl_max/min`, `inl_max/min`, `monotonic`, `offset_mv` |
| `tb_dac_dynamic_sfdr.scs` | Coherent single-tone (`sig_mode=0`) or two-tone IMD3 (`sig_mode=1`) `tran` | Single-tone: `sfdr_db`, `hd2_dbc`, `hd3_dbc`, `thd_db`, `sndr_db`, `enob`; Two-tone: `im3_lo_dbc`, `im3_hi_dbc`, `imd3_dbc`, `sfdr_db` |
| `tb_dac_glitch_settle.scs` | Fine-timestep (`maxstep=5p`) major-carry `511 -> 512` & `512 -> 511` `tran` | `rise/fall_glitch_peak_mv`, `rise/fall_glitch_impulse_pvs`, `rise/fall_t_settle_0p5lsb_ns` |
| `analyze_cs_dac.py` | Standalone PSF ASCII analyzer (`static`, `dynamic`, `twotone`, `glitch`) | JSON summary |

## DUT Interface Contract

Provide `models_corner.scs` and `dut_subckt.scs` defining:

```spectre
subckt dut_cs_dac DIN9 DIN8 DIN7 DIN6 DIN5 DIN4 DIN3 DIN2 DIN1 DIN0 VDD VSS IOUTP IOUTN
    // instantiate your transistor CS-DAC (or wrap ../../va/va_dac_cs_10b.va)
ends dut_cs_dac
```

The testbenches terminate `IOUTP` and `IOUTN` with matched load resistors `rload` (default `50 ohm` to `VSS`, plus optional `cload`) and evaluate differential output `V_diff = V(IOUTP) - V(IOUTN)`. For continuous-time RF DAC harmonic measurements including ZOH sinc roll-off and switching glitch energy, set `osr > 1` (e.g., `strobeperiod = ts / 8`) and pass `--n-fft` accordingly.
