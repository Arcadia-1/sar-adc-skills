#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from PFD + Charge Pump testbenches.

Usage:
  python analyze_pfd_cp.py transfer <psf_dir> [--vdd 0.9] [--t-ref 20e-9]
  python analyze_pfd_cp.py compliance <psf_dir> [--vdd 0.9] [--v-comp-lo 0.20] [--v-comp-hi 0.65]
  python analyze_pfd_cp.py <psf_dir> [--vdd 0.9] [--t-ref 20e-9]  # legacy alias for transfer
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

from psf_utils import crossings, find_single, parse_psf_ascii, trapz


def analyze_pfd_cp(
    psf_dir: Path, *, vdd: float = 0.9, t_ref: float = 20e-9
) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    i_out = d["VMEAS:p"]  # positive = current sourced INTO IOUT (UP) flows into VMEAS:p
    vth = 0.5 * vdd

    t_ref_edges = crossings(t, d["FREF"], vth, "rising")
    t_div_edges = crossings(t, d["FDIV"], vth, "rising")
    n = min(len(t_ref_edges), len(t_div_edges))
    if n < 5:
        raise RuntimeError(f"Expected >= 5 clock cycles, got {n}")

    dts: list[float] = []
    qs: list[float] = []
    for k in range(n):
        tr_k = t_ref_edges[k]
        td_k = t_div_edges[k]
        dt_k = td_k - tr_k  # positive = FDIV late -> UP current (>0)
        # Integration window centered on this pair of edges
        t0 = min(tr_k, td_k) - 0.2 * t_ref
        t1 = max(tr_k, td_k) + 0.3 * t_ref
        if t0 < t[0] or t1 > t[-1]:
            continue
        mask = (t >= t0) & (t <= t1)
        if np.sum(mask) < 3:
            continue
        q_k = trapz(i_out[mask], t[mask])
        dts.append(dt_k)
        qs.append(q_k)

    dt_arr = np.asarray(dts, dtype=float)
    q_arr = np.asarray(qs, dtype=float)

    # Fit positive side (I_up) and negative side (I_dn) slopes (Q = I * dt)
    pos = dt_arr > 0.25 * np.max(dt_arr)
    neg = dt_arr < 0.25 * np.min(dt_arr)
    if np.sum(pos) < 2 or np.sum(neg) < 2:
        raise RuntimeError("Insufficient positive/negative phase-error points for fit")

    i_up = float(np.polyfit(dt_arr[pos], q_arr[pos], 1)[0])
    i_dn = float(np.polyfit(dt_arr[neg], q_arr[neg], 1)[0])
    i_nom = 0.5 * (i_up + i_dn)
    mismatch_pct = 100.0 * (i_up - i_dn) / i_nom if abs(i_nom) > 1e-12 else float("nan")
    kd_ua_rad = (i_nom / (2.0 * math.pi)) * 1e6

    # Check dead-zone slope across the closest points straddling Delta_t = 0
    idx0 = int(np.argmin(np.abs(dt_arr)))
    q_zero_fc = float(q_arr[idx0] * 1e15)
    lo = max(idx0 - 1, 0)
    hi = min(idx0 + 1, len(dt_arr) - 1)
    slope_zero = float((q_arr[hi] - q_arr[lo]) / (dt_arr[hi] - dt_arr[lo]))
    dead_zone_ratio = slope_zero / i_nom if abs(i_nom) > 1e-12 else 0.0

    return {
        "n_cycles": int(len(dt_arr)),
        "i_up_ua": i_up * 1e6,
        "i_dn_ua": i_dn * 1e6,
        "i_nom_ua": i_nom * 1e6,
        "mismatch_pct": mismatch_pct,
        "kd_ua_per_rad": kd_ua_rad,
        "q_at_zero_fc": q_zero_fc,
        "zero_slope_over_nom": dead_zone_ratio,
        "dead_zone_free": bool(dead_zone_ratio > 0.7),
    }


def _find_comp_bound(
    v: np.ndarray, curr: np.ndarray, v_mid: float, thresh: float, direction: str
) -> float:
    """Interpolate voltage boundary where current drops below `thresh` moving away from v_mid."""
    mid_idx = int(np.argmin(np.abs(v - v_mid)))
    if direction == "down":
        for i in range(mid_idx, 0, -1):
            if curr[i] >= thresh > curr[i - 1]:
                frac = (thresh - curr[i - 1]) / max(curr[i] - curr[i - 1], 1e-18)
                return float(v[i - 1] + frac * (v[i] - v[i - 1]))
        return float(v[0])
    for i in range(mid_idx, len(v) - 1):
        if curr[i] >= thresh > curr[i + 1]:
            frac = (curr[i] - thresh) / max(curr[i] - curr[i + 1], 1e-18)
            return float(v[i] + frac * (v[i + 1] - v[i]))
    return float(v[-1])


