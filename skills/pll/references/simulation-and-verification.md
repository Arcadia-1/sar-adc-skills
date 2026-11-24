# PLL Spectre Simulation & Verification Guide

## 1. Phased Verification Strategy

Never jump straight to full-transistor closed-loop PLL transient simulation — a 1 GHz–10 GHz PLL takes $2\text{–}20\;\mu\text{s}$ ($2{,}000\text{–}200{,}000$ VCO cycles!) to lock, making brute-force full-transistor transient painfully slow and impossible for phase-noise extraction. Follow a disciplined 4-phase flow:

1. **Phase 1 — Behavioral Verilog-A & Phase-Domain AC Closure:**
   - Verify loop stability ($f_u$, $\text{PM}$, $\text{GM}$, peaking) in `< 1 s` with [`tb_int_n_pll_ac_loop.scs`](../assets/tb/int_n_pll/tb_int_n_pll_ac_loop.scs).
   - Verify nonlinear locking, cycle slipping, Fractional-N MASH 1-1-1 average ratio, and ADPLL digital PI convergence in a few seconds using the bundled Verilog-A models in [`../assets/va/`](../assets/va/) and top-level decks [`int_n_pll/`](../assets/tb/int_n_pll/README.md), [`frac_n_pll/`](../assets/tb/frac_n_pll/README.md), and [`adpll/`](../assets/tb/adpll/README.md).
2. **Phase 2 — Per-Block Transistor Characterization (Spectre RF & Tran):**
   - **VCO / DCO** ([`../assets/tb/vco/`](../assets/tb/vco/README.md), [`../assets/tb/tdc_dco/`](../assets/tb/tdc_dco/README.md)): Autonomous `pss` + relative `pnoise` $\to \mathcal{L}(\Delta f)$, $\text{FoM}$, integrated jitter, $K_{\text{VCO}}/K_{\text{DCO}}$ tuning curve, startup at `ss`.
   - **PFD + CP** ([`../assets/tb/pfd_cp/`](../assets/tb/pfd_cp/README.md)): Swept $\Delta t$ charge-transfer curve $\to$ dead-zone free, Up/Down mismatch, compliance, and driven `pss+pnoise` for CP noise.
   - **Divider / MMD** ([`../assets/tb/divider/`](../assets/tb/divider/README.md)): Functional ratio & max frequency across PVT + driven sampled `pnoise` for divider added jitter.
   - **TDC (ADPLL)** ([`../assets/tb/tdc_dco/`](../assets/tb/tdc_dco/README.md)): Edge-delay ramp $\to$ $\Delta t_{\text{res}}$, DNL/INL, PVT range.
   - **Noise budget synthesis:** Plug measured block noise curves ($\mathcal{L}_{\text{vco}}$, $S_{I,\text{cp}}$, $\mathcal{L}_{\text{div}}$, $\mathcal{L}_{\text{tdc}}$, $R$ thermal, $\Delta\Sigma$) into the linear phase-domain NTF model to predict exact closed-loop phase noise and RMS jitter in milliseconds!
3. **Phase 3 — Hybrid Replacement:**
   - Replace one block at a time with its transistor subcircuit inside the fast closed-loop testbench (e.g., transistor PFD+CP + behavioral VCO/Div to verify real reference spurs and noise folding; transistor VCO + behavioral PFD/CP/Div to verify real startup and varactor tuning behavior).
4. **Phase 4 — Full Transistor Lock & Post-Layout PVT Signoff:**
   - Initialize `VCTRL` (or `FTW`) close to the expected locked value to cut transient lock time by $5\text{–}10\times$; verify lock, ripple/spur, and startup across `ss`/`tt`/`ff`, temperature, and supply corners with extracted parasitics.

---

## 2. Spectre Autonomous Oscillator PSS + PNOISE Setup

A free-running VCO/DCO is an **autonomous** circuit — Spectre determines autonomous vs. driven mode solely by whether you supply the differential oscillation node pair `(OUTP OUTN)` to `pss`:

```spectre
// Autonomous shooting PSS: supply (OUTP OUTN) pins + estimated fund + tstab
pss (OUTP OUTN) pss fund=f_est harms=20 errpreset=conservative \
    tstab=t_stab autotstab=yes annotate=status

// Relative single-sideband PM phase noise L(df) [dBc/Hz] around fundamental (relharmnum=1)
pnoise (OUTP OUTN) pnoise sweeptype=relative relharmnum=1 \
    start=1k stop=100M dec=20 pnoisemethod=fullspectrum \
    noisetype=timeaverage noiseout=[pm] annotate=status
```

