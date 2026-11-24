# SerDes CDR, PAM4 Signaling, Clocking/Jitter & Industrial Signoff Additions

## 1. Clock & Data Recovery (CDR): BBPD, Phase Interpolator & 2nd-Order Loop

### 1.1 2x-Oversampled Alexander (Bang-Bang) Phase Detector
A full-rate 2x-oversampled Alexander BBPD samples the differential NRZ input `(INP, INN)` twice per UI:
- **Data sampler** (rising edge of recovered `CLKP - CLKN`): captures $D_k = \text{sign}(V_{\text{in}}(t_{\text{data}}))$ at eye center.
- **Edge sampler** (falling edge, $0.5\;\text{UI}$ earlier): captures $E_{k-1} = \text{sign}(V_{\text{in}}(t_{\text{edge}}))$ near the transition between $D_{k-1}$ and $D_k$.

On each data edge where a bit transition occurred ($D_k \neq D_{k-1}$):
- **Clock LATE** ($E_{k-1} = D_k$, edge sampled after the transition): assert **`UP = 1, DN = 0`** (advance / speed up recovered clock).
- **Clock EARLY** ($E_{k-1} = D_{k-1}$, edge sampled before the transition): assert **`UP = 0, DN = 1`** (retard / delay recovered clock).
- **No transition** ($D_k = D_{k-1}$) or **metastable edge sample** ($|V_{\text{edge}}| < v_{\text{meta}}$): **`UP = DN = 0`** (hold / dead zone).

The finite edge-sampler metastability aperture $v_{\text{meta}}$ creates a phase dead zone of width $\Delta\phi_{\text{dz}} \approx 2 v_{\text{meta}} / (dV/dt)$ around $0\;\text{UI}$, which limits small-signal BBPD gain and prevents idle chatter at lock. Verify early/late polarity and dead-zone width with [`assets/tb/cdr/tb_bbpd_transfer.scs`](../assets/tb/cdr/tb_bbpd_transfer.scs) and [`assets/va/va_bbpd_serdes.va`](../assets/va/va_bbpd_serdes.va).

### 1.2 Quadrature Phase Interpolator (PI) Linearity
A multi-bit quadrature PI mixes orthogonal $0^\circ$ ($V_I = A\sin\omega t$) and $-90^\circ$ ($V_Q = -A\cos\omega t$) clocks weighted by phase angle $\theta(\text{code}) = 2\pi \cdot \text{code} / N_{\text{codes}}$:

$$V_{\text{mix}}(t) = \cos(\theta)\,V_I(t) + \sin(\theta)\,V_Q(t) = A\sin(\omega t - \theta)$$

Increasing `VCODE` linearly delays the output clock by $1 / N_{\text{codes}}\;\text{UI}$ per LSB ($15.625\;\text{mUI} = 5.625^\circ$ for a 6-bit / 64-code PI). Real current-interpolating PIs exhibit characteristic **4th-harmonic quadrant-bowing INL** ($\propto \sin 4\phi$) due to triangular/finite-slew weighting and 3rd-harmonic clock content, plus odd/even code DNL. Non-monotonic steps ($\text{DNL} < -1\;\text{LSB}$) cause local CDR deadlocks and deterministic jitter spurs. Verify full-$2\pi$ DNL/INL and monotonicity using [`assets/tb/cdr/tb_pi_linearity.scs`](../assets/tb/cdr/tb_pi_linearity.scs) and [`assets/va/va_phase_interp.va`](../assets/va/va_phase_interp.va).

### 1.3 Type-II 2nd-Order PI-Based Digital CDR & JTOL Slew Limit
Unlike a VCO (which intrinsically integrates frequency into phase via $K_{\text{VCO}}/s$), a Phase Interpolator is a **direct phase actuator**. Achieving Type-II dynamics (zero steady-state phase error for both phase steps and frequency offsets $\Delta f$ in ppm) therefore requires **two nested digital accumulators** ([`assets/va/va_cdr_loop.va`](../assets/va/va_cdr_loop.va)):

$$\text{err}[n] = \text{DN}[n] - \text{UP}[n] \in \{-1, 0, +1\}$$

