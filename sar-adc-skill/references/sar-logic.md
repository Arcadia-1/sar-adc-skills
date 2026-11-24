# SAR Logic Design & Verification Reference

This reference covers synchronous and asynchronous SAR control logic, dynamic SRAM/16T latch-chain bit slices, global asynchronous clock/stop generation, DAC switch polarity, internal timing races, and verification checks.

---

## 1. Signal Interface & System Role

| Signal | Direction | Description |
|---|---|---|
| `CLKS` | Input | External sampling clock. High = sample & reset; falling edge starts conversion; rising edge ends conversion and latches output. |
| `DCMPP`, `DCMPN` | Input | Differential comparator outputs (active-low convention: both reset to `VDD` when `CMPCK = 0`; one drops to `VSS` on decision). |
| `CMPCK` | Output | Comparator clock — external (`CLKC`) in synchronous SAR, self-timed internally in asynchronous SAR. |
| `DOP<N-1:0>`, `DON<N-1:0>` | Output / Internal | Per-bit latched differential decisions driving the CDAC bottom-plate drivers (directly or via inverters/buffers). |
| `VBOTP`, `VBOTN` | Output | CDAC bottom-plate voltages driven to `VREFP` or `VREFN`. |
| `DOUT<N-1:0>` | Output | Retimed binary/redundant output code captured by output DFFs at the end of conversion. |

---

## 2. Synchronous vs. Asynchronous SAR Logic

| Aspect | Synchronous SAR | Asynchronous SAR |
|---|---|---|
| `CMPCK` source | External high-speed bit clock ($\ge (N+2) f_s$) | Internal self-timed feedback ring (`VALID_G → CMPCK`) |
| Bit time allocation | Fixed slot sized for worst-case metastable bit | Dynamically shared: large-residue bits finish fast, small-residue bits borrow slack |
| Power / clock distribution | High-frequency clock tree overhead | Only $f_s$ clock (`CLKS`) needed externally |
| Primary timing risk | Wasted margin on easy bits | Self-timed loop can outrun CDAC settling or trigger internal `VALID_L`/`EN` races |
| Typical hardware | Shift-register sequencer + bit registers | Domino dynamic latch chain (`logic_cell`) + global clock/stop logic |

### Full Conversion Cycle (Asynchronous)

1. **Sample & Reset (`CLKS = 1`):** `RSTP = 1`, `RSTN_G = 0`, `STOP = 1`, `CMPCK = 0`. All bit latches reset to their precharge state and CDAC bottom plates return to the sampling state.
2. **Conversion Start (`CLKS` falls):** `STOP` drops to `0` (`RSTP = 0`, `RSTN_G = 1`). Because the comparator is reset (`DCMPP = DCMPN = VDD` → `VALID_G = 0`), `CMPCK = NOR(VALID_G, STOP)` immediately rises to fire bit $N-1$ (MSB).
3. **Self-Timed Bit Loop (bits $N-1 \to 0$):**
   - Comparator evaluates → one of `DCMPP`/`DCMPN` falls to `VSS`.
   - Active bit slice latches the decision onto `DOP[k]`/`DON[k]`, updates its CDAC bottom-plate switch, asserts `VALID_L[k]`, and pulls `ENB_N[k]` low to arm bit $k-1$.
   - Globally, `VALID_G = NAND(DCMPP, DCMPN)` rises to `1` → `CMPCK = NOR(VALID_G, STOP)` falls to `0` → comparator resets (`DCMPP = DCMPN = VDD`).
   - Once comparator resets, `VALID_G` drops back to `0` → `CMPCK` rises again to fire bit $k-1$ (provided `STOP = 0`).
4. **End of Conversion (`ENB_N[0]` falls):** `VALID_LSB = !ENB_N[0]` goes high, immediately asserting `STOP = 1` to halt `CMPCK` cleanly after exactly $N$ pulses (no spurious $(N+1)$-th comparison). Final codes are captured into output DFFs (on `CLKS` rising or `STOP` rising, depending on whether the latch chain holds codes until `CLKS` or self-resets immediately).

---

## 3. Asynchronous Bit Slice: Dynamic SRAM + 16T Domino Latch

