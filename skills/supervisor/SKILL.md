---
name: supervisor
description: >
  Process-independent Power-On Reset (POR), Programmable Brown-Out Reset (BOR),
  On-Chip Temperature Sensor, and Over-Temperature Shutdown (TSD) IC design guide
  and Spectre X verification toolkit. Covers nano-power V_th- and bandgap-referenced
  POR/BOR architectures, hysteresis sizing against PDN inrush chatter, cold-boot
  low-VDD spurious glitch clamping, multi-decade supply ramp-rate immunity,
  asymmetric RC brown-out deglitchers, 3-bit programmable BOR threshold ladders,
  BJT V_BE(T) Tsividis 2nd-order curvature vs. subthreshold CMOS V_GS/dV_GS sensors,
  ratiometric PTAT/BGR readout, 1-point & 2-point calibration, dynamic offset
  chopping & 1/f noise suppression, supply sensitivity (deg C/V), thermal noise
  resolution (mK_rms), and hysteretic TSD comparator sizing, paired with 2 Verilog-A
  behavioral models and 7 standalone Spectre X testbenches. Use for any POR, BOR,
  brown-out deglitcher, on-chip temperature sensor, or thermal shutdown design or
  Spectre verification task.
---

# Supervisor (POR / BOR & Temperature Sensor / TSD) Skill

A process-independent engineering guide, Verilog-A behavioral model library, and standalone **Spectre X** verification toolkit for nano-power Power-On Reset / Programmable Brown-Out Reset supervisors and precision On-Chip Temperature Sensors with Over-Temperature Shutdown.

## Read Order

- `references/por-bor-design.md`
  POR vs. BOR roles, $V_{th}$-referenced CMOS and bandgap-referenced programmable architectures, hysteresis sizing against PDN inrush chatter, cold-boot low-$V_{DD}$ glitch suppression, multi-decade ramp-rate release delay timers (`t_rst`), asymmetric RC brown-out deglitchers, and nano-power $I_q$ budgeting.
- `references/temperature-sensor-and-tsd.md`
  Substrate PNP BJT vs. subthreshold CMOS sensor physics, exact Tsividis 2nd-order $V_{BE}(T)$ curvature, ratiometric $\mu = \alpha\Delta V_{BE}/(V_{BE}+\alpha\Delta V_{BE})$ readout, uncalibrated vs. 1-point (`@ 27°C`) vs. 2-point trim budgets, dynamic offset chopping (`CHOP`), supply sensitivity ($^\circ\text{C/V}$), noise resolution ($\text{mK}_{\text{rms}}$), and hysteretic TSD comparator sizing.
- `references/simulation-and-verification.md`
  Complete 7-testbench Spectre X (`+preset=cx`) verification workflow, `dut_por_bor` & `dut_tsens` interface contracts, relative midpoint & rail-tracking pitfalls, native DC thermal hysteresis (`prevoppoint=yes`), fault-injection negative tests, and transistor-level cross-check benchmarks.

## Bundled Assets

### Spectre X Testbench Suites (`assets/tb/`)
Plug in external `models_corner.scs` + `dut_subckt.scs` (see `assets/tb/README.md`):
- `assets/tb/por_bor/` — 4 signoff decks: `tb_por_thresholds_hys.scs` (slow triangle ramp `V_POR+`/`V_POR-`/`V_hys`/low-VDD clamp/`I_q`), `tb_por_ramp_rates.scs` (3-decade `10 us` / `200 us` / `4 ms` ramp-rate `t_rst` stability), `tb_por_glitch_immunity.scs` (`0.5 us` / `1.5 us` / `5 us` / `15 us` negative `VDD` glitch immunity curve), `tb_bor_multi_level.scs` (3-bit programmable `code = 0..7` BOR sweep, `mV/LSB`, DNL/INL, monotonicity), and `analyze_por_bor.py`
- `assets/tb/temp_sensor/` — 3 signoff decks: `tb_tsens_linearity.scs` (`-40..125°C` `V_BE`/`V_PTAT`/`V_TEMP` raw, 1-pt & 2-pt curvature fit), `tb_tsens_psrr_noise.scs` (`VDD` sensitivity `deg C/V`, `1 Hz..100 kHz` integrated `mK_rms` noise & `CHOP=0` vs. `1` offset cancellation), `tb_tsens_thermal_alarm.scs` (native rising/falling DC thermal hysteresis `T_trip`/`T_release`/`T_hys`), and `analyze_temp_sensor.py`

### Verilog-A Behavioral Models (`assets/va/`)
- `assets/va/va_por_bor.va` — 4-pin nano-power POR/BOR model (`VDD, VTRIM, RSTB, VSS`) with 3-bit programmable threshold ladder (`0..7`), saddle-node-compensated continuous hysteresis, asymmetric RC brown-out deglitcher (`tau_glitch`), linear release delay timer (`t_rst`), low-$V_{DD}$ clamp (with `fault_low_vdd_glitch` switch), and `150 nA` quiescent current
- `assets/va/va_temp_sensor_tsd.va` — 7-pin ratiometric BJT temperature sensor + TSD model (`VDD, CHOP, VPTAT, VBE, VTEMP, TSD_OUT, VSS`) with live `$temperature` Tsividis curvature, dynamic chopping (`CHOP`) suppressing front-end `v_os` and `1/f` noise, finite supply sensitivity (`psrr_deg_per_v`), thermal noise, and hysteretic over-temperature shutdown (`135°C` trip / `120°C` release)

> **Related Power & Reference Skills:** For dedicated bandgap voltage references see [`skills/bandgap/`](../bandgap/SKILL.md); for LDO regulators see [`skills/ldo/`](../ldo/SKILL.md).