$$\text{freq\_acc}[n] = \text{clamp}\big(\text{freq\_acc}[n-1] + k_i \cdot \text{err}[n],\; -f_{\max},\; +f_{\max}\big)$$

$$\text{phase\_acc}[n] = \text{phase\_acc}[n-1] + k_p \cdot \text{err}[n] + \text{freq\_acc}[n]$$

- **Stability & damping:** Keep $k_p \gg \sqrt{k_i}$ (zero frequency $f_z = (k_i/k_p) f_{\text{upd}} / (2\pi)$ well below the loop bandwidth) so jitter peaking in the Jitter Transfer Function $|H_{\text{JTF}}(f)|$ stays $< 0.1\text{–}0.5\;\text{dB}$.
- **Bang-Bang JTOL slew-rate ceiling:** Tracking sinusoidal jitter $A_{\text{pp}}/2 \cdot \sin(2\pi f_{\text{sj}} t)$ demands maximum phase slew rate $\pi f_{\text{sj}} A_{\text{pp}}$ [UI/s]. A Bang-Bang CDR with transition density $D_T \approx 0.5$ saturates at:

$$\left.\frac{d\phi_{\text{CDR}}}{dt}\right|_{\max} = \frac{D_T \cdot k_p}{N_{\text{codes}} \cdot T_{\text{UI}}} \quad [\text{UI/s}]$$

Exceeding this slew limit collapses JTF gain and causes cycle slipping and burst bit errors. Verify locked tracking error, $|H_{\text{JTF}}(f_{\text{sj}})|$, and 0-BER JTOL pass/fail with [`assets/tb/cdr/tb_cdr_jtol.scs`](../assets/tb/cdr/tb_cdr_jtol.scs).

### 1.4 Frequency-Offset (`ppm`) Tracking, $2\pi$ PI Wraparound & Multi-Frequency JTOL Mask
Real plesiochronous serial links operate with independent TX and RX reference crystals (`±100` to `±1000 ppm` offset, or spread-spectrum clocking SSC). In a Type-II PI-based CDR:
- **Exact `FREQ_MON` conversion:** When the TX runs at $f_{\text{tx}} = f_{\text{ref}}(1 + \Delta_{\text{ppm}}\times 10^{-6})$, the nested frequency accumulator settles to `freq_acc` [PI codes / UI] satisfying:

$$\Delta_{\text{ppm}} = \left(\frac{1}{1 + \text{freq\_acc} / N_{\text{codes}}} - 1\right)\times 10^6$$

- **Seamless $2\pi$ PI wraparound:** Tracking $+1000\;\text{ppm}$ at $10\;\text{Gb/s}$ slips $1\;\text{UI}$ every $100\;\text{ns}$, forcing continuous $0 \leftrightarrow N_{\text{codes}}$ ($2\pi$) quadrant wraparounds. Any sign flip, dead code, or missing step at the $2\pi$ boundary creates a periodic phase glitch and burst errors. Verify `FREQ_MON` convergence (`ppm_err_pct`), wrap count (`n_wraps >= 2`), max phase glitch across wraps, and `0` post-lock bit errors with [`assets/tb/cdr/tb_cdr_ppm_wrap.scs`](../assets/tb/cdr/tb_cdr_ppm_wrap.scs) (`analyze_cdr.py ppm_wrap`).
- **Multi-frequency OIF/IEEE JTOL mask:** A single-frequency JTOL check cannot prove both low-frequency tracking ($A_{\text{pp}} > 1\;\text{UI}$, requiring $|H_{\text{JTF}}| \approx 0\;\text{dB}$) AND high-frequency jitter filtering ($|H_{\text{JTF}}| < -3\;\text{dB}$ above the loop corner while the static eye absorbs residual SJ). Run the 4-point Spectre `alter` mask sweep (`5/20/60/150 MHz`, `1.20..0.25 UIpp`) in [`assets/tb/cdr/tb_cdr_jtol_mask.scs`](../assets/tb/cdr/tb_cdr_jtol_mask.scs) (`analyze_cdr.py jtol_mask`) to extract full `JTF(f)` magnitude/phase rolloff, `-3 dB` JTF bandwidth, and `jtol_all_pass`.

