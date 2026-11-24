#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from Pierce Crystal Oscillator (XO) testbenches.

Usage:
  python analyze_xo.py neg_r <psf_dir> [--f0 24e6] [--rm 40.0] [--min-margin 5.0]
  python analyze_xo.py startup <psf_dir> [--rm 40.0] [--q-scale 20.0] [--max-drive-uw 100.0]
  python analyze_xo.py pullability <psf_dir> [--c-loads 10,13,16,19,22] [--min-margin 5.0]
  python analyze_xo.py pss_pnoise <psf_dir> [--vdd 1.8] [--f-low 1e3] [--f-high 1e6]
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
    find_single,
    integrate_phase_noise_jitter,
    parse_psf_ascii,
    trapz,
)


def _find_optional(psf_dir: Path, patterns: list[str]) -> Path | None:
    try:
        return find_single(psf_dir, patterns)
    except FileNotFoundError:
        return None


def analyze_neg_r(
    psf_dir: Path,
    *,
    f0: float = 24.0e6,
    rm: float = 40.0,
    min_margin: float = 5.0,
) -> dict[str, object]:
    """Extract Pierce negative resistance R_neg(f0), startup margin, and active band."""
    ac_file = find_single(psf_dir, ["ac_negr.ac", "ac_negr.ac.ac", "*.ac.ac", "*.ac"])
    d = parse_psf_ascii(ac_file)
    freq = np.real(d["freq"])
    v_xi = d["XI"]
    v_xo = d["XO_P"] if "XO_P" in d else d["XO"]

    # ITEST (XO_P XI) injects +1 A into XI and extracts +1 A from XO_P:
    # Z_in(f) = (V(XI) - V(XO_P)) / 1 A
    z_in = v_xi - v_xo
    re_z = np.real(z_in)
    im_z = np.imag(z_in)
    r_neg = -re_z

    log_f = np.log10(freq)
    log_f0 = math.log10(f0)
    re_f0 = float(np.interp(log_f0, log_f, re_z))
    im_f0 = float(np.interp(log_f0, log_f, im_z))
    r_neg_f0 = -re_f0

    c_eff_pf = (
        float(-1.0 / (2.0 * math.pi * f0 * im_f0) * 1e12)
        if im_f0 < -1e-12
        else 0.0
    )
    margin_x = r_neg_f0 / max(rm, 1e-12)

    # Identify active frequency band where Re{Z_in(f)} < 0
    neg_mask = re_z < 0.0
    if np.any(neg_mask):
        idx = np.where(neg_mask)[0]
        f_min_mhz = float(freq[idx[0]] * 1e-6)
        f_max_mhz = float(freq[idx[-1]] * 1e-6)
        # Refine boundaries via linear zero-crossing interpolation when interior
        if idx[0] > 0:
            i0 = int(idx[0]) - 1
            frac = (0.0 - re_z[i0]) / (re_z[i0 + 1] - re_z[i0])
            f_min_mhz = float((freq[i0] + frac * (freq[i0 + 1] - freq[i0])) * 1e-6)
        if idx[-1] + 1 < len(freq):
            i1 = int(idx[-1])
            frac = (0.0 - re_z[i1]) / (re_z[i1 + 1] - re_z[i1])
            f_max_mhz = float((freq[i1] + frac * (freq[i1 + 1] - freq[i1])) * 1e-6)
        pk_idx = int(np.argmax(r_neg))
        r_neg_pk = float(r_neg[pk_idx])
        f_pk_mhz = float(freq[pk_idx] * 1e-6)
    else:
        f_min_mhz = 0.0
        f_max_mhz = 0.0
        r_neg_pk = float(np.max(r_neg))
        f_pk_mhz = float(freq[int(np.argmax(r_neg))] * 1e-6)

    res: dict[str, object] = {
        "f0_mhz": f0 * 1e-6,
        "rm_ohm": rm,
        "r_neg_at_f0_ohm": r_neg_f0,
        "re_zin_at_f0_ohm": re_f0,
        "im_zin_at_f0_ohm": im_f0,
        "c_eff_pf": c_eff_pf,
        "startup_margin_x": margin_x,
        "min_margin_spec_x": min_margin,
        "margin_pass": bool(margin_x >= min_margin),
        "neg_r_fmin_mhz": f_min_mhz,
        "neg_r_fmax_mhz": f_max_mhz,
        "r_neg_peak_ohm": r_neg_pk,
        "r_neg_peak_freq_mhz": f_pk_mhz,
    }

    dc_file = _find_optional(psf_dir, ["dcOp.dc", "*.dc"])
    if dc_file is not None:
        ddc = parse_psf_ascii(dc_file)
        if "VSUP:p" in ddc:
            res["i_dd_dc_ua"] = float(abs(ddc["VSUP:p"][0]) * 1e6)
    return res


