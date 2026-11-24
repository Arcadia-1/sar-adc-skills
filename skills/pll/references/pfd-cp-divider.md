# PFD, Charge Pump & Frequency Dividers

## 1. Tri-State Phase-Frequency Detector (PFD)

A standard tri-state PFD uses two resettable rising-edge DFFs (`D` tied to `VDD`, clocked by `FREF` and `FDIV`) plus an `AND` gate feeding a controlled **reset delay** $t_{\text{rst}}$ back to both async resets:

- **Frequency acquisition:** Unlike an XOR phase detector, the tri-state PFD pulls frequency monotonically across the full VCO range without false harmonic locking.
- **Dead-zone elimination:** If `UP` and `DN` reset instantaneously at $\Delta t \approx 0$, narrow pulses cannot fully turn on the charge-pump switches, leaving a zero-gain flat spot (dead zone) that lets VCO phase drift freely and ruins jitter. Adding a controlled delay $t_{\text{rst}}$ forces both `UP` and `DN` to overlap for $t_{\text{rst}}$ every cycle so both switches always reach full conduction.
- **Tradeoff on $t_{\text{rst}}$:**
  - Too short ($< 30\text{ ps}$ at slow corner): dead zone re-appears.
  - Too long ($> 200\text{–}300\text{ ps}$): widens the window where both CP currents are on simultaneously, increasing CP thermal noise injection ($\propto t_{\text{rst}}/T_{\text{ref}}$) and amplifying reference spurs from Up/Down mismatch ($\Delta t_{\text{mis}} \approx \frac{\Delta I}{I_{\text{cp}}} t_{\text{rst}}$).
  - Target: $t_{\text{rst}} \approx 60\text{–}150\text{ ps}$ (just above the CP switch turn-on time across worst-case `ss` corner).
- **Blind-zone / maximum input frequency:** $f_{\text{ref,max}} < \frac{1}{2 t_{\text{rst}}}$ (otherwise a fast edge arrives during reset and gets skipped, flipping loop polarity!).

---

## 2. Charge Pump (CP)

The CP steers matched sourcing ($I_{\text{up}}$) and sinking ($I_{\text{dn}}$) currents onto `VCTRL` under `UP`/`DN` control.

### Key Non-Idealities & Circuit Fixes
1. **Up/Down current mismatch ($\Delta I / I_{\text{cp}}$):**
   - Causes static phase offset and reference spurs in Integer-N PLLs, and **catastrophic $\Delta\Sigma$ quantization noise folding** in Fractional-N PLLs.
   - **Fixes:** Long-channel cascode current mirrors (high $r_o$, small $\sigma_{I}/I \propto 1/\sqrt{WL}$), source-switched or differential current-steering switches (faster than drain-switched, less channel-charge injection), and optional active feedback current-matching calibration.
2. **Charge sharing:**
   - When `UP`/`DN` turn off, the internal drain node of the current source drifts to `VDD`/`VSS`; on the next turn-on it dumps parasitic charge $C_p (V_{\text{DD}} - V_{\text{ctrl}})$ onto `VCTRL`.
   - **Fix:** Add a **unity-gain opamp replica buffer** that steers the inactive complementary branch (`UPB`/`DNB`) to a dummy node held at $V_{\text{dummy}} = V_{\text{ctrl}}$!
3. **Output compliance range:**
   - Maintain both current sources in strong saturation across the entire usable VCO tuning window $[V_{\text{ctrl,min}}, V_{\text{ctrl,max}}]$ (typically $[0.2\,V_{\text{DD}}, 0.8\,V_{\text{DD}}]$). Leaving compliance collapses $r_o$ and explodes $\Delta I / I_{\text{cp}}$.
4. **CP thermal noise:**
   - During the overlap window $t_{\text{rst}}$, both branches inject current noise $S_{I,\text{cp}} \approx 4 k T \gamma (g_{m,\text{up}} + g_{m,\text{dn}}) \cdot \frac{t_{\text{rst}}}{T_{\text{ref}}}$. Use larger $V_{\text{ov}} = V_{\text{gs}} - V_{\text{th}}$ on current mirrors to reduce $g_m / I_{\text{cp}}$ (subject to compliance headroom!).

