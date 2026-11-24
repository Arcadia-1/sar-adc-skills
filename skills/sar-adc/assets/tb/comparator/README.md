# Process-Independent Dynamic Comparator Testbench Suite (Spectre)

A clean, PDK-agnostic Spectre testbench set for characterizing clocked dynamic comparators (StrongARM, Miyahara / double-tail, preamp + latch, etc.) directly from the command line or via `virtuoso-bridge-lite`'s `SpectreSimulator`.

## Files

| File | Purpose | Typical runtime / point |
|---|---|---|
| `tb_cmp_pss_pnoise.scs` | **Primary benchmark**: Shooting PSS + sampled full-spectrum PNOISE (`jitterevent`) → input-referred RMS noise, `t_cmp`, `t_rst`, regeneration `tau`, `power`, `energy`, `FoM1`, `FoM2` | ~2–4 s |
| `tb_cmp_delay.scs` | Multi-`vidin` transient sweep (e.g. `100u`, `1m`, `10m`) → decision delay, `E_cmp`, `P_at_fclk` | ~1–2 s |
| `tb_cmp_trannoise.scs` | Independent transient-noise cross-check (`N=300` cycles, probit fit of `DCMPN`/`DCMPP` counts) | ~15–40 s |
| `tb_cmp_offset.scs` + `cmp_bisect.va` | Binary-search offset (`vpre=0`, e.g. for Monte Carlo mismatch) and memory/hysteresis effect (`vpre=±100m`) | ~2–5 s |
| `run_cmp_tb.py` | Parallel runner & PSF ASCII analyzer matching Cadence ADE Maestro expressions | — |

## DUT Interface Contract

Supply two external files next to the staged testbench (never committed to a public repo if they reference a foundry PDK):

1. **`models_corner.scs`**: foundry or generic device model include + any PDK-specific global parameters for the target corner.
2. **`dut_subckt.scs`**: defines (or wraps) a 7-pin subcircuit named `dut_cmp`:
   ```spectre
   subckt dut_cmp CMPCK DCMPN DCMPP VDD VIN VIP VSS
       // instantiate or inline your comparator here
   ends dut_cmp
   ```
   **Polarity convention (for `VIP > VIN`, `vidin > 0`):**
   - `CMPCK = 0` resets the comparator (`DCMPP == DCMPN`).
   - `CMPCK ↑ VDD` triggers comparison; `DCMPP - DCMPN` rises from `0` to `+VDD`.
   - For `tb_cmp_pss_pnoise.scs`, point `I0.LP` / `I0.LM` to the internal differential latch nodes where `V(LP) - V(LM)` rises cleanly past `+v_observe` (e.g., `I0.OP` / `I0.ON` for StrongARM, `I0.OA` / `I0.OB` for Miyahara).

## Metric & FoM Definitions (Matching ADE Maestro)

- **Effective gain at latch crossing**: $A_{\text{eff}} = V_{\text{observe}} / V_{\text{id,in}}$ (choose $V_{\text{observe}}$ well below $V_{\text{DD}}$, typically `50m`–`200m`, and `vidin` small enough that regeneration is not yet saturated).
- **Input-referred RMS noise** (PSS + sampled PNOISE):
  $$\sigma_n = \frac{1}{A_{\text{eff}}} \sqrt{\int_0^{f_{\text{clk}}/2} S_{v,\text{out}}(f)\, df}$$
  from the `pnoise` `pm0` sampled spectrum (`pnoisemethod=fullspectrum`, `noisetype=sampled`, `trigger=[LP LM]`, `target=[LP LM]`, `triggerthresh=v_observe`, `triggerdir=rise`).
- **Decision delay**: `t_cmp = t_cross(DCMPP - DCMPN, VDD/2, rise) - t_cross(CMPCK, VDD/2, rise)` (and in `tb_cmp_delay.scs`, also `delay` via `DCMPP * DCMPN` falling across `VDD^2 / 2` on cycle 3).
- **Regeneration time constant**: $\tau = t_{\text{cross}}(V_{LP}-V_{LM}, 0.2718\text{ V}) - t_{\text{cross}}(V_{LP}-V_{LM}, 0.1\text{ V})$ (ratio $e^1$).
- **Energy per comparison**: $E_{\text{cmp}} = |I_{\text{avg}}(\text{VSUP:p})| \cdot V_{\text{DD}} \cdot T_{\text{clk}}$.
- **Figures of merit**:
  - $\text{FoM}_1 = \sigma_n^2 \cdot E_{\text{cmp}} \cdot 10^{21}$ (units: $\text{mV}^2 \cdot \text{fJ}$, lower is better)
  - $\text{FoM}_2 = \sigma_n^2 \cdot E_{\text{cmp}} \cdot t_{\text{cmp}} \cdot 10^{30}$ (units: $\text{mV}^2 \cdot \text{fJ} \cdot \text{ns}$, lower is better)

## Key Spectre / Maestro Gotchas Avoided

1. **No Verilog-A needed for DELAY / TRANNOISE / PSS+PNOISE**: using plain `vsource` avoids `*.ahdlSimDB` compile clutter and `ignore_hidden_state` surprises. `cmp_bisect.va` is only included by `tb_cmp_offset.scs`.
2. **Explicit `autotstab=yes` and `pm0 jitterevent`**: in ADE Maestro, these fields silently drop out of `input.scs` unless clicked in the GUI form; in standalone `.scs` they are explicit and reproducible.
3. **Explicit `save=selected` and `noiseruns=1`**: keeps PSF ASCII compact and avoids Maestro's `noiseruns=100` blowup on transient noise.
4. **Never pass `-param` on the Spectre CLI**: stage parameter edits directly in the `parameters` block of the `.scs` copy.
