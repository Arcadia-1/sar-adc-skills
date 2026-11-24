# VCO & DCO Design (LC vs. Ring)

## 1. Topology Comparison

| Metric | Cross-Coupled LC-VCO | CMOS Ring-VCO | LC / Ring DCO |
|---|---|---|---|
| Phase noise at 1 MHz offset | **Excellent** (high-$Q$ passive tank filters noise) | 15–30 dB worse for same power ($Q_{\text{eff}} \approx 1$) | Matches underlying LC or Ring core |
| Tuning range | Narrower (15–30% per band; widened with switched-cap banks) | Very wide (2×–10× continuous) | Segmented: PVT (coarse) + Acq (mid) + Track (fine) |
| Area | Large (on-chip spiral inductor) | **Tiny** (standard CMOS cells) | LC-DCO large; Ring-DCO tiny |
| Supply sensitivity ($K_{\text{VDD}}$) | Moderate (primarily via tail/varactor) | **High** (needs dedicated clean LDO!) | Controlled via tail/LDO isolation |
| Best fit | Low-jitter RF LO, SerDes, high-ENOB ADC clock | Area-constrained digital SoC, wide-range clock gen | ADPLLs (eliminates analog varactor noise sensitivity) |

---

## 2. LC-VCO Core Equations & Phase Noise

- **Oscillation frequency:** $f_0 = \frac{1}{2\pi \sqrt{L C_{\text{tot}}}}$.
- **Startup condition:** Effective negative transconductance of the cross-coupled pair must exceed tank parallel loss $G_p = \frac{1}{R_p} = \frac{1}{Q \omega_0 L}$ with margin:
  $$g_{m,\text{eff}} R_p \ge 2.5\text{–}3.5 \quad (\text{worst-case SS / high-}T \text{ corner})$$
- **Tank swing (current-limited regime):**
  - NMOS-only cross-coupled: $V_{\text{amp,diff}} \approx \frac{2}{\pi} I_{\text{tail}} R_p$ (can swing above $V_{\text{DD}}$!).
  - Complementary CMOS (NMOS + PMOS cross-coupled): $V_{\text{amp,diff}} \approx \frac{4}{\pi} I_{\text{tail}} R_p$ ($2\times$ current efficiency, lower $1/f^3$ corner when rise/fall symmetry is balanced, capped by $V_{\text{DD}}$ headroom).
- **Leeson / thermal $1/f^2$ phase noise:**
  $$\mathcal{L}(\Delta f) = 10\log_{10}\left[ \frac{2 F k T}{P_{\text{sig}}} \left(\frac{f_0}{2 Q \Delta f}\right)^2 \left(1 + \frac{\Delta f_{1/f^3}}{\Delta f}\right) \right] \quad [\text{dBc/Hz}]$$
  - Noise factor $F \approx 1 + \gamma$ (tail current noise at $2 f_0$ down-converts via hard switching — filter the tail node with a $2 f_0$ LC tail tank or large tail bypass cap!).
  - **Symmetry reduces $1/f^3$ up-conversion:** In Hajimiri's ISF theory, matching PMOS/NMOS rise and fall slopes minimizes the DC component $\Gamma_{\text{dc}}$ of the impulse sensitivity function, pushing the $1/f^3$ corner down by 5–10 dB.
- **Standard Figures of Merit:**
  $$\text{FoM} = -\mathcal{L}(\Delta f) + 20\log_{10}\left(\frac{f_0}{\Delta f}\right) - 10\log_{10}\left(\frac{P_{\text{DC}}}{1\text{ mW}}\right) \quad [\text{dBc/Hz}]$$
  $$\text{FoM}_T = \text{FoM} + 20\log_{10}\left(\frac{\text{TR}\%}{10}\right)$$
  (Typical good CMOS LC-VCO: $\text{FoM} \approx 185\text{–}192\text{ dBc/Hz}$; Ring-VCO: $\text{FoM} \approx 155\text{–}165\text{ dBc/Hz}$.)

