#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from Bandgap Reference testbenches.

Usage:
  python analyze_bandgap.py temp_line <psf_dir>
  python analyze_bandgap.py startup <psf_dir> [--t-delay 2e-6]
  python analyze_bandgap.py psrr_noise <psf_dir>
  python analyze_bandgap.py stb <psf_dir>
  python analyze_bandgap.py trim <psf_dir> [--target-v <V>]
  python analyze_bandgap.py brownout <psf_dir>
  python analyze_bandgap.py en_leak <psf_dir> [--max-start-leak-na 50.0]
  python analyze_bandgap.py load_step <psf_dir>
  python analyze_bandgap.py bias_currents <psf_dir> [--vdd-nom 1.2] [--vos-step-mv 3.0]
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

from psf_utils import dnl_inl_from_transfer, find_single, parse_psf_ascii, trapz


def _find_optional(psf_dir: Path, patterns: list[str]) -> Path | None:
    try:
        return find_single(psf_dir, patterns)
    except FileNotFoundError:
        return None


def _box_tc_ppm(temp: np.ndarray, sig: np.ndarray, t_ref: float = 27.0) -> tuple[float, float]:
    val_ref = float(np.interp(t_ref, temp, sig))
    t_span = float(temp[-1] - temp[0])
    if abs(val_ref) < 1e-18 or abs(t_span) < 1e-12:
        return val_ref, 0.0
    tc = (float(np.max(sig)) - float(np.min(sig))) / (abs(val_ref) * t_span) * 1e6
    return val_ref, float(tc)


def _settling_time(
    t: np.ndarray,
    y: np.ndarray,
    *,
    t_start: float,
    t_end: float,
    v_target: float,
    tol_abs: float,
) -> float:
    m = (t >= t_start) & (t <= t_end)
    tw, vw = t[m], y[m]
    if len(tw) < 2:
        return 0.0
    err = np.abs(vw - v_target)
    out = np.where(err > tol_abs)[0]
    if len(out) == 0:
        return 0.0
    idx = int(out[-1])
    if idx + 1 >= len(tw):
        return float(tw[-1] - t_start)
    e0, e1 = float(err[idx]), float(err[idx + 1])
    frac = (e0 - tol_abs) / max(e0 - e1, 1e-30)
    frac = min(max(frac, 0.0), 1.0)
    t_cross = float(tw[idx] + frac * (tw[idx + 1] - tw[idx]))
    return max(t_cross - t_start, 0.0)


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


def analyze_stb(psf_dir: Path) -> dict[str, object]:
    f = find_single(psf_dir, ["stb.stb", "*.stb.stb"])
    d = parse_psf_ascii(f)
    freq = np.real(d["freq"])
    lg_raw = d["loopGain"]
    dc_phase_raw = float(math.degrees(math.atan2(float(np.imag(lg_raw[0])), float(np.real(lg_raw[0])))))
    # Spectre `stb` outputs loopGain = T(s): negative DC feedback has Re(T(0)) < 0
    # (phase ~= +/-180 deg) when iprobe is oriented forward (LOOP_OUT -> LOOP_IN).
    neg_fb = bool(float(np.real(lg_raw[0])) < 0.0)
    lg = -lg_raw if neg_fb else lg_raw

    mag_db = 20.0 * np.log10(np.maximum(np.abs(lg), 1e-30))
    phase_deg = np.degrees(np.unwrap(np.angle(lg)))

    ugf = float("nan")
    pm_deg = float("nan")
    for i in range(len(mag_db) - 1):
        if mag_db[i] >= 0.0 > mag_db[i + 1]:
            frac = (0.0 - mag_db[i]) / (mag_db[i + 1] - mag_db[i])
            ugf = float(10.0 ** (math.log10(freq[i]) + frac * (math.log10(freq[i + 1]) - math.log10(freq[i]))))
            pm_deg = 180.0 + float(phase_deg[i] + frac * (phase_deg[i + 1] - phase_deg[i]))
            break

    gm_db = float("inf")
    for i in range(len(phase_deg) - 1):
        if phase_deg[i] >= -180.0 > phase_deg[i + 1]:
            frac = (-180.0 - phase_deg[i]) / (phase_deg[i + 1] - phase_deg[i])
            gm_db = -float(mag_db[i] + frac * (mag_db[i + 1] - mag_db[i]))
            break

    return {
        "net_negative_feedback": neg_fb,
        "dc_phase_raw_deg": dc_phase_raw,
        "dc_loop_gain_db": float(mag_db[0]),
        "ugf_hz": ugf,
        "phase_margin_deg": pm_deg,
        "gain_margin_db": gm_db,
    }


