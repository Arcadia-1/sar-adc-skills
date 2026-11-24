#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from frequency divider & MMD testbenches.

Usage:
  python analyze_divider.py func <psf_dir> [--f-in 1e9] [--vdd 0.9] [--n-expected 20]
  python analyze_divider.py toggle <psf_dir> [--n-target 4] [--vdd 0.9]
  python analyze_divider.py <psf_dir> [--f-in 1e9] [--vdd 0.9] [--n-expected 20]  # legacy alias
"""

from __future__ import annotations

import argparse
import json
import re
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


def _edge_slew_ps(
    t: np.ndarray, y: np.ndarray, mid_edges: np.ndarray, lo_lvl: float, hi_lvl: float, direction: str, max_span: float
) -> float | None:
    """Compute median 20%-80% transition time [ps] around detected mid-level edges."""
    if direction == "rising":
        t_start = np.asarray(crossings(t, y, lo_lvl, "rising"), dtype=float)
        t_end = np.asarray(crossings(t, y, hi_lvl, "rising"), dtype=float)
    else:
        t_start = np.asarray(crossings(t, y, hi_lvl, "falling"), dtype=float)
        t_end = np.asarray(crossings(t, y, lo_lvl, "falling"), dtype=float)
    if len(t_start) == 0 or len(t_end) == 0:
        return None
    dts: list[float] = []
    for tm in mid_edges:
        pre = t_start[t_start <= tm]
        post = t_end[t_end >= tm]
        if len(pre) > 0 and len(post) > 0:
            dt = float(post[0] - pre[-1])
            if 0.0 < dt < max_span:
                dts.append(dt * 1e12)
    return float(np.median(dts)) if dts else None


def analyze_toggle(
    psf_dir: Path, *, n_target: float = 4.0, vdd: float = 0.9
) -> dict[str, object]:
    """Analyze multi-frequency toggle, cycle-slip, duty cycle, and edge speed from tb_div_max_toggle.scs."""
    files = sorted(
        Path(psf_dir).glob("tran_f*.tran"),
        key=lambda p: int(m.group(1)) if (m := re.search(r"f(\d+)", p.name)) else 0,
    )
    if not files:
        raise FileNotFoundError(f"No tran_f*.tran files found in {psf_dir}")

    vth = 0.5 * vdd
    points: list[dict[str, object]] = []
    for p in files:
        d = parse_psf_ascii(p)
        t = d["time"]
        m_ss = t >= 0.20 * float(t[-1])
        tw = t[m_ss]
        vin = d["CLK_IN"][m_ss]
        vout = d["CLK_OUT"][m_ss]

        in_rise = np.asarray(crossings(tw, vin, vth, "rising"), dtype=float)
        if len(in_rise) < 4:
            raise RuntimeError(f"Insufficient CLK_IN edges in {p.name}: {len(in_rise)}")
        f_in_hz = float((len(in_rise) - 1) / (in_rise[-1] - in_rise[0]))

        out_rise = np.asarray(crossings(tw, vout, vth, "rising"), dtype=float)
        out_fall = np.asarray(crossings(tw, vout, vth, "falling"), dtype=float)
        vout_pp = float(np.max(vout) - np.min(vout))

        if len(out_rise) >= 3 and vout_pp >= 0.65 * vdd:
            periods_out = np.diff(out_rise)
            inst_ratios = periods_out * f_in_hz
            n_meas = float((out_rise[-1] - out_rise[0]) * f_in_hz / (len(out_rise) - 1))
            max_inst_err = float(np.max(np.abs(inst_ratios - n_target)))
            cycle_slip = bool((abs(n_meas - n_target) > 0.01) or (max_inst_err > 0.20))

            duties: list[float] = []
            for k in range(len(out_rise) - 1):
                t0, t1 = float(out_rise[k]), float(out_rise[k + 1])
                f_in_cyc = out_fall[(out_fall > t0) & (out_fall < t1)]
                if len(f_in_cyc) == 1:
                    duties.append(100.0 * (float(f_in_cyc[0]) - t0) / (t1 - t0))
            duty_pct: float | None = float(np.mean(duties)) if duties else None

            med_per = float(np.median(periods_out))
            tr_ps = _edge_slew_ps(tw, vout, out_rise, 0.2 * vdd, 0.8 * vdd, "rising", 0.45 * med_per)
            tf_ps = _edge_slew_ps(tw, vout, out_fall, 0.2 * vdd, 0.8 * vdd, "falling", 0.45 * med_per)
        else:
            n_meas = None
            max_inst_err = None
            cycle_slip = True
            duty_pct = None
            tr_ps = None
            tf_ps = None

        points.append(
            {
                "file": p.name,
                "f_in_ghz": round(f_in_hz * 1e-9, 4),
                "in_edges": int(len(in_rise)),
                "out_edges": int(len(out_rise)),
                "vout_pp_v": round(vout_pp, 4),
                "n_meas": round(n_meas, 5) if n_meas is not None else None,
                "max_inst_ratio_err": round(max_inst_err, 5) if max_inst_err is not None else None,
                "cycle_slip": cycle_slip,
                "duty_pct": round(duty_pct, 2) if duty_pct is not None else None,
                "tr_20_80_ps": round(tr_ps, 2) if tr_ps is not None else None,
                "tf_80_20_ps": round(tf_ps, 2) if tf_ps is not None else None,
            }
        )

    passed = [pt for pt in points if not pt["cycle_slip"]]
    f_max_pass = max((float(pt["f_in_ghz"]) for pt in passed), default=0.0)
    return {
        "n_target": float(n_target),
        "n_freqs": int(len(points)),
        "n_passed": int(len(passed)),
        "n_failed": int(len(points) - len(passed)),
        "f_max_pass_ghz": f_max_pass,
        "all_pass": bool(len(passed) == len(points)),
        "points": points,
    }


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    # Preserve backward compatibility: `analyze_divider.py <psf_dir> ...` defaults to `func`
    if raw_argv and raw_argv[0] not in ("func", "toggle", "-h", "--help"):
        raw_argv = ["func", *raw_argv]

    ap = argparse.ArgumentParser(description="Analyze divider / MMD Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_fn = sub.add_parser("func", help="Analyze average division ratio from tb_div_func_mmd.scs")
    p_fn.add_argument("psf_dir", type=Path)
    p_fn.add_argument("--f-in", type=float, default=1.0e9)
    p_fn.add_argument("--vdd", type=float, default=0.9)
    p_fn.add_argument("--n-expected", type=float, default=None)

    p_tg = sub.add_parser("toggle", help="Analyze max toggle & cycle slips from tb_div_max_toggle.scs")
    p_tg.add_argument("psf_dir", type=Path)
    p_tg.add_argument("--n-target", type=float, default=4.0)
    p_tg.add_argument("--vdd", type=float, default=0.9)

    args = ap.parse_args(raw_argv)
    if args.mode == "toggle":
        res = analyze_toggle(args.psf_dir, n_target=args.n_target, vdd=args.vdd)
    else:
        res = analyze_divider(
            args.psf_dir, f_in=args.f_in, vdd=args.vdd, n_expected=args.n_expected
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
