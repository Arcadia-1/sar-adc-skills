#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from full SAR ADC testbenches.

Usage:
  python analyze_adc_top.py fft <psf_dir> [--n-bits 10] [--n-fft 128] [--m-bin 19] [--fs 50e6]
  python analyze_adc_top.py ramp <psf_dir> [--n-bits 10]
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
    coherent_fft_metrics,
    extract_uniform_strobe,
    find_single,
    parse_psf_ascii,
)


def analyze_fft(
    psf_dir: Path,
    *,
    n_bits: int,
    n_fft: int,
    m_bin: int | None,
    fs: float | None,
) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, code_raw = extract_uniform_strobe(d["time"], d["CODE"])
    codes = np.rint(code_raw)
    if len(codes) < n_fft:
        raise RuntimeError(f"Expected >= {n_fft} strobed codes, got {len(codes)}")
    # Use the final n_fft uniform strobe samples (skips startup and 1-sample latch latency)
    win = codes[-n_fft:]
    res = coherent_fft_metrics(win, fs=fs, m_bin=m_bin)

    full_scale_peak = (2**n_bits) / 2.0
    res["amp_dbfs"] = 20.0 * math.log10(max(res["amp_peak"] / full_scale_peak, 1e-12))
    res["code_min"] = float(np.min(win))
    res["code_max"] = float(np.max(win))
    res["clipped"] = float((res["code_min"] <= 0.0) or (res["code_max"] >= (2**n_bits - 1)))
    return res


def analyze_ramp(psf_dir: Path, *, n_bits: int) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, code_raw, vip, vin = extract_uniform_strobe(d["time"], d["CODE"], d["VIP"], d["VIN"])
    codes = np.rint(code_raw).astype(int)
    vid = vip - vin

    n_codes = 2**n_bits
    counts = np.bincount(np.clip(codes, 0, n_codes - 1), minlength=n_codes)
    # Interior codes [1 .. n_codes - 2] (exclude clipped rails 0 and 2^N - 1)
    interior = counts[1 : n_codes - 1].astype(float)
    avg_hits = float(np.mean(interior))
    if avg_hits <= 0.0:
        raise RuntimeError("No interior ADC codes hit during ramp sweep")

    dnl = interior / avg_hits - 1.0
    inl = np.cumsum(dnl)
    # Remove endpoint linear slope from INL for standard endpoint-fit INL
    inl = inl - np.linspace(inl[0], inl[-1], len(inl))

    missing = int(np.sum(interior == 0))

    # Estimate usable full-scale differential range (first exit from code 0 to first hit of max)
    above_zero = np.where(codes > 0)[0]
    at_max = np.where(codes >= n_codes - 1)[0]
    # Note 1-sample latch offset between VIP/VIN and CODE
    idx_lo = max(int(above_zero[0]) - 1, 0) if len(above_zero) else 0
    idx_hi = max(int(at_max[0]) - 1, 0) if len(at_max) else len(vid) - 1
    usable_fs_diff = float(vid[idx_hi] - vid[idx_lo])

    return {
        "n_codes": float(n_codes),
        "avg_hits_per_code": avg_hits,
        "missing_codes": float(missing),
        "dnl_max_lsb": float(np.max(dnl)),
        "dnl_min_lsb": float(np.min(dnl)),
        "inl_max_lsb": float(np.max(inl)),
        "inl_min_lsb": float(np.min(inl)),
        "usable_vfs_diff_v": usable_fs_diff,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze full SAR ADC Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_fft = sub.add_parser("fft", help="Compute coherent ENOB/SNDR/SFDR/THD from tb_sar_adc_fft.scs")
    p_fft.add_argument("psf_dir", type=Path)
    p_fft.add_argument("--n-bits", type=int, default=10)
    p_fft.add_argument("--n-fft", type=int, default=128)
    p_fft.add_argument("--m-bin", type=int, default=None)
    p_fft.add_argument("--fs", type=float, default=None)

    p_ramp = sub.add_parser("ramp", help="Compute histogram DNL/INL & usable swing from tb_sar_adc_ramp_dnl.scs")
    p_ramp.add_argument("psf_dir", type=Path)
    p_ramp.add_argument("--n-bits", type=int, default=10)

    args = ap.parse_args(argv)
    if args.mode == "fft":
        res = analyze_fft(
            args.psf_dir, n_bits=args.n_bits, n_fft=args.n_fft, m_bin=args.m_bin, fs=args.fs
        )
    else:
        res = analyze_ramp(args.psf_dir, n_bits=args.n_bits)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
