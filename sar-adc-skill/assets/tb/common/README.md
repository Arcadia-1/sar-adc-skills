# Shared Testbench Utilities (`assets/tb/common/`)

Shared, process-independent helper assets used across all SAR ADC block testbenches:

- **`psf_utils.py`** — Zero-dependency Spectre PSF ASCII parser (handles real `tran`/`dc`/`noise`/`pss`/`pnoise` and complex `ac`/`stb` traces), threshold crossing interpolator, coherent FFT metric extractor (`ENOB`, `SNDR`, `SNR`, `SFDR`, `THD`), and endpoint-fit `DNL`/`INL` calculator.
- **`models_generic_bsim4.scs`** — Synthetic, foundry-free textbook Spectre BSIM4 model pair (`nch` / `pch`) with thermal noise and overlap/junction capacitances enabled. Use this strictly for out-of-the-box smoke verification of transistor testbenches when no PDK is attached; replace with your own `models_corner.scs` for real process sizing and signoff.
