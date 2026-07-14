# .claude/skills/nuomi-drama-skills/styles_table.py
"""skill 自带的风格 suffix 表：逐字节镜像 shot_agent/axes/builtin/styles/visual_styles.json
的 prompt_suffix/negative_suffix @ CONTRACT 2026-06-20。generate 出图时按 style_id 查表应用。
漂移由 tests/skill_export/test_styles_table.py 的 parity 测强制守护。"""
from __future__ import annotations

STYLE_SUFFIXES: dict[str, dict] = {
    "real/cinematic-warm-v1": {
        "prompt_suffix": "cinematic, warm tungsten grade, shallow depth of field, film grain",
        "negative_suffix": "no subtitles, no watermark, no split frame, no text overlay",
    },
    "real/cinematic-cool-v1": {
        "prompt_suffix": "cinematic, teal-and-orange cool grade, crisp contrast, anamorphic flare",
        "negative_suffix": "no subtitles, no watermark, no split frame, no text overlay",
    },
    "real/doc-natural-v1": {
        "prompt_suffix": "naturalistic, available daylight, handheld realism, true-to-life color",
        "negative_suffix": "no subtitles, no watermark, no split frame, no text overlay",
    },
    "real/golden-hour-romance-v1": {
        "prompt_suffix": "warm golden-hour sunlight from the left, soft backlight rim, shallow depth of field, dreamy bokeh, romantic mood, photorealistic",
        "negative_suffix": "no subtitles, no watermark, no split frame, no text overlay",
    },
    "2D/anime-cel-v1": {
        "prompt_suffix": "anime cel-shaded, clean line art, vivid pastel palette, soft gradient sky",
        "negative_suffix": "no subtitles, no watermark, no split frame, no text overlay",
    },
    "2D/guofeng-ink-v1": {
        "prompt_suffix": "chinese ink wash painting, calligraphic brush lines, rice-paper texture, muted earth tones",
        "negative_suffix": "no subtitles, no watermark, no split frame, no text overlay",
    },
    "2D/ghibli-warm-v1": {
        "prompt_suffix": "ghibli style, soft hand-painted backgrounds, lush watercolor skies, warm pastel palette, gentle anime, whimsical cozy atmosphere",
        "negative_suffix": "no subtitles, no watermark, no split frame, no text overlay",
    },
    "2D/guofeng-gongbi-v1": {
        "prompt_suffix": "chinese gongbi fine-brush painting, meticulous detailed linework, rich mineral pigments, ornate patterns, gold accents, elegant traditional guofeng",
        "negative_suffix": "no subtitles, no watermark, no split frame, no text overlay",
    },
    "3D/pixar-stylized-v1": {
        "prompt_suffix": "Pixar-style stylized 3D render, soft global illumination, rounded forms, subsurface skin",
        "negative_suffix": "no subtitles, no watermark, no split frame, no text overlay",
    },
    "3D/photoreal-octane-v1": {
        "prompt_suffix": "photorealistic 3D render, physically-based materials, HDRI lighting, ray-traced reflections",
        "negative_suffix": "no subtitles, no watermark, no split frame, no text overlay",
    },
    "3D/pixar-cute-v1": {
        "prompt_suffix": "pixar style stylized 3D render, cute rounded character forms, big expressive eyes, soft global illumination, subsurface skin, warm friendly palette",
        "negative_suffix": "no subtitles, no watermark, no split frame, no text overlay",
    },
}


def style_suffix(style_id: str) -> tuple[str, str]:
    """按 style_id 取 (prompt_suffix, negative_suffix)。丢前缀时按末段唯一匹配兜底；仍无 → ('','')。"""
    sid = str(style_id or "")
    e = STYLE_SUFFIXES.get(sid)
    if e is None:
        tail = sid.rsplit("/", 1)[-1]
        hits = [v for k, v in STYLE_SUFFIXES.items() if k.rsplit("/", 1)[-1] == tail]
        if len(hits) == 1:
            e = hits[0]
    if e is None:
        return ("", "")
    return (e["prompt_suffix"], e["negative_suffix"])
