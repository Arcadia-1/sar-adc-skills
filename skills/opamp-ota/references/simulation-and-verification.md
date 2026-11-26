# OpAmp & OTA Spectre X Verification Guide

See [`signoff-testbench-methodology.md`](signoff-testbench-methodology.md) for the complete 29-item / 36-metric industrial signoff taxonomy, multi-definition ICMR reconciliation, 4-resistor CMRR bridge pitfalls, FD symmetry traps, and PVT/MC scoping.

## 1. Ready-to-Run Process-Independent Spectre X Testbench Suites

Run all decks with **Spectre X** (`spectre +preset=cx +mt=2 -format psfascii`; add `-preset_override` for `<-90 dB` coherent THD runs).

### Single-Ended Suite ([`../assets/tb/single_ended/`](../assets/tb/single_ended/README.md))
- `tb_ota_stb_ac.scs` — Closed-loop `stb` (`iprobe`) + DC operating point & power $\to$ $A_0$, $\text{UGF}$, $\text{PM}$, $\text{GM}$, $I_{\text{DD}}$, $P_{\text{DC}}$, $\text{FoM}_S$.
- `tb_ota_cmrr_psrr_noise.scs` — 5-replica AC + `noise` (`1 Hz..1 GHz`): 4 DC-servo replicas (`I_DM`, `I_CM`, `I_PP`, `I_PN`) + classic 4-resistor CMRR bridge (`I_CM4R`) $\to$ exact $\text{CMRR}(f)$, bridge $\text{CMRR}_{\text{4R}}$, $\text{PSRR}^+(f)$, $\text{PSRR}^-(f)$, spot & white noise floor, $1/f$ corner, integrated RMS output/input noise, and average noise density.
- `tb_ota_dc_signoff.scs` — Multi-analysis DC signoff: systematic $V_{\text{OS}}$, $\alpha_{V_{\text{OS}}}$ (`-55..150 °C`), follower/4R-bridge/AC-$-6\text{ dB}$ ICMR, inverting ($-2$) output swing across $R_L = 1\text{ M}/100\text{ k}/10\text{ k}/1\text{ k}\Omega$, rail-overdrive phase-reversal check (`VIDR`), and operating $V_{\text{DD}}$ range.
- `tb_ota_cl_zout_gm.scs` — Closed-loop AC ($f_{-3\text{dB}}$, $f_{0.1\text{dB}}$, peaking, group delay), closed-loop $Z_{\text{out}}(f)$, open-loop $R_O$, $R_{\text{ID}}$/$C_{\text{ID}}$, and OTA $g_m$, 10%-linear $V_{\text{ID}}$, $g_m/I_{\text{DD}}$, $I_{\text{OPP}}$, and $g_m(f)$ (short-circuit & real-load).
- `tb_ota_slew_settle.scs` — Unity-gain step transient (configurable `r_src` for source-impedance overshoot testing) $\to$ $\text{SR}^+$, $\text{SR}^-$, overshoot %, $0.1\%$ / $0.01\%$ settling time, $\text{FoM}_L$.
- `tb_ota_thd_fpbw.scs` — Coherently strobed sine wave (follower + inverting $-1$) $\to$ THD, HD2, HD3, SFDR, SNDR, transient dynamic swing & $\text{BW}_{\text{full}}$.
- `tb_ota_power_ramp.scs` — `5 ms` / `10 ms` linear power-up and power-down ramp stability with proportional `VCM = 0.5*VDD`.
- `tb_ota_supply_surge_cmstep.scs` — `±50 mV` (`10 ns` edge, `100k/300k/1M Hz`) supply-surge ringing and `0.2 V` input CM-step transient.
- `analyze_ota.py` — Zero-dependency PSF ASCII analyzer (`stb`, `cmrr_psrr_noise`, `slew_settle`, `dc_signoff`, `cl_zout_gm`, `thd_fpbw`, `power_ramp`, `supply_surge_cmstep`).

