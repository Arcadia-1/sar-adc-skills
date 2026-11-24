#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from SerDes CTLE & VGA testbenches.

Usage:
  python analyze_ctle_vga.py ac_noise <psf_dir>
  python analyze_ctle_vga.py channel_ac <psf_dir>
  python analyze_ctle_vga.py eye <psf_dir> [--ui 100e-12] [--t-skip 5e-9]
  python analyze_ctle_vga.py offset_cal <psf_dir>
  python analyze_ctle_vga.py linearity <psf_dir> [--fs 16e9] [--m-bin 19] [--n-fft 128]
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
    eye_diagram_metrics,
    extract_uniform_strobe,
    find_single,
    parse_psf_ascii,
    sbr_cursor_metrics,
    trapz,
)


def analyze_ac_noise(psf_dir: Path) -> dict[str, float]:
    f_ac = find_single(psf_dir, ["ac.ac", "*.ac.ac", "*.ac"])
    dac = parse_psf_ascii(f_ac)
    freq = np.real(dac["freq"])
    h = (dac["OUTP"] - dac["OUTN"]) / np.maximum(np.abs(dac["INP"] - dac["INN"]), 1e-30)
    mag_db = 20.0 * np.log10(np.maximum(np.abs(h), 1e-30))

    dc_db = float(mag_db[0])
    idx_pk = int(np.argmax(mag_db))
    pk_db = float(mag_db[idx_pk])
    f_pk = float(freq[idx_pk])
    peaking_db = pk_db - dc_db

    # -3 dB bandwidth relative to DC gain (scanning downward after the peak)
    f3db = float("nan")
    ref = dc_db - 3.0
    for i in range(idx_pk, len(mag_db) - 1):
        if mag_db[i] >= ref > mag_db[i + 1]:
            frac = (ref - mag_db[i]) / (mag_db[i + 1] - mag_db[i])
            f3db = float(10.0 ** (math.log10(freq[i]) + frac * (math.log10(freq[i + 1]) - math.log10(freq[i]))))
            break

    f_n = find_single(psf_dir, ["noise.noise", "*.noise"])
    dn = parse_psf_ascii(f_n)
    fn = np.real(dn["freq"])
    vn = np.real(dn["out"])
    vout_rms = math.sqrt(max(trapz(vn**2, fn), 0.0))
    vn_1g = float(np.interp(math.log10(1e9), np.log10(fn), vn))

    return {
        "dc_gain_db": dc_db,
        "peak_gain_db": pk_db,
        "peaking_db": peaking_db,
        "f_peak_ghz": f_pk / 1e9,
        "f_3db_ghz": f3db / 1e9,
        "out_noise_mvrms": vout_rms * 1e3,
        "out_noise_1ghz_nv_rthz": vn_1g * 1e9,
    }


def analyze_channel_ac(psf_dir: Path) -> dict[str, float]:
    f_ac = find_single(psf_dir, ["ac.ac", "*.ac.ac", "*.ac"])
    dac = parse_psf_ascii(f_ac)
    freq = np.real(dac["freq"])
    log_f = np.log10(freq)

    v_tx = dac["CH_INP"] - dac["CH_INN"]
    v_rx = dac["RX_INP"] - dac["RX_INN"]
    v_eq = dac["OUTP"] - dac["OUTN"]

    h_ch_db = 20.0 * np.log10(np.maximum(np.abs(v_rx) / np.maximum(np.abs(v_tx), 1e-30), 1e-30))
    h_eq_db = 20.0 * np.log10(np.maximum(np.abs(v_eq) / np.maximum(np.abs(v_tx), 1e-30), 1e-30))

    def at(arr: np.ndarray, f_hz: float) -> float:
        return float(np.interp(math.log10(f_hz), log_f, arr))

    m_5g = (freq >= 10e6) & (freq <= 5e9)
    eq_dc = float(h_eq_db[0])
    eq_band = h_eq_db[m_5g]
    flatness_5g = float(np.max(eq_band) - np.min(eq_band))
    over_peak = float(np.max(h_eq_db) - eq_dc)

    f3db = float("nan")
    ref = eq_dc - 3.0
    idx_pk = int(np.argmax(h_eq_db))
    for i in range(idx_pk, len(h_eq_db) - 1):
        if h_eq_db[i] >= ref > h_eq_db[i + 1]:
            frac = (ref - h_eq_db[i]) / (h_eq_db[i + 1] - h_eq_db[i])
            f3db = float(10.0 ** (log_f[i] + frac * (log_f[i + 1] - log_f[i])))
            break

    return {
        "ch_loss_5ghz_db": at(h_ch_db, 5e9),
        "ch_loss_10ghz_db": at(h_ch_db, 10e9),
        "eq_dc_db": eq_dc,
        "eq_5ghz_db": at(h_eq_db, 5e9),
        "eq_10ghz_db": at(h_eq_db, 10e9),
        "eq_flatness_to_5ghz_db": flatness_5g,
        "eq_over_peaking_db": max(over_peak, 0.0),
        "eq_f3db_ghz": f3db / 1e9,
    }