---

## 3. Tuning Curve, $K_{\text{VCO}}$ & AM-to-PM Noise Conversion

- **Keep fine $K_{\text{VCO}}$ small!** Large $K_{\text{VCO}}$ amplifies control-line thermal noise, loop-filter resistor noise, and reference/supply spurs by $+20\log_{10}(K_{\text{VCO}})$, and increases **AM-to-PM conversion** through the nonlinear $C(V)$ varactor curve.
- **Standard solution:** Cover PVT + frequency bands with a binary/thermometer **switched MOM/MIM capacitor coarse bank** (overlapping adjacent bands by $\ge 25\%\text{–}35\%$ across PVT), leaving a small linear varactor (or fine DCO tracking bank) with small $K_{\text{VCO}}$ for fine phase tracking.
- **DCO segmented bank sizing:**
  - **PVT bank:** Covers process/temperature spread (binary-weighted, calibrated once at startup).
  - **Acquisition bank:** Covers channel jump range (thermometer-coded for guaranteed monotonicity).
  - **Tracking bank:** Fine unit step $\Delta C_{\text{min}}$ ($\Delta f_{\text{res}} = -\frac{1}{2} f_0 \frac{\Delta C_{\text{min}}}{C_{\text{tot}}}$) — thermometer-coded, optionally $\Delta\Sigma$-dithered to push frequency quantization noise out of band.

---

## How to Verify a VCO or DCO

> **Ready-to-run process-independent Spectre testbenches:** See [`../assets/tb/vco/`](../assets/tb/vco/README.md) (`tb_vco_tuning_kvco.scs`, `tb_vco_pss_pnoise.scs`, `analyze_vco.py`), [`../assets/tb/tdc_dco/`](../assets/tb/tdc_dco/README.md) (`tb_dco_tuning.scs`), and [`../assets/va/va_vco.va`](../assets/va/va_vco.va) / [`../assets/va/va_dco.va`](../assets/va/va_dco.va).

1. **Startup & Tuning Curve (`tb_vco_tuning_kvco.scs` / `tb_dco_tuning.scs`):**
   - Always check oscillation startup under worst-case `ss` / high-temperature / low-$V_{\text{DD}}$ with an explicit tiny initial kick (e.g., short current impulse or `ic` on tank node) so a numerically symmetric differential LC tank does not sit on its metastable DC equilibrium!
   - Sweep $V_{\text{ctrl}}$ (or `FTW`) across the usable range to extract $f_{\text{min}}$, $f_{\text{max}}$, tuning range $\text{TR}\%$, local $K_{\text{VCO}}(V_{\text{ctrl}}) = df/dV_{\text{ctrl}}$, and monotonicity across coarse/fine bank boundaries.
2. **Autonomous Shooting PSS + PNOISE (`tb_vco_pss_pnoise.scs`):**
   - Pass the oscillator differential output pair to `pss`: `pss (OUTP OUTN) pss fund=f_est harms=20 errpreset=conservative tstab=t_stab autotstab=yes`.
   - Run relative single-sideband PM noise: `pnoise (OUTP OUTN) pnoise sweeptype=relative relharmnum=1 start=1k stop=100M dec=20 pnoisemethod=fullspectrum noisetype=timeaverage noiseout=[pm]`.
   - Extract exact $f_0$, output swing, DC power $P_{\text{DC}}$, $\mathcal{L}(\Delta f)$ at `100 kHz` / `1 MHz` / `10 MHz`, $\text{FoM}$, and integrated RMS jitter (`integrate_phase_noise_jitter` in `common/psf_utils.py`).
3. **Supply Pushing ($K_{\text{VDD}}$):**
   - Perturb $V_{\text{DD}}$ by $\pm 5\%$ and measure $|\Delta f / \Delta V_{\text{DD}}|$ [MHz/V] to size the LDO PSRR budget.
