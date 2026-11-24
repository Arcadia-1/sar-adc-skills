#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from SerDes TX & FFE testbenches.

Usage:
  python analyze_tx_ffe.py s11 <psf_dir>
  python analyze_tx_ffe.py dc_term <psf_dir> [--r-target 50.0]
  python analyze_tx_ffe.py eye <psf_dir> [--ui 100e-12] [--t-skip 5e-9]
  python analyze_tx_ffe.py cm_sndr <psf_dir> [--ui 100e-12] [--t-skip 3e-9] [--n-p 12] [--osr 16]
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
    eye_diagram_metrics,
    find_single,
    mixed_mode_s_params,
    parse_psf_ascii,
    sbr_cursor_metrics,
)


def analyze_s11(psf_dir: Path) -> dict[str, float]:
    f = find_single(psf_dir, ["sp.sp", "*.sp.sp", "*.sp"])
    d = parse_psf_ascii(f)
    freq = np.real(d["freq"])
    log_f = np.log10(freq)
    mm = mixed_mode_s_params(d, in_p=1, in_n=2, out_p=None, out_n=None)
    sdd11_db = 20.0 * np.log10(np.maximum(np.abs(mm["sdd11"]), 1e-30))

    def at(f_hz: float) -> float:
        return float(np.interp(math.log10(f_hz), log_f, sdd11_db))

    m_5g = freq <= 5e9
    m_10g = freq <= 10e9
    return {
        "sdd11_dc_db": float(sdd11_db[0]),
        "sdd11_1ghz_db": at(1e9),
        "sdd11_5ghz_db": at(5e9),
        "sdd11_10ghz_db": at(10e9),
        "sdd11_worst_to_5ghz_db": float(np.max(sdd11_db[m_5g])),
        "sdd11_worst_to_10ghz_db": float(np.max(sdd11_db[m_10g])),
    }


def analyze_eye(psf_dir: Path, *, ui: float, t_skip: float) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_tx = d["TXP"] - d["TXN"]
    v_rx = d["RXP"] - d["RXN"]
    v_sbr = d["SRXP"] - d["SRXN"]

    return {
        "tx_swing_pp_mv": float((np.max(v_tx[t >= t_skip]) - np.min(v_tx[t >= t_skip])) * 1e3),
        "rx_eye": eye_diagram_metrics(t, v_rx, ui_s=ui, t_skip=t_skip),
        "rx_sbr": sbr_cursor_metrics(t, v_sbr, ui_s=ui, t_base_end=25.0 * ui),
    }


def analyze_dc_term(psf_dir: Path, *, r_target: float) -> dict[str, float]:
    f = find_single(psf_dir, ["dc_term.dc", "*term*.dc", "*.dc"])
    d = parse_psf_ascii(f)
    v = d["OUTP"]
    # Current leaving VPRB_P into OUTP is -VPRB_P:p (Spectre passive sign convention)
    i_in = -d["VPRB_P:p"]
    dv = np.diff(v)
    di = np.diff(i_in)
    r_inc = np.abs(dv / np.where(np.abs(di) > 1e-15, di, np.nan))
    r_inc = r_inc[np.isfinite(r_inc)]
    r_med = float(np.median(r_inc))
    r_min = float(np.min(r_inc))
    r_max = float(np.max(r_inc))
    return {
        "r_target_ohm": r_target,
        "r_median_ohm": r_med,
        "r_min_ohm": r_min,
        "r_max_ohm": r_max,
        "r_err_max_pct": float(max(abs(r_min - r_target), abs(r_max - r_target)) / r_target * 100.0),
        "r_flatness_pct": float((r_max - r_min) / max(r_med, 1e-9) * 100.0),
    }


