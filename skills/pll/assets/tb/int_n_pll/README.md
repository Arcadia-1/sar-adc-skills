# Process-Independent Integer-N CP-PLL Testbench Suite (Spectre)

Standalone Spectre X testbenches and analyzer covering the full industrial Integer-N charge-pump PLL signoff checklist: phase-domain loop closure, nonlinear lock, auto-band calibration & lock-detect timing, direct FFT vs. NBFM reference spurs, closed-loop supply rejection (`PSRR`), closed-loop phase-noise/jitter budget, and programmable `N x I_CP` stability scaling.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_int_n_pll_ac_loop.scs` | Phase-domain `stb` (`iprobe`) + `ac` | `fu_mhz`, `phase_margin_deg`, `cl_peaking_db`, `cl_bw_3db_mhz` |
| `tb_int_n_pll_lock.scs` | Closed-loop nonlinear lock `tran` (`dut_int_n_pll`) | `f_locked_mhz`, `freq_err_ppm`, `t_settle_0p1pct_us`, `vctrl_ripple_pp_mv`, `est_ref_spur_dbc` |
| `tb_int_n_pll_bandcal_lock.scs` | Closed-loop AFC binary-search band-cal (`va_vco_multiband` + `va_bandcal_lockdet`) + lock-detect `tran` | `t_cal_us`, `cal_code`, `t_lock_1pct_us`, `t_lock_detect_us`, `freq_err_ppm`, `vctrl_final_v`, `p_dd_mw` |
| `tb_int_n_pll_ref_spur.scs` | High-accuracy strobed closed-loop `tran` (`+preset=cx`) with CP mismatch + leakage | Direct Kaiser-FFT `ref_spur_fft_dbc` (`f_0 +/- f_ref`, `+/- 2*f_ref`), `v_rip_fref_uv`, `ref_spur_nbfm_dbc`, `fft_vs_nbfm_err_db` |
| `tb_int_n_pll_psrr.scs` | 3-frequency `alter` sinusoidal `VDDA` ripple injection (`200 kHz / 1.5 MHz / 10 MHz`) | `df_peak_khz`, `vctrl_counter_mv`, `psrr_db`, `fm_sideband_dbc`, `psrr_fft_db`, `inband_vs_oob_rejection_db` |
| `tb_int_n_pll_noise_scaling.scs` | Phase-domain 5-sweep `noise` budget + 9-pt `N x I_CP` `alter`/`stb` matrix (`< 1 s`) | `L(100k/1M/10M)`, `rms_jitter_fs`, per-block `noise_contrib_pct` (`cp`/`vco`/`r1`/`ref_div`), 9-pt `fu_mhz`/`phase_margin_deg`, `pm_min_deg` |
| `analyze_int_n_pll.py` | Standalone PSF ASCII analyzer (`ac_loop`, `lock`, `bandcal`, `spur`, `psrr`, `noise_scaling` modes) | JSON summary |

## DUT Interface Contract (`tb_int_n_pll_lock.scs`)

```spectre
subckt dut_int_n_pll FREF OUTP OUTN VCTRL VDD VSS
    // Phase 1: assemble va_pfd + va_cp + passive R1/C1/C2 + va_vco + va_div_int
    // Phase 3/4: swap blocks incrementally to transistor subcircuits
ends dut_int_n_pll
```

> **Note:** `tb_int_n_pll_ac_loop.scs`, `tb_int_n_pll_bandcal_lock.scs`, `tb_int_n_pll_ref_spur.scs`, `tb_int_n_pll_psrr.scs`, and `tb_int_n_pll_noise_scaling.scs` run completely out of the box using the bundled Verilog-A models in `../../va/`. For Phase-3 hybrid replacement, swap any individual instance (`I_VCO`, `I_CP`, `I_DIV`, `I_AFC`) with your transistor subcircuit.
