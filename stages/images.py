# .claude/skills/nuomi-drama-skills/stages/images.py
from __future__ import annotations
import json, io, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image
from providers.base import ImageProvider, GridUpscaleProvider
from imaging.grid_canvas import compute_grid_canvas
from imaging.aspect_ops import trim_white_edges, trim_seam_edges, center_crop_to_aspect
from imaging.specs import AspectRatio
from stages import GenerateLog

_DEFAULT_UPSCALE_THRESHOLD = 2


def run_anchors(out_dir: str, provider: ImageProvider, force: bool = False) -> dict:
    out = Path(out_dir)
    reg_path = out / "assets" / "registry.json"
    if not reg_path.exists():
        return {"skipped": 0, "done": 0, "failed": 0, "failures": []}
    registry = json.loads(reg_path.read_text(encoding="utf-8"))
    psfx, nsfx = _style_from_series(out)
    log = GenerateLog(out_dir)
    stats = {"done": 0, "skipped": 0, "failed": 0, "failures": []}

    # 兼容扁平键 "character/xxx" / "scene/xxx" / "prop/xxx" (平台实际格式)
    # 和分组 {"characters": {...}, "scenes": {...}, "props": {...}}
    is_flat = any(k.startswith(("character/", "scene/", "prop/")) for k in registry.keys())
    type_map = {"character/": "characters", "scene/": "scenes", "prop/": "props"}

    # 先收集待生成任务，独立锚图之间没有依赖，可并发出图（并发数取自 provider.max_parallel）
    jobs: list[tuple[str, str, dict, Path]] = []
    for rtype in ("characters", "scenes", "props"):
        type_dir = out / "assets" / rtype
        if is_flat:
            prefix = {"characters": "character/", "scenes": "scene/", "props": "prop/"}[rtype]
            entries = {k.partition("/")[2]: v for k, v in registry.items() if k.startswith(prefix)}
        else:
            entries = registry.get(rtype) or {}
        for name, entry in entries.items():
            if not force and entry.get("status") == "ready":
                stats["skipped"] += 1
                continue
            # 用户导入的资源（source=imported）永不被 AI 覆盖
            if entry.get("source") == "imported":
                stats["skipped"] += 1
                continue
            jobs.append((rtype, name, entry, type_dir))

    stats_lock = threading.Lock()
    log_lock = threading.Lock()

    def _run_one(job: tuple[str, str, dict, Path]) -> None:
        rtype, name, entry, type_dir = job
        appearance = entry.get("appearance") or entry.get("描述") or name
        prompt = _anchor_prompt(rtype, appearance) + _style_tail(psfx, nsfx)
        try:
            img_bytes = provider.generate_image(prompt)
            type_dir.mkdir(parents=True, exist_ok=True)
            dst = type_dir / f"{name}.jpg"
            _save_jpg(img_bytes, dst)
            with stats_lock:
                entry["status"] = "ready"
                entry["anchor_path"] = f"assets/{rtype}/{name}.jpg"
                stats["done"] += 1
        except Exception as e:
            with log_lock:
                log.append("anchors", None, f"{rtype}/{name}", str(e))
            with stats_lock:
                stats["failed"] += 1
                stats["failures"].append({"ep": None, "shot_id": f"{rtype}/{name}", "error": str(e)})

    max_workers = max(1, int(getattr(provider, "max_parallel", 1)))
    if jobs:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            list(pool.map(_run_one, jobs))

    reg_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


