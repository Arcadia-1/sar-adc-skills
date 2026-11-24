# SerDes Spectre X Simulation & Verification Guide

## 1. Running Spectre X (`+preset=cx` / `ax` / `mx`) vs. Legacy APS

Modern high-speed SerDes verification (multi-GHz `sp`, lossy `mtline`/`nport` convolution, hundreds-of-UI NRZ/PAM4 eyes, CDR JTOL, `trannoise`, and adaptive SS-LMS transients) should run on **Spectre X** rather than relying solely on legacy `+aps`:

```bash
# Golden signoff accuracy (T-coil, S-param, SBR, precision eye, slicer, PI/BBPD, PAM4 RLM)
spectre +preset=cx +mt=4 -format psfascii -raw raw_cx +log sim.log tb_channel_sbr_eye.scs

# Ultra-clean coherent FFT / HD3 / P1dB floor (honors tight netlist reltol & maxstep)
spectre +preset=cx -preset_override +mt=2 -format psfascii -raw raw_lin +log sim.log tb_ctle_linearity_p1db.scs

# Fast accurate analog/mixed-signal iteration (long PRBS eyes, CDR JTOL, trannoise, SS-LMS)
spectre +preset=ax +mt=4 -format psfascii -raw raw_ax +log sim.log tb_cdr_jtol.scs
```

| Engine / Preset | CLI Flag | Accuracy & Use Case |
|---|---|---|
| **Spectre X `CX`** | `+preset=cx +mt=N` | **Golden highest accuracy** (`conservative_sigglobal`); mandatory for T-coil `S11`, `SDD21`/`SDD11`/`SCD21`, SBR cursors, slicer sensitivity/hysteresis/`Clk-to-Q`, PI/BBPD, PAM4 RLM, and signoff |
| **Spectre X `AX`** | `+preset=ax +mt=N` | Analog-accurate fast iteration; ideal for long CDR JTOL (`>= 2000 UI`), TX jitter bathtub (`> 500 UI`), `trannoise`, crosstalk, and SS-LMS convergence |
| **Spectre X `MX`** | `+preset=mx +mt=N` | Mixed-signal balanced mode for large digital-heavy SerDes top-level / long `> 2000 UI` runs (cross-check final eye against `CX`/`AX`!) |
| **Spectre X `LX` / `VX`** | `+preset=lx` / `+preset=vx` | Large post-layout RC-extracted blocks; pair with `+postlpreset=cx|ax|mx` to control RC reduction aggressiveness |
| **Spectre XPS** | `+xps +cktpreset=...` | FastSPICE engine for massive SRAM/digital arrays (requires explicit `+cktpreset`; do **not** use for analog CTLE/T-coil/S-param signoff) |
| **Legacy APS** | `+aps` | Fallback only when Spectre X licenses are unavailable |

### Critical Spectre X Gotchas
1. **Spectre X overrides netlist solver tolerances by default!** When `+preset=cx|ax|mx` is active, Spectre X ignores manual `reltol`/`errpreset` inside `simulatorOptions` unless you explicitly pass **`-preset_override`** (essential for coherent FFT `HD3`/`SFDR` in `tb_ctle_linearity_p1db.scs`!). Keep `maxstep` tight in transient statements (`maxstep=1p..5p`) for clean eye/TDR/Clk-to-Q edges.
2. **Do not over-subscribe `+mt`:** On small behavioral/block decks (a few dozen nodes), `+mt=1` or `+mt=2` is fastest; use `+mt=4..8` on transistor-level multi-stage CTLE/DFE/top-level decks, ensuring `jobs * mt <= physical_cores`.
3. **Causal channel models (`mtline` & `nport`):**
   - Always specify causal Djordjevic-Sarkar dielectric loss (`fgdloss` and `fgdloss1`) when using `gdloss` in Spectre `mtline`; bare `gdloss * f` is non-causal and produces pre-cursor ringing artifacts!
   - When simulating measured Touchstone `.s4p` channels via Spectre X `nport`, use **`interp=bbspice passivity=fit_enforce`** (delay-extracting Broadband SPICE rational macro-model). Legacy `interp=rational` lacks delay extraction and can fail DC convergence (`> 80` poles) on electrically long transmission-line channels; include low-frequency RL knee points (`1..50 MHz`) to avoid `CMI-2839` discontinuity warnings.