---

## 2. PAM4 Signaling: Gray Coding, IEEE 802.3 RLM & 1-Tap PAM4 DFE

### 2.1 Gray Mapping & Vertical SNR Penalty
PAM4 encodes 2 bits per symbol across four differential levels $V_0 < V_1 < V_2 < V_3$ (normalized $\{-1, -\frac{1}{3}, +\frac{1}{3}, +1\}$), halving the Nyquist frequency relative to NRZ at the same bit rate (`10 Gbaud = 20 Gb/s`, `28 Gbaud = 56 Gb/s`) at the cost of **$3\times$ ($-9.54\;\text{dB}$) smaller vertical eye height** per eye. IEEE 802.3 Gray coding maps `(00, 01, 11, 10)` $\to$ `(V_0, V_1, V_2, V_3)` so any adjacent-level symbol error flips only **1 bit** ($\text{BER} \approx \frac{1}{2}\text{SER}$).

### 2.2 Exact IEEE 802.3 Ratio of Level Mismatch (RLM)
Driver compression (CML/SST outer-level saturation) or MSB/LSB DAC slice mismatch shrinks either the outer or middle PAM4 eyes. Defining midpoint $V_{\text{mid}} = \frac{1}{2}(V_0 + V_3)$ and normalized inner-level ratios:

$$E_{S1} = \frac{V_1 - V_{\text{mid}}}{V_0 - V_{\text{mid}}}, \qquad E_{S2} = \frac{V_2 - V_{\text{mid}}}{V_3 - V_{\text{mid}}}$$

the exact IEEE 802.3 RLM specification (typically $\text{RLM} \ge 0.95$) is:

$$\text{RLM} = \min\!\big(3 E_{S1},\; 3 E_{S2},\; 2 - 3 E_{S1},\; 2 - 3 E_{S2}\big)$$

Verify TX RLM, level symmetry, and lower/middle/upper 3-eye heights & widths with [`assets/tb/pam4/tb_pam4_tx_rlm_eye.scs`](../assets/tb/pam4/tb_pam4_tx_rlm_eye.scs), [`assets/va/va_pam4_gen.va`](../assets/va/va_pam4_gen.va), and [`assets/va/va_pam4_tx.va`](../assets/va/va_pam4_tx.va).

### 2.3 3-Threshold PAM4 Slicer & 1-Tap PAM4 DFE
A PAM4 receiver slices the summer output $V_{\text{sum}}$ simultaneously against three thresholds $\big\{-\frac{2}{3}V_{\text{ref}},\; 0,\; +\frac{2}{3}V_{\text{ref}}\big\}$, where $V_{\text{ref}} \approx h_0$ is the received outer-level peak, and subtracts proportional post-cursor feedback $s_{k-1} \cdot h_1$ with $s_{k-1} \in \{-1, -\frac{1}{3}, +\frac{1}{3}, +1\}$. Because each PAM4 half-eye is only $h_0 / 3$, even moderate post-cursor ISI ($h_1 / h_0 \approx 0.30$) closes all three eyes before DFE; canceling $h_1$ opens all three eyes simultaneously with zero symbol and Gray-decoded bit errors. Verify with [`assets/tb/pam4/tb_pam4_dfe_ber.scs`](../assets/tb/pam4/tb_pam4_dfe_ber.scs) and [`assets/va/va_pam4_dfe_slicer.va`](../assets/va/va_pam4_dfe_slicer.va).

### 2.4 End-to-End 10 Gbaud (`20 Gb/s`) PAM4 Link Equalization Partition
Over long-reach channels ($\approx -16\;\text{dB}$ at Nyquist, `0.55 m` causal `mtline`), a 1-tap DFE alone cannot cancel broadband roll-off and multi-UI tails, so PAM4 links combine **light TX FFE** (pre-cursor cancellation preserving $\text{RLM} \ge 0.95$) + **linear RX CTLE** (broadband loss flattening without compressing outer levels!) + **1-tap PAM4 DFE** (canceling residual $h_1$ noiselessly). Verify stage-by-stage 3-eye progression (`tx_pam4 -> ch_pam4 -> ctle_pam4 -> dfe_pam4`), TX RLM, and `0`-SER / Gray-decoded `0`-BER with [`assets/tb/pam4/tb_pam4_link_top.scs`](../assets/tb/pam4/tb_pam4_link_top.scs) (`analyze_pam4.py link_top`).