def run_episode_shots(out_dir: str, ep: int, provider: ImageProvider,
                      upscale_provider: GridUpscaleProvider | None,
                      threshold: int = _DEFAULT_UPSCALE_THRESHOLD, target_aspect: str = "9:16",
                      force: bool = False, only: set | None = None, solo: bool = False) -> dict:
    ep_dir = Path(out_dir) / f"E{ep}"
    ctx_path = ep_dir / "gen_context.json"
    if not ctx_path.exists():
        return {"skipped": 0, "done": 0, "failed": 0, "failures": []}
    ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
    psfx, nsfx = _style_from_ctx(ctx)
    sb = ctx.get("storyboard") or {}
    shots = sb.get("shots") or []
    groups = sb.get("shot_groups") or []
    shots_dir = ep_dir / "shots_assets"
    shots_dir.mkdir(parents=True, exist_ok=True)
    log = GenerateLog(out_dir)
    stats = {"done": 0, "skipped": 0, "failed": 0, "failures": []}

    shot_by_id = {str(s.get("shot_id")): s for s in shots}

    # 定向模式：只处理 only 里落在本集的镜
    if only is not None:
        present = [sid for sid in shot_by_id if sid in only]
        if solo:
            for sid in present:
                try:
                    render_solo_shot(shot_by_id[sid], shots_dir, provider, target_aspect,
                                     prompt_suffix=psfx, negative_suffix=nsfx)
                    stats["done"] += 1
                except Exception as e:  # noqa: BLE001
                    log.append("images", ep, sid, f"solo: {e}")
                    stats["failed"] += 1
                    stats["failures"].append({"ep": ep, "shot_id": sid, "error": f"solo: {e}"})
            return stats
        from stages.targeting import resolve_targets
        groups = resolve_targets(sb, present)  # 组原子：重出这些镜触及的组

    effective_force = force or (only is not None)  # 定向重出无条件重跑目标组

    # 收集需要处理的任务，独立叙事组之间没有依赖可并发
    grid_jobs: list[tuple[list, list[str]]] = []
    for group in groups:
        shot_ids = [str(sid) for sid in (group.get("shot_ids") or [])]
        group_shots = [shot_by_id[sid] for sid in shot_ids if sid in shot_by_id]
        if not group_shots:
            continue
        if not effective_force and all((shots_dir / f"{sid}.jpg").exists() for sid in shot_ids):
            stats["skipped"] += len(shot_ids)
            continue
        grid_jobs.append((group_shots, shot_ids))

    stats_lock = threading.Lock()
    log_lock = threading.Lock()

    def _run_grid_job(job: tuple[list, list[str]]) -> None:
        group_shots, shot_ids = job
        try:
            _run_grid_pipeline(group_shots, shot_ids, shots_dir, ep_dir, out_dir,
                               provider, upscale_provider, target_aspect, ep, log, stats,
                               threshold=threshold, prompt_suffix=psfx, negative_suffix=nsfx,
                               stats_lock=stats_lock, log_lock=log_lock)
        except Exception as e:
            with log_lock:
                for sid in shot_ids:
                    log.append("images", ep, sid, f"grid pipeline: {e}")
            with stats_lock:
                for sid in shot_ids:
                    stats["failed"] += 1
                    stats["failures"].append({"ep": ep, "shot_id": sid, "error": f"grid pipeline: {e}"})

    max_workers = max(1, int(getattr(provider, "max_parallel", 1)))
    if grid_jobs:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            list(pool.map(_run_grid_job, grid_jobs))
    return stats


def _run_grid_pipeline(group_shots, shot_ids, shots_dir, ep_dir, out_dir,
                       provider, upscale_provider, target_aspect, ep, log, stats,
                       threshold: int = _DEFAULT_UPSCALE_THRESHOLD,
                       prompt_suffix: str = "", negative_suffix: str = "",
                       stats_lock=None, log_lock=None):
    n = len(group_shots)
    canvas = compute_grid_canvas(n, target_aspect, mode="economy", model="gpt-image-2")
    rows, cols = canvas.rows, canvas.cols
    waste = rows * cols - n

    styled = bool(prompt_suffix or negative_suffix)
    no_text = "画面中严禁出现任何文字、数字、分镜编号；下方 [n] 仅为排版参考，禁止绘入画面。"
    panels = "\n".join(
        f"[{i+1}] {s.get('action_desc','')}{_nohumans(s) if styled else ''}"
        for i, s in enumerate(group_shots))
    grid_prompt = (f"分镜宫格：正好 {n} 个画面，{rows}行×{cols}列等大网格，"
                   f"格间纯白分隔缝。{no_text}\n{panels}")
    # 有空位时明确标注哪些格留白，避免 AI 在空位填充无关内容导致裁切偏移
    if waste > 0:
        empty_positions = ", ".join(str(n + i + 1) for i in range(waste))
        grid_prompt += (
            f"\n重要：第 {empty_positions} 号格子必须保持空白（纯白色），"
            "不得绘制任何内容，严禁在空白格填充分镜画面。"
        )
    grid_prompt += _style_tail(prompt_suffix, negative_suffix)
    grid_bytes = provider.generate_image(grid_prompt, size=canvas.provider_args)

    grid_dir = ep_dir / "imggen" / "grids"
    grid_dir.mkdir(parents=True, exist_ok=True)
    grid_path = grid_dir / f"group_{_safe(shot_ids[0])}.png"
    grid_path.write_bytes(grid_bytes)

    if upscale_provider is not None and n > threshold:
        tmp_dir = ep_dir / "imggen" / ".upscale_tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        cell_paths = upscale_provider.upscale_grid(str(grid_path), rows, cols, str(tmp_dir))
        # upscale_grid 返回纯格图（已去除 items[0] 的放大宫格），正好 n 张
        cells = [Image.open(p).convert("RGB") for p in cell_paths[:n]]
    else:
        cells = _local_split(grid_path, rows, cols)[:n]

    aspect = AspectRatio(int(target_aspect.split(":")[0]), int(target_aspect.split(":")[1]))
    for sid, cell in zip(shot_ids, cells):
        norm = _normalize_to_aspect(cell, aspect)
        dst = shots_dir / f"{sid}.jpg"
        norm.save(str(dst), "JPEG", quality=92)
        if stats_lock:
            with stats_lock:
                stats["done"] += 1
        else:
            stats["done"] += 1


def _local_split(grid_path: Path, rows: int, cols: int) -> list[Image.Image]:
    img = Image.open(grid_path).convert("RGB")
    w, h = img.size
    cw, ch = w // cols, h // rows
    cells = []
    for r in range(rows):
        for c in range(cols):
            box = (c * cw, r * ch, (c + 1) * cw, (r + 1) * ch)
            cells.append(img.crop(box))
    return cells


