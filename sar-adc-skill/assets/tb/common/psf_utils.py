#!/usr/bin/env python3
"""Shared Spectre PSF ASCII parser and SAR ADC signal-analysis helpers.

Works completely standalone (only requires Python >= 3.10 and numpy). When
`virtuoso-bridge-lite` is installed, real-valued PSF ASCII files can also be
loaded seamlessly; complex-valued AC / STB PSF ASCII files (`(re im)`) are
parsed directly by the built-in parser.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import numpy as np

_TRAPZ = getattr(np, "trapezoid", None) or getattr(np, "trapz", None)

# Matches a quoted signal name followed by either a complex pair `(re im)` or a real float.
_VALUE_LINE_RE = re.compile(
    r'^\s*"([^"]+)"\s+(?:\(\s*([+-]?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)\s+'
    r'([+-]?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)\s*\)|'
    r'([+-]?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?))\s*$'
)


def trapz(y: np.ndarray, x: np.ndarray) -> float:
    return float(_TRAPZ(y, x))


def parse_psf_ascii(path: Path) -> dict[str, np.ndarray]:
    """Parse a Spectre PSF ASCII sweep file (`tran`, `dc`, `ac`, `stb`, `noise`, `pss`, `pnoise`).

    Returns a mapping `{signal_name: np.ndarray}` where complex traces (such as
    `ac` or `stb` loopGain) have `complex128` dtype and real traces have `float64`.
    """
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    idx = text.find("\nVALUE\n")
    if idx < 0:
        idx = text.find("VALUE\n")
        if idx < 0:
            raise RuntimeError(f"No VALUE section found in PSF ASCII file: {path}")
        body = text[idx + len("VALUE\n") :]
    else:
        body = text[idx + len("\nVALUE\n") :]

    end_idx = body.find("\nEND")
    if end_idx >= 0:
        body = body[:end_idx]

    raw: dict[str, list[Any]] = {}
    is_complex: dict[str, bool] = {}

    for line in body.splitlines():
        m = _VALUE_LINE_RE.match(line)
        if not m:
            continue
        name, c_re, c_im, r_val = m.groups()
        if c_re is not None:
            raw.setdefault(name, []).append(complex(float(c_re), float(c_im)))
            is_complex[name] = True
        else:
            raw.setdefault(name, []).append(float(r_val))

    if not raw:
        raise RuntimeError(f"No numeric VALUE entries parsed from PSF file: {path}")

    out: dict[str, np.ndarray] = {}
    for k, vals in raw.items():
        dtype = np.complex128 if is_complex.get(k, False) else np.float64
        out[k] = np.asarray(vals, dtype=dtype)
    return out


def find_single(raw_dir: Path, patterns: list[str]) -> Path:
    """Return the first file in `raw_dir` matching any glob pattern in `patterns`."""
    raw_dir = Path(raw_dir)
    for pat in patterns:
        matches = sorted(raw_dir.glob(pat))
        if matches:
            return matches[0]
    avail = [p.name for p in sorted(raw_dir.iterdir())] if raw_dir.exists() else []
    raise FileNotFoundError(f"None of {patterns} found in {raw_dir}; available: {avail}")


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


def extract_uniform_strobe(
    t: np.ndarray, *arrays: np.ndarray, tol: float = 1e-3
) -> tuple[np.ndarray, ...]:
    """Filter a `strobeoutput=strobeonly` waveform to the uniform strobe grid.

    Spectre always appends `t = 0` and `t = t_stop` to transient PSF files even
    when `strobeoutput=strobeonly` is set; if those endpoints do not land on the
    `k * strobeperiod + strobedelay` grid, they introduce duplicate/shifted points
    that cause FFT spectral leakage or false `-1 LSB` DNL spikes.
    """
    t_arr = np.asarray(t, dtype=float)
    if len(t_arr) < 4:
        return (t_arr, *(np.asarray(a, dtype=float) for a in arrays))
    dt = float(np.median(np.diff(t_arr)))
    if dt <= 0.0:
        return (t_arr, *(np.asarray(a, dtype=float) for a in arrays))
    t_anchor = float(t_arr[len(t_arr) // 2])
    phase = (t_arr - t_anchor) / dt
    mask = np.abs(phase - np.round(phase)) < tol
    return (t_arr[mask], *(np.asarray(a, dtype=float)[mask] for a in arrays))


def coherent_fft_metrics(
    samples: np.ndarray,
    *,
    num_harmonics: int = 5,
    fs: float | None = None,
    m_bin: int | None = None,
) -> dict[str, float]:
    """Compute coherent single-tone FFT metrics (SNDR, ENOB, SNR, SFDR, THD).

    Assumes `samples` contains exactly `N` uniformly strobe-sampled points of a
    coherently sampled sine wave (`f_in = f_s * M / N`, `gcd(M, N) = 1`).
    """
    x = np.asarray(samples, dtype=float)
    n = len(x)
    if n < 16:
        raise ValueError(f"Need at least 16 samples for FFT, got {n}")

    x = x - np.mean(x)
    spec = np.fft.rfft(x)
    # Single-sided power spectrum (bin 0 is DC; Nyquist bin n//2 is real-only)
    pwr = (np.abs(spec) ** 2) / (n * n)
    pwr[1 : (n // 2 if n % 2 == 0 else (n + 1) // 2)] *= 2.0

    # Fundamental bin (exclude DC bin 0)
    if m_bin is not None:
        fund_bin = int(m_bin)
    else:
        fund_bin = int(np.argmax(pwr[1:]) + 1)

    p_sig = float(pwr[fund_bin])
    if p_sig <= 0.0:
        raise RuntimeError("Zero signal power in FFT spectrum")

    # Aliased harmonic bins h = 2..num_harmonics
    harm_bins: set[int] = set()
    for h in range(2, num_harmonics + 1):
        k = (h * fund_bin) % n
        if k > n // 2:
            k = n - k
        if k != 0 and k != fund_bin:
            harm_bins.add(k)

    p_harm = float(sum(pwr[k] for k in harm_bins))
    total_non_dc = float(np.sum(pwr[1:]))
    p_nad = max(total_non_dc - p_sig, 1e-30)
    p_noise = max(p_nad - p_harm, 1e-30)

    # Highest non-fundamental spur
    spur_pwr = pwr.copy()
    spur_pwr[0] = 0.0
    spur_pwr[fund_bin] = 0.0
    max_spur_bin = int(np.argmax(spur_pwr))
    p_spur = max(float(spur_pwr[max_spur_bin]), 1e-30)

    sndr_db = 10.0 * math.log10(p_sig / p_nad)
    snr_db = 10.0 * math.log10(p_sig / p_noise)
    thd_db = 10.0 * math.log10(max(p_harm, 1e-30) / p_sig)
    sfdr_db = 10.0 * math.log10(p_sig / p_spur)
    enob = (sndr_db - 1.7609125905568124) / 6.020599913279624

    res: dict[str, float] = {
        "n_fft": float(n),
        "fund_bin": float(fund_bin),
        "sndr_db": sndr_db,
        "enob": enob,
        "snr_db": snr_db,
        "sfdr_db": sfdr_db,
        "thd_db": thd_db,
        "amp_peak": float(math.sqrt(2.0 * p_sig)),
        "max_spur_bin": float(max_spur_bin),
    }
    if fs is not None:
        res["fin_hz"] = fs * fund_bin / n
    return res


def dnl_inl_from_transfer(levels: np.ndarray) -> dict[str, float]:
    """Compute endpoint-fit DNL and INL [LSB] from a monotonic DAC transfer curve."""
    y = np.asarray(levels, dtype=float)
    n = len(y)
    if n < 4:
        raise ValueError(f"Need at least 4 transfer points, got {n}")
    # Ensure ascending orientation
    if y[-1] < y[0]:
        y = y[::-1]
    span = float(y[-1] - y[0])
    if abs(span) < 1e-12:
        raise RuntimeError("Degenerate zero-span DAC transfer curve")
    lsb = span / (n - 1)
    steps = np.diff(y)
    dnl = steps / lsb - 1.0
    ideal = y[0] + np.arange(n, dtype=float) * lsb
    inl = (y - ideal) / lsb
    return {
        "n_codes": float(n),
        "full_scale_v": span,
        "lsb_v": lsb,
        "dnl_max_lsb": float(np.max(dnl)),
        "dnl_min_lsb": float(np.min(dnl)),
        "dnl_abs_max_lsb": float(np.max(np.abs(dnl))),
        "inl_max_lsb": float(np.max(inl)),
        "inl_min_lsb": float(np.min(inl)),
        "inl_abs_max_lsb": float(np.max(np.abs(inl))),
    }
