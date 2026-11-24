# SAR ADC Simulation & Verification Reference

Practical guide for setting up accurate, fast Cadence Spectre / ADE Maestro simulations for SAR ADCs and extracting dynamic, static, and per-block metrics.

---

## 1. Coherent Sampling Setup

FFT-based ENOB/SNDR/SFDR extraction requires **coherent sampling** so the fundamental tone and all harmonics fall cleanly on FFT bins with zero spectral leakage:

$$f_{\text{in}} = \frac{M}{N} f_s$$

where $N$ is a power of 2 and $M$ is an odd prime coprime to $N$.

| $N$ | Typical prime $M$ (low-freq / near-Nyquist) | Use case |
|---|---|---|
| 64 | 7, 11, 13 / 29, 31 | Fast sanity check & corner screening |
| 128 | 11, 13 / 61 | Minimum for ~10-bit iteration |
| 256 | 13, 31 / 127 | Solid 8–12 bit characterization |
| 1024+ | 127, 251 / 509 | High-resolution / noisy signoff & INL/DNL |

Use `adctoolbox.find_coherent_frequency(fs, fin_target, N)` to pick $M$ cleanly. Always test **both** a low-frequency tone (checks static linearity, noise, CDAC weights) and a **near-Nyquist** tone ($M \approx N/2 - 1$, stresses sampling linearity, bootstrap switch $R_{\text{on}}$ flatness, feedthrough, and jitter).

---

## 2. Input Signal & Clocking

### Differential Sine Input

- Center both sides at $V_{\text{cm}}$ (typically $V_{\text{DD}}/2$):
  - `VIP`: `sinedc=vcm`, `ampl=+A/2`
  - `VIN`: `sinedc=vcm`, `ampl=-A/2`
- Drive at ~85–95% of differential full scale (`−1.4` to `−0.4 dBFS`) to avoid early rail clipping from top-plate parasitics or offset.
- **Spectre `vsource` gotcha:** Use **`ampl`** for transient sine amplitude; **`mag`** is AC small-signal magnitude only. Leaving `ampl` unset silently falls back to a default 1 V amplitude.

### Sampling Clock (`CLKS`)

- **Synchronous SAR:** External `CLKS` at $f_s$ plus `CLKC`/`BITCLK` at $\ge (N_{\text{bits}} + 2) f_s$.
- **Asynchronous SAR:** Only `CLKS` at $f_s$ (typically 20–25% high duty cycle for sampling, leaving 75–80% of $1/f_s$ for the self-timed conversion window).

---

## 3. Spectre Performance, Accuracy, and Output Size Control

### Solver Modes

| Mode | Flag | Accuracy vs. APS (typical 11-bit SAR) | Use case |
|---|---|---|---|
| Classic Spectre / APS | `(none)` / `+aps` | Reference | Final signoff, comparator noise/metastability |
| Spectre X `cx` / `ax` | `+preset=cx` / `+preset=ax +mt` | `ax` within ~0.03 bit ENOB of APS | Fast accurate iteration when Spectre X is licensed |
| Spectre X `mx` | `+preset=mx +mt` | ~0.3 bit ENOB loss possible | Fast coarse functional sweeps only — **validate against `aps`/`ax` before signoff** |
| Spectre X `lx` / `vx` | `+preset=lx` / `+preset=vx +mt` | Multi-bit ENOB degradation | Do **not** use for SAR ADC ENOB or comparator accuracy |

*(Always verify solver tolerances on your own circuit; regenerative comparators are especially sensitive to loose presets.)*

### Controlling PSF Size & Speed (Critical Gotchas)

1. **Always use `save=selected` with a curated signal list** (`saveOptions options save=selected`). Default `save=allpub` on a clocked SAR transient produces hundreds of MB of PSF ASCII per run.
2. **Use `strobeoutput=strobeonly`, NOT `strobeoutput=all`:**
   - `strobeoutput=all` saves **every solver timestep plus strobed points** (largest file; and in `psfascii`, Spectre emits only the huge continuous waveform).
   - `strobeoutput=strobeonly` with `strobeperiod=1/Fs` and `strobedelay` aligned to the settled end-of-conversion phase saves **exactly 1 sample per conversion** and shrinks PSF files by ~500–1500×!
