"""Command dispatcher — central router with gate checks and context loading.

Absorbs seedance fast-lane + gate routing and short-drama lazy-loading patterns.

Usage:
    from commands.dispatcher import dispatch
    result = dispatch("new", [], out_dir)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


class GateBlocked(Exception):
    """Raised when a command is blocked by a gate check."""
    def __init__(self, message: str, suggestion: str = ""):
        super().__init__(message)
        self.suggestion = suggestion


# ── Reference load map (absorbs seedance progressive-disclosure pattern) ──
COMMAND_REFERENCES: dict[str, list[str]] = {
    "new":        ["references/创作方法论.md"],
    "review":     ["references/分镜表规范.md", "references/提示词规则.md"],
    "compliance": ["references/平台契约.md"],
}

# ── Precondition checks ──────────────────────────────────────────────
_PHASE_ORDER = [
    "ideation", "outline", "bible", "beats",
    "scripting", "storyboard", "generating", "done",
]


def _phase_index(phase: str) -> int:
    try:
        return _PHASE_ORDER.index(phase)
    except ValueError:
        return -1


def dispatch(command: str, args: list[str], out_dir: str) -> dict[str, Any]:
    """Route a command through gate → context-load → handler.

    Args:
        command: One of "new", "review", "compliance".
        args: Positional arguments (list of strings).
        out_dir: Project output directory (contains writing_state.json).

    Returns:
        Handler result dict.

    Raises:
        GateBlocked: When a precondition is not met.
        KeyError: When command is unknown.
    """
    from writing_state import load_state

    state = load_state(Path(out_dir))
    phase = state.get("phase", "ideation")
    force = "--force" in args

    # ── Route Gate ─────────────────────────────────────────────────
    if command == "new":
        if not force and phase != "ideation":
            raise GateBlocked(
                f"已有进行中的项目（当前阶段: {phase}），使用 --force 覆盖现有项目",
                suggestion="如需保留现有项目，请在新目录中创建；或使用 --force 覆盖"
            )

    elif command == "review":
        if _phase_index(phase) < _phase_index("scripting"):
            raise GateBlocked(
                f"需要先完成剧本才能审查（当前阶段: {phase}，需要 >= scripting）",
                suggestion="请先完成立意→大纲→圣经→节拍→剧本→分镜表，再运行审查"
            )

    elif command == "compliance":
        # Compliance can run at any phase with content
        pass

    else:
        raise KeyError(f"未知命令: {command!r}，可用: new, review, compliance")

    # ── Context Load ───────────────────────────────────────────────
    refs = COMMAND_REFERENCES.get(command, [])
    ref_paths: list[Path] = []
    skill_dir = Path(__file__).parents[1]
    for ref in refs:
        p = skill_dir / ref
        if p.is_file():
            ref_paths.append(p)

    # ── Dispatch ───────────────────────────────────────────────────
    from commands.new import run_new
    from commands.review import run_review
    from commands.compliance import run_compliance

    handlers = {
        "new": run_new,
        "review": run_review,
        "compliance": run_compliance,
    }
    handler = handlers[command]
    return handler(out_dir=out_dir, args=args, ref_paths=ref_paths, state=state)
