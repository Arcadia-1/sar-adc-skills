# Process-Independent PFD + Charge Pump Testbench (Spectre)

Standalone, PDK-agnostic beat-sweep testbench for characterizing tri-state PFD + charge-pump linearity, current matching, compliance, and dead-zone behavior in a single transient run.

## Files

- **`tb_pfd_cp_transfer.scs`** — Sweeps `t(FDIV) - t(FREF)` linearly across `[-2 ns, +2 ns]` while holding `IOUT` at fixed DC `vctrl_dc`.
- **`analyze_pfd_cp.py`** — Integrates per-cycle charge $Q_{\text{out}}(\Delta t)$ and reports `i_up_ua`, `i_dn_ua`, `mismatch_pct`, `kd_ua_per_rad`, `q_at_zero_fc`, and `dead_zone_free`.

## DUT Interface Contract

```spectre
subckt dut_pfd_cp FREF FDIV IOUT VDD VSS
    // instantiate your transistor PFD + CP (or wrap ../../va/va_pfd.va + ../../va/va_cp.va)
ends dut_pfd_cp
```
