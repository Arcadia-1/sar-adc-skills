# Pierce Crystal Oscillator (XO) Spectre Testbench Suite

Process-independent Spectre X & Spectre RF testbenches and zero-dependency PSF analyzer for fundamental-mode **Pierce Crystal Oscillators** (default 24 MHz AT-cut Butterworth–Van Dyke quartz model: `L_m = 7.329368 mH`, `C_m = 6.0 fF`, `R_m = 40 Ohm`, `C_0 = 2.0 pF`, `C_L1 = C_L2 = 16 pF` -> `C_L = 8 pF`, `Q = 27,630`).

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_xo_neg_resistance.scs` | Small-signal `ac` (`1 MHz - 100 MHz`) across `XI - XO_P` (with `C_0`, `C_L1`, `C_L2`) | `r_neg_at_f0_ohm`, `startup_margin_x` (`|R_neg|/R_m >= 5x`), `c_eff_pf`, active band `[neg_r_fmin_mhz, neg_r_fmax_mhz]`, `margin_pass` |
| `tb_xo_startup_drive.scs` | Closed-loop BVD `tran` (`q_scale=20` fast envelope + `IKICK` pulse, `method=traponly`, requires `+aps`) | `v_xi_pp_v`, `v_xo_pp_v`, `i_mot_pk_ma`, `p_xtal_uw` (`< 100 uW`), `f_osc_mhz`, `duty_cycle_pct`, `t_startup_90pct_us`, `i_dd_ua`, `drive_level_pass` |
| `tb_xo_pullability_cload.scs` | 5-code `alter` sweep of `C_L1 = C_L2` (`10, 13, 16, 19, 22 pF`) on full-Q BVD via series `VTEST` `ac` loop probe | Per-code `f_osc_mhz`, `df_ppm`, `pull_range_ppm`, `trim_step_ppm`, `pullability_ppm_per_pf`, `monotonic`, `worst_startup_margin_x` |
| `tb_xo_pss_pnoise.scs` | Full-Q (`q_scale=1`) autonomous Harmonic-Balance `pss (XO 0)` (`flexbalance=yes oscic=lin`) + relative PM `pnoise` (`10 Hz - 1 MHz`, requires `+aps`) | `f_0_mhz`, `pn_100hz/1khz/10khz/100khz/1mhz_dbc`, integrated `j_rms_fs` (`1 kHz - 1 MHz`), `p_dc_uw`, `i_dd_ua` |
| `analyze_xo.py` | Standalone PSF ASCII analyzer (`neg_r`, `startup`, `pullability`, `pss_pnoise`) | JSON summary |

## DUT Interface Contract

Provide `models_corner.scs` (your PDK or repo-root `common/models_generic_bsim4.scs` / `common/models_sky130_minimal.scs`) and `dut_subckt.scs` implementing a 4-pin Pierce sustaining amplifier (including internal DC self-bias feedback resistor `R_fb`, e.g., `1 MOhm`):

```spectre
subckt dut_xo_amp XI XO VDD VSS
    // Instantiate your transistor Pierce CMOS inverter + R_fb,
    // or wrap ../../va/va_xo_amp.va
ends dut_xo_amp
```

### Usage Examples

```bash
# Behavioral or transistor-level Spectre X runs
spectre +preset=cx -format psfascii -raw neg_r.raw tb_xo_neg_resistance.scs
python3 analyze_xo.py neg_r neg_r.raw --f0 24e6 --rm 40 --min-margin 5

spectre +aps -format psfascii -raw start.raw tb_xo_startup_drive.scs
python3 analyze_xo.py startup start.raw --rm 40 --q-scale 20 --max-drive-uw 100

spectre +preset=cx -format psfascii -raw pull.raw tb_xo_pullability_cload.scs
python3 analyze_xo.py pullability pull.raw --min-margin 5

spectre +aps -format psfascii -raw pss.raw tb_xo_pss_pnoise.scs
python3 analyze_xo.py pss_pnoise pss.raw --vdd 1.8 --f-low 1e3 --f-high 1e6
```
