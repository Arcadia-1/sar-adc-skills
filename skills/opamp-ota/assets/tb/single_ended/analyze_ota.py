#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from single-ended OpAmp/OTA signoff testbenches.

Usage:
  python analyze_ota.py stb <psf_dir> [--vdd 0.9] [--cload-pf 2.0]
  python analyze_ota.py cmrr_psrr_noise <psf_dir>
  python analyze_ota.py slew_settle <psf_dir> [--t-rise 200e-9] [--t-fall 1.2e-6] [--cload-pf 2.0]
  python analyze_ota.py dc_signoff <psf_dir> [--vdd 0.9] [--vcm 0.45]
  python analyze_ota.py cl_zout_gm <psf_dir> [--r-gm 10.0] [--rload 1e6]
  python analyze_ota.py thd_fpbw <psf_dir> [--m-bin 3] [--f-in 10e3]
  python analyze_ota.py power_ramp <psf_dir> [--vdd 0.9] [--t-ramp 5e-3] [--t-hold 2e-3]
  python analyze_ota.py supply_surge_cmstep <psf_dir> [--vcm 0.45] [--t-cm-rise 2e-6] [--t-cm-fall 10e-6]
"""

from __future__ import annotations

import argparse
import json
import math
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

from psf_utils import (
    coherent_fft_metrics,
    crossings,
    extract_uniform_strobe,
    find_single,
    parse_psf_ascii,
    trapz,
)


def _contiguous_range(x: np.ndarray, mask: np.ndarray, center_idx: int) -> tuple[float, float]:
    """Return [x_lo, x_hi] of the contiguous True span containing `center_idx`."""
    if len(x) == 0 or not bool(mask[center_idx]):
        return (float("nan"), float("nan"))
    lo = center_idx
    while lo > 0 and bool(mask[lo - 1]):
        lo -= 1
    hi = center_idx
    while hi + 1 < len(x) and bool(mask[hi + 1]):
        hi += 1
    return (float(x[lo]), float(x[hi]))


def _detect_oscillation(t: np.ndarray, err: np.ndarray, thresh_v: float) -> bool:
    """Detect sustained ringing / oscillation (> 6 alternating extrema above threshold)."""
    if len(err) < 8:
        return False
    y = err - float(np.median(err))
    peaks = 0
    last_sign = 0
    for val in y:
        if val > thresh_v and last_sign != 1:
            peaks += 1
            last_sign = 1
        elif val < -thresh_v and last_sign != -1:
            peaks += 1
            last_sign = -1
    return peaks > 6


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
            ugf_hz = float(
                10.0 ** (math.log10(freq[i]) + frac * (math.log10(freq[i + 1]) - math.log10(freq[i])))
            )
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

    if "VOUT_CM4R" in da:
        acm4r = np.maximum(np.abs(da["VOUT_CM4R"]), 1e-30)
        cmrr_4r = 20.0 * np.log10(1.0 / acm4r)
        res["cmrr_4r_dc_db"] = float(cmrr_4r[0])
        res["cmrr_4r_1mhz_db"] = at(cmrr_4r, 1e6)

    f_n = find_single(psf_dir, ["noise.noise", "*.noise"])
    dn = parse_psf_ascii(f_n)
    fn = np.real(dn["freq"])
    log_fn = np.log10(fn)
    vn_out = np.real(dn["out"])
    vn_in = np.real(dn["in"]) if "in" in dn else vn_out / np.interp(fn, freq, adm)

    vn_in_rms = math.sqrt(max(trapz(vn_in**2, fn), 0.0))
    vn_out_rms = math.sqrt(max(trapz(vn_out**2, fn), 0.0))
    bw_hz = max(float(fn[-1] - fn[0]), 1.0)
    vn_out_avg = vn_out_rms / math.sqrt(bw_hz)

    # White-noise floor from high-frequency plateau (top decade below UGF, or 100k..10M median)
    mid_mask = (fn >= 1e5) & (fn <= 1e7)
    vn_white = float(np.median(vn_in[mid_mask])) if np.any(mid_mask) else float(np.min(vn_in))
    f_corner = float("nan")
    for i in range(len(fn) - 1):
        if vn_in[i] >= math.sqrt(2.0) * vn_white > vn_in[i + 1]:
            frac = (math.sqrt(2.0) * vn_white - vn_in[i]) / (vn_in[i + 1] - vn_in[i])
            f_corner = float(10.0 ** (log_fn[i] + frac * (log_fn[i + 1] - log_fn[i])))
            break

    res["vn_in_1khz_nv_rthz"] = float(np.interp(math.log10(1e3), log_fn, vn_in) * 1e9)
    res["vn_in_100khz_nv_rthz"] = float(np.interp(math.log10(1e5), log_fn, vn_in) * 1e9)
    res["vn_in_1mhz_nv_rthz"] = float(np.interp(math.log10(1e6), log_fn, vn_in) * 1e9)
    res["vn_white_nv_rthz"] = vn_white * 1e9
    res["flicker_corner_khz"] = f_corner * 1e-3 if math.isfinite(f_corner) else float("nan")
    res["vn_out_int_uvrms"] = vn_out_rms * 1e6
    res["vn_in_int_uvrms"] = vn_in_rms * 1e6
    res["vn_out_avg_nv_rthz"] = vn_out_avg * 1e9
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

    m_r = (t >= t_rise) & (t < t_fall)
    tr_arr, vr_arr = t[m_r], vout[m_r]
    t20_r = crossings(tr_arr, vr_arr, v_lo_ss + 0.2 * dv, "rising")[0]
    t80_r = crossings(tr_arr, vr_arr, v_lo_ss + 0.8 * dv, "rising")[0]
    sr_pos = (0.6 * dv / (t80_r - t20_r)) * 1e-6
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

    m_f = t >= t_fall
    tf_arr, vf_arr = t[m_f], vout[m_f]
    t80_f = crossings(tf_arr, vf_arr, v_lo_ss + 0.8 * dv, "falling")[0]
    t20_f = crossings(tf_arr, vf_arr, v_lo_ss + 0.2 * dv, "falling")[0]
    sr_neg = (0.6 * dv / (t20_f - t80_f)) * 1e-6
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


def analyze_dc_signoff(psf_dir: Path, *, vdd: float, vcm: float) -> dict[str, object]:
    res: dict[str, object] = {}

    # 1. Operating point: systematic V_OS, I_DD, P_DC
    f_op = find_single(psf_dir, ["dc_op.dc", "*dc_op*.dc"])
    dop = parse_psf_ascii(f_op)
    vref_op = float(dop["VCM_REF"][0]) if "VCM_REF" in dop else vcm
    vos_v = float(dop["VOUT_OP"][0]) - vref_op
    idd_a = abs(float(dop["VSUP_OP:p"][0])) if "VSUP_OP:p" in dop else float("nan")
    res["vos_mv"] = vos_v * 1e3
    res["idd_ua"] = idd_a * 1e6 if math.isfinite(idd_a) else float("nan")
    res["p_dc_mw"] = idd_a * vdd * 1e3 if math.isfinite(idd_a) else float("nan")

    # 2. Temperature sweep: alpha_VOS (-40..125 C) and DC operating temp range (-55..150 C)
    f_tmp = find_single(psf_dir, ["dc_temp.dc", "*dc_temp*.dc"])
    dt = parse_psf_ascii(f_tmp)
    temp_arr = dt["temp"]
    vos_t = dt["VOUT_OP"] - (dt["VCM_REF"] if "VCM_REF" in dt else vcm)
    v_m40 = float(np.interp(-40.0, temp_arr, vos_t))
    v_125 = float(np.interp(125.0, temp_arr, vos_t))
    res["alpha_vos_uv_per_c"] = (v_125 - v_m40) / 165.0 * 1e6
    mid_t = int(np.argmin(np.abs(temp_arr - 27.0)))
    t_lo, t_hi = _contiguous_range(temp_arr, np.abs(vos_t) <= 10e-3, mid_t)
    res["temp_range_dc_c"] = [t_lo, t_hi]

    # 3. Normalized DC sweep (u_sw = 0..1): follower ICMR, 4R bridge ICMR, swing vs RL, VIDR
    f_sw = find_single(psf_dir, ["dc_sweep.dc", "*dc_sweep*.dc"])
    ds = parse_psf_ascii(f_sw)
    vin_fol = ds["VIN_FOL"]
    vout_fol = ds["VOUT_FOL"]
    mid_sw = int(np.argmin(np.abs(vin_fol - vcm)))

    # 3a. Follower tracking range: |Vout - Vin - Vos| <= 10 mV
    fol_lo, fol_hi = _contiguous_range(vin_fol, np.abs(vout_fol - vin_fol - vos_v) <= 10e-3, mid_sw)
    res["icmr_follower_v"] = [fol_lo, fol_hi]

    # 3b. 4-resistor bridge closed-loop CM range (local |dVout/dVcm| within 6 dB of mid-rail)
    vin_brg = ds["VIN_BRG"]
    vout_brg = ds["VOUT_BRG"]
    slope_brg = np.abs(np.gradient(vout_brg, vin_brg))
    slope_ref = max(float(slope_brg[mid_sw]), 1e-6)
    brg_mask = (slope_brg <= 2.0 * slope_ref) & (np.abs(vout_brg - vcm) <= 20e-3)
    brg_lo, brg_hi = _contiguous_range(vin_brg, brg_mask, mid_sw)
    res["icmr_bridge_4r_v"] = [brg_lo, brg_hi]

    # 3c. Inverting (-2) DC output swing across RL = 1M / 100k / 10k / 1k
    vin_swg = ds["VIN_SWG"]
    swing_map: dict[str, float] = {}
    for label, sig in [
        ("1M", "VOUT_S1M"),
        ("100k", "VOUT_S100K"),
        ("10k", "VOUT_S10K"),
        ("1k", "VOUT_S1K"),
    ]:
        if sig in ds:
            vout_s = ds[sig]
            g_arr = np.abs(np.gradient(vout_s, vin_swg))
            g_mid = float(g_arr[mid_sw])
            if g_mid > 0.05:
                s_mask = g_arr >= 0.9 * g_mid
                lo_i = mid_sw
                while lo_i > 0 and bool(s_mask[lo_i - 1]):
                    lo_i -= 1
                hi_i = mid_sw
                while hi_i + 1 < len(vout_s) and bool(s_mask[hi_i + 1]):
                    hi_i += 1
                swing_map[label] = float(abs(vout_s[lo_i] - vout_s[hi_i]))
            else:
                swing_map[label] = 0.0
    res["vopp_dc_v"] = swing_map.get("1M", float("nan"))
    res["vopp_vs_rload_v"] = swing_map

    # 3d. Rail-to-rail differential overdrive phase-reversal check (VIDR)
    vip_vidr = ds["VIP_VIDR"]
    vout_vidr = ds["VOUT_VIDR"]
    vout_mid = float(vout_vidr[mid_sw])
    hi_side = vout_vidr[vip_vidr > vcm + 0.05]
    lo_side = vout_vidr[vip_vidr < vcm - 0.05]
    phase_reversal = bool(
        (len(hi_side) > 0 and float(np.min(hi_side)) < vout_mid - 0.02)
        or (len(lo_side) > 0 and float(np.max(lo_side)) > vout_mid + 0.02)
    )
    res["vidr_phase_reversal"] = phase_reversal

    # 4. Operating supply voltage range (dc_vdd)
    f_vdd = find_single(psf_dir, ["dc_vdd.dc", "*dc_vdd*.dc"])
    dvdd = parse_psf_ascii(f_vdd)
    vdd_arr = dvdd["VDD_SW"]
    err_vdd = np.abs(dvdd["VOUT_VDD"] - dvdd["VIP_SW"])
    nom_i = int(np.argmin(np.abs(vdd_arr - vdd)))
    vdd_lo, vdd_hi = _contiguous_range(vdd_arr, err_vdd <= 10e-3, nom_i)
    res["vdd_range_dc_v"] = [vdd_lo, vdd_hi]

    # 5. AC-definition ICMR from sweep_icmr_ac (A_DM and CMRR within 6 dB of mid-rail)
    ac_files = sorted(psf_dir.glob("*sweep_icmr_ac*ac_icmr*.ac"))
    if not ac_files:
        ac_files = sorted(psf_dir.glob("sweep_icmr_ac-*.ac"))
    if ac_files:
        sweep_vals: list[float] | None = None
        sweep_idx_files = sorted(psf_dir.glob("*sweep_icmr_ac*.sweep"))
        if sweep_idx_files:
            try:
                ds_idx = parse_psf_ascii(sweep_idx_files[0])
                if "vcm_ac" in ds_idx and len(ds_idx["vcm_ac"]) == len(ac_files):
                    sweep_vals = [float(x) for x in ds_idx["vcm_ac"]]
            except Exception:
                pass
        vcm_pts: list[float] = []
        adm_db_pts: list[float] = []
        cmrr_db_pts: list[float] = []
        for idx, af in enumerate(ac_files):
            da = parse_psf_ascii(af)
            adm = max(float(np.abs(da["VOUT_ACM_DM"][0])), 1e-30)
            acm = max(float(np.abs(da["VOUT_ACM_CM"][0])), 1e-30)
            if sweep_vals is not None:
                vcm_pts.append(sweep_vals[idx])
            else:
                vcm_pts.append(0.05 * vdd + idx * (0.90 * vdd / max(len(ac_files) - 1, 1)))
            adm_db_pts.append(20.0 * math.log10(adm))
            cmrr_db_pts.append(20.0 * math.log10(adm / acm))
        order = np.argsort(vcm_pts)
        vc_arr = np.asarray(vcm_pts)[order]
        ad_arr = np.asarray(adm_db_pts)[order]
        cm_arr = np.asarray(cmrr_db_pts)[order]
        c_i = int(np.argmin(np.abs(vc_arr - vcm)))
        ac_mask = (ad_arr >= ad_arr[c_i] - 6.0) & (cm_arr >= cm_arr[c_i] - 6.0)
        ac_lo, ac_hi = _contiguous_range(vc_arr, ac_mask, c_i)
        res["icmr_ac_6db_v"] = [ac_lo, ac_hi]

    return res


def analyze_cl_zout_gm(psf_dir: Path, *, r_gm: float, rload: float) -> dict[str, float]:
    f_ac = find_single(psf_dir, ["ac.ac", "*.ac.ac", "*.ac"])
    da = parse_psf_ascii(f_ac)
    freq = np.real(da["freq"])
    log_f = np.log10(freq)

    # 1. Closed-loop AC: f_-3dB, f_0.1dB, peaking, group delay
    hcl = da["VOUT_CL"]
    hcl_db = 20.0 * np.log10(np.maximum(np.abs(hcl), 1e-30))
    dc_db = float(hcl_db[0])
    peaking_db = max(float(np.max(hcl_db) - dc_db), 0.0)

    def bw_cross(drop_db: float) -> float:
        tgt = dc_db - drop_db
        for i in range(len(hcl_db) - 1):
            if hcl_db[i] >= tgt > hcl_db[i + 1]:
                frac = (tgt - hcl_db[i]) / (hcl_db[i + 1] - hcl_db[i])
                return float(10.0 ** (log_f[i] + frac * (log_f[i + 1] - log_f[i])))
        return float("nan")

    f3db = bw_cross(3.0)
    f0p1db = bw_cross(0.1)

    phase_rad = np.unwrap(np.angle(hcl))
    # Low-frequency group delay: -(1 / 2*pi) * d(phase)/df evaluated in passband (<= 0.05*f3db)
    gd_arr = -np.gradient(phase_rad, freq) / (2.0 * math.pi)
    gd_mask = (freq >= 100.0) & (freq <= (0.05 * f3db if math.isfinite(f3db) else 1e5))
    gd_ns = float(np.median(gd_arr[gd_mask]) * 1e9) if np.any(gd_mask) else float(gd_arr[0] * 1e9)

    # 2. Closed-loop Z_out(f)
    zout = np.abs(da["VOUT_ZOUT"])
    zout_1k = float(np.interp(math.log10(1e3), log_f, zout))
    z_pk_i = int(np.argmax(zout))
    zout_peak = float(zout[z_pk_i])
    zout_pk_mhz = float(freq[z_pk_i] * 1e-6)

    # 3. Open-loop R_O and input impedance R_ID / C_ID at 1 kHz
    ro_ol = float(np.abs(da["VOUT_RO"][0]))
    i_in_1k = complex(
        float(np.interp(math.log10(1e3), log_f, np.real(-da["VZIN:p"]))),
        float(np.interp(math.log10(1e3), log_f, np.imag(-da["VZIN:p"]))),
    )
    rid_gohm = (1.0 / i_in_1k.real * 1e-9) if i_in_1k.real > 1e-15 else float("inf")
    cid_ff = (i_in_1k.imag / (2.0 * math.pi * 1e3)) * 1e15

    # 4. OTA AC transconductance bandwidth (short-circuit & real-load)
    gm_sc = np.abs(da["VOUT_GM_SHORT"]) / r_gm
    gm_sc_dc = float(gm_sc[0])
    gm_sc_f3db = float("nan")
    for i in range(len(gm_sc) - 1):
        if gm_sc[i] >= gm_sc_dc / math.sqrt(2.0) > gm_sc[i + 1]:
            frac = (gm_sc_dc / math.sqrt(2.0) - gm_sc[i]) / (gm_sc[i + 1] - gm_sc[i])
            gm_sc_f3db = float(10.0 ** (log_f[i] + frac * (log_f[i + 1] - log_f[i])))
            break

    gm_ld = np.abs(da["VOUT_GM_LOAD"]) / rload
    gm_ld_dc = float(gm_ld[0])
    gm_ld_f3db = float("nan")
    for i in range(len(gm_ld) - 1):
        if gm_ld[i] >= gm_ld_dc / math.sqrt(2.0) > gm_ld[i + 1]:
            frac = (gm_ld_dc / math.sqrt(2.0) - gm_ld[i]) / (gm_ld[i + 1] - gm_ld[i])
            gm_ld_f3db = float(10.0 ** (log_f[i] + frac * (log_f[i + 1] - log_f[i])))
            break

    res: dict[str, float] = {
        "cl_gain_dc_db": dc_db,
        "cl_f3db_mhz": f3db * 1e-6 if math.isfinite(f3db) else float("nan"),
        "cl_f0p1db_mhz": f0p1db * 1e-6 if math.isfinite(f0p1db) else float("nan"),
        "cl_peaking_db": peaking_db,
        "group_delay_ns": gd_ns,
        "zout_1khz_ohm": zout_1k,
        "zout_peak_ohm": zout_peak,
        "zout_peak_freq_mhz": zout_pk_mhz,
        "ro_ol_kohm": ro_ol * 1e-3,
        "rid_gohm": rid_gohm,
        "cid_ff": cid_ff,
        "gm_ac_short_us": gm_sc_dc * 1e6,
        "gm_short_f3db_mhz": gm_sc_f3db * 1e-6 if math.isfinite(gm_sc_f3db) else float("nan"),
        "gm_ac_loaded_us": gm_ld_dc * 1e6,
        "gm_loaded_f3db_mhz": gm_ld_f3db * 1e-6 if math.isfinite(gm_ld_f3db) else float("nan"),
    }

    # 5. OTA DC transconductance sweep (gm, linear VID within 10%, gm/IDD, IOPP)
    try:
        f_gm = find_single(psf_dir, ["dc_gm.dc", "*dc_gm*.dc"])
        dg = parse_psf_ascii(f_gm)
        vid = dg["vid_sw"]
        vref = dg["VCM_REF"] if "VCM_REF" in dg else float(np.median(dg["VOUT_GM_DC"]))
        iout = (dg["VOUT_GM_DC"] - vref) / r_gm
        gm_arr = np.gradient(iout, vid)
        null_i = int(np.argmin(np.abs(iout)))
        gm_abs = np.abs(gm_arr)
        gm0 = float(gm_abs[null_i])
        thr = 0.9 * gm0
        # Linearly interpolated crossing on both sides of the null for sub-step accuracy
        v_lo = float(vid[0])
        for k in range(null_i, 0, -1):
            if gm_abs[k] >= thr > gm_abs[k - 1]:
                frac = (thr - gm_abs[k]) / (gm_abs[k - 1] - gm_abs[k])
                v_lo = float(vid[k] + frac * (vid[k - 1] - vid[k]))
                break
        v_hi = float(vid[-1])
        for k in range(null_i, len(vid) - 1):
            if gm_abs[k] >= thr > gm_abs[k + 1]:
                frac = (thr - gm_abs[k]) / (gm_abs[k + 1] - gm_abs[k])
                v_hi = float(vid[k] + frac * (vid[k + 1] - vid[k]))
                break
        res["gm_dc_us"] = gm0 * 1e6
        res["vid_linear_10pct_mv"] = (v_hi - v_lo) * 1e3
        res["iopp_ua"] = float((np.max(iout) - np.min(iout)) * 1e6)
        if "VSUP_GM:p" in dg:
            idd0 = abs(float(dg["VSUP_GM:p"][null_i]))
            if idd0 > 0.0:
                res["gm_over_idd_inv_v"] = gm0 / idd0
    except Exception:
        pass
    return res


def analyze_thd_fpbw(psf_dir: Path, *, m_bin: int, f_in: float, n_fft: int = 1024) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    out: dict[str, object] = {}
    for label, sig in [("follower", "VOUT_FOL"), ("inverting", "VOUT_INV")]:
        if sig not in d:
            continue
        t_u, y_u = extract_uniform_strobe(d["time"], d[sig])
        if len(y_u) > n_fft:
            y_u = y_u[:n_fft]
        n = len(y_u)
        fs = f_in * n / m_bin
        m = coherent_fft_metrics(y_u, num_harmonics=10, fs=fs, m_bin=m_bin)
        thd_pct = 100.0 * (10.0 ** (m["thd_db"] / 20.0))
        out[label] = {
            "n_fft": int(m["n_fft"]),
            "fin_hz": m["fin_hz"],
            "vout_pp_v": 2.0 * m["amp_peak"],
            "thd_db": m["thd_db"],
            "thd_pct": thd_pct,
            "hd2_dbc": m["hd2_dbc"],
            "hd3_dbc": m["hd3_dbc"],
            "sfdr_db": m["sfdr_db"],
            "sndr_db": m["sndr_db"],
            "pass_thd_1pct": bool(thd_pct <= 1.0),
        }
    return out


def analyze_power_ramp(
    psf_dir: Path, *, vdd: float, t_ramp: float, t_hold: float
) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vdd_w = d["VDD"]
    vip = d["VIP"]
    vout = d["VOUT"]
    err = vout - vip

    t_hold_start = 0.5e-3 + t_ramp
    t_hold_end = t_hold_start + t_hold
    m_hold = (t >= t_hold_start + 0.2 * t_hold) & (t <= t_hold_end - 0.05 * t_hold)
    settled_err_mv = float(np.max(np.abs(err[m_hold])) * 1e3) if np.any(m_hold) else float("nan")

    # Check high-voltage active region (VDD >= 0.75 * vdd_nom) for any sustained oscillation
    m_act = vdd_w >= 0.75 * vdd
    max_act_dev_mv = float(np.max(np.abs(err[m_act])) * 1e3) if np.any(m_act) else float("nan")
    osc_hold = _detect_oscillation(t[m_hold], err[m_hold], thresh_v=2e-3) if np.any(m_hold) else False
    osc_ramp = _detect_oscillation(t[m_act], err[m_act], thresh_v=5e-3) if np.any(m_act) else False

    return {
        "settled_err_mv": settled_err_mv,
        "max_active_ramp_dev_mv": max_act_dev_mv,
        "oscillation_detected": bool(osc_hold or osc_ramp),
        "pass": bool(not (osc_hold or osc_ramp) and math.isfinite(settled_err_mv) and settled_err_mv <= 10.0),
    }


def analyze_supply_surge_cmstep(
    psf_dir: Path, *, vcm: float, t_cm_rise: float, t_cm_fall: float
) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vref = float(d["VCM_REF"][0]) if "VCM_REF" in d else vcm

    # 1. Supply surge disturbance
    v_sg = d["VOUT_SURGE"]
    m_pre = (t >= 0.1e-6) & (t <= 0.9e-6)
    v_sg_base = float(np.mean(v_sg[m_pre])) if np.any(m_pre) else vref
    m_sg = t >= 1.0e-6
    sg_err = v_sg[m_sg] - v_sg_base
    surge_peak_mv = float(np.max(np.abs(sg_err)) * 1e3)

    # 2. Input CM-step transient
    v_cm = d["VOUT_CMSTEP"]
    m_cm_pre = (t >= 0.2 * t_cm_rise) & (t <= 0.9 * t_cm_rise)
    v_cm_base = float(np.mean(v_cm[m_cm_pre])) if np.any(m_cm_pre) else vref
    m_cm_win = (t >= t_cm_rise) & (t < t_cm_fall)
    cm_err = v_cm[m_cm_win] - v_cm_base
    cm_peak_mv = float(np.max(np.abs(cm_err)) * 1e3)
    tw = t[m_cm_win]
    tail_m = tw >= (t_cm_rise + 0.8 * (t_cm_fall - t_cm_rise))
    cm_steady = float(np.mean(cm_err[tail_m])) if np.any(tail_m) else float(cm_err[-1])
    out_1mv = np.where(np.abs(cm_err - cm_steady) > 1e-3)[0]
    if len(out_1mv) == 0:
        cm_settle_ns = 0.0
    elif out_1mv[-1] + 1 < len(tw):
        cm_settle_ns = float((tw[out_1mv[-1] + 1] - t_cm_rise) * 1e9)
    else:
        cm_settle_ns = float("nan")

    return {
        "supply_surge_peak_mv": surge_peak_mv,
        "cm_step_peak_mv": cm_peak_mv,
        "cm_step_dc_shift_mv": cm_steady * 1e3,
        "cm_step_settle_1mv_ns": cm_settle_ns,
    }


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

    p_dc = sub.add_parser("dc_signoff")
    p_dc.add_argument("psf_dir", type=Path)
    p_dc.add_argument("--vdd", type=float, default=0.9)
    p_dc.add_argument("--vcm", type=float, default=0.45)

    p_cl = sub.add_parser("cl_zout_gm")
    p_cl.add_argument("psf_dir", type=Path)
    p_cl.add_argument("--r-gm", type=float, default=10.0)
    p_cl.add_argument("--rload", type=float, default=1e6)

    p_thd = sub.add_parser("thd_fpbw")
    p_thd.add_argument("psf_dir", type=Path)
    p_thd.add_argument("--m-bin", type=int, default=3)
    p_thd.add_argument("--f-in", type=float, default=10e3)
    p_thd.add_argument("--n-fft", type=int, default=1024)

    p_pr = sub.add_parser("power_ramp")
    p_pr.add_argument("psf_dir", type=Path)
    p_pr.add_argument("--vdd", type=float, default=0.9)
    p_pr.add_argument("--t-ramp", type=float, default=5e-3)
    p_pr.add_argument("--t-hold", type=float, default=2e-3)

    p_sg = sub.add_parser("supply_surge_cmstep")
    p_sg.add_argument("psf_dir", type=Path)
    p_sg.add_argument("--vcm", type=float, default=0.45)
    p_sg.add_argument("--t-cm-rise", type=float, default=2e-6)
    p_sg.add_argument("--t-cm-fall", type=float, default=10e-6)

    args = ap.parse_args(argv)
    if args.mode == "stb":
        res: object = analyze_stb(args.psf_dir, vdd=args.vdd, cload_pf=args.cload_pf)
    elif args.mode == "cmrr_psrr_noise":
        res = analyze_cmrr_psrr_noise(args.psf_dir)
    elif args.mode == "slew_settle":
        res = analyze_slew_settle(
            args.psf_dir, t_rise=args.t_rise, t_fall=args.t_fall, cload_pf=args.cload_pf
        )
    elif args.mode == "dc_signoff":
        res = analyze_dc_signoff(args.psf_dir, vdd=args.vdd, vcm=args.vcm)
    elif args.mode == "cl_zout_gm":
        res = analyze_cl_zout_gm(args.psf_dir, r_gm=args.r_gm, rload=args.rload)
    elif args.mode == "thd_fpbw":
        res = analyze_thd_fpbw(args.psf_dir, m_bin=args.m_bin, f_in=args.f_in, n_fft=args.n_fft)
    elif args.mode == "power_ramp":
        res = analyze_power_ramp(
            args.psf_dir, vdd=args.vdd, t_ramp=args.t_ramp, t_hold=args.t_hold
        )
    else:
        res = analyze_supply_surge_cmstep(
            args.psf_dir, vcm=args.vcm, t_cm_rise=args.t_cm_rise, t_cm_fall=args.t_cm_fall
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
