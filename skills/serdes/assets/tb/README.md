# SerDes Process-Independent Spectre Testbench Suites

Self-contained, PDK-agnostic Spectre testbench suites (verified with **Spectre X `+preset=cx`** and **`+preset=ax`**) covering an entire high-speed NRZ wireline transceiver chain from channel & TX FFE to RX CTLE/VGA, slicer/DFE, Sign-Sign LMS adaptation, and T-coil bandwidth extension.

All analyzers are zero-dependency Python (`numpy` only) backed by [`common/psf_utils.py`](../../../../common/psf_utils.py).

| Suite | Decks | Primary Verification Metrics |
|---|---|---|
| [`channel/`](channel/README.md) | `channel_diff_lossy.scs`, `tb_channel_sp_tdr.scs`, `tb_channel_sbr_eye.scs`, `analyze_channel.py` | 4-port differential `SDD21(f)` insertion loss & `SDD11(f)` return loss, differential TDR `Z_TDR(t)`, Single-Bit Response (SBR `h_-1, h0, h1..h5` & PDA eye), PRBS-7 eye height/width |
| [`tx_ffe/`](tx_ffe/README.md) | `tb_tx_s11.scs`, `tb_tx_ffe_channel.scs`, `analyze_tx_ffe.py` | TX differential output return loss `SDD11(f)`, 4-tap TX FFE pre-shoot/de-emphasis SBR & PRBS eye opening across a lossy channel |
| [`ctle_vga/`](ctle_vga/README.md) | `tb_ctle_ac_noise.scs`, `tb_ctle_channel_eye.scs`, `tb_vga_offset_cal.scs`, `analyze_ctle_vga.py` | CTLE/VGA DC gain, peak gain, peaking boost (`dB`), `f_peak`, `-3 dB` BW, shaped RMS noise, before/after channel eye opening, closed-loop offset calibration convergence |
| [`slicer_dfe/`](slicer_dfe/README.md) | `tb_slicer_hys_vtf.scs`, `tb_dfe_3tap_eye.scs`, `analyze_slicer_dfe.py` | Slicer sensitivity, VTF & hysteresis width; closed-loop 3-tap DFE before/after eye opening & 0-error BER check |
| [`sslms/`](sslms/README.md) | `tb_sslms_adapt.scs`, `analyze_sslms.py` | Live transient Sign-Sign LMS adaptive convergence of VGA gain & 3-tap DFE coefficients (`h1, h2, h3`) + `DONE` freeze |
| [`tcoil/`](tcoil/README.md) | `tb_tcoil_bw.scs`, `analyze_tcoil.py` | Bridged T-coil bandwidth extension ratio (`~2.7x` over bare `RL || C_pad`), peaking, `S11` return loss, and step overshoot |
