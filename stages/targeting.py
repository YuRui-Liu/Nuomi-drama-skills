# .claude/skills/nuomi-drama-skills/stages/targeting.py
from __future__ import annotations


def resolve_targets(storyboard: dict, shot_ids: list[str]) -> list[dict]:
    """把请求的 shot_id 映射到其所属叙事组（去重）。

    - 属某组的镜 → 该组整组进结果（默认组原子）。
    - 不属任何组的孤儿镜 → 合成单元 {"group_id": None, "shot_ids": [sid]}。
    - 未知 shot_id（不在 storyboard.shots 里）→ 抛 KeyError。
    """
    shots = storyboard.get("shots") or []
    groups = storyboard.get("shot_groups") or []
    known = {str(s.get("shot_id")) for s in shots}
    for sid in shot_ids:
        if str(sid) not in known:
            raise KeyError(f"unknown shot_id: {sid}")

    group_of: dict[str, dict] = {}
    for g in groups:
        for sid in (g.get("shot_ids") or []):
            group_of[str(sid)] = g

    result: list[dict] = []
    seen: set = set()
    for sid in shot_ids:
        sid = str(sid)
        g = group_of.get(sid)
        if g is None:
            key = ("__solo__", sid)
            g = {"group_id": None, "shot_ids": [sid]}
        else:
            key = g.get("group_id") or ("__ids__", tuple(str(x) for x in g.get("shot_ids") or []))
        if key in seen:
            continue
        seen.add(key)
        result.append(g)
    return result
