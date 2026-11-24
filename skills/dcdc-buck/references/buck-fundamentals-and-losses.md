# Synchronous Buck Converter Fundamentals, Sizing & Loss Analysis

## 1. Topology and Steady-State Relations

A **synchronous step-down (Buck) DC-DC converter** steps an input rail $V_{\text{in}}$ down to a regulated output voltage $V_{\text{out}} < V_{\text{in}}$ by chop-modulating the switching node `SW` between $V_{\text{in}}$ (high-side switch `HS` ON, duration $D T_{\text{sw}}$) and `VSS` (synchronous low-side switch `LS` ON, duration $(1-D) T_{\text{sw}}$), followed by a second-order $LC$ low-pass output filter ($L, R_{\text{DCR}}, C_{\text{out}}, R_{\text{ESR}}$).

### Volt-Second Balance (CCM)
In **Continuous Conduction Mode (CCM)**, inductor current $i_L(t)$ remains strictly positive over the entire switching period $T_{\text{sw}} = 1/f_{\text{sw}}$. Enforcing zero net volt-seconds across $L$:

$$D_{\text{ideal}} = \frac{V_{\text{out}}}{V_{\text{in}}}$$

Including resistive conduction drops ($R_{\text{on,HS}}$, $R_{\text{on,LS}}$, inductor $R_{\text{DCR}}$) and dead-time body-diode drop $V_f$ over total dead-time $2 t_{\text{dead}}$ per cycle:

$$D_{\text{actual}} \approx \frac{V_{\text{out}} + I_{\text{load}}(R_{\text{DCR}} + R_{\text{on,LS}}) + 2 V_f t_{\text{dead}} f_{\text{sw}}}{V_{\text{in}} - I_{\text{load}}(R_{\text{on,HS}} - R_{\text{on,LS}})}$$

For a canonical reference point ($V_{\text{in}} = 3.3\text{ V}$, $V_{\text{out}} = 1.2\text{ V}$, $f_{\text{sw}} = 2\text{ MHz}$, $I_{\text{load}} = 300\text{ mA}$, $R_{\text{on,HS}} = 120\;\text{m}\Omega$, $R_{\text{on,LS}} = 90\;\text{m}\Omega$, $R_{\text{DCR}} = 80\;\text{m}\Omega$, $t_{\text{dead}} = 10\text{ ns}$), $D_{\text{ideal}} = 0.3636$ while $D_{\text{actual}} \approx 0.388$ — a key sanity check when comparing measured switching duty cycle against $V_{\text{out}}/V_{\text{in}}$.

---

## 2. Inductor Ripple, CCM/DCM Boundary & Output Filter Sizing

### Inductor Current Ripple
During the `LS` freewheeling interval $(1-D) T_{\text{sw}}$, the inductor discharges across $V_{\text{out}}$:

$$\Delta I_L = \frac{V_{\text{out}}(1 - D)}{L f_{\text{sw}}} = \frac{(V_{\text{in}} - V_{\text{out}}) D}{L f_{\text{sw}}}$$

Design rule of thumb: choose $L$ so the peak-to-peak ripple ratio $r = \Delta I_L / I_{\text{load,max}} \in [0.25, 0.40]$ (balancing transient slew speed against peak current stress and inductor core/AC copper losses). With $L = 2.2\;\mu\text{H}$ and $f_{\text{sw}} = 2\text{ MHz}$ at $3.3\text{ V} \to 1.2\text{ V}$, $\Delta I_L \approx 174\text{ mA}_{\text{pp}}$ ($35\%$ of $500\text{ mA}$ full load).

### CCM / DCM Boundary and Zero-Current Detection (ZCD)
Inductor current reaches zero at the critical boundary load current:

$$I_{\text{crit}} = \frac{\Delta I_L}{2} = \frac{V_{\text{out}}(1 - D)}{2 L f_{\text{sw}}}$$

