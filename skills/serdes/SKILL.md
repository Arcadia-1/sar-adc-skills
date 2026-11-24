---
name: serdes-skill
description: >
  Process-independent high-speed Wireline / SerDes IC design guide and Spectre X
  verification toolkit. Covers end-to-end NRZ/PAM4 link budgets, causal lossy
  channels (mixed-mode SDD21/SDD11/SCD21, TDR, Single-Bit Response SBR & Peak
  Distortion eye, Touchstone .s4p nport bbspice convolution, FEXT/NEXT
  crosstalk, AC-coupled CID baseline wander BLW), bridged T-coil bandwidth
  extension (2.83x constant-resistance sizing), CML vs. VML/SST TX drivers &
  4-tap FFE (peak-power constraint, de-emphasis, SDD11, R_term flatness, P/N
  skew, V_cm,ac, IEEE 802.3 Clause 93/120 linear-fit SNDR_TX), source-degenerated
  RC CTLE & VGA peaking/noise/P1dB/HD3/PSRR/offset calibration, CML/StrongARM
  slicers (VTF, trannoise, Clk-to-Q, tau_regen, Setup/Hold, input kickback &
  interleaved coupling) & 3-tap DFE, Sign-Sign LMS adaptive equalization,
  2x-oversampled Alexander BBPD + quadrature PI + 2nd-order CDR ppm tracking,
  2*pi wraparound & multi-frequency JTF/JTOL mask, Gray-coded PAM4 RLM/3-eye/
  1-tap DFE & end-to-end PAM4 link, half-rate DCD/IQ skew, PSIJ & TX jitter
  bathtub decomposition, 15 Verilog-A models, and 10 standalone Spectre X
  (+preset=cx / +preset=ax) testbench suites (35 decks). Use for any
  high-speed wireline, equalizer, CDR, PAM4, jitter, channel SI, eye diagram,
  T-coil, DFE/SS-LMS, or Spectre X verification task.
---

# High-Speed SerDes / Wireline Skill

A process-independent engineering guide, 15-model Verilog-A behavioral library, and standalone **Spectre X (`+preset=cx` / `+preset=ax`)** verification toolkit (10 suites, 35 executable testbenches) for high-speed NRZ & PAM4 serial links (10–56 Gb/s).

## Read Order

- `references/serdes-architecture-and-channel.md`
  End-to-end TX FFE / RX CTLE / RX DFE equalization split, mixed-mode `SDD21`/`SDD11`, Single-Bit Response (SBR $h(t)$) & Peak-Distortion eye height, TDR, and constant-resistance bridged T-coil sizing ($2.83\times$ Butterworth BW extension).
- `references/tx-cml-vml-and-ffe.md`
  CML vs. VML/SST output driver trade-offs, $100\;\Omega$ differential return loss (`SDD11`), 4-tap TX FFE peak-power constraint ($\sum |w_k| = 1$), de-emphasis & Zero-Forcing tap sizing.
- `references/rx-ctle-vga-and-offset.md`
  Source-degenerated RC CTLE pole-zero transfer function ($f_z, f_{p1}, f_{p2}$), multi-stage peaking vs. high-frequency noise amplification, broadband VGA linearity, and closed-loop offset calibration FSM + IDAC.
- `references/dfe-slicer-and-sslms.md`
  CML vs. StrongARM slicers (sensitivity, hysteresis, VTF), 3-tap DFE post-cursor ISI cancellation, 1-UI critical loop & speculative loop-unrolling, and Sign-Sign LMS adaptive equalization rules & convergence freeze.
- `references/cdr-pam4-and-clocking.md`
  2x-oversampled Alexander BBPD, multi-bit quadrature Phase Interpolator (DNL/INL), Type-II 2nd-order PI-CDR ppm tracking, $2\pi$ wraparound & multi-frequency JTF/JTOL mask, Gray-coded PAM4 RLM, 1-tap DFE & full PAM4 link, half-rate DCD/IQ skew, PSIJ/PSRR & Dual-Dirac jitter bathtub (`BER = 1e-12`), TX P/N skew, $V_{\text{cm,ac}}$ & IEEE 802.3 `SNDR_TX`, slicer `Clk-to-Q`/`tau_regen`/input kickback, CTLE `P1dB`/`HD3`, RX `SCD21`, `nport` `.s4p` `bbspice` causality, FEXT/NEXT crosstalk, and AC-coupled CID baseline wander (BLW).
