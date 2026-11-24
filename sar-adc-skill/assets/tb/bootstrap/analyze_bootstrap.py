#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII results from the bootstrap switch testbenches.

Usage:
  python analyze_bootstrap.py ron <psf_dir> [--vds-probe 1e-3] [--vdd 0.9]
  python analyze_bootstrap.py linearity <psf_dir> [--n-fft 128] [--m-bin 61] [--fs 100e6]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

COMMON_DIR = Path(__file__).resolve().parent.parent / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from psf_utils import (
    coherent_fft_metrics,
    extract_uniform_strobe,
    find_single,
    parse_psf_ascii,
)


def analyze_ron(psf_dir: Path, *, vds_probe: float, vdd: float) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, vin, i_probe = extract_uniform_strobe(d["time"], d["VIN"], d["VPROBE:p"])
    i_sw = -i_probe
    # Evaluate across interior operating range [0.05*vdd, 0.95*vdd]
    mask = (vin >= 0.05 * vdd) & (vin <= 0.95 * vdd) & (np.abs(i_sw) > 1e-12)
    if not np.any(mask):
        raise RuntimeError("No valid switch-on current samples found in [0.05*vdd, 0.95*vdd]")
    ron = vds_probe / np.abs(i_sw[mask])
    ron_min = float(np.min(ron))
    ron_max = float(np.max(ron))
    ron_med = float(np.median(ron))
    return {
        "n_valid_pts": float(np.sum(mask)),
        "ron_min_ohm": ron_min,
        "ron_median_ohm": ron_med,
        "ron_max_ohm": ron_max,
        "ron_max_over_min": ron_max / ron_min,
        "ron_variation_pct": 100.0 * (ron_max - ron_min) / ron_med,
    }


def analyze_linearity(
    psf_dir: Path, *, n_fft: int, m_bin: int | None, fs: float | None
) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, vout = extract_uniform_strobe(d["time"], d["VOUT"])
    if len(vout) < n_fft:
        raise RuntimeError(f"Expected >= {n_fft} strobed samples, got {len(vout)}")
    samples = vout[-n_fft:]
    return coherent_fft_metrics(samples, fs=fs, m_bin=m_bin)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze bootstrap switch Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_ron = sub.add_parser("ron", help="Extract Ron(VIN) flatness from tb_boot_ron_sweep.scs")
    p_ron.add_argument("psf_dir", type=Path)
    p_ron.add_argument("--vds-probe", type=float, default=1e-3)
    p_ron.add_argument("--vdd", type=float, default=0.9)

    p_lin = sub.add_parser("linearity", help="Extract coherent THD/SFDR/ENOB from tb_boot_tran_linearity.scs")
    p_lin.add_argument("psf_dir", type=Path)
    p_lin.add_argument("--n-fft", type=int, default=128)
    p_lin.add_argument("--m-bin", type=int, default=None)
    p_lin.add_argument("--fs", type=float, default=None)

    args = ap.parse_args(argv)
    if args.mode == "ron":
        res = analyze_ron(args.psf_dir, vds_probe=args.vds_probe, vdd=args.vdd)
    else:
        res = analyze_linearity(args.psf_dir, n_fft=args.n_fft, m_bin=args.m_bin, fs=args.fs)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
