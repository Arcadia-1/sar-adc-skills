# Bootstrap Switch

The bootstrap switch is the standard sampling front-end for high-linearity SAR ADCs because it eliminates the signal-dependent on-resistance that plagues plain NMOS and CMOS transmission-gate switches. A plain NMOS switch driven by a fixed gate voltage (e.g., VDD) has Ron ∝ 1/(Vgs − Vth) = 1/(VDD − Vin − Vth), so Ron rises as Vin approaches VDD, introducing harmonic distortion that limits linearity beyond roughly 8 bits. The bootstrap circuit solves this by dynamically boosting the gate voltage to Vin + VDD during sampling, keeping Vgs = VDD (constant) across the entire input range and delivering a nearly flat Ron — making it the preferred front-end for SAR ADCs targeting 10 bits and above.

## Why Bootstrap Is Needed

### Ron vs. Vin Problem for a Plain NMOS Switch

For an NMOS switch with fixed gate voltage VDD:

```
Ron ≈ 1 / (μn · Cox · (W/L) · (VDD − Vin − Vth))
```

As Vin increases toward VDD, the overdrive (VDD − Vin − Vth) shrinks and Ron increases. This creates a signal-dependent resistance that generates harmonic distortion.

### Signal-Dependent Distortion

Because Ron varies with the instantaneous input signal, the RC time constant of the sampling network τ = Ron · Csample also varies with Vin. This causes the sampled voltage to track the input with a gain error that depends on the signal amplitude and frequency, producing THD that grows with input frequency and amplitude. The effect becomes the dominant linearity limiter above roughly 8-bit resolution.

### CMOS Transmission Gate: Partial Fix

A CMOS transmission gate (parallel NMOS + PMOS) partially cancels the Ron variation because the PMOS Ron rises as Vin decreases (where NMOS Ron is low) and vice versa. However, the cancellation is imperfect — the two Ron curves do not mirror exactly — and it consumes twice the area and switch capacitance. The bootstrap approach provides a cleaner, more scalable solution.

## Circuit Topology

The classic bootstrapped NMOS sampling switch contains three functional blocks:

1. **Inverter** — generates the complementary clock CLKSB from CLKS.
2. **Charge pump (bootstrapper)** — pre-charges a bootstrap capacitor CB to VDD during reset, then level-shifts it by VIN during sampling to produce VGATE = VIN + VDD.
3. **Sampling switch MS** — an NMOS transistor whose gate is driven by VGATE, achieving constant Vgs = VDD.

### Transistor Role Table

| Transistor | Type | Gate | Drain | Source | Role |
|------------|------|------|-------|--------|------|
| MS | NMOS | VGATE | VOUT | VIN | Sampling switch (main) |
| M1 | PMOS | VGATE | CB_TOP | VDD | Reset: charges CB to VDD |
| M2 | NMOS | CLKSB | GND | CB_BOT | Reset: discharges CB bottom |
| M3 | NMOS | VGATE | CB_BOT | VIN | Sampling: connects VIN to CB bottom |
| M4 | PMOS | NET_G4 | VGATE | CB_TOP | Sampling: connects CB top to VGATE |
| M4A | NMOS | VGATE | NET_G4 | VIN | Sampling: drives M4 gate to VIN |
| M4B | PMOS | CLKS | NET_G4 | VDD | Reset: drives M4 gate to VDD |
| M4C | NMOS | CLKS | NET_G4 | CB_BOT | Startup: pulls M4 gate low at CLK edge |
| M5 | NMOS | CLKSB | GND | NET_5A | Reset: pulls VGATE toward GND |
| M5A | NMOS | VDD | NET_5A | VGATE | Cascode: protects M5 from VDD+VIN overvoltage |
| MP_INV | PMOS | CLKS | CLKSB | VDD | Inverter PMOS |
| MN_INV | NMOS | CLKS | CLKSB | GND | Inverter NMOS |

## Operating Phases

### Reset Phase (CLKS = 0, CLKSB = 1)

- M1 ON → charges CB top plate to VDD.
- M2 ON → discharges CB bottom plate to GND.
- Therefore CB stores VDD across it (top = VDD, bottom = GND).
- M5 + M5A ON → pulls VGATE to GND → MS is OFF (switch open, hold mode).
- M4B ON → pre-charges M4 gate to VDD (keeps M4 OFF during reset).

### Sampling Phase (CLKS = 1, CLKSB = 0)