def analyze_compliance(
    psf_dir: Path,
    *,
    vdd: float = 0.9,
    v_comp_lo: float = 0.20,
    v_comp_hi: float = 0.65,
) -> dict[str, object]:
    """Extract I_UP(V_CP), I_DN(V_CP), mismatch %, r_o, and 10%-drop compliance window."""
    f_up = find_single(psf_dir, ["dc_up.dc", "*dc_up*.dc"])
    f_dn = find_single(psf_dir, ["dc_dn.dc", "*dc_dn*.dc"])
    d_up = parse_psf_ascii(f_up)
    d_dn = parse_psf_ascii(f_dn)

    vx_key_up = "v_cp" if "v_cp" in d_up else next(k for k in d_up if not k.endswith(":p"))
    vx_key_dn = "v_cp" if "v_cp" in d_dn else next(k for k in d_dn if not k.endswith(":p"))
    v_up = np.real(d_up[vx_key_up])
    v_dn = np.real(d_dn[vx_key_dn])
    ord_u = np.argsort(v_up)
    ord_d = np.argsort(v_dn)
    v_cp = v_up[ord_u]
    i_up = np.real(d_up["VCP:p"])[ord_u]
    i_dn_raw = -np.real(d_dn["VCP:p"])[ord_d]
    i_dn = np.interp(v_cp, v_dn[ord_d], i_dn_raw)

    v_mid = 0.5 * vdd
    i_up_mid = float(np.interp(v_mid, v_cp, i_up))
    i_dn_mid = float(np.interp(v_mid, v_cp, i_dn))
    i_nom_mid = 0.5 * (i_up_mid + i_dn_mid)

    win = (v_cp >= v_comp_lo - 1e-9) & (v_cp <= v_comp_hi + 1e-9)
    if np.sum(win) < 3:
        raise RuntimeError(f"Too few DC sweep points inside [{v_comp_lo}, {v_comp_hi}] V")

    i_avg_w = 0.5 * (i_up[win] + i_dn[win])
    mis_w = 100.0 * np.abs(i_up[win] - i_dn[win]) / np.maximum(np.abs(i_avg_w), 1e-12)
    mis_mid = 100.0 * abs(i_up_mid - i_dn_mid) / max(abs(i_nom_mid), 1e-12)

    # Local output resistance r_o = |dV/dI| around mid-rail (+/-50 mV)
    dv_ro = 0.05
    di_up = abs(
        float(np.interp(v_mid + dv_ro, v_cp, i_up)) - float(np.interp(v_mid - dv_ro, v_cp, i_up))
    )
    di_dn = abs(
        float(np.interp(v_mid + dv_ro, v_cp, i_dn)) - float(np.interp(v_mid - dv_ro, v_cp, i_dn))
    )
    ro_up_kohm = (2.0 * dv_ro / di_up) * 1e-3 if di_up > 1e-15 else 1e9
    ro_dn_kohm = (2.0 * dv_ro / di_dn) * 1e-3 if di_dn > 1e-15 else 1e9

    # 10% current-drop compliance boundaries
    v_min_eff = _find_comp_bound(v_cp, i_dn, v_mid, 0.90 * i_dn_mid, "down")
    v_max_eff = _find_comp_bound(v_cp, i_up, v_mid, 0.90 * i_up_mid, "up")
    comp_span = max(v_max_eff - v_min_eff, 0.0)

    return {
        "n_pts": int(len(v_cp)),
        "v_mid_v": v_mid,
        "i_up_mid_ua": i_up_mid * 1e6,
        "i_dn_mid_ua": i_dn_mid * 1e6,
        "i_nom_mid_ua": i_nom_mid * 1e6,
        "v_comp_window_v": [float(v_comp_lo), float(v_comp_hi)],
        "mismatch_mid_pct": float(mis_mid),
        "mismatch_mean_pct": float(np.mean(mis_w)),
        "mismatch_max_pct": float(np.max(mis_w)),
        "ro_up_kohm": float(ro_up_kohm),
        "ro_dn_kohm": float(ro_dn_kohm),
        "v_comp_min_eff_v": v_min_eff,
        "v_comp_max_eff_v": v_max_eff,
        "compliance_span_v": comp_span,
        "compliance_pass": bool(v_min_eff <= v_comp_lo + 1e-6 and v_max_eff >= v_comp_hi - 1e-6),
    }


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    # Preserve backward compatibility: `analyze_pfd_cp.py <psf_dir> ...` defaults to `transfer`
    if raw_argv and raw_argv[0] not in ("transfer", "compliance", "-h", "--help"):
        raw_argv = ["transfer", *raw_argv]

    ap = argparse.ArgumentParser(description="Analyze PFD+CP Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_tr = sub.add_parser("transfer", help="Analyze beat-sweep transfer from tb_pfd_cp_transfer.scs")
    p_tr.add_argument("psf_dir", type=Path)
    p_tr.add_argument("--vdd", type=float, default=0.9)
    p_tr.add_argument("--t-ref", type=float, default=20e-9)

    p_cm = sub.add_parser(
        "compliance", help="Analyze DC compliance & mismatch from tb_cp_compliance_mismatch.scs"
    )
    p_cm.add_argument("psf_dir", type=Path)
    p_cm.add_argument("--vdd", type=float, default=0.9)
    p_cm.add_argument("--v-comp-lo", type=float, default=0.20)
    p_cm.add_argument("--v-comp-hi", type=float, default=0.65)

    args = ap.parse_args(raw_argv)
    if args.mode == "compliance":
        res = analyze_compliance(
            args.psf_dir, vdd=args.vdd, v_comp_lo=args.v_comp_lo, v_comp_hi=args.v_comp_hi
        )
    else:
        res = analyze_pfd_cp(args.psf_dir, vdd=args.vdd, t_ref=args.t_ref)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
