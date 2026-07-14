"""LTX 2.3 prompt validation rules.

Validates video_prompt / video_prompt_en against LTX 2.3 video generation best
practices.  Hard blocks (LTXPromptError) prevent generation; soft warnings
(LTXPromptWarning) flag likely quality issues.

Rules are loaded from prompt_rules.json at import time.
Swap the JSON file for new LTX versions without code changes.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass
class LTXPromptError:
    """Hard block: the prompt will produce unusable LTX output."""
    message: str
    rule: str


@dataclass
class LTXPromptWarning:
    """Soft warning: the prompt may cause quality issues."""
    message: str
    rule: str


# ── Load rules from JSON ────────────────────────────────────────────────
_RULES_PATH = Path(__file__).parent / "prompt_rules.json"

def _load_rules() -> dict:
    if _RULES_PATH.is_file():
        try:
            return json.loads(_RULES_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"hard_blocks": [], "soft_warnings": [], "version": "unknown"}

_RULES = _load_rules()


def _compile_patterns(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p) for p in patterns]


# Pre-compile patterns at module load time
_HARD_BLOCK_PATTERNS: list[tuple] = []
for _b in _RULES.get("hard_blocks", []):
    _p_zh = _compile_patterns(_b.get("patterns_zh", []))
    _p_en = _compile_patterns(_b.get("patterns_en", []))
    _p_all = _compile_patterns(_b.get("patterns", []))
    _HARD_BLOCK_PATTERNS.append((
        _b["rule"], _p_all, _p_zh, _p_en,
        _b.get("message_zh", _b.get("message_en", "")),
        _b.get("message_en", _b.get("message_zh", "")),
    ))

_SOFT_WARNING_PATTERNS: list[tuple] = []
for _w in _RULES.get("soft_warnings", []):
    _p_all = _compile_patterns(_w.get("patterns", []))
    _p_front = _compile_patterns(_w.get("patterns_front", []))
    _p_back = _compile_patterns(_w.get("patterns_back", []))
    _SOFT_WARNING_PATTERNS.append((
        _w["rule"], _p_all, _p_front, _p_back,
        _w.get("message_zh", _w.get("message_en", "")),
        _w.get("message_en", _w.get("message_zh", "")),
    ))


# ── Retained compiled patterns for performance-critical checks ──────────
_RE_SENTENCE = re.compile(r"[.!?]+(?:\s+|$)")


# ── Public API ─────────────────────────────────────────────────────────

def check_video_prompt(
    prompt: str,
    lang: str = "en",
    character_count: int = 0,
) -> Tuple[List[LTXPromptWarning], List[LTXPromptError]]:
    """Validate a video prompt against LTX best practices.

    Args:
        prompt: The video_prompt or video_prompt_en string.
        lang: Language code — ``"en"`` or ``"zh"``.
        character_count: Number of characters in the shot (for the >3 check).

    Returns:
        A ``(warnings, errors)`` tuple.  Empty lists mean all checks passed.
    """
    warnings: List[LTXPromptWarning] = []
    errors: List[LTXPromptError] = []

    if not prompt or not prompt.strip():
        return warnings, errors

    # ── Hard blocks ──────────────────────────────────────────────────
    for rule, p_all, p_zh, p_en, msg_zh, msg_en in _HARD_BLOCK_PATTERNS:
        patterns = p_zh if lang == "zh" and p_zh else (p_en if lang != "zh" and p_en else p_all)
        for pat in patterns:
            if pat.search(prompt):
                msg = msg_zh if lang == "zh" else msg_en
                errors.append(LTXPromptError(message=msg, rule=rule))
                break  # one error per rule per prompt

    # ── Soft warnings ────────────────────────────────────────────────
    for rule, p_all, p_front, p_back, msg_zh, msg_en in _SOFT_WARNING_PATTERNS:
        if rule == "conflicting_light_warning":
            has_front = any(pat.search(prompt) for pat in p_front) if p_front else False
            has_back = any(pat.search(prompt) for pat in p_back) if p_back else False
            if has_front and has_back:
                msg = msg_zh if lang == "zh" else msg_en
                warnings.append(LTXPromptWarning(message=msg, rule=rule))
        elif rule == "character_count_warning":
            if character_count > 3:
                msg = msg_zh if lang == "zh" else msg_en
                warnings.append(LTXPromptWarning(
                    message=f"{msg} (当前 {character_count} 个角色)",
                    rule=rule))
        elif rule == "prompt_length_warning":
            if lang == "en":
                sentences = [s.strip() for s in _RE_SENTENCE.split(prompt) if s.strip()]
                n = len(sentences)
                if n < 4 or n > 8:
                    msg = msg_zh if lang == "zh" else msg_en
                    warnings.append(LTXPromptWarning(
                        message=f"{msg} (当前 {n} 句)",
                        rule=rule))
        else:
            for pat in p_all:
                if pat.search(prompt):
                    msg = msg_zh if lang == "zh" else msg_en
                    warnings.append(LTXPromptWarning(message=msg, rule=rule))
                    break

    return warnings, errors
