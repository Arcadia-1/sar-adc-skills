#!/usr/bin/env python3
"""Offline repository validation suite for ams-skills (multi-skill layout).

Automatically discovers and validates every skill under `skills/*`:
  1. Policy / leak scan (zero foundry, PDK, private-project, or lab host strings)
  2. LF-only line endings (zero CRLF)
  3. Per-skill SKILL.md YAML frontmatter & agents/openai.yaml schema
  4. Per-skill evals/evals.json schema, sequential IDs, and file existence
  5. Complete reference coverage in each SKILL.md and root README.md
  6. All relative Markdown links and SKILL.md backtick paths exist on disk
  7. All `ahdl_include` paths inside Spectre `.scs` decks exist on disk
  8. Python syntax, CLI `--help`, and unit tests for `common/psf_utils.py` & runners
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
SKILLS_ROOT = ROOT / "skills"

# Terms prohibited in public process-independent documentation and assets
LEAK_RE = re.compile(
    r"tsmc|gf22|fdx|globalfoundries|gpdk045|nmos1v|pmos1v|28nm|28 nm|22nm|22 nm|\bzzs\b|nch_|pch_|"
    r"_mac\b|crn28|hpc\+|thu-|nesthorn|larain|zhangz|/home/|/usr/pack|peters_01|"
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

    # Discover all skills under skills/*
    skill_dirs = sorted(p for p in SKILLS_ROOT.iterdir() if p.is_dir())
    if not skill_dirs:
        errors.append("No skill directories found under skills/")

    skills_readme_path = SKILLS_ROOT / "README.md"
    if not skills_readme_path.exists():
        errors.append("Missing skills/README.md catalog")
        skills_readme_text = ""
    else:
        skills_readme_text = skills_readme_path.read_text(encoding="utf-8")

    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    total_refs = 0
    total_evals = 0
    total_va = 0

    bt_re = re.compile(r"`((?:references|assets)/[A-Za-z0-9_./-]+)`")

    for sdir in skill_dirs:
        sname = sdir.name
        if f"{sname}/" not in skills_readme_text:
            errors.append(f"skills/README.md missing skill entry: {sname}/")
        skill_md = sdir / "SKILL.md"
        if not skill_md.exists():
            errors.append(f"{sname}: missing SKILL.md")
            continue

        skill_text = skill_md.read_text(encoding="utf-8")
        fm_match = re.match(r"^---\n(.*?)\n---\n", skill_text, re.S)
        if not fm_match:
            errors.append(f"{sname}/SKILL.md missing YAML frontmatter")
        else:
            parsed = yaml.safe_load(fm_match.group(1))
            if not isinstance(parsed.get("name"), str) or not parsed["name"].strip():
                errors.append(f"{sname}/SKILL.md frontmatter missing name")
            if not isinstance(parsed.get("description"), str) or len(parsed["description"]) < 50:
                errors.append(f"{sname}/SKILL.md frontmatter description too short")

        oa_path = sdir / "agents/openai.yaml"
        if not oa_path.exists():
            errors.append(f"{sname}: missing agents/openai.yaml")
        else:
            oa = yaml.safe_load(oa_path.read_text(encoding="utf-8"))
            if "interface" not in oa or "policy" not in oa:
                errors.append(f"{sname}/agents/openai.yaml missing interface or policy")

        # evals.json
        evals_path = sdir / "evals/evals.json"
        if not evals_path.exists():
            errors.append(f"{sname}: missing evals/evals.json")
        else:
            evals = json.loads(evals_path.read_text(encoding="utf-8"))
            ids = [e["id"] for e in evals["evals"]]
            total_evals += len(ids)
            if ids != list(range(1, len(ids) + 1)):
                errors.append(f"{sname}/evals/evals.json IDs not sequential 1..N: {ids}")
            for e in evals["evals"]:
                for f in e["files"]:
                    if not (sdir / f).exists():
                        errors.append(f"{sname} eval {e['id']} missing file: {f}")

        # Canonical hierarchy checks
        if not (sdir / "references/simulation-and-verification.md").exists():
            errors.append(f"{sname}: missing references/simulation-and-verification.md")
        tb_root = sdir / "assets/tb"
        if not (tb_root / "README.md").exists():
            errors.append(f"{sname}: missing assets/tb/README.md")
        for sub_tb in sorted(p for p in tb_root.iterdir() if p.is_dir()):
            if any(sub_tb.glob("*.scs")) and not (sub_tb / "README.md").exists():
                errors.append(f"{sname}: TB suite {sub_tb.name}/ missing README.md")

        # References coverage in SKILL.md & root README.md
        ref_files = sorted(p.name for p in (sdir / "references").glob("*.md"))
        total_refs += len(ref_files)
        for rf in ref_files:
            if f"references/{rf}" not in skill_text:
                errors.append(f"{sname}/SKILL.md missing references/{rf}")
            if rf not in readme_text:
                errors.append(f"README.md missing {sname} reference {rf}")

        # Backtick paths in SKILL.md
        for path_str in bt_re.findall(skill_text):
            if not (sdir / path_str.rstrip("/")).exists():
                errors.append(f"{sname}/SKILL.md backtick path missing: {path_str}")

        total_va += len(list((sdir / "assets/va").rglob("*.va")))

    # 6. Relative Markdown links across entire repo
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

    # 7. Verify ahdl_include paths in all .scs decks
    ahdl_re = re.compile(r'^\s*ahdl_include\s+"([^"]+)"', re.M)
    scs_files = sorted(p for p in all_files if p.suffix == ".scs")
    for scs in scs_files:
        for inc in ahdl_re.findall(scs.read_text(encoding="utf-8")):
            if not (scs.parent / inc).resolve().exists():
                errors.append(f"Missing ahdl_include '{inc}' in {scs.relative_to(ROOT)}")

    # 8. Python syntax, CLI --help, and unit tests
    py_files = sorted(p for p in all_files if p.suffix == ".py")
    for pf in py_files:
        with tempfile.NamedTemporaryFile(suffix=".pyc") as tf:
            py_compile.compile(str(pf), cfile=tf.name, doraise=True)

    cli_scripts = sorted(
        p
        for p in py_files
        if p.name.startswith(("analyze_", "run_"))
    )
    for script in cli_scripts:
        res = subprocess.run(
            [sys.executable, "-B", str(script), "--help"],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            errors.append(f"{script.relative_to(ROOT)} --help failed: {res.stderr}")

    # Unit tests for common/psf_utils.py
    psf_path = ROOT / "common/psf_utils.py"
    spec = importlib.util.spec_from_file_location("psf_utils", psf_path)
    psf_mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(psf_mod)

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

        p_dcop = pathlib.Path(td) / "mc1-001_dcOp.dc"
        p_dcop.write_text(
            'HEADER\nVALUE\n"VSUP:p" "I" -1.0e-4 PROP(\n"units" "A"\n)\n'
            '"OUTP" "V" 0.752\n"OUTN" "V" 0.748\nEND\n',
            encoding="utf-8",
        )
        dop = psf_mod.parse_psf_ascii(p_dcop)
        assert abs((dop["OUTP"][0] - dop["OUTN"][0]) - 0.004) < 1e-12
        assert abs(dop["VSUP:p"][0] - (-1.0e-4)) < 1e-15

    # Test extract_uniform_strobe drops off-grid endpoints
    t_grid = np.array([0.0, 0.1, 1.1, 2.1, 3.1, 4.1, 5.0])
    y_grid = np.array([99.0, 1.0, 2.0, 3.0, 4.0, 5.0, 99.0])
    tf, yf = psf_mod.extract_uniform_strobe(t_grid, y_grid)
    assert len(tf) == 5 and np.allclose(yf, [1.0, 2.0, 3.0, 4.0, 5.0])

    # Test coherent_fft_metrics
    n_fft, m_bin = 128, 19
    phase = 2.0 * math.pi * m_bin * np.arange(n_fft) / n_fft
    q_sine = np.floor((0.5 + 0.49 * np.sin(phase)) * 1024.0)
    m_fft = psf_mod.coherent_fft_metrics(q_sine, m_bin=m_bin)
    assert 9.5 < m_fft["enob"] < 10.2, f"Unexpected 10b ENOB: {m_fft['enob']}"

    # Test coherent_twotone_metrics with known 3rd-order nonlinearity (x - 0.02*x^3)
    n_tt, m1, m2 = 256, 59, 61
    k_idx = np.arange(n_tt)
    x_tt = 0.5 * (np.sin(2.0 * math.pi * m1 * k_idx / n_tt) + np.sin(2.0 * math.pi * m2 * k_idx / n_tt))
    y_tt = x_tt - 0.02 * (x_tt**3)
    m_tt = psf_mod.coherent_twotone_metrics(y_tt, m_bin1=m1, m_bin2=m2, fs=200e6)
    assert m_tt["im3_lo_bin"] == 57.0 and m_tt["im3_hi_bin"] == 63.0
    # Theoretical IM3 for A=0.5, a3=-0.02: 3/4 * |a3| * A^2 = 0.00375 -> -48.5 dBc
    assert -50.0 < m_tt["imd3_dbc"] < -47.0, f"Unexpected IMD3: {m_tt['imd3_dbc']}"

    # Verify install_skills.sh syntax & --list output
    install_sh = ROOT / "scripts/install_skills.sh"
    if not install_sh.exists():
        errors.append("Missing scripts/install_skills.sh")
    else:
        chk = subprocess.run(["bash", "-n", str(install_sh)], capture_output=True, text=True)
        if chk.returncode != 0:
            errors.append(f"install_skills.sh syntax error: {chk.stderr}")
        lst = subprocess.run([str(install_sh), "--list"], capture_output=True, text=True)
        listed = sorted(x.strip() for x in lst.stdout.splitlines() if x.strip())
        if lst.returncode != 0 or listed != [d.name for d in skill_dirs]:
            errors.append(f"install_skills.sh --list mismatch: got {listed}")

    # Test dnl_inl_from_transfer
    ramp = np.linspace(-1.0, 1.0, 64)
    m_dnl = psf_mod.dnl_inl_from_transfer(ramp)
    assert m_dnl["dnl_abs_max_lsb"] < 1e-12 and m_dnl["inl_abs_max_lsb"] < 1e-12

    # Test integrate_phase_noise_jitter (flat -120 dBc/Hz over 1 MHz BW -> 2e-6 rad^2)
    f_pn = np.logspace(4, 7, 200)
    l_pn = np.full_like(f_pn, -120.0)
    jit = psf_mod.integrate_phase_noise_jitter(f_pn, l_pn, f_carrier_hz=1.0e9, f_low_hz=1e5, f_high_hz=1.1e6)
    expected_rad = math.sqrt(2.0 * 1e-12 * 1.0e6)
    assert abs(jit["rms_phase_rad"] - expected_rad) / expected_rad < 1e-3

    # Test SerDes helpers: sbr_cursor_metrics, eye_diagram_metrics, mixed_mode_s_params
    t_sbr = np.linspace(0.0, 2.0e-9, 2001)
    # 1-UI=100ps pulse peaking at 0.5ns with h0=0.3V, h1=0.1V
    h_syn = 0.3 * np.exp(-0.5 * ((t_sbr - 0.5e-9) / 20e-12) ** 2) + 0.1 * np.exp(-0.5 * ((t_sbr - 0.6e-9) / 20e-12) ** 2)
    v_sbr = -0.3 + 2.0 * h_syn
    m_sbr = psf_mod.sbr_cursor_metrics(t_sbr, v_sbr, ui_s=100e-12, t_base_end=0.2e-9)
    assert abs(m_sbr["h0_mv"] - 300.0) < 2.0 and abs(m_sbr["cursors_mv"]["h1"] - 100.0) < 2.0
    assert m_sbr["pda_eye_open"] is True

    # Ideal alternating NRZ square wave eye -> full height & width
    t_eye = np.linspace(0.0, 2.0e-9, 4001)
    bits_eye = np.where((np.floor(t_eye / 100e-12).astype(int) % 2) == 0, 0.25, -0.25)
    m_eye = psf_mod.eye_diagram_metrics(t_eye, bits_eye, ui_s=100e-12, t_skip=0.2e-9)
    assert m_eye["eye_open"] is True and abs(m_eye["eye_height_mv"] - 500.0) < 1.0

    # Mixed-mode S-parameters on symmetric differential through (s31=s42=0.5, cross=0)
    sp_mock = {
        "s11": np.array([0.1 + 0j]), "s12": np.array([0.0 + 0j]),
        "s21": np.array([0.0 + 0j]), "s22": np.array([0.1 + 0j]),
        "s31": np.array([0.5 + 0j]), "s32": np.array([0.0 + 0j]),
        "s41": np.array([0.0 + 0j]), "s42": np.array([0.5 + 0j]),
    }
    mm = psf_mod.mixed_mode_s_params(sp_mock)
    assert abs(mm["sdd21"][0] - 0.5) < 1e-12 and abs(mm["sdd11"][0] - 0.1) < 1e-12

    # Unit tests for comparator run_cmp_tb.py
    runner_path = SKILLS_ROOT / "sar-adc/assets/tb/comparator/run_cmp_tb.py"
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
        f"({len(skill_dirs)} skills, {total_refs} refs, {total_evals} evals, "
        f"{len(scs_files)} .scs decks, {total_va} VA models, "
        f"{len(py_files)} .py scripts, {len(cli_scripts)} CLI checks, "
        f"{link_count} relative links, 0 leaks, 0 CRLF)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
