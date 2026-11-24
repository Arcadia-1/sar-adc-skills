# Power-On Reset (POR) & Brown-Out Reset (BOR) Supervisor Design Guide

A first-principles, process-independent design reference for nano-power Power-On Reset (POR) and programmable Brown-Out Reset (BOR) supervisory circuits in analog and mixed-signal SoCs.

## 1. Functional Role: POR vs. BOR

Supervisory reset circuits protect digital logic, SRAM arrays, OTP/eFuse controllers, and analog state machines whenever the supply rail $V_{DD}$ is below the guaranteed operating minimum $V_{DD,\min}$:

| Requirement | Power-On Reset (POR) | Programmable Brown-Out Reset (BOR) |
|---|---|---|
| **Primary mission** | Guarantee deterministic cold-boot reset (`RSTB = 0`) from $V_{DD} = 0\text{ V}$ until supply, clocks, and bias settle | Monitor regulated/battery $V_{DD}$ during operation; assert reset cleanly before SRAM/logic retention fails |
| **Threshold accuracy** | Relaxed ($\pm 5\text{–}15\%$), often $V_{th}$-referenced | Tight ($\pm 1.5\text{–}3\%$), bandgap-referenced with multi-bit threshold trim (`VTRIM`) |
| **Threshold programmability** | Fixed single level | Multi-level (e.g., 3-bit code `0..7`, $50\text{ mV/LSB}$ step) matched to operating frequency / DVFS voltage bins |
| **Quiescent current ($I_q$)** | Ultra-low ($20\text{–}200\text{ nA}$, always-on domain) | Nano-power ($100\text{ nA}\text{–}2\,\mu\text{A}$ depending on continuous vs. duty-cycled reference) |
| **Critical hazards** | Cold-boot low-$V_{DD}$ spurious pulse (`RSTB` glitching high when $V_{DD} < V_{th,n}$), ultra-slow ramp failure | Supply-impedance chatter without hysteresis, false resets on short inductive load spikes (insufficient deglitching) |

```text
  VDD
   ^          ___________________
   |         /                   \
   |--------/------- V_POR+ ------\-----------  (Rising release threshold)
   |-------/-------- V_POR- -------\----------  (Falling assert threshold)
   |      /|<-- t_rst -->|          \
   |_____/                           \________
   +------------------------------------------> t

  RSTB
   ^                    ____________
   |                   |            |
   |  (clamped <50mV)  |  Released  |  Asserted on brown-out
   |___________________|            |_________
   +------------------------------------------> t
```

## 2. Core Architectures

### 2.1 Why Naive RC + Inverter POR Fails
A passive RC delay tied to $V_{DD}$ feeding a CMOS inverter or Schmitt trigger only works for fast, monotonic ramps ($\tau_{RC} \gg t_{\text{ramp}}$). Under a slow battery or energy-harvester ramp ($t_{\text{ramp}} = 10\text{ ms}\text{–}10\text{ s}$), the capacitor tracks $V_{DD}$ directly, eliminating the delay and causing premature reset release—or complete failure to assert on a shallow brown-out dip. **Never use an unreferenced RC-only POR for industrial SoCs.**

### 2.2 $V_{th}$-Referenced Nano-Power CMOS POR
For ultra-low-$I_q$ always-on domains without a running bandgap, a classic all-CMOS architecture compares $V_{DD}$ against a MOSFET $V_{th}$ clamp:
1. **Diode-clamp reference**: A megaohm resistor $R_{\text{ref}}$ (or stacked long-channel subthreshold PMOS current limit) biases a diode-connected NMOS $M_{\text{ref}}$, clamping $V_{\text{ref}} \approx V_{th,n}$ once $V_{DD} > V_{th,n}$.
2. **Threshold detector**: A PMOS detector $M_{P,\text{det}}$ with source at $V_{DD}$ and gate at $V_{\text{ref}}$ turns on strongly once:
   $$V_{SG} = V_{DD} - V_{\text{ref}} \gtrsim |V_{th,p}| \implies V_{\text{POR}+} \approx V_{th,n} + |V_{th,p}| + V_{\text{ov}}$$
   Using a resistive divider on $V_{\text{ref}}$ or low-$V_{th}$ / native devices tunes $V_{\text{POR}+}$ to the desired supply corner (e.g., $1.05\text{ V}$ for a $1.8\text{ V}$ rail or $0.65\text{ V}$ for a $1.0\text{ V}$ core rail).
3. **Regenerative hysteresis**: A feedback NMOS $M_{N,\text{hys}}$ gated by $\overline{\text{RSTB}}$ adds parallel pull-down conductance at the detector node while in reset, raising $V_{\text{POR}+}$ relative to $V_{\text{POR}-}$ by a clean, process-tracked $V_{\text{hys}} \approx 80\text{–}150\text{ mV}$.

