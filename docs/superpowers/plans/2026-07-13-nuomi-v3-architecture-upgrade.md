# nuomi-drama-skills v3 架构升级实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 nuomi-drama-skills 从工具箱模式升级为操作系统模式——门控链、状态机、题材参数、Provider 容灾、导演引擎、剪映集成、提示词规则配置化。

**Architecture:** 7 个新/改文件，全平行实现。每个组件有清晰的单一职责：`writing_state.py` 管状态持久化，`gates.py` 管门控校验，`genre_params.py` 管题材配置加载，`provider_chain.py` 管降级容灾，`director.py` 管生成评估，`prompt_rules.json` 管规则配置。所有新组件是包装层/配置层，不修改现有核心逻辑。

**Tech Stack:** Python 3.9+ stdlib + json + dataclasses；现有依赖 httpx/Pillow 保持不变。

**Spec:** `docs/superpowers/specs/2026-07-13-nuomi-v3-architecture-upgrade.md`

---

## 文件清单

| 文件 | 操作 | 职责 |
|------|------|------|
| `writing_state.py` | 新建 | 状态机读写 API |
| `gates.py` | 新建 | 8 个 Gate 纯函数 + GateResult dataclass |
| `genre_params.py` | 新建 | 题材特定参数加载 |
| `provider_chain.py` | 新建 | 按角色 Provider 降级链 |
| `director.py` | 新建 | 导演引擎 5 判决协议 |
| `prompt_rules.json` | 新建 | 提示词规则 JSON 配置 |
| `prompt_checker.py` | 修改 | 从 JSON 加载规则，抽取通用引擎 |
| `export.py` | 修改 | 增加 `--jianying` 标志 |
| `skill.env.example` | 修改 | 增加 ANCHOR/SHOT fallback 字段 |
| `SKILL.md` | 修改 | 增加门控矩阵表 |
| `templates/genres/zombie-survival.yaml` | 修改 | 示例题材参数扩展字段 |

---

### Task 1: writing_state.py 状态机

**Files:**
- Create: `E:\Tools\Hermes\skills\nuomi-drama-skills\writing_state.py`

- [ ] **Step 1: 创建 writing_state.py**

```python
"""Manuscript writing state machine — lightweight persistence for session recovery.

Stores phase-level progress. Shot-level state is determined by filesystem
product inspection (via stages/status.py), never written here.

Usage:
    from writing_state import load_state, save_state, advance_phase, mark_gate

    state = load_state(manuscript_dir)
    state = advance_phase(manuscript_dir, "outline")
    state = mark_gate(manuscript_dir, "triplet", True, warnings=[])
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_STATE_FILE = "writing_state.json"

VALID_PHASES = [
    "ideation",      # 立意 / 三轴
    "outline",       # 大纲
    "bible",         # 角色 + 场景 + 道具 + 世界观 + 伏笔
    "beats",         # 分卷节拍表
    "scripting",     # 逐集剧本
    "storyboard",    # 逐集分镜表
    "generating",    # 出图/出视频/配音
    "done",          # 全部完成
]


def _default_state() -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "phase": "ideation",
        "completed_episodes": [],
        "current_episode": 1,
        "current_arc": 1,
        "gates_passed": [],
        "gates_warnings": {},
        "created_at": now,
        "last_updated": now,
    }


def _state_path(manuscript_dir: Path) -> Path:
    return Path(manuscript_dir) / _STATE_FILE


def load_state(manuscript_dir: Path) -> dict[str, Any]:
    """读取状态文件，不存在时返回默认初始状态。"""
    path = _state_path(manuscript_dir)
    if not path.is_file():
        return _default_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default_state()
    # 向后兼容：补齐新增字段的默认值
    defaults = _default_state()
    for k, v in defaults.items():
        data.setdefault(k, v)
    return data


def save_state(manuscript_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    """持久化状态到 manuscript 目录。"""
    state["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path = _state_path(manuscript_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def advance_phase(manuscript_dir: Path, new_phase: str) -> dict[str, Any]:
    """推进到新阶段。非法 phase 值抛出 ValueError。"""
    if new_phase not in VALID_PHASES:
        raise ValueError(f"非法阶段: {new_phase!r}，合法值: {VALID_PHASES}")
    state = load_state(manuscript_dir)
    state["phase"] = new_phase
    return save_state(manuscript_dir, state)


def mark_gate(manuscript_dir: Path, gate_name: str, passed: bool,
              warnings: list[str] | None = None) -> dict[str, Any]:
    """记录 gate 结果。passed gate 记入 gates_passed + 覆盖同名旧结果。
    warnings 写入 gates_warnings（passed=False 时清空同名旧 warnings）。
    """
    state = load_state(manuscript_dir)
    gated = state.setdefault("gates_passed", [])
    gated_warnings = state.setdefault("gates_warnings", {})
    if passed:
        if gate_name not in gated:
            gated.append(gate_name)
        if warnings:
            gated_warnings[gate_name] = warnings
        elif gate_name in gated_warnings:
            del gated_warnings[gate_name]
    else:
        if gate_name in gated:
            gated.remove(gate_name)
        gated_warnings[gate_name] = warnings or []
    return save_state(manuscript_dir, state)


def mark_episode_complete(manuscript_dir: Path, ep: int) -> dict[str, Any]:
    """标记某集完成（剧本+分镜均已写入）。"""
    state = load_state(manuscript_dir)
    completed = state.setdefault("completed_episodes", [])
    if ep not in completed:
        completed.append(ep)
        completed.sort()
    return save_state(manuscript_dir, state)


def set_current_episode(manuscript_dir: Path, ep: int) -> dict[str, Any]:
    state = load_state(manuscript_dir)
    state["current_episode"] = ep
    return save_state(manuscript_dir, state)


def set_current_arc(manuscript_dir: Path, arc: int) -> dict[str, Any]:
    state = load_state(manuscript_dir)
    state["current_arc"] = arc
    return save_state(manuscript_dir, state)
```

- [ ] **Step 2: 验证导入**

```bash
cd E:\Tools\Hermes\skills\nuomi-drama-skills && python -c "
from writing_state import load_state, save_state, advance_phase, mark_gate, mark_episode_complete, VALID_PHASES
print('VALID_PHASES:', VALID_PHASES)
print('All imports OK')
"
```

- [ ] **Step 3: 功能验证**

```bash
cd E:\Tools\Hermes\skills\nuomi-drama-skills && python -c "
import tempfile, os
from pathlib import Path
from writing_state import load_state, save_state, advance_phase, mark_gate, mark_episode_complete

with tempfile.TemporaryDirectory() as td:
    d = Path(td)
    # 默认状态
    s = load_state(d)
    assert s['phase'] == 'ideation'
    assert s['completed_episodes'] == []
    assert s['current_episode'] == 1

    # 推进阶段
    s = advance_phase(d, 'outline')
    assert s['phase'] == 'outline'

    # gate 标记
    s = mark_gate(d, 'triplet', True, warnings=['基调缺 arc'])
    assert 'triplet' in s['gates_passed']
    assert 'triplet' in s['gates_warnings']

    # gate 失败
    s = mark_gate(d, 'outline', False, warnings=['缺 series_logline'])
    assert 'outline' not in s['gates_passed']

    # 集完成
    s = mark_episode_complete(d, 3)
    assert 3 in s['completed_episodes']

    # 持久化
    assert (d / 'writing_state.json').exists()

    # 重新加载
    s2 = load_state(d)
    assert s2['phase'] == 'outline'
    assert 3 in s2['completed_episodes']

    # 非法 phase
    try:
        advance_phase(d, 'invalid_phase')
        assert False, 'should have raised'
    except ValueError:
        pass

    print('All assertions passed')
"
```

