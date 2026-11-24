#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII output from tb_frac_n_pll_lock.scs."""

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


def analyze_frac_n_lock(
    psf_dir: Path, *, f_ref: float, n_eff: float, vdd: float = 0.9, ss_frac: float = 0.5
) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vctrl = d["VCTRL"]

    f_target = f_ref * n_eff
    ss = t >= (ss_frac * float(t[-1]))
    vctrl_ss = vctrl[ss]
    vctrl_mean = float(np.mean(vctrl_ss))
    vctrl_pp = float(np.max(vctrl_ss) - np.min(vctrl_ss))
    vctrl_rms = float(np.std(vctrl_ss))

    edges = np.asarray(crossings(t[ss], d["OUTP"][ss], 0.5 * vdd, "rising"), dtype=float)
    if len(edges) < 10:
        raise RuntimeError(f"Expected >= 10 steady-state VCO edges, got {len(edges)}")
    f_locked = float((len(edges) - 1) / (edges[-1] - edges[0]))
    periods = np.diff(edges)
    per_jit_ps = float(np.std(periods) * 1e12)
    c2c_jit_ps = float(np.std(np.diff(periods)) * 1e12)
    freq_err_ppm = (f_locked - f_target) / f_target * 1e6

    return {
        "n_eff_target": float(n_eff),
        "f_target_mhz": f_target * 1e-6,
        "f_locked_mhz": f_locked * 1e-6,
        "freq_err_ppm": freq_err_ppm,
        "ss_vco_cycles": float(len(periods)),
        "vctrl_mean_v": vctrl_mean,
        "vctrl_dsm_ripple_pp_mv": vctrl_pp * 1e3,
        "vctrl_dsm_ripple_rms_mv": vctrl_rms * 1e3,
        "period_jitter_ps": per_jit_ps,
        "c2c_jitter_ps": c2c_jit_ps,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze Fractional-N PLL Spectre output.")
    ap.add_argument("psf_dir", type=Path)
    ap.add_argument("--f-ref", type=float, default=50.0e6)
    ap.add_argument("--n-eff", type=float, default=20.0 + 13.0 / 128.0)
    ap.add_argument("--vdd", type=float, default=0.9)
    ap.add_argument("--ss-frac", type=float, default=0.5)
    args = ap.parse_args(argv)
    print(
        json.dumps(
            analyze_frac_n_lock(
                args.psf_dir,
                f_ref=args.f_ref,
                n_eff=args.n_eff,
                vdd=args.vdd,
                ss_frac=args.ss_frac,
            ),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
