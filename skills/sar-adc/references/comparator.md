# Comparator Design & Verification Reference

Dynamic clocked comparators are the standard decision elements in SAR ADCs because they draw zero static current, deliver rail-to-rail outputs during evaluation, and achieve near-$kT/C$-limited noise energy efficiency. This reference covers the two dominant topologies (**StrongARM** and **Miyahara two-stage dynamic**), their speed/noise/offset/FoM trade-offs, polarity alignment with SAR logic, and the verified Spectre characterization workflow in [`../assets/tb/comparator/`](../assets/tb/comparator/README.md).

---

## 1. StrongARM Dynamic Comparator

The StrongARM combines a clocked integrating input pair and a stacked cross-coupled regenerative latch in a single dynamic branch, followed by output inverters (and a downstream latch to hold the result across reset).

### Core Topology

| Device | Type | Gate | Drain | Source | Role |
|---|---|---|---|---|---|
| M0 | NMOS | CLK | VS | VSS | Tail evaluation switch |
| M1 | NMOS | VINP | VN1 | VS | Positive input transistor |
| M2 | NMOS | VINN | VP1 | VS | Negative input transistor |
| M3 | NMOS | LP | LM | VN1 | NMOS cross-coupled latch (stacked on M1) |
| M4 | NMOS | LM | LP | VP1 | NMOS cross-coupled latch (stacked on M2) |
| M5 | PMOS | LP | LM | VDD | PMOS cross-coupled latch |
| M6 | PMOS | LM | LP | VDD | PMOS cross-coupled latch |
| M7–M10 | PMOS | CLK | VN1, VP1, LM, LP | VDD | Reset pull-up switches |
| M11 (optional) | PMOS | CLK | LP | LM | Equalizing reset switch between latch nodes |
| Output buffers | CMOS | LP, LM | DCMPP, DCMPN | VDD/VSS | Isolate latch nodes from heavy SAR logic load |

**Critical connection:** M3 source connects to VN1 and M4 source connects to VP1 (not VSS). During evaluation, current flows `VSS → M0 → M1/M2 → VN1/VP1 → M3/M4 → LM/LP`.

### Four Operating Phases

1. **Reset (`CLK = 0`):** M0 is off (no static current). Reset PMOS switches M7–M10 pull VN1, VP1, LP, and LM to VDD; optional M11 equalizes LP and LM to eliminate residual memory from the previous cycle. **Plain output inverters do not hold the previous decision** — during reset, both buffered outputs return to the same rail (`0` after 1 inverter stage, `VDD` after 2 stages). Downstream SAR latch cells or an SR latch must hold the decision across reset.
2. **Integration (`CLK` rises, early):** M0 turns on and M1/M2 discharge VN1 and VP1 with differential current proportional to $V_{\text{INP}} - V_{\text{INN}}$. If $V_{\text{INP}} > V_{\text{INN}}$, VN1 falls faster than VP1. LP and LM remain near VDD until VN1/VP1 drop by $\sim V_{\text{th,n}}$.
3. **Regeneration (Latch):** Once VN1 drops below $\text{VDD} - V_{\text{th,n}}$, M3 turns on first and pulls LM down; M6 turns on harder to keep LP high while M4 turns off. Positive feedback amplifies the differential latch voltage exponentially:
   $$\Delta V(t) = \Delta V_0 \exp(t / \tau), \qquad \tau = \frac{C_{\text{latch}}}{g_{m,\text{lat,n}} + g_{m,\text{lat,p}}}$$
   For $V_{\text{INP}} > V_{\text{INN}}$, LM falls to VSS while LP stays at VDD.
4. **Restore (`CLK` falls):** M0 turns off and reset switches restore VN1, VP1, LP, and LM to VDD. Reset strength must be high enough that residual differential voltage on LP/LM and VN1/VP1 decays well below 1 LSB before the next clock rising edge, or hysteresis (memory effect) will corrupt subsequent comparisons.

### Output Buffer Parity and SAR Logic Polarity

Buffer stage count directly determines output polarity during reset and evaluation:

