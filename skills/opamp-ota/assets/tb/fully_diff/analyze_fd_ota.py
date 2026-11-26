#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from fully differential OTA signoff testbenches.

Usage:
  python analyze_fd_ota.py dm_cm_stb <psf_dir>
  python analyze_fd_ota.py slew_settle <psf_dir> [--t-step 100e-9] [--vocm 0.45]
  python analyze_fd_ota.py cmrr_psrr_noise <psf_dir>
  python analyze_fd_ota.py dc_signoff <psf_dir> [--vdd 0.9] [--vocm 0.45]
  python analyze_fd_ota.py cl_zout_gm <psf_dir> [--r-gm 10.0] [--rload 1e6]
  python analyze_fd_ota.py thd_fpbw <psf_dir> [--m-bin 3] [--f-in 10e3]
  python analyze_fd_ota.py power_ramp <psf_dir> [--vdd 0.9] [--t-ramp 5e-3] [--t-hold 2e-3]
  python analyze_fd_ota.py supply_surge_cmstep <psf_dir> [--vocm 0.45] [--t-cm-rise 2e-6] [--t-cm-fall 10e-6]
  python analyze_fd_ota.py sc_closed_loop <psf_dir> [--cs 1e-12] [--cf 250e-15] [--vstep-in 0.0625] [--tol 0.005]
  python analyze_fd_ota.py gain_swing <psf_dir> [--rs 250e3] [--rf 1e6] [--err 0.005]
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
    sr_diff = (0.6 * abs(dv) / abs(t80 - t20)) * 1e-6

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


def analyze_cmrr_psrr_noise(psf_dir: Path) -> dict[str, float]:
    f_ac = find_single(psf_dir, ["ac.ac", "*.ac.ac", "*.ac"])
    da = parse_psf_ascii(f_ac)
    freq = np.real(da["freq"])
    log_f = np.log10(freq)

    adm = np.maximum(np.abs(da["VOP_DM"] - da["VON_DM"]), 1e-30)
    acm_cm = np.maximum(np.abs(0.5 * (da["VOP_CM"] + da["VON_CM"])), 1e-30)
    acm_dm = np.maximum(np.abs(da["VOP_CM"] - da["VON_CM"]), 1e-30)
    app_cm = np.maximum(np.abs(0.5 * (da["VOP_PP"] + da["VON_PP"])), 1e-30)
    app_dm = np.maximum(np.abs(da["VOP_PP"] - da["VON_PP"]), 1e-30)
    apn_cm = np.maximum(np.abs(0.5 * (da["VOP_PN"] + da["VON_PN"])), 1e-30)
    apn_dm = np.maximum(np.abs(da["VOP_PN"] - da["VON_PN"]), 1e-30)

    acm_cm_db = 20.0 * np.log10(acm_cm)
    cmrr_dm_db = np.minimum(-20.0 * np.log10(acm_dm), 240.0)
    psrr_p_cm = -20.0 * np.log10(app_cm)
    psrr_p_dm = np.minimum(-20.0 * np.log10(app_dm), 240.0)
    psrr_n_cm = -20.0 * np.log10(apn_cm)
    psrr_n_dm = np.minimum(-20.0 * np.log10(apn_dm), 240.0)

    def at(arr: np.ndarray, f_hz: float) -> float:
        return float(np.interp(math.log10(f_hz), log_f, arr))

    res: dict[str, float] = {
        "adm_dc_db": float(20.0 * math.log10(adm[0])),
        "acm_to_cm_dc_db": float(acm_cm_db[0]),
        "acm_to_cm_1mhz_db": at(acm_cm_db, 1e6),
        "cmrr_cm_to_dm_dc_db": float(cmrr_dm_db[0]),
        "psrr_p_to_cm_dc_db": float(psrr_p_cm[0]),
        "psrr_p_to_cm_1mhz_db": at(psrr_p_cm, 1e6),
        "psrr_p_to_dm_dc_db": float(psrr_p_dm[0]),
        "psrr_n_to_cm_dc_db": float(psrr_n_cm[0]),
        "psrr_n_to_cm_1mhz_db": at(psrr_n_cm, 1e6),
        "psrr_n_to_dm_dc_db": float(psrr_n_dm[0]),
    }

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