def analyze_startup(
    psf_dir: Path,
    *,
    rm: float = 40.0,
    q_scale: float = 20.0,
    max_drive_uw: float = 100.0,
) -> dict[str, object]:
    """Extract XO startup envelope time, steady-state swings, crystal drive power, and duty cycle."""
    tr_file = find_single(
        psf_dir, ["tran_start.tran.tran", "tran_start.tran", "*.tran.tran", "*.tran"]
    )
    d = parse_psf_ascii(tr_file)
    t = d["time"]
    v_xi = d["XI"]
    v_xo = d["XO"]
    i_mot = d["V_IM:p"]
    i_sup = d["VSUP:p"]

    t_end = float(t[-1])
    ss_mask = t >= 0.80 * t_end
    t_ss = t[ss_mask]
    xi_ss = v_xi[ss_mask]
    xo_ss = v_xo[ss_mask]
    im_ss = i_mot[ss_mask]
    isup_ss = i_sup[ss_mask]

    v_xi_pp = float(np.max(xi_ss) - np.min(xi_ss))
    v_xo_pp = float(np.max(xo_ss) - np.min(xo_ss))
    v_xi_mid = 0.5 * (float(np.max(xi_ss)) + float(np.min(xi_ss)))
    v_xo_mid = 0.5 * (float(np.max(xo_ss)) + float(np.min(xo_ss)))

    # Motional current peak & crystal drive power P_xtal = 0.5 * I_m,pk^2 * R_m
    i_mot_pk = 0.5 * float(np.max(im_ss) - np.min(im_ss))
    p_xtal_uw = 0.5 * (i_mot_pk**2) * rm * 1e6
    dt_ss = max(float(t_ss[-1] - t_ss[0]), 1e-15)
    p_xtal_rms_uw = (trapz(im_ss**2, t_ss) / dt_ss) * rm * 1e6
    i_dd_ua = abs(trapz(isup_ss, t_ss) / dt_ss) * 1e6

    # Steady-state oscillation frequency from XI rising crossings
    t_r_xi = crossings(t_ss, xi_ss, v_xi_mid, direction="rising")
    if len(t_r_xi) >= 2:
        t_per = float(np.mean(np.diff(t_r_xi)))
        f_osc_mhz = (1.0 / t_per) * 1e-6
    else:
        t_per = 0.0
        f_osc_mhz = 0.0

    # Duty cycle of sustaining output XO around mid-swing
    t_r_xo = crossings(t_ss, xo_ss, v_xo_mid, direction="rising")
    t_f_xo = crossings(t_ss, xo_ss, v_xo_mid, direction="falling")
    duties: list[float] = []
    for k in range(len(t_r_xo) - 1):
        tr0, tr1 = t_r_xo[k], t_r_xo[k + 1]
        tf_in = [tf for tf in t_f_xo if tr0 < tf < tr1]
        if tf_in and tr1 > tr0:
            duties.append(100.0 * (tf_in[0] - tr0) / (tr1 - tr0))
    duty_pct = float(np.mean(duties)) if duties else 50.0

    # Envelope startup time to 90% of steady-state V_XI,pp using multi-cycle windows
    bin_w = max(5.0 * t_per, t_end / 120.0) if t_per > 0.0 else t_end / 100.0
    n_bins = max(int(t_end / bin_w), 10)
    edges = np.linspace(float(t[0]), t_end, n_bins + 1)
    env_t: list[float] = []
    env_pp: list[float] = []
    for b in range(n_bins):
        bm = (t >= edges[b]) & (t <= edges[b + 1])
        if np.sum(bm) >= 2:
            env_t.append(0.5 * (float(edges[b]) + float(edges[b + 1])))
            env_pp.append(float(np.max(v_xi[bm]) - np.min(v_xi[bm])))

    env_t_arr = np.asarray(env_t, dtype=float)
    env_pp_arr = np.asarray(env_pp, dtype=float)
    target_90 = 0.90 * v_xi_pp
    t_start_90_sim_s = t_end
    if v_xi_pp > 0.05 and len(env_pp_arr) >= 2:
        hit = np.where(env_pp_arr >= target_90)[0]
        if len(hit) > 0:
            idx90 = int(hit[0])
            if idx90 == 0:
                t_start_90_sim_s = float(env_t_arr[0])
            else:
                e0, e1 = float(env_pp_arr[idx90 - 1]), float(env_pp_arr[idx90])
                frac = (target_90 - e0) / max(e1 - e0, 1e-18)
                frac = min(max(frac, 0.0), 1.0)
                t_start_90_sim_s = float(
                    env_t_arr[idx90 - 1] + frac * (env_t_arr[idx90] - env_t_arr[idx90 - 1])
                )

    oscillating = bool(v_xi_pp > 0.1 and f_osc_mhz > 0.0)
    t_start_sim_us = t_start_90_sim_s * 1e6
    return {
        "oscillating": oscillating,
        "f_osc_mhz": f_osc_mhz,
        "v_xi_pp_v": v_xi_pp,
        "v_xo_pp_v": v_xo_pp,
        "i_mot_pk_ma": i_mot_pk * 1e3,
        "p_xtal_uw": p_xtal_uw,
        "p_xtal_rms_uw": p_xtal_rms_uw,
        "max_drive_spec_uw": max_drive_uw,
        "drive_level_pass": bool(oscillating and p_xtal_uw <= max_drive_uw),
        "duty_cycle_pct": duty_pct,
        "q_scale": q_scale,
        "t_startup_90pct_sim_us": t_start_sim_us,
        "t_startup_90pct_us": t_start_sim_us * q_scale,
        "i_dd_ua": i_dd_ua,
    }


