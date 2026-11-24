#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from SerDes Slicer & DFE testbenches.

Usage:
  python analyze_slicer_dfe.py vtf <psf_dir>
  python analyze_slicer_dfe.py noise_tran <psf_dir> [--vid-in 1.5e-3] [--vos 0.0]
  python analyze_slicer_dfe.py dfe_eye <psf_dir> [--ui 100e-12] [--t-skip 2e-9]
  python analyze_slicer_dfe.py clk2q_sh <psf_dir> [--vdd 1.0] [--tclk 400e-12]
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
    eye_diagram_metrics,
    extract_uniform_strobe,
    find_single,
    parse_psf_ascii,
)


def analyze_vtf(psf_dir: Path) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t, inp, inn, dp, dn = extract_uniform_strobe(
        d["time"], d["INP"], d["INN"], d["DOUTP"], d["DOUTN"]
    )
    vin = inp - inn
    vout = dp - dn

    # Split at triangle peak (ascending half vs. descending half)
    idx_pk = int(np.argmax(vin))
    vin_up, vout_up = vin[: idx_pk + 1], vout[: idx_pk + 1]
    vin_dn, vout_dn = vin[idx_pk:], vout[idx_pk:]

    def find_th(x: np.ndarray, y: np.ndarray, rising: bool) -> float:
        for i in range(len(y) - 1):
            if rising and y[i] <= 0.0 < y[i + 1]:
                return float(0.5 * (x[i] + x[i + 1]))
            if (not rising) and y[i] >= 0.0 > y[i + 1]:
                return float(0.5 * (x[i] + x[i + 1]))
        return float("nan")

    v_up = find_th(vin_up, vout_up, rising=True)
    v_dn = find_th(vin_dn, vout_dn, rising=False)
    return {
        "n_points": float(len(t)),
        "v_th_up_mv": v_up * 1e3,
        "v_th_dn_mv": v_dn * 1e3,
        "offset_mv": 0.5 * (v_up + v_dn) * 1e3,
        "hysteresis_mv": (v_up - v_dn) * 1e3,
        "out_swing_diff_mv": float((np.max(vout) - np.min(vout)) * 1e3),
    }


def analyze_dfe_eye(psf_dir: Path, *, ui: float, t_skip: float) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_before = d["CH_INP"] - d["CH_INN"]
    v_after = d["SUMP"] - d["SUMN"]
    v_dout = d["DOUTP"] - d["DOUTN"]
    bit_tx = d["BIT_TX"]

    # Sample TX and RX bits once per UI after t_skip and find best integer-UI latency alignment
    t_samp = np.arange(t_skip + 0.5 * ui, float(t[-1]) - 0.5 * ui, ui)
    tx_bits = (np.interp(t_samp, t, bit_tx) >= 0.5).astype(int)
    rx_bits = (np.interp(t_samp + 0.45 * ui, t, v_dout) >= 0.0).astype(int)

    best_err = len(tx_bits)
    best_lag = 0
    for lag in range(0, 6):
        if len(tx_bits) - lag < 20:
            continue
        errs = int(np.sum(rx_bits[lag:] != tx_bits[: len(tx_bits) - lag]))
        if errs < best_err:
            best_err = errs
            best_lag = lag

    n_checked = max(len(tx_bits) - best_lag, 1)
    return {
        "before_dfe_eye": eye_diagram_metrics(t, v_before, ui_s=ui, t_skip=t_skip),
        "after_dfe_eye": eye_diagram_metrics(t, v_after, ui_s=ui, t_skip=t_skip),
        "bit_latency_ui": int(best_lag),
        "bits_checked": int(n_checked),
        "bit_errors": int(best_err),
    }


def _norm_ppf(p: float) -> float:
    """Inverse standard normal CDF Phi^-1(p) via bisection on math.erf."""
    lo, hi = -8.0, 8.0
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        cdf = 0.5 * (1.0 + math.erf(mid / math.sqrt(2.0)))
        if cdf < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def analyze_noise_tran(psf_dir: Path, *, vid_in: float, vos: float) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, dp, dn = extract_uniform_strobe(d["time"], d["DOUTP"], d["DOUTN"])
    vout = dp - dn
    # Drop initial startup sample if any
    if len(vout) > 10:
        vout = vout[1:]
    n_tot = len(vout)
    n_ones = int(np.sum(vout > 0.0))
    p_one = n_ones / max(n_tot, 1)
    # Clamp slightly away from 0/1 to keep probit finite
    p_clamped = min(max(p_one, 0.5 / max(n_tot, 1)), 1.0 - 0.5 / max(n_tot, 1))
    z = _norm_ppf(p_clamped)
    sigma_n = abs(vid_in - vos) / abs(z) if abs(z) > 1e-6 else float("nan")
    # Q = 7.0345 for BER = 1e-12 (single-sided Gaussian tail)
    sens_1e12 = 7.0345 * sigma_n if math.isfinite(sigma_n) else float("nan")
    return {
        "n_cycles": float(n_tot),
        "n_ones": float(n_ones),
        "p_one": float(p_one),
        "z_probit": float(z),
        "vid_in_mv": vid_in * 1e3,
        "sigma_n_mvrms": sigma_n * 1e3,
        "ber_1e12_half_eye_mv": sens_1e12 * 1e3,
    }