def analyze_dc_signoff(psf_dir: Path, *, vdd: float, vocm: float) -> dict[str, object]:
    res: dict[str, object] = {}

    # 1. Operating point: DM offset (input-referred = 0.5*(VOP-VON) for gain -1), VOCM err, I_DD
    f_op = find_single(psf_dir, ["dc_op.dc", "*dc_op*.dc"])
    dop = parse_psf_ascii(f_op)
    vocm_ref = float(dop["VOCM"][0]) if "VOCM" in dop else vocm
    vop0 = float(dop["VOP_OP"][0])
    von0 = float(dop["VON_OP"][0])
    vos_dm_v = 0.5 * (vop0 - von0)
    vocm_err_v = 0.5 * (vop0 + von0) - vocm_ref
    idd_a = abs(float(dop["VSUP_OP:p"][0])) if "VSUP_OP:p" in dop else float("nan")
    res["vos_dm_mv"] = vos_dm_v * 1e3
    res["vocm_err_mv"] = vocm_err_v * 1e3
    res["idd_ua"] = idd_a * 1e6 if math.isfinite(idd_a) else float("nan")
    res["p_dc_mw"] = idd_a * vdd * 1e3 if math.isfinite(idd_a) else float("nan")

    # 2. Temperature sweep (-55..150 C)
    f_tmp = find_single(psf_dir, ["dc_temp.dc", "*dc_temp*.dc"])
    dt = parse_psf_ascii(f_tmp)
    temp_arr = dt["temp"]
    vos_t = 0.5 * (dt["VOP_OP"] - dt["VON_OP"])
    vocm_t = 0.5 * (dt["VOP_OP"] + dt["VON_OP"]) - (dt["VOCM"] if "VOCM" in dt else vocm)
    res["alpha_vos_dm_uv_per_c"] = (
        (float(np.interp(125.0, temp_arr, vos_t)) - float(np.interp(-40.0, temp_arr, vos_t)))
        / 165.0
        * 1e6
    )
    m_op_t = (temp_arr >= -40.0) & (temp_arr <= 125.0)
    res["vocm_drift_m40_125_mv"] = float(np.ptp(vocm_t[m_op_t]) * 1e3) if np.any(m_op_t) else float("nan")
    mid_t = int(np.argmin(np.abs(temp_arr - 27.0)))
    t_lo, t_hi = _contiguous_range(
        temp_arr, (np.abs(vos_t) <= 10e-3) & (np.abs(vocm_t) <= 10e-3), mid_t
    )
    res["temp_range_dc_c"] = [t_lo, t_hi]

    # 3. Normalized DC sweep (u_sw = 0..1)
    f_sw = find_single(psf_dir, ["dc_sweep.dc", "*dc_sweep*.dc"])
    ds = parse_psf_ascii(f_sw)
    vin_cm = ds["VIN_CM_SW"]
    vocm_cm = 0.5 * (ds["VOP_CM"] + ds["VON_CM"])
    mid_sw = int(np.argmin(np.abs(vin_cm - vocm)))
    cm_lo, cm_hi = _contiguous_range(vin_cm, np.abs(vocm_cm - vocm) <= 10e-3, mid_sw)
    res["icmr_cl_hold_v"] = [cm_lo, cm_hi]

    # Differential & single-ended output swing across RL = 1M / 100k / 10k / 1k
    vin_diff = ds["IN_SW_P"] - ds["IN_SW_N"]
    swing_diff: dict[str, float] = {}
    swing_se: dict[str, float] = {}
    for label, sp, sn in [
        ("1M", "VOP_S1M", "VON_S1M"),
        ("100k", "VOP_S100K", "VON_S100K"),
        ("10k", "VOP_S10K", "VON_S10K"),
        ("1k", "VOP_S1K", "VON_S1K"),
    ]:
        if sp in ds and sn in ds:
            vod = ds[sp] - ds[sn]
            g_arr = np.abs(np.gradient(vod, vin_diff))
            g_mid = float(g_arr[mid_sw])
            if g_mid > 0.1:
                s_mask = g_arr >= 0.9 * g_mid
                lo_i = mid_sw
                while lo_i > 0 and bool(s_mask[lo_i - 1]):
                    lo_i -= 1
                hi_i = mid_sw
                while hi_i + 1 < len(vod) and bool(s_mask[hi_i + 1]):
                    hi_i += 1
                swing_diff[label] = float(abs(vod[lo_i] - vod[hi_i]))
                swing_se[label] = float(abs(ds[sp][lo_i] - ds[sp][hi_i]))
            else:
                swing_diff[label] = 0.0
                swing_se[label] = 0.0
    res["vopp_diff_dc_v"] = swing_diff.get("1M", float("nan"))
    res["vopp_se_dc_v"] = swing_se.get("1M", float("nan"))
    res["vopp_diff_vs_rload_v"] = swing_diff

    # Rail-to-rail differential overdrive phase-reversal check (VIDR)
    vid_vr = ds["VIP_VIDR"] - ds["VIN_VIDR"]
    vod_vr = ds["VOP_VIDR"] - ds["VON_VIDR"]
    hi_s = vod_vr[vid_vr > 0.05]
    lo_s = vod_vr[vid_vr < -0.05]
    phase_rev = bool(
        (len(hi_s) > 0 and float(np.min(hi_s)) < -0.02)
        or (len(lo_s) > 0 and float(np.max(lo_s)) > 0.02)
    )
    res["vidr_phase_reversal"] = phase_rev

    # 4. Operating supply voltage sweep (dc_vdd)
    f_vdd = find_single(psf_dir, ["dc_vdd.dc", "*dc_vdd*.dc"])
    dvdd = parse_psf_ascii(f_vdd)
    vdd_arr = dvdd["VDD_SW"]
    vin_p_arr = dvdd["INP_SW"] - dvdd["INN_SW"]
    vod_vdd = dvdd["VOP_VDD"] - dvdd["VON_VDD"]
    vocm_vdd = 0.5 * (dvdd["VOP_VDD"] + dvdd["VON_VDD"])
    ok_vdd = (np.abs(vod_vdd - (-vin_p_arr)) <= 10e-3) & (np.abs(vocm_vdd - dvdd["VOCM_SW"]) <= 10e-3)
    nom_i = int(np.argmin(np.abs(vdd_arr - vdd)))
    vdd_lo, vdd_hi = _contiguous_range(vdd_arr, ok_vdd, nom_i)
    res["vdd_range_dc_v"] = [vdd_lo, vdd_hi]

    # 5. Open-loop AC-definition ICMR from sweep_icmr_ac (A_DM within 6 dB of mid-rail)
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
        for idx, af in enumerate(ac_files):
            da = parse_psf_ascii(af)
            adm = max(float(np.abs(da["VOP_ACM"][0] - da["VON_ACM"][0])), 1e-30)
            if sweep_vals is not None:
                vcm_pts.append(sweep_vals[idx])
            else:
                vcm_pts.append(0.05 * vdd + idx * (0.90 * vdd / max(len(ac_files) - 1, 1)))
            adm_db_pts.append(20.0 * math.log10(adm))
        order = np.argsort(vcm_pts)
        vc_arr = np.asarray(vcm_pts)[order]
        ad_arr = np.asarray(adm_db_pts)[order]
        c_i = int(np.argmin(np.abs(vc_arr - vocm)))
        ac_lo, ac_hi = _contiguous_range(vc_arr, ad_arr >= ad_arr[c_i] - 6.0, c_i)
        res["icmr_ac_6db_v"] = [ac_lo, ac_hi]

    return res


