# SerDes Process-Independent Spectre X Testbench Suites

Self-contained, PDK-agnostic Spectre X (`+preset=cx` / `+preset=ax`) testbench suites covering every block and end-to-end top-level link of a high-speed NRZ wireline transceiver.

All analyzers are zero-dependency Python (`numpy` only) backed by [`common/psf_utils.py`](../../../../common/psf_utils.py).

| Suite | Decks | Primary Verification Metrics |
|---|---|---|
| [`channel/`](channel/README.md) | `channel_diff_lossy.scs`, `tb_channel_sp_tdr.scs`, `tb_channel_sbr_eye.scs`, `analyze_channel.py` | 4-port `SDD21`/`SDD11`, differential TDR `Z_TDR(t)`, SBR (`h_-1, h0, h1..h5` & PDA eye), PRBS-7 eye height/width |
| [`tx_ffe/`](tx_ffe/README.md) | `tb_tx_s11.scs`, `tb_dc_termination.scs`, `tb_tx_ffe_channel.scs`, `analyze_tx_ffe.py` | TX `SDD11(f)`, DC termination `R_term(V)` flatness, 4-tap TX FFE SBR & PRBS eye opening |
| [`ctle_vga/`](ctle_vga/README.md) | `tb_ctle_ac_noise.scs`, `tb_ctle_channel_ac.scs`, `tb_ctle_channel_eye.scs`, `tb_vga_offset_cal.scs`, `analyze_ctle_vga.py` | Standalone AC peaking/noise, combined `H_ch(f)*H_ctle(f)` DC-to-Nyquist flatness, before/after eye opening, closed-loop offset calibration |
| [`slicer_dfe/`](slicer_dfe/README.md) | `tb_slicer_hys_vtf.scs`, `tb_slicer_noise_tran.scs`, `tb_dfe_3tap_eye.scs`, `analyze_slicer_dfe.py` | Bidirectional VTF & hysteresis, probit transient-noise sensitivity (`BER = 1e-12`), closed-loop 3-tap DFE eye opening & 0-BER check |
| [`sslms/`](sslms/README.md) | `tb_sslms_adapt.scs`, `tb_sslms_ctle_boost.scs`, `analyze_sslms.py` | Live concurrent VGA + 3-tap DFE SS-LMS convergence AND transition-filtered (`edge_only=1`) CTLE `VBOOST` adaptation on a real lossy `mtline` channel |
| [`tcoil/`](tcoil/README.md) | `tb_tcoil_bw.scs`, `analyze_tcoil.py` | Bridged T-coil bandwidth extension (`2.83x` Butterworth), peaking, `S11`, and step overshoot |
| [`link_top/`](link_top/README.md) | `tb_serdes_link_top.scs`, `analyze_link_top.py` | End-to-end `TX FFE -> Long-Reach Channel (-24 dB @ 5 GHz) -> CTLE -> 3-Tap DFE -> Slicer` stage-by-stage eye progression & 0-BER check |