### Fully Differential Suite ([`../assets/tb/fully_diff/`](../assets/tb/fully_diff/README.md))
- `tb_fd_ota_dm_cm_stb.scs` — Simultaneous DM + CM `stb` using an inline lossless reciprocal Tian balun (`diff_stb_probe` with native `iprobe`s `IPRB_DM` and `IPRB_CM` — zero `analogLib` dependency).
- `tb_fd_ota_cmrr_psrr_noise.scs` — 4-replica FD AC + `noise`: open-loop DM reference & exact single-source differential input-referred noise, closed-loop CM→CM & CM→DM rejection, and VDD/VSS→CM & DM PSRR.
- `tb_fd_ota_dc_signoff.scs` — FD systematic $V_{\text{OS}}$ & $V_{\text{OCM}}$ error, temperature drift, closed-loop CM hold & AC $-6\text{ dB}$ ICMR, inverting ($-4$) differential & single-ended swing across $R_L = 1\text{ M}/100\text{ k}/10\text{ k}/1\text{ k}\Omega$, `VIDR` phase-reversal check, and operating $V_{\text{DD}}$ sweep.
- `tb_fd_ota_cl_zout_gm.scs` — Closed-loop ($-1$) AC & group delay, differential $Z_{\text{out,DM}}(f)$ & CMFB common-mode $Z_{\text{out,CM}}(f)$, open-loop $R_O$, $R_{\text{ID}}$/$C_{\text{ID}}$, and FD OTA $g_m$/$V_{\text{ID}}$/$I_{\text{OPP}}$/$g_m(f)$.
- `tb_fd_ota_slew_settle.scs` — Differential closed-loop step $\to$ $\text{SR}_{\text{diff}}$, $0.1\%$ / $0.01\%$ settling time, and `VOCM` disturbance.
- `tb_fd_ota_thd_fpbw.scs` — Coherently strobed differential sine wave $\to$ THD, HD2 (even-harmonic suppression), HD3, SFDR, SNDR, and $\text{BW}_{\text{full}}$.
- `tb_fd_ota_power_ramp.scs` — `5 ms` / `10 ms` FD power-up/down ramp stability checking both $V_{\text{OD}}$ and $V_{\text{OCM}}$.
- `tb_fd_ota_supply_surge_cmstep.scs` — `±50 mV` supply surge and `0.2 V` input CM step measuring both CMFB kick and differential glitch.
- `tb_fd_ota_sc_closed_loop.scs` — The OTA inside its switched-capacitor gain stage (`-cs/cf`, load `cl`), amplify phase, 3 replicas: DM + CM `stb` with the real $\beta$ and load, up/down step `tran` (settling to a band around the actual final value, dynamic error, static error $1/(1+T_0)$ kept separate), and output `noise` with noiseless $10\text{ M}\Omega$ summing-node DC paths and per-device shares.
- `tb_fd_ota_gain_swing.scs` — Resistive closed-loop DC sweep $\to$ local open-loop gain $A(V_{od})$ and the differential swing over which $A \ge (1-\varepsilon)/(\varepsilon\beta)$ ($199/\beta$ at $\varepsilon = 0.5\%$).
- `analyze_fd_ota.py` — Zero-dependency PSF ASCII analyzer (`dm_cm_stb`, `slew_settle`, `cmrr_psrr_noise`, `dc_signoff`, `cl_zout_gm`, `thd_fpbw`, `power_ramp`, `supply_surge_cmstep`, `sc_closed_loop`, `gain_swing`).

## 2. Quick Pitfall Checklist

1. **Use `stb` (`iprobe` / `diff_stb_probe`) for stability, DC servo (`1 GΩ + 1 F`) for open-loop rejection & noise.** Never break a feedback loop with $1\text{ H} / 1\text{ F}$ when measuring PM/GM.
2. **Decouple ICMR from output swing** via a level-shifted DC servo (in `tb_*_dc_signoff.scs`) and check `region == 2` with $V_{ds} - V_{dsat} \ge 50\text{ mV}$ across PVT corners.
3. **Never trust a 4-resistor CMRR bridge blindly on high-$R_{\text{out}}$ OTAs** — compare `cmrr_dc_db` against `cmrr_4r_dc_db`.
4. **Input-referred noise in FD setups:** Drive a single AC source `VSRC_DM` through `±0.5` `vcvs` splitters and set `iprobe=VSRC_DM` so Spectre's `in` trace equals exact differential input-referred noise without a $2\times$ factor error.
5. **Statistical mismatch offset:** Pair these deterministic signoff decks with [`../../../common/tb/tb_mc_offset_template.scs`](../../../common/tb/tb_mc_offset_template.scs) for 100-run Monte Carlo $\sigma_{V_{\text{OS}}}$.
6. **No 1 GΩ DC path in a noise run of a thin-oxide input pair.** Tens of pA of gate leakage drop tens of mV across 1 GΩ (the bias of the noise replica shifts) and add gate shot noise on a floating node. Use a noiseless (`isnoisy=no`) $10\text{ M}\Omega$ path, as `tb_fd_ota_sc_closed_loop.scs` does, and keep the 1 GΩ servo for AC rejection only.
7. **A `dc` inside `sweep { }` needs `restart=no`.** Otherwise each point restarts from scratch and a high-gain loop can land on another solution near $V_{od} = 0$, showing a false dip in gain or swing. Native `dc param=...` sweeps already continue from the previous point.
8. **Settling error against the actual final value.** Measure the dynamic error to the value the output really settles to, and report the static error $1/(1+T_0)$ separately; adding them gives a bound on the total error at a given time.
9. **PVT and saturation at every point.** Nest `sweep vdd { sweep temp { ... } }` in one netlist per corner, dump `info what=oppoint` per point, and audit all points with [`../../../common/tb/analyze_op_region.py`](../../../common/tb/analyze_op_region.py); split long Monte Carlo jobs into reproducible batches with `seed` + `firstrun` ([`../../../common/tb/tb_pvt_mc_wrapper_template.scs`](../../../common/tb/tb_pvt_mc_wrapper_template.scs)).
