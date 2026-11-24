#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII Monte Carlo mismatch offset outputs.

Usage:
  python analyze_mc.py <psf_dir> [--spec-mv 15.0]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

COMMON_DIR = Path(__file__).resolve().parents[1]
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from psf_utils import parse_psf_ascii


def analyze_mc(psf_dir: Path, *, spec_mv: float) -> dict[str, float]:
    files = sorted(psf_dir.glob("mc1-*_dcOp.dc"))
    if not files:
        files = sorted(p for p in psf_dir.glob("mc*-*.dc") if p.is_file())
    if not files:
        raise FileNotFoundError(f"No per-run Monte Carlo dc PSF files found in {psf_dir}")

    vals = []
    for f in files:
        d = parse_psf_ascii(f)
        if "OUTP" in d and "OUTN" in d:
            v = float(d["OUTP"][0] - d["OUTN"][0])
        elif "VOUT" in d:
            v = float(d["VOUT"][0])
        else:
            raise KeyError(f"Expected OUTP/OUTN or VOUT in {f}, found {sorted(d.keys())}")
        vals.append(v * 1e3)

    arr = np.asarray(vals, dtype=float)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    in_spec = int(np.sum(np.abs(arr) <= spec_mv))
    return {
        "n_runs": float(len(arr)),
        "mean_mv": mean,
        "std_1sigma_mv": std,
        "three_sigma_mv": 3.0 * std,
        "min_mv": float(np.min(arr)),
        "max_mv": float(np.max(arr)),
        "spec_abs_mv": spec_mv,
        "yield_pct": float(in_spec / len(arr) * 100.0),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze Spectre Monte Carlo DC offset runs.")
    ap.add_argument("psf_dir", type=Path)
    ap.add_argument("--spec-mv", type=float, default=15.0)
    args = ap.parse_args(argv)
    print(json.dumps(analyze_mc(args.psf_dir, spec_mv=args.spec_mv), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
