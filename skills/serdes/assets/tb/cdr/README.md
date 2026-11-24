# SerDes Clock & Data Recovery (CDR) Spectre X Testbench Suite

Process-independent Spectre X (`+preset=cx` / `+preset=ax`) decks and analyzer covering 2x-oversampled Alexander Bang-Bang Phase Detector (BBPD) transfer & dead zone, multi-bit Phase Interpolator (PI) DNL/INL linearity, and closed-loop 2nd-order CDR Jitter Transfer Function (JTF) & Sinusoidal Jitter Tolerance (JTOL).

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_bbpd_transfer.scs` | Vernier beat-frequency phase sweep across `[-0.46 UI, +0.47 UI]` (`0.5 ps` step) | `early_mean_up_minus_dn`, `late_mean_up_minus_dn`, `polarity_correct`, `deadzone_width_mui` |
| `tb_pi_linearity.scs` | Full `2*pi` (65-step `0..64`) static dwell sweep at `10 GHz` | `mean_step_mui`, `mean_step_deg`, `monotonic`, `dnl_max_lsb`/`mui`/`deg`, `inl_max_lsb`/`mui`/`deg` |
| `tb_cdr_jtol.scs` | Closed-loop 2nd-order Bang-Bang PI CDR tracking SJ-modulated `10 Gb/s` PRBS-7 | `track_err_rms_mui`, `track_err_peak_mui`, `jtf_gain_db`, `jtf_phase_deg`, `bit_errors`, `jtol_pass` |
| `analyze_cdr.py` | Standalone PSF ASCII analyzer (`bbpd`, `pi`, `jtol`) | JSON summary |

## DUT Interface Contracts

```spectre
// 2x-oversampled Alexander BBPD (tb_bbpd_transfer.scs, tb_cdr_jtol.scs)
subckt dut_bbpd INP INN CLKP CLKN VDD VSS UP DN DOUT
    // wrap ../../va/va_bbpd_serdes.va or your transistor BBPD
ends dut_bbpd

// Quadrature Phase Interpolator (tb_pi_linearity.scs, tb_cdr_jtol.scs)
subckt dut_pi CKI_P CKI_N CKQ_P CKQ_N VCODE VDD VSS CLKP CLKN
    // wrap ../../va/va_phase_interp.va or your transistor PI
ends dut_pi

// Digital 2nd-order CDR loop filter (tb_cdr_jtol.scs)
subckt dut_cdr_loop UP DN CLK VDD VSS VCODE FREQ_MON
    // wrap ../../va/va_cdr_loop.va or your digital CDR filter
ends dut_cdr_loop
```