### 2.3 Bandgap-Referenced Programmable BOR
When multiple voltage bins (e.g., $0.90\text{ V}..1.25\text{ V}$ in $50\text{ mV}$ steps) require $\pm 2\%$ accuracy across PVT:
- Compare a resistor-ladder tap $k(c)\cdot V_{DD}$ against a nano-power bandgap reference $V_{\text{BG}}$ (see [`skills/bandgap/`](../../bandgap/SKILL.md)):
  $$V_{\text{BOR}+}(c) = \frac{V_{\text{BG}}}{k_{\text{rise}}(c)}, \qquad k(c) = \frac{R_{\text{bot}}(c)}{R_{\text{top}}(c) + R_{\text{bot}}(c)}$$
- Implement hysteresis by switching an additional resistor segment $\Delta R_{\text{hys}}$ in the ladder via the comparator output (`RSTB`), making hysteresis ratiometric with $V_{\text{BG}}$:
  $$V_{\text{hys}} = V_{\text{BOR}+} - V_{\text{BOR}-} = V_{\text{BG}}\left(\frac{1}{k_{\text{rise}}} - \frac{1}{k_{\text{fall}}}\right)$$
- **Monotonicity & ladder sizing**: Use unit-resistor arrays with dummy end segments and common-centroid tap taps so $\text{DNL} \ll 0.5\text{ LSB}$ across all 3-bit codes (`0..7`). Keep total ladder resistance $R_{\text{tot}} = V_{DD,\text{nom}} / I_{\text{div}}$ high enough to stay within the nano-power budget (e.g., $R_{\text{tot}} \ge 20\text{ M}\Omega$ for $I_{\text{div}} \le 90\text{ nA}$ at $1.8\text{ V}$), or use switched-capacitor sampling if resistor area dominates.

## 3. Hysteresis Sizing & Chatter Prevention

When `RSTB` releases (`0 -> 1`), the SoC exits reset and draws a sudden wake-up inrush current $\Delta I_{\text{inrush}}$ through the power-delivery network impedance $R_{\text{PDN}}$ (package bondwire + regulator drop + PCB trace):
$$\Delta V_{\text{droop}} = \Delta I_{\text{inrush}} \cdot R_{\text{PDN}}$$
If $V_{\text{hys}} \le \Delta V_{\text{droop}} + V_{\text{rip,pp}} + 6\sigma_{V_{\text{os}}}$, releasing reset pulls $V_{DD}$ below $V_{\text{POR}-}$, re-asserting reset in an endless **POR chattering loop** ("motorboating").

**Design rule for minimum hysteresis:**
$$V_{\text{hys}} \ge \Delta I_{\text{inrush}} R_{\text{PDN}} + V_{\text{rip,pp}} + V_{\text{margin}} \quad (\text{typically } 60\text{–}150\text{ mV on a } 1.8\text{ V rail})$$
Simultaneously, ensure $V_{\text{POR}-}$ remains comfortably above the worst-case SRAM/flip-flop data-retention minimum $V_{\text{ret},\max}$ across all corners, while $V_{\text{POR}+}$ stays cleanly below the minimum valid operating supply $V_{DD,\min}$:
$$V_{\text{ret},\max} < V_{\text{POR}-} < V_{\text{POR}+} < V_{DD,\min}$$

## 4. Eliminating Cold-Boot Low-$V_{DD}$ Spurious Glitches

Between $V_{DD} = 0\text{ V}$ and $V_{DD} \approx V_{th,n}$ ($\sim 0.4\text{–}0.6\text{ V}$), standard enhancement-mode NMOS pull-down transistors are still in weak subthreshold inversion. Parasitic capacitive feedthrough ($C_{gd}$ of the output PMOS driver or ESD clamp coupling) during a fast supply ramp can momentarily pull `RSTB` upward to $200\text{–}400\text{ mV}$, potentially corrupting low-$V_{th}$ core flip-flops before the comparator wakes up.

**Proven low-$V_{DD}$ clamp techniques:**
1. **Passive resistive bleed clamp** ($R_{\text{clamp}}$ from `RSTB` to `VSS`): Guarantees `RSTB = 0 V` all the way down to $V_{DD} = 0\text{ V}$. Size $R_{\text{clamp}}$ large enough (e.g., $5\text{–}20\text{ M}\Omega$) so steady-state leakage when `RSTB = VDD` is $< 100\text{–}300\text{ nA}$, or gate it off via a feedback switch once `RSTB` releases.
2. **Native / zero-$V_{th}$ NMOS clamp**: A native NMOS pull-down with $V_{th} \approx 0\text{ V}$ conducts cleanly as soon as $V_{DD} > 50\text{ mV}$ and turns off once the internal comparator asserts high.
3. **Asymmetric inverter sizing**: Size the final output stage (`RSTB_N -> RSTB`) with a strong NMOS pull-down ($W_n/W_p \ge 2\text{–}4$) and small PMOS $C_{gd}$, ensuring `RSTB_N` tracks $V_{DD}$ early through a weak PMOS pre-pull-up.

