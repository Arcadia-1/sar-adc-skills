#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from VCO testbenches.

Usage:
  python analyze_vco.py tuning <psf_dir>
  python analyze_vco.py pss_pnoise <psf_dir> [--vdd 0.9] [--f-low 10e3] [--f-high 40e6]
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
    extract_uniform_strobe,
    find_single,
    integrate_phase_noise_jitter,
    parse_psf_ascii,
    trapz,
)


def analyze_tuning(psf_dir: Path) -> dict[str, object]:
    f = find_single(psf_dir, ["*.tran", "tran.tran*"])
    d = parse_psf_ascii(f)
    _, vctrl, finst_ghz = extract_uniform_strobe(d["time"], d["VCTRL"], d["F_INST"])
    finst = finst_ghz * 1e9  # va_phase_err_mon outputs GHz (freq_scale=1e-9)
    if len(vctrl) < 2:
        raise RuntimeError(f"Expected >= 2 strobed tuning points, got {len(vctrl)}")

    dv = np.diff(vctrl)
    df = np.diff(finst)
    valid = np.abs(dv) > 1e-6
    kvco = df[valid] / dv[valid]  # Hz/V

    f_min = float(np.min(finst))
    f_max = float(np.max(finst))
    f_mid = 0.5 * (f_min + f_max)
    tr_pct = 100.0 * (f_max - f_min) / f_mid if f_mid > 0 else 0.0

    return {
        "n_pts": int(len(vctrl)),
        "f_min_mhz": f_min * 1e-6,
        "f_max_mhz": f_max * 1e-6,
        "tuning_range_pct": tr_pct,
        "kvco_avg_mhz_per_v": float((finst[-1] - finst[0]) / (vctrl[-1] - vctrl[0]) * 1e-6),
        "kvco_min_mhz_per_v": float(np.min(kvco) * 1e-6),
        "kvco_max_mhz_per_v": float(np.max(kvco) * 1e-6),
        "monotonic": bool(np.all(df > 0) or np.all(df < 0)),
    }


def analyze_pss_pnoise(
    psf_dir: Path, *, vdd: float, f_low: float, f_high: float
) -> dict[str, float]:
    pss_file = find_single(psf_dir, ["pss.td.pss", "*.td.pss"])
    dp = parse_psf_ascii(pss_file)
    t = dp["time"]
    period = float(t[-1] - t[0])
    if period <= 0.0:
        raise RuntimeError(f"Invalid PSS period: {period}")
    f0 = 1.0 / period

    vdiff = dp["OUTP"] - dp["OUTN"]
    v_pp_diff = float(np.max(vdiff) - np.min(vdiff))

    i_sup = dp["VSUP:p"]
    i_avg = abs(trapz(i_sup, t) / period)
    p_dc_mw = i_avg * vdd * 1e3

    # Extract differential carrier peak amplitude at fundamental from pss.fd.pss
    fd_file = find_single(psf_dir, ["pss.fd.pss", "*.fd.pss"])
    dfd = parse_psf_ascii(fd_file)
    fd_freq = np.real(dfd["freq"])
    fund_idx = int(np.argmin(np.abs(fd_freq - f0)))
    v_carr_pk = float(np.abs(dfd["OUTP"][fund_idx] - dfd["OUTN"][fund_idx]))
    if v_carr_pk <= 1e-9:
        v_carr_pk = 0.5 * v_pp_diff

    # Locate PM pnoise file (`pnoise.pm.pnoise`, `pnoise.pnoise`, etc.)
    pn_file = find_single(psf_dir, ["*pm*.pnoise", "pnoise*.pnoise", "*.pnoise"])
    dn = parse_psf_ascii(pn_file)
    freq_key = "relative frequency" if "relative frequency" in dn else "freq"
    freq = np.real(dn[freq_key])

    if "out" in dn:
        val = np.real(dn["out"])
    else:
        sig_key = next(k for k in dn if k != freq_key)
        val = np.real(dn[sig_key])

    # In Spectre `noiseout=[pm]` (and `usb`), `out` is single-sideband RMS noise
    # voltage [V_rms/sqrt(Hz)] (verified against `pnoise.pnoise` USB output!).
    # Normalize to carrier RMS voltage (V_carr_pk / sqrt(2)) per IEEE Std 1139:
    #   L(df) = 10*log10(out^2 / (V_carr_pk^2 / 2)) = 20*log10(out / V_carr_rms)
    v_carr_rms = v_carr_pk / math.sqrt(2.0)
    if np.all(val > 0.0):
        l_dbc = 20.0 * np.log10(np.maximum(val / v_carr_rms, 1e-30))
    else:
        l_dbc = val

    log_f = np.log10(freq)

    def l_at(df_hz: float) -> float:
        return float(np.interp(math.log10(df_hz), log_f, l_dbc))

    l_100k = l_at(1e5)
    l_1m = l_at(1e6)
    l_10m = l_at(1e7)

    fom_1m = -l_1m + 20.0 * math.log10(f0 / 1e6) - 10.0 * math.log10(max(p_dc_mw, 1e-12))
    jit = integrate_phase_noise_jitter(freq, l_dbc, f0, f_low_hz=f_low, f_high_hz=f_high)

    return {
        "f0_ghz": f0 * 1e-9,
        "vdiff_pp_v": v_pp_diff,
        "p_dc_mw": p_dc_mw,
        "l_100khz_dbc_hz": l_100k,
        "l_1mhz_dbc_hz": l_1m,
        "l_10mhz_dbc_hz": l_10m,
        "fom_1mhz_dbc_hz": fom_1m,
        "rms_jitter_fs": jit["rms_jitter_fs"],
        "rms_phase_deg": jit["rms_phase_deg"],
        "jitter_band_khz_to_mhz": f"{f_low*1e-3:.1f}k-{f_high*1e-6:.1f}M",
        "pnoise_file": pn_file.name,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze VCO Spectre outputs.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_t = sub.add_parser("tuning", help="Extract f(Vctrl) and K_VCO from tb_vco_tuning_kvco.scs")
    p_t.add_argument("psf_dir", type=Path)

    p_p = sub.add_parser("pss_pnoise", help="Extract f0, L(df), FoM, RMS jitter from tb_vco_pss_pnoise.scs")
    p_p.add_argument("psf_dir", type=Path)
    p_p.add_argument("--vdd", type=float, default=0.9)
    p_p.add_argument("--f-low", type=float, default=10e3)
    p_p.add_argument("--f-high", type=float, default=40e6)

    args = ap.parse_args(argv)
    if args.mode == "tuning":
        res = analyze_tuning(args.psf_dir)
    else:
        res = analyze_pss_pnoise(
            args.psf_dir, vdd=args.vdd, f_low=args.f_low, f_high=args.f_high
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
