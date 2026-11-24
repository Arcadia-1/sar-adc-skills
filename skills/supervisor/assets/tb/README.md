# Supervisor Process-Independent Spectre X Testbench Suites

Self-contained Spectre X verification suites for Power-On Reset (POR) / Programmable Brown-Out Reset (BOR) supervisors and On-Chip Temperature Sensor / Thermal Shutdown (TSD) blocks, backed by [`common/psf_utils.py`](../../../../common/psf_utils.py).

| Suite | Decks | Primary Verification Metrics |
|---|---|---|
| [`por_bor/`](por_bor/README.md) | 4 decks: `tb_por_thresholds_hys.scs`, `tb_por_ramp_rates.scs`, `tb_por_glitch_immunity.scs`, `tb_bor_multi_level.scs`, `analyze_por_bor.py` | Rising/falling thresholds (`V_POR+`, `V_POR-`), hysteresis `V_hys`, cold-boot low-VDD glitch audit, nano-power `I_q`, 3-decade ramp-rate `t_rst` stability, negative-VDD glitch immunity curve, and 3-bit programmable BOR monotonicity (`DNL`/`INL`/`mV/LSB`) |
| [`temp_sensor/`](temp_sensor/README.md) | 3 decks: `tb_tsens_linearity.scs`, `tb_tsens_psrr_noise.scs`, `tb_tsens_thermal_alarm.scs`, `analyze_temp_sensor.py` | `-40..125 C` `V_BE`/`V_PTAT`/`V_TEMP` sensitivity, raw vs. 1-point (`@ 27 C`) vs. 2-point trimmed 2nd-order curvature bow, supply sensitivity (`deg C / V`), integrated RMS noise (`mK_rms`), dynamic chopping offset cancellation (`> 10x`), and hysteretic TSD `T_trip`/`T_release`/`T_hys` |

> **Bandgap & Regulator Companions:** For dedicated bandgap reference verification see [`skills/bandgap/`](../../../bandgap/SKILL.md); for LDO regulator verification see [`skills/ldo/`](../../../ldo/SKILL.md).