---

## 3. Frequency Dividers (Prescaler, Integer-N & MMD)

- **High-speed front-end prescaler ($\div 2$ or $\div 2/3$):**
  - Driven directly by the VCO at $f_{\text{out}}$ (GHz range); must self-oscillate or track well above $f_{\text{out,max}}$ at `ss`/high-$T$/low-$V_{\text{DD}}$ with reasonable input swing.
  - **CML (Current-Mode Logic)** for $> 5\text{–}10\text{ GHz}$ or small sinusoidal VCO swings; **TSPC (True Single-Phase Clock)** CMOS for lower power at rail-to-rail multi-GHz clocks.
- **2/3-cell Multi-Modulus Divider (MMD) chain:**
  - A chain of $K$ cascaded $2/3$ cells produces programmable division across $[2^K, 2^{K+1} - 1]$ with strictly local high-speed feedback (only adjacent cells communicate, avoiding long global reset loops).
  - Accepts the instantaneous integer word $N[n] = N_{\text{int}} + y[n]$ from the MASH 1-1-1 $\Delta\Sigma$ modulator synchronously on the divided clock edge.
- **Output retiming flip-flop (essential for low in-band noise!):**
  - A long ripple/MMD chain accumulates supply and thermal jitter from every stage. Re-sampling `FDIV` with a single clean high-speed DFF clocked directly by the **VCO output** resets the divider's accumulated jitter back to just that one final flip-flop!

---

## How to Verify PFD, Charge Pump & Dividers

> **Ready-to-run process-independent Spectre testbenches:** See [`../assets/tb/pfd_cp/`](../assets/tb/pfd_cp/README.md) (`tb_pfd_cp_transfer.scs`, `analyze_pfd_cp.py`), [`../assets/tb/divider/`](../assets/tb/divider/README.md) (`tb_div_func_mmd.scs`, `analyze_divider.py`), and behavioral models [`va_pfd.va`](../assets/va/va_pfd.va), [`va_cp.va`](../assets/va/va_cp.va), [`va_div_int.va`](../assets/va/va_div_int.va), and [`va_mmd_mash111.va`](../assets/va/va_mmd_mash111.va).

1. **PFD + CP Transfer Curve & Dead-Zone Check (`tb_pfd_cp_transfer.scs`):**
   - Hold `VCTRL` at a fixed DC voltage (sweep `0.2*VDD`, `0.5*VDD`, `0.8*VDD`) while stepping `FREF`-to-`FDIV` delay $\Delta t$ across negative, fine near-zero ($\pm 1\text{–}50\text{ ps}$), and positive offsets.
   - Integrate $Q_{\text{out}}(\Delta t) = \int I(\text{VCTRL})\,dt$ per cycle and extract:
     - Effective gain $K_d = \frac{1}{2\pi} \frac{d(Q_{\text{out}} f_{\text{ref}})}{d\Delta t}$ (compare vs. nominal $I_{\text{cp}} / 2\pi$).
     - **Dead-zone check:** Verify smooth non-zero slope right through $\Delta t = 0$.
     - **Current mismatch:** Ratio $|I_{\text{up}} - I_{\text{dn}}| / I_{\text{nom}}$ and zero-offset charge error $Q_{\text{out}}(0)$ across `VCTRL` compliance range.
2. **Divider & MMD Verification (`tb_div_func_mmd.scs`):**
   - Measure exact average division ratio (integer $N$ or fractional $N_{\text{int}} + K_{\text{frac}}/2^M$) over $\ge 256$ divided cycles, verify zero skipped/glitched pulses across minimum and maximum $f_{\text{in}}$ at `ss`/`ff`, and check `t_clk2q` / power.
3. **Divider Added Phase Noise:**
   - Run driven `pss` + sampled `pnoise` (`pmjitter` / `jitterevent` on `FDIV` rising edge crossing `VDD/2`) to extract divider RMS output jitter $\sigma_{t,\text{div}}$ and refer it to in-band phase noise $\mathcal{L}_{\text{div}} = 10\log_{10}((2\pi f_{\text{out}} \sigma_{t,\text{div}})^2 / f_{\text{ref}})$.