---

## 3. Half-Rate / Quarter-Rate Clocking, DCD/IQ Skew & Jitter Bathtub

### 3.1 Duty-Cycle Distortion (DCD) & 90-Degree I/Q Phase Skew
Half-rate (`CK0, CK180`) and quarter-rate (`CK0, CK90, CK180, CK270`) SerDes architectures shrink clock power and relax 1-UI timing, but convert clock impairments directly into deterministic horizontal eye closure:
- **DCD** ($\Delta\text{DC} = T_{\text{high}}/T_{\text{clk}} - 50\%$): creates alternating wide/narrow UIs ($\text{DCD}_{\text{ps}} = (T_{\text{high}} - T_{\text{low}})/2$). Even a $5\%$ DCD on a $5\;\text{GHz}$ half-rate clock ($T_{\text{clk}} = 200\;\text{ps}$) eats $10\;\text{ps}$ ($0.10\;\text{UI}$) of horizontal eye width.
- **Quadrature I/Q skew** ($\Delta\phi_{\text{IQ}} = \phi_{90} - 90^\circ$): misaligns data vs. edge slicers in half-rate Alexander BBPDs (creating static sampling-phase offset away from eye center!) and unequally spaces quarter-rate UIs.

Because DCD (common threshold/rise-fall imbalance) and I/Q skew (Q-branch delay offset) are physically orthogonal, calibrate them independently via `VDCD_CAL` and `VIQ_CAL` and verify before-vs-after quadrant spacings with [`assets/tb/clocking_jitter/tb_clk_dcd_iq_skew.scs`](../assets/tb/clocking_jitter/tb_clk_dcd_iq_skew.scs) and [`assets/va/va_clk_dcd_iq.va`](../assets/va/va_clk_dcd_iq.va).

### 3.2 Dual-Dirac Jitter Decomposition & BER = 1e-12 Bathtub Extrapolation
From zero-crossing Time Interval Error ($\text{TIE}_i$) extracted over multiple repetitions of a PRBS-7 pattern (`127 UI`), decompose jitter into orthogonal components:
1. **DCD:** $|\overline{\text{TIE}}_{\text{rise}} - \overline{\text{TIE}}_{\text{fall}}|$
2. **SJ (Periodic/Sinusoidal):** coherent single-tone amplitude $2A_{\text{sj}}$ at $f_{\text{sj}}$
3. **DDJ (Data-Dependent / ISI):** peak-to-peak variation of pattern-locked mean $\overline{\text{TIE}}[k \bmod 127]$
4. **RJ (Random Gaussian):** unbiased within-slot ANOVA RMS $\sigma_{\text{RJ}}$ of the pattern/SJ/DCD-removed residual

Under the Dual-Dirac model with transition density $\rho_T \approx 0.5$ ($Q(\text{BER}) = \sqrt{2}\,\text{erfc}^{-1}(2\cdot\text{BER}/\rho_T)$, giving $Q \approx 6.94\text{–}7.03$ at $\text{BER} = 10^{-12}$):

$$\text{TJ}(\text{BER}) = \text{DJ}_{\delta\delta} + 2\,Q(\text{BER})\,\sigma_{\text{RJ}}, \qquad \text{EW}(\text{BER}) = \max\big(T_{\text{UI}} - \text{TJ}(\text{BER}),\; 0\big)$$

Verify full decomposition and bathtub curves across $\text{BER} = 10^{-3}\text{..}10^{-12}$ with [`assets/tb/clocking_jitter/tb_tx_jitter_bathtub.scs`](../assets/tb/clocking_jitter/tb_tx_jitter_bathtub.scs).

