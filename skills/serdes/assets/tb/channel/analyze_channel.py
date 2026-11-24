#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from SerDes Channel testbenches.

Usage:
  python analyze_channel.py sp <psf_dir>
  python analyze_channel.py tdr <psf_dir> [--v-step 0.4] [--z0-diff 100.0]
  python analyze_channel.py sbr_eye <psf_dir> [--ui 100e-12] [--t-skip 4e-9]
  python analyze_channel.py nport_s4p <psf_dir> [--ui 100e-12] [--t-skip 5e-9]
  python analyze_channel.py xtalk <psf_dir> [--ui 100e-12] [--t-skip 5e-9]
  python analyze_channel.py blw_cid <psf_dir> [--ui 100e-12] [--z0 50.0] [--c-ac 200e-12] [--n-cid 64]
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


def analyze_blw_cid(
    psf_dir: Path, *, ui: float, z0: float, c_ac: float, n_cid: int
) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_rx = d["RXP"] - d["RXN"]
    v_rx_cm = 0.5 * (d["RXP"] + d["RXN"])
    v_tx = d["TXP"] - d["TXN"]

    # Locate the long CID positive plateau at RX by finding the longest rising-to-falling run
    r_rx = crossings(t, v_rx, 0.0, direction="rising")
    f_rx = crossings(t, v_rx, 0.0, direction="falling")
    best_dur = 0.0
    t_cid_start = 0.0
    t_cid_end = 0.0
    for tr in r_rx:
        fa = [tf for tf in f_rx if tf > tr]
        if fa:
            dur = fa[0] - tr
            if dur > best_dur:
                best_dur = dur
                t_cid_start = tr
                t_cid_end = fa[0]
    if best_dur < 5.0 * ui:
        raise RuntimeError(f"Could not locate CID plateau (longest positive run = {best_dur*1e9:.3f} ns)")

    # Exponential RC droop fit over settled CID burst [t_cid_start + 3*ui, t_cid_end - 0.5*ui]
    tau_ac = 2.0 * z0 * c_ac
    t_cid_nom = n_cid * ui
    t_a = t_cid_start + 3.0 * ui
    t_b = t_cid_end - 0.5 * ui
    m_cid = (t >= t_a) & (t <= t_b) & (v_rx > 1e-4)
    if np.sum(m_cid) < 10:
        raise RuntimeError("Insufficient positive samples inside CID burst for exponential fit")

    dt_fit = t[m_cid] - t_cid_start
    slope_ln, intercept_ln = np.polyfit(dt_fit, np.log(v_rx[m_cid]), 1)
    v0_est = math.exp(float(intercept_ln))
    tau_meas = -1.0 / float(slope_ln) if slope_ln < -1e-12 else float("inf")

    v_end_cid = float(np.interp(t_cid_end - 0.25 * ui, t, v_rx))
    blw_peak_v = v0_est - v_end_cid
    blw_analytical_v = v0_est * (1.0 - math.exp(-t_cid_nom / tau_ac))
    rel_err_pct = 100.0 * abs(blw_peak_v - blw_analytical_v) / max(blw_analytical_v, 1e-9)

    # Pre-CID (settled 1010 preamble) vs. Immediate Post-CID (first 8 UIs after CID) eye & DC shift
    def window_1010_metrics(t_lo: float, t_hi: float) -> tuple[float, float, float, float]:
        # Extract local positive peaks ('1' bits) and negative troughs ('0' bits) per UI
        n_w = max(int(math.floor((t_hi - t_lo) / ui)), 2)
        hi_vals: list[float] = []
        lo_vals: list[float] = []
        for k in range(n_w):
            ta_k = t_lo + (k + 0.20) * ui
            tb_k = t_lo + (k + 0.80) * ui
            mk = (t >= ta_k) & (t <= tb_k)
            if not np.any(mk):
                continue
            vm = float(np.median(v_rx[mk]))
            if k % 2 == 0:
                lo_vals.append(vm)
            else:
                hi_vals.append(vm)
        # Ensure hi_vals holds the upper rail ('1') and lo_vals holds the lower rail ('0')
        if hi_vals and lo_vals and float(np.mean(hi_vals)) < float(np.mean(lo_vals)):
            hi_vals, lo_vals = lo_vals, hi_vals
        v1_min = float(np.min(hi_vals))
        v0_max = float(np.max(lo_vals))
        dc_mid = 0.5 * (float(np.mean(hi_vals)) + float(np.mean(lo_vals)))
        # Eye height referenced to fixed 0 V slicer threshold (worst-case margin = min(v1_min, -v0_max))
        eye_h = max(2.0 * min(v1_min, -v0_max), 0.0)
        return eye_h, dc_mid, v1_min, v0_max

    pre_eye_h, pre_dc, pre_v1_min, pre_v0_max = window_1010_metrics(
        t_cid_start - 16.0 * ui, t_cid_start - 2.0 * ui
    )
    post_eye_h, post_dc, post_v1_min, post_v0_max = window_1010_metrics(
        t_cid_end, t_cid_end + 8.0 * ui
    )
    # First 4 UIs aligned at t_cid_end (0, 1, 0, 1 bit boundaries) capture peak BLW DC shift & eye
    post_eye_imm, post_dc_imm, post_v1_imm, post_v0_imm = window_1010_metrics(
        t_cid_end, t_cid_end + 4.0 * ui
    )
    eye_closure_pct = 100.0 * (pre_eye_h - post_eye_imm) / max(pre_eye_h, 1e-9)

    return {
        "n_cid_ui": int(n_cid),
        "t_cid_meas_ns": float(best_dur * 1e9),
        "tau_ac_analytical_ns": float(tau_ac * 1e9),
        "tau_ac_meas_ns": float(tau_meas * 1e9),
        "v0_plateau_mv": float(v0_est * 1e3),
        "v_cid_end_mv": float(v_end_cid * 1e3),
        "blw_peak_mv": float(blw_peak_v * 1e3),
        "blw_pct": float(100.0 * blw_peak_v / max(v0_est, 1e-9)),
        "blw_analytical_mv": float(blw_analytical_v * 1e3),
        "blw_analytical_pct": float(100.0 * (1.0 - math.exp(-t_cid_nom / tau_ac))),
        "rel_err_pct": float(rel_err_pct),
        "pre_cid_dc_mv": float(pre_dc * 1e3),
        "post_cid_dc_shift_mv": float(post_dc_imm * 1e3),
        "pre_cid_eye_height_mv": float(pre_eye_h * 1e3),
        "post_cid_eye_height_mv": float(post_eye_imm * 1e3),
        "post_cid_8ui_eye_height_mv": float(post_eye_h * 1e3),
        "post_cid_eye_open": bool(post_eye_imm > 0.0),
        "eye_closure_pct": float(eye_closure_pct),
        "rx_cm_dc_mv": float(np.mean(v_rx_cm) * 1e3),
        "tx_swing_pp_mv": float((np.max(v_tx) - np.min(v_tx)) * 1e3),
    }


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

    p_blw = sub.add_parser("blw_cid")
    p_blw.add_argument("psf_dir", type=Path)
    p_blw.add_argument("--ui", type=float, default=100e-12)
    p_blw.add_argument("--z0", type=float, default=50.0)
    p_blw.add_argument("--c-ac", type=float, default=200e-12)
    p_blw.add_argument("--n-cid", type=int, default=64)

    args = ap.parse_args(argv)
    if args.mode == "sp":
        res: object = analyze_sp(args.psf_dir)
    elif args.mode == "tdr":
        res = analyze_tdr(args.psf_dir, v_step=args.v_step, z0_diff=args.z0_diff)
    elif args.mode == "sbr_eye":
        res = analyze_sbr_eye(args.psf_dir, ui=args.ui, t_skip=args.t_skip)
    elif args.mode == "nport_s4p":
        res = analyze_nport_s4p(args.psf_dir, ui=args.ui, t_skip=args.t_skip)
    elif args.mode == "xtalk":
        res = analyze_xtalk(args.psf_dir, ui=args.ui, t_skip=args.t_skip)
    else:
        res = analyze_blw_cid(args.psf_dir, ui=args.ui, z0=args.z0, c_ac=args.c_ac, n_cid=args.n_cid)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
