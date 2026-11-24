# Shared AMS Testbench Utilities (`common/`)

Shared, process-independent helper assets and universal device/statistical characterization decks used across all 7 skills in `ams-skills` (`skills/sar-adc/`, `skills/dac/`, `skills/pll/`, `skills/serdes/`, `skills/opamp-ota/`, `skills/ldo/`, `skills/bandgap/`):

- **`psf_utils.py`** — Zero-dependency Spectre PSF ASCII parser (real `tran`/`dc`/`noise`/`pss`/`pnoise` + complex `ac`/`stb`/`sp`), `extract_uniform_strobe`, threshold crossing interpolator, coherent single-tone FFT (`ENOB`/`SNDR`/`SNR`/`SFDR`/`THD`/`HD2`/`HD3`), coherent two-tone `IMD3`, endpoint `DNL`/`INL`, IEEE-1139 phase-noise-to-RMS-jitter integration, and SerDes signal-integrity helpers (`sbr_cursor_metrics`, `eye_diagram_metrics`, `mixed_mode_s_params`).
- **`models_generic_bsim4.scs`** — Synthetic, foundry-free textbook Spectre BSIM4 model pair (`nch` / `pch`) with thermal noise and overlap/junction capacitances enabled. Use strictly for out-of-the-box smoke verification when no PDK is attached; replace with your own `models_corner.scs` for real process signoff.
- **[`tb/`](tb/README.md)** — Universal foundry-free Spectre X utility decks:
  - `tb_gmid_nmos_pmos.scs` + `analyze_gmid.py` — Simultaneous NMOS/PMOS $g_m/I_D$ lookup tables (`Id/W`, `gm*ro`, `fT`, `Vov`)
  - `tb_mc_offset_template.scs` + `analyze_mc.py` — Spectre `montecarlo` mismatch offset statistics (`mean`, `1σ`, `3σ`, parametric `yield`)
  - `tb_ring_process_mon.scs` + `analyze_ring_mon.py` — 5-stage CMOS ring-oscillator PVT speed & power monitor

## Running Standalone Decks with Spectre X

Prefer **Spectre X** (`+preset=cx` for golden signoff accuracy; `+preset=ax` for fast analog iteration; `+preset=mx` for large digital-heavy runs; `+postlpreset=cx|ax|mx` for post-layout RC optimization; `-preset_override` when netlist `reltol`/`errpreset` must be honored) over legacy `+aps`:

```bash
spectre +preset=cx +mt=2 -format psfascii -raw raw_cx +log sim.log <deck.scs>
```