### 3.3 Power-Supply-Induced Jitter (`PSIJ`) & RX Supply Rejection (`PSRR`)
Switching noise on shared SerDes supply rails modulates both CMOS clock-buffer propagation delay (`PSIJ` in $\text{ps/mV}$ or $\text{mUI/mV}$) and RX differential eye amplitude (`PSRR` in $\text{dB}$):
- **Clock PSIJ:** For sinusoidal ripple $V_{\text{rip,pp}}$ at $f_{\text{rip}}$ on `VDD`, extract coherent clock-edge TIE amplitude $\Delta t_{\text{TIE,pp}}$ to compute $\text{PSIJ} = \Delta t_{\text{TIE,pp}} / V_{\text{rip,pp}}\;[\text{ps/mV}]$. High-speed CMOS clock spines typically target $< 0.1\text{–}0.2\;\text{ps/mV}$ or dedicated LDO regulation.
- **RX CTLE PSRR:** Supply noise coupled into a CTLE input/tail is amplified by the CTLE peaking transfer function near Nyquist, making high-frequency `PSRR(5 GHz)` significantly worse than DC/low-frequency PSRR! Measure coherent transient `PSIJ`, transient `PSRR_tran`, and wideband AC `PSRR(f)` (`10 MHz..10 GHz`) simultaneously with [`assets/tb/clocking_jitter/tb_psij_supply_noise.scs`](../assets/tb/clocking_jitter/tb_psij_supply_noise.scs) (`analyze_clocking_jitter.py psij`).

---

## 4. Dynamic Slicer Timing, CTLE Linearity, RX Mode Conversion, nport & Crosstalk

### 4.1 Slicer Clk-to-Q, Regeneration $\tau_{\text{regen}}$ & SR-Latch Kickback
A regenerative StrongARM or CML slicer exhibits logarithmic overdrive-to-delay scaling:

$$t_{\text{ck2q}}(V_{\text{od}}) = t_0 + \tau_{\text{regen}} \ln\!\left(\frac{V_{\text{ref}}}{|V_{\text{od}}|}\right)$$

where $\tau_{\text{regen}} \approx C_L / g_{m,\text{eff}}$ determines both the 1-UI DFE critical path budget and the metastability error floor.

> **Critical Silicon Gotcha — StrongARM SR-Latch Hysteresis:** Connecting an asymmetric NAND/NOR SR latch directly to the StrongARM regenerative nodes (`LP, LN`) creates state-dependent Miller/gate-to-channel capacitance asymmetry that induces tens of mV of dynamic hysteresis (blocking small-overdrive resolution and biasing `trannoise` runs). Always place **identical symmetric CMOS inverter isolation buffers** between `(LP, LN)` and the SR latch, plus differential equalize switches during `CLK = 0`. Verify `tau_regen` and Setup/Hold aperture across $0.5\text{–}100\;\text{mV}$ with [`assets/tb/slicer_dfe/tb_slicer_clk2q_setup_hold.scs`](../assets/tb/slicer_dfe/tb_slicer_clk2q_setup_hold.scs).

### 4.2 CTLE Large-Signal Linearity (`P1dB`, `HD3`, `SFDR`)
High-gain CTLEs compress large low-loss or short-reach eyes (especially critical for PAM4 RLM!). Measure input/output 1-dB compression (`P1dB` in `Vpp` and `dBm` into $100\;\Omega$ diff) and coherent `HD3`/`SFDR` using [`assets/tb/ctle_vga/tb_ctle_linearity_p1db.scs`](../assets/tb/ctle_vga/tb_ctle_linearity_p1db.scs) (`outputstart` for full settling, `strobedelay < strobeperiod`, coherent `M/N` prime tone, and `-preset_override` on Spectre X for $> 80\;\text{dB}$ FFT floor).