def _ac_code_key(path: Path) -> int:
    m = re.search(r"ac_c(\d+)", path.name)
    return int(m.group(1)) if m else 0


def analyze_pullability(
    psf_dir: Path,
    *,
    c_loads_pf: list[float] | None = None,
    min_margin: float = 5.0,
) -> dict[str, object]:
    """Extract per-code exact oscillation frequency, ppm pull range, and worst startup margin."""
    ac_files = sorted(psf_dir.glob("ac_c*.ac*"), key=_ac_code_key)
    # Deduplicate if both .ac and .ac.ac matched (prefer exact match)
    dedup: dict[int, Path] = {}
    for p in ac_files:
        m = re.search(r"ac_c(\d+)", p.name)
        if m:
            idx = int(m.group(1))
            if idx not in dedup:
                dedup[idx] = p
    ordered = [dedup[k] for k in sorted(dedup)]
    if len(ordered) < 2:
        raise FileNotFoundError(
            f"Expected >= 2 ac_c*.ac files in {psf_dir}, found {[p.name for p in ordered]}"
        )

    if c_loads_pf is None or len(c_loads_pf) != len(ordered):
        default_cl = [10.0, 13.0, 16.0, 19.0, 22.0]
        c_loads_pf = default_cl[: len(ordered)] if len(ordered) <= len(default_cl) else [
            float(i) for i in range(len(ordered))
        ]

    rows: list[dict[str, float | int]] = []
    for code_idx, (pf, cl_pin) in enumerate(zip(ordered, c_loads_pf)):
        d = parse_psf_ascii(pf)
        freq = np.real(d["freq"])
        i_m = d["VTEST:p"]
        v_xi = d["XI"]
        v_xo = d["XO_P"] if "XO_P" in d else d["XO"]

        # KVL around motional loop with VTEST(XI, M1, mag=1):
        # Z_loop = -1 / I(VTEST:p) = Z_m + Z_in, Z_in = (V(XI) - V(XO_P)) / (-I(VTEST:p))
        z_loop = -1.0 / i_m
        z_in = (v_xi - v_xo) / (-i_m)
        z_m = z_loop - z_in

        im_loop = np.imag(z_loop)
        # Find upward zero crossing Im{Z_loop(f_osc)} = 0
        f_osc = float("nan")
        for i in range(len(im_loop) - 1):
            if im_loop[i] <= 0.0 < im_loop[i + 1]:
                frac = (0.0 - im_loop[i]) / (im_loop[i + 1] - im_loop[i])
                f_osc = float(freq[i] + frac * (freq[i + 1] - freq[i]))
                break
        if math.isnan(f_osc):
            raise RuntimeError(
                f"No Im{{Z_loop}}=0 resonance crossing found in {pf.name} "
                f"across [{freq[0]*1e-6:.4f}, {freq[-1]*1e-6:.4f}] MHz"
            )

        r_neg_osc = float(np.interp(f_osc, freq, -np.real(z_in)))
        rm_osc = float(np.interp(f_osc, freq, np.real(z_m)))
        margin_x = r_neg_osc / max(rm_osc, 1e-12)
        rows.append(
            {
                "code": code_idx,
                "c_load_pin_pf": float(cl_pin),
                "c_l_eff_pf": 0.5 * float(cl_pin),
                "f_osc_mhz": f_osc * 1e-6,
                "r_neg_ohm": r_neg_osc,
                "rm_ohm": rm_osc,
                "startup_margin_x": margin_x,
            }
        )

    mid_idx = len(rows) // 2
    f_nom_mhz = float(rows[mid_idx]["f_osc_mhz"])
    for r in rows:
        r["df_ppm"] = (float(r["f_osc_mhz"]) - f_nom_mhz) / f_nom_mhz * 1e6

    freqs = np.array([float(r["f_osc_mhz"]) for r in rows], dtype=float)
    cl_eff = np.array([float(r["c_l_eff_pf"]) for r in rows], dtype=float)
    df_arr = np.array([float(r["df_ppm"]) for r in rows], dtype=float)
    margins = np.array([float(r["startup_margin_x"]) for r in rows], dtype=float)

    f_min = float(np.min(freqs))
    f_max = float(np.max(freqs))
    pull_range_ppm = (f_max - f_min) / f_nom_mhz * 1e6
    steps_ppm = np.abs(np.diff(df_arr))
    monotonic = bool(np.all(np.diff(freqs) < 0.0) or np.all(np.diff(freqs) > 0.0))
    slope_ppm_per_pf = float(np.polyfit(cl_eff, df_arr, 1)[0])
    worst_margin = float(np.min(margins))

    return {
        "n_codes": int(len(rows)),
        "f_nom_mhz": f_nom_mhz,
        "f_min_mhz": f_min,
        "f_max_mhz": f_max,
        "pull_range_ppm": pull_range_ppm,
        "pull_half_range_ppm": 0.5 * pull_range_ppm,
        "trim_step_ppm": float(np.mean(steps_ppm)),
        "pullability_ppm_per_pf": slope_ppm_per_pf,
        "monotonic": monotonic,
        "worst_startup_margin_x": worst_margin,
        "min_margin_spec_x": min_margin,
        "margin_pass": bool(worst_margin >= min_margin),
        "codes": rows,
    }


