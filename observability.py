"""Observability — aggregate generation state into structured reports.

Reads gen_context.json, filesystem state, and generate_log.json to
produce GenerationSummary. Inspired by seedance-2.0 observability patterns.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class StageStats:
    stage: str
    total: int = 0
    done: int = 0
    failed: int = 0
    skipped: int = 0

    @property
    def success_rate(self) -> float:
        attempted = self.done + self.failed
        return self.done / attempted if attempted > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "stage": self.stage, "total": self.total,
            "done": self.done, "failed": self.failed,
            "skipped": self.skipped,
            "success_rate": round(self.success_rate, 3),
        }


@dataclass
class EpisodeProgress:
    ep: int
    images: StageStats = field(default_factory=lambda: StageStats("images"))
    video: StageStats = field(default_factory=lambda: StageStats("video"))
    dub: StageStats = field(default_factory=lambda: StageStats("dub"))

    def to_dict(self) -> dict:
        return {
            "ep": self.ep,
            "images": self.images.to_dict(),
            "video": self.video.to_dict(),
            "dub": self.dub.to_dict(),
        }


@dataclass
class GenerationSummary:
    project_dir: str
    generated_at: str
    total_episodes: int
    episodes: list[EpisodeProgress] = field(default_factory=list)
    overall_health: str = "healthy"

    def to_dict(self) -> dict:
        return {
            "project_dir": self.project_dir,
            "generated_at": self.generated_at,
            "total_episodes": self.total_episodes,
            "overall_health": self.overall_health,
            "episodes": [e.to_dict() for e in self.episodes],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def to_markdown(self) -> str:
        lines = [
            "# 生成摘要",
            "",
            f"**项目**: {self.project_dir}",
            f"**时间**: {self.generated_at}",
            f"**健康度**: {self.overall_health}",
            "",
            "| 集 | 图片 | 视频 | 配音 |",
            "|----|------|------|------|",
        ]
        for ep in self.episodes:
            lines.append(
                f"| E{ep.ep} | {ep.images.done}/{ep.images.total} "
                f"| {ep.video.done}/{ep.video.total} "
                f"| {ep.dub.done}/{ep.dub.total} |"
            )
        return "\n".join(lines)


def build_summary(out_dir: str) -> GenerationSummary:
    """Aggregate all observable state into a single report."""
    out = Path(out_dir)
    episodes: list[EpisodeProgress] = []

    ep_dirs = sorted(out.glob("E*"))
    for ed in ep_dirs:
        try:
            ep_num = int(ed.name.lstrip("E"))
        except ValueError:
            continue

        ctx_path = ed / "gen_context.json"
        if not ctx_path.is_file():
            continue

        try:
            ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        sb = ctx.get("storyboard") or {}
        shots = sb.get("shots") or []
        total_shots = len(shots)
        shots_dir = ed / "shots_assets"

        img_done = sum(1 for s in shots
                       if isinstance(s, dict) and s.get("shot_id")
                       and (shots_dir / f"{s['shot_id']}.jpg").exists())
        vid_done = sum(1 for s in shots
                       if isinstance(s, dict) and s.get("shot_id")
                       and (shots_dir / f"{s['shot_id']}.mp4").exists())

        # Dub check is approximate — count per-shot wav files
        dub_done = 0
        audio_dub = out / "audio" / f"E{ep_num}" / "dub"
        if audio_dub.is_dir():
            wav_shots = set()
            for w in audio_dub.glob("*.wav"):
                sid = w.stem.split("_")[0] if "_" in w.stem else w.stem
                wav_shots.add(sid)
            dub_done = len(wav_shots & {
                s["shot_id"] for s in shots
                if isinstance(s, dict) and s.get("shot_id")
            })

        ep_prog = EpisodeProgress(
            ep=ep_num,
            images=StageStats("images", total=total_shots, done=img_done,
                              failed=0, skipped=total_shots - img_done),
            video=StageStats("video", total=total_shots, done=vid_done,
                             failed=0, skipped=total_shots - vid_done),
            dub=StageStats("dub", total=total_shots, done=dub_done,
                           failed=0, skipped=total_shots - dub_done),
        )
        episodes.append(ep_prog)

    # Read error log for failure counts
    log_path = out / "generate_log.json"
    if log_path.is_file():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            ep = entry.get("ep")
            stage = entry.get("stage", "")
            for ep_prog in episodes:
                if ep_prog.ep == ep:
                    s = getattr(ep_prog, stage, None)
                    if s:
                        s.failed += 1
                    break

    overall = "healthy"
    for ep in episodes:
        if ep.images.success_rate < 0.5 and ep.images.total > 0:
            overall = "blocked"
            break
        if ep.images.success_rate < 0.8 and ep.images.total > 0:
            overall = "degraded"

    return GenerationSummary(
        project_dir=str(out.resolve()),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        total_episodes=len(episodes),
        episodes=episodes,
        overall_health=overall,
    )
