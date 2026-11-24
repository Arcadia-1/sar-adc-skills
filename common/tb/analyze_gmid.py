#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from universal NMOS/PMOS gm/Id sweep.

Usage:
  python analyze_gmid.py <psf_dir> [--wn-um 2.0] [--wp-um 2.0]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

COMMON_DIR = Path(__file__).resolve().parents[1]
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from psf_utils import find_single, parse_psf_ascii


def _extract_device(
    d: dict[str, np.ndarray], prefix: str, vgs: np.ndarray, w_um: float
) -> dict[str, object]:
    id_a = np.abs(d[f"{prefix}:id"])
    gm = np.abs(d[f"{prefix}:gm"])
    gds = np.abs(d[f"{prefix}:gds"])
    cgg = np.abs(d[f"{prefix}:cgg"])
    vth = np.abs(d[f"{prefix}:vth"])

    valid = (id_a > 1e-12) & (gm > 1e-12)
    vgs_v = vgs[valid]
    id_v = id_a[valid]
    gm_v = gm[valid]
    gds_v = np.maximum(gds[valid], 1e-15)
    cgg_v = np.maximum(cgg[valid], 1e-21)
    vth_v = vth[valid]

    gmid = gm_v / id_v
    id_w_ua_um = (id_v * 1e6) / w_um
    gm_ro = gm_v / gds_v
    ft_ghz = gm_v / (2.0 * math.pi * cgg_v) / 1e9

    # Sort ascending by gm/Id for clean interpolation at standard design targets
    order = np.argsort(gmid)
    gmid_s = gmid[order]
    table: dict[str, dict[str, float]] = {}
    for target in (5.0, 10.0, 15.0, 20.0):
        if float(gmid_s[0]) <= target <= float(gmid_s[-1]):
            table[f"gmid_{int(target)}"] = {
                "vgs_v": float(np.interp(target, gmid_s, vgs_v[order])),
                "vov_v": float(np.interp(target, gmid_s, (vgs_v - vth_v)[order])),
                "id_per_w_ua_per_um": float(np.interp(target, gmid_s, id_w_ua_um[order])),
                "gm_ro": float(np.interp(target, gmid_s, gm_ro[order])),
                "ft_ghz": float(np.interp(target, gmid_s, ft_ghz[order])),
            }

    return {
        "gmid_min_per_v": float(np.min(gmid)),
        "gmid_max_per_v": float(np.max(gmid)),
        "ft_peak_ghz": float(np.max(ft_ghz)),
        "gm_ro_peak": float(np.max(gm_ro)),
        "lookup": table,
    }


def analyze_gmid(psf_dir: Path, *, wn_um: float, wp_um: float) -> dict[str, object]:
    f = find_single(psf_dir, ["dc_gmid.dc", "*gmid*.dc", "*.dc"])
    d = parse_psf_ascii(f)
    sweep_key = next(k for k in d if ":" not in k)
    vgs = np.real(d[sweep_key])
    return {
        "nmos": _extract_device(d, "MN", vgs, wn_um),
        "pmos": _extract_device(d, "MP", vgs, wp_um),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze NMOS & PMOS gm/Id sweep outputs.")
    ap.add_argument("psf_dir", type=Path)
    ap.add_argument("--wn-um", type=float, default=2.0)
    ap.add_argument("--wp-um", type=float, default=2.0)
    args = ap.parse_args(argv)
    print(json.dumps(analyze_gmid(args.psf_dir, wn_um=args.wn_um, wp_um=args.wp_um), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