- `references/simulation-and-verification.md`
  Spectre X (`+preset=cx`, `+preset=ax`, `+preset=mx`, `+postlpreset`, `-preset_override`) vs. APS/XPS solver guide, causal `mtline`/`nport` (`interp=bbspice`) channel pitfalls, `trannoise` rules, and complete usage of all 10 bundled testbench suites (35 decks).

## Bundled Assets

### Process-Independent Spectre X Testbench Suites (`assets/tb/`)
See `assets/tb/README.md` for full contracts (verified on Spectre X `+preset=cx` and `+preset=ax`):
- `assets/tb/channel/` — `channel_diff_lossy.scs` (causal 100-ohm FR4 `mtline`), `channel_synth_causal.s4p` (passive causal synthetic Touchstone), `tb_channel_sp_tdr.scs` (`SDD21`/`SDD11` + TDR), `tb_channel_sbr_eye.scs` (SBR + PRBS-7 eye), `tb_channel_nport_s4p.scs` (`nport` `bbspice` `sp` + SBR + eye), `tb_channel_xtalk_fext_next.scs` (FEXT/NEXT eye degradation), `tb_channel_blw_cid.scs` (AC-coupled CID baseline wander vs. RC theory & pre/post eye), `analyze_channel.py`
- `assets/tb/tx_ffe/` — `tb_tx_s11.scs` (`SDD11`), `tb_dc_termination.scs` (`R_term(V)` flatness), `tb_tx_ffe_channel.scs` (4-tap FFE channel equalization), `tb_tx_cm_skew_sndr.scs` (20–80% `t_r`/`t_f`, P/N skew, `V_cm,ac` & IEEE 802.3 linear-fit `SNDR_TX`), `analyze_tx_ffe.py`
- `assets/tb/ctle_vga/` — `tb_ctle_ac_noise.scs` (peaking + shaped noise), `tb_ctle_channel_ac.scs` (combined channel+CTLE AC flatness), `tb_ctle_channel_eye.scs` (before/after eye), `tb_ctle_linearity_p1db.scs` (coherent `P1dB`/`HD3`/`SFDR`), `tb_vga_offset_cal.scs` (offset cal loop), `analyze_ctle_vga.py`
- `assets/tb/slicer_dfe/` — `tb_slicer_hys_vtf.scs` (bidirectional VTF & hysteresis), `tb_slicer_noise_tran.scs` (probit transient-noise BER sensitivity), `tb_slicer_clk2q_setup_hold.scs` (`Clk-to-Q`, `tau_regen` & Setup/Hold margin), `tb_slicer_kickback.scs` (single & half-rate interleaved input kickback), `tb_dfe_3tap_eye.scs` (closed-loop 3-tap DFE & 0-BER check), `analyze_slicer_dfe.py`
- `assets/tb/sslms/` — `tb_sslms_adapt.scs` (concurrent VGA gain + 3-tap DFE SS-LMS), `tb_sslms_ctle_boost.scs` (transition-filtered CTLE boost SS-LMS on `mtline`), `analyze_sslms.py`
- `assets/tb/tcoil/` — `tb_tcoil_bw.scs` (bare `R_L || C_L` vs. bridged T-coil BW ratio, `S11` & step overshoot), `tb_rx_frontend_sdd11_scd21.scs` (4-port RX ESD + T-coil `SDD11`/`SCD11`/`SCD21`/`SDC21`), `analyze_tcoil.py`
- `assets/tb/cdr/` — `tb_bbpd_transfer.scs` (Alexander BBPD early/late polarity & dead zone), `tb_pi_linearity.scs` (full-$2\pi$ PI DNL/INL), `tb_cdr_jtol.scs` (closed-loop 2nd-order CDR JTF & 0-BER JTOL), `tb_cdr_ppm_wrap.scs` (`+1000 ppm` frequency tracking & multi-$2\pi$ PI wraparound), `tb_cdr_jtol_mask.scs` (4-frequency `alter` JTOL mask & `-3 dB` JTF corner), `analyze_cdr.py`
- `assets/tb/pam4/` — `tb_pam4_tx_rlm_eye.scs` (IEEE 802.3 RLM & 3-eye heights/widths), `tb_pam4_dfe_ber.scs` (PAM4 channel + 3-threshold slicer + 1-tap DFE 0-SER/0-BER), `tb_pam4_link_top.scs` (end-to-end 10 Gbaud PAM4 `TX FFE -> Channel -> CTLE -> 1-Tap DFE` stage-by-stage 3-eye & 0-SER/0-BER), `analyze_pam4.py`
- `assets/tb/clocking_jitter/` — `tb_clk_dcd_iq_skew.scs` (half-rate DCD & 90-degree I/Q skew before/after calibration), `tb_tx_jitter_bathtub.scs` (DCD/DDJ/SJ/RJ decomposition & `BER = 1e-12` bathtub eye width), `tb_psij_supply_noise.scs` (clock PSIJ `[ps/mV, mUI/mV]` & RX CTLE supply-to-diff `PSRR [dB]`), `analyze_clocking_jitter.py`
- `assets/tb/link_top/` — `tb_serdes_link_top.scs` (end-to-end `TX FFE -> 0.85 m Channel -> CTLE -> 3-Tap DFE -> Slicer` stage-by-stage eye & BER), `analyze_link_top.py`

