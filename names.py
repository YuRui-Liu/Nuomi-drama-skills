"""Resource naming helpers. VENDORED FROM shot_agent/resources/names.py @ CONTRACT 2026-06-20.
角色 canonical id 使用短名;括号描述只进入 meta/aliases。Parity-tested in tests/skill_export/test_names.py."""
from __future__ import annotations

_OPEN = "（("
_CLOSE_OF = {"（": "）", "(": ")"}


def split_character_descriptor(name: str) -> tuple[str, str]:
    raw = str(name or "").strip()
    if not raw:
        return raw, ""
    open_idx = next((i for i, ch in enumerate(raw) if ch in _OPEN), -1)
    if open_idx < 0:
        return raw, ""
    short = raw[:open_idx].strip()
    if not short:
        return raw, ""
    close_idx = -1
    depth = 0
    for i in range(open_idx, len(raw)):
        ch = raw[i]
        if ch in _OPEN:
            depth += 1
        elif ch in ("）", ")"):
            depth -= 1
            if depth == 0:
                close_idx = i
                break
    if close_idx < 0:
        desc = raw[open_idx + 1:].strip()
    else:
        desc = raw[open_idx + 1:close_idx].strip()
    return short or raw, desc


def normalize_character_name(name: str) -> str:
    return split_character_descriptor(name)[0]
