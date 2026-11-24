# SerDes PAM4 Signaling & DFE Spectre X Testbench Suite

Process-independent Spectre X (`+preset=cx` / `+preset=ax`) decks and analyzer for 4-level Gray-coded PAM4 TX Ratio of Level Mismatch (IEEE 802.3 RLM), 3-eye (lower/middle/upper) opening, and closed-loop 3-threshold PAM4 slicer + 1-tap DFE bit/symbol-error verification.

## Files

| File | Analysis | Key Metrics |
|---|---|---|
| `tb_pam4_tx_rlm_eye.scs` | 10 Gbaud (`20 Gb/s`) Gray-coded PRBS-7 PAM4 TX into 100-ohm load | `levels_mv`, IEEE 802.3 `rlm` (`>= 0.95` pass), `inner_asym_mv`, lower/mid/upper eye heights & widths |
| `tb_pam4_dfe_ber.scs` | PAM4 TX -> lossy causal `mtline` channel -> 3-threshold slicer + 1-tap PAM4 DFE | `before_dfe_pam4` vs. `after_dfe_pam4` 3-eye opening, `symbol_errors`, Gray-decoded `bit_errors` |
| `tb_pam4_link_top.scs` | End-to-end 10 Gbaud (`20 Gb/s`) PAM4 `TX FFE -> 0.55 m Channel -> CTLE -> 1-Tap DFE` | Stage-by-stage `tx`/`ch`/`ctle`/`dfe` 3-eye heights/widths, `tx_rlm`, `symbol_errors`, Gray `bit_errors`, `link_pass` |
| `analyze_pam4.py` | Standalone PSF ASCII analyzer (`tx_rlm`, `dfe_ber`, `link_top`) | JSON summary |

## DUT Interface Contracts

```spectre
// 3-tap PAM4 TX driver (tb_pam4_tx_rlm_eye.scs, tb_pam4_dfe_ber.scs, tb_pam4_link_top.scs)
subckt dut_pam4_tx INP INN CLK VDD VSS OUTP OUTN
    // wrap ../../va/va_pam4_tx.va or your transistor PAM4 TX driver
ends dut_pam4_tx

// RX CTLE + VGA front end (tb_pam4_link_top.scs)
subckt dut_pam4_ctle INP INN VBOOST VOFF_CAL VDD VSS OUTP OUTN
    // wrap ../../va/va_ctle_vga.va or your transistor CTLE/VGA
ends dut_pam4_ctle

// 3-threshold PAM4 slicer + 1-tap DFE + Gray decoder (tb_pam4_dfe_ber.scs, tb_pam4_link_top.scs)
subckt dut_pam4_dfe INP INN CLK H1 VREF VDD VSS SUMP SUMN SYM_OUT MSB_OUT LSB_OUT
    // wrap ../../va/va_pam4_dfe_slicer.va or your transistor PAM4 DFE
ends dut_pam4_dfe
```
