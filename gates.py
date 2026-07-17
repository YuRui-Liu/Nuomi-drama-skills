"""Gate functions — pure validators returning GateResult.

G0 → source integrity check (HARD) — verifies human-reviewed content
G1-G4 (创作阶段) → hard_block=False (软提醒)
G5-G8 (生成阶段) → hard_block=True  (硬阻断)
G9:G10 → video/audio health (HARD)
G_sequence → manuscript drift detection (HARD)

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


# ── G0: 源完整性 (HARD) ────────────────────────────────────────────
def gate_source_integrity(manuscript_dir: Path, out_dir: Path) -> GateResult:
    """Verify human-reviewed content entered the generation pipeline.

    Checks:
    1. Every manuscript episode with storyboard has gen_context.json
    2. Review report exists with score >= 30/50 (if present)
    3. Compliance report exists with zero red-line findings (if present)
    """
    errors: list[str] = []
    warnings: list[str] = []

    ep_dir = manuscript_dir / "episodes"
    if not ep_dir.is_dir():
        return GateResult(gate_name="source_integrity", passed=True,
                          hard_block=True,
                          warnings=["manuscript/episodes/ 目录不存在（可能是新项目）"])

    for ep_md in sorted(ep_dir.glob("E*.md")):
        ep_name = ep_md.stem
        ctx_path = out_dir / ep_name / "gen_context.json"
        md = ep_md.read_text(encoding="utf-8")
        has_sb = "## 分镜表" in md and "shot_id" in md
        has_ctx = ctx_path.is_file()

        if has_sb and not has_ctx:
            errors.append(f"{ep_name}: 手稿有分镜表但编译产物缺失——请先 export")
        if has_ctx and not has_sb:
            warnings.append(f"{ep_name}: 编译产物存在但手稿无分镜表（骨架集）")

    # Review report threshold
    review_path = out_dir / "review_report.json"
    if review_path.is_file():
        try:
            review = json.loads(review_path.read_text(encoding="utf-8"))
            score = review.get("total", 0)
            if score < 30:
                errors.append(f"审查评分 {score}/50 低于阈值(30)——质量问题未解决")
        except (OSError, json.JSONDecodeError):
            warnings.append("审查报告无法解析")

    # Compliance red-line check
    comp_path = out_dir / "compliance_report.json"
    if comp_path.is_file():
        try:
            comp = json.loads(comp_path.read_text(encoding="utf-8"))
            if comp.get("red_lines_hit", 0) > 0:
                errors.append(f"合规检查发现 {comp['red_lines_hit']} 条红线——必须清零")
        except (OSError, json.JSONDecodeError):
            warnings.append("合规报告无法解析")

    return GateResult(
        gate_name="source_integrity",
        passed=len(errors) == 0,
        hard_block=True,
        errors=errors,
        warnings=warnings,
    )


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


# ── G7: 首帧完整性 + 图片健康 (HARD) ──────────────────────────────
def gate_first_frames(out_dir: Path, ep: int) -> GateResult:
    """Check first-frame existence + image validity (Pillow)."""
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

    for s in shots:
        sid = str(s.get("shot_id", ""))
        jpg_path = shots_dir / f"{sid}.jpg"
        if not jpg_path.exists():
            errors.append(f"E{ep}/{sid}: 首帧缺失")
            continue
        # Enhanced validation using Pillow
        try:
            from PIL import Image
            img = Image.open(jpg_path)
            w, h = img.size
            if w < 512 or h < 896:
                errors.append(f"E{ep}/{sid}: 分辨率过低 ({w}x{h} < 512x896)")
            expected_ratio = 9.0 / 16.0
            actual_ratio = w / h if h > 0 else 0
            if abs(actual_ratio - expected_ratio) / expected_ratio > 0.05:
                errors.append(f"E{ep}/{sid}: 宽高比偏差过大 ({w}x{h})")
            # Detect all-black error pages
            import numpy as np
            arr = np.array(img.convert("RGB"))
            if arr.mean() < 10:
                errors.append(f"E{ep}/{sid}: 图片几乎全黑（可能是 provider 错误页）")
        except Exception as e:
            errors.append(f"E{ep}/{sid}: 图片文件损坏 ({e})")

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


# ── G9: 视频健康 (HARD) ────────────────────────────────────────────
def gate_video_health(out_dir: Path, ep: int) -> GateResult:
    """Check video files: existence, size > 1KB, MP4 header."""
    shots_dir = out_dir / f"E{ep}" / "shots_assets"
    errors: list[str] = []
    for mp4 in sorted(shots_dir.glob("*.mp4")):
        if mp4.stat().st_size < 1024:
            errors.append(f"E{ep}/{mp4.stem}: video < 1KB (可能为空)")
        else:
            header = mp4.read_bytes()[:12]
            if b"ftyp" not in header:
                errors.append(f"E{ep}/{mp4.stem}: not valid MP4")
    return GateResult(gate_name="video_health", passed=len(errors) == 0,
                      hard_block=True, errors=errors)


# ── G10: 音频健康 (HARD) ───────────────────────────────────────────
def gate_audio_health(out_dir: Path, ep: int) -> GateResult:
    """Check audio files: size > 44 bytes, WAV RIFF header."""
    audio_dir = out_dir / "audio" / f"E{ep}" / "dub"
    errors: list[str] = []
    if not audio_dir.is_dir():
        return GateResult(gate_name="audio_health", passed=True,
                          hard_block=True)
    for wav in audio_dir.rglob("*.wav"):
        if wav.stat().st_size < 44:
            errors.append(f"E{ep}/{wav.name}: audio < 44 bytes")
        elif wav.read_bytes()[:4] != b"RIFF":
            errors.append(f"E{ep}/{wav.name}: not valid WAV")
    return GateResult(gate_name="audio_health", passed=len(errors) == 0,
                      hard_block=True, errors=errors)


# ── G_sequence: 漂移检测 (HARD) ────────────────────────────────────
def gate_sequence(manuscript_dir: Path, out_dir: Path, ep: int) -> GateResult:
    """Detect manuscript drift: E{n}.md modified after gen_context.json
    was written — compiled output is stale."""
    ep_md = manuscript_dir / "episodes" / f"E{ep}.md"
    ctx = out_dir / f"E{ep}" / "gen_context.json"
    errors: list[str] = []
    if ep_md.is_file() and ctx.is_file():
        if ep_md.stat().st_mtime > ctx.stat().st_mtime:
            errors.append(
                f"E{ep}: 手稿已修改但未重新编译——请先 export 后再生成"
            )
    return GateResult(gate_name="sequence", passed=len(errors) == 0,
                      hard_block=True, errors=errors)


# ── 批量运行 ─────────────────────────────────────────────────────
def run_all_gates(manuscript_dir: Path, out_dir: Path,
                  stage: str = "all",
                  mode_config: dict | None = None) -> list[GateResult]:
    """按 stage 选择执行哪些 gate。
    stage="scripting"  → G1-G4 (soft)
    stage="generating" → G0 + G5-G8 + G9/G10 + G_sequence (hard)
    stage="all"        → all gates
    mode_config        → optional draft/production gate selection
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
        # G0: source integrity (runs first)
        results.append(gate_source_integrity(manuscript_dir, out_dir))

        ep_dir = manuscript_dir / "episodes"
        skip_video = mode_config and mode_config.get("video", {}).get("skip")
        skip_dub = mode_config and mode_config.get("dub", {}).get("skip")

        for ep_md in sorted(ep_dir.glob("E*.md")) if ep_dir.is_dir() else []:
            results.append(gate_storyboard(ep_md))
            results.append(gate_prompts(ep_md))
            try:
                ep_num = int(ep_md.stem.lstrip("E"))
            except ValueError:
                continue
            results.append(gate_first_frames(out_dir, ep_num))
            results.append(gate_sequence(manuscript_dir, out_dir, ep_num))
            if not skip_video:
                results.append(gate_video_health(out_dir, ep_num))
            if not skip_dub:
                results.append(gate_audio_health(out_dir, ep_num))

        from providers import load_config
        results.append(gate_provider_health(load_config()))
    return results