## 5. Brown-Out Glitch Immunity & Asymmetric Deglitching

Digital switching bursts (e.g., RF PA turn-on, flash erase, or buck inductor transient) inject narrow negative $V_{DD}$ dips ($0.2\text{–}2\,\mu\text{s}$) that dip momentarily below $V_{\text{POR}-}$ without threatening logic state (decoupling capacitance holds core charge). Without deglitching, every short spike triggers a catastrophic system reboot.

- **Glitch Immunity Curve**: Every BOR has an amplitude-vs.-duration rejection boundary. Deeper drops discharge the internal filter faster; shallower drops near $V_{\text{POR}-}$ require longer persistence.
- **Asymmetric RC / Current-Starved Deglitcher**:
  - Place a falling-edge filter with time constant $\tau_{\text{glitch}}$ after the comparator: a sustained brown-out must pull the filter node below $0.5$ to qualify, yielding a minimum detectable pulse width:
    $$T_{\min,\text{detect}} \approx \tau_{\text{glitch}}\ln(2) \approx 0.693\,\tau_{\text{glitch}}$$
  - Example: $\tau_{\text{glitch}} = 3.5\,\mu\text{s} \implies T_{\min,\text{detect}} \approx 2.43\,\mu\text{s}$ cleanly rejects $0.5\,\mu\text{s}$ and $1.5\,\mu\text{s}$ spikes while deterministically tripping on $5\,\mu\text{s}$ and $15\,\mu\text{s}$ brown-outs.
  - Keep the **rising recovery time constant fast** ($\tau_{\text{rise}} \ll \tau_{\text{glitch}}$) so back-to-back rejected glitches do not integrate down into a false trip ("ratcheting"), while qualified brown-outs still pass through the full release delay timer $t_{\text{rst}}$.

## 6. Release Delay Timer ($t_{\text{rst}}$) & Ramp-Rate Independence

Once $V_{DD} > V_{\text{POR}+}$, `RSTB` must remain asserted for a guaranteed hold time $t_{\text{rst}}$ (typically $10\,\mu\text{s}\text{–}10\text{ ms}$) so the on-chip oscillator, bandgap, and LDO settle before CPU instruction fetch begins:
- **Constant-current capacitor ramp** (or digital counter clocked by a nano-power relaxation oscillator):
  $$t_{\text{rst}} = \frac{C_{\text{tmr}} \cdot V_{\text{th,tmr}}}{I_{\text{chg}}}$$
  Using $I_{\text{chg}} = 50\text{ nA}$, $C_{\text{tmr}} = 1\text{ pF}$, $V_{\text{th,tmr}} = 1.0\text{ V}$ yields $t_{\text{rst}} = 20\,\mu\text{s}$ with near-zero dependence on supply ramp speed across multiple decades ($10\,\mu\text{s}$ fast ramps through $4\text{ ms}$+ slow ramps).
- **Mandatory instant timer discharge**: Any qualified brown-out (even an aborted startup where $V_{DD}$ dips halfway through $t_{\text{rst}}$) must discharge $C_{\text{tmr}}$ in $< 100\text{ ns}$ through a strong reset NMOS switch so the full $t_{\text{rst}}$ hold period restarts cleanly upon recovery.

## 7. Nano-Power Quiescent Current & High-Temperature Leakage Audit

At $I_q \approx 100\text{–}200\text{ nA}$ at $27^\circ\text{C}$, subthreshold and reverse-junction leakage at $125^\circ\text{C}$ can easily dominate total standby current if devices are oversized:
- Use long-channel ($L \ge 3\text{–}5\,L_{\min}$) high-$V_{th}$ / I/O transistors for always-on bias branches and comparators.
- Budget $I_q$ across: (1) voltage reference / divider ($40\%$), (2) hysteretic comparator ($30\%$), (3) delay timer bias ($20\%$), and (4) output buffer & clamp leakage ($10\%$).
- Always verify $I_q$ on a **flat DC $V_{DD}$ plateau** (not during a voltage ramp, where $I = C_L \cdot dV_{DD}/dt$ masks true static current) and re-check at $125^\circ\text{C}$ FF corner.
