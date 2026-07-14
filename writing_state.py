"""Manuscript writing state machine — lightweight persistence for session recovery.

Stores phase-level progress. Shot-level state is determined by filesystem
product inspection (via stages/status.py), never written here.

Usage:
    from writing_state import load_state, save_state, advance_phase, mark_gate

    state = load_state(manuscript_dir)
    state = advance_phase(manuscript_dir, "outline")
    state = mark_gate(manuscript_dir, "triplet", True, warnings=[])
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_STATE_FILE = "writing_state.json"

VALID_PHASES = [
    "ideation",      # 立意 / 三轴
    "outline",       # 大纲
    "bible",         # 角色 + 场景 + 道具 + 世界观 + 伏笔
    "beats",         # 分卷节拍表
    "scripting",     # 逐集剧本
    "storyboard",    # 逐集分镜表
    "generating",    # 出图/出视频/配音
    "done",          # 全部完成
]


def _default_state() -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "phase": "ideation",
        "completed_episodes": [],
        "current_episode": 1,
        "current_arc": 1,
        "gates_passed": [],
        "gates_warnings": {},
        "created_at": now,
        "last_updated": now,
    }


def _state_path(manuscript_dir: Path) -> Path:
    return Path(manuscript_dir) / _STATE_FILE


def load_state(manuscript_dir: Path) -> dict[str, Any]:
    """读取状态文件，不存在时返回默认初始状态。"""
    path = _state_path(manuscript_dir)
    if not path.is_file():
        return _default_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default_state()
    # 向后兼容：补齐新增字段的默认值
    defaults = _default_state()
    for k, v in defaults.items():
        data.setdefault(k, v)
    return data


def save_state(manuscript_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    """持久化状态到 manuscript 目录。"""
    state["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path = _state_path(manuscript_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def advance_phase(manuscript_dir: Path, new_phase: str) -> dict[str, Any]:
    """推进到新阶段。非法 phase 值抛出 ValueError。"""
    if new_phase not in VALID_PHASES:
        raise ValueError(f"非法阶段: {new_phase!r}，合法值: {VALID_PHASES}")
    state = load_state(manuscript_dir)
    state["phase"] = new_phase
    return save_state(manuscript_dir, state)


def mark_gate(manuscript_dir: Path, gate_name: str, passed: bool,
              warnings: list[str] | None = None) -> dict[str, Any]:
    """记录 gate 结果。passed gate 记入 gates_passed + 覆盖同名旧结果。
    warnings 写入 gates_warnings（passed=False 时清空同名旧 warnings）。
    """
    state = load_state(manuscript_dir)
    gated = state.setdefault("gates_passed", [])
    gated_warnings = state.setdefault("gates_warnings", {})
    if passed:
        if gate_name not in gated:
            gated.append(gate_name)
        if warnings:
            gated_warnings[gate_name] = warnings
        elif gate_name in gated_warnings:
            del gated_warnings[gate_name]
    else:
        if gate_name in gated:
            gated.remove(gate_name)
        gated_warnings[gate_name] = warnings or []
    return save_state(manuscript_dir, state)


def mark_episode_complete(manuscript_dir: Path, ep: int) -> dict[str, Any]:
    """标记某集完成（剧本+分镜均已写入）。"""
    state = load_state(manuscript_dir)
    completed = state.setdefault("completed_episodes", [])
    if ep not in completed:
        completed.append(ep)
        completed.sort()
    return save_state(manuscript_dir, state)


def set_current_episode(manuscript_dir: Path, ep: int) -> dict[str, Any]:
    state = load_state(manuscript_dir)
    state["current_episode"] = ep
    return save_state(manuscript_dir, state)


def set_current_arc(manuscript_dir: Path, arc: int) -> dict[str, Any]:
    state = load_state(manuscript_dir)
    state["current_arc"] = arc
    return save_state(manuscript_dir, state)
