#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from SerDes Slicer & DFE testbenches.

Usage:
  python analyze_slicer_dfe.py vtf <psf_dir>
  python analyze_slicer_dfe.py noise_tran <psf_dir> [--vid-in 1.5e-3] [--vos 0.0]
  python analyze_slicer_dfe.py dfe_eye <psf_dir> [--ui 100e-12] [--t-skip 2e-9]
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


def _norm_ppf(p: float) -> float:
    """Inverse standard normal CDF Phi^-1(p) via bisection on math.erf."""
    lo, hi = -8.0, 8.0
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        cdf = 0.5 * (1.0 + math.erf(mid / math.sqrt(2.0)))
        if cdf < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def analyze_noise_tran(psf_dir: Path, *, vid_in: float, vos: float) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, dp, dn = extract_uniform_strobe(d["time"], d["DOUTP"], d["DOUTN"])
    vout = dp - dn
    # Drop initial startup sample if any
    if len(vout) > 10:
        vout = vout[1:]
    n_tot = len(vout)
    n_ones = int(np.sum(vout > 0.0))
    p_one = n_ones / max(n_tot, 1)
    # Clamp slightly away from 0/1 to keep probit finite
    p_clamped = min(max(p_one, 0.5 / max(n_tot, 1)), 1.0 - 0.5 / max(n_tot, 1))
    z = _norm_ppf(p_clamped)
    sigma_n = abs(vid_in - vos) / abs(z) if abs(z) > 1e-6 else float("nan")
    # Q = 7.0345 for BER = 1e-12 (single-sided Gaussian tail)
    sens_1e12 = 7.0345 * sigma_n if math.isfinite(sigma_n) else float("nan")
    return {
        "n_cycles": float(n_tot),
        "n_ones": float(n_ones),
        "p_one": float(p_one),
        "z_probit": float(z),
        "vid_in_mv": vid_in * 1e3,
        "sigma_n_mvrms": sigma_n * 1e3,
        "ber_1e12_half_eye_mv": sens_1e12 * 1e3,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze SerDes Slicer & DFE Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_vtf = sub.add_parser("vtf")
    p_vtf.add_argument("psf_dir", type=Path)

    p_nt = sub.add_parser("noise_tran")
    p_nt.add_argument("psf_dir", type=Path)
    p_nt.add_argument("--vid-in", type=float, default=1.5e-3)
    p_nt.add_argument("--vos", type=float, default=0.0)

    p_dfe = sub.add_parser("dfe_eye")
    p_dfe.add_argument("psf_dir", type=Path)
    p_dfe.add_argument("--ui", type=float, default=100e-12)
    p_dfe.add_argument("--t-skip", type=float, default=2.0e-9)

    args = ap.parse_args(argv)
    if args.mode == "vtf":
        res: object = analyze_vtf(args.psf_dir)
    elif args.mode == "noise_tran":
        res = analyze_noise_tran(args.psf_dir, vid_in=args.vid_in, vos=args.vos)
    else:
        res = analyze_dfe_eye(args.psf_dir, ui=args.ui, t_skip=args.t_skip)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
