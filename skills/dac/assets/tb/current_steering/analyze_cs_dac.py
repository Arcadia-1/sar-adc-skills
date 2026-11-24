#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from Current-Steering DAC testbenches.

Usage:
  python analyze_cs_dac.py static <psf_dir> [--n-codes 1024]
  python analyze_cs_dac.py dynamic <psf_dir> [--n-fft 256] [--m-bin 29] [--fs 200e6]
  python analyze_cs_dac.py twotone <psf_dir> [--n-fft 256] [--m-bin1 59] [--m-bin2 61] [--fs 200e6]
  python analyze_cs_dac.py glitch <psf_dir> [--t-rise 10e-9] [--t-fall 20e-9] [--lsb-v 1e-3]
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
    coherent_fft_metrics,
    coherent_twotone_metrics,
    dnl_inl_from_transfer,
    extract_uniform_strobe,
    find_single,
    parse_psf_ascii,
    trapz,
)


def analyze_static(psf_dir: Path, *, n_codes: int) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t, vp, vn, cm = extract_uniform_strobe(d["time"], d["IOUTP"], d["IOUTN"], d["CODE_MON"])
    vdiff = vp - vn
    if len(vdiff) < n_codes:
        raise RuntimeError(f"Expected at least {n_codes} strobed codes, got {len(vdiff)}")

    # Group by rounded integer code so exact 0..n_codes-1 levels are extracted
    codes = np.round(cm).astype(int)
    levels = np.empty(n_codes, dtype=float)
    for c in range(n_codes):
        idx = np.where(codes == c)[0]
        if len(idx) == 0:
            raise RuntimeError(f"Missing code {c} in static sweep")
        levels[c] = float(vdiff[idx[-1]])

    m = dnl_inl_from_transfer(levels)
    v_mid_err = 0.5 * (levels[0] + levels[-1])
    monotonic = bool(m["dnl_min_lsb"] > -1.0)
    return {
        "n_codes": int(n_codes),
        "full_scale_v": m["full_scale_v"],
        "lsb_mv": m["lsb_v"] * 1e3,
        "midpoint_offset_mv": float(v_mid_err * 1e3),
        "vcm_mean_v": float(0.5 * np.mean(vp + vn)),
        "dnl_max_lsb": m["dnl_max_lsb"],
        "dnl_min_lsb": m["dnl_min_lsb"],
        "dnl_abs_max_lsb": m["dnl_abs_max_lsb"],
        "inl_max_lsb": m["inl_max_lsb"],
        "inl_min_lsb": m["inl_min_lsb"],
        "inl_abs_max_lsb": m["inl_abs_max_lsb"],
        "monotonic": monotonic,
    }


def analyze_dynamic(
    psf_dir: Path, *, n_fft: int, m_bin: int | None, fs: float | None
) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, vp, vn = extract_uniform_strobe(d["time"], d["IOUTP"], d["IOUTN"])
    vdiff = vp - vn
    if len(vdiff) < n_fft:
        raise RuntimeError(f"Expected at least {n_fft} strobed samples, got {len(vdiff)}")
    seg = vdiff[-n_fft:]
    return coherent_fft_metrics(seg, num_harmonics=7, fs=fs, m_bin=m_bin)


def analyze_twotone(
    psf_dir: Path, *, n_fft: int, m_bin1: int, m_bin2: int, fs: float | None
) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, vp, vn = extract_uniform_strobe(d["time"], d["IOUTP"], d["IOUTN"])
    vdiff = vp - vn
    if len(vdiff) < n_fft:
        raise RuntimeError(f"Expected at least {n_fft} strobed samples, got {len(vdiff)}")
    seg = vdiff[-n_fft:]
    return coherent_twotone_metrics(seg, m_bin1=m_bin1, m_bin2=m_bin2, fs=fs)


