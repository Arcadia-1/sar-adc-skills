# On-Chip Temperature Sensor & Thermal Shutdown (TSD) Design Guide

A first-principles, process-independent engineering guide to precision ratiometric BJT/CMOS on-chip temperature sensors, calibration budgets, dynamic offset chopping, noise-resolution trade-offs, and hysteretic Over-Temperature Shutdown (TSD) design.

## 1. Sensor Architectures & Trade-Offs

| Architecture | Sensing Physics | Typical Uncalibrated Accuracy | 1-Pt / 2-Pt Trimmed Accuracy ($-40..125^\circ\text{C}$) | Power & Area | Primary Use Case |
|---|---|---|---|---|---|
| **Substrate PNP BJT** | $\Delta V_{BE} = \frac{kT}{q}\ln p$ vs. $V_{BE}(T)$ | $\pm 1.5\text{–}3^\circ\text{C}$ | $\pm 0.5\text{–}1.2^\circ\text{C}$ (1-pt), $\pm 0.4\text{–}0.7^\circ\text{C}$ (2-pt, curvature-limited) | Moderate ($2\text{–}20\,\mu\text{A}$, medium area) | Industrial SoC telemetry, thermal management, bandgap co-design |
| **Subthreshold CMOS MOSFET** | $\Delta V_{GS} = \frac{nkT}{q}\ln p$ vs. $V_{GS}(T)$ | $\pm 5\text{–}15^\circ\text{C}$ | $\pm 2\text{–}5^\circ\text{C}$ (1-pt), $\pm 1.5\text{–}3.0^\circ\text{C}$ (2-pt, $n(T)$ & mobility bow) | Ultra-low ($< 1\,\mu\text{A}$, small area) | Ultra-low-power IoT, compact local thermal monitors where PNPs are unavailable |
| **Resistor / RC / Thermal Diffusivity** | $R(T)$ TC or silicon $D(T) \propto T^{-1.8}$ | Process-dependent | $\pm 0.1\text{–}0.5^\circ\text{C}$ (2-pt or high-power TD) | Low (resistor) or high (TD heater) | Ultra-high resolution ($\text{sub-mK}$) or advanced nodes with weak PNPs |

## 2. First-Principles BJT $V_{BE}(T)$ Physics & 2nd-Order Curvature

In standard CMOS technologies, vertical substrate PNP transistors (p+ emitter in n-well base over p-substrate collector) remain the gold standard for accurate, process-portable temperature sensing.

### 2.1 CTAT $V_{BE}(T)$ and PTAT $\Delta V_{BE}(T)$
Biasing a BJT at collector current $I_C(T) \propto T^{\alpha_I}$ (typically $\alpha_I = 1$ for PTAT biasing) produces the exact Tsividis base-emitter voltage temperature dependence:
$$V_{BE}(T) = V_{G0} - \left(V_{G0} - V_{BE}(T_r)\right)\frac{T}{T_r} - (\eta - \alpha_I)\frac{kT}{q}\ln\!\left(\frac{T}{T_r}\right)$$
where:
- $V_{G0} \approx 1.205\text{ V}$ is the extrapolated $0\text{ K}$ silicon bandgap voltage,
- $T_r = 300.15\text{ K}$ ($27^\circ\text{C}$) is the reference temperature,
- $V_{BE}(T_r) \approx 0.65\text{ V}$ at $I_C \approx 1\text{–}5\,\mu\text{A}$, giving a CTAT slope of $\approx -2.0\text{ to }-2.2\text{ mV/}^\circ\text{C}$,
- $\eta \approx 4.0\text{–}4.5$ is the process exponent of $I_S(T)$ (so $\eta - \alpha_I \approx 3.0\text{–}3.5$).

Taking the difference between two matched PNPs operating at emitter current-density ratio $p$ (typically $p = 8$ via a $3\times 3$ common-centroid array with 1 center unit and 8 surrounding units) eliminates $I_S(T)$ completely:
$$\Delta V_{BE}(T) = \frac{kT}{q}\ln(p) \quad \left(\text{for } p = 8:\; \frac{d\Delta V_{BE}}{dT} = +0.1792\text{ mV/K}\right)$$
Note that finite current gain $\beta_F(T)$ and emitter/base series resistance $R_s$ introduce minor errors at high current density; keep $I_C$ low enough that $I_C R_s \ll 50\,\mu\text{V}$ and use base-current cancellation if $\beta_F < 10$.

