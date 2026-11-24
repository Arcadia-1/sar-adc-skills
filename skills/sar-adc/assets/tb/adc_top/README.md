# Process-Independent Full SAR ADC Testbench Suite (Spectre)

Standalone, PDK-agnostic system-level Spectre testbenches and analyzer for phased SAR ADC verification (behavioral -> hybrid -> full transistor-level signoff).

## Files

| File | Purpose | Key Metrics |
|---|---|---|
| `tb_sar_adc_fft.scs` | Coherent single-tone FFT (`strobeoutput=strobeonly`, `conservative`) | `ENOB`, `SNDR`, `SNR`, `SFDR`, `THD`, `amp_dbfs`, clipping flag |
| `tb_sar_adc_ramp_dnl.scs` | Overdriven slow differential ramp sweep | Usable `VFS_diff`, missing codes, histogram `DNL` / `INL` |
| `tb_sar_adc_twotone_imd.scs` | Coherent near-Nyquist two-tone FFT (`m_bin1=97, m_bin2=107`, `-6.5 dBFS`/tone) | `imd2_dbc`, `imd3_dbc`, `sfdr_db`, `sndr_db`, `tone1_db`, `tone2_db` |
| `tb_sar_adc_vref_droop.scs` | Ideal vs. undersized vs. decoupled `va_vref_buffer` (`alter` + 4-cycle waveform) | `vref_droop_peak_mv`, `vref_settle_err_lsb`, before/after `enob`/`sfdr_db`/`hd3_dbc` |
| `tb_sar_adc_trannoise_fft.scs` | Dual transient-noise coherent FFT + grounded-input histogram (`n_hist=512`) | Measured vs. analytical `SNR`/`ENOB`, `sigma_total_lsb`, `sigma_in_uvrms`, `offset_lsb` |
| `tb_sar_adc_psrr_cmrr.scs` | Coherent `50 mVpp` `VDD` ripple + 3-point `Vcm` `alter` sweep (`vcm_nom +/- 0.1 V`) | `psrr_db`, `f_in +/- f_rip` sidebands, `cmrr_db`, `offset_shift_lsb`, `ENOB(Vcm)` |
| `tb_sar_adc_input_driver.scs` | Slew/BW-limited `va_input_driver` + AA RC (`r_aa`, `c_ext`) with CDAC kickback & unloaded reference branch | Acquisition-end settling error `[LSB]`, `enob`/`thd_db`/`sfdr_db` before & after sizing |
| `tb_sar_adc_erbw_jitter.scs` | 4-frequency coherent prime-bin sweep (`~0.03, 0.23, 0.44, 0.91 * fs`) with `va_clk_jitter` | `ENOB(f_in)`, `SNR(f_in)`, `ERBW`, inverted RMS aperture jitter `t_j_est_fs` |
| `tb_ti_sar_mismatch.scs` | 4-channel Time-Interleaved SAR (`fs_eff = 4 * fs_ch`, `0/90/180/270 deg`) with `vos_k`, `dg_k`, `dt_k` | Uncalibrated offset/image spurs, foreground O/G/skew estimation & calibrated `SFDR`/`ENOB` recovery |
| `analyze_adc_top.py` | Standalone PSF ASCII analyzer (`fft`, `ramp`, `twotone`, `vref_droop`, `noise_hist`, `psrr_cmrr`, `input_driver`, `erbw_jitter`, `ti_sar`) | JSON summary |

## DUT Interface Contracts

### Standard 10-bit SAR ADC (`dut_sar_adc`)

Used by all decks except `tb_sar_adc_vref_droop.scs`:

```spectre
subckt dut_sar_adc VIP VIN CLKS \
    DOUT9 DOUT8 DOUT7 DOUT6 DOUT5 DOUT4 DOUT3 DOUT2 DOUT1 DOUT0 \
    VDD VSS
    // Phase 1 (behavioral): assemble va_cdac_10b_diff + va_cmp_dynamic + va_sar_logic_10b_async
    // Phase 2 (hybrid): swap one block at a time with your transistor subcircuit
    // Phase 3 (full): instantiate your complete transistor SAR ADC core
ends dut_sar_adc
```

### Explicit-VREF 10-bit SAR ADC (`dut_sar_adc_vref`)

Used by `tb_sar_adc_vref_droop.scs` so the CDAC physically draws switching charge from `VREF` driven by `va_vref_buffer.va`:

```spectre
subckt dut_sar_adc_vref VIP VIN CLKS \
    DOUT9 DOUT8 DOUT7 DOUT6 DOUT5 DOUT4 DOUT3 DOUT2 DOUT1 DOUT0 \
    VREF VDD VSS
    // Phase 1: build a physical split-capacitor Spectre capacitor+relay CDAC wired to VREF
    //          + va_cmp_dynamic + va_sar_logic_10b_async
    // Phase 3: instantiate your complete transistor SAR ADC with VREF pin exposed
ends dut_sar_adc_vref
```

## Notes

- Run Spectre X with `+preset=cx` (add `-preset_override` for ultra-clean two-tone IMD and TI-SAR spectral floors) or `+preset=ax` for transient-noise runs (`noiseruns=1`). Avoid `+preset=mx` for ENOB signoff (~0.3-bit accuracy loss).
- For deeper FFT diagnostics (harmonic spurs, noise-floor breakdown, INL-from-sine), export `CODE` directly to [ADCToolbox](https://github.com/Arcadia-1/ADCToolbox).
