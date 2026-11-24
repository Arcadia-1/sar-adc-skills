#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from SerDes Bridged T-Coil testbench.

Usage:
  python analyze_tcoil.py <psf_dir>
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

from psf_utils import find_single, parse_psf_ascii


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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze SerDes Bridged T-Coil Spectre outputs.")
    ap.add_argument("psf_dir", type=Path)
    args = ap.parse_args(argv)
    print(json.dumps(analyze_tcoil(args.psf_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
