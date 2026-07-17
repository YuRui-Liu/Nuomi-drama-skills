"""SRT subtitle exporter.

Reads gen_context.json per episode, extracts dialogue from storyboard shots,
and generates standard SRT subtitle files.

Registered as exporter "srt" via hooks.register_exporter.
"""
from __future__ import annotations

import json
from pathlib import Path

from hooks import register_exporter


def _seconds_to_srt_time(seconds: float) -> str:
    """Convert float seconds to SRT timestamp: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def export_srt(out_dir: str, ep_range: list[int] | None = None,
               lang: str = "zh") -> list[Path]:
    """Export SRT subtitles for specified episodes.

    Args:
        out_dir: Project output directory.
        ep_range: Episode numbers to export (None = auto-detect).
        lang: Language code for filename suffix.

    Returns:
        List of generated SRT file paths.
    """
    out = Path(out_dir)
    generated: list[Path] = []

    if ep_range is None:
        ep_dirs = sorted(out.glob("E*"))
        ep_range = []
        for d in ep_dirs:
            try:
                ep_range.append(int(d.name.lstrip("E")))
            except ValueError:
                pass

    for ep in ep_range:
        ctx_path = out / f"E{ep}" / "gen_context.json"
        if not ctx_path.is_file():
            continue

        try:
            ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        sb = ctx.get("storyboard") or {}
        shots = sb.get("shots") or []
        if not isinstance(shots, list) or not shots:
            continue

        entries: list[str] = []
        index = 0
        time_cursor = 0.0

        for shot in shots:
            if not isinstance(shot, dict):
                continue
            duration = float(shot.get("duration", 3.0))
            dialogue = shot.get("dialogue") or []

            if not dialogue:
                time_cursor += duration
                continue

            sub_dur = duration / len(dialogue)
            for line in dialogue:
                if not isinstance(line, dict):
                    continue
                speaker = line.get("speaker", "")
                text = line.get("text", "")
                if not text:
                    continue

                index += 1
                start = _seconds_to_srt_time(time_cursor)
                end = _seconds_to_srt_time(time_cursor + sub_dur)

                prefix = f"{speaker}: " if speaker else ""
                entries.append(f"{index}\n{start} --> {end}\n{prefix}{text}\n")
                time_cursor += sub_dur

        if not entries:
            continue

        srt_path = out / f"E{ep}" / f"subtitle_{lang}.srt"
        srt_path.parent.mkdir(parents=True, exist_ok=True)
        srt_path.write_text("\n".join(entries), encoding="utf-8")
        generated.append(srt_path)

    return generated


register_exporter("srt", export_srt)
