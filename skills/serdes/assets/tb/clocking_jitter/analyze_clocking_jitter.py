#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from SerDes Clocking & Jitter testbenches.

Usage:
  python analyze_clocking_jitter.py dcd_iq <psf_dir> [--f-clk 5e9] [--vdd 1.0]
  python analyze_clocking_jitter.py bathtub <psf_dir> [--ui 100e-12] [--f-sj 50e6] [--t-skip 5e-9]
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

from psf_utils import crossings, eye_diagram_metrics, find_single, parse_psf_ascii


def _measure_clk_dcd_iq(path: Path, *, f_clk: float, vdd: float) -> dict[str, float]:
    d = parse_psf_ascii(path)
    t = d["time"]
    vth = 0.5 * vdd
    t_clk = 1.0 / f_clk
    t_skip = 3.0 * t_clk  # skip startup cycles

    def edges(sig: np.ndarray, direction: str) -> np.ndarray:
        xs = [x for x in crossings(t, sig, vth, direction=direction) if x >= t_skip]
        return np.asarray(xs, dtype=float)

    r0 = edges(d["CK0"], "rising")
    f0 = edges(d["CK0"], "falling")
    r90 = edges(d["CK90"], "rising")
    r180 = edges(d["CK180"], "rising")
    r270 = edges(d["CK270"], "rising")

    if len(r0) < 3:
        raise RuntimeError(f"Insufficient CK0 cycles in {path}")

    periods = np.diff(r0)
    t_per = float(np.median(periods))

    # Duty cycle of CK0
    highs: list[float] = []
    for tr in r0[:-1]:
        fa = f0[f0 > tr]
        if len(fa) > 0 and (float(fa[0]) - tr) < t_per:
            highs.append(float(fa[0]) - tr)
    t_high = float(np.median(highs))
    duty_pct = 100.0 * t_high / t_per
    dcd_pct = duty_pct - 50.0
    dcd_ps = (t_high - 0.5 * t_per) * 1e12

    def mean_spacing(a: np.ndarray, b: np.ndarray) -> float:
        vals: list[float] = []
        for ta in a[:-1]:
            ba = b[b > ta]
            if len(ba) > 0 and (float(ba[0]) - ta) < t_per:
                vals.append(float(ba[0]) - ta)
        return float(np.median(vals)) if vals else float("nan")

    dt_0_90 = mean_spacing(r0, r90)
    dt_90_180 = mean_spacing(r90, r180)
    dt_180_270 = mean_spacing(r180, r270)
    dt_270_360 = mean_spacing(r270, r0)

    iq_phase_deg = 360.0 * dt_0_90 / t_per
    iq_skew_deg = iq_phase_deg - 90.0
    iq_skew_ps = (dt_0_90 - 0.25 * t_per) * 1e12
    quad_ps = [x * 1e12 for x in (dt_0_90, dt_90_180, dt_180_270, dt_270_360)]
    max_quad_err_ps = max(abs(x - 0.25 * t_per * 1e12) for x in quad_ps)

    return {
        "period_ps": t_per * 1e12,
        "duty_cycle_pct": duty_pct,
        "dcd_pct": dcd_pct,
        "dcd_ps": dcd_ps,
        "iq_phase_deg": iq_phase_deg,
        "iq_skew_deg": iq_skew_deg,
        "iq_skew_ps": iq_skew_ps,
        "quadrant_spacings_ps": quad_ps,
        "max_quadrant_err_ps": max_quad_err_ps,
    }


def analyze_dcd_iq(psf_dir: Path, *, f_clk: float, vdd: float) -> dict[str, object]:
    p_raw = find_single(psf_dir, ["tran_raw*.tran", "*raw*.tran", "*.tran"])
    raw = _measure_clk_dcd_iq(p_raw, f_clk=f_clk, vdd=vdd)
    out: dict[str, object] = {"before_cal": raw}
    cal_matches = sorted(psf_dir.glob("tran_cal*.tran"))
    if cal_matches:
        cal = _measure_clk_dcd_iq(cal_matches[0], f_clk=f_clk, vdd=vdd)
        out["after_cal"] = cal
        out["dcd_reduction_ratio"] = abs(raw["dcd_pct"]) / max(abs(cal["dcd_pct"]), 1e-4)
        out["iq_skew_reduction_ratio"] = abs(raw["iq_skew_deg"]) / max(abs(cal["iq_skew_deg"]), 1e-4)
    return out


