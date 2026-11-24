#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from the standalone LDO testbench suite.

Usage:
  python analyze_ldo.py dc_reg <psf_dir> [--vref 0.9]
  python analyze_ldo.py stb <psf_dir>
  python analyze_ldo.py psrr_zout_noise <psf_dir>
  python analyze_ldo.py tran <psf_dir> [--t-ld1 1e-6] [--t-ld2 3e-6] [--t-ln1 5e-6]
  python analyze_ldo.py startup <psf_dir> [--t-en-on 10e-6] [--t-en-off 250e-6]
  python analyze_ldo.py ocp <psf_dir> [--t-sh1 20e-6] [--t-sh2 50e-6]
  python analyze_ldo.py esr_grid <psf_dir>
  python analyze_ldo.py dropout_tran <psf_dir> [--t-dip1 20e-6] [--t-dip2 60e-6] [--f-rip 50e3]
  python analyze_ldo.py temp_shdn <psf_dir>
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


def _stb_metrics_from_file(psf_file: Path) -> dict[str, float]:
    d = parse_psf_ascii(psf_file)
    freq = np.real(d["freq"])
    lg = d["loopGain"]
    if np.real(lg[0]) < 0:
        lg = -lg
    mag_db = 20.0 * np.log10(np.maximum(np.abs(lg), 1e-30))
    phase_deg = np.degrees(np.unwrap(np.angle(lg)))

    ugf = float("nan")
    pm_deg = float("nan")
    for i in range(len(mag_db) - 1):
        if mag_db[i] >= 0.0 > mag_db[i + 1]:
            frac = (0.0 - mag_db[i]) / (mag_db[i + 1] - mag_db[i])
            ugf = float(
                10.0 ** (math.log10(freq[i]) + frac * (math.log10(freq[i + 1]) - math.log10(freq[i])))
            )
            pm_deg = 180.0 + float(phase_deg[i] + frac * (phase_deg[i + 1] - phase_deg[i]))
            break

    gm_db = float("inf")
    for i in range(len(phase_deg) - 1):
        if phase_deg[i] >= -180.0 > phase_deg[i + 1]:
            frac = (-180.0 - phase_deg[i]) / (phase_deg[i + 1] - phase_deg[i])
            gm_db = -float(mag_db[i] + frac * (mag_db[i + 1] - mag_db[i]))
            break

    return {
        "T0_db": float(mag_db[0]),
        "ugf_mhz": ugf * 1e-6 if math.isfinite(ugf) else float("nan"),
        "pm_deg": pm_deg,
        "gm_db": gm_db,
    }


def _settling_time(
    t: np.ndarray, y: np.ndarray, t0: float, t1: float, y_ref: float, tol_frac: float = 0.01
) -> float:
    """Return time after `t0` when `y` enters and stays within `tol_frac * |y_ref|` until `t1`."""
    tol = tol_frac * abs(y_ref)
    mask = (t >= t0) & (t <= t1)
    tw, yw = t[mask], y[mask]
    if len(tw) < 2:
        return 0.0
    outside = np.where(np.abs(yw - y_ref) > tol)[0]
    if len(outside) == 0:
        return 0.0
    last_out = int(outside[-1])
    if last_out + 1 >= len(tw):
        return float(tw[-1] - t0)
    return float(tw[last_out + 1] - t0)


