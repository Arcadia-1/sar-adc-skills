# LDO Spectre Verification Guide

## 1. Ready-to-Run Process-Independent Testbench Suite (`assets/tb/`)

All 4 standalone Spectre testbenches plug in external `models_corner.scs` + `dut_subckt.scs` (`subckt dut_ldo VDD VREF VOUT FB_IN VSS`) and are parsed by [`../assets/tb/analyze_ldo.py`](../assets/tb/analyze_ldo.py):

1. **`tb_ldo_dc_reg_dropout.scs`** — Two DC sweeps in one run:
   - `dc_line`: sweeps `VDD` from `0.5*vref` to `1.5*vdd_in` at `iload_max` $\to$ extracts **Dropout Voltage $V_{\text{DO}}$** (where `VOUT` drops $2\%$ below nominal), **Line Regulation** $[\text{mV/V}]$, and **Quiescent Current $I_Q$** & current efficiency $\eta_I$.
   - `dc_load`: sweeps `ILOAD` from `iload_min` to `iload_max` at nominal `vdd_in` $\to$ extracts **Load Regulation** $[\text{mV/mA}]$.
2. **`tb_ldo_stb.scs`** — Inserts `IPRB (VOUT FB_IN) iprobe` for exact Spectre `stb` stability (`T0`, `UGF`, `PM`, `GM`). Always run at **both `iload_min` and `iload_max`** (plus `ss`/`tt`/`ff`, temperature, and `CLOAD`/`RESR` extremes)!
3. **`tb_ldo_psrr_zout_noise.scs`** — Two matched closed-loop replicas in one fast run:
   - Replica 1 (`ac` `mag=1` on `VDD` + `noise`): extracts **$\text{PSRR}(f)$** at DC, `100 kHz`, `1 MHz`, `100 MHz`, worst-case minimum, plus **integrated output RMS noise** (`10 Hz`–`100 MHz`).
   - Replica 2 (`ac` `1 A` current probe at `VOUT_Z`): extracts closed-loop output impedance **$|Z_{\text{out}}(f)|$** (DC, `1 MHz`, peak $|Z_{\text{out}}|$)!
4. **`tb_ldo_load_line_tran.scs`** — Sequential **Load-Step** (`iload_lo -> iload_hi -> iload_lo`) and **Line-Step** (`vdd_lo -> vdd_hi`) transient $\to$ undershoot, overshoot, line-step glitch, and $1\%$ recovery time.

## 2. Signoff Pass Criteria Checklist

| Metric | Typical Target | Corner to Watch |
|---|---|---|
| Phase Margin (`stb`) | $\ge 60^\circ$ nom, $\ge 45^\circ$ worst-case | **Lightest load $I_{\text{min}}$**, max $C_L$, `ss` / high-$T$ |
| Gain Margin (`stb`) | $\ge 10\text{ dB}$ | Heavy load $I_{\text{max}}$, `ff` / low-$T$ |
| Dropout $V_{\text{DO}}$ | $\le V_{\text{in,min}} - V_{\text{out}}$ | Heavy load $I_{\text{max}}$, `ss` / high-$T$ |
| Load/Line Regulation | $< 1\text{–}5\text{ mV/mA}$, $< 5\text{ mV/V}$ | `ss`, low `VDD` (pass device near triode) |
| Load-Step Undershoot | $< 5\%\text{–}10\%$ of $V_{\text{out}}$ (or $< 0.5\text{ LSB}$ for ADC ref) | Fastest edge `tr`, $I_{\text{min}} \to I_{\text{max}}$ |
