# SAR ADC Simulation & Verification

How to set up a Spectre transient simulation for a SAR ADC and extract dynamic/static performance metrics.

## 1. Coherent Sampling Setup

FFT-based metric extraction requires **coherent sampling** — the input frequency must be an exact integer number of cycles within the record:

```
fin = M / N * Fs
```

where `M` (number of input cycles) and `N` (number of samples) are coprime. Common choices:

| N | Good M values (prime) | Notes |
|---|----------------------|-------|
| 64 | 7, 11, 13 | Quick smoke test |
| 128 | 11, 13, 53 | Minimum for ~10-bit resolution |
| 256 | 31, 67, 127 | Good for 10-12 bit |
| 1024 | 127, 251, 509 | Publication quality |

Use `adctoolbox.find_coherent_frequency(Fs, fin_target, N)` to select the nearest coherent frequency.

**Non-coherent sampling** causes spectral leakage that artificially degrades ENOB by 10-20 dB. Windowing (Hann, etc.) can mitigate but is inferior to coherent sampling for ADC testing.

## 2. Input Signal

### Amplitude

- Single-ended: `ampl = A`, `sinedc = VDD/2` (centered at mid-supply)
- Differential: VIP gets `ampl = +A/2`, VIN gets `ampl = -A/2`, both with `sinedc = VDD/2`
- Typical A = 80-95% of full scale. Too close to rail causes clipping distortion; too small underutilizes the ADC range.

### Spectre vsource Gotcha

In Spectre `vsource type=sine`:
- **`ampl`** sets transient sine amplitude (this is what you want)
- **`mag`** sets AC small-signal magnitude (for `.ac` analysis only, NOT transient)

Using `mag` instead of `ampl` gives a default 1V swing in transient — a common mistake.

## 3. Sampling Clock

### Sync SAR (external bit clock)

Two clocks needed:
- **CLKS** at Fs — controls sample/convert phases
- **BITCLK** at (N_bits + 2) × Fs — one tick per SAR bit decision

CLKS duty cycle: ~1-2 BITCLK cycles high (sample), remainder low (convert).

### Async SAR (self-timed)

Only CLKS needed. The SAR logic internally generates CMPCK pulses. CLKS duty cycle typically 20-25% high.

## 4. Simulation Settings

| Parameter | Conservative | Fast Iteration |
|-----------|-------------|----------------|
| `maxstep` | 5-10 ps | 50-200 ps |
| Spectre mode | `spectre` / `aps` | `mx` (3-5x faster) |
| N (FFT length) | 128-1024 | 16-64 |
| Extra settle cycles | 5-20 | 2-5 |

**`mx` mode** is strongly recommended for iterative design — gives nearly identical accuracy at 3-5x less wall time.

### Strobe Output

Add `strobeperiod=1/Fs` and `strobeoutput=all` to capture exactly one data point per conversion. This avoids the need to manually identify sample boundaries in post-processing.

## 5. Output Extraction

### Analog Reconstruction (preferred)

If the testbench includes a behavioral DAC that converts DOUT back to analog (common practice), use its output (e.g., `AOUT`) for FFT analysis. This is cleaner than reconstructing from digital bits.

**Resample at strobe times:**

```python
t_strobe = t_skip + np.arange(N) * (1.0 / Fs)
samples = np.interp(t_strobe, t_sim, aout_sim)
```

Misaligned resampling is the #1 cause of artificially low SFDR. Sample at a consistent phase within each clock period, after the DAC output has settled.

### From Digital Bits

Reconstruct codes from DOUT bus signals:

```python
code = sum((V(DOUT[bit]) > VDD/2) << bit for bit in range(n_bits))
```

Read codes at a consistent time relative to the end-of-conversion marker (EOC signal, or CLKS rising edge).

### Spectre Bus Port Ordering

**Spectre expands bus ports `[N:0]` as MSB first.** A subcircuit port `DOUT[9:0]` maps to pin order `DOUT9, DOUT8, ..., DOUT0` in the instance connection. Getting this wrong produces bit-reversed codes — easily mistaken for a broken ADC.

## 6. Performance Metrics (ADCToolbox)

### Dynamic Metrics

```python
from adctoolbox import analyze_spectrum
spec = analyze_spectrum(samples, fs=Fs, max_harmonic=7, create_plot=False)
# Returns: enob, sndr_dbc, sfdr_dbc, snr_dbc, thd_dbc, harmonics_dbc
```

### Static Metrics

```python
from adctoolbox import analyze_inl_from_sine
result = analyze_inl_from_sine(codes, num_bits=N_bits)
# Returns: inl, dnl (in LSB)
```

Needs >1024 samples spanning full input range.

**Do not hand-write FFT or ENOB formulas.** Use `adctoolbox` — it handles windowing, bin detection, harmonic exclusion, and noise floor estimation correctly.

