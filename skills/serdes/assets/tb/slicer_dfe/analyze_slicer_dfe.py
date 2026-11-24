#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from SerDes Slicer & DFE testbenches.

Usage:
  python analyze_slicer_dfe.py vtf <psf_dir>
  python analyze_slicer_dfe.py dfe_eye <psf_dir> [--ui 100e-12] [--t-skip 2e-9]
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
    eye_diagram_metrics,
    extract_uniform_strobe,
    find_single,
    parse_psf_ascii,
)


def analyze_vtf(psf_dir: Path) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t, inp, inn, dp, dn = extract_uniform_strobe(
        d["time"], d["INP"], d["INN"], d["DOUTP"], d["DOUTN"]
    )
    vin = inp - inn
    vout = dp - dn

    # Split at triangle peak (ascending half vs. descending half)
    idx_pk = int(np.argmax(vin))
    vin_up, vout_up = vin[: idx_pk + 1], vout[: idx_pk + 1]
    vin_dn, vout_dn = vin[idx_pk:], vout[idx_pk:]

    def find_th(x: np.ndarray, y: np.ndarray, rising: bool) -> float:
        for i in range(len(y) - 1):
            if rising and y[i] <= 0.0 < y[i + 1]:
                return float(0.5 * (x[i] + x[i + 1]))
            if (not rising) and y[i] >= 0.0 > y[i + 1]:
                return float(0.5 * (x[i] + x[i + 1]))
        return float("nan")

    v_up = find_th(vin_up, vout_up, rising=True)
    v_dn = find_th(vin_dn, vout_dn, rising=False)
    return {
        "n_points": float(len(t)),
        "v_th_up_mv": v_up * 1e3,
        "v_th_dn_mv": v_dn * 1e3,
        "offset_mv": 0.5 * (v_up + v_dn) * 1e3,
        "hysteresis_mv": (v_up - v_dn) * 1e3,
        "out_swing_diff_mv": float((np.max(vout) - np.min(vout)) * 1e3),
    }


def analyze_dfe_eye(psf_dir: Path, *, ui: float, t_skip: float) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_before = d["CH_INP"] - d["CH_INN"]
    v_after = d["SUMP"] - d["SUMN"]
    v_dout = d["DOUTP"] - d["DOUTN"]
    bit_tx = d["BIT_TX"]

    # Sample TX and RX bits once per UI after t_skip and find best integer-UI latency alignment
    t_samp = np.arange(t_skip + 0.5 * ui, float(t[-1]) - 0.5 * ui, ui)
    tx_bits = (np.interp(t_samp, t, bit_tx) >= 0.5).astype(int)
    rx_bits = (np.interp(t_samp + 0.45 * ui, t, v_dout) >= 0.0).astype(int)

    best_err = len(tx_bits)
    best_lag = 0
    for lag in range(0, 6):
        if len(tx_bits) - lag < 20:
            continue
        errs = int(np.sum(rx_bits[lag:] != tx_bits[: len(tx_bits) - lag]))
        if errs < best_err:
            best_err = errs
            best_lag = lag

    n_checked = max(len(tx_bits) - best_lag, 1)
    return {
        "before_dfe_eye": eye_diagram_metrics(t, v_before, ui_s=ui, t_skip=t_skip),
        "after_dfe_eye": eye_diagram_metrics(t, v_after, ui_s=ui, t_skip=t_skip),
        "bit_latency_ui": int(best_lag),
        "bits_checked": int(n_checked),
        "bit_errors": int(best_err),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze SerDes Slicer & DFE Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_vtf = sub.add_parser("vtf")
    p_vtf.add_argument("psf_dir", type=Path)

    p_dfe = sub.add_parser("dfe_eye")
    p_dfe.add_argument("psf_dir", type=Path)
    p_dfe.add_argument("--ui", type=float, default=100e-12)
    p_dfe.add_argument("--t-skip", type=float, default=2.0e-9)

    args = ap.parse_args(argv)
    if args.mode == "vtf":
        res: object = analyze_vtf(args.psf_dir)
    else:
        res = analyze_dfe_eye(args.psf_dir, ui=args.ui, t_skip=args.t_skip)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
