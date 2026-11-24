#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from Integer-N CP-PLL testbenches.

Usage:
  python analyze_int_n_pll.py ac_loop <psf_dir>
  python analyze_int_n_pll.py lock <psf_dir> [--f-target 1e9] [--f-ref 50e6] [--kvco 200e6] [--vdd 0.9]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

COMMON_DIR = next(
    p / "common"
    for p in Path(__file__).resolve().parents
    if (p / "common" / "psf_utils.py").exists()
)
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from psf_utils import crossings, find_single, parse_psf_ascii


def analyze_ac_loop(psf_dir: Path) -> dict[str, float]:
    f_stb = find_single(psf_dir, ["stb.stb", "*.stb.stb"])
    ds = parse_psf_ascii(f_stb)
    freq = np.real(ds["freq"])
    lg = ds["loopGain"]
    # Normalize probe polarity so low-frequency phase of Type-II loop starts near -180 deg
    # (or 0 deg in Spectre negative-feedback convention where PM = 180 + phase)
    if np.real(lg[0]) > 0 and np.imag(lg[0]) > 0:
        lg = -lg
    # Actually in Type-II loop, L(s) ~ K / s^2 at low freq -> real(L) < 0, imag(L) > 0, phase ~ -180 -> +180.
    # For consistent PM extraction matching Spectre stb, use angle in [-180, +180]:
    mag_db = 20.0 * np.log10(np.maximum(np.abs(lg), 1e-30))

    # Find unity-gain crossing (first downward 0 dB crossing)
    fu_hz = float("nan")
    pm_deg = float("nan")
    for i in range(len(mag_db) - 1):
        if mag_db[i] >= 0.0 > mag_db[i + 1]:
            frac = (0.0 - mag_db[i]) / (mag_db[i + 1] - mag_db[i])
            fu_hz = float(10.0 ** (math.log10(freq[i]) + frac * (math.log10(freq[i + 1]) - math.log10(freq[i]))))
            lg_u = lg[i] + frac * (lg[i + 1] - lg[i])
            # Distance of loopGain(fu) from the unstable point (-1 + 0j):
            # In Spectre stb, loopGain = -T(s) or +T(s); phase margin is angle from -180 deg.
            ang_deg = math.degrees(math.atan2(lg_u.imag, lg_u.real))
            # Map angle relative to -180 deg into [0, 180]
            pm_deg = (ang_deg + 180.0) % 360.0
            if pm_deg > 180.0:
                pm_deg = 360.0 - pm_deg
            break

    # AC closed-loop peaking and -3 dB bandwidth
    f_ac = find_single(psf_dir, ["ac.ac", "*.ac.ac", "*.ac"])
    da = parse_psf_ascii(f_ac)
    freq_ac = np.real(da["freq"])
    h_cl = np.abs(da["PHI_FB"]) / np.maximum(np.abs(da["PHI_REF"]), 1e-30)
    h_db = 20.0 * np.log10(np.maximum(h_cl, 1e-30))
    peaking_db = float(np.max(h_db) - h_db[0])

    f_3db = float("nan")
    target_db = float(h_db[0] - 3.0)
    for i in range(len(h_db) - 1):
        if h_db[i] >= target_db > h_db[i + 1]:
            frac = (target_db - h_db[i]) / (h_db[i + 1] - h_db[i])
            f_3db = float(10.0 ** (math.log10(freq_ac[i]) + frac * (math.log10(freq_ac[i + 1]) - math.log10(freq_ac[i]))))
            break

    return {
        "fu_mhz": fu_hz * 1e-6 if math.isfinite(fu_hz) else float("nan"),
        "phase_margin_deg": pm_deg,
        "cl_peaking_db": peaking_db,
        "cl_bw_3db_mhz": f_3db * 1e-6 if math.isfinite(f_3db) else float("nan"),
    }


def analyze_lock(
    psf_dir: Path, *, f_target: float, f_ref: float, kvco: float, vdd: float
) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vctrl = d["VCTRL"]
    finst = d["F_INST"] * 1e9  # va_phase_err_mon outputs GHz (freq_scale=1e-9)

    # Steady-state window = final 25% of simulation
    t_ss = 0.75 * float(t[-1])
    ss = t >= t_ss
    vctrl_ss = vctrl[ss]
    vctrl_mean = float(np.mean(vctrl_ss))
    vctrl_ripple_pp = float(np.max(vctrl_ss) - np.min(vctrl_ss))

    # Exact average locked frequency by counting OUTP rising edges in steady state
    edges = np.asarray(crossings(t[ss], d["OUTP"][ss], 0.5 * vdd, "rising"), dtype=float)
    if len(edges) >= 4:
        f_locked = float((len(edges) - 1) / (edges[-1] - edges[0]))
        per_jit_ps = float(np.std(np.diff(edges)) * 1e12)
    else:
        f_locked = float(np.mean(finst[ss]))
        per_jit_ps = float("nan")

    freq_err_ppm = (f_locked - f_target) / f_target * 1e6

    # 0.1% frequency settling time
    tol = 0.001 * f_target
    outside = np.where(np.abs(finst - f_target) > tol)[0]
    if len(outside) == 0:
        t_settle = 0.0
    elif outside[-1] + 1 < len(t):
        t_settle = float(t[outside[-1] + 1])
    else:
        t_settle = float("nan")

    # Narrowband FM reference spur estimate from sinusoidal approximation V_pk = V_pp / 2
    v_pk = 0.5 * vctrl_ripple_pp
    ref_spur_dbc = (
        20.0 * math.log10(max((kvco * v_pk) / (2.0 * f_ref), 1e-12))
        if v_pk > 0.0
        else -200.0
    )

    return {
        "f_target_mhz": f_target * 1e-6,
        "f_locked_mhz": f_locked * 1e-6,
        "freq_err_ppm": freq_err_ppm,
        "t_settle_0p1pct_us": t_settle * 1e6 if math.isfinite(t_settle) else float("nan"),
        "vctrl_mean_v": vctrl_mean,
        "vctrl_ripple_pp_mv": vctrl_ripple_pp * 1e3,
        "est_ref_spur_dbc": ref_spur_dbc,
        "period_jitter_ps": per_jit_ps,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze Integer-N PLL Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_ac = sub.add_parser("ac_loop", help="Extract f_u, PM, peaking, 3dB BW from tb_int_n_pll_ac_loop.scs")
    p_ac.add_argument("psf_dir", type=Path)

    p_lk = sub.add_parser("lock", help="Extract lock freq, settling time, VCTRL ripple from tb_int_n_pll_lock.scs")
    p_lk.add_argument("psf_dir", type=Path)
    p_lk.add_argument("--f-target", type=float, default=1.0e9)
    p_lk.add_argument("--f-ref", type=float, default=50.0e6)
    p_lk.add_argument("--kvco", type=float, default=200.0e6)
    p_lk.add_argument("--vdd", type=float, default=0.9)

    args = ap.parse_args(argv)
    if args.mode == "ac_loop":
        res = analyze_ac_loop(args.psf_dir)
    else:
        res = analyze_lock(
            args.psf_dir,
            f_target=args.f_target,
            f_ref=args.f_ref,
            kvco=args.kvco,
            vdd=args.vdd,
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
