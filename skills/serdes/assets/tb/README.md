# SerDes Process-Independent Spectre X Testbench Suites

Self-contained, PDK-agnostic Spectre X (`+preset=cx` / `+preset=ax`) testbench suites (`10` suites, `28` executable `.scs` testbenches + causal `mtline` & synthetic `.s4p` channels) covering every block and end-to-end top-level link of a high-speed NRZ & PAM4 wireline transceiver.

All analyzers are zero-dependency Python (`numpy` only) backed by [`common/psf_utils.py`](../../../../common/psf_utils.py).

| Suite | Decks | Primary Verification Metrics |
|---|---|---|
| [`channel/`](channel/README.md) | `channel_diff_lossy.scs`, `channel_synth_causal.s4p`, `tb_channel_sp_tdr.scs`, `tb_channel_sbr_eye.scs`, `tb_channel_nport_s4p.scs`, `tb_channel_xtalk_fext_next.scs`, `analyze_channel.py` | 4-port `SDD21`/`SDD11`, TDR `Z_TDR(t)`, SBR (`h_-1, h0, h1..h5` & PDA eye), `nport` `bbspice` causal `.s4p` convolution, FEXT/NEXT crosstalk eye degradation |
| [`tx_ffe/`](tx_ffe/README.md) | `tb_tx_s11.scs`, `tb_dc_termination.scs`, `tb_tx_ffe_channel.scs`, `analyze_tx_ffe.py` | TX `SDD11(f)`, DC termination `R_term(V)` flatness, 4-tap TX FFE SBR & PRBS eye opening |
| [`ctle_vga/`](ctle_vga/README.md) | `tb_ctle_ac_noise.scs`, `tb_ctle_channel_ac.scs`, `tb_ctle_channel_eye.scs`, `tb_ctle_linearity_p1db.scs`, `tb_vga_offset_cal.scs`, `analyze_ctle_vga.py` | Standalone AC peaking/noise, combined `H_ch(f)*H_ctle(f)` DC-to-Nyquist flatness, before/after eye opening, coherent `P1dB`/`HD3`/`SFDR`, closed-loop offset calibration |
| [`slicer_dfe/`](slicer_dfe/README.md) | `tb_slicer_hys_vtf.scs`, `tb_slicer_noise_tran.scs`, `tb_slicer_clk2q_setup_hold.scs`, `tb_dfe_3tap_eye.scs`, `analyze_slicer_dfe.py` | Bidirectional VTF & hysteresis, probit transient-noise (`trannoise`) sensitivity, `Clk-to-Q`/`tau_regen` & Setup/Hold margin, closed-loop 3-tap DFE & 0-BER check |
| [`sslms/`](sslms/README.md) | `tb_sslms_adapt.scs`, `tb_sslms_ctle_boost.scs`, `analyze_sslms.py` | Live concurrent VGA + 3-tap DFE SS-LMS convergence AND transition-filtered (`edge_only=1`) CTLE `VBOOST` adaptation on a real lossy `mtline` channel |
| [`tcoil/`](tcoil/README.md) | `tb_tcoil_bw.scs`, `tb_rx_frontend_sdd11_scd21.scs`, `analyze_tcoil.py` | Bridged T-coil bandwidth extension (`2.83x` Butterworth), `S11` & step overshoot; 4-port RX front-end `SDD11`/`SCD11`/`SCD21`/`SDC21` mode conversion |
| [`cdr/`](cdr/README.md) | `tb_bbpd_transfer.scs`, `tb_pi_linearity.scs`, `tb_cdr_jtol.scs`, `analyze_cdr.py` | 2x-oversampled Alexander BBPD early/late polarity & dead zone, full-$2\pi$ PI DNL/INL, closed-loop 2nd-order CDR tracking error, `JTF`, and 0-BER `JTOL` |
| [`pam4/`](pam4/README.md) | `tb_pam4_tx_rlm_eye.scs`, `tb_pam4_dfe_ber.scs`, `analyze_pam4.py` | IEEE 802.3 PAM4 `RLM` (`>= 0.95`), lower/mid/upper 3-eye heights & widths, 3-threshold slicer + 1-tap PAM4 DFE 0-SER & Gray-decoded 0-BER |
| [`clocking_jitter/`](clocking_jitter/README.md) | `tb_clk_dcd_iq_skew.scs`, `tb_tx_jitter_bathtub.scs`, `analyze_clocking_jitter.py` | Half-rate DCD (`%`/`ps`) & 90-degree I/Q skew (`deg`/`ps`) before vs. after cal; TX `DCD`/`DDJ`/`SJ`/`RJ` decomposition & `BER = 1e-12` bathtub eye width |
| [`link_top/`](link_top/README.md) | `tb_serdes_link_top.scs`, `analyze_link_top.py` | End-to-end `TX FFE -> Long-Reach Channel (-24 dB @ 5 GHz) -> CTLE -> 3-Tap DFE -> Slicer` stage-by-stage eye progression & 0-BER check |
