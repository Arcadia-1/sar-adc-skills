#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from SerDes Channel testbenches.

Usage:
  python analyze_channel.py sp <psf_dir>
  python analyze_channel.py tdr <psf_dir> [--v-step 0.4] [--z0-diff 100.0]
  python analyze_channel.py sbr_eye <psf_dir> [--ui 100e-12] [--t-skip 4e-9]
  python analyze_channel.py nport_s4p <psf_dir> [--ui 100e-12] [--t-skip 5e-9]
  python analyze_channel.py xtalk <psf_dir> [--ui 100e-12] [--t-skip 5e-9]
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
    eye_diagram_metrics,
    find_single,
    mixed_mode_s_params,
    parse_psf_ascii,
    sbr_cursor_metrics,
)


def analyze_sp(psf_dir: Path) -> dict[str, float]:
    f = find_single(psf_dir, ["sp.sp", "*.sp.sp", "*.sp"])
    d = parse_psf_ascii(f)
    freq = np.real(d["freq"])
    log_f = np.log10(freq)
    mm = mixed_mode_s_params(d, in_p=1, in_n=2, out_p=3, out_n=4)
    sdd21_db = 20.0 * np.log10(np.maximum(np.abs(mm["sdd21"]), 1e-30))
    sdd11_db = 20.0 * np.log10(np.maximum(np.abs(mm["sdd11"]), 1e-30))

    def at(arr: np.ndarray, f_hz: float) -> float:
        return float(np.interp(math.log10(f_hz), log_f, arr))

    m_10g = freq <= 10e9
    return {
        "sdd21_dc_db": float(sdd21_db[0]),
        "sdd21_1ghz_db": at(sdd21_db, 1e9),
        "sdd21_5ghz_db": at(sdd21_db, 5e9),
        "sdd21_7ghz_db": at(sdd21_db, 7e9),
        "sdd21_10ghz_db": at(sdd21_db, 10e9),
        "sdd11_worst_to_10ghz_db": float(np.max(sdd11_db[m_10g])),
        "sdd11_5ghz_db": at(sdd11_db, 5e9),
    }


def analyze_tdr(psf_dir: Path, *, v_step: float, z0_diff: float) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_in = d["TDR_INP"] - d["TDR_INN"]
    # Incident differential step amplitude into matched Z0_diff is v_step (open-circuit = 2*v_step)
    rho = (v_in - v_step) / max(v_step, 1e-9)
    rho_c = np.clip(rho, -0.95, 0.95)
    z_tdr = z0_diff * (1.0 + rho_c) / (1.0 - rho_c)

    # Evaluate transmission-line plateau region (1.2 ns .. 5.0 ns, avoiding launch edge)
    m = (t >= 1.2e-9) & (t <= 5.0e-9)
    zw = z_tdr[m] if np.any(m) else z_tdr
    return {
        "z_tdr_median_ohm": float(np.median(zw)),
        "z_tdr_min_ohm": float(np.min(zw)),
        "z_tdr_max_ohm": float(np.max(zw)),
        "z_tdr_ripple_ohm": float(np.max(zw) - np.min(zw)),
    }


def analyze_sbr_eye(psf_dir: Path, *, ui: float, t_skip: float) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_sbr = d["SBR_OUTP"] - d["SBR_OUTN"]
    v_tx = d["EYE_INP"] - d["EYE_INN"]
    v_rx = d["EYE_OUTP"] - d["EYE_OUTN"]

    sbr = sbr_cursor_metrics(t, v_sbr, ui_s=ui, t_base_end=25.0 * ui)
    tx_eye = eye_diagram_metrics(t, v_tx, ui_s=ui, t_skip=t_skip)
    rx_eye = eye_diagram_metrics(t, v_rx, ui_s=ui, t_skip=t_skip)
    return {
        "sbr": sbr,
        "tx_eye": tx_eye,
        "rx_eye": rx_eye,
    }


def analyze_nport_s4p(psf_dir: Path, *, ui: float, t_skip: float) -> dict[str, object]:
    sp_res = analyze_sp(psf_dir)
    se_res = analyze_sbr_eye(psf_dir, ui=ui, t_skip=t_skip)
    sbr = se_res["sbr"]
    assert isinstance(sbr, dict)
    cursors = sbr["cursors_mv"]
    assert isinstance(cursors, dict)
    h0 = max(abs(float(cursors.get("h0", 1e-9))), 1e-9)
    h_pre2 = abs(float(cursors.get("h-2", 0.0)))
    h_pre1 = abs(float(cursors.get("h-1", 0.0)))
    return {
        "sp": sp_res,
        "sbr": sbr,
        "tx_eye": se_res["tx_eye"],
        "rx_eye": se_res["rx_eye"],
        "pre2_cursor_ratio_pct": float(100.0 * h_pre2 / h0),
        "pre1_cursor_ratio_pct": float(100.0 * h_pre1 / h0),
        "causal_ok": bool((h_pre2 / h0 < 0.02) and (h_pre1 / h0 < 0.15)),
    }