- M3 ON → connects VIN to CB bottom plate; CB bottom rises to VIN.
- CB was pre-charged to VDD, so CB top = VIN + VDD (charge conservation).
- M4C assists startup → pulls M4 gate low momentarily → M4 turns ON.
- M4 ON → connects CB top (VIN + VDD) to VGATE.
- M4A ON → connects VIN to M4 gate (steady-state control, takes over from M4C).
- MS: Vgs = VGATE − VIN = VDD (constant regardless of VIN) → switch ON.

## Bootstrap Voltage Derivation

During reset, CB is charged to VDD:

```
VCB = CB_TOP − CB_BOT = VDD − 0 = VDD
```

At the start of sampling, M3 connects VIN to the bottom plate. Since the charge on CB cannot change instantaneously:

```
VCB_TOP = VCB_BOT + VDD = VIN + VDD
```

This is connected to the gate of MS via M4, so:

```
Vgate = VIN + VDD
Vgs(MS) = Vgate − VIN = VDD   (constant, independent of VIN)
```

This constant overdrive means Ron of MS does not depend on the signal, eliminating signal-dependent distortion.

## Transistor Sizing Guidelines

### Sampling Switch MS

The sampling switch width W(MS) sets the on-resistance during sampling:

```
Ron(MS) ≈ 1 / (μn · Cox · (W/L) · (VDD − Vth))
```

Increasing W reduces Ron and improves settling speed, at the cost of larger switch capacitance (clock feedthrough, charge injection). Typical sizing targets Ron · Csample ≪ Tsample / 5 to ensure adequate settling.

### Bootstrap Capacitor CB

The bootstrap capacitor must be large enough to hold VDD across it with minimal droop when VIN is connected to the bottom plate. The parasitic capacitance at CB_BOT (from M3, M2 gate-drain overlap, and wiring) causes a partial redistribution. The rule of thumb is:

```
CB ≥ 5 × Cgg(MS)
```

where Cgg(MS) is the total gate capacitance of the sampling switch. This ensures that when the bottom plate is connected to VIN (a low-impedance node), the voltage droop at CB_TOP remains small (< a few percent of VDD).

### Cascode M5A

M5A is sized to withstand the full Vds stress that would otherwise appear across M5 when VGATE is at VIN + VDD. Without the cascode, M5 would see Vds ≈ VDD + Vin_max, exceeding the transistor's rated oxide voltage.

## Key Metrics

### Bootstrap Voltage Accuracy

The ideal VGATE = VIN + VDD. In practice, parasitic capacitances at CB_TOP (gate of M4, drain of M1, wiring) form a capacitive divider with CB, so VGATE falls slightly short:

```
VGATE ≈ VIN + VDD × CB / (CB + Cpar)
```

Larger CB and careful layout to minimize Cpar improve accuracy.

### Ron Flatness vs. Vin

The bootstrap switch achieves a nearly flat Ron vs. Vin characteristic because Vgs(MS) = VDD across the full input swing. Any residual variation comes from imperfect Vgate tracking (voltage droop in CB) and body effect in MS (Vsb = VIN raises Vth). Body effect can be mitigated in deep-submicron processes by using an enclosed layout or triple-well NMOS.

### Clock Feedthrough and Charge Injection

**Charge injection** occurs when MS turns off: the channel charge splits between VOUT and VIN, leaving a pedestal on the held output. The error is proportional to W(MS) · L · Cox · (Vgs − Vth) / Csample and varies weakly with VIN (through Vth body effect), creating a nonlinearity. Minimizing W(MS) (while still meeting Ron/settling requirements) and using a dummy switch can reduce this.

**Clock feedthrough** couples the CLK transition through the gate-drain/source overlap capacitances of MS. The effect is ∝ Cov / (Cov + Csample) and is usually smaller than charge injection but adds a fixed pedestal.

Both effects are substantially reduced in a differential sampling topology, where correlated errors cancel to first order.

## Comparison to Alternative Switch Topologies

| Topology | Ron vs. Vin | Linearity Limit | Area | Notes |
|----------|-------------|-----------------|------|-------|
| Plain NMOS | Strong dependence | ~8-bit | Small | Simple; distortion limits high-resolution use |
| CMOS T-gate | Partial cancellation | ~9-bit | 2× NMOS | Cancellation imperfect; higher switch capacitance |
| Bootstrap NMOS | Nearly flat | >12-bit | Moderate | Preferred for SAR ADCs; overhead is the charge pump |

