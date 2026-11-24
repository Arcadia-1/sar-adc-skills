#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII output from tb_div_func_mmd.scs."""

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

from psf_utils import crossings, find_single, parse_psf_ascii


def analyze_divider(
    psf_dir: Path, *, f_in: float = 1.0e9, vdd: float = 0.9, n_expected: float | None = None
) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    edges = np.asarray(crossings(t, d["CLK_OUT"], 0.5 * vdd, "rising"), dtype=float)
    if len(edges) < 5:
        raise RuntimeError(f"Expected >= 5 divided edges, got {len(edges)}")

    # Discard first cycle startup transient
    edges = edges[1:]
    periods = np.diff(edges)
    ratios = periods * f_in
    # Exact long-term average ratio from total elapsed time / cycles
    n_avg = float((edges[-1] - edges[0]) * f_in / (len(edges) - 1))

    res: dict[str, object] = {
        "n_cycles": int(len(periods)),
        "n_avg": n_avg,
        "n_min_inst": float(np.min(ratios)),
        "n_max_inst": float(np.max(ratios)),
        "n_std_inst": float(np.std(ratios)),
        "f_out_avg_mhz": float((f_in / n_avg) * 1e-6),
    }
    if n_expected is not None:
        err_ppm = (n_avg - n_expected) / n_expected * 1e6
        res["n_expected"] = float(n_expected)
        res["ratio_err_ppm"] = float(err_ppm)
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze divider / MMD Spectre output.")
    ap.add_argument("psf_dir", type=Path)
    ap.add_argument("--f-in", type=float, default=1.0e9)
    ap.add_argument("--vdd", type=float, default=0.9)
    ap.add_argument("--n-expected", type=float, default=None)
    args = ap.parse_args(argv)
    print(
        json.dumps(
            analyze_divider(
                args.psf_dir, f_in=args.f_in, vdd=args.vdd, n_expected=args.n_expected
            ),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
