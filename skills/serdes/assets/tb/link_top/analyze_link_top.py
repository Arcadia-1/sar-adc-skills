#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from End-to-End SerDes Link Top-Level TB.

Usage:
  python analyze_link_top.py <psf_dir> [--ui 100e-12] [--t-skip 8e-9]
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

from psf_utils import eye_diagram_metrics, find_single, parse_psf_ascii


def analyze_link(psf_dir: Path, *, ui: float, t_skip: float) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]

    v_tx = d["TXP"] - d["TXN"]
    v_ch = d["RXP"] - d["RXN"]
    v_eq = d["EQP"] - d["EQN"]
    v_dfe = d["SUMP"] - d["SUMN"]
    v_dout = d["DOUTP"] - d["DOUTN"]
    bit_tx = d["BIT_TX"]

    # Check bit errors across arbitrary channel+pipeline latency (up to 80 UI!)
    t_samp = np.arange(t_skip + 0.5 * ui, float(t[-1]) - 0.5 * ui, ui)
    tx_bits = (np.interp(t_samp, t, bit_tx) >= 0.5).astype(int)
    rx_bits = (np.interp(t_samp + 0.35 * ui, t, v_dout) >= 0.0).astype(int)

    best_err = len(tx_bits)
    best_lag = 0
    for lag in range(0, min(80, len(tx_bits) - 20)):
        errs = int(np.sum(rx_bits[lag:] != tx_bits[: len(tx_bits) - lag]))
        if errs < best_err:
            best_err = errs
            best_lag = lag

    n_checked = max(len(tx_bits) - best_lag, 1)
    return {
        "tx_eye": eye_diagram_metrics(t, v_tx, ui_s=ui, t_skip=t_skip),
        "after_channel_eye": eye_diagram_metrics(t, v_ch, ui_s=ui, t_skip=t_skip),
        "after_ctle_eye": eye_diagram_metrics(t, v_eq, ui_s=ui, t_skip=t_skip),
        "after_dfe_eye": eye_diagram_metrics(t, v_dfe, ui_s=ui, t_skip=t_skip),
        "link_latency_ui": int(best_lag),
        "bits_checked": int(n_checked),
        "bit_errors": int(best_err),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze End-to-End SerDes Link Top-Level outputs.")
    ap.add_argument("psf_dir", type=Path)
    ap.add_argument("--ui", type=float, default=100e-12)
    ap.add_argument("--t-skip", type=float, default=8.0e-9)
    args = ap.parse_args(argv)
    print(json.dumps(analyze_link(args.psf_dir, ui=args.ui, t_skip=args.t_skip), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
