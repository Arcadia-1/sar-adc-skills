#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from the standalone Synchronous Buck TB suite.

Usage:
  python analyze_buck.py efficiency <psf_dir> [--f-sw 2e6] [--n-cycles 10]
  python analyze_buck.py ripple <psf_dir> [--f-sw 2e6] [--l-out 2.2e-6] [--n-cycles 10]
  python analyze_buck.py softstart <psf_dir> [--t-en 5e-6]
  python analyze_buck.py tran <psf_dir> [--t-ld1 35e-6] [--t-ld2 65e-6] [--t-ln1 95e-6]
  python analyze_buck.py stb <psf_dir>
  python analyze_buck.py ocp <psf_dir> [--t-sh1 40e-6] [--t-sh2 80e-6]
  python analyze_buck.py psrr_spur <psf_dir> [--f-sw 2e6] [--n-fft 1024]
  python analyze_buck.py deadtime <psf_dir> [--f-sw 2e6] [--n-cycles 8] [--shoot-thresh-ma 1000]
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
    crossings,
    extract_uniform_strobe,
    find_single,
    parse_psf_ascii,
    trapz,
)


def _window_slice(
    t: np.ndarray, t0: float, t1: float
) -> tuple[np.ndarray, np.ndarray]:
    """Return boolean mask and exact boundary-interpolated time vector on [t0, t1]."""
    mask = (t >= t0) & (t <= t1)
    if np.sum(mask) < 4:
        raise RuntimeError(f"Insufficient samples in window [{t0:.3e}, {t1:.3e}]")
    return mask, t[mask]


def _cycle_avg(t: np.ndarray, y: np.ndarray, t0: float, t1: float) -> float:
    """Exact time-weighted average of y(t) over [t0, t1] via trapezoidal integration."""
    t_in = t[(t > t0) & (t < t1)]
    ts = np.concatenate(([t0], t_in, [t1]))
    ys = np.interp(ts, t, y)
    return float(trapz(ys, ts) / (t1 - t0))


def _settling_time(
    t: np.ndarray, y: np.ndarray, t0: float, t1: float, y_ref: float, tol_abs: float
) -> float:
    """Time after `t0` until `y` enters and stays within `tol_abs` of `y_ref` until `t1`."""
    mask = (t >= t0) & (t <= t1)
    tw, yw = t[mask], y[mask]
    if len(tw) < 2:
        return 0.0
    outside = np.where(np.abs(yw - y_ref) > tol_abs)[0]
    if len(outside) == 0:
        return 0.0
    last_out = int(outside[-1])
    if last_out + 1 >= len(tw):
        return float(tw[-1] - t0)
    return float(tw[last_out + 1] - t0)


def _moving_avg_window(t: np.ndarray, y: np.ndarray, t_win: float) -> tuple[np.ndarray, np.ndarray]:
    """Compute switching-cycle averaged waveform on uniform grid for ripple-free envelope checks."""
    dt = t_win / 8.0
    t_u = np.arange(float(t[0]), float(t[-1]), dt)
    if len(t_u) < 16:
        return t, y
    y_u = np.interp(t_u, t, y)
    k = max(int(round(t_win / dt)), 1)
    kernel = np.ones(k, dtype=float) / k
    y_avg = np.convolve(y_u, kernel, mode="valid")
    t_avg = t_u[k - 1 :] - 0.5 * t_win
    return t_avg, y_avg


