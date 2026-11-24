#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from full SAR ADC testbenches.

Usage:
  python analyze_adc_top.py fft <psf_dir> [--n-bits 10] [--n-fft 128] [--m-bin 19] [--fs 50e6]
  python analyze_adc_top.py ramp <psf_dir> [--n-bits 10]
  python analyze_adc_top.py twotone <psf_dir> [--n-bits 10] [--n-fft 256] [--m-bin1 97] [--m-bin2 107] [--fs 50e6]
  python analyze_adc_top.py vref_droop <psf_dir> [--n-bits 10] [--n-fft 128] [--m-bin 19] [--fs 50e6] [--vref 0.9]
  python analyze_adc_top.py noise_hist <psf_dir> [--n-bits 10] [--n-fft 256] [--m-bin 43] [--n-hist 512] [--vref 0.9]
  python analyze_adc_top.py psrr_cmrr <psf_dir> [--n-bits 10] [--n-fft 256] [--m-bin 43] [--m-rip 17] [--vref 0.9]
  python analyze_adc_top.py input_driver <psf_dir> [--n-bits 10] [--n-fft 128] [--m-bin 19] [--fs 50e6] [--vref 0.9]
  python analyze_adc_top.py erbw_jitter <psf_dir> [--n-bits 10] [--n-fft 256] [--fs 50e6] [--t-jitter-inj-fs 7000]
  python analyze_adc_top.py ti_sar <psf_dir> [--n-bits 10] [--n-fft 256] [--m-bin 97] [--fs-eff 200e6] [--vref 0.9]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

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
    crossings,
    extract_uniform_strobe,
    find_single,
    parse_psf_ascii,
)


def _find_tran(psf_dir: Path, name: str) -> Path:
    return find_single(psf_dir, [f"{name}.tran.tran", f"{name}.tran", f"*{name}*.tran*"])


def _fold_bin(k: int, n: int) -> int:
    k_mod = abs(int(k)) % n
    return n - k_mod if k_mod > n // 2 else k_mod