### 4.3 4-Port RX Front-End Mode Conversion (`SDD11`, `SCD11`, `SCD21`, `SDC21`)
Even when differential return loss `SDD11` meets IEEE 802.3 / OIF-CEI masks via bridged T-coils, P/N asymmetry in ESD diodes, coil ESR, or termination resistors converts differential signal into common-mode EMI (`SCD11`, `SCD21`) and common-mode supply/ground noise directly into differential eye closure (`SDC21`). Quantify all four mixed-mode parameters up to $25\;\text{GHz}$ with [`assets/tb/tcoil/tb_rx_frontend_sdd11_scd21.scs`](../assets/tb/tcoil/tb_rx_frontend_sdd11_scd21.scs).

### 4.4 Touchstone `.s4p` `nport` Causality & Spectre X `bbspice` vs. `rational`
When importing Touchstone `.s4p` channels into Spectre X transient simulation:
- **Use `interp=bbspice passivity=fit_enforce`** (Broadband SPICE delay-extracting passive rational macro-model) for electrically long channels ($\tau_{\text{flight}} \cdot f_{\max} \gtrsim 5$ cycles). Legacy `interp=rational` fits without delay extraction, exceeds practical pole order ($> 80$ poles), loses passivity near DC, and can diverge during DC operating point!
- **Include low-frequency RL knee points** (`0, 1M, 2M, 5M, 10M, 20M, 50M, 100M...`) in `.s4p` tables so `S11` transitions smoothly from resistive DC to $50\;\Omega$ without triggering `CMI-2839` discontinuity warnings.
- **Verify causality via SBR `h_-2 / h_0`:** Genuine physical dispersion yields a small 1-UI precursor `h_-1`, while `|h_-2| / h_0` before flight time must remain near zero (`< 1–2%`). Verify end-to-end with [`assets/tb/channel/tb_channel_nport_s4p.scs`](../assets/tb/channel/tb_channel_nport_s4p.scs) and the bundled analytically-generated passive causal [`channel_synth_causal.s4p`](../assets/tb/channel/channel_synth_causal.s4p).

### 4.5 FEXT & NEXT Crosstalk Eye Budgeting
Adjacent differential lanes couple asymmetrically across connectors, vias, and BGA breakouts (inner edge-to-edge traces couple more strongly than outer traces, producing net differential crosstalk):
- **NEXT** (Near-End Crosstalk from a local TX aggressor into an adjacent RX) is NOT attenuated by the long channel loss and often dominates high-density long-reach links!
- **FEXT** (Far-End Crosstalk co-propagating with the victim) scales with edge rate ($dV/dt$) and channel dispersion.
- Always run crosstalk aggressors on **uncorrelated PRBS-9 patterns with slightly offset asynchronous clocks** so worst-case phase alignment is sampled across the victim eye. Quantify isolated vs. coupled eye loss and FEXT/NEXT RMS/dB levels with [`assets/tb/channel/tb_channel_xtalk_fext_next.scs`](../assets/tb/channel/tb_channel_xtalk_fext_next.scs).

### 4.6 IEEE 802.3 Clause 93/120 TX Linear-Fit `SNDR_TX`, P/N Skew & AC Common-Mode Noise
High-speed TX signoff extends beyond return loss (`SDD11`) to waveform linearity and differential symmetry:
- **Intra-pair P/N timing skew (`t_skew_pn`):** Even $4\text{–}15\;\text{ps}$ mismatch between `OUTP` and `OUTN` pre-driver paths converts every differential edge into an AC common-mode spike $V_{\text{cm,ac}}(t) = \frac{1}{2}(V_{\text{OUTP}} + V_{\text{OUTN}}) - V_{\text{cm,dc}}$ (radiating EMI and triggering RX common-mode-to-differential conversion `SDC21`).
- **Linear-Fit Pulse Response $p(k)$ & `SNDR_TX`:** Solve the oversampled least-squares fit $y \approx X p$ of the TX PRBS-7 waveform against the known bipolar bit sequence $x[n] \in \{-1, +1\}$ across $N_p$ taps (`12 UI` at `16x` oversampling). With peak linear-fit pulse $p_{\max} = \max|p(k)|$ and fit residual RMS $\sigma_e = \text{rms}(y - Xp)$:

