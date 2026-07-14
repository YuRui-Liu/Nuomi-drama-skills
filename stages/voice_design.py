# .claude/skills/nuomi-drama-skills/stages/voice_design.py
from __future__ import annotations
import json
from pathlib import Path
from providers.base import DubProvider
from stages import GenerateLog


def run_voice_design(out_dir: str, provider: DubProvider,
                     force: bool = False) -> dict:
    """读 registry.json 所有角色 → design_voice → 写 voices.json。"""
    out = Path(out_dir)
    reg_path = out / "assets" / "registry.json"
    if not reg_path.exists():
        return {"done": 0, "skipped": 0, "failed": 0}
    registry = json.loads(reg_path.read_text(encoding="utf-8"))
    # 兼容扁平键 "character/沈云晚" (平台实际格式) 和分组 {"characters": {...}}
    if any(k.startswith("character/") for k in registry.keys()):
        characters = {k.partition("/")[2]: v for k, v in registry.items()
                      if k.startswith("character/")}
    else:
        characters = registry.get("characters") or {}

    voices_path = out / "assets" / "voices.json"
    voices = (json.loads(voices_path.read_text(encoding="utf-8"))
              if voices_path.exists() else {})

    voices_dir = out / "assets" / "voices"
    log = GenerateLog(out_dir)
    stats = {"done": 0, "skipped": 0, "failed": 0}

    for name, entry in characters.items():
        existing = voices.get(name, {})
        if not force and existing.get("status") == "ready":
            stats["skipped"] += 1
            continue
        style = str(entry.get("voice_style") or entry.get("描述") or "")
        language = str(entry.get("voice_language") or "zh")
        try:
            ref_path = provider.design_voice(name, style, language, str(voices_dir))
            rel = str(Path(ref_path).relative_to(out)).replace("\\", "/")
            voices[name] = {
                "status": "ready",
                "anchor_path": rel,
                "voice_style": style,
            }
            stats["done"] += 1
        except Exception as e:
            voices[name] = {"status": "failed", "voice_style": style, "error": str(e)}
            log.append("voice_design", None, name, str(e))
            stats["failed"] += 1
        voices_path.write_text(
            json.dumps(voices, ensure_ascii=False, indent=2), encoding="utf-8")

    return stats
