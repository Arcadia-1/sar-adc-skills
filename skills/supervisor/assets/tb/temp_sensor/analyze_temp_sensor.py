#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from On-Chip Temperature Sensor & TSD testbenches.

Usage:
  python analyze_temp_sensor.py linearity <psf_dir> [--s-nom-mv-per-c 2.0]
  python analyze_temp_sensor.py psrr_noise <psf_dir> [--s-nom-mv-per-c 2.0]
  python analyze_temp_sensor.py tsd <psf_dir> [--min-hys-c 5.0]
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

from psf_utils import crossings, find_single, parse_psf_ascii, trapz


def _sweep_key(d: dict[str, np.ndarray], exclude: set[str]) -> str:
    for cand in ("temp", "temperature", "vdd_in", "VDD"):
        if cand in d and cand not in exclude:
            return cand
    return next(k for k in d if k not in exclude)


def analyze_linearity(
    psf_dir: Path,
    *,
    s_nom_mv_per_c: float = 2.0,
) -> dict[str, float]:
    f = find_single(psf_dir, ["dc_temp.dc", "*temp*.dc", "*.dc"])
    d = parse_psf_ascii(f)
    t_key = _sweep_key(d, {"VBE", "VPTAT", "VTEMP", "TSD_OUT", "VSUP:p", "VDD", "CHOP"})
    temp = np.asarray(d[t_key], dtype=float)
    vbe = np.asarray(d["VBE"], dtype=float)
    vptat = np.asarray(d["VPTAT"], dtype=float)
    vtemp = np.asarray(d["VTEMP"], dtype=float)

    order = np.argsort(temp)
    temp, vbe, vptat, vtemp = temp[order], vbe[order], vptat[order], vtemp[order]

    # Slopes [mV/C]
    s_vbe = float(np.polyfit(temp, vbe, 1)[0])
    s_vptat = float(np.polyfit(temp, vptat, 1)[0])
    c1, c0 = np.polyfit(temp, vtemp, 1)
    c1, c0 = float(c1), float(c0)

    # 1. Raw uncalibrated error against nominal ratiometric Kelvin scale V = s_nom * (T_C + 273.15)
    s_nom = s_nom_mv_per_c * 1e-3
    err_raw = (vtemp / s_nom - 273.15) - temp

    # 2. 1-point gain-trimmed error at 27 C (standard wafer-sort single-point PTAT/ratio cal)
    v_27 = float(np.interp(27.0, temp, vtemp))
    s_1pt = v_27 / 300.15
    err_1pt = (vtemp / s_1pt - 273.15) - temp

    # 3. 2-point linear trimmed residual (isolates irreducible 2nd-order BJT curvature bow)
    err_2pt = (vtemp - c0) / c1 - temp
    err_2pt_p2p = float(np.max(err_2pt) - np.min(err_2pt))

    res: dict[str, float] = {
        "temp_min_c": float(temp[0]),
        "temp_max_c": float(temp[-1]),
        "vbe_27c_v": float(np.interp(27.0, temp, vbe)),
        "vbe_slope_mv_per_c": s_vbe * 1e3,
        "vptat_27c_v": float(np.interp(27.0, temp, vptat)),
        "vptat_slope_mv_per_c": s_vptat * 1e3,
        "vtemp_27c_v": v_27,
        "sens_mv_per_c": c1 * 1e3,
        "err_raw_max_abs_c": float(np.max(np.abs(err_raw))),
        "err_1pt_27c_max_abs_c": float(np.max(np.abs(err_1pt))),
        "err_2pt_min_c": float(np.min(err_2pt)),
        "err_2pt_max_c": float(np.max(err_2pt)),
        "err_2pt_max_abs_c": float(np.max(np.abs(err_2pt))),
        "err_2pt_p2p_c": err_2pt_p2p,
        "err_2pt_half_span_c": 0.5 * err_2pt_p2p,
    }
    if "VSUP:p" in d:
        i_sup = np.abs(np.asarray(d["VSUP:p"], dtype=float)[order])
        res["iq_27c_ua"] = float(np.interp(27.0, temp, i_sup) * 1e6)
    return res


