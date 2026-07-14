"""Gate functions — pure validators returning GateResult.

G1-G4 (创作阶段) → hard_block=False (软提醒)
G5-G8 (生成阶段) → hard_block=True  (硬阻断)

Each gate is a pure function: input paths/config → GateResult.
Reuses existing validators.py / prompt_checker.py where possible.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GateResult:
    gate_name: str
    passed: bool
    hard_block: bool                    # True=阻断, False=软提醒
    errors: list[str] = field(default_factory=list)     # 阻断级 / 硬错误
    warnings: list[str] = field(default_factory=list)   # 提醒级 / 软问题


# ── G1: 三轴一致性 (SOFT) ──────────────────────────────────────────
def gate_triplet(manuscript_dir: Path) -> GateResult:
    """校验 genre_id / style_id / 基调四维 + arc。复用 validators.validate_triplet。"""
    import manuscript_parse as mp
    import validators
    _, triplet, _, _ = mp.load_idea(manuscript_dir)
    issues = validators.validate_triplet(triplet, manuscript_dir)
    return GateResult(
        gate_name="triplet",
        passed=len(issues) == 0,
        hard_block=False,
        warnings=issues,
    )


# ── G2: 大纲完整性 (SOFT) ──────────────────────────────────────────
def gate_outline(manuscript_dir: Path) -> GateResult:
    import manuscript_parse as mp
    import validators
    _, _, _, count = mp.load_idea(manuscript_dir)
    outline = mp.load_outline(manuscript_dir)
    if outline is None:
        return GateResult(
            gate_name="outline",
            passed=False,
            hard_block=False,
            warnings=["大纲未写（01_大纲.md 不存在或无 JSON 块）"],
        )
    if count <= 0:
        return GateResult(
            gate_name="outline",
            passed=False,
            hard_block=False,
            warnings=["00_立意.md 缺 episode_count（必须 ≥1）"],
        )
    issues = validators.validate_outline(outline, count)
    return GateResult(
        gate_name="outline",
        passed=len(issues) == 0,
        hard_block=False,
        warnings=issues,
    )


# ── G3: 圣经非空检查 (SOFT) ───────────────────────────────────────
def gate_bible(manuscript_dir: Path) -> GateResult:
    import manuscript_parse as mp
    bible = mp.load_bible(manuscript_dir)
    warnings: list[str] = []
    for key, label in [("characters", "角色"), ("scenes", "场景"),
                        ("props", "道具"), ("canon", "世界观"),
                        ("foreshadows", "伏笔")]:
        if not bible.get(key):
            warnings.append(f"圣经缺 {label} 表（bible/{label}.md 为空或不存在）")
    return GateResult(
        gate_name="bible",
        passed=len(warnings) == 0,
        hard_block=False,
        warnings=warnings,
    )


# ── G4: 节拍表校验 (SOFT) ─────────────────────────────────────────
def gate_beats(manuscript_dir: Path) -> GateResult:
    import manuscript_parse as mp
    import validators
    arcs = mp.load_arcs(manuscript_dir)
    issues = validators.validate_beats(arcs)
    return GateResult(
        gate_name="beats",
        passed=len(issues) == 0,
        hard_block=False,
        warnings=issues,
    )


# ── G5: 分镜表规范 (HARD) ─────────────────────────────────────────
def gate_storyboard(ep_path: Path) -> GateResult:
    import manuscript_parse as mp
    import validators
    md = ep_path.read_text(encoding="utf-8") if ep_path.is_file() else None
    if md is None:
        return GateResult(
            gate_name="storyboard",
            passed=False,
            hard_block=True,
            errors=[f"{ep_path.name} 不存在"],
        )
    sb = mp.first_json_block(md)
    if sb is None:
        return GateResult(
            gate_name="storyboard",
            passed=False,
            hard_block=True,
            errors=[f"{ep_path.name} 无分镜表 JSON 块"],
        )
    issues = validators.validate_storyboard(sb)
    return GateResult(
        gate_name="storyboard",
        passed=len(issues) == 0,
        hard_block=True,
        errors=issues,
    )


# ── G6: 提示词质量 (HARD) ─────────────────────────────────────────
def gate_prompts(ep_path: Path) -> GateResult:
    import manuscript_parse as mp
    import prompt_checker
    md = ep_path.read_text(encoding="utf-8") if ep_path.is_file() else None
    if md is None:
        return GateResult(
            gate_name="prompts",
            passed=False,
            hard_block=True,
            errors=[f"{ep_path.name} 不存在"],
        )
    sb = mp.first_json_block(md)
    if sb is None:
        return GateResult(
            gate_name="prompts",
            passed=False,
            hard_block=True,
            errors=[f"{ep_path.name} 无分镜表 JSON 块"],
        )
    errors: list[str] = []
    warnings: list[str] = []
    shots = sb.get("shots") or []
    for s in shots:
        if not isinstance(s, dict):
            continue
        shot_id = s.get("shot_id", "?")
        char_count = len(s.get("characters") or [])
        vp_zh = str(s.get("video_prompt") or "").strip()
        vp_en = str(s.get("video_prompt_en") or "").strip()

        if vp_zh:
            w_zh, e_zh = prompt_checker.check_video_prompt(
                vp_zh, lang="zh", character_count=char_count)
            for w in w_zh:
                warnings.append(f"[{shot_id}] video_prompt(zh): {w.message}")
            for e in e_zh:
                errors.append(f"[{shot_id}] video_prompt(zh): {e.message}")

        if vp_en:
            w_en, e_en = prompt_checker.check_video_prompt(
                vp_en, lang="en", character_count=char_count)
            for w in w_en:
                warnings.append(f"[{shot_id}] video_prompt_en: {w.message}")
            for e in e_en:
                errors.append(f"[{shot_id}] video_prompt_en: {e.message}")

        if not vp_zh and not vp_en:
            warnings.append(f"[{shot_id}] 缺 video_prompt 和 video_prompt_en（将回退 action_desc）")

    return GateResult(
        gate_name="prompts",
        passed=len(errors) == 0,
        hard_block=True,
        errors=errors,
        warnings=warnings,
    )


# ── G7: 首帧完整性 (HARD) ─────────────────────────────────────────
def gate_first_frames(out_dir: Path, ep: int) -> GateResult:
    ctx_path = out_dir / f"E{ep}" / "gen_context.json"
    errors: list[str] = []
    if not ctx_path.exists():
        return GateResult(
            gate_name="first_frames",
            passed=False,
            hard_block=True,
            errors=[f"E{ep}/gen_context.json 不存在，请先 export"],
        )
    ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
    shots = (ctx.get("storyboard") or {}).get("shots") or []
    shots_dir = out_dir / f"E{ep}" / "shots_assets"
    missing = []
    for s in shots:
        sid = str(s.get("shot_id", ""))
        if not (shots_dir / f"{sid}.jpg").exists():
            missing.append(sid)
    if missing:
        errors.append(f"E{ep}: {len(missing)} 镜缺首帧 ({', '.join(missing)})")
    return GateResult(
        gate_name="first_frames",
        passed=len(errors) == 0,
        hard_block=True,
        errors=errors,
    )


# ── G8: Provider 健康 (HARD) ──────────────────────────────────────
def gate_provider_health(cfg: dict) -> GateResult:
    """检查 provider 配置完整性。不实际 ping（避免副作用），只查必填字段。"""
    errors: list[str] = []
    img = cfg.get("image_provider", "")
    if img not in ("grsai", "comfyui", "runninghub", "gemini"):
        errors.append(f"未知 IMAGE_PROVIDER: {img!r}")

    if img == "grsai" and not cfg.get("grsai", {}).get("api_key"):
        errors.append("Grsai: GRSAI_API_KEY 未配置")
    if img == "gemini" and not cfg.get("gemini", {}).get("api_key"):
        errors.append("Gemini: GEMINI_API_KEY 未配置")
    if img == "comfyui" and not cfg.get("comfyui", {}).get("base_url"):
        errors.append("ComfyUI: COMFYUI_BASE_URL 未配置")

    rh = cfg.get("runninghub", {})
    if not rh.get("api_key"):
        errors.append("RunningHub: RUNNINGHUB_API_KEY 未配置（出视频/配音需要）")
    if not rh.get("video_workflow_id"):
        errors.append("RunningHub: RUNNINGHUB_VIDEO_WORKFLOW_ID 未配置")
    if not rh.get("dub_workflow_id"):
        errors.append("RunningHub: RUNNINGHUB_DUB_WORKFLOW_ID 未配置")

    return GateResult(
        gate_name="provider_health",
        passed=len(errors) == 0,
        hard_block=True,
        errors=errors,
    )


# ── 批量运行 ─────────────────────────────────────────────────────
def run_all_gates(manuscript_dir: Path, out_dir: Path,
                  stage: str = "all") -> list[GateResult]:
    """按 stage 选择执行哪些 gate。
    stage="scripting"  → G1-G4 (soft)
    stage="generating" → G5-G8 (hard)
    stage="all"        → G1-G8
    """
    results: list[GateResult] = []
    if stage in ("scripting", "all"):
        results.extend([
            gate_triplet(manuscript_dir),
            gate_outline(manuscript_dir),
            gate_bible(manuscript_dir),
            gate_beats(manuscript_dir),
        ])
    if stage in ("generating", "all"):
        ep_dir = manuscript_dir / "episodes"
        for ep_md in sorted(ep_dir.glob("E*.md")) if ep_dir.is_dir() else []:
            results.append(gate_storyboard(ep_md))
            results.append(gate_prompts(ep_md))
            try:
                ep_num = int(ep_md.stem.lstrip("E"))
            except ValueError:
                continue
            results.append(gate_first_frames(out_dir, ep_num))
        from providers import load_config
        results.append(gate_provider_health(load_config()))
    return results