$$\text{SNDR}_{\text{TX}} = 10\log_{10}\!\left(\frac{p_{\max}^2}{\sigma_e^2 + \sigma_n^2}\right) \quad [\text{dB}]$$

  When TX FFE is active, output driver compression (`v_clip_tx`) distorts peak transition levels relative to de-emphasized runs, directly degrading `SNDR_TX` below IEEE 802.3 targets ($\ge 27\text{–}32.5\;\text{dB}$). Verify 20–80% $t_r/t_f$, `pn_skew_ps`, `vcm_ac_rms_mv`/`pp_mv`, $p(k)$ cursors, and `sndr_tx_db` with [`assets/tb/tx_ffe/tb_tx_cm_skew_sndr.scs`](../assets/tb/tx_ffe/tb_tx_cm_skew_sndr.scs) (`analyze_tx_ffe.py cm_sndr`).

### 4.7 Slicer Input Kickback & Half-Rate Interleaved Neighbor Corruption
Dynamic StrongARM and clocked CML slicers inject charge back into their input nodes `(INP, INN)` through input-pair $C_{gs}/C_{gd}$ when internal tail/drain nodes discharge rapidly on `CLK` rising and precharge more slowly on `CLK` falling. Driven through a finite CTLE/VGA source impedance ($R_{\text{src}} \parallel C_{\text{src}}$):
- **Single-slicer kickback:** Creates a large common-mode glitch and—under any P/N capacitance or $R_{\text{src}}$ mismatch, or data-dependent latch regeneration—a differential kickback pulse decaying with $\tau_{\text{src}} = R_{\text{src}}(C_{\text{src}} + C_{\text{in}})$.
- **Half-rate interleaved coupling (`Odd -> Even`):** Because evaluate discharge is much faster than reset precharge, Even and Odd kickbacks on a shared input node do **not** cancel even at $50\%$ duty cycle! If $\tau_{\text{src}}$ is too large relative to $0.5\,T_{\text{clk}}$ (`1 UI`), the Odd slicer's kickback residual corrupts the Even slicer's sampling aperture. Quantify standalone and interleaved kickback peaks plus settled neighbor residuals with [`assets/tb/slicer_dfe/tb_slicer_kickback.scs`](../assets/tb/slicer_dfe/tb_slicer_kickback.scs) (`analyze_slicer_dfe.py kickback`, verified on both behavioral `va_slicer_cml.va` and transistor-level BSIM4 StrongARM).

### 4.8 AC-Coupled Baseline Wander (`BLW`) Under Long CID Bursts
Series AC-coupling capacitors ($C_{\text{ac}}$ on both P and N lines) isolate TX vs. RX DC common-mode voltages but form a high-pass filter with exact differential time constant $\tau_{\text{ac}} = (R_{\text{src}} + R_{\text{rx}}) C_{\text{ac}} = 2 Z_0 C_{\text{ac}}$. During a long run of $N_{\text{cid}}$ Consecutive Identical Digits (`T_cid = N_cid * UI`), the differential voltage droops exponentially:

$$V_{\text{droop}} = V_0 \left(1 - e^{-T_{\text{cid}} / (2 Z_0 C_{\text{ac}})}\right)$$

Immediately when alternating transitions resume, the DC baseline is shifted by $-V_{\text{droop}}$, closing the vertical eye margin relative to a fixed $0\;\text{V}$ slicer threshold by $2 V_{\text{droop}}$ (and collapsing the eye completely if $C_{\text{ac}}$ is undersized!).
> **Spectre DC-Op AC-Coupling Pitfall:** If a stimulus generator outputs a non-zero static differential voltage ($\pm V_0$) during the `t = 0` DC operating point, Spectre pre-charges `C_ac` to that bogus DC voltage at `t = 0`, corrupting the entire transient! Always hold differential output at balanced `0 V` during DC operating point (`va_prbs_gen.va mode=3` does this automatically while preserving `V_cm,tx - V_cm,rx`). Verify `blw_peak_mv`, analytical RC agreement (`rel_err_pct < 5%`), and pre- vs. post-CID eye closure with [`assets/tb/channel/tb_channel_blw_cid.scs`](../assets/tb/channel/tb_channel_blw_cid.scs) (`analyze_channel.py blw_cid`).
