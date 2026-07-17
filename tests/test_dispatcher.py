from __future__ import annotations
import json, tempfile
from pathlib import Path
import pytest
import sys; sys.path.insert(0, str(Path(__file__).parents[1]))


def _make_state_dir(phase: str = "ideation") -> str:
    """Create temp dir with writing_state.json set to given phase."""
    td = tempfile.mkdtemp()
    from writing_state import save_state
    state = {"phase": phase, "completed_episodes": [], "current_episode": 1,
             "current_arc": 1, "gates_passed": [], "gates_warnings": {}}
    save_state(Path(td), state)
    return td


def test_dispatch_unknown_command():
    """Unknown command raises KeyError."""
    from commands.dispatcher import dispatch
    d = _make_state_dir("ideation")
    with pytest.raises(KeyError, match="未知命令"):
        dispatch("nonexistent", [], d)


def test_new_blocked_when_not_ideation_unless_force():
    """Non-ideation phase blocks /nuomi:new unless --force."""
    from commands.dispatcher import dispatch, GateBlocked
    d = _make_state_dir("scripting")
    with pytest.raises(GateBlocked, match="已有进行中的项目"):
        dispatch("new", [], d)


def test_review_blocked_before_scripting():
    """Before scripting phase, /nuomi:review is blocked."""
    from commands.dispatcher import dispatch, GateBlocked
    d = _make_state_dir("outline")
    with pytest.raises(GateBlocked, match="需要先完成剧本"):
        dispatch("review", [], d)
