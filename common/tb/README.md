# Universal Foundry-Free Analog Verification Utilities (`common/tb/`)

Process-independent Spectre X (`+preset=cx`) device-level and statistical characterization templates usable across all 7 skills in `ams-skills` (plug in your PDK `models_corner.scs`, or smoke-test out of the box with `../models_generic_bsim4.scs`).

| Deck | Analyzer | Purpose & Key Metrics |
|---|---|---|
| `tb_gmid_nmos_pmos.scs` | `analyze_gmid.py` | Simultaneous NMOS & PMOS $g_m/I_D$ characterization across `Vgs`: lookup tables at $g_m/I_D = 5, 10, 15, 20\;\text{V}^{-1}$ for `Id/W [uA/um]`, intrinsic gain `gm*ro`, `fT [GHz]`, and `Vov` |
| `tb_mc_offset_template.scs` | `analyze_mc.py` | Reusable Spectre `montecarlo` mismatch template (`numruns=100`, `variations=mismatch`, `savefamilyplots=yes`): extracts `mean`, `1-sigma`, `3-sigma`, `min/max`, and parametric `yield_pct` |
| `tb_pvt_mc_wrapper_template.scs` | `analyze_op_region.py`, `analyze_mc.py` | Wrapper pattern for signoff runs: nested `sweep vdd { sweep temp { ... } }` (one netlist per corner), `info what=oppoint` per point audited by `analyze_op_region.py` (flags off/triode/breakdown and $|V_{ds}|-|V_{dsat}|$ below a margin), and Monte Carlo split into reproducible batches with `seed` + `firstrun` (pooled by `analyze_mc.py dir1 dir2 ...`) |
| `tb_ring_process_mon.scs` | `analyze_ring_mon.py` | 5-stage CMOS ring-oscillator PVT speed monitor: extracts `f_osc_ghz`, per-stage gate delay `t_pd_ps`, and dynamic `power_mw` across corners |