def analyze_efficiency(
    psf_dir: Path, *, f_sw: float, n_cycles: int
) -> dict[str, object]:
    cases = [
        ("20mA", ["tran_20ma.tran*", "*20ma*.tran*"]),
        ("100mA", ["tran_100ma.tran*", "*100ma*.tran*"]),
        ("300mA", ["tran_300ma.tran*", "*300ma*.tran*"]),
        ("500mA", ["tran_500ma.tran*", "*500ma*.tran*"]),
    ]
    t_sw = 1.0 / f_sw
    loads: dict[str, dict[str, object]] = {}

    for label, pats in cases:
        f = find_single(psf_dir, pats)
        d = parse_psf_ascii(f)
        t = d["time"]
        t1 = float(t[-1])
        t0 = max(float(t[0]), t1 - n_cycles * t_sw)

        v_in = d["VIN"]
        v_out = d["VOUT"]
        i_in = -d["VSUP:p"]
        i_out = d["VMEAS_O:p"]
        i_l = d["VMEAS_L:p"]

        vout_avg = _cycle_avg(t, v_out, t0, t1)
        iout_avg = _cycle_avg(t, i_out, t0, t1)
        p_in = _cycle_avg(t, v_in * i_in, t0, t1)
        p_out = _cycle_avg(t, v_out * i_out, t0, t1)
        p_loss = max(p_in - p_out, 0.0)
        eff_pct = (p_out / p_in * 100.0) if p_in > 0.0 else float("nan")

        # DCM vs CCM detection over steady-state window
        mask = (t >= t0) & (t <= t1)
        tw, ilw = t[mask], i_l[mask]
        dt_w = np.diff(tw)
        il_mid = 0.5 * (ilw[:-1] + ilw[1:])
        zero_dwell_frac = float(np.sum(dt_w[il_mid < 2.0e-3]) / max(tw[-1] - tw[0], 1e-15))
        il_min_ma = float(np.min(ilw) * 1e3)
        il_max_ma = float(np.max(ilw) * 1e3)
        mode = "DCM" if (zero_dwell_frac > 0.05 and il_min_ma < 2.0) else "CCM"

        loads[label] = {
            "i_load_ma": iout_avg * 1e3,
            "vout_avg_v": vout_avg,
            "p_in_mw": p_in * 1e3,
            "p_out_mw": p_out * 1e3,
            "p_loss_mw": p_loss * 1e3,
            "eff_pct": eff_pct,
            "il_min_ma": il_min_ma,
            "il_max_ma": il_max_ma,
            "zero_dwell_frac": zero_dwell_frac,
            "mode": mode,
        }

    effs = [float(v["eff_pct"]) for v in loads.values()]
    modes = {str(v["mode"]) for v in loads.values()}
    return {
        "loads": loads,
        "eff_peak_pct": float(max(effs)),
        "eff_light_load_pct": float(loads["20mA"]["eff_pct"]),
        "eff_full_load_pct": float(loads["500mA"]["eff_pct"]),
        "has_dcm_and_ccm": bool("DCM" in modes and "CCM" in modes),
    }


def analyze_ripple(
    psf_dir: Path, *, f_sw: float, l_out: float, n_cycles: int
) -> dict[str, float]:
    f = find_single(psf_dir, ["tran.tran*", "*.tran"])
    d = parse_psf_ascii(f)
    t = d["time"]
    t_sw = 1.0 / f_sw
    t1 = float(t[-1])
    t0 = max(float(t[0]), t1 - n_cycles * t_sw)

    v_in = d["VIN"]
    v_out = d["VOUT"]
    v_sw = d["SW"]
    i_l = d["VMEAS_L:p"]

    mask = (t >= t0) & (t <= t1)
    tw = t[mask]
    vw = v_out[mask]
    ilw = i_l[mask]
    sww = v_sw[mask]

    vin_avg = _cycle_avg(t, v_in, t0, t1)
    vout_avg = _cycle_avg(t, v_out, t0, t1)
    il_avg = _cycle_avg(t, i_l, t0, t1)

    vout_ripple_pp_mv = float((np.max(vw) - np.min(vw)) * 1e3)
    il_ripple_pp_ma = float((np.max(ilw) - np.min(ilw)) * 1e3)

    # Duty cycle from SW > 0.5 * VIN
    dt_w = np.diff(tw)
    sw_hi = (0.5 * (sww[:-1] + sww[1:])) > (0.5 * vin_avg)
    duty_meas = float(np.sum(dt_w[sw_hi]) / max(tw[-1] - tw[0], 1e-15))
    duty_ideal = float(vout_avg / vin_avg)

    il_ripple_theory_ma = float(vout_avg * (1.0 - duty_ideal) / (l_out * f_sw) * 1e3)
    il_ripple_err_pct = float(abs(il_ripple_pp_ma - il_ripple_theory_ma) / max(il_ripple_theory_ma, 1e-9) * 100.0)

    sw_max_v = float(np.max(sww))
    sw_min_v = float(np.min(sww))
    sw_overshoot_v = max(0.0, sw_max_v - vin_avg)
    sw_undershoot_v = max(0.0, -sw_min_v)

    return {
        "vin_avg_v": vin_avg,
        "vout_avg_v": vout_avg,
        "vout_ripple_pp_mv": vout_ripple_pp_mv,
        "il_avg_ma": il_avg * 1e3,
        "il_ripple_pp_ma": il_ripple_pp_ma,
        "il_ripple_theory_ma": il_ripple_theory_ma,
        "il_ripple_err_pct": il_ripple_err_pct,
        "duty_cycle_meas": duty_meas,
        "duty_cycle_ideal": duty_ideal,
        "sw_max_v": sw_max_v,
        "sw_min_v": sw_min_v,
        "sw_overshoot_v": sw_overshoot_v,
        "sw_undershoot_v": sw_undershoot_v,
    }


