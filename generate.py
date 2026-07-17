"""独立生成 CLI：图片 / 视频 / 配音 / 音色设计四阶段命令。

用法:
  python generate.py images E1-E3 --out ./out [--provider grsai] [--force]
  python generate.py video E1 --out ./out [--force]
  python generate.py dub E1-E3 --out ./out [--force]
  python generate.py voice_design --out ./out [--force]
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path


def _load_env(skill_dir: Path) -> None:
    """手动解析 skill.env 文件，填充缺失的环境变量。

    查找顺序（先到先用，env 里的同名变量优先保留）：
      1) <skill_dir>/skill.env     —— skill 安装目录（开发者用）
      2) <cwd>/skill.env           —— 当前工作目录（项目目录部署时）
    """
    candidates = [skill_dir / "skill.env", Path.cwd() / "skill.env"]
    for env_file in candidates:
        if not env_file.exists():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def parse_ep_range(spec: str, episode_count: int) -> list[int]:
    """解析集号范围: E1 | E1-E3 | all"""
    spec = spec.strip().upper()
    if spec == "ALL":
        return list(range(1, episode_count + 1))
    if "-" in spec:
        a, b = spec.split("-", 1)
        return list(range(int(a.lstrip("E")), int(b.lstrip("E")) + 1))
    return [int(spec.lstrip("E"))]


def _dry_run(out_dir: str, ep_range: list[int], stage: str, force: bool = False,
             only: set | None = None, solo: bool = False) -> dict:
    """模拟运行：校验输入、统计会生成/跳过/失败多少，但不调用 provider API。"""
    stats = {"done": 0, "skipped": 0, "failed": 0, "failures": [], "checks": []}
    out = Path(out_dir)

    for ep in ep_range:
        ctx_path = out / f"E{ep}" / "gen_context.json"
        if not ctx_path.exists():
            stats["skipped"] += 1
            stats["checks"].append(f"E{ep}: gen_context.json 不存在，跳过")
            continue

        try:
            ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            stats["failed"] += 1
            stats["failures"].append({"ep": ep, "error": f"gen_context.json 解析失败: {e}"})
            continue

        if stage == "images":
            _dry_run_images(out, ep, ctx, stats, force=force, only=only, solo=solo)
        elif stage == "video":
            _dry_run_video(out, ep, ctx, stats, force=force)
        elif stage == "dub":
            _dry_run_dub(out, ep, ctx, stats, force=force)

    # 检查 provider 配置完整性
    from providers import load_config
    cfg = load_config()
    if stage == "images":
        img_name = cfg["image_provider"]
        if img_name not in ("grsai", "comfyui", "runninghub", "gemini"):
            stats["checks"].append(f"图片 provider 未知: {img_name}")
    if stage in ("video", "dub"):
        if not cfg["runninghub"]["api_key"]:
            stats["checks"].append("RunningHub API key 未配置，视频/配音将失败")

    return stats


def _dry_run_images(out: Path, ep: int, ctx: dict, stats: dict,
                    force: bool = False, only: set | None = None, solo: bool = False) -> None:
    sb = ctx.get("storyboard") or {}
    shots = sb.get("shots") or []
    shots_dir = out / f"E{ep}" / "shots_assets"

    for s in shots:
        sid = str(s.get("shot_id", ""))
        if not sid:
            stats["failed"] += 1
            stats["failures"].append({"ep": ep, "shot_id": "?", "error": "shot 缺 shot_id"})
            continue
        if only is not None and sid not in only:
            continue
        if not force and (shots_dir / f"{sid}.jpg").exists():
            stats["skipped"] += 1
            continue
        # 校验必填字段
        if not s.get("action_desc"):
            stats["checks"].append(f"E{ep}/{sid}: 缺 action_desc，出图质量可能下降")
        stats["done"] += 1


def _dry_run_video(out: Path, ep: int, ctx: dict, stats: dict, force: bool = False) -> None:
    sb = ctx.get("storyboard") or {}
    shots = sb.get("shots") or []
    shots_dir = out / f"E{ep}" / "shots_assets"

    for s in shots:
        sid = str(s.get("shot_id", ""))
        if not sid:
            continue
        if not force and (shots_dir / f"{sid}.mp4").exists():
            stats["skipped"] += 1
            continue
        if not (shots_dir / f"{sid}.jpg").exists():
            stats["failed"] += 1
            stats["failures"].append({"ep": ep, "shot_id": sid, "error": "首帧缺失，无法出视频"})
            continue
        if not s.get("video_prompt") and not s.get("video_prompt_en"):
            stats["checks"].append(f"E{ep}/{sid}: 缺 video_prompt，将回退 action_desc")
        stats["done"] += 1

def _episode_count(out_dir: str) -> int:
    """Read series.json and return episode_count."""
    sp = Path(out_dir) / "series.json"
    if not sp.exists():
        return 1
    try:
        series = json.loads(sp.read_text(encoding="utf-8"))
        return int(series.get("episode_count", 1))
    except (OSError, json.JSONDecodeError, ValueError):
        return 1


def _dry_run_dub(out: Path, ep: int, ctx: dict, stats: dict, force: bool = False) -> None:
    sb = ctx.get("storyboard") or {}
    shots = sb.get("shots") or []
    audio_dir = out / "audio" / f"E{ep}" / "dub"

    for s in shots:
        sid = str(s.get("shot_id", ""))
        dialogue = s.get("dialogue") or []
        if not dialogue:
            continue
        for idx, line in enumerate(dialogue):
            speaker = str(line.get("speaker", "unknown"))
            text = str(line.get("text", ""))
            if not text:
                continue
            dst = audio_dir / f"{sid}_{speaker}_line{idx}.wav"
            if not force and dst.exists():
                stats["skipped"] += 1
                continue
            stats["done"] += 1


def run_images(out_dir: str, ep_range: list[int], force: bool = False,
               only: set | None = None, solo: bool = False) -> dict:
    from providers import get_image_provider, get_upscale_provider, load_config
    from stages.images import run_images as _run
    cfg = load_config()
    img_p = get_image_provider()
    up_p = get_upscale_provider() if cfg["runninghub"]["upscale_workflow_id"] else None
    return _run(out_dir, ep_range=ep_range, provider=img_p, upscale_provider=up_p,
                threshold=cfg["grid"]["upscale_threshold"],
                target_aspect=cfg["grid"]["target_aspect"], force=force,
                only=only, solo=solo)


def run_video(out_dir: str, ep_range: list[int], force: bool = False) -> dict:
    from providers import get_video_provider
    from stages.video import run_video as _run
    return _run(out_dir, ep_range=ep_range, provider=get_video_provider(), force=force)


def run_dub(out_dir: str, ep_range: list[int], force: bool = False) -> dict:
    from providers import get_dub_provider
    from stages.dub import run_dub as _run
    return _run(out_dir, ep_range=ep_range, provider=get_dub_provider(), force=force)


def run_voice_design(out_dir: str, force: bool = False) -> dict:
    from providers import get_dub_provider
    from stages.voice_design import run_voice_design as _run
    return _run(out_dir, provider=get_dub_provider(), force=force)


def _print_stats(stage: str, stats: dict) -> None:
    d, s, f = stats.get("done", 0), stats.get("skipped", 0), stats.get("failed", 0)
    print(f"[{stage}] 完成 {d} / 跳过 {s} / 失败 {f}")
    if f:
        print(f"  ⚠ {f} 个失败，详见 generate_log.json", file=sys.stderr)


_STAGE_LABELS_CN = {"images": "图片", "video": "视频", "dub": "配音", "voice_design": "音色设计"}


def _emit_stats(stage: str, stats: dict, as_json: bool) -> None:
    """stage 用英文标识（JSON 契约稳定）；人读模式映射为中文标签。"""
    if as_json:
        print(json.dumps({"stage": stage,
                          "done": stats.get("done", 0),
                          "skipped": stats.get("skipped", 0),
                          "failed": stats.get("failed", 0),
                          "failures": stats.get("failures", [])}, ensure_ascii=False))
    else:
        _print_stats(_STAGE_LABELS_CN.get(stage, stage), stats)


def _print_status(data: dict) -> None:
    for epd in data["episodes"]:
        shots = epd["shots"]
        r = sum(1 for s in shots if s["state"] == "ready")
        p = sum(1 for s in shots if s["state"] == "pending")
        f = sum(1 for s in shots if s["state"] == "failed")
        print(f"E{epd['ep']}: ready {r} / pending {p} / failed {f}")
        for s in shots:
            if s["state"] == "failed":
                print(f"  ✗ {s['shot_id']} (in_grid={s['in_grid']}): {s.get('reason','')}")


def main() -> int:
    skill_dir = Path(__file__).parent
    _load_env(skill_dir)

    parser = argparse.ArgumentParser(prog="generate.py",
                                     description="nuomi-drama-skills 独立生成 CLI")
    parser.add_argument("stage", choices=["images", "video", "dub", "voice_design", "status"],
                        help="生成阶段 / status 报告")
    parser.add_argument("ep_range", nargs="?", default=None,
                        help="集号范围: E1 | E1-E3 | all（voice_design 不需要）")
    parser.add_argument("--out", default="./out", help="编译输出目录（默认 ./out）")
    parser.add_argument("--force", action="store_true", help="强制重生成（忽略已有产物）")
    parser.add_argument("--provider", default=None,
                        help="覆盖 IMAGE_PROVIDER (grsai|comfyui|runninghub)")
    parser.add_argument("--only", default=None,
                        help="只处理指定镜(逗号分隔 shot_id)，仅 images")
    parser.add_argument("--solo", action="store_true",
                        help="单镜旁路直出，不走宫格（需配 --only/--retry-failed）")
    parser.add_argument("--retry-failed", action="store_true", dest="retry_failed",
                        help="只重跑有失败记录且当前无产物的镜")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="结构化 JSON 输出")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="只校验、统计、报告，不实际调用 provider API")

    args = parser.parse_args()
    if args.provider:
        os.environ["IMAGE_PROVIDER"] = args.provider

    out_dir = str(Path(args.out).resolve())
    if not Path(out_dir).exists():
        print(f"ERROR: 输出目录不存在: {out_dir}", file=sys.stderr)
        return 1

    only_set = set(x.strip() for x in args.only.split(",") if x.strip()) if args.only else None
    if only_set is not None and args.retry_failed:
        print("ERROR: --only 与 --retry-failed 互斥", file=sys.stderr)
        return 1
    if args.solo and not (only_set is not None or args.retry_failed):
        print("ERROR: --solo 需配 --only 或 --retry-failed", file=sys.stderr)
        return 1
    if (only_set is not None or args.solo or args.retry_failed) and args.stage != "images":
        print("ERROR: --only/--solo/--retry-failed 仅适用于 images 阶段", file=sys.stderr)
        return 1

    if args.stage != "voice_design" and args.ep_range is None:
        print("ERROR: 请提供集号范围（如 E1 | E1-E3 | all）", file=sys.stderr)
        return 1

    if args.stage == "status":
        ep_range = parse_ep_range(args.ep_range, _episode_count(out_dir))
        from stages.status import collect_status
        data = collect_status(out_dir, ep_range)
        if args.as_json:
            print(json.dumps(data, ensure_ascii=False))
        else:
            _print_status(data)
        return 0

    stats: dict = {}
    if args.dry_run:
        ep_range = parse_ep_range(args.ep_range, _episode_count(out_dir))
        stats = _dry_run(out_dir, ep_range, args.stage, force=args.force,
                         only=only_set, solo=args.solo)
        _emit_stats(args.stage, stats, args.as_json)
    elif args.stage == "voice_design":
        stats = run_voice_design(out_dir, force=args.force)
        _emit_stats("voice_design", stats, args.as_json)
    else:
        ep_range = parse_ep_range(args.ep_range, _episode_count(out_dir))
        if args.stage == "images":
            only = only_set
            if args.retry_failed:
                from stages.status import failed_shots_to_retry
                only = failed_shots_to_retry(out_dir, ep_range, "images")
            stats = run_images(out_dir, ep_range, force=args.force, only=only, solo=args.solo)
            _emit_stats("images", stats, args.as_json)
        elif args.stage == "video":
            stats = run_video(out_dir, ep_range, force=args.force)
            _emit_stats("video", stats, args.as_json)
        elif args.stage == "dub":
            stats = run_dub(out_dir, ep_range, force=args.force)
            _emit_stats("dub", stats, args.as_json)

    return 1 if stats.get("failed", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
