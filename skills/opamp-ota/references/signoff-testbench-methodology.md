# Industrial OpAmp & OTA Signoff Testbench Methodology

A complete, process-independent characterization methodology for single-ended (SE) and fully differential (FD) operational amplifiers and transconductance amplifiers (OTAs). It bridges textbook open-loop Bode checks with tape-out-grade verification across **29 characterization items** (**36 numerical metrics + 2 stability pass/fail checks**) using **Spectre X (`+preset=cx`)**.

---

## 1. Complete Signoff Matrix (SE & FD Coverage)

An amplifier fits either the **single-ended** or **fully differential** interface contract; 7 core measurements have distinct SE and FD test circuits, so every design executes **22 applicable test items** (the complementary class's 7 items are `n/a`). Single-ended frequency, impedance, noise, and harmonic tests are equally applicable to fully differential amplifiers and are mirrored in `assets/tb/fully_diff/`.

| Category | Metric / Check | Single-Ended Deck & Mode | Fully Differential Deck & Mode |
|---|---|---|---|
| **DC & Bias** | Systematic $V_{\text{OS}}$, $I_{\text{DD}}$, $P_{\text{DC}}$, $V_{\text{OCM}}$ err | `tb_ota_dc_signoff.scs` (`dc_signoff`) | `tb_fd_ota_dc_signoff.scs` (`dc_signoff`) |
| **DC & Bias** | Offset tempco $\alpha_{V_{\text{OS}}}$ [µV/°C] & $V_{\text{OCM}}$ drift | `tb_ota_dc_signoff.scs` (`dc_temp`) | `tb_fd_ota_dc_signoff.scs` (`dc_temp`) |
| **DC & Bias** | ICMR (AC $-6\text{ dB}$, 4R bridge, follower, OP est.) | `tb_ota_dc_signoff.scs` (`dc_sweep`, `sweep_icmr_ac`) | `tb_fd_ota_dc_signoff.scs` (`dc_sweep`, `sweep_icmr_ac`) |
| **DC & Bias** | DC output swing $V_{\text{OPP}}$ vs. $R_L$ (`1M/100k/10k/1k`) | `tb_ota_dc_signoff.scs` (`dc_sweep`) | `tb_fd_ota_dc_signoff.scs` (`dc_sweep`) |
| **DC & Bias** | Rail overdrive phase-reversal check (`VIDR`) | `tb_ota_dc_signoff.scs` (`dc_sweep`) | `tb_fd_ota_dc_signoff.scs` (`dc_sweep`) |
| **AC & Loop** | Open-loop $A_0$, UGF, PM, GM (+ FD CMFB loop) | `tb_ota_stb_ac.scs` (`stb`) | `tb_fd_ota_dm_cm_stb.scs` (`dm_cm_stb`) |
| **AC & Loop** | Closed-loop $f_{-3\text{dB}}$, $f_{0.1\text{dB}}$, peaking, group delay | `tb_ota_cl_zout_gm.scs` (`cl_zout_gm`) | `tb_fd_ota_cl_zout_gm.scs` (`cl_zout_gm`) |
| **AC & Loop** | CMRR($f$) (+ 4R bridge comparison / FD CM→CM) | `tb_ota_cmrr_psrr_noise.scs` (`cmrr_psrr_noise`) | `tb_fd_ota_cmrr_psrr_noise.scs` (`cmrr_psrr_noise`) |
| **AC & Loop** | PSRR+($f$), PSRR−($f$) (SE DM; FD supply→CM & DM) | `tb_ota_cmrr_psrr_noise.scs` (`cmrr_psrr_noise`) | `tb_fd_ota_cmrr_psrr_noise.scs` (`cmrr_psrr_noise`) |
| **AC & Loop** | Closed-loop $Z_{\text{out}}(f)$, $Z_{\text{out,CM}}(f)$, $R_O$, $R_{\text{ID}}$, $C_{\text{ID}}$ | `tb_ota_cl_zout_gm.scs` (`cl_zout_gm`) | `tb_fd_ota_cl_zout_gm.scs` (`cl_zout_gm`) |
| **Noise** | Spot $v_{n,\text{in}}$, white floor, $1/f$ corner, RMS out/in, avg density | `tb_ota_cmrr_psrr_noise.scs` (`cmrr_psrr_noise`) | `tb_fd_ota_cmrr_psrr_noise.scs` (`cmrr_psrr_noise`) |
| **OTA $g_m$** | DC $g_m$, 10%-linear $V_{\text{ID}}$, $g_m/I_{\text{DD}}$, $I_{\text{OPP}}$, $g_m(f)$ | `tb_ota_cl_zout_gm.scs` (`cl_zout_gm`) | `tb_fd_ota_cl_zout_gm.scs` (`cl_zout_gm`) |
| **Transient** | Slew rate ($\text{SR}^+$/$\text{SR}^-$), $0.1\%$/$0.01\%$ settling, $R_S$ overshoot | `tb_ota_slew_settle.scs` (`slew_settle`) | `tb_fd_ota_slew_settle.scs` (`slew_settle`) |
| **Transient** | Coherent THD, HD2, HD3, SFDR, TRAN swing & $\text{BW}_{\text{full}}$ | `tb_ota_thd_fpbw.scs` (`thd_fpbw`) | `tb_fd_ota_thd_fpbw.scs` (`thd_fpbw`) |
| **Limits** | Operating $V_{\text{DD}}$ & $T_A$ range sweeps | `tb_ota_dc_signoff.scs` (`dc_vdd`, `dc_temp`) | `tb_fd_ota_dc_signoff.scs` (`dc_vdd`, `dc_temp`) |
| **Integrity** | Power-up / power-down ramp stability (`5 ms`, `10 ms`) | `tb_ota_power_ramp.scs` (`power_ramp`) | `tb_fd_ota_power_ramp.scs` (`power_ramp`) |
| **Integrity** | Supply surge ringing (`±50 mV`, `100k/300k/1M`) & CM step | `tb_ota_supply_surge_cmstep.scs` (`supply_surge_cmstep`) | `tb_fd_ota_supply_surge_cmstep.scs` (`supply_surge_cmstep`) |
| **Statistical** | Mismatch random offset $\sigma_{V_{\text{OS}}}$ (Monte Carlo) | [`common/tb/tb_mc_offset_template.scs`](../../../common/tb/tb_mc_offset_template.scs) | [`common/tb/tb_mc_offset_template.scs`](../../../common/tb/tb_mc_offset_template.scs) |

---

## 2. Critical Engineering Pitfalls & How the Testbenches Solve Them

### 2.1 Loop Stability (`stb`) vs. Ultra-Low-Frequency DC Servo
- **Always use Spectre `stb` (`iprobe` or Tian `diff_stb_probe`) for loop gain, PM, and GM.** Breaking a feedback loop with a giant $L$/$C$ distorts loading impedance and misses bilateral feedback through Miller $C_c$.
- **Use a DC-only servo ($1\text{ G}\Omega + 1\text{ F} \Rightarrow f_{\text{servo}} = 0.16\text{ nHz}$) for open-loop transfer metrics** (`CMRR`, `PSRR`, `R_O`, `Z_in`, `g_m(f)`, and AC-definition `ICMR`). For `f >= 1 Hz`, the servo is strictly open-loop while pinning the DC operating point of even $>100\text{ dB}$ amplifiers without railing.
- **Level-shifted DC servo for ICMR decoupling:** Directly tying `VOUT -> VIN` via `1 GΩ` pins `VOUT = VCM_in`, which conflates input common-mode limits with output rail saturation. Inserting a unity-gain error amplifier `E_srv (N_srv Vcm_in VOUT Vcm_mid)` forces `VOUT = Vcm_mid` (mid-rail) while `VIP = VIN = Vcm_in` sweeps across `0..VDD`, measuring pure **input** common-mode range.

### 2.2 Four-Resistor CMRR Bridge Artifact on High-$R_{\text{out}}$ OTAs
A textbook 4-resistor unity-gain difference bridge ($R_1 = R_2 = R_3 = R_4 = R$) estimates $\text{CMRR} \approx 1 / |V_{\text{out}}/V_{\text{cm}}|$. However, when the DUT has high output resistance $R_{\text{out}}$ (such as a single-stage folded-cascode or telescopic OTA driving $R = 100\text{ k}\Omega$), the feedback resistor loads the output and caps the bridge reading near:
$$\text{CMRR}_{\text{4R,max}} \approx g_m R \quad \text{(if } R_{\text{out}} \gg R\text{)}$$
For example, a single-stage OTA with true $\text{CMRR} = 95\text{ dB}$ can read only $40\text{ dB}$ on a $100\text{ k}\Omega$ bridge. `tb_ota_cmrr_psrr_noise.scs` instantiates **both** the exact matched-replica DC-servo $A_{\text{DM}}/A_{\text{CM}}$ path **and** a 5th 4-resistor bridge replica (`VOUT_CM4R`) so designers can inspect true CMRR alongside the resistor-loaded bridge behavior.

### 2.3 Multi-Definition ICMR Reconciliation
Different specs define ICMR differently, and the numbers can differ by $>200\text{ mV}$ on the same circuit:
1. **AC $-6\text{ dB}$ definition (`icmr_ac_6db_v`)**: Range of $V_{\text{CM}}$ where open-loop $A_{\text{DM}}(V_{\text{CM}})$ and $\text{CMRR}(V_{\text{CM}})$ stay within $6\text{ dB}$ of mid-rail (strictest pure-input metric; output held at mid-rail).
2. **Closed-loop 4R bridge (`icmr_bridge_4r_v`) / FD CM hold (`icmr_cl_hold_v`)**: Range where the closed-loop CM error stays bounded.
3. **Follower tracking (`icmr_follower_v`)**: $|V_{\text{out}} - V_{\text{in}} - V_{\text{OS}}| \le 10\text{ mV}$ — bounded by $\min(\text{ICMR}, \text{output swing})$.
4. **Operating-point analytical check**: For an NMOS input pair with tail current source, $\text{ICMR}_{\min} \approx V_{GS,\text{in}} + V_{DSAT,\text{tail}}$ and $\text{ICMR}_{\max} \approx V_{D,\text{in}} + V_{TH,\text{in}}$.
5. **Common-mode step transient (`tb_*_supply_surge_cmstep.scs`)**: Checks dynamic slewing/recovery of the tail node and CMFB loop under a fast $0.2\text{ V}$ CM step.

### 2.4 Output Swing vs. Load Resistance & Rail Overdrive (`VIDR`)
- **Decouple input ICMR from output swing:** Use inverting gain $-2$ (SE) or $-4$ (FD) so the inputs stay near mid-rail while the outputs drive rail-to-rail. Define DC linear swing $V_{\text{OPP}}$ as the span where $|dV_{\text{out}}/dV_{\text{in}}| \ge 0.9 |G_0|$.
- **Sweep $R_L$ across decades (`1M / 100k / 10k / 1k`):** Single-stage OTAs collapse quickly at $R_L = 10\text{ k}\Omega$ due to finite $I_{\text{tail}}$, whereas Class-A/AB multi-stage opamps maintain swing until their output stage saturates.
- **Grounded-$R_L$ & $\pm I_{\text{load}}$ PVT stress:** Returning $R_L$ to mid-rail draws zero quiescent output current; returning $R_L$ to `VSS` (or injecting $\pm I_{\text{load}}$ static DC current into `VOUT`) stresses asymmetric sourcing/sinking headroom across corners.
- **Phase-reversal check (`VIDR`):** Driving `VIP` all the way to `VDD` and `VSS` open-loop verifies the output never inverts polarity when the input pair or tail device leaves saturation.

### 2.5 Closed-Loop AC Flatness, Group Delay & Output Impedance
- **Peaking vs. Phase Margin:** A closed-loop amplifier with $\text{PM} > 70^\circ$ shows $\approx 0\text{ dB}$ magnitude peaking; peaking above $1\text{ dB}$ signals insufficient margin or high-frequency pole interaction (including CMFB interaction in FD circuits).
- **Group Delay:** $\tau_g(f) = -\frac{1}{2\pi}\frac{d\phi}{df}$ is flat across the passband ($\tau_g \approx 1/(2\pi f_{-3\text{dB}})$ for a single-pole rolloff) and degrades sharply near gain peaking.
- **Inductive $Z_{\text{out}}(f)$ Peaking & CMFB $Z_{\text{out,CM}}(f)$:** At DC, negative feedback reduces closed-loop output impedance to $R_O / (1 + T_0)$, but as loop gain $T(j\omega)$ rolls off at $-20\text{ dB/dec}$, $Z_{\text{out}}(f)$ rises inductively and peaks near UGF before $C_L$ rolls it down. For FD amplifiers, measure **both** differential $Z_{\text{out,DM}}(f)$ and common-mode $Z_{\text{out,CM}}(f)$ (governed by the CMFB loop!).

### 2.6 OTA Transconductance: Short-Circuit Sense vs. Loaded Sense
Measuring true transconductance $g_m(f) = I_{\text{out}}(f) / V_{\text{id}}(f)$ requires holding `VOUT` at AC ground through a low-impedance current-sense resistor (`r_gm = 10 Ω` $\ll R_O$) with a high-gain DC servo (`gain = 1e4` so loop gain $10^4 g_m r_{\text{gm}} \gg 1$ nulls DC offset current even for low-$g_m$ single-stage OTAs). Measuring $|V_{\text{out}}|/R_L$ with the real $R_L \parallel C_L$ load mixes in output voltage division $R_O \parallel R_L$ and the output pole $1/(2\pi (R_O \parallel R_L) C_L)$. Both `tb_ota_cl_zout_gm.scs` and `tb_fd_ota_cl_zout_gm.scs` simulate both side by side.

### 2.7 Fully Differential Symmetry Pitfalls
In a perfectly symmetric FD transistor netlist:
- Systematic differential $V_{\text{OS}} \equiv 0$, $\text{CMRR}_{\text{DM}} > 200\text{ dB}$, $\text{PSRR}_{\text{DM}} > 200\text{ dB}$, and even-order harmonic $\text{HD2} < -200\text{ dBc}$.
- **Always add three explicit checks for FD signoff:**
  1. **Common-mode transfer metrics:** Measure **input-CM to output-CM gain** $A_{\text{cm,cm}}$ and **supply-to-output-CM PSRR** (`VDD→CM`, `VSS→CM`), which remain strictly finite even with perfect symmetry.
  2. **Deterministic skew + Monte Carlo:** Inject a $1\%$ input-pair $W$ skew (or `v_os_dm` parameter) to verify deterministic offset sensitivity, and run `common/tb/tb_mc_offset_template.scs` (100+ mismatch draws) for $\sigma_{V_{\text{OS}}}$ and mismatch-limited $\text{CMRR}_{\text{DM}}$.
  3. **Practical MC scoping:** Run full mismatch Monte Carlo on offset and small-signal CMRR/gain/UGF; large-signal FD capacitive step settling is dominated by PVT corners and bias current rather than local mismatch (and random offset conflicts with fixed `.ic` initial conditions unless an auto-zero reset phase is added).

### 2.8 Coherent THD, Full-Power Bandwidth & Source-Impedance Overshoot
- **Coherent strobing:** Choose odd `m_bin` coprime with `n_fft` (`m_bin=3, n_fft=1024`), discard `n_settle` initial cycles via `strobedelay`, and run `strobeoutput=strobeonly`.
- **Spectre X precision override:** Spectre X (`+preset=cx`) manages internal solver tolerances automatically; for ultra-low distortion (`THD < -90 dB`), pass `-preset_override` alongside `+preset=cx` so Spectre honors `reltol=1e-6` and tight `maxstep`.
- **Follower vs. Inverting THD:** Running both in `tb_ota_thd_fpbw.scs` separates input-stage common-mode nonlinearity (visible only in the follower) from output-stage distortion (dominant in the inverting configuration).
- **Transient swing & $\text{BW}_{\text{full}}$:** Sweep `v_amp` at $1\text{ kHz}$ until $\text{THD} = 1\%$ ($-40\text{ dB}$) for transient dynamic swing; fix full swing and sweep `f_in` until $\text{THD} = 1\%$ for full-power bandwidth $\text{BW}_{\text{full}}$ (typically slew-rate limited: $\text{BW}_{\text{full}} \approx \text{SR} / (\pi V_{\text{OPP}})$).
- **Source-impedance overshoot:** Re-run `tb_ota_slew_settle.scs` with a small step (`100 mV`) and `r_src=10k` to expose high-frequency phase-margin degradation caused by $R_S C_{\text{in}}$ input pole loading.

### 2.9 Power-Up/Down Ramps & Supply Surge Stability
- **Keep slow and fast integrity tests in separate decks:** Power-up/down ramps span milliseconds (`5 ms` and `10 ms` edges), whereas supply-surge square waves switch in nanoseconds (`±50 mV`, `10 ns` edges at `100 kHz / 300 kHz / 1 MHz`). Separating `tb_*_power_ramp.scs` and `tb_*_supply_surge_cmstep.scs` keeps every Spectre X run fast and tightly controlled.
- **Track `VCM = 0.5*VDD` during ramps:** Driving `VIP` or `VOCM` from a fixed `0.45 V` source while `VDD = 0 V` forward-biases ESD/substrate junctions and causes fake startup failures; use `vcvs gain=0.5` from `VDD` so references scale cleanly with the rail.

---

## 3. Running the Signoff Suite with Spectre X

```bash
# Single-ended example (Spectre X conservative preset)
spectre +preset=cx +mt=2 -format psfascii tb_ota_dc_signoff.scs
python3 analyze_ota.py dc_signoff tb_ota_dc_signoff.raw --vdd 0.9 --vcm 0.45

# Ultra-low-distortion coherent THD (override preset reltol floor)
spectre +preset=cx -preset_override +mt=2 -format psfascii tb_ota_thd_fpbw.scs
python3 analyze_ota.py thd_fpbw tb_ota_thd_fpbw.raw --m-bin 3 --f-in 10e3

# Fully differential example
spectre +preset=cx +mt=2 -format psfascii tb_fd_ota_cl_zout_gm.scs
python3 analyze_fd_ota.py cl_zout_gm tb_fd_ota_cl_zout_gm.raw --r-gm 10 --rload 1e6
```
