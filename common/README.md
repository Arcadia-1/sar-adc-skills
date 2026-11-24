# Shared AMS Testbench Utilities (`common/`)

Shared, process-independent helper assets used across all skills in `ams-skills` (`skills/sar-adc/`, `skills/pll/`, etc.):

- **`psf_utils.py`** — Zero-dependency Spectre PSF ASCII parser (handles real `tran`/`dc`/`noise`/`pss`/`pnoise` and complex `ac`/`stb` traces), `extract_uniform_strobe`, threshold crossing interpolator, coherent FFT metric extractor (`ENOB`, `SNDR`, `SNR`, `SFDR`, `THD`), endpoint-fit `DNL`/`INL` calculator, and single-sideband phase-noise-to-RMS-jitter integrator.
- **`models_generic_bsim4.scs`** — Synthetic, foundry-free textbook Spectre BSIM4 model pair (`nch` / `pch`) with thermal noise and overlap/junction capacitances enabled. Use this strictly for out-of-the-box smoke verification of transistor testbenches when no PDK is attached; replace with your own `models_corner.scs` for real process sizing and signoff.