def _measure_transition(
    t: np.ndarray, v: np.ndarray, t_edge: float, t_end: float, lsb_v: float
) -> dict[str, float]:
    pre_m = (t >= t_edge - 2e-9) & (t <= t_edge - 0.2e-9)
    post_m = (t >= t_end - 2e-9) & (t <= t_end - 0.2e-9)
    v_pre = float(np.mean(v[pre_m]))
    v_post = float(np.mean(v[post_m]))

    win_m = (t >= t_edge) & (t <= t_end - 0.5e-9)
    tw, vw = t[win_m], v[win_m]

    v_lo, v_hi = min(v_pre, v_post), max(v_pre, v_post)
    excess = np.where(vw > v_hi, vw - v_hi, np.where(vw < v_lo, v_lo - vw, 0.0))
    peak_glitch_v = float(np.max(excess))
    impulse_vs = float(trapz(excess, tw))

    tol = 0.5 * lsb_v
    outside = np.where(np.abs(vw - v_post) > tol)[0]
    t_settle = float(tw[outside[-1] + 1] - t_edge) if (len(outside) > 0 and outside[-1] + 1 < len(tw)) else 0.0

    return {
        "step_mv": (v_post - v_pre) * 1e3,
        "glitch_peak_mv": peak_glitch_v * 1e3,
        "glitch_impulse_pvs": impulse_vs * 1e12,
        "t_settle_0p5lsb_ns": t_settle * 1e9,
    }


def analyze_glitch(
    psf_dir: Path, *, t_rise: float, t_fall: float, lsb_v: float
) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vdiff = d["IOUTP"] - d["IOUTN"]
    t_stop = float(t[-1])

    r = _measure_transition(t, vdiff, t_rise, t_fall, lsb_v)
    fa = _measure_transition(t, vdiff, t_fall, t_stop, lsb_v)
    return {
        "rise_step_mv": r["step_mv"],
        "rise_glitch_peak_mv": r["glitch_peak_mv"],
        "rise_glitch_impulse_pvs": r["glitch_impulse_pvs"],
        "rise_t_settle_0p5lsb_ns": r["t_settle_0p5lsb_ns"],
        "fall_step_mv": fa["step_mv"],
        "fall_glitch_peak_mv": fa["glitch_peak_mv"],
        "fall_glitch_impulse_pvs": fa["glitch_impulse_pvs"],
        "fall_t_settle_0p5lsb_ns": fa["t_settle_0p5lsb_ns"],
        "worst_glitch_impulse_pvs": max(r["glitch_impulse_pvs"], fa["glitch_impulse_pvs"]),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze Current-Steering DAC Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_st = sub.add_parser("static")
    p_st.add_argument("psf_dir", type=Path)
    p_st.add_argument("--n-codes", type=int, default=1024)

    p_dy = sub.add_parser("dynamic")
    p_dy.add_argument("psf_dir", type=Path)
    p_dy.add_argument("--n-fft", type=int, default=256)
    p_dy.add_argument("--m-bin", type=int, default=None)
    p_dy.add_argument("--fs", type=float, default=200e6)

    p_tt = sub.add_parser("twotone")
    p_tt.add_argument("psf_dir", type=Path)
    p_tt.add_argument("--n-fft", type=int, default=256)
    p_tt.add_argument("--m-bin1", type=int, default=59)
    p_tt.add_argument("--m-bin2", type=int, default=61)
    p_tt.add_argument("--fs", type=float, default=200e6)

    p_gl = sub.add_parser("glitch")
    p_gl.add_argument("psf_dir", type=Path)
    p_gl.add_argument("--t-rise", type=float, default=10e-9)
    p_gl.add_argument("--t-fall", type=float, default=20e-9)
    p_gl.add_argument("--lsb-v", type=float, default=1.0e-3)

    args = ap.parse_args(argv)
    if args.mode == "static":
        res: object = analyze_static(args.psf_dir, n_codes=args.n_codes)
    elif args.mode == "dynamic":
        res = analyze_dynamic(args.psf_dir, n_fft=args.n_fft, m_bin=args.m_bin, fs=args.fs)
    elif args.mode == "twotone":
        res = analyze_twotone(
            args.psf_dir, n_fft=args.n_fft, m_bin1=args.m_bin1, m_bin2=args.m_bin2, fs=args.fs
        )
    else:
        res = analyze_glitch(
            args.psf_dir, t_rise=args.t_rise, t_fall=args.t_fall, lsb_v=args.lsb_v
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
