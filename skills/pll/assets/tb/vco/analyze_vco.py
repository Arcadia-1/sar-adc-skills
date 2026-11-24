#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from VCO testbenches.

Usage:
  python analyze_vco.py tuning <psf_dir>
  python analyze_vco.py pss_pnoise <psf_dir> [--vdd 0.9] [--f-low 10e3] [--f-high 40e6]
  python analyze_vco.py capbank <psf_dir> [--min-overlap-pct 20.0]
"""

from __future__ import annotations

import argparse
import json
import math
import re
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


def analyze_capbank(
    psf_dir: Path, *, min_overlap_pct: float = 20.0
) -> dict[str, object]:
    """Analyze multi-sub-band cap-bank overlap and K_LIN from tb_vco_capbank_overlap.scs."""
    files = sorted(
        Path(psf_dir).glob("tran_b*.tran"),
        key=lambda p: int(m.group(1)) if (m := re.search(r"b(\d+)", p.name)) else 0,
    )
    if len(files) < 2:
        raise FileNotFoundError(
            f"Expected >= 2 tran_b*.tran files in {psf_dir}, found {[p.name for p in files]}"
        )

    bands: list[dict[str, object]] = []
    for p in files:
        d = parse_psf_ascii(p)
        _, vctrl, vcode, finst_ghz = extract_uniform_strobe(
            d["time"], d["VCTRL"], d["VCODE"], d["F_INST"]
        )
        order = np.argsort(vctrl)
        vctrl = vctrl[order]
        f_mhz = finst_ghz[order] * 1e3  # va_phase_err_mon outputs GHz (1 V == 1 GHz)
        if len(vctrl) < 3:
            raise RuntimeError(f"Expected >= 3 strobed VCTRL points in {p.name}, got {len(vctrl)}")

        code = int(round(float(np.median(vcode))))
        f_min = float(f_mhz[0])
        f_max = float(f_mhz[-1])
        span = f_max - f_min
        dv_tot = float(vctrl[-1] - vctrl[0])
        kvco_avg = span / dv_tot if abs(dv_tot) > 1e-9 else 0.0
        kvco_local = np.diff(f_mhz) / np.diff(vctrl)

        f_line = f_min + kvco_avg * (vctrl - vctrl[0])
        k_lin_pct = float(100.0 * np.max(np.abs(f_mhz - f_line)) / max(abs(span), 1e-9))

        bands.append(
            {
                "code": code,
                "n_pts": int(len(vctrl)),
                "f_min_mhz": f_min,
                "f_max_mhz": f_max,
                "span_mhz": span,
                "kvco_avg_mhz_per_v": float(kvco_avg),
                "kvco_min_mhz_per_v": float(np.min(kvco_local)),
                "kvco_max_mhz_per_v": float(np.max(kvco_local)),
                "k_lin_pct": k_lin_pct,
                "monotonic": bool(np.all(np.diff(f_mhz) > 0.0)),
            }
        )

    bands.sort(key=lambda b: float(b["f_min_mhz"]))

    overlaps_mhz: list[float] = []
    overlaps_pct: list[float] = []
    f_steps_mhz: list[float] = []
    for k in range(len(bands) - 1):
        b0, b1 = bands[k], bands[k + 1]
        f_step = 0.5 * (
            (float(b1["f_min_mhz"]) - float(b0["f_min_mhz"]))
            + (float(b1["f_max_mhz"]) - float(b0["f_max_mhz"]))
        )
        ov_mhz = float(b0["f_max_mhz"]) - float(b1["f_min_mhz"])
        ov_pct = 100.0 * ov_mhz / max(f_step, 1e-9)
        f_steps_mhz.append(f_step)
        overlaps_mhz.append(ov_mhz)
        overlaps_pct.append(ov_pct)

    f_tot_min = float(bands[0]["f_min_mhz"])
    f_tot_max = float(bands[-1]["f_max_mhz"])
    f_tot_mid = 0.5 * (f_tot_min + f_tot_max)
    blind_holes = int(sum(1 for ov in overlaps_mhz if ov <= 0.0))
    min_ov = float(min(overlaps_pct))

    return {
        "n_bands": int(len(bands)),
        "f_total_min_mhz": f_tot_min,
        "f_total_max_mhz": f_tot_max,
        "total_tuning_range_pct": 100.0 * (f_tot_max - f_tot_min) / max(f_tot_mid, 1e-9),
        "mean_f_step_mhz": float(np.mean(f_steps_mhz)),
        "mean_kvco_mhz_per_v": float(np.mean([float(b["kvco_avg_mhz_per_v"]) for b in bands])),
        "max_k_lin_pct": float(max(float(b["k_lin_pct"]) for b in bands)),
        "min_overlap_pct": min_ov,
        "max_overlap_pct": float(max(overlaps_pct)),
        "mean_overlap_pct": float(np.mean(overlaps_pct)),
        "overlaps_pct": [round(x, 3) for x in overlaps_pct],
        "blind_hole_count": blind_holes,
        "min_overlap_spec_pct": float(min_overlap_pct),
        "overlap_pass": bool(blind_holes == 0 and min_ov >= min_overlap_pct),
        "all_bands_monotonic": bool(all(bool(b["monotonic"]) for b in bands)),
        "bands": bands,
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

    p_c = sub.add_parser("capbank", help="Extract sub-band overlap and K_LIN from tb_vco_capbank_overlap.scs")
    p_c.add_argument("psf_dir", type=Path)
    p_c.add_argument("--min-overlap-pct", type=float, default=20.0)

    args = ap.parse_args(argv)
    if args.mode == "tuning":
        res = analyze_tuning(args.psf_dir)
    elif args.mode == "capbank":
        res = analyze_capbank(args.psf_dir, min_overlap_pct=args.min_overlap_pct)
    else:
        res = analyze_pss_pnoise(
            args.psf_dir, vdd=args.vdd, f_low=args.f_low, f_high=args.f_high
        )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