def analyze_cl_zout_gm(psf_dir: Path, *, r_gm: float, rload: float) -> dict[str, float]:
    f_ac = find_single(psf_dir, ["ac.ac", "*.ac.ac", "*.ac"])
    da = parse_psf_ascii(f_ac)
    freq = np.real(da["freq"])
    log_f = np.log10(freq)

    # 1. Closed-loop inverting (-1) AC & group delay (negate so DC phase starts at 0 deg)
    hcl = -(da["VOP_CL"] - da["VON_CL"])
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
    gd_arr = -np.gradient(phase_rad, freq) / (2.0 * math.pi)
    gd_mask = (freq >= 100.0) & (freq <= (0.05 * f3db if math.isfinite(f3db) else 1e5))
    gd_ns = float(np.median(gd_arr[gd_mask]) * 1e9) if np.any(gd_mask) else float(gd_arr[0] * 1e9)

    # 2. Closed-loop DM (per-output) and CM (CMFB) output impedance
    z_dm = np.abs(da["VOP_ZD"] - da["VON_ZD"])
    z_dm_1k = float(np.interp(math.log10(1e3), log_f, z_dm))
    z_dm_pk_i = int(np.argmax(z_dm))

    z_cm = np.abs(0.5 * (da["VOP_ZC"] + da["VON_ZC"]))
    z_cm_1k = float(np.interp(math.log10(1e3), log_f, z_cm))
    z_cm_pk_i = int(np.argmax(z_cm))

    # 3. Open-loop per-output R_O and differential input impedance R_ID / C_ID
    ro_ol = float(np.abs(da["VOP_RO"][0] - da["VON_RO"][0]))
    i_in_1k = complex(
        float(np.interp(math.log10(1e3), log_f, np.real(-da["VZIN_P:p"]))),
        float(np.interp(math.log10(1e3), log_f, np.imag(-da["VZIN_P:p"]))),
    )
    rid_gohm = (1.0 / i_in_1k.real * 1e-9) if i_in_1k.real > 1e-15 else float("inf")
    cid_ff = (i_in_1k.imag / (2.0 * math.pi * 1e3)) * 1e15

    # 4. FD OTA AC transconductance bandwidth (short-circuit & real-load)
    gm_sc = np.abs(da["VOP_GM_SHORT"] - da["VON_GM_SHORT"]) / (2.0 * r_gm)
    gm_sc_dc = float(gm_sc[0])
    gm_sc_f3db = float("nan")
    for i in range(len(gm_sc) - 1):
        if gm_sc[i] >= gm_sc_dc / math.sqrt(2.0) > gm_sc[i + 1]:
            frac = (gm_sc_dc / math.sqrt(2.0) - gm_sc[i]) / (gm_sc[i + 1] - gm_sc[i])
            gm_sc_f3db = float(10.0 ** (log_f[i] + frac * (log_f[i + 1] - log_f[i])))
            break

    gm_ld = np.abs(da["VOP_GM_LOAD"] - da["VON_GM_LOAD"]) / (2.0 * rload)
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
        "zout_dm_1khz_ohm": z_dm_1k,
        "zout_dm_peak_ohm": float(z_dm[z_dm_pk_i]),
        "zout_dm_peak_freq_mhz": float(freq[z_dm_pk_i] * 1e-6),
        "zout_cm_1khz_ohm": z_cm_1k,
        "zout_cm_peak_ohm": float(z_cm[z_cm_pk_i]),
        "zout_cm_peak_freq_mhz": float(freq[z_cm_pk_i] * 1e-6),
        "ro_ol_kohm": ro_ol * 1e-3,
        "rid_gohm": rid_gohm,
        "cid_ff": cid_ff,
        "gm_ac_short_us": gm_sc_dc * 1e6,
        "gm_short_f3db_mhz": gm_sc_f3db * 1e-6 if math.isfinite(gm_sc_f3db) else float("nan"),
        "gm_ac_loaded_us": gm_ld_dc * 1e6,
        "gm_loaded_f3db_mhz": gm_ld_f3db * 1e-6 if math.isfinite(gm_ld_f3db) else float("nan"),
    }

    # 5. FD OTA DC transconductance sweep
    try:
        f_gm = find_single(psf_dir, ["dc_gm.dc", "*dc_gm*.dc"])
        dg = parse_psf_ascii(f_gm)
        vid = dg["vid_sw"]
        iout = (dg["VOP_GM_DC"] - dg["VON_GM_DC"]) / (2.0 * r_gm)
        gm_arr = np.gradient(iout, vid)
        null_i = int(np.argmin(np.abs(iout)))
        gm_abs = np.abs(gm_arr)
        gm0 = float(gm_abs[null_i])
        thr = 0.9 * gm0
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
    t_u, vod_u = extract_uniform_strobe(d["time"], d["VOP"] - d["VON"])
    if len(vod_u) > n_fft:
        vod_u = vod_u[:n_fft]
    n = len(vod_u)
    fs = f_in * n / m_bin
    m = coherent_fft_metrics(vod_u, num_harmonics=10, fs=fs, m_bin=m_bin)
    thd_pct = 100.0 * (10.0 ** (m["thd_db"] / 20.0))
    return {
        "n_fft": int(m["n_fft"]),
        "fin_hz": m["fin_hz"],
        "v_od_pp_v": 2.0 * m["amp_peak"],
        "thd_db": m["thd_db"],
        "thd_pct": thd_pct,
        "hd2_dbc": m["hd2_dbc"],
        "hd3_dbc": m["hd3_dbc"],
        "sfdr_db": m["sfdr_db"],
        "sndr_db": m["sndr_db"],
        "pass_thd_1pct": bool(thd_pct <= 1.0),
    }