- **Forced CCM (no ZCD):** Below $I_{\text{crit}}$, $i_L(t)$ reverses direction through the synchronous `LS` MOSFET, circulating reactive energy back from $C_{\text{out}}$ to `VSS` and collapsing light-load efficiency.
- **Discontinuous Conduction Mode (DCM with ZCD):** A zero-current detector senses $V(\text{SW}, \text{VSS})$ crossing zero from negative to positive during the `LS` interval and turns `LS` off, clamping $i_L = 0$ until the next cycle. In DCM, the required on-time shrinks with load as $D_1 = \sqrt{\frac{2 L f_{\text{sw}} I_{\text{load}} V_{\text{out}}}{V_{\text{in}}(V_{\text{in}} - V_{\text{out}})}}$, preventing negative circulating current and dramatically boosting light-load efficiency.
- **PFM / Pulse-Skipping:** At ultra-light loads ($< 1\text{–}5\%$ full load), reducing effective switching frequency further cuts $C_g V_{\text{in}}^2 f_{\text{sw}}$ gate-drive loss at the expense of higher, load-dependent output ripple spectrum.

### Output Voltage Ripple Decomposition
The triangular inductor ripple current splits across the output capacitor's capacitive reactance and its equivalent series resistance $R_{\text{ESR}}$:

$$\Delta V_C = \frac{\Delta I_L}{8 f_{\text{sw}} C_{\text{out}}}, \qquad \Delta V_{\text{ESR}} = \Delta I_L \cdot R_{\text{ESR}}$$

Because the capacitive triangle integral is $90^\circ$ out of phase with the ESR drop:
- When $\Delta V_{\text{ESR}} \gg \Delta V_C$: $\Delta V_{\text{out,pp}} \approx \Delta V_{\text{ESR}} + \frac{\Delta V_C^2}{2 \Delta V_{\text{ESR}}}$.
- When ceramic MLCCs with ultra-low $R_{\text{ESR}}$ are used ($\Delta V_C \gg \Delta V_{\text{ESR}}$): $\Delta V_{\text{out,pp}} \approx \Delta V_C$ (plus ESL spikes at switch transitions).

With $C_{\text{out}} = 10\;\mu\text{F}$ and $R_{\text{ESR}} = 15\;\text{m}\Omega$: $\Delta V_C \approx 1.09\text{ mV}$, $\Delta V_{\text{ESR}} \approx 2.61\text{ mV}$, giving $\Delta V_{\text{out,pp}} \approx 2.75\text{ mV}_{\text{pp}}$.

---

## 3. Complete Power-Loss Budget & Efficiency Optimization

Total Buck power loss decomposes into six physical mechanisms:

| Loss Mechanism | Analytical Expression (CCM) | Dominant Regime |
|---|---|---|
| **Switch Conduction** | $P_{\text{cond,sw}} = I_{L,\text{rms}}^2 \left[D R_{\text{on,HS}} + (1 - D) R_{\text{on,LS}}\right]$ | Heavy load ($\propto I_{\text{load}}^2$) |
| **Inductor DCR** | $P_{\text{DCR}} = I_{L,\text{rms}}^2 R_{\text{DCR}}$, where $I_{L,\text{rms}}^2 = I_{\text{load}}^2 + \frac{\Delta I_L^2}{12}$ | Heavy load ($\propto I_{\text{load}}^2$) |
| **Gate Drive** | $P_{\text{gate}} = (Q_{g,\text{HS}} + Q_{g,\text{LS}}) V_{\text{drv}} f_{\text{sw}} = (C_{g,\text{HS}} + C_{g,\text{LS}}) V_{\text{in}}^2 f_{\text{sw}}$ | Light / mid load (fixed $\propto f_{\text{sw}}$) |
| **Switching Crossover & $C_{\text{sw}}$** | $P_{\text{sw}} = \frac{1}{2} V_{\text{in}} (I_{L,\text{val}} t_{\text{rise}} + I_{L,\text{pk}} t_{\text{fall}}) f_{\text{sw}} + \frac{1}{2} C_{\text{sw}} V_{\text{in}}^2 f_{\text{sw}}$ | High $V_{\text{in}}$, high $f_{\text{sw}}$ |
| **Dead-Time Body Diode** | $P_{\text{dt}} = (I_{L,\text{pk}} + I_{L,\text{val}}) V_f t_{\text{dead}} f_{\text{sw}} = 2 I_{\text{load}} V_f t_{\text{dead}} f_{\text{sw}}$ | Long $t_{\text{dead}}$, high $f_{\text{sw}}$ |
| **Controller Quiescent** | $P_q = V_{\text{in}} I_q$ | Ultra-light load / standby |

