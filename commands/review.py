"""/nuomi:review — run multi-dimension quality review.

Reads manuscript/ content and gen_context.json files, runs the 5-dimension
scoring engine from quality/review.py, writes review_report.json and
review_report.md into out_dir.

Registered as command "review" via hooks.register_command.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hooks import register_command


def run_review(out_dir: str, args: list[str], ref_paths: list[Path],
               state: dict[str, Any]) -> dict[str, Any]:
    """Run quality review on current project content.

    Args:
        out_dir: Project output directory.
        args: CLI args.
        ref_paths: Resolved reference file paths.
        state: Current writing_state.

    Returns:
        {"status": "ok"|"no_content", "message": str, "report_path": str, "total": int}
    """
    out = Path(out_dir)
    manuscript_dir = out / "manuscript"

    if not manuscript_dir.is_dir():
        return {"status": "no_content",
                "message": "manuscript 目录不存在，请先运行 /nuomi:new"}

    md_files = sorted(manuscript_dir.rglob("*.md"))
    if not md_files:
        return {"status": "no_content",
                "message": "manuscript 中无 .md 文件，请先完成创作"}

    from quality.review import run_review as run_review_engine
    report = run_review_engine(out, manuscript_dir, ref_paths)

    report_json = out / "review_report.json"
    report_md = out / "review_report.md"
    report_json.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md.write_text(report.to_markdown(), encoding="utf-8")

    from writing_state import load_state, save_state
    from datetime import datetime, timezone
    current = load_state(out)
    history = current.setdefault("review_history", [])
    history.append({
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": report.total,
        "grade": report.grade,
    })
    current["current_command"] = "review"
    current["last_command_at"] = history[-1]["at"]
    save_state(out, current)

    return {
        "status": "ok",
        "message": f"审查完成: {report.total}/50 — {report.grade}",
        "report_path": str(report_json),
        "total": report.total,
    }


register_command("review", run_review)