The bootstrap switch trades circuit complexity (charge pump, ~10 transistors) for a flat Ron and high linearity ceiling, making it the standard choice for SAR ADC sampling networks at resolutions of 10 bits and above.

---

## How to Verify a Bootstrap Switch

### Sampling Linearity Test (THD)

The primary figure of merit is harmonic distortion of the sampled output. Testbench setup:

- Apply a sine input through the bootstrap switch into a sampling capacitor (sized to match the target CDAC total capacitance).
- Clock the switch at the target sampling rate Fs.
- Run transient analysis for N complete input cycles (use coherent sampling: `fin = M/N * Fs`, M and N coprime).
- Resample the capacitor voltage at the hold phase of each clock cycle.
- Extract THD using `adctoolbox.analyze_spectrum()` on the resampled output.
- Target: THD < -70 dB for a 10+ bit ADC (each -6 dB of THD costs ~1 ENOB).
- Sweep input amplitude from 10% to 95% of full scale — THD should remain below spec across the range.

### Differential Sampling Testbench (Recommended)

The most realistic verification uses a differential testbench matching the SAR ADC front end:

```
Parameters: A=0.4  CL=1p  Fs=1G  N=128  J=37  Fin=J/N*Fs (coherent)

               VINP ──> LB_BOOTSTRAP ──> VGP ──┐
                                                M0 (nch, W=5u, gate=VGP, S=VINP)
                                                └── D=VSP ──> C_load (100fF)

               VINN ──> LB_BOOTSTRAP ──> VGN ──┐
                                                M1 (nch, W=5u, gate=VGN, S=VINN)
                                                └── D=VSN ──> C_load (100fF)

VINP = Vcm + A*sin(2π*Fin*t)
VINN = Vcm + A*sin(2π*Fin*t + 180°)
CLKS = pulse at Fs, 25% duty cycle
```

This mirrors the real SAR front end: bootstrap only provides gate voltage, external NMOS does the sampling into a capacitive load. The load cap should approximate the total CDAC capacitance.

**Key saves:** `VINP VINN VSP VSN M0:vgs M0:gds M1:vgs M1:gds` — the vgs and gds waveforms directly reveal Ron behavior during sampling.

**Analysis:** Resample VSP and VSN at the hold phase, compute differential (VSP-VSN), run `analyze_spectrum()` to get THD and SNDR. The differential output cancels even-order harmonics and common-mode charge injection.

### Ron vs. Vin Sweep

This directly verifies the bootstrap's core function (constant Vgs):

- Apply a slow ramp input (frequency << Fs) while the switch is held ON.
- At each input level, measure Ron = Vds_switch / Ids_switch.
- Plot Ron vs. Vin across the full input range (0 to VDD).
- Pass criterion: Ron variation < 10% across the input range. A plain NMOS switch will show 2-5x variation over the same range.
- If Ron rises significantly near VDD, the bootstrap capacitor is too small (voltage droop) or parasitic capacitance at CB_TOP is too large.

### Bandwidth and Settling Check

- Apply a step input (e.g., 0 to VDD/2) at the beginning of the sampling phase.
- Measure the time for the sampled output (capacitor voltage) to settle within 0.5 LSB of the final value.
- Settling time must be comfortably less than the sampling phase duration (typically < Tsample/5 for adequate margin).
- Check both small-step (1 LSB) and large-step (full-scale) settling — the large step is the worst case because Ron x Csample is largest.

### Gate Voltage Waveform Verification

- Monitor VGATE (the bootstrap output) over several clock cycles.
- During sampling (CLK high): VGATE should track VIN + VDD. Verify the waveform follows the input with minimal droop (< 2% of VDD over the sampling window).
- During reset (CLK low): VGATE should return to ~0V (switch OFF).
- Check for overshoot: VGATE must not exceed VDD + VIN + 10% at any point, to avoid gate oxide reliability violation on the sampling transistor. For thin-oxide devices, the absolute limit is typically ~1.1x VDD above the source voltage.
- Verify CB voltage: the bootstrap capacitor should charge to VDD during reset and hold that voltage during the sampling phase.

---

## SAR ADC Integration Context

### Output is Gate Voltage, NOT Sampled Voltage

This is the single most important integration fact: the bootstrap switch outputs a **gate voltage** (VBST = VIN + VDD), not a sampled or buffered version of VIN. In a SAR ADC:

