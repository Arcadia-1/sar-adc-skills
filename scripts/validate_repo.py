#!/usr/bin/env python3
"""Offline repository validation suite for sar-adc-skills.

Checks:
  1. Policy / leak scan (zero foundry, PDK, private-project, or lab host strings)
  2. LF-only line endings (zero CRLF)
  3. SKILL.md YAML frontmatter & agents/openai.yaml schema
  4. evals/evals.json schema, sequential IDs, and file existence
  5. Complete reference coverage in SKILL.md and README.md
  6. All relative Markdown links and SKILL.md backtick paths exist on disk
  7. All `ahdl_include` paths inside Spectre `.scs` decks exist on disk
  8. Python syntax, CLI `--help`, and unit tests for `psf_utils.py` & `run_cmp_tb.py`
"""

from __future__ import annotations

import importlib.util
import json
import math
import pathlib
import py_compile
import re
import subprocess
import sys
import tempfile

import numpy as np
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "sar-adc-skill"

# Terms prohibited in public process-independent documentation and assets
LEAK_RE = re.compile(
    r"tsmc|gf22|fdx|globalfoundries|28nm|28 nm|22nm|22 nm|\bzzs\b|nch_|pch_|"
    r"_mac\b|crn28|hpc\+|thu-|nesthorn|larain|zhangz|/home/|/usr/pack|"
    r"cfmom|rupolym|sc8t|slvt|ulvt|ehvt|raw_materials|sar_logic_11b_diff|"
    r"01-course|02-design|03-nonidealities|04-sampling|05-pvt|06-image|"
    r"taped-out|11b_zzs|sar_11b|bwp12t|sar-adc-11b-zzs|wait --|wait —|ajdust",
    re.IGNORECASE,
)

SKIP_LEAK_FILES = {
    ".gitignore",
    "scripts/validate_repo.py",
}