def analyze_power_ramp(
    psf_dir: Path, *, vdd: float, t_ramp: float, t_hold: float
) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vdd_w = d["VDD"]
    vocm_ref = d["VOCM"]
    vdiff = d["VOP"] - d["VON"]
    vocm_err = 0.5 * (d["VOP"] + d["VON"]) - vocm_ref

    t_hold_start = 0.5e-3 + t_ramp
    t_hold_end = t_hold_start + t_hold
    m_hold = (t >= t_hold_start + 0.2 * t_hold) & (t <= t_hold_end - 0.05 * t_hold)
    m_act = vdd_w >= 0.75 * vdd

    settled_vocm_mv = float(np.max(np.abs(vocm_err[m_hold])) * 1e3) if np.any(m_hold) else float("nan")
    settled_vdiff_mv = float(np.max(np.abs(vdiff[m_hold])) * 1e3) if np.any(m_hold) else float("nan")
    osc = bool(
        (np.any(m_hold) and (_detect_oscillation(t[m_hold], vocm_err[m_hold], 2e-3) or _detect_oscillation(t[m_hold], vdiff[m_hold], 2e-3)))
        or (np.any(m_act) and (_detect_oscillation(t[m_act], vocm_err[m_act], 5e-3) or _detect_oscillation(t[m_act], vdiff[m_act], 5e-3)))
    )
    return {
        "settled_vocm_err_mv": settled_vocm_mv,
        "settled_vdiff_err_mv": settled_vdiff_mv,
        "oscillation_detected": osc,
        "pass": bool(
            not osc
            and math.isfinite(settled_vocm_mv)
            and settled_vocm_mv <= 10.0
            and settled_vdiff_mv <= 10.0
        ),
    }


