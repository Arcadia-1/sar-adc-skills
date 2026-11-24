# SerDes TX Driver & FFE Spectre Testbench Suite

Process-independent Spectre X (`+preset=cx` / `+preset=ax`) decks and analyzer for CML/VML TX output return loss (`SDD11`) and 4-tap TX FFE channel equalization.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_tx_s11.scs` | 2-port differential `sp` (`10 MHz..20 GHz`) | `sdd11_1/5/10ghz_db`, `sdd11_worst_to_5/10ghz_db` |
| `tb_tx_ffe_channel.scs` | PRBS-7 eye + isolated 1-UI SBR through `channel_diff_lossy.scs` | `tx_swing_pp_mv`, `rx_eye` (height/width), `rx_sbr` (`h_-1, h0, h1..h5`, PDA eye) |
| `analyze_tx_ffe.py` | Standalone PSF ASCII analyzer (`s11`, `eye`) | JSON summary |

## DUT Interface Contract

```spectre
subckt dut_tx INP INN CLK VDD VSS OUTP OUTN
    // instantiate your CML/VML TX + FFE (or wrap ../../va/va_tx_ffe_4tap.va)
ends dut_tx
```
