#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from SerDes CDR testbenches.

Usage:
  python analyze_cdr.py bbpd <psf_dir> [--ui 100e-12] [--vdd 1.0]
  python analyze_cdr.py pi <psf_dir> [--f-clk 10e9] [--t-dwell 400e-12] [--n-codes 64]
  python analyze_cdr.py jtol <psf_dir> [--f-sj 20e6] [--n-codes 64] [--t-lock 40e-9]
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

from psf_utils import crossings, find_single, parse_psf_ascii


def analyze_bbpd(psf_dir: Path, *, ui: float, vdd: float) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vin = d["INP"] - d["INN"]
    vclk = d["CLKP"] - d["CLKN"]
    up = d["UP"]
    dn = d["DN"]

    # Find all data transition midpoints (both rising and falling crossings of vin=0)
    data_edges = sorted(
        crossings(t, vin, 0.0, direction="rising")
        + crossings(t, vin, 0.0, direction="falling")
    )
    data_arr = np.asarray(data_edges, dtype=float)
    clk_fall = crossings(t, vclk, 0.0, direction="falling")
    clk_rise = crossings(t, vclk, 0.0, direction="rising")

    phases_ui: list[float] = []
    votes: list[float] = []

    # Each falling edge (edge sample) is followed ~0.5 UI later by a rising edge
    # (data sample) which latches UP/DN; sample UP/DN 0.30 UI after that rising edge.
    for te in clk_fall:
        if len(data_arr) == 0:
            break
        idx_d = int(np.argmin(np.abs(data_arr - te)))
        dt_ui = (te - float(data_arr[idx_d])) / ui
        if abs(dt_ui) > 0.48:
            continue
        # Next rising edge after te
        tr_list = [tr for tr in clk_rise if tr > te and tr - te < 0.8 * ui]
        if not tr_list:
            continue
        t_samp = tr_list[0] + 0.35 * ui
        if t_samp >= float(t[-1]):
            continue
        u_b = 1.0 if float(np.interp(t_samp, t, up)) >= 0.5 * vdd else 0.0
        d_b = 1.0 if float(np.interp(t_samp, t, dn)) >= 0.5 * vdd else 0.0
        phases_ui.append(dt_ui)
        votes.append(u_b - d_b)

    ph = np.asarray(phases_ui, dtype=float)
    vt = np.asarray(votes, dtype=float)
    early_m = (ph >= -0.40) & (ph <= -0.08)
    late_m = (ph >= 0.08) & (ph <= 0.40)
    dz_m = (np.abs(ph) <= 0.10) & (vt == 0.0)

    early_mean = float(np.mean(vt[early_m])) if np.any(early_m) else float("nan")
    late_mean = float(np.mean(vt[late_m])) if np.any(late_m) else float("nan")

    if np.any(dz_m):
        dz_ph = ph[dz_m]
        deadzone_mui = float((np.max(dz_ph) - np.min(dz_ph) + 0.005) * 1e3)
    else:
        deadzone_mui = 0.0

    # Zero-crossing phase offset (midpoint between last -1 and first +1)
    neg_idx = np.where((ph < 0.15) & (vt < -0.5))[0]
    pos_idx = np.where((ph > -0.15) & (vt > 0.5))[0]
    if len(neg_idx) > 0 and len(pos_idx) > 0:
        center_mui = 0.5 * (float(ph[neg_idx[-1]]) + float(ph[pos_idx[0]])) * 1e3
    else:
        center_mui = float("nan")

    return {
        "n_phase_points": int(len(ph)),
        "early_mean_up_minus_dn": early_mean,
        "late_mean_up_minus_dn": late_mean,
        "polarity_correct": bool(early_mean < -0.9 and late_mean > 0.9),
        "deadzone_width_mui": deadzone_mui,
        "deadzone_points": int(np.sum(dz_m)),
        "transition_center_mui": center_mui,
    }


