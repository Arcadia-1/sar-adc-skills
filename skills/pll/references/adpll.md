# All-Digital PLL (ADPLL) Design

## 1. Motivation & Core Architectures

An **All-Digital PLL (ADPLL)** replaces the analog PFD, charge pump, and bulky passive loop filter capacitor $C_1$ with digital logic and a **Digitally Controlled Oscillator (DCO)**. Advantages in scaled CMOS: compact area, immunity to analog leakage, programmable bandwidth/gear-shifting (fast coarse acquisition $\to$ narrow low-noise tracking), and built-in digital calibration.

Three main ADPLL topologies:

1. **Divider + TDC ADPLL** (direct digital counterpart of a CP-PLL):
   - Feedback divider (`va_div_int` or `va_mmd_mash111`) outputs `FDIV`; a **Time-to-Digital Converter (TDC)** quantizes $\Delta t = t_{\text{FREF}} - t_{\text{FDIV}}$ into a signed digital error word $e[k]$; a **Digital PI Loop Filter (DLF)** computes the DCO tuning word $\text{FTW}[k]$; the **DCO** generates $f_{\text{out}}(\text{FTW})$.
   - Easy to understand, modular for hybrid verification (swap TDC, DLF, DCO, or divider individually).
2. **Phase-Domain Counter + TDC ADPLL (Staszewski architecture):**
   - Eliminates the high-speed programmable MMD completely: accumulates reference phase $R[k] = R[k-1] + \text{FCW}$ (where $\text{FCW} = f_{\text{out}} / f_{\text{ref}} = N_{\text{int}} + \alpha$), subtracts an integer DCO cycle counter plus the normalized fractional TDC reading $\epsilon[k] = \Delta t / T_{\text{DCO}}$ to form exact phase error $e[k]$!
   - Naturally supports Fractional-N without MASH divider quantization noise (only TDC quantization noise!).
3. **Bang-Bang ADPLL (BBPLL):**
   - Replaces the multi-bit TDC with a **1-bit Bang-Bang Phase Detector (BBPD — a single DFF/comparator)** outputting `EARLY` ($-1$) or `LATE` ($+1$).
   - Ultra-low power and zero TDC nonlinearity spurs, at the cost of nonlinear linearized gain $K_{\text{BBPD}} = \sqrt{\frac{2}{\pi}} \frac{1}{\sigma_t}$ (depends on jitter $\sigma_t$!) and deterministic **limit-cycle wander** if proportional step $\alpha$ is too large.

---

## 2. Digital PI Loop Filter & $z$-Domain Design

A Type-II digital PI loop filter clocked at $f_{\text{ref}}$ ($T_{\text{ref}} = 1/f_{\text{ref}}$) updates the DCO tuning word on each reference edge:

$$p[k] = \alpha \, e[k], \qquad i[k] = i[k-1] + \beta \, e[k], \qquad \text{FTW}[k] = \text{FTW}_0 + p[k] + i[k]$$

Its $z$-domain transfer function is:

$$H_{\text{DLF}}(z) = \alpha + \frac{\beta}{1 - z^{-1}} \approx \alpha + \frac{\beta \, f_{\text{ref}}}{s} \qquad (f \ll f_{\text{ref}})$$

### Mapping Continuous-Time Specs ($f_u, \zeta$) to Digital Gains ($\alpha, \beta$)

For a Divider + TDC ADPLL with TDC time resolution $\Delta t_{\text{res}}$ (gain $K_{\text{TDC}} = \frac{1}{2\pi f_{\text{ref}} \Delta t_{\text{res}}}\;[\text{LSB/rad}]$), DCO gain $K_{\text{DCO}}\;[\text{Hz/LSB}]$, and division ratio $N$:

- Open-loop gain (continuous-time approximation for $f_u \le f_{\text{ref}}/15$):
  $$L(s) \approx \frac{K_{\text{TDC}} \, (2\pi K_{\text{DCO}})}{N \, s} \left(\alpha + \frac{\beta f_{\text{ref}}}{s}\right) = \frac{K_{\text{DCO}}}{N \, f_{\text{ref}} \, \Delta t_{\text{res}}} \cdot \frac{\alpha s + \beta f_{\text{ref}}}{s^2}$$
- **Proportional gain $\alpha$ sets unity-gain bandwidth $\omega_u = 2\pi f_u$:**
  $$\alpha \approx \frac{N \, f_{\text{ref}} \, \Delta t_{\text{res}} \, \omega_u}{K_{\text{DCO}}}$$
- **Integral gain $\beta$ sets zero frequency $\omega_z = \frac{\beta}{\alpha} f_{\text{ref}}$ and damping $\zeta$:**
  $$\text{Choose } \frac{\omega_u}{\omega_z} \approx 4\text{–}8 \quad (\text{for PM} \approx 60^\circ\text{–}70^\circ) \implies \beta = \alpha \frac{\omega_z}{f_{\text{ref}}} = \frac{\alpha \, \omega_u}{(4\text{–}8) \, f_{\text{ref}}}$$
