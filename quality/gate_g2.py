"""Gate G2 — LTX prompt quality check (pre_generate).

Reads gen_context.json storyboard shots and runs prompt_checker.check_video_prompt
on each shot's video_prompt (zh) and video_prompt_en (en). Returns {passed, errors, warnings}
for gating the generation pipeline.

Registered as gate "pre_generate" via hooks.register_gate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hooks import register_gate
import prompt_checker


def gate_g2(context: dict[str, Any]) -> dict[str, Any]:
    """Run LTX prompt quality checks on all storyboard shots.

    Args:
        context: Dict with at least a ``gen_context_path`` (str) key pointing
                 to the episode's gen_context.json file.

    Returns:
        ``{"passed": bool, "errors": [str, ...], "warnings": [str, ...]}``.
        ``passed`` is False when any hard-block error was found.
    """
    errors: list[str] = []
    warnings: list[str] = []

    gen_path = context.get("gen_context_path", "")
    if not gen_path:
        errors.append("[gate_g2] missing gen_context_path in context")
        return {"passed": False, "errors": errors, "warnings": warnings}

    ctx_file = Path(gen_path)
    if not ctx_file.is_file():
        errors.append(f"[gate_g2] gen_context.json not found: {gen_path}")
        return {"passed": False, "errors": errors, "warnings": warnings}

    # ── Load storyboard shots ─────────────────────────────────────
    try:
        data = json.loads(ctx_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"[gate_g2] failed to read/parse gen_context.json: {exc}")
        return {"passed": False, "errors": errors, "warnings": warnings}

    storyboard = data.get("storyboard") or {}
    shots = storyboard.get("shots") or []
    if not isinstance(shots, list) or not shots:
        warnings.append("[gate_g2] storyboard has no shots — skipping prompt checks")
        return {"passed": True, "errors": errors, "warnings": warnings}

    # ── Check every shot ──────────────────────────────────────────
    for shot in shots:
        if not isinstance(shot, dict):
            continue

        shot_id = shot.get("shot_id", "?")
        char_count = len(shot.get("characters") or [])

        # --- Chinese video_prompt ---
        vp_zh = str(shot.get("video_prompt") or "").strip()
        if vp_zh:
            w_zh, e_zh = prompt_checker.check_video_prompt(
                vp_zh, lang="zh", character_count=char_count,
            )
            for w in w_zh:
                warnings.append(f"[{shot_id}] video_prompt(zh): {w.message} (rule={w.rule})")
            for e in e_zh:
                errors.append(f"[{shot_id}] video_prompt(zh): {e.message} (rule={e.rule})")

        # --- English video_prompt_en ---
        vp_en = str(shot.get("video_prompt_en") or "").strip()
        if vp_en:
            w_en, e_en = prompt_checker.check_video_prompt(
                vp_en, lang="en", character_count=char_count,
            )
            for w in w_en:
                warnings.append(f"[{shot_id}] video_prompt_en: {w.message} (rule={w.rule})")
            for e in e_en:
                errors.append(f"[{shot_id}] video_prompt_en: {e.message} (rule={e.rule})")

        # --- Missing both prompts ---
        if not vp_zh and not vp_en:
            warnings.append(
                f"[{shot_id}] both video_prompt and video_prompt_en are empty — "
                f"generation will fall back to action_desc"
            )

    passed = len(errors) == 0
    return {"passed": passed, "errors": errors, "warnings": warnings}


# ── Register ──────────────────────────────────────────────────────
register_gate("pre_generate", gate_g2)