### Optimal Power-FET Width Sizing
For a switch with width $W$, on-resistance scales as $R_{\text{on}} = R_{\text{on,0}} / W$ while gate capacitance scales as $C_g = C_{g,0} W$. Minimizing $P_{\text{cond}} + P_{\text{gate}}$ at target load $I_{\text{opt}}$ yields:

$$W_{\text{HS,opt}} = I_{\text{opt}} \sqrt{\frac{D \cdot R_{\text{on,HS0}}}{C_{g,\text{HS0}} V_{\text{in}}^2 f_{\text{sw}}}}, \qquad W_{\text{LS,opt}} = I_{\text{opt}} \sqrt{\frac{(1 - D) \cdot R_{\text{on,LS0}}}{C_{g,\text{LS0}} V_{\text{in}}^2 f_{\text{sw}}}}$$

Note the asymmetric ratio: at low duty cycles ($D < 0.5$, e.g. $3.3\text{ V} \to 1.2\text{ V}$ where $1-D \approx 0.64 > D \approx 0.36$), the low-side synchronous NMOS conducts for nearly twice as long as the high-side switch and naturally benefits from lower $R_{\text{on,LS}}$ (which NMOS mobility also favors).

---

## 4. Dead-Time Optimization, Shoot-Through & Switch-Node Stress

In a synchronous half-bridge, non-overlapping dead-time $t_{\text{dead}}$ between turning off one power FET and turning on the other faces a sharp two-sided optimum:

1. **Negative / Insufficient Dead-Time ($t_{\text{dead}} \le 0$ — Shoot-Through):**
   Both `HS` and `LS` conduct simultaneously, creating a low-impedance short across the input supply with cross-conduction peak current:
   $$I_{\text{shoot}} \approx \frac{V_{\text{in}}}{R_{\text{on,HS}} + R_{\text{on,LS}}}$$
   Even a $5\text{ ns}$ overlap at $2\text{ MHz}$ produces multi-ampere spikes ($3\text{–}10\text{ A}$), catastrophic efficiency collapse ($-20\%$ to $-30\%$), severe ground bounce, and electromigration/reliability hazards.
2. **Optimal Dead-Time ($t_{\text{dead}} \approx 5\text{–}15\text{ ns}$):**
   Long enough to guarantee zero overlap across PVT corners (including gate-driver skew and Miller plateau tail), yet short enough that body-diode conduction stays under $1\text{–}2\%$ of output power.
3. **Excessive Dead-Time ($t_{\text{dead}} \ge 40\text{–}60\text{ ns}$):**
   During *both* dead-time intervals in CCM (`HS` off $\to$ `LS` on, and `LS` off $\to$ `HS` on), positive inductor current forces `SW` down to $-V_f \approx -0.75\text{ V}$ through the `LS` body diode. At $f_{\text{sw}} = 2\text{ MHz}$ and $t_{\text{dead}} = 60\text{ ns}$, body-diode conduction occupies $24\%$ of the switching period, dropping efficiency by $> 10\%$ and injecting minority carriers (reverse-recovery loss $Q_{rr} V_{\text{in}} f_{\text{sw}}$) when `HS` turns back on.

### Switch-Node Ringing & Reliability
Parasitic input loop inductance $L_{\text{par}}$ (bondwires, package leads, input cap ESL) resonating with $C_{\text{sw}}$ at $f_{\text{ring}} = \frac{1}{2\pi\sqrt{L_{\text{par}} C_{\text{sw}}}}$ causes `SW` voltage overshoot above $V_{\text{in}}$ on the rising edge and undershoot below $-V_f$ on the falling edge. Keep the high-frequency input bypass capacitor tightly coupled to the `VIN`/`VSS` power pins and control `HS` turn-on slew via gate-driver resistance (`r_drv_hs`) to prevent oxide breakdown on `LS` and substrate minority-carrier injection below ground.
