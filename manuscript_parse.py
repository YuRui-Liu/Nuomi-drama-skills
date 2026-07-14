"""Markdown manuscript → structured dicts. Stdlib only. All structured data lives in
```json fenced blocks; prose lives outside fences."""
from __future__ import annotations

import json
import re

_FENCE_RE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)
_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def first_json_block(md: str) -> dict | None:
    """Parse the first ```json fenced block. Returns None if none present.
    Raises ValueError (with context) if a block exists but is malformed."""
    m = _FENCE_RE.search(md or "")
    if not m:
        return None
    raw = m.group(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"json 围栏块解析失败: {e}") from e


def extract_sections(md: str) -> dict:
    """Split markdown by `## ` headings. Returns {heading: body, ..., '_preamble': text-before-first-h2}."""
    md = md or ""
    out: dict[str, str] = {}
    matches = list(_H2_RE.finditer(md))
    out["_preamble"] = md[: matches[0].start()] if matches else md
    for i, mt in enumerate(matches):
        start = mt.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        out[mt.group(1).strip()] = md[start:end]
    return out


from pathlib import Path


def _read(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.is_file() else None


def load_idea(manuscript_dir) -> tuple[str | None, dict | None, str, int]:
    """Return (idea_prose, triplet, mode, episode_count) from 00_立意.md."""
    md = _read(Path(manuscript_dir) / "00_立意.md")
    if md is None:
        return None, None, "series", 0
    block = first_json_block(md) or {}
    idea = _FENCE_RE.sub("", md).strip() or None
    return idea, block.get("triplet"), block.get("mode", "series"), int(block.get("episode_count") or 0)


def load_outline(manuscript_dir) -> dict | None:
    md = _read(Path(manuscript_dir) / "01_大纲.md")
    return first_json_block(md) if md is not None else None


def load_arcs(manuscript_dir) -> list:
    md = _read(Path(manuscript_dir) / "02_分卷节拍表.md")
    block = first_json_block(md) if md is not None else None
    return (block or {}).get("arcs", []) if isinstance(block, dict) else []


def load_bible(manuscript_dir) -> dict:
    """Merge bible/*.md json blocks into {characters, scenes, props, canon, foreshadows, threads}."""
    base = Path(manuscript_dir) / "bible"
    out = {"characters": {}, "scenes": {}, "props": {}, "canon": {}, "foreshadows": {}, "threads": {}}
    files = {"角色.md": ("characters",), "场景.md": ("scenes",), "道具.md": ("props",),
             "世界观.md": ("canon",), "伏笔与线索.md": ("foreshadows", "threads")}
    for fname, keys in files.items():
        md = _read(base / fname)
        if md is None:
            continue
        block = first_json_block(md) or {}
        for k in keys:
            if isinstance(block.get(k), dict):
                out[k].update(block[k])
    return out


_SCRIPT_HEAD_RE = re.compile(r"^##\s*剧本\s*$", re.MULTILINE)
_SB_HEAD_RE = re.compile(r"^##\s*分镜表\s*$", re.MULTILINE)


def load_episode(manuscript_dir, ep: int) -> tuple[str | None, dict | None]:
    """剧本 = `## 剧本` 到 `## 分镜表`(或文末)之间的整段——**结构化剧本的 `## 第N场`
    场头属剧本正文,不当 section 切分点**(否则剧本被截到只剩集名首行)。分镜表 json
    只在 `## 分镜表` 之后的区段里找。"""
    md = _read(Path(manuscript_dir) / "episodes" / f"E{ep}.md")
    if md is None:
        return None, None
    sb_m = _SB_HEAD_RE.search(md)
    sc_m = _SCRIPT_HEAD_RE.search(md)
    if sc_m:
        s_end = sb_m.start() if sb_m else len(md)
        script = md[sc_m.end():s_end].strip() or None
    else:
        script = None
    sb = first_json_block(md[sb_m.start():] if sb_m else md)
    return script, sb
