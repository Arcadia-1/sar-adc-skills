#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from the standalone LDO testbench suite.

Usage:
  python analyze_ldo.py dc_reg <psf_dir> [--vref 0.9]
  python analyze_ldo.py stb <psf_dir>
  python analyze_ldo.py psrr_zout_noise <psf_dir>
  python analyze_ldo.py tran <psf_dir> [--t-ld1 1e-6] [--t-ld2 3e-6] [--t-ln1 5e-6]
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

from psf_utils import find_single, parse_psf_ascii, trapz


def analyze_dc_reg(psf_dir: Path, *, vref: float) -> dict[str, float]:
    f_line = find_single(psf_dir, ["dc_line.dc", "*line*.dc"])
    dl = parse_psf_ascii(f_line)
    vdd = dl["VDD"] if "VDD" in dl else dl[next(iter(dl))]
    vout_l = dl["VOUT"]
    v_nom = float(vout_l[-1])

    # Dropout voltage = VDD - VOUT where VOUT falls 2% below nominal
    in_reg = vout_l >= 0.98 * v_nom
    idx_do = int(np.where(in_reg)[0][0]) if np.any(in_reg) else 0
    v_dropout = float(vdd[idx_do] - vout_l[idx_do])

    # Line regulation over well-regulated upper region [VDD >= v_nom + 0.3 V]
    reg_mask = vdd >= (v_nom + 0.3)
    if np.sum(reg_mask) >= 2:
        line_reg_mv_per_v = float(
            (vout_l[reg_mask][-1] - vout_l[reg_mask][0]) / (vdd[reg_mask][-1] - vdd[reg_mask][0]) * 1e3
        )
    else:
        line_reg_mv_per_v = float("nan")

    f_load = find_single(psf_dir, ["dc_load.dc", "*load*.dc"])
    di = parse_psf_ascii(f_load)
    sweep_key = next(k for k in di if k not in {"VOUT", "VDD", "VSUP:p"})
    iload = di[sweep_key]
    vout_i = di["VOUT"]
    load_reg_mv_per_ma = float(abs(vout_i[0] - vout_i[-1]) / ((iload[-1] - iload[0]) * 1e3) * 1e3)

    res: dict[str, float] = {
        "vout_nom_v": v_nom,
        "vout_err_pct": (v_nom - vref) / vref * 100.0,
        "dropout_mv": v_dropout * 1e3,
        "line_reg_mv_per_v": line_reg_mv_per_v,
        "load_reg_mv_per_ma": load_reg_mv_per_ma,
    }
    if "VSUP:p" in di:
        i_sup = np.abs(di["VSUP:p"])
        iq_ua = float(np.median(i_sup - iload) * 1e6)
        res["iq_ua"] = iq_ua
        res["current_eff_max_pct"] = float(iload[-1] / i_sup[-1] * 100.0)
    return res


def analyze_stb(psf_dir: Path) -> dict[str, float]:
    f = find_single(psf_dir, ["stb.stb", "*.stb.stb"])
    d = parse_psf_ascii(f)
    freq = np.real(d["freq"])
    lg = d["loopGain"]
    if np.real(lg[0]) < 0:
        lg = -lg
    mag_db = 20.0 * np.log10(np.maximum(np.abs(lg), 1e-30))
    phase_deg = np.degrees(np.unwrap(np.angle(lg)))

    ugf = float("nan")
    pm_deg = float("nan")
    for i in range(len(mag_db) - 1):
        if mag_db[i] >= 0.0 > mag_db[i + 1]:
            frac = (0.0 - mag_db[i]) / (mag_db[i + 1] - mag_db[i])
            ugf = float(10.0 ** (math.log10(freq[i]) + frac * (math.log10(freq[i + 1]) - math.log10(freq[i]))))
            pm_deg = 180.0 + float(phase_deg[i] + frac * (phase_deg[i + 1] - phase_deg[i]))
            break

    gm_db = float("inf")
    for i in range(len(phase_deg) - 1):
        if phase_deg[i] >= -180.0 > phase_deg[i + 1]:
            frac = (-180.0 - phase_deg[i]) / (phase_deg[i + 1] - phase_deg[i])
            gm_db = -float(mag_db[i] + frac * (mag_db[i + 1] - mag_db[i]))
            break

    return {
        "dc_loop_gain_db": float(mag_db[0]),
        "ugf_mhz": ugf * 1e-6 if math.isfinite(ugf) else float("nan"),
        "phase_margin_deg": pm_deg,
        "gain_margin_db": gm_db,
    }


