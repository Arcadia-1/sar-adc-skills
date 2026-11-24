#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from Integer-N CP-PLL testbenches.

Usage:
  python analyze_int_n_pll.py ac_loop <psf_dir>
  python analyze_int_n_pll.py lock <psf_dir> [--f-target 1e9] [--f-ref 50e6] [--kvco 200e6] [--vdd 0.9]
  python analyze_int_n_pll.py bandcal <psf_dir> [--f-target 2e9] [--vdd 0.9] [--f-ref 50e6]
  python analyze_int_n_pll.py spur <psf_dir> [--f-carrier 1e9] [--f-ref 50e6] [--kvco 200e6] [--t-skip 1.8e-6]
  python analyze_int_n_pll.py psrr <psf_dir> [--f-carrier 1e9] [--kvco 200e6] [--t-skip 2.0e-6]
  python analyze_int_n_pll.py noise_scaling <psf_dir> [--f-carrier 1.6e9] [--f-low 10e3] [--f-high 30e6] [--pm-min-spec 45.0]
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
    crossings,
    extract_uniform_strobe,
    find_single,
    integrate_phase_noise_jitter,
    parse_psf_ascii,
    trapz,
)


def analyze_ac_loop(psf_dir: Path) -> dict[str, float]:
    f_stb = find_single(psf_dir, ["stb.stb", "*.stb.stb"])
    ds = parse_psf_ascii(f_stb)
    freq = np.real(ds["freq"])
    lg = ds["loopGain"]
    # Normalize probe polarity so low-frequency phase of Type-II loop starts near -180 deg
    # (or 0 deg in Spectre negative-feedback convention where PM = 180 + phase)
    if np.real(lg[0]) > 0 and np.imag(lg[0]) > 0:
        lg = -lg
    # Actually in Type-II loop, L(s) ~ K / s^2 at low freq -> real(L) < 0, imag(L) > 0, phase ~ -180 -> +180.
    # For consistent PM extraction matching Spectre stb, use angle in [-180, +180]:
    mag_db = 20.0 * np.log10(np.maximum(np.abs(lg), 1e-30))

    # Find unity-gain crossing (first downward 0 dB crossing)
    fu_hz = float("nan")
    pm_deg = float("nan")
    for i in range(len(mag_db) - 1):
        if mag_db[i] >= 0.0 > mag_db[i + 1]:
            frac = (0.0 - mag_db[i]) / (mag_db[i + 1] - mag_db[i])
            fu_hz = float(10.0 ** (math.log10(freq[i]) + frac * (math.log10(freq[i + 1]) - math.log10(freq[i]))))
            lg_u = lg[i] + frac * (lg[i + 1] - lg[i])
            # Distance of loopGain(fu) from the unstable point (-1 + 0j):
            # In Spectre stb, loopGain = -T(s) or +T(s); phase margin is angle from -180 deg.
            ang_deg = math.degrees(math.atan2(lg_u.imag, lg_u.real))
            # Map angle relative to -180 deg into [0, 180]
            pm_deg = (ang_deg + 180.0) % 360.0
            if pm_deg > 180.0:
                pm_deg = 360.0 - pm_deg
            break

    # AC closed-loop peaking and -3 dB bandwidth
    f_ac = find_single(psf_dir, ["ac.ac", "*.ac.ac", "*.ac"])
    da = parse_psf_ascii(f_ac)
    freq_ac = np.real(da["freq"])
    h_cl = np.abs(da["PHI_FB"]) / np.maximum(np.abs(da["PHI_REF"]), 1e-30)
    h_db = 20.0 * np.log10(np.maximum(h_cl, 1e-30))
    peaking_db = float(np.max(h_db) - h_db[0])

    f_3db = float("nan")
    target_db = float(h_db[0] - 3.0)
    for i in range(len(h_db) - 1):
        if h_db[i] >= target_db > h_db[i + 1]:
            frac = (target_db - h_db[i]) / (h_db[i + 1] - h_db[i])
            f_3db = float(10.0 ** (math.log10(freq_ac[i]) + frac * (math.log10(freq_ac[i + 1]) - math.log10(freq_ac[i]))))
            break

    return {
        "fu_mhz": fu_hz * 1e-6 if math.isfinite(fu_hz) else float("nan"),
        "phase_margin_deg": pm_deg,
        "cl_peaking_db": peaking_db,
        "cl_bw_3db_mhz": f_3db * 1e-6 if math.isfinite(f_3db) else float("nan"),
    }