def _first_rising_after(
    t: np.ndarray, y: np.ndarray, level: float, t_start: float, t_end: float
) -> float | None:
    m = (t >= t_start) & (t <= t_end)
    if not np.any(m):
        return None
    idx = np.where(m)[0]
    i0 = max(int(idx[0]) - 1, 0)
    i1 = min(int(idx[-1]) + 1, len(t) - 1)
    xs = crossings(t[i0 : i1 + 1], y[i0 : i1 + 1], level, direction="rising")
    for x in xs:
        if t_start <= x <= t_end:
            return x
    return None


def analyze_clk2q_sh(psf_dir: Path, *, vdd: float, tclk: float) -> dict[str, object]:
    od_files = sorted(
        psf_dir.glob("tran_od*.tran"),
        key=lambda p: int(m.group(1)) if (m := re.search(r"tran_od(\d+)", p.name)) else 0,
    )
    od_points: list[dict[str, object]] = []
    xs_ln: list[float] = []
    ys_ps: list[float] = []
    v_th_q = 0.5 * vdd

    for pf in od_files:
        d = parse_psf_ascii(pf)
        t = d["time"]
        clk = d["CLK"]
        vin = d["OD_INP"] - d["OD_INN"]
        vq = d["OD_OUTP"] - d["OD_OUTN"]

        c_edges = crossings(t, clk, 0.5 * vdd, direction="rising")
        if len(c_edges) < 2:
            continue
        t_clk2 = c_edges[1]
        m_pre = (t >= t_clk2 - 30e-12) & (t <= t_clk2 - 5e-12)
        v_od = float(np.median(vin[m_pre])) if np.any(m_pre) else float(np.interp(t_clk2 - 10e-12, t, vin))
        t_q = _first_rising_after(t, vq, v_th_q, t_clk2, t_clk2 + 0.48 * tclk)
        ck2q_ps = (t_q - t_clk2) * 1e12 if t_q is not None else None
        od_points.append({
            "v_od_mv": v_od * 1e3,
            "resolved": t_q is not None,
            "clk2q_ps": ck2q_ps,
        })
        if t_q is not None and v_od > 1e-6:
            xs_ln.append(math.log(1.0 / v_od))
            ys_ps.append(float(ck2q_ps))

    tau_regen_ps = float("nan")
    r2_fit = float("nan")
    if len(xs_ln) >= 2:
        x_arr = np.asarray(xs_ln, dtype=float)
        y_arr = np.asarray(ys_ps, dtype=float)
        slope, intercept = np.polyfit(x_arr, y_arr, 1)
        tau_regen_ps = float(slope)
        y_hat = slope * x_arr + intercept
        ss_res = float(np.sum((y_arr - y_hat) ** 2))
        ss_tot = float(np.sum((y_arr - np.mean(y_arr)) ** 2))
        r2_fit = 1.0 - ss_res / max(ss_tot, 1e-30) if ss_tot > 1e-12 else 1.0

    # Setup & Hold analysis from tran_sh*.tran
    sh_path = find_single(psf_dir, ["tran_sh*.tran", "*sh*.tran"])
    dsh = parse_psf_ascii(sh_path)
    t = dsh["time"]
    clk = dsh["CLK"]
    vsu = dsh["SU_OUTP"] - dsh["SU_OUTN"]
    vhd = dsh["HD_OUTP"] - dsh["HD_OUTN"]
    c_edges = crossings(t, clk, 0.5 * vdd, direction="rising")

    su_rows: list[dict[str, object]] = []
    hd_rows: list[dict[str, object]] = []
    for m in range(21):
        idx_c = 2 * m + 1
        if idx_c >= len(c_edges):
            break
        tc = c_edges[idx_c]
        # Data edge midpoints match tb_slicer_clk2q_setup_hold.scs (2 ps ramps)
        t_su_edge = (451.0 + 803.0 * m) * 1e-12
        t_hd_edge = (551.0 + 797.0 * m) * 1e-12
        lead_ps = (tc - t_su_edge) * 1e12
        hold_ps = (t_hd_edge - tc) * 1e12

        tq_su = _first_rising_after(t, vsu, v_th_q, tc, tc + 0.48 * tclk)
        tq_hd = _first_rising_after(t, vhd, v_th_q, tc, tc + 0.48 * tclk)
        su_rows.append({
            "lead_ps": lead_ps,
            "pass": tq_su is not None,
            "clk2q_ps": (tq_su - tc) * 1e12 if tq_su is not None else None,
        })
        hd_rows.append({
            "hold_ps": hold_ps,
            "pass": tq_hd is not None,
            "clk2q_ps": (tq_hd - tc) * 1e12 if tq_hd is not None else None,
        })

    su_nom = float(su_rows[0]["clk2q_ps"]) if (su_rows and su_rows[0]["clk2q_ps"] is not None) else float("nan")
    hd_nom = float(hd_rows[0]["clk2q_ps"]) if (hd_rows and hd_rows[0]["clk2q_ps"] is not None) else float("nan")

    su_pass = [float(r["lead_ps"]) for r in su_rows if r["pass"]]
    su_10 = [
        float(r["lead_ps"])
        for r in su_rows
        if r["pass"] and r["clk2q_ps"] is not None and math.isfinite(su_nom) and float(r["clk2q_ps"]) <= 1.15 * su_nom
    ]
    hd_pass = [float(r["hold_ps"]) for r in hd_rows if r["pass"]]
    hd_10 = [
        float(r["hold_ps"])
        for r in hd_rows
        if r["pass"] and r["clk2q_ps"] is not None and math.isfinite(hd_nom) and float(r["clk2q_ps"]) <= 1.15 * hd_nom
    ]

    t_setup_min = min(su_pass) if su_pass else float("nan")
    t_hold_min = min(hd_pass) if hd_pass else float("nan")
    t_setup_15pct = min(su_10) if su_10 else t_setup_min
    t_hold_15pct = min(hd_10) if hd_10 else t_hold_min

    return {
        "n_overdrive_resolved": sum(1 for r in od_points if r["resolved"]),
        "clk2q_100mv_ps": od_points[0]["clk2q_ps"] if od_points else None,
        "clk2q_1mv_ps": next((r["clk2q_ps"] for r in od_points if abs(float(r["v_od_mv"]) - 1.0) < 0.2), None),
        "clk2q_0p5mv_ps": od_points[-1]["clk2q_ps"] if od_points else None,
        "tau_regen_ps": tau_regen_ps,
        "tau_regen_r2": r2_fit,
        "t_setup_min_pass_ps": t_setup_min,
        "t_setup_15pct_ps": t_setup_15pct,
        "t_hold_min_pass_ps": t_hold_min,
        "t_hold_15pct_ps": t_hold_15pct,
        "aperture_window_ps": (t_setup_min + t_hold_min) if (math.isfinite(t_setup_min) and math.isfinite(t_hold_min)) else float("nan"),
        "overdrive_sweep": od_points,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze SerDes Slicer & DFE Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_vtf = sub.add_parser("vtf")
    p_vtf.add_argument("psf_dir", type=Path)

    p_nt = sub.add_parser("noise_tran")
    p_nt.add_argument("psf_dir", type=Path)
    p_nt.add_argument("--vid-in", type=float, default=1.5e-3)
    p_nt.add_argument("--vos", type=float, default=0.0)

    p_dfe = sub.add_parser("dfe_eye")
    p_dfe.add_argument("psf_dir", type=Path)
    p_dfe.add_argument("--ui", type=float, default=100e-12)
    p_dfe.add_argument("--t-skip", type=float, default=2.0e-9)

    p_c2q = sub.add_parser("clk2q_sh")
    p_c2q.add_argument("psf_dir", type=Path)
    p_c2q.add_argument("--vdd", type=float, default=1.0)
    p_c2q.add_argument("--tclk", type=float, default=400e-12)

    args = ap.parse_args(argv)
    if args.mode == "vtf":
        res: object = analyze_vtf(args.psf_dir)
    elif args.mode == "noise_tran":
        res = analyze_noise_tran(args.psf_dir, vid_in=args.vid_in, vos=args.vos)
    elif args.mode == "dfe_eye":
        res = analyze_dfe_eye(args.psf_dir, ui=args.ui, t_skip=args.t_skip)
    else:
        res = analyze_clk2q_sh(args.psf_dir, vdd=args.vdd, tclk=args.tclk)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