- [ ] **Step 4: Commit**

```bash
cd E:\Tools\Hermes\skills\nuomi-drama-skills && git add writing_state.py && git commit -m "feat: writing_state.json 状态机 —— 阶段+集级持久化

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: gates.py 门控纯函数

**Files:**
- Create: `E:\Tools\Hermes\skills\nuomi-drama-skills\gates.py`

- [ ] **Step 1: 创建 gates.py**

```python
"""Gate functions — pure validators returning GateResult.

G1-G4 (创作阶段) → hard_block=False (软提醒)
G5-G8 (生成阶段) → hard_block=True  (硬阻断)

Each gate is a pure function: input paths/config → GateResult.
Reuses existing validators.py / prompt_checker.py where possible.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GateResult:
    gate_name: str
    passed: bool
    hard_block: bool                    # True=阻断, False=软提醒
    errors: list[str] = field(default_factory=list)     # 阻断级 / 硬错误
    warnings: list[str] = field(default_factory=list)   # 提醒级 / 软问题


# ── G1: 三轴一致性 (SOFT) ──────────────────────────────────────────
def gate_triplet(manuscript_dir: Path) -> GateResult:
    """校验 genre_id / style_id / 基调四维 + arc。复用 validators.validate_triplet。"""
    import manuscript_parse as mp
    import validators
    _, triplet, _, _ = mp.load_idea(manuscript_dir)
    issues = validators.validate_triplet(triplet, manuscript_dir)
    return GateResult(
        gate_name="triplet",
        passed=len(issues) == 0,
        hard_block=False,
        warnings=issues,
    )


# ── G2: 大纲完整性 (SOFT) ──────────────────────────────────────────
def gate_outline(manuscript_dir: Path) -> GateResult:
    import manuscript_parse as mp
    import validators
    _, _, _, count = mp.load_idea(manuscript_dir)
    outline = mp.load_outline(manuscript_dir)
    if outline is None:
        return GateResult(
            gate_name="outline",
            passed=False,
            hard_block=False,
            warnings=["大纲未写（01_大纲.md 不存在或无 JSON 块）"],
        )
    if count <= 0:
        return GateResult(
            gate_name="outline",
            passed=False,
            hard_block=False,
            warnings=["00_立意.md 缺 episode_count（必须 ≥1）"],
        )
    issues = validators.validate_outline(outline, count)
    return GateResult(
        gate_name="outline",
        passed=len(issues) == 0,
        hard_block=False,
        warnings=issues,
    )


# ── G3: 圣经非空检查 (SOFT) ───────────────────────────────────────
def gate_bible(manuscript_dir: Path) -> GateResult:
    import manuscript_parse as mp
    bible = mp.load_bible(manuscript_dir)
    errors: list[str] = []
    warnings: list[str] = []
    for key, label in [("characters", "角色"), ("scenes", "场景"),
                        ("props", "道具"), ("canon", "世界观"),
                        ("foreshadows", "伏笔")]:
        if not bible.get(key):
            warnings.append(f"圣经缺 {label} 表（bible/{label}.md 为空或不存在）")
    return GateResult(
        gate_name="bible",
        passed=len(warnings) == 0,
        hard_block=False,
        warnings=warnings,
    )


# ── G4: 节拍表校验 (SOFT) ─────────────────────────────────────────
def gate_beats(manuscript_dir: Path) -> GateResult:
    import manuscript_parse as mp
    import validators
    arcs = mp.load_arcs(manuscript_dir)
    issues = validators.validate_beats(arcs)
    return GateResult(
        gate_name="beats",
        passed=len(issues) == 0,
        hard_block=False,
        warnings=issues,
    )


# ── G5: 分镜表规范 (HARD) ─────────────────────────────────────────
def gate_storyboard(ep_path: Path) -> GateResult:
    import manuscript_parse as mp
    import validators
    md = ep_path.read_text(encoding="utf-8") if ep_path.is_file() else None
    if md is None:
        return GateResult(
            gate_name="storyboard",
            passed=False,
            hard_block=True,
            errors=[f"{ep_path.name} 不存在"],
        )
    sb = mp.first_json_block(md)
    if sb is None:
        return GateResult(
            gate_name="storyboard",
            passed=False,
            hard_block=True,
            errors=[f"{ep_path.name} 无分镜表 JSON 块"],
        )
    issues = validators.validate_storyboard(sb)
    return GateResult(
        gate_name="storyboard",
        passed=len(issues) == 0,
        hard_block=True,
        errors=issues,
    )


# ── G6: 提示词质量 (HARD) ─────────────────────────────────────────
def gate_prompts(ep_path: Path) -> GateResult:
    import manuscript_parse as mp
    import prompt_checker
    md = ep_path.read_text(encoding="utf-8") if ep_path.is_file() else None
    if md is None:
        return GateResult(
            gate_name="prompts",
            passed=False,
            hard_block=True,
            errors=[f"{ep_path.name} 不存在"],
        )
    sb = mp.first_json_block(md)
    if sb is None:
        return GateResult(
            gate_name="prompts",
            passed=False,
            hard_block=True,
            errors=[f"{ep_path.name} 无分镜表 JSON 块"],
        )
    errors: list[str] = []
    warnings: list[str] = []
    shots = sb.get("shots") or []
    for s in shots:
        if not isinstance(s, dict):
            continue
        shot_id = s.get("shot_id", "?")
        char_count = len(s.get("characters") or [])
        vp_zh = str(s.get("video_prompt") or "").strip()
        vp_en = str(s.get("video_prompt_en") or "").strip()

        if vp_zh:
            w_zh, e_zh = prompt_checker.check_video_prompt(
                vp_zh, lang="zh", character_count=char_count)
            for w in w_zh:
                warnings.append(f"[{shot_id}] video_prompt(zh): {w.message}")
            for e in e_zh:
                errors.append(f"[{shot_id}] video_prompt(zh): {e.message}")

        if vp_en:
            w_en, e_en = prompt_checker.check_video_prompt(
                vp_en, lang="en", character_count=char_count)
            for w in w_en:
                warnings.append(f"[{shot_id}] video_prompt_en: {w.message}")
            for e in e_en:
                errors.append(f"[{shot_id}] video_prompt_en: {e.message}")

        if not vp_zh and not vp_en:
            warnings.append(f"[{shot_id}] 缺 video_prompt 和 video_prompt_en（将回退 action_desc）")

    return GateResult(
        gate_name="prompts",
        passed=len(errors) == 0,
        hard_block=True,
        errors=errors,
        warnings=warnings,
    )


# ── G7: 首帧完整性 (HARD) ─────────────────────────────────────────
def gate_first_frames(out_dir: Path, ep: int) -> GateResult:
    ctx_path = out_dir / f"E{ep}" / "gen_context.json"
    errors: list[str] = []
    if not ctx_path.exists():
        return GateResult(
            gate_name="first_frames",
            passed=False,
            hard_block=True,
            errors=[f"E{ep}/gen_context.json 不存在，请先 export"],
        )
    ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
    shots = (ctx.get("storyboard") or {}).get("shots") or []
    shots_dir = out_dir / f"E{ep}" / "shots_assets"
    missing = []
    for s in shots:
        sid = str(s.get("shot_id", ""))
        if not (shots_dir / f"{sid}.jpg").exists():
            missing.append(sid)
    if missing:
        errors.append(f"E{ep}: {len(missing)} 镜缺首帧 ({', '.join(missing)})")
    return GateResult(
        gate_name="first_frames",
        passed=len(errors) == 0,
        hard_block=True,
        errors=errors,
    )


# ── G8: Provider 健康 (HARD) ──────────────────────────────────────
def gate_provider_health(cfg: dict) -> GateResult:
    """检查 provider 配置完整性。不实际 ping（避免副作用），只查必填字段。
    实际连通性由 provider_chain.health_check 负责。
    """
    errors: list[str] = []
    img = cfg.get("image_provider", "")
    if img not in ("grsai", "comfyui", "runninghub", "gemini"):
        errors.append(f"未知 IMAGE_PROVIDER: {img!r}")

    if img == "grsai" and not cfg.get("grsai", {}).get("api_key"):
        errors.append("Grsai: GRSAI_API_KEY 未配置")
    if img == "gemini" and not cfg.get("gemini", {}).get("api_key"):
        errors.append("Gemini: GEMINI_API_KEY 未配置")
    if img == "comfyui" and not cfg.get("comfyui", {}).get("base_url"):
        errors.append("ComfyUI: COMFYUI_BASE_URL 未配置")

    rh = cfg.get("runninghub", {})
    if not rh.get("api_key"):
        errors.append("RunningHub: RUNNINGHUB_API_KEY 未配置（出视频/配音需要）")
    if not rh.get("video_workflow_id"):
        errors.append("RunningHub: RUNNINGHUB_VIDEO_WORKFLOW_ID 未配置")
    if not rh.get("dub_workflow_id"):
        errors.append("RunningHub: RUNNINGHUB_DUB_WORKFLOW_ID 未配置")

    return GateResult(
        gate_name="provider_health",
        passed=len(errors) == 0,
        hard_block=True,
        errors=errors,
    )


# ── 批量运行 ─────────────────────────────────────────────────────
def run_all_gates(manuscript_dir: Path, out_dir: Path,
                  stage: str = "all") -> list[GateResult]:
    """按 stage 选择执行哪些 gate。
    stage="scripting"  → G1-G4 (soft)
    stage="generating" → G5-G8 (hard)
    stage="all"        → G1-G8
    """
    results: list[GateResult] = []
    if stage in ("scripting", "all"):
        results.extend([
            gate_triplet(manuscript_dir),
            gate_outline(manuscript_dir),
            gate_bible(manuscript_dir),
            gate_beats(manuscript_dir),
        ])
    if stage in ("generating", "all"):
        # G5-G6: per-episode gates — iterate written episodes
        ep_dir = manuscript_dir / "episodes"
        for ep_md in sorted(ep_dir.glob("E*.md")) if ep_dir.is_dir() else []:
            results.append(gate_storyboard(ep_md))
            results.append(gate_prompts(ep_md))
            # G7
            try:
                ep_num = int(ep_md.stem.lstrip("E"))
            except ValueError:
                continue
            results.append(gate_first_frames(out_dir, ep_num))
        # G8
        from providers import load_config
        results.append(gate_provider_health(load_config()))
    return results
```

- [ ] **Step 2: 验证导入和基础功能**

```bash
cd E:\Tools\Hermes\skills\nuomi-drama-skills && python -c "
from gates import GateResult, gate_triplet, gate_outline, gate_bible, gate_beats, gate_provider_health
from pathlib import Path

# G3: empty bible
import tempfile
with tempfile.TemporaryDirectory() as td:
    d = Path(td)
    r = gate_bible(d)
    assert not r.passed
    assert r.hard_block == False
    print(f'G3 warnings: {r.warnings}')

# G8: provider health
from providers import load_config
r = gate_provider_health(load_config())
print(f'G8 passed={r.passed}, errors={r.errors}')

print('All gate tests passed')
"
```

- [ ] **Step 3: Commit**

```bash
cd E:\Tools\Hermes\skills\nuomi-drama-skills && git add gates.py && git commit -m "feat: gates.py 8 个门控纯函数（G1-G8）

G1-G4 创作阶段软提醒，G5-G8 生成阶段硬阻断。复用 validators.py/prompt_checker.py 已有逻辑，GateResult 统一返回类型。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: genre_params.py 题材特定参数

**Files:**
- Create: `E:\Tools\Hermes\skills\nuomi-drama-skills\genre_params.py`
- Modify: `E:\Tools\Hermes\skills\nuomi-drama-skills\templates\genres\zombie-survival.yaml`

- [ ] **Step 1: 扩展 zombie-survival.yaml 新字段**

Read the existing file first, then append after `recommended_episodes` line:

```yaml
# 以下为 v3 新增字段（可选，缺则用默认值）
style_defaults:
  style_id_override: "real/cinematic-cool-v1"
  color_bias: "desaturated cold, teal shadows, muted skin tones, bleach bypass grade"
  negative_extra: "no vibrant colors, no warm sunlight, no clean polished environments, no cheerful atmosphere"

tone_defaults:
  情感温度: "冷峻"
  动作密度: "强动作"
  叙事节奏: "高频反转"

generation_guardrails:
  max_characters_per_shot: 3
  preferred_shot_types: ["近景", "特写", "中景"]
  avoid_shot_types: []
```

- [ ] **Step 2: 创建 genre_params.py**

```python
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
            # 简单值
            if val:
                section[key] = val
            # 列表（下一行开始 - 项）
            else:
                pass  # 列表在下一轮解析（见下方）
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
```

- [ ] **Step 3: 验证测试**

```bash
cd E:\Tools\Hermes\skills\nuomi-drama-skills && python -c "
from genre_params import load_genre_params, _parse_simple_yaml, _load_yaml_genre
from pathlib import Path

# 内置题材
params = load_genre_params('zombie-survival')
assert 'style_defaults' in params, f'Expected style_defaults, got {params.keys()}'
sd = params['style_defaults']
assert sd.get('style_id_override') == 'real/cinematic-cool-v1'
assert 'desaturated' in sd.get('color_bias', '')
assert 'no vibrant colors' in sd.get('negative_extra', '')

# 未知题材
params2 = load_genre_params('nonexistent-genre-xyz')
assert params2 == {}

# 解析器基础测试
yaml_text = '''
style_defaults:
  color_bias: \"cool tones\"
  negative_extra: \"no warm light\"
tone_defaults:
  情感温度: \"冷峻\"
generation_guardrails:
  max_characters_per_shot: 3
  preferred_shot_types:
    - \"近景\"
    - \"特写\"
'''
parsed = _parse_simple_yaml(yaml_text)
assert 'style_defaults' in parsed
assert parsed['style_defaults']['color_bias'] == 'cool tones'

print('All genre_params tests passed')
"
```

- [ ] **Step 4: Commit**

```bash
cd E:\Tools\Hermes\skills\nuomi-drama-skills && git add genre_params.py templates/genres/zombie-survival.yaml && git commit -m "feat: genre_params.py 题材特定参数加载器 + zombie-survival 示例扩展

新增 style_defaults/tone_defaults/generation_guardrails 三组可选字段。
极简 YAML 解析器无外部依赖。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: provider_chain.py Provider 容灾降级链

**Files:**
- Create: `E:\Tools\Hermes\skills\nuomi-drama-skills\provider_chain.py`
- Modify: `E:\Tools\Hermes\skills\nuomi-drama-skills\skill.env.example`

- [ ] **Step 1: 创建 provider_chain.py**

```python
"""Provider chain — role-based fallback for image generation.