def analyze_supply_surge_cmstep(
    psf_dir: Path, *, vocm: float, t_cm_rise: float, t_cm_fall: float
) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vref = float(d["VOCM"][0]) if "VOCM" in d else vocm

    # 1. Supply surge
    vocm_sg = 0.5 * (d["VOP_SG"] + d["VON_SG"])
    vdiff_sg = d["VOP_SG"] - d["VON_SG"]
    m_pre = (t >= 0.1e-6) & (t <= 0.9e-6)
    base_cm = float(np.mean(vocm_sg[m_pre])) if np.any(m_pre) else vref
    base_dm = float(np.mean(vdiff_sg[m_pre])) if np.any(m_pre) else 0.0
    m_sg = t >= 1.0e-6
    surge_vocm_mv = float(np.max(np.abs(vocm_sg[m_sg] - base_cm)) * 1e3)
    surge_vdiff_mv = float(np.max(np.abs(vdiff_sg[m_sg] - base_dm)) * 1e3)

    # 2. Input CM step transient
    vocm_cm = 0.5 * (d["VOP_CM"] + d["VON_CM"])
    vdiff_cm = d["VOP_CM"] - d["VON_CM"]
    m_cm_pre = (t >= 0.2 * t_cm_rise) & (t <= 0.9 * t_cm_rise)
    base_cm2 = float(np.mean(vocm_cm[m_cm_pre])) if np.any(m_cm_pre) else vref
    base_dm2 = float(np.mean(vdiff_cm[m_cm_pre])) if np.any(m_cm_pre) else 0.0
    m_win = (t >= t_cm_rise) & (t < t_cm_fall)
    cm_err = vocm_cm[m_win] - base_cm2
    dm_err = vdiff_cm[m_win] - base_dm2
    tw = t[m_win]
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
        "surge_vocm_peak_mv": surge_vocm_mv,
        "surge_vdiff_peak_mv": surge_vdiff_mv,
        "cm_step_vocm_peak_mv": float(np.max(np.abs(cm_err)) * 1e3),
        "cm_step_vocm_dc_shift_mv": cm_steady * 1e3,
        "cm_step_vdiff_peak_mv": float(np.max(np.abs(dm_err)) * 1e3),
        "cm_step_vocm_settle_1mv_ns": cm_settle_ns,
    }


