# .claude/skills/nuomi-drama-skills/stages/status.py
from __future__ import annotations
import json
from pathlib import Path
from stages import GenerateLog


def _group_index(storyboard: dict) -> dict:
    """shot_id -> (group_id, group_size)。"""
    idx: dict[str, tuple] = {}
    for g in (storyboard.get("shot_groups") or []):
        gid = g.get("group_id")
        sids = [str(s) for s in (g.get("shot_ids") or [])]
        for sid in sids:
            idx[sid] = (gid, len(sids))
    return idx


def shot_states(out_dir: str, ep: int, storyboard: dict, log_entries: list[dict]) -> list[dict]:
    shots_dir = Path(out_dir) / f"E{ep}" / "shots_assets"
    group_of = _group_index(storyboard)
    err_of: dict[str, str] = {}
    for e in log_entries:
        if e.get("stage") == "images" and e.get("ep") == ep:
            err_of[str(e.get("shot_id"))] = e.get("error")

    out: list[dict] = []
    for s in (storyboard.get("shots") or []):
        sid = str(s.get("shot_id"))
        gid, gsize = group_of.get(sid, (s.get("group_id"), 1))
        if (shots_dir / f"{sid}.jpg").exists():
            state, reason = "ready", None
        elif sid in err_of:
            state, reason = "failed", err_of[sid]
        else:
            state, reason = "pending", None
        rec = {"shot_id": sid, "state": state, "group_id": gid, "in_grid": gsize > 1}
        if reason is not None:
            rec["reason"] = reason
        out.append(rec)
    return out


def collect_status(out_dir: str, ep_range: list[int]) -> dict:
    log = GenerateLog(out_dir).read()
    episodes = []
    for ep in ep_range:
        ctx_path = Path(out_dir) / f"E{ep}" / "gen_context.json"
        if not ctx_path.exists():
            continue
        sb = (json.loads(ctx_path.read_text(encoding="utf-8")).get("storyboard") or {})
        episodes.append({"ep": ep, "shots": shot_states(out_dir, ep, sb, log)})
    return {"episodes": episodes}


def failed_shots_to_retry(out_dir: str, ep_range: list[int], stage: str = "images") -> set:
    """有失败记录且当前无产物的镜（jpg 已存在则视为已被补上，不重试）。"""
    log = GenerateLog(out_dir).read()
    result: set = set()
    for ep in ep_range:
        shots_dir = Path(out_dir) / f"E{ep}" / "shots_assets"
        for e in log:
            if e.get("stage") == stage and e.get("ep") == ep:
                sid = str(e.get("shot_id"))
                if not (shots_dir / f"{sid}.jpg").exists():
                    result.add(sid)
    return result