def analyze_dc_reg(psf_dir: Path, *, vref: float) -> dict[str, float]:
    f_line = find_single(psf_dir, ["dc_line.dc", "*line*.dc"])
    dl = parse_psf_ascii(f_line)
    vdd = dl["VDD"] if "VDD" in dl else dl[next(iter(dl))]
    vout_l = dl["VOUT"]
    v_nom = float(vout_l[-1])

    # Dropout voltage = VDD - VOUT where VOUT falls 2% below nominal
    in_reg = vout_l >= 0.98 * v_nom
    idx_do = int(np.where(in_reg)[0][0]) if np.any(in_reg) else 0
    v_dropout = float(vdd[idx_do] - vout_l[idx_do])

    # Line regulation over well-regulated upper region [VDD >= v_nom + 0.3 V]
    reg_mask = vdd >= (v_nom + 0.3)
    if np.sum(reg_mask) >= 2:
        line_reg_mv_per_v = float(
            (vout_l[reg_mask][-1] - vout_l[reg_mask][0]) / (vdd[reg_mask][-1] - vdd[reg_mask][0]) * 1e3
        )
    else:
        line_reg_mv_per_v = float("nan")

    f_load = find_single(psf_dir, ["dc_load.dc", "*load*.dc"])
    di = parse_psf_ascii(f_load)
    sweep_key = next(k for k in di if k not in {"VOUT", "VDD", "VSUP:p"})
    iload = di[sweep_key]
    vout_i = di["VOUT"]
    load_reg_mv_per_ma = float(abs(vout_i[0] - vout_i[-1]) / ((iload[-1] - iload[0]) * 1e3) * 1e3)

    res: dict[str, float] = {
        "vout_nom_v": v_nom,
        "vout_err_pct": (v_nom - vref) / vref * 100.0,
        "dropout_mv": v_dropout * 1e3,
        "line_reg_mv_per_v": line_reg_mv_per_v,
        "load_reg_mv_per_ma": load_reg_mv_per_ma,
    }
    if "VSUP:p" in di:
        i_sup = np.abs(di["VSUP:p"])
        iq_ua = float(np.median(i_sup - iload) * 1e6)
        res["iq_ua"] = iq_ua
        res["current_eff_max_pct"] = float(iload[-1] / i_sup[-1] * 100.0)
    return res


def analyze_stb(psf_dir: Path) -> dict[str, float]:
    f = find_single(psf_dir, ["stb.stb", "*.stb.stb"])
    m = _stb_metrics_from_file(f)
    return {
        "dc_loop_gain_db": m["T0_db"],
        "ugf_mhz": m["ugf_mhz"],
        "phase_margin_deg": m["pm_deg"],
        "gain_margin_db": m["gm_db"],
    }


def analyze_psrr_zout_noise(psf_dir: Path) -> dict[str, float]:
    f_ac = find_single(psf_dir, ["ac.ac", "*.ac.ac", "*.ac"])
    dac = parse_psf_ascii(f_ac)
    freq = np.real(dac["freq"])
    log_f = np.log10(freq)

    h_psrr = np.abs(dac["VOUT"]) / np.maximum(np.abs(dac.get("VDD", np.ones_like(dac["VOUT"]))), 1e-30)
    psrr_db = -20.0 * np.log10(np.maximum(h_psrr, 1e-30))
    zout = np.abs(dac["VOUT_Z"])

    def at(arr: np.ndarray, f_hz: float) -> float:
        return float(np.interp(math.log10(f_hz), log_f, arr))

    f_n = find_single(psf_dir, ["noise.noise", "*.noise"])
    dn = parse_psf_ascii(f_n)
    fn = np.real(dn["freq"])
    vn = np.real(dn["out"])
    vrms = math.sqrt(max(trapz(vn**2, fn), 0.0))

    return {
        "psrr_dc_db": float(psrr_db[0]),
        "psrr_100khz_db": at(psrr_db, 1e5),
        "psrr_1mhz_db": at(psrr_db, 1e6),
        "psrr_100mhz_db": at(psrr_db, 1e8),
        "psrr_min_db": float(np.min(psrr_db)),
        "zout_dc_ohm": float(zout[0]),
        "zout_1mhz_ohm": at(zout, 1e6),
        "zout_peak_ohm": float(np.max(zout)),
        "output_noise_uvrms": vrms * 1e6,
    }


