#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from R-2R Ladder DAC testbenches.

Usage:
  python analyze_r2r.py static <psf_dir> [--n-codes 256] [--vref 1.0]
  python analyze_r2r.py settle <psf_dir> [--t-fs 50e-9] [--t-prep 250e-9] [--t-mc 450e-9] [--vref 1.0]
"""

from __future__ import annotations

import argparse
import json
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

from psf_utils import (
    dnl_inl_from_transfer,
    extract_uniform_strobe,
    find_single,
    parse_psf_ascii,
)


def analyze_static(psf_dir: Path, *, n_codes: int, vref: float) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, vout, cm = extract_uniform_strobe(d["time"], d["VOUT"], d["CODE_MON"])
    if len(vout) < n_codes:
        raise RuntimeError(f"Expected at least {n_codes} strobed codes, got {len(vout)}")

    codes = np.round(cm).astype(int)
    levels = np.empty(n_codes, dtype=float)
    for c in range(n_codes):
        idx = np.where(codes == c)[0]
        if len(idx) == 0:
            raise RuntimeError(f"Missing code {c} in R-2R static sweep")
        levels[c] = float(vout[idx[-1]])

    m = dnl_inl_from_transfer(levels)
    ideal_fs = vref * (n_codes - 1) / n_codes
    gain_err_pct = (m["full_scale_v"] - ideal_fs) / ideal_fs * 100.0
    return {
        "n_codes": int(n_codes),
        "zero_code_mv": float(levels[0] * 1e3),
        "full_scale_v": m["full_scale_v"],
        "lsb_mv": m["lsb_v"] * 1e3,
        "gain_err_pct": float(gain_err_pct),
        "dnl_max_lsb": m["dnl_max_lsb"],
        "dnl_min_lsb": m["dnl_min_lsb"],
        "dnl_abs_max_lsb": m["dnl_abs_max_lsb"],
        "inl_max_lsb": m["inl_max_lsb"],
        "inl_min_lsb": m["inl_min_lsb"],
        "inl_abs_max_lsb": m["inl_abs_max_lsb"],
        "monotonic": bool(m["dnl_min_lsb"] > -1.0),
    }


def _settle_time(
    t: np.ndarray, v: np.ndarray, t_start: float, t_end: float, tol_v: float
) -> tuple[float, float, float]:
    pre_m = (t >= t_start - 20e-9) & (t <= t_start - 2e-9)
    post_m = (t >= t_end - 20e-9) & (t <= t_end - 2e-9)
    v_pre = float(np.mean(v[pre_m]))
    v_post = float(np.mean(v[post_m]))

    win_m = (t >= t_start) & (t <= t_end - 5e-9)
    tw, vw = t[win_m], v[win_m]
    outside = np.where(np.abs(vw - v_post) > tol_v)[0]
    t_set = float(tw[outside[-1] + 1] - t_start) if (len(outside) > 0 and outside[-1] + 1 < len(tw)) else 0.0
    return v_pre, v_post, t_set


def analyze_settle(
    psf_dir: Path, *, t_fs: float, t_prep: float, t_mc: float, vref: float, n_bits: int
) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v = d["VOUT"]
    t_stop = float(t[-1])
    lsb_v = vref / (2**n_bits)
    tol = 0.5 * lsb_v

    vp0, vp1, t_set_fs = _settle_time(t, v, t_fs, t_prep, tol)
    vm0, vm1, t_set_mc = _settle_time(t, v, t_mc, t_stop, tol)
    return {
        "lsb_mv": lsb_v * 1e3,
        "fs_step_v": vp1 - vp0,
        "fs_t_settle_0p5lsb_ns": t_set_fs * 1e9,
        "mc_step_mv": (vm1 - vm0) * 1e3,
        "mc_t_settle_0p5lsb_ns": t_set_mc * 1e9,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze R-2R Ladder DAC Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_st = sub.add_parser("static")
    p_st.add_argument("psf_dir", type=Path)
    p_st.add_argument("--n-codes", type=int, default=256)
    p_st.add_argument("--vref", type=float, default=1.0)

    p_se = sub.add_parser("settle")
    p_se.add_argument("psf_dir", type=Path)
    p_se.add_argument("--t-fs", type=float, default=50e-9)
    p_se.add_argument("--t-prep", type=float, default=250e-9)
    p_se.add_argument("--t-mc", type=float, default=450e-9)
    p_se.add_argument("--vref", type=float, default=1.0)
    p_se.add_argument("--n-bits", type=int, default=8)

    args = ap.parse_args(argv)
    if args.mode == "static":
        res: object = analyze_static(args.psf_dir, n_codes=args.n_codes, vref=args.vref)
    else:
        res = analyze_settle(
            args.psf_dir,
            t_fs=args.t_fs,
            t_prep=args.t_prep,
            t_mc=args.t_mc,
            vref=args.vref,
            n_bits=args.n_bits,
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
