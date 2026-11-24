# SerDes End-to-End Full-Link Spectre X Testbench Suite

Process-independent Spectre X (`+preset=cx` / `+preset=ax`) top-level transceiver verification combining **TX FFE $\to$ Long-Reach Lossy Channel (~`-24 dB @ 5 GHz`) $\to$ RX CTLE/VGA $\to$ 3-Tap DFE $\to$ Slicer**.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_serdes_link_top.scs` | 220-UI PRBS-7 end-to-end link `tran` (`10 Gb/s`) | Stage-by-stage `tx_eye`, `after_channel_eye`, `after_ctle_eye`, `after_dfe_eye`, `link_latency_ui`, `bit_errors` |
| `analyze_link_top.py` | Standalone PSF ASCII analyzer | JSON summary |

## DUT Interface Contracts

Plug in any combination of behavioral Verilog-A (`../../va/`) and transistor-level blocks inside `dut_subckt.scs`:

```spectre
subckt dut_link_tx   INP INN CLK VDD VSS OUTP OUTN ... ends
subckt dut_link_ctle INP INN VBOOST VOFF_CAL VDD VSS OUTP OUTN ... ends
subckt dut_link_dfe  INP INN CLK H1 H2 H3 VREF_ERR VDD VSS SUMP SUMN DOUTP DOUTN ERRP ERRN ... ends
```
