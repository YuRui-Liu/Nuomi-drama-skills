"""Build & merge-write platform JSON files. Replicates the platform's load-modify-save
(.mutate) semantics without importing shot_agent: existing keys preserved, owned keys win,
defaults fill brand-new files. Stdlib only."""
from __future__ import annotations

import json
import shutil
from pathlib import Path


def merge_write(path, owned: dict, defaults: dict | None = None) -> dict:
    path = Path(path)
    existing: dict = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing = loaded
        except (OSError, json.JSONDecodeError):
            existing = {}            # corrupt/partial: treated as absent (platform also .bad-backs-up)
    out = {**(defaults or {}), **existing, **owned}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def emit_series(project_dir, *, idea, triplet, mode, episode_count, outline) -> dict:
    return merge_write(
        Path(project_dir) / "series.json",
        owned={"project_dir": str(project_dir), "mode": mode,
               "episode_count": episode_count, "triplet": triplet,
               "idea": idea, "outline": outline},
    )


def emit_arcs(project_dir, *, arcs: list) -> dict:
    # story_bible.json/arcs.json load via cls(**data): MUST contain only known keys.
    return merge_write(Path(project_dir) / "arcs.json",
                       owned={"project_dir": str(project_dir), "arcs": arcs})


def emit_story_bible(project_dir, bible: dict) -> dict:
    # Writes the four PLANNING tables; episode_digests is a runtime product (preserved, never written).
    return merge_write(
        Path(project_dir) / "story_bible.json",
        owned={"project_dir": str(project_dir),
               "characters": bible.get("characters", {}),
               "foreshadows": bible.get("foreshadows", {}),
               "threads": bible.get("threads", {}),
               "canon": bible.get("canon", {})},
        defaults={"episode_digests": {}},
    )


import names


def _registry_entry(rtype: str, rid: str, spec: dict, existing: dict | None) -> dict:
    norm = names.normalize_character_name(rid) if rtype == "character" else rid
    aliases = list(spec.get("aliases") or [])
    raw = str(rid).strip()
    if rtype == "character" and raw and raw != norm and raw not in aliases:
        aliases.append(raw)                                  # paren-form kept as alias
    meta = dict((existing or {}).get("meta") or {})
    meta["appearance"] = spec.get("外貌") or spec.get("appearance") or meta.get("appearance", "")
    if spec.get("描述"):
        meta["description"] = spec["描述"]
    if aliases:
        meta["aliases"] = aliases
    if existing:                                             # refresh text, never downgrade
        e = dict(existing)
        e["meta"] = meta
        # 已有条目保持其 source（若为 imported 则不被出口调降为 generated）
        e.setdefault("source", "generated")
        return e
    return {"type": rtype, "id": norm, "name": rid, "status": "pending",
            "source": "generated", "anchor_path": "", "meta": meta, "overrides": {}}


def emit_registry(project_dir, bible: dict) -> dict:
    path = Path(project_dir) / "assets" / "registry.json"
    entries: dict = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                entries = loaded
        except (OSError, json.JSONDecodeError):
            entries = {}
    for rtype, table in (("character", "characters"), ("scene", "scenes"), ("prop", "props")):
        for rid, spec in (bible.get(table) or {}).items():
            norm = names.normalize_character_name(rid) if rtype == "character" else rid
            key = f"{rtype}/{norm}"
            entries[key] = _registry_entry(rtype, rid, spec or {}, entries.get(key))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    return entries


def _enrich_storyboard(sb: dict, target_aspect: str) -> dict:
    """补齐平台 storyboard schema:顶层 aspect_ratio/fps/compose_mode;组级 scene/narrative_purpose。
    缺则补、有则保留;不伪造镜级 camera_movement(创作字段)。"""
    if not isinstance(sb, dict):
        return sb
    out = dict(sb)
    out.setdefault("aspect_ratio", target_aspect or "9:16")
    out.setdefault("fps", 24)
    out.setdefault("compose_mode", "group")
    scene_by_group: dict = {}
    for s in (out.get("shots") or []):
        gid = str(s.get("group_id"))
        if gid not in scene_by_group and s.get("scene"):
            scene_by_group[gid] = s.get("scene")
    groups = []
    for g in (out.get("shot_groups") or []):
        g2 = dict(g)
        gid = str(g2.get("group_id"))
        if not g2.get("scene"):
            g2["scene"] = scene_by_group.get(gid, "")
        if "narrative_purpose" not in g2:
            g2["narrative_purpose"] = g2.get("name", "") or ""
        groups.append(g2)
    if groups:
        out["shot_groups"] = groups
    # Inject 对白 section into video_prompt for shots with non-empty dialogue.
    shots_out = []
    for s in (out.get("shots") or []):
        s2 = dict(s)
        dialogue = s2.get("dialogue")
        if dialogue:  # non-empty list only
            diatext = json.dumps(dialogue, ensure_ascii=False, separators=(",", ":"))
            vp = str(s2.get("video_prompt") or "").rstrip()
            s2["video_prompt"] = (vp + "\n对白：" + diatext) if vp else ("对白：" + diatext)
        shots_out.append(s2)
    if shots_out:
        out["shots"] = shots_out
    return out


def emit_episode(project_dir, *, ep: int, mode: str, triplet, script, storyboard) -> dict:
    edir = Path(project_dir) / f"E{ep}"
    target_aspect = "9:16"
    sb = _enrich_storyboard(storyboard, target_aspect) if storyboard is not None else storyboard
    result = merge_write(
        edir / "gen_context.json",
        owned={"project_dir": str(edir), "mode": mode, "episode_id": f"E{ep}",
               "triplet": triplet, "script": script, "storyboard": sb},
        defaults={"target_aspect": target_aspect, "idea": None, "anchors": {},
                  "style_anchor": None, "shots_assets": {}, "audio": None},
    )
    # 平台内容视图读这两个产物文件(镜像 run.py:282/311):编剧面板读 script.md、分镜产物读 storyboard.json。
    # 仅已写集落盘;骨架集(script/storyboard 为 None)不写;不碰 audio/imggen/video 等下游产物。
    if script is not None:
        (edir / "script.md").write_text(script, encoding="utf-8")
    if sb is not None:
        (edir / "storyboard.json").write_text(
            json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def emit_project_genres(project_dir, manuscript_dir) -> list:
    """随项目自带的自定义题材:把 manuscript/genres/*.{yaml,yml,md} 拷进 project/genres/。
    平台 axes/loader 解析题材时先查 project_dir/genres/(再回退包内 builtin),故自定义题材
    放进导出项目即生效(打包后也能读,因读的是项目目录非冻结包)。无 genres/ 目录则什么都不做。"""
    src = Path(manuscript_dir) / "genres"
    if not src.is_dir():
        return []
    dst = Path(project_dir) / "genres"
    dst.mkdir(parents=True, exist_ok=True)
    copied = []
    for p in sorted(src.iterdir()):
        if p.is_file() and p.suffix.lower() in (".yaml", ".yml", ".md"):
            shutil.copy2(p, dst / p.name)
            copied.append(p.name)
    return copied


def emit_harness_state(project_dir) -> dict:
    """The project marker (its presence = a valid importable project). Create iff absent;
    never overwrite (would wipe platform run progress: passed/stall_counts)."""
    path = Path(project_dir) / "harness_state.json"
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"passed": []}, ensure_ascii=False, indent=2), encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))
