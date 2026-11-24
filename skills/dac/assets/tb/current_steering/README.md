# Current-Steering DAC Spectre Testbench Suite

Process-independent Spectre decks and zero-dependency analyzer for 10-bit differential current-steering DACs.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_dac_static_dnl_inl.scs` | 1024-code sequential sweep (`strobeoutput=strobeonly`) | `full_scale_v`, `lsb_mv`, `dnl_max/min`, `inl_max/min`, `monotonic`, `offset_mv` |
| `tb_dac_dynamic_sfdr.scs` | Coherent single-tone (`sig_mode=0`) or two-tone IMD3 (`sig_mode=1`) `tran` | Single-tone: `sfdr_db`, `hd2_dbc`, `hd3_dbc`, `thd_db`, `sndr_db`, `enob`; Two-tone: `im3_lo_dbc`, `im3_hi_dbc`, `imd3_dbc`, `sfdr_db` |
| `tb_dac_glitch_settle.scs` | Fine-timestep (`maxstep=5p`) major-carry `511 -> 512` & `512 -> 511` `tran` | `rise/fall_glitch_peak_mv`, `rise/fall_glitch_impulse_pvs`, `rise/fall_t_settle_0p5lsb_ns` |
| `tb_dac_sfdr_vs_fin.scs` | 4-frequency coherent Nyquist `alter` sweep (`M={7,29,67,113}`, `osr=8` + 3rd-order Butterworth AA LPF) | Per-tone `f_in_mhz`, `sfdr_db`, `hd2_dbc`, `hd3_dbc`, `sndr_db`, `enob_bits`, plus `sfdr_low_db`, `sfdr_nyq_db`, `sfdr_rolloff_db` |
| `tb_dac_psrr_jitter.scs` | 3-stage `alter` (`tran_psrr`, `tran_clean`, `tran_jitter` w/ `va_dac_clk_jitter.va`) | `psrr_db`, `supply_spur_dbc`, `sb_lo/hi_dbc`, `snr_clean_db`, `snr_jitter_db`, `snr_jitter_theory_db`, `t_j_est_ps` |
| `tb_dac_output_compliance.scs` | DC `v_term` compliance sweep (`dc_comp`) + dynamic `0% vs 2%` `R_load` mismatch (`tran_matched`/`tran_mismatched`) | `v_comp_max_v`, `r_out_eff_kohm`, `compliance_margin_mv`, `hd2_matched_dbc`, `hd2_mismatched_dbc`, `hd2_degradation_db` |
| `tb_dac_dem_mismatch.scs` | Static (`DEM_EN=0`) vs. first-order DWA (`DEM_EN=vdd_dig`) `alter` (`N=512`, `m_bin=19`, `OSR=4`) | `sfdr_static_db`, `sfdr_dem_db`, `sfdr_gain_db`, `hd2/hd3_static_vs_dem_dbc`, `sndr_static/dem_db` (in-band & Nyquist) |
| `analyze_cs_dac.py` | Standalone PSF ASCII analyzer (`static`, `dynamic`, `twotone`, `glitch`, `sfdr_sweep`, `psrr_jitter`, `compliance`, `dem`) | JSON summary |

## DUT Interface Contracts

Provide `models_corner.scs` and `dut_subckt.scs` defining the matching subcircuit:

```spectre
// Unclocked 14-pin contract (static, dynamic, glitch, sfdr_vs_fin, output_compliance):
subckt dut_cs_dac DIN9 DIN8 DIN7 DIN6 DIN5 DIN4 DIN3 DIN2 DIN1 DIN0 VDD VSS IOUTP IOUTN
    // instantiate your transistor CS-DAC (or wrap ../../va/va_dac_cs_10b.va / va_dac_cs_dem_10b.va)
ends dut_cs_dac

// Clocked 15-pin contract (tb_dac_psrr_jitter.scs):
subckt dut_cs_dac_clk DIN9 DIN8 DIN7 DIN6 DIN5 DIN4 DIN3 DIN2 DIN1 DIN0 CLK VDD VSS IOUTP IOUTN
    // instantiate clocked CS-DAC (or wrap ../../va/va_dac_cs_dem_10b.va with clk_en=1)
ends dut_cs_dac_clk

// Clocked + DEM control 16-pin contract (tb_dac_dem_mismatch.scs):
subckt dut_cs_dac_dem DIN9 DIN8 DIN7 DIN6 DIN5 DIN4 DIN3 DIN2 DIN1 DIN0 CLK DEM_EN VDD VSS IOUTP IOUTN
    // instantiate DWA/DEM CS-DAC (or wrap ../../va/va_dac_cs_dem_10b.va)
ends dut_cs_dac_dem
```

The testbenches terminate `IOUTP` and `IOUTN` with matched load resistors `rload` (default `50 ohm` to `VSS`, or to swept `VTERM` in `tb_dac_output_compliance.scs`, plus optional `cload`) and evaluate differential output `V_diff = V(IOUTP) - V(IOUTN)`. For continuous-time RF DAC harmonic and clock-jitter measurements (`tb_dac_sfdr_vs_fin.scs`, `tb_dac_psrr_jitter.scs`), a unity-gain 3rd-order passive Butterworth anti-aliasing filter (`fc_lpf = 0.65 * fs`) drives `V_FILT` strobed at `osr = 8`, eliminating out-of-band ZOH staircase aliasing while keeping the first Nyquist zone `[0, fs/2]` flat.