| Topology | Latch reset state | Buffer stages | Output reset state | Output during decision ($V_{\text{INP}} > V_{\text{INN}}$) | Matches active-low SAR latch? |
|---|---|---|---|---|---|
| StrongARM | LP = LM = VDD | **2 stages** (even) | DCMPP = DCMPN = VDD | One output falls to VSS, other stays VDD | Yes |
| StrongARM | LP = LM = VDD | **1 stage** (odd) | DCMPP = DCMPN = VSS | One output rises to VDD, other stays VSS | No (requires active-high / PMOS-pass latch) |
| StrongARM | LP = LM = VDD | **0 stages** | LP = LM = VDD | One output falls to VSS | Avoid: heavy SAR load degrades $\tau$, noise, and kickback |
| Miyahara | OA = OB = VSS | **1 stage** (odd) | DCMPP = DCMPN = VDD | One output falls to VSS, other stays VDD | Yes |

Check sign mapping explicitly: in StrongARM with 2 inverter stages per rail, `LP` (stays VDD for $V_{\text{INP}} > V_{\text{INN}}$) buffered twice gives `VDD`, while `LM` (falls to VSS) buffered twice gives `VSS`. Wire `DCMPP` / `DCMPN` consistently with the SAR logic and CDAC switching polarity (see [`integration.md`](integration.md)).

---

## 2. Two-Stage Dynamic (Miyahara / Double-Tail) Comparator

When supply voltage is low, kickback must be minimized, or closed-loop async SAR speed is tight, a **two-stage dynamic comparator** separates integration and regeneration into two independently clocked stages:

- **Stage 1 (Dynamic Preamp):** NMOS input pair with clocked tail (driven by `CLK`) and PMOS reset devices pulling intermediate nodes `DiA`/`DiB` to VDD during `CLK = 0`. When `CLK` rises, `DiA`/`DiB` integrate downward with differential voltage proportional to $V_{\text{INP}} - V_{\text{INN}}$.
- **Stage 2 (Regenerative Latch):** Cross-coupled CMOS latch with a clocked PMOS tail driven by `CLKB` (generated locally by an inverter) and `DiA`/`DiB`-gated NMOS pull-down/reset switches that hold latch outputs `OA`/`OB` at VSS during reset and release them as `DiA`/`DiB` fall.
- **Output Stage:** Because `OA`/`OB` reset to VSS and one rises to VDD during evaluation, **a single output inverter stage** restores reset-high / active-low polarity (`DCMPP = DCMPN = VDD` during reset) — saving one inverter delay in the SAR loop compared to a 2-stage-buffered StrongARM.

### StrongARM vs. Miyahara Trade-Offs

| Dimension | StrongARM (2-stage buffer) | Miyahara 2-stage (1-stage buffer) |
|---|---|---|
| Headroom | 4 stacked devices (sensitive at low VDD) | 3 stacked devices per stage (better at low VDD) |
| Kickback to CDAC | Higher (full-swing latch couples through M3/M4 to input pair) | Lower (Stage 1 isolates latch regeneration from input) |
| Closed-loop SAR speed | Baseline | Often ~7–10% faster due to 1 fewer output inverter & decoupled latch sizing |
| Energy per comparison | Lower (~1× baseline) | Typically ~1.5–2× higher (two dynamic branches + `CLKB` inverter) |
| Noise–Energy FoM | Typically better (lower FoM1/FoM2 at nominal VDD) | Higher FoM1/FoM2 unless Stage 1 gain and Stage 2 energy are co-optimized |

---

## 3. Speed, Noise, Offset, and Figures of Merit

### Comparison Time

$$t_{\text{cmp}} = t_{\text{int}} + t_{\text{regen}} \approx t_{\text{int}} + \tau \ln\!\left(\frac{V_{\text{swing}}}{\Delta V_0}\right)$$

- **$t_{\text{int}}$** scales inversely with integration current and increases with `VN1`/`VP1` capacitance.
- **$t_{\text{regen}}$** scales with $\tau = C_{\text{latch}} / (g_{m,\text{lat,n}} + g_{m,\text{lat,p}})$ and grows logarithmically as differential input $|V_{\text{id}}|$ shrinks — so LSB decisions near zero residue dominate worst-case conversion time and metastability.
- **Closed-loop loading warning:** In an asynchronous SAR loop, `CMPCK` is driven by a finite-strength logic gate (`NOR2`). Aggressively upsizing the comparator tail and reset devices reduces standalone delay (tested with an ideal voltage pulse) but increases `CMPCK` gate capacitance; in the closed loop, the slower clock edge can easily wipe out the standalone gain and make the total SAR conversion *slower*. Always re-verify sizing inside the closed SAR loop.

