"""Vendored schema validators. MIRRORS shot_agent/tools/{outline,storyboard}.py and
shot_agent/pipeline/arc.py @ CONTRACT 2026-06-20. Parity-tested in tests/skill_export/."""
from __future__ import annotations

REQUIRED_EPISODE_FIELDS = ["ep", "标题", "梗概", "本集钩子", "爽点节拍"]


def validate_outline(data, episode_count: int) -> list[str]:
    if not isinstance(data, dict):
        return ["大纲必须是 JSON 对象"]
    errors: list[str] = []
    if not data.get("series_logline"):
        errors.append("缺 series_logline")
    if not data.get("主线"):
        errors.append("缺 主线")
    eps = data.get("episodes")
    if not isinstance(eps, list) or not eps:
        errors.append("episodes 必须是非空数组")
        return errors
    if len(eps) != episode_count:
        errors.append(f"集数不符:episodes={len(eps)} 应为 {episode_count}")
    for i, e in enumerate(eps):
        if not isinstance(e, dict):
            errors.append(f"episodes[{i}] 不是对象"); continue
        for f in REQUIRED_EPISODE_FIELDS:
            if f not in e or e[f] in (None, "", []):
                errors.append(f"episodes[{i}] 缺字段 {f}")
    return errors


REQUIRED_SHOT_FIELDS = ["shot_id", "shot_number", "scene", "shot_type", "action_desc",
                        "duration", "group_id"]
ALLOWED_RELATIONS = {"montage", "progressive", "causal", "contrast", "single"}
REQUIRED_GROUP_FIELDS = ["group_id", "relation", "shot_ids"]
_VP_ZH_SECTIONS = ("画面：", "运镜：", "音效：")


def validate_storyboard(data, video_prompt_lang: str | None = None) -> list[str]:
    if not isinstance(data, dict):
        return ["分镜表必须是 JSON 对象"]
    errors: list[str] = []
    if not data.get("title"):
        errors.append("缺 title")
    shots = data.get("shots")
    groups = data.get("shot_groups")
    if not isinstance(shots, list) or not shots:
        errors.append("shots 必须是非空数组")
    if not isinstance(groups, list) or not groups:
        errors.append("shot_groups(叙事组)必须是非空数组")
    if errors:
        return errors
    group_ids = set()
    group_shot_ids: set[str] = set()
    for i, g in enumerate(groups):
        if not isinstance(g, dict):
            errors.append(f"shot_groups[{i}] 不是对象"); continue
        for f in REQUIRED_GROUP_FIELDS:
            if g.get(f) is None or g.get(f) == "":
                errors.append(f"shot_groups[{i}] 缺字段 {f}")
        if g.get("relation") and g["relation"] not in ALLOWED_RELATIONS:
            errors.append(f"shot_groups[{i}] relation 非法: {g.get('relation')}(合法:{sorted(ALLOWED_RELATIONS)})")
        group_ids.add(str(g.get("group_id")))
        for sid in (g.get("shot_ids") or []):
            group_shot_ids.add(str(sid))
    seen = set()
    actual_shot_ids: set[str] = set()
    for i, s in enumerate(shots):
        if not isinstance(s, dict):
            errors.append(f"shots[{i}] 不是对象"); continue
        for f in REQUIRED_SHOT_FIELDS:
            if f not in s or s[f] in (None, ""):
                errors.append(f"shots[{i}] 缺字段 {f}")
        if video_prompt_lang:
            vp = str(s.get("video_prompt") or "").strip()
            if not vp:
                errors.append(f"shots[{i}] 缺字段 video_prompt(运动描述)")
            elif video_prompt_lang == "zh":
                missing = [h for h in _VP_ZH_SECTIONS if h not in vp]
                if missing:
                    errors.append(f"shots[{i}] video_prompt 缺段头 {'/'.join(missing)}"
                                  "(中文三段格式: 画面：/运镜：/音效：)")
        if s.get("group_id") is not None and str(s["group_id"]) not in group_ids:
            errors.append(f"shots[{i}] 未归属任何叙事组 group_id={s.get('group_id')}")
        sid = s.get("shot_id")
        if sid is None:
            continue
        sid_str = str(sid)
        if sid_str in seen:
            errors.append(f"shot_id 重复: {sid}")
        seen.add(sid_str)
        actual_shot_ids.add(sid_str)
    dangling = group_shot_ids - actual_shot_ids
    if dangling:
        errors.append(f"shot_groups.shot_ids 含 shots 中不存在的镜头: {sorted(dangling)}")
    return errors


