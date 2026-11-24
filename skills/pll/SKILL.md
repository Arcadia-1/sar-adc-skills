---
name: pll-skill
description: >
  Process-independent PLL engineering guide and Spectre verification toolkit
  covering Integer-N CP-PLL, Fractional-N Delta-Sigma (MASH 1-1-1) PLL, and
  All-Digital PLL (TDC-ADPLL and Bang-Bang ADPLL). Covers phase-domain loop
  modeling, 2nd/3rd-order passive loop filter sizing, phase noise and RMS
  jitter integration, optimal loop bandwidth, MASH quantization noise shaping
  and CP nonlinearity noise folding, TDC/DCO quantization budgets, digital PI
  loop filters, LC vs. Ring VCO/DCO design, tri-state PFD/CP/MMD dividers,
  12 Verilog-A behavioral models, and 17 standalone Spectre X testbenches across
  7 suites (autonomous oscillator PSS+PNOISE, cap-bank overlap, PFD+CP beat
  sweep & compliance, MMD & max-toggle, TDC/DCO, AC loop, closed-loop lock,
  auto band-calibration, reference spur FFT, closed-loop PSRR, and noise/N-ICP
  signoff). Use for any PLL architecture, sizing, noise budgeting, debugging,
  or Spectre verification task.
---

# PLL Skill (Integer-N, Fractional-N & ADPLL)

A process-independent engineering guide and Spectre verification toolkit for phase-locked loops — spanning Integer-N CP-PLLs, Fractional-N MASH 1-1-1 $\Delta\Sigma$ PLLs, and All-Digital PLLs (TDC-ADPLL and Bang-Bang ADPLL).

## Read Order

Read only the minimum reference needed for the user's task:

### Architectures & System Design
- `references/pll-fundamentals.md`
  Phase-domain linear model, Type-I vs. Type-II loops, noise transfer functions, optimal bandwidth rule, phase-noise-to-RMS-jitter conversion, and Integer-N vs. Fractional-N vs. ADPLL selection.
- `references/integer-n-pll.md`
  Type-II CP-PLL exact 2nd/3rd-order passive loop filter sizing (`R, C1, C2, R3, C3`), reference spur equations (leakage, CP mismatch, feedthrough), settling time, cycle slipping, and verification (`assets/tb/int_n_pll/`).
- `references/fractional-n-pll.md`
  Multi-Modulus Divider (MMD), 3rd-order MASH 1-1-1 $\Delta\Sigma$ noise shaping, 3rd-order loop filter requirement, charge-pump nonlinearity & quantization-noise folding, static bleed/DTC mitigation, integer-boundary spurs (IBS), and verification (`assets/tb/frac_n_pll/`).
- `references/adpll.md`
  TDC-ADPLL (divider-based and phase-domain counter+TDC) and Bang-Bang ADPLL (BBPLL), digital PI loop filter (`alpha`, `beta`, latency PM loss, gear-shifting), TDC and DCO quantization noise floors, and verification (`assets/tb/tdc_dco/`, `assets/tb/adpll/`).

### Submodules & Verification
- `references/vco-and-dco.md`
  LC-VCO vs. Ring-VCO vs. segmented DCO, startup margin, Leeson/Hajimiri phase noise, FoM / FoM_T, $K_{\text{VCO}}$ / $K_{\text{DCO}}$ AM-to-PM tradeoffs, and autonomous `pss+pnoise` verification (`assets/tb/vco/`).
- `references/pfd-cp-divider.md`
  Tri-state PFD dead-zone vs. reset pulse width $t_{\text{rst}}$, CP mismatch/compliance/replica buffer, CML/TSPC prescalers, 2/3-cell MMD, retiming flip-flop, and verification (`assets/tb/pfd_cp/`, `assets/tb/divider/`).
- `references/simulation-and-verification.md`
  Phased verification flow (Phase 1 VA/AC $\to$ Phase 2 per-block RF $\to$ Phase 3 hybrid $\to$ Phase 4 transistor PVT), exact Spectre autonomous oscillator `pss (OUTP OUTN)` + relative `pnoise` (`noiseout=[pm]`), kick-start rules, and Maestro pitfalls.

## Default Workflow

1. **Clarify target specs:** Output frequency range, channel step $\Delta f$, reference frequency $f_{\text{ref}}$, integrated RMS jitter & band (or spot phase noise), reference/fractional spur limits, settling time, power/area, and CMOS node class.
2. **Choose architecture:** Integer-N (fixed clock multiplier, high $f_{\text{ref}}$), Fractional-N MASH 1-1-1 (fine step + low RF phase noise), or ADPLL/BBPLL (compact area in scaled CMOS, fast gear-shifting, digital calibration).
3. **Build noise & loop budgets:** Allocate in-band noise (Ref, CP/TDC, Div) vs. out-of-band VCO/DCO noise, choose $f_u \le f_{\text{ref}}/10$ (or $\le f_{\text{ref}}/30$ for MASH 1-1-1 without cancellation), verify $\text{PM} \approx 55^\circ\text{–}65^\circ$, and size loop filter or digital $(\alpha, \beta)$.
4. **Verify block-by-block and closed-loop:** Run phase-domain AC + behavioral Verilog-A lock first, then per-block Spectre RF/tran characterization, then hybrid replacement.