4. **Transient sine phase parameter:** In Spectre `vsource type=sine`, use **`sinephase=-90`** for transient quadrature clocks (`phase=-90` applies ONLY to AC analysis!).
5. **Transistor-level `trannoise` (`noiseruns=1`):** Append `noisefmax=50G noiseruns=1 noiseseed=1` directly to `tran` in `tb_slicer_noise_tran.scs` — always verify interior probit probability (`0.05 < P(1) < 0.95`) across two overdrive levels and isolate StrongARM latch nodes from SR-latch kickback with symmetric inverter buffers!

---

## 2. Bundled Process-Independent Spectre X Testbench Suites (`assets/tb/`)

All 10 suites (`28` executable `.scs` testbench decks + `channel_diff_lossy.scs` + `channel_synth_causal.s4p`) run cleanly under **Spectre X `+preset=cx`** and **`+preset=ax`** with zero PDK dependencies and zero-dependency Python analyzers backed by [`common/psf_utils.py`](../../../common/psf_utils.py):

1. **Channel (`assets/tb/channel/`):**
   - [`tb_channel_sp_tdr.scs`](../assets/tb/channel/tb_channel_sp_tdr.scs) + `analyze_channel.py sp` / `tdr`: 4-port differential `SDD21`, `SDD11`, and TDR `Z_TDR(t)` on causal passive [`channel_diff_lossy.scs`](../assets/tb/channel/channel_diff_lossy.scs).
   - [`tb_channel_sbr_eye.scs`](../assets/tb/channel/tb_channel_sbr_eye.scs) + `analyze_channel.py sbr_eye`: exact 1-UI SBR cursors (`h_-1, h0, h1..h5`, PDA eye) and PRBS-7 folded eye height & width.
   - [`tb_channel_nport_s4p.scs`](../assets/tb/channel/tb_channel_nport_s4p.scs) + `analyze_channel.py nport_s4p`: Spectre X `nport` (`interp=bbspice passivity=fit_enforce`) `sp` + SBR causality check (`|h_-2|/h0`) + PRBS-7 eye on bundled analytically-generated passive causal [`channel_synth_causal.s4p`](../assets/tb/channel/channel_synth_causal.s4p).
   - [`tb_channel_xtalk_fext_next.scs`](../assets/tb/channel/tb_channel_xtalk_fext_next.scs) + `analyze_channel.py xtalk`: victim vs. asynchronous PRBS-9 FEXT/NEXT aggressors quantifying eye height/width loss, quiet-victim FEXT/NEXT mVrms/mVpp, and AC coupling dB.
2. **TX & FFE (`assets/tb/tx_ffe/`):**
   - [`tb_tx_s11.scs`](../assets/tb/tx_ffe/tb_tx_s11.scs) + `analyze_tx_ffe.py s11`: 2-port AC-coupled differential TX output return loss `SDD11(f)`.
   - [`tb_dc_termination.scs`](../assets/tb/tx_ffe/tb_dc_termination.scs) + `analyze_tx_ffe.py dc_term`: output swing sweep verifying `R_term(V) = dV/dI` accuracy vs. `50 ohm` and flatness across swing.
   - [`tb_tx_ffe_channel.scs`](../assets/tb/tx_ffe/tb_tx_ffe_channel.scs) + `analyze_tx_ffe.py eye`: 4-tap TX FFE driving `channel_diff_lossy.scs`.
3. **CTLE, VGA & Offset Cal (`assets/tb/ctle_vga/`):**
   - [`tb_ctle_ac_noise.scs`](../assets/tb/ctle_vga/tb_ctle_ac_noise.scs) + `analyze_ctle_vga.py ac_noise`: differential AC peaking, `f_peak`, `-3 dB` BW, and shaped output RMS noise.
   - [`tb_ctle_channel_ac.scs`](../assets/tb/ctle_vga/tb_ctle_channel_ac.scs) + `analyze_ctle_vga.py channel_ac`: combined `H_ch(f) * H_ctle(f)` DC-to-Nyquist flatness & over-peaking check.
   - [`tb_ctle_channel_eye.scs`](../assets/tb/ctle_vga/tb_ctle_channel_eye.scs) + `analyze_ctle_vga.py eye`: before-vs-after CTLE eye height, eye width, and SBR ISI cancellation.
   - [`tb_ctle_linearity_p1db.scs`](../assets/tb/ctle_vga/tb_ctle_linearity_p1db.scs) + `analyze_ctle_vga.py linearity`: 8-point coherent large-signal sine sweep extracting input/output `P1dB` (`Vpp` & `dBm` @ `100 ohm`), `HD2`, `HD3`, `THD`, and `SFDR`.
   - [`tb_vga_offset_cal.scs`](../assets/tb/ctle_vga/tb_vga_offset_cal.scs) + `analyze_ctle_vga.py offset_cal`: closed-loop digital offset calibration canceling injected DC offset to `< 1 LSB`.
