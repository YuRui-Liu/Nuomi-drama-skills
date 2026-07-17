"""Exporters package — format-specific project exporters.

Exporters:
    jianying    Jianying (剪映) JSON draft (existing)
    srt         Standard SRT subtitle files
    ffmpeg      FFmpeg composition scripts

All exporters register via hooks.register_exporter() (same pattern as
jianying.py). Import triggers side-effect registration.
"""
from __future__ import annotations

# Import to trigger hook registration
import exporters.jianying  # noqa: F401 — registers "jianying"
import exporters.srt       # noqa: F401 — registers "srt"
import exporters.ffmpeg    # noqa: F401 — registers "ffmpeg"
