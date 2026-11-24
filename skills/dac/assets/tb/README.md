# DAC Process-Independent Spectre Testbench Suites

Self-contained Spectre verification suites for high-speed Current-Steering DACs and Voltage-Mode R-2R Ladder DACs, backed by [`common/psf_utils.py`](../../../../common/psf_utils.py).

| Suite | Decks | Primary Verification Metrics |
|---|---|---|
| [`current_steering/`](current_steering/README.md) | `tb_dac_static_dnl_inl.scs`, `tb_dac_dynamic_sfdr.scs`, `tb_dac_glitch_settle.scs`, `analyze_cs_dac.py` | 1024-code static DNL/INL/monotonicity, coherent single-tone SFDR/HD2/HD3/THD/SNDR/ENOB, coherent two-tone IMD3, major-carry (`511 <-> 512`) peak glitch, glitch impulse `[pV*s]` & `0.5 LSB` settling time |
| [`r2r/`](r2r/README.md) | `tb_r2r_static.scs`, `tb_r2r_settle.scs`, `analyze_r2r.py` | 256-code static DNL/INL/offset/gain error, major-carry (`127 -> 128`) & full-scale `0.5 LSB` settling time |

> **Capacitive DAC (CDAC) for SAR ADCs:** For charge-redistribution CDAC static/settling verification, see [`skills/sar-adc/assets/tb/cdac/`](../../../sar-adc/assets/tb/cdac/README.md).
