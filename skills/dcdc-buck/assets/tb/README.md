# Process-Independent Synchronous Buck Spectre X Testbench Suite

Full 8-deck industrial signoff Spectre X testbench suite for synchronous step-down DC-DC Buck converters (`V_in = 3.3 V`, `V_out = 1.2 V`, `f_sw = 2 MHz`, `L = 2.2 uH` w/ DCR `80 mOhm`, `C_out = 10 uF` w/ ESR `15 mOhm`, `I_load = 5..500 mA`).

All 8 decks are self-contained with the bundled Verilog-A models (`../va/`) and run out-of-the-box under **Spectre X (`+preset=cx +mt=2 -format psfascii`)**. To verify a transistor-level PDK design, replace the behavioral power stage / controller blocks with your PDK `models_corner.scs` + `dut_subckt.scs` matching the subcircuit interface contracts below.

## Files

| File | Analysis | Analyzer Subcommand | Key Metrics |
|---|---|---|---|
| `tb_buck_eff_ccm_dcm.scs` | 4-load `alter` + `tran` (20..500 mA) | `efficiency` | Per-load `vout_avg_v`, `p_in_mw`, `p_out_mw`, `eff_pct`, `p_loss_mw`, `mode` (`DCM`/`CCM`), `eff_peak_pct`, `eff_full_load_pct` |
| `tb_buck_ripple_sw.scs` | High-res CCM `tran` (`+preset=cx`) | `ripple` | `vout_avg_v`, `vout_ripple_pp_mv`, `il_ripple_pp_ma` vs. analytical, `duty_cycle_meas`, `sw_overshoot_v`, `sw_undershoot_v` |
| `tb_buck_softstart_inrush.scs` | Cold `EN` rising `tran` | `softstart` | `t_start_90pct_us`, `t_settle_1pct_us`, `il_inrush_peak_ma`, `vout_overshoot_mv`/`pct`, `monotonic_startup` |
| `tb_buck_load_line_tran.scs` | Load-step + line-step `tran` | `tran` | `load_undershoot_mv`, `load_overshoot_mv`, `t_recover_load_us`, `line_step_dev_mv` |
| `tb_buck_loop_stb.scs` | 4-corner averaged `alter` + `stb` | `stb` | Per-corner `dc_loop_gain_db`, `f_crossover_khz`, `phase_margin_deg`, `gain_margin_db`, `pm_min_deg`, `stb_pass` |
| `tb_buck_ocp_short.scs` | Hard `0.2 Ohm` short + release `tran` | `ocp` | `il_ocp_peak_ma`, `vout_short_mv`, `vout_recover_ok`, `t_recover_us` |
| `tb_buck_psrr_noise.scs` | Averaged `ac` + strobed switching FFT | `psrr_spur` | `psrr_dc_db`, `psrr_10khz_db`, `psrr_fc_min_db`, `spur_fsw_dbv`/`mvrms`, `spur_2fsw_dbv`/`mvrms` |
| `tb_buck_deadtime_shoot.scs` | 3-regime `t_dead` `alter` + `tran` | `deadtime` | Per-regime (`-5 ns`, `10 ns`, `60 ns`): `i_shoot_peak_ma`, `p_sw_loss_mw`, `eff_pct`, `sw_min_v`, `deadtime_safe` |
| `analyze_buck.py` | Standalone PSF ASCII analyzer | 8 subcommands above | Zero-dependency (`numpy` + `common/psf_utils.py`) JSON summary |

## Transistor-Level Plug-In Contracts

```spectre
// 5-pin synchronous half-bridge power stage (used directly in tb_buck_deadtime_shoot.scs
// and inside closed-loop switching decks to swap in BSIM4 / PDK power FETs)
subckt dut_halfbridge (VIN SW GH GL VSS)
    // Active-high gate commands GH (high-side) and GL (low-side), [0..VIN].
    // For a PMOS high-side switch, invert GH internally (GHB = VIN - GH).
ends dut_halfbridge

// 9-pin Peak Current-Mode PWM controller (used in closed-loop switching decks)
subckt dut_buck_controller (VIN VREF EN FB COMP ISNS GH GL VSS)
    // Regulates FB -> VREF with external Type-II compensation on COMP and
    // cycle-by-cycle current limit sensed via V(ISNS) = r_sns * I_L.
ends dut_buck_controller
```
