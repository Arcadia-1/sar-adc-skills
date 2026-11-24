---
name: serdes-skill
description: >
  Process-independent high-speed Wireline / SerDes IC design guide and Spectre X
  verification toolkit. Covers end-to-end NRZ/PAM4 link budgets, causal lossy
  channels (mixed-mode SDD21/SDD11, TDR, Single-Bit Response SBR & Peak
  Distortion eye), bridged T-coil bandwidth extension (2.72x constant-resistance
  sizing), CML vs. VML/SST TX drivers & 4-tap FFE (peak-power constraint,
  de-emphasis, SDD11), source-degenerated RC CTLE & VGA peaking/noise/offset
  calibration, CML/StrongARM slicers & 3-tap DFE (1-UI timing & loop unrolling),
  Sign-Sign LMS adaptive equalization, 8 clean Verilog-A models, and 7 standalone
  Spectre X (+preset=cx / +preset=ax) testbench suites (channel, tx_ffe,
  ctle_vga, slicer_dfe, sslms, tcoil, link_top). Use for any high-speed wireline,
  equalizer, channel SI, eye diagram, T-coil, DFE/SS-LMS, or Spectre X
  verification task.
---

# High-Speed SerDes / Wireline Skill

A process-independent engineering guide, Verilog-A behavioral model library, and standalone **Spectre X (`+preset=cx` / `+preset=ax`)** verification toolkit for high-speed serial links (10–56 Gb/s).

## Read Order

- `references/serdes-architecture-and-channel.md`
  End-to-end TX FFE / RX CTLE / RX DFE equalization split, mixed-mode `SDD21`/`SDD11`, Single-Bit Response (SBR $h(t)$) & Peak-Distortion eye height, TDR, and constant-resistance bridged T-coil sizing ($2.72\times$ BW extension).
- `references/tx-cml-vml-and-ffe.md`
  CML vs. VML/SST output driver trade-offs, $100\;\Omega$ differential return loss (`SDD11`), 4-tap TX FFE peak-power constraint ($\sum |w_k| = 1$), de-emphasis & Zero-Forcing tap sizing.
- `references/rx-ctle-vga-and-offset.md`
  Source-degenerated RC CTLE pole-zero transfer function ($f_z, f_{p1}, f_{p2}$), multi-stage peaking vs. high-frequency noise amplification, broadband VGA linearity, and closed-loop offset calibration FSM + IDAC.
- `references/dfe-slicer-and-sslms.md`
  CML vs. StrongARM slicers (sensitivity, hysteresis, VTF), 3-tap DFE post-cursor ISI cancellation, 1-UI critical loop & speculative loop-unrolling, and Sign-Sign LMS adaptive equalization rules & convergence freeze.
- `references/simulation-and-verification.md`
  Spectre X (`+preset=cx`, `+preset=ax`, `+preset=mx`, `+postlpreset`, `-preset_override`) vs. APS/XPS solver guide, causal `mtline`/`nport` channel pitfalls, and complete usage of all 6 bundled testbench suites.

## Bundled Assets

### Process-Independent Spectre X Testbench Suites (`assets/tb/`)
See `assets/tb/README.md` for full contracts (verified on Spectre X `+preset=cx` and `+preset=ax`):
- `assets/tb/channel/` — `channel_diff_lossy.scs` (causal 100-ohm FR4 `mtline`), `tb_channel_sp_tdr.scs` (`SDD21`/`SDD11` + TDR), `tb_channel_sbr_eye.scs` (SBR + PRBS-7 eye), `analyze_channel.py`
- `assets/tb/tx_ffe/` — `tb_tx_s11.scs` (`SDD11`), `tb_dc_termination.scs` (`R_term(V)` flatness), `tb_tx_ffe_channel.scs` (4-tap FFE channel equalization), `analyze_tx_ffe.py`
- `assets/tb/ctle_vga/` — `tb_ctle_ac_noise.scs` (peaking + shaped noise), `tb_ctle_channel_ac.scs` (combined channel+CTLE AC flatness), `tb_ctle_channel_eye.scs` (before/after eye), `tb_vga_offset_cal.scs` (offset cal loop), `analyze_ctle_vga.py`
- `assets/tb/slicer_dfe/` — `tb_slicer_hys_vtf.scs` (bidirectional VTF & hysteresis), `tb_slicer_noise_tran.scs` (probit transient-noise BER sensitivity), `tb_dfe_3tap_eye.scs` (closed-loop 3-tap DFE & 0-BER check), `analyze_slicer_dfe.py`
- `assets/tb/sslms/` — `tb_sslms_adapt.scs` (concurrent VGA gain + 3-tap DFE SS-LMS), `tb_sslms_ctle_boost.scs` (transition-filtered CTLE boost SS-LMS on `mtline`), `analyze_sslms.py`
- `assets/tb/tcoil/` — `tb_tcoil_bw.scs` (bare `R_L || C_L` vs. bridged T-coil BW ratio, `S11` & step overshoot), `analyze_tcoil.py`
- `assets/tb/link_top/` — `tb_serdes_link_top.scs` (end-to-end `TX FFE -> 0.85 m Channel -> CTLE -> 3-Tap DFE -> Slicer` stage-by-stage eye & BER), `analyze_link_top.py`

### Verilog-A Behavioral Models (`assets/va/`)
- `assets/va/va_prbs_gen.va` — Clocked PRBS-7 (`x^7+x^6+1`), PRBS-9 (`x^9+x^5+1`), and isolated 1-UI SBR pulse differential NRZ generator
- `assets/va/va_tx_ffe_4tap.va` — 4-tap TX FFE with L1 peak-swing normalization, `50 ohm` termination & pad cap
- `assets/va/va_ctle_vga.va` — Passive-stable 1-zero / 2-pole differential CTLE + VGA with tunable boost, offset/cal port & shaped white noise
- `assets/va/va_slicer_cml.va` — High-speed CML/StrongARM data slicer with injectable `vos`, `hysteresis_v`, and Gaussian `vnoise_rms`
- `assets/va/va_dfe_3tap.va` — Closed-loop 3-tap DFE summer + data slicer + SS-LMS error slicer
- `assets/va/va_sslms_adapt.va` — Sign-Sign LMS adaptive tap engine (`edge_only=0|1` for DFE/VGA & transition-filtered CTLE boost) with working `DONE` freeze
- `assets/va/va_offset_cal_fsm.va` — Rail-independent majority-vote digital offset calibration FSM
- `assets/va/va_channel_isi.va` — Deterministic multi-cursor (`h_pre, h0, h1, h2, h3`) ISI channel for DFE/SS-LMS benchmarking
