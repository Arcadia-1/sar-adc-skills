#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from Current-Steering DAC testbenches.

Usage:
  python analyze_cs_dac.py static <psf_dir> [--n-codes 1024]
  python analyze_cs_dac.py dynamic <psf_dir> [--n-fft 256] [--m-bin 29] [--fs 200e6]
  python analyze_cs_dac.py twotone <psf_dir> [--n-fft 256] [--m-bin1 59] [--m-bin2 61] [--fs 200e6]
  python analyze_cs_dac.py glitch <psf_dir> [--t-rise 10e-9] [--t-fall 20e-9] [--lsb-v 1e-3]
  python analyze_cs_dac.py sfdr_sweep <psf_dir> [--n-fft 256] [--osr 8] [--fs 200e6]
  python analyze_cs_dac.py psrr_jitter <psf_dir> [--n-fft 256] [--osr 8] [--m-bin 67] [--m-rip 17]
  python analyze_cs_dac.py compliance <psf_dir> [--n-fft 256] [--m-bin 29] [--fs 200e6]
  python analyze_cs_dac.py dem <psf_dir> [--n-fft 512] [--m-bin 19] [--fs 200e6] [--osr-inband 4]
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
    coherent_fft_metrics,
    coherent_twotone_metrics,
    dnl_inl_from_transfer,
    extract_uniform_strobe,
    find_single,
    parse_psf_ascii,
    trapz,
)


def analyze_static(psf_dir: Path, *, n_codes: int) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t, vp, vn, cm = extract_uniform_strobe(d["time"], d["IOUTP"], d["IOUTN"], d["CODE_MON"])
    vdiff = vp - vn
    if len(vdiff) < n_codes:
        raise RuntimeError(f"Expected at least {n_codes} strobed codes, got {len(vdiff)}")

    # Group by rounded integer code so exact 0..n_codes-1 levels are extracted
    codes = np.round(cm).astype(int)
    levels = np.empty(n_codes, dtype=float)
    for c in range(n_codes):
        idx = np.where(codes == c)[0]
        if len(idx) == 0:
            raise RuntimeError(f"Missing code {c} in static sweep")
        levels[c] = float(vdiff[idx[-1]])

    m = dnl_inl_from_transfer(levels)
    v_mid_err = 0.5 * (levels[0] + levels[-1])
    monotonic = bool(m["dnl_min_lsb"] > -1.0)
    return {
        "n_codes": int(n_codes),
        "full_scale_v": m["full_scale_v"],
        "lsb_mv": m["lsb_v"] * 1e3,
        "midpoint_offset_mv": float(v_mid_err * 1e3),
        "vcm_mean_v": float(0.5 * np.mean(vp + vn)),
        "dnl_max_lsb": m["dnl_max_lsb"],
        "dnl_min_lsb": m["dnl_min_lsb"],
        "dnl_abs_max_lsb": m["dnl_abs_max_lsb"],
        "inl_max_lsb": m["inl_max_lsb"],
        "inl_min_lsb": m["inl_min_lsb"],
        "inl_abs_max_lsb": m["inl_abs_max_lsb"],
        "monotonic": monotonic,
    }


def analyze_dynamic(
    psf_dir: Path, *, n_fft: int, m_bin: int | None, fs: float | None
) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, vp, vn = extract_uniform_strobe(d["time"], d["IOUTP"], d["IOUTN"])
    vdiff = vp - vn
    if len(vdiff) < n_fft:
        raise RuntimeError(f"Expected at least {n_fft} strobed samples, got {len(vdiff)}")
    seg = vdiff[-n_fft:]
    return coherent_fft_metrics(seg, num_harmonics=7, fs=fs, m_bin=m_bin)


def analyze_twotone(
    psf_dir: Path, *, n_fft: int, m_bin1: int, m_bin2: int, fs: float | None
) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, vp, vn = extract_uniform_strobe(d["time"], d["IOUTP"], d["IOUTN"])
    vdiff = vp - vn
    if len(vdiff) < n_fft:
        raise RuntimeError(f"Expected at least {n_fft} strobed samples, got {len(vdiff)}")
    seg = vdiff[-n_fft:]
    return coherent_twotone_metrics(seg, m_bin1=m_bin1, m_bin2=m_bin2, fs=fs)