def analyze_lock(
    psf_dir: Path, *, f_target: float, f_ref: float, kvco: float, vdd: float
) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vctrl = d["VCTRL"]
    finst = d["F_INST"] * 1e9  # va_phase_err_mon outputs GHz (freq_scale=1e-9)

    # Steady-state window = final 25% of simulation
    t_ss = 0.75 * float(t[-1])
    ss = t >= t_ss
    vctrl_ss = vctrl[ss]
    vctrl_mean = float(np.mean(vctrl_ss))
    vctrl_ripple_pp = float(np.max(vctrl_ss) - np.min(vctrl_ss))

    # Exact average locked frequency by counting OUTP rising edges in steady state
    edges = np.asarray(crossings(t[ss], d["OUTP"][ss], 0.5 * vdd, "rising"), dtype=float)
    if len(edges) >= 4:
        f_locked = float((len(edges) - 1) / (edges[-1] - edges[0]))
        per_jit_ps = float(np.std(np.diff(edges)) * 1e12)
    else:
        f_locked = float(np.mean(finst[ss]))
        per_jit_ps = float("nan")

    freq_err_ppm = (f_locked - f_target) / f_target * 1e6

    # 0.1% frequency settling time
    tol = 0.001 * f_target
    outside = np.where(np.abs(finst - f_target) > tol)[0]
    if len(outside) == 0:
        t_settle = 0.0
    elif outside[-1] + 1 < len(t):
        t_settle = float(t[outside[-1] + 1])
    else:
        t_settle = float("nan")

    # Narrowband FM reference spur estimate from sinusoidal approximation V_pk = V_pp / 2
    v_pk = 0.5 * vctrl_ripple_pp
    ref_spur_dbc = (
        20.0 * math.log10(max((kvco * v_pk) / (2.0 * f_ref), 1e-12))
        if v_pk > 0.0
        else -200.0
    )

    return {
        "f_target_mhz": f_target * 1e-6,
        "f_locked_mhz": f_locked * 1e-6,
        "freq_err_ppm": freq_err_ppm,
        "t_settle_0p1pct_us": t_settle * 1e6 if math.isfinite(t_settle) else float("nan"),
        "vctrl_mean_v": vctrl_mean,
        "vctrl_ripple_pp_mv": vctrl_ripple_pp * 1e3,
        "est_ref_spur_dbc": ref_spur_dbc,
        "period_jitter_ps": per_jit_ps,
    }