def analyze_xtalk(psf_dir: Path, *, ui: float, t_skip: float) -> dict[str, object]:
    f_tr = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f_tr)
    t = d["time"]
    v_iso = d["ISO_OUTP"] - d["ISO_OUTN"]
    v_xtk = d["XTK_OUTP"] - d["XTK_OUTN"]
    v_fext = d["FEXT_P"] - d["FEXT_N"]
    v_next = d["NEXT_P"] - d["NEXT_N"]

    iso_eye = eye_diagram_metrics(t, v_iso, ui_s=ui, t_skip=t_skip)
    xtk_eye = eye_diagram_metrics(t, v_xtk, ui_s=ui, t_skip=t_skip)

    m = t >= t_skip
    vf = v_fext[m] if np.any(m) else v_fext
    vn = v_next[m] if np.any(m) else v_next

    iso_h = float(iso_eye["eye_height_mv"])
    xtk_h = float(xtk_eye["eye_height_mv"])
    iso_w = float(iso_eye["eye_width_ps"])
    xtk_w = float(xtk_eye["eye_width_ps"])

    res: dict[str, object] = {
        "isolated_eye": iso_eye,
        "xtalk_eye": xtk_eye,
        "eye_height_loss_mv": iso_h - xtk_h,
        "eye_height_loss_pct": (100.0 * (iso_h - xtk_h) / max(iso_h, 1e-9)),
        "eye_width_loss_ps": iso_w - xtk_w,
        "fext_rms_mv": float(np.sqrt(np.mean(vf**2)) * 1e3),
        "fext_pp_mv": float((np.max(vf) - np.min(vf)) * 1e3),
        "next_rms_mv": float(np.sqrt(np.mean(vn**2)) * 1e3),
        "next_pp_mv": float((np.max(vn) - np.min(vn)) * 1e3),
    }

    # Optional AC coupling transfer at 5 GHz & 10 GHz
    try:
        f_ac = find_single(psf_dir, ["ac.ac", "*.ac.ac", "*.ac"])
        dac = parse_psf_ascii(f_ac)
        freq = np.real(dac["freq"])
        log_f = np.log10(freq)
        # Incident differential voltage into matched 100 ohm is 1.0 V (2 V open-circuit)
        hf_db = 20.0 * np.log10(np.maximum(np.abs(dac["AC_FEXTP"] - dac["AC_FEXTN"]), 1e-30))
        hn_db = 20.0 * np.log10(np.maximum(np.abs(dac["AC_NEXTP"] - dac["AC_NEXTN"]), 1e-30))
        res["fext_5ghz_db"] = float(np.interp(math.log10(5e9), log_f, hf_db))
        res["next_5ghz_db"] = float(np.interp(math.log10(5e9), log_f, hn_db))
        res["fext_10ghz_db"] = float(np.interp(math.log10(10e9), log_f, hf_db))
        res["next_10ghz_db"] = float(np.interp(math.log10(10e9), log_f, hn_db))
    except FileNotFoundError:
        pass
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze SerDes Channel Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_sp = sub.add_parser("sp")
    p_sp.add_argument("psf_dir", type=Path)

    p_tdr = sub.add_parser("tdr")
    p_tdr.add_argument("psf_dir", type=Path)
    p_tdr.add_argument("--v-step", type=float, default=0.4)
    p_tdr.add_argument("--z0-diff", type=float, default=100.0)

    p_se = sub.add_parser("sbr_eye")
    p_se.add_argument("psf_dir", type=Path)
    p_se.add_argument("--ui", type=float, default=100e-12)
    p_se.add_argument("--t-skip", type=float, default=5.0e-9)

    p_np = sub.add_parser("nport_s4p")
    p_np.add_argument("psf_dir", type=Path)
    p_np.add_argument("--ui", type=float, default=100e-12)
    p_np.add_argument("--t-skip", type=float, default=5.0e-9)

    p_xt = sub.add_parser("xtalk")
    p_xt.add_argument("psf_dir", type=Path)
    p_xt.add_argument("--ui", type=float, default=100e-12)
    p_xt.add_argument("--t-skip", type=float, default=5.0e-9)

    args = ap.parse_args(argv)
    if args.mode == "sp":
        res: object = analyze_sp(args.psf_dir)
    elif args.mode == "tdr":
        res = analyze_tdr(args.psf_dir, v_step=args.v_step, z0_diff=args.z0_diff)
    elif args.mode == "sbr_eye":
        res = analyze_sbr_eye(args.psf_dir, ui=args.ui, t_skip=args.t_skip)
    elif args.mode == "nport_s4p":
        res = analyze_nport_s4p(args.psf_dir, ui=args.ui, t_skip=args.t_skip)
    else:
        res = analyze_xtalk(args.psf_dir, ui=args.ui, t_skip=args.t_skip)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