def analyze_pi(psf_dir: Path, *, f_clk: float, t_dwell: float, n_codes: int) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_ref = d["CKI_P"] - d["CKI_N"]
    v_pi = d["CLKP"] - d["CLKN"]
    t_clk = 1.0 / f_clk

    ref_rise = np.asarray(crossings(t, v_ref, 0.0, direction="rising"), dtype=float)
    pi_rise = np.asarray(crossings(t, v_pi, 0.0, direction="rising"), dtype=float)

    phases_ui: list[float] = []
    for k in range(n_codes + 1):
        # Measure settled phase during final quarter of dwell k (avoiding code ramp)
        t_win_lo = (k + 0.55) * t_dwell
        t_win_hi = (k + 0.92) * t_dwell
        p_in = pi_rise[(pi_rise >= t_win_lo) & (pi_rise <= t_win_hi)]
        if len(p_in) == 0:
            raise RuntimeError(f"No PI clock rising edge found in dwell window k={k}")
        tp = float(p_in[-1])
        # Reference clock rising edge immediately preceding (or at) tp
        r_prev = ref_rise[ref_rise <= tp + 0.05 * t_clk]
        if len(r_prev) == 0:
            raise RuntimeError(f"No reference clock edge before t={tp}")
        dt_ui = ((tp - float(r_prev[-1])) % t_clk) / t_clk
        phases_ui.append(dt_ui)

    # Unwrap phase across 0..1 UI smoothly
    ph_rad = np.unwrap(2.0 * math.pi * np.asarray(phases_ui, dtype=float))
    ph_ui = ph_rad / (2.0 * math.pi)
    ph_ui = ph_ui - ph_ui[0]

    steps_ui = np.diff(ph_ui)
    ideal_lsb_ui = 1.0 / n_codes
    dnl_lsb = steps_ui / ideal_lsb_ui - 1.0
    ideal_curve = np.arange(n_codes + 1, dtype=float) * ideal_lsb_ui
    # Endpoint-referenced INL
    end_slope = (ph_ui[-1] - ph_ui[0]) / n_codes
    inl_ui = ph_ui - (ph_ui[0] + np.arange(n_codes + 1, dtype=float) * end_slope)
    inl_lsb = inl_ui / ideal_lsb_ui

    return {
        "n_codes": int(n_codes),
        "total_span_ui": float(ph_ui[-1]),
        "ideal_step_mui": ideal_lsb_ui * 1e3,
        "mean_step_mui": float(np.mean(steps_ui) * 1e3),
        "mean_step_deg": float(np.mean(steps_ui) * 360.0),
        "min_step_mui": float(np.min(steps_ui) * 1e3),
        "max_step_mui": float(np.max(steps_ui) * 1e3),
        "monotonic": bool(np.min(steps_ui) > 0.0),
        "dnl_max_lsb": float(np.max(np.abs(dnl_lsb))),
        "dnl_max_mui": float(np.max(np.abs(steps_ui - ideal_lsb_ui)) * 1e3),
        "dnl_max_deg": float(np.max(np.abs(steps_ui - ideal_lsb_ui)) * 360.0),
        "inl_max_lsb": float(np.max(np.abs(inl_lsb))),
        "inl_max_mui": float(np.max(np.abs(inl_ui)) * 1e3),
        "inl_max_deg": float(np.max(np.abs(inl_ui)) * 360.0),
    }