def _single_sided_pwr(x: np.ndarray) -> np.ndarray:
    x0 = np.asarray(x, dtype=float)
    n = len(x0)
    x0 = x0 - np.mean(x0)
    spec = np.fft.rfft(x0)
    pwr = (np.abs(spec) ** 2) / (n * n)
    pwr[1 : (n // 2 if n % 2 == 0 else (n + 1) // 2)] *= 2.0
    return pwr


def analyze_fft(
    psf_dir: Path,
    *,
    n_bits: int,
    n_fft: int,
    m_bin: int | None,
    fs: float | None,
) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, code_raw = extract_uniform_strobe(d["time"], d["CODE"])
    codes = np.rint(code_raw)
    if len(codes) < n_fft:
        raise RuntimeError(f"Expected >= {n_fft} strobed codes, got {len(codes)}")
    # Use the final n_fft uniform strobe samples (skips startup and 1-sample latch latency)
    win = codes[-n_fft:]
    res = coherent_fft_metrics(win, fs=fs, m_bin=m_bin)

    full_scale_peak = (2**n_bits) / 2.0
    res["amp_dbfs"] = 20.0 * math.log10(max(res["amp_peak"] / full_scale_peak, 1e-12))
    res["code_min"] = float(np.min(win))
    res["code_max"] = float(np.max(win))
    res["clipped"] = float((res["code_min"] <= 0.0) or (res["code_max"] >= (2**n_bits - 1)))
    return res


def analyze_ramp(psf_dir: Path, *, n_bits: int) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, code_raw, vip, vin = extract_uniform_strobe(d["time"], d["CODE"], d["VIP"], d["VIN"])
    codes = np.rint(code_raw).astype(int)
    vid = vip - vin

    n_codes = 2**n_bits
    counts = np.bincount(np.clip(codes, 0, n_codes - 1), minlength=n_codes)
    # Interior codes [1 .. n_codes - 2] (exclude clipped rails 0 and 2^N - 1)
    interior = counts[1 : n_codes - 1].astype(float)
    avg_hits = float(np.mean(interior))
    if avg_hits <= 0.0:
        raise RuntimeError("No interior ADC codes hit during ramp sweep")

    dnl = interior / avg_hits - 1.0
    inl = np.cumsum(dnl)
    # Remove endpoint linear slope from INL for standard endpoint-fit INL
    inl = inl - np.linspace(inl[0], inl[-1], len(inl))

    missing = int(np.sum(interior == 0))

    # Estimate usable full-scale differential range (first exit from code 0 to first hit of max)
    above_zero = np.where(codes > 0)[0]
    at_max = np.where(codes >= n_codes - 1)[0]
    # Note 1-sample latch offset between VIP/VIN and CODE
    idx_lo = max(int(above_zero[0]) - 1, 0) if len(above_zero) else 0
    idx_hi = max(int(at_max[0]) - 1, 0) if len(at_max) else len(vid) - 1
    usable_fs_diff = float(vid[idx_hi] - vid[idx_lo])

    return {
        "n_codes": float(n_codes),
        "avg_hits_per_code": avg_hits,
        "missing_codes": float(missing),
        "dnl_max_lsb": float(np.max(dnl)),
        "dnl_min_lsb": float(np.min(dnl)),
        "inl_max_lsb": float(np.max(inl)),
        "inl_min_lsb": float(np.min(inl)),
        "usable_vfs_diff_v": usable_fs_diff,
    }


def analyze_twotone(
    psf_dir: Path,
    *,
    n_bits: int,
    n_fft: int,
    m_bin1: int,
    m_bin2: int,
    fs: float | None,
) -> dict[str, float]:
    """Extract coherent two-tone IMD2, IMD3, SFDR, SNDR, and tone levels."""
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, code_raw = extract_uniform_strobe(d["time"], d["CODE"])
    codes = np.rint(code_raw)
    if len(codes) < n_fft:
        raise RuntimeError(f"Expected >= {n_fft} strobed codes, got {len(codes)}")
    win = codes[-n_fft:]

    tt = coherent_twotone_metrics(win, m_bin1=m_bin1, m_bin2=m_bin2, fs=fs)
    pwr = _single_sided_pwr(win)
    b1, b2 = sorted((int(m_bin1), int(m_bin2)))
    p1 = float(pwr[b1])
    p2 = float(pwr[b2])
    p_sig = p1 + p2
    p_nad = max(float(np.sum(pwr[1:])) - p_sig, 1e-30)
    sndr_db = 10.0 * math.log10(p_sig / p_nad)

    p_fs = 0.5 * ((2**n_bits) / 2.0) ** 2
    tone1_db = 10.0 * math.log10(max(p1, 1e-30) / p_fs)
    tone2_db = 10.0 * math.log10(max(p2, 1e-30) / p_fs)

    out: dict[str, float] = {
        "n_fft": tt["n_fft"],
        "m_bin1": tt["m_bin1"],
        "m_bin2": tt["m_bin2"],
        "tone1_db": tone1_db,
        "tone2_db": tone2_db,
        "tone_imbalance_db": tt["tone_imbalance_db"],
        "imd2_dbc": tt["im2_dbc"],
        "imd3_dbc": tt["imd3_dbc"],
        "im3_lo_dbc": tt["im3_lo_dbc"],
        "im3_hi_dbc": tt["im3_hi_dbc"],
        "im3_lo_bin": tt["im3_lo_bin"],
        "im3_hi_bin": tt["im3_hi_bin"],
        "sfdr_db": tt["sfdr_db"],
        "sndr_db": sndr_db,
        "enob_twotone": (sndr_db - 1.7609125905568124) / 6.020599913279624,
        "max_spur_bin": tt["max_spur_bin"],
        "code_min": float(np.min(win)),
        "code_max": float(np.max(win)),
        "clipped": float((np.min(win) <= 0.0) or (np.max(win) >= (2**n_bits - 1))),
    }
    if fs is not None:
        out["f1_hz"] = tt["f1_hz"]
        out["f2_hz"] = tt["f2_hz"]
    return out


def _extract_vref_wf_metrics(
    psf_path: Path, *, vref: float, vdd: float, lsb_v: float
) -> dict[str, float]:
    d = parse_psf_ascii(psf_path)
    t = d["time"]
    vr = d["VREF"]
    ck = d["CLKS"]
    ck_r = crossings(t, ck, 0.5 * vdd, "rising")
    ck_f = crossings(t, ck, 0.5 * vdd, "falling")
    t_start = ck_r[1] if len(ck_r) >= 2 else float(t[0] + 0.25 * (t[-1] - t[0]))
    m = t >= t_start
    droop = vref - vr[m]
    droop_pk = max(float(np.max(droop)), 0.0)
    overshoot_pk = max(float(np.max(-droop)), 0.0)

    # Measure settling error right before end of each conversion window (90% of Ts after CLKS fall)
    settle_errs: list[float] = []
    for idx_f, tf in enumerate(ck_f):
        if tf < t_start:
            continue
        next_r = next((tr for tr in ck_r if tr > tf), float(t[-1]))
        t_probe = tf + 0.5 * (next_r - tf)
        if t_probe <= float(t[-1]):
            settle_errs.append(abs(float(np.interp(t_probe, t, vr)) - vref))
    settle_err_v = max(settle_errs) if settle_errs else float(np.max(np.abs(droop)))
    return {
        "vref_droop_peak_mv": droop_pk * 1e3,
        "vref_overshoot_peak_mv": overshoot_pk * 1e3,
        "vref_settle_err_mv": settle_err_v * 1e3,
        "vref_settle_err_lsb": settle_err_v / lsb_v,
    }


def analyze_vref_droop(
    psf_dir: Path,
    *,
    n_bits: int,
    n_fft: int,
    m_bin: int,
    fs: float,
    vref: float,
    vdd: float,
) -> dict[str, Any]:
    """Compare ideal, undersized-decap, and properly-decoupled VREF performance."""
    lsb_v = (2.0 * vref) / (2**n_bits)
    cases: dict[str, dict[str, float]] = {}
    for label, name in (
        ("ideal", "tran_ideal"),
        ("undersized", "tran_small"),
        ("decoupled", "tran_sized"),
    ):
        d = parse_psf_ascii(_find_tran(psf_dir, name))
        _, code_raw = extract_uniform_strobe(d["time"], d["CODE"])
        win = np.rint(code_raw)[-n_fft:]
        m = coherent_fft_metrics(win, m_bin=m_bin, fs=fs)
        cases[label] = {
            "enob": m["enob"],
            "sndr_db": m["sndr_db"],
            "sfdr_db": m["sfdr_db"],
            "thd_db": m["thd_db"],
            "hd3_dbc": m["hd3_dbc"],
        }

    wf_small = _extract_vref_wf_metrics(
        _find_tran(psf_dir, "tran_wf_small"), vref=vref, vdd=vdd, lsb_v=lsb_v
    )
    wf_sized = _extract_vref_wf_metrics(
        _find_tran(psf_dir, "tran_wf_sized"), vref=vref, vdd=vdd, lsb_v=lsb_v
    )
    cases["undersized"].update(wf_small)
    cases["decoupled"].update(wf_sized)

    return {
        "lsb_mv": lsb_v * 1e3,
        "ideal": cases["ideal"],
        "undersized": cases["undersized"],
        "decoupled": cases["decoupled"],
        "enob_drop_undersized_bits": cases["ideal"]["enob"] - cases["undersized"]["enob"],
        "enob_recovery_bits": cases["decoupled"]["enob"] - cases["undersized"]["enob"],
        "sfdr_recovery_db": cases["decoupled"]["sfdr_db"] - cases["undersized"]["sfdr_db"],
    }


def analyze_noise_hist(
    psf_dir: Path,
    *,
    n_bits: int,
    n_fft: int,
    m_bin: int,
    n_hist: int,
    fs: float,
    vref: float,
    a_in_ratio: float,
    sigma_ktc_uv: float,
    sigma_cmp_uv: float,
) -> dict[str, Any]:
    """Analyze transient-noise coherent FFT vs analytical budget and grounded-input histogram."""
    lsb_v = (2.0 * vref) / (2**n_bits)

    d_fft = parse_psf_ascii(_find_tran(psf_dir, "tran_fft"))
    _, code_fft = extract_uniform_strobe(d_fft["time"], d_fft["CODE"])
    win_fft = np.rint(code_fft)[-n_fft:]
    m_fft = coherent_fft_metrics(win_fft, m_bin=m_bin, fs=fs)

    # Analytical SNR budget: SNR_theory = 10*log10(P_sig / (P_q + P_kTC + P_cmp))
    p_sig = 0.5 * (a_in_ratio * vref) ** 2
    p_q = (lsb_v**2) / 12.0
    p_ktc = (sigma_ktc_uv * 1e-6) ** 2
    p_cmp = (sigma_cmp_uv * 1e-6) ** 2
    p_tot_theory = p_q + p_ktc + p_cmp
    snr_theory_db = 10.0 * math.log10(p_sig / p_tot_theory)
    enob_theory = (snr_theory_db - 1.7609125905568124) / 6.020599913279624

    # Grounded-input code histogram
    d_hist = parse_psf_ascii(_find_tran(psf_dir, "tran_hist"))
    _, code_hist = extract_uniform_strobe(d_hist["time"], d_hist["CODE"])
    if len(code_hist) < n_hist:
        raise RuntimeError(f"Expected >= {n_hist} histogram samples, got {len(code_hist)}")
    c_hist = np.rint(code_hist)[-n_hist:]

    sigma_total_lsb = float(np.std(c_hist, ddof=1))
    sigma_in_lsb = math.sqrt(max(sigma_total_lsb**2 - (1.0 / 12.0), 0.0))
    mid_code = (2 ** (n_bits - 1)) - 0.5
    offset_lsb = float(np.mean(c_hist) - mid_code)

    return {
        "lsb_mv": lsb_v * 1e3,
        "fft": {
            "n_fft": float(n_fft),
            "snr_db": m_fft["snr_db"],
            "sndr_db": m_fft["sndr_db"],
            "enob": m_fft["enob"],
            "sfdr_db": m_fft["sfdr_db"],
            "snr_theory_db": snr_theory_db,
            "enob_theory": enob_theory,
            "snr_delta_vs_theory_db": m_fft["snr_db"] - snr_theory_db,
        },
        "histogram": {
            "n_hist": float(n_hist),
            "sigma_total_lsb": sigma_total_lsb,
            "sigma_total_uvrms": sigma_total_lsb * lsb_v * 1e6,
            "sigma_in_lsb": sigma_in_lsb,
            "sigma_in_uvrms": sigma_in_lsb * lsb_v * 1e6,
            "sigma_in_theory_uvrms": math.sqrt(p_ktc + p_cmp) * 1e6,
            "offset_lsb": offset_lsb,
            "offset_mv": offset_lsb * lsb_v * 1e3,
            "code_min": float(np.min(c_hist)),
            "code_max": float(np.max(c_hist)),
            "unique_codes": float(len(np.unique(c_hist))),
        },
    }


def analyze_psrr_cmrr(
    psf_dir: Path,
    *,
    n_bits: int,
    n_fft: int,
    m_bin: int,
    m_rip: int,
    fs: float,
    vref: float,
    v_rip_pp: float,
    dvcm: float,
) -> dict[str, Any]:
    """Extract dynamic PSRR, supply IM sidebands, and CMRR across Vcm sweep."""
    lsb_v = (2.0 * vref) / (2**n_bits)
    mid_code = (2 ** (n_bits - 1)) - 0.5

    # 1) PSRR run
    d_p = parse_psf_ascii(_find_tran(psf_dir, "tran_psrr"))
    _, code_p = extract_uniform_strobe(d_p["time"], d_p["CODE"])
    win_p = np.rint(code_p)[-n_fft:]
    m_p = coherent_fft_metrics(win_p, m_bin=m_bin, fs=fs)

    # Convert codes to input-referred differential voltage [V]
    v_code_p = (win_p - mid_code) * lsb_v
    pwr_v = _single_sided_pwr(v_code_p)
    p_sig_v = float(pwr_v[m_bin])
    p_rip_v = max(float(pwr_v[m_rip]), 1e-30)
    v_spur_peak = math.sqrt(2.0 * p_rip_v)
    v_rip_peak = 0.5 * v_rip_pp
    psrr_db = 20.0 * math.log10(v_rip_peak / max(v_spur_peak, 1e-15))
    f_rip_spur_dbfs = 10.0 * math.log10(p_rip_v / (0.5 * vref**2))

    im_lo_bin = _fold_bin(m_bin - m_rip, n_fft)
    im_hi_bin = _fold_bin(m_bin + m_rip, n_fft)
    im_lo_dbc = 10.0 * math.log10(max(float(pwr_v[im_lo_bin]), 1e-30) / max(p_sig_v, 1e-30))
    im_hi_dbc = 10.0 * math.log10(max(float(pwr_v[im_hi_bin]), 1e-30) / max(p_sig_v, 1e-30))

    # 2) CMRR sweep across Vcm = vcm_nom - dvcm, vcm_nom, vcm_nom + dvcm
    cm_res: dict[str, dict[str, float]] = {}
    for label, name in (
        ("vcm_lo", "tran_cm_lo"),
        ("vcm_nom", "tran_cm_nom"),
        ("vcm_hi", "tran_cm_hi"),
    ):
        d_c = parse_psf_ascii(_find_tran(psf_dir, name))
        _, code_c = extract_uniform_strobe(d_c["time"], d_c["CODE"])
        win_c = np.rint(code_c)[-n_fft:]
        m_c = coherent_fft_metrics(win_c, m_bin=m_bin, fs=fs)
        off_lsb = float(np.mean(win_c) - mid_code)
        cm_res[label] = {
            "offset_lsb": off_lsb,
            "offset_mv": off_lsb * lsb_v * 1e3,
            "enob": m_c["enob"],
            "sndr_db": m_c["sndr_db"],
            "sfdr_db": m_c["sfdr_db"],
        }

    offset_shift_lsb = cm_res["vcm_hi"]["offset_lsb"] - cm_res["vcm_lo"]["offset_lsb"]
    dv_os = abs(offset_shift_lsb) * lsb_v
    cmrr_db = 20.0 * math.log10((2.0 * dvcm) / max(dv_os, 1e-15))
    enob_cm_min = min(cm_res["vcm_lo"]["enob"], cm_res["vcm_nom"]["enob"], cm_res["vcm_hi"]["enob"])

    return {
        "psrr": {
            "v_rip_pp_mv": v_rip_pp * 1e3,
            "f_rip_hz": fs * m_rip / n_fft,
            "psrr_db": psrr_db,
            "f_rip_spur_mv": v_spur_peak * 1e3,
            "f_rip_spur_dbfs": f_rip_spur_dbfs,
            "im_lo_bin": float(im_lo_bin),
            "im_hi_bin": float(im_hi_bin),
            "im_lo_dbc": im_lo_dbc,
            "im_hi_dbc": im_hi_dbc,
            "enob_psrr": m_p["enob"],
            "sndr_psrr_db": m_p["sndr_db"],
            "sfdr_psrr_db": m_p["sfdr_db"],
        },
        "cmrr": {
            "dvcm_span_v": 2.0 * dvcm,
            "cmrr_db": cmrr_db,
            "offset_shift_lsb": offset_shift_lsb,
            "offset_shift_mv": offset_shift_lsb * lsb_v * 1e3,
            "enob_cm_drop_bits": cm_res["vcm_nom"]["enob"] - enob_cm_min,
            "vcm_lo": cm_res["vcm_lo"],
            "vcm_nom": cm_res["vcm_nom"],
            "vcm_hi": cm_res["vcm_hi"],
        },
    }


def analyze_input_driver(
    psf_dir: Path,
    *,
    n_bits: int,
    n_fft: int,
    m_bin: int,
    fs: float,
    vref: float,
) -> dict[str, Any]:
    """Compare undersized vs. properly sized input driver & AA RC settling/linearity."""
    lsb_v = (2.0 * vref) / (2**n_bits)
    out_cases: dict[str, dict[str, float]] = {}

    for label, name in (("undersized", "tran_under"), ("sized", "tran_sized")):
        d = parse_psf_ascii(_find_tran(psf_dir, name))
        _, code_raw, vip, vin, vip_ref, vin_ref = extract_uniform_strobe(
            d["time"], d["CODE"], d["VIP"], d["VIN"], d["VIP_REF"], d["VIN_REF"]
        )
        win_code = np.rint(code_raw)[-n_fft:]
        m = coherent_fft_metrics(win_code, m_bin=m_bin, fs=fs)

        # Acquisition-end kickback settling error right before CLKS falls
        v_err = ((vip - vin) - (vip_ref - vin_ref))[-n_fft:]
        err_pk = float(np.max(np.abs(v_err)))
        err_rms = float(np.sqrt(np.mean(v_err**2)))
        out_cases[label] = {
            "settle_err_peak_mv": err_pk * 1e3,
            "settle_err_peak_lsb": err_pk / lsb_v,
            "settle_err_rms_lsb": err_rms / lsb_v,
            "enob": m["enob"],
            "sndr_db": m["sndr_db"],
            "sfdr_db": m["sfdr_db"],
            "thd_db": m["thd_db"],
            "hd3_dbc": m["hd3_dbc"],
        }

    return {
        "lsb_mv": lsb_v * 1e3,
        "undersized": out_cases["undersized"],
        "sized": out_cases["sized"],
        "enob_recovery_bits": out_cases["sized"]["enob"] - out_cases["undersized"]["enob"],
        "sfdr_recovery_db": out_cases["sized"]["sfdr_db"] - out_cases["undersized"]["sfdr_db"],
        "settle_err_reduction_x": out_cases["undersized"]["settle_err_peak_lsb"]
        / max(out_cases["sized"]["settle_err_peak_lsb"], 1e-9),
    }


def analyze_erbw_jitter(
    psf_dir: Path,
    *,
    n_fft: int,
    fs: float,
    m_bins: list[int],
    t_jitter_inj_fs: float | None,
) -> dict[str, Any]:
    """Extract ENOB(f_in), SNR(f_in), ERBW, and inverted RMS aperture jitter."""
    points: list[dict[str, float]] = []
    for idx, m_true in enumerate(m_bins):
        d = parse_psf_ascii(_find_tran(psf_dir, f"tran_f{idx}"))
        _, code_raw = extract_uniform_strobe(d["time"], d["CODE"])
        win = np.rint(code_raw)[-n_fft:]
        m_fold = _fold_bin(m_true, n_fft)
        m = coherent_fft_metrics(win, m_bin=m_fold, fs=fs)
        f_in_hz = fs * m_true / n_fft
        points.append(
            {
                "m_bin_true": float(m_true),
                "m_bin_folded": float(m_fold),
                "fin_hz": f_in_hz,
                "fin_mhz": f_in_hz * 1e-6,
                "fin_over_fs": m_true / n_fft,
                "enob": m["enob"],
                "snr_db": m["snr_db"],
                "sndr_db": m["sndr_db"],
                "sfdr_db": m["sfdr_db"],
            }
        )

    # Effective Resolution Bandwidth (ERBW): 0.5-bit ENOB drop from f0
    enob_ref = points[0]["enob"]
    target_enob = enob_ref - 0.5
    erbw_hz = float("nan")
    for i in range(len(points) - 1):
        e0, e1 = points[i]["enob"], points[i + 1]["enob"]
        f0, f1 = points[i]["fin_hz"], points[i + 1]["fin_hz"]
        if e0 >= target_enob >= e1 and e0 != e1:
            frac = (e0 - target_enob) / (e0 - e1)
            erbw_hz = 10.0 ** (math.log10(f0) + frac * (math.log10(f1) - math.log10(f0)))
            break
    if math.isnan(erbw_hz):
        # Extrapolate using SNR_jit slope if 0.5-bit drop occurs beyond highest frequency
        erbw_hz = points[-1]["fin_hz"]

    # Invert RMS aperture jitter from lowest vs highest frequency SNR
    snr_lf = points[0]["snr_db"]
    snr_hf = points[-1]["snr_db"]
    f_lf = points[0]["fin_hz"]
    f_hf = points[-1]["fin_hz"]
    var_diff = max(10.0 ** (-snr_hf / 10.0) - 10.0 ** (-snr_lf / 10.0), 0.0)
    t_j_est_s = math.sqrt(var_diff) / (2.0 * math.pi * math.sqrt(max(f_hf**2 - f_lf**2, 1.0)))
    t_j_est_fs = t_j_est_s * 1e15

    res: dict[str, Any] = {
        "points": points,
        "enob_lf": enob_ref,
        "enob_hf": points[-1]["enob"],
        "enob_drop_total_bits": enob_ref - points[-1]["enob"],
        "erbw_hz": erbw_hz,
        "erbw_mhz": erbw_hz * 1e-6,
        "t_j_est_fs": t_j_est_fs,
        "t_j_est_ps": t_j_est_fs * 1e-3,
    }
    if t_jitter_inj_fs is not None and t_jitter_inj_fs > 0.0:
        res["t_jitter_inj_fs"] = t_jitter_inj_fs
        res["t_j_err_pct"] = ((t_j_est_fs - t_jitter_inj_fs) / t_jitter_inj_fs) * 100.0
    return res


def _ti_spur_summary(samples: np.ndarray, *, n_fft: int, m_bin: int, fs_eff: float) -> dict[str, float]:
    m = coherent_fft_metrics(samples, m_bin=m_bin, fs=fs_eff)
    pwr = _single_sided_pwr(samples)
    p_sig = max(float(pwr[m_bin]), 1e-30)

    b_fs4 = n_fft // 4
    b_fs2 = n_fft // 2
    spur_fs4 = 10.0 * math.log10(max(float(pwr[b_fs4]), 1e-30) / p_sig)
    spur_fs2 = 10.0 * math.log10(max(float(pwr[b_fs2]), 1e-30) / p_sig)
    offset_max = max(spur_fs4, spur_fs2)

    img_bins = sorted({_fold_bin(k * (n_fft // 4) + s * m_bin, n_fft) for k in (1, 2, 3) for s in (-1, 1)})
    img_spurs = [10.0 * math.log10(max(float(pwr[b]), 1e-30) / p_sig) for b in img_bins]
    image_max = max(img_spurs)

    return {
        "enob": m["enob"],
        "sndr_db": m["sndr_db"],
        "snr_db": m["snr_db"],
        "sfdr_db": m["sfdr_db"],
        "thd_db": m["thd_db"],
        "spur_fs4_dbc": spur_fs4,
        "spur_fs2_dbc": spur_fs2,
        "offset_spur_max_dbc": offset_max,
        "image_spur_max_dbc": image_max,
    }


def analyze_ti_sar(
    psf_dir: Path,
    *,
    n_bits: int,
    n_fft: int,
    m_bin: int,
    fs_eff: float,
    vref: float,
) -> dict[str, Any]:
    """Analyze 4-channel TI-SAR mismatch spurs and apply foreground O/G/skew calibration."""
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, c0, c1, c2, c3 = extract_uniform_strobe(
        d["time"], d["CODE0"], d["CODE1"], d["CODE2"], d["CODE3"]
    )
    n_ch = n_fft // 4
    if len(c0) < n_ch:
        raise RuntimeError(f"Expected >= {n_ch} strobed 4-channel frames, got {len(c0)}")

    ch = np.vstack([
        np.rint(c0[-n_ch:]),
        np.rint(c1[-n_ch:]),
        np.rint(c2[-n_ch:]),
        np.rint(c3[-n_ch:]),
    ])  # shape (4, n_ch)
    y_uncal = ch.T.ravel()  # chronological order [c0[0], c1[0], c2[0], c3[0], c0[1], ...]
    uncal = _ti_spur_summary(y_uncal, n_fft=n_fft, m_bin=m_bin, fs_eff=fs_eff)

    # Foreground per-channel coherent sine fit: y_k[r] = o_k + A_k * cos(w*(4r+k) + phi_k)
    f_in = fs_eff * m_bin / n_fft
    omega_s = 2.0 * math.pi * m_bin / n_fft
    o_est = np.zeros(4, dtype=float)
    a_est = np.zeros(4, dtype=float)
    phi_est = np.zeros(4, dtype=float)
    r_idx = np.arange(n_ch, dtype=float)

    for k in range(4):
        n_k = 4.0 * r_idx + k
        a_mat = np.column_stack([np.ones(n_ch), np.cos(omega_s * n_k), np.sin(omega_s * n_k)])
        coef, *_ = np.linalg.lstsq(a_mat, ch[k], rcond=None)
        o_est[k] = coef[0]
        a_est[k] = math.hypot(coef[1], coef[2])
        # a*cos(theta) + b*sin(theta) = A*cos(theta + phi) where phi = atan2(-b, a)
        phi_est[k] = math.atan2(-coef[2], coef[1])

    # Estimate relative mismatches referenced to Channel 0
    lsb_v = (2.0 * vref) / (2**n_bits)
    vos_est_lsb = o_est - o_est[0]
    dg_est_pct = ((a_est / a_est[0]) - 1.0) * 100.0
    dphi = np.angle(np.exp(1j * (phi_est - phi_est[0])))
    dt_est_s = dphi / (2.0 * math.pi * f_in)

    # Step 1: Offset + Gain calibration per channel
    ch_og = np.empty_like(ch)
    for k in range(4):
        ch_og[k] = (ch[k] - o_est[k]) * (a_est[0] / a_est[k]) + o_est[0]
    y_og = ch_og.T.ravel()

    # Step 2: 2nd-order bandlimited FFT-differentiator timing-skew calibration
    # Since y_og[n] = x(nT + dt_k) = x(nT) + dt_k*x'(nT) + 0.5*dt_k^2*x''(nT) + ...,
    # fixed-point inversion x = y_og - dt_k*x' - 0.5*dt_k^2*x'' cancels skew spurs!
    dt_seq = np.tile(dt_est_s, n_ch)
    freqs = np.fft.rfftfreq(n_fft, d=1.0 / fs_eff)
    jw = 1j * 2.0 * math.pi * freqs
    x_cal = y_og.copy()
    for _ in range(4):
        spec_x = np.fft.rfft(x_cal - np.mean(x_cal))
        dx = np.fft.irfft(jw * spec_x, n=n_fft)
        d2x = np.fft.irfft((jw**2) * spec_x, n=n_fft)
        x_cal = y_og - dt_seq * dx - 0.5 * (dt_seq**2) * d2x

    cal = _ti_spur_summary(x_cal, n_fft=n_fft, m_bin=m_bin, fs_eff=fs_eff)

    return {
        "fs_eff_hz": fs_eff,
        "fin_hz": f_in,
        "uncalibrated": uncal,
        "calibrated": cal,
        "sfdr_recovery_db": cal["sfdr_db"] - uncal["sfdr_db"],
        "sndr_recovery_db": cal["sndr_db"] - uncal["sndr_db"],
        "enob_recovery_bits": cal["enob"] - uncal["enob"],
        "estimated_mismatches_vs_ch0": {
            "vos_mv": [round(float(x * lsb_v * 1e3), 3) for x in vos_est_lsb],
            "dg_pct": [round(float(x), 4) for x in dg_est_pct],
            "dt_ps": [round(float(x * 1e12), 3) for x in dt_est_s],
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze full SAR ADC Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_fft = sub.add_parser("fft", help="Compute coherent ENOB/SNDR/SFDR/THD from tb_sar_adc_fft.scs")
    p_fft.add_argument("psf_dir", type=Path)
    p_fft.add_argument("--n-bits", type=int, default=10)
    p_fft.add_argument("--n-fft", type=int, default=128)
    p_fft.add_argument("--m-bin", type=int, default=None)
    p_fft.add_argument("--fs", type=float, default=None)

    p_ramp = sub.add_parser("ramp", help="Compute histogram DNL/INL & usable swing from tb_sar_adc_ramp_dnl.scs")
    p_ramp.add_argument("psf_dir", type=Path)
    p_ramp.add_argument("--n-bits", type=int, default=10)

    p_tt = sub.add_parser("twotone", help="Compute coherent two-tone IMD2/IMD3/SFDR/SNDR from tb_sar_adc_twotone_imd.scs")
    p_tt.add_argument("psf_dir", type=Path)
    p_tt.add_argument("--n-bits", type=int, default=10)
    p_tt.add_argument("--n-fft", type=int, default=256)
    p_tt.add_argument("--m-bin1", type=int, default=97)
    p_tt.add_argument("--m-bin2", type=int, default=107)
    p_tt.add_argument("--fs", type=float, default=50e6)

    p_vr = sub.add_parser("vref_droop", help="Analyze VREF droop & ENOB recovery from tb_sar_adc_vref_droop.scs")
    p_vr.add_argument("psf_dir", type=Path)
    p_vr.add_argument("--n-bits", type=int, default=10)
    p_vr.add_argument("--n-fft", type=int, default=128)
    p_vr.add_argument("--m-bin", type=int, default=19)
    p_vr.add_argument("--fs", type=float, default=50e6)
    p_vr.add_argument("--vref", type=float, default=0.9)
    p_vr.add_argument("--vdd", type=float, default=0.9)

    p_nh = sub.add_parser("noise_hist", help="Analyze trannoise FFT & grounded histogram from tb_sar_adc_trannoise_fft.scs")
    p_nh.add_argument("psf_dir", type=Path)
    p_nh.add_argument("--n-bits", type=int, default=10)
    p_nh.add_argument("--n-fft", type=int, default=256)
    p_nh.add_argument("--m-bin", type=int, default=43)
    p_nh.add_argument("--n-hist", type=int, default=512)
    p_nh.add_argument("--fs", type=float, default=50e6)
    p_nh.add_argument("--vref", type=float, default=0.9)
    p_nh.add_argument("--a-in-ratio", type=float, default=0.90)
    p_nh.add_argument("--sigma-ktc-uv", type=float, default=0.0)
    p_nh.add_argument("--sigma-cmp-uv", type=float, default=0.0)

    p_pc = sub.add_parser("psrr_cmrr", help="Analyze dynamic PSRR & input CMRR from tb_sar_adc_psrr_cmrr.scs")
    p_pc.add_argument("psf_dir", type=Path)
    p_pc.add_argument("--n-bits", type=int, default=10)
    p_pc.add_argument("--n-fft", type=int, default=256)
    p_pc.add_argument("--m-bin", type=int, default=43)
    p_pc.add_argument("--m-rip", type=int, default=17)
    p_pc.add_argument("--fs", type=float, default=50e6)
    p_pc.add_argument("--vref", type=float, default=0.9)
    p_pc.add_argument("--v-rip-pp", type=float, default=0.05)
    p_pc.add_argument("--dvcm", type=float, default=0.1)

    p_id = sub.add_parser("input_driver", help="Analyze input driver & AA RC settling from tb_sar_adc_input_driver.scs")
    p_id.add_argument("psf_dir", type=Path)
    p_id.add_argument("--n-bits", type=int, default=10)
    p_id.add_argument("--n-fft", type=int, default=128)
    p_id.add_argument("--m-bin", type=int, default=19)
    p_id.add_argument("--fs", type=float, default=50e6)
    p_id.add_argument("--vref", type=float, default=0.9)

    p_ej = sub.add_parser("erbw_jitter", help="Extract ERBW & aperture jitter from tb_sar_adc_erbw_jitter.scs")
    p_ej.add_argument("psf_dir", type=Path)
    p_ej.add_argument("--n-fft", type=int, default=256)
    p_ej.add_argument("--fs", type=float, default=50e6)
    p_ej.add_argument("--m-bins", type=str, default="7,59,113,233")
    p_ej.add_argument("--t-jitter-inj-fs", type=float, default=None)

    p_ti = sub.add_parser("ti_sar", help="Analyze 4-channel TI-SAR mismatch spurs & foreground calibration from tb_ti_sar_mismatch.scs")
    p_ti.add_argument("psf_dir", type=Path)
    p_ti.add_argument("--n-bits", type=int, default=10)
    p_ti.add_argument("--n-fft", type=int, default=256)
    p_ti.add_argument("--m-bin", type=int, default=97)
    p_ti.add_argument("--fs-eff", type=float, default=200e6)
    p_ti.add_argument("--vref", type=float, default=0.9)

    args = ap.parse_args(argv)
    if args.mode == "fft":
        res: Any = analyze_fft(
            args.psf_dir, n_bits=args.n_bits, n_fft=args.n_fft, m_bin=args.m_bin, fs=args.fs
        )
    elif args.mode == "ramp":
        res = analyze_ramp(args.psf_dir, n_bits=args.n_bits)
    elif args.mode == "twotone":
        res = analyze_twotone(
            args.psf_dir,
            n_bits=args.n_bits,
            n_fft=args.n_fft,
            m_bin1=args.m_bin1,
            m_bin2=args.m_bin2,
            fs=args.fs,
        )
    elif args.mode == "vref_droop":
        res = analyze_vref_droop(
            args.psf_dir,
            n_bits=args.n_bits,
            n_fft=args.n_fft,
            m_bin=args.m_bin,
            fs=args.fs,
            vref=args.vref,
            vdd=args.vdd,
        )
    elif args.mode == "noise_hist":
        res = analyze_noise_hist(
            args.psf_dir,
            n_bits=args.n_bits,
            n_fft=args.n_fft,
            m_bin=args.m_bin,
            n_hist=args.n_hist,
            fs=args.fs,
            vref=args.vref,
            a_in_ratio=args.a_in_ratio,
            sigma_ktc_uv=args.sigma_ktc_uv,
            sigma_cmp_uv=args.sigma_cmp_uv,
        )
    elif args.mode == "psrr_cmrr":
        res = analyze_psrr_cmrr(
            args.psf_dir,
            n_bits=args.n_bits,
            n_fft=args.n_fft,
            m_bin=args.m_bin,
            m_rip=args.m_rip,
            fs=args.fs,
            vref=args.vref,
            v_rip_pp=args.v_rip_pp,
            dvcm=args.dvcm,
        )
    elif args.mode == "input_driver":
        res = analyze_input_driver(
            args.psf_dir,
            n_bits=args.n_bits,
            n_fft=args.n_fft,
            m_bin=args.m_bin,
            fs=args.fs,
            vref=args.vref,
        )
    elif args.mode == "erbw_jitter":
        mb = [int(x.strip()) for x in args.m_bins.split(",") if x.strip()]
        res = analyze_erbw_jitter(
            args.psf_dir,
            n_fft=args.n_fft,
            fs=args.fs,
            m_bins=mb,
            t_jitter_inj_fs=args.t_jitter_inj_fs,
        )
    else:
        res = analyze_ti_sar(
            args.psf_dir,
            n_bits=args.n_bits,
            n_fft=args.n_fft,
            m_bin=args.m_bin,
            fs_eff=args.fs_eff,
            vref=args.vref,
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
