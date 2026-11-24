#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from SerDes Channel testbenches.

Usage:
  python analyze_channel.py sp <psf_dir>
  python analyze_channel.py tdr <psf_dir> [--v-step 0.4] [--z0-diff 100.0]
  python analyze_channel.py sbr_eye <psf_dir> [--ui 100e-12] [--t-skip 4e-9]
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


def analyze_sp(psf_dir: Path) -> dict[str, float]:
    f = find_single(psf_dir, ["sp.sp", "*.sp.sp", "*.sp"])
    d = parse_psf_ascii(f)
    freq = np.real(d["freq"])
    log_f = np.log10(freq)
    mm = mixed_mode_s_params(d, in_p=1, in_n=2, out_p=3, out_n=4)
    sdd21_db = 20.0 * np.log10(np.maximum(np.abs(mm["sdd21"]), 1e-30))
    sdd11_db = 20.0 * np.log10(np.maximum(np.abs(mm["sdd11"]), 1e-30))

    def at(arr: np.ndarray, f_hz: float) -> float:
        return float(np.interp(math.log10(f_hz), log_f, arr))

    m_10g = freq <= 10e9
    return {
        "sdd21_dc_db": float(sdd21_db[0]),
        "sdd21_1ghz_db": at(sdd21_db, 1e9),
        "sdd21_5ghz_db": at(sdd21_db, 5e9),
        "sdd21_7ghz_db": at(sdd21_db, 7e9),
        "sdd21_10ghz_db": at(sdd21_db, 10e9),
        "sdd11_worst_to_10ghz_db": float(np.max(sdd11_db[m_10g])),
        "sdd11_5ghz_db": at(sdd11_db, 5e9),
    }


def analyze_tdr(psf_dir: Path, *, v_step: float, z0_diff: float) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_in = d["TDR_INP"] - d["TDR_INN"]
    # Incident differential step amplitude into matched Z0_diff is v_step (open-circuit = 2*v_step)
    rho = (v_in - v_step) / max(v_step, 1e-9)
    rho_c = np.clip(rho, -0.95, 0.95)
    z_tdr = z0_diff * (1.0 + rho_c) / (1.0 - rho_c)

    # Evaluate transmission-line plateau region (1.2 ns .. 5.0 ns, avoiding launch edge)
    m = (t >= 1.2e-9) & (t <= 5.0e-9)
    zw = z_tdr[m] if np.any(m) else z_tdr
    return {
        "z_tdr_median_ohm": float(np.median(zw)),
        "z_tdr_min_ohm": float(np.min(zw)),
        "z_tdr_max_ohm": float(np.max(zw)),
        "z_tdr_ripple_ohm": float(np.max(zw) - np.min(zw)),
    }


def analyze_sbr_eye(psf_dir: Path, *, ui: float, t_skip: float) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_sbr = d["SBR_OUTP"] - d["SBR_OUTN"]
    v_tx = d["EYE_INP"] - d["EYE_INN"]
    v_rx = d["EYE_OUTP"] - d["EYE_OUTN"]

    sbr = sbr_cursor_metrics(t, v_sbr, ui_s=ui, t_base_end=25.0 * ui)
    tx_eye = eye_diagram_metrics(t, v_tx, ui_s=ui, t_skip=t_skip)
    rx_eye = eye_diagram_metrics(t, v_rx, ui_s=ui, t_skip=t_skip)
    return {
        "sbr": sbr,
        "tx_eye": tx_eye,
        "rx_eye": rx_eye,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze SerDes Channel Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_sp = sub.add_parser("sp")
    p_sp.add_argument("psf_dir", type=Path)

    p_tdr = sub.add_parser("tdr")
    p_tdr.add_argument("psf_dir", type=Path)
    p_tdr.add_argument("--v-step", type=float, default=0.4)
    p_tdr.add_argument("--z0-diff", type=float, default=100.0)

    p_se = sub.add_parser("sbr_eye")
    p_se.add_argument("psf_dir", type=Path)
    p_se.add_argument("--ui", type=float, default=100e-12)
    p_se.add_argument("--t-skip", type=float, default=5.0e-9)

    args = ap.parse_args(argv)
    if args.mode == "sp":
        res: object = analyze_sp(args.psf_dir)
    elif args.mode == "tdr":
        res = analyze_tdr(args.psf_dir, v_step=args.v_step, z0_diff=args.z0_diff)
    else:
        res = analyze_sbr_eye(args.psf_dir, ui=args.ui, t_skip=args.t_skip)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