3. **Transient noise (`tranNoise=yes`) — ALWAYS set `noiseruns=1`:**
   - ADE Maestro frequently defaults `noiseruns=100` (100× compute cost for ensemble Monte Carlo!). For ADC ENOB or a single $N$-cycle comparator noise count, set `noiseruns=1` explicitly, with `noisefmax` $\ge 5 f_{\text{clk}}$ (e.g., `50G`–`100G` for GHz comparators).
4. **Never pass `-param X=Y` on the Spectre CLI:** Spectre parses it as a second netlist file (`SPECTRE-132`). Bake swept parameters directly into the `parameters` line of a staged copy of the netlist, and do not re-declare upstream parameters after an `include` if dependent expressions were already bound.
5. **Avoid over-subscribing CPU threads:** When running $P$ Spectre jobs in parallel on an $M$-core machine, set `+mt=floor(M/P)` (e.g. `+mt=2` for 8–12 jobs on 24 cores); letting every job auto-spawn max threads causes severe contention and 5–10× slowdown.

---

## 4. Output Extraction & ADCToolbox

### Reconstructing Output Codes

- **Behavioral DAC / `CODE` pin (cleanest):** Include a Verilog-A reconstructor (like `assets/va/_va_dac_4b.va` or an ideal CDAC with a latched `CODE` pin) and sample at a fixed settled instant each period:
  ```python
  t_strobe = t_skip + np.arange(N) / Fs
  samples = np.interp(t_strobe, t_sim, aout_sim)
  ```
- **From digital bus `DOUT<N-1:0>`:** Sample at `CLKS` rising edge (or end-of-conversion strobe) and threshold at `VDD/2`.
- **Spectre bus port ordering gotcha:** Spectre expands bus ports `[N-1:0]` **MSB first**. Mismatched bit order produces bit-reversed codes that look like a completely broken ADC.
- **PSF ASCII escaped bus names:** Signals like `DOUT<0>` parse as `r"DOUT\<0\>"` in PSF ASCII.

### Dynamic & Static Metrics

