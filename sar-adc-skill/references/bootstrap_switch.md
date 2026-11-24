# Bootstrap Switch Design & Verification Reference

The bootstrapped NMOS switch is the standard sampling front-end for high-linearity SAR ADCs (typically $\ge 10\text{ bits}$). A plain NMOS switch with a fixed gate drive `VDD` has on-resistance $R_{\text{on}} \propto 1/(V_{\text{DD}} - V_{\text{in}} - V_{\text{th}})$, which rises steeply as $V_{\text{in}}$ approaches $V_{\text{DD}}$ and limits sampling linearity to roughly 8 bits. By dynamically boosting the gate to $V_{\text{gate}} \approx V_{\text{in}} + V_{\text{DD}}$ during sampling, the bootstrap keeps $V_{\text{gs}} \approx V_{\text{DD}}$ constant across the full input swing and delivers nearly flat $R_{\text{on}}$.

---

## 1. Why Bootstrap Is Needed

| Topology | $R_{\text{on}}$ vs. $V_{\text{in}}$ | Typical Linearity Ceiling | Notes |
|---|---|---|---|
| Plain NMOS | Strong variation; opens near $V_{\text{DD}} - V_{\text{th}}$ | ~8 bit | Smallest cap, high signal-dependent THD |
| CMOS transmission gate | Partial cancellation | ~9–10 bit | Imperfect NMOS/PMOS match, ~2× switch cap |
| Bootstrapped NMOS | Nearly flat ($V_{\text{gs}} \approx V_{\text{DD}}$) | >12 bit | Standard for medium/high-resolution SAR ADCs |

Signal-dependent $R_{\text{on}}$ modulates the tracking time constant $\tau(V_{\text{in}}) = R_{\text{on}}(V_{\text{in}}) C_{\text{sample}}$, producing harmonic distortion that worsens rapidly with input amplitude and frequency.

---

## 2. Circuit Topology & Operating Phases

A classic bootstrapped sampling switch consists of a clock inverter (`CLKS → CLKSB`), a capacitive level-shifting charge pump (`CB` + switches), and the main sampling NMOS `MS` (commonly placed inside the CDAC block so the bootstrap outputs only the boosted gate node `VGBTS`).

### Device Roles

| Device | Type | Gate | Drain | Source | Role |
|---|---|---|---|---|---|
| `MS` | NMOS | `VGATE` | `VTOP` | `VIN` | Main sampling switch (constant $V_{\text{gs}} \approx V_{\text{DD}}$) |
| `CB` | MOM/MIM cap | — | `CB_TOP` | `CB_BOT` | Bootstrap capacitor storing $V_{\text{DD}}$ |
| `M1` | PMOS | `VGATE` | `CB_TOP` | `VDD` | Reset: pre-charges `CB_TOP` to `VDD` |
| `M2` | NMOS | `CLKSB` | `CB_BOT` | `VSS` | Reset: discharges `CB_BOT` to `VSS` |
| `M3` | NMOS | `VGATE` | `CB_BOT` | `VIN` | Sample: connects `CB_BOT` to `VIN` |
| `M4` | PMOS | `NET_G4` | `VGATE` | `CB_TOP` | Sample: passes boosted `CB_TOP` (`VIN + VDD`) to `VGATE` |
| `M4A` | NMOS | `VGATE` | `NET_G4` | `VIN` | Sample: holds `M4` gate at `VIN` (steady state) |
| `M4B` | PMOS | `CLKS` | `NET_G4` | `VDD` | Reset: pulls `M4` gate to `VDD` (keeps `M4` off) |
| `M4C` | NMOS | `CLKS` | `NET_G4` | `CB_BOT` | Startup: pulls `M4` gate low at `CLKS` rising edge |
| `M5` | NMOS | `CLKSB` | `NET_5A` | `VSS` | Reset: discharges `VGATE` to `VSS` |
| `M5A` | NMOS | `VDD` | `VGATE` | `NET_5A` | Cascode reliability shield protecting `M5` from `VIN + VDD` overvoltage |

### Operating Phases

- **Reset / Hold (`CLKS = 0`, `CLKSB = 1`):** `M1` and `M2` charge `CB` to $V_{\text{CB}} = V_{\text{DD}}$ (`CB_TOP = VDD`, `CB_BOT = VSS`). `M5` + cascode `M5A` pull `VGATE` to `VSS` so `MS` is off; `M4B` holds `M4` off.
- **Sampling / Track (`CLKS = 1`, `CLKSB = 0`):** `M4C` initiates turn-on of `M4`, connecting `CB_TOP` to `VGATE`; `M3` connects `CB_BOT` to `VIN`, lifting `CB_TOP` and `VGATE` to $V_{\text{in}} + V_{\text{DD}}$ by charge conservation, while `M4A` holds `M4`'s gate at `VIN` (keeping $|V_{\text{gs,M4}}| \approx V_{\text{DD}}$). `MS` sees constant $V_{\text{gs}} = V_{\text{gate}} - V_{\text{in}} \approx V_{\text{DD}}$.

---

## 3. Sizing Guidelines & Key Non-Idealities

### Bootstrap Capacitor `CB` and Voltage Droop

Parasitic capacitance $C_{\text{par}}$ at the boosted top node (`CB_TOP` + `VGATE` = gate of `MS`, `M3`, `M4A`, drains of `M1`/`M4`/`M5A`, and routing) forms a capacitive divider with `CB`:

$$V_{\text{gate}} \approx V_{\text{in}} + V_{\text{DD}} \cdot \frac{C_B}{C_B + C_{\text{par}}}$$

