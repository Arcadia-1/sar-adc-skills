#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from ADPLL TDC and DCO testbenches.

Usage:
  python analyze_tdc_dco.py tdc <psf_dir> [--dt-step 10e-12] [--n-half 40]
  python analyze_tdc_dco.py dco <psf_dir>
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

from psf_utils import extract_uniform_strobe, find_single, parse_psf_ascii


def analyze_tdc(psf_dir: Path, *, dt_step: float, n_half: int) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, codes = extract_uniform_strobe(d["time"], d["TDC_OUT"])
    n_expected = 2 * n_half + 1
    if len(codes) < n_expected:
        raise RuntimeError(f"Expected >= {n_expected} strobed points, got {len(codes)}")
    codes = codes[:n_expected]
    dts = (np.arange(n_expected, dtype=float) - n_half) * dt_step

    slope, intercept = np.polyfit(dts, codes, 1)  # codes per second
    t_res_meas = 1.0 / slope if abs(slope) > 1e-3 else float("nan")
    offset_s = -intercept / slope if abs(slope) > 1e-3 else float("nan")
    ideal_codes = slope * dts + intercept
    inl = codes - ideal_codes
    steps = np.diff(codes)
    ideal_step = slope * dt_step
    dnl = steps / ideal_step - 1.0 if abs(ideal_step) > 1e-9 else np.zeros_like(steps)

    return {
        "n_pts": int(n_expected),
        "t_res_meas_ps": float(t_res_meas * 1e12),
        "offset_ps": float(offset_s * 1e12),
        "code_min": float(np.min(codes)),
        "code_max": float(np.max(codes)),
        "dnl_abs_max_lsb": float(np.max(np.abs(dnl))),
        "inl_abs_max_lsb": float(np.max(np.abs(inl))),
        "monotonic": bool(np.all(steps >= -1e-6)),
    }


def analyze_dco(psf_dir: Path) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, ftw, finst_ghz = extract_uniform_strobe(d["time"], d["FTW"], d["F_INST"])
    finst = finst_ghz * 1e9  # va_phase_err_mon outputs GHz (freq_scale=1e-9)
    if len(ftw) < 2:
        raise RuntimeError(f"Expected >= 2 strobed DCO points, got {len(ftw)}")

    df = np.diff(finst)
    dftw = np.diff(ftw)
    kdco = df / dftw  # Hz/LSB
    k_avg = float((finst[-1] - finst[0]) / (ftw[-1] - ftw[0]))

    return {
        "n_pts": int(len(ftw)),
        "f_min_mhz": float(np.min(finst) * 1e-6),
        "f_max_mhz": float(np.max(finst) * 1e-6),
        "k_dco_avg_khz_per_lsb": k_avg * 1e-3,
        "k_dco_min_khz_per_lsb": float(np.min(kdco) * 1e-3),
        "k_dco_max_khz_per_lsb": float(np.max(kdco) * 1e-3),
        "monotonic": bool(np.all(df > 0) or np.all(df < 0)),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze ADPLL TDC/DCO Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_tdc = sub.add_parser("tdc", help="Extract TDC t_res, offset, DNL/INL from tb_tdc_transfer.scs")
    p_tdc.add_argument("psf_dir", type=Path)
    p_tdc.add_argument("--dt-step", type=float, default=10e-12)
    p_tdc.add_argument("--n-half", type=int, default=40)

    p_dco = sub.add_parser("dco", help="Extract DCO K_DCO and monotonicity from tb_dco_tuning.scs")
    p_dco.add_argument("psf_dir", type=Path)

    args = ap.parse_args(argv)
    if args.mode == "tdc":
        res = analyze_tdc(args.psf_dir, dt_step=args.dt_step, n_half=args.n_half)
    else:
        res = analyze_dco(args.psf_dir)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
