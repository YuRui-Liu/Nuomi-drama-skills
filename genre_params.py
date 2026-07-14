"""题材特定参数加载器。

从 templates/genres/<genre_id>.yaml（vendored）或 manuscript/genres/<genre_id>.yaml（项目级）
加载题材的 style 覆盖/色调/基调/生成护栏。

Usage:
    from genre_params import load_genre_params
    params = load_genre_params("zombie-survival", manuscript_dir)
    # params 为 dict，缺字段返回 {}（无特定配置 = 默认行为）
"""
from __future__ import annotations

from pathlib import Path

# Vendored genre templates directory (relative to this file)
_VENDORED = Path(__file__).parent / "templates" / "genres"


def _parse_simple_yaml(text: str) -> dict:
    """极简 YAML 解析器 —— 只处理本模块需要的嵌套层级（2 级）。
    不做完整 YAML 解析，避免依赖 PyYAML。
    """
    result: dict = {}
    current_section: str | None = None
    section: dict = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # 顶级键（无缩进）：结束上一 section
        if not line.startswith(" ") and not line.startswith("\t"):
            if ":" in stripped and not stripped.startswith("-"):
                if current_section is not None and section:
                    result[current_section] = section
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if val:
                    result[key] = val
                    current_section = None
                    section = {}
                else:
                    current_section = key
                    section = {}
        # 二级缩进键（2 空格或 4 空格）
        elif current_section is not None and ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val:
                section[key] = val
        # 列表项
        elif stripped.startswith("- ") and current_section is not None:
            item = stripped[2:].strip().strip('"').strip("'")
            key = list(section.keys())[-1] if section else None
            if key:
                existing = section.get(key, [])
                if isinstance(existing, list):
                    existing.append(item)
                    section[key] = existing
                else:
                    section[key] = [item]
    if current_section is not None and section:
        result[current_section] = section
    return result


def _load_yaml_genre(path: Path) -> dict:
    """加载单个题材 YAML 文件，提取 v3 新增字段。"""
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    raw = _parse_simple_yaml(text)
    params: dict = {}
    for section in ("style_defaults", "tone_defaults", "generation_guardrails"):
        val = raw.get(section)
        if isinstance(val, dict):
            params[section] = val
    return params


def load_genre_params(genre_id: str, manuscript_dir: Path | None = None) -> dict:
    """加载题材特定参数。

    查找顺序（先到先用）：
      1) manuscript/genres/<genre_id>.yaml（项目级自定义）
      2) templates/genres/<genre_id>.yaml（vendored 内置）
      3) 返回 {}

    Returns:
        dict with optional keys: style_defaults, tone_defaults, generation_guardrails.
        每个 key 为 dict 或 absent。
    """
    gid = str(genre_id or "").strip()
    if not gid:
        return {}

    # 1) 项目级
    if manuscript_dir is not None:
        proj = Path(manuscript_dir) / "genres" / f"{gid}.yaml"
        if proj.is_file():
            return _load_yaml_genre(proj)

    # 2) vendored
    vendored = _VENDORED / f"{gid}.yaml"
    if vendored.is_file():
        return _load_yaml_genre(vendored)

    return {}