### Input-Referred Noise

- **Thermal noise** during the integration phase dominates input-referred noise ($\sigma_n^2 \propto kT / C_{\text{int}}$ scaled by input-pair $g_m/I_D$ and latch noise referred back through pre-amplification gain).
- **Budget rule:** Keep comparator RMS noise $\sigma_n$ well below quantization noise $\Delta / \sqrt{12}$ (typically $\sigma_n \le 0.25\text{–}0.4\text{ LSB}$, depending on the total noise budget allocation alongside $kT/C$ noise).

### Offset & Offset Trimming

- **Systematic offset:** Caused by asymmetric routing capacitance, asymmetric reset paths, or unequal output loading on the two halves. Must be near zero pre-layout and minimized via symmetric layout.
- **Random (mismatch) offset:** Dominated by input-pair threshold mismatch ($\sigma_{V_{os}} \propto A_{Vt} / \sqrt{WL}$), with secondary latch mismatch attenuated by Stage-1/integration gain.
- **Offset in SAR ADCs:** Static comparator offset shifts the entire ADC transfer curve (DC offset) without degrading DNL/INL or ENOB, provided it does not clip full scale. When tight DC offset is required, add binary-weighted differential trim (e.g., cascoded parallel input-pair fingers or switchable capacitive load trim on `VN1`/`VP1`) with matched dummy devices on the opposite side so mid-code is balanced.

### Figures of Merit (Frequency-Independent)

Use energy per comparison $E_{\text{cmp}} = P_{\text{avg}} \cdot T_{\text{clk}}$ rather than raw power so FoM is independent of clock rate:

$$\text{FoM}_1 = \sigma_n^2 \cdot E_{\text{cmp}} \quad [\text{J}\cdot\text{V}^2], \qquad \text{scaled: } \sigma_n^2 \cdot E_{\text{cmp}} \cdot 10^{21} \quad [\text{mV}^2 \cdot \text{fJ}]$$

$$\text{FoM}_2 = \sigma_n^2 \cdot E_{\text{cmp}} \cdot t_{\text{cmp}} \quad [\text{J}\cdot\text{V}^2\cdot\text{s}], \qquad \text{scaled: } \sigma_n^2 \cdot E_{\text{cmp}} \cdot t_{\text{cmp}} \cdot 10^{30} \quad [\text{mV}^2 \cdot \text{fJ} \cdot \text{ns}]$$

Lower is better for both.

---

## 4. Relative Sizing Trade-Offs (StrongARM)

Use low-Vth / fast core transistors on the evaluation and regeneration critical path, with multi-finger layout for matched parasitics and low gate resistance.

| Lever | Effect on $\tau$ / Speed | Effect on $\sigma_n$ | Effect on Energy | Practical Caveat |
|---|---|---|---|---|
| ↑ Tail switch $W$ | Faster integration up to saturation | Slightly lower | ↑ | Beyond ~2× baseline, input pair limits current while `CMPCK` cap grows |
| ↑ Input pair $W$ | Mixed ($g_m$ ↑ vs. `VX` cap ↑) | Lower ($\sigma_n \downarrow$, $\sigma_{V_{os}} \downarrow$) | ↑ | Heavy post-layout wiring cap on `VX` and `TAIL` |
| ↑ NMOS latch $W$ | Nearly flat ($g_m$ and $C$ scale together) | Small | ↑ | Keep moderate; match layout tightly |
| ↑ PMOS latch $W$ | Faster $\tau$ up to self-loading limit | Small | ↑ | Primary lever for regeneration $\tau$ |
| ↑ Reset PMOS $W$ | Faster reset $t_{\text{rst}}$ | — | ↑ | Size to guarantee clean reset within $T_{\text{clk}}/2$ without overloading `CMPCK` |
| Output buffer ratio | ~2–3× taper between Stage 1 and Stage 2 | — | ↑ | Stage 1 small (keeps latch load light); Stage 2 drives SAR latch fan-out |

---

## 5. How to Verify a Dynamic Comparator

Ready-to-run, **100% process-independent Spectre testbenches** and a matching PSF ASCII analyzer live in [`../assets/tb/comparator/`](../assets/tb/comparator/README.md):