def _parse_stb_metrics(stb_file: Path) -> dict[str, object]:
    """Extract f_u, phase margin, and gain margin from a Spectre stb PSF ASCII file."""
    ds = parse_psf_ascii(stb_file)
    freq = np.real(ds["freq"])
    lg = ds["loopGain"]
    if np.real(lg[0]) > 0 and np.imag(lg[0]) > 0:
        lg = -lg
    mag_db = 20.0 * np.log10(np.maximum(np.abs(lg), 1e-30))

    fu_hz = float("nan")
    pm_deg = float("nan")
    idx_u = -1
    for i in range(len(mag_db) - 1):
        if mag_db[i] >= 0.0 > mag_db[i + 1]:
            frac = (0.0 - mag_db[i]) / (mag_db[i + 1] - mag_db[i])
            fu_hz = float(
                10.0 ** (math.log10(freq[i]) + frac * (math.log10(freq[i + 1]) - math.log10(freq[i])))
            )
            lg_u = lg[i] + frac * (lg[i + 1] - lg[i])
            ang_deg = math.degrees(math.atan2(lg_u.imag, lg_u.real))
            pm_deg = (ang_deg + 180.0) % 360.0
            if pm_deg > 180.0:
                pm_deg = 360.0 - pm_deg
            idx_u = i
            break

    # Look for a -180 deg phase crossing above f_u (negative real axis crossing)
    gm_db: float | None = None
    if idx_u >= 0:
        for i in range(idx_u, len(lg) - 1):
            im0, im1 = float(lg[i].imag), float(lg[i + 1].imag)
            re_mid = 0.5 * (float(lg[i].real) + float(lg[i + 1].real))
            if re_mid < 0.0 and ((im0 >= 0.0 > im1) or (im0 <= 0.0 < im1)):
                frac = abs(im0) / max(abs(im0) + abs(im1), 1e-30)
                lg_180 = lg[i] + frac * (lg[i + 1] - lg[i])
                gm_db = float(-20.0 * math.log10(max(abs(lg_180), 1e-30)))
                break

    return {
        "fu_mhz": fu_hz * 1e-6 if math.isfinite(fu_hz) else float("nan"),
        "phase_margin_deg": pm_deg,
        "gain_margin_db": gm_db,
        "gm_unconditional": bool(gm_db is None),
    }


def _tone_amp_ls(t: np.ndarray, y: np.ndarray, freq_hz: float) -> float:
    """Exact single-sided peak amplitude of `y(t)` at `freq_hz` via linear least squares."""
    w = 2.0 * math.pi * freq_hz * (t - t[0])
    design = np.column_stack([np.ones_like(w), np.cos(w), np.sin(w)])
    coeff, *_ = np.linalg.lstsq(design, y, rcond=None)
    return float(math.hypot(coeff[1], coeff[2]))


def _peak_near_bin(mag: np.ndarray, target_bin: int, half_width: int = 3) -> tuple[float, int]:
    lo = max(1, target_bin - half_width)
    hi = min(len(mag) - 1, target_bin + half_width)
    sub = mag[lo : hi + 1]
    idx_rel = int(np.argmax(sub))
    return float(sub[idx_rel]), lo + idx_rel