4. **Slicer & 3-Tap DFE (`assets/tb/slicer_dfe/`):**
   - [`tb_slicer_hys_vtf.scs`](../assets/tb/slicer_dfe/tb_slicer_hys_vtf.scs) + `analyze_slicer_dfe.py vtf`: bidirectional triangle sweep extracting `V_th,up`, `V_th,dn`, static offset, and dynamic hysteresis.
   - [`tb_slicer_noise_tran.scs`](../assets/tb/slicer_dfe/tb_slicer_noise_tran.scs) + `analyze_slicer_dfe.py noise_tran`: 300-cycle fixed-overdrive transient-noise sensitivity extracting probit `sigma_n_mvrms` and `BER = 1e-12` half-eye margin (verified with real BSIM4 `trannoise`).
   - [`tb_slicer_clk2q_setup_hold.scs`](../assets/tb/slicer_dfe/tb_slicer_clk2q_setup_hold.scs) + `analyze_slicer_dfe.py clk2q_sh`: 8-point overdrive sweep (`100 mV..0.5 mV`) extracting `Clk-to-Q`, `tau_regen [ps]`, and 21-step Setup/Hold timing margin.
   - [`tb_dfe_3tap_eye.scs`](../assets/tb/slicer_dfe/tb_dfe_3tap_eye.scs) + `analyze_slicer_dfe.py dfe_eye`: closed-loop 3-tap DFE opening a severely closed post-cursor ISI eye with `0` bit errors.
5. **Sign-Sign LMS Adaptation (`assets/tb/sslms/`):**
   - [`tb_sslms_adapt.scs`](../assets/tb/sslms/tb_sslms_adapt.scs) + `analyze_sslms.py --mode dfe`: live concurrent PRBS-9 adaptation of VGA gain + 3-tap DFE coefficients (`h1, h2, h3`) with `DONE` freeze verification.
   - [`tb_sslms_ctle_boost.scs`](../assets/tb/sslms/tb_sslms_ctle_boost.scs) + `analyze_sslms.py --mode ctle_boost`: transition-filtered (`edge_only=1`) CTLE `VBOOST` adaptation on the real lossy `mtline` channel.
6. **Bridged T-Coil & RX Front-End (`assets/tb/tcoil/`):**
   - [`tb_tcoil_bw.scs`](../assets/tb/tcoil/tb_tcoil_bw.scs) + `analyze_tcoil.py`: bare `R_L || C_L` vs. bridged T-coil `ac` bandwidth ratio (`2.83x`), `S11` return loss, and step overshoot.
   - [`tb_rx_frontend_sdd11_scd21.scs`](../assets/tb/tcoil/tb_rx_frontend_sdd11_scd21.scs) + `analyze_tcoil.py --mode rx_frontend`: 4-port differential RX ESD + T-coil + mismatch network extracting `SDD11`, `SCD11`, `SDD21`, `SCD21`, and `SDC21`.
7. **Clock & Data Recovery (`assets/tb/cdr/`):**
   - [`tb_bbpd_transfer.scs`](../assets/tb/cdr/tb_bbpd_transfer.scs) + `analyze_cdr.py bbpd`: vernier phase sweep across `[-0.46 UI, +0.47 UI]` verifying early/late Bang-Bang polarity and metastability dead zone.
   - [`tb_pi_linearity.scs`](../assets/tb/cdr/tb_pi_linearity.scs) + `analyze_cdr.py pi`: 65-step full-$2\pi$ PI code sweep extracting step size, monotonicity, DNL, and INL `[LSB / mUI / deg]`.
   - [`tb_cdr_jtol.scs`](../assets/tb/cdr/tb_cdr_jtol.scs) + `analyze_cdr.py jtol`: closed-loop 2nd-order Bang-Bang PI CDR tracking SJ-modulated PRBS-7 extracting tracking error, `|JTF(f_sj)|`, and 0-BER JTOL pass/fail.