- Anchors (characters/scenes/props): primary → fallback silently
- Shots (storyboard frames): primary → fallback with ⚠️ log marker
- Video / Dub: single provider only (RunningHub), no fallback

Usage:
    from provider_chain import ProviderChain, health_check

    chain = ProviderChain(cfg)
    img = chain.generate_anchor("a warrior in armor")
    img = chain.generate_shot("close-up of a hand reaching for a door")
    vid = chain.generate_video("camera pans left", "s1.jpg", 4.0)
    aud = chain.generate_dub("你好", "沈云晚", "悲伤", "温柔女声")
"""
from __future__ import annotations

from typing import Any


class ProviderChain:
    def __init__(self, cfg: dict[str, Any]) -> None:
        self._cfg = cfg
        self._anchor_primary = self._make_image_provider("anchor", "primary")
        self._anchor_fallback = self._make_image_provider("anchor", "fallback")
        self._shot_primary = self._make_image_provider("shot", "primary")
        self._shot_fallback = self._make_image_provider("shot", "fallback")
        self._video_provider = self._make_video_provider()
        self._dub_provider = self._make_dub_provider()
        self._fallback_log: list[dict] = []   # 记录降级事件

    # ── 工厂方法 ──────────────────────────────────────────────────
    def _make_image_provider(self, role: str, tier: str):
        """创建图片 provider。role=anchor|shot, tier=primary|fallback。"""
        key = f"IMAGE_PROVIDER_{role.upper()}"
        fallback_key = f"{key}_FALLBACK"
        from providers import load_config as _lc
        c = _lc()
        # 支持按角色分离配置（如果 env 里设了的话）
        env_img = c.get("image_provider", "grsai")
        if role == "anchor":
            name = c.get("image_provider_anchor", env_img)
            fallback_name = c.get("image_provider_anchor_fallback",
                                  c.get("image_provider_shot_fallback", "gemini"))
        else:
            name = c.get("image_provider_shot", env_img)
            fallback_name = c.get("image_provider_shot_fallback",
                                  c.get("image_provider_anchor_fallback", "gemini"))
        chosen = name if tier == "primary" else fallback_name
        if not chosen or chosen == name:
            return None

        # 为 chosen provider 构造配置
        if chosen == "grsai":
            from providers.grsai import GrsaiProvider
            return GrsaiProvider(c.get("grsai", {}))
        if chosen == "gemini":
            from providers.gemini import GeminiImageProvider
            return GeminiImageProvider(c.get("gemini", {}))
        if chosen == "comfyui":
            from providers.comfyui import ComfyUIProvider
            return ComfyUIProvider(c.get("comfyui", {}))
        if chosen == "runninghub":
            from providers.runninghub import RunningHubProvider
            return RunningHubProvider(c.get("runninghub", {}))
        return None

    def _make_video_provider(self):
        from providers import get_video_provider
        return get_video_provider()

    def _make_dub_provider(self):
        from providers import get_dub_provider
        return get_dub_provider()

    # ── Fallback 日志 ─────────────────────────────────────────────
    def get_fallback_events(self) -> list[dict]:
        return list(self._fallback_log)

    # ── 锚图生成（可降级） ──────────────────────────────────────────
    def generate_anchor(self, prompt: str) -> bytes:
        if self._anchor_primary is not None:
            try:
                return self._anchor_primary.generate_image(prompt)
            except Exception as e:
                if self._anchor_fallback is not None:
                    self._fallback_log.append({
                        "role": "anchor", "action": "fallback",
                        "primary_error": str(e)[:200],
                    })
                    return self._anchor_fallback.generate_image(prompt)
                raise
        if self._anchor_fallback is not None:
            self._fallback_log.append({
                "role": "anchor", "action": "direct_fallback",
            })
            return self._anchor_fallback.generate_image(prompt)
        raise RuntimeError("锚图生成: 无可用 provider（请配置 IMAGE_PROVIDER_ANCHOR）")

    # ── 分镜首帧生成（降级打 ⚠️ 标记） ──────────────────────────────
    def generate_shot(self, prompt: str, size=None) -> bytes:
        if self._shot_primary is not None:
            try:
                return self._shot_primary.generate_image(prompt, size=size)
            except Exception as e:
                if self._shot_fallback is not None:
                    self._fallback_log.append({
                        "role": "shot", "action": "fallback",
                        "warning": "分镜首帧降级为 fallback provider，风格可能不一致",
                        "primary_error": str(e)[:200],
                    })
                    return self._shot_fallback.generate_image(prompt, size=size)
                raise
        if self._shot_fallback is not None:
            self._fallback_log.append({
                "role": "shot", "action": "direct_fallback",
                "warning": "分镜首帧使用 fallback provider（无主 provider 配置）",
            })
            return self._shot_fallback.generate_image(prompt, size=size)
        raise RuntimeError("分镜生成: 无可用 provider（请配置 IMAGE_PROVIDER_SHOT）")

    # ── 视频生成（无降级） ────────────────────────────────────────
    def generate_video(self, prompt: str, first_frame_path: str,
                       duration: float) -> bytes:
        if self._video_provider is None:
            raise RuntimeError("视频生成: 无可用 provider（仅 RunningHub 支持）")
        return self._video_provider.generate_video(prompt, first_frame_path, duration)

    def generate_video_group(self, global_prompt: str, segments: list[dict],
                             motion_segments: list[str] | None = None) -> bytes:
        if self._video_provider is None:
            raise RuntimeError("视频分组生成: 无可用 provider")
        return self._video_provider.generate_video_group(
            global_prompt, segments, motion_segments)

    # ── 配音生成（无降级） ────────────────────────────────────────
    def generate_dub(self, text: str, speaker: str, emotion: str,
                     voice_style: str = "") -> bytes:
        if self._dub_provider is None:
            raise RuntimeError("配音: 无可用 provider（仅 RunningHub 支持）")
        return self._dub_provider.generate_dub(text, speaker, emotion, voice_style)

    def design_voice(self, name: str, style: str, language: str,
                     out_dir: str) -> str:
        if self._dub_provider is None:
            raise RuntimeError("音色设计: 无可用 provider")
        return self._dub_provider.design_voice(name, style, language, out_dir)

    def clone_voice(self, text: str, speaker_ref: str, emotion: str) -> bytes:
        if self._dub_provider is None:
            raise RuntimeError("声音克隆: 无可用 provider")
        return self._dub_provider.clone_voice(text, speaker_ref, emotion)


def health_check(cfg: dict) -> dict[str, bool]:
    """预检各 provider 配置完整性（不做网络 ping，避免超时阻塞）。
    返回 {provider_name: is_healthy}。
    """
    results: dict[str, bool] = {}
    img = cfg.get("image_provider", "")
    for name in ("grsai", "gemini", "comfyui", "runninghub"):
        section = cfg.get(name, {})
        if name == img or name in ("grsai", "gemini", "comfyui", "runninghub"):
            results[name] = bool(section.get("api_key") or section.get("base_url"))
    results["runninghub_video"] = bool(
        cfg.get("runninghub", {}).get("api_key")
        and cfg.get("runninghub", {}).get("video_workflow_id"))
    results["runninghub_dub"] = bool(
        cfg.get("runninghub", {}).get("api_key")
        and cfg.get("runninghub", {}).get("dub_workflow_id"))
    return results
```

- [ ] **Step 2: 更新 skill.env.example**

在 `RUNNINGHUB_MAX_PARALLEL=3` 之后追加：

```bash
# ── Provider 容灾（按角色分离，可选） ──────────────────────────
# 锚图（角色/场景/道具）和分镜首帧可分别指定主/备 provider
# 留空则沿用 IMAGE_PROVIDER 的值
IMAGE_PROVIDER_ANCHOR=
IMAGE_PROVIDER_ANCHOR_FALLBACK=gemini
IMAGE_PROVIDER_SHOT=
IMAGE_PROVIDER_SHOT_FALLBACK=gemini
```

- [ ] **Step 3: 验证导入**

```bash
cd E:\Tools\Hermes\skills\nuomi-drama-skills && python -c "
from provider_chain import ProviderChain, health_check
from providers import load_config
cfg = load_config()
h = health_check(cfg)
print('Health check:', h)
print('ProviderChain imported OK')
"
```

- [ ] **Step 4: Commit**

```bash
cd E:\Tools\Hermes\skills\nuomi-drama-skills && git add provider_chain.py skill.env.example && git commit -m "feat: provider_chain.py 按角色 Provider 降级容灾

锚图自动降级，分镜降级打标记，视频/配音无降级直接报错。
health_check 预检配置完整性。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: director.py 导演引擎

**Files:**
- Create: `E:\Tools\Hermes\skills\nuomi-drama-skills\director.py`

- [ ] **Step 1: 创建 director.py**

```python
"""导演引擎 —— 生成结果的拍摄评估协议。