def analyze_cm_sndr(
    psf_dir: Path, *, ui: float, t_skip: float, n_p: int, osr: int, vdd: float
) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    outp = d["OUTP"]
    outn = d["OUTN"]
    bit_mon = d["BIT_MON"]
    clk_tx = d["CLK_TX"]

    v_diff = outp - outn
    v_cm = 0.5 * (outp + outn)

    m = t >= t_skip
    tm = t[m]
    vcm_m = v_cm[m]
    vdiff_m = v_diff[m]
    outp_m = outp[m]
    outn_m = outn[m]

    # 1. AC common-mode noise
    vcm_dc = float(np.mean(vcm_m))
    vcm_ac = vcm_m - vcm_dc
    vcm_ac_rms_mv = float(np.sqrt(np.mean(vcm_ac**2)) * 1e3)
    vcm_ac_pp_mv = float((np.max(vcm_ac) - np.min(vcm_ac)) * 1e3)
    swing_pp = float(np.max(vdiff_m) - np.min(vdiff_m))

    # 2. Intra-pair P/N timing skew (OUTP midpoint crossing minus opposite OUTN crossing)
    mid_p = 0.5 * (float(np.max(outp_m)) + float(np.min(outp_m)))
    mid_n = 0.5 * (float(np.max(outn_m)) + float(np.min(outn_m)))
    p_rise = np.asarray(crossings(tm, outp_m, mid_p, direction="rising"), dtype=float)
    p_fall = np.asarray(crossings(tm, outp_m, mid_p, direction="falling"), dtype=float)
    n_rise = np.asarray(crossings(tm, outn_m, mid_n, direction="rising"), dtype=float)
    n_fall = np.asarray(crossings(tm, outn_m, mid_n, direction="falling"), dtype=float)

    skews_s: list[float] = []
    for p_arr, n_arr in ((p_rise, n_fall), (p_fall, n_rise)):
        if len(p_arr) == 0 or len(n_arr) == 0:
            continue
        for tp in p_arr:
            idx = int(np.argmin(np.abs(n_arr - tp)))
            dt = float(tp - n_arr[idx])
            if abs(dt) < 0.35 * ui:
                skews_s.append(dt)
    pn_skew_ps = float(np.median(skews_s) * 1e12) if skews_s else float("nan")

    # 3. 20-80% differential rise & fall times across full transitions
    clk_edges = np.asarray(crossings(t, clk_tx, 0.5 * vdd, direction="rising"), dtype=float)
    tr_list: list[float] = []
    tf_list: list[float] = []
    for tc in clk_edges:
        if tc < t_skip + ui or tc + 0.90 * ui >= float(t[-1]):
            continue
        v_pre = float(np.interp(tc - 0.15 * ui, t, v_diff))
        v_post = float(np.interp(tc + 0.80 * ui, t, v_diff))
        dv = v_post - v_pre
        if abs(dv) < 0.45 * swing_pp:
            continue
        mw = (t >= tc - 0.05 * ui) & (t <= tc + 0.85 * ui)
        tw = t[mw]
        vw = v_diff[mw]
        if len(tw) < 4:
            continue
        lvl20 = v_pre + 0.20 * dv
        lvl80 = v_pre + 0.80 * dv
        if dv > 0.0:
            c20 = crossings(tw, vw, lvl20, direction="rising")
            c80 = crossings(tw, vw, lvl80, direction="rising")
            if c20 and c80 and c80[0] > c20[0]:
                tr_list.append(c80[0] - c20[0])
        else:
            c20 = crossings(tw, vw, lvl20, direction="falling")
            c80 = crossings(tw, vw, lvl80, direction="falling")
            if c20 and c80 and c80[0] > c20[0]:
                tf_list.append(c80[0] - c20[0])

    t_r_ps = float(np.median(tr_list) * 1e12) if tr_list else float("nan")
    t_f_ps = float(np.median(tf_list) * 1e12) if tf_list else float("nan")

    # 4. IEEE 802.3 Clause 93/120 Linear-Fit Pulse Response p(k) & TX SNDR
    # Sample PRBS-7 bits at every CLK_TX rising edge (race-free 0.5-UI shifted from PRBS gen)
    x_all = np.where(np.interp(clk_edges, t, bit_mon) >= 0.5, 1.0, -1.0)
    # Locate first UI index safely after t_skip with n_p history available
    d_pre = 3
    idx_start = int(np.searchsorted(clk_edges, t_skip))
    idx_start = max(idx_start, n_p + 2)
    idx_end = len(clk_edges) - 2
    n_fit = idx_end - idx_start
    if n_fit < 64:
        raise RuntimeError(f"Insufficient UIs ({n_fit}) after t_skip for linear-fit SNDR")

    # Oversample v_diff at `osr` uniform sub-UI phases per UI
    sub_ph = (np.arange(osr, dtype=float) / float(osr)) * ui
    t_grid = clk_edges[idx_start:idx_end, None] + sub_ph[None, :]
    Y = np.interp(t_grid, t, v_diff)  # shape (n_fit, osr)

    # Auto-align integer UI latency lag_0 via correlation at mid-UI
    y_mid = Y[:, osr // 2] - np.mean(Y[:, osr // 2])
    best_corr = -1.0
    lag_0 = 1
    for lag in range(-2, 7):
        s_i = idx_start - lag
        e_i = idx_end - lag
        if s_i < 0 or e_i > len(x_all):
            continue
        corr = abs(float(np.dot(x_all[s_i:e_i], y_mid)))
        if corr > best_corr:
            best_corr = corr
            lag_0 = lag

    # Ensure indexing bounds for taps j = 0..n_p-1 centered at lag_0 with d_pre pre-cursors
    max_shift = lag_0 - d_pre + (n_p - 1)
    min_shift = lag_0 - d_pre
    trim_lo = max(0, max_shift - idx_start)
    trim_hi = max(0, idx_end - min_shift - len(x_all))
    if trim_lo > 0 or trim_hi > 0:
        idx_start += trim_lo
        idx_end -= trim_hi
        Y = Y[trim_lo : len(Y) - trim_hi if trim_hi > 0 else len(Y), :]
        n_fit = idx_end - idx_start

    cols = [x_all[idx_start - (lag_0 - d_pre + j) : idx_end - (lag_0 - d_pre + j)] for j in range(n_p)]
    cols.append(np.ones(n_fit, dtype=float))
    X = np.column_stack(cols)  # shape (n_fit, n_p + 1)

    P_mat, _, _, _ = np.linalg.lstsq(X, Y, rcond=None)
    Y_fit = X @ P_mat
    E = Y - Y_fit

    # Linear-fit pulse p(t) sampled at UI/osr
    p_pulse = P_mat[:n_p, :].reshape(-1)
    pk_idx = int(np.argmax(np.abs(p_pulse)))
    if p_pulse[pk_idx] < 0.0:
        p_pulse = -p_pulse
    p_max_v = float(p_pulse[pk_idx])
    e_rms_v = float(np.sqrt(np.mean(E**2)))
    sndr_tx_db = 10.0 * math.log10((p_max_v**2) / max(e_rms_v**2, 1e-30))

    p_cursors_mv: dict[str, float] = {}
    for k in range(-2, 4):
        idx_k = pk_idx + k * osr
        p_cursors_mv[f"p{k}"] = float(p_pulse[idx_k] * 1e3) if 0 <= idx_k < len(p_pulse) else 0.0

    return {
        "n_ui_fit": int(n_fit),
        "n_p_taps": int(n_p),
        "osr": int(osr),
        "tx_swing_pp_mv": float(swing_pp * 1e3),
        "t_r_ps": t_r_ps,
        "t_f_ps": t_f_ps,
        "pn_skew_ps": pn_skew_ps,
        "pn_skew_abs_ps": abs(pn_skew_ps) if math.isfinite(pn_skew_ps) else float("nan"),
        "vcm_dc_mv": float(vcm_dc * 1e3),
        "vcm_ac_rms_mv": vcm_ac_rms_mv,
        "vcm_ac_pp_mv": vcm_ac_pp_mv,
        "p_max_mv": float(p_max_v * 1e3),
        "e_rms_mv": float(e_rms_v * 1e3),
        "sndr_tx_db": float(sndr_tx_db),
        "p_cursors_mv": p_cursors_mv,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze SerDes TX & FFE Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_s11 = sub.add_parser("s11")
    p_s11.add_argument("psf_dir", type=Path)

    p_dt = sub.add_parser("dc_term")
    p_dt.add_argument("psf_dir", type=Path)
    p_dt.add_argument("--r-target", type=float, default=50.0)

    p_eye = sub.add_parser("eye")
    p_eye.add_argument("psf_dir", type=Path)
    p_eye.add_argument("--ui", type=float, default=100e-12)
    p_eye.add_argument("--t-skip", type=float, default=5.0e-9)

    p_cs = sub.add_parser("cm_sndr")
    p_cs.add_argument("psf_dir", type=Path)
    p_cs.add_argument("--ui", type=float, default=100e-12)
    p_cs.add_argument("--t-skip", type=float, default=3.0e-9)
    p_cs.add_argument("--n-p", type=int, default=12)
    p_cs.add_argument("--osr", type=int, default=16)
    p_cs.add_argument("--vdd", type=float, default=1.0)

    args = ap.parse_args(argv)
    if args.mode == "s11":
        res: object = analyze_s11(args.psf_dir)
    elif args.mode == "dc_term":
        res = analyze_dc_term(args.psf_dir, r_target=args.r_target)
    elif args.mode == "eye":
        res = analyze_eye(args.psf_dir, ui=args.ui, t_skip=args.t_skip)
    else:
        res = analyze_cm_sndr(
            args.psf_dir, ui=args.ui, t_skip=args.t_skip, n_p=args.n_p, osr=args.osr, vdd=args.vdd
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