def analyze_jtol(
    psf_dir: Path, *, f_sj: float, n_codes: int, t_lock: float, vdd: float
) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    sj_ui = d["SJ_CODE"] / float(n_codes)
    rx_ui = d["RX_VCODE"] / float(n_codes)
    tx_clk = d["TX_CLKP"]
    rx_clk = d["RX_CLKP"]
    tx_bit = d["TX_BIT"]
    rx_dout = d["RX_DOUT"]

    m = t >= t_lock
    tm = t[m]
    # Remove constant DC eye-centering offset (~0.5 UI) to measure dynamic phase tracking error
    diff_ui = rx_ui[m] - sj_ui[m]
    dc_off_ui = float(np.mean(diff_ui))
    err_ui = diff_ui - dc_off_ui

    # Single-tone least-squares DFT at f_sj to extract JTF = Phi_cdr(f_sj) / Phi_in(f_sj)
    w = 2.0 * math.pi * f_sj * tm
    c_vec = np.cos(w)
    s_vec = np.sin(w)
    A = np.column_stack([np.ones_like(tm), c_vec, s_vec])
    coeff_in, _, _, _ = np.linalg.lstsq(A, sj_ui[m], rcond=None)
    coeff_out, _, _, _ = np.linalg.lstsq(A, rx_ui[m], rcond=None)
    z_in = complex(float(coeff_in[1]), -float(coeff_in[2]))
    z_out = complex(float(coeff_out[1]), -float(coeff_out[2]))
    h_jtf = z_out / z_in if abs(z_in) > 1e-9 else complex(float("nan"), 0.0)
    jtf_mag = abs(h_jtf)
    jtf_db = 20.0 * math.log10(max(jtf_mag, 1e-30))
    jtf_phase_deg = math.degrees(math.atan2(h_jtf.imag, h_jtf.real))

    # Bit-error check after t_lock: sample TX_BIT on TX_CLKP mid-UI and RX_DOUT on RX_CLKP mid-UI
    tx_edges = [te for te in crossings(t, tx_clk, 0.5 * vdd, direction="rising") if te >= t_lock]
    rx_edges = [re for re in crossings(t, rx_clk, 0.5 * vdd, direction="rising") if re >= t_lock]

    t_tx_s = np.asarray([te + 45e-12 for te in tx_edges if te + 45e-12 < float(t[-1])], dtype=float)
    t_rx_s = np.asarray([re + 45e-12 for re in rx_edges if re + 45e-12 < float(t[-1])], dtype=float)
    tx_b = (np.interp(t_tx_s, t, tx_bit) >= 0.5).astype(int)
    rx_b = (np.interp(t_rx_s, t, rx_dout) >= 0.5 * vdd).astype(int)

    n_min = min(len(tx_b), len(rx_b))
    best_err = n_min
    best_lag = 0
    for lag in range(-6, 7):
        if lag >= 0:
            a, b = tx_b[: n_min - lag], rx_b[lag:n_min]
        else:
            a, b = tx_b[-lag:n_min], rx_b[: n_min + lag]
        if len(a) < 50:
            continue
        errs = int(np.sum(a != b))
        if errs < best_err:
            best_err = errs
            best_lag = lag

    bits_checked = max(n_min - abs(best_lag), 1)
    return {
        "f_sj_mhz": f_sj / 1e6,
        "sj_in_pp_ui": float(2.0 * abs(z_in)),
        "cdr_out_pp_ui": float(2.0 * abs(z_out)),
        "dc_phase_offset_ui": dc_off_ui,
        "track_err_rms_mui": float(np.sqrt(np.mean(err_ui**2)) * 1e3),
        "track_err_peak_mui": float(np.max(np.abs(err_ui)) * 1e3),
        "jtf_gain_linear": float(jtf_mag),
        "jtf_gain_db": float(jtf_db),
        "jtf_phase_deg": float(jtf_phase_deg),
        "bit_lag_ui": int(best_lag),
        "bits_checked": int(bits_checked),
        "bit_errors": int(best_err),
        "jtol_pass": bool(best_err == 0 and float(np.max(np.abs(err_ui))) < 0.35),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze SerDes CDR Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_bb = sub.add_parser("bbpd")
    p_bb.add_argument("psf_dir", type=Path)
    p_bb.add_argument("--ui", type=float, default=100e-12)
    p_bb.add_argument("--vdd", type=float, default=1.0)

    p_pi = sub.add_parser("pi")
    p_pi.add_argument("psf_dir", type=Path)
    p_pi.add_argument("--f-clk", type=float, default=10e9)
    p_pi.add_argument("--t-dwell", type=float, default=400e-12)
    p_pi.add_argument("--n-codes", type=int, default=64)

    p_jt = sub.add_parser("jtol")
    p_jt.add_argument("psf_dir", type=Path)
    p_jt.add_argument("--f-sj", type=float, default=20e6)
    p_jt.add_argument("--n-codes", type=int, default=64)
    p_jt.add_argument("--t-lock", type=float, default=40e-9)
    p_jt.add_argument("--vdd", type=float, default=1.0)

    args = ap.parse_args(argv)
    if args.mode == "bbpd":
        res: object = analyze_bbpd(args.psf_dir, ui=args.ui, vdd=args.vdd)
    elif args.mode == "pi":
        res = analyze_pi(args.psf_dir, f_clk=args.f_clk, t_dwell=args.t_dwell, n_codes=args.n_codes)
    else:
        res = analyze_jtol(
            args.psf_dir, f_sj=args.f_sj, n_codes=args.n_codes, t_lock=args.t_lock, vdd=args.vdd
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
