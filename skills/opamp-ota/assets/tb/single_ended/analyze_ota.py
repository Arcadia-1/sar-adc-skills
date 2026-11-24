#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from single-ended OpAmp/OTA testbenches.

Usage:
  python analyze_ota.py stb <psf_dir> [--vdd 0.9] [--cload-pf 2.0]
  python analyze_ota.py cmrr_psrr_noise <psf_dir>
  python analyze_ota.py slew_settle <psf_dir> [--t-rise 200e-9] [--t-fall 1.2e-6] [--cload-pf 2.0]
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


def analyze_stb(psf_dir: Path, *, vdd: float, cload_pf: float) -> dict[str, float]:
    f_stb = find_single(psf_dir, ["stb.stb", "*.stb.stb"])
    d = parse_psf_ascii(f_stb)
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

    res: dict[str, float] = {
        "a0_db": a0_db,
        "ugf_mhz": ugf_hz * 1e-6 if math.isfinite(ugf_hz) else float("nan"),
        "phase_margin_deg": pm_deg,
        "gain_margin_db": gm_db,
    }

    # Optional DC power & FoM_S from dc.dc if present
    try:
        f_dc = find_single(psf_dir, ["dc.dc", "*.dc"])
        ddc = parse_psf_ascii(f_dc)
        if "VSUP:p" in ddc:
            idd_ma = abs(float(ddc["VSUP:p"][0])) * 1e3
            res["idd_ua"] = idd_ma * 1e3
            res["p_dc_mw"] = idd_ma * vdd
            if math.isfinite(ugf_hz) and idd_ma > 0.0:
                res["fom_s_mhz_pf_per_ma"] = (ugf_hz * 1e-6) * cload_pf / idd_ma
    except Exception:
        pass
    return res


def analyze_cmrr_psrr_noise(psf_dir: Path) -> dict[str, float]:
    f_ac = find_single(psf_dir, ["ac.ac", "*.ac.ac", "*.ac"])
    da = parse_psf_ascii(f_ac)
    freq = np.real(da["freq"])
    log_f = np.log10(freq)

    adm = np.maximum(np.abs(da["VOUT_DM"]), 1e-30)
    acm = np.maximum(np.abs(da["VOUT_CM"]), 1e-30)
    app = np.maximum(np.abs(da["VOUT_PP"]), 1e-30)
    apn = np.maximum(np.abs(da["VOUT_PN"]), 1e-30)

    cmrr = 20.0 * np.log10(adm / acm)
    psrr_p = 20.0 * np.log10(adm / app)
    psrr_n = 20.0 * np.log10(adm / apn)

    def at(arr: np.ndarray, f_hz: float) -> float:
        return float(np.interp(math.log10(f_hz), log_f, arr))

    res: dict[str, float] = {
        "adm_dc_db": float(20.0 * math.log10(adm[0])),
        "cmrr_dc_db": float(cmrr[0]),
        "cmrr_1mhz_db": at(cmrr, 1e6),
        "psrr_p_dc_db": float(psrr_p[0]),
        "psrr_p_1mhz_db": at(psrr_p, 1e6),
        "psrr_n_dc_db": float(psrr_n[0]),
        "psrr_n_1mhz_db": at(psrr_n, 1e6),
    }

    f_n = find_single(psf_dir, ["noise.noise", "*.noise"])
    dn = parse_psf_ascii(f_n)
    fn = np.real(dn["freq"])
    log_fn = np.log10(fn)
    vn_in = np.real(dn["in"]) if "in" in dn else np.real(dn["out"]) / np.interp(fn, freq, adm)
    vn_rms = math.sqrt(max(trapz(vn_in**2, fn), 0.0))

    res["vn_in_1khz_nv_rthz"] = float(np.interp(math.log10(1e3), log_fn, vn_in) * 1e9)
    res["vn_in_100khz_nv_rthz"] = float(np.interp(math.log10(1e5), log_fn, vn_in) * 1e9)
    res["vn_in_1mhz_nv_rthz"] = float(np.interp(math.log10(1e6), log_fn, vn_in) * 1e9)
    res["vn_in_int_uvrms"] = vn_rms * 1e6
    return res