### 2.2 Ratiometric Bandgap-Referenced Readout $\mu(T)$
A temperature sensor requires a temperature-independent reference to digitize $\Delta V_{BE}(T)$. Forming the zero-TC bandgap sum $V_{BG}(T) = V_{BE}(T) + \alpha\,\Delta V_{BE}(T)$ directly inside the sensor yields a self-referenced ratiometric output:
$$\mu(T) = \frac{\alpha\,\Delta V_{BE}(T)}{V_{BE}(T) + \alpha\,\Delta V_{BE}(T)}, \qquad V_{\text{TEMP}}(T) = V_{\text{scale}}\cdot\mu(T)$$
Choosing $\alpha$ to cancel the first-order slope at $T_r$ ($\alpha = \frac{(V_{G0}-V_{BE}(T_r))/T_r + (\eta - \alpha_I)k/q}{(k/q)\ln p} \approx 11.8$) makes $V_{BG}(T_r) = V_{G0} + (\eta - \alpha_I)V_T(T_r) \approx 1.28\text{ V}$.

Because the numerator $\alpha\Delta V_{BE}(T)$ is strictly linear in $T$ while the denominator $V_{BG}(T)$ droops parabolically away from $T_r$ by:
$$V_{\text{nl}}(T) = (\eta - \alpha_I)\frac{k}{q}\left[(T - T_r) - T\ln\!\left(\frac{T}{T_r}\right)\right] \approx -2.4\text{ to }-4.4\text{ mV at }-40^\circ\text{C}/125^\circ\text{C}$$
the ratiometric output $\mu(T)$ exhibits an irreducible **2nd-order parabolic bow** of $\pm 0.4\text{–}0.8^\circ\text{C}$ across $-40..125^\circ\text{C}$ after straight-line fitting.

> **Why subthreshold MOSFET sensors bow more:** In a subthreshold CMOS $\Delta V_{GS} / V_{GS}$ sensor, $V_{GS}(T)$ carries additional nonlinearities from the temperature-dependent subthreshold slope factor $n(T)$, mobility $\mu(T) \propto T^{-m}$, and threshold voltage curvature, typically enlarging the 2-point residual bow to $\pm 1.5\text{–}3.0^\circ\text{C}$ across $-40..125^\circ\text{C}$.

## 3. Error Sources & Calibration Hierarchy

| Calibration Tier | What Is Trimmed | Dominant Residual Error | Typical Accuracy ($-40..125^\circ\text{C}$) |
|---|---|---|---|
| **Uncalibrated (Raw)** | Nominal design scaling only | $I_S$ spread ($\Delta V_{BE,\text{proc}}$), $\alpha$ mismatch, unchopped $V_{os}$ | $\pm 1.5\text{–}4.0^\circ\text{C}$ (with chopping) |
| **1-Point Trim (`@ 27°C`)** | Multiplicative PTAT gain trim (or $\alpha$ trim) at single wafer-sort temperature | 2nd-order BJT curvature bow + residual mechanical package stress | $\pm 0.8\text{–}1.3^\circ\text{C}$ |
| **2-Point Linear Trim** | Offset + slope across two temperatures (e.g., $0^\circ\text{C}$ & $100^\circ\text{C}$, or least-squares) | Irreducible 2nd-order BJT curvature bow | $\pm 0.4\text{–}0.65^\circ\text{C}$ |
| **Curvature-Corrected** | Fixed digital 2nd-order polynomial or $I_C \propto T^2$ / resistor-compensated bias | Packaging stress & residual DEM/chop error | $\pm 0.1\text{–}0.25^\circ\text{C}$ |

**Why 1-point trim works so well on BJTs:** Wafer-to-wafer variation in saturation current $I_S \to I_S(1+\delta)$ shifts $V_{BE} = \frac{kT}{q}\ln(I_C/I_S)$ by $-\frac{kT}{q}\ln(1+\delta)$, which is **purely PTAT** ($\propto T$)! Therefore, a single multiplicative gain calibration at $27^\circ\text{C}$ cancels $I_S$ spread across the entire $-40..125^\circ\text{C}$ range.

## 4. Dynamic Offset Chopping & DEM

Front-end amplifier or $\Delta\Sigma$ ADC input-referred offset $V_{os}$ adds directly to $\Delta V_{BE}$. Because $\Delta V_{BE}$ has a small slope ($0.179\text{ mV/}^\circ\text{C}$ for $p=8$), even a modest CMOS opamp offset causes severe temperature error:
$$\Delta T_{os} \approx \frac{V_{os}}{(k/q)\ln(p)}\cdot(1 - \mu)$$
- For $V_{os} = 1.2\text{ mV}$ and $\mu \approx 0.49$ at $27^\circ\text{C}$: unchopped error is $\approx +3.3^\circ\text{C}$!
- **Dynamic Chopping (`CHOP = 1`)**: Swapping the amplifier/integrator input and output polarity at $f_{\text{chop}}$ modulates $V_{os}$ and $1/f$ flicker noise up to $f_{\text{chop}}$ where the decimation filter notches them out, reducing DC offset error by $> 10\text{–}30\times$ (e.g., $+3.3^\circ\text{C} \to +0.10^\circ\text{C}$) and lowering the $1/f$ noise corner by $\text{chop\_atten}^2$.
- **Dynamic Element Matching (DEM)**: Rotating the $1:p$ unit bias current sources and $1:p$ BJT array elements removes current-ratio mismatch $\Delta p/p$ error ($\Delta T_p \approx \frac{T}{\ln p}\frac{\Delta p}{p}$).