## 7. Debugging Checklist

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Only 2 unique codes (0 and full-scale) | Comparator polarity wrong or not reading valid output | Check StrongArm output polarity; add SR latch if comparator resets before SAR reads |
| Bit-reversed code mapping | Bus `[N:0]` port ordering (MSB first) | Reverse pin order in subcircuit instantiation |
| ENOB near ideal but bad SFDR | Resampling time misaligned | Use strobe output or sample at consistent clock phase |
| Code range < full scale | Input exceeds reference, or sampling switch has Vth drop | Reduce amplitude or use bootstrap switch |
| Large offset in code mean | CDAC initial state mismatch (single-ended) or charge injection | Use differential CDAC; match initial bottom-plate states |
| ENOB degrades with transistor-level blocks | Parasitic capacitance changes bit weights | Increase CDAC unit cap to reduce parasitic ratio; verify settling |
| Alternating valid/zero codes | SAR state machine missing cycles | Check CLKS duty cycle vs required number of bit-clock cycles |

## 8. StrongArm Comparator Interface

The StrongArm dynamic comparator has specific behavior that affects how SAR logic reads its output:

- During **CLK=high** (evaluation): one output falls to 0, the other stays at VDD. The falling output indicates which input is larger.
- During **CLK=low** (reset): both outputs return to VDD.

**Problem:** If SAR logic reads at CLK falling edge, both outputs are transitioning to VDD (reset). The valid decision is lost.

**Solution:** Insert an **SR latch** between comparator and SAR logic. The latch captures which output fell first and holds the decision through the reset phase. SAR logic reads the latched output safely at any time.

## 9. Differential vs Single-Ended CDAC

Single-ended CDAC suffers from **signal-dependent charge injection** from the sampling switch — this fundamentally limits ENOB to ~4-6 bits regardless of resolution.

Differential CDAC (two matched CDACs, cross-connected inputs) cancels common-mode charge injection. The comparator sees the differential VTOP_P - VTOP_N, rejecting matched injection on both sides.

**CDAC switch polarity convention (complementary pass gate):**
- CTRL=LOW → PMOS on → bottom plate = VREFP
- CTRL=HIGH → NMOS on → bottom plate = VREFN
- Setting a bit = CTRL goes HIGH = bottom plate moves from VREFP to VREFN = VTOP drops

In differential operation, CDACP and CDACN use complementary CTRL signals (from SAR logic DP/DN outputs). Setting a bit drops VTOPP and raises VTOPN simultaneously.

## 10. Phased Verification Flow

```
Phase 1: All-behavioral Verilog-A
  Goal: Verify architecture, establish ENOB baseline (expect near-ideal)
  Effort: 1 day, single worker

Phase 2: Per-block functional test
  Goal: Each sub-block simulates independently with quantitative pass/fail
  Effort: Parallelize across multiple workers

  Comparator — PSS + Pnoise noise characterization:
    Run PSS (fund=CLK_FREQ, harms=10, errpreset=conservative) then
    Pnoise (pnoisemethod=fullspectrum, noisetype=sampled) with jitter
    event on latch nodes (LP/LM). Extract input-referred noise (sigma),
    comparison delay Tcmp, and power from supply current integral.
    Compute FOM = sigma^2 x power. Pass: FOM meets noise budget for
    target ENOB (sigma < 0.5 LSB of the full ADC).

  Bootstrap — sampling linearity via THD:
    Drive sine input through bootstrap switch into a capacitor load
    sized to match the CDAC. Resample output at Fs, extract THD with
    analyze_spectrum. Sweep input amplitude 10-95% FS.
    Pass: THD < -70 dB. Also verify Ron flatness (< 10% variation
    across VIN range) with a slow ramp + DC operating point.

  CDAC — code sweep for static linearity:
    Drive all 2^N codes sequentially with a behavioral SAR controller.
    Measure VTOP at each code after full settling. Compute DNL and INL.
    Pass: |DNL| < 0.5 LSB, |INL| < 1 LSB. Also measure MSB settling
    time — must be < one bit-clock period with margin.

  SAR logic — ramp test with behavioral analog blocks:
    Connect behavioral comparator + CDAC to the transistor-level logic.
    Apply a slow ramp covering full scale. Verify output codes are
    monotonic and all 2^N codes appear (no missing codes). Measure
    total conversion time — must complete within 1/Fs.
    Pass: zero missing codes, monotonic transfer curve.

Phase 3: Incremental transistor replacement
  Goal: Replace one block at a time, verify ENOB degradation < 0.3 bits
  Order: Comparator → Bootstrap → CDAC → SAR logic
  Criterion: If ENOB drops significantly, debug that block before proceeding

Phase 4: Full transistor-level / Maestro netlist
  Goal: Final performance characterization
  Metrics: ENOB, SNDR, SFDR, THD, DNL, INL across corners
```

Each phase catches different classes of bugs:
- Phase 1 catches architecture errors (wrong polarity, missing connections)
- Phase 2 catches per-block performance issues (noise, settling, linearity)
- Phase 3 catches interface issues (timing, charge sharing, parasitics)
- Phase 4 catches system-level issues (PVT sensitivity, supply noise, reference droop)