def analyze_trim(psf_dir: Path, *, target_v: float | None = None) -> dict[str, object]:
    f_nom = find_single(psf_dir, ["dc_trim_nom.dc", "*trim_nom*.dc", "*trim*.dc"])
    d_nom = parse_psf_ascii(f_nom)
    code_key = "vtrim_code" if "vtrim_code" in d_nom else (
        "VTRIM" if "VTRIM" in d_nom else next(k for k in d_nom if k not in {"VREF", "VDD", "VSUP:p"})
    )
    order = np.argsort(d_nom[code_key])
    codes = d_nom[code_key][order]
    v_nom = d_nom["VREF"][order]

    m_dnl = dnl_inl_from_transfer(v_nom)
    steps = np.diff(v_nom)
    monotonic = bool(np.all(steps > 0.0) or np.all(steps < 0.0))
    mid_idx = len(v_nom) // 2
    v_tgt = float(v_nom[mid_idx]) if target_v is None else float(target_v)

    lsb_mv = float(m_dnl["lsb_v"] * 1e3)
    res: dict[str, object] = {
        "n_codes": int(len(v_nom)),
        "vref_min_v": float(np.min(v_nom)),
        "vref_max_v": float(np.max(v_nom)),
        "vref_mid_v": float(v_nom[mid_idx]),
        "vref_target_v": v_tgt,
        "trim_span_mv": float((np.max(v_nom) - np.min(v_nom)) * 1e3),
        "lsb_step_mv": lsb_mv,
        "dnl_max_lsb": float(m_dnl["dnl_abs_max_lsb"]),
        "inl_max_lsb": float(m_dnl["inl_abs_max_lsb"]),
        "monotonic": monotonic,
    }

    corner_errs: list[float] = []
    for tag, pats in [
        ("m3s", ["dc_trim_m3s.dc", "*m3s*.dc"]),
        ("p3s", ["dc_trim_p3s.dc", "*p3s*.dc"]),
    ]:
        f_c = _find_optional(psf_dir, pats)
        if f_c is None:
            continue
        dc = parse_psf_ascii(f_c)
        ck = code_key if code_key in dc else next(k for k in dc if k not in {"VREF", "VDD", "VSUP:p"})
        ord_c = np.argsort(dc[ck])
        vc = dc["VREF"][ord_c]
        cc = dc[ck][ord_c]
        untrimmed_mv = float((vc[mid_idx] - v_tgt) * 1e3)
        best_i = int(np.argmin(np.abs(vc - v_tgt)))
        trimmed_mv = float((vc[best_i] - v_tgt) * 1e3)
        corner_errs.append(abs(trimmed_mv))
        res[f"untrimmed_{tag}_mv"] = untrimmed_mv
        res[f"best_code_{tag}"] = int(round(float(cc[best_i])))
        res[f"trimmed_err_{tag}_mv"] = trimmed_mv

    if corner_errs:
        worst_err_mv = float(max(corner_errs))
    else:
        best_nom = int(np.argmin(np.abs(v_nom - v_tgt)))
        worst_err_mv = float(abs(v_nom[best_nom] - v_tgt) * 1e3)
    res["trimmed_err_mv"] = worst_err_mv
    res["trim_centers_3sigma"] = bool(worst_err_mv <= 0.5 * lsb_mv + 1e-6)
    return res