def analyze_bandcal(
    psf_dir: Path, *, f_target: float = 2.0e9, vdd: float = 0.9, f_ref: float = 50.0e6
) -> dict[str, object]:
    """Extract AFC calibration time, latched code, lock/lock-detect timing, ppm error, and P_DD."""
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vth = 0.5 * vdd

    en_edges = crossings(t, d["PLL_EN"], vth, "rising")
    cal_edges = crossings(t, d["CAL_DONE"], vth, "rising")
    lock_edges = crossings(t, d["LOCK"], vth, "rising")
    if not en_edges or not cal_edges:
        raise RuntimeError(f"Missing PLL_EN ({len(en_edges)}) or CAL_DONE ({len(cal_edges)}) edge")

    t_en = float(en_edges[0])
    t_cal_done = float(cal_edges[0])
    t_cal = t_cal_done - t_en

    post_cal = t >= t_cal_done
    cal_code = int(round(float(np.median(d["VCODE"][t >= t_cal_done + 50e-9]))))

    finst = d["F_INST"] * 1e9
    t_pc = t[post_cal]
    f_pc = finst[post_cal]

    def _settle_after_cal(tol_rel: float) -> float:
        out = np.where(np.abs(f_pc - f_target) > tol_rel * f_target)[0]
        if len(out) == 0:
            return 0.0
        if out[-1] + 1 < len(t_pc):
            return float(t_pc[out[-1] + 1] - t_cal_done)
        return float("nan")

    t_lock_1pct = _settle_after_cal(0.01)
    t_lock_0p1pct = _settle_after_cal(0.001)

    lock_after_cal = [x for x in lock_edges if x >= t_cal_done]
    t_lock_det = float(lock_after_cal[0] - t_cal_done) if lock_after_cal else float("nan")
    t_total_lock = float(lock_after_cal[0] - t_en) if lock_after_cal else float("nan")
    lock_stable = bool(np.min(d["LOCK"][t >= 0.90 * float(t[-1])]) > vth)

    # Steady-state frequency, VCTRL, and active supply power over final 15%
    ss = t >= 0.85 * float(t[-1])
    edges_out = np.asarray(crossings(t[ss], d["OUTP"][ss], vth, "rising"), dtype=float)
    if len(edges_out) >= 4:
        f_locked = float((len(edges_out) - 1) / (edges_out[-1] - edges_out[0]))
    else:
        f_locked = float(np.mean(finst[ss]))
    freq_err_ppm = (f_locked - f_target) / f_target * 1e6
    vctrl_final = float(np.mean(d["VCTRL"][ss]))

    p_dd_mw = float("nan")
    if "VSUP:p" in d:
        i_avg = abs(trapz(d["VSUP:p"][ss], t[ss]) / max(float(t[ss][-1] - t[ss][0]), 1e-15))
        p_dd_mw = i_avg * vdd * 1e3

    return {
        "f_target_mhz": f_target * 1e-6,
        "f_ref_mhz": f_ref * 1e-6,
        "t_en_us": t_en * 1e6,
        "t_cal_done_us": t_cal_done * 1e6,
        "t_cal_us": t_cal * 1e6,
        "cal_code": cal_code,
        "t_lock_1pct_us": t_lock_1pct * 1e6 if math.isfinite(t_lock_1pct) else float("nan"),
        "t_lock_0p1pct_us": t_lock_0p1pct * 1e6 if math.isfinite(t_lock_0p1pct) else float("nan"),
        "t_lock_detect_us": t_lock_det * 1e6 if math.isfinite(t_lock_det) else float("nan"),
        "t_total_lock_us": t_total_lock * 1e6 if math.isfinite(t_total_lock) else float("nan"),
        "lock_asserted": bool(len(lock_after_cal) > 0),
        "lock_stable_at_end": lock_stable,
        "f_locked_mhz": f_locked * 1e-6,
        "freq_err_ppm": freq_err_ppm,
        "vctrl_final_v": vctrl_final,
        "p_dd_mw": p_dd_mw,
    }


def analyze_spur(
    psf_dir: Path,
    *,
    f_carrier: float = 1.0e9,
    f_ref: float = 50.0e6,
    kvco: float = 200.0e6,
    t_skip: float = 1.8e-6,
) -> dict[str, object]:
    """Direct Kaiser-windowed OUTP FFT reference spur vs. VCTRL NBFM prediction."""
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t, outp, vctrl = extract_uniform_strobe(d["time"], d["OUTP"], d["VCTRL"])
    dt = float(np.median(np.diff(t)))
    fs = 1.0 / dt

    m = t >= t_skip - 1e-15
    t_w, out_w, vc_w = t[m], outp[m], vctrl[m]
    pts_per_ref = int(round(fs / f_ref))
    n_ref_cyc = len(t_w) // pts_per_ref
    if n_ref_cyc < 8:
        raise RuntimeError(f"Need >= 8 settled reference cycles for spur FFT, got {n_ref_cyc}")
    n_fft = n_ref_cyc * pts_per_ref
    t_w, out_w, vc_w = t_w[-n_fft:], out_w[-n_fft:], vc_w[-n_fft:]

    win = np.kaiser(n_fft, 12.0)
    norm = 2.0 / float(np.sum(win))
    mag_out = np.abs(np.fft.rfft((out_w - np.mean(out_w)) * win)) * norm
    mag_vc = np.abs(np.fft.rfft((vc_w - np.mean(vc_w)) * win)) * norm
    df = fs / n_fft

    a_carr, b_carr = _peak_near_bin(mag_out, int(round(f_carrier / df)), half_width=3)
    f0_meas = b_carr * df
    b_step = int(round(f_ref / df))
    a_lo1, _ = _peak_near_bin(mag_out, b_carr - b_step, half_width=2)
    a_hi1, _ = _peak_near_bin(mag_out, b_carr + b_step, half_width=2)
    a_lo2, _ = _peak_near_bin(mag_out, b_carr - 2 * b_step, half_width=2)
    a_hi2, _ = _peak_near_bin(mag_out, b_carr + 2 * b_step, half_width=2)

    spur_lo1 = 20.0 * math.log10(max(a_lo1, 1e-15) / max(a_carr, 1e-15))
    spur_hi1 = 20.0 * math.log10(max(a_hi1, 1e-15) / max(a_carr, 1e-15))
    spur_1st = max(spur_lo1, spur_hi1)
    spur_2nd = 20.0 * math.log10(max(a_lo2, a_hi2, 1e-15) / max(a_carr, 1e-15))

    v_rip_1, _ = _peak_near_bin(mag_vc, b_step, half_width=2)
    v_rip_2, _ = _peak_near_bin(mag_vc, 2 * b_step, half_width=2)
    spur_nbfm = 20.0 * math.log10(max(kvco * v_rip_1 / (2.0 * f_ref), 1e-15))

    return {
        "n_fft": int(n_fft),
        "n_ref_cycles": int(n_ref_cyc),
        "fs_ghz": fs * 1e-9,
        "f0_meas_mhz": f0_meas * 1e-6,
        "f_ref_mhz": f_ref * 1e-6,
        "spur_lo1_dbc": spur_lo1,
        "spur_hi1_dbc": spur_hi1,
        "ref_spur_fft_dbc": spur_1st,
        "spur_2nd_fft_dbc": spur_2nd,
        "vctrl_mean_v": float(np.mean(vc_w)),
        "vctrl_ripple_pp_mv": float((np.max(vc_w) - np.min(vc_w)) * 1e3),
        "v_rip_fref_uv": v_rip_1 * 1e6,
        "v_rip_2fref_uv": v_rip_2 * 1e6,
        "ref_spur_nbfm_dbc": spur_nbfm,
        "fft_vs_nbfm_err_db": spur_1st - spur_nbfm,
    }


