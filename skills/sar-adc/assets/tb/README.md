# SAR ADC Process-Independent Spectre Testbench Suites

Each subdirectory is a self-contained Spectre verification suite with standalone `.scs` decks, a DUT interface contract (`models_corner.scs` + `dut_subckt.scs`), and a zero-dependency Python PSF ASCII analyzer backed by [`common/psf_utils.py`](../../../../common/psf_utils.py).

| Suite | Decks | Primary Verification Metrics |
|---|---|---|
| [`comparator/`](comparator/README.md) | `tb_cmp_pss_pnoise.scs`, `tb_cmp_delay.scs`, `tb_cmp_trannoise.scs`, `tb_cmp_offset.scs` (+ `cmp_bisect.va`, `run_cmp_tb.py`) | PSS+PNOISE input-referred noise `sigma_n`, `A_eff`, `t_cmp`, `t_rst`, `tau`, `E_comp`, `FoM1/FoM2`, `trannoise` cross-check, bisect offset & hysteresis |
| [`bootstrap/`](bootstrap/README.md) | `tb_boot_ron_sweep.scs`, `tb_boot_tran_linearity.scs`, `analyze_bootstrap.py` | Clocked flying-cap `Ron(Vin)` flatness, near-Nyquist coherent sampling THD/SFDR/SNDR |
| [`cdac/`](cdac/README.md) | `tb_cdac_static_dnl_inl.scs`, `tb_cdac_settling.scs`, `analyze_cdac.py` | 512-state static DNL/INL, common-mode shift, worst-case MSB `0.5 LSB` settling time |
| [`sar_logic/`](sar_logic/README.md) | `tb_sar_logic_timing.scs`, `analyze_sar_logic.py` | Closed-loop 4-frame timing (incl. `0.1 mV` near-metastable stress), exact `N` `CMPCK` pulses, `EOC` stop, `t_conv` slack |
| [`adc_top/`](adc_top/README.md) | `tb_sar_adc_fft.scs`, `tb_sar_adc_ramp_dnl.scs`, `analyze_adc_top.py` | Coherent single-tone ENOB/SNDR/SNR/SFDR/THD, overdriven ramp DNL/INL, missing codes & usable full swing |

> **ADC Power-Delivery LDO Verification:** For LDO stability (`stb`), DC dropout/regulation, PSRR, $|Z_{\text{out}}(f)|$, output noise, and load/line-step droop, use the canonical [`skills/ldo/assets/tb/`](../../../ldo/assets/tb/README.md) suite.
