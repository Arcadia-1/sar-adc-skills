#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from SerDes Sign-Sign LMS adaptation TB.

Usage:
  python analyze_sslms.py <psf_dir> [--ui 100e-12] [--h0 0.25] [--h1 0.11] [--h2 0.05] [--h3 0.02] [--vref 0.40]
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


def analyze_sslms(
    psf_dir: Path, *, ui: float, h0: float, h1: float, h2: float, h3: float, vref: float
) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    t_end = float(t[-1])
    tail = t >= 0.85 * t_end

    g_fin = float(np.mean(d["W_GAIN"][tail]))
    h1_fin = float(np.mean(d["W_H1"][tail]))
    h2_fin = float(np.mean(d["W_H2"][tail]))
    h3_fin = float(np.mean(d["W_H3"][tail]))

    g_tgt = vref / h0
    h1_tgt = g_tgt * h1
    h2_tgt = g_tgt * h2
    h3_tgt = g_tgt * h3

    v_ch = d["CHP"] - d["CHN"]
    v_sum = d["SUMP"] - d["SUMN"]
    eye_raw = eye_diagram_metrics(t, v_ch, ui_s=ui, t_skip=0.80 * t_end)
    eye_eq = eye_diagram_metrics(t, v_sum, ui_s=ui, t_skip=0.80 * t_end)

    return {
        "gain_final": g_fin,
        "gain_target": g_tgt,
        "h1_final_mv": h1_fin * 1e3,
        "h1_target_mv": h1_tgt * 1e3,
        "h2_final_mv": h2_fin * 1e3,
        "h2_target_mv": h2_tgt * 1e3,
        "h3_final_mv": h3_fin * 1e3,
        "h3_target_mv": h3_tgt * 1e3,
        "done_flags": {
            "gain": bool(float(d["DONE_G"][-1]) > 0.5),
            "h1": bool(float(d["DONE_H1"][-1]) > 0.5),
            "h2": bool(float(d["DONE_H2"][-1]) > 0.5),
            "h3": bool(float(d["DONE_H3"][-1]) > 0.5),
        },
        "raw_channel_eye_height_mv": eye_raw["eye_height_mv"],
        "converged_equalized_eye_height_mv": eye_eq["eye_height_mv"],
        "converged_equalized_eye_width_ui": eye_eq["eye_width_ui"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze SerDes Sign-Sign LMS Spectre outputs.")
    ap.add_argument("psf_dir", type=Path)
    ap.add_argument("--ui", type=float, default=100e-12)
    ap.add_argument("--h0", type=float, default=0.25)
    ap.add_argument("--h1", type=float, default=0.11)
    ap.add_argument("--h2", type=float, default=0.05)
    ap.add_argument("--h3", type=float, default=0.02)
    ap.add_argument("--vref", type=float, default=0.40)
    args = ap.parse_args(argv)
    print(
        json.dumps(
            analyze_sslms(
                args.psf_dir,
                ui=args.ui,
                h0=args.h0,
                h1=args.h1,
                h2=args.h2,
                h3=args.h3,
                vref=args.vref,
            ),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
