# .claude/skills/nuomi-drama-skills/stages/dub.py
from __future__ import annotations
import json
from pathlib import Path
from providers.base import DubProvider
from stages import GenerateLog


def _voice_style(out_dir: str, speaker: str) -> str:
    reg_path = Path(out_dir) / "assets" / "registry.json"
    if not reg_path.exists():
        return ""
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    # 兼容扁平键 "character/沈云晚" (平台实际格式) 和分组 {"characters": {...}}
    if any(k.startswith("character/") for k in reg.keys()):
        entry = reg.get(f"character/{speaker}", {})
    else:
        entry = (reg.get("characters") or {}).get(speaker, {})
    return entry.get("voice_style", "") or ""


def _speaker_ref(out_dir: str, speaker: str) -> str | None:
    """返回 voices.json 中 speaker 的本地 speaker_ref 路径，不存在/未就绪返回 None。"""
    voices_path = Path(out_dir) / "assets" / "voices.json"
    if voices_path.exists():
        v = json.loads(voices_path.read_text(encoding="utf-8")).get(speaker, {})
        if v.get("status") == "ready" and v.get("anchor_path"):
            ref = Path(out_dir) / v["anchor_path"]
            if ref.exists():
                return str(ref)
    return None


def run_episode_dub(out_dir: str, ep: int, provider: DubProvider,
                    force: bool = False) -> dict:
    ep_dir = Path(out_dir) / f"E{ep}"
    ctx_path = ep_dir / "gen_context.json"
    if not ctx_path.exists():
        return {"done": 0, "skipped": 0, "failed": 0, "failures": []}
    ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
    shots = (ctx.get("storyboard") or {}).get("shots") or []
    dub_dir = Path(out_dir) / "audio" / f"E{ep}" / "dub"
    log = GenerateLog(out_dir)
    stats = {"done": 0, "skipped": 0, "failed": 0, "failures": []}

    for s in shots:
        sid = str(s.get("shot_id", ""))
        dialogue = s.get("dialogue") or []
        if not dialogue:
            stats["skipped"] += 1
            continue
        for idx, line in enumerate(dialogue):
            speaker = str(line.get("speaker", "unknown"))
            text = str(line.get("text", ""))
            emotion = str(line.get("emotion", ""))
            if not text:
                continue
            dst = dub_dir / f"{sid}_{speaker}_line{idx}.wav"
            if not force and dst.exists():
                stats["skipped"] += 1
                continue
            try:
                ref = _speaker_ref(out_dir, speaker)
                if ref:
                    data = provider.clone_voice(text, ref, emotion)
                else:
                    vs = _voice_style(out_dir, speaker)
                    data = provider.generate_dub(text, speaker, emotion, vs)
                dub_dir.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(data)
                stats["done"] += 1
            except Exception as e:
                log.append("dub", ep, f"{sid}_line{idx}", str(e))
                stats["failed"] += 1
                stats["failures"].append({"ep": ep, "shot_id": f"{sid}_line{idx}", "error": str(e)})
    return stats


def run_dub(out_dir: str, ep_range: list[int], provider: DubProvider,
            force: bool = False) -> dict:
    total = {"done": 0, "skipped": 0, "failed": 0, "failures": []}
    for ep in ep_range:
        r = run_episode_dub(out_dir, ep=ep, provider=provider, force=force)
        for k in ("done", "skipped", "failed"):
            total[k] += r.get(k, 0)
        total["failures"].extend(r.get("failures") or [])
    return total