def analyze_psrr_noise(
    psf_dir: Path,
    *,
    s_nom_mv_per_c: float = 2.0,
) -> dict[str, object]:
    # 1. Chopped (CHOP=1) local slope and 27 C output
    f_c1 = find_single(psf_dir, ["dc_chop1.dc", "*chop1*.dc"])
    dc1 = parse_psf_ascii(f_c1)
    t_k1 = _sweep_key(dc1, {"VDD", "CHOP", "VTEMP", "VPTAT", "VBE", "VSUP:p"})
    t1 = np.asarray(dc1[t_k1], dtype=float)
    vt1 = np.asarray(dc1["VTEMP"], dtype=float)
    sens_v_per_c = float(np.polyfit(t1, vt1, 1)[0])
    vtemp_c1_27 = float(np.interp(27.0, t1, vt1))

    # 2. Supply voltage sensitivity (CHOP=1)
    f_vdd = find_single(psf_dir, ["dc_vdd.dc", "*vdd*.dc"])
    dv = parse_psf_ascii(f_vdd)
    vdd_arr = np.asarray(dv["VDD"] if "VDD" in dv else dv[_sweep_key(dv, {"CHOP", "VTEMP", "VPTAT", "VBE", "VSUP:p"})], dtype=float)
    vt_vdd = np.asarray(dv["VTEMP"], dtype=float)
    dvtemp_dvdd = float(np.polyfit(vdd_arr, vt_vdd, 1)[0])
    supply_sens_c_per_v = abs(dvtemp_dvdd) / max(abs(sens_v_per_c), 1e-12)
    psrr_dc_db = -20.0 * math.log10(max(abs(dvtemp_dvdd), 1e-30))

    # 3. Integrated noise with CHOP=1 (1 Hz .. 100 kHz)
    f_n1 = find_single(psf_dir, ["noise_chop1.noise", "*noise_chop1*", "*.noise"])
    dn1 = parse_psf_ascii(f_n1)
    fn1 = np.real(dn1["freq"])
    vn1 = np.real(dn1["out"])
    v_rms_c1 = math.sqrt(max(trapz(vn1**2, fn1), 0.0))
    temp_noise_mk_rms = (v_rms_c1 / max(abs(sens_v_per_c), 1e-12)) * 1e3

    # 4. Unchopped (CHOP=0) offset & 1/f noise comparison
    f_c0 = find_single(psf_dir, ["dc_chop0.dc", "*chop0*.dc"])
    dc0 = parse_psf_ascii(f_c0)
    t_k0 = _sweep_key(dc0, {"VDD", "CHOP", "VTEMP", "VPTAT", "VBE", "VSUP:p"})
    vtemp_c0_27 = float(np.interp(27.0, np.asarray(dc0[t_k0], dtype=float), np.asarray(dc0["VTEMP"], dtype=float)))

    v_ideal_27 = (s_nom_mv_per_c * 1e-3) * 300.15
    err_unchopped_c = (vtemp_c0_27 - v_ideal_27) / max(abs(sens_v_per_c), 1e-12)
    err_chopped_c = (vtemp_c1_27 - v_ideal_27) / max(abs(sens_v_per_c), 1e-12)
    chop_suppression_x = abs(err_unchopped_c) / max(abs(err_chopped_c), 1e-6)

    f_n0 = find_single(psf_dir, ["noise_chop0.noise", "*noise_chop0*"])
    dn0 = parse_psf_ascii(f_n0)
    fn0 = np.real(dn0["freq"])
    vn0 = np.real(dn0["out"])
    v_rms_c0 = math.sqrt(max(trapz(vn0**2, fn0), 0.0))
    temp_noise_unchopped_mk_rms = (v_rms_c0 / max(abs(sens_v_per_c), 1e-12)) * 1e3

    return {
        "sens_mv_per_c": sens_v_per_c * 1e3,
        "supply_sens_c_per_v": float(supply_sens_c_per_v),
        "psrr_dc_db": float(psrr_dc_db),
        "v_noise_chopped_uvrms": float(v_rms_c1 * 1e6),
        "temp_noise_mk_rms": float(temp_noise_mk_rms),
        "v_noise_unchopped_uvrms": float(v_rms_c0 * 1e6),
        "temp_noise_unchopped_mk_rms": float(temp_noise_unchopped_mk_rms),
        "err_unchopped_c": float(err_unchopped_c),
        "err_chopped_c": float(err_chopped_c),
        "chop_offset_delta_c": float(err_unchopped_c - err_chopped_c),
        "chop_suppression_x": float(chop_suppression_x),
        "chop_pass": bool(chop_suppression_x >= 10.0),
    }


