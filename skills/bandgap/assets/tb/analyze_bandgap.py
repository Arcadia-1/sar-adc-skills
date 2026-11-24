#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from Bandgap Reference testbenches.

Usage:
  python analyze_bandgap.py temp_line <psf_dir>
  python analyze_bandgap.py startup <psf_dir> [--t-delay 2e-6]
  python analyze_bandgap.py psrr_noise <psf_dir>
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

from psf_utils import find_single, parse_psf_ascii, trapz


def analyze_temp_line(psf_dir: Path) -> dict[str, float]:
    f_t = find_single(psf_dir, ["dc_temp.dc", "*temp*.dc"])
    dt = parse_psf_ascii(f_t)
    t_key = next(k for k in dt if k not in {"VREF", "VDD", "VSUP:p"})
    temp = dt[t_key]
    vref = dt["VREF"]

    v_min = float(np.min(vref))
    v_max = float(np.max(vref))
    v_27 = float(np.interp(27.0, temp, vref))
    t_span = float(temp[-1] - temp[0])
    tc_ppm = (v_max - v_min) / (v_27 * t_span) * 1e6
    t_peak = float(temp[int(np.argmax(vref))])

    f_l = find_single(psf_dir, ["dc_line.dc", "*line*.dc"])
    dl = parse_psf_ascii(f_l)
    vdd = dl["VDD"] if "VDD" in dl else dl[next(iter(dl))]
    vl = dl["VREF"]
    v_hi = float(vl[-1])
    in_reg = vl >= 0.99 * v_hi
    idx_min = int(np.where(in_reg)[0][0]) if np.any(in_reg) else 0
    vdd_min = float(vdd[idx_min])

    reg_m = vdd >= (vdd_min + 0.1)
    line_reg = (
        float((vl[reg_m][-1] - vl[reg_m][0]) / (vdd[reg_m][-1] - vdd[reg_m][0]) * 1e3)
        if np.sum(reg_m) >= 2
        else float("nan")
    )

    res: dict[str, float] = {
        "vref_27c_v": v_27,
        "vref_min_v": v_min,
        "vref_max_v": v_max,
        "temp_peak_c": t_peak,
        "tc_box_ppm_per_c": tc_ppm,
        "vdd_min_1pct_v": vdd_min,
        "line_reg_mv_per_v": line_reg,
    }
    if "VSUP:p" in dt:
        res["iq_27c_ua"] = float(abs(np.interp(27.0, temp, dt["VSUP:p"])) * 1e6)
    return res


def analyze_startup(psf_dir: Path, *, t_delay: float) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vref = d["VREF"]

    v_final = float(np.mean(vref[t >= 0.9 * float(t[-1])]))
    started = v_final > 0.1
    m = t >= t_delay
    tw, vw = t[m], vref[m]

    out = np.where(np.abs(vw - v_final) > 0.01 * max(abs(v_final), 1e-6))[0]
    t_start_1pct = float(tw[out[-1] + 1] - t_delay) if (len(out) > 0 and out[-1] + 1 < len(tw)) else 0.0
    overshoot_pct = max((float(np.max(vw)) - v_final) / max(abs(v_final), 1e-6) * 100.0, 0.0)

    return {
        "started_cleanly": bool(started),
        "vref_final_v": v_final,
        "t_startup_1pct_us": t_start_1pct * 1e6,
        "overshoot_pct": overshoot_pct,
    }


def analyze_psrr_noise(psf_dir: Path) -> dict[str, float]:
    f_ac = find_single(psf_dir, ["ac.ac", "*.ac.ac", "*.ac"])
    dac = parse_psf_ascii(f_ac)
    freq = np.real(dac["freq"])
    log_f = np.log10(freq)
    h = np.abs(dac["VREF"]) / np.maximum(np.abs(dac.get("VDD", np.ones_like(dac["VREF"]))), 1e-30)
    psrr = -20.0 * np.log10(np.maximum(h, 1e-30))

    def at(f_hz: float) -> float:
        return float(np.interp(math.log10(f_hz), log_f, psrr))

    f_n = find_single(psf_dir, ["noise.noise", "*.noise"])
    dn = parse_psf_ascii(f_n)
    fn = np.real(dn["freq"])
    vn = np.real(dn["out"])
    vrms = math.sqrt(max(trapz(vn**2, fn), 0.0))

    return {
        "psrr_dc_db": float(psrr[0]),
        "psrr_10khz_db": at(1e4),
        "psrr_100khz_db": at(1e5),
        "psrr_1mhz_db": at(1e6),
        "output_noise_uvrms": vrms * 1e6,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze Bandgap Reference Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_tl = sub.add_parser("temp_line")
    p_tl.add_argument("psf_dir", type=Path)

    p_st = sub.add_parser("startup")
    p_st.add_argument("psf_dir", type=Path)
    p_st.add_argument("--t-delay", type=float, default=2e-6)

    p_pn = sub.add_parser("psrr_noise")
    p_pn.add_argument("psf_dir", type=Path)

    args = ap.parse_args(argv)
    if args.mode == "temp_line":
        res = analyze_temp_line(args.psf_dir)
    elif args.mode == "startup":
        res = analyze_startup(args.psf_dir, t_delay=args.t_delay)
    else:
        res = analyze_psrr_noise(args.psf_dir)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
