# Shared AMS Testbench Utilities (`common/`)

Shared, process-independent helper assets and universal device/statistical characterization decks used across all 7 skills in `ams-skills` (`skills/sar-adc/`, `skills/dac/`, `skills/pll/`, `skills/serdes/`, `skills/opamp-ota/`, `skills/ldo/`, `skills/bandgap/`):

- **`psf_utils.py`** — Zero-dependency Spectre PSF ASCII parser (real `tran`/`dc`/`noise`/`pss`/`pnoise` + complex `ac`/`stb`/`sp`), `extract_uniform_strobe`, threshold crossing interpolator, coherent single-tone FFT (`ENOB`/`SNDR`/`SNR`/`SFDR`/`THD`/`HD2`/`HD3`), coherent two-tone `IMD3`, endpoint `DNL`/`INL`, IEEE-1139 phase-noise-to-RMS-jitter integration, and SerDes signal-integrity helpers (`sbr_cursor_metrics`, `eye_diagram_metrics`, `mixed_mode_s_params`).
- **`models_generic_bsim4.scs`** (~1.6 KB) — Synthetic, foundry-free textbook Spectre BSIM4 model pair (`nch` / `pch`, `VDD = 1.0 V`) with thermal noise and overlap/junction capacitances enabled. Ideal for ultra-fast smoke verification when no PDK is attached.
- **`models_sky130_minimal.scs`** (~60 KB, **Apache-2.0**, upstream `google/skywater-pdk-libs-sky130_fd_pr`) — Minimal self-contained TT subset of silicon-calibrated **SkyWater 130 nm planar CMOS** BSIM4.5 models (`sky130_fd_pr__nfet_01v8` / `sky130_fd_pr__pfet_01v8`, aliases `sky130_nch` / `sky130_pch`, `VDD = 1.8 V`, 5 continuous `L`-bins `0.14–100 um`). Recommended for **SAR ADC, OpAmp/OTA, LDO, Bandgap, DAC**, and low/mid-speed mixed-signal verification.
- **`models_asap7_minimal.scs`** (~20 KB, **BSD-3-Clause**, upstream `The-OpenROAD-Project/asap7_pdk_r1p7`) — Minimal self-contained TT subset of **ASU ASAP7 7 nm FinFET** BSIM-CMG (`level=72`) models (`nmos_rvt`/`pmos_rvt` and `nmos_lvt`/`pmos_lvt`, `VDD = 0.7 V`, `L_min = 20 nm`, parameter `nfin`). Recommended for **10 Gb/s+ high-speed SerDes** (CML/CTLE/StrongARM/DFE) and advanced-node mixed-signal verification.
  - *Note:* All three bundled cards are open-source / foundry-free models for framework bring-up and education; replace `models_corner.scs` with your full foundry PDK for PVT, Monte Carlo, and production signoff.
- **[`tb/`](tb/README.md)** — Universal foundry-free Spectre X utility decks:
  - `tb_gmid_nmos_pmos.scs` + `analyze_gmid.py` — Simultaneous NMOS/PMOS $g_m/I_D$ lookup tables (`Id/W`, `gm*ro`, `fT`, `Vov`)
  - `tb_mc_offset_template.scs` + `analyze_mc.py` — Spectre `montecarlo` mismatch offset statistics (`mean`, `1σ`, `3σ`, parametric `yield`)
  - `tb_ring_process_mon.scs` + `analyze_ring_mon.py` — 5-stage CMOS ring-oscillator PVT speed & power monitor

## Running Standalone Decks with Spectre X

Prefer **Spectre X** (`+preset=cx` for golden signoff accuracy; `+preset=ax` for fast analog iteration; `+preset=mx` for large digital-heavy runs; `+postlpreset=cx|ax|mx` for post-layout RC optimization; `-preset_override` when netlist `reltol`/`errpreset` must be honored) over legacy `+aps`:

```bash
spectre +preset=cx +mt=2 -format psfascii -raw raw_cx +log sim.log <deck.scs>
```
