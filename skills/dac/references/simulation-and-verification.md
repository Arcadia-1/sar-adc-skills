# DAC Spectre Simulation & Verification Guide

## 1. Ready-to-Run Process-Independent Testbench Suites (`assets/tb/`)

All Spectre decks plug in external `models_corner.scs` + `dut_subckt.scs` (zero PDK assumptions) and are analyzed by standalone Python scripts backed by [`common/psf_utils.py`](../../../common/psf_utils.py):

### Current-Steering DAC Suite (`assets/tb/current_steering/`)
DUT contracts:
- `subckt dut_cs_dac DIN9..DIN0 VDD VSS IOUTP IOUTN` (decks 1–4, 6)
- `subckt dut_cs_dac_clk DIN9..DIN0 CLK VDD VSS IOUTP IOUTN` (deck 5)
- `subckt dut_cs_dac_dem DIN9..DIN0 CLK DEM_EN VDD VSS IOUTP IOUTN` (deck 7)

1. **[`tb_dac_static_dnl_inl.scs`](../assets/tb/current_steering/tb_dac_static_dnl_inl.scs)** + `analyze_cs_dac.py static`:
   - Sweeps all `1024` codes (`0..1023`) via `va_dac_ramp_gen_10b.va` with `strobeoutput=strobeonly` (`strobedelay = 0.85*ts < strobeperiod = ts`).
   - Extracts `full_scale_v`, `lsb_mv`, `midpoint_offset_mv`, `vcm_mean_v`, endpoint **`dnl_max/min`**, **`inl_max/min`**, and **`monotonic`**.
2. **[`tb_dac_dynamic_sfdr.scs`](../assets/tb/current_steering/tb_dac_dynamic_sfdr.scs)** + `analyze_cs_dac.py dynamic` / `twotone`:
   - **`sig_mode = 0` (Single-Tone Coherent FFT):** `va_dac_sine_gen_10b.va` drives `f_sig = fs * m_bin / n_fft` (default `fs = 200M`, `n_fft = 256`, `m_bin = 29`; also sweep near-Nyquist `m_bin = 119` or `127`!). Extracts `sfdr_db`, `hd2_dbc`, `hd3_dbc`, `thd_db`, `sndr_db`, `snr_db`, and `enob`.
   - **`sig_mode = 1` (Two-Tone Coherent IMD3):** Drives equal-amplitude tones at `m_bin1 = 59`, `m_bin2 = 61` (each at `-6 dBFS` so summed peak stays inside `0..1023` without clipping!). Extracts **`im3_lo_dbc`**, **`im3_hi_dbc`**, **`imd3_dbc`**, `im2_dbc`, and `sfdr_db`.
3. **[`tb_dac_glitch_settle.scs`](../assets/tb/current_steering/tb_dac_glitch_settle.scs)** + `analyze_cs_dac.py glitch`:
   - Drives both rising (`511 -> 512`) and falling (`512 -> 511`) major-carry transitions with `maxstep = 5p`, `errpreset = conservative`.
   - Extracts peak glitch (`mV`), **glitch impulse energy (`pV*s`)**, and **`0.5 LSB` settling time (`ns`)**!
4. **[`tb_dac_sfdr_vs_fin.scs`](../assets/tb/current_steering/tb_dac_sfdr_vs_fin.scs)** + `analyze_cs_dac.py sfdr_sweep`:
   - Sweeps 4 coherent prime bins via `alter` (`M = {7, 29, 67, 113}` out of `N = 256` @ `200 MS/s`, `osr = 8` through a unity-gain 3rd-order Butterworth anti-aliasing filter at `fc = 0.65*fs`) to capture code-dependent unit-cell impedance $Z_{\text{out}}(f)$ high-frequency distortion without ZOH image aliasing.
   - Extracts per-frequency `f_in_mhz`, `sfdr_db`, `hd2_dbc`, `hd3_dbc`, `sndr_db`, `enob_bits`, plus `sfdr_low_db`, `sfdr_nyq_db`, and `sfdr_rolloff_db`.
