#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from SerDes Bridged T-Coil & RX Front-End testbenches.

Usage:
  python analyze_tcoil.py <psf_dir>
  python analyze_tcoil.py --mode rx_frontend <psf_dir>
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

from psf_utils import find_single, mixed_mode_s_params, parse_psf_ascii


def _f3db(freq: np.ndarray, mag_db: np.ndarray) -> float:
    ref = float(mag_db[0]) - 3.0
    for i in range(len(mag_db) - 1):
        if mag_db[i] >= ref > mag_db[i + 1]:
            frac = (ref - mag_db[i]) / (mag_db[i + 1] - mag_db[i])
            return float(10.0 ** (math.log10(freq[i]) + frac * (math.log10(freq[i + 1]) - math.log10(freq[i]))))
    return float("nan")


def analyze_tcoil(psf_dir: Path) -> dict[str, float]:
    f_ac = find_single(psf_dir, ["ac.ac", "*.ac.ac", "*.ac"])
    dac = parse_psf_ascii(f_ac)
    freq = np.real(dac["freq"])
    bare_db = 20.0 * np.log10(np.maximum(np.abs(dac["V_BARE"]), 1e-30))
    tc_db = 20.0 * np.log10(np.maximum(np.abs(dac["V_TCOIL_MID"]), 1e-30))

    f3_bare = _f3db(freq, bare_db)
    f3_tc = _f3db(freq, tc_db)
    peaking = float(np.max(tc_db) - tc_db[0])

    f_sp = find_single(psf_dir, ["sp.sp", "*.sp.sp", "*.sp"])
    dsp = parse_psf_ascii(f_sp)
    fsp = np.real(dsp["freq"])
    s11_key = next(k for k in ("s11", "S11", "s(1,1)") if k in dsp)
    s11_db = 20.0 * np.log10(np.maximum(np.abs(dsp[s11_key]), 1e-30))
    m_20g = fsp <= 20e9

    f_tr = find_single(psf_dir, ["*.tran", "tran.tran*"])
    dtr = parse_psf_ascii(f_tr)
    t = dtr["time"]
    vb = dtr["VT_BARE"]
    vt = dtr["VT_TCOIL"]
    v_fin = float(np.mean(vt[t >= 0.8 * float(t[-1])]))
    overshoot_pct = max((float(np.max(vt)) - v_fin) / max(abs(v_fin), 1e-9) * 100.0, 0.0)

    def tr_20_80(y: np.ndarray) -> float:
        vf = float(np.mean(y[t >= 0.8 * float(t[-1])]))
        idx20 = np.where(y >= 0.2 * vf)[0]
        idx80 = np.where(y >= 0.8 * vf)[0]
        if len(idx20) == 0 or len(idx80) == 0:
            return float("nan")
        return float(t[idx80[0]] - t[idx20[0]])

    return {
        "bare_f3db_ghz": f3_bare / 1e9,
        "tcoil_f3db_ghz": f3_tc / 1e9,
        "bw_extension_ratio": f3_tc / f3_bare if f3_bare > 0 else float("nan"),
        "tcoil_peaking_db": peaking,
        "s11_worst_to_20ghz_db": float(np.max(s11_db[m_20g])),
        "bare_tr_20_80_ps": tr_20_80(vb) * 1e12,
        "tcoil_tr_20_80_ps": tr_20_80(vt) * 1e12,
        "tcoil_step_overshoot_pct": overshoot_pct,
    }


def analyze_rx_frontend(psf_dir: Path) -> dict[str, float]:
    f_sp = find_single(psf_dir, ["sp.sp", "*.sp.sp", "*.sp"])
    dsp = parse_psf_ascii(f_sp)
    freq = np.real(dsp["freq"])
    log_f = np.log10(freq)
    mm = mixed_mode_s_params(dsp, in_p=1, in_n=2, out_p=3, out_n=4)

    def db(arr: np.ndarray) -> np.ndarray:
        return 20.0 * np.log10(np.maximum(np.abs(arr), 1e-30))

    sdd11 = db(mm["sdd11"])
    scd11 = db(mm["scd11"])
    sdd21 = db(mm["sdd21"])
    scd21 = db(mm["scd21"])
    sdc21 = db(mm["sdc21"])

    def at(arr: np.ndarray, f_hz: float) -> float:
        return float(np.interp(math.log10(f_hz), log_f, arr))

    m_10g = freq <= 10e9
    m_20g = freq <= 20e9
    return {
        "sdd11_5ghz_db": at(sdd11, 5e9),
        "sdd11_10ghz_db": at(sdd11, 10e9),
        "sdd11_worst_to_10ghz_db": float(np.max(sdd11[m_10g])),
        "sdd11_worst_to_20ghz_db": float(np.max(sdd11[m_20g])),
        "scd11_10ghz_db": at(scd11, 10e9),
        "scd11_worst_to_20ghz_db": float(np.max(scd11[m_20g])),
        "sdd21_dc_db": float(sdd21[0]),
        "sdd21_10ghz_db": at(sdd21, 10e9),
        "scd21_10ghz_db": at(scd21, 10e9),
        "scd21_worst_to_20ghz_db": float(np.max(scd21[m_20g])),
        "sdc21_10ghz_db": at(sdc21, 10e9),
        "sdc21_worst_to_20ghz_db": float(np.max(sdc21[m_20g])),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze SerDes Bridged T-Coil & RX Front-End Spectre outputs.")
    ap.add_argument("psf_dir", type=Path)
    ap.add_argument("--mode", choices=["bw", "rx_frontend"], default="bw")
    args = ap.parse_args(argv)
    if args.mode == "rx_frontend":
        res = analyze_rx_frontend(args.psf_dir)
    else:
        res = analyze_tcoil(args.psf_dir)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
