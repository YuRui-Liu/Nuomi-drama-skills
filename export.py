"""nuomi-drama-skills compiler: manuscript/*.md -> importable project folder.
Self-contained, stdlib only. Validates with vendored frozen validators before declaring success.

Usage: python export.py <manuscript_dir> <out_project_dir>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import contract
import emit
import manuscript_parse as mp
import validators


def export_project(manuscript_dir, out_dir) -> dict:
    manuscript_dir = Path(manuscript_dir)
    out_dir = Path(out_dir)
    errors: list[str] = []

    idea, triplet, mode, count = mp.load_idea(manuscript_dir)
    outline = mp.load_outline(manuscript_dir) or {}
    arcs = mp.load_arcs(manuscript_dir)
    bible = mp.load_bible(manuscript_dir)

    # 三轴一致性:SOFT 软提醒(不阻断渐进创作),镜像平台 axes loader 的硬校验,
    # 把 genre/style/tone 的契约漂移在 export 期就暴露,而非拖到平台导入才报错。
    triplet_warnings = validators.validate_triplet(triplet, manuscript_dir)

    # --- validate inputs BEFORE writing anything the platform would load ---
    if count <= 0:
        errors.append("00_立意.md 缺 episode_count(必须 ≥1)")
    errors += [f"大纲: {e}" for e in validators.validate_outline(outline, count)] if count > 0 else []
    errors += [f"分卷节拍表: {e}" for e in validators.validate_beats(arcs)]

    episodes: dict[int, tuple] = {}
    skeleton: list[int] = []
    vp_gaps: list[str] = []
    dur_warnings: list[str] = []            # 总时长不在 [90,180]s 的已写集
    script_format_warnings: list[str] = []  # 剧本疑似非结构化(无 `## 第N场` 场头)
    for ep in range(1, max(count, 0) + 1):
        script, sb = mp.load_episode(manuscript_dir, ep)
        if sb is not None:
            sb_errs = validators.validate_storyboard(sb)
            errors += [f"E{ep} 分镜表: {e}" for e in sb_errs]
            shots = sb.get("shots") or []
            missing = [str(s.get("shot_id")) for s in shots
                       if isinstance(s, dict) and not str(s.get("video_prompt") or "").strip()]
            if missing:
                vp_gaps.append(f"E{ep}: {', '.join(missing)}")
            total = sum(float(s.get("duration") or 0) for s in shots if isinstance(s, dict))
            if total and not (90.0 <= total <= 180.0):
                dur_warnings.append(f"E{ep}: {round(total, 1)}s / {len(shots)}镜")
        else:
            skeleton.append(ep)
        ep_path = manuscript_dir / "episodes" / f"E{ep}.md"
        if script is not None and ep_path.is_file() and "## 第" not in ep_path.read_text(encoding="utf-8"):
            script_format_warnings.append(f"E{ep}")
        episodes[ep] = (script, sb)

    if errors:
        return {"ok": False, "errors": errors, "skeleton_episodes": skeleton,
                "video_prompt_gaps": vp_gaps, "duration_warnings": dur_warnings,
                "script_format_warnings": script_format_warnings,
                "triplet_warnings": triplet_warnings,
                "contract_version": contract.CONTRACT_VERSION}

    # --- emit (only after all validation passes) ---
    out_dir.mkdir(parents=True, exist_ok=True)
    emit.emit_series(out_dir, idea=idea, triplet=triplet, mode=mode,
                     episode_count=count, outline=outline)
    emit.emit_arcs(out_dir, arcs=arcs)
    emit.emit_story_bible(out_dir, bible)
    emit.emit_registry(out_dir, bible)
    for ep, (script, sb) in episodes.items():
        emit.emit_episode(out_dir, ep=ep, mode=mode, triplet=triplet, script=script, storyboard=sb)
    genres_copied = emit.emit_project_genres(out_dir, manuscript_dir)
    emit.emit_harness_state(out_dir)

    return {"ok": True, "errors": [], "skeleton_episodes": skeleton,
            "video_prompt_gaps": vp_gaps, "duration_warnings": dur_warnings,
            "script_format_warnings": script_format_warnings,
            "triplet_warnings": triplet_warnings, "genres_copied": genres_copied,
            "episodes": count,
            "contract_version": contract.CONTRACT_VERSION, "out_dir": str(out_dir)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Compile a nuomi-drama manuscript into an importable project.")
    ap.add_argument("manuscript_dir")
    ap.add_argument("out_project_dir")
    ap.add_argument("--jianying", action="store_true",
                    help="编译后同时导出剪映草稿 (jianying_draft.json)")
    args = ap.parse_args(argv)
    report = export_project(args.manuscript_dir, args.out_project_dir)
    if report["ok"]:
        print(f"OK 导出成功 (contract {report['contract_version']}, {report['episodes']} 集, "
              f"骨架集 {report['skeleton_episodes']}) -> {report['out_dir']}")
        if report.get("genres_copied"):
            print(f"  · 已随项目自带自定义题材: {', '.join(report['genres_copied'])} (project/genres/)")
        if args.jianying:
            from exporters.jianying import export_jianying
            export_jianying(
                {"episodes": [
                    {"episode_id": f"E{n}"}
                    for n in range(1, report.get("episodes", 0) + 1)
                ]},
                report["out_dir"],
            )
            print("  · 剪映草稿已导出")
        if report.get("triplet_warnings"):
            print("⚠ 软提醒:三轴(题材/风格/基调)与平台 axes 表不一致,平台导入会报错,请回 00_立意.md 修正:",
                  file=sys.stderr)
            for w in report["triplet_warnings"]:
                print(f"  - {w}", file=sys.stderr)
        if report.get("video_prompt_gaps"):
            print("⚠ 软提醒:以下集的镜头缺 video_prompt(出视频将回退 action_desc,运动表现打折):",
                  file=sys.stderr)
            for g in report["video_prompt_gaps"]:
                print(f"  - {g}", file=sys.stderr)
        if report.get("duration_warnings"):
            print("⚠ 软提醒:以下集总时长不在 90–180s(竖屏短剧推荐区间):", file=sys.stderr)
            for w in report["duration_warnings"]:
                print(f"  - {w}", file=sys.stderr)
        if report.get("script_format_warnings"):
            print("⚠ 软提醒:以下集剧本疑似非结构化(应遵 reference/剧本格式规范.md:`## 第N场`…`**【第X集完】**`):",
                  file=sys.stderr)
            print(f"  - {', '.join(report['script_format_warnings'])}", file=sys.stderr)
        return 0
    print("导出失败,以下问题需在 manuscript 修正(未写出任何平台文件):", file=sys.stderr)
    for e in report["errors"]:
        print(f"  - {e}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
