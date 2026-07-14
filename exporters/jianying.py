"""Jianying (剪映) draft exporter.

Produces a simple JSON draft consumable by Jianying's import/scripting API.
Registered as exporter "jianying" via hooks.register_exporter.

The draft includes:
  - draft_name, duration, resolution
  - tracks array with video, audio, and subtitle clips
  - Each clip derived from storyboard shots and dialogue.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from hooks import register_exporter


# ── Constants ──────────────────────────────────────────────────────
_DEFAULT_RESOLUTION = {"width": 1080, "height": 1920}  # 9:16 vertical
_DEFAULT_FPS = 24
_DEFAULT_TRANSITION = {"name": "fade", "duration": 0.3}


def _build_jianying_draft(
    compiled: dict[str, Any],
    out_dir: str,
    ep: int,
) -> dict[str, Any]:
    """Build a Jianying-compatible draft JSON from compiled episode data.

    Args:
        compiled: The full gen_context.json data (includes storyboard, script, etc.).
        out_dir: Output directory (used for resolving relative asset paths).
        ep: Episode number.

    Returns:
        A dict with ``draft_name``, ``duration``, ``resolution``, and ``tracks``.
    """
    storyboard = compiled.get("storyboard") or {}
    shots: list[dict] = storyboard.get("shots") or []
    target_aspect = compiled.get("target_aspect", "9:16")

    # ── Resolve resolution from aspect ratio ─────────────────────
    if target_aspect == "9:16":
        resolution = {"width": 1080, "height": 1920}
    elif target_aspect == "16:9":
        resolution = {"width": 1920, "height": 1080}
    elif target_aspect == "1:1":
        resolution = {"width": 1080, "height": 1080}
    else:
        resolution = _DEFAULT_RESOLUTION

    # ── Build tracks ─────────────────────────────────────────────
    video_clips: list[dict] = []
    audio_clips: list[dict] = []
    subtitle_clips: list[dict] = []

    time_cursor = 0.0
    ep_id = f"E{ep}"

    for i, shot in enumerate(shots):
        if not isinstance(shot, dict):
            continue

        shot_id = shot.get("shot_id", f"s{i}")
        duration = float(shot.get("duration") or 3.0)
        scene = shot.get("scene", "")
        action_desc = shot.get("action_desc", "")
        dialogue = shot.get("dialogue") or []
        shot_num = shot.get("shot_number", i + 1)

        # ── Video clip ──────────────────────────────────────────
        video_clips.append({
            "id": f"video_{shot_id}",
            "type": "video",
            "name": f"{ep_id}-S{shot_num:02d}",
            "start": time_cursor,
            "duration": duration,
            "source": f"{out_dir}/shots/{shot_id}.mp4",
            "scene": scene,
            "transition": dict(_DEFAULT_TRANSITION),
            "effect": None,
        })

        # ── Audio clips (dialogue) ───────────────────────────────
        if dialogue:
            # Split dialogue evenly within shot duration
            sub_dur = duration / len(dialogue) if dialogue else duration
            for di, line in enumerate(dialogue):
                if not isinstance(line, dict):
                    continue
                speaker = line.get("speaker", "旁白")
                text = line.get("text", "")
                emotion = line.get("emotion", "")
                clip_start = time_cursor + di * sub_dur

                audio_clips.append({
                    "id": f"audio_{shot_id}_d{di}",
                    "type": "audio",
                    "name": f"{speaker} - {text[:20]}",
                    "start": clip_start,
                    "duration": sub_dur,
                    "source": f"{out_dir}/dub/{shot_id}_d{di}.wav",
                    "speaker": speaker,
                    "emotion": emotion,
                })

                # ── Subtitle clip ──────────────────────────────
                subtitle_clips.append({
                    "id": f"sub_{shot_id}_d{di}",
                    "type": "subtitle",
                    "text": text,
                    "start": clip_start,
                    "duration": sub_dur,
                    "speaker": speaker,
                    "style": "default",
                })

        time_cursor += duration

    total_duration = math.ceil(time_cursor * 10) / 10

    return {
        "draft_name": f"{ep_id}",
        "duration": total_duration,
        "resolution": resolution,
        "fps": _DEFAULT_FPS,
        "tracks": [
            {"track_type": "video", "clips": video_clips},
            {"track_type": "audio", "clips": audio_clips},
            {"track_type": "subtitle", "clips": subtitle_clips},
        ],
    }


def export_jianying(compiled: dict[str, Any], out_dir: str) -> None:
    """Export a Jianying draft for every episode in the compiled project.

    Iterates over episode directories, reads gen_context.json for each,
    and writes a ``jianying_draft.json`` into each episode's folder.
    """
    episodes = compiled.get("episodes") or []
    if not episodes:
        # Single-episode mode: compiled IS the gen_context
        ep = compiled.get("episode_id", "E1")
        ep_num = int(str(ep).lstrip("E") or 1)
        draft = _build_jianying_draft(compiled, out_dir, ep_num)
        draft_path = Path(out_dir) / f"{ep}" / "jianying_draft.json"
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(
            json.dumps(draft, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return

    for ep_data in episodes:
        ep = ep_data.get("episode_id", "E1")
        ep_num = int(str(ep).lstrip("E") or 1)
        edir = Path(out_dir) / str(ep)
        ctx_path = edir / "gen_context.json"
        if not ctx_path.is_file():
            continue
        try:
            ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        draft = _build_jianying_draft(ctx, str(edir), ep_num)
        draft_path = edir / "jianying_draft.json"
        draft_path.write_text(
            json.dumps(draft, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


# ── Register ──────────────────────────────────────────────────────
register_exporter("jianying", export_jianying)