def analyze_psrr(
    psf_dir: Path,
    *,
    f_carrier: float = 1.0e9,
    kvco: float = 200.0e6,
    t_skip: float = 2.0e-6,
) -> dict[str, object]:
    """Extract closed-loop PLL PSRR(f) across injected VDDA ripple frequencies."""
    files = sorted(
        Path(psf_dir).glob("tran_f*.tran"),
        key=lambda p: int(m.group(1)) if (m := re.search(r"f(\d+)", p.name)) else 0,
    )
    if not files:
        raise FileNotFoundError(f"No tran_f*.tran files found in {psf_dir}")

    points: list[dict[str, object]] = []
    for p in files:
        d = parse_psf_ascii(p)
        t, vdda, vctrl, finst_ghz, outp = extract_uniform_strobe(
            d["time"], d["VDDA"], d["VCTRL"], d["F_INST"], d["OUTP"]
        )
        dt = float(np.median(np.diff(t)))
        fs = 1.0 / dt
        m = t >= t_skip - 1e-15
        tw, va_w, vc_w, fi_w, out_w = t[m], vdda[m], vctrl[m], finst_ghz[m] * 1e9, outp[m]

        # Auto-detect injected supply ripple frequency from VDDA FFT peak
        spec_va = np.abs(np.fft.rfft(va_w - np.mean(va_w)))
        freqs_raw = np.fft.rfftfreq(len(va_w), d=dt)
        k_rip = int(np.argmax(spec_va[1:]) + 1)
        f_rip_est = float(freqs_raw[k_rip])
        # Snap to exact coherent integer cycle count in window
        n_cyc = max(int(round((tw[-1] - tw[0] + dt) * f_rip_est)), 1)
        pts_per_cyc = int(round(fs / f_rip_est))
        n_use = min(n_cyc * pts_per_cyc, len(tw))
        tw, va_w, vc_w, fi_w, out_w = (
            tw[-n_use:],
            va_w[-n_use:],
            vc_w[-n_use:],
            fi_w[-n_use:],
            out_w[-n_use:],
        )
        f_rip = float(n_cyc * fs / n_use)

        v_rip_pk = _tone_amp_ls(tw, va_w, f_rip)
        df_peak_hz = _tone_amp_ls(tw, fi_w, f_rip)
        vctrl_rip_pk = _tone_amp_ls(tw, vc_w, f_rip)
        v_ctrl_eq = df_peak_hz / max(abs(kvco), 1.0)
        psrr_finst_db = 20.0 * math.log10(max(v_rip_pk, 1e-15) / max(v_ctrl_eq, 1e-15))

        # Cross-check via direct OUTP(t) FM sidebands at f_carrier +/- f_rip
        win = np.hanning(n_use)
        mag_out = np.abs(np.fft.rfft((out_w - np.mean(out_w)) * win)) * (2.0 / float(np.sum(win)))
        df_bin = fs / n_use
        b_carr = int(round(f_carrier / df_bin))
        b_rip = int(round(f_rip / df_bin))
        a_carr = float(mag_out[b_carr])
        a_sb = max(
            float(mag_out[max(1, b_carr - b_rip)]),
            float(mag_out[min(len(mag_out) - 1, b_carr + b_rip)]),
        )
        spur_dbc = 20.0 * math.log10(max(a_sb, 1e-15) / max(a_carr, 1e-15))
        df_peak_fft = 2.0 * f_rip * (10.0 ** (spur_dbc / 20.0))
        psrr_fft_db = 20.0 * math.log10(max(v_rip_pk, 1e-15) / max(df_peak_fft / kvco, 1e-15))

        points.append(
            {
                "file": p.name,
                "f_rip_mhz": round(f_rip * 1e-6, 4),
                "v_rip_mv": round(v_rip_pk * 1e3, 3),
                "df_peak_khz": round(df_peak_hz * 1e-3, 3),
                "vctrl_counter_mv": round(vctrl_rip_pk * 1e3, 3),
                "v_ctrl_eq_mv": round(v_ctrl_eq * 1e3, 4),
                "psrr_db": round(psrr_finst_db, 2),
                "fm_sideband_dbc": round(spur_dbc, 2),
                "psrr_fft_db": round(psrr_fft_db, 2),
            }
        )

    points.sort(key=lambda pt: float(pt["f_rip_mhz"]))
    psrr_in = float(points[0]["psrr_db"])
    psrr_oob = float(points[-1]["psrr_db"])
    return {
        "n_freqs": int(len(points)),
        "kvco_mhz_per_v": kvco * 1e-6,
        "psrr_inband_db": psrr_in,
        "psrr_oob_db": psrr_oob,
        "inband_vs_oob_rejection_db": round(psrr_in - psrr_oob, 2),
        "points": points,
    }