def analyze_tsd(psf_dir: Path, *, min_hys_c: float = 5.0) -> dict[str, object]:
    f_up = find_single(psf_dir, ["dc_up.dc", "*up*.dc"])
    f_dn = find_single(psf_dir, ["dc_dn.dc", "*dn*.dc"])
    du = parse_psf_ascii(f_up)
    dd = parse_psf_ascii(f_dn)

    excl = {"TSD_OUT", "VTEMP", "VBE", "VPTAT", "VDD", "VSUP:p", "CHOP"}
    tu = np.asarray(du[_sweep_key(du, excl)], dtype=float)
    yu = np.asarray(du["TSD_OUT"], dtype=float)
    td = np.asarray(dd[_sweep_key(dd, excl)], dtype=float)
    yd = np.asarray(dd["TSD_OUT"], dtype=float)

    vdd_val = float(np.median(du["VDD"])) if "VDD" in du else max(float(np.max(yu)), 1.0)
    v_th = 0.5 * vdd_val

    # Rising sweep: ensure ascending temperature order
    if tu[-1] < tu[0]:
        tu, yu = tu[::-1], yu[::-1]
    up_x = crossings(tu, yu, v_th, direction="rising")
    if not up_x:
        raise RuntimeError("TSD_OUT never tripped HIGH during rising temperature sweep")
    t_trip = float(up_x[0])

    # Falling sweep: traverse in descending temperature order (hot -> cold)
    if td[-1] > td[0]:
        td, yd = td[::-1], yd[::-1]
    # Walk from high T to low T: crossings() interpolates linearly along index order
    dn_x = crossings(td, yd, v_th, direction="falling")
    if not dn_x:
        raise RuntimeError("TSD_OUT never released LOW during falling temperature sweep")
    t_release = float(dn_x[0])

    t_hys = t_trip - t_release
    tripped = bool(float(np.max(yu)) >= 0.9 * vdd_val and float(np.min(yu)) <= 0.1 * vdd_val)
    released = bool(float(np.max(yd)) >= 0.9 * vdd_val and float(np.min(yd)) <= 0.1 * vdd_val)
    hys_pass = bool(tripped and released and t_hys >= min_hys_c)

    return {
        "vdd_v": vdd_val,
        "t_trip_c": t_trip,
        "t_release_c": t_release,
        "t_hys_c": float(t_hys),
        "tsd_tripped": tripped,
        "tsd_released": released,
        "hys_pass": hys_pass,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze Temperature Sensor & TSD Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_lin = sub.add_parser("linearity", help="Extract -40..125 C sensitivity, 1-pt & 2-pt curvature")
    p_lin.add_argument("psf_dir", type=Path)
    p_lin.add_argument("--s-nom-mv-per-c", type=float, default=2.0)

    p_pn = sub.add_parser("psrr_noise", help="Extract supply sensitivity, noise [mK_rms] & chop check")
    p_pn.add_argument("psf_dir", type=Path)
    p_pn.add_argument("--s-nom-mv-per-c", type=float, default=2.0)

    p_tsd = sub.add_parser("tsd", help="Extract T_trip, T_release, and thermal hysteresis [deg C]")
    p_tsd.add_argument("psf_dir", type=Path)
    p_tsd.add_argument("--min-hys-c", type=float, default=5.0)

    args = ap.parse_args(argv)
    if args.mode == "linearity":
        res: object = analyze_linearity(args.psf_dir, s_nom_mv_per_c=args.s_nom_mv_per_c)
    elif args.mode == "psrr_noise":
        res = analyze_psrr_noise(args.psf_dir, s_nom_mv_per_c=args.s_nom_mv_per_c)
    else:
        res = analyze_tsd(args.psf_dir, min_hys_c=args.min_hys_c)

    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
