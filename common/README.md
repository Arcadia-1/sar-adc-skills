# Shared AMS Testbench Utilities (`common/`)

Shared, process-independent helper assets used across all skills in `ams-skills` (`skills/sar-adc/`, `skills/dac/`, `skills/pll/`, `skills/opamp-ota/`, `skills/ldo/`, `skills/bandgap/`):

- **`psf_utils.py`** — Zero-dependency Spectre PSF ASCII parser (handles real `tran`/`dc`/`noise`/`pss`/`pnoise` and complex `ac`/`stb` traces), `extract_uniform_strobe`, threshold crossing interpolator, coherent single-tone FFT extractor (`ENOB`, `SNDR`, `SNR`, `SFDR`, `THD`, `HD2`, `HD3`), coherent two-tone intermodulation extractor (`IM3`, `IMD3`, `IM2`, `SFDR`), endpoint-fit `DNL`/`INL` calculator, and IEEE-1139 phase-noise-to-RMS-jitter integrator.
- **`models_generic_bsim4.scs`** — Synthetic, foundry-free textbook Spectre BSIM4 model pair (`nch` / `pch`) with thermal noise and overlap/junction capacitances enabled. Use this strictly for out-of-the-box smoke verification of transistor testbenches when no PDK is attached; replace with your own `models_corner.scs` for real process sizing and signoff.
