"""/nuomi:new — create a new project skeleton.

Creates manuscript/ directory with template files and initializes
writing_state.json. If the project already exists, enters resume mode
and reports current progress.

Registered as command "new" via hooks.register_command.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hooks import register_command


_MANUSCRIPT_TEMPLATES = [
    "00_立意.md",
    "01_大纲.md",
    "02_分卷节拍表.md",
]


def run_new(out_dir: str, args: list[str], ref_paths: list[Path],
            state: dict[str, Any]) -> dict[str, Any]:
    """Create project skeleton or report existing project state.

    Args:
        out_dir: Project output directory.
        args: CLI args (may contain --force).
        ref_paths: Resolved reference file paths for context.
        state: Current writing_state (may be default ideation).

    Returns:
        {"status": "ok"|"resumed", "message": str, "phase": str}
    """
    out = Path(out_dir)
    manuscript_dir = out / "manuscript"
    templates_dir = Path(__file__).parents[1] / "templates"

    # ── Resume mode: project already has manuscript/ ──────────────
    if manuscript_dir.is_dir() and any(manuscript_dir.iterdir()):
        existing = sorted(p.name for p in manuscript_dir.iterdir())
        return {
            "status": "resumed",
            "message": f"已恢复项目（阶段: {state.get('phase', 'ideation')}），"
                       f"已有文件: {', '.join(existing[:5])}",
            "phase": state.get("phase", "ideation"),
        }

    # ── Create skeleton ───────────────────────────────────────────
    manuscript_dir.mkdir(parents=True, exist_ok=True)

    # Copy root templates
    for tmpl in _MANUSCRIPT_TEMPLATES:
        src = templates_dir / tmpl
        if src.is_file():
            shutil.copy2(src, manuscript_dir / tmpl)

    # Copy bible templates
    bible_src = templates_dir / "bible"
    bible_dst = manuscript_dir / "bible"
    if bible_src.is_dir():
        shutil.copytree(bible_src, bible_dst, dirs_exist_ok=True)

    # Initialize writing state
    from writing_state import save_state
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    default_state = {
        "phase": "ideation",
        "completed_episodes": [],
        "current_episode": 1,
        "current_arc": 1,
        "gates_passed": [],
        "gates_warnings": {},
        "current_command": "new",
        "last_command_at": now,
        "review_history": [],
        "compliance_history": [],
        "created_at": now,
        "last_updated": now,
    }
    save_state(out, default_state)

    return {
        "status": "ok",
        "message": f"项目骨架已创建在 {manuscript_dir}，当前阶段: ideation",
        "phase": "ideation",
    }


# ── Register ──────────────────────────────────────────────────────
register_command("new", run_new)