def _measure_transition(
    t: np.ndarray, v: np.ndarray, t_edge: float, t_end: float, lsb_v: float
) -> dict[str, float]:
    pre_m = (t >= t_edge - 2e-9) & (t <= t_edge - 0.2e-9)
    post_m = (t >= t_end - 2e-9) & (t <= t_end - 0.2e-9)
    v_pre = float(np.mean(v[pre_m]))
    v_post = float(np.mean(v[post_m]))

    win_m = (t >= t_edge) & (t <= t_end - 0.5e-9)
    tw, vw = t[win_m], v[win_m]

    v_lo, v_hi = min(v_pre, v_post), max(v_pre, v_post)
    excess = np.where(vw > v_hi, vw - v_hi, np.where(vw < v_lo, v_lo - vw, 0.0))
    peak_glitch_v = float(np.max(excess))
    impulse_vs = float(trapz(excess, tw))

    tol = 0.5 * lsb_v
    outside = np.where(np.abs(vw - v_post) > tol)[0]
    t_settle = float(tw[outside[-1] + 1] - t_edge) if (len(outside) > 0 and outside[-1] + 1 < len(tw)) else 0.0

    return {
        "step_mv": (v_post - v_pre) * 1e3,
        "glitch_peak_mv": peak_glitch_v * 1e3,
        "glitch_impulse_pvs": impulse_vs * 1e12,
        "t_settle_0p5lsb_ns": t_settle * 1e9,
    }


def analyze_glitch(
    psf_dir: Path, *, t_rise: float, t_fall: float, lsb_v: float
) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vdiff = d["IOUTP"] - d["IOUTN"]
    t_stop = float(t[-1])

    r = _measure_transition(t, vdiff, t_rise, t_fall, lsb_v)
    fa = _measure_transition(t, vdiff, t_fall, t_stop, lsb_v)
    return {
        "rise_step_mv": r["step_mv"],
        "rise_glitch_peak_mv": r["glitch_peak_mv"],
        "rise_glitch_impulse_pvs": r["glitch_impulse_pvs"],
        "rise_t_settle_0p5lsb_ns": r["t_settle_0p5lsb_ns"],
        "fall_step_mv": fa["step_mv"],
        "fall_glitch_peak_mv": fa["glitch_peak_mv"],
        "fall_glitch_impulse_pvs": fa["glitch_impulse_pvs"],
        "fall_t_settle_0p5lsb_ns": fa["t_settle_0p5lsb_ns"],
        "worst_glitch_impulse_pvs": max(r["glitch_impulse_pvs"], fa["glitch_impulse_pvs"]),
    }


def _fold_bin(k: int, n: int) -> int:
    k_mod = abs(int(k)) % n
    return n - k_mod if k_mod > n // 2 else k_mod


def _extract_output_trace(d: dict[str, np.ndarray], *, prefer_filt: bool = True) -> np.ndarray:
    if prefer_filt and "V_FILT" in d:
        _, sig = extract_uniform_strobe(d["time"], d["V_FILT"])
        return sig
    _, vp, vn = extract_uniform_strobe(d["time"], d["IOUTP"], d["IOUTN"])
    return vp - vn