```
Bootstrap module:
  Input:  VIN (analog signal), CLK (sample clock)
  Output: VBST = VIN + VDD  (gate drive for CDAC sampling NMOS)

CDAC module:
  M3 (sampling NMOS):  Gate = VBST,  Source = VIN (direct),  Drain = VTOP
```

The input signal VIN connects directly to the CDAC sampling switch source terminal. The bootstrap provides only the gate overdrive. There is no separate sample-and-hold module between the input and the CDAC.

### Differential Operation: Two Bootstrap Instances

In a fully differential SAR ADC, the bootstrap module (L4_BTS_X2) contains two independent LB_SAR_BTS instances, one per input channel:

```
I0 (LB_SAR_BTS):  VIN = VIP  →  VBST = VBTSP  →  I_CDACP.VGBTS
I2 (LB_SAR_BTS):  VIN = VIN  →  VBST = VBTSN  →  I_CDACN.VGBTS
```

Both share the same CLK (= CLKS, the external sample clock) and power supplies (VDD, VSS).

### Connection Summary

| Bootstrap Port | Connected To | Description |
|---------------|-------------|-------------|
| VIP | External VIP, I_CDACP.VIN | Positive input (direct to CDAC source) |
| VIN | External VIN, I_CDACN.VIN | Negative input (direct to CDAC source) |
| CLKS | External sample clock | Shared with SAR logic |
| VBTSP | I_CDACP.VGBTS | Gate voltage for P-side sampling switch |
| VBTSN | I_CDACN.VGBTS | Gate voltage for N-side sampling switch |
| VDD | Supply (0.9V) | Also charges bootstrap capacitor |
| VSS | Ground | |

### Reference Design Transistor Sizing (LB_SAR_BTS)

All transistors in the ZZS bootstrap (TSMC 28nm HPC+, VDD=0.9V):

| Transistor | Type | Gate | Drain | Source | W | L | NF | Role |
|-----------|------|------|-------|--------|---|---|-----|------|
| M5 | nch_ulvt | VBST | net1 | VIN | 4u | 30n | 8 | Sampling switch (connects VIN to CB bottom during sampling) |
| M4 | nch_ulvt | VDD | VBST | CLKP | 4u | 30n | 8 | Cascode protection (limits Vds on M5 gate node) |
| M3 | nch_ulvt | CLKN | CLKP | VSS | 4u | 30n | 8 | Inverter NMOS (generates CLKP from CLKN) |
| M2 | nch_ulvt | CLK | CLKN | VSS | 2u | 30n | 4 | Inverter NMOS (generates CLKN from CLK) |
| M1 | pch_ulvt | CLK | CLKN | VDD | 2u | 30n | 4 | Inverter PMOS (generates CLKN from CLK) |
| M0 | pch_ulvt | net2 | VBST | net33 | 4u | 30n | 8 | Connects CB top (net33) to VBST during sampling |
| M23 | nch_mac | CLK | VDD | VBST | 2u | 30n | 4 | Reset: charges VBST toward VDD during reset |
| M22 | nch_mac | CLKN | net1 | VSS | 1u | 30n | 2 | Reset: discharges CB bottom (net1) to VSS |
| M21 | nch_mac | CLKP | net2 | net1 | 1u | 30n | 2 | Sampling: connects CB bottom (net1) to gate control (net2) |
| M20 | pch_mac | CLKP | net2 | VDD | 1u | 30n | 2 | Reset: charges M0 gate (net2) to VDD (keeps M0 off) |
| M24 | pch_mac | CLKN | CLKP | VDD | 1u | 30n | 2 | Level shifter for CLKP generation |
| M25 | pch_mac | VBST | VDD | net33 | 1u | 30n | 2 | Reset: charges CB top (net33) to VDD |
| C1 | cfmom_2t | -- | net33 (PLUS) | net1 (MINUS) | -- | -- | -- | Bootstrap capacitor (MOM cap) |

Key sizing observations:
- The main switch M5 and cascode M4 are the largest NMOS (4u, 8 fingers) for low Ron
- Inverter transistors M2/M1 (2u, 4 fingers) generate the complementary clock phases
- Reset/control transistors (M20-M25) are smaller (1u, 2 fingers) since speed is not critical during reset
- The bootstrap capacitor C1 uses a `cfmom_2t` (finger-type MOM capacitor from the PDK), providing high density and good matching
- M5 uses `nch_ulvt_mac` for the sampling path (lowest Ron), while M22/M23 use `nch_mac` (standard Vth) for non-critical reset paths
