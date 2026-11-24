# SerDes Spectre X Simulation & Verification Guide

## 1. Running Spectre X (`+preset=cx` / `ax` / `mx`) vs. Legacy APS

Modern high-speed SerDes verification (multi-GHz `sp`, lossy `mtline`/`nport` convolution, hundreds-of-UI PRBS eyes, and adaptive SS-LMS transients) should run on **Spectre X** rather than relying solely on legacy `+aps`:

```bash
# Golden signoff accuracy (T-coil, S-param, SBR, precision eye, comparator/slicer)
spectre +preset=cx +mt=4 -format psfascii -raw raw_cx +log sim.log tb_channel_sbr_eye.scs

# Fast accurate analog/mixed-signal iteration (long PRBS eyes, SS-LMS convergence)
spectre +preset=ax +mt=4 -format psfascii -raw raw_ax +log sim.log tb_sslms_adapt.scs
```

| Engine / Preset | CLI Flag | Accuracy & Use Case |
|---|---|---|
| **Spectre X `CX`** | `+preset=cx +mt=N` | **Golden highest accuracy** (`conservative_sigglobal`); mandatory for T-coil `S11`, `SDD21`/`SDD11`, SBR cursors, slicer sensitivity/hysteresis, precision eye, and signoff |
| **Spectre X `AX`** | `+preset=ax +mt=N` | Analog-accurate fast iteration; nearly identical to `CX` on eye height/width & SS-LMS trajectories with better speed |
| **Spectre X `MX`** | `+preset=mx +mt=N` | Mixed-signal balanced mode for large digital-heavy SerDes top-level / long `> 2000 UI` adaptation runs (cross-check final eye against `CX`/`AX`!) |
| **Spectre X `LX` / `VX`** | `+preset=lx` / `+preset=vx` | Large post-layout RC-extracted blocks; pair with `+postlpreset=cx|ax|mx` to control RC reduction aggressiveness |
| **Spectre XPS** | `+xps +cktpreset=...` | FastSPICE engine for massive SRAM/digital arrays (requires explicit `+cktpreset`; do **not** use for analog CTLE/T-coil/S-param signoff) |
| **Legacy APS** | `+aps` | Fallback only when Spectre X licenses are unavailable |

### Critical Spectre X Gotchas
1. **Spectre X overrides netlist solver tolerances by default!** When `+preset=cx|ax|mx` is active, Spectre X ignores manual `reltol`/`errpreset` inside `simulatorOptions` unless you explicitly pass **`-preset_override`** (or `-preset_override="reltol,maxstep"`). Keep `maxstep` tight in transient statements (`maxstep=2p..5p`) for clean eye/TDR edges.
2. **Do not over-subscribe `+mt`:** On small behavioral/block decks (a few dozen nodes), `+mt=1` or `+mt=2` is fastest; use `+mt=4..8` on transistor-level multi-stage CTLE/DFE/top-level decks, ensuring `jobs * mt <= physical_cores`.
3. **Causal channel models (`mtline` & `nport`):**
   - Always specify causal Djordjevic-Sarkar dielectric loss (`fgdloss` and `fgdloss1`) when using `gdloss` in Spectre `mtline`; bare `gdloss * f` is non-causal and produces pre-cursor ringing artifacts!
   - When swapping in a measured Touchstone `.s4p` file (`nport`), verify passivity and causality (`interp=rational` / `passivity=yes` / `causality=yes`) before trusting transient eye height!

---

## 2. Bundled Process-Independent Spectre Testbench Suites (`assets/tb/`)

All 7 suites (15 `.scs` decks) run cleanly under **Spectre X `+preset=cx`** and **`+preset=ax`** with zero PDK dependencies and zero-dependency Python analyzers backed by [`common/psf_utils.py`](../../../common/psf_utils.py):

1. **Channel (`assets/tb/channel/`):**
   - [`tb_channel_sp_tdr.scs`](../assets/tb/channel/tb_channel_sp_tdr.scs) + `analyze_channel.py sp` / `tdr`: 4-port differential `SDD21`, `SDD11`, and TDR `Z_TDR(t)` on causal passive [`channel_diff_lossy.scs`](../assets/tb/channel/channel_diff_lossy.scs) (or swap in your own `nport`).
   - [`tb_channel_sbr_eye.scs`](../assets/tb/channel/tb_channel_sbr_eye.scs) + `analyze_channel.py sbr_eye`: exact 1-UI SBR cursors (`h_-1, h0, h1..h5`, PDA eye) and PRBS-7 folded eye height & width.
2. **TX & FFE (`assets/tb/tx_ffe/`):**
   - [`tb_tx_s11.scs`](../assets/tb/tx_ffe/tb_tx_s11.scs) + `analyze_tx_ffe.py s11`: 2-port AC-coupled differential TX output return loss `SDD11(f)`.
   - [`tb_dc_termination.scs`](../assets/tb/tx_ffe/tb_dc_termination.scs) + `analyze_tx_ffe.py dc_term`: output swing sweep verifying `R_term(V) = dV/dI` accuracy vs. `50 ohm` and linearity across swing (critical for VML/SST drivers and RX termination!).
   - [`tb_tx_ffe_channel.scs`](../assets/tb/tx_ffe/tb_tx_ffe_channel.scs) + `analyze_tx_ffe.py eye`: 4-tap TX FFE driving `channel_diff_lossy.scs` (compare raw `w_main=1` vs. FFE-equalized SBR & eye).