def analyze_brownout(
    psf_dir: Path,
    *,
    t_dip_start: float = 25e-6,
    t_dip_release: float = 45e-6,
    t_glitch_start: float = 100e-6,
    v_lock_min: float = 0.25,
) -> dict[str, object]:
    f_dip = find_single(psf_dir, ["tran_dip.tran.tran", "tran_dip.tran", "*dip*.tran*"])
    d_dip = parse_psf_ascii(f_dip)
    t_d = d_dip["time"]
    v_d = d_dip["VREF"]

    pre_m = (t_d >= 15e-6) & (t_d <= t_dip_start - 1e-6)
    dip_m = (t_d >= t_dip_start) & (t_d <= t_dip_release + 15e-6)
    post_m = (t_d >= t_glitch_start - 12e-6) & (t_d <= t_glitch_start - 1e-6)
    glitch_w = (t_d >= t_glitch_start) & (t_d <= t_glitch_start + 15e-6)
    end_m = t_d >= (float(t_d[-1]) - 12e-6)

    v_pre = float(np.mean(v_d[pre_m]))
    v_dip_min = float(np.min(v_d[dip_m]))
    v_post_dip = float(np.mean(v_d[post_m]))
    v_post_glitch = float(np.mean(v_d[end_m]))

    recovered = bool(
        v_post_dip >= v_lock_min
        and (v_pre < v_lock_min or abs(v_post_dip - v_pre) <= 0.02 * max(abs(v_pre), 0.1))
    )
    if recovered:
        t_rec_s = _settling_time(
            t_d,
            v_d,
            t_start=t_dip_release,
            t_end=t_glitch_start - 1e-6,
            v_target=v_post_dip,
            tol_abs=0.01 * max(abs(v_post_dip), 1e-6),
        )
        t_rec_us: float | None = float(t_rec_s * 1e6)
        glitch_droop_mv = float(max(v_post_dip - float(np.min(v_d[glitch_w])), 0.0) * 1e3)
    else:
        t_rec_us = None
        glitch_droop_mv = 0.0

    f_slow = _find_optional(psf_dir, ["tran_slow.tran.tran", "tran_slow.tran", "*slow*.tran*"])
    slow_started = True
    v_slow_final = v_post_dip
    vdd_turnon_slow: float | None = None
    if f_slow is not None:
        d_s = parse_psf_ascii(f_slow)
        t_s = d_s["time"]
        v_s = d_s["VREF"]
        vdd_s = d_s["VDD"]
        v_slow_final = float(np.mean(v_s[t_s >= float(t_s[-1]) - 40e-6]))
        slow_started = bool(v_slow_final >= v_lock_min)
        if slow_started:
            idx_half = np.where(v_s >= 0.5 * v_slow_final)[0]
            if len(idx_half) > 0:
                vdd_turnon_slow = float(vdd_s[int(idx_half[0])])

    dead_state_free = bool(recovered and slow_started and (v_post_glitch >= v_lock_min))
    return {
        "vref_pre_dip_v": v_pre,
        "vref_dip_min_v": v_dip_min,
        "vref_post_dip_v": v_post_dip,
        "recovered_after_dip": recovered,
        "t_recover_1pct_us": t_rec_us,
        "glitch_droop_mv": glitch_droop_mv,
        "vref_post_glitch_v": v_post_glitch,
        "vref_slow_final_v": v_slow_final,
        "slow_ramp_started": slow_started,
        "vdd_turnon_slow_v": vdd_turnon_slow,
        "dead_state_free": dead_state_free,
    }