8. **PAM4 Signaling & DFE (`assets/tb/pam4/`):**
   - [`tb_pam4_tx_rlm_eye.scs`](../assets/tb/pam4/tb_pam4_tx_rlm_eye.scs) + `analyze_pam4.py tx_rlm`: exact IEEE 802.3 RLM (`>= 0.95` check), level symmetry, and lower/mid/upper 3-eye heights & widths.
   - [`tb_pam4_dfe_ber.scs`](../assets/tb/pam4/tb_pam4_dfe_ber.scs) + `analyze_pam4.py dfe_ber`: PAM4 TX -> lossy channel -> 3-threshold slicer + 1-tap PAM4 DFE verifying 3-eye opening and `0` symbol/Gray-bit errors.
9. **Clocking & Jitter Bathtub (`assets/tb/clocking_jitter/`):**
   - [`tb_clk_dcd_iq_skew.scs`](../assets/tb/clocking_jitter/tb_clk_dcd_iq_skew.scs) + `analyze_clocking_jitter.py dcd_iq`: 5 GHz half-rate 4-phase clock DCD (`%`/`ps`) and 90-degree I/Q skew (`deg`/`ps`) before vs. after calibration.
   - [`tb_tx_jitter_bathtub.scs`](../assets/tb/clocking_jitter/tb_tx_jitter_bathtub.scs) + `analyze_clocking_jitter.py bathtub`: full TX jitter decomposition (`DCD`, `DDJ`, `SJ`, unbiased ANOVA `RJ_rms`) and Dual-Dirac bathtub `BER = 1e-12` eye width extrapolation.
10. **End-to-End Full Link (`assets/tb/link_top/`):**
    - [`tb_serdes_link_top.scs`](../assets/tb/link_top/tb_serdes_link_top.scs) + `analyze_link_top.py`: full `TX FFE -> 0.85 m Long-Reach Channel (-24 dB @ 5 GHz) -> RX CTLE -> 3-Tap DFE -> Slicer` stage-by-stage eye progression and `0`-BER verification.

> **Universal Device & Statistical Utilities (`common/tb/`):** For process-independent NMOS/PMOS $g_m/I_D$ lookup tables (`tb_gmid_nmos_pmos.scs`), Spectre `montecarlo` mismatch offset statistics (`tb_mc_offset_template.scs`), and 5-stage ring-oscillator PVT speed monitoring (`tb_ring_process_mon.scs`), see [`common/tb/README.md`](../../../common/tb/README.md).

---

## 3. Common SerDes Verification Pitfalls

- **Non-causal channel ringing:** Always check `h_-2` in SBR — non-zero ringing before the propagation flight time means your S-parameter interpolation (`interp=rational` vs. `bbspice`) or `mtline` loss model violated causality!
- **Forgotten `strobeoutput=strobeonly` filtering:** In `tb_slicer_hys_vtf.scs`, `tb_slicer_noise_tran.scs`, and `tb_ctle_linearity_p1db.scs`, Spectre appends off-grid `t = 0` and `t = t_stop` points; always pass traces through `extract_uniform_strobe()` and enforce `strobedelay < strobeperiod`.
- **Short PRBS pattern hiding long-tail ISI:** PRBS-7 (`127 UI`) is great for fast block checks; always sign off final equalizers and SS-LMS loops on PRBS-9 (`511 UI`) or longer (`PRBS-15` / worst-case lone-bit patterns) so long-run DC wander and correlated tap leakage are exposed.
- **T-coil mutual-inductor dot polarity:** Series-aiding (`+k` with `L1 (IN MID)` and `L2 (MID OUT)`) puts `-M` in the center tap for constant-resistance matching; flipping `k` negative collapses both `S11` (from `-125 dB` to `-0.5 dB`) and bandwidth (`2.83x` to `1.56x`)!
- **PAM4 & CDR negative signoff checks:** Always run fault-injection sanity checks — mismatched PAM4 `rlm_err` dropping `RLM < 0.95`, excess CDR SJ breaking the Bang-Bang slew limit (`bit_errors > 0`), and large CTLE swing hitting `P1dB` compression — to prove your verification harness actually catches real failures.
