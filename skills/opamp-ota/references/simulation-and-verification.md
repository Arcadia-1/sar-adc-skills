# OpAmp & OTA Spectre Verification Guide

## 1. Ready-to-Run Process-Independent Testbench Suites

- **Single-ended OpAmp / OTA** ([`../assets/tb/single_ended/`](../assets/tb/single_ended/README.md)):
  - `tb_ota_stb_ac.scs` — Closed-loop `stb` (`iprobe`) + DC operating point & power $\to$ $A_0$, $\text{UGF}$, $\text{PM}$, $\text{GM}$, $P_{\text{DC}}$, $\text{FoM}_S$.
  - `tb_ota_cmrr_psrr_noise.scs` — Three matched open-loop/closed-loop replicas in one AC + `noise` run $\to$ exact $\text{CMRR}(f)$, $\text{PSRR}^+(f)$, $\text{PSRR}^-(f)$, spot input-referred noise ($1\text{ kHz}$/$100\text{ kHz}$/$1\text{ MHz}$), and integrated RMS input-referred noise.
  - `tb_ota_slew_settle.scs` — Unity-gain large-signal rising/falling step transient $\to$ $\text{SR}^+$, $\text{SR}^-$, overshoot %, $0.1\%$ and $0.01\%$ settling time, $\text{FoM}_L$.
  - `analyze_ota.py` — Zero-dependency PSF ASCII analyzer (`stb`, `cmrr_psrr_noise`, `slew_settle`).
- **Fully Differential OTA + CMFB** ([`../assets/tb/fully_diff/`](../assets/tb/fully_diff/README.md)):
  - `tb_fd_ota_dm_cm_stb.scs` — Simultaneous DM + CM `stb` using a standalone reciprocal Tian balun (`diff_stb_probe` with native `iprobe`s `IPRB_DM` and `IPRB_CM` — zero `analogLib` dependency!).
  - `tb_fd_ota_slew_settle.scs` — Differential closed-loop step $\to$ $\text{SR}_{\text{diff}}$, $0.1\%$ / $0.01\%$ settling time, and `VOCM` disturbance.
  - `analyze_fd_ota.py` — Zero-dependency PSF ASCII analyzer (`dm_cm_stb`, `slew_settle`).

## 2. Common OpAmp/OTA Simulation Pitfalls

1. **Never break the DC feedback loop with a 1 H inductor / 1 F capacitor for AC open-loop tests when `stb` is available!** Large $L$/$C$ breaks distort loading impedance and miss bilateral feedback paths (like Miller $C_c$). Always use Spectre `stb` with `iprobe` (single-ended) or `diff_stb_probe` (fully differential).
2. **CMRR and PSRR must be measured with the exact same closed-loop DC operating point** (either in closed-loop unity gain where $V_{\text{out}}/V_{\text{cm}} \approx 1/\text{CMRR}$ and $V_{\text{out}}/V_{\text{dd}} \approx 1/\text{PSRR}$ for $f \ll \text{UGF}$, OR dividing exact open-loop $A_{\text{DM}}(f)$ by $A_{\text{CM}}(f)$ / $A_{\text{VDD}}(f)$ at identical DC bias!). Using closed-loop unity gain for `CMRR` and `PSRR` automatically locks the DC bias of high-gain ($> 80\text{ dB}$) opamps without railing!
   - Exact closed-loop unity-gain relationships (for $A_{\text{DM}}(s) \gg 1$):
     - Apply AC `1 V` in series with `VIP` (leaving `VIN = VOUT`): $V_{\text{out}}/V_{\text{in}} = \frac{A_{\text{DM}}}{1 + A_{\text{DM}}}$.
     - Apply AC `1 V` common-mode on **both** `VIP` and the `VOUT -> VIN` return (or open-loop bias-stabilized via a `1 GΩ` DC feedback + `1 F` AC shunt): exact $\text{CMRR}(f) = 20\log_{10}|A_{\text{DM}}(f) / A_{\text{CM}}(f)|$ and $\text{PSRR}(f) = 20\log_{10}|A_{\text{DM}}(f) / A_{\text{VDD}}(f)|$ valid across **ALL frequencies** (both below AND above UGF!).
   - `tb_ota_cmrr_psrr_noise.scs` uses **identical DC bias** (via `1 GΩ` DC servo + `1 F` AC ground on the feedback divider, i.e., `f_servo = 0.16 nHz`) across three matched DUT instances (`I_DM`, `I_CM`, `I_PS`) so `CMRR(f)` and `PSRR(f)` are exact from `1 Hz` to `10 GHz`!
3. **Check `region` / saturation margin across PVT:** In Spectre DC operating point (`dcOp`), verify every transistor stays in saturation (`region == 2` for BSIM4) with $V_{\text{ds}} - V_{\text{dsat}} \ge 50\text{ mV}$ across `ss`/`tt`/`ff`, temperature, and input/output swing corners.
4. **Input-referred noise:** In Spectre `noise (VOUT 0) noise iprobe=V_IN`, Spectre outputs BOTH `out` (output noise $[\text{V}/\sqrt{\text{Hz}}]$) and `in` (exact input-referred noise $[\text{V}/\sqrt{\text{Hz}}]$ = `out / |A_DM(f)|`!) automatically!