def analyze_softstart(psf_dir: Path, *, t_en: float, f_sw: float = 2.0e6) -> dict[str, object]:
    f = find_single(psf_dir, ["tran.tran*", "*.tran"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vout = d["VOUT"]
    i_l = d["VMEAS_L:p"]
    en = d.get("EN")

    t_on = t_en
    if en is not None and float(np.max(en)) > 0.5:
        rc = crossings(t, en, 0.5 * float(np.max(en)), direction="rising")
        if rc:
            t_on = rc[0]

    t_end = float(t[-1])
    v_final = _cycle_avg(t, vout, t_end - 10.0 / f_sw, t_end)

    m_on = t >= t_on
    tw, vw, ilw = t[m_on], vout[m_on], i_l[m_on]

    c10 = crossings(tw, vw, 0.10 * v_final, direction="rising")
    c90 = crossings(tw, vw, 0.90 * v_final, direction="rising")
    t_start_90 = (c90[0] - t_on) if c90 else float("nan")
    t_settle_1 = _settling_time(t, vout, t_on, t_end, v_final, tol_abs=0.01 * abs(v_final))

    v_peak = float(np.max(vw))
    overshoot_mv = max(0.0, (v_peak - v_final) * 1e3)
    overshoot_pct = overshoot_mv / max(abs(v_final) * 1e3, 1e-9) * 100.0
    il_inrush_peak_ma = float(np.max(ilw) * 1e3)

    # Monotonicity check on switching-cycle-averaged envelope across 10% -> 90% rise
    t_env, v_env = _moving_avg_window(tw, vw, 1.0 / f_sw)
    if c10 and c90 and c90[0] > c10[0]:
        mr = (t_env >= c10[0]) & (t_env <= c90[0])
        vr = v_env[mr]
        if len(vr) > 2:
            v_rmax = np.maximum.accumulate(vr)
            max_dip_mv = float(np.max(v_rmax - vr) * 1e3)
        else:
            max_dip_mv = 0.0
    else:
        max_dip_mv = 0.0
    monotonic = bool(max_dip_mv < 10.0)

    return {
        "vout_final_v": v_final,
        "t_start_90pct_us": t_start_90 * 1e6,
        "t_settle_1pct_us": t_settle_1 * 1e6,
        "il_inrush_peak_ma": il_inrush_peak_ma,
        "vout_overshoot_mv": overshoot_mv,
        "overshoot_pct": overshoot_pct,
        "max_rise_dip_mv": max_dip_mv,
        "monotonic_startup": monotonic,
    }


def analyze_tran(
    psf_dir: Path, *, t_ld1: float, t_ld2: float, t_ln1: float
) -> dict[str, float]:
    f = find_single(psf_dir, ["tran.tran*", "*.tran"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vout = d["VOUT"]

    v_nom = _cycle_avg(t, vout, t_ld1 - 5.0e-6, t_ld1 - 0.5e-6)
    m_ld1 = (t >= t_ld1) & (t < t_ld2)
    m_ld2 = (t >= t_ld2) & (t < t_ln1)
    m_ln = t >= t_ln1

    load_undershoot_mv = max(0.0, (v_nom - float(np.min(vout[m_ld1]))) * 1e3)
    load_overshoot_mv = max(0.0, (float(np.max(vout[m_ld2])) - v_nom) * 1e3)

    # Settling time to within +/-1% (+/-12 mV) of nominal after load step-up & step-down
    tol_v = max(0.01 * abs(v_nom), 10.0e-3)
    t_rec_up = _settling_time(t, vout, t_ld1, t_ld2 - 1.0e-6, v_nom, tol_abs=tol_v)
    t_rec_dn = _settling_time(t, vout, t_ld2, t_ln1 - 1.0e-6, v_nom, tol_abs=tol_v)

    v_pre_ln = _cycle_avg(t, vout, t_ln1 - 5.0e-6, t_ln1 - 0.5e-6)
    line_step_dev_mv = float(np.max(np.abs(vout[m_ln] - v_pre_ln)) * 1e3)

    return {
        "vout_nom_v": v_nom,
        "load_undershoot_mv": load_undershoot_mv,
        "load_overshoot_mv": load_overshoot_mv,
        "t_recover_up_us": t_rec_up * 1e6,
        "t_recover_dn_us": t_rec_dn * 1e6,
        "t_recover_load_us": max(t_rec_up, t_rec_dn) * 1e6,
        "line_step_dev_mv": line_step_dev_mv,
    }


def _stb_metrics_from_file(psf_file: Path) -> dict[str, float]:
    d = parse_psf_ascii(psf_file)
    freq = np.real(d["freq"])
    lg = d["loopGain"]
    if np.real(lg[0]) < 0.0:
        lg = -lg
    mag_db = 20.0 * np.log10(np.maximum(np.abs(lg), 1e-30))
    phase_deg = np.degrees(np.unwrap(np.angle(lg)))

    fc_hz = float("nan")
    pm_deg = float("nan")
    for i in range(len(mag_db) - 1):
        if mag_db[i] >= 0.0 > mag_db[i + 1]:
            frac = (0.0 - mag_db[i]) / (mag_db[i + 1] - mag_db[i])
            fc_hz = float(
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
        "dc_loop_gain_db": float(mag_db[0]),
        "f_crossover_khz": fc_hz * 1e-3 if math.isfinite(fc_hz) else float("nan"),
        "phase_margin_deg": pm_deg,
        "gain_margin_db": gm_db,
    }


def analyze_stb(psf_dir: Path) -> dict[str, object]:
    corner_specs = [
        ("vin2p7_100mA", ["stb_vinlo_ilo.stb*", "*vinlo_ilo*.stb*"]),
        ("vin3p3_100mA", ["stb_vinnom_ilo.stb*", "*vinnom_ilo*.stb*"]),
        ("vin3p3_500mA", ["stb_vinnom_ihi.stb*", "*vinnom_ihi*.stb*"]),
        ("vin4p5_500mA", ["stb_vinhi_ihi.stb*", "*vinhi_ihi*.stb*"]),
    ]
    corners: dict[str, dict[str, float]] = {}
    for name, pats in corner_specs:
        f = find_single(psf_dir, pats)
        corners[name] = _stb_metrics_from_file(f)

    worst_corner = min(corners, key=lambda k: corners[k]["phase_margin_deg"])
    pm_min = float(corners[worst_corner]["phase_margin_deg"])
    gm_vals = [float(v["gain_margin_db"]) for v in corners.values()]
    gm_min = float(min(gm_vals))

    return {
        "corners": corners,
        "pm_min_deg": pm_min,
        "worst_corner": worst_corner,
        "gm_min_db": gm_min,
        "f_crossover_nom_khz": float(corners["vin3p3_500mA"]["f_crossover_khz"]),
        "stb_pass": bool(pm_min >= 45.0 and gm_min >= 10.0),
    }


def analyze_ocp(psf_dir: Path, *, t_sh1: float, t_sh2: float) -> dict[str, object]:
    f = find_single(psf_dir, ["tran.tran*", "*.tran"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vout = d["VOUT"]
    i_l = d["VMEAS_L:p"]
    t_end = float(t[-1])

    v_pre = _cycle_avg(t, vout, t_sh1 - 5.0e-6, t_sh1 - 0.5e-6)
    m_sh = (t >= t_sh1) & (t <= t_sh2)
    m_sh_settled = (t >= t_sh1 + 0.5 * (t_sh2 - t_sh1)) & (t <= t_sh2 - 1.0e-6)

    il_ocp_peak_ma = float(np.max(i_l[m_sh]) * 1e3)
    vout_short_mv = float(np.mean(vout[m_sh_settled]) * 1e3)

    v_post = _cycle_avg(t, vout, t_end - 5.0e-6, t_end)
    vout_recover_ok = bool(abs(v_post - v_pre) < 0.02 * abs(v_pre))
    t_recover = _settling_time(t, vout, t_sh2, t_end, v_pre, tol_abs=0.02 * abs(v_pre))

    return {
        "vout_pre_v": v_pre,
        "il_ocp_peak_ma": il_ocp_peak_ma,
        "vout_short_mv": vout_short_mv,
        "vout_post_v": v_post,
        "vout_recover_ok": vout_recover_ok,
        "t_recover_us": t_recover * 1e6,
    }


def analyze_psrr_spur(
    psf_dir: Path, *, f_sw: float, n_fft: int
) -> dict[str, float]:
    # Part (a): Averaged small-signal audio susceptibility PSRR(f)
    f_ac = find_single(psf_dir, ["ac_psrr.ac*", "*.ac"])
    dac = parse_psf_ascii(f_ac)
    freq = np.real(dac["freq"])
    log_f = np.log10(freq)
    v_in_ac = dac.get("VIN_AC", np.ones_like(dac["VOUT_AC"]))
    h_aud = np.abs(dac["VOUT_AC"]) / np.maximum(np.abs(v_in_ac), 1e-30)
    psrr_db = -20.0 * np.log10(np.maximum(h_aud, 1e-30))

    def at(f_hz: float) -> float:
        return float(np.interp(math.log10(f_hz), log_f, psrr_db))

    idx_min = int(np.argmin(psrr_db))

    # Part (b): Coherently strobed switching VOUT FFT
    f_tr = find_single(psf_dir, ["tran_spur.tran*", "*.tran"])
    dtr = parse_psf_ascii(f_tr)
    tu, vu = extract_uniform_strobe(dtr["time"], dtr["VOUT_SW"])
    if len(vu) < n_fft:
        raise RuntimeError(f"Expected >= {n_fft} uniform strobe samples, got {len(vu)}")
    ts = tu[-n_fft:]
    vs = vu[-n_fft:]
    dt = float(np.median(np.diff(ts)))
    fs = 1.0 / dt

    vs_ac = vs - np.mean(vs)
    spec = np.fft.rfft(vs_ac)
    # Single-sided RMS voltage amplitude per bin
    v_rms_bins = np.abs(spec) / n_fft
    v_rms_bins[1 : (n_fft // 2 if n_fft % 2 == 0 else (n_fft + 1) // 2)] *= math.sqrt(2.0)

    k1 = int(round(f_sw / (fs / n_fft)))
    k2 = int(round(2.0 * f_sw / (fs / n_fft)))
    k3 = int(round(3.0 * f_sw / (fs / n_fft)))

    v_fsw = float(v_rms_bins[k1])
    v_2fsw = float(v_rms_bins[k2])
    v_3fsw = float(v_rms_bins[k3])
    v_rip_rms = float(np.sqrt(np.mean(vs_ac**2)))

    return {
        "psrr_dc_db": float(psrr_db[0]),
        "psrr_10khz_db": at(10e3),
        "psrr_fc_min_db": float(psrr_db[idx_min]),
        "f_psrr_min_khz": float(freq[idx_min] * 1e-3),
        "psrr_1mhz_db": at(1e6),
        "fs_mhz": fs * 1e-6,
        "n_fft": float(n_fft),
        "bin_fsw": float(k1),
        "spur_fsw_mvrms": v_fsw * 1e3,
        "spur_fsw_dbv": 20.0 * math.log10(max(v_fsw, 1e-15)),
        "spur_2fsw_mvrms": v_2fsw * 1e3,
        "spur_2fsw_dbv": 20.0 * math.log10(max(v_2fsw, 1e-15)),
        "spur_3fsw_dbv": 20.0 * math.log10(max(v_3fsw, 1e-15)),
        "vout_ripple_rms_mv": v_rip_rms * 1e3,
    }


def analyze_deadtime(
    psf_dir: Path, *, f_sw: float, n_cycles: int, shoot_thresh_ma: float
) -> dict[str, object]:
    regimes = [
        ("overlap_-5ns", -5.0, ["tran_overlap.tran*", "*overlap*.tran*"]),
        ("opt_10ns", 10.0, ["tran_opt.tran*", "*opt*.tran*"]),
        ("long_60ns", 60.0, ["tran_long.tran*", "*long*.tran*"]),
    ]
    t_sw = 1.0 / f_sw
    cases: dict[str, dict[str, object]] = {}

    for name, td_ns, pats in regimes:
        f = find_single(psf_dir, pats)
        d = parse_psf_ascii(f)
        t = d["time"]
        t1 = float(t[-1])
        t0 = max(float(t[0]), t1 - n_cycles * t_sw)

        v_in = d["VIN"]
        v_out = d["VOUT"]
        v_sw = d["SW"]
        i_in = -d["VSUP:p"]
        i_l = d["VMEAS_L:p"]
        i_out = d["VMEAS_O:p"]

        vout_avg = _cycle_avg(t, v_out, t0, t1)
        p_in = _cycle_avg(t, v_in * i_in, t0, t1)
        p_out = _cycle_avg(t, v_out * i_out, t0, t1)
        p_loss = max(p_in - p_out, 0.0)
        eff_pct = (p_out / p_in * 100.0) if p_in > 0.0 else float("nan")

        mask = (t >= t0) & (t <= t1)
        # Shoot-through cross-conduction current = supply current exceeding inductor current
        i_shoot = np.maximum(i_in[mask] - np.maximum(i_l[mask], 0.0), 0.0)
        i_shoot_peak_ma = float(np.max(i_shoot) * 1e3)
        i_vin_peak_ma = float(np.max(i_in[mask]) * 1e3)
        sw_min_v = float(np.min(v_sw[mask]))

        cases[name] = {
            "t_dead_ns": td_ns,
            "vout_avg_v": vout_avg,
            "i_vin_peak_ma": i_vin_peak_ma,
            "i_shoot_peak_ma": i_shoot_peak_ma,
            "p_in_mw": p_in * 1e3,
            "p_out_mw": p_out * 1e3,
            "p_sw_loss_mw": p_loss * 1e3,
            "eff_pct": eff_pct,
            "sw_min_v": sw_min_v,
            "deadtime_safe": bool(i_shoot_peak_ma < shoot_thresh_ma),
        }

    return {
        "cases": cases,
        "overlap_shoot_peak_ma": float(cases["overlap_-5ns"]["i_shoot_peak_ma"]),
        "opt_eff_pct": float(cases["opt_10ns"]["eff_pct"]),
        "long_loss_penalty_mw": float(
            cases["long_60ns"]["p_sw_loss_mw"] - cases["opt_10ns"]["p_sw_loss_mw"]
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze Spectre PSF ASCII outputs from the Synchronous Buck TB suite."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_eff = sub.add_parser("efficiency", help="Multi-load DCM/CCM efficiency sweep")
    p_eff.add_argument("psf_dir", type=Path)
    p_eff.add_argument("--f-sw", type=float, default=2.0e6)
    p_eff.add_argument("--n-cycles", type=int, default=10)

    p_rip = sub.add_parser("ripple", help="Steady-state CCM ripple & SW overshoot/undershoot")
    p_rip.add_argument("psf_dir", type=Path)
    p_rip.add_argument("--f-sw", type=float, default=2.0e6)
    p_rip.add_argument("--l-out", type=float, default=2.2e-6)
    p_rip.add_argument("--n-cycles", type=int, default=10)

    p_ss = sub.add_parser("softstart", help="Enable cold soft-start & inductor inrush")
    p_ss.add_argument("psf_dir", type=Path)
    p_ss.add_argument("--t-en", type=float, default=5.0e-6)
    p_ss.add_argument("--f-sw", type=float, default=2.0e6)

    p_tr = sub.add_parser("tran", help="Load-step & line-step transient response")
    p_tr.add_argument("psf_dir", type=Path)
    p_tr.add_argument("--t-ld1", type=float, default=35.0e-6)
    p_tr.add_argument("--t-ld2", type=float, default=65.0e-6)
    p_tr.add_argument("--t-ln1", type=float, default=95.0e-6)

    p_stb = sub.add_parser("stb", help="4-corner averaged control-loop iprobe stability")
    p_stb.add_argument("psf_dir", type=Path)

    p_ocp = sub.add_parser("ocp", help="Cycle-by-cycle OCP & hard short-circuit recovery")
    p_ocp.add_argument("psf_dir", type=Path)
    p_ocp.add_argument("--t-sh1", type=float, default=40.0e-6)
    p_ocp.add_argument("--t-sh2", type=float, default=80.0e-6)

    p_psrr = sub.add_parser("psrr_spur", help="Averaged PSRR(f) & switching Vout FFT spurs")
    p_psrr.add_argument("psf_dir", type=Path)
    p_psrr.add_argument("--f-sw", type=float, default=2.0e6)
    p_psrr.add_argument("--n-fft", type=int, default=1024)

    p_dt = sub.add_parser("deadtime", help="Dead-time sweep: shoot-through vs optimal vs body-diode loss")
    p_dt.add_argument("psf_dir", type=Path)
    p_dt.add_argument("--f-sw", type=float, default=2.0e6)
    p_dt.add_argument("--n-cycles", type=int, default=8)
    p_dt.add_argument("--shoot-thresh-ma", type=float, default=1000.0)

    args = parser.parse_args(argv)
    if args.cmd == "efficiency":
        res = analyze_efficiency(args.psf_dir, f_sw=args.f_sw, n_cycles=args.n_cycles)
    elif args.cmd == "ripple":
        res = analyze_ripple(args.psf_dir, f_sw=args.f_sw, l_out=args.l_out, n_cycles=args.n_cycles)
    elif args.cmd == "softstart":
        res = analyze_softstart(args.psf_dir, t_en=args.t_en, f_sw=args.f_sw)
    elif args.cmd == "tran":
        res = analyze_tran(args.psf_dir, t_ld1=args.t_ld1, t_ld2=args.t_ld2, t_ln1=args.t_ln1)
    elif args.cmd == "stb":
        res = analyze_stb(args.psf_dir)
    elif args.cmd == "ocp":
        res = analyze_ocp(args.psf_dir, t_sh1=args.t_sh1, t_sh2=args.t_sh2)
    elif args.cmd == "psrr_spur":
        res = analyze_psrr_spur(args.psf_dir, f_sw=args.f_sw, n_fft=args.n_fft)
    elif args.cmd == "deadtime":
        res = analyze_deadtime(
            args.psf_dir, f_sw=args.f_sw, n_cycles=args.n_cycles, shoot_thresh_ma=args.shoot_thresh_ma
        )
    else:
        raise ValueError(args.cmd)

    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