Use [`ADCToolbox`](https://github.com/Arcadia-1/ADCToolbox) rather than hand-written FFT/ENOB scripts:

```python
from adctoolbox import analyze_spectrum, analyze_inl_from_sine

spec = analyze_spectrum(samples, fs=Fs, max_harmonic=7, create_plot=False)
# -> enob, sndr_dbc, sfdr_dbc, snr_dbc, thd_dbc

stat = analyze_inl_from_sine(codes, num_bits=N_bits)  # needs >= 1024 samples
# -> inl, dnl (in LSB)
```

**Watch for 1-sample latency masking a failed corner:** On an asynchronous SAR whose conversion slightly exceeds the conversion window, the code can latch cleanly one cycle late — a coherent sine FFT still shows high ENOB because a pure delay leaves the spectrum unchanged! Always check **undecided bit counts** and **$T_{\text{conv}}$ vs. window** alongside ENOB.

---

## 5. Phased Verification Flow

### Phase 1 — All-Behavioral Verilog-A Baseline
- Build the complete loop using the 10-bit behavioral models (`va_cdac_10b_diff.va`, `va_cmp_dynamic.va`, `va_sar_logic_10b_async.va`, `va_dac_10b_diff.va`, `va_bootstrap_sw.va`, `va_ldo_ideal.va`) or 4-bit tutorial models in [`../assets/va/`](../assets/va/), driven by [`../assets/tb/adc_top/`](../assets/tb/adc_top/README.md) (`tb_sar_adc_fft.scs` and `tb_sar_adc_ramp_dnl.scs`).
- Confirm architecture, polarities, bus ordering, coherent FFT setup, and near-ideal ENOB baseline ($6.02N + 1.76\text{ dB}$).

### Phase 2 — Standalone Per-Block Characterization

Run each block independently with its ready-to-run, process-independent Spectre testbench suite (plug in your PDK `models_corner.scs` + `dut_subckt.scs`, or smoke-test with [`../assets/tb/common/models_generic_bsim4.scs`](../assets/tb/common/models_generic_bsim4.scs)):

1. **Comparator** — [`../assets/tb/comparator/`](../assets/tb/comparator/README.md):
   - **`tb_cmp_pss_pnoise.scs`** (~3 s/corner): Shooting `pss` (`fund=1/tclk`, `harms=100`, `errpreset=conservative`, `autotstab=yes`) + sampled full-spectrum `pnoise` (`start=0`, `stop=0.5/tclk`, `measurement=[pm0]`, `pm0 jitterevent` on internal latch nodes `[LP LM]` crossing `v_observe`). Extract:
     - $\sigma_n = \frac{1}{V_{\text{observe}}/V_{\text{id,in}}} \sqrt{\int_0^{f_{\text{clk}}/2} S_{v,\text{out}}(f)\, df}$
     - `t_cmp`, `t_rst`, regeneration $\tau$, `power`, `energy = power * tclk`
     - $\text{FoM}_1 = \sigma_n^2 \cdot E_{\text{cmp}} \cdot 10^{21}\;[\text{mV}^2\cdot\text{fJ}]$, $\text{FoM}_2 = \sigma_n^2 \cdot E_{\text{cmp}} \cdot t_{\text{cmp}} \cdot 10^{30}\;[\text{mV}^2\cdot\text{fJ}\cdot\text{ns}]$.
   - **`tb_cmp_delay.scs`**: Sweep `vidin = 100u, 1m, 10m` across PVT corners.
   - **`tb_cmp_trannoise.scs`**: 300-cycle transient noise cross-check confirming PSS+PNOISE accuracy.
   - **`tb_cmp_offset.scs` + `cmp_bisect.va`**: Binary-search offset (Monte Carlo mismatch) and memory/hysteresis (`vpre = ±100m`).
2. **Bootstrap switch** — [`../assets/tb/bootstrap/`](../assets/tb/bootstrap/README.md) (`tb_boot_ron_sweep.scs`, `tb_boot_tran_linearity.scs`, `analyze_bootstrap.py`): clocked $R_{\text{on}}(V_{\text{in}})$ sweep (precharging flying cap `CB` every cycle, flatness $< 10\%$), near-Nyquist coherent sine sampling into `CL` (THD below noise floor, typically $< -70\text{ dB}$ for 10+ bits), and `VGATE` droop/oxide-stress audit.
3. **CDAC** — [`../assets/tb/cdac/`](../assets/tb/cdac/README.md) (`tb_cdac_static_dnl_inl.scs`, `tb_cdac_settling.scs`, `analyze_cdac.py`): full-code static sweep (DNL $< 0.5\text{ LSB}$, INL $< 1\text{ LSB}$, common-mode shift), worst-case MSB 0.5-LSB settling time, hold-mode feedthrough, and AC capacitance extraction.
4. **SAR logic** — [`../assets/tb/sar_logic/`](../assets/tb/sar_logic/README.md) (`tb_sar_logic_timing.scs`, `analyze_sar_logic.py`): multi-frame closed-loop timing & metastability check with `va_cmp_dynamic.va` + `va_cdac_10b_diff.va` (exact $N$ `CMPCK` pulses, clean `EOC`/`NOR3` stop, $T_{\text{conv}} < (1 - D_{\text{samp}})/f_s$, positive `VALID_L`-vs-`EN` margin).
5. **LDO (if used)** — [`../assets/tb/ldo/`](../assets/tb/ldo/README.md) (`tb_ldo_stb.scs`, `tb_ldo_psrr_noise.scs`, `tb_ldo_load_tran.scs`, `analyze_ldo.py`): `stb` phase margin ($\ge 45\text{–}60^\circ$), AC PSRR, integrated output noise, and fast load-step droop.
6. **Full SAR ADC top** — [`../assets/tb/adc_top/`](../assets/tb/adc_top/README.md) (`tb_sar_adc_fft.scs`, `tb_sar_adc_ramp_dnl.scs`, `analyze_adc_top.py`): coherent FFT (ENOB/SNDR/SFDR/THD) and overdriven ramp DNL/INL + usable full-swing check.

### Phase 3 — Incremental Transistor Replacement
Replace behavioral blocks one at a time in order: **Comparator → Bootstrap → CDAC → SAR Logic**, verifying ENOB and timing at each step to isolate interface, polarity, kickback, or parasitic issues immediately.

### Phase 4 — Full Transistor-Level & Post-Layout PVT Closure
Run full coherent FFT (low-freq + near-Nyquist), transient noise (`noiseruns=1`), Monte Carlo mismatch, and PVT corners (`ss`/`tt`/`ff`, temperature & supply bounds) pre- and post-layout (extracted R+C).

---

## 6. ADE Maestro Pitfalls (When Driving Virtuoso/Maestro)

When running these testbenches through Cadence ADE Maestro instead of standalone Spectre:
- **Verify generated `input.scs` for GUI-only fields:** `tranNoise` (`noisefmax`), `pss autotstab=yes`, and `pnoise pm0 jitterevent` are frequently dropped from `input.scs` if configured only via SKILL API without opening the GUI form. Inspect the generated netlist before trusting results (or use standalone `.scs` decks).
- **Corner `modelFiles` override test-level includes:** Put shared standard-cell SPICE/CDL includes in **Definition Files** (`definitionFiles`), not `modelFiles`, so corners do not silently drop them.
- **Use `VAR("param")` inside Maestro analysis forms** (e.g., `6*VAR("tclk")`, `1/VAR("tclk")`), whereas standalone Spectre decks use bare parameter names (`6*tclk`, `1/tclk`).
- **Always check per-point `spectre.out` logs:** Maestro can report a history "done" even when individual corners crashed or failed to converge.

---

## 7. Quick Debugging Checklist

| Symptom | Likely Cause | Fix |
|---|---|---|
| Only 2 codes (`0` and full-scale) | Comparator polarity inverted, or logic sampling during reset | Check reset-high vs. reset-low polarity; verify latch captures before `CMPCK` falls |
| Bit-reversed transfer curve | Spectre bus `[N-1:0]` MSB-first port ordering mismatch | Match MSB-first ordering in subcircuit instantiation |
| High ENOB on failed slow corner | Conversion spilled past window; code latched 1 sample late | Check `T_conv`, undecided bit count, and `VALID_LSB` vs. `CLKS` edge |
| Good ENOB, poor SFDR | Misaligned resampling instant, or sampling switch hold feedthrough | Use `strobeoutput=strobeonly` aligned after settling; add cross-connected dummy switch |
| Double comparator firing on one bit | `VALID_L` vs. `EN` race margin negative | Buffer `DOP`/`DON` before CDAC switches; add delay on `VALID_G → EN` path |
| Extra $(N+1)$-th `CMPCK` pulse | Slow `VALID_LSB → STOP` path through SR latch | Feed `VALID_LSB` directly into `NOR3(CLKS, QN, VALID_LSB)` |
| Silent zero noise in Maestro `NOISE` | `tranNoise` toggle not written to `input.scs` | Check `input.scs` for `noisefmax`; enable via GUI form or run standalone Spectre |
| `ERROR (SPECTRE-16394)` on `strobedelay` | `strobedelay >= strobeperiod` in `tran` | Keep `strobedelay < strobeperiod` and drop the initial warmup samples in post-processing |
| Severe FFT leakage or false `-1 LSB` DNL on `strobeonly` | Spectre appends `t = 0` and `t = t_stop` off the strobe grid | Filter waveforms to the uniform `k * strobeperiod + strobedelay` grid (see `extract_uniform_strobe` in `assets/tb/common/psf_utils.py`) |