借鉴 seedance-2.0 的 5 判决 + 单变量规则 + 尝试预算。
只适用于生成阶段（出图/出视频），不替代创作阶段的批判环。

Usage:
    from director import ShootProtocol, Verdict

    protocol = ShootProtocol(max_attempts=5)
    result = protocol.evaluate(shot_id, image_path, expected_desc)
    if result.verdict == Verdict.RETRY:
        protocol.retry(shot_id, new_seed=True)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    KEEP = "keep"           # 直接使用
    FIX = "fix"             # 后期修（不在生成侧改动）
    EDIT = "edit"           # 同 prompt 不同 seed 重生成
    REGEN = "regen"         # 修改 prompt 重生成
    REWRITE = "rewrite"     # 回创作侧改 action_desc/video_prompt


@dataclass
class ShotVerdict:
    shot_id: str
    verdict: Verdict
    reason: str = ""
    suggestion: str = ""     # 修复建议（RETRY/REWRITE 时提供）


@dataclass
class ShootProtocol:
    """拍摄协议：管理每个镜头的尝试预算和重拍历史。

    max_attempts: 每镜最大尝试次数（默认 5）
    """
    max_attempts: int = 5
    _history: dict[str, list[dict]] = field(default_factory=dict)
    _budget: dict[str, int] = field(default_factory=dict)

    def remaining(self, shot_id: str) -> int:
        """返回该镜剩余可用尝试次数。"""
        used = self._budget.get(shot_id, 0)
        return max(0, self.max_attempts - used)

    def can_retry(self, shot_id: str) -> bool:
        return self.remaining(shot_id) > 0

    def record_attempt(self, shot_id: str, verdict: Verdict,
                       change: str = "", note: str = ""):
        """记录一次尝试。"""
        self._budget[shot_id] = self._budget.get(shot_id, 0) + 1
        entry = {
            "attempt": self._budget[shot_id],
            "verdict": verdict.value,
            "change": change,
            "note": note,
        }
        self._history.setdefault(shot_id, []).append(entry)

    def analyze_failures(self, shot_id: str) -> str | None:
        """分析该镜历史尝试，给出建议。连续 2 次 REGEN → 建议 REWRITE。"""
        entries = self._history.get(shot_id, [])
        if len(entries) >= 2:
            last_two = entries[-2:]
            if all(e["verdict"] in (Verdict.REGEN.value, Verdict.EDIT.value)
                   for e in last_two):
                return (
                    f"连续 {len(last_two)} 次重生成未解决问题，"
                    f"建议回创作侧修改 action_desc 或 video_prompt（REWRITE）"
                )
        if self.remaining(shot_id) <= 1:
            return "最后一次尝试，建议改变策略（尝试不同 seed 或修改 prompt 关键句）"
        return None

    # ── 判决辅助逻辑（供 Agent 参考，非自动判定） ──────────────────
    @staticmethod
    def suggest_verdict(issues: list[str]) -> ShotVerdict:
        """根据问题列表给出初步判决建议。
        这是 Agent 的参考框架，最终判决由人工/AI Agent 做出。
        """
        if not issues:
            return ShotVerdict(shot_id="?", verdict=Verdict.KEEP,
                               reason="无问题")
        critical = [i for i in issues if any(
            kw in i for kw in ("角色", "身份", "人脸", "character", "face", "identity"))]
        composition = [i for i in issues if any(
            kw in i for kw in ("构图", "composition", "景别", "角度", "crop"))]
        minor = [i for i in issues if any(
            kw in i for kw in ("色调", "color", "亮度", "brightness", "对比度", "contrast"))]

        if critical:
            return ShotVerdict(
                shot_id="?", verdict=Verdict.REGEN,
                reason=f"角色/身份问题: {', '.join(critical[:2])}",
                suggestion="检查角色 reference 是否已加载，修改 action_desc 的角色描述")
        if composition:
            return ShotVerdict(
                shot_id="?", verdict=Verdict.EDIT,
                reason=f"构图问题: {', '.join(composition[:2])}",
                suggestion="同 prompt 换 seed 重试，或微调景别/角度描述")
        if minor:
            return ShotVerdict(
                shot_id="?", verdict=Verdict.FIX,
                reason=f"后期可修: {', '.join(minor[:2])}",
                suggestion="后期调色/亮度修正即可")
        return ShotVerdict(
            shot_id="?", verdict=Verdict.KEEP,
            reason="问题不严重，可使用")
