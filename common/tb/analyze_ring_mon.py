#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from 5-stage Ring Oscillator PVT Monitor.

Usage:
  python analyze_ring_mon.py <psf_dir> [--n-stages 5] [--vdd 1.0]
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

from psf_utils import crossings, find_single, parse_psf_ascii, trapz


def analyze_ring(psf_dir: Path, *, n_stages: int, vdd: float) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v = d["N0"]
    t_end = float(t[-1])

    # Discard initial 25% startup transient
    m = t >= 0.25 * t_end
    tw, vw = t[m], v[m]
    rises = crossings(tw, vw, 0.5 * vdd, direction="rising")
    falls = crossings(tw, vw, 0.5 * vdd, direction="falling")
    if len(rises) < 3:
        raise RuntimeError(f"Ring oscillator did not sustain oscillation ({len(rises)} rising edges)")

    periods = np.diff(rises)
    t_per = float(np.median(periods))
    f_osc = 1.0 / t_per
    t_pd = t_per / (2.0 * n_stages)

    duty = float("nan")
    hi_times = []
    for r in rises[:-1]:
        nxt_f = [x for x in falls if x > r]
        if nxt_f:
            hi_times.append(nxt_f[0] - r)
    if hi_times:
        duty = float(np.median(hi_times) / t_per * 100.0)

    res: dict[str, float] = {
        "n_stages": float(n_stages),
        "n_cycles_measured": float(len(periods)),
        "f_osc_ghz": f_osc / 1e9,
        "period_ps": t_per * 1e12,
        "stage_delay_ps": t_pd * 1e12,
        "duty_cycle_pct": duty,
    }
    if "VSUP:p" in d:
        i_sup = -d["VSUP:p"][m]
        p_avg = vdd * trapz(i_sup, tw) / (tw[-1] - tw[0])
        res["avg_power_mw"] = p_avg * 1e3
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze Ring Oscillator PVT Monitor outputs.")
    ap.add_argument("psf_dir", type=Path)
    ap.add_argument("--n-stages", type=int, default=5)
    ap.add_argument("--vdd", type=float, default=1.0)
    args = ap.parse_args(argv)
    print(json.dumps(analyze_ring(args.psf_dir, n_stages=args.n_stages, vdd=args.vdd), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
