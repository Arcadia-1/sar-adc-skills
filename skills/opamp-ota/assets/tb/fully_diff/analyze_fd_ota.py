#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from fully differential OTA testbenches.

Usage:
  python analyze_fd_ota.py dm_cm_stb <psf_dir>
  python analyze_fd_ota.py slew_settle <psf_dir> [--t-step 100e-9] [--vocm 0.45]
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

from psf_utils import crossings, find_single, parse_psf_ascii


def _extract_stb_file(path: Path) -> dict[str, float]:
    d = parse_psf_ascii(path)
    freq = np.real(d["freq"])
    lg = d["loopGain"]
    if np.real(lg[0]) < 0:
        lg = -lg
    mag_db = 20.0 * np.log10(np.maximum(np.abs(lg), 1e-30))
    phase_deg = np.degrees(np.unwrap(np.angle(lg)))

    a0_db = float(mag_db[0])
    ugf_hz = float("nan")
    pm_deg = float("nan")
    for i in range(len(mag_db) - 1):
        if mag_db[i] >= 0.0 > mag_db[i + 1]:
            frac = (0.0 - mag_db[i]) / (mag_db[i + 1] - mag_db[i])
            ugf_hz = float(10.0 ** (math.log10(freq[i]) + frac * (math.log10(freq[i + 1]) - math.log10(freq[i]))))
            ph_u = float(phase_deg[i] + frac * (phase_deg[i + 1] - phase_deg[i]))
            pm_deg = 180.0 + ph_u
            break

    gm_db = float("inf")
    for i in range(len(phase_deg) - 1):
        if phase_deg[i] >= -180.0 > phase_deg[i + 1]:
            frac = (-180.0 - phase_deg[i]) / (phase_deg[i + 1] - phase_deg[i])
            gm_db = -float(mag_db[i] + frac * (mag_db[i + 1] - mag_db[i]))
            break

    return {
        "t0_db": a0_db,
        "ugf_mhz": ugf_hz * 1e-6 if math.isfinite(ugf_hz) else float("nan"),
        "phase_margin_deg": pm_deg,
        "gain_margin_db": gm_db,
    }


def analyze_dm_cm_stb(psf_dir: Path) -> dict[str, object]:
    f_dm = find_single(psf_dir, ["stb_dm.stb", "*dm*.stb"])
    f_cm = find_single(psf_dir, ["stb_cm.stb", "*cm*.stb"])
    return {
        "differential_mode": _extract_stb_file(f_dm),
        "common_mode": _extract_stb_file(f_cm),
    }


def analyze_slew_settle(psf_dir: Path, *, t_step: float, vocm: float) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vdiff = d["VOP"] - d["VON"]
    vcm = 0.5 * (d["VOP"] + d["VON"])

    v_pre = float(np.mean(vdiff[(t > 0.2 * t_step) & (t < 0.95 * t_step)]))
    v_fin = float(vdiff[-1])
    dv = v_fin - v_pre

    m = t >= t_step
    tw, vw = t[m], vdiff[m]
    direction = "rising" if dv > 0 else "falling"
    t20 = crossings(tw, vw, v_pre + 0.2 * dv, direction)[0]
    t80 = crossings(tw, vw, v_pre + 0.8 * dv, direction)[0]
    sr_diff = (0.6 * abs(dv) / abs(t80 - t20)) * 1e-6  # V/us

    def settle(tol_frac: float) -> float:
        out = np.where(np.abs(vw - v_fin) > tol_frac * abs(dv))[0]
        if len(out) == 0:
            return 0.0
        return float(tw[out[-1] + 1] - t_step) if out[-1] + 1 < len(tw) else float("nan")

    ts_0p1 = settle(1e-3)
    ts_0p01 = settle(1e-4)
    vocm_err_mv = float(np.max(np.abs(vcm[m] - vocm)) * 1e3)

    return {
        "delta_vdiff_v": dv,
        "sr_diff_v_per_us": sr_diff,
        "t_settle_0p1pct_ns": ts_0p1 * 1e9 if math.isfinite(ts_0p1) else float("nan"),
        "t_settle_0p01pct_ns": ts_0p01 * 1e9 if math.isfinite(ts_0p01) else float("nan"),
        "vocm_max_disturbance_mv": vocm_err_mv,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze fully differential OTA Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_stb = sub.add_parser("dm_cm_stb")
    p_stb.add_argument("psf_dir", type=Path)

    p_sl = sub.add_parser("slew_settle")
    p_sl.add_argument("psf_dir", type=Path)
    p_sl.add_argument("--t-step", type=float, default=100e-9)
    p_sl.add_argument("--vocm", type=float, default=0.45)

    args = ap.parse_args(argv)
    if args.mode == "dm_cm_stb":
        res = analyze_dm_cm_stb(args.psf_dir)
    else:
        res = analyze_slew_settle(args.psf_dir, t_step=args.t_step, vocm=args.vocm)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