def analyze_tran(psf_dir: Path, *, t_ld1: float, t_ld2: float, t_ln1: float) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vout = d["VOUT"]

    v_nom = float(np.mean(vout[(t > 0.2 * t_ld1) & (t < 0.95 * t_ld1)]))
    m_ld1 = (t >= t_ld1) & (t < t_ld2)
    m_ld2 = (t >= t_ld2) & (t < t_ln1)
    m_ln1 = t >= t_ln1

    undershoot = (v_nom - float(np.min(vout[m_ld1]))) * 1e3
    overshoot = (float(np.max(vout[m_ld2])) - v_nom) * 1e3
    v_pre_ln = float(np.mean(vout[(t > t_ln1 - 0.5e-6) & (t < t_ln1)]))
    line_glitch = float(np.max(np.abs(vout[m_ln1] - v_pre_ln)) * 1e3)

    return {
        "vout_nom_v": v_nom,
        "load_undershoot_mv": undershoot,
        "load_overshoot_mv": overshoot,
        "line_step_glitch_mv": line_glitch,
    }


def analyze_startup(psf_dir: Path, *, t_en_on: float, t_en_off: float) -> dict[str, object]:
    f = find_single(psf_dir, ["tran.tran*", "*.tran"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vout = d["VOUT"]
    en = d.get("EN")

    t_on = t_en_on
    t_off = t_en_off
    if en is not None and float(np.max(en)) > 0.2:
        v_mid = 0.5 * float(np.max(en))
        r_cross = crossings(t, en, v_mid, direction="rising")
        f_cross = crossings(t, en, v_mid, direction="falling")
        if r_cross:
            t_on = r_cross[0]
        if f_cross:
            post_f = [tc for tc in f_cross if tc > t_on]
            if post_f:
                t_off = post_f[0]

    # Settled plateau in last 20% of ON window
    span_on = t_off - t_on
    m_plat = (t >= t_on + 0.80 * span_on) & (t <= t_off - 0.02 * span_on)
    v_final = float(np.median(vout[m_plat]))

    m_on = (t >= t_on) & (t < t_off)
    t_on_w, v_on_w = t[m_on], vout[m_on]

    c10 = crossings(t_on_w, v_on_w, 0.10 * v_final, direction="rising")
    c90 = crossings(t_on_w, v_on_w, 0.90 * v_final, direction="rising")
    t_start_90 = (c90[0] - t_on) if c90 else float("nan")
    t_settle_1 = _settling_time(t, vout, t_on, t_off - 0.02 * span_on, v_final, tol_frac=0.01)

    v_peak = float(np.max(v_on_w))
    overshoot_mv = max(0.0, (v_peak - v_final) * 1e3)
    overshoot_pct = overshoot_mv / max(abs(v_final) * 1e3, 1e-9) * 100.0

    # Monotonicity check across 10% -> 90% rise window (tolerance 2 mV)
    if c10 and c90 and c90[0] > c10[0]:
        m_rise = (t_on_w >= c10[0]) & (t_on_w <= c90[0])
        v_rise = v_on_w[m_rise]
        v_runmax = np.maximum.accumulate(v_rise)
        max_dip_mv = float(np.max(v_runmax - v_rise) * 1e3) if len(v_rise) > 0 else 0.0
    else:
        max_dip_mv = 0.0
    monotonic = bool(max_dip_mv < 2.0)

    i_sup = np.abs(d["VSUP:p"]) if "VSUP:p" in d else np.zeros_like(t)
    i_inrush_peak_ma = float(np.max(i_sup[m_on]) * 1e3)

    # Active output discharge after EN falling edge
    m_off = t >= t_off
    c_dis = crossings(t[m_off], vout[m_off], 0.10 * v_final, direction="falling")
    t_disch_10 = (c_dis[0] - t_off) if c_dis else float("nan")

    return {
        "vout_final_v": v_final,
        "t_start_90pct_us": t_start_90 * 1e6,
        "t_settle_1pct_us": t_settle_1 * 1e6,
        "overshoot_mv": overshoot_mv,
        "overshoot_pct": overshoot_pct,
        "monotonic_startup": monotonic,
        "max_startup_dip_mv": max_dip_mv,
        "i_inrush_peak_ma": i_inrush_peak_ma,
        "t_discharge_10pct_us": t_disch_10 * 1e6,
    }


def analyze_ocp(psf_dir: Path, *, t_sh1: float, t_sh2: float) -> dict[str, object]:
    f_dc = find_single(psf_dir, ["dc_iv.dc", "*dc_iv*.dc", "*.dc"])
    ddc = parse_psf_ascii(f_dc)
    vout_dc = ddc["VOUT"]
    iout_dc = np.abs(ddc["VMEAS:p"]) if "VMEAS:p" in ddc else np.abs(ddc["VSUP:p"])

    idx_pk = int(np.argmax(iout_dc))
    i_lim_peak_ma = float(iout_dc[idx_pk] * 1e3)
    vout_knee_v = float(vout_dc[idx_pk])

    idx_sc = int(np.argmin(vout_dc))
    i_short_ma = float(iout_dc[idx_sc] * 1e3)
    vout_short_dc_mv = float(vout_dc[idx_sc] * 1e3)
    foldback_ratio = i_short_ma / max(i_lim_peak_ma, 1e-12)

    f_tr = find_single(psf_dir, ["tran_short.tran*", "*short*.tran", "*.tran"])
    dtr = parse_psf_ascii(f_tr)
    t = dtr["time"]
    vout = dtr["VOUT"]

    t_on = t_sh1
    t_rel = t_sh2
    sh_en = dtr.get("SHORT_EN")
    if sh_en is not None and float(np.max(sh_en)) > 0.5:
        rc = crossings(t, sh_en, 0.5, direction="rising")
        fc = crossings(t, sh_en, 0.5, direction="falling")
        if rc:
            t_on = rc[0]
        if fc:
            post_f = [tc for tc in fc if tc > t_on]
            if post_f:
                t_rel = post_f[0]

    v_nom = float(np.median(vout[(t > 0.2 * t_on) & (t < 0.95 * t_on)]))
    m_sh = (t >= t_on) & (t <= t_rel)
    vout_short_tran_mv = float(np.min(vout[m_sh]) * 1e3)

    m_end = t >= t_rel + 0.80 * (t[-1] - t_rel)
    v_end = float(np.median(vout[m_end]))
    vout_recover_ok = bool(abs(v_end - v_nom) <= 0.02 * abs(v_nom))
    t_rec = _settling_time(t, vout, t_rel, float(t[-1]), v_nom, tol_frac=0.01)

    return {
        "i_lim_peak_ma": i_lim_peak_ma,
        "vout_knee_v": vout_knee_v,
        "i_short_ma": i_short_ma,
        "vout_short_dc_mv": vout_short_dc_mv,
        "foldback_ratio": foldback_ratio,
        "vout_nom_v": v_nom,
        "vout_short_tran_mv": vout_short_tran_mv,
        "vout_recover_ok": vout_recover_ok,
        "t_recover_us": t_rec * 1e6,
    }


def analyze_esr_grid(psf_dir: Path) -> dict[str, object]:
    loads = [("ilo", "10uA"), ("imid", "1mA"), ("ihi", "10mA")]
    esrs = [("esrlo", "5mOhm"), ("esrmid", "200mOhm"), ("esrhi", "5Ohm")]

    corners: dict[str, dict[str, object]] = {}
    pm_min_deg = float("inf")
    worst_corner = ""

    by_esr: dict[str, list[tuple[str, float]]] = {el: [] for _, el in esrs}

    for lk, ll in loads:
        for ek, el in esrs:
            f = find_single(psf_dir, [f"stb_{lk}_{ek}.stb", f"*{lk}_{ek}*.stb"])
            m = _stb_metrics_from_file(f)
            cname = f"{ll}_{el}"
            corners[cname] = {
                "load": ll,
                "esr": el,
                "T0_db": m["T0_db"],
                "ugf_mhz": m["ugf_mhz"],
                "pm_deg": m["pm_deg"],
                "gm_db": m["gm_db"],
            }
            by_esr[el].append((ll, m["pm_deg"]))
            if m["pm_deg"] < pm_min_deg:
                pm_min_deg = m["pm_deg"]
                worst_corner = cname

    def _summarize_esr(esr_lbl: str) -> dict[str, object]:
        pts = by_esr[esr_lbl]
        w_load, w_pm = min(pts, key=lambda x: x[1])
        return {
            "esr": esr_lbl,
            "pm_min_deg": w_pm,
            "worst_load": w_load,
            "all_loads_ge_45deg": bool(w_pm >= 45.0),
            "unstable_lt_30deg": bool(w_pm < 30.0),
        }

    return {
        "pm_min_deg": pm_min_deg,
        "worst_corner": worst_corner,
        "low_esr_boundary": _summarize_esr("5mOhm"),
        "tunnel_nominal": _summarize_esr("200mOhm"),
        "high_esr_boundary": _summarize_esr("5Ohm"),
        "corners": corners,
    }


def analyze_dropout_tran(
    psf_dir: Path, *, t_dip1: float, t_dip2: float, f_rip: float
) -> dict[str, float]:
    f_bo = find_single(psf_dir, ["tran_brownout.tran*", "*brownout*.tran"])
    dbo = parse_psf_ascii(f_bo)
    t = dbo["time"]
    vout = dbo["VOUT"]

    v_nom = float(np.median(vout[(t > 0.2 * t_dip1) & (t < 0.95 * t_dip1)]))
    m_dip = (t >= t_dip1) & (t <= t_dip2 + 5e-6)
    vout_min_dip_v = float(np.min(vout[m_dip]))

    m_rec = t >= t_dip2
    vout_recover_overshoot_mv = float(max(0.0, (np.max(vout[m_rec]) - v_nom) * 1e3))
    t_rec = _settling_time(t, vout, t_dip2, float(t[-1]), v_nom, tol_frac=0.01)

    f_rip_p = find_single(psf_dir, ["tran_ripple.tran*", "*ripple*.tran"])
    drip = parse_psf_ascii(f_rip_p)
    tr = drip["time"]
    vr_out = drip["VOUT"]
    vr_dd = drip["VDD"]

    t_ss_start = max(0.5 * float(tr[-1]), float(tr[-1]) - 4.0 / f_rip)
    m_ss = tr >= t_ss_start
    vdd_pp_mv = float((np.max(vr_dd[m_ss]) - np.min(vr_dd[m_ss])) * 1e3)
    vout_pp_mv = float((np.max(vr_out[m_ss]) - np.min(vr_out[m_ss])) * 1e3)
    dyn_psrr_db = float(20.0 * math.log10(max(vdd_pp_mv, 1e-12) / max(vout_pp_mv, 1e-12)))

    return {
        "vout_nom_v": v_nom,
        "vout_min_dip_v": vout_min_dip_v,
        "vout_recover_overshoot_mv": vout_recover_overshoot_mv,
        "t_recover_1pct_us": t_rec * 1e6,
        "vdd_ripple_pp_mv": vdd_pp_mv,
        "vout_ripple_pp_mv": vout_pp_mv,
        "dyn_psrr_db": dyn_psrr_db,
    }


def analyze_temp_shdn(psf_dir: Path) -> dict[str, float]:
    f_temp = find_single(psf_dir, ["dc_temp.dc", "*dc_temp*.dc"])
    dt = parse_psf_ascii(f_temp)
    t_key = next(k for k in dt if k not in {"VOUT", "EN", "VDD", "VSUP:p"})
    temps = dt[t_key]
    vout_t = dt["VOUT"]
    vout_27c_v = float(np.interp(27.0, temps, vout_t))
    tc_ppm_per_c = float(
        (np.max(vout_t) - np.min(vout_t))
        / (max(abs(vout_27c_v), 1e-12) * max(float(temps[-1] - temps[0]), 1e-9))
        * 1e6
    )

    f_iq = find_single(psf_dir, ["dc_iq_load.dc", "*iq_load*.dc"])
    di = parse_psf_ascii(f_iq)
    il_key = next(k for k in di if k not in {"VOUT", "EN", "VDD", "VSUP:p"})
    iload = di[il_key]
    isup = np.abs(di["VSUP:p"])
    iq = np.maximum(isup - iload, 0.0)
    iq_light_ua = float(iq[0] * 1e6)
    iq_full_ua = float(iq[-1] * 1e6)
    current_eff_light_pct = float(iload[0] / max(isup[0], 1e-30) * 100.0)
    current_eff_full_pct = float(iload[-1] / max(isup[-1], 1e-30) * 100.0)

    f_shdn = find_single(psf_dir, ["dc_shdn_temp.dc", "*shdn*.dc"])
    ds = parse_psf_ascii(f_shdn)
    ts_key = next(k for k in ds if k not in {"VOUT", "EN", "VDD", "VSUP:p"})
    t_shdn = ds[ts_key]
    i_shdn = np.abs(ds["VSUP:p"])
    i_shdn_27c_na = float(np.interp(27.0, t_shdn, i_shdn) * 1e9)
    i_shdn_125c_ua = float(np.interp(125.0, t_shdn, i_shdn) * 1e6)

    return {
        "vout_27c_v": vout_27c_v,
        "tc_ppm_per_c": tc_ppm_per_c,
        "iq_light_ua": iq_light_ua,
        "iq_full_ua": iq_full_ua,
        "current_eff_light_pct": current_eff_light_pct,
        "current_eff_full_pct": current_eff_full_pct,
        "i_shdn_27c_na": i_shdn_27c_na,
        "i_shdn_125c_ua": i_shdn_125c_ua,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze LDO Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_dc = sub.add_parser("dc_reg")
    p_dc.add_argument("psf_dir", type=Path)
    p_dc.add_argument("--vref", type=float, default=0.9)

    p_stb = sub.add_parser("stb")
    p_stb.add_argument("psf_dir", type=Path)

    p_pn = sub.add_parser("psrr_zout_noise")
    p_pn.add_argument("psf_dir", type=Path)

    p_tr = sub.add_parser("tran")
    p_tr.add_argument("psf_dir", type=Path)
    p_tr.add_argument("--t-ld1", type=float, default=1e-6)
    p_tr.add_argument("--t-ld2", type=float, default=3e-6)
    p_tr.add_argument("--t-ln1", type=float, default=5e-6)

    p_su = sub.add_parser("startup")
    p_su.add_argument("psf_dir", type=Path)
    p_su.add_argument("--t-en-on", type=float, default=10e-6)
    p_su.add_argument("--t-en-off", type=float, default=250e-6)

    p_ocp = sub.add_parser("ocp")
    p_ocp.add_argument("psf_dir", type=Path)
    p_ocp.add_argument("--t-sh1", type=float, default=20e-6)
    p_ocp.add_argument("--t-sh2", type=float, default=50e-6)

    p_esr = sub.add_parser("esr_grid")
    p_esr.add_argument("psf_dir", type=Path)

    p_do = sub.add_parser("dropout_tran")
    p_do.add_argument("psf_dir", type=Path)
    p_do.add_argument("--t-dip1", type=float, default=20e-6)
    p_do.add_argument("--t-dip2", type=float, default=60e-6)
    p_do.add_argument("--f-rip", type=float, default=50e3)

    p_ts = sub.add_parser("temp_shdn")
    p_ts.add_argument("psf_dir", type=Path)

    args = ap.parse_args(argv)
    if args.mode == "dc_reg":
        res: object = analyze_dc_reg(args.psf_dir, vref=args.vref)
    elif args.mode == "stb":
        res = analyze_stb(args.psf_dir)
    elif args.mode == "psrr_zout_noise":
        res = analyze_psrr_zout_noise(args.psf_dir)
    elif args.mode == "tran":
        res = analyze_tran(args.psf_dir, t_ld1=args.t_ld1, t_ld2=args.t_ld2, t_ln1=args.t_ln1)
    elif args.mode == "startup":
        res = analyze_startup(args.psf_dir, t_en_on=args.t_en_on, t_en_off=args.t_en_off)
    elif args.mode == "ocp":
        res = analyze_ocp(args.psf_dir, t_sh1=args.t_sh1, t_sh2=args.t_sh2)
    elif args.mode == "esr_grid":
        res = analyze_esr_grid(args.psf_dir)
    elif args.mode == "dropout_tran":
        res = analyze_dropout_tran(
            args.psf_dir, t_dip1=args.t_dip1, t_dip2=args.t_dip2, f_rip=args.f_rip
        )
    else:
        res = analyze_temp_shdn(args.psf_dir)

    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
