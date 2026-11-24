# SerDes Slicers, Decision Feedback Equalizers (DFE) & Sign-Sign LMS

## 1. High-Speed Data Slicers (CML Latch vs. StrongARM)

| Metric | CML Latch Slicer | StrongARM / Two-Stage Dynamic Slicer |
|---|---|---|
| **Static Power** | Always-on tail current (high power, constant supply current) | Zero static power (dynamic energy $E \propto C V^2 f_b$) |
| **Input Sensitivity & Kickback** | Smooth tracking phase, low kickback, easy inductive peaking | High sensitivity; check clock kickback & precharge reset completeness |
| **Hysteresis / Memory Risk** | Residual voltage on latch regeneration nodes if track time is too short | Residual charge if reset switches are undersized at high $f_{\text{clk}}$ |
| **Typical Role** | Full-rate / half-rate `> 10 Gb/s` continuous loops, DFE summing latch | Half-rate / quarter-rate low-power RX slicers & error samplers (see also [`skills/sar-adc/references/comparator.md`](../../sar-adc/references/comparator.md)) |

- **Slicer Verification ([`../assets/tb/slicer_dfe/tb_slicer_hys_vtf.scs`](../assets/tb/slicer_dfe/tb_slicer_hys_vtf.scs)):** Always sweep differential input in **both ascending and descending directions** (`-V_span -> +V_span -> -V_span`) to separate static input offset $V_{\text{os}} = \frac{1}{2}(V_{\text{th,up}} + V_{\text{th,dn}})$ from dynamic **hysteresis / memory** $\text{Hys} = V_{\text{th,up}} - V_{\text{th,dn}}$!

---

## 2. Decision Feedback Equalizer (DFE) Physics & 1-UI Timing Bottleneck

A multi-tap DFE cancels post-cursor ISI ($h_1, h_2, \dots, h_M$) by subtracting weighted **past sliced decisions** $d[k-m] \in \{-1, +1\}$ from the incoming analog waveform at the summing node:

$$y[k] = x[k] - \sum_{m=1}^{M} h_m\,d[k-m]$$

### Why DFE Beats Linear Equalizers on Severe Post-Cursor ISI
- **Zero noise amplification:** Because $d[k-m]$ are noiseless digital logic levels, DFE subtracts sharp post-cursor ISI and channel notches **without boosting high-frequency RX noise or crosstalk**!
- **Trade-offs:**
  1. **Cannot cancel pre-cursor ISI ($h_{-1}$):** Decisions are strictly causal.
  2. **Error propagation:** A single bit error flips the sign of $h_1 d[k-1]$ on the next bit (doubles ISI momentarily!). Keep raw pre-FEC BER low and avoid letting $h_1$ exceed `~0.6–0.8 * h0`.
  3. **The 1-UI First-Tap Critical Loop:**
     $$t_{\text{ck}\to q,\text{slicer}} + t_{\text{tap1,DAC}} + t_{\text{sum,settle}} + t_{\text{setup,slicer}} < 1\text{ UI}$$
     At `10 Gb/s` (`UI = 100 ps`) and especially `25–56 Gb/s` (`UI = 18–40 ps`), direct 1-tap feedback often cannot close within `1 UI`!
     - **Architectural solution — Speculative / Loop-Unrolled 1st-Tap DFE:** Pre-compute BOTH $+h_1$ and $-h_1$ branches in parallel using two slicers (with built-in threshold shifts $\pm h_1$) and select the right output with a fast 2:1 MUX driven by the previous decision — moving the slicer regeneration time **outside** the 1-UI critical path! (Taps $h_2, h_3, \dots$ have `2 UI, 3 UI` slack and use direct current-summing feedback.)

Verify 3-tap DFE eye opening and bit-error-free slicing using [`../assets/tb/slicer_dfe/tb_dfe_3tap_eye.scs`](../assets/tb/slicer_dfe/tb_dfe_3tap_eye.scs) and [`../assets/va/va_dfe_3tap.va`](../assets/va/va_dfe_3tap.va).

---

## 3. Sign-Sign LMS (SS-LMS) Adaptive Equalization

To track PVT, temperature drift, and arbitrary channel lengths automatically, modern SerDes receivers add an **error slicer** (thresholded at target eye amplitude $d_{\text{lev}} = V_{\text{ref,err}}$) alongside the data slicer:

$$e[k] = y[k] - d_{\text{lev}}\,d[k], \qquad \text{err}[k] = \text{sgn}\!\left(e[k]\right), \qquad d[k] = \text{sgn}\!\left(y[k]\right)$$

Minimizing mean-squared error $J = \frac{1}{2}\mathbb{E}\!\left[e[k]^2\right]$ with 1-bit sign approximations yields the **Sign-Sign LMS update rules**:

- **VGA Gain ($g$, lag $0$):**
  $$g[k+1] = g[k] - \mu_g\,\text{sgn}(e[k])\,\text{sgn}(d[k])$$
- **DFE Post-Cursor Tap $m$ ($h_m$, lag $m = 1, 2, 3, \dots$):**
  $$h_m[k+1] = h_m[k] + \mu_h\,\text{sgn}(e[k])\,\text{sgn}(d[k-m])$$
- **CTLE Peaking Boost (transition-filtered SS-LMS):** Correlate $\text{sgn}(e[k])$ specifically on isolated `0 -> 1` / `1 -> 0` edge transitions (`d[k] != d[k-1]`) to steer zero/pole peaking without fighting VGA DC gain!

### Practical SS-LMS Engineering Rules
1. **Sign conventions are fatal if reversed:** Reversing `sign_pol` drives taps straight into the rails! Always verify signs first on behavioral [`../assets/va/va_sslms_adapt.va`](../assets/va/va_sslms_adapt.va) inside [`../assets/tb/sslms/tb_sslms_adapt.scs`](../assets/tb/sslms/tb_sslms_adapt.scs).
2. **Use majority-vote accumulator decimation (`acc_th = 4–32`):** Cuts update chatter and allows low-speed digital FSM clocks (`f_b / 16` or `f_b / 64`) to save digital power.
3. **Convergence freeze (`DONE` gating):** Monitor rolling correlation $|\overline{\text{sgn}(e)\text{sgn}(d)}| < \text{conv\_th}$ and **actually gate the tap update (`w += sign_pol * mu * step * (1 - done)`)** when background tracking is turned off (a common RTL/Verilog-A bug is asserting `done` without multiplying the update step by `1 - done`!).
4. **Prevent gain-vs-DFE deadlock:** Use PRBS-9 or scrambled data (sufficiently long run-lengths and decorrelated bit lags) so the `h0, h1, h2, h3` gradient directions stay orthogonal!