def analyze_en_leak(
    psf_dir: Path,
    *,
    t_on1: float = 10e-6,
    t_off2: float = 55e-6,
    t_on2: float = 85e-6,
    max_start_leak_na: float = 50.0,
) -> dict[str, object]:
    f = find_single(psf_dir, ["tran.tran.tran", "tran.tran", "*.tran.tran", "*.tran"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vref = d["VREF"]
    i_dd = np.abs(d["VSUP:p"])
    ist_key = "VISTART:p" if "VISTART:p" in d else next(
        k for k in d if "START" in k.upper()
    )
    i_st = np.abs(d[ist_key])

    off1_m = (t >= 4e-6) & (t <= t_on1 - 0.5e-6)
    on1_ss = (t >= t_off2 - 10e-6) & (t <= t_off2 - 1e-6)
    off2_m = (t >= t_on2 - 10e-6) & (t <= t_on2 - 1e-6)
    on2_ss = t >= (float(t[-1]) - 10e-6)

    i_shdn_init_na = float(np.median(i_dd[off1_m]) * 1e9)
    i_shdn_na = float(np.median(i_dd[off2_m]) * 1e9)
    vref_on1 = float(np.mean(vref[on1_ss]))
    vref_on2 = float(np.mean(vref[on2_ss]))
    iq_on_ua = float(np.mean(i_dd[on1_ss]) * 1e6)

    t_wake1_s = _settling_time(
        t,
        vref,
        t_start=t_on1,
        t_end=t_off2 - 1e-6,
        v_target=vref_on1,
        tol_abs=0.01 * max(abs(vref_on1), 1e-6),
    )
    t_wake2_s = _settling_time(
        t,
        vref,
        t_start=t_on2,
        t_end=float(t[-1]) - 1e-6,
        v_target=vref_on2,
        tol_abs=0.01 * max(abs(vref_on2), 1e-6),
    )

    kick_w = (t >= t_on1) & (t <= t_on1 + 20e-6)
    i_start_peak_ua = float(np.max(i_st[kick_w]) * 1e6)
    i_start_steady_na = float(0.5 * (np.mean(i_st[on1_ss]) + np.mean(i_st[on2_ss])) * 1e9)

    startup_turnoff_pass = bool(i_start_steady_na < max_start_leak_na)
    shdn_leak_pass = bool(i_shdn_na < 100.0)

    return {
        "vref_on_v": vref_on1,
        "iq_on_ua": iq_on_ua,
        "i_shdn_init_na": i_shdn_init_na,
        "i_shdn_na": i_shdn_na,
        "t_en_wakeup_1pct_us": float(t_wake1_s * 1e6),
        "t_re_enable_us": float(t_wake2_s * 1e6),
        "i_startup_peak_ua": i_start_peak_ua,
        "i_startup_steady_na": i_start_steady_na,
        "startup_turnoff_pass": startup_turnoff_pass,
        "shdn_leak_pass": shdn_leak_pass,
    }


def analyze_load_step(
    psf_dir: Path,
    *,
    t_step: float = 10e-6,
    t_pulse: float = 15e-6,
) -> dict[str, float]:
    f_dc = find_single(psf_dir, ["dc_load.dc", "*load*.dc"])
    ddc = parse_psf_ascii(f_dc)
    i_key = "iload_dc" if "iload_dc" in ddc else next(
        k for k in ddc if k not in {"VREF", "VLOAD_MON:p", "VSUP:p"}
    )
    i_dc = ddc[i_key]
    v_dc = ddc["VREF"]
    order = np.argsort(i_dc)
    i_dc, v_dc = i_dc[order], v_dc[order]

    # Positive iload_dc pulls current out of VREF -> dVREF/dI = -R_out
    slope = -float(np.polyfit(i_dc, v_dc, 1)[0])
    v_noload = float(np.interp(0.0, i_dc, v_dc))

    f_tr = find_single(psf_dir, ["tran_step.tran.tran", "tran_step.tran", "*step*.tran*", "*.tran.tran", "*.tran"])
    dtr = parse_psf_ascii(f_tr)
    t = dtr["time"]
    vref = dtr["VREF"]

    t_rel = t_step + t_pulse
    v_base = float(np.mean(vref[(t >= 0.4 * t_step) & (t <= t_step - 0.5e-6)]))
    v_loaded = float(np.mean(vref[(t >= t_rel - 4e-6) & (t <= t_rel - 0.5e-6)]))
    v_post = float(np.mean(vref[t >= (float(t[-1]) - 5e-6)]))

    m_load = (t >= t_step) & (t <= t_rel)
    m_rel = t >= t_rel
    droop_mv = float(max(v_base - float(np.min(vref[m_load])), 0.0) * 1e3)
    overshoot_mv = float(max(float(np.max(vref[m_rel])) - v_post, 0.0) * 1e3)

    tol_0p5 = 0.005 * max(abs(v_base), 1e-6)
    t_rec_load_s = _settling_time(
        t, vref, t_start=t_step, t_end=t_rel - 0.5e-6, v_target=v_loaded, tol_abs=tol_0p5
    )
    t_rec_rel_s = _settling_time(
        t, vref, t_start=t_rel, t_end=float(t[-1]) - 0.5e-6, v_target=v_post, tol_abs=tol_0p5
    )

    return {
        "vref_noload_v": v_noload,
        "vref_sink_100u_v": float(v_dc[0]),
        "vref_src_100u_v": float(v_dc[-1]),
        "r_out_dc_ohm": slope,
        "load_reg_mv_per_ma": slope,
        "step_steady_err_mv": float((v_base - v_loaded) * 1e3),
        "step_droop_mv": droop_mv,
        "step_overshoot_mv": overshoot_mv,
        "t_recover_0p5pct_us": float(t_rec_load_s * 1e6),
        "t_release_0p5pct_us": float(t_rec_rel_s * 1e6),
    }


def analyze_bias_currents(
    psf_dir: Path,
    *,
    vdd_nom: float = 1.2,
    vos_step_mv: float = 3.0,
) -> dict[str, float]:
    f_t = find_single(psf_dir, ["dc_temp.dc", "*temp_nom*.dc"])
    dt = parse_psf_ascii(f_t)
    t_key = next(k for k in dt if k not in {"VREF", "VDD", "VIPTAT:p", "VIZTC:p", "VSUP:p"})
    temp = dt[t_key]
    iptat = np.abs(dt["VIPTAT:p"])
    iztc = np.abs(dt["VIZTC:p"])
    vref = dt["VREF"]

    iptat_27 = float(np.interp(27.0, temp, iptat))
    iztc_27, iztc_tc_ppm = _box_tc_ppm(temp, iztc, 27.0)
    vref_27, vref_tc_nom = _box_tc_ppm(temp, vref, 27.0)
    t_span = float(temp[-1] - temp[0])
    # Signed PTAT linear slope across temperature sweep [ppm/C]
    iptat_tc_ppm = float((iptat[-1] - iptat[0]) / (max(iptat_27, 1e-18) * t_span) * 1e6)

    f_c = find_single(psf_dir, ["dc_comp.dc", "*comp*.dc"])
    dc = parse_psf_ascii(f_c)
    vc_key = "v_comp" if "v_comp" in dc else next(
        k for k in dc if k not in {"VREF", "VDD", "VIPTAT:p", "VIZTC:p", "VSUP:p"}
    )
    vc = dc[vc_key]
    ip_c = np.abs(dc["VIPTAT:p"])
    iz_c = np.abs(dc["VIZTC:p"])
    ord_c = np.argsort(vc)
    vc, ip_c, iz_c = vc[ord_c], ip_c[ord_c], iz_c[ord_c]

    v_ref_pt = float(min(0.6, 0.5 * vc[-1]))
    ip_ref = float(np.interp(v_ref_pt, vc, ip_c))
    iz_ref = float(np.interp(v_ref_pt, vc, iz_c))

    def _comp_min(v_arr: np.ndarray, i_arr: np.ndarray, i_ref: float) -> float:
        m = i_arr >= 0.95 * i_ref
        return float(v_arr[int(np.where(m)[0][0])]) if np.any(m) else float(v_arr[-1])

    comp_ptat = _comp_min(vc, ip_c, ip_ref)
    comp_ztc = _comp_min(vc, iz_c, iz_ref)
    comp_min = max(comp_ptat, comp_ztc)

    sat_m = (vc >= max(comp_min + 0.15, 0.45)) & (vc <= vc[-1] - 0.05)
    def _ro_mohm(v_arr: np.ndarray, i_arr: np.ndarray) -> float:
        if np.sum(sat_m) < 2:
            return 0.0
        g = float(np.polyfit(v_arr[sat_m], i_arr[sat_m], 1)[0])
        return float(1.0 / max(abs(g), 1e-15) * 1e-6)

    ro_ptat_mohm = _ro_mohm(vc, ip_c)
    ro_ztc_mohm = _ro_mohm(vc, iz_c)

    f_ac = find_single(psf_dir, ["ac_psrr.ac", "*psrr*.ac", "*.ac.ac", "*.ac"])
    dac = parse_psf_ascii(f_ac)
    freq = np.real(dac["freq"])
    log_f = np.log10(freq)
    vdd_ac = np.maximum(np.abs(dac.get("VDD", np.ones_like(freq))), 1e-30)
    # Normalized relative current PSRR: -20*log10((|I_ac|/I_dc) / (|V_dd_ac|/V_dd_nom))
    s_ptat = (np.abs(dac["VIPTAT:p"]) / max(iptat_27, 1e-18)) / (vdd_ac / vdd_nom)
    s_ztc = (np.abs(dac["VIZTC:p"]) / max(iztc_27, 1e-18)) / (vdd_ac / vdd_nom)
    psrr_ptat = -20.0 * np.log10(np.maximum(s_ptat, 1e-30))
    psrr_ztc = -20.0 * np.log10(np.maximum(s_ztc, 1e-30))
    bias_psrr_dc = float(min(psrr_ptat[0], psrr_ztc[0]))
    bias_psrr_100k = float(
        min(
            float(np.interp(math.log10(1e5), log_f, psrr_ptat)),
            float(np.interp(math.log10(1e5), log_f, psrr_ztc)),
        )
    )

    res: dict[str, float] = {
        "vref_27c_v": vref_27,
        "vref_tc_nom_ppm_per_c": vref_tc_nom,
        "iptat_27c_ua": float(iptat_27 * 1e6),
        "iptat_tc_ppm_per_c": iptat_tc_ppm,
        "iztc_27c_ua": float(iztc_27 * 1e6),
        "iztc_tc_ppm_per_c": iztc_tc_ppm,
        "iptat_compliance_min_v": comp_ptat,
        "iztc_compliance_min_v": comp_ztc,
        "compliance_min_v": comp_min,
        "ro_iptat_mohm": ro_ptat_mohm,
        "ro_iztc_mohm": ro_ztc_mohm,
        "iptat_psrr_dc_db": float(psrr_ptat[0]),
        "iztc_psrr_dc_db": float(psrr_ztc[0]),
        "bias_psrr_dc_db": bias_psrr_dc,
        "bias_psrr_100khz_db": bias_psrr_100k,
    }

    f_vp = _find_optional(psf_dir, ["dc_temp_vosp.dc", "*vosp*.dc"])
    f_vm = _find_optional(psf_dir, ["dc_temp_vosm.dc", "*vosm*.dc"])
    if f_vp is not None and f_vm is not None:
        dp = parse_psf_ascii(f_vp)
        dm = parse_psf_ascii(f_vm)
        tp = dp[t_key] if t_key in dp else dp[next(k for k in dp if k not in {"VREF", "VDD", "VIPTAT:p", "VIZTC:p", "VSUP:p"})]
        tm = dm[t_key] if t_key in dm else dm[next(k for k in dm if k not in {"VREF", "VDD", "VIPTAT:p", "VIZTC:p", "VSUP:p"})]
        vp_27, tc_vp = _box_tc_ppm(tp, dp["VREF"], 27.0)
        vm_27, tc_vm = _box_tc_ppm(tm, dm["VREF"], 27.0)
        vos_v = vos_step_mv * 1e-3
        res["vref_27c_vosp_v"] = vp_27
        res["vref_27c_vosm_v"] = vm_27
        res["vref_tc_vosp_ppm_per_c"] = tc_vp
        res["vref_tc_vosm_ppm_per_c"] = tc_vm
        res["vos_vref_gain_v_per_v"] = float(abs(vp_27 - vm_27) / max(2.0 * vos_v, 1e-12))
        res["vos_tc_sensitivity_ppm_per_mv"] = float(
            (0.5 * (tc_vp + tc_vm) - vref_tc_nom) / max(vos_step_mv, 1e-9)
        )
    else:
        res["vos_tc_sensitivity_ppm_per_mv"] = 0.0

    return res


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

    p_sb = sub.add_parser("stb")
    p_sb.add_argument("psf_dir", type=Path)

    p_tr = sub.add_parser("trim")
    p_tr.add_argument("psf_dir", type=Path)
    p_tr.add_argument("--target-v", type=float, default=None)

    p_bo = sub.add_parser("brownout")
    p_bo.add_argument("psf_dir", type=Path)

    p_en = sub.add_parser("en_leak")
    p_en.add_argument("psf_dir", type=Path)
    p_en.add_argument("--max-start-leak-na", type=float, default=50.0)

    p_ls = sub.add_parser("load_step")
    p_ls.add_argument("psf_dir", type=Path)

    p_bc = sub.add_parser("bias_currents")
    p_bc.add_argument("psf_dir", type=Path)
    p_bc.add_argument("--vdd-nom", type=float, default=1.2)
    p_bc.add_argument("--vos-step-mv", type=float, default=3.0)

    args = ap.parse_args(argv)
    if args.mode == "temp_line":
        res: object = analyze_temp_line(args.psf_dir)
    elif args.mode == "startup":
        res = analyze_startup(args.psf_dir, t_delay=args.t_delay)
    elif args.mode == "psrr_noise":
        res = analyze_psrr_noise(args.psf_dir)
    elif args.mode == "stb":
        res = analyze_stb(args.psf_dir)
    elif args.mode == "trim":
        res = analyze_trim(args.psf_dir, target_v=args.target_v)
    elif args.mode == "brownout":
        res = analyze_brownout(args.psf_dir)
    elif args.mode == "en_leak":
        res = analyze_en_leak(args.psf_dir, max_start_leak_na=args.max_start_leak_na)
    elif args.mode == "load_step":
        res = analyze_load_step(args.psf_dir)
    else:
        res = analyze_bias_currents(
            args.psf_dir, vdd_nom=args.vdd_nom, vos_step_mv=args.vos_step_mv
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