5. **[`tb_dac_psrr_jitter.scs`](../assets/tb/current_steering/tb_dac_psrr_jitter.scs)** + `analyze_cs_dac.py psrr_jitter`:
   - Three-stage `alter` sensitivity bench (`tran_psrr`, `tran_clean`, `tran_jitter`) with `osr = 8` anti-aliased continuous-time capture:
     - **Dynamic PSRR:** superimposes `50 mVpp` coherent supply ripple (`m_rip = 17`) on `VDD` alongside `m_bin = 67`, extracting `psrr_db`, direct feedthrough `supply_spur_dbc` at `f_rip`, and AM sidebands `f_out +/- f_rip` (`sb_lo_dbc`, `sb_hi_dbc`).
     - **Clock Jitter:** injects calibrated RMS rising-edge jitter (`t_jitter_rms = 5p` via `va_dac_clk_jitter.va`), verifying continuous-time Nyquist SNR degradation matches analytical $-20\log_{10}(2\pi f_{\text{out}}\sigma_t)$ and inverting `t_j_est_ps`.
6. **[`tb_dac_output_compliance.scs`](../assets/tb/current_steering/tb_dac_output_compliance.scs)** + `analyze_cs_dac.py compliance`:
   - Sweeps DC termination bias `v_term` (`dc_comp`) to measure array output resistance `r_out_eff_kohm` and the 1%-compression compliance limit `v_comp_max_v`, then runs dynamic coherent tones with `dr_load = 0%` vs. `2%` (`tran_matched` / `tran_mismatched`) to quantify P/N load-asymmetry `HD2` conversion (`hd2_degradation_db`). Verified directly on both behavioral and generic BSIM4 cascode current-steering DUTs.
7. **[`tb_dac_dem_mismatch.scs`](../assets/tb/current_steering/tb_dac_dem_mismatch.scs)** + `analyze_cs_dac.py dem`:
   - Runs an identically mismatched 10-bit segmented CS-DAC (`sigma_cell = 0.8%`) with `DEM_EN = 0` (static thermometer) vs. `DEM_EN = vdd_dig` (first-order DWA pointer rotation) at `N = 512`, `m_bin = 19` (`OSR = 4`).
   - Extracts `sfdr_static_db`, `sfdr_dem_db`, `sfdr_gain_db`, `hd2/hd3` spur suppression, and both in-band (`OSR = 4`) and full-Nyquist `SNDR`, verifying harmonic-to-high-pass-shaped-noise conversion.

### R-2R Ladder DAC Suite (`assets/tb/r2r/`)
DUT contract: `subckt dut_r2r_dac DIN7 DIN6 DIN5 DIN4 DIN3 DIN2 DIN1 DIN0 VREF VSS VOUT`

1. **[`tb_r2r_static.scs`](../assets/tb/r2r/tb_r2r_static.scs)** + `analyze_r2r.py static`: 256-code static sweep (`0..255`) extracting `zero_code_mv`, `full_scale_v`, `gain_err_pct`, `dnl_max/min`, `inl_max/min`, and `monotonic`.
2. **[`tb_r2r_settle.scs`](../assets/tb/r2r/tb_r2r_settle.scs)** + `analyze_r2r.py settle`: Full-scale (`0 -> 255`) and major-carry (`127 -> 128`) `0.5 LSB` settling time across `cload`.

---

## 2. Behavioral Verilog-A Library (`assets/va/`)