def analyze_psrr_zout_noise(psf_dir: Path) -> dict[str, float]:
    f_ac = find_single(psf_dir, ["ac.ac", "*.ac.ac", "*.ac"])
    dac = parse_psf_ascii(f_ac)
    freq = np.real(dac["freq"])
    log_f = np.log10(freq)

    h_psrr = np.abs(dac["VOUT"]) / np.maximum(np.abs(dac.get("VDD", np.ones_like(dac["VOUT"]))), 1e-30)
    psrr_db = -20.0 * np.log10(np.maximum(h_psrr, 1e-30))
    zout = np.abs(dac["VOUT_Z"])

    def at(arr: np.ndarray, f_hz: float) -> float:
        return float(np.interp(math.log10(f_hz), log_f, arr))

    f_n = find_single(psf_dir, ["noise.noise", "*.noise"])
    dn = parse_psf_ascii(f_n)
    fn = np.real(dn["freq"])
    vn = np.real(dn["out"])
    vrms = math.sqrt(max(trapz(vn**2, fn), 0.0))

    return {
        "psrr_dc_db": float(psrr_db[0]),
        "psrr_100khz_db": at(psrr_db, 1e5),
        "psrr_1mhz_db": at(psrr_db, 1e6),
        "psrr_100mhz_db": at(psrr_db, 1e8),
        "psrr_min_db": float(np.min(psrr_db)),
        "zout_dc_ohm": float(zout[0]),
        "zout_1mhz_ohm": at(zout, 1e6),
        "zout_peak_ohm": float(np.max(zout)),
        "output_noise_uvrms": vrms * 1e6,
    }


def analyze_tran(psf_dir: Path, *, t_ld1: float, t_ld2: float, t_ln1: float) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vout = d["VOUT"]

    v_nom = float(np.mean(vout[(t > 0.2 * t_ld1) & (t < 0.95 * t_ld1)]))
    m_ld1 = (t >= t_ld1) & (t < t_ld2)
    m_ld2 = (t >= t_ld2) & (t < t_ln1)
    m_ln1 = t >= t_ln1

    undershoot = (v_nom - float(np.min(vout[m_ld1]))) * 1e3
    overshoot = (float(np.max(vout[m_ld2])) - v_nom) * 1e3
    v_pre_ln = float(np.mean(vout[(t > t_ln1 - 0.5e-6) & (t < t_ln1)]))
    line_glitch = float(np.max(np.abs(vout[m_ln1] - v_pre_ln)) * 1e3)

    return {
        "vout_nom_v": v_nom,
        "load_undershoot_mv": undershoot,
        "load_overshoot_mv": overshoot,
        "line_step_glitch_mv": line_glitch,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze LDO Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_dc = sub.add_parser("dc_reg")
    p_dc.add_argument("psf_dir", type=Path)
    p_dc.add_argument("--vref", type=float, default=0.9)

    p_stb = sub.add_parser("stb")
    p_stb.add_argument("psf_dir", type=Path)

    p_pn = sub.add_parser("psrr_zout_noise")
    p_pn.add_argument("psf_dir", type=Path)

    p_tr = sub.add_parser("tran")
    p_tr.add_argument("psf_dir", type=Path)
    p_tr.add_argument("--t-ld1", type=float, default=1e-6)
    p_tr.add_argument("--t-ld2", type=float, default=3e-6)
    p_tr.add_argument("--t-ln1", type=float, default=5e-6)

    args = ap.parse_args(argv)
    if args.mode == "dc_reg":
        res = analyze_dc_reg(args.psf_dir, vref=args.vref)
    elif args.mode == "stb":
        res = analyze_stb(args.psf_dir)
    elif args.mode == "psrr_zout_noise":
        res = analyze_psrr_zout_noise(args.psf_dir)
    else:
        res = analyze_tran(args.psf_dir, t_ld1=args.t_ld1, t_ld2=args.t_ld2, t_ln1=args.t_ln1)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
