# PLL Process-Independent Spectre Testbench Suites

Self-contained Spectre verification suites covering block-level and closed-loop Integer-N, Fractional-N ($\Delta\Sigma$), and All-Digital PLL (TDC-ADPLL & Bang-Bang ADPLL) verification, backed by [`common/psf_utils.py`](../../../../common/psf_utils.py).

| Suite | Decks | Primary Verification Metrics |
|---|---|---|
| [`vco/`](vco/README.md) | `tb_vco_tuning_kvco.scs`, `tb_vco_pss_pnoise.scs`, `analyze_vco.py` | Tuning range, `K_VCO(Vctrl)`, autonomous shooting `pss` + `pnoise` `L(df)` & IEEE-1139 RMS jitter |
| [`pfd_cp/`](pfd_cp/README.md) | `tb_pfd_cp_transfer.scs`, `analyze_pfd_cp.py` | Phase-frequency transfer slope `K_PD = I_CP/(2*pi)`, dead-zone check, UP/DN current mismatch |
| [`divider/`](divider/README.md) | `tb_mmd_frac_n.scs`, `analyze_divider.py` | Integer & MASH 1-1-1 fractional-N mean division ratio, modulus sequence bounds, spur audit |
| [`tdc_dco/`](tdc_dco/README.md) | `tb_tdc_transfer.scs`, `tb_dco_tuning.scs`, `analyze_tdc_dco.py` | TDC step resolution `Delta_t_TDC`, DNL/INL; DCO frequency range & `K_DCO` linearity |
| [`int_n_pll/`](int_n_pll/README.md) | `tb_int_n_pll_ac_loop.scs`, `tb_int_n_pll_lock.scs`, `analyze_int_n_pll.py` | Linearized AC open-loop `f_BW`/PM/GM + closed-loop transient frequency lock, overshoot & reference spur |
| [`frac_n_pll/`](frac_n_pll/README.md) | `tb_frac_n_pll_lock.scs`, `analyze_frac_n_pll.py` | Fractional-N MASH 1-1-1 lock accuracy (`N + K/2^B`), `VCTRL` ripple & fractional spur audit |
| [`adpll/`](adpll/README.md) | `tb_adpll_lock.scs`, `analyze_adpll.py` | TDC-ADPLL & Bang-Bang ADPLL lock transient, steady-state `FCW` tracking & residual phase error |
