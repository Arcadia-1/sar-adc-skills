#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from the LDO testbenches.

Usage:
  python analyze_ldo.py stb <psf_dir>
  python analyze_ldo.py psrr_noise <psf_dir>
  python analyze_ldo.py load_tran <psf_dir> [--t-step1 1e-6] [--t-step2 3e-6]
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


def analyze_stb(psf_dir: Path) -> dict[str, float]:
    f = find_single(psf_dir, ["stb.stb", "*.stb.stb"])
    d = parse_psf_ascii(f)
    freq = np.real(d["freq"])
    # Spectre stb loopGain is T(s) with negative-feedback convention where DC phase ~ 0 deg
    # (or 180 deg if probe orientation is inverted); normalize so low-freq phase starts at 0 deg.
    lg = d["loopGain"]
    if np.real(lg[0]) < 0:
        lg = -lg
    mag_db = 20.0 * np.log10(np.maximum(np.abs(lg), 1e-30))
    phase_deg = np.degrees(np.unwrap(np.angle(lg)))

    t0_db = float(mag_db[0])

    # Unity-gain frequency (first downward 0 dB crossing)
    ugf = float("nan")
    pm_deg = float("nan")
    for i in range(len(mag_db) - 1):
        if mag_db[i] >= 0.0 > mag_db[i + 1]:
            frac = (0.0 - mag_db[i]) / (mag_db[i + 1] - mag_db[i])
            ugf = float(10.0 ** (math.log10(freq[i]) + frac * (math.log10(freq[i + 1]) - math.log10(freq[i]))))
            ph_ugf = float(phase_deg[i] + frac * (phase_deg[i + 1] - phase_deg[i]))
            pm_deg = 180.0 + ph_ugf
            break

    # Gain margin (first downward -180 deg crossing)
    gm_db = float("inf")
    for i in range(len(phase_deg) - 1):
        if phase_deg[i] >= -180.0 > phase_deg[i + 1]:
            frac = (-180.0 - phase_deg[i]) / (phase_deg[i + 1] - phase_deg[i])
            gain_at_180 = float(mag_db[i] + frac * (mag_db[i + 1] - mag_db[i]))
            gm_db = -gain_at_180
            break

    return {
        "dc_loop_gain_db": t0_db,
        "ugf_mhz": ugf * 1e-6 if math.isfinite(ugf) else float("nan"),
        "phase_margin_deg": pm_deg,
        "gain_margin_db": gm_db,
    }


def analyze_psrr_noise(psf_dir: Path) -> dict[str, float]:
    res: dict[str, float] = {}
    f_ac = find_single(psf_dir, ["*.ac", "ac.ac*"])
    dac = parse_psf_ascii(f_ac)
    freq_ac = np.real(dac["freq"])
    h_psrr = np.abs(dac["VOUT"]) / np.maximum(np.abs(dac.get("VDD", np.ones_like(dac["VOUT"]))), 1e-30)
    psrr_db = -20.0 * np.log10(np.maximum(h_psrr, 1e-30))

    def psrr_at(f_target: float) -> float:
        return float(np.interp(math.log10(f_target), np.log10(freq_ac), psrr_db))

    res["psrr_dc_db"] = float(psrr_db[0])
    res["psrr_100khz_db"] = psrr_at(1e5)
    res["psrr_1mhz_db"] = psrr_at(1e6)
    res["psrr_100mhz_db"] = psrr_at(1e8)
    res["psrr_min_db"] = float(np.min(psrr_db))
    res["psrr_min_freq_mhz"] = float(freq_ac[int(np.argmin(psrr_db))] * 1e-6)

    f_noise = find_single(psf_dir, ["*.noise", "noise.noise*"])
    dn = parse_psf_ascii(f_noise)
    freq_n = np.real(dn["freq"])
    out_n = np.real(dn["out"])  # V/sqrt(Hz)
    vrms = math.sqrt(max(trapz(out_n**2, freq_n), 0.0))
    res["noise_f_start_hz"] = float(freq_n[0])
    res["noise_f_stop_mhz"] = float(freq_n[-1] * 1e-6)
    res["output_noise_uvrms"] = vrms * 1e6
    return res


def analyze_load_tran(psf_dir: Path, *, t_step1: float, t_step2: float) -> dict[str, float]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    t = d["time"]
    vout = d["VOUT"]

    pre_mask = (t > 0.2 * t_step1) & (t < 0.95 * t_step1)
    v_nom = float(np.mean(vout[pre_mask]))

    step1_mask = (t >= t_step1) & (t < t_step2)
    step2_mask = t >= t_step2

    v_min_1 = float(np.min(vout[step1_mask]))
    v_max_2 = float(np.max(vout[step2_mask]))
    v_hi_ss = float(np.mean(vout[(t > t_step2 - 0.1 * (t_step2 - t_step1)) & (t < t_step2)]))

    return {
        "vout_nom_v": v_nom,
        "load_reg_mv": (v_nom - v_hi_ss) * 1e3,
        "undershoot_mv": (v_nom - v_min_1) * 1e3,
        "overshoot_mv": (v_max_2 - v_nom) * 1e3,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze LDO Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_stb = sub.add_parser("stb", help="Extract T0, UGF, PM, GM from tb_ldo_stb.scs")
    p_stb.add_argument("psf_dir", type=Path)

    p_pn = sub.add_parser("psrr_noise", help="Extract PSRR(f) and output noise from tb_ldo_psrr_noise.scs")
    p_pn.add_argument("psf_dir", type=Path)

    p_tr = sub.add_parser("load_tran", help="Extract droop/overshoot from tb_ldo_load_tran.scs")
    p_tr.add_argument("psf_dir", type=Path)
    p_tr.add_argument("--t-step1", type=float, default=1e-6)
    p_tr.add_argument("--t-step2", type=float, default=3e-6)

    args = ap.parse_args(argv)
    if args.mode == "stb":
        res = analyze_stb(args.psf_dir)
    elif args.mode == "psrr_noise":
        res = analyze_psrr_noise(args.psf_dir)
    else:
        res = analyze_load_tran(args.psf_dir, t_step1=args.t_step1, t_step2=args.t_step2)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