# --- Vendored axes registry. MIRRORS shot_agent/axes/builtin/{genres,styles,tones} @ CONTRACT 2026-06-20.
# 平台导入时 shot_agent/axes/loader.py 会按这三张表校验三轴;export 此前不校验,导致 genre/style/tone
# 的契约漂移只在平台导入才暴露(题材不存在 / 风格不存在 / 基调缺维度)。这里把表搬进来做 export 期软提醒。
TONE_SCALES = {
    "情感温度": ["冷峻", "克制", "温暖", "炽热"],
    "动作密度": ["纯文戏", "文武均衡", "强动作"],
    "叙事节奏": ["舒缓", "稳健", "快切", "高频反转"],
    "主题深度": ["纯爽无负担", "轻寓意", "厚重思辨"],
}
TONE_ARCS = ["成长型", "觉醒型", "救赎型", "双向救赎", "堕落型", "悲剧型", "坚守型"]
STYLE_IDS = {
    "real/cinematic-warm-v1", "real/cinematic-cool-v1", "real/doc-natural-v1",
    "real/golden-hour-romance-v1", "2D/anime-cel-v1", "2D/guofeng-ink-v1",
    "2D/ghibli-warm-v1", "2D/guofeng-gongbi-v1", "3D/pixar-stylized-v1",
    "3D/photoreal-octane-v1", "3D/pixar-cute-v1",
}
BUILTIN_GENRE_IDS = {
    "ceo-romance", "commercial", "counterattack", "face-slap", "mv", "oral-skit",
    "short-drama", "single-episode", "vlog", "war-god-return", "rebirth", "time-travel",
    "son-in-law", "chase-wife", "revenge", "divine-doctor", "system-rich", "war-god",
    "urban-xianxia", "palace-intrigue", "school-rising", "group-pet",
}


def validate_triplet(triplet, manuscript_dir=None) -> list[str]:
    """三轴一致性检查(SOFT —— export 软提醒,不阻断;镜像平台 axes/loader+models 的硬校验)。
    - 题材:genre_id 须命中内置题材集,或 manuscript/genres/<id>.{yaml,md} 存在(平台先查项目级)。
    - 风格:style_id 须命中已知 style(含平台同款的末段后缀容错)。
    - 基调:TONE_SCALES 四维全齐且档位合法 + arc 在弧光枚举内(平台 ToneVocab.validate 会逐项硬报)。
    """
    if triplet is None:
        return ["缺 triplet(三轴未写)"]
    if not isinstance(triplet, dict):
        return ["triplet 不是对象"]
    issues: list[str] = []

    gid = str((triplet.get("题材") or {}).get("genre_id") or "").strip()
    if not gid:
        issues.append("题材缺 genre_id")
    elif gid not in BUILTIN_GENRE_IDS:
        from pathlib import Path
        found = False
        if manuscript_dir is not None:
            gd = Path(manuscript_dir) / "genres"
            found = (gd / f"{gid}.yaml").is_file() or (gd / f"{gid}.md").is_file()
        if not found:
            issues.append(f"题材不存在: {gid}(非内置题材,且 manuscript/genres/{gid}.yaml|.md 均无 —— "
                          f"放一份到 manuscript/genres/ 即随项目自带;内置题材: {sorted(BUILTIN_GENRE_IDS)})")

    sid = str((triplet.get("风格") or {}).get("style_id") or "").strip()
    if not sid:
        issues.append("风格缺 style_id")
    elif sid not in STYLE_IDS:
        tail = sid.rsplit("/", 1)[-1]
        if sum(1 for s in STYLE_IDS if s.rsplit("/", 1)[-1] == tail) != 1:
            issues.append(f"风格不存在: {sid}(可用: {sorted(STYLE_IDS)})")

    tone = triplet.get("基调") or {}
    levels = tone.get("levels") or {}
    for dim, allowed in TONE_SCALES.items():
        if dim not in levels:
            issues.append(f"基调缺维度: {dim}(需四维全齐: {list(TONE_SCALES)})")
        elif levels[dim] not in allowed:
            issues.append(f"基调档位非法 {dim}={levels[dim]!r}; 合法: {allowed}")
    arc = str(tone.get("arc") or "").strip()
    if not arc:
        issues.append("基调缺 arc(人物弧光)")
    elif arc not in TONE_ARCS:
        issues.append(f"人物弧光非法 {arc!r}; 合法: {TONE_ARCS}")
    return issues


def validate_beats(arcs: list) -> list[str]:
    """Mirror of shot_agent.pipeline.arc.ArcPlan.validate_beats, operating on an arcs list.
    逐卷查: 目标集落卷内 / 关联thread 已声明 / 关联伏笔已声明 / 节拍按目标集递增。"""
    issues: list[str] = []
    for a in (arcs or []):
        tag = f"卷{a.get('arc', '?')}"
        eps = {e.get("ep") for e in (a.get("集") or [])}
        known_threads = set(a.get("threads") or [])
        known_fore = {f.get("id") for f in (a.get("伏笔计划") or [])}
        last_target = None
        for b in (a.get("节拍") or []):
            beat = b.get("beat", "?")
            target = b.get("目标集")
            if eps and target not in eps:
                issues.append(f"{tag} 节拍「{beat}」目标集 {target} 不在本卷集范围 {sorted(eps)}")
            for t in (b.get("关联thread") or []):
                if t not in known_threads:
                    issues.append(f"{tag} 节拍「{beat}」关联未知 thread {t}")
            for fid in (b.get("关联伏笔") or []):
                if fid not in known_fore:
                    issues.append(f"{tag} 节拍「{beat}」关联未知伏笔 {fid}")
            if last_target is not None and target is not None and target < last_target:
                issues.append(f"{tag} 节拍「{beat}」目标集 {target} 顺序倒序(前一拍 {last_target})")
            if target is not None:
                last_target = target
    return issues