def _noise_contributions(path: Path, prefix: str) -> dict[str, float]:
    """Integrate per-device output noise power from a psfascii `noise` file.

    Spectre writes one struct per noisy instance; its last field is the total
    noise power spectral density [V^2/Hz] of that instance at each frequency.
    """
    text = Path(path).read_text(encoding="utf-8", errors="replace").split("\nVALUE\n", 1)[-1]
    freq = np.array([float(x) for x in re.findall(r'^"freq" ([-+0-9.eE]+)', text, re.M)])
    per: dict[str, list[float]] = {}
    for m in re.finditer(r'^"(' + re.escape(prefix) + r'[^"]+)" \(\n(.*?)\n\)', text, re.S | re.M):
        per.setdefault(m.group(1), []).append(float(m.group(2).split("\n")[-1]))
    out: dict[str, float] = {}
    for inst, vals in per.items():
        if len(vals) >= len(freq) > 1:
            out[inst[len(prefix):]] = trapz(np.asarray(vals[: len(freq)]), freq)
    return out


def analyze_sc_closed_loop(
    psf_dir: Path,
    *,
    cs: float,
    cf: float,
    vstep_in: float,
    t1: float,
    t2: float,
    t3: float,
    t_eval: float,
    tol: float,
    noise_prefix: str,
) -> dict[str, object]:
    dm = _extract_stb_file(find_single(psf_dir, ["stb_dm.stb", "*dm*.stb"]))
    cm = _extract_stb_file(find_single(psf_dir, ["stb_cm.stb", "*cm*.stb"]))

    d = parse_psf_ascii(find_single(psf_dir, ["tran.tran*", "*.tran"]))
    t = d["time"]
    vo = d["VOP_B"] - d["VON_B"]
    vcm = 0.5 * (d["VOP_B"] + d["VON_B"])
    vstep_out = 2.0 * vstep_in * cs / cf  # each edge swings the output by twice the step

    def edge(ta: float, tb: float) -> dict[str, float]:
        m = (t >= ta) & (t <= tb)
        tw, vw = t[m], vo[m]
        v_fin = float(np.interp(tb - 0.01 * (tb - ta), t, vo))  # actual final value of this edge
        out = np.where(np.abs(vw - v_fin) > tol * vstep_out)[0]
        if len(out) == 0:
            ts = 0.0
        elif out[-1] + 1 < len(tw):
            ts = float(tw[out[-1] + 1] - ta)
        else:
            ts = float("nan")
        dyn = abs(float(np.interp(ta + t_eval, t, vo)) - v_fin) / vstep_out * 100.0
        return {"t_settle_ns": ts * 1e9, "dynamic_err_pct_at_t_eval": dyn, "final_vod_v": v_fin}

    second = edge(t2, t3)
    first = edge(t1, t2)
    static_err = 100.0 / (1.0 + 10.0 ** (dm["t0_db"] / 20.0))
    m_on = t >= t1
    vocm_ref = float(np.interp(t1, t, vcm))

    res: dict[str, object] = {
        "differential_mode_loop": dm,
        "common_mode_loop": cm,
        "ideal_gain": -cs / cf,
        "vstep_out_v": vstep_out,
        "settling_tol_pct": tol * 100.0,
        "edge_at_t1": first,
        "edge_at_t2": second,
        "static_gain_err_pct": static_err,
        "total_err_bound_pct_at_t_eval": static_err
        + max(first["dynamic_err_pct_at_t_eval"], second["dynamic_err_pct_at_t_eval"]),
        "vocm_max_disturbance_mv": float(np.max(np.abs(vcm[m_on] - vocm_ref)) * 1e3),
    }

    n = parse_psf_ascii(find_single(psf_dir, ["noise.noise", "*.noise"]))
    fn = np.real(n["freq"])
    s_out = np.abs(n["out"])
    p_tot = trapz(s_out**2, fn)
    res["noise_out_rms_uv"] = math.sqrt(p_tot) * 1e6
    res["noise_in_rms_uv"] = math.sqrt(p_tot) * 1e6 * cf / cs
    contrib = _noise_contributions(find_single(psf_dir, ["noise.noise", "*.noise"]), noise_prefix)
    if contrib:
        tot = sum(contrib.values())
        top = sorted(contrib.items(), key=lambda kv: -kv[1])[:12]
        res["noise_contributors_pct"] = {k: v / tot * 100.0 for k, v in top}
    return res


