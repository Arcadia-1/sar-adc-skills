#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from SerDes CTLE & VGA testbenches.

Usage:
  python analyze_ctle_vga.py ac_noise <psf_dir>
  python analyze_ctle_vga.py eye <psf_dir> [--ui 100e-12] [--t-skip 4e-9]
  python analyze_ctle_vga.py offset_cal <psf_dir>
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

from psf_utils import (
    eye_diagram_metrics,
    find_single,
    parse_psf_ascii,
    sbr_cursor_metrics,
    trapz,
)


def analyze_ac_noise(psf_dir: Path) -> dict[str, float]:
    f_ac = find_single(psf_dir, ["ac.ac", "*.ac.ac", "*.ac"])
    dac = parse_psf_ascii(f_ac)
    freq = np.real(dac["freq"])
    h = (dac["OUTP"] - dac["OUTN"]) / np.maximum(np.abs(dac["INP"] - dac["INN"]), 1e-30)
    mag_db = 20.0 * np.log10(np.maximum(np.abs(h), 1e-30))

    dc_db = float(mag_db[0])
    idx_pk = int(np.argmax(mag_db))
    pk_db = float(mag_db[idx_pk])
    f_pk = float(freq[idx_pk])
    peaking_db = pk_db - dc_db

    # -3 dB bandwidth relative to DC gain (scanning downward after the peak)
    f3db = float("nan")
    ref = dc_db - 3.0
    for i in range(idx_pk, len(mag_db) - 1):
        if mag_db[i] >= ref > mag_db[i + 1]:
            frac = (ref - mag_db[i]) / (mag_db[i + 1] - mag_db[i])
            f3db = float(10.0 ** (math.log10(freq[i]) + frac * (math.log10(freq[i + 1]) - math.log10(freq[i]))))
            break

    f_n = find_single(psf_dir, ["noise.noise", "*.noise"])
    dn = parse_psf_ascii(f_n)
    fn = np.real(dn["freq"])
    vn = np.real(dn["out"])
    vout_rms = math.sqrt(max(trapz(vn**2, fn), 0.0))
    vn_1g = float(np.interp(math.log10(1e9), np.log10(fn), vn))

    return {
        "dc_gain_db": dc_db,
        "peak_gain_db": pk_db,
        "peaking_db": peaking_db,
        "f_peak_ghz": f_pk / 1e9,
        "f_3db_ghz": f3db / 1e9,
        "out_noise_mvrms": vout_rms * 1e3,
        "out_noise_1ghz_nv_rthz": vn_1g * 1e9,
    }


def analyze_eye(psf_dir: Path, *, ui: float, t_skip: float) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_in = d["RX_INP"] - d["RX_INN"]
    v_out = d["OUTP"] - d["OUTN"]
    s_in = d["SRX_INP"] - d["SRX_INN"]
    s_out = d["SOUTP"] - d["SOUTN"]

    return {
        "before_ctle_eye": eye_diagram_metrics(t, v_in, ui_s=ui, t_skip=t_skip),
        "after_ctle_eye": eye_diagram_metrics(t, v_out, ui_s=ui, t_skip=t_skip),
        "before_ctle_sbr": sbr_cursor_metrics(t, s_in, ui_s=ui, t_base_end=25.0 * ui),
        "after_ctle_sbr": sbr_cursor_metrics(t, s_out, ui_s=ui, t_base_end=25.0 * ui),
    }


def analyze_offset_cal(psf_dir: Path) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_out = d["OUTP"] - d["OUTN"]
    v_cal = d["VOFF_CAL"]
    code = d["CODE_MON"]
    done = d["DONE"]

    v_init_mv = float(v_out[0] * 1e3)
    tail = t >= 0.9 * float(t[-1])
    v_final_mv = float(np.mean(v_out[tail]) * 1e3)
    converged = bool(float(done[-1]) > 0.5)
    idx_done = np.where(done > 0.5)[0]
    t_conv_ns = float(t[idx_done[0]] * 1e9) if len(idx_done) > 0 else float("nan")

    return {
        "converged": converged,
        "t_converge_ns": t_conv_ns,
        "initial_out_offset_mv": v_init_mv,
        "residual_out_offset_mv": v_final_mv,
        "final_cal_code": int(round(float(code[-1]))),
        "final_voff_cal_mv": float(v_cal[-1] * 1e3),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze SerDes CTLE & VGA Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_an = sub.add_parser("ac_noise")
    p_an.add_argument("psf_dir", type=Path)

    p_ey = sub.add_parser("eye")
    p_ey.add_argument("psf_dir", type=Path)
    p_ey.add_argument("--ui", type=float, default=100e-12)
    p_ey.add_argument("--t-skip", type=float, default=5.0e-9)

    p_oc = sub.add_parser("offset_cal")
    p_oc.add_argument("psf_dir", type=Path)

    args = ap.parse_args(argv)
    if args.mode == "ac_noise":
        res: object = analyze_ac_noise(args.psf_dir)
    elif args.mode == "eye":
        res = analyze_eye(args.psf_dir, ui=args.ui, t_skip=args.t_skip)
    else:
        res = analyze_offset_cal(args.psf_dir)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
