# Oscillator Process-Independent Spectre Testbench Suites

Self-contained **Spectre X** verification suites for **Pierce Crystal Oscillators (XO)** and **On-Chip RC Relaxation Oscillators**, backed by [`common/psf_utils.py`](../../../../common/psf_utils.py).

| Suite | Decks | Primary Verification Metrics |
|---|---|---|
| [`xo/`](xo/README.md) | 4 decks: `tb_xo_neg_resistance.scs`, `tb_xo_startup_drive.scs`, `tb_xo_pullability_cload.scs`, `tb_xo_pss_pnoise.scs`, `analyze_xo.py` | Small-signal negative resistance `-Re{Z_in(f0)}` & startup margin `|R_neg|/R_m` (`>= 5x`), transient startup envelope & crystal drive power `P_xtal` (`< 100 uW`), 5-code load-cap `C_L` pullability `[ppm]` & worst-case margin, and full-Q autonomous `pss + pnoise` SSB phase noise `L(df)` & RMS jitter `[fs]` |
| [`rc_osc/`](rc_osc/README.md) | 3 decks: `tb_rc_osc_temp_vdd.scs`, `tb_rc_osc_trim_startup.scs`, `tb_rc_osc_jitter_duty.scs`, `analyze_rc_osc.py` | 5-temp (`-40..125 C`) & 3-supply (`0.9..1.1 VDD`) PVT drift (`TC [ppm/C]`, `%/V`), 5-bit digital trim linearity/range & `EN` cold-startup `1%` settling, and 450+ cycle RMS/C2C period jitter, duty cycle, & `10%-90%` edge times |

> **LC-VCO, Ring-VCO, & DCO Verification inside PLLs:** For voltage/digitally-controlled RF oscillators (`K_VCO`, multi-band cap-bank overlap, FoM), see [`skills/pll/assets/tb/vco/`](../../../pll/assets/tb/vco/README.md) and [`skills/pll/assets/tb/tdc_dco/`](../../../pll/assets/tb/tdc_dco/README.md).
