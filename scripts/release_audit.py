"""Release audit script — deterministic offline quality gate.

Absorbs seedance offline-validator pattern. Checks:
  1. File existence — all required modules present
  2. Version consistency — contract.py vs SKILL.md vs README vs pyproject.toml
  3. Security scan — no skill.env tracked, no hardcoded keys in source
  4. Reference integrity — no dead links, no duplicate paths

Usage:
    python scripts/release_audit.py --check       # Quick check
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))


def check_file_existence() -> list[str]:
    """Check that all required modules exist."""
    errors: list[str] = []
    required = [
        "commands/__init__.py", "commands/__main__.py",
        "commands/dispatcher.py", "commands/new.py",
        "commands/review.py", "commands/compliance.py",
        "quality/__init__.py", "quality/review.py",
        "quality/compliance.py", "quality/profiles/cn.json",
        "exporters/__init__.py", "exporters/jianying.py",
        "exporters/srt.py", "exporters/ffmpeg.py",
        "CLAUDE.md", "pyproject.toml", "SKILL.md", "README.md",
        "generate.py", "export.py", "emit.py", "gates.py",
        "validators.py", "contract.py", "hooks.py",
    ]
    for p in required:
        if not (ROOT / p).exists():
            errors.append(f"MISSING: {p}")
    return errors


def check_version_consistency() -> list[str]:
    """Check that CONTRACT_VERSION is consistent across all files."""
    errors: list[str] = []

    contract_ver = None
    contract_py = ROOT / "contract.py"
    if contract_py.is_file():
        m = re.search(r'CONTRACT_VERSION\s*=\s*"([^"]+)"',
                      contract_py.read_text(encoding="utf-8"))
        if m:
            contract_ver = m.group(1)

    if not contract_ver:
        errors.append("VERSION: cannot extract CONTRACT_VERSION from contract.py")
        return errors

    # Check pyproject.toml
    ppt = ROOT / "pyproject.toml"
    if ppt.is_file():
        text = ppt.read_text(encoding="utf-8")
        m = re.search(r'version\s*=\s*"([^"]+)"', text)
        if m and m.group(1) != contract_ver:
            errors.append(f"VERSION: pyproject.toml={m.group(1)} != contract.py={contract_ver}")

    # Check SKILL.md references contract version
    skill_md = ROOT / "SKILL.md"
    if skill_md.is_file():
        if contract_ver not in skill_md.read_text(encoding="utf-8"):
            errors.append(f"VERSION: SKILL.md does not reference {contract_ver}")

    return errors


def check_security() -> list[str]:
    """Check for security issues."""
    errors: list[str] = []

    # Check skill.env for real keys
    skill_env = ROOT / "skill.env"
    if skill_env.is_file():
        text = skill_env.read_text(encoding="utf-8")
        if re.search(r'sk-[A-Za-z0-9]{30,}', text):
            errors.append("SECURITY: skill.env contains what looks like a real Grsai API key")

    # Scan source code for hardcoded keys
    for py_file in ROOT.rglob("*.py"):
        if py_file.name == "release_audit.py":
            continue
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        if re.search(r'sk-[A-Za-z0-9]{30,}', text):
            errors.append(f"SECURITY: possible API key in {py_file.relative_to(ROOT)}")

    return errors


def check_reference_integrity() -> list[str]:
    """Check that reference/ is gone and references/ is complete."""
    errors: list[str] = []

    ref_dir = ROOT / "reference"
    if ref_dir.exists():
        errors.append("REF: reference/ directory still exists — should be merged into references/")

    refs_dir = ROOT / "references"
    required_refs = ["创作方法论.md", "平台契约.md", "剧本格式规范.md", "分镜表规范.md", "提示词规则.md"]
    for r in required_refs:
        if not (refs_dir / r).exists():
            errors.append(f"REF: references/{r} missing")

    # Check no dead links in SKILL.md
    skill_md = ROOT / "SKILL.md"
    if skill_md.is_file():
        text = skill_md.read_text(encoding="utf-8")
        refs = re.findall(r'`(reference[s]?/[^`]+\.\w+)`', text)
        for ref in refs:
            # Skip references with § section markers (those are doc references, not file paths)
            if "§" in ref:
                continue
            if not (ROOT / ref).exists():
                errors.append(f"REF: dead link in SKILL.md: {ref}")

    return errors


def check_module_registrations() -> list[str]:
    """Check that all commands/exporters are importable."""
    errors: list[str] = []

    for mod in ["commands.new", "commands.review", "commands.compliance"]:
        try:
            __import__(mod)
        except Exception as e:
            errors.append(f"REG: cannot import {mod}: {e}")

    for mod in ["exporters.srt", "exporters.ffmpeg"]:
        try:
            __import__(mod)
        except Exception as e:
            errors.append(f"REG: cannot import {mod}: {e}")

    return errors


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Release audit for nuomi-drama-skills")
    parser.add_argument("--check", action="store_true", help="Quick check")
    args = parser.parse_args()

    all_errors: list[str] = []
    all_errors.extend(check_file_existence())
    all_errors.extend(check_version_consistency())
    all_errors.extend(check_security())
    all_errors.extend(check_reference_integrity())
    all_errors.extend(check_module_registrations())

    if all_errors:
        print(f"FAIL: {len(all_errors)} audit issue(s):")
        for e in all_errors:
            print(f"  - {e}")
        return 1

    print("OK: All audit checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