```

- [ ] **Step 2: 验证导入**

```bash
cd E:\Tools\Hermes\skills\nuomi-drama-skills && python -c "
from director import ShootProtocol, Verdict, ShotVerdict

# 基本流程
p = ShootProtocol(max_attempts=5)
assert p.can_retry('s1')
p.record_attempt('s1', Verdict.EDIT, change='new seed')
assert p.remaining('s1') == 4
p.record_attempt('s1', Verdict.REGEN, change='adjusted prompt')
advice = p.analyze_failures('s1')
assert advice is not None
print(f'Advice: {advice}')

# 预算耗尽
p2 = ShootProtocol(max_attempts=2)
p2.record_attempt('s2', Verdict.EDIT)
p2.record_attempt('s2', Verdict.EDIT)
assert not p2.can_retry('s2')

# 判决建议
sv = ShootProtocol.suggest_verdict(['角色手指变形', '构图偏左'])
assert sv.verdict == Verdict.REGEN, f'Expected REGEN for character issues, got {sv.verdict}'

sv2 = ShootProtocol.suggest_verdict(['色调偏暖'])
assert sv2.verdict == Verdict.FIX, f'Expected FIX for minor color issues, got {sv2.verdict}'

sv3 = ShootProtocol.suggest_verdict([])
assert sv3.verdict == Verdict.KEEP

