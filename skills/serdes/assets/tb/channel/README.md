# SerDes Channel Characterization Spectre Testbench Suite

Process-independent Spectre X (`+preset=cx` / `+preset=ax`) decks and analyzer for differential backplane/PCB channel S-parameters, TDR, Single-Bit Response (SBR), and PRBS eye characterization.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `channel_diff_lossy.scs` | Causal passive 100-ohm differential `mtline` model (skin effect + Djordjevic-Sarkar dielectric loss) | Reusable across `sp`, `ac`, `dc`, `noise`, and `tran` |
| `tb_channel_sp_tdr.scs` | 4-port `sp` (`10 MHz..20 GHz`) + differential TDR `tran` | `SDD21` at 1/5/7/10 GHz, worst `SDD11`, `Z_TDR` impedance plateau |
| `tb_channel_sbr_eye.scs` | Simultaneous 1-UI isolated pulse SBR + PRBS-7 eye `tran` (`10 Gb/s`) | Pre/main/post cursors (`h_-1, h0, h1..h5`), PDA eye height, TX/RX eye height `[mV]` & width `[UI/ps]` |
| `analyze_channel.py` | Standalone PSF ASCII analyzer (`sp`, `tdr`, `sbr_eye`) | JSON summary |

## DUT Interface Contract

```spectre
subckt dut_channel INP INN OUTP OUTN VSS
    // wrap channel_diff_lossy (or your Touchstone nport file="channel.s4p")
ends dut_channel
```