def analyze_slew_settle(
    psf_dir: Path, *, t_rise: float, t_fall: float, cload_pf: float
) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vout = d["VOUT"]

    v_lo_ss = float(np.mean(vout[(t > 0.2 * t_rise) & (t < 0.95 * t_rise)]))
    v_hi_ss = float(np.mean(vout[(t > t_fall - 0.1 * (t_fall - t_rise)) & (t < 0.99 * t_fall)]))
    dv = v_hi_ss - v_lo_ss

    # Rising step [t_rise .. t_fall)
    m_r = (t >= t_rise) & (t < t_fall)
    tr_arr, vr_arr = t[m_r], vout[m_r]
    t20_r = crossings(tr_arr, vr_arr, v_lo_ss + 0.2 * dv, "rising")[0]
    t80_r = crossings(tr_arr, vr_arr, v_lo_ss + 0.8 * dv, "rising")[0]
    sr_pos = (0.6 * dv / (t80_r - t20_r)) * 1e-6  # V/us
    overshoot_pct = max((float(np.max(vr_arr)) - v_hi_ss) / dv * 100.0, 0.0)

    def settle_time(t_w: np.ndarray, v_w: np.ndarray, t0: float, v_tgt: float, tol_frac: float) -> float:
        out = np.where(np.abs(v_w - v_tgt) > tol_frac * abs(dv))[0]
        if len(out) == 0:
            return 0.0
        if out[-1] + 1 < len(t_w):
            return float(t_w[out[-1] + 1] - t0)
        return float("nan")

    ts_0p1_r = settle_time(tr_arr, vr_arr, t_rise, v_hi_ss, 1e-3)
    ts_0p01_r = settle_time(tr_arr, vr_arr, t_rise, v_hi_ss, 1e-4)

    # Falling step [t_fall .. end]
    m_f = t >= t_fall
    tf_arr, vf_arr = t[m_f], vout[m_f]
    t80_f = crossings(tf_arr, vf_arr, v_lo_ss + 0.8 * dv, "falling")[0]
    t20_f = crossings(tf_arr, vf_arr, v_lo_ss + 0.2 * dv, "falling")[0]
    sr_neg = (0.6 * dv / (t20_f - t80_f)) * 1e-6  # V/us
    ts_0p1_f = settle_time(tf_arr, vf_arr, t_fall, v_lo_ss, 1e-3)

    res: dict[str, float] = {
        "step_v": dv,
        "sr_pos_v_per_us": sr_pos,
        "sr_neg_v_per_us": sr_neg,
        "overshoot_pct": overshoot_pct,
        "t_settle_0p1pct_rise_ns": ts_0p1_r * 1e9 if math.isfinite(ts_0p1_r) else float("nan"),
        "t_settle_0p01pct_rise_ns": ts_0p01_r * 1e9 if math.isfinite(ts_0p01_r) else float("nan"),
        "t_settle_0p1pct_fall_ns": ts_0p1_f * 1e9 if math.isfinite(ts_0p1_f) else float("nan"),
    }
    if "VSUP:p" in d:
        idd_ma = abs(float(np.mean(d["VSUP:p"][(t > 0.2 * t_rise) & (t < 0.95 * t_rise)]))) * 1e3
        if idd_ma > 0.0:
            res["fom_l_vus_pf_per_ma"] = min(sr_pos, sr_neg) * cload_pf / idd_ma
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze single-ended OpAmp/OTA Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_stb = sub.add_parser("stb")
    p_stb.add_argument("psf_dir", type=Path)
    p_stb.add_argument("--vdd", type=float, default=0.9)
    p_stb.add_argument("--cload-pf", type=float, default=2.0)

    p_cpn = sub.add_parser("cmrr_psrr_noise")
    p_cpn.add_argument("psf_dir", type=Path)

    p_sl = sub.add_parser("slew_settle")
    p_sl.add_argument("psf_dir", type=Path)
    p_sl.add_argument("--t-rise", type=float, default=200e-9)
    p_sl.add_argument("--t-fall", type=float, default=1.2e-6)
    p_sl.add_argument("--cload-pf", type=float, default=2.0)

    args = ap.parse_args(argv)
    if args.mode == "stb":
        res = analyze_stb(args.psf_dir, vdd=args.vdd, cload_pf=args.cload_pf)
    elif args.mode == "cmrr_psrr_noise":
        res = analyze_cmrr_psrr_noise(args.psf_dir)
    else:
        res = analyze_slew_settle(
            args.psf_dir, t_rise=args.t_rise, t_fall=args.t_fall, cload_pf=args.cload_pf
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
