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
