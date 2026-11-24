# POR / BOR Supervisor Spectre X Testbench Suite

Process-independent Spectre X (`+preset=cx`) decks and zero-dependency PSF ASCII analyzer for nano-power Power-On Reset (POR) and programmable Brown-Out Reset (BOR) supervisors.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_por_thresholds_hys.scs` | Slow triangular `VDD` ramp (`0 -> 1.8 V -> 0 V`, `2 ms` plateau) `tran` | `v_por_rise_v`, `v_por_fall_v`, `v_hys_mv`, `max_glitch_low_vdd_mv`, `n_rise_edges`, `iq_na`, `hys_pass`, `low_vdd_clamp_pass` |
| `tb_por_ramp_rates.scs` | 3-decade `alter` ramp stress (`10 us`, `200 us`, `4 ms`) `tran` | Per-ramp `v_release_v`, `t_rst_delay_us`, `low_vdd_glitch_mv`, `clean_release`, plus `t_rst_spread_us` & `all_clean_release` |
| `tb_por_glitch_immunity.scs` | 4 negative `VDD` drop pulses (`0.5 us`, `1.5 us`, `5 us`, `15 us` to `0.6 V`) `tran` | Per-pulse `triggered`, `min_rstb_over_vdd`, `t_rst_recover_us`, plus `immune_short`, `detect_long`, `glitch_filter_pass` |
| `tb_bor_multi_level.scs` | 8-code `alter` sweep (`vtrim_code = 0..7`) with triangle ramp per code | `v_bor_rise_v[0..7]`, `v_bor_fall_v[0..7]`, `v_hys_mv[0..7]`, `step_mv_per_lsb`, `dnl_max_lsb`, `inl_max_lsb`, `monotonic`, `iq_mean_na` |
| `analyze_por_bor.py` | Standalone PSF ASCII analyzer (`thresholds`, `ramps`, `glitch`, `bor_levels`) | JSON summary |

## DUT Interface Contract

Provide `models_corner.scs` (your PDK corner or repo-root `common/models_generic_bsim4.scs` / `common/models_sky130_minimal.scs`) and `dut_subckt.scs`:

```spectre
// 4-pin POR/BOR Supervisor contract
//   - VTRIM: analog 3-bit code 0..7 (nominal code = 3 -> V_POR+ = 1.05 V)
//   - RSTB : active-low reset output (0 V = asserted, VDD = released)
subckt dut_por_bor VDD VTRIM RSTB VSS
    // instantiate your transistor POR/BOR (or wrap ../../va/va_por_bor.va)
ends dut_por_bor
```

All decks measure rising/falling trip points via relative `RSTB - 0.5 * VDD = 0` crossings (supporting programmable low BOR thresholds and CMOS rail-tracking drivers) and evaluate quiescent current on a flat `VDD = vdd_nom` plateau to exclude capacitive ramp current.
