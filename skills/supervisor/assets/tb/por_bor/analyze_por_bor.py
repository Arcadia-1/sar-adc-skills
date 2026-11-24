#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from POR/BOR Supervisor testbenches.

Usage:
  python analyze_por_bor.py thresholds <psf_dir> [--min-hys-mv 30.0]
  python analyze_por_bor.py ramps <psf_dir> [--v-por-rise 1.05]
  python analyze_por_bor.py glitch <psf_dir> [--v-por-rise 1.05]
  python analyze_por_bor.py bor_levels <psf_dir> [--n-codes 8]
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

from psf_utils import crossings, dnl_inl_from_transfer, find_single, parse_psf_ascii


def _vdd_current_key(d: dict[str, np.ndarray]) -> str | None:
    for cand in ("VSUP:p", "VSUP_MON:p"):
        if cand in d:
            return cand
    for k in d:
        if k.upper().endswith(":P") and "SUP" in k.upper():
            return k
    return None


def _extract_triangle_metrics(
    d: dict[str, np.ndarray],
    *,
    vdd_valid_min: float = 0.25,
) -> dict[str, float]:
    """Extract V_POR+, V_POR-, V_hys, low-VDD glitch, and plateau I_q from a triangle VDD ramp."""
    t = d["time"]
    vdd = d["VDD"]
    rstb = d["RSTB"]

    vdd_max = float(np.max(vdd))
    plat_idx = np.where(vdd >= 0.995 * vdd_max)[0]
    if len(plat_idx) < 2:
        raise RuntimeError(f"Could not locate VDD plateau (vdd_max={vdd_max:.3f} V)")
    i_p0 = int(plat_idx[0])
    i_p1 = int(plat_idx[-1])
    t_p0 = float(t[i_p0])
    t_p1 = float(t[i_p1])

    # Rising leg: [0, t_p0 + tiny margin], Falling leg: [t_p1 - tiny margin, t_end]
    # Use RSTB - 0.5*VDD midpoint crossing so detection works across all BOR levels
    # and transistor-level CMOS rail-tracking outputs.
    m_rise = (t <= t_p0 + 0.2 * (t_p1 - t_p0)) & (vdd >= vdd_valid_min)
    m_fall = (t >= t_p1 - 0.2 * (t_p1 - t_p0)) & (vdd >= vdd_valid_min)

    tr, vr, rr = t[m_rise], vdd[m_rise], rstb[m_rise]
    tf, vf, rf = t[m_fall], vdd[m_fall], rstb[m_fall]

    rise_x = crossings(tr, rr - 0.5 * vr, 0.0, direction="rising")
    fall_x = crossings(tf, rf - 0.5 * vf, 0.0, direction="falling")
    if not rise_x:
        raise RuntimeError("RSTB never released (no rising crossing of 0.5*VDD on up-ramp)")
    if not fall_x:
        raise RuntimeError("RSTB never asserted (no falling crossing of 0.5*VDD on down-ramp)")

    t_rise = rise_x[-1]
    t_fall = fall_x[0]
    v_por_rise = float(np.interp(t_rise, t, vdd))
    v_por_fall = float(np.interp(t_fall, t, vdd))
    v_hys_mv = (v_por_rise - v_por_fall) * 1e3

    # Low-VDD cold-boot glitch audit: peak RSTB while VDD is below (V_POR+ - 50 mV)
    m_low = (t <= t_rise) & (vdd >= 0.02) & (vdd <= max(v_por_rise - 0.05, 0.1))
    max_glitch_mv = float(np.max(rstb[m_low]) * 1e3) if np.any(m_low) else 0.0

    # Steady-state quiescent current on middle 60% of flat VDD plateau
    i_key = _vdd_current_key(d)
    t_q0 = t_p0 + 0.2 * (t_p1 - t_p0)
    t_q1 = t_p0 + 0.8 * (t_p1 - t_p0)
    m_q = (t >= t_q0) & (t <= t_q1)
    if i_key is not None and np.any(m_q):
        iq_na = float(np.median(np.abs(d[i_key][m_q])) * 1e9)
    else:
        iq_na = 0.0

    rstb_plat = float(np.median(rstb[m_q])) if np.any(m_q) else float(np.max(rstb))
    return {
        "v_por_rise_v": v_por_rise,
        "v_por_fall_v": v_por_fall,
        "v_hys_mv": v_hys_mv,
        "max_glitch_low_vdd_mv": max_glitch_mv,
        "n_rise_edges": int(len(rise_x)),
        "iq_na": iq_na,
        "vdd_max_v": vdd_max,
        "rstb_high_v": rstb_plat,
    }