def _erfc_inv(y: float) -> float:
    """Inverse complementary error function via bisection."""
    lo, hi = 0.0, 10.0
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        if math.erfc(mid) > y:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _decompose_jitter(
    t: np.ndarray,
    v_diff: np.ndarray,
    *,
    ui: float,
    f_sj: float,
    t_skip: float,
    prbs_period: int = 127,
) -> dict[str, object]:
    m = t >= t_skip
    tm = t[m]
    vm = v_diff[m]

    r_x = crossings(tm, vm, 0.0, direction="rising")
    f_x = crossings(tm, vm, 0.0, direction="falling")
    edges = sorted([(x, 1) for x in r_x] + [(x, -1) for x in f_x], key=lambda p: p[0])
    if len(edges) < 40:
        raise RuntimeError(f"Insufficient zero crossings ({len(edges)}) for jitter decomposition")

    te = np.asarray([e[0] for e in edges], dtype=float)
    dirs = np.asarray([e[1] for e in edges], dtype=int)

    # Circular mean phase removes arbitrary channel flight delay cleanly
    ang = 2.0 * math.pi * (te / ui)
    phi0_ui = math.atan2(float(np.mean(np.sin(ang))), float(np.mean(np.cos(ang)))) / (2.0 * math.pi)
    t_shifted = te - phi0_ui * ui
    slot_idx = np.rint(t_shifted / ui).astype(int)
    tie_s = t_shifted - slot_idx * ui
    tie_ps = tie_s * 1e12

    # 1. DCD: difference between mean rising and mean falling crossing times
    rise_m = dirs == 1
    fall_m = dirs == -1
    mu_r = float(np.mean(tie_ps[rise_m]))
    mu_f = float(np.mean(tie_ps[fall_m]))
    dcd_ps = abs(mu_r - mu_f)
    tie_dcd_comp = np.where(rise_m, mu_r, mu_f)
    tie_nodcd = tie_ps - tie_dcd_comp

    # 2. SJ: coherent single-tone sine fit at f_sj
    w = 2.0 * math.pi * f_sj * te
    A = np.column_stack([np.ones_like(te), np.cos(w), np.sin(w)])
    coeff, _, _, _ = np.linalg.lstsq(A, tie_nodcd, rcond=None)
    sj_amp_ps = math.hypot(float(coeff[1]), float(coeff[2]))
    sj_pp_ps = 2.0 * sj_amp_ps
    tie_sj_comp = A @ coeff
    tie_nosj = tie_nodcd - tie_sj_comp

    # 3. Pattern-locked DDJ (PRBS-7 period = 127 UI) + unbiased ANOVA RJ_rms
    pat_slot = slot_idx % prbs_period
    ddj_means: list[float] = []
    tie_ddj_comp = np.zeros_like(tie_nosj)
    ss_within = 0.0
    dof_within = 0
    for k in np.unique(pat_slot):
        mk = pat_slot == k
        vals = tie_nosj[mk]
        mu_k = float(np.mean(vals))
        tie_ddj_comp[mk] = mu_k
        if len(vals) >= 2:
            ddj_means.append(mu_k)
            ss_within += float(np.sum((vals - mu_k) ** 2))
            dof_within += len(vals) - 1

    ddj_pp_ps = float(max(ddj_means) - min(ddj_means)) if len(ddj_means) >= 2 else 0.0
    rj_rms_ps = math.sqrt(ss_within / dof_within) if dof_within > 0 else 0.0

    # Combined deterministic jitter waveform (DCD + SJ + DDJ)
    tie_det = tie_dcd_comp + tie_sj_comp + tie_ddj_comp
    dj_pp_ps = float(np.max(tie_det) - np.min(tie_det))
    dj_sum_ps = dcd_ps + ddj_pp_ps + sj_pp_ps

    # Dual-Dirac bathtub eye width extrapolation across BER levels (transition density rho=0.5)
    ui_ps = ui * 1e12
    rho_t = 0.5
    bathtub: dict[str, dict[str, float]] = {}
    for label, ber in (("1e-3", 1e-3), ("1e-6", 1e-6), ("1e-9", 1e-9), ("1e-12", 1e-12)):
        q_ber = math.sqrt(2.0) * _erfc_inv(2.0 * ber / rho_t)
        tj_ps = dj_pp_ps + 2.0 * q_ber * rj_rms_ps
        ew_ps = max(ui_ps - tj_ps, 0.0)
        bathtub[label] = {
            "q_factor": q_ber,
            "tj_ps": tj_ps,
            "tj_ui": tj_ps / ui_ps,
            "ew_ps": ew_ps,
            "ew_ui": ew_ps / ui_ps,
        }

    eye = eye_diagram_metrics(t, v_diff, ui_s=ui, t_skip=t_skip)
    return {
        "n_edges": int(len(edges)),
        "dcd_ps": dcd_ps,
        "ddj_pp_ps": ddj_pp_ps,
        "sj_pp_ps": sj_pp_ps,
        "rj_rms_ps": rj_rms_ps,
        "dj_pp_ps": dj_pp_ps,
        "dj_sum_ps": dj_sum_ps,
        "tj_1e12_ps": bathtub["1e-12"]["tj_ps"],
        "tj_1e12_ui": bathtub["1e-12"]["tj_ui"],
        "ew_1e12_ps": bathtub["1e-12"]["ew_ps"],
        "ew_1e12_ui": bathtub["1e-12"]["ew_ui"],
        "bathtub": bathtub,
        "sim_eye": eye,
    }


def analyze_bathtub(psf_dir: Path, *, ui: float, f_sj: float, t_skip: float) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    v_cln = d["CLEAN_P"] - d["CLEAN_N"]
    v_jit = d["JIT_P"] - d["JIT_N"]
    return {
        "clean_tx": _decompose_jitter(t, v_cln, ui=ui, f_sj=f_sj, t_skip=t_skip),
        "jittered_tx": _decompose_jitter(t, v_jit, ui=ui, f_sj=f_sj, t_skip=t_skip),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze SerDes Clocking & Jitter Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_di = sub.add_parser("dcd_iq")
    p_di.add_argument("psf_dir", type=Path)
    p_di.add_argument("--f-clk", type=float, default=5e9)
    p_di.add_argument("--vdd", type=float, default=1.0)

    p_bt = sub.add_parser("bathtub")
    p_bt.add_argument("psf_dir", type=Path)
    p_bt.add_argument("--ui", type=float, default=100e-12)
    p_bt.add_argument("--f-sj", type=float, default=50e6)
    p_bt.add_argument("--t-skip", type=float, default=5.0e-9)

    args = ap.parse_args(argv)
    if args.mode == "dcd_iq":
        res: object = analyze_dcd_iq(args.psf_dir, f_clk=args.f_clk, vdd=args.vdd)
    else:
        res = analyze_bathtub(args.psf_dir, ui=args.ui, f_sj=args.f_sj, t_skip=args.t_skip)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