def analyze_eye(psf_dir: Path, *, ui: float, t_skip: float) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_in = d["RX_INP"] - d["RX_INN"]
    v_out = d["OUTP"] - d["OUTN"]
    s_in = d["SRX_INP"] - d["SRX_INN"]
    s_out = d["SOUTP"] - d["SOUTN"]

    return {
        "before_ctle_eye": eye_diagram_metrics(t, v_in, ui_s=ui, t_skip=t_skip),
        "after_ctle_eye": eye_diagram_metrics(t, v_out, ui_s=ui, t_skip=t_skip),
        "before_ctle_sbr": sbr_cursor_metrics(t, s_in, ui_s=ui, t_base_end=25.0 * ui),
        "after_ctle_sbr": sbr_cursor_metrics(t, s_out, ui_s=ui, t_base_end=25.0 * ui),
    }


def analyze_offset_cal(psf_dir: Path) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_out = d["OUTP"] - d["OUTN"]
    v_cal = d["VOFF_CAL"]
    code = d["CODE_MON"]
    done = d["DONE"]

    v_init_mv = float(v_out[0] * 1e3)
    tail = t >= 0.9 * float(t[-1])
    v_final_mv = float(np.mean(v_out[tail]) * 1e3)
    converged = bool(float(done[-1]) > 0.5)
    idx_done = np.where(done > 0.5)[0]
    t_conv_ns = float(t[idx_done[0]] * 1e9) if len(idx_done) > 0 else float("nan")

    return {
        "converged": converged,
        "t_converge_ns": t_conv_ns,
        "initial_out_offset_mv": v_init_mv,
        "residual_out_offset_mv": v_final_mv,
        "final_cal_code": int(round(float(code[-1]))),
        "final_voff_cal_mv": float(v_cal[-1] * 1e3),
    }


def _vpp_to_dbm(vpp: float, r_diff: float = 100.0) -> float:
    p_w = (vpp * vpp) / (8.0 * r_diff)
    return 10.0 * math.log10(max(p_w, 1e-30) / 1e-3)


