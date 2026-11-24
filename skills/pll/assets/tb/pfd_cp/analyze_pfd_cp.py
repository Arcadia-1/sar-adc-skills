#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII output from tb_pfd_cp_transfer.scs.

Integrates CP output current per reference cycle across the swept Delta_t range
to extract K_d, Up/Down current mismatch, zero-phase charge offset, and dead-zone status.
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze PFD+CP transfer testbench PSF.")
    ap.add_argument("psf_dir", type=Path)
    ap.add_argument("--vdd", type=float, default=0.9)
    ap.add_argument("--t-ref", type=float, default=20e-9)
    args = ap.parse_args(argv)
    print(json.dumps(analyze_pfd_cp(args.psf_dir, vdd=args.vdd, t_ref=args.t_ref), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