def _nyquist_fft_metrics(
    samples: np.ndarray,
    *,
    n_fft: int,
    osr: int,
    m_bin: int,
    fs: float,
    num_harmonics: int = 7,
    bw_bins: int | None = None,
) -> tuple[dict[str, float], np.ndarray]:
    """Compute coherent FFT metrics inside the first Nyquist zone [0, fs/2] (or bw_bins)."""
    n_tot = int(n_fft * osr)
    if len(samples) < n_tot:
        raise RuntimeError(f"Expected at least {n_tot} strobed samples, got {len(samples)}")
    seg = np.asarray(samples[-n_tot:], dtype=float)
    seg = seg - np.mean(seg)
    spec = np.fft.rfft(seg)
    pwr = (np.abs(spec) ** 2) / (n_tot * n_tot)
    pwr[1 : (n_tot // 2 if n_tot % 2 == 0 else (n_tot + 1) // 2)] *= 2.0

    # Restrict to first Nyquist zone [0, fs/2) (bins 0 .. n_fft//2 - 1)
    nyq_hi = n_fft // 2
    nyq = pwr[:nyq_hi].copy()
    p_sig = float(nyq[m_bin])
    if p_sig <= 0.0:
        raise RuntimeError(f"Zero fundamental power at bin {m_bin}")

    hi_lim = min(int(bw_bins), nyq_hi - 1) if bw_bins is not None else (nyq_hi - 1)
    band = nyq[: hi_lim + 1].copy()

    harm_bins: set[int] = set()
    hd_dbc: dict[int, float] = {}
    for h in range(2, num_harmonics + 1):
        kb = _fold_bin(h * m_bin, n_fft)
        if 0 < kb < nyq_hi and kb != m_bin:
            hd_dbc[h] = 10.0 * math.log10(max(float(nyq[kb]), 1e-30) / p_sig)
            if kb <= hi_lim:
                harm_bins.add(kb)

    p_harm = float(sum(band[kb] for kb in harm_bins))
    p_non_dc = float(np.sum(band[1:]))
    p_nad = max(p_non_dc - p_sig, 1e-30)
    p_noise = max(p_nad - p_harm, 1e-30)

    spur = band.copy()
    spur[0] = 0.0
    if m_bin <= hi_lim:
        spur[m_bin] = 0.0
    max_spur_bin = int(np.argmax(spur))
    p_spur = max(float(spur[max_spur_bin]), 1e-30)

    sndr_db = 10.0 * math.log10(p_sig / p_nad)
    snr_db = 10.0 * math.log10(p_sig / p_noise)
    thd_db = 10.0 * math.log10(max(p_harm, 1e-30) / p_sig)
    sfdr_db = 10.0 * math.log10(p_sig / p_spur)
    enob_bits = (sndr_db - 1.7609125905568124) / 6.020599913279624

    metrics = {
        "m_bin": float(m_bin),
        "f_in_mhz": float(fs * m_bin / n_fft / 1e6),
        "sfdr_db": float(sfdr_db),
        "hd2_dbc": float(hd_dbc.get(2, -180.0)),
        "hd3_dbc": float(hd_dbc.get(3, -180.0)),
        "thd_db": float(thd_db),
        "sndr_db": float(sndr_db),
        "snr_db": float(snr_db),
        "enob_bits": float(enob_bits),
        "amp_peak_v": float(math.sqrt(2.0 * p_sig)),
        "max_spur_bin": float(max_spur_bin),
    }
    return metrics, nyq


def analyze_sfdr_sweep(
    psf_dir: Path, *, n_fft: int, osr: int, fs: float, bins: list[int]
) -> dict[str, object]:
    points: list[dict[str, float]] = []
    for idx, m_bin in enumerate(bins):
        f = find_single(psf_dir, [f"tran_f{idx}.tran*", f"tran_f{idx}*.tran"])
        d = parse_psf_ascii(f)
        sig = _extract_output_trace(d, prefer_filt=True)
        m, _ = _nyquist_fft_metrics(sig, n_fft=n_fft, osr=osr, m_bin=m_bin, fs=fs)
        points.append(m)

    sfdr_low = points[0]["sfdr_db"]
    sfdr_nyq = points[-1]["sfdr_db"]
    return {
        "fs_mhz": float(fs / 1e6),
        "n_fft": int(n_fft),
        "osr": int(osr),
        "sfdr_low_db": float(sfdr_low),
        "sfdr_nyq_db": float(sfdr_nyq),
        "sfdr_rolloff_db": float(sfdr_low - sfdr_nyq),
        "hd3_low_dbc": float(points[0]["hd3_dbc"]),
        "hd3_nyq_dbc": float(points[-1]["hd3_dbc"]),
        "enob_low_bits": float(points[0]["enob_bits"]),
        "enob_nyq_bits": float(points[-1]["enob_bits"]),
        "points": points,
    }


def analyze_psrr_jitter(
    psf_dir: Path,
    *,
    n_fft: int,
    osr: int,
    m_bin: int,
    m_rip: int,
    fs: float,
    v_rip_pp: float,
    t_jitter_rms: float,
) -> dict[str, object]:
    # Part A: Dynamic Supply PSRR
    f_psrr = find_single(psf_dir, ["tran_psrr.tran*", "tran_psrr*.tran"])
    d_psrr = parse_psf_ascii(f_psrr)
    sig_psrr = _extract_output_trace(d_psrr, prefer_filt=True)
    m_psrr, nyq_psrr = _nyquist_fft_metrics(sig_psrr, n_fft=n_fft, osr=osr, m_bin=m_bin, fs=fs)

    # Measure actual VDD ripple amplitude at bin m_rip if VDD was saved
    v_rip_pk = 0.5 * v_rip_pp
    if "VDD" in d_psrr:
        _, vdd_s = extract_uniform_strobe(d_psrr["time"], d_psrr["VDD"])
        n_tot = int(n_fft * osr)
        if len(vdd_s) >= n_tot:
            vdd_seg = vdd_s[-n_tot:] - np.mean(vdd_s[-n_tot:])
            vdd_spec = np.fft.rfft(vdd_seg)
            vdd_pwr = 2.0 * (np.abs(vdd_spec) ** 2) / (n_tot * n_tot)
            v_rip_pk_meas = math.sqrt(max(2.0 * float(vdd_pwr[m_rip]), 1e-30))
            if v_rip_pk_meas > 1e-6:
                v_rip_pk = v_rip_pk_meas

    p_sig = float(nyq_psrr[m_bin])
    p_rip = max(float(nyq_psrr[m_rip]), 1e-30)
    v_out_rip_pk = math.sqrt(2.0 * p_rip)
    psrr_db = 20.0 * math.log10(v_rip_pk / max(v_out_rip_pk, 1e-15))
    supply_spur_dbc = 10.0 * math.log10(p_rip / p_sig)

    sb_lo_bin = _fold_bin(m_bin - m_rip, n_fft)
    sb_hi_bin = _fold_bin(m_bin + m_rip, n_fft)
    sb_lo_dbc = 10.0 * math.log10(max(float(nyq_psrr[sb_lo_bin]), 1e-30) / p_sig)
    sb_hi_dbc = 10.0 * math.log10(max(float(nyq_psrr[sb_hi_bin]), 1e-30) / p_sig)

    # Part B: Clean baseline vs calibrated RMS clock jitter
    f_clean = find_single(psf_dir, ["tran_clean.tran*", "tran_clean*.tran"])
    d_clean = parse_psf_ascii(f_clean)
    sig_clean = _extract_output_trace(d_clean, prefer_filt=True)
    m_clean, _ = _nyquist_fft_metrics(sig_clean, n_fft=n_fft, osr=osr, m_bin=m_bin, fs=fs)

    f_jit = find_single(psf_dir, ["tran_jitter.tran*", "tran_jitter*.tran"])
    d_jit = parse_psf_ascii(f_jit)
    sig_jit = _extract_output_trace(d_jit, prefer_filt=True)
    m_jit, _ = _nyquist_fft_metrics(sig_jit, n_fft=n_fft, osr=osr, m_bin=m_bin, fs=fs)

    f_out_hz = fs * m_bin / n_fft
    snr_thy_db = -20.0 * math.log10(max(2.0 * math.pi * f_out_hz * t_jitter_rms, 1e-15))

    nsr_clean = 10.0 ** (-m_clean["snr_db"] / 10.0)
    nsr_jit = 10.0 ** (-m_jit["snr_db"] / 10.0)
    excess_nsr = max(nsr_jit - nsr_clean, 1e-15)
    snr_jit_iso_db = -10.0 * math.log10(excess_nsr)
    t_j_est_ps = math.sqrt(excess_nsr) / (2.0 * math.pi * f_out_hz) * 1e12
    snr_theory_err_db = snr_jit_iso_db - snr_thy_db

    return {
        "f_out_mhz": float(f_out_hz / 1e6),
        "f_rip_mhz": float(fs * m_rip / n_fft / 1e6),
        "v_rip_pp_mv": float(2.0 * v_rip_pk * 1e3),
        "psrr_db": float(psrr_db),
        "supply_spur_dbc": float(supply_spur_dbc),
        "sb_lo_bin": int(sb_lo_bin),
        "sb_hi_bin": int(sb_hi_bin),
        "sb_lo_dbc": float(sb_lo_dbc),
        "sb_hi_dbc": float(sb_hi_dbc),
        "sideband_worst_dbc": float(max(sb_lo_dbc, sb_hi_dbc)),
        "snr_psrr_db": float(m_psrr["snr_db"]),
        "snr_clean_db": float(m_clean["snr_db"]),
        "sndr_clean_db": float(m_clean["sndr_db"]),
        "snr_jitter_db": float(m_jit["snr_db"]),
        "sndr_jitter_db": float(m_jit["sndr_db"]),
        "snr_degradation_db": float(m_clean["snr_db"] - m_jit["snr_db"]),
        "snr_jitter_isolated_db": float(snr_jit_iso_db),
        "snr_jitter_theory_db": float(snr_thy_db),
        "snr_theory_err_db": float(snr_theory_err_db),
        "t_j_injected_ps": float(t_jitter_rms * 1e12),
        "t_j_est_ps": float(t_j_est_ps),
        "jitter_model_match": bool(abs(snr_theory_err_db) <= 3.0),
    }


def analyze_compliance(
    psf_dir: Path, *, n_fft: int, m_bin: int, fs: float, drop_pct: float
) -> dict[str, object]:
    # Part A: DC output compliance sweep
    f_dc = find_single(psf_dir, ["dc_comp.dc*", "dc_comp*.dc"])
    d_dc = parse_psf_ascii(f_dc)
    v_out = np.asarray(d_dc["IOUTP"], dtype=float)
    i_key = "VPROBEP:p" if "VPROBEP:p" in d_dc else next(k for k in d_dc if k.endswith(":p"))
    i_out = np.asarray(d_dc[i_key], dtype=float)
    if float(np.median(i_out)) < 0.0:
        i_out = -i_out

    order = np.argsort(v_out)
    v_out, i_out = v_out[order], i_out[order]

    # Fit linear saturation slope I_lin(V) = intercept + slope*V in flat region
    sat_mask = (v_out >= 0.05) & (v_out <= 0.35)
    if int(np.sum(sat_mask)) < 3:
        i_pk = float(np.max(i_out[v_out >= 0.0])) if np.any(v_out >= 0.0) else float(np.max(i_out))
        sat_mask = (v_out >= 0.0) & (i_out >= 0.99 * i_pk)
    if int(np.sum(sat_mask)) < 2:
        sat_mask = np.arange(len(v_out)) < max(3, len(v_out) // 4)

    slope, intercept = np.polyfit(v_out[sat_mask], i_out[sat_mask], 1)
    r_out_eff_kohm = float((-1.0 / slope) / 1e3) if slope < -1e-12 else 1.0e6
    i_lin = intercept + slope * v_out
    i_nom_ma = float(np.interp(0.20, v_out, i_out) * 1e3)

    # Nonlinear compliance knee: first V_out > 0.25 V where current drops drop_pct% below I_lin(V)
    drop_frac = (i_lin - i_out) / np.maximum(i_lin, 1e-12)
    thresh = drop_pct / 100.0
    knee_idx = np.where((v_out > 0.25) & (drop_frac >= thresh))[0]
    if len(knee_idx) > 0:
        k0 = int(knee_idx[0])
        if k0 > 0 and drop_frac[k0] != drop_frac[k0 - 1]:
            frac = (thresh - drop_frac[k0 - 1]) / (drop_frac[k0] - drop_frac[k0 - 1])
            v_comp_max_v = float(v_out[k0 - 1] + frac * (v_out[k0] - v_out[k0 - 1]))
        else:
            v_comp_max_v = float(v_out[k0])
    else:
        v_comp_max_v = float(v_out[-1])

    # Part B: Dynamic matched vs 2% mismatched load resistor impact on HD2
    f_mat = find_single(psf_dir, ["tran_matched.tran*", "tran_matched*.tran"])
    d_mat = parse_psf_ascii(f_mat)
    _, vp_m, vn_m = extract_uniform_strobe(d_mat["time"], d_mat["IOUTP"], d_mat["IOUTN"])
    v_out_peak_v = float(max(np.max(vp_m[-n_fft:]), np.max(vn_m[-n_fft:])))
    m_mat = coherent_fft_metrics((vp_m - vn_m)[-n_fft:], num_harmonics=7, fs=fs, m_bin=m_bin)

    f_mis = find_single(psf_dir, ["tran_mismatched.tran*", "tran_mismatched*.tran"])
    d_mis = parse_psf_ascii(f_mis)
    _, vp_x, vn_x = extract_uniform_strobe(d_mis["time"], d_mis["IOUTP"], d_mis["IOUTN"])
    m_mis = coherent_fft_metrics((vp_x - vn_x)[-n_fft:], num_harmonics=7, fs=fs, m_bin=m_bin)

    return {
        "i_midscale_ma": i_nom_ma,
        "r_out_eff_kohm": r_out_eff_kohm,
        "v_comp_max_v": v_comp_max_v,
        "v_out_peak_v": v_out_peak_v,
        "compliance_margin_mv": float((v_comp_max_v - v_out_peak_v) * 1e3),
        "compliance_pass": bool(v_out_peak_v <= v_comp_max_v),
        "hd2_matched_dbc": float(m_mat["hd2_dbc"]),
        "hd3_matched_dbc": float(m_mat["hd3_dbc"]),
        "sfdr_matched_db": float(m_mat["sfdr_db"]),
        "hd2_mismatched_dbc": float(m_mis["hd2_dbc"]),
        "hd3_mismatched_dbc": float(m_mis["hd3_dbc"]),
        "sfdr_mismatched_db": float(m_mis["sfdr_db"]),
        "hd2_degradation_db": float(m_mis["hd2_dbc"] - m_mat["hd2_dbc"]),
    }


def analyze_dem(
    psf_dir: Path,
    *,
    n_fft: int,
    m_bin: int,
    fs: float,
    osr_inband: int,
    sfdr_spec_db: float,
) -> dict[str, object]:
    f_st = find_single(psf_dir, ["tran_static.tran*", "tran_static*.tran"])
    d_st = parse_psf_ascii(f_st)
    v_st = _extract_output_trace(d_st, prefer_filt=False)

    f_dm = find_single(psf_dir, ["tran_dem.tran*", "tran_dem*.tran"])
    d_dm = parse_psf_ascii(f_dm)
    v_dm = _extract_output_trace(d_dm, prefer_filt=False)

    bw_bins = max(n_fft // (2 * osr_inband), m_bin + 1)
    st_ib, _ = _nyquist_fft_metrics(v_st, n_fft=n_fft, osr=1, m_bin=m_bin, fs=fs, bw_bins=bw_bins)
    dm_ib, _ = _nyquist_fft_metrics(v_dm, n_fft=n_fft, osr=1, m_bin=m_bin, fs=fs, bw_bins=bw_bins)
    st_nyq, _ = _nyquist_fft_metrics(v_st, n_fft=n_fft, osr=1, m_bin=m_bin, fs=fs)
    dm_nyq, _ = _nyquist_fft_metrics(v_dm, n_fft=n_fft, osr=1, m_bin=m_bin, fs=fs)

    return {
        "n_fft": int(n_fft),
        "m_bin": int(m_bin),
        "f_in_mhz": float(fs * m_bin / n_fft / 1e6),
        "osr_inband": int(osr_inband),
        "sfdr_static_db": float(st_ib["sfdr_db"]),
        "sfdr_dem_db": float(dm_ib["sfdr_db"]),
        "sfdr_gain_db": float(dm_ib["sfdr_db"] - st_ib["sfdr_db"]),
        "sfdr_static_nyq_db": float(st_nyq["sfdr_db"]),
        "sfdr_dem_nyq_db": float(dm_nyq["sfdr_db"]),
        "sfdr_nyq_gain_db": float(dm_nyq["sfdr_db"] - st_nyq["sfdr_db"]),
        "hd2_static_dbc": float(st_ib["hd2_dbc"]),
        "hd2_dem_dbc": float(dm_ib["hd2_dbc"]),
        "hd3_static_dbc": float(st_ib["hd3_dbc"]),
        "hd3_dem_dbc": float(dm_ib["hd3_dbc"]),
        "sndr_static_db": float(st_ib["sndr_db"]),
        "sndr_dem_db": float(dm_ib["sndr_db"]),
        "sndr_inband_gain_db": float(dm_ib["sndr_db"] - st_ib["sndr_db"]),
        "sndr_static_nyq_db": float(st_nyq["sndr_db"]),
        "sndr_dem_nyq_db": float(dm_nyq["sndr_db"]),
        "sfdr_spec_db": float(sfdr_spec_db),
        "sfdr_pass": bool(st_ib["sfdr_db"] >= sfdr_spec_db),
        "sfdr_dem_pass": bool(dm_ib["sfdr_db"] >= sfdr_spec_db),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze Current-Steering DAC Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_st = sub.add_parser("static")
    p_st.add_argument("psf_dir", type=Path)
    p_st.add_argument("--n-codes", type=int, default=1024)

    p_dy = sub.add_parser("dynamic")
    p_dy.add_argument("psf_dir", type=Path)
    p_dy.add_argument("--n-fft", type=int, default=256)
    p_dy.add_argument("--m-bin", type=int, default=None)
    p_dy.add_argument("--fs", type=float, default=200e6)

    p_tt = sub.add_parser("twotone")
    p_tt.add_argument("psf_dir", type=Path)
    p_tt.add_argument("--n-fft", type=int, default=256)
    p_tt.add_argument("--m-bin1", type=int, default=59)
    p_tt.add_argument("--m-bin2", type=int, default=61)
    p_tt.add_argument("--fs", type=float, default=200e6)

    p_gl = sub.add_parser("glitch")
    p_gl.add_argument("psf_dir", type=Path)
    p_gl.add_argument("--t-rise", type=float, default=10e-9)
    p_gl.add_argument("--t-fall", type=float, default=20e-9)
    p_gl.add_argument("--lsb-v", type=float, default=1.0e-3)

    p_sw = sub.add_parser("sfdr_sweep")
    p_sw.add_argument("psf_dir", type=Path)
    p_sw.add_argument("--n-fft", type=int, default=256)
    p_sw.add_argument("--osr", type=int, default=8)
    p_sw.add_argument("--fs", type=float, default=200e6)
    p_sw.add_argument("--bins", type=int, nargs="+", default=[7, 29, 67, 113])

    p_pj = sub.add_parser("psrr_jitter")
    p_pj.add_argument("psf_dir", type=Path)
    p_pj.add_argument("--n-fft", type=int, default=256)
    p_pj.add_argument("--osr", type=int, default=8)
    p_pj.add_argument("--m-bin", type=int, default=67)
    p_pj.add_argument("--m-rip", type=int, default=17)
    p_pj.add_argument("--fs", type=float, default=200e6)
    p_pj.add_argument("--v-rip-pp", type=float, default=0.05)
    p_pj.add_argument("--t-jitter-rms", type=float, default=5e-12)

    p_cp = sub.add_parser("compliance")
    p_cp.add_argument("psf_dir", type=Path)
    p_cp.add_argument("--n-fft", type=int, default=256)
    p_cp.add_argument("--m-bin", type=int, default=29)
    p_cp.add_argument("--fs", type=float, default=200e6)
    p_cp.add_argument("--drop-pct", type=float, default=1.0)

    p_dm = sub.add_parser("dem")
    p_dm.add_argument("psf_dir", type=Path)
    p_dm.add_argument("--n-fft", type=int, default=512)
    p_dm.add_argument("--m-bin", type=int, default=19)
    p_dm.add_argument("--fs", type=float, default=200e6)
    p_dm.add_argument("--osr-inband", type=int, default=4)
    p_dm.add_argument("--sfdr-spec-db", type=float, default=48.0)

    args = ap.parse_args(argv)
    if args.mode == "static":
        res: object = analyze_static(args.psf_dir, n_codes=args.n_codes)
    elif args.mode == "dynamic":
        res = analyze_dynamic(args.psf_dir, n_fft=args.n_fft, m_bin=args.m_bin, fs=args.fs)
    elif args.mode == "twotone":
        res = analyze_twotone(
            args.psf_dir, n_fft=args.n_fft, m_bin1=args.m_bin1, m_bin2=args.m_bin2, fs=args.fs
        )
    elif args.mode == "glitch":
        res = analyze_glitch(
            args.psf_dir, t_rise=args.t_rise, t_fall=args.t_fall, lsb_v=args.lsb_v
        )
    elif args.mode == "sfdr_sweep":
        res = analyze_sfdr_sweep(
            args.psf_dir, n_fft=args.n_fft, osr=args.osr, fs=args.fs, bins=args.bins
        )
    elif args.mode == "psrr_jitter":
        res = analyze_psrr_jitter(
            args.psf_dir,
            n_fft=args.n_fft,
            osr=args.osr,
            m_bin=args.m_bin,
            m_rip=args.m_rip,
            fs=args.fs,
            v_rip_pp=args.v_rip_pp,
            t_jitter_rms=args.t_jitter_rms,
        )
    elif args.mode == "compliance":
        res = analyze_compliance(
            args.psf_dir, n_fft=args.n_fft, m_bin=args.m_bin, fs=args.fs, drop_pct=args.drop_pct
        )
    else:
        res = analyze_dem(
            args.psf_dir,
            n_fft=args.n_fft,
            m_bin=args.m_bin,
            fs=args.fs,
            osr_inband=args.osr_inband,
            sfdr_spec_db=args.sfdr_spec_db,
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
