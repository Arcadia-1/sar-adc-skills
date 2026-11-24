# SAR ADC Verilog-A Behavioral Model Library

Process-independent, Spectre-verified Verilog-A models for phased SAR ADC verification (`Phase 1` all-behavioral $\to$ `Phase 3` hybrid transistor replacement).

## `behavioral_10b/` — 10-Bit Non-Ideality-Injectable Models (Production Verification)

| Model | Module | Key Injectable Non-Idealities / Purpose |
|---|---|---|
| [`va_cmp_dynamic.va`](behavioral_10b/va_cmp_dynamic.va) | `va_cmp_dynamic` | `vos`, Gaussian `vnoise_rms`, logarithmic regeneration delay `tau_regen`, `td_min`, `td_rst` |
| [`va_cdac_10b_diff.va`](behavioral_10b/va_cdac_10b_diff.va) | `va_cdac_10b_diff` | Vcm-based (`mode=0`) or monotonic (`mode=1`), `c_par_ratio`, MSB mismatch `dm_msb`, `tau_settle` |
| [`va_sar_logic_10b_async.va`](behavioral_10b/va_sar_logic_10b_async.va) | `va_sar_logic_10b_async` | Self-timed async state machine with `EOC` completion stop and latched `DOUT[9:0]` |
| [`va_dac_10b_diff.va`](behavioral_10b/va_dac_10b_diff.va) | `va_dac_10b_diff` | Mid-rise 10-bit differential reconstruction DAC (`AOUT` + integer `CODE`) |
| [`va_bootstrap_sw.va`](behavioral_10b/va_bootstrap_sw.va) | `va_bootstrap_sw` | Bootstrapped (`mode=0`, flat `Ron`) vs. plain NMOS (`mode=1`, nonlinear `Ron(Vin)`) |
| [`va_code_ramp_10b.va`](behavioral_10b/va_code_ramp_10b.va) | `va_code_ramp_10b` | Sequential 10-bit code/differential-control sweep generator for CDAC DNL/INL TBs |

## `tutorial_4b/` — 4-Bit Educational Baseline Models

| Model | Module | Purpose |
|---|---|---|
| [`L2_cdac_4b_ideal.va`](tutorial_4b/L2_cdac_4b_ideal.va) | `L2_cdac_4b_ideal` | Minimal 4-bit ideal differential CDAC |
| [`L2_comparator_ideal.va`](tutorial_4b/L2_comparator_ideal.va) | `L2_comparator_ideal` | Minimal ideal clocked comparator |
| [`L2_logic_4b_sync.va`](tutorial_4b/L2_logic_4b_sync.va) | `L2_logic_4b_sync_ideal` | 4-bit synchronous SAR logic (`CLKS` + `CLKC`) |
| [`L3_logic_4b_async.va`](tutorial_4b/L3_logic_4b_async.va) | `L3_logic_4b_async` | 4-bit asynchronous event-driven SAR logic |
| [`_va_dac_4b.va`](tutorial_4b/_va_dac_4b.va) | `_va_dac_4b` | 4-bit differential reconstruction DAC |
| [`_va_dac_4b_se.va`](tutorial_4b/_va_dac_4b_se.va) | `_va_dac_4b_se` | 4-bit single-ended reconstruction DAC |
| [`sar_4b_se_ideal.va`](tutorial_4b/sar_4b_se_ideal.va) | `sar_4b_se_ideal` | Monolithic single-ended 4-bit ideal SAR ADC |
