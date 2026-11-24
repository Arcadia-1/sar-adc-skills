# AMS Skills Catalog & Directory Architecture

Every subdirectory under `skills/` is an **independently installable AI agent skill** following the standard `skills/<skill-name>/SKILL.md` discovery convention (compatible with Claude Code, Codex, Antigravity, and Cursor).

## Domain Taxonomy

| Domain | Skill | Scope | Sub-Suites / Key Coverage |
|---|---|---|---|
| **Data Converters** | [`sar-adc/`](sar-adc/SKILL.md) | Successive-Approximation Register ADC | `comparator`, `bootstrap`, `cdac`, `sar_logic`, `adc_top` (LDO power delivery delegates to `ldo/`) |
| **Data Converters** | [`dac/`](dac/SKILL.md) | Digital-to-Analog Converters | `current_steering` (static DNL/INL, coherent SFDR/IMD3, major-carry glitch/settle), `r2r` |
| **Clocking & RF** | [`pll/`](pll/SKILL.md) | Integer-N, Fractional-N ($\Delta\Sigma$), & ADPLL | `vco` (PSS+PNOISE, cap-bank overlap), `pfd_cp` (beat-sweep & compliance), `divider` (MMD & max-toggle), `tdc_dco`, `int_n_pll` (AC/lock/AFC band-cal/ref-spur/PSRR/noise+$N \times I_{\text{CP}}$), `frac_n_pll`, `adpll` (17 TB decks, 12 VA) |
| **Wireline / SerDes** | [`serdes/`](serdes/SKILL.md) | High-Speed NRZ/PAM4 Serial Links (10–56 Gb/s) | `channel` (`mtline`, `nport` `.s4p`, FEXT/NEXT), `tx_ffe`, `ctle_vga` (`P1dB`/`HD3`), `slicer_dfe` (`Clk-to-Q`/SH, `trannoise`), `sslms`, `tcoil` (`SCD21`), `cdr` (BBPD/PI/JTOL), `pam4` (RLM/DFE), `clocking_jitter` (DCD/IQ/bathtub), `link_top` (35 TB decks) |
| **Analog Core** | [`opamp-ota/`](opamp-ota/SKILL.md) | Single-Ended & Fully Differential OpAmp/OTA | `single_ended` & `fully_diff` (16 Spectre X signoff decks covering 29 items: `stb`/Tian DM+CM, CMRR/4R-bridge/PSRR±/noise, ICMR/swing-vs-$R_L$/VIDR, $Z_{\text{out,DM}}$/$Z_{\text{out,CM}}$/OTA $g_m$, slew/THD/$\text{BW}_{\text{full}}$, power-ramp & surge) |
| **Power & Reference** | [`ldo/`](ldo/SKILL.md) | PMOS-Pass, Capless (OCL), & NMOS-Pass LDO | DC reg/dropout, `iprobe` `stb`, PSRR/`|Zout|`/`noise`, load/line step transients |
| **Power & Reference** | [`bandgap/`](bandgap/SKILL.md) | Kuijk/Brokaw & Banba Sub-1 V Bandgap Reference | Temp/line sweeps (`TC [ppm/C]`), dead-state startup, `iprobe` core-loop `stb`, PSRR/noise |

## Canonical Skill Layout Contract

Every skill under `skills/<skill-name>/` follows the same predictable layout (enforced by [`../scripts/validate_repo.py`](../scripts/validate_repo.py)):

```text
skills/<skill-name>/
├── SKILL.md                             # YAML frontmatter + read order + asset map + scope
├── agents/
│   └── openai.yaml                      # UI display metadata & invocation policy
├── references/
│   ├── <topic>.md                       # First-principles theory, sizing equations, pitfalls
│   └── simulation-and-verification.md   # Spectre verification methodology (standardized name)
├── assets/
│   ├── va/                              # Process-independent Verilog-A behavioral models
│   └── tb/
│       ├── README.md                    # Mandatory testbench suite index & DUT contract
│       └── [<suite>/]                   # Multi-block/topology skills group into self-contained suites;
│                                        # single-DUT-contract skills (ldo, bandgap) place decks directly here
└── evals/
    └── evals.json                       # Sequential evaluation prompts grounded in skill files
```

### Shared Foundation & Zero-Duplication Rule
- All skills share [`../common/psf_utils.py`](../common/psf_utils.py) (zero-dependency PSF ASCII parser + FFT/IMD3/DNL/INL/jitter utilities) and [`../common/models_generic_bsim4.scs`](../common/models_generic_bsim4.scs).
- **Single source of truth per circuit block:** Reusable analog blocks (`opamp-ota`, `ldo`, `bandgap`, `dac`) live in their own top-level skills and are cross-referenced by system skills (`sar-adc`, `pll`) rather than duplicated.
- **100% process-independent:** No foundry names, PDK paths, proprietary device/cell names, or private tape-out identifiers are permitted anywhere in this repository.
