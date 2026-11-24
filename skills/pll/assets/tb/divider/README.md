# Process-Independent Frequency Divider & MMD Testbench Suite (Spectre)

Standalone Spectre testbenches for verifying Integer-N dividers, Fractional-N MASH 1-1-1 Multi-Modulus Dividers (MMD), and high-speed prescaler/divider maximum toggle frequency (`f_max`) and cycle-slip signoff.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_div_func_mmd.scs` | Long transient (~300 divided output cycles at `f_in = 1 GHz`) | Long-term mean ratio `n_avg`, instantaneous modulus bounds `[n_min_inst, n_max_inst]`, `ratio_err_ppm` |
| `tb_div_max_toggle.scs` | 4-frequency `alter` stress sweep (`1.5 / 3.0 / 4.5 / 6.0 GHz`) into `c_load = 50 fF` | Per-frequency edge counts, `n_meas`, `cycle_slip` flag, `f_max_pass_ghz`, `duty_pct`, 20%–80% `tr_20_80_ps` / `tf_80_20_ps` |
| `analyze_divider.py` | Standalone PSF ASCII analyzer (`func` and `toggle` modes; legacy bare `<psf_dir>` aliases `func`) | JSON summary |

## DUT Interface Contract

Provide `models_corner.scs` (your PDK or repo-root `common/models_generic_bsim4.scs`) and `dut_subckt.scs`:

```spectre
subckt dut_divider CLK_IN CLK_OUT VDD VSS
    // instantiate your transistor divider/MMD or behavioral wrapper
ends dut_divider
```

### Reference DUT Wrappers for `tb_div_max_toggle.scs`

- **Behavioral Finite-BW Wrapper (`va_div_int.va`):** Insert an input RC pole (`R_BW`, `C_BW`) ahead of `va_div_int` and a finite output driver resistance (`R_O`) to model front-end bandwidth roll-off and `50 fF` load slewing:
  ```spectre
  ahdl_include "../../va/va_div_int.va"
  subckt dut_divider CLK_IN CLK_OUT VDD VSS
      R_BW (CLK_IN CLK_F)   resistor  r=1k
      C_BW (CLK_F  VSS)     capacitor c=35f
      IDIV (CLK_F  CLK_RAW) va_div_int n_div=4 vdd=0.9 vth=0.45 td=25p tr=15p
      R_O  (CLK_RAW CLK_OUT) resistor r=150
  ends dut_divider
  ```
- **Transistor 9T TSPC $\div 4$ Divider (`common/models_generic_bsim4.scs`):** Cascade two 9-transistor positive-edge TSPC $\div 2$ cells (`D` tied directly to `QB`) followed by a two-stage CMOS output buffer (with realistic drain/source diffusion `ad/as/pd/ps` so high-speed stress cleanly exposes physical cycle slip / division collapse above `f_max`).
