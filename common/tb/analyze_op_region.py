#!/usr/bin/env python3
"""Saturation audit over Spectre `info what=oppoint` PSF ASCII dumps.

Reads every `*.info` file under the given directories (one per PVT / sweep
point, e.g. from `tb_pvt_mc_wrapper_template.scs`), finds the MOS instances
(entries carrying both `region` and `vdsat`) and lists those that are off,
in triode or in breakdown, or whose |Vds| - |Vdsat| is below a margin.

Spectre MOS `region`: 0 off, 1 triode, 2 saturation, 3 subthreshold,
4 breakdown. Subthreshold (3) is a legal low-gm/Id bias and is not flagged.

Usage:
  python analyze_op_region.py <psf_dir> [<psf_dir> ...] [--prefix I0.] [--margin-mv 50]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

BAD_REGIONS = {0: "off", 1: "triode", 4: "breakdown"}

_STRUCT_RE = re.compile(r'^"([^"]+)" STRUCT\(')
_FIELD_RE = re.compile(r'^"([^"]+)" (FLOAT|INT|STRING)')
_INST_RE = re.compile(r'^"([^"]+)" "([^"]+)" \(\n(.*?)\n\)', re.S | re.M)


def load_oppoint(path: Path) -> dict[str, dict[str, object]]:
    """Parse one psfascii `info` file into {instance: {param: value}}."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    head, _, body = text.partition("\nVALUE\n")
    types: dict[str, list[str]] = {}
    cur = None
    for line in head.splitlines():
        line = line.strip()
        m = _STRUCT_RE.match(line)
        if m:
            cur = m.group(1)
            types[cur] = []
            continue
        m = _FIELD_RE.match(line)
        if m and cur is not None:
            types[cur].append(m.group(1))
    out: dict[str, dict[str, object]] = {}
    for inst, typ, block in _INST_RE.findall(body):
        vals: list[object] = []
        for tok in block.splitlines():
            tok = tok.strip()
            try:
                vals.append(float(tok))
            except ValueError:
                vals.append(tok.strip('"'))
        out[inst] = dict(zip(types.get(typ, []), vals))
    return out


def audit(dirs: list[Path], *, prefix: str, margin_mv: float) -> dict[str, object]:
    files = sorted(f for d in dirs for f in Path(d).rglob("*.info"))
    if not files:
        raise FileNotFoundError(f"No *.info operating-point files under {[str(d) for d in dirs]}")
    flagged = []
    n_mos = 0
    worst_margin = None
    for f in files:
        for inst, p in load_oppoint(f).items():
            if not inst.startswith(prefix) or "region" not in p or "vdsat" not in p:
                continue
            try:
                region = int(float(p["region"]))
                margin = (abs(float(p["vds"])) - abs(float(p["vdsat"]))) * 1e3
            except (KeyError, TypeError, ValueError):
                continue
            n_mos += 1
            if region != 3 and (worst_margin is None or margin < worst_margin["margin_mv"]):
                worst_margin = {"point": f.name, "instance": inst, "margin_mv": round(margin, 2)}
            reason = BAD_REGIONS.get(region)
            if reason is None and region == 2 and margin < margin_mv:
                reason = f"vds-vdsat < {margin_mv:g} mV"
            if reason:
                flagged.append(
                    {"point": f.name, "instance": inst, "region": region,
                     "reason": reason, "margin_mv": round(margin, 2)}
                )
    return {
        "n_points": len(files),
        "n_mos_checks": n_mos,
        "n_flagged": len(flagged),
        "worst_saturation_margin": worst_margin,
        "flagged": flagged,
        "pass": not flagged,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Audit MOS operating regions over Spectre oppoint dumps.")
    ap.add_argument("psf_dirs", type=Path, nargs="+")
    ap.add_argument("--prefix", default="", help="only instances whose name starts with this, e.g. I0.")
    ap.add_argument("--margin-mv", type=float, default=50.0)
    args = ap.parse_args(argv)
    print(json.dumps(audit(args.psf_dirs, prefix=args.prefix, margin_mv=args.margin_mv), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
