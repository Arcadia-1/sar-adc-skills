# SerDes Clocking & Jitter Decomposition Spectre X Testbench Suite

Process-independent Spectre X (`+preset=cx` / `+preset=ax`) decks and analyzer for half-rate/quarter-rate clock distribution Duty-Cycle Distortion (`DCD`) & 90-degree quadrature I/Q phase skew calibration, and TX jitter decomposition (`DCD`, `DDJ`, `SJ`, `RJ`) with Dual-Dirac bathtub `BER = 1e-12` eye width extrapolation.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_clk_dcd_iq_skew.scs` | 5 GHz half-rate 4-phase clock (`CK0, CK90, CK180, CK270`) before vs. after `VDCD_CAL` & `VIQ_CAL` | `duty_cycle_pct`, `dcd_pct`/`ps`, `iq_skew_deg`/`ps`, `quadrant_spacings_ps`, reduction ratios |
| `tb_tx_jitter_bathtub.scs` | 10 Gb/s PRBS-7 through lossy channel (clean baseline vs. DDJ + DCD + SJ + RJ) | `dcd_ps`, `ddj_pp_ps`, `sj_pp_ps`, `rj_rms_ps`, `dj_pp_ps`, `tj_1e12_ps`, `ew_1e12_ui`/`ps`, bathtub curve |
| `tb_psij_supply_noise.scs` | Sinusoidal `VDD` ripple (`50 mVpp @ 100 MHz`) + AC PSRR sweep on `dut_clk_dist` & `dut_ctle_vga` | `tie_psij_pp_ps`, `psij_ps_per_mv`, `psij_mui_per_mv`, `ctle_psrr_tran_db`, wideband `ctle_psrr_ac_*_db` |
| `analyze_clocking_jitter.py` | Standalone PSF ASCII analyzer (`dcd_iq`, `bathtub`, `psij`) | JSON summary |

## DUT Interface Contracts

```spectre
// Half-rate / quarter-rate clock distribution with DCD, I/Q cal & PSIJ (tb_clk_dcd_iq_skew.scs, tb_psij_supply_noise.scs)
subckt dut_clk_dist CKI_P CKI_N CKQ_P CKQ_N VDCD_CAL VIQ_CAL VDD VSS CK0 CK90 CK180 CK270
    // wrap ../../va/va_clk_dcd_iq.va or your transistor clock tree
ends dut_clk_dist

// RX CTLE + VGA front end for supply-to-diff PSRR (tb_psij_supply_noise.scs)
subckt dut_ctle_vga INP INN VBOOST VOFF_CAL VDD VSS OUTP OUTN
    // wrap ../../va/va_ctle_vga.va or your transistor CTLE/VGA
ends dut_ctle_vga
```