def _save_jpg(data: bytes, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.save(str(dst), "JPEG", quality=92)


def _style_from_ctx(ctx: dict) -> tuple[str, str]:
    """读 gen_context.triplet.风格.style_id → 查 vendored 表取 (prompt_suffix, negative_suffix)；缺/未命中 → ('','')。"""
    return _style_from_triplet(ctx.get("triplet") or {})


def _style_from_triplet(triplet: dict) -> tuple[str, str]:
    sid = str(((triplet or {}).get("风格") or {}).get("style_id") or "")
    from styles_table import style_suffix
    return style_suffix(sid)


def _style_from_series(out: Path) -> tuple[str, str]:
    """读项目级 series.json 的 triplet.风格.style_id（锚图是项目级资源，跨集共用同一风格）。"""
    series_path = out / "series.json"
    if not series_path.exists():
        return "", ""
    try:
        series = json.loads(series_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "", ""
    return _style_from_triplet(series.get("triplet") or {})


# 锚图三类各自的构图框架：角色要能跨集复用（正面/中性背景/无道具干扰），
# 场景要空镜环境全景（无人物），道具要单体产品图（无手/无人）。
_ANCHOR_FRAME = {
    "characters": (
        "角色设计图：正面全身像，自然站姿，中性纯色背景，"
        "clean character reference sheet, front view, neutral studio background, "
        "consistent facial features and outfit for reuse across scenes, no props, no other people"
    ),
    "scenes": (
        "场景概念图：无人物环境全景，"
        "establishing shot, wide angle environment concept art, empty of characters, no people, no text"
    ),
    "props": (
        "道具设计图：单体物件特写，白底产品图，"
        "clean product shot, plain neutral background, no hands, no people, no text"
    ),
}


def _anchor_prompt(rtype: str, appearance: str) -> str:
    frame = _ANCHOR_FRAME.get(rtype, "")
    return f"{frame}\n{appearance}" if frame else appearance


def _nohumans(shot: dict) -> str:
    """无出场角色的画格加 NOT-humans（由调用方在有风格时启用）。"""
    return "" if shot.get("characters") else "（本格无人物 / no humans in this panel）"


def _style_tail(prompt_suffix: str, negative_suffix: str) -> str:
    tail = ""
    if prompt_suffix:
        tail += f"\n画风：{prompt_suffix}"
    if negative_suffix:
        tail += f"\n禁止出现：{negative_suffix}"
    return tail


def _normalize_to_aspect(img: "Image.Image", aspect: AspectRatio) -> "Image.Image":
    """去白边/去拼缝后归一到目标比例；已在 3% 容差内则不裁。"""
    trimmed = trim_seam_edges(trim_white_edges(img))
    target_val = aspect.value
    cur = trimmed.width / max(1, trimmed.height)
    if abs(cur - target_val) / max(target_val, 1e-6) < 0.03:
        return trimmed
    return center_crop_to_aspect(trimmed, aspect)


def render_solo_shot(shot, shots_dir: Path, provider: ImageProvider,
                     target_aspect: str = "9:16",
                     prompt_suffix: str = "", negative_suffix: str = "") -> Path:
    """单镜直出（不走宫格）：只写该镜的 jpg，绝不触碰同组邻镜。

    代价：该镜可能与同组宫格一致性漂移；用于"就修这一镜"应急。
    """
    sid = str(shot.get("shot_id"))
    styled = bool(prompt_suffix or negative_suffix)
    prompt = f"{shot.get('action_desc', '')}{_nohumans(shot) if styled else ''}" \
        + _style_tail(prompt_suffix, negative_suffix)
    img_bytes = provider.generate_image(prompt)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    aspect = AspectRatio(int(target_aspect.split(":")[0]), int(target_aspect.split(":")[1]))
    norm = _normalize_to_aspect(img, aspect)
    shots_dir.mkdir(parents=True, exist_ok=True)
    dst = shots_dir / f"{sid}.jpg"
    norm.save(str(dst), "JPEG", quality=92)
    return dst


def _safe(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(s))


def run_images(out_dir: str, ep_range: list[int], provider: ImageProvider,
               upscale_provider: GridUpscaleProvider | None,
               threshold: int = _DEFAULT_UPSCALE_THRESHOLD, target_aspect: str = "9:16",
               force: bool = False, only: set | None = None, solo: bool = False) -> dict:
    total = {"done": 0, "skipped": 0, "failed": 0, "failures": []}
    if only is None and not solo:
        r1 = run_anchors(out_dir, provider=provider, force=force)
        for k in ("done", "skipped", "failed"):
            total[k] += r1.get(k, 0)
        total["failures"].extend(r1.get("failures") or [])
    for ep in ep_range:
        r2 = run_episode_shots(out_dir, ep=ep, provider=provider,
                               upscale_provider=upscale_provider,
                               threshold=threshold, target_aspect=target_aspect,
                               force=force, only=only, solo=solo)
        for k in ("done", "skipped", "failed"):
            total[k] += r2.get(k, 0)
        total["failures"].extend(r2.get("failures") or [])
    return total