def analyze_thresholds(
    psf_dir: Path,
    *,
    min_hys_mv: float = 30.0,
    max_glitch_mv: float = 100.0,
) -> dict[str, object]:
    f = find_single(psf_dir, ["tran_hys.tran.tran", "tran_hys.tran", "*.tran.tran", "*.tran"])
    d = parse_psf_ascii(f)
    m = _extract_triangle_metrics(d)
    hys_pass = bool(m["v_hys_mv"] >= min_hys_mv)
    clamp_pass = bool(m["max_glitch_low_vdd_mv"] <= max_glitch_mv)
    return {
        **m,
        "hys_pass": hys_pass,
        "low_vdd_clamp_pass": clamp_pass,
        "pass": bool(hys_pass and clamp_pass),
    }


def analyze_ramps(
    psf_dir: Path,
    *,
    v_por_rise: float = 1.05,
    max_glitch_mv: float = 100.0,
) -> dict[str, object]:
    specs = [
        ("fast", ["tran_fast.tran.tran", "tran_fast.tran", "*fast*.tran*"]),
        ("med", ["tran_med.tran.tran", "tran_med.tran", "*med*.tran*"]),
        ("slow", ["tran_slow.tran.tran", "tran_slow.tran", "*slow*.tran*"]),
    ]
    per_ramp: dict[str, dict[str, object]] = {}
    delays: list[float] = []
    glitches: list[float] = []
    all_clean = True

    for label, pats in specs:
        f = find_single(psf_dir, pats)
        d = parse_psf_ascii(f)
        t = d["time"]
        vdd = d["VDD"]
        rstb = d["RSTB"]

        vdd_final = float(np.median(vdd[t >= 0.9 * float(t[-1])]))
        rstb_final = float(np.median(rstb[t >= 0.9 * float(t[-1])]))

        t_10 = crossings(t, vdd, 0.1 * vdd_final, direction="rising")
        t_90 = crossings(t, vdd, 0.9 * vdd_final, direction="rising")
        ramp_10_90_us = float((t_90[0] - t_10[0]) * 1e6) if (t_10 and t_90) else 0.0

        t_vth_list = crossings(t, vdd, v_por_rise, direction="rising")
        if not t_vth_list:
            raise RuntimeError(f"VDD never crossed v_por_rise={v_por_rise} V in {label} ramp")
        t_vth = t_vth_list[0]

        m_valid = vdd >= 0.25
        rise_edges = crossings(t[m_valid], rstb[m_valid] - 0.5 * vdd[m_valid], 0.0, direction="rising")
        if not rise_edges:
            raise RuntimeError(f"RSTB never released in {label} ramp")
        t_rel = rise_edges[-1]
        v_rel = float(np.interp(t_rel, t, vdd))
        t_rst_delay_us = max((t_rel - t_vth) * 1e6, 0.0)

        m_low = (t <= t_vth) & (vdd >= 0.02) & (vdd <= 0.90 * v_por_rise)
        low_glitch_mv = float(np.max(rstb[m_low]) * 1e3) if np.any(m_low) else 0.0

        clean = bool(
            len(rise_edges) == 1
            and rstb_final >= 0.95 * vdd_final
            and low_glitch_mv <= max_glitch_mv
        )
        all_clean = all_clean and clean
        delays.append(t_rst_delay_us)
        glitches.append(low_glitch_mv)

        per_ramp[label] = {
            "ramp_10_90_us": ramp_10_90_us,
            "v_release_v": v_rel,
            "t_rst_delay_us": t_rst_delay_us,
            "low_vdd_glitch_mv": low_glitch_mv,
            "n_rise_edges": int(len(rise_edges)),
            "rstb_final_v": rstb_final,
            "clean_release": clean,
        }

    return {
        "ramps": per_ramp,
        "t_rst_mean_us": float(np.mean(delays)),
        "t_rst_spread_us": float(np.max(delays) - np.min(delays)),
        "worst_low_vdd_glitch_mv": float(np.max(glitches)),
        "all_clean_release": bool(all_clean),
    }