## 5. Supply Sensitivity (PSRR) & Noise Resolution Budget

- **Supply sensitivity** ($^\circ\text{C/V}$):
  $$S_{VDD} = \frac{|\partial V_{\text{TEMP}} / \partial V_{DD}|}{|\partial V_{\text{TEMP}} / \partial T|} \quad [^\circ\text{C/V}]$$
  Target $S_{VDD} < 0.5\text{–}1.0^\circ\text{C/V}$ via cascoded PTAT/BJT current mirrors and high-PSRR reference biasing (cross-reference [`skills/bandgap/`](../../bandgap/SKILL.md) and [`skills/opamp-ota/`](../../opamp-ota/SKILL.md)).
- **Integrated thermal resolution ($\text{mK}_{\text{rms}}$)**:
  $$\Delta T_{\text{rms}} = \frac{1}{|\partial V_{\text{TEMP}}/\partial T|} \sqrt{\int_{f_{\min}}^{f_{\max}} S_{v,\text{out}}(f)\,df}$$
  For an output sensitivity of $2.0\text{ mV/}^\circ\text{C}$, achieving $20\text{ mK}_{\text{rms}}$ resolution across a $100\text{ kHz}$ front-end noise bandwidth requires $v_{n,\text{rms}} \le 40\,\mu\text{V}_{\text{rms}}$ ($v_{n,\text{white}} \le 126\text{ nV/}\sqrt{\text{Hz}}$), and chopping is mandatory to prevent low-frequency $1/f$ noise from bloating narrow-bandwidth conversion noise.
- **Resolution Figure of Merit**:
  $$\text{FoM}_{\text{res}} = E_{\text{conv}} \cdot (\Delta T_{\text{rms}})^2 \quad [\text{nJ}\cdot\text{K}^2]$$

## 6. Over-Temperature Shutdown (TSD) Design

An Over-Temperature Shutdown (TSD) block protects power stages (LDOs, buck converters, RF PAs, SoC cores) from thermal runaway by asserting an active-high digital shutdown flag `TSD_OUT` when junction temperature exceeds $T_{\text{trip}}$ (typically $130\text{–}150^\circ\text{C}$).

### 6.1 Architecture & Threshold Equations
Compare a scaled CTAT voltage $V_{BE}(T)$ directly against a PTAT voltage $K\cdot\Delta V_{BE}(T)$ (or against a bandgap $V_{\text{BG}}$). Because $V_{BE}(T)$ falls at $\approx -2.1\text{ mV/}^\circ\text{C}$ while $K\Delta V_{BE}(T)$ rises at $\approx +2.1\text{ mV/}^\circ\text{C}$, their differential slope at crossover is $\approx 4.2\text{ mV/}^\circ\text{C}$, cutting comparator offset impact in half:
$$V_{BE}(T_{\text{trip}}) = K_{\text{trip}} \cdot \Delta V_{BE}(T_{\text{trip}})$$

### 6.2 Thermal Hysteresis ($T_{\text{hys}}$) & Chatter Prevention
When `TSD_OUT` asserts high and disables the high-power load, the silicon die cools down with package thermal time constant $\tau_{\text{th}} = R_{\theta,JA} C_{\text{th}}$ (typically $10\text{ ms}\text{–}5\text{ s}$).
- **Zero-hysteresis failure mode**: If $T_{\text{hys}} = 0$, the power stage immediately re-enables the instant the die cools by $0.1^\circ\text{C}$, locking the chip into high-frequency thermal cycling right at $T_{\text{trip}} = 135^\circ\text{C}$ and causing solder-fatigue / gate-oxide reliability failure.
- **Sizing rule**: Design $T_{\text{hys}} = T_{\text{trip}} - T_{\text{release}} \approx 15\text{–}25^\circ\text{C}$ (e.g., $T_{\text{trip}} = 135^\circ\text{C}$, $T_{\text{release}} = 120^\circ\text{C}$) by switching a parallel tap resistor in the $K\Delta V_{BE}$ / $V_{BE}$ comparator network upon trip.
- **Hotspot placement**: Place the TSD sensing PNP directly adjacent to the hottest power FET (within $50\text{–}150\,\mu\text{m}$), since die thermal gradients can exceed $10\text{–}20^\circ\text{C/mm}$ during short-circuit faults.