## Bundled Assets

### Process-Independent Spectre Testbenches (`assets/tb/`)
Every testbench plugs in external `models_corner.scs` + `dut_subckt.scs` and pairs with a standalone Python PSF ASCII analyzer (sharing repo-root `common/psf_utils.py` and `common/models_generic_bsim4.scs`):

- `assets/tb/vco/` — `tb_vco_tuning_kvco.scs`, `tb_vco_pss_pnoise.scs` (autonomous `pss` + relative `pm` `pnoise`), `tb_vco_capbank_overlap.scs` (multi-sub-band overlap & `K_LIN`), `analyze_vco.py`
- `assets/tb/pfd_cp/` — `tb_pfd_cp_transfer.scs` (detuned beat-sweep $Q(\Delta t)$, mismatch & dead-zone check), `tb_cp_compliance_mismatch.scs` (DC compliance & UP/DN mismatch), `analyze_pfd_cp.py`
- `assets/tb/divider/` — `tb_div_func_mmd.scs` (Integer-N and Fractional-N MMD ratio verification), `tb_div_max_toggle.scs` (multi-frequency `f_max`, cycle-slip, duty & slew), `analyze_divider.py`
- `assets/tb/tdc_dco/` — `tb_tdc_transfer.scs` (TDC `t_res`, DNL/INL), `tb_dco_tuning.scs` (DCO $K_{\text{DCO}}$ & monotonicity), `analyze_tdc_dco.py`
- `assets/tb/int_n_pll/` — `tb_int_n_pll_ac_loop.scs` (phase-domain `stb` + `ac`), `tb_int_n_pll_lock.scs` (closed-loop lock), `tb_int_n_pll_bandcal_lock.scs` (AFC binary-search band-cal & lock-detect), `tb_int_n_pll_ref_spur.scs` (direct FFT vs. NBFM reference spurs), `tb_int_n_pll_psrr.scs` (closed-loop supply rejection), `tb_int_n_pll_noise_scaling.scs` (closed-loop phase-noise budget & 9-pt $N \times I_{\text{CP}}$ `stb` matrix), `analyze_int_n_pll.py`
- `assets/tb/frac_n_pll/` — `tb_frac_n_pll_lock.scs` (MASH 1-1-1 fractional lock & DSM ripple), `analyze_frac_n_pll.py`
- `assets/tb/adpll/` — `tb_adpll_lock.scs` (Integer/Fractional TDC-ADPLL & BBPLL lock), `analyze_adpll.py`

### Verilog-A Behavioral Library (`assets/va/`)
12 Spectre-verified models for Phase 1–3 behavioral and hybrid PLL simulation:

- `assets/va/va_pfd.va` — tri-state PFD with controlled dead-zone reset delay `td_rst`
- `assets/va/va_cp.va` — charge pump with `mismatch`, compliance clamping, `i_leak`, and Frac-N `i_offset`
- `assets/va/va_vco.va` — differential VCO with `kvco` and optional per-cycle `jitter_rms`
- `assets/va/va_vco_multiband.va` — multi-sub-band differential LC-VCO with coarse `VCODE`, S-curve `kvco_nl3`, supply pushing `k_vdd`, and core current `i_dd`
- `assets/va/va_bandcal_lockdet.va` — digital binary-search auto-band-calibration FSM (`VCODE`, `CAL_DONE`, `VCFORCE`) & phase-window `LOCK` detector
- `assets/va/va_div_int.va` — programmable Integer-N divider
- `assets/va/va_mmd_mash111.va` — Multi-Modulus Divider + 3rd-order MASH 1-1-1 $\Delta\Sigma$ modulator
- `assets/va/va_tdc.va` — PFD-assisted signed TDC with `t_res`, `t_offset`, and `inl_lsb`
- `assets/va/va_dco.va` — differential DCO with `k_dco` and integer `FTW` quantization
- `assets/va/va_dlf_pi.va` — clocked digital PI loop filter (`alpha`, `beta`)
- `assets/va/va_bbpd.va` — 1-bit Bang-Bang Phase Detector for BB-ADPLL
- `assets/va/va_phase_err_mon.va` — instantaneous frequency & cycle period monitor

## Scope

- Intentionally process-independent (no proprietary foundry PDK models or signoff device sizes).
- Pair with your process documentation and EDA execution skills (`spectre` / `virtuoso`) for PDK-specific transistor sizing and post-layout closure.