- [`va_dac_cs_10b.va`](../assets/va/va_dac_cs_10b.va): 10-bit CS-DAC with code-dependent unit-cell `r_cell` & `c_cell` (reproducing textbook HD3 vs. $Z_{\text{unit}}(f)$!), MSB mismatch `dm_msb`, switching skew `t_skew`, compliance headroom clamp, and white current noise.
- [`va_dac_cs_dem_10b.va`](../assets/va/va_dac_cs_dem_10b.va): 10-bit segmented (`4+6`) CS-DAC with deterministic Park-Miller 15-cell thermometer mismatch (`sigma_cell`, `seed`), switchable first-order DWA (`DEM_EN` / `dem_en`), charge-conserving `r_cell`/`c_cell` output impedance, smooth 1%-drop `v_comp_max` compliance knee, `VDD` modulation (`psrr_g`, `psrr_asym`), and rising-edge clock sampling (`clk_en`, `duty_hd2_k`).
- [`va_dac_clk_jitter.va`](../assets/va/va_dac_clk_jitter.va): Causal rising-edge Gaussian clock jitter injector (`t_jitter_rms` with `6*sigma` pedestal delay) for continuous-time DAC jitter verification.
- [`va_dac_r2r_8b.va`](../assets/va/va_dac_r2r_8b.va): 8-bit R-2R ladder DAC with constant $R_{\text{out}} = r_{\text{unit}} + r_{\text{sw}}$, MSB mismatch `dm_msb`, and output capacitance `c_out`.
- [`va_dac_ramp_gen_10b.va`](../assets/va/va_dac_ramp_gen_10b.va) & [`va_dac_sine_gen_10b.va`](../assets/va/va_dac_sine_gen_10b.va): Coherent digital stimulus generators (`DIN[9:0]`, `CODE_MON`).

---

## 3. Critical Spectre DAC Verification Pitfalls

1. **Always run with `+aps` and filter `strobeoutput=strobeonly` grids:** Spectre appends off-grid `t = 0` and `t = t_stop` points even with `strobeoutput=strobeonly`. All bundled analyzers pass traces through `extract_uniform_strobe()` from `common/psf_utils.py` to prevent FFT leakage and false `-1 LSB` DNL spikes.
2. **Keep `strobedelay < strobeperiod`:** Spectre throws `ERROR (SPECTRE-16394)` if `strobedelay >= strobeperiod`; skip warmup cycles (`n_warmup`) in post-processing by slicing `samples[-n_fft:]`.
3. **Oversample (`osr = 8` or `16`) when checking glitch-induced or ZOH-induced RF harmonics:** A single `osr = 1` strobe after settling measures static + impedance nonlinearity (`r_cell`, mismatch, compliance), whereas oversampling (`osr >= 8`) captures continuous-time switching glitches and ZOH sinc roll-off directly in the FFT!
4. **Two-tone back-off (`-6 dBFS` per tone):** Driving two tones at full scale clips the digital input word (`0..1023`), creating artificial IM3! Keep `amp_fs <= 0.98` so each tone sits at `-6.2 dBFS` (`0.49 * FS`).
5. **Tight `maxstep` for glitch impulse:** Default adaptive transient timesteps easily step right over a `50–150 ps` switching glitch! Always bound `maxstep <= 5p` (or `<= t_edge / 4`) in `tb_dac_glitch_settle.scs`.
6. **Continuous-time anti-aliasing filter for `c_cell` SFDR(f_in) and clock-jitter verification:** Strobing an unfiltered ZOH staircase at `osr = 1` misses both `c_cell` transient settling errors and picosecond sampling-clock jitter, whereas strobing an unfiltered ZOH at `osr = 8` aliases high-order staircase images back into `[0, fs/2]`. Passing `V_diff` through a unity-gain 3rd-order passive Butterworth anti-aliasing filter (`fc = 0.65*fs`) before `osr = 8` strobing (as in `tb_dac_sfdr_vs_fin.scs` and `tb_dac_psrr_jitter.scs`) eliminates aliasing while preserving exact Nyquist-band `HD3(f_in)` and analytical `-20*log10(2*pi*f_out*sigma_t)` jitter SNR.
7. **Verify compliance headroom, `R_load` symmetry, & Monte Carlo INL yield:** Check that every current source and cascode remains firmly in saturation at peak output swing (`tb_dac_output_compliance.scs`, verifying `v_out_peak_v <= v_comp_max_v` and checking `2%` `R_load` mismatch HD2 sensitivity), and run `N >= 200` Monte Carlo mismatch points (or DWA/DEM verification in `tb_dac_dem_mismatch.scs`) to verify linearity yield!
