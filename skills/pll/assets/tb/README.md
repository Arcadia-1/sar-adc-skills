# PLL Process-Independent Spectre Testbench Suites

Self-contained Spectre X verification suites (17 `.scs` decks across 7 suites) covering block-level and closed-loop Integer-N, Fractional-N ($\Delta\Sigma$), and All-Digital PLL (TDC-ADPLL & Bang-Bang ADPLL) signoff verification, backed by [`common/psf_utils.py`](../../../../common/psf_utils.py).

| Suite | Decks | Primary Verification Metrics |
|---|---|---|
| [`vco/`](vco/README.md) | `tb_vco_tuning_kvco.scs`, `tb_vco_pss_pnoise.scs`, `tb_vco_capbank_overlap.scs`, `analyze_vco.py` | Tuning range, `K_VCO(Vctrl)`, autonomous `pss` + `pnoise` `L(df)` & RMS jitter, multi-sub-band cap-bank overlap (%) & `K_LIN` blind-hole check |
| [`pfd_cp/`](pfd_cp/README.md) | `tb_pfd_cp_transfer.scs`, `tb_cp_compliance_mismatch.scs`, `analyze_pfd_cp.py` | Beat-sweep `K_PD = I_CP/(2*pi)` & dead-zone check; isolated CP DC compliance window `[v_comp_min, v_comp_max]`, `r_o` & `Delta_I_CP(V_CP)` mismatch |
| [`divider/`](divider/README.md) | `tb_div_func_mmd.scs`, `tb_div_max_toggle.scs`, `analyze_divider.py` | Integer & MASH 1-1-1 fractional-N mean ratio & modulus span; multi-frequency max toggle `f_max_pass`, cycle-slip detection, duty cycle & `t_r`/`t_f` |
| [`tdc_dco/`](tdc_dco/README.md) | `tb_tdc_transfer.scs`, `tb_dco_tuning.scs`, `analyze_tdc_dco.py` | TDC step resolution `Delta_t_TDC`, DNL/INL; DCO frequency range & `K_DCO` linearity |
| [`int_n_pll/`](int_n_pll/README.md) | `tb_int_n_pll_ac_loop.scs`, `tb_int_n_pll_lock.scs`, `tb_int_n_pll_bandcal_lock.scs`, `tb_int_n_pll_ref_spur.scs`, `tb_int_n_pll_psrr.scs`, `tb_int_n_pll_noise_scaling.scs`, `analyze_int_n_pll.py` | Open-loop `f_u`/PM/GM, lock transient, AFC band-cal & lock-detect timing + `P_DD`, direct FFT vs. NBFM reference spur, closed-loop `PSRR(f)`, noise budget & 9-pt `N x I_CP` stability matrix |
| [`frac_n_pll/`](frac_n_pll/README.md) | `tb_frac_n_pll_lock.scs`, `analyze_frac_n_pll.py` | Fractional-N MASH 1-1-1 lock accuracy (`N + K/2^B`), `VCTRL` ripple & fractional spur audit |
| [`adpll/`](adpll/README.md) | `tb_adpll_lock.scs`, `analyze_adpll.py` | TDC-ADPLL & Bang-Bang ADPLL lock transient, steady-state `FCW` tracking & residual phase error |