def main() -> int:
    errors: list[str] = []

    all_files = sorted(
        p
        for p in ROOT.rglob("*")
        if p.is_file()
        and ".git" not in p.parts
        and "__pycache__" not in p.parts
        and not p.name.endswith(".pyc")
    )

    # 1 & 2. CRLF and policy/leak scan
    for p in all_files:
        rel = p.relative_to(ROOT).as_posix()
        raw = p.read_bytes()
        if b"\r" in raw:
            errors.append(f"CRLF found in {rel}")
        if rel not in SKIP_LEAK_FILES:
            text = raw.decode("utf-8", errors="replace")
            for lineno, line in enumerate(text.splitlines(), 1):
                m = LEAK_RE.search(line)
                if m:
                    errors.append(f"Policy/leak match '{m.group(0)}' in {rel}:{lineno}")

    # 3. YAML frontmatter & openai.yaml
    skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    fm_match = re.match(r"^---\n(.*?)\n---\n", skill_text, re.S)
    if not fm_match:
        errors.append("SKILL.md missing YAML frontmatter")
    else:
        parsed = yaml.safe_load(fm_match.group(1))
        if parsed.get("name") != "sar-adc-skill":
            errors.append(f"Unexpected skill name: {parsed.get('name')}")
        if not isinstance(parsed.get("description"), str) or len(parsed["description"]) < 50:
            errors.append("SKILL.md frontmatter description too short")

    oa = yaml.safe_load((SKILL_DIR / "agents/openai.yaml").read_text(encoding="utf-8"))
    if "interface" not in oa or "policy" not in oa:
        errors.append("agents/openai.yaml missing interface or policy")

    # 4. evals.json
    evals = json.loads((SKILL_DIR / "evals/evals.json").read_text(encoding="utf-8"))
    ids = [e["id"] for e in evals["evals"]]
    if ids != list(range(1, len(ids) + 1)):
        errors.append(f"evals.json IDs not sequential 1..N: {ids}")
    for e in evals["evals"]:
        for f in e["files"]:
            if not (SKILL_DIR / f).exists():
                errors.append(f"eval {e['id']} missing file: {f}")

    # 5. All references/*.md listed in SKILL.md and README.md
    ref_files = sorted(p.name for p in (SKILL_DIR / "references").glob("*.md"))
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    for rf in ref_files:
        if f"references/{rf}" not in skill_text:
            errors.append(f"SKILL.md missing references/{rf}")
        if rf not in readme_text:
            errors.append(f"README.md missing {rf}")

    # 6. Relative Markdown links and SKILL.md backtick paths
    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    link_count = 0
    for md in sorted(p for p in all_files if p.suffix == ".md"):
        text = md.read_text(encoding="utf-8")
        for raw_target in link_re.findall(text):
            target = raw_target.split("#", 1)[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            link_count += 1
            if not (md.parent / target).resolve().exists():
                errors.append(f"Broken link in {md.relative_to(ROOT)}: {raw_target}")

    bt_re = re.compile(r"`((?:references|assets)/[A-Za-z0-9_./-]+)`")
    for path_str in bt_re.findall(skill_text):
        if not (SKILL_DIR / path_str.rstrip("/")).exists():
            errors.append(f"SKILL.md backtick path missing: {path_str}")

    # 7. Verify ahdl_include paths in all .scs decks
    ahdl_re = re.compile(r'^\s*ahdl_include\s+"([^"]+)"', re.M)
    scs_files = sorted(p for p in all_files if p.suffix == ".scs")
    for scs in scs_files:
        for inc in ahdl_re.findall(scs.read_text(encoding="utf-8")):
            if not (scs.parent / inc).resolve().exists():
                errors.append(f"Missing ahdl_include '{inc}' in {scs.relative_to(ROOT)}")

    # 8. Python syntax, --help, and unit tests
    py_files = sorted(p for p in all_files if p.suffix == ".py")
    for pf in py_files:
        with tempfile.NamedTemporaryFile(suffix=".pyc") as tf:
            py_compile.compile(str(pf), cfile=tf.name, doraise=True)

    cli_scripts = [
        SKILL_DIR / "assets/tb/comparator/run_cmp_tb.py",
        SKILL_DIR / "assets/tb/bootstrap/analyze_bootstrap.py",
        SKILL_DIR / "assets/tb/cdac/analyze_cdac.py",
        SKILL_DIR / "assets/tb/sar_logic/analyze_sar_logic.py",
        SKILL_DIR / "assets/tb/ldo/analyze_ldo.py",
        SKILL_DIR / "assets/tb/adc_top/analyze_adc_top.py",
    ]
    for script in cli_scripts:
        res = subprocess.run(
            [sys.executable, "-B", str(script), "--help"],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            errors.append(f"{script.relative_to(ROOT)} --help failed: {res.stderr}")

    # Unit tests for psf_utils.py
    psf_path = SKILL_DIR / "assets/tb/common/psf_utils.py"
    spec = importlib.util.spec_from_file_location("psf_utils", psf_path)
    psf_mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(psf_mod)

    # Test real + complex PSF ASCII parsing
    with tempfile.TemporaryDirectory() as td:
        p_real = pathlib.Path(td) / "real.tran"
        p_real.write_text(
            'HEADER\nVALUE\n"time" 0.0\n"VOUT" 0.1\n"time" 1e-9\n"VOUT" 0.9\nEND\n',
            encoding="utf-8",
        )
        dr = psf_mod.parse_psf_ascii(p_real)
        assert np.allclose(dr["time"], [0.0, 1e-9])
        assert np.allclose(dr["VOUT"], [0.1, 0.9])

        p_cplx = pathlib.Path(td) / "cplx.stb"
        p_cplx.write_text(
            'HEADER\nVALUE\n"freq" 1e3\n"loopGain" (100.0 -50.0)\n'
            '"freq" 1e6\n"loopGain" (0.5 -0.866)\nEND\n',
            encoding="utf-8",
        )
        dc = psf_mod.parse_psf_ascii(p_cplx)
        assert np.iscomplexobj(dc["loopGain"])
        assert abs(dc["loopGain"][0] - (100.0 - 50.0j)) < 1e-9

    # Test extract_uniform_strobe drops off-grid t=0 and t=t_stop
    t_grid = np.array([0.0, 0.1, 1.1, 2.1, 3.1, 4.1, 5.0])
    y_grid = np.array([99.0, 1.0, 2.0, 3.0, 4.0, 5.0, 99.0])
    tf, yf = psf_mod.extract_uniform_strobe(t_grid, y_grid)
    assert len(tf) == 5 and np.allclose(yf, [1.0, 2.0, 3.0, 4.0, 5.0])

    # Test coherent_fft_metrics on an exact 10-bit quantized sine wave
    n_fft, m_bin = 128, 19
    phase = 2.0 * math.pi * m_bin * np.arange(n_fft) / n_fft
    q_sine = np.floor((0.5 + 0.49 * np.sin(phase)) * 1024.0)
    m_fft = psf_mod.coherent_fft_metrics(q_sine, m_bin=m_bin)
    assert 9.5 < m_fft["enob"] < 10.2, f"Unexpected 10b ENOB: {m_fft['enob']}"

    # Test dnl_inl_from_transfer
    ramp = np.linspace(-1.0, 1.0, 64)
    m_dnl = psf_mod.dnl_inl_from_transfer(ramp)
    assert m_dnl["dnl_abs_max_lsb"] < 1e-12 and m_dnl["inl_abs_max_lsb"] < 1e-12

    # Unit tests for run_cmp_tb.py
    runner_path = SKILL_DIR / "assets/tb/comparator/run_cmp_tb.py"
    spec2 = importlib.util.spec_from_file_location("run_cmp_tb", runner_path)
    rmod = importlib.util.module_from_spec(spec2)
    assert spec2 and spec2.loader
    spec2.loader.exec_module(rmod)
    assert abs(rmod._eng_to_float("200m") - 0.2) < 1e-12
    assert abs(rmod._eng_to_float("100u") - 1e-4) < 1e-12
    patched = rmod.patch_deck("parameters vdd=0.8\nI0.LP I0.LM\n", {"vdd": "0.9"}, latch_p="I0.OP", latch_n="I0.ON")
    assert "vdd=0.9" in patched and "I0.OP" in patched and "I0.ON" in patched

    if errors:
        print("VALIDATION FAILED:")
        for err in errors:
            print("  -", err)
        return 1

    print(
        f"ALL VALIDATION CHECKS PASSED! "
        f"({len(ref_files)} refs, {len(ids)} evals, {len(scs_files)} .scs decks, "
        f"{len(list((SKILL_DIR / 'assets/va').glob('*.va')))} VA models, "
        f"{len(py_files)} .py scripts, {link_count} relative links, 0 leaks, 0 CRLF)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
