# SerDes Channel Characterization Spectre Testbench Suite

Process-independent Spectre X (`+preset=cx` / `+preset=ax`) decks and analyzer for differential backplane/PCB channel S-parameters, TDR, Single-Bit Response (SBR), Touchstone `.s4p` `nport` rational convolution, FEXT/NEXT crosstalk, and PRBS eye characterization.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `channel_diff_lossy.scs` | Causal passive 100-ohm differential `mtline` model (skin effect + Djordjevic-Sarkar dielectric loss) | Reusable across `sp`, `ac`, `dc`, `noise`, and `tran` |
| `channel_synth_causal.s4p` | Analytically-generated passive causal 4-port Touchstone `.s4p` (`0..20 GHz`, `L = 0.15 m`, `-9.7 dB @ 5 GHz`) | Zero proprietary IP; verified passive ($\sigma_{\max} \le 1$) |
| `tb_channel_sp_tdr.scs` | 4-port `sp` (`10 MHz..20 GHz`) + differential TDR `tran` | `SDD21` at 1/5/7/10 GHz, worst `SDD11`, `Z_TDR` impedance plateau |
| `tb_channel_sbr_eye.scs` | Simultaneous 1-UI isolated pulse SBR + PRBS-7 eye `tran` (`10 Gb/s`) | Pre/main/post cursors (`h_-1, h0, h1..h5`), PDA eye height, TX/RX eye height `[mV]` & width `[UI/ps]` |
| `tb_channel_nport_s4p.scs` | Spectre X `nport` (`interp=bbspice passivity=fit_enforce`) `sp` + SBR causality check + PRBS-7 eye on `channel_synth_causal.s4p` | `SDD21`/`SDD11`, pre-cursor causality ratio (`h_-2/h0`), SBR PDA eye, folded eye |
| `tb_channel_xtalk_fext_next.scs` | Victim + asynchronous PRBS-9 FEXT/NEXT aggressors (`ac` coupling + `tran` eye comparison) | `isolated_eye` vs. `xtalk_eye`, eye loss `[mV / % / ps]`, `fext/next_rms_mv`, `fext/next_5ghz_db` |
| `tb_channel_blw_cid.scs` | 10 Gb/s CID stress burst (`mode=3`) through `dut_channel` + series `C_ac` + RX bias | `blw_peak_mv`, `blw_pct`, analytical RC `rel_err_pct`, `post_cid_dc_shift_mv`, pre vs. post-CID eye height |
| `analyze_channel.py` | Standalone PSF ASCII analyzer (`sp`, `tdr`, `sbr_eye`, `nport_s4p`, `xtalk`, `blw_cid`) | JSON summary |

## DUT Interface Contract

```spectre
subckt dut_channel INP INN OUTP OUTN VSS
    // wrap channel_diff_lossy (or your Touchstone nport file="channel_synth_causal.s4p" interp=rational)
ends dut_channel
```