print('All director tests passed')
"
```

- [ ] **Step 3: Commit**

```bash
cd E:\Tools\Hermes\skills\nuomi-drama-skills && git add director.py && git commit -m "feat: director.py 导演引擎 5 判决协议 + 尝试预算

借鉴 seedance-2.0: KEEP/FIX/EDIT/REGEN/REWRITE + 单变量规则 + 连续失败升级建议。
Agent 参考框架，非自动判定。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: 剪映导出集成

**Files:**
- Modify: `E:\Tools\Hermes\skills\nuomi-drama-skills\export.py`

- [ ] **Step 1: 修改 export.py 增加 --jianying 标志**

```python
# 在 main() 函数的 argparse 定义中，ap.add_argument("out_project_dir") 之后加：
ap.add_argument("--jianying", action="store_true",
                help="编译后同时导出剪映草稿 (jianying_draft.json)")

# 在 report["ok"] 分支的 print 语句之后、return 0 之前加：
if args.jianying:
    from exporters.jianying import export_jianying
    export_jianying(
        {"out_dir": str(Path(args.out_project_dir).resolve())},
        str(Path(args.out_project_dir).resolve()),
    )
    print("  · 剪映草稿已导出")
```

具体操作：

在 `export.py:93` 行 `ap.add_argument("out_project_dir")` 之后插入：
```python
    ap.add_argument("--jianying", action="store_true",
                    help="编译后同时导出剪映草稿 (jianying_draft.json)")
```

在 `export.py:99` 行（`if report.get("genres_copied"):` 之前）插入：
```python
        if args.jianying:
            from exporters.jianying import export_jianying
            # export_jianying 按集遍历 out_dir 下的 E{n}/gen_context.json
            export_jianying(
                {"episodes": [
                    {"episode_id": f"E{n}"}
                    for n in range(1, report.get("episodes", 0) + 1)
                ]},
                report["out_dir"],
            )
            print("  · 剪映草稿已导出")
```

- [ ] **Step 2: 验证 CLI**

```bash
cd E:\Tools\Hermes\skills\nuomi-drama-skills && python export.py --help | grep jianying
```

预期输出：包含 `--jianying` 选项。

- [ ] **Step 3: Commit**

