#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from On-Chip RC Relaxation Oscillator testbenches.

Usage:
  python analyze_rc_osc.py temp_vdd <psf_dir> [--vdd-nom 1.2]
  python analyze_rc_osc.py trim_startup <psf_dir> [--t-en 200e-9] [--codes 0,4,8,12,16,20,24,31]
  python analyze_rc_osc.py jitter_duty <psf_dir> [--max-jitter-ps 80.0] [--max-duty-err-pct 2.0]
"""

from __future__ import annotations

import argparse
import json
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

from psf_utils import crossings, find_single, parse_psf_ascii, trapz


def _steady_clock_stats(
    t: np.ndarray,
    v_out: np.ndarray,
    *,
    t_skip: float = 0.0,
) -> dict[str, object]:
    """Extract period, frequency, duty cycle, and 10%-90% rise/fall times from OUT."""
    m = t >= t_skip
    tw, vw = t[m], v_out[m]
    v_lo = float(np.min(vw))
    v_hi = float(np.max(vw))
    v_pp = v_hi - v_lo
    if v_pp < 0.1:
        raise RuntimeError(f"Clock output amplitude too small ({v_pp:.4f} V) — oscillator not toggling")

    v_mid = 0.5 * (v_lo + v_hi)
    v_10 = v_lo + 0.1 * v_pp
    v_90 = v_lo + 0.9 * v_pp

    t_r = crossings(tw, vw, v_mid, direction="rising")
    t_f = crossings(tw, vw, v_mid, direction="falling")
    if len(t_r) < 3:
        raise RuntimeError(f"Expected >= 3 rising edges after t_skip={t_skip}, got {len(t_r)}")

    periods = np.diff(np.asarray(t_r, dtype=float))
    duties: list[float] = []
    for k in range(len(t_r) - 1):
        tr0, tr1 = t_r[k], t_r[k + 1]
        tf_in = [tf for tf in t_f if tr0 < tf < tr1]
        if tf_in and tr1 > tr0:
            duties.append(100.0 * (tf_in[0] - tr0) / (tr1 - tr0))

    # 10%-90% rise and 90%-10% fall transition times
    t_r10 = crossings(tw, vw, v_10, direction="rising")
    t_r90 = crossings(tw, vw, v_90, direction="rising")
    t_f90 = crossings(tw, vw, v_90, direction="falling")
    t_f10 = crossings(tw, vw, v_10, direction="falling")

    t_mean = float(np.mean(periods))
    tr_list: list[float] = []
    j = 0
    for tr10 in t_r10:
        while j < len(t_r90) and t_r90[j] <= tr10:
            j += 1
        if j < len(t_r90) and (t_r90[j] - tr10) < 0.25 * t_mean:
            tr_list.append(t_r90[j] - tr10)

    tf_list: list[float] = []
    j = 0
    for tf90 in t_f90:
        while j < len(t_f10) and t_f10[j] <= tf90:
            j += 1
        if j < len(t_f10) and (t_f10[j] - tf90) < 0.25 * t_mean:
            tf_list.append(t_f10[j] - tf90)

    return {
        "n_cycles": int(len(periods)),
        "periods_s": periods,
        "t_mean_s": t_mean,
        "f_mean_mhz": (1.0 / t_mean) * 1e-6,
        "duty_mean_pct": float(np.mean(duties)) if duties else 50.0,
        "t_r_ps": float(np.mean(tr_list) * 1e12) if tr_list else 0.0,
        "t_f_ps": float(np.mean(tf_list) * 1e12) if tf_list else 0.0,
    }


def _freq_from_tran(psf_file: Path) -> tuple[float, float]:
    d = parse_psf_ascii(psf_file)
    t = d["time"]
    stats = _steady_clock_stats(t, d["OUT"], t_skip=0.25 * float(t[-1]))
    vdd_mean = float(np.mean(d["VDD"])) if "VDD" in d else 0.0
    return float(stats["f_mean_mhz"]), vdd_mean


def analyze_temp_vdd(psf_dir: Path, *, vdd_nom: float = 1.2) -> dict[str, object]:
    """Extract temperature TC, supply sensitivity, and total PVT spread from tb_rc_osc_temp_vdd.scs."""
    temp_specs = [
        (-40.0, ["tran_tm40.tran.tran", "tran_tm40.tran"]),
        (0.0, ["tran_t0.tran.tran", "tran_t0.tran"]),
        (27.0, ["tran_t27.tran.tran", "tran_t27.tran"]),
        (85.0, ["tran_t85.tran.tran", "tran_t85.tran"]),
        (125.0, ["tran_t125.tran.tran", "tran_t125.tran"]),
    ]

    temp_rows: list[dict[str, float]] = []
    f_nom = 0.0
    vdd_actual_nom = vdd_nom
    for tc, pats in temp_specs:
        pf = find_single(psf_dir, pats)
        f_mhz, vdd_m = _freq_from_tran(pf)
        temp_rows.append({"temp_c": tc, "f_mhz": f_mhz})
        if abs(tc - 27.0) < 1e-6:
            f_nom = f_mhz
            if vdd_m > 0.1:
                vdd_actual_nom = vdd_m

    for row in temp_rows:
        row["df_pct"] = (row["f_mhz"] - f_nom) / f_nom * 100.0

    f_lo, v_lo = _freq_from_tran(find_single(psf_dir, ["tran_vlo.tran.tran", "tran_vlo.tran"]))
    f_hi, v_hi = _freq_from_tran(find_single(psf_dir, ["tran_vhi.tran.tran", "tran_vhi.tran"]))
    if v_lo <= 0.1:
        v_lo = 0.9 * vdd_actual_nom
    if v_hi <= 0.1:
        v_hi = 1.1 * vdd_actual_nom

    vdd_rows = [
        {"vdd_v": v_lo, "f_mhz": f_lo, "df_pct": (f_lo - f_nom) / f_nom * 100.0},
        {"vdd_v": vdd_actual_nom, "f_mhz": f_nom, "df_pct": 0.0},
        {"vdd_v": v_hi, "f_mhz": f_hi, "df_pct": (f_hi - f_nom) / f_nom * 100.0},
    ]

    f_temps = [r["f_mhz"] for r in temp_rows]
    t_span = temp_rows[-1]["temp_c"] - temp_rows[0]["temp_c"]
    temp_drift_pct = (max(f_temps) - min(f_temps)) / f_nom * 100.0
    tc_ppm_per_c = (max(f_temps) - min(f_temps)) / (f_nom * t_span) * 1e6

    vdd_sens_pct_per_v = abs(f_hi - f_lo) / (f_nom * max(v_hi - v_lo, 1e-9)) * 100.0
    vdd_drift_pct = abs(f_hi - f_lo) / f_nom * 100.0

    f_all = f_temps + [f_lo, f_hi]
    total_pvt_spread_pct = (max(f_all) - min(f_all)) / f_nom * 100.0

    return {
        "f_nom_mhz": f_nom,
        "temp_drift_pct": temp_drift_pct,
        "tc_ppm_per_c": tc_ppm_per_c,
        "vdd_sens_pct_per_v": vdd_sens_pct_per_v,
        "vdd_drift_pct": vdd_drift_pct,
        "total_pvt_spread_pct": total_pvt_spread_pct,
        "temp_points": temp_rows,
        "vdd_points": vdd_rows,
    }


def analyze_trim_startup(
    psf_dir: Path,
    *,
    t_en: float = 200.0e-9,
    codes: list[int] | None = None,
) -> dict[str, object]:
    """Extract 5-bit trim linearity/range and EN cold-startup settling from tb_rc_osc_trim_startup.scs."""
    if codes is None:
        codes = [0, 4, 8, 12, 16, 20, 24, 31]

    trim_rows: list[dict[str, float | int]] = []
    for idx, code in enumerate(codes):
        pf = find_single(psf_dir, [f"tran_trim_{idx}.tran.tran", f"tran_trim_{idx}.tran"])
        d = parse_psf_ascii(pf)
        t = d["time"]
        st = _steady_clock_stats(t, d["OUT"], t_skip=0.25 * float(t[-1]))
        code_meas = int(round(float(np.median(d["VTRIM"])))) if "VTRIM" in d else code
        trim_rows.append({"code": code_meas, "f_mhz": float(st["f_mean_mhz"])})

    # Reference midpoint (code 16 if present, else center element)
    mid_row = min(trim_rows, key=lambda r: abs(int(r["code"]) - 16))
    f_mid = float(mid_row["f_mhz"])
    for r in trim_rows:
        r["df_pct"] = (float(r["f_mhz"]) - f_mid) / f_mid * 100.0

    f_arr = np.array([float(r["f_mhz"]) for r in trim_rows], dtype=float)
    c_arr = np.array([float(r["code"]) for r in trim_rows], dtype=float)
    df_arr = np.array([float(r["df_pct"]) for r in trim_rows], dtype=float)

    trim_range_pct = float((np.max(f_arr) - np.min(f_arr)) / f_mid * 100.0)
    step_per_lsb = np.diff(df_arr) / np.maximum(np.diff(c_arr), 1.0)
    monotonic = bool(np.all(np.diff(f_arr) > 0.0) or np.all(np.diff(f_arr) < 0.0))

    # Part B: Cold startup transient from EN rising edge
    st_file = find_single(psf_dir, ["tran_startup.tran.tran", "tran_startup.tran"])
    ds = parse_psf_ascii(st_file)
    t_s = ds["time"]
    en_s = ds["EN"]
    out_s = ds["OUT"]
    isup_s = np.abs(ds["VSUP:p"])

    en_mid = 0.5 * (float(np.max(en_s)) + float(np.min(en_s)))
    en_cross = crossings(t_s, en_s, en_mid, direction="rising")
    t_en_ref = en_cross[0] if en_cross else t_en

    off_mask = (t_s >= 20e-9) & (t_s <= max(t_en_ref - 20e-9, 40e-9))
    ss_mask = t_s >= 0.70 * float(t_s[-1])
    i_shdn_na = float(np.median(isup_s[off_mask]) * 1e9) if np.any(off_mask) else 0.0
    dt_ss = max(float(t_s[ss_mask][-1] - t_s[ss_mask][0]), 1e-15)
    i_dd_ua = float(trapz(isup_s[ss_mask], t_s[ss_mask]) / dt_ss * 1e6)

    out_mid = 0.5 * (float(np.max(out_s[ss_mask])) + float(np.min(out_s[ss_mask])))
    t_r_all = crossings(t_s, out_s, out_mid, direction="rising")
    t_r = [tr for tr in t_r_all if tr > t_en_ref]
    if len(t_r) < 6:
        raise RuntimeError(f"Expected >= 6 startup cycles after EN rising edge, got {len(t_r)}")

    t_r_arr = np.asarray(t_r, dtype=float)
    per_arr = np.diff(t_r_arr)
    f_inst = 1.0 / per_arr
    n_ss = min(10, max(len(f_inst) // 3, 3))
    f_ss = float(np.median(f_inst[-n_ss:]))

    first_cycle_err_pct = float((f_inst[0] - f_ss) / f_ss * 100.0)
    rel_err = np.abs(f_inst - f_ss) / f_ss
    bad = np.where(rel_err > 0.01)[0]
    if len(bad) == 0:
        idx_settle = 0
    else:
        idx_settle = min(int(bad[-1]) + 1, len(t_r_arr) - 1)
    t_startup_1pct_us = float((t_r_arr[idx_settle] - t_en_ref) * 1e6)

    return {
        "n_trim_points": int(len(trim_rows)),
        "f_trim_min_mhz": float(np.min(f_arr)),
        "f_trim_mid_mhz": f_mid,
        "f_trim_max_mhz": float(np.max(f_arr)),
        "trim_range_pct": trim_range_pct,
        "trim_half_range_pct": 0.5 * trim_range_pct,
        "trim_step_pct_per_lsb": float(np.mean(step_per_lsb)),
        "monotonic": monotonic,
        "f_startup_settled_mhz": f_ss * 1e-6,
        "t_startup_1pct_us": t_startup_1pct_us,
        "startup_cycles_to_1pct": int(idx_settle),
        "first_cycle_err_pct": first_cycle_err_pct,
        "i_dd_ua": i_dd_ua,
        "i_shdn_na": i_shdn_na,
        "trim_codes": trim_rows,
    }


def analyze_jitter_duty(
    psf_dir: Path,
    *,
    max_jitter_ps: float = 80.0,
    max_duty_err_pct: float = 2.0,
) -> dict[str, object]:
    """Extract period jitter, C2C jitter, duty cycle, and edge times from tb_rc_osc_jitter_duty.scs."""
    tr_file = find_single(
        psf_dir, ["tran_jit.tran.tran", "tran_jit.tran", "*.tran.tran", "*.tran"]
    )
    d = parse_psf_ascii(tr_file)
    t = d["time"]
    out = d["OUT"]

    t_skip = min(0.5e-6, 0.05 * float(t[-1]))
    st = _steady_clock_stats(t, out, t_skip=t_skip)
    periods = np.asarray(st["periods_s"], dtype=float)
    per_jit_rms_ps = float(np.std(periods, ddof=1) * 1e12)
    per_jit_pp_ps = float((np.max(periods) - np.min(periods)) * 1e12)
    c2c_jit_rms_ps = float(np.std(np.diff(periods), ddof=1) * 1e12)
    duty_mean = float(st["duty_mean_pct"])
    duty_err = abs(duty_mean - 50.0)

    ss = t >= t_skip
    i_dd_ua = (
        float(abs(trapz(d["VSUP:p"][ss], t[ss]) / max(float(t[ss][-1] - t[ss][0]), 1e-15)) * 1e6)
        if "VSUP:p" in d
        else 0.0
    )

    return {
        "n_cycles": int(st["n_cycles"]),
        "f_mean_mhz": float(st["f_mean_mhz"]),
        "t_per_mean_ns": float(st["t_mean_s"]) * 1e9,
        "period_jitter_rms_ps": per_jit_rms_ps,
        "period_jitter_pp_ps": per_jit_pp_ps,
        "c2c_jitter_rms_ps": c2c_jit_rms_ps,
        "c2c_to_per_ratio": c2c_jit_rms_ps / max(per_jit_rms_ps, 1e-12),
        "duty_mean_pct": duty_mean,
        "duty_err_pct": duty_err,
        "t_r_ps": float(st["t_r_ps"]),
        "t_f_ps": float(st["t_f_ps"]),
        "i_dd_ua": i_dd_ua,
        "max_jitter_spec_ps": max_jitter_ps,
        "jitter_pass": bool(per_jit_rms_ps <= max_jitter_ps),
        "duty_pass": bool(duty_err <= max_duty_err_pct),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze RC Relaxation Oscillator Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_tv = sub.add_parser("temp_vdd", help="Extract temp drift, TC & VDD sensitivity from tb_rc_osc_temp_vdd.scs")
    p_tv.add_argument("psf_dir", type=Path)
    p_tv.add_argument("--vdd-nom", type=float, default=1.2)

    p_ts = sub.add_parser("trim_startup", help="Extract trim linearity & cold startup from tb_rc_osc_trim_startup.scs")
    p_ts.add_argument("psf_dir", type=Path)
    p_ts.add_argument("--t-en", type=float, default=200.0e-9)
    p_ts.add_argument("--codes", type=str, default="0,4,8,12,16,20,24,31")

    p_jd = sub.add_parser("jitter_duty", help="Extract RMS/C2C jitter, duty cycle & rise/fall from tb_rc_osc_jitter_duty.scs")
    p_jd.add_argument("psf_dir", type=Path)
    p_jd.add_argument("--max-jitter-ps", type=float, default=80.0)
    p_jd.add_argument("--max-duty-err-pct", type=float, default=2.0)

    args = ap.parse_args(argv)
    if args.mode == "temp_vdd":
        res = analyze_temp_vdd(args.psf_dir, vdd_nom=args.vdd_nom)
    elif args.mode == "trim_startup":
        code_list = [int(x) for x in args.codes.split(",") if x.strip()]
        res = analyze_trim_startup(args.psf_dir, t_en=args.t_en, codes=code_list)
    else:
        res = analyze_jitter_duty(
            args.psf_dir,
            max_jitter_ps=args.max_jitter_ps,
            max_duty_err_pct=args.max_duty_err_pct,
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
