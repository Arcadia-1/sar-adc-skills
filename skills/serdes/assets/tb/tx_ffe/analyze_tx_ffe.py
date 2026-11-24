#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from SerDes TX & FFE testbenches.

Usage:
  python analyze_tx_ffe.py s11 <psf_dir>
  python analyze_tx_ffe.py dc_term <psf_dir> [--r-target 50.0]
  python analyze_tx_ffe.py eye <psf_dir> [--ui 100e-12] [--t-skip 5e-9]
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

from psf_utils import (
    eye_diagram_metrics,
    find_single,
    mixed_mode_s_params,
    parse_psf_ascii,
    sbr_cursor_metrics,
)


def analyze_s11(psf_dir: Path) -> dict[str, float]:
    f = find_single(psf_dir, ["sp.sp", "*.sp.sp", "*.sp"])
    d = parse_psf_ascii(f)
    freq = np.real(d["freq"])
    log_f = np.log10(freq)
    mm = mixed_mode_s_params(d, in_p=1, in_n=2, out_p=None, out_n=None)
    sdd11_db = 20.0 * np.log10(np.maximum(np.abs(mm["sdd11"]), 1e-30))

    def at(f_hz: float) -> float:
        return float(np.interp(math.log10(f_hz), log_f, sdd11_db))

    m_5g = freq <= 5e9
    m_10g = freq <= 10e9
    return {
        "sdd11_dc_db": float(sdd11_db[0]),
        "sdd11_1ghz_db": at(1e9),
        "sdd11_5ghz_db": at(5e9),
        "sdd11_10ghz_db": at(10e9),
        "sdd11_worst_to_5ghz_db": float(np.max(sdd11_db[m_5g])),
        "sdd11_worst_to_10ghz_db": float(np.max(sdd11_db[m_10g])),
    }


def analyze_eye(psf_dir: Path, *, ui: float, t_skip: float) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_tx = d["TXP"] - d["TXN"]
    v_rx = d["RXP"] - d["RXN"]
    v_sbr = d["SRXP"] - d["SRXN"]

    return {
        "tx_swing_pp_mv": float((np.max(v_tx[t >= t_skip]) - np.min(v_tx[t >= t_skip])) * 1e3),
        "rx_eye": eye_diagram_metrics(t, v_rx, ui_s=ui, t_skip=t_skip),
        "rx_sbr": sbr_cursor_metrics(t, v_sbr, ui_s=ui, t_base_end=25.0 * ui),
    }


def analyze_dc_term(psf_dir: Path, *, r_target: float) -> dict[str, float]:
    f = find_single(psf_dir, ["dc_term.dc", "*term*.dc", "*.dc"])
    d = parse_psf_ascii(f)
    v = d["OUTP"]
    # Current leaving VPRB_P into OUTP is -VPRB_P:p (Spectre passive sign convention)
    i_in = -d["VPRB_P:p"]
    dv = np.diff(v)
    di = np.diff(i_in)
    r_inc = np.abs(dv / np.where(np.abs(di) > 1e-15, di, np.nan))
    r_inc = r_inc[np.isfinite(r_inc)]
    r_med = float(np.median(r_inc))
    r_min = float(np.min(r_inc))
    r_max = float(np.max(r_inc))
    return {
        "r_target_ohm": r_target,
        "r_median_ohm": r_med,
        "r_min_ohm": r_min,
        "r_max_ohm": r_max,
        "r_err_max_pct": float(max(abs(r_min - r_target), abs(r_max - r_target)) / r_target * 100.0),
        "r_flatness_pct": float((r_max - r_min) / max(r_med, 1e-9) * 100.0),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze SerDes TX & FFE Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_s11 = sub.add_parser("s11")
    p_s11.add_argument("psf_dir", type=Path)

    p_dt = sub.add_parser("dc_term")
    p_dt.add_argument("psf_dir", type=Path)
    p_dt.add_argument("--r-target", type=float, default=50.0)

    p_eye = sub.add_parser("eye")
    p_eye.add_argument("psf_dir", type=Path)
    p_eye.add_argument("--ui", type=float, default=100e-12)
    p_eye.add_argument("--t-skip", type=float, default=5.0e-9)

    args = ap.parse_args(argv)
    if args.mode == "s11":
        res: object = analyze_s11(args.psf_dir)
    elif args.mode == "dc_term":
        res = analyze_dc_term(args.psf_dir, r_target=args.r_target)
    else:
        res = analyze_eye(args.psf_dir, ui=args.ui, t_skip=args.t_skip)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