```bash
cd E:\Tools\Hermes\skills\nuomi-drama-skills && git add export.py && git commit -m "feat: export.py 增加 --jianying 标志，编译后可选导出剪映草稿

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: prompt_rules.json 提示词规则配置化

**Files:**
- Create: `E:\Tools\Hermes\skills\nuomi-drama-skills\prompt_rules.json`
- Modify: `E:\Tools\Hermes\skills\nuomi-drama-skills\prompt_checker.py`

- [ ] **Step 1: 创建 prompt_rules.json**

```json
{
  "version": "ltx-2.3",
  "description": "LTX 2.3 video prompt validation rules. Swap this file for new LTX versions without code changes.",
  "hard_blocks": [
    {
      "rule": "no_abstract_emotion",
      "description": "Abstract emotion labels — LTX cannot interpret 'is sad'. Use physical cues instead.",
      "patterns_zh": [
        "很难过", "很伤心", "很生气", "很害怕", "很紧张",
        "很焦虑", "很兴奋", "很沮丧", "很绝望", "很愤怒",
        "很恐惧", "悲伤地", "愤怒地", "恐惧地", "痛苦地", "焦虑地"
      ],
      "patterns_en": [
        "\\b(is|feels|looks|seems|appears)\\s+(sad|angry|scared|nervous|anxious|excited|frustrated|desperate|furious|terrified|happy|confused|depressed)\\b"
      ],
      "message_zh": "抽象情绪标签，请用身体线索替代（如「肩膀下垂，眼睛盯着地面」而非「很难过」）",
      "message_en": "Abstract emotion label detected: use physical cues instead. e.g. 'shoulders slump, eyes fixed on floor' NOT 'looks sad'"
    },
    {
      "rule": "no_text_logo",
      "description": "Text/logo descriptions — LTX cannot reliably render on-screen text.",
      "patterns": [
        "\\b(text|logo|lettering|sign|billboard|subtitle|caption|headline|brand\\s*name|watermark|typography|words?\\s+on\\s+screen|written\\s+text|onscreen\\s+text)\\b"
      ],
      "message_zh": "文本/Logo 描述，LTX 无法可靠渲染屏幕文字。请移除所有屏幕文字的引用。",
      "message_en": "Text/logo description detected: LTX cannot reliably render text. Remove references to on-screen text, logos, signs, or written words."
    }
  ],
  "soft_warnings": [
    {
      "rule": "complex_physics_warning",
      "description": "Complex physics (shatter/explode/fragment) likely produce visible artifacts.",
      "patterns": [
        "\\b(shatters?|shattering|explodes?|exploding|fragments?|fragmenting|bursts?\\s+into\\s+pieces|disintegrate|disintegrates|pulverize|crumbles?\\s+into|breaks?\\s+apart\\s+into\\s+(tiny|small|many)\\s+pieces|splinters?|splintering)\\b"
      ],
      "message_zh": "复杂物理效果（破碎/爆炸/碎片）可能产生可见伪影",
      "message_en": "Complex physics described (shatter/explode/fragment): likely to produce visible artifacts in LTX output."
    },
    {
      "rule": "character_count_warning",
      "description": ">3 distinct characters may cause LTX quality degradation.",
      "message_zh": "角色数超过 3，LTX 可能难以处理多角色场景",
      "message_en": "Character count exceeds 3: LTX may struggle with many distinct characters."
    },
    {
      "rule": "prompt_length_warning",
      "description": "LTX works best with 4-8 well-structured sentences (English only).",
      "message_zh": "英文提示词句数不在 4-8 推荐区间内",
      "message_en": "Prompt sentence count outside 4-8 range: LTX works best with 4-8 well-structured sentences."
    },
    {
      "rule": "conflicting_light_warning",
      "description": "Front light + backlight in same shot produces unnatural results.",
      "patterns_front": [
        "\\b(front\\s*light|frontal\\s*light|front\\s*lighting|frontal\\s*lighting|key\\s*light|fill\\s*light)\\b"
      ],
      "patterns_back": [
        "\\b(back\\s*light|backlight|back\\s*lighting|rim\\s*light|silhouette\\s*light|silhouette\\s*lighting)\\b"
      ],
      "message_zh": "冲突光照：同时存在前光和逆光描述，可能产生不自然画面",
      "message_en": "Conflicting lighting: both front light and backlight described. This can produce unnatural-looking results."
    }
  ]
}
```

- [ ] **Step 2: 修改 prompt_checker.py 加载 JSON 规则**

在文件开头（`import re` 之后）增加规则加载逻辑，将硬编码正则替换为从 JSON 读取：

```python
"""LTX 2.3 prompt validation rules.

Validates video_prompt / video_prompt_en against LTX 2.3 video generation best
practices.  Hard blocks (LTXPromptError) prevent generation; soft warnings
(LTXPromptWarning) flag likely quality issues.

Rules are loaded from prompt_rules.json at import time.
Swap the JSON file for new LTX versions without code changes.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass
class LTXPromptError:
    """Hard block: the prompt will produce unusable LTX output."""
    message: str
    rule: str


@dataclass
class LTXPromptWarning:
    """Soft warning: the prompt may cause quality issues."""
    message: str
    rule: str


# ── Load rules from JSON ────────────────────────────────────────────────
_RULES_PATH = Path(__file__).parent / "prompt_rules.json"

def _load_rules() -> dict:
    if _RULES_PATH.is_file():
        try:
            return json.loads(_RULES_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"hard_blocks": [], "soft_warnings": [], "version": "unknown"}

_RULES = _load_rules()


def _compile_patterns(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p) for p in patterns]


# Pre-compile patterns at module load time
_HARD_BLOCK_PATTERNS: list[tuple[str, list[re.Pattern], list[re.Pattern], str, str]] = []
for _b in _RULES.get("hard_blocks", []):
    _p_zh = _compile_patterns(_b.get("patterns_zh", []))
    _p_en = _compile_patterns(_b.get("patterns_en", []))
    _p_all = _compile_patterns(_b.get("patterns", []))
    _HARD_BLOCK_PATTERNS.append((
        _b["rule"], _p_all, _p_zh, _p_en,
        _b.get("message_zh", _b.get("message_en", "")),
        _b.get("message_en", _b.get("message_zh", "")),
    ))

_SOFT_WARNING_PATTERNS: list[tuple[str, list[re.Pattern], str, str]] = []
for _w in _RULES.get("soft_warnings", []):
    _p_all = _compile_patterns(_w.get("patterns", []))
    _p_front = _compile_patterns(_w.get("patterns_front", []))
    _p_back = _compile_patterns(_w.get("patterns_back", []))
    _SOFT_WARNING_PATTERNS.append((
        _w["rule"], _p_all, _p_front, _p_back,
        _w.get("message_zh", _w.get("message_en", "")),
        _w.get("message_en", _w.get("message_zh", "")),
    ))


# ── Retained compiled patterns for performance-critical checks ──────────
_RE_SENTENCE = re.compile(r"[.!?]+(?:\s+|$)")


# ── Public API ─────────────────────────────────────────────────────────

def check_video_prompt(
    prompt: str,
    lang: str = "en",
    character_count: int = 0,
) -> Tuple[List[LTXPromptWarning], List[LTXPromptError]]:
    """Validate a video prompt against LTX best practices.

    Args:
        prompt: The video_prompt or video_prompt_en string.
        lang: Language code — ``"en"`` or ``"zh"``.
        character_count: Number of characters in the shot (for the >3 check).

    Returns:
        A ``(warnings, errors)`` tuple.  Empty lists mean all checks passed.
    """
    warnings: List[LTXPromptWarning] = []
    errors: List[LTXPromptError] = []

    if not prompt or not prompt.strip():
        return warnings, errors

    # ── Hard blocks ──────────────────────────────────────────────────
    for rule, p_all, p_zh, p_en, msg_zh, msg_en in _HARD_BLOCK_PATTERNS:
        patterns = p_zh if lang == "zh" and p_zh else (p_en if lang != "zh" and p_en else p_all)
        for pat in patterns:
            if pat.search(prompt):
                msg = msg_zh if lang == "zh" else msg_en
                errors.append(LTXPromptError(message=msg, rule=rule))
                break  # one error per rule per prompt

    # ── Soft warnings ────────────────────────────────────────────────
    for rule, p_all, p_front, p_back, msg_zh, msg_en in _SOFT_WARNING_PATTERNS:
        if rule == "conflicting_light_warning":
            has_front = any(pat.search(prompt) for pat in p_front) if p_front else False
            has_back = any(pat.search(prompt) for pat in p_back) if p_back else False
            if has_front and has_back:
                msg = msg_zh if lang == "zh" else msg_en
                warnings.append(LTXPromptWarning(message=msg, rule=rule))
        elif rule == "character_count_warning":
            if character_count > 3:
                msg = msg_zh if lang == "zh" else msg_en
                warnings.append(LTXPromptWarning(
                    message=f"{msg} (当前 {character_count} 个角色)",
                    rule=rule))
        elif rule == "prompt_length_warning":
            if lang == "en":
                sentences = [s.strip() for s in _RE_SENTENCE.split(prompt) if s.strip()]
                n = len(sentences)
                if n < 4 or n > 8:
                    msg = msg_zh if lang == "zh" else msg_en
                    warnings.append(LTXPromptWarning(
                        message=f"{msg} (当前 {n} 句)",
                        rule=rule))
        else:
            for pat in p_all:
                if pat.search(prompt):
                    msg = msg_zh if lang == "zh" else msg_en
                    warnings.append(LTXPromptWarning(message=msg, rule=rule))
                    break

    return warnings, errors
```

注意：这是完整替换现有文件的内容。关键变化：
- 硬编码正则 → JSON 加载 + `_compile_patterns` 预编译
- `check_video_prompt` 使用通用循环而非 if/elif 逐个规则
- 向后兼容：JSON 缺失时 `_RULES = {"hard_blocks": [], "soft_warnings": []}` 优雅降级

- [ ] **Step 3: 验证导入和功能一致性**

```bash
cd E:\Tools\Hermes\skills\nuomi-drama-skills && python -c "
from prompt_checker import check_video_prompt, _RULES, _HARD_BLOCK_PATTERNS, _SOFT_WARNING_PATTERNS

print(f'Rules version: {_RULES.get(\"version\", \"unknown\")}')
print(f'Hard blocks: {len(_HARD_BLOCK_PATTERNS)}')
print(f'Soft warnings: {len(_SOFT_WARNING_PATTERNS)}')

# 验证核心规则仍然生效
w, e = check_video_prompt('the character looks sad and nervous', lang='en')
assert len(e) > 0, 'Expected hard block for abstract emotion'
print(f'Abstract emotion block: {e[0].rule}')

w2, e2 = check_video_prompt('a logo appears on screen with text overlay', lang='en')
assert len(e2) > 0, 'Expected hard block for text/logo'
print(f'Text/logo block: {e2[0].rule}')

w3, e3 = check_video_prompt('the glass shatters into fragments', lang='en')
assert len(w3) > 0, 'Expected soft warning for complex physics'
print(f'Complex physics warning: {w3[0].rule}')

# 验证中文规则
w4, e4 = check_video_prompt('她很难过地低下头', lang='zh')
assert len(e4) > 0, 'Expected hard block for Chinese abstract emotion'
print(f'Chinese emotion block: {e4[0].rule}')

# 验证清洁 prompt
w5, e5 = check_video_prompt('camera pans slowly across the room, sunlight streams through the window, hands reach for the door handle', lang='en')
assert len(e5) == 0, f'Expected no errors for clean prompt, got {[x.rule for x in e5]}'
print('Clean prompt passed')

print('All prompt_checker tests passed — JSON config mode')
"
```

- [ ] **Step 4: Commit**

```bash
cd E:\Tools\Hermes\skills\nuomi-drama-skills && git add prompt_rules.json prompt_checker.py && git commit -m "feat: prompt_rules.json 配置化 + prompt_checker.py 通用规则引擎

LTX 规则从 JSON 加载，版本升级只需换配置。向后兼容：JSON 缺失时优雅降级。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: SKILL.md 门控矩阵表

**Files:**
- Modify: `E:\Tools\Hermes\skills\nuomi-drama-skills\SKILL.md`

- [ ] **Step 1: 在 SKILL.md 第 2 节（方法论引用）之后插入门控矩阵**

在 `## 3. 两档工作流` 之前插入新 section：

```markdown
## 2.5. 门控序列（创作软提醒 · 生成硬阻断）

每次阶段推进时，Agent 应按需跑对应 gate。软提醒 gate 不过可继续但需告知用户风险；
硬阻断 gate 不过必须修完才能进生成。

| Gate | 名称 | 阶段 | 阻断? | 触发时机 | 校验内容 |
|------|------|------|-------|----------|---------|
| G1 | 三轴一致性 | 立意后 | ⚠️ 软 | export / 推进到大纲前 | genre_id 命中注册表, style_id 命中, 基调四维全齐 + arc 合法 |
| G2 | 大纲完整性 | 大纲后 | ⚠️ 软 | export / 推进到圣经前 | episodes 数组完整, 每集必填字段(ep/标题/梗概/钩子/爽点) |
| G3 | 圣经非空 | 角色/场景后 | ⚠️ 软 | export / 推进到节拍前 | 角色/场景/道具/世界观/伏笔五表非空 |
| G4 | 节拍表校验 | 分卷后 | ⚠️ 软 | export / 推进到剧本前 | 目标集在卷内, thread/伏笔已声明, 节拍递增不倒序 |
| G5 | 分镜规范 | 分镜表后 | 🛑 硬 | generate images 前 | shot/group 必填字段, relation 合法, 交叉引用一致 |
| G6 | 提示词质量 | 分镜表后 | 🛑 硬 | generate video 前 | video_prompt 无抽象情绪/无文本Logo/无冲突光照 |
| G7 | 首帧完整 | 出图后 | 🛑 硬 | generate video 前 | 所有镜 jpg 首帧存在 |
| G8 | Provider 健康 | 生成前 | 🛑 硬 | 每次 provider 调用前 | API key 完整, workflow ID 配置, 连通性预检 |

**运行 gate**: Agent 可通过 Python 直接调用 `gates.py` 的对应函数，或调 `run_all_gates()` 批量：
```bash
python -c "from gates import run_all_gates; from pathlib import Path; \
  results = run_all_gates(Path('manuscript'), Path('out'), 'all'); \
  [print(f'{r.gate_name}: {\"PASS\" if r.passed else \"FAIL\"}') for r in results]"
```

**Gate 结果解读**:
- `hard_block=True` + `passed=False` → 🛑 必须修完 `errors` 列表的问题才能继续
- `hard_block=False` + `passed=False` → ⚠️ 看 `warnings` 列表，用户决定是否继续
- `hard_block=False` + `passed=True` → ✅ 通过
- `hard_block=True` + `passed=True` → ✅ 通过（硬阻断但全过 = 无问题）
```

- [ ] **Step 2: 验证 SKILL.md 结构完整性**

```bash
cd E:\Tools\Hermes\skills\nuomi-drama-skills && python -c "
md = open('SKILL.md', encoding='utf-8').read()
assert '门控序列' in md, 'Missing gate section'
assert 'G1' in md and 'G8' in md, 'Missing gate entries'
assert 'gates.py' in md, 'Missing gates.py reference'
print('SKILL.md gate table verified')
"
```

- [ ] **Step 3: Commit**

```bash
cd E:\Tools\Hermes\skills\nuomi-drama-skills && git add SKILL.md && git commit -m "docs: SKILL.md 增加门控矩阵表（G1-G8 分层阻断）

创作阶段 G1-G4 软提醒，生成阶段 G5-G8 硬阻断。
Agent 可见 + gates.py 可编程调用。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 完整性检查

| 文件 | Task | 状态 |
|------|------|------|
| `writing_state.py` | Task 1 | 新建 |
| `gates.py` | Task 2 | 新建 |
| `genre_params.py` | Task 3 | 新建 |
| `provider_chain.py` | Task 4 | 新建 |
| `director.py` | Task 5 | 新建 |
| `export.py` | Task 6 | 修改 |
| `prompt_rules.json` | Task 7 | 新建 |
| `prompt_checker.py` | Task 7 | 修改 |
| `SKILL.md` | Task 8 | 修改 |
| `skill.env.example` | Task 4 | 修改 |
| `templates/genres/zombie-survival.yaml` | Task 3 | 修改 |

**总新增**: 6 个 Python 文件 + 1 个 JSON 文件
**总修改**: 4 个文件
**总新增代码行**: ~600 行 Python + ~90 行 JSON + ~30 行 Markdown + ~20 行 YAML

---

## 自审结果

1. **Spec 覆盖**: 7 项全部有对应 Task。Task 1→4.1 状态机, Task 2→4.2 门控表, Task 3→4.3 题材参数, Task 4→4.4 Provider 容灾, Task 5→4.5 导演引擎, Task 6→4.6 剪映集成, Task 7→4.7 提示词配置化, Task 8→4.2 SKILL.md 门控表。

2. **Placeholder 扫描**: ✅ 无 TBD/TODO。所有代码步骤有完整实现。所有命令有预期输出。

3. **类型一致性**: ✅ `GateResult` 在 Task 2 定义，Task 2 内的所有 gate 函数返回一致。`ProviderChain` 在 Task 4 定义，方法签名与 `providers/base.py` 的 ABC 一致。`ShootProtocol` 在 Task 5 定义，`Verdict` 枚举值在 `record_attempt` 和 `suggest_verdict` 中引用一致。
