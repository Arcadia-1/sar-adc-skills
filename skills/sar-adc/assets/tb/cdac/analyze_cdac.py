#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from the CDAC testbenches.

Usage:
  python analyze_cdac.py static <psf_dir> [--n-codes 512]
  python analyze_cdac.py settling <psf_dir> [--n-bits 10] [--vfs-diff 1.8] [--t-msb 8e-9]
  python analyze_cdac.py mismatch_cal <psf_dir> [--fs 50e6] [--n-fft 256] [--m-bin 19]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

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
    dnl_inl_from_transfer,
    extract_uniform_strobe,
    find_single,
    parse_psf_ascii,
)

# Nominal 11-trial sub-radix-2 weights (bits 10..1 switched caps + 0.5 LSB final decision)
W_RED_NOM_10 = np.array([232.0, 128.0, 72.0, 40.0, 22.0, 12.0, 6.0, 4.0, 2.0, 1.0], dtype=float)
W_RED_BIT0 = 0.5


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


def _find_tran(psf_dir: Path, name: str) -> Path:
    return find_single(psf_dir, [f"{name}.tran.tran", f"{name}.tran", f"*{name}*.tran*"])


def _unpack_red_bits(raw_codes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Unpack integer RAW_CODE [0..2047] into bipolar {-1,+1} arrays B10 (N,10) & b0 (N,)."""
    rc = np.rint(raw_codes).astype(int)
    n = len(rc)
    b10 = np.empty((n, 10), dtype=float)
    for idx, bit_pos in enumerate(range(10, 0, -1)):
        b10[:, idx] = np.where(((rc >> bit_pos) & 1) == 1, 1.0, -1.0)
    b0 = np.where((rc & 1) == 1, 1.0, -1.0)
    return b10, b0


def _sine_binned_inl(y: np.ndarray, *, m_bin: int, n_bins: int = 32) -> float:
    """Compute peak INL [LSB] by fitting the coherent sine and binning code residuals."""
    n = len(y)
    idx = np.arange(n, dtype=float)
    w = 2.0 * math.pi * m_bin / n
    a_mat = np.column_stack([np.ones(n), np.cos(w * idx), np.sin(w * idx)])
    coef, *_ = np.linalg.lstsq(a_mat, y, rcond=None)
    y_fit = a_mat @ coef
    resid = y - y_fit

    edges = np.linspace(float(np.min(y_fit)), float(np.max(y_fit)), n_bins + 1)
    bin_errs: list[float] = []
    for k in range(n_bins):
        lo, hi = edges[k], edges[k + 1]
        m = (y_fit >= lo) & (y_fit <= hi if k == n_bins - 1 else y_fit < hi)
        if np.sum(m) >= 3:
            bin_errs.append(float(np.mean(resid[m])))
    if not bin_errs:
        return float(np.max(np.abs(resid)))
    return float(np.max(np.abs(bin_errs)))


def _calibrate_weights_sine(b10: np.ndarray, b0: np.ndarray, *, m_bin: int) -> np.ndarray:
    """Blind foreground least-squares digital weight calibration on a coherent sine."""
    n = b10.shape[0]
    idx = np.arange(n, dtype=float)
    w_rad = 2.0 * math.pi * m_bin / n
    a_tone = np.column_stack([np.ones(n), np.cos(w_rad * idx), np.sin(w_rad * idx)])
    q_mat, _ = np.linalg.qr(a_tone)

    # Project bit decisions onto orthogonal complement of [DC, cos, sin]
    b10_p = b10 - q_mat @ (q_mat.T @ b10)
    b0_p = b0 - q_mat @ (q_mat.T @ b0)

    # Minimize || b10_p @ w + 0.5 * b0_p ||^2 subject to sum(w) = sum(W_RED_NOM_10)
    m_mat = b10_p.T @ b10_p + 1e-12 * np.eye(10)
    g_vec = b10_p.T @ (W_RED_BIT0 * b0_p)
    c_vec = np.ones(10, dtype=float)
    s_sum = float(np.sum(W_RED_NOM_10))

    minv_g = np.linalg.solve(m_mat, g_vec)
    minv_c = np.linalg.solve(m_mat, c_vec)
    scale = (s_sum + float(c_vec @ minv_g)) / float(c_vec @ minv_c)
    return -minv_g + scale * minv_c


def analyze_mismatch_cal(
    psf_dir: Path,
    *,
    fs: float = 50e6,
    n_fft: int = 256,
    m_bin: int = 19,
    n_fft_mm: int = 512,
    m_bin_mm: int = 29,
) -> dict[str, Any]:
    """Analyze redundancy recovery and foreground digital weight calibration."""
    # 1) Ideal baseline
    d_id = parse_psf_ascii(_find_tran(psf_dir, "tran_ideal"))
    _, rc_id = extract_uniform_strobe(d_id["time"], d_id["RAW_CODE"])
    b10_id, b0_id = _unpack_red_bits(rc_id[-n_fft:])
    y_id = b10_id @ W_RED_NOM_10 + W_RED_BIT0 * b0_id
    m_id = coherent_fft_metrics(y_id, m_bin=m_bin, fs=fs)

    # 2) Redundancy recovery under injected MSB decision error
    d_red = parse_psf_ascii(_find_tran(psf_dir, "tran_red_err"))
    _, rc_red = extract_uniform_strobe(d_red["time"], d_red["RAW_CODE"])
    b10_red, b0_red = _unpack_red_bits(rc_red[-n_fft:])
    y_red = b10_red @ W_RED_NOM_10 + W_RED_BIT0 * b0_red
    m_red = coherent_fft_metrics(y_red, m_bin=m_bin, fs=fs)

    # 2b) Full-scale ramp under MSB decision error -> verify 0 missing codes
    d_rmp = parse_psf_ascii(_find_tran(psf_dir, "tran_ramp_red"))
    _, rc_rmp = extract_uniform_strobe(d_rmp["time"], d_rmp["RAW_CODE"])
    b10_r, b0_r = _unpack_red_bits(rc_rmp[4:])
    y_rmp = b10_r @ W_RED_NOM_10 + W_RED_BIT0 * b0_r
    codes_rmp = np.clip(np.floor(512.0 + y_rmp).astype(int), 0, 1023)
    counts = np.bincount(codes_rmp, minlength=1024)
    interior = counts[1:1023]
    missing_codes_red = int(np.sum(interior == 0))

    # 3) Mismatch + foreground least-squares digital weight calibration
    d_mm = parse_psf_ascii(_find_tran(psf_dir, "tran_mismatch"))
    _, rc_mm = extract_uniform_strobe(d_mm["time"], d_mm["RAW_CODE"])
    if len(rc_mm) < n_fft_mm:
        raise RuntimeError(f"Expected >= {n_fft_mm} strobed samples in tran_mismatch, got {len(rc_mm)}")
    b10_mm, b0_mm = _unpack_red_bits(rc_mm[-n_fft_mm:])

    y_uncal = b10_mm @ W_RED_NOM_10 + W_RED_BIT0 * b0_mm
    m_uncal = coherent_fft_metrics(y_uncal, m_bin=m_bin_mm, fs=fs)
    inl_uncal = _sine_binned_inl(y_uncal, m_bin=m_bin_mm)

    w_cal = _calibrate_weights_sine(b10_mm, b0_mm, m_bin=m_bin_mm)
    y_cal = b10_mm @ w_cal + W_RED_BIT0 * b0_mm
    m_cal = coherent_fft_metrics(y_cal, m_bin=m_bin_mm, fs=fs)
    inl_cal = _sine_binned_inl(y_cal, m_bin=m_bin_mm)

    # Normalize calibrated weights against nominal LSB group [6:1] to report % mismatch
    lsb_scale = float(np.sum(W_RED_NOM_10[4:])) / float(np.sum(w_cal[4:]))
    w_cal_norm = w_cal * lsb_scale
    dm_est_pct = ((w_cal_norm / W_RED_NOM_10) - 1.0) * 100.0

    return {
        "ideal": {
            "enob": m_id["enob"],
            "sndr_db": m_id["sndr_db"],
            "sfdr_db": m_id["sfdr_db"],
        },
        "redundancy_recovery": {
            "enob": m_red["enob"],
            "sndr_db": m_red["sndr_db"],
            "sfdr_db": m_red["sfdr_db"],
            "enob_delta_vs_ideal_bits": m_red["enob"] - m_id["enob"],
            "missing_codes": missing_codes_red,
            "ramp_avg_hits_per_code": float(np.mean(interior)),
        },
        "mismatch_uncalibrated": {
            "enob": m_uncal["enob"],
            "sndr_db": m_uncal["sndr_db"],
            "sfdr_db": m_uncal["sfdr_db"],
            "thd_db": m_uncal["thd_db"],
            "inl_max_lsb": inl_uncal,
        },
        "mismatch_calibrated": {
            "enob": m_cal["enob"],
            "sndr_db": m_cal["sndr_db"],
            "sfdr_db": m_cal["sfdr_db"],
            "thd_db": m_cal["thd_db"],
            "inl_max_lsb": inl_cal,
            "sfdr_recovery_db": m_cal["sfdr_db"] - m_uncal["sfdr_db"],
            "enob_recovery_bits": m_cal["enob"] - m_uncal["enob"],
            "est_mismatch_msb_pct": {
                "dm10_pct": float(dm_est_pct[0]),
                "dm9_pct": float(dm_est_pct[1]),
                "dm8_pct": float(dm_est_pct[2]),
                "dm7_pct": float(dm_est_pct[3]),
            },
            "calibrated_weights": [round(float(x), 4) for x in w_cal_norm],
        },
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

    p_mc = sub.add_parser(
        "mismatch_cal",
        help="Verify sub-radix-2 redundancy recovery and foreground weight calibration from tb_cdac_mismatch_redundancy.scs",
    )
    p_mc.add_argument("psf_dir", type=Path)
    p_mc.add_argument("--fs", type=float, default=50e6)
    p_mc.add_argument("--n-fft", type=int, default=256)
    p_mc.add_argument("--m-bin", type=int, default=19)
    p_mc.add_argument("--n-fft-mm", type=int, default=512)
    p_mc.add_argument("--m-bin-mm", type=int, default=29)

    args = ap.parse_args(argv)
    if args.mode == "static":
        res: Any = analyze_static(args.psf_dir, n_codes=args.n_codes)
    elif args.mode == "settling":
        res = analyze_settling(
            args.psf_dir, n_bits=args.n_bits, vfs_diff=args.vfs_diff, t_msb=args.t_msb
        )
    else:
        res = analyze_mismatch_cal(
            args.psf_dir,
            fs=args.fs,
            n_fft=args.n_fft,
            m_bin=args.m_bin,
            n_fft_mm=args.n_fft_mm,
            m_bin_mm=args.m_bin_mm,
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