def analyze_noise_scaling(
    psf_dir: Path,
    *,
    f_carrier: float = 1.6e9,
    f_low: float = 10.0e3,
    f_high: float = 30.0e6,
    pm_min_spec: float = 45.0,
) -> dict[str, object]:
    """Analyze closed-loop phase-noise budget and 9-point N x ICP stability matrix."""
    def _load_sphi(name: str) -> tuple[np.ndarray, np.ndarray]:
        p = find_single(psf_dir, [f"{name}.noise", f"*{name}*.noise"])
        dn = parse_psf_ascii(p)
        fk = "freq" if "freq" in dn else next(iter(dn.keys()))
        ok = "out" if "out" in dn else next(k for k in dn if k != fk)
        return np.real(dn[fk]), np.real(dn[ok]) ** 2  # double-sided S_phi [rad^2/Hz]

    freq, s_tot = _load_sphi("noise_tot")
    _, s_r1 = _load_sphi("noise_r1")
    _, s_cp_r1 = _load_sphi("noise_cp")
    _, s_vco_r1 = _load_sphi("noise_vco")
    _, s_ref_r1 = _load_sphi("noise_ref")

    s_cp = np.maximum(s_cp_r1 - s_r1, 0.0)
    s_vco = np.maximum(s_vco_r1 - s_r1, 0.0)
    s_ref = np.maximum(s_ref_r1 - s_r1, 0.0)

    def _sphi_to_l(s_arr: np.ndarray) -> np.ndarray:
        return 10.0 * np.log10(np.maximum(0.5 * s_arr, 1e-30))

    l_tot = _sphi_to_l(s_tot)
    log_f = np.log10(freq)
    jit_tot = integrate_phase_noise_jitter(
        freq, l_tot, f_carrier, f_low_hz=f_low, f_high_hz=f_high
    )
    var_tot = jit_tot["rms_phase_rad"] ** 2

    contribs_var: dict[str, float] = {}
    for label, s_blk in (("cp", s_cp), ("vco", s_vco), ("r1", s_r1), ("ref_div", s_ref)):
        j_blk = integrate_phase_noise_jitter(
            freq, _sphi_to_l(s_blk), f_carrier, f_low_hz=f_low, f_high_hz=f_high
        )
        contribs_var[label] = j_blk["rms_phase_rad"] ** 2

    var_sum = sum(contribs_var.values())
    contrib_pct = {
        k: round(100.0 * v / max(var_tot, 1e-30), 2) for k, v in contribs_var.items()
    }
    closure_err_pct = 100.0 * abs(var_sum - var_tot) / max(var_tot, 1e-30)

    # Part B: 9-point N x I_CP stability matrix (exclude Spectre *.margin.stb summaries)
    stb_files = sorted(
        p for p in Path(psf_dir).glob("stb_n*_i*.stb") if not p.name.endswith(".margin.stb")
    )
    if not stb_files:
        raise FileNotFoundError(f"No stb_n*_i*.stb files found in {psf_dir}")

    matrix: list[dict[str, object]] = []
    for p in stb_files:
        m = re.search(r"n(\d+)_i(\d+)", p.name)
        if not m:
            continue
        n_val, icp_ua = int(m.group(1)), int(m.group(2))
        st = _parse_stb_metrics(p)
        pm = float(st["phase_margin_deg"])
        matrix.append(
            {
                "n_div": n_val,
                "i_cp_ua": icp_ua,
                "icp_over_n_ua": round(icp_ua / n_val, 3),
                "fu_mhz": round(float(st["fu_mhz"]), 4),
                "phase_margin_deg": round(pm, 2),
                "gain_margin_db": st["gain_margin_db"],
                "gm_unconditional": st["gm_unconditional"],
                "pm_pass": bool(pm >= pm_min_spec),
            }
        )
    matrix.sort(key=lambda r: (int(r["n_div"]), int(r["i_cp_ua"])))

    pms = [float(r["phase_margin_deg"]) for r in matrix]
    diag = [r for r in matrix if abs(float(r["icp_over_n_ua"]) - 5.0) < 0.05]
    diag_fus = [float(r["fu_mhz"]) for r in diag]
    diag_spread = (
        100.0 * (max(diag_fus) - min(diag_fus)) / max(float(np.mean(diag_fus)), 1e-9)
        if len(diag_fus) >= 2
        else 0.0
    )

    return {
        "f_carrier_ghz": f_carrier * 1e-9,
        "jitter_band_khz_to_mhz": f"{f_low*1e-3:.1f}k-{f_high*1e-6:.1f}M",
        "l_100khz_dbc_hz": round(float(np.interp(math.log10(1e5), log_f, l_tot)), 2),
        "l_1mhz_dbc_hz": round(float(np.interp(math.log10(1e6), log_f, l_tot)), 2),
        "l_10mhz_dbc_hz": round(float(np.interp(math.log10(1e7), log_f, l_tot)), 2),
        "rms_jitter_fs": round(jit_tot["rms_jitter_fs"], 2),
        "rms_phase_deg": round(jit_tot["rms_phase_deg"], 4),
        "noise_contrib_pct": contrib_pct,
        "noise_budget_closure_err_pct": round(closure_err_pct, 4),
        "n_matrix_points": int(len(matrix)),
        "pm_min_deg": round(min(pms), 2),
        "pm_max_deg": round(max(pms), 2),
        "pm_min_spec_deg": pm_min_spec,
        "n_pm_below_spec": int(sum(1 for pm in pms if pm < pm_min_spec)),
        "diag_const_bw_fu_spread_pct": round(diag_spread, 4),
        "matrix": matrix,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze Integer-N PLL Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_ac = sub.add_parser("ac_loop", help="Extract f_u, PM, peaking, 3dB BW from tb_int_n_pll_ac_loop.scs")
    p_ac.add_argument("psf_dir", type=Path)

    p_lk = sub.add_parser("lock", help="Extract lock freq, settling time, VCTRL ripple from tb_int_n_pll_lock.scs")
    p_lk.add_argument("psf_dir", type=Path)
    p_lk.add_argument("--f-target", type=float, default=1.0e9)
    p_lk.add_argument("--f-ref", type=float, default=50.0e6)
    p_lk.add_argument("--kvco", type=float, default=200.0e6)
    p_lk.add_argument("--vdd", type=float, default=0.9)

    p_bc = sub.add_parser("bandcal", help="Analyze AFC band-calibration & lock detect from tb_int_n_pll_bandcal_lock.scs")
    p_bc.add_argument("psf_dir", type=Path)
    p_bc.add_argument("--f-target", type=float, default=2.0e9)
    p_bc.add_argument("--vdd", type=float, default=0.9)
    p_bc.add_argument("--f-ref", type=float, default=50.0e6)

    p_sp = sub.add_parser("spur", help="Analyze FFT & NBFM reference spurs from tb_int_n_pll_ref_spur.scs")
    p_sp.add_argument("psf_dir", type=Path)
    p_sp.add_argument("--f-carrier", type=float, default=1.0e9)
    p_sp.add_argument("--f-ref", type=float, default=50.0e6)
    p_sp.add_argument("--kvco", type=float, default=200.0e6)
    p_sp.add_argument("--t-skip", type=float, default=1.8e-6)

    p_ps = sub.add_parser("psrr", help="Analyze closed-loop supply rejection from tb_int_n_pll_psrr.scs")
    p_ps.add_argument("psf_dir", type=Path)
    p_ps.add_argument("--f-carrier", type=float, default=1.0e9)
    p_ps.add_argument("--kvco", type=float, default=200.0e6)
    p_ps.add_argument("--t-skip", type=float, default=2.0e-6)

    p_ns = sub.add_parser("noise_scaling", help="Analyze phase-noise budget & 9-pt N x ICP stb matrix from tb_int_n_pll_noise_scaling.scs")
    p_ns.add_argument("psf_dir", type=Path)
    p_ns.add_argument("--f-carrier", type=float, default=1.6e9)
    p_ns.add_argument("--f-low", type=float, default=10.0e3)
    p_ns.add_argument("--f-high", type=float, default=30.0e6)
    p_ns.add_argument("--pm-min-spec", type=float, default=45.0)

    args = ap.parse_args(argv)
    if args.mode == "ac_loop":
        res: object = analyze_ac_loop(args.psf_dir)
    elif args.mode == "lock":
        res = analyze_lock(
            args.psf_dir,
            f_target=args.f_target,
            f_ref=args.f_ref,
            kvco=args.kvco,
            vdd=args.vdd,
        )
    elif args.mode == "bandcal":
        res = analyze_bandcal(
            args.psf_dir, f_target=args.f_target, vdd=args.vdd, f_ref=args.f_ref
        )
    elif args.mode == "spur":
        res = analyze_spur(
            args.psf_dir,
            f_carrier=args.f_carrier,
            f_ref=args.f_ref,
            kvco=args.kvco,
            t_skip=args.t_skip,
        )
    elif args.mode == "psrr":
        res = analyze_psrr(
            args.psf_dir,
            f_carrier=args.f_carrier,
            kvco=args.kvco,
            t_skip=args.t_skip,
        )
    else:
        res = analyze_noise_scaling(
            args.psf_dir,
            f_carrier=args.f_carrier,
            f_low=args.f_low,
            f_high=args.f_high,
            pm_min_spec=args.pm_min_spec,
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
