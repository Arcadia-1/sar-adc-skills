#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from SerDes PAM4 testbenches.

Usage:
  python analyze_pam4.py tx_rlm <psf_dir> [--ui 100e-12] [--t-skip 2.5e-9]
  python analyze_pam4.py dfe_ber <psf_dir> [--ui 100e-12] [--t-skip 5.0e-9] [--vdd 1.0]
  python analyze_pam4.py link_top <psf_dir> [--ui 100e-12] [--t-skip 6.0e-9] [--vdd 1.0]
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

# Gray code table: symbol index (0..3) -> (MSB, LSB)
_GRAY_BITS = {0: (0, 0), 1: (0, 1), 2: (1, 1), 3: (1, 0)}


def _longest_circular_run(mask: np.ndarray) -> int:
    n = len(mask)
    if np.all(mask):
        return n
    if not np.any(mask):
        return 0
    doubled = np.concatenate([mask, mask])
    best = 0
    cur = 0
    for flag in doubled:
        if flag:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return min(best, n)


def pam4_eye_and_rlm(
    t: np.ndarray,
    v_diff: np.ndarray,
    *,
    ui_s: float,
    t_skip: float,
    n_phase: int = 64,
) -> dict[str, object]:
    """Fold a PAM4 waveform into 1 UI and extract IEEE 802.3 RLM + 3-eye openings."""
    t_start = max(float(t[0]), float(t_skip))
    t_end = float(t[-1])
    n_ui = int(math.floor((t_end - t_start) / ui_s))
    if n_ui < 16:
        raise ValueError(f"Need at least 16 symbols after t_skip for PAM4 eye, got {n_ui}")

    grid = t_start + (np.arange(n_ui)[:, None] + (np.arange(n_phase)[None, :] / n_phase)) * ui_s
    traces = np.interp(grid, t, v_diff)

    # Scan phase bins to locate eye center where worst of the 3 eyes is widest
    min_gap = np.full(n_phase, -1e9, dtype=float)
    for j in range(n_phase):
        col = traces[:, j]
        v_lo, v_hi = float(np.min(col)), float(np.max(col))
        v_mid = 0.5 * (v_lo + v_hi)
        v_half = max(0.5 * (v_hi - v_lo), 1e-9)
        th0, th1, th2 = v_mid - (2.0 / 3.0) * v_half, v_mid, v_mid + (2.0 / 3.0) * v_half
        g0 = col[col < th0]
        g1 = col[(col >= th0) & (col < th1)]
        g2 = col[(col >= th1) & (col < th2)]
        g3 = col[col >= th2]
        if len(g0) > 0 and len(g1) > 0 and len(g2) > 0 and len(g3) > 0:
            min_gap[j] = min(
                float(np.min(g1) - np.max(g0)),
                float(np.min(g2) - np.max(g1)),
                float(np.min(g3) - np.max(g2)),
            )

    max_min_gap = float(np.max(min_gap))
    if max_min_gap > 0.0:
        plat = min_gap >= 0.85 * max_min_gap
        doubled_p = np.concatenate([plat, plat])
        best_len = 0
        best_start = int(np.argmax(min_gap))
        cur_len = 0
        cur_start = 0
        for idx_p, flag in enumerate(doubled_p):
            if flag:
                if cur_len == 0:
                    cur_start = idx_p
                cur_len += 1
                if cur_len > best_len and cur_start < n_phase:
                    best_len = min(cur_len, n_phase)
                    best_start = cur_start
            else:
                cur_len = 0
        best_idx = (best_start + best_len // 2) % n_phase
    else:
        best_idx = int(np.argmax(min_gap))

    col_best = traces[:, best_idx]
    v_lo, v_hi = float(np.min(col_best)), float(np.max(col_best))
    v_mid0 = 0.5 * (v_lo + v_hi)
    v_half0 = max(0.5 * (v_hi - v_lo), 1e-9)
    th0, th1, th2 = v_mid0 - (2.0 / 3.0) * v_half0, v_mid0, v_mid0 + (2.0 / 3.0) * v_half0

    sym = np.zeros(n_ui, dtype=int)
    sym[(col_best >= th0) & (col_best < th1)] = 1
    sym[(col_best >= th1) & (col_best < th2)] = 2
    sym[col_best >= th2] = 3

    levels: list[float] = []
    for k in range(4):
        pts = col_best[sym == k]
        levels.append(float(np.median(pts)) if len(pts) > 0 else float("nan"))

    v0, v1, v2, v3 = levels
    v_mid = 0.5 * (v0 + v3)
    es1 = (v1 - v_mid) / (v0 - v_mid) if abs(v0 - v_mid) > 1e-9 else float("nan")
    es2 = (v2 - v_mid) / (v3 - v_mid) if abs(v3 - v_mid) > 1e-9 else float("nan")
    rlm = min(3.0 * es1, 3.0 * es2, 2.0 - 3.0 * es1, 2.0 - 3.0 * es2)

    eyes: dict[str, dict[str, object]] = {}
    swing_pp = float(np.max(traces) - np.min(traces))
    for name, lo_k, hi_k in (("lower", 0, 1), ("mid", 1, 2), ("upper", 2, 3)):
        m_lo = sym == lo_k
        m_hi = sym == hi_k
        if not np.any(m_lo) or not np.any(m_hi):
            eyes[name] = {
                "eye_open": False,
                "eye_height_mv": 0.0,
                "eye_width_ui": 0.0,
                "eye_width_ps": 0.0,
            }
            continue
        opening = np.min(traces[m_hi, :], axis=0) - np.max(traces[m_lo, :], axis=0)
        eh = max(float(np.max(opening)), 0.0)
        run = _longest_circular_run(opening > 0.0)
        if run < 2 or eh < 0.005 * max(swing_pp, 1e-9):
            eh = 0.0
            run = 0
        ew_ui = run / n_phase
        eyes[name] = {
            "eye_open": bool(eh > 0.0 and run > 0),
            "eye_height_mv": eh * 1e3,
            "eye_width_ui": ew_ui,
            "eye_width_ps": ew_ui * ui_s * 1e12,
        }

    min_eh = min(float(eyes[k]["eye_height_mv"]) for k in ("lower", "mid", "upper"))
    min_ew = min(float(eyes[k]["eye_width_ps"]) for k in ("lower", "mid", "upper"))
    all_open = all(bool(eyes[k]["eye_open"]) for k in ("lower", "mid", "upper"))

    return {
        "n_symbols": int(n_ui),
        "best_phase_ui": float(best_idx / n_phase),
        "levels_mv": [v * 1e3 for v in levels],
        "outer_swing_pp_mv": float((v3 - v0) * 1e3),
        "inner_asym_mv": float(abs((v1 + v2) - 2.0 * v_mid) * 1e3),
        "es1": float(es1),
        "es2": float(es2),
        "rlm": float(rlm),
        "rlm_pass": bool(math.isfinite(rlm) and rlm >= 0.95),
        "all_3_eyes_open": all_open,
        "min_eye_height_mv": min_eh,
        "min_eye_width_ps": min_ew,
        "eyes": eyes,
    }


def analyze_tx_rlm(psf_dir: Path, *, ui: float, t_skip: float) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_out = d["OUTP"] - d["OUTN"]
    return pam4_eye_and_rlm(t, v_out, ui_s=ui, t_skip=t_skip)


def analyze_dfe_ber(psf_dir: Path, *, ui: float, t_skip: float, vdd: float) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_before = d["RXP"] - d["RXN"]
    v_after = d["SUMP"] - d["SUMN"]
    sym_tx_w = d["SYM_TX"]
    sym_rx_w = d["SYM_RX"]
    msb_rx_w = d["MSB_RX"]
    lsb_rx_w = d["LSB_RX"]
    clk_rx = d["CLK_RX"]

    before_m = pam4_eye_and_rlm(t, v_before, ui_s=ui, t_skip=t_skip)
    after_m = pam4_eye_and_rlm(t, v_after, ui_s=ui, t_skip=t_skip)

    # Sample TX symbols on UI grid and RX symbols after CLK_RX rising edges
    rx_edges = [te for te in crossings(t, clk_rx, 0.5 * vdd, direction="rising") if te >= t_skip]
    t_rx_s = np.asarray([te + 0.50 * ui for te in rx_edges if te + 0.50 * ui < float(t[-1])], dtype=float)
    t_tx_s = np.arange(t_skip + 0.50 * ui, float(t[-1]) - 0.50 * ui, ui)

    tx_sym = np.clip(np.rint(np.interp(t_tx_s, t, sym_tx_w)).astype(int), 0, 3)
    rx_sym = np.clip(np.rint(np.interp(t_rx_s, t, sym_rx_w)).astype(int), 0, 3)
    rx_msb = (np.interp(t_rx_s, t, msb_rx_w) >= 0.5 * vdd).astype(int)
    rx_lsb = (np.interp(t_rx_s, t, lsb_rx_w) >= 0.5 * vdd).astype(int)

    n_min = min(len(tx_sym), len(rx_sym))
    best_ser = n_min
    best_lag = 0
    best_ber = 2 * n_min

    for lag in range(-5, 45):
        if lag >= 0:
            a, b = tx_sym[: n_min - lag], rx_sym[lag:n_min]
            rm, rl = rx_msb[lag:n_min], rx_lsb[lag:n_min]
        else:
            a, b = tx_sym[-lag:n_min], rx_sym[: n_min + lag]
            rm, rl = rx_msb[: n_min + lag], rx_lsb[: n_min + lag]
        if len(a) < 20:
            continue
        ser = int(np.sum(a != b))
        if ser < best_ser:
            best_ser = ser
            best_lag = lag
            tx_m = np.array([_GRAY_BITS[int(s)][0] for s in a], dtype=int)
            tx_l = np.array([_GRAY_BITS[int(s)][1] for s in a], dtype=int)
            best_ber = int(np.sum(tx_m != rm) + np.sum(tx_l != rl))

    sym_checked = max(n_min - abs(best_lag), 1)
    return {
        "before_dfe_pam4": before_m,
        "after_dfe_pam4": after_m,
        "symbol_latency_ui": int(best_lag),
        "symbols_checked": int(sym_checked),
        "symbol_errors": int(best_ser),
        "bits_checked": int(2 * sym_checked),
        "bit_errors": int(best_ber),
    }


def analyze_link_top(psf_dir: Path, *, ui: float, t_skip: float, vdd: float) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_tx = d["TXP"] - d["TXN"]
    v_ch = d["RXP"] - d["RXN"]
    v_ctle = d["EQP"] - d["EQN"]
    v_dfe = d["SUMP"] - d["SUMN"]
    sym_tx_w = d["SYM_TX"]
    sym_rx_w = d["SYM_RX"]
    msb_rx_w = d["MSB_RX"]
    lsb_rx_w = d["LSB_RX"]
    clk_rx = d["CLK_RX"]

    tx_m = pam4_eye_and_rlm(t, v_tx, ui_s=ui, t_skip=t_skip)
    ch_m = pam4_eye_and_rlm(t, v_ch, ui_s=ui, t_skip=t_skip)
    ctle_m = pam4_eye_and_rlm(t, v_ctle, ui_s=ui, t_skip=t_skip)
    dfe_m = pam4_eye_and_rlm(t, v_dfe, ui_s=ui, t_skip=t_skip)

    rx_edges = [te for te in crossings(t, clk_rx, 0.5 * vdd, direction="rising") if te >= t_skip]
    t_rx_s = np.asarray([te + 0.50 * ui for te in rx_edges if te + 0.50 * ui < float(t[-1])], dtype=float)
    t_tx_s = np.arange(t_skip + 0.50 * ui, float(t[-1]) - 0.50 * ui, ui)

    tx_sym = np.clip(np.rint(np.interp(t_tx_s, t, sym_tx_w)).astype(int), 0, 3)
    rx_sym = np.clip(np.rint(np.interp(t_rx_s, t, sym_rx_w)).astype(int), 0, 3)
    rx_msb = (np.interp(t_rx_s, t, msb_rx_w) >= 0.5 * vdd).astype(int)
    rx_lsb = (np.interp(t_rx_s, t, lsb_rx_w) >= 0.5 * vdd).astype(int)

    n_min = min(len(tx_sym), len(rx_sym))
    best_ser = n_min
    best_lag = 0
    best_ber = 2 * n_min

    for lag in range(-5, 65):
        if lag >= 0:
            a, b = tx_sym[: n_min - lag], rx_sym[lag:n_min]
            rm, rl = rx_msb[lag:n_min], rx_lsb[lag:n_min]
        else:
            a, b = tx_sym[-lag:n_min], rx_sym[: n_min + lag]
            rm, rl = rx_msb[: n_min + lag], rx_lsb[: n_min + lag]
        if len(a) < 20:
            continue
        ser = int(np.sum(a != b))
        if ser < best_ser:
            best_ser = ser
            best_lag = lag
            tx_m_b = np.array([_GRAY_BITS[int(s)][0] for s in a], dtype=int)
            tx_l_b = np.array([_GRAY_BITS[int(s)][1] for s in a], dtype=int)
            best_ber = int(np.sum(tx_m_b != rm) + np.sum(tx_l_b != rl))

    sym_checked = max(n_min - abs(best_lag), 1)
    return {
        "tx_pam4": tx_m,
        "ch_pam4": ch_m,
        "ctle_pam4": ctle_m,
        "dfe_pam4": dfe_m,
        "tx_rlm": float(tx_m["rlm"]),
        "dfe_rlm": float(dfe_m["rlm"]),
        "symbol_latency_ui": int(best_lag),
        "symbols_checked": int(sym_checked),
        "symbol_errors": int(best_ser),
        "bits_checked": int(2 * sym_checked),
        "bit_errors": int(best_ber),
        "link_pass": bool(
            best_ser == 0
            and best_ber == 0
            and bool(dfe_m["all_3_eyes_open"])
            and bool(tx_m["rlm_pass"])
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze SerDes PAM4 Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_tx = sub.add_parser("tx_rlm")
    p_tx.add_argument("psf_dir", type=Path)
    p_tx.add_argument("--ui", type=float, default=100e-12)
    p_tx.add_argument("--t-skip", type=float, default=2.5e-9)

    p_df = sub.add_parser("dfe_ber")
    p_df.add_argument("psf_dir", type=Path)
    p_df.add_argument("--ui", type=float, default=100e-12)
    p_df.add_argument("--t-skip", type=float, default=5.0e-9)
    p_df.add_argument("--vdd", type=float, default=1.0)

    p_lt = sub.add_parser("link_top")
    p_lt.add_argument("psf_dir", type=Path)
    p_lt.add_argument("--ui", type=float, default=100e-12)
    p_lt.add_argument("--t-skip", type=float, default=10.0e-9)
    p_lt.add_argument("--vdd", type=float, default=1.0)

    args = ap.parse_args(argv)
    if args.mode == "tx_rlm":
        res: object = analyze_tx_rlm(args.psf_dir, ui=args.ui, t_skip=args.t_skip)
    elif args.mode == "dfe_ber":
        res = analyze_dfe_ber(args.psf_dir, ui=args.ui, t_skip=args.t_skip, vdd=args.vdd)
    else:
        res = analyze_link_top(args.psf_dir, ui=args.ui, t_skip=args.t_skip, vdd=args.vdd)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