### Verilog-A Behavioral Models (`assets/va/`)
- `assets/va/va_prbs_gen.va` — Clocked PRBS-7 (`x^7+x^6+1`), PRBS-9 (`x^9+x^5+1`), isolated 1-UI SBR pulse (`mode=2`), and CID stress burst (`mode=3`) differential NRZ generator
- `assets/va/va_tx_ffe_4tap.va` — 4-tap TX FFE with L1 peak-swing normalization, `50 ohm` termination, pad cap, optional intra-pair P/N skew `t_skew_pn` & soft `tanh` saturation `v_clip_tx`
- `assets/va/va_ctle_vga.va` — Passive-stable 1-zero / 2-pole differential CTLE + VGA with tunable boost, offset/cal port, smooth `tanh` `v_clip`/`v_clip_in` compression, optional supply coupling `psrr_v_per_v` & shaped white noise
- `assets/va/va_slicer_cml.va` — High-speed CML/StrongARM data slicer with injectable `vos`, `hysteresis_v`, Gaussian `vnoise_rms`, optional `tau_regen`/`tau_in`/`t_int` dynamic timing, and optional asymmetric internal-node kickback `c_kb_p`/`c_kb_n`
- `assets/va/va_dfe_3tap.va` — Closed-loop 3-tap DFE summer + data slicer + SS-LMS error slicer
- `assets/va/va_sslms_adapt.va` — Sign-Sign LMS adaptive tap engine (`edge_only=0|1` for DFE/VGA & transition-filtered CTLE boost) with working `DONE` freeze
- `assets/va/va_offset_cal_fsm.va` — Rail-independent majority-vote digital offset calibration FSM
- `assets/va/va_channel_isi.va` — Deterministic multi-cursor (`h_pre, h0, h1, h2, h3`) ISI channel for DFE/SS-LMS benchmarking
- `assets/va/va_bbpd_serdes.va` — 2x-oversampled Alexander / Bang-Bang phase detector with configurable metastability aperture `v_meta`, `UP`/`DN`, and retimed `DOUT`
- `assets/va/va_phase_interp.va` — Multi-bit quadrature Phase Interpolator with configurable 4th-harmonic `inl_amp`, `dnl_amp`, and optional `rj_rms_ui`
- `assets/va/va_cdr_loop.va` — Type-II 2nd-order proportional+integral digital CDR loop filter (`kp`, `ki`) driving unwrapped PI `VCODE`
- `assets/va/va_pam4_gen.va` — 4-level Gray-coded PAM4 PRBS-7/9 generator with configurable `rlm_err` and ground-truth `SYM_MON`
- `assets/va/va_pam4_tx.va` — 3-tap PAM4 TX FFE driver with configurable cubic RLM nonlinearity (`rlm_err`), finite bandwidth & 50-ohm termination
- `assets/va/va_pam4_dfe_slicer.va` — 3-threshold PAM4 slicer (`-2/3, 0, +2/3` scaled by `VREF`) + 1-tap proportional PAM4 DFE + IEEE 802.3 Gray decoder
- `assets/va/va_clk_dcd_iq.va` — Half-rate / quarter-rate 4-phase clock distribution model with orthogonally injectable & calibratable DCD (`VDCD_CAL`), 90-degree I/Q skew (`VIQ_CAL`), and optional supply-noise PSIJ (`k_psij_ps_per_v`)
