# SerDes TX Driver & FFE Spectre X Testbench Suite

Process-independent Spectre X (`+preset=cx` / `+preset=ax`) decks and analyzer for CML/VML TX output return loss (`SDD11`), DC termination linearity (`R_term(V)`), and 4-tap TX FFE channel equalization.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_tx_s11.scs` | 2-port differential `sp` (`10 MHz..20 GHz`) | `sdd11_1/5/10ghz_db`, `sdd11_worst_to_5/10ghz_db` |
| `tb_dc_termination.scs` | Output DC swing sweep (`v_min..v_max`) | `r_median_ohm`, `r_min/max_ohm`, `r_err_max_pct`, `r_flatness_pct` |
| `tb_tx_ffe_channel.scs` | PRBS-7 eye + isolated 1-UI SBR through `channel_diff_lossy.scs` | `tx_swing_pp_mv`, `rx_eye` (height/width), `rx_sbr` (`h_-1, h0, h1..h5`, PDA eye) |
| `tb_tx_cm_skew_sndr.scs` | 10 Gb/s PRBS-7 TX signoff into matched 50-ohm loads | 20–80% `t_r_ps`/`t_f_ps`, `pn_skew_ps`, `vcm_ac_rms_mv`/`pp_mv`, IEEE 802.3 linear-fit `p_max_mv`, `e_rms_mv`, `sndr_tx_db` |
| `analyze_tx_ffe.py` | Standalone PSF ASCII analyzer (`s11`, `dc_term`, `eye`, `cm_sndr`) | JSON summary |

## DUT Interface Contract

```spectre
subckt dut_tx INP INN CLK VDD VSS OUTP OUTN
    // instantiate your CML/VML TX + FFE (or wrap ../../va/va_tx_ffe_4tap.va)
ends dut_tx
```