def analyze_linearity(
    psf_dir: Path, *, fs: float, m_bin: int, n_fft: int, nom_idx: int
) -> dict[str, object]:
    files = sorted(
        psf_dir.glob("tran_a*.tran"),
        key=lambda p: int(m.group(1)) if (m := re.search(r"tran_a(\d+)", p.name)) else 0,
    )
    if not files:
        files = [find_single(psf_dir, ["*.tran", "tran.tran*"])]

    points: list[dict[str, float]] = []
    for pf in files:
        d = parse_psf_ascii(pf)
        _, inp, inn, outp, outn = extract_uniform_strobe(
            d["time"], d["INP"], d["INN"], d["OUTP"], d["OUTN"]
        )
        vin = inp - inn
        vout = outp - outn
        if len(vout) >= n_fft:
            vin = vin[-n_fft:]
            vout = vout[-n_fft:]
        m_in = coherent_fft_metrics(vin, fs=fs, m_bin=m_bin)
        m_out = coherent_fft_metrics(vout, fs=fs, m_bin=m_bin)
        vin_pp = 2.0 * m_in["amp_peak"]
        vout_pp = 2.0 * m_out["amp_peak"]
        gain_db = 20.0 * math.log10(max(vout_pp, 1e-30) / max(vin_pp, 1e-30))
        points.append({
            "v_in_pp_v": vin_pp,
            "v_out_pp_v": vout_pp,
            "gain_db": gain_db,
            "hd2_dbc": m_out["hd2_dbc"],
            "hd3_dbc": m_out["hd3_dbc"],
            "thd_db": m_out["thd_db"],
            "sfdr_db": m_out["sfdr_db"],
        })

    points.sort(key=lambda r: r["v_in_pp_v"])
    gain_ss_db = points[0]["gain_db"]
    for pt in points:
        pt["compression_db"] = gain_ss_db - pt["gain_db"]

    in_p1db_vpp = float("nan")
    out_p1db_vpp = float("nan")
    compressed_1db = False
    for i in range(len(points) - 1):
        c0, c1 = points[i]["compression_db"], points[i + 1]["compression_db"]
        if c0 < 1.0 <= c1 and c1 > c0:
            frac = (1.0 - c0) / (c1 - c0)
            in_p1db_vpp = points[i]["v_in_pp_v"] + frac * (points[i + 1]["v_in_pp_v"] - points[i]["v_in_pp_v"])
            out_p1db_vpp = points[i]["v_out_pp_v"] + frac * (points[i + 1]["v_out_pp_v"] - points[i]["v_out_pp_v"])
            compressed_1db = True
            break

    ni = min(max(nom_idx, 0), len(points) - 1)
    nom = points[ni]
    return {
        "fin_ghz": (fs * m_bin / n_fft) / 1e9,
        "small_signal_gain_db": gain_ss_db,
        "compressed_1db": compressed_1db,
        "max_compression_db": max(p["compression_db"] for p in points),
        "in_p1db_vpp": in_p1db_vpp,
        "in_p1db_dbm_100ohm": _vpp_to_dbm(in_p1db_vpp) if compressed_1db else float("nan"),
        "out_p1db_vpp": out_p1db_vpp,
        "out_p1db_dbm_100ohm": _vpp_to_dbm(out_p1db_vpp) if compressed_1db else float("nan"),
        "nom_v_in_pp_v": nom["v_in_pp_v"],
        "nom_hd2_dbc": nom["hd2_dbc"],
        "nom_hd3_dbc": nom["hd3_dbc"],
        "nom_thd_db": nom["thd_db"],
        "nom_sfdr_db": nom["sfdr_db"],
        "sweep": points,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze SerDes CTLE & VGA Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_an = sub.add_parser("ac_noise")
    p_an.add_argument("psf_dir", type=Path)

    p_ca = sub.add_parser("channel_ac")
    p_ca.add_argument("psf_dir", type=Path)

    p_ey = sub.add_parser("eye")
    p_ey.add_argument("psf_dir", type=Path)
    p_ey.add_argument("--ui", type=float, default=100e-12)
    p_ey.add_argument("--t-skip", type=float, default=5.0e-9)

    p_oc = sub.add_parser("offset_cal")
    p_oc.add_argument("psf_dir", type=Path)

    p_lin = sub.add_parser("linearity")
    p_lin.add_argument("psf_dir", type=Path)
    p_lin.add_argument("--fs", type=float, default=16e9)
    p_lin.add_argument("--m-bin", type=int, default=19)
    p_lin.add_argument("--n-fft", type=int, default=128)
    p_lin.add_argument("--nom-idx", type=int, default=3)

    args = ap.parse_args(argv)
    if args.mode == "ac_noise":
        res: object = analyze_ac_noise(args.psf_dir)
    elif args.mode == "channel_ac":
        res = analyze_channel_ac(args.psf_dir)
    elif args.mode == "eye":
        res = analyze_eye(args.psf_dir, ui=args.ui, t_skip=args.t_skip)
    elif args.mode == "offset_cal":
        res = analyze_offset_cal(args.psf_dir)
    else:
        res = analyze_linearity(
            args.psf_dir, fs=args.fs, m_bin=args.m_bin, n_fft=args.n_fft, nom_idx=args.nom_idx
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
