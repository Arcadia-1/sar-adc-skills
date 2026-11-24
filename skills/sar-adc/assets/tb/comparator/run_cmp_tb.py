#!/usr/bin/env python3
"""Process-independent dynamic comparator testbench runner and PSF analyzer.

Runs the standalone Spectre testbenches in this directory (PSS+PNOISE, DELAY,
TRANNOISE, OFFSET) against any external models + DUT subcircuit, parses the
resulting PSF ASCII waveforms, and extracts metrics using the same definitions
as Cadence ADE Maestro.

Zero foundry paths or PDK parameters are hardcoded here; supply them via CLI
flags or a small JSON config at runtime.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from statistics import NormalDist
from typing import Any

import numpy as np

TB_DIR = Path(__file__).resolve().parent
_TRAPZ = getattr(np, "trapezoid", None) or getattr(np, "trapz", None)


def _trapz(y: np.ndarray, x: np.ndarray) -> float:
    return float(_TRAPZ(y, x))


def parse_psf_ascii(path: Path) -> dict[str, np.ndarray]:
    """Parse a Spectre PSF ASCII file into {signal: np.ndarray}."""
    try:
        from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii

        res = parse_spectre_psf_ascii(path)
        if not res.data:
            raise RuntimeError(f"Empty or unreadable PSF file: {path}")
        return {k: np.asarray(v, dtype=float) for k, v in res.data.items()}
    except ImportError:
        common_dir = next(
            (p / "common" for p in TB_DIR.parents if (p / "common" / "psf_utils.py").exists()),
            TB_DIR.parent / "common",
        )
        if str(common_dir) not in sys.path:
            sys.path.insert(0, str(common_dir))
        from psf_utils import parse_psf_ascii as _fallback_parse

        return _fallback_parse(path)


def crossings(
    t: np.ndarray, y: np.ndarray, level: float, direction: str = "rising"
) -> list[float]:
    """Linearly interpolated threshold crossing times."""
    out: list[float] = []
    for i in range(len(y) - 1):
        a, b = float(y[i]), float(y[i + 1])
        if direction == "rising" and a < level <= b and b != a:
            out.append(float(t[i] + (level - a) / (b - a) * (t[i + 1] - t[i])))
        elif direction == "falling" and a > level >= b and b != a:
            out.append(float(t[i] + (a - level) / (a - b) * (t[i + 1] - t[i])))
    return out


def clip_xy(t: np.ndarray, y: np.ndarray, t0: float, t1: float) -> tuple[np.ndarray, np.ndarray]:
    """Clip (t, y) to [t0, t1] with linearly interpolated endpoints."""
    if t1 <= t0:
        raise ValueError(f"Invalid clip window [{t0}, {t1}]")
    mask = (t > t0) & (t < t1)
    y0 = float(np.interp(t0, t, y))
    y1 = float(np.interp(t1, t, y))
    tc = np.concatenate(([t0], t[mask], [t1]))
    yc = np.concatenate(([y0], y[mask], [y1]))
    return tc, yc


def patch_deck(
    text: str,
    params: dict[str, str],
    *,
    latch_p: str = "I0.LP",
    latch_n: str = "I0.LM",
) -> str:
    """Update parameter assignments and latch node names in a staged TB copy."""
    for key, val in params.items():
        pattern = rf"(?<![A-Za-z0-9_]){re.escape(key)}=[^\s\\]+"
        text, n = re.subn(pattern, f"{key}={val}", text)
        if n == 0:
            raise ValueError(f"Parameter '{key}' not found in deck")
    if latch_p != "I0.LP":
        text = text.replace("I0.LP", latch_p)
    if latch_n != "I0.LM":
        text = text.replace("I0.LM", latch_n)
    return text


def run_spectre(
    spectre_cmd: str,
    deck_path: Path,
    *,
    extra_args: list[str] | None = None,
    timeout: int = 1800,
) -> Path:
    """Execute Spectre in deck_path.parent with PSF ASCII output."""
    run_dir = deck_path.parent
    raw_dir = run_dir / "psf"
    log_path = run_dir / "spectre.out"
    cmd = [
        *shlex.split(spectre_cmd),
        "-format",
        "psfascii",
        "-raw",
        str(raw_dir),
        "+log",
        str(log_path),
        *(extra_args or []),
        deck_path.name,
    ]
    proc = subprocess.run(
        cmd,
        cwd=run_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        if log_path.exists():
            tail = log_path.read_text(errors="replace")[-1500:]
        else:
            tail = (proc.stderr + "\n" + proc.stdout)[-1500:]
        raise RuntimeError(f"Spectre exited {proc.returncode} in {run_dir}:\n{tail}")
    if log_path.exists():
        log_txt = log_path.read_text(errors="replace")
        if re.search(r"^\s*FATAL\b", log_txt, re.M) or "completes with 0 errors" not in log_txt:
            err_lines = [ln for ln in log_txt.splitlines() if "ERROR" in ln or "FATAL" in ln][:10]
            raise RuntimeError(f"Spectre errors in {run_dir}:\n" + "\n".join(err_lines))
    return raw_dir


def find_single(raw_dir: Path, patterns: list[str]) -> Path:
    for pat in patterns:
        matches = sorted(raw_dir.glob(pat))
        if matches:
            return matches[0]
    raise FileNotFoundError(
        f"None of {patterns} found in {raw_dir}; available: {[p.name for p in sorted(raw_dir.iterdir())]}"
    )


def analyze_pss_pnoise(
    raw_dir: Path,
    *,
    vdd: float,
    vidin: float,
    tclk: float,
    v_observe: float,
    latch_p: str,
    latch_n: str,
) -> dict[str, Any]:
    """Extract noise, power, energy, t_cmp, t_rst, regeneration_tau, FoM1, FoM2."""
    pss_file = find_single(raw_dir, ["pss.td.pss", "*.td.pss"])
    pn_file = find_single(
        raw_dir,
        ["pnoise*pm0*sample*.pnoise", "pnoise_sample_pm0*.pnoise", "*pm0*.pnoise", "*.pnoise"],
    )
    pss = parse_psf_ascii(pss_file)
    pn = parse_psf_ascii(pn_file)

    t = pss["time"]
    ck = pss["CMPCK"]
    dp = pss["DCMPP"]
    dn = pss["DCMPN"]
    lp = pss[latch_p]
    lm = pss[latch_n]
    isup = pss["VSUP:p"]

    # Power & energy over one PSS period
    period = float(t[-1] - t[0])
    avg_i = _trapz(isup, t) / period
    power_w = abs(avg_i) * vdd
    energy_j = power_w * tclk

    # Decision delay: CMPCK rising VDD/2 -> (DCMPP - DCMPN) rising VDD/2
    diff_out = dp - dn
    t_ck_r = crossings(t, ck, vdd / 2.0, "rising")
    t_out_r = crossings(t, diff_out, vdd / 2.0, "rising")
    t_cmp = (t_out_r[0] - t_ck_r[0]) if (t_ck_r and t_out_r) else math.nan

    # Reset delay (handle periodic wrap if CMPCK falls near period boundary)
    t_ck_f = crossings(t, ck, vdd / 2.0, "falling")
    t_out_f = crossings(t, diff_out, vdd / 2.0, "falling")
    t_rst = math.nan
    if t_ck_f and t_out_f:
        dt = t_out_f[0] - t_ck_f[0]
        if dt < 0:
            dt += period
        t_rst = dt

    # Regeneration time constant tau: 0.1 V -> 0.2718 V (e^1 ratio) on LP - LM
    diff_latch = lp - lm
    t_01 = crossings(t, diff_latch, 0.1, "rising")
    t_027 = crossings(t, diff_latch, 0.2718, "rising")
    tau = (t_027[0] - t_01[0]) if (t_01 and t_027) else math.nan

    # Input-referred RMS noise (exact _TB_L5_COMPARATOR / Maestro formula)
    freq = pn["freq"]
    out_psd_sqrt = pn["out"]  # V / sqrt(Hz)
    noise_bw = 0.5 / tclk
    fc, sc = clip_xy(freq, out_psd_sqrt, 0.0, min(noise_bw, float(freq[-1])))
    out_power = _trapz(sc**2, fc)
    out_rms = math.sqrt(out_power)
    eff_gain = v_observe / vidin
    noise_v = out_rms / eff_gain

    fom1 = (noise_v**2) * energy_j * 1e21         # mV^2 * fJ
    fom2 = (noise_v**2) * energy_j * t_cmp * 1e30 # mV^2 * fJ * ns

    return {
        "noise_mV": noise_v * 1e3,
        "energy_fJ": energy_j * 1e15,
        "power_uW": power_w * 1e6,
        "t_cmp_ps": t_cmp * 1e12,
        "t_rst_ps": t_rst * 1e12,
        "tau_ps": tau * 1e12,
        "FoM1": fom1,
        "FoM2": fom2,
        "pnoise_file": pn_file.name,
    }


def analyze_delay(raw_dir: Path, *, vdd: float, tclk: float) -> dict[str, Any]:
    """Extract delay (both Maestro product-cross and diff-cross) and E_cmp."""
    tran_file = find_single(raw_dir, ["tran.tran.tran", "tran.tran", "*.tran"])
    tr = parse_psf_ascii(tran_file)
    t = tr["time"]
    ck = tr["CMPCK"]
    dp = tr["DCMPP"]
    dn = tr["DCMPN"]
    isup = tr["VSUP:p"]

    ck_r = crossings(t, ck, vdd / 2.0, "rising")
    prod_f = crossings(t, dp * dn, (vdd * vdd) / 2.0, "falling")
    diff_r = crossings(t, dp - dn, vdd / 2.0, "rising")

    # 3rd cycle matches Maestro's cross(..., 3, ...)
    delay_prod = (prod_f[2] - ck_r[2]) if (len(prod_f) >= 3 and len(ck_r) >= 3) else math.nan
    delay_diff = (diff_r[2] - ck_r[2]) if (len(diff_r) >= 3 and len(ck_r) >= 3) else math.nan

    tc, ic = clip_xy(t, isup, tclk, 5.0 * tclk)
    e_cmp_j = (-_trapz(ic, tc) * vdd) / 4.0
    p_w = e_cmp_j / tclk

    return {
        "delay_ps": delay_prod * 1e12,
        "delay_diff_ps": delay_diff * 1e12,
        "E_cmp_fJ": e_cmp_j * 1e15,
        "P_at_fclk_uW": p_w * 1e6,
    }


def analyze_trannoise(
    raw_dir: Path, *, vdd: float, vidin: float, tclk: float, n_warmup: int = 2, n_cycles: int = 300
) -> dict[str, Any]:
    """Count DCMPN/DCMPP decisions and estimate probit input-referred sigma."""
    tran_file = find_single(raw_dir, ["tran.tran.tran", "tran.tran", "*.tran"])
    tr = parse_psf_ascii(tran_file)
    t = tr["time"]
    dp = tr["DCMPP"]
    dn = tr["DCMPN"]
    t0 = n_warmup * tclk
    t1 = (n_warmup + n_cycles) * tclk
    tc, dpc = clip_xy(t, dp, t0, t1)
    _, dnc = clip_xy(t, dn, t0, t1)

    n_dn = len(crossings(tc, dnc, vdd / 2.0, "falling"))
    n_dp = len(crossings(tc, dpc, vdd / 2.0, "falling"))
    tot = n_dn + n_dp
    sigma_mv = math.nan
    if tot > 0 and 0 < n_dn < tot:
        z = NormalDist().inv_cdf(n_dn / tot)
        if z != 0:
            sigma_mv = (vidin / z) * 1e3
    return {
        "n_DCMPN": n_dn,
        "n_DCMPP": n_dp,
        "sigma_mV": sigma_mv,
    }


def analyze_offset(raw_dir: Path) -> dict[str, Any]:
    """Read final bisected input-referred offset from VMON."""
    tran_file = find_single(raw_dir, ["tran.tran.tran", "tran.tran", "*.tran"])
    tr = parse_psf_ascii(tran_file)
    vmon = tr["VMON"]
    return {"offset_mV": float(vmon[-1]) * 1e3}


def _eng_to_float(val: str) -> float:
    suffixes = {
        "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3,
        "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12,
    }
    s = val.strip()
    if s and s[-1] in suffixes:
        return float(s[:-1]) * suffixes[s[-1]]
    return float(s)


def stage_and_run_case(
    *,
    test: str,
    run_dir: Path,
    models_text: str,
    dut_text: str,
    params: dict[str, str],
    latch_p: str,
    latch_n: str,
    spectre_cmd: str,
    spectre_args: list[str],
) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "models_corner.scs").write_text(models_text)
    (run_dir / "dut_subckt.scs").write_text(dut_text)

    tb_map = {
        "pss_pnoise": "tb_cmp_pss_pnoise.scs",
        "delay": "tb_cmp_delay.scs",
        "trannoise": "tb_cmp_trannoise.scs",
        "offset": "tb_cmp_offset.scs",
    }
    src_tb = TB_DIR / tb_map[test]
    deck_txt = patch_deck(src_tb.read_text(), params, latch_p=latch_p, latch_n=latch_n)
    deck_path = run_dir / src_tb.name
    deck_path.write_text(deck_txt)
    if test == "offset":
        shutil.copy2(TB_DIR / "cmp_bisect.va", run_dir / "cmp_bisect.va")

    raw_dir = run_spectre(spectre_cmd, deck_path, extra_args=spectre_args)

    vdd = _eng_to_float(params.get("vdd", "0.8"))
    tclk = _eng_to_float(params.get("tclk", "1n"))
    if test == "pss_pnoise":
        return analyze_pss_pnoise(
            raw_dir,
            vdd=vdd,
            vidin=_eng_to_float(params.get("vidin", "1m")),
            tclk=tclk,
            v_observe=_eng_to_float(params.get("v_observe", "200m")),
            latch_p=latch_p,
            latch_n=latch_n,
        )
    if test == "delay":
        return analyze_delay(raw_dir, vdd=vdd, tclk=tclk)
    if test == "trannoise":
        return analyze_trannoise(
            raw_dir,
            vdd=vdd,
            vidin=_eng_to_float(params.get("vidin", "500u")),
            tclk=tclk,
            n_warmup=int(params.get("n_warmup", "2")),
            n_cycles=int(params.get("n_cycles", "300")),
        )
    return analyze_offset(raw_dir)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run process-independent comparator Spectre TBs.")
    ap.add_argument("--config", required=True, help="JSON run config specifying models, DUT, corners, tests")
    ap.add_argument("--work-dir", required=True, help="Output directory for staged runs and summary.json")
    ap.add_argument("--spectre", default=os.environ.get("SPECTRE_BIN", "spectre"), help="Spectre binary")
    ap.add_argument("--max-workers", type=int, default=6, help="Parallel Spectre jobs")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text())
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    spectre_args = cfg.get("spectre_args", [])

    jobs: list[tuple[str, dict[str, Any]]] = []
    for dut_entry in cfg["duts"]:
        dut_name = dut_entry["name"]
        dut_text = Path(dut_entry["dut_subckt"]).read_text()
        latch_p = dut_entry.get("latch_p", "I0.LP")
        latch_n = dut_entry.get("latch_n", "I0.LM")
        for corner in cfg["corners"]:
            cname = corner["name"]
            models_text = corner["models_scs"]
            base_params = {k: str(v) for k, v in corner.get("params", {}).items()}
            for tspec in cfg["tests"]:
                tname = tspec["test"]
                sweeps = tspec.get("sweeps", [{}])
                for idx, sw in enumerate(sweeps):
                    params = dict(base_params)
                    params.update({k: str(v) for k, v in tspec.get("params", {}).items()})
                    params.update({k: str(v) for k, v in sw.items()})
                    label = f"{dut_name}__{cname}__{tname}" + (f"__{idx}" if len(sweeps) > 1 else "")
                    jobs.append(
                        (
                            label,
                            dict(
                                test=tname,
                                run_dir=work_dir / label,
                                models_text=models_text,
                                dut_text=dut_text,
                                params=params,
                                latch_p=latch_p,
                                latch_n=latch_n,
                                spectre_cmd=args.spectre,
                                spectre_args=spectre_args,
                            ),
                        )
                    )

    results: dict[str, Any] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as pool:
        fut_map = {pool.submit(stage_and_run_case, **kw): (lbl, kw) for lbl, kw in jobs}
        for fut in concurrent.futures.as_completed(fut_map):
            lbl, kw = fut_map[fut]
            metrics = fut.result()
            results[lbl] = {"test": kw["test"], "params": kw["params"], "metrics": metrics}
            print(f"[OK] {lbl}: {metrics}", flush=True)

    summary_path = work_dir / "summary.json"
    summary_path.write_text(json.dumps(results, indent=2, sort_keys=True))
    print(f"\nSaved summary -> {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