- **Sizing rule:** Choose **$C_B \ge 5\text{–}10 \times C_{\text{gg}}(\text{MS})$** (typically a dense MOM/MIM capacitor) so boost droop stays within a few percent of $V_{\text{DD}}$ and remains flat over $V_{\text{in}}$.

### Main Switch `MS` and Auxiliary Switches

- **Main sampling switch `MS`:** Size $W/L$ for $R_{\text{on}} C_{\text{sample}} \ll T_{\text{sample}} / 5$ (for $>10$-bit settling, allow $\ge (N+1)\ln 2 \approx 7\text{–}9$ time constants inside $T_{\text{sample}}$). Prefer a **standard-Vth** NMOS for `MS` so off-state leakage does not droop the floating CDAC top plate during conversion.
- **Bootstrap path devices (`M3`, `M4`, `M5A`, `M5`):** Size generously (~0.5–1× `MS` width; low-Vth where safe) so `VGATE` turns on and off crisply with fast turn-off edge (reducing signal-dependent charge-injection aperture error).
- **Reset / precharge devices (`M1`, `M2`, `M4B`, `M4C`):** Smaller standard-Vth devices (~0.25× `MS` width) suffice because they switch during the longer conversion/hold interval.
- **Reliability check:** Verify that **no device** exceeds its oxide voltage limit ($V_{\text{gs}}$, $V_{\text{gd}}$, $V_{\text{ds}} \lesssim 1.1\,V_{\text{DD}}$) during transients. Cascode `M5A` (gate at `VDD`) is mandatory so `M5` never sees $V_{\text{in}} + V_{\text{DD}}$.
- **Residual nonlinearity:** Even with perfect $V_{\text{gs}} = V_{\text{DD}}$, **body effect** ($V_{\text{sb}} = V_{\text{in}}$ raises $V_{\text{th}}$) and voltage-dependent drain junction capacitance on `MS` remain. Use a triple-well/isolated-body NMOS (tying body to `VIN` where the process permits) or differential cancellation when pushing beyond 12 bits at high $f_{\text{in}}$.

---

## 4. SAR ADC Integration Contract

A common integration mistake is treating the bootstrap as a voltage follower. In a SAR ADC, **the bootstrap outputs only a boosted gate voltage (`VGBTS`), not a sampled signal**:

```
VIP ──┬─────────────────────────────► CDAC_P.VIN   (direct to sampling NMOS source)
      └─► Bootstrap_P (CLKS) ─► VBTSP ─► CDAC_P.VGBTS (sampling NMOS gate)

VIN ──┬─────────────────────────────► CDAC_N.VIN   (direct to sampling NMOS source)
      └─► Bootstrap_N (CLKS) ─► VBTSN ─► CDAC_N.VGBTS (sampling NMOS gate)
```

Use two matched bootstrap instances (one per differential input channel) sharing `CLKS`, `VDD`, and `VSS`.

---

## How to Verify a Bootstrap Switch

### 1. Differential Sampling Linearity (THD / SFDR — Primary Gate)

Mirror the real SAR front end: drive two bootstrap instances with a coherent differential sine wave (`VIP = Vcm + A*sin(2*pi*Fin*t)`, `VIN = Vcm - A*sin(2*pi*Fin*t)`), connect `VGBTS` to matched NMOS switches `M0`/`M1` sampling onto load capacitors `CL` equal to the CDAC total capacitance (e.g., `CL = 200 fF`–`1 pF`), and clock `CLKS` at target $f_s$ (~20–25% high duty cycle).

- **Coherent setup:** e.g., $N = 128$ or $256$, near-Nyquist prime $M$ (such as $M = 61$ for $N = 128$, or $M = 127$ for $N = 256$).
- **Key saves:** `VINP VINN VSP VSN VGATEP VGATEN M0:vgs M0:gds`.
- **Analysis:** Sample `VSP - VSN` at a fixed instant in the hold phase (use `strobeoutput=strobeonly`) and run `adctoolbox.analyze_spectrum()`.
- **Pass criterion:** Differential THD comfortably below the target ADC noise floor (e.g., $\text{THD} < -70\text{ dB}$ for 10+ bits, $< -80\text{ dB}$ for 12+ bits) across 10–95% full scale and up to Nyquist $f_{\text{in}} \approx f_s/2$.

### 2. $R_{\text{on}}$ Flatness vs. $V_{\text{in}}$

- Hold `CLKS` active (or sample at a low rate with small probe current/voltage across `MS`) while sweeping $V_{\text{in}}$ from $0$ to $V_{\text{DD}}$ (or across the intended input swing).
- Extract $R_{\text{on}}(V_{\text{in}}) = V_{\text{ds}} / I_{\text{ds}}$ (or `1 / M0:gds`).
- **Pass criterion:** $R_{\text{on}}$ variation $< 10\%$ across the usable input range (compared to 2–5× for a plain NMOS). Rising $R_{\text{on}}$ near $V_{\text{DD}}$ points to undersized `CB`, excessive `CB_TOP` parasitic, or strong body effect.

### 3. Tracking Bandwidth & Settling

- Apply a full-scale step at the start of the sampling window and verify `VTOP` settles within $0.5\text{ LSB}$ before `CLKS` falls (with PVT margin, especially `ss` corner).

### 4. Gate Waveform & Oxide-Stress Audit

- Inspect `VGATE - VIN` during `CLKS = 1`: droop over the sampling window should be $< 2\%$ of $V_{\text{DD}}$, and `VGATE` should return cleanly to `~0 V` during hold.
- Check peak transient $|V_{\text{gs}}|$, $|V_{\text{gd}}|$, and $|V_{\text{ds}}|$ on every transistor in the bootstrap cell (especially `M1`, `M4`, `M5`, `M5A`, `MS`) across `ff` high-$V_{\text{DD}}$ corners to guarantee no oxide overstress.