def analyze_gain_swing(psf_dir: Path, *, rs: float, rf: float, err: float) -> dict[str, float]:
    d = parse_psf_ascii(find_single(psf_dir, ["dc_vid.dc", "*vid*.dc"]))
    vod = d["VOP"] - d["VON"]
    vsum = d["VIP"] - d["VIN"]
    a = np.abs(np.gradient(vod) / np.where(np.abs(np.gradient(vsum)) > 0, np.gradient(vsum), np.nan))
    beta = rs / (rs + rf)
    a_req = (1.0 - err) / (err * beta)

    def span(mask: np.ndarray) -> tuple[float, float]:
        if not np.any(mask):
            return float("nan"), float("nan")
        return float(np.min(vod[mask])), float(np.max(vod[mask]))

    lo, hi = span(a >= a_req)
    lo6, hi6 = span(a >= np.nanmax(a) / 2.0)
    return {
        "beta": beta,
        "a_peak_db": float(20.0 * np.log10(np.nanmax(a))),
        "a_required_db": float(20.0 * np.log10(a_req)),
        "vod_min_v": lo,
        "vod_max_v": hi,
        "swing_diff_vpp": hi - lo,
        "vod_min_6db_v": lo6,
        "vod_max_6db_v": hi6,
        "swing_diff_6db_vpp": hi6 - lo6,
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

    p_cpn = sub.add_parser("cmrr_psrr_noise")
    p_cpn.add_argument("psf_dir", type=Path)

    p_dc = sub.add_parser("dc_signoff")
    p_dc.add_argument("psf_dir", type=Path)
    p_dc.add_argument("--vdd", type=float, default=0.9)
    p_dc.add_argument("--vocm", type=float, default=0.45)

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
    p_sg.add_argument("--vocm", type=float, default=0.45)
    p_sg.add_argument("--t-cm-rise", type=float, default=2e-6)
    p_sg.add_argument("--t-cm-fall", type=float, default=10e-6)

    p_sc = sub.add_parser("sc_closed_loop")
    p_sc.add_argument("psf_dir", type=Path)
    p_sc.add_argument("--cs", type=float, default=1e-12)
    p_sc.add_argument("--cf", type=float, default=250e-15)
    p_sc.add_argument("--vstep-in", type=float, default=0.0625)
    p_sc.add_argument("--t1", type=float, default=30e-9)
    p_sc.add_argument("--t2", type=float, default=70e-9)
    p_sc.add_argument("--t3", type=float, default=110e-9)
    p_sc.add_argument("--t-eval", type=float, default=10e-9, help="time after each edge for the dynamic error")
    p_sc.add_argument("--tol", type=float, default=0.005, help="settling band as a fraction of the output step")
    p_sc.add_argument("--noise-prefix", default="I_C.")

    p_gs = sub.add_parser("gain_swing")
    p_gs.add_argument("psf_dir", type=Path)
    p_gs.add_argument("--rs", type=float, default=250e3)
    p_gs.add_argument("--rf", type=float, default=1e6)
    p_gs.add_argument("--err", type=float, default=0.005, help="allowed closed-loop gain error")

    args = ap.parse_args(argv)
    if args.mode == "dm_cm_stb":
        res: object = analyze_dm_cm_stb(args.psf_dir)
    elif args.mode == "slew_settle":
        res = analyze_slew_settle(args.psf_dir, t_step=args.t_step, vocm=args.vocm)
    elif args.mode == "cmrr_psrr_noise":
        res = analyze_cmrr_psrr_noise(args.psf_dir)
    elif args.mode == "dc_signoff":
        res = analyze_dc_signoff(args.psf_dir, vdd=args.vdd, vocm=args.vocm)
    elif args.mode == "cl_zout_gm":
        res = analyze_cl_zout_gm(args.psf_dir, r_gm=args.r_gm, rload=args.rload)
    elif args.mode == "thd_fpbw":
        res = analyze_thd_fpbw(args.psf_dir, m_bin=args.m_bin, f_in=args.f_in, n_fft=args.n_fft)
    elif args.mode == "power_ramp":
        res = analyze_power_ramp(
            args.psf_dir, vdd=args.vdd, t_ramp=args.t_ramp, t_hold=args.t_hold
        )
    elif args.mode == "sc_closed_loop":
        res = analyze_sc_closed_loop(
            args.psf_dir, cs=args.cs, cf=args.cf, vstep_in=args.vstep_in,
            t1=args.t1, t2=args.t2, t3=args.t3, t_eval=args.t_eval,
            tol=args.tol, noise_prefix=args.noise_prefix,
        )
    elif args.mode == "gain_swing":
        res = analyze_gain_swing(args.psf_dir, rs=args.rs, rf=args.rf, err=args.err)
    else:
        res = analyze_supply_surge_cmstep(
            args.psf_dir, vocm=args.vocm, t_cm_rise=args.t_cm_rise, t_cm_fall=args.t_cm_fall
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
