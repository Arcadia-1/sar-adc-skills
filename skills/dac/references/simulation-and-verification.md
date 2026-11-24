# DAC Spectre Simulation & Verification Guide

## 1. Ready-to-Run Process-Independent Testbench Suites (`assets/tb/`)

All Spectre decks plug in external `models_corner.scs` + `dut_subckt.scs` (zero PDK assumptions) and are analyzed by standalone Python scripts backed by [`common/psf_utils.py`](../../../common/psf_utils.py):

### Current-Steering DAC Suite (`assets/tb/current_steering/`)
DUT contract: `subckt dut_cs_dac DIN9 DIN8 DIN7 DIN6 DIN5 DIN4 DIN3 DIN2 DIN1 DIN0 VDD VSS IOUTP IOUTN`

1. **[`tb_dac_static_dnl_inl.scs`](../assets/tb/current_steering/tb_dac_static_dnl_inl.scs)** + `analyze_cs_dac.py static`:
   - Sweeps all `1024` codes (`0..1023`) via `va_dac_ramp_gen_10b.va` with `strobeoutput=strobeonly` (`strobedelay = 0.85*ts < strobeperiod = ts`).
   - Extracts `full_scale_v`, `lsb_mv`, `midpoint_offset_mv`, `vcm_mean_v`, endpoint **`dnl_max/min`**, **`inl_max/min`**, and **`monotonic`**.
2. **[`tb_dac_dynamic_sfdr.scs`](../assets/tb/current_steering/tb_dac_dynamic_sfdr.scs)** + `analyze_cs_dac.py dynamic` / `twotone`:
   - **`sig_mode = 0` (Single-Tone Coherent FFT):** `va_dac_sine_gen_10b.va` drives `f_sig = fs * m_bin / n_fft` (default `fs = 200M`, `n_fft = 256`, `m_bin = 29`; also sweep near-Nyquist `m_bin = 119` or `127`!). Extracts `sfdr_db`, `hd2_dbc`, `hd3_dbc`, `thd_db`, `sndr_db`, `snr_db`, and `enob`.
   - **`sig_mode = 1` (Two-Tone Coherent IMD3):** Drives equal-amplitude tones at `m_bin1 = 59`, `m_bin2 = 61` (each at `-6 dBFS` so summed peak stays inside `0..1023` without clipping!). Extracts **`im3_lo_dbc`**, **`im3_hi_dbc`**, **`imd3_dbc`**, `im2_dbc`, and `sfdr_db`.
3. **[`tb_dac_glitch_settle.scs`](../assets/tb/current_steering/tb_dac_glitch_settle.scs)** + `analyze_cs_dac.py glitch`:
   - Drives both rising (`511 -> 512`) and falling (`512 -> 511`) major-carry transitions with `maxstep = 5p`, `errpreset = conservative`.
   - Extracts peak glitch (`mV`), **glitch impulse energy (`pV*s`)**, and **`0.5 LSB` settling time (`ns`)**!

### R-2R Ladder DAC Suite (`assets/tb/r2r/`)
DUT contract: `subckt dut_r2r_dac DIN7 DIN6 DIN5 DIN4 DIN3 DIN2 DIN1 DIN0 VREF VSS VOUT`

1. **[`tb_r2r_static.scs`](../assets/tb/r2r/tb_r2r_static.scs)** + `analyze_r2r.py static`: 256-code static sweep (`0..255`) extracting `zero_code_mv`, `full_scale_v`, `gain_err_pct`, `dnl_max/min`, `inl_max/min`, and `monotonic`.
2. **[`tb_r2r_settle.scs`](../assets/tb/r2r/tb_r2r_settle.scs)** + `analyze_r2r.py settle`: Full-scale (`0 -> 255`) and major-carry (`127 -> 128`) `0.5 LSB` settling time across `cload`.

---

## 2. Behavioral Verilog-A Library (`assets/va/`)

- [`va_dac_cs_10b.va`](../assets/va/va_dac_cs_10b.va): 10-bit CS-DAC with code-dependent unit-cell `r_cell` & `c_cell` (reproducing textbook HD3 vs. $Z_{\text{unit}}(f)$!), MSB mismatch `dm_msb`, switching skew `t_skew`, compliance headroom clamp, and white current noise.
- [`va_dac_r2r_8b.va`](../assets/va/va_dac_r2r_8b.va): 8-bit R-2R ladder DAC with constant $R_{\text{out}} = r_{\text{unit}} + r_{\text{sw}}$, MSB mismatch `dm_msb`, and output capacitance `c_out`.
- [`va_dac_ramp_gen_10b.va`](../assets/va/va_dac_ramp_gen_10b.va) & [`va_dac_sine_gen_10b.va`](../assets/va/va_dac_sine_gen_10b.va): Coherent digital stimulus generators (`DIN[9:0]`, `CODE_MON`).

---

## 3. Critical Spectre DAC Verification Pitfalls

1. **Always run with `+aps` and filter `strobeoutput=strobeonly` grids:** Spectre appends off-grid `t = 0` and `t = t_stop` points even with `strobeoutput=strobeonly`. All bundled analyzers pass traces through `extract_uniform_strobe()` from `common/psf_utils.py` to prevent FFT leakage and false `-1 LSB` DNL spikes.
2. **Keep `strobedelay < strobeperiod`:** Spectre throws `ERROR (SPECTRE-16394)` if `strobedelay >= strobeperiod`; skip warmup cycles (`n_warmup`) in post-processing by slicing `samples[-n_fft:]`.
3. **Oversample (`osr = 8` or `16`) when checking glitch-induced or ZOH-induced RF harmonics:** A single `osr = 1` strobe after settling measures static + impedance nonlinearity (`r_cell`, mismatch, compliance), whereas oversampling (`osr >= 8`) captures continuous-time switching glitches and ZOH sinc roll-off directly in the FFT!
4. **Two-tone back-off (`-6 dBFS` per tone):** Driving two tones at full scale clips the digital input word (`0..1023`), creating artificial IM3! Keep `amp_fs <= 0.98` so each tone sits at `-6.2 dBFS` (`0.49 * FS`).
5. **Tight `maxstep` for glitch impulse:** Default adaptive transient timesteps easily step right over a `50–150 ps` switching glitch! Always bound `maxstep <= 5p` (or `<= t_edge / 4`) in `tb_dac_glitch_settle.scs`.
6. **Verify compliance headroom & Monte Carlo INL yield:** Check that every current source and cascode remains firmly in saturation at `code = 1023` (`ss`, lowest `VDD`, max `rload`), and run `N >= 200` Monte Carlo mismatch points (or analytical unit-cell MC) to verify INL yield!