3. **CTLE, VGA & Offset Cal (`assets/tb/ctle_vga/`):**
   - [`tb_ctle_ac_noise.scs`](../assets/tb/ctle_vga/tb_ctle_ac_noise.scs) + `analyze_ctle_vga.py ac_noise`: differential AC DC/peak gain, peaking boost, `f_peak`, `-3 dB` BW, and shaped output RMS noise.
   - [`tb_ctle_channel_ac.scs`](../assets/tb/ctle_vga/tb_ctle_channel_ac.scs) + `analyze_ctle_vga.py channel_ac`: combined `H_ch(f) * H_ctle(f)` DC-to-Nyquist flatness & over-peaking check.
   - [`tb_ctle_channel_eye.scs`](../assets/tb/ctle_vga/tb_ctle_channel_eye.scs) + `analyze_ctle_vga.py eye`: before-vs-after CTLE eye height, eye width, and SBR ISI cancellation.
   - [`tb_vga_offset_cal.scs`](../assets/tb/ctle_vga/tb_vga_offset_cal.scs) + `analyze_ctle_vga.py offset_cal`: closed-loop digital offset calibration canceling injected DC offset to `< 1 LSB`.
4. **Slicer & 3-Tap DFE (`assets/tb/slicer_dfe/`):**
   - [`tb_slicer_hys_vtf.scs`](../assets/tb/slicer_dfe/tb_slicer_hys_vtf.scs) + `analyze_slicer_dfe.py vtf`: bidirectional triangle sweep extracting `V_th,up`, `V_th,dn`, static offset, and dynamic hysteresis (with [`va_slicer_cml.va`](../assets/va/va_slicer_cml.va)).
   - [`tb_slicer_noise_tran.scs`](../assets/tb/slicer_dfe/tb_slicer_noise_tran.scs) + `analyze_slicer_dfe.py noise_tran`: 300-cycle fixed-overdrive transient-noise sensitivity extracting probit `sigma_n_mvrms` and `BER = 1e-12` (`7.03 * sigma_n`) half-eye margin.
   - [`tb_dfe_3tap_eye.scs`](../assets/tb/slicer_dfe/tb_dfe_3tap_eye.scs) + `analyze_slicer_dfe.py dfe_eye`: closed-loop 3-tap DFE opening a severely closed post-cursor ISI eye with `0` bit errors.
5. **Sign-Sign LMS Adaptation (`assets/tb/sslms/`):**
   - [`tb_sslms_adapt.scs`](../assets/tb/sslms/tb_sslms_adapt.scs) + `analyze_sslms.py --mode dfe`: live concurrent PRBS-9 adaptation of VGA gain + 3-tap DFE coefficients (`h1, h2, h3`) with `DONE` freeze verification.
   - [`tb_sslms_ctle_boost.scs`](../assets/tb/sslms/tb_sslms_ctle_boost.scs) + `analyze_sslms.py --mode ctle_boost`: transition-filtered (`edge_only=1`) CTLE `VBOOST` adaptation on the real lossy `mtline` channel.
6. **Bridged T-Coil (`assets/tb/tcoil/`):**
   - [`tb_tcoil_bw.scs`](../assets/tb/tcoil/tb_tcoil_bw.scs) + `analyze_tcoil.py`: bare `R_L || C_L` vs. bridged T-coil `ac` bandwidth ratio (`2.83x`), `S11` return loss, and step overshoot.
7. **End-to-End Full Link (`assets/tb/link_top/`):**
   - [`tb_serdes_link_top.scs`](../assets/tb/link_top/tb_serdes_link_top.scs) + `analyze_link_top.py`: full `TX FFE -> 0.85 m Long-Reach Channel (-24 dB @ 5 GHz) -> RX CTLE -> 3-Tap DFE -> Slicer` stage-by-stage eye progression and `0`-BER verification.

> **Universal Device & Statistical Utilities (`common/tb/`):** For process-independent NMOS/PMOS $g_m/I_D$ lookup tables (`tb_gmid_nmos_pmos.scs`), Spectre `montecarlo` mismatch offset statistics (`tb_mc_offset_template.scs`), and 5-stage ring-oscillator PVT speed monitoring (`tb_ring_process_mon.scs`), see [`common/tb/README.md`](../../../common/tb/README.md).

---

## 3. Common SerDes Verification Pitfalls

- **Non-causal channel ringing:** Always check `h_-2, h_-1` in SBR — large unphysical pre-cursor ripples before the propagation flight time mean your S-parameter interpolation or `mtline` loss model violated causality!
- **Forgotten `strobeoutput=strobeonly` filtering:** In `tb_slicer_hys_vtf.scs`, Spectre appends off-grid `t = 0` and `t = t_stop` points; always pass traces through `extract_uniform_strobe()`.
- **Short PRBS pattern hiding long-tail ISI:** PRBS-7 (`127 UI`) is great for fast block checks; always sign off final equalizers and SS-LMS loops on PRBS-9 (`511 UI`) or longer (`PRBS-15` / worst-case lone-bit patterns) so long-run DC wander and correlated tap leakage are exposed.
- **T-coil mutual-inductor dot polarity:** Series-aiding (`+k` with `L1 (IN MID)` and `L2 (MID OUT)`) puts `-M` in the center tap for constant-resistance matching; flipping `k` negative destroys both `S11` and bandwidth!
