# Process-Independent PFD + Charge Pump Testbench Suite (Spectre)

Standalone, PDK-agnostic Spectre testbenches for characterizing tri-state PFD + charge-pump linearity, dead-zone behavior, DC output compliance headroom, and UP/DN current matching.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_pfd_cp_transfer.scs` | Beat-sweep transient (`t(FDIV) - t(FREF)` across `[-2 ns, +2 ns]`) at fixed `vctrl_dc` | `i_up_ua`, `i_dn_ua`, `mismatch_pct`, `kd_ua_per_rad`, `q_at_zero_fc`, `dead_zone_free` |
| `tb_cp_compliance_mismatch.scs` | Dual DC sweep (`dc_up` & `dc_dn` via `alter`, `V_CP = 0 .. VDD`) on isolated `dut_cp` | `i_up_mid_ua`, `i_dn_mid_ua`, `mismatch_max/mean_pct` in `[v_comp_lo, v_comp_hi]`, `ro_up/dn_kohm`, 10%-drop `[v_comp_min_eff, v_comp_max_eff]` |
| `analyze_pfd_cp.py` | Standalone PSF ASCII analyzer (`transfer` and `compliance` modes; legacy bare `<psf_dir>` aliases `transfer`) | JSON summary |

## DUT Interface Contracts

Provide `models_corner.scs` (your PDK or repo-root `common/models_generic_bsim4.scs`) and `dut_subckt.scs`:

### Combined PFD + CP (`tb_pfd_cp_transfer.scs`)
```spectre
subckt dut_pfd_cp FREF FDIV IOUT VDD VSS
    // instantiate your transistor PFD + CP (or wrap ../../va/va_pfd.va + ../../va/va_cp.va)
ends dut_pfd_cp
```

### Isolated Charge Pump (`tb_cp_compliance_mismatch.scs`)
```spectre
subckt dut_cp UP DN IOUT VDD VSS
    // instantiate your transistor cascode CP (e.g., matched wide-swing BSIM4 cascode)
    // or wrap ../../va/va_cp.va for behavioral compliance closure
ends dut_cp
```