A widely used high-speed async bit slice combines a **dynamic cross-coupled SRAM latch** (zero static power, minimal clock-to-CDAC delay) with a compact **4-gate (16T) domino sequencer**:

### Per-Bit Circuit Roles

- **Precharge PMOS (`MPR_P`, `MPR_N`):** Controlled by `RSTN = !ENB_P`. While the previous bit has not finished (`ENB_P = 1`, `RSTN = 0`), both `DOP` and `DON` are precharged to `VDD`.
- **NMOS Pass Gates (`MNT_P`, `MNT_N`):** Controlled by `EN`. When enabled, they pass the active-low comparator outputs `DCMPP`/`DCMPN` directly to `DOP`/`DON` with only ~1 pass-transistor delay (no intervening logic gate on the critical CDAC path!).
- **Cross-Coupled Latch (`MPL_P/N`, `MNL_P/N`) with Series Foot Switches (`MNL_EN` gated by `VALID_L`, `MNL_RST` gated by `RSTN`):** Off during precharge; once one side of `DOP`/`DON` drops and `VALID_L` rises, the latch locks the state and holds it even after `EN` turns off and the comparator resets.
- **4-Gate Local Sequencer:**
  - `RSTN = INV(ENB_P)` — releases precharge when previous bit completes.
  - `VALID_L = NAND(DOP, DON)` — rises to `1` as soon as either `DOP` or `DON` is pulled low (current bit decided).
  - `EN = NOR3(ENB_P, VALID_G, VALID_L)` — pass gates open **only** when (1) previous bit finished (`ENB_P = 0`), (2) comparator is still in reset (`VALID_G = 0`, prevents capturing the *previous* bit's decision), and (3) current bit has not yet decided (`VALID_L = 0`).
  - `ENB_N = NAND(VALID_L, RSTN_G)` — falls to `0` to arm the next bit once `VALID_L = 1` (forced back to `1` during global reset `RSTN_G = 0`).

### Polarity Alignment Requirement

Because `DOP`/`DON` precharge to `VDD` and NMOS pass gates pull one node low, the comparator **must** present `DCMPP = DCMPN = VDD` during reset and pull one output low during evaluation (2 output inverters for StrongARM; 1 output inverter for Miyahara). Flipping comparator output polarity without flipping the entire SRAM cell (to NMOS pre-discharge + PMOS pass gates + NOR `VALID_L`) breaks both `VALID_G` and bit latching.

---

## 4. Global Asynchronous Clock & Stop Generation

### Recommended Global Clock Ring

```
VALID_G   = NAND2(DCMPP, DCMPN)            // 0 in reset, 1 when comparator decides
CMPCK     = NOR2(VALID_G, STOP)            // 1 to evaluate, 0 to reset or stop

VALID_LSB = INV(ENB_N<0>)                  // 1 when bit 0 finishes
SR Latch (NOR-type):  S = CLKS, R = VALID_LSB  →  Q = 1 during conversion, QN = 0
run       = NOR3(CLKS, QN, VALID_LSB)      // 3-input NOR kills CMPCK immediately on LSB!
STOP      = INV(run)                       // = CLKS | QN | VALID_LSB
RSTP      = INV(run)                       // separate buffer driving bit-(N-1) ENB_P and RSTN_G
RSTN_G    = INV(RSTP)
```

**Why the 3-input `NOR3(CLKS, QN, VALID_LSB)` matters:** Using only `NOR2(CLKS, QN)` introduces the SR-latch propagation delay between `VALID_LSB` rising and `STOP` asserting. In fast loops, `VALID_G` can clear first and launch an unwanted $(N+1)$-th comparator pulse before `STOP` arrives. Feeding `VALID_LSB` directly into `NOR3` cuts `VALID_LSB → STOP` latency roughly in half and guarantees **exactly $N$ comparator pulses** across `ss`/`tt`/`ff`.

*(Note: if `RSTP` is driven by `STOP`, the chain resets immediately after the LSB finishes, so capture `DOUT` on the `STOP` rising edge — or buffer `RSTP` directly from `CLKS` if you want `DOP`/`DON` held static until `CLKS` rises.)*

---

## 5. Critical Timing Constraints & Races

### Constraint 1 — CDAC Settling vs. Asynchronous Loop Delay

The time from bit-$k$ latch decision to the next comparator evaluation edge must exceed the CDAC settling time for bit $k$:

$$t_{\text{loop,next}} = t_{\text{cmp,rst}} + t_{\text{VALID\_G}\downarrow} + t_{\text{CMPCK}\uparrow} + t_{\text{delay\_buf}} > t_{\text{CDAC,settle}}$$

If the clock ring outruns the CDAC (especially on the MSB transition), the comparator evaluates an unsettled residue, causing missing codes or degraded ENOB. Add intentional delay buffers in the `VALID_G → CMPCK` path (or use sub-radix-2 redundancy) when CDAC settling is slower than the raw clock ring.

### Constraint 2 — Internal `VALID_L` vs. `EN` Race

When the comparator decides (`DCMP ↓`), two paths race to turn off `EN = NOR3(ENB_P, VALID_G, VALID_L)` in the active bit slice:

- **Path A (desired winner):** `DCMP ↓ → pass gate → DOP/DON ↓ → VALID_L ↑` (locks the latch and disables `EN`).
- **Path B (competing global path):** `DCMP ↓ → I_VG (NAND2) → VALID_G ↑ → EN ↓`.

If **Path B wins** (most likely at the `ff` corner or when post-layout parasitic capacitance slows down `DOP`/`DON`), `EN` shuts off before `DOP`/`DON` cross the `VALID_L` threshold — causing either a double-comparison retry (slowing conversion) or a mis-latched bit.

- **Key design lessons:**
  - Buffer `DOP`/`DON` with inverters before driving heavy CDAC switches so the internal dynamic latch nodes stay lightly loaded.
  - Do **not** blindly bypass `DCMP` by taking `CMPCK` directly from the comparator's first inverter (`NOR3(OPB, ONB, STOP)`) without checking this race — bypassing `DCMP` can shorten the clock loop faster than `logic_cell` can latch, driving `VALID_L`-vs-`EN` margin negative and corrupting codes!
  - Upsizing pass gates `MNT_P/N` alone gives diminishing returns because larger pass-gate capacitance simultaneously loads `EN` and `DCMP`. If margin is negative post-layout, add small controlled delay specifically on the `VALID_G → EN` branch rather than blindly widening pass gates.

### Constraint 3 — Clock Ring Drive Sizing

In high-speed async SARs (hundreds of MS/s to ~1 GS/s), `I_VG` (`VALID_G` NAND) drives all $N$ bit-slice `NOR3` gates plus `I_CK`, while `I_CK` (`CMPCK` NOR) directly drives the comparator tail and reset PMOS gate capacitance. Minimum-size (`X1`) gates here can burn **>50% of the per-bit loop delay**. Sizing `I_VG` (`X4`–`X8`) and `I_CK` (`X8`–`X12`) to match fan-out can cut total 8-bit conversion time by ~40% — verify both speed and `VALID_L`-vs-`EN` margin across `ss`, `tt`, and `ff`.

---

## 6. DAC Switch Polarity & Output Latching

### Complementary Pass-Gate DAC Switch

With a 2-transistor CMOS driver per bit (`PMOS` to `VREFP`, `NMOS` to `VREFN`, shared gate `DCTRL[i]`):
- `DCTRL[i] = LOW` → `VBOT[i] = VREFP` (initial/sample state)
- `DCTRL[i] = HIGH` → `VBOT[i] = VREFN` (bit set → `VTOP` decreases)

Because `DOP[k]` / `DON[k]` are active-low out of the dynamic latch (one falls to `0`, the other stays `1`), inserting an inverter stage between `DOP`/`DON` and `DCTRLP`/`DCTRLN` both **isolates the sensitive latch node** from DAC switch capacitance and produces clean active-high `DCTRL` signals (`0` during reset, `1` when selected). Verify sign/MSB polarity in simulation before wiring the full loop — a swapped comparator polarity on bit $N-1$ or an extra inversion on a single MSB buffer is one of the most common integration bugs.

### Output Retiming (DFF Array)

Capture the $N$ decided bits into a bank of standard-cell D flip-flops clocked by the end-of-conversion strobe (or `CLKS` rising edge if codes are held until sampling) so downstream digital blocks see clean, glitch-free `DOUT<N-1:0>` held for the entire next clock period.

---

## 7. Correspondence to Bundled Verilog-A Assets

The skill includes both 4-bit tutorial and 10-bit production behavioral models in [`../assets/va/`](../assets/va/):
- [`L2_logic_4b_sync.va`](../assets/va/L2_logic_4b_sync.va): 4-bit synchronous SAR state machine (`CLKS` + `CLKC`).
- [`L3_logic_4b_async.va`](../assets/va/L3_logic_4b_async.va): 4-bit asynchronous event-driven model mimicking comparator fire (`CMPCK = 1`), decision capture, comparator close (`CMPCK = 0`), reset detect, and step decrement.
- [`va_sar_logic_10b_async.va`](../assets/va/va_sar_logic_10b_async.va): 10-bit self-timed asynchronous SAR logic with `EOC` completion stop (zero spurious post-LSB `CMPCK` pulses), glitch-free latched `DOUT[9:0]`, and parameterized `t_start_delay` / `t_valid_to_rst` / `t_rst_to_cmp`.

Note that the behavioral models use active-high comparator outputs (`0` in reset, one rises to `VDD` on decision), whereas a 2-inverter StrongARM or 1-inverter Miyahara uses active-low outputs (`VDD` in reset, one falls to `0`). Align polarity explicitly when mixing behavioral and transistor-level blocks in Phase 3 hybrid verification.

---

## How to Verify SAR Logic

> **Ready-to-run process-independent Spectre testbench:** See [`../assets/tb/sar_logic/`](../assets/tb/sar_logic/README.md) (`tb_sar_logic_timing.scs`, `analyze_sar_logic.py`), which pairs your SAR logic DUT with [`va_cmp_dynamic.va`](../assets/va/va_cmp_dynamic.va) (logarithmic metastability delay) and [`va_cdac_10b_diff.va`](../assets/va/va_cdac_10b_diff.va) across 4 test frames including a `0.1 mV` near-metastable MSB stress.

### 1. Code & Pulse-Count Verification (Behavioral CDAC + Real Logic/Comparator)

- Connect transistor-level `sar_logic` + `comparator` to an ideal Verilog-A CDAC (`vcm = VDD/2`).
- Test several DC inputs spanning negative, near-zero (small residue / worst-case metastability), and positive full scale for at least 2–3 consecutive conversions each (verifying reset repeatability!).
- **Pass criteria:**
  - Output code matches ideal quantized code on every conversion.
  - **Exact pulse count:** `CMPCK` emits exactly $N$ pulses per conversion (neither $N-1$ nor $N+1$), and stays quiescent during `CLKS = 1`.
  - `RSTP` is a full-swing pulse (not a runt glitch).

### 2. Corner Timing & Race Margin Sweep

- Run across `ss`, `tt`, `ff` (plus temperature extremes and supply bounds, e.g., nominal `VDD` and any allowed slow-corner supply boost).
- Measure:
  1. Total conversion time $T_{\text{conv}}$ (`CLKS ↓` to `VALID_LSB ↑`) vs. conversion window $(1 - D_{\text{samp}}) / f_s$.
  2. Per-bit delay breakdown: comparator decision, comparator reset, `I_VG`, and `I_CK`.
  3. Internal race margin per bit: $t(\text{EN}\downarrow) - t(\text{VALID\_L}\uparrow)$ — must stay positive across all corners, especially `ff` and post-layout with extracted `DOP`/`DON` parasitics.

### 3. Dynamic ENOB Verification (Coherent Sine + Behavioral CDAC)

- Drive a coherent sine wave sampled at `CLKS` falling edge for $N_{\text{FFT}} = 256$ cycles (plus warmup) at the target $f_s$ and sampling duty cycle.
- Count undecided bits across all $N_{\text{FFT}} \times N$ bit trials — any undecided bits at `ss` indicate insufficient conversion window.
- Compute SNDR/ENOB (via `adctoolbox.analyze_spectrum`) and verify code latency (confirming conversion never spills into the next sampling phase, which can masquerade as a 1-sample phase shift in FFT!).