def analyze_glitch(
    psf_dir: Path,
    *,
    v_por_rise: float = 1.05,
) -> dict[str, object]:
    f = find_single(psf_dir, ["tran_glitch.tran.tran", "tran_glitch.tran", "*.tran.tran", "*.tran"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vdd = d["VDD"]
    rstb = d["RSTB"]
    vdd_nom = float(np.median(vdd[t <= 15e-6]))

    pulses_spec = [
        ("p1_0p5us", 0.5, 20e-6, 20.5e-6, 75e-6, False),
        ("p2_1p5us", 1.5, 80e-6, 81.5e-6, 135e-6, False),
        ("p3_5p0us", 5.0, 140e-6, 145.0e-6, 235e-6, True),
        ("p4_15p0us", 15.0, 240e-6, 255.0e-6, 338e-6, True),
    ]

    results: list[dict[str, object]] = []
    short_ok = True
    long_ok = True

    for name, width_us, t_s, t_e, t_win_end, expect_trig in pulses_spec:
        m_w = (t >= t_s - 1e-6) & (t <= t_win_end)
        tw, vw, rw = t[m_w], vdd[m_w], rstb[m_w]

        # Normalized RSTB/VDD cleanly distinguishes a real reset assertion
        # (RSTB pulled to 0 V -> ratio ~ 0) from rail tracking during a rejected dip
        # (RSTB tracks VDD down to 0.6 V -> ratio ~ 1.0).
        ratio = rw / np.maximum(vw, 0.1)
        min_ratio = float(np.min(ratio))
        min_rstb_v = float(np.min(rw))
        triggered = bool(min_ratio < 0.5)

        # Verify recovery back to HIGH by end of inspection window
        m_end = (tw >= t_win_end - 5e-6) & (tw <= t_win_end)
        rstb_end_v = float(np.median(rw[m_end])) if np.any(m_end) else float(rw[-1])
        recovered_cleanly = bool(rstb_end_v >= 0.95 * vdd_nom)

        # Measure release delay t_rst after VDD rises back across v_por_rise
        t_rst_rec_us = 0.0
        if triggered:
            m_rec = tw >= t_e - 0.5e-6
            vdd_up = crossings(tw[m_rec], vw[m_rec], v_por_rise, direction="rising")
            rst_up = crossings(tw[m_rec], rw[m_rec] - 0.5 * vw[m_rec], 0.0, direction="rising")
            if vdd_up and rst_up:
                t_rst_rec_us = max((rst_up[-1] - vdd_up[0]) * 1e6, 0.0)

        if not expect_trig:
            short_ok = short_ok and (not triggered) and recovered_cleanly
        else:
            long_ok = long_ok and triggered and recovered_cleanly

        results.append({
            "pulse": name,
            "width_us": width_us,
            "expect_trigger": expect_trig,
            "triggered": triggered,
            "min_rstb_over_vdd": min_ratio,
            "min_rstb_v": min_rstb_v,
            "t_rst_recover_us": t_rst_rec_us,
            "recovered_cleanly": recovered_cleanly,
        })

    return {
        "vdd_nom_v": vdd_nom,
        "pulses": results,
        "immune_short": bool(short_ok),
        "detect_long": bool(long_ok),
        "glitch_filter_pass": bool(short_ok and long_ok),
    }


def analyze_bor_levels(psf_dir: Path, *, n_codes: int = 8) -> dict[str, object]:
    codes: list[int] = []
    v_rise: list[float] = []
    v_fall: list[float] = []
    v_hys: list[float] = []
    iq_list: list[float] = []
    glitch_list: list[float] = []

    for c in range(n_codes):
        f = find_single(psf_dir, [f"tran_c{c}.tran.tran", f"tran_c{c}.tran", f"*c{c}*.tran*"])
        d = parse_psf_ascii(f)
        m = _extract_triangle_metrics(d)
        codes.append(c)
        v_rise.append(m["v_por_rise_v"])
        v_fall.append(m["v_por_fall_v"])
        v_hys.append(m["v_hys_mv"])
        iq_list.append(m["iq_na"])
        glitch_list.append(m["max_glitch_low_vdd_mv"])

    vr_arr = np.asarray(v_rise, dtype=float)
    vf_arr = np.asarray(v_fall, dtype=float)
    m_dnl = dnl_inl_from_transfer(vr_arr)

    mono_rise = bool(np.all(np.diff(vr_arr) > 0.0))
    mono_fall = bool(np.all(np.diff(vf_arr) > 0.0))
    return {
        "n_codes": int(n_codes),
        "codes": codes,
        "v_bor_rise_v": [round(x, 6) for x in v_rise],
        "v_bor_fall_v": [round(x, 6) for x in v_fall],
        "v_hys_mv": [round(x, 3) for x in v_hys],
        "step_mv_per_lsb": float(m_dnl["lsb_v"] * 1e3),
        "dnl_max_lsb": float(m_dnl["dnl_abs_max_lsb"]),
        "inl_max_lsb": float(m_dnl["inl_abs_max_lsb"]),
        "hys_min_mv": float(np.min(v_hys)),
        "hys_max_mv": float(np.max(v_hys)),
        "iq_mean_na": float(np.mean(iq_list)),
        "worst_low_vdd_glitch_mv": float(np.max(glitch_list)),
        "monotonic_rise": mono_rise,
        "monotonic_fall": mono_fall,
        "monotonic": bool(mono_rise and mono_fall),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze POR/BOR Supervisor Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_th = sub.add_parser("thresholds", help="Extract V_POR+, V_POR-, V_hys, low-VDD glitch & I_q")
    p_th.add_argument("psf_dir", type=Path)
    p_th.add_argument("--min-hys-mv", type=float, default=30.0)
    p_th.add_argument("--max-glitch-mv", type=float, default=100.0)

    p_rm = sub.add_parser("ramps", help="Extract multi-decade ramp release delay & glitch metrics")
    p_rm.add_argument("psf_dir", type=Path)
    p_rm.add_argument("--v-por-rise", type=float, default=1.05)
    p_rm.add_argument("--max-glitch-mv", type=float, default=100.0)

    p_gl = sub.add_parser("glitch", help="Extract negative VDD glitch immunity & brown-out curve")
    p_gl.add_argument("psf_dir", type=Path)
    p_gl.add_argument("--v-por-rise", type=float, default=1.05)

    p_bl = sub.add_parser("bor_levels", help="Extract programmable 3-bit BOR levels & monotonicity")
    p_bl.add_argument("psf_dir", type=Path)
    p_bl.add_argument("--n-codes", type=int, default=8)

    args = ap.parse_args(argv)
    if args.mode == "thresholds":
        res: object = analyze_thresholds(
            args.psf_dir, min_hys_mv=args.min_hys_mv, max_glitch_mv=args.max_glitch_mv
        )
    elif args.mode == "ramps":
        res = analyze_ramps(
            args.psf_dir, v_por_rise=args.v_por_rise, max_glitch_mv=args.max_glitch_mv
        )
    elif args.mode == "glitch":
        res = analyze_glitch(args.psf_dir, v_por_rise=args.v_por_rise)
    else:
        res = analyze_bor_levels(args.psf_dir, n_codes=args.n_codes)

    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
