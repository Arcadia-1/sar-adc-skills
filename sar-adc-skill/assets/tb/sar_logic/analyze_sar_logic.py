#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII results from tb_sar_logic_timing.scs.

Verifies per conversion frame:
  - Exact N_BITS CMPCK pulses (detects missed bits or post-LSB spurious firing)
  - Total conversion time (CLKS falling -> EOC rising) and slack before next CLKS
  - Decoded code accuracy against the sampled differential input
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

from psf_utils import crossings, find_single, parse_psf_ascii


def analyze_sar_logic(
    psf_dir: Path, *, vdd: float = 0.9, vref: float = 0.9, n_bits: int = 10
) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vth = 0.5 * vdd

    clks_fall = crossings(t, d["CLKS"], vth, "falling")
    clks_rise = crossings(t, d["CLKS"], vth, "rising")
    cmpck_rise = crossings(t, d["CMPCK"], vth, "rising")
    eoc_rise = crossings(t, d["EOC"], vth, "rising")

    frames = []
    all_pass = True
    for idx, t_start in enumerate(clks_fall):
        next_rises = [tr for tr in clks_rise if tr > t_start + 1e-12]
        if not next_rises:
            break
        t_end = next_rises[0]

        pulses = [tc for tc in cmpck_rise if t_start < tc < t_end]
        eocs = [te for te in eoc_rise if t_start < te < t_end]
        t_conv = (eocs[0] - t_start) if eocs else float("nan")
        slack = (t_end - eocs[0]) if eocs else float("nan")

        # Input sampled at CLKS falling edge
        vid_in = float(np.interp(t_start, t, d["VIP"] - d["VIN"]))
        expected_code = int(
            np.clip(np.floor((vid_in / (2.0 * vref) + 0.5) * (2**n_bits)), 0, 2**n_bits - 1)
        )
        # Code latched on next CLKS rising edge
        t_read = min(t_end + 1e-9, float(t[-1]))
        measured_code = int(round(float(np.interp(t_read, t, d["CODE"]))))
        code_err = measured_code - expected_code

        frame_ok = (len(pulses) == n_bits) and (len(eocs) == 1) and (abs(code_err) <= 1)
        if not frame_ok:
            all_pass = False

        frames.append(
            {
                "frame": idx,
                "vid_in_mv": round(vid_in * 1e3, 3),
                "cmpck_pulses": len(pulses),
                "eoc_pulses": len(eocs),
                "t_conv_ns": round(t_conv * 1e9, 4) if np.isfinite(t_conv) else None,
                "timing_slack_ns": round(slack * 1e9, 4) if np.isfinite(slack) else None,
                "expected_code": expected_code,
                "measured_code": measured_code,
                "code_err_lsb": code_err,
                "pass": frame_ok,
            }
        )

    return {"n_frames": len(frames), "all_pass": all_pass, "frames": frames}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze SAR logic timing testbench PSF.")
    ap.add_argument("psf_dir", type=Path)
    ap.add_argument("--vdd", type=float, default=0.9)
    ap.add_argument("--vref", type=float, default=0.9)
    ap.add_argument("--n-bits", type=int, default=10)
    args = ap.parse_args(argv)
    res = analyze_sar_logic(args.psf_dir, vdd=args.vdd, vref=args.vref, n_bits=args.n_bits)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