def analyze_pss_pnoise(
    psf_dir: Path,
    *,
    vdd: float = 1.8,
    f_low: float = 1.0e3,
    f_high: float = 1.0e6,
) -> dict[str, object]:
    """Extract XO carrier frequency, SSB PM phase noise L(df), and integrated RMS jitter [fs]."""
    pss_td = find_single(psf_dir, ["pss.td.pss", "*.td.pss"])
    dp = parse_psf_ascii(pss_td)
    t = dp["time"]
    period = float(t[-1] - t[0])
    if period <= 0.0:
        raise RuntimeError(f"Invalid PSS period: {period}")
    f0 = 1.0 / period

    v_xo_pp = float(np.max(dp["XO"]) - np.min(dp["XO"]))
    v_xi_pp = float(np.max(dp["XI"]) - np.min(dp["XI"])) if "XI" in dp else 0.0
    i_dd_a = abs(trapz(dp["VSUP:p"], t) / period)
    p_dc_uw = i_dd_a * vdd * 1e6

    # Fundamental peak amplitude of XO from pss.fd.pss
    pss_fd = find_single(psf_dir, ["pss.fd.pss", "*.fd.pss"])
    dfd = parse_psf_ascii(pss_fd)
    fd_freq = np.real(dfd["freq"])
    fund_idx = int(np.argmin(np.abs(fd_freq - f0)))
    v_carr_pk = float(np.abs(dfd["XO"][fund_idx]))
    if v_carr_pk <= 1e-9:
        v_carr_pk = 0.5 * v_xo_pp

    pn_file = find_single(psf_dir, ["*pm*.pnoise", "pnoise*.pnoise", "*.pnoise"])
    dn = parse_psf_ascii(pn_file)
    freq_key = "relative frequency" if "relative frequency" in dn else "freq"
    freq = np.real(dn[freq_key])
    if "out" in dn:
        val = np.real(dn["out"])
    else:
        sig_key = next(k for k in dn if k != freq_key)
        val = np.real(dn[sig_key])

    # IEEE Std 1139 normalization of Spectre PM pnoise V_rms/sqrt(Hz) to dBc/Hz
    v_carr_rms = v_carr_pk / math.sqrt(2.0)
    if np.all(val > 0.0):
        l_dbc = 20.0 * np.log10(np.maximum(val / v_carr_rms, 1e-30))
    else:
        l_dbc = val

    log_f = np.log10(freq)

    def l_at(df_hz: float) -> float:
        return float(np.interp(math.log10(df_hz), log_f, l_dbc))

    jit = integrate_phase_noise_jitter(freq, l_dbc, f0, f_low_hz=f_low, f_high_hz=f_high)

    return {
        "f_0_mhz": f0 * 1e-6,
        "v_xo_pp_v": v_xo_pp,
        "v_xi_pp_v": v_xi_pp,
        "i_dd_ua": i_dd_a * 1e6,
        "p_dc_uw": p_dc_uw,
        "pn_100hz_dbc": l_at(100.0),
        "pn_1khz_dbc": l_at(1.0e3),
        "pn_10khz_dbc": l_at(10.0e3),
        "pn_100khz_dbc": l_at(100.0e3),
        "pn_1mhz_dbc": l_at(1.0e6),
        "j_rms_fs": jit["rms_jitter_fs"],
        "rms_phase_mdeg": jit["rms_phase_deg"] * 1e3,
        "jitter_band_hz": [f_low, f_high],
        "pnoise_file": pn_file.name,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze Pierce Crystal Oscillator Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_nr = sub.add_parser("neg_r", help="Extract R_neg(f0), startup margin & active band from tb_xo_neg_resistance.scs")
    p_nr.add_argument("psf_dir", type=Path)
    p_nr.add_argument("--f0", type=float, default=24.0e6)
    p_nr.add_argument("--rm", type=float, default=40.0)
    p_nr.add_argument("--min-margin", type=float, default=5.0)

    p_st = sub.add_parser("startup", help="Extract startup time, swing & crystal drive level from tb_xo_startup_drive.scs")
    p_st.add_argument("psf_dir", type=Path)
    p_st.add_argument("--rm", type=float, default=40.0)
    p_st.add_argument("--q-scale", type=float, default=20.0)
    p_st.add_argument("--max-drive-uw", type=float, default=100.0)

    p_pl = sub.add_parser("pullability", help="Extract CL trim pull range & worst margin from tb_xo_pullability_cload.scs")
    p_pl.add_argument("psf_dir", type=Path)
    p_pl.add_argument("--c-loads", type=str, default="10,13,16,19,22")
    p_pl.add_argument("--min-margin", type=float, default=5.0)

    p_pn = sub.add_parser("pss_pnoise", help="Extract f0, SSB phase noise & RMS jitter from tb_xo_pss_pnoise.scs")
    p_pn.add_argument("psf_dir", type=Path)
    p_pn.add_argument("--vdd", type=float, default=1.8)
    p_pn.add_argument("--f-low", type=float, default=1.0e3)
    p_pn.add_argument("--f-high", type=float, default=1.0e6)

    args = ap.parse_args(argv)
    if args.mode == "neg_r":
        res = analyze_neg_r(args.psf_dir, f0=args.f0, rm=args.rm, min_margin=args.min_margin)
    elif args.mode == "startup":
        res = analyze_startup(
            args.psf_dir, rm=args.rm, q_scale=args.q_scale, max_drive_uw=args.max_drive_uw
        )
    elif args.mode == "pullability":
        cl_list = [float(x) for x in args.c_loads.split(",") if x.strip()]
        res = analyze_pullability(args.psf_dir, c_loads_pf=cl_list, min_margin=args.min_margin)
    else:
        res = analyze_pss_pnoise(
            args.psf_dir, vdd=args.vdd, f_low=args.f_low, f_high=args.f_high
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