- **Check loop latency $z^{-D}$:** Digital pipeline delay of $D$ reference cycles subtracts $\Delta\text{PM} = D \cdot 360^\circ \cdot (f_u / f_{\text{ref}})$ of phase margin! Keep $D \le 1\text{–}2$ cycles and account for it explicitly when choosing $f_u / f_{\text{ref}}$.
- **Gear shifting:** Start acquisition with $4\times\text{–}8\times$ larger $(\alpha, \beta)$ for rapid locking, then switch smoothly to narrow low-noise $(\alpha, \beta)$ once $|e[k]|$ drops below threshold!

---

## 3. TDC & DCO Quantization Noise Budgets

### TDC In-Band Phase Noise Floor
A uniform TDC with time step $\Delta t_{\text{res}}$ has quantization variance $\Delta t_{\text{res}}^2 / 12$, contributing a flat in-band output phase-noise floor:

$$\mathcal{L}_{\text{TDC}} = 10\log_{10}\left[ \frac{(2\pi)^2}{12} \left(\frac{\Delta t_{\text{res}}}{T_{\text{out}}}\right)^2 \frac{1}{f_{\text{ref}}} \right] \quad [\text{dBc/Hz}]$$

- **Worked example:** At $f_{\text{out}} = 2.4\text{ GHz}$ ($T_{\text{out}} = 417\text{ ps}$) and $f_{\text{ref}} = 50\text{ MHz}$:
  - A coarse inverter-chain TDC with $\Delta t_{\text{res}} = 20\text{ ps}$ gives $\mathcal{L}_{\text{TDC}} \approx -98.2\text{ dBc/Hz}$.
  - Improving to a Vernier/interpolating TDC with $\Delta t_{\text{res}} = 5\text{ ps}$ drops the floor by **12 dB** to $-110.2\text{ dBc/Hz}$!

### DCO Frequency Quantization Noise
Finite DCO tracking-bank step $\Delta f_{\text{res}} = K_{\text{DCO}}\;[\text{Hz/LSB}]$ (updated at clock $f_{\text{dith}}$) produces quantization phase noise:

$$\mathcal{L}_{\text{DCO},q}(\Delta f) = 10\log_{10}\left[ \frac{1}{12} \left(\frac{\Delta f_{\text{res}}}{\Delta f}\right)^2 \frac{1}{f_{\text{dith}}} \cdot \text{sinc}^2\left(\frac{\Delta f}{f_{\text{dith}}}\right) \right] \quad [\text{dBc/Hz}]$$

- **Fix:** Either make the finest capacitive tracking unit tiny ($\Delta f_{\text{res}} \le 10\text{–}50\text{ kHz}$), or apply a high-speed $\Delta\Sigma$ dither modulator clocked at $f_{\text{dith}} \approx f_{\text{out}}/4\text{–}f_{\text{out}}/8$ on the tracking LSBs to push quantization noise far out of band!

---

## How to Verify an ADPLL

> **Ready-to-run process-independent Spectre testbenches:** See [`../assets/tb/tdc_dco/`](../assets/tb/tdc_dco/README.md) (`tb_tdc_transfer.scs`, `tb_dco_tuning.scs`, `analyze_tdc_dco.py`), [`../assets/tb/adpll/`](../assets/tb/adpll/README.md) (`tb_adpll_lock.scs`, `analyze_adpll.py`), and the behavioral models [`va_tdc.va`](../assets/va/va_tdc.va), [`va_dco.va`](../assets/va/va_dco.va), [`va_dlf_pi.va`](../assets/va/va_dlf_pi.va), and [`va_bbpd.va`](../assets/va/va_bbpd.va).

1. **TDC Linearity (`tb_tdc_transfer.scs`):**
   - Sweep arrival-time offset $\Delta t$ across the full TDC input range and extract average $\Delta t_{\text{res}}$, DNL ($< 0.5\text{ LSB}$), INL ($< 1\text{ LSB}$), and zero-crossing offset across PVT.
2. **DCO Tuning & Monotonicity (`tb_dco_tuning.scs`):**
   - Step `FTW` across the tracking bank and verify strictly monotonic frequency steps, average $K_{\text{DCO}}$, and bank overlap margin between PVT / acquisition / tracking banks.
3. **Closed-Loop ADPLL Lock (`tb_adpll_lock.scs`):**
   - Run both **Integer-N ADPLL** and **Fractional-N ADPLL** (swapping `va_div_int` $\leftrightarrow$ `va_mmd_mash111`) from an initial frequency error; verify `FTW` settling without excessive ringing or limit cycles, steady-state frequency error, and steady-state `FTW` / period jitter.
4. **BBPLL Check:**
   - Replace `va_tdc` with `va_bbpd` and tune proportional step $\alpha$ to confirm bounded limit-cycle amplitude ($\le \pm 1\text{–}2\text{ LSB}$) without slope overload during frequency steps.
