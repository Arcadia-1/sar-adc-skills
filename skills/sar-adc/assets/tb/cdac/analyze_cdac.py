#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from the CDAC testbenches.

Usage:
  python analyze_cdac.py static <psf_dir> [--n-codes 512]
  python analyze_cdac.py settling <psf_dir> [--n-bits 10] [--vfs-diff 1.8] [--t-msb 8e-9]
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
    dnl_inl_from_transfer,
    extract_uniform_strobe,
    find_single,
    parse_psf_ascii,
)


def analyze_static(psf_dir: Path, *, n_codes: int) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, vcp, vcn = extract_uniform_strobe(d["time"], d["VCP"], d["VCN"])
    vdiff = vcp - vcn
    vcm = 0.5 * (vcp + vcn)
    if len(vdiff) < n_codes:
        raise RuntimeError(f"Expected >= {n_codes} strobed points, got {len(vdiff)}")
    vdiff = vdiff[:n_codes]
    vcm = vcm[:n_codes]
    res = dnl_inl_from_transfer(vdiff)
    res["vcm_min_v"] = float(np.min(vcm))
    res["vcm_max_v"] = float(np.max(vcm))
    res["vcm_shift_mv"] = float((np.max(vcm) - np.min(vcm)) * 1e3)
    return res


def analyze_settling(
    psf_dir: Path, *, n_bits: int, vfs_diff: float, t_msb: float
) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vdiff = d["VCP"] - d["VCN"]
    vcm = 0.5 * (d["VCP"] + d["VCN"])

    pre_mask = (t > t_msb - 1e-9) & (t < t_msb - 0.1e-9)
    v_pre = float(np.mean(vdiff[pre_mask]))
    vcm_pre = float(np.mean(vcm[pre_mask]))
    v_final = float(vdiff[-1])
    vcm_final = float(vcm[-1])

    lsb = vfs_diff / (2**n_bits)
    err_band = 0.5 * lsb
    post_idx = np.where(t >= t_msb)[0]
    post_t = t[post_idx]
    post_err = np.abs(vdiff[post_idx] - v_final)

    outside = np.where(post_err > err_band)[0]
    if len(outside) == 0:
        t_settle = 0.0
    elif outside[-1] + 1 < len(post_t):
        t_settle = float(post_t[outside[-1] + 1] - t_msb)
    else:
        t_settle = float("nan")

    return {
        "v_pre_v": v_pre,
        "v_final_v": v_final,
        "delta_v_msb_v": v_final - v_pre,
        "delta_vcm_mv": (vcm_final - vcm_pre) * 1e3,
        "lsb_mv": lsb * 1e3,
        "err_band_0p5lsb_mv": err_band * 1e3,
        "t_settle_0p5lsb_ps": t_settle * 1e12,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze CDAC Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_st = sub.add_parser("static", help="Extract DNL/INL/Vcm from tb_cdac_static_dnl_inl.scs")
    p_st.add_argument("psf_dir", type=Path)
    p_st.add_argument("--n-codes", type=int, default=512)

    p_set = sub.add_parser("settling", help="Extract MSB 0.5-LSB settling time from tb_cdac_settling.scs")
    p_set.add_argument("psf_dir", type=Path)
    p_set.add_argument("--n-bits", type=int, default=10)
    p_set.add_argument("--vfs-diff", type=float, default=1.8)
    p_set.add_argument("--t-msb", type=float, default=8e-9)

    args = ap.parse_args(argv)
    if args.mode == "static":
        res = analyze_static(args.psf_dir, n_codes=args.n_codes)
    else:
        res = analyze_settling(
            args.psf_dir, n_bits=args.n_bits, vfs_diff=args.vfs_diff, t_msb=args.t_msb
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
