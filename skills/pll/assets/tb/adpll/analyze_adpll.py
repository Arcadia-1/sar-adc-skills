#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII output from tb_adpll_lock.scs."""

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

from psf_utils import crossings, find_single, parse_psf_ascii


def analyze_adpll(
    psf_dir: Path, *, f_target: float, vdd: float = 0.9, ss_frac: float = 0.55
) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    ftw = d["FTW"]
    tdc = d["TDC_OUT"]
    finst = d["F_INST"] * 1e9  # va_phase_err_mon outputs GHz (freq_scale=1e-9)

    ss = t >= (ss_frac * float(t[-1]))
    ftw_ss = ftw[ss]
    tdc_ss = tdc[ss]

    edges = np.asarray(crossings(t[ss], d["OUTP"][ss], 0.5 * vdd, "rising"), dtype=float)
    if len(edges) < 10:
        raise RuntimeError(f"Expected >= 10 steady-state DCO edges, got {len(edges)}")
    f_locked = float((len(edges) - 1) / (edges[-1] - edges[0]))
    periods = np.diff(edges)
    per_jit_ps = float(np.std(periods) * 1e12)
    freq_err_ppm = (f_locked - f_target) / f_target * 1e6

    # 0.2% frequency settling time
    tol = 0.002 * f_target
    outside = np.where(np.abs(finst - f_target) > tol)[0]
    if len(outside) == 0:
        t_settle = 0.0
    elif outside[-1] + 1 < len(t):
        t_settle = float(t[outside[-1] + 1])
    else:
        t_settle = float("nan")

    return {
        "f_target_mhz": f_target * 1e-6,
        "f_locked_mhz": f_locked * 1e-6,
        "freq_err_ppm": freq_err_ppm,
        "t_settle_0p2pct_us": t_settle * 1e6 if math.isfinite(t_settle) else float("nan"),
        "ftw_steady_mean": float(np.mean(ftw_ss)),
        "ftw_steady_pp_lsb": float(np.max(ftw_ss) - np.min(ftw_ss)),
        "tdc_steady_rms_lsb": float(np.std(tdc_ss)),
        "period_jitter_ps": per_jit_ps,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze ADPLL Spectre output.")
    ap.add_argument("psf_dir", type=Path)
    ap.add_argument("--f-target", type=float, default=1.0e9)
    ap.add_argument("--vdd", type=float, default=0.9)
    ap.add_argument("--ss-frac", type=float, default=0.55)
    args = ap.parse_args(argv)
    print(
        json.dumps(
            analyze_adpll(
                args.psf_dir, f_target=args.f_target, vdd=args.vdd, ss_frac=args.ss_frac
            ),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