### Critical Oscillator PSS/PNOISE Pitfalls
1. **Run with `+aps`** (required for `pnoisemethod=fullspectrum` — classic non-APS Spectre aborts with `FATAL (SPCRTRF-15412)`).
2. **Always kick-start symmetric differential LC tanks:** A perfectly symmetric netlist with zero mismatch can sit forever at its unstable DC saddle point (zero oscillation amplitude, PSS fails or converges to DC!). Inject a tiny asymmetric current pulse during $t \in [0, 0.2/f_{\text{est}}]$ (`ic` or brief `ipulse` that turns strictly off before `tstab` ends!) so oscillation always builds cleanly without perturbing steady state.
3. **Choose `tstab` long enough to reach steady amplitude** (typically $20\text{–}100$ cycles for LC-VCO, $5\text{–}15$ cycles for Ring-VCO) and enable `autotstab=yes`.
4. **Understand `noiseout=[pm]` units and exact carrier normalization:** In Spectre PSF ASCII (`pnoise.pm.pnoise`), `"out"` is single-sideband PM RMS voltage spectral density in $\text{V}_{\text{rms}}/\sqrt{\text{Hz}}$ (matching single-sideband `usb` when AM noise is negligible), and `pss.fd.pss` reports the peak complex carrier phasor $V_{\text{carr,pk}} = |V_{\text{OUTP},1} - V_{\text{OUTN},1}|$. Therefore, per IEEE Std 1139, $\mathcal{L}(\Delta f) = 20\log_{10}(\text{out} / (V_{\text{carr,pk}}/\sqrt{2}))$ (avoiding a 3.01 dB error from dividing by $V_{\text{carr,pk}}$).
5. **Phase-noise-to-jitter integration (`common/psf_utils.py`):** Remember the factor of $2$ for double-sideband variance ($\sigma_\phi^2 = 2 \int 10^{\mathcal{L}(f)/10} df$) and always state the exact integration band $[f_{\text{low}}, f_{\text{high}}]$ (e.g., `10 kHz–40 MHz` or `100 kHz–100 MHz`).
6. **Scale GHz frequency-monitor outputs below Spectre's 1 GV guard:** Outputting raw Hz (`1e9`) as a Verilog-A node voltage triggers `ERROR (SPECTRE-16384)` (1 GV blowup limit); `va_phase_err_mon.va` scales `F_INST` by `1e-9` so `1.0 V == 1.0 GHz`.

---

## 3. Closed-Loop Transient & Frequency/Jitter Measurement Tips

- **Use `va_phase_err_mon.va` for instant frequency & jitter readout:** Computing instantaneous frequency $f_{\text{inst}}[k] = 1 / (t_k - t_{k-1})$ directly inside Verilog-A lets you plot the lock trajectory and save compact `F_INST` / `T_PER` waveforms without saving every GHz VCO waveform sample!
- **Keep `maxstep` bounded during VCO/PFD transient runs:** Coarse adaptive timesteps create numerical integration jitter that masks real circuit jitter; use `errpreset=conservative` and `maxstep <= T_vco / 20` whenever measuring phase ripple, fractional spurs, or transient jitter.
- **Avoid `strobedelay >= strobeperiod`:** Spectre raises `ERROR (SPECTRE-16394)` if `strobedelay >= strobeperiod`; keep `strobedelay < strobeperiod` and filter out Spectre's off-grid `t=0` / `t=t_stop` endpoints using `extract_uniform_strobe` in `common/psf_utils.py`.
- **ADE Maestro checks:** As with SAR ADCs, always inspect Maestro's generated `input.scs` to verify `pss` oscillator nodes `(OUTP OUTN)`, `autotstab=yes`, `pnoisemethod=fullspectrum`, `noiseout=[pm]`, and corner `definitionFiles` were actually written before trusting Maestro results.

---

## 4. Industrial Integer-N CP-PLL Signoff Checklist (7 Extended Decks)

Beyond core loop stability and basic lock, tape-out-grade PLL signoff requires seven additional block and closed-loop checks — all bundled under `assets/tb/`:

1. **Multi-Sub-Band VCO Cap-Bank Overlap & Linearity ([`tb_vco_capbank_overlap.scs`](../assets/tb/vco/tb_vco_capbank_overlap.scs)):**
   - Sweeps coarse sub-band code `VCODE` via `alter` across 8 bands × 7 `VCTRL` levels. Confirms adjacent sub-band overlap $\frac{f_{\max}[k] - f_{\min}[k+1]}{f_{\text{step}}} \ge 20\%$–$25\%$ with zero blind frequency holes across PVT, and tracks varactor endpoint linearity error $K_{\text{LIN}}\,[\%]$.
2. **Isolated Charge-Pump Compliance & Matching ([`tb_cp_compliance_mismatch.scs`](../assets/tb/pfd_cp/tb_cp_compliance_mismatch.scs)):**
   - Runs `dc_up` and `dc_dn` sweeps of `V_CP` from `0` to `VDD`, measuring $I_{\text{UP}}(V_{\text{CP}})$, $I_{\text{DN}}(V_{\text{CP}})$, fractional mismatch inside the usable VCO tuning window $[V_{\text{comp,lo}}, V_{\text{comp,hi}}]$, mid-rail output resistance $r_o$, and 10%-current-drop compliance boundaries.
3. **High-Speed Divider Max Toggle & Cycle-Slip Signoff ([`tb_div_max_toggle.scs`](../assets/tb/divider/tb_div_max_toggle.scs)):**
   - Steps input clock frequency via `alter` into a realistic `50 fF` load, flagging any average or per-cycle division-ratio error (`cycle_slip`) alongside output duty cycle and 20%–80% rise/fall times to establish the slip-free ceiling $f_{\max,\text{pass}}$.
4. **Auto Band-Calibration & Lock-Detector Closure ([`tb_int_n_pll_bandcal_lock.scs`](../assets/tb/int_n_pll/tb_int_n_pll_bandcal_lock.scs)):**
   - Verifies end-to-end startup from `PLL_EN↑`: open-loop `VCTRL = VDD/2` forcing (`VCFORCE=1`), binary-search coarse-code convergence (`t_cal`, latched `VCODE`), smooth analog loop handoff (`CAL_DONE↑`), fine frequency settling (`±1%` / `±0.1%`), phase-window `LOCK` assertion, steady-state ppm error, and active supply power $P_{\text{DD}}$.
5. **Direct FFT vs. NBFM Reference Spur Signoff ([`tb_int_n_pll_ref_spur.scs`](../assets/tb/int_n_pll/tb_int_n_pll_ref_spur.scs)):**
   - Runs tight-accuracy (`+preset=cx -preset_override`, bounded `maxstep`) strobed transient over an exact integer count of $T_{\text{ref}}$ cycles after settling. Cross-checks the direct Kaiser-windowed FFT sidebands at $f_0 \pm f_{\text{ref}}$ and $\pm 2 f_{\text{ref}}$ directly against the analytical narrowband-FM prediction $20\log_{10}(K_{\text{VCO}} V_{\text{rip},1} / (2 f_{\text{ref}}))$ (matching within $< 1\text{ dB}$).
6. **Closed-Loop Supply Rejection ([`tb_int_n_pll_psrr.scs`](../assets/tb/int_n_pll/tb_int_n_pll_psrr.scs)):**
   - Injects a small sinusoidal ripple onto VCO supply `VDDA` at in-band ($f \ll f_u$), near-bandwidth ($f \approx f_u$), and out-of-band ($f \gg f_u$) frequencies via `alter`. Confirms strong in-band loop suppression transitioning to the open-loop pushing floor $20\log_{10}(K_{\text{VCO}} / K_{\text{VDD}})$ via both `F_INST(t)` demodulation and `OUTP(t)` FM sidebands.
7. **Closed-Loop Phase-Noise Budget & Programmable $N \times I_{\text{CP}}$ Matrix ([`tb_int_n_pll_noise_scaling.scs`](../assets/tb/int_n_pll/tb_int_n_pll_noise_scaling.scs)):**
   - Runs a 5-sweep Spectre phase-domain `noise` analysis (`< 1 s`) decomposing total integrated RMS jitter (`10 kHz–30 MHz`) into exact Ref/Div, CP, native $4kTR_1$, and VCO percentage shares (100% variance closure), followed by a 9-point `alter` + `stb` sweep across $N \in \{16, 32, 64\} \times I_{\text{CP}} \in \{80, 160, 320\}\;\mu\text{A}$ verifying constant $f_u$ along $I_{\text{CP}} \propto N$ and flagging any low-PM corners ($< 45^\circ$).
