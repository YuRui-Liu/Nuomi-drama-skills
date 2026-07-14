# .claude/skills/nuomi-drama-skills/stages/video.py
from __future__ import annotations
import json
from pathlib import Path
from providers.base import VideoProvider
from stages import GenerateLog

_MAX_GROUP_DURATION = 18.0
_DEFAULT_FRAME_RATE = 24


class DirectorCall:
    """A batched call to the LTX Director for multi-shot group generation."""

    def __init__(self, global_prompt: str, segments: list[dict], motion_mode: str):
        self.global_prompt = global_prompt
        self.segments = segments
        self.motion_mode = motion_mode


def build_director_calls(shot_group, shots, scene_map=None) -> list[DirectorCall]:
    """Group shots within a narrative group into DirectorCalls.

    Rules:
    - Shots in the same scene with total duration ≤ 18s → merged into one call (motion_mode="smooth")
    - Scene change or cumulative duration would exceed 18s → new call (hard cut between calls)

    Args:
        shot_group: dict with "shot_ids" list, e.g. {"shot_ids": ["s1","s2","s3"]}
        shots: full list of shot dicts from gen_context.json storyboard
        scene_map: optional dict for scene metadata (unused, reserved)

    Returns:
        list of DirectorCall objects
    """
    shot_ids = shot_group.get("shot_ids", [])
    if not shot_ids:
        return []

    shot_lookup = {str(s.get("shot_id", "")): s for s in shots}

    calls: list[DirectorCall] = []
    current_segments: list[dict] = []
    current_duration = 0.0
    current_scene = None

    for sid in shot_ids:
        shot = shot_lookup.get(str(sid))
        if not shot:
            continue

        scene = shot.get("scene", "")
        duration = float(shot.get("duration") or 4)

        # Start a new call if scene changes or adding this shot would exceed the limit
        if current_scene is not None and (
            scene != current_scene or current_duration + duration > _MAX_GROUP_DURATION
        ):
            calls.append(DirectorCall(
                global_prompt="",
                segments=list(current_segments),
                motion_mode="smooth",
            ))
            current_segments = []
            current_duration = 0.0

        segment = {
            "shot_id": str(sid),
            "prompt": shot.get("video_prompt_en") or shot.get("video_prompt") or shot.get("action_desc", ""),
            "duration": duration,
        }
        current_segments.append(segment)
        current_duration += duration
        current_scene = scene

    # Flush the last group
    if current_segments:
        calls.append(DirectorCall(
            global_prompt="",
            segments=list(current_segments),
            motion_mode="smooth",
        ))

    return calls


def run_episode_video(out_dir: str, ep: int, provider: VideoProvider,
                      force: bool = False) -> dict:
    ep_dir = Path(out_dir) / f"E{ep}"
    ctx_path = ep_dir / "gen_context.json"
    if not ctx_path.exists():
        return {"done": 0, "skipped": 0, "failed": 0, "failures": []}
    ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
    storyboard = ctx.get("storyboard") or {}
    shots = storyboard.get("shots") or []
    shot_groups = storyboard.get("shot_groups") or []
    shots_dir = ep_dir / "shots_assets"
    log = GenerateLog(out_dir)
    stats = {"done": 0, "skipped": 0, "failed": 0, "failures": []}

    # Build global prompt from storyboard-level context
    synopsis = storyboard.get("synopsis", "")
    emotion_tone = storyboard.get("emotion_tone", "")
    global_prompt_base = synopsis
    if emotion_tone:
        global_prompt_base = f"{synopsis}\nEmotion tone: {emotion_tone}"

    # If no narrative groups, fall back to per-shot iteration
    if not shot_groups:
        for s in shots:
            sid = str(s.get("shot_id", ""))
            dst = shots_dir / f"{sid}.mp4"
            if not force and dst.exists():
                stats["skipped"] += 1
                continue
            frame_path = shots_dir / f"{sid}.jpg"
            if not frame_path.exists():
                stats["skipped"] += 1
                continue
            prompt = s.get("video_prompt_en") or s.get("video_prompt") or s.get("action_desc", "")
            duration = float(s.get("duration") or 4)
            try:
                data = provider.generate_video(prompt, str(frame_path), duration)
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(data)
                stats["done"] += 1
            except Exception as e:
                log.append("video", ep, sid, str(e))
                stats["failed"] += 1
                stats["failures"].append({"ep": ep, "shot_id": sid, "error": str(e)})
        return stats

    # Narrative group batching path
    for group in shot_groups:
        calls = build_director_calls(group, shots)
        for dc in calls:
            dc.global_prompt = global_prompt_base

            # Build provider-ready segments and validate all first-frame images exist
            provider_segments: list[dict] = []
            motion_modes: list[str] = []
            all_frames_exist = True

            for seg in dc.segments:
                shot_id = seg["shot_id"]
                frame_path = shots_dir / f"{shot_id}.jpg"
                if not frame_path.exists():
                    all_frames_exist = False
                    break
                length_frames = max(1, int(round(seg["duration"] * _DEFAULT_FRAME_RATE)))
                provider_segments.append({
                    "prompt": seg["prompt"],
                    "image_path": str(frame_path),
                    "length": length_frames,
                    "type": "image",
                })
                motion_modes.append("smooth")

            if not all_frames_exist:
                stats["skipped"] += len(dc.segments)
                continue

            # Determine output path: single-segment → sN.mp4, multi-segment → group_sN.mp4
            if len(dc.segments) == 1:
                shot_id = dc.segments[0]["shot_id"]
                dst = shots_dir / f"{shot_id}.mp4"
            else:
                first_shot_id = dc.segments[0]["shot_id"]
                dst = shots_dir / f"group_{first_shot_id}.mp4"

            if not force and dst.exists():
                stats["skipped"] += len(dc.segments)
                continue

            try:
                data = provider.generate_video_group(
                    dc.global_prompt, provider_segments, motion_modes,
                )
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(data)
                stats["done"] += len(dc.segments)
            except Exception as e:
                for seg in dc.segments:
                    log.append("video", ep, seg["shot_id"], str(e))
                    stats["failed"] += 1
                    stats["failures"].append({
                        "ep": ep, "shot_id": seg["shot_id"], "error": str(e),
                    })

    return stats


def run_video(out_dir: str, ep_range: list[int], provider: VideoProvider,
              force: bool = False) -> dict:
    total = {"done": 0, "skipped": 0, "failed": 0, "failures": []}
    for ep in ep_range:
        r = run_episode_video(out_dir, ep=ep, provider=provider, force=force)
        for k in ("done", "skipped", "failed"):
            total[k] += r.get(k, 0)
        total["failures"].extend(r.get("failures") or [])
    return total