| Testbench | What it measures | Key settings |
|---|---|---|
| [`tb_cmp_pss_pnoise.scs`](../assets/tb/comparator/tb_cmp_pss_pnoise.scs) | **Primary benchmark (~3 s/corner):** `noise`, `t_cmp`, `t_rst`, regeneration `tau`, `power`, `energy`, `FoM1`, `FoM2` | Shooting `pss` (`harms=100`, `errpreset=conservative`, `autotstab=yes`) + sampled full-spectrum `pnoise` (`pm0 jitterevent` on latch nodes `[I0.LP I0.LM]` crossing `v_observe`) |
| [`tb_cmp_delay.scs`](../assets/tb/comparator/tb_cmp_delay.scs) | Delay vs. overdrive (`vidin = 100u, 1m, 10m`) and $E_{\text{cmp}}$ over steady cycles | Pure Spectre `tran` (`stop=6*tclk`, `errpreset=conservative`) |
| [`tb_cmp_trannoise.scs`](../assets/tb/comparator/tb_cmp_trannoise.scs) | Independent transient-noise cross-check via probit inversion $\sigma_n = V_{\text{id}} / \Phi^{-1}(P_1)$ | 300+ cycles, `noisefmax=100G`, `noisefmin=10M`, `noiseruns=1`, `save=selected` (`DCMPP DCMPN` only) |
| [`tb_cmp_offset.scs`](../assets/tb/comparator/tb_cmp_offset.scs) + [`cmp_bisect.va`](../assets/tb/comparator/cmp_bisect.va) | Binary-search input-referred offset (for MC mismatch) and memory/hysteresis (`vpre = ±100m`) | `mode=1`, 18 cycles ($\pm V_{\text{range}} / 2^{17}$ resolution) |

### Exact PSS + Sampled PNOISE Setup and Extraction

```spectre
pss pss fund=1/tclk harms=100 errpreset=conservative autotstab=yes annotate=status

pnoise pnoise start=0 stop=0.5/tclk pnoisemethod=fullspectrum \
    noisetype=sampled measurement=[pm0] annotate=status
pm0 jitterevent trigger=[I0.LP I0.LM] triggerthresh=v_observe \
    triggernum=1 triggerdir=rise target=[I0.LP I0.LM]
```

**Why each parameter matters:**
- **`harms=100`** (not `10`): clocked comparators have sharp digital transitions; too few harmonics corrupts the PSS waveform and noise folding accuracy.
- **`autotstab=yes`**: guarantees the periodic steady state settles cleanly before shooting starts.
- **`trigger=[I0.LP I0.LM]` / `target=[I0.LP I0.LM]`**: observe the **internal differential latch nodes** where $V_{\text{LP}} - V_{\text{LM}}$ rises past `v_observe` (e.g., `200 mV`, well below `VDD` so regeneration is not yet rail-saturated). Choose `vidin` small (typically `1 mV`).
- **Exact input-referred RMS noise formula:**
  $$\sigma_n = \frac{1}{A_{\text{eff}}} \sqrt{\int_0^{f_{\text{clk}}/2} S_{v,\text{out}}(f)\, df}, \qquad A_{\text{eff}} = \frac{V_{\text{observe}}}{V_{\text{id,in}}}$$
  where $S_{v,\text{out}}(f)$ is the `out` spectrum ($\text{V}/\sqrt{\text{Hz}}$) in `pnoiseMpm0.0.sample.pnoise` (or `getData("out" ?result "pnoise_sample_pm0")` in ADE/OCEAN).
- **Regeneration time constant $\tau$:** Measure $t_{\text{cross}}(V_{\text{LP}} - V_{\text{LM}}, 0.2718\text{ V}) - t_{\text{cross}}(V_{\text{LP}} - V_{\text{LM}}, 0.1\text{ V})$ (ratio $e^1 \approx 2.718$).
- **Cross-check once against `tb_cmp_trannoise.scs`:** A properly configured PSS+PNOISE run agrees closely with 300-cycle transient noise (within the $\sim\pm 8\%$ binomial error bar of 300 trials) while running ~10–20× faster.
- **ADE Maestro caveat:** In Cadence ADE Maestro, `autotstab`, `pm0 jitterevent`, and `tranNoise` are often ignored unless toggled in the GUI form. Always inspect the generated `input.scs` before trusting a Maestro noise run — or run the standalone decks in `assets/tb/comparator/` directly via Spectre.
