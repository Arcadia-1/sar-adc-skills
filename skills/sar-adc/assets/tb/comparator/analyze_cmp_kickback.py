#!/usr/bin/env python3
"""Analyze Spectre PSF ASCII outputs from `tb_cmp_kickback.scs`.

Measures common-mode and differential kickback injected by a dynamic comparator
onto floating high-Z sampled CDAC top plates, plus induced dynamic differential
voltage shift right at the decision edge (in mV and LSB).

Usage:
  python analyze_cmp_kickback.py <psf_dir> [--vdd 0.8] [--vref 0.8] [--n-bits 10] [--vidin 1m]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

COMMON_DIR = next(
    p / "common"
    for p in Path(__file__).resolve().parents
    if (p / "common" / "psf_utils.py").exists()
)
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from psf_utils import crossings, find_single, parse_psf_ascii


def analyze_kickback(
    psf_dir: Path,
    *,
    vdd: float = 0.8,
    vref: float | None = None,
    n_bits: int = 10,
    vidin: float = 1e-3,
) -> dict[str, Any]:
    """Extract CM/diff kickback peaks and decision-edge induced offset."""
    tran_file = find_single(psf_dir, ["tran.tran.tran", "tran.tran", "*.tran"])
    tr = parse_psf_ascii(tran_file)

    t = tr["time"]
    ck = tr["CMPCK"]
    vip = tr["VIP"]
    vin = tr["VIN"]
    dp = tr["DCMPP"]
    dn = tr["DCMPN"]

    ck_r = crossings(t, ck, 0.5 * vdd, "rising")
    ck_f = crossings(t, ck, 0.5 * vdd, "falling")
    if not ck_r:
        raise RuntimeError("No CMPCK rising edge found in kickback transient waveform")

    t0 = ck_r[0]
    tclk = (ck_r[1] - ck_r[0]) if len(ck_r) >= 2 else float(t[-1] - t0)
    t_end_c0 = ck_r[1] if len(ck_r) >= 2 else float(t[-1])

    # Pre-clock settled baseline on floating CDAC inputs
    pre_mask = (t >= max(float(t[0]), t0 - 0.25 * tclk)) & (t <= t0 - 20e-12)
    if not np.any(pre_mask):
        pre_idx = max(int(np.searchsorted(t, t0)) - 1, 0)
        vcm_pre = float(0.5 * (vip[pre_idx] + vin[pre_idx]))
        vdiff_pre = float(vip[pre_idx] - vin[pre_idx])
    else:
        vcm_pre = float(np.mean(0.5 * (vip[pre_mask] + vin[pre_mask])))
        vdiff_pre = float(np.mean(vip[pre_mask] - vin[pre_mask]))

    vcm_err = 0.5 * (vip + vin) - vcm_pre
    vdiff_err = (vip - vin) - vdiff_pre

    # Restrict primary measurement to cycle 0 [t0, t_end_c0]
    cyc_mask = (t >= t0) & (t <= t_end_c0)
    tc = t[cyc_mask]
    cm_c = vcm_err[cyc_mask]
    df_c = vdiff_err[cyc_mask]
    out_diff_c = dp[cyc_mask] - dn[cyc_mask]

    idx_cm = int(np.argmax(np.abs(cm_c)))
    idx_df = int(np.argmax(np.abs(df_c)))
    vkb_cm_signed = float(cm_c[idx_cm])
    vkb_cm_peak = abs(vkb_cm_signed)
    vkb_diff_signed = float(df_c[idx_df])
    vkb_diff_peak = abs(vkb_diff_signed)

    # Locate decision edge (|DCMPP - DCMPN| crosses 0.5 * vdd)
    dec_cross = crossings(tc, np.abs(out_diff_c), 0.5 * vdd, "rising")
    if dec_cross:
        t_dec = dec_cross[0]
        t_cmp = t_dec - t0
    else:
        t_dec = t0 + 0.25 * tclk
        t_cmp = float("nan")

    # Induced differential shift right at decision edge and peak during integration [t0, t_dec]
    vkb_diff_at_dec = float(np.interp(t_dec, tc, df_c))
    int_mask = (tc >= t0) & (tc <= t_dec)
    if np.any(int_mask):
        df_int = df_c[int_mask]
        vkb_diff_pre_dec = float(df_int[int(np.argmax(np.abs(df_int)))])
    else:
        vkb_diff_pre_dec = vkb_diff_at_dec

    # Residual post-reset disturbance right before next CMPCK edge
    t_res_probe = t_end_c0 - 20e-12
    vkb_cm_res = float(np.interp(t_res_probe, t, vcm_err))
    vkb_diff_res = float(np.interp(t_res_probe, t, vdiff_err))

    # Multi-cycle peak across all comparison cycles
    all_mask = t >= t0
    vkb_cm_all_peak = float(np.max(np.abs(vcm_err[all_mask])))
    vkb_diff_all_peak = float(np.max(np.abs(vdiff_err[all_mask])))

    # Decision polarity verification (settled inside high phase of CMPCK)
    t_fall0 = next((tf for tf in ck_f if tf > t0), t0 + 0.5 * tclk)
    t_eval_check = min(t_dec + 0.1 * tclk, t_fall0 - 10e-12)
    out_val = float(np.interp(t_eval_check, t, dp - dn))
    decision_ok = bool((out_val > 0.0) if vidin >= 0.0 else (out_val < 0.0))

    vref_eff = vdd if vref is None else vref
    lsb_v = (2.0 * vref_eff) / (2**n_bits)

    return {
        "vcm_pre_v": vcm_pre,
        "vdiff_pre_mv": vdiff_pre * 1e3,
        "lsb_mv": lsb_v * 1e3,
        "t_cmp_ps": t_cmp * 1e12 if not math.isnan(t_cmp) else -1.0,
        "decision_ok": decision_ok,
        "vkb_cm_peak_mv": vkb_cm_peak * 1e3,
        "vkb_cm_signed_mv": vkb_cm_signed * 1e3,
        "vkb_diff_peak_mv": vkb_diff_peak * 1e3,
        "vkb_diff_signed_mv": vkb_diff_signed * 1e3,
        "vkb_diff_at_decision_mv": vkb_diff_at_dec * 1e3,
        "vkb_diff_at_decision_lsb": vkb_diff_at_dec / lsb_v,
        "vkb_diff_pre_decision_peak_mv": abs(vkb_diff_pre_dec) * 1e3,
        "vkb_diff_pre_decision_peak_lsb": abs(vkb_diff_pre_dec) / lsb_v,
        "vkb_cm_residual_mv": vkb_cm_res * 1e3,
        "vkb_diff_residual_mv": vkb_diff_res * 1e3,
        "vkb_cm_all_cycles_peak_mv": vkb_cm_all_peak * 1e3,
        "vkb_diff_all_cycles_peak_mv": vkb_diff_all_peak * 1e3,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Analyze dynamic comparator kickback on floating high-Z CDAC inputs."
    )
    ap.add_argument("psf_dir", type=Path, help="PSF ASCII directory from tb_cmp_kickback.scs")
    ap.add_argument("--vdd", type=float, default=0.8, help="Supply voltage [V]")
    ap.add_argument("--vref", type=float, default=None, help="ADC reference voltage for LSB [V] (default: vdd)")
    ap.add_argument("--n-bits", type=int, default=10, help="ADC resolution for LSB calculation")
    ap.add_argument("--vidin", type=float, default=1e-3, help="Applied differential input [V]")
    args = ap.parse_args(argv)

    res = analyze_kickback(
        args.psf_dir,
        vdd=args.vdd,
        vref=args.vref,
        n_bits=args.n_bits,
        vidin=args.vidin,
    )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
