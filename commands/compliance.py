"""/nuomi:compliance — run content compliance check.

Reads manuscript/ content and runs the three-tier compliance checker
from quality/compliance.py against quality/profiles/cn.json.

Registered as command "compliance" via hooks.register_command.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hooks import register_command


def run_compliance(out_dir: str, args: list[str], ref_paths: list[Path],
                   state: dict[str, Any]) -> dict[str, Any]:
    """Run compliance check on current project content."""
    out = Path(out_dir)
    manuscript_dir = out / "manuscript"

    if not manuscript_dir.is_dir():
        return {"status": "no_content",
                "message": "manuscript 目录不存在，请先运行 /nuomi:new"}

    md_files = sorted(manuscript_dir.rglob("*.md"))
    if not md_files:
        return {"status": "no_content",
                "message": "manuscript 中无内容，请先完成创作"}

    profile_path = Path(__file__).parents[1] / "quality" / "profiles" / "cn.json"
    from quality.compliance import run_compliance as run_cc
    report = run_cc(manuscript_dir, profile_path)

    report_json = out / "compliance_report.json"
    report_md = out / "compliance_report.md"
    report_json.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md.write_text(report.to_markdown(), encoding="utf-8")

    from writing_state import load_state, save_state
    from datetime import datetime, timezone
    current = load_state(out)
    history = current.setdefault("compliance_history", [])
    history.append({
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "red_lines_hit": len(report.red_line_findings),
        "gray_zones_hit": len(report.gray_zone_findings),
    })
    current["current_command"] = "compliance"
    current["last_command_at"] = history[-1]["at"]
    save_state(out, current)

    return {
        "status": "ok",
        "message": f"合规检查完成: {len(report.red_line_findings)} 红线, "
                   f"{len(report.gray_zone_findings)} 灰区",
        "report_path": str(report_json),
        "red_lines_hit": len(report.red_line_findings),
        "gray_zones_hit": len(report.gray_zone_findings),
    }


register_command("compliance", run_compliance)
