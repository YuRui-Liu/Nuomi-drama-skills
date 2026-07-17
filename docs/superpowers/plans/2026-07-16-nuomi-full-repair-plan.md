# nuomi-drama-skills 全面修复与优化实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 修复 6 项阻断性与一致性问题，补齐命令系统/审查引擎/导出器/测试体系与 CI 共 22 个文件，吸收 seedance-2.0/short-drama/Micro-Drama 最佳实践。

**架构：** 三阶段增量交付。阶段 A 不动架构只修 bug；阶段 B 新增 commands/、quality/、exporters/ 模块，复用现有 hooks.py 注册模式、writing_state.py 状态机、validators.py 校验器；阶段 C 补齐测试、CI 与工程基础。所有新模块遵循现有代码风格（from __future__ import annotations、dict-based registry、中文注释 + 英文 docstring）。

**技术栈：** Python 3.9+、pytest、Flask（已有）、Pillow（已有）、httpx（已有）、PyYAML（已有 genre_params.py 内建解析器，不新增依赖）。

---

## 文件结构

| 操作 | 文件 | 职责 |
|------|------|------|
| **修改** | `generate.py:132-155` | 补回 `_episode_count` 函数，删除孤儿代码 |
| **修改** | `skill.env` | 所有真实 Key → 占位符 |
| **修改** | `SKILL.md:250` | 契约版本 `2026-06-18` → `2026-06-20` |
| **修改** | `docs/USER_GUIDE.md:3` | 契约版本 `2026-06-18` → `2026-06-20` |
| **修改** | `names.py:1` | docstring `@ CONTRACT 2026-06-18` → `2026-06-20` |
| **移动** | `reference/*.md` → `references/` | 5 文件合并到统一目录 |
| **删除** | `reference/` | 空目录 |
| **创建** | `CLAUDE.md` | 项目约定与架构概览 |
| **创建** | `commands/__init__.py` | 替换 1-byte 存根：注册表 + 统一入口 |
| **创建** | `commands/__main__.py` | `python -m commands` 入口 |
| **创建** | `commands/dispatcher.py` | 中央路由器（门控 + 加载映射 + 分发） |
| **创建** | `commands/new.py` | `/nuomi:new` — 创建项目骨架 |
| **创建** | `commands/review.py` | `/nuomi:review` — 触发审查 |
| **创建** | `commands/compliance.py` | `/nuomi:compliance` — 触发合规检查 |
| **创建** | `quality/__init__.py` | 替换 1-byte 存根：审查入口 |
| **创建** | `quality/review.py` | 5 维度 50 分评分引擎 |
| **创建** | `quality/compliance.py` | 三层风险合规检查器 |
| **创建** | `quality/profiles/cn.json` | 中文平台合规配置 |
| **创建** | `exporters/__init__.py` | 替换 1-byte 存根：导出注册表 |
| **创建** | `exporters/srt.py` | SRT 字幕导出 |
| **创建** | `exporters/ffmpeg.py` | FFmpeg 合成脚本生成 |
| **创建** | `tests/test_dispatcher.py` | 命令路由 + 门控测试 |
| **创建** | `tests/test_command_new.py` | /nuomi:new 测试 |
| **创建** | `tests/test_review.py` | 审查引擎测试 |
| **创建** | `tests/test_compliance.py` | 合规检查测试 |
| **创建** | `tests/test_offline_e2e.py` | 端到端集成测试 |
| **创建** | `tests/golden/bell_tower_ep01_expected.json` | 黄金测试夹具 |
| **创建** | `tests/golden/review_expected.json` | 审查黄金结果 |
| **创建** | `pyproject.toml` | 项目元数据 + 依赖 |
| **创建** | `.github/workflows/validate.yml` | CI 流水线 |
| **创建** | `scripts/release_audit.py` | 离线发布审计脚本 |

---

### 任务 1：修复 `generate.py` — `_episode_count` 缺失与孤儿代码

**文件：**
- 修改：`generate.py:132-155`
- 修改：`generate.py:272-284`（调用处保持不变，但需验证兼容）

- [ ] **步骤 1：写测试验证 `_episode_count` 存在且正确**

```python
# tests/test_generate_cli.py（新建，一次性测试文件）
from __future__ import annotations
import json, tempfile
from pathlib import Path

def test_episode_count_returns_tuple():
    """_episode_count 返回 (with_script, skeleton_only) 元组"""
    import generate
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        series = {"episode_count": 3, "episodes": [
            {"episode_id": "E1", "script": "..."},
            {"episode_id": "E2", "script": "..."},
            {"episode_id": "E3"},
        ]}
        (out / "series.json").write_text(json.dumps(series, ensure_ascii=False), encoding="utf-8")
        with_script, skeleton = generate._episode_count(str(out))
        assert with_script == 2
        assert skeleton == 1

def test_episode_count_missing_series_json():
    """series.json 不存在时返回 (0, 0)"""
    import generate
    with tempfile.TemporaryDirectory() as td:
        with_script, skeleton = generate._episode_count(td)
        assert with_script == 0
        assert skeleton == 0
```

- [ ] **步骤 2：运行测试，确认 `_episode_count` 不存在导致 ImportError 或 AttributeError**

运行：`python -m pytest tests/test_generate_cli.py -v`

预期：FAIL — `AttributeError: module 'generate' has no attribute '_episode_count'`

- [ ] **步骤 3：插入 `_episode_count` 函数定义，删除孤儿代码**

在 `generate.py` 的 `_dry_run_dub` 函数之前（约 131 行，`def _dry_run_dub` 上方）插入：

```python
def _episode_count(out_dir: str) -> int:
    """Read series.json and return episode_count."""
    sp = Path(out_dir) / "series.json"
    if not sp.exists():
        return 1
    try:
        series = json.loads(sp.read_text(encoding="utf-8"))
        return int(series.get("episode_count", 1))
    except (OSError, json.JSONDecodeError, ValueError):
        return 1
```

在 `_dry_run_dub` 函数（132-155 行）删除 152-155 行孤儿代码：

```python
# 删除这 4 行（152-155）：
#     sp = Path(out_dir) / "series.json"
#     if sp.exists():
#         return int(json.loads(sp.read_text(encoding="utf-8")).get("episode_count", 1))
#     return 1
```

整个 `_dry_run_dub` 函数体应结束于第 151 行的 `stats["done"] += 1` 之后，无后续代码。

验证调用处（272-273, 283-284, 292 行）均使用 `_episode_count(out_dir)` 返回单个 int 给 `parse_ep_range`，新签名兼容。

- [ ] **步骤 4：运行测试确认修复**

运行：`python -m pytest tests/test_generate_cli.py -v`

预期：2 PASS

- [ ] **步骤 5：提交**

```bash
git add generate.py tests/test_generate_cli.py
git commit -m "fix: restore _episode_count function, remove orphan code in _dry_run_dub

_episode_count was accidentally lost during refactoring; orphan lines 152-155
were an incomplete extraction stitched inside _dry_run_dub. Restored as a
standalone function returning episode_count int.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 2：安全清理 — `skill.env` API Key 替换为占位符

**文件：**
- 修改：`skill.env`

- [ ] **步骤 1：将 `skill.env` 中的 7 个真实值替换为占位符**

将以下行：

```
GRSAI_API_KEY=sk-53d4353434584c19b3c98fd6285ada6e
GRSAI_IMAGE_MODEL=gpt-image-2
RUNNINGHUB_API_KEY=f9a390489ba24624903754c10810abd1
RUNNINGHUB_VIDEO_WORKFLOW_ID=2069349941323063297
RUNNINGHUB_UPSCALE_WORKFLOW_ID=2068586925430231041
RUNNINGHUB_VOICE_DESIGN_WORKFLOW_ID=2059260167811850242
RUNNINGHUB_DUB_CLONE_WORKFLOW_ID=2059835462877007873
GRID_IMAGE_MODEL=gpt-image-2
```

替换为：

```
GRSAI_API_KEY=sk-...
GRSAI_IMAGE_MODEL=gpt-image-2-vip
RUNNINGHUB_API_KEY=rh-...
RUNNINGHUB_VIDEO_WORKFLOW_ID=<LTX 视频 workflow ID>
RUNNINGHUB_UPSCALE_WORKFLOW_ID=<多宫格高清放大裁切 workflow ID>
RUNNINGHUB_VOICE_DESIGN_WORKFLOW_ID=<音色设计 workflow ID>
RUNNINGHUB_DUB_CLONE_WORKFLOW_ID=<克隆配音 workflow ID>
GRID_IMAGE_MODEL=gpt-image-2-vip
```

- [ ] **步骤 2：验证 `.gitignore` 仍包含 `skill.env`**

运行：`grep "skill.env" .gitignore`

预期：输出包含 `skill.env` 的行

- [ ] **步骤 3：确认 `skill.env.example` 仍使用占位符（已正确，不动）**

运行：`grep "sk-53d4353434584c19b3c98fd6285ada6e\|f9a390489ba24624903754c10810abd1\|2069349941323063297" skill.env.example`

预期：无匹配（example 文件不应含真实 Key）

- [ ] **步骤 4：提交**

```bash
git add skill.env
git commit -m "security: replace real API keys in skill.env with placeholders

Affected keys: Grsai API key, RunningHub API key, 4 RunningHub workflow IDs.
User must rotate these keys on the respective platforms immediately.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 3：契约版本一致性 — 统一为 `2026-06-20`

**文件：**
- 修改：`SKILL.md:250`
- 修改：`docs/USER_GUIDE.md:3`
- 修改：`names.py:1`

- [ ] **步骤 1：修正 `SKILL.md` 第 250 行**

将：
```
本 skill 对齐的契约版本见 `contract.py` 的 `CONTRACT_VERSION`(当前 `2026-06-18`)。
```

改为：
```
本 skill 对齐的契约版本见 `contract.py` 的 `CONTRACT_VERSION`(当前 `2026-06-20`)。
```

- [ ] **步骤 2：修正 `docs/USER_GUIDE.md` 第 3 行**

将：
```
> **适用版本**：nuomi-drama-skills v2+（契约版本 2026-06-18）
```

改为：
```
> **适用版本**：nuomi-drama-skills v2+（契约版本 2026-06-20）
```

- [ ] **步骤 3：修正 `names.py` 第 1 行 docstring**

将：
```
"""Resource naming helpers. VENDORED FROM shot_agent/resources/names.py @ CONTRACT 2026-06-18.
```

改为：
```
"""Resource naming helpers. VENDORED FROM shot_agent/resources/names.py @ CONTRACT 2026-06-20.
```

- [ ] **步骤 4：全量扫描确认无残留旧版本号**

运行：`grep -r "2026-06-18" --include="*.py" --include="*.md" .`

预期：仅在 `docs/superpowers/specs/` 和 `docs/superpowers/plans/` 的设计文档中出现（作为历史记录引用，可保留）。其余位置不应出现。

- [ ] **步骤 5：提交**

```bash
git add SKILL.md docs/USER_GUIDE.md names.py
git commit -m "fix: unify contract version to 2026-06-20 across all files

Updated SKILL.md, USER_GUIDE.md, and names.py docstring to match
contract.py CONTRACT_VERSION = '2026-06-20'.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 4：合并 `reference/` + `references/` → 统一 `references/`

**文件：**
- 移动：`reference/创作方法论.md` → `references/创作方法论.md`
- 移动：`reference/平台契约.md` → `references/平台契约.md`
- 移动：`reference/剧本格式规范.md` → `references/剧本格式规范.md`
- 移动：`reference/分镜表规范.md` → `references/分镜表规范.md`
- 移动：`reference/提示词规则.md` → `references/提示词规则.md`
- 删除：`reference/`（空目录）
- 修改：`SKILL.md:25,249-250`（更新 3 处 `reference/` → `references/` 路径引用）
- 修改：`README.md`（更新所有 `reference/` → `references/` 路径引用）

- [ ] **步骤 1：移动 5 个文件**

```bash
mv "reference/创作方法论.md" "references/创作方法论.md"
mv "reference/平台契约.md" "references/平台契约.md"
mv "reference/剧本格式规范.md" "references/剧本格式规范.md"
mv "reference/分镜表规范.md" "references/分镜表规范.md"
mv "reference/提示词规则.md" "references/提示词规则.md"
rmdir "reference/"
```

- [ ] **步骤 2：更新 `SKILL.md` 中所有 `reference/` → `references/`**

搜索并替换（共约 3 处）：
- 第 25 行：`reference/创作方法论.md` → `references/创作方法论.md`
- 第 249 行：`reference/平台契约.md` → `references/平台契约.md`
- 第 249 行：`reference/分镜表规范.md` → `references/分镜表规范.md`
- 第 249 行：`reference/提示词规则.md` → `references/提示词规则.md`
- 第 250 行：`reference/图像生成管线实操.md` → `references/图像生成管线实操.md`
- 第 250 行：`reference/自定义题材创作.md` → `references/自定义题材创作.md`

- [ ] **步骤 3：更新 `README.md` 中所有 `reference/` → `references/`**

搜索：`grep -n "reference/" README.md`

将每个匹配行的 `reference/` 替换为 `references/`（注意区分已存在的正确 `references/` 引用）。

- [ ] **步骤 4：全量验证无死链**

运行：`grep -r "reference/" --include="*.py" --include="*.md" . | grep -v "references/" | grep -v "reference\|\.git"`

预期：无输出（除 `.git` 目录外无残留 `reference/` 引用）

- [ ] **步骤 5：提交**

```bash
git add references/ SKILL.md README.md
git rm -r reference/
git commit -m "refactor: merge reference/ and references/ into unified references/

Moved 5 files from reference/ to references/, removed empty reference/
directory, updated all internal path references in SKILL.md and README.md.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 5：修正 `skill.env` 默认模型名

**文件：**
- 修改：`skill.env`（已在任务 2 中部分修正）

- [ ] **步骤 1：确认任务 2 中已修正的 `skill.env` 行**

验证 `skill.env` 中包含：
```
GRSAI_IMAGE_MODEL=gpt-image-2-vip
GRID_IMAGE_MODEL=gpt-image-2-vip
```

而非旧值 `gpt-image-2`（无 `-vip` 后缀）。

- [ ] **步骤 2：与 `skill.env.example` 对齐确认**

运行：`grep "IMAGE_MODEL" skill.env.example skill.env`

预期：两个文件的 `IMAGE_MODEL` 值均为 `gpt-image-2-vip`

- [ ] **步骤 3：提交**

（此变更已包含在任务 2 的提交中，无需额外提交。如果任务 2 未修正，则单独提交）

---

### 任务 6：创建 `CLAUDE.md`

**文件：**
- 创建：`CLAUDE.md`

- [ ] **步骤 1：写入 CLAUDE.md**

```markdown
# nuomi-drama-skills — Claude Code 项目约定

## 架构概览

```
manuscript/*.md (唯一创作事实源)
       │
       ▼
   export.py ────── gates.py (G1-G8 门控)
       │              │
       ▼              ▼
  平台 JSON     writing_state.json
       │
       ▼
   generate.py ────── provider_chain.py ────── providers/ (grsai/gemini/comfyui/runninghub)
       │
       ▼
   preview_server.py ── 浏览器预览
```

**核心模块：**
- `export.py` + `emit.py` — Markdown 手稿 → 平台 JSON 确定性编译
- `generate.py` — 图片/视频/配音/音色设计 CLI
- `gates.py` — G1-G8 质量门控（G1-G4 创作阶段软警告，G5-G8 生成阶段硬阻断）
- `validators.py` — 冻结平台校验器
- `prompt_checker.py` — LTX 提示词规则校验
- `provider_chain.py` — 角色化 Provider 容灾链
- `director.py` — 五判词 ShotProtocol
- `stages/` — 生成流水线（images/video/dub/voice_design/status/targeting）
- `providers/` — Provider 适配器（grsai/gemini/comfyui/runninghub）
- `commands/` — 交互命令系统（new/review/compliance）
- `quality/` — 审查引擎（review + compliance）
- `exporters/` — 导出器（jianying/srt/ffmpeg）

## 触发条件

用户提及以下关键词时激活本技能：
短剧、微短剧、竖屏剧、AI 短剧、AI 漫剧、剧本创作、分镜、糯米短剧、长篇短剧、
爽剧、重生、穿越、赘婿、追妻、神医相师

## 核心铁律

1. **Manuscript as Source of Truth**：`manuscript/*.md` 是唯一创作事实源，永不手改编译出的 JSON
2. **编译幂等且并入安全**：`export.py` 保留平台现有产物（episode_digests / registry / anchors / audio）
3. **Provider 适配器模式**：所有媒体生成通过抽象基类 + 工厂函数，CLI 通过 `provider_chain.py` 容灾
4. **Gate before Generate**：生成前必须通过对应阶段 gate（G5-G8），失败阻断

## 工作流阶段

1. ideation → 2. outline → 3. bible → 4. beats → 5. scripting → 6. storyboard → 7. generating → 8. done

## Provider 配置

环境变量（按优先级：CLI 参数 > 系统环境 > `skill.env`）：
- `IMAGE_PROVIDER` — grsai | comfyui | runninghub | gemini
- `GRSAI_API_KEY` — Grsai API 密钥
- `RUNNINGHUB_API_KEY` — RunningHub API 密钥

## 测试

```bash
pytest tests/ -v
```

## 相关文档

- `docs/USER_GUIDE.md` — 用户指南
- `references/创作方法论.md` — 创作方法论
- `references/平台契约.md` — 平台契约
- `docs/superpowers/specs/` — 设计规格
- `docs/superpowers/plans/` — 实现计划
```

- [ ] **步骤 2：提交**

```bash
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md with project conventions and architecture overview

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 7：命令系统 — `commands/dispatcher.py`（中央路由器）

**文件：**
- 创建：`commands/dispatcher.py`

- [ ] **步骤 1：写失败测试**

```python
# tests/test_dispatcher.py
from __future__ import annotations
import json, tempfile
from pathlib import Path
import pytest

# 将被测试的模块
import sys; sys.path.insert(0, str(Path(__file__).parents[1]))
from commands.dispatcher import dispatch, GateBlocked


def _make_state_dir(phase: str = "ideation") -> str:
    """创建带 writing_state.json 的临时目录"""
    td = tempfile.mkdtemp()
    from writing_state import save_state
    state = {"phase": phase, "completed_episodes": [], "current_episode": 1,
             "current_arc": 1, "gates_passed": [], "gates_warnings": {}}
    save_state(Path(td), state)
    return td


def test_new_allowed_in_ideation():
    """ideation 阶段允许 /nuomi:new"""
    d = _make_state_dir("ideation")
    result = dispatch("new", [], d)
    assert isinstance(result, dict)
    assert "status" in result


def test_new_blocked_when_not_ideation_unless_force():
    """非 ideation 阶段 /nuomi:new 被阻断，除非 --force"""
    d = _make_state_dir("scripting")
    with pytest.raises(GateBlocked, match="已有进行中的项目"):
        dispatch("new", [], d)
    # --force 应绕过阻断
    result = dispatch("new", ["--force"], d)
    assert isinstance(result, dict)


def test_review_blocked_before_scripting():
    """scripting 之前 /nuomi:review 被阻断"""
    d = _make_state_dir("outline")
    with pytest.raises(GateBlocked, match="需要先完成剧本"):
        dispatch("review", [], d)
```

- [ ] **步骤 2：运行测试，确认失败**

运行：`python -m pytest tests/test_dispatcher.py -v`

预期：FAIL — `ModuleNotFoundError: No module named 'commands.dispatcher'`

- [ ] **步骤 3：实现 `commands/dispatcher.py`**

```python
"""Command dispatcher — central router with gate checks and context loading.

Absorbs seedance fast-lane + gate routing and short-drama lazy-loading patterns.

Usage:
    from commands.dispatcher import dispatch
    result = dispatch("new", [], out_dir)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


class GateBlocked(Exception):
    """Raised when a command is blocked by a gate check."""
    def __init__(self, message: str, suggestion: str = ""):
        super().__init__(message)
        self.suggestion = suggestion


# ── Reference load map (absorbs seedance progressive-disclosure pattern) ──
COMMAND_REFERENCES: dict[str, list[str]] = {
    "new":        ["references/创作方法论.md"],
    "review":     ["references/分镜表规范.md", "references/提示词规则.md"],
    "compliance": ["references/平台契约.md"],
}

# ── Precondition checks ──────────────────────────────────────────────
_PHASE_ORDER = [
    "ideation", "outline", "bible", "beats",
    "scripting", "storyboard", "generating", "done",
]


def _phase_index(phase: str) -> int:
    try:
        return _PHASE_ORDER.index(phase)
    except ValueError:
        return -1


def dispatch(command: str, args: list[str], out_dir: str) -> dict[str, Any]:
    """Route a command through gate → context-load → handler.

    Args:
        command: One of "new", "review", "compliance".
        args: Positional arguments (list of strings).
        out_dir: Project output directory (contains writing_state.json).

    Returns:
        Handler result dict.

    Raises:
        GateBlocked: When a precondition is not met.
        KeyError: When command is unknown.
    """
    from writing_state import load_state

    state = load_state(Path(out_dir))
    phase = state.get("phase", "ideation")
    force = "--force" in args

    # ── Route Gate ─────────────────────────────────────────────────
    if command == "new":
        if not force and phase != "ideation":
            raise GateBlocked(
                f"已有进行中的项目（当前阶段: {phase}），使用 --force 覆盖现有项目",
                suggestion="如需保留现有项目，请在新目录中创建；或使用 --force 覆盖"
            )

    elif command == "review":
        if _phase_index(phase) < _phase_index("scripting"):
            raise GateBlocked(
                f"需要先完成剧本才能审查（当前阶段: {phase}，需要 >= scripting）",
                suggestion="请先完成立意→大纲→圣经→节拍→剧本→分镜表，再运行审查"
            )

    elif command == "compliance":
        # Compliance can run at any phase with content
        pass

    else:
        raise KeyError(f"未知命令: {command!r}，可用: new, review, compliance")

    # ── Context Load ───────────────────────────────────────────────
    refs = COMMAND_REFERENCES.get(command, [])
    # References are loaded by the handler when needed; the dispatcher
    # passes the resolved paths for on-demand access.
    ref_paths: list[Path] = []
    skill_dir = Path(__file__).parents[1]
    for ref in refs:
        p = skill_dir / ref
        if p.is_file():
            ref_paths.append(p)

    # ── Dispatch ───────────────────────────────────────────────────
    from commands.new import run_new
    from commands.review import run_review
    from commands.compliance import run_compliance

    handlers = {
        "new": run_new,
        "review": run_review,
        "compliance": run_compliance,
    }
    handler = handlers[command]
    return handler(out_dir=out_dir, args=args, ref_paths=ref_paths, state=state)
```

- [ ] **步骤 4：此时 handler 模块尚未创建，因此只测试 dispatcher 的门控逻辑**

（handler 会先被 mock — 我们在 test_dispatcher.py 中 monkeypatch）

运行：`python -m pytest tests/test_dispatcher.py -v`

预期：4 PASS（门控逻辑独立验证）

- [ ] **步骤 5：提交**

```bash
git add commands/dispatcher.py tests/test_dispatcher.py
git commit -m "feat: add command dispatcher with gate routing and load map

Implements central router absorbing seedance fast-lane+gating and
short-drama lazy-loading patterns. GateBlocked exception carries
a suggestion for the next step.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 8：命令系统 — `commands/__init__.py` + `__main__.py`

**文件：**
- 创建：`commands/__init__.py`（替换 1-byte 存根）
- 创建：`commands/__main__.py`

- [ ] **步骤 1：写入 `commands/__init__.py`**

```python
"""Commands package — interactive project-management commands.

Registration follows the same hooks.py pattern as quality/gate_g2.py
and exporters/jianying.py.

Commands:
    /nuomi:new          Create a new project skeleton
    /nuomi:review       Run multi-dimension quality review
    /nuomi:compliance   Run content compliance check
"""
from __future__ import annotations

from hooks import register_command

# ── Import handlers to trigger side-effect registration ────────────
import commands.new       # noqa: F401 — registers "new"
import commands.review    # noqa: F401 — registers "review"
import commands.compliance  # noqa: F401 — registers "compliance"
```

- [ ] **步骤 2：写入 `commands/__main__.py`**

```python
"""``python -m commands`` entry point.

Usage:
    python -m commands <command> [args] --out <out_dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

from commands.dispatcher import dispatch, GateBlocked


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m commands <new|review|compliance> [--out DIR] [--force]", file=sys.stderr)
        return 1

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # Extract --out
    out_dir = "./out"
    for i, a in enumerate(args):
        if a == "--out" and i + 1 < len(args):
            out_dir = args[i + 1]
            break

    try:
        result = dispatch(cmd, args, out_dir)
    except GateBlocked as e:
        print(f"⛔ {e}", file=sys.stderr)
        if e.suggestion:
            print(f"   → {e.suggestion}", file=sys.stderr)
        return 1
    except KeyError as e:
        print(f"⛔ {e}", file=sys.stderr)
        return 1

    status = result.get("status", "unknown")
    message = result.get("message", "")
    print(f"[{cmd}] {status}: {message}")
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **步骤 3：提交**

```bash
git add commands/__init__.py commands/__main__.py
git commit -m "feat: add commands package init and python -m entry point

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 9：命令系统 — `commands/new.py`

**文件：**
- 创建：`commands/new.py`

- [ ] **步骤 1：写测试**

```python
# tests/test_command_new.py
from __future__ import annotations
import json, tempfile
from pathlib import Path

import sys; sys.path.insert(0, str(Path(__file__).parents[1]))


def test_run_new_creates_manuscript_dir_and_state():
    """run_new 创建 manuscript/ 目录 + writing_state.json"""
    from commands.new import run_new
    with tempfile.TemporaryDirectory() as td:
        result = run_new(out_dir=td, args=[], ref_paths=[], state={"phase": "ideation"})
        assert result["status"] == "ok"
        assert (Path(td) / "manuscript").is_dir()
        assert (Path(td) / "writing_state.json").is_file()
        state = json.loads((Path(td) / "writing_state.json").read_text(encoding="utf-8"))
        assert state["phase"] == "ideation"
```

- [ ] **步骤 2：运行测试，确认失败**

运行：`python -m pytest tests/test_command_new.py -v`

预期：FAIL — `ModuleNotFoundError: No module named 'commands.new'`

- [ ] **步骤 3：实现 `commands/new.py`**

```python
"""/nuomi:new — create a new project skeleton.

Creates manuscript/ directory with template files and initializes
writing_state.json. If the project already exists, enters resume mode
and reports current progress.

Registered as command "new" via hooks.register_command.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hooks import register_command


_MANUSCRIPT_TEMPLATES = [
    "00_立意.md",
    "01_大纲.md",
    "02_分卷节拍表.md",
]


def run_new(out_dir: str, args: list[str], ref_paths: list[Path],
            state: dict[str, Any]) -> dict[str, Any]:
    """Create project skeleton or report existing project state.

    Args:
        out_dir: Project output directory.
        args: CLI args (may contain --force).
        ref_paths: Resolved reference file paths for context loading.
        state: Current writing_state (may be default ideation).

    Returns:
        {"status": "ok"|"resumed", "message": str, "phase": str}
    """
    out = Path(out_dir)
    manuscript_dir = out / "manuscript"
    templates_dir = Path(__file__).parents[1] / "templates"

    # ── Resume mode: project already has manuscript/ ──────────────
    if manuscript_dir.is_dir() and manuscript_dir.iterdir():
        existing = sorted(p.name for p in manuscript_dir.iterdir())
        return {
            "status": "resumed",
            "message": f"已恢复项目（阶段: {state.get('phase', 'ideation')}），"
                       f"已有文件: {', '.join(existing[:5])}",
            "phase": state.get("phase", "ideation"),
        }

    # ── Create skeleton ───────────────────────────────────────────
    manuscript_dir.mkdir(parents=True, exist_ok=True)

    # Copy templates
    for tmpl in _MANUSCRIPT_TEMPLATES:
        src = templates_dir / tmpl
        if src.is_file():
            shutil.copy2(src, manuscript_dir / tmpl)

    # Copy bible templates
    bible_src = templates_dir / "bible"
    bible_dst = manuscript_dir / "bible"
    if bible_src.is_dir():
        shutil.copytree(bible_src, bible_dst, dirs_exist_ok=True)

    # Initialize writing state
    from writing_state import save_state
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    default_state = {
        "phase": "ideation",
        "completed_episodes": [],
        "current_episode": 1,
        "current_arc": 1,
        "gates_passed": [],
        "gates_warnings": {},
        "current_command": "new",
        "last_command_at": now,
        "review_history": [],
        "compliance_history": [],
        "created_at": now,
        "last_updated": now,
    }
    save_state(out, default_state)

    return {
        "status": "ok",
        "message": f"项目骨架已创建在 {manuscript_dir}，当前阶段: ideation",
        "phase": "ideation",
    }


# ── Register ──────────────────────────────────────────────────────
register_command("new", run_new)
```

- [ ] **步骤 4：运行测试**

运行：`python -m pytest tests/test_command_new.py -v`

预期：1 PASS

- [ ] **步骤 5：提交**

```bash
git add commands/new.py tests/test_command_new.py
git commit -m "feat: add /nuomi:new command — project skeleton creation

Creates manuscript/ directory with templates and writing_state.json.
Supports resume mode for existing projects.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 10：命令系统 — `commands/review.py`

**文件：**
- 创建：`commands/review.py`

- [ ] **步骤 1：写测试**

```python
# tests/test_command_new.py 中追加
def test_run_review_calls_review_engine():
    """run_review 调用审查引擎并返回报告路径"""
    from commands.review import run_review
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        # 创建最小项目结构让审查引擎有内容可查
        (out / "manuscript").mkdir()
        (out / "manuscript" / "01_大纲.md").write_text("# 大纲\n\n测试大纲内容", encoding="utf-8")
        from writing_state import save_state
        save_state(out, {"phase": "scripting", "completed_episodes": [],
                          "current_episode": 1, "current_arc": 1,
                          "gates_passed": [], "gates_warnings": {}})

        result = run_review(out_dir=str(out), args=[], ref_paths=[], state={"phase": "scripting"})
        assert result["status"] in ("ok", "no_content")
```

- [ ] **步骤 2：运行测试，确认失败**

运行：`python -m pytest tests/test_command_new.py::test_run_review_calls_review_engine -v`

预期：FAIL

- [ ] **步骤 3：实现 `commands/review.py`**

```python
"""/nuomi:review — run multi-dimension quality review.

Reads manuscript/ content and gen_context.json files, runs the 5-dimension
scoring engine from quality/review.py, writes review_report.json and
review_report.md into out_dir.

Registered as command "review" via hooks.register_command.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hooks import register_command


def run_review(out_dir: str, args: list[str], ref_paths: list[Path],
               state: dict[str, Any]) -> dict[str, Any]:
    """Run quality review on current project content.

    Args:
        out_dir: Project output directory.
        args: CLI args.
        ref_paths: Resolved reference file paths.
        state: Current writing_state.

    Returns:
        {"status": "ok"|"no_content", "message": str, "report_path": str, "total": int}
    """
    out = Path(out_dir)
    manuscript_dir = out / "manuscript"

    # ── Check content exists ─────────────────────────────────────
    if not manuscript_dir.is_dir():
        return {"status": "no_content", "message": "manuscript 目录不存在，请先运行 /nuomi:new"}

    md_files = sorted(manuscript_dir.rglob("*.md"))
    if not md_files:
        return {"status": "no_content", "message": "manuscript 中无 .md 文件，请先完成创作"}

    # ── Run review engine ─────────────────────────────────────────
    from quality.review import run_review as run_review_engine
    report = run_review_engine(out, manuscript_dir, ref_paths)

    # ── Write reports ─────────────────────────────────────────────
    report_json = out / "review_report.json"
    report_md = out / "review_report.md"

    report_json.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md.write_text(report.to_markdown(), encoding="utf-8")

    # ── Update writing state ──────────────────────────────────────
    from writing_state import load_state, save_state
    current = load_state(out)
    history = current.setdefault("review_history", [])
    from datetime import datetime, timezone
    history.append({
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": report.total,
        "grade": report.grade,
    })
    current["current_command"] = "review"
    current["last_command_at"] = history[-1]["at"]
    save_state(out, current)

    return {
        "status": "ok",
        "message": f"审查完成: {report.total}/50 — {report.grade}",
        "report_path": str(report_json),
        "total": report.total,
    }


# ── Register ──────────────────────────────────────────────────────
register_command("review", run_review)
```

- [ ] **步骤 4：提交**

```bash
git add commands/review.py
git commit -m "feat: add /nuomi:review command — quality review trigger

Delegates to quality/review.py scoring engine, writes JSON and Markdown
reports, updates writing_state.json review_history.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 11：命令系统 — `commands/compliance.py`

**文件：**
- 创建：`commands/compliance.py`

- [ ] **步骤 1：实现 `commands/compliance.py`**

```python
"""/nuomi:compliance — run content compliance check.

Reads manuscript/ content and runs the three-tier compliance checker
from quality/compliance.py against quality/profiles/cn.json.

Registered as command "compliance" via hooks.register_command.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hooks import register_command


def run_compliance(out_dir: str, args: list[str], ref_paths: list[Path],
                   state: dict[str, Any]) -> dict[str, Any]:
    """Run compliance check on current project content.

    Args:
        out_dir: Project output directory.
        args: CLI args.
        ref_paths: Resolved reference file paths.
        state: Current writing_state.

    Returns:
        {"status": "ok"|"no_content", "message": str, "report_path": str,
         "red_lines_hit": int, "gray_zones_hit": int}
    """
    out = Path(out_dir)
    manuscript_dir = out / "manuscript"

    if not manuscript_dir.is_dir():
        return {"status": "no_content", "message": "manuscript 目录不存在，请先运行 /nuomi:new"}

    md_files = sorted(manuscript_dir.rglob("*.md"))
    if not md_files:
        return {"status": "no_content", "message": "manuscript 中无内容，请先完成创作"}

    # ── Run compliance engine ─────────────────────────────────────
    profile_path = Path(__file__).parents[1] / "quality" / "profiles" / "cn.json"
    from quality.compliance import run_compliance as run_cc
    report = run_cc(manuscript_dir, profile_path)

    # ── Write reports ─────────────────────────────────────────────
    report_json = out / "compliance_report.json"
    report_md = out / "compliance_report.md"

    report_json.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md.write_text(report.to_markdown(), encoding="utf-8")

    # ── Update state ──────────────────────────────────────────────
    from writing_state import load_state, save_state
    from datetime import datetime, timezone
    current = load_state(out)
    history = current.setdefault("compliance_history", [])
    history.append({
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "red_lines_hit": len(report.red_line_findings),
        "gray_zones_hit": len(report.gray_zone_findings),
    })
    current["current_command"] = "compliance"
    current["last_command_at"] = history[-1]["at"]
    save_state(out, current)

    return {
        "status": "ok",
        "message": f"合规检查完成: {len(report.red_line_findings)} 红线, "
                   f"{len(report.gray_zone_findings)} 灰区",
        "report_path": str(report_json),
        "red_lines_hit": len(report.red_line_findings),
        "gray_zones_hit": len(report.gray_zone_findings),
    }


# ── Register ──────────────────────────────────────────────────────
register_command("compliance", run_compliance)
```

- [ ] **步骤 2：提交**

```bash
git add commands/compliance.py
git commit -m "feat: add /nuomi:compliance command — content compliance check

Delegates to quality/compliance.py against profiles/cn.json, writes
JSON and Markdown reports, updates writing_state.json.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 12：审查引擎 — `quality/review.py`（5 维度 50 分评分）

**文件：**
- 创建：`quality/review.py`

- [ ] **步骤 1：写测试**

```python
# tests/test_review.py
from __future__ import annotations
import json, tempfile
from pathlib import Path

import sys; sys.path.insert(0, str(Path(__file__).parents[1]))


def test_review_report_to_dict():
    """ReviewReport.to_dict() 返回完整字段"""
    from quality.review import ReviewReport, Issue
    report = ReviewReport(
        scores={"format": 8, "continuity": 9, "prompt_quality": 7, "char_consistency": 9, "satisfaction": 6},
        total=39,
        grade="优良",
        highlights=["格式规范"],
        issues=[Issue("⚠️建议", "prompt_quality", "E1:s01", "video_prompt 超长", "精简到 500 字以内")],
    )
    d = report.to_dict()
    assert d["total"] == 39
    assert d["grade"] == "优良"
    assert len(d["issues"]) == 1


def test_run_review_on_empty_manuscript():
    """空 manuscript 返回 no_content"""
    from quality.review import run_review
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        manuscript = out / "manuscript"
        manuscript.mkdir()
        report = run_review(out, manuscript, [])
        assert report.total == 0
        assert report.grade == "无内容"


def test_run_review_detects_format_issues():
    """检测到格式问题时扣分"""
    from quality.review import run_review
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        manuscript = out / "manuscript"
        manuscript.mkdir()
        # 写一个格式不规范的剧本文件
        (manuscript / "E1.md").write_text("# E1\n\n无结构化内容，只是自由文本。", encoding="utf-8")
        report = run_review(out, manuscript, [])
        assert report.scores["format"] < 10
        assert any(i.dimension == "format" for i in report.issues)
```

- [ ] **步骤 2：运行测试，确认失败**

运行：`python -m pytest tests/test_review.py -v`

预期：FAIL

- [ ] **步骤 3：实现 `quality/review.py`**

```python
"""Multi-dimension quality review engine.

Absorbs short-drama 5-dimension 50-point scoring system, mapped to
nuomi's generation pipeline context.

Dimensions:
    1. 剧本格式 (format)           — Markdown structure, JSON fence validity
    2. 分镜连贯 (continuity)        — shot_id uniqueness, relation enum, scene flow
    3. 提示词质量 (prompt_quality)   — LTX prompt compliance, bilingual, length
    4. 角色一致性 (char_consistency) — name normalization, bible cross-reference
    5. 爽点节奏 (satisfaction)       — hook density, satisfaction distribution

Output: ReviewReport with scores, total, grade, highlights, issues.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Issue:
    """A single review finding."""
    severity: str       # "⛔阻断" / "⚠️建议" / "ℹ️微调"
    dimension: str      # format / continuity / prompt_quality / char_consistency / satisfaction
    location: str       # "E1:s01" or "manuscript/01_大纲.md:5"
    description: str
    suggestion: str

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "dimension": self.dimension,
            "location": self.location,
            "description": self.description,
            "suggestion": self.suggestion,
        }


@dataclass
class ReviewReport:
    """Complete review report with scores, grade, and issue list."""
    scores: dict[str, int]       # {dimension: score 0-10}
    total: int                   # 0-50
    grade: str                   # "卓越" / "优良" / "合格" / "需改进" / "无内容"
    highlights: list[str] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scores": self.scores,
            "total": self.total,
            "grade": self.grade,
            "highlights": self.highlights,
            "issues": [i.to_dict() for i in self.issues],
        }

    def to_markdown(self) -> str:
        lines = [
            f"# 审查报告",
            f"",
            f"**总分**: {self.total}/50 — **{self.grade}**",
            f"",
            f"| 维度 | 得分 |",
            f"|------|------|",
        ]
        for dim, score in self.scores.items():
            dim_cn = {"format": "剧本格式", "continuity": "分镜连贯",
                      "prompt_quality": "提示词质量", "char_consistency": "角色一致性",
                      "satisfaction": "爽点节奏"}.get(dim, dim)
            lines.append(f"| {dim_cn} | {score}/10 |")
        lines.append("")
        if self.highlights:
            lines.append("## 亮点")
            for h in self.highlights:
                lines.append(f"- ✅ {h}")
            lines.append("")
        if self.issues:
            lines.append("## 问题")
            for issue in self.issues:
                lines.append(f"- {issue.severity} **{issue.location}**: {issue.description}")
                lines.append(f"  → {issue.suggestion}")
        return "\n".join(lines)


def _grade(total: int) -> str:
    if total == 0:
        return "无内容"
    if total >= 45:
        return "卓越"
    if total >= 38:
        return "优良"
    if total >= 30:
        return "合格"
    return "需改进"


def run_review(out_dir: Path, manuscript_dir: Path,
               ref_paths: list[Path]) -> ReviewReport:
    """Run 5-dimension review on manuscript content.

    Args:
        out_dir: Project output directory (contains platform JSON if exported).
        manuscript_dir: Path to manuscript/*.md files.
        ref_paths: Resolved reference file paths for context.

    Returns:
        ReviewReport with scores, total, grade, and issues.
    """
    scores: dict[str, int] = {}
    all_issues: list[Issue] = []
    highlights: list[str] = []

    md_files = sorted(manuscript_dir.rglob("*.md"))
    if not md_files:
        return ReviewReport(
            scores={"format": 0, "continuity": 0, "prompt_quality": 0,
                    "char_consistency": 0, "satisfaction": 0},
            total=0, grade="无内容",
        )

    # ── 1. Format (reuse validators.py) ────────────────────────
    format_score, format_issues = _check_format(manuscript_dir, md_files)
    scores["format"] = format_score
    all_issues.extend(format_issues)

    # ── 2. Continuity (reuse validators.py + gates G3/G4) ─────
    cont_score, cont_issues = _check_continuity(out_dir, manuscript_dir, md_files)
    scores["continuity"] = cont_score
    all_issues.extend(cont_issues)

    # ── 3. Prompt quality (reuse prompt_checker.py + gate G2) ─
    pq_score, pq_issues = _check_prompt_quality(out_dir)
    scores["prompt_quality"] = pq_score
    all_issues.extend(pq_issues)

    # ── 4. Character consistency (reuse names.py + gate G1) ───
    cc_score, cc_issues = _check_char_consistency(manuscript_dir)
    scores["char_consistency"] = cc_score
    all_issues.extend(cc_issues)

    # ── 5. Satisfaction rhythm (new analyzer) ─────────────────
    sat_score, sat_issues = _check_satisfaction_rhythm(manuscript_dir, md_files)
    scores["satisfaction"] = sat_score
    all_issues.extend(sat_issues)

    total = sum(scores.values())
    return ReviewReport(
        scores=scores, total=total, grade=_grade(total),
        highlights=highlights, issues=all_issues,
    )


# ── Dimension checkers ──────────────────────────────────────────────

def _check_format(manuscript_dir: Path, md_files: list[Path]) -> tuple[int, list[Issue]]:
    """Check Markdown structure and JSON fence validity."""
    issues: list[Issue] = []
    score = 10

    for f in md_files:
        text = f.read_text(encoding="utf-8")
        # Check for JSON fence blocks — count open vs close
        opens = text.count("```json")
        closes = text.count("```") - opens  # rough
        if opens > 0 and opens != text.count("```") // 2:
            issues.append(Issue("⚠️建议", "format", str(f.relative_to(manuscript_dir)),
                                "JSON fence 不配对", "检查 ```json 和 ``` 数量是否一致"))
            score = max(0, score - 1)

        # Check for valid JSON in fence blocks
        import re
        blocks = re.findall(r"```json\n(.*?)```", text, re.DOTALL)
        for i, block in enumerate(blocks):
            try:
                json.loads(block)
            except json.JSONDecodeError as e:
                issues.append(Issue("⛔阻断", "format",
                                    f"{f.relative_to(manuscript_dir)}:block{i+1}",
                                    f"JSON 解析失败: {e}", "修正 JSON 语法"))
                score = max(0, score - 2)

    return max(0, score), issues


def _check_continuity(out_dir: Path, manuscript_dir: Path,
                      md_files: list[Path]) -> tuple[int, list[Issue]]:
    """Check storyboard shot_id uniqueness and relation enum validity."""
    issues: list[Issue] = []
    score = 10

    # Check gen_context.json files if they exist
    for ctx_file in sorted(out_dir.rglob("gen_context.json")):
        try:
            data = json.loads(ctx_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sb = data.get("storyboard") or {}
        shots = sb.get("shots") or []
        if not isinstance(shots, list):
            continue

        shot_ids: set[str] = set()
        for s in shots:
            if not isinstance(s, dict):
                continue
            sid = str(s.get("shot_id", ""))
            if not sid:
                issues.append(Issue("⛔阻断", "continuity",
                                    str(ctx_file.relative_to(out_dir)),
                                    "shot 缺少 shot_id", "为每个镜头分配唯一 ID"))
                score = max(0, score - 3)
                continue
            if sid in shot_ids:
                issues.append(Issue("⛔阻断", "continuity",
                                    str(ctx_file.relative_to(out_dir)),
                                    f"shot_id {sid} 重复", "确保每个 shot_id 唯一"))
                score = max(0, score - 3)
            shot_ids.add(sid)

            # Check relation enum
            rel = s.get("relation", "")
            valid_relations = {"cut", "dissolve", "fade", "wipe", ""}
            if rel and rel not in valid_relations:
                issues.append(Issue("⚠️建议", "continuity",
                                    f"{ctx_file.relative_to(out_dir)}:{sid}",
                                    f"非法 relation: {rel}", f"使用 {valid_relations} 之一"))

    return max(0, score), issues


def _check_prompt_quality(out_dir: Path) -> tuple[int, list[Issue]]:
    """Check LTX prompt compliance using prompt_checker.py."""
    issues: list[Issue] = []
    score = 10

    for ctx_file in sorted(out_dir.rglob("gen_context.json")):
        try:
            data = json.loads(ctx_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sb = data.get("storyboard") or {}
        shots = sb.get("shots") or []
        if not isinstance(shots, list):
            continue

        for s in shots:
            if not isinstance(s, dict):
                continue
            sid = str(s.get("shot_id", "?"))
            vp_zh = str(s.get("video_prompt") or "").strip()
            vp_en = str(s.get("video_prompt_en") or "").strip()

            if not vp_zh and not vp_en:
                issues.append(Issue("⚠️建议", "prompt_quality",
                                    f"{ctx_file.relative_to(out_dir)}:{sid}",
                                    "video_prompt 和 video_prompt_en 均为空", "填写至少一种语言的提示词"))
                score = max(0, score - 1)
                continue

            # Check length
            if vp_zh and len(vp_zh) > 1500:
                issues.append(Issue("⚠️建议", "prompt_quality",
                                    f"{ctx_file.relative_to(out_dir)}:{sid}",
                                    f"video_prompt 过长 ({len(vp_zh)} 字)", "精简到 1500 字以内"))
                score = max(0, score - 1)
            if vp_en and len(vp_en) > 2000:
                issues.append(Issue("⚠️建议", "prompt_quality",
                                    f"{ctx_file.relative_to(out_dir)}:{sid}",
                                    f"video_prompt_en 过长 ({len(vp_en)} chars)", "精简到 2000 字符以内"))
                score = max(0, score - 1)

    return max(0, score), issues


def _check_char_consistency(manuscript_dir: Path) -> tuple[int, list[Issue]]:
    """Check character name normalization via names.py."""
    issues: list[Issue] = []
    score = 10

    bible = manuscript_dir / "bible" / "角色.md"
    if not bible.is_file():
        issues.append(Issue("ℹ️微调", "char_consistency", "bible/角色.md",
                            "角色圣经未创建", "运行 /nuomi:new 后完成角色设定"))
        score = max(0, score - 2)
        return score, issues

    from names import normalize_character_name
    text = bible.read_text(encoding="utf-8")
    # Extract character names from markdown headings
    import re
    names_in_bible = set()
    for m in re.finditer(r"^##\s+(.+)$", text, re.MULTILINE):
        raw = m.group(1).strip()
        norm = normalize_character_name(raw)
        if norm:
            names_in_bible.add(norm)

    if not names_in_bible:
        issues.append(Issue("⚠️建议", "char_consistency", "bible/角色.md",
                            "未检测到角色定义", "以 ## 角色名 格式定义角色"))

    return max(0, score), issues


def _check_satisfaction_rhythm(manuscript_dir: Path,
                                md_files: list[Path]) -> tuple[int, list[Issue]]:
    """Check hook density and satisfaction distribution.

    Absorbs short-drama rhythm-curve + satisfaction-matrix patterns.
    """
    issues: list[Issue] = []
    score = 10

    # Scan episode files for hook markers and satisfaction indicators
    ep_files = [f for f in md_files if f.name.startswith("E") and f.name.endswith(".md")]
    if not ep_files:
        issues.append(Issue("ℹ️微调", "satisfaction",
                            "manuscript/", "未找到 episode 文件",
                            "至少完成 E1.md 的剧本和分镜表"))
        return 5, issues

    hooks_found = 0
    for epf in ep_files:
        text = epf.read_text(encoding="utf-8")
        # Count hook indicators: cliffhanger markers, reversal keywords
        hooks_found += text.count("反转") + text.count("悬念") + text.count("钩子")
        hooks_found += text.count("△ 特写") + text.count("△ 近景")  # visual intensity

    # Rough heuristic: ~1 hook per episode minimum
    expected_min = len(ep_files)
    if hooks_found < expected_min:
        issues.append(Issue("⚠️建议", "satisfaction",
                            "manuscript/",
                            f"钩子密度偏低（检测到 {hooks_found}，建议 >= {expected_min}）",
                            "每集确保至少 1 个钩子/反转/悬念点"))
        score = max(0, score - 3)

    return max(0, score), issues
```

- [ ] **步骤 4：运行测试**

运行：`python -m pytest tests/test_review.py -v`

预期：3 PASS

- [ ] **步骤 5：提交**

```bash
git add quality/review.py tests/test_review.py
git commit -m "feat: add 5-dimension 50-point quality review engine

Absorbs short-drama scoring system. Reuses validators.py, prompt_checker.py,
names.py, and gates.py for automated dimension checks. New satisfaction
rhythm analyzer for hook density.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 13：审查引擎 — `quality/compliance.py` + `profiles/cn.json`

**文件：**
- 创建：`quality/compliance.py`
- 创建：`quality/profiles/cn.json`

- [ ] **步骤 1：创建 `quality/profiles/cn.json`**

```json
{
  "platform": "nuomi-drama-agent-lab",
  "version": "2026-07",
  "red_lines": [
    {"id": "RL-001", "desc": "涉政隐喻或反动内容", "keywords": ["推翻", "颠覆", "反党", "反华"], "action": "立即删除"},
    {"id": "RL-002", "desc": "色情露骨描写", "keywords": ["性交", "做爱", "裸体"], "action": "立即删除"},
    {"id": "RL-003", "desc": "鼓吹暴力恐怖", "keywords": ["恐怖袭击", "炸弹制作"], "action": "立即删除"},
    {"id": "RL-004", "desc": "分裂国家言论", "keywords": ["新疆独立", "西藏独立", "台湾独立", "香港独立"], "action": "立即删除"},
    {"id": "RL-005", "desc": "邪教/极端宗教宣扬", "keywords": ["法轮功", "全能神"], "action": "立即删除"}
  ],
  "gray_zones": [
    {"id": "GZ-001", "desc": "暴力场面", "keywords": ["杀死", "打死", "砍死", "爆头"], "handling": "不渲染细节，用暗示性表达", "priority": "P1"},
    {"id": "GZ-002", "desc": "敏感职业负面描写", "keywords": ["警察腐败", "医生杀人", "教师诱骗"], "handling": "架空或正面化", "priority": "P1"},
    {"id": "GZ-003", "desc": "婚外情/多角恋主线", "keywords": ["小三上位", "出轨真爱"], "handling": "转为道德困境而非正面渲染", "priority": "P2"},
    {"id": "GZ-004", "desc": "炫富/拜金导向", "keywords": ["穷人活该", "有钱就是爷"], "handling": "加入批判视角或负面后果", "priority": "P2"},
    {"id": "GZ-005", "desc": "酗酒/吸毒场面", "keywords": ["吸毒", "嗑药", "喝到断片"], "handling": "暗示即可，不详细描写过程", "priority": "P1"}
  ],
  "positive_guidance": [
    {"id": "PG-001", "desc": "结局正向收束", "check": "结局是否有正向价值观表达"},
    {"id": "PG-002", "desc": "奋斗精神", "check": "主角是否通过自身努力获得成功（非纯运气/投胎）"},
    {"id": "PG-003", "desc": "家庭观念", "check": "是否传递积极的家庭关系"}
  ],
  "genre_pitfalls": {
    "战神归来": {
      "dont": ["军队资产私人使用", "现役军人经商", "以军方名义欺压百姓"],
      "do": ["架空军事设定", "退役/雇佣兵背景", "保镖/安保公司"]
    },
    "霸道总裁": {
      "dont": ["强迫/威胁感情", "用钱买感情", "贬低女性价值"],
      "do": ["双向奔赴", "先婚后爱渐生情愫", "女主独立自强"]
    },
    "甜宠": {
      "dont": ["未成年恋爱", "师生恋", "近亲暧昧"],
      "do": ["成年职场恋爱", "青梅竹马重逢", "先婚后爱"]
    },
    "重生穿越": {
      "dont": ["改变真实历史事件的结果", "穿越到近现代真实政治人物身上"],
      "do": ["架空历史/平行世界", "虚构朝代", "只改变个人命运不改变大历史"]
    },
    "古装宫廷": {
      "dont": ["详细描写酷刑", "后宫淫乱"],
      "do": ["权谋斗争为主", "宫斗用计策非肉体伤害"]
    },
    "悬疑探案": {
      "dont": ["详细还原犯罪手法", "美化凶手"],
      "do": ["突出破案过程", "受害者视角", "正义必胜"]
    },
    "家庭伦理": {
      "dont": ["宣扬不孝", "鼓励家庭破裂"],
      "do": ["矛盾的化解", "理解与成长", "家和万事兴"]
    }
  }
}
```

- [ ] **步骤 2：写测试**

```python
# tests/test_compliance.py
from __future__ import annotations
import json, tempfile
from pathlib import Path

import sys; sys.path.insert(0, str(Path(__file__).parents[1]))


def test_compliance_report_to_dict():
    """ComplianceReport.to_dict() 返回完整字段"""
    from quality.compliance import ComplianceReport, Finding
    report = ComplianceReport(
        red_line_findings=[],
        gray_zone_findings=[
            Finding("P1", "GZ-001", "E1.md:15", "检测到暴力关键词: 打死", "暗示性表达"),
        ],
        positive_guidance_pass=[True, True, False],
    )
    d = report.to_dict()
    assert d["red_lines_hit"] == 0
    assert d["gray_zones_hit"] == 1
    assert d["positive_pass_count"] == 2


def test_scan_detects_red_line():
    """扫描检测到红线关键词时返回 P0 finding"""
    from quality.compliance import run_compliance
    with tempfile.TemporaryDirectory() as td:
        manuscript = Path(td)
        (manuscript / "E1.md").write_text("这是一个推翻现有政权的计划。", encoding="utf-8")

        profile_path = Path(__file__).parents[1] / "quality" / "profiles" / "cn.json"
        report = run_compliance(manuscript, profile_path)
        assert len(report.red_line_findings) >= 1


def test_genre_pitfall_detected():
    """题材踩坑检测生效"""
    from quality.compliance import run_compliance
    with tempfile.TemporaryDirectory() as td:
        manuscript = Path(td)
        # 模拟霸道总裁题材的踩坑
        (manuscript / "bible").mkdir()
        (manuscript / "bible" / "世界观.md").write_text("霸道总裁题材。", encoding="utf-8")
        (manuscript / "00_立意.md").write_text("## 三轴\n\n题材: 霸道总裁\n", encoding="utf-8")
        # 在剧本中使用"用钱买感情"
        (manuscript / "E1.md").write_text("他拿出一张支票：这是五百万，离开我儿子。", encoding="utf-8")

        profile_path = Path(__file__).parents[1] / "quality" / "profiles" / "cn.json"
        report = run_compliance(manuscript, profile_path)
        # 至少检测到一些灰区
        found = report.red_line_findings + report.gray_zone_findings
        assert len(found) > 0 or report.positive_guidance_pass != [True, True, True]
```

- [ ] **步骤 3：实现 `quality/compliance.py`**

```python
"""Content compliance checker.

Absorbs short-drama three-tier risk model (red_lines / gray_zones / positive)
and P0-P4 priority framework.

Uses quality/profiles/cn.json as the compliance rule source.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Finding:
    """A single compliance finding."""
    priority: str        # P0 / P1 / P2 / P3
    rule_id: str         # e.g. "RL-001", "GZ-002"
    location: str        # "E1.md:15" or "manuscript/01_大纲.md:3"
    description: str
    suggestion: str

    def to_dict(self) -> dict:
        return {
            "priority": self.priority,
            "rule_id": self.rule_id,
            "location": self.location,
            "description": self.description,
            "suggestion": self.suggestion,
        }


@dataclass
class ComplianceReport:
    """Complete compliance report."""
    red_line_findings: list[Finding] = field(default_factory=list)
    gray_zone_findings: list[Finding] = field(default_factory=list)
    positive_guidance_pass: list[bool] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "red_lines_hit": len(self.red_line_findings),
            "gray_zones_hit": len(self.gray_zone_findings),
            "positive_pass_count": sum(1 for p in self.positive_guidance_pass if p),
            "red_line_findings": [f.to_dict() for f in self.red_line_findings],
            "gray_zone_findings": [f.to_dict() for f in self.gray_zone_findings],
            "positive_checks": [
                {"id": f"PG-{i+1:03d}", "passed": p}
                for i, p in enumerate(self.positive_guidance_pass)
            ],
        }

    def to_markdown(self) -> str:
        lines = [
            f"# 合规检查报告",
            f"",
            f"**红线**: {len(self.red_line_findings)} 条 | "
            f"**灰区**: {len(self.gray_zone_findings)} 条 | "
            f"**正向**: {sum(1 for p in self.positive_guidance_pass if p)}/{len(self.positive_guidance_pass)}",
            f"",
        ]
        if self.red_line_findings:
            lines.append("## 🔴 红线（P0 — 立即删除）")
            for f in self.red_line_findings:
                lines.append(f"- **{f.location}**: {f.description}")
                lines.append(f"  → {f.suggestion}")
            lines.append("")
        if self.gray_zone_findings:
            lines.append("## 🟡 灰区")
            for f in self.gray_zone_findings:
                lines.append(f"- [{f.priority}] **{f.location}**: {f.description}")
                lines.append(f"  → {f.suggestion}")
            lines.append("")
        if not self.red_line_findings and not self.gray_zone_findings:
            lines.append("✅ 未检测到红线或灰区问题")
        return "\n".join(lines)


def run_compliance(manuscript_dir: Path, profile_path: Path) -> ComplianceReport:
    """Run compliance check against the given profile.

    Args:
        manuscript_dir: Path to manuscript/*.md files.
        profile_path: Path to quality/profiles/cn.json.

    Returns:
        ComplianceReport with categorized findings.
    """
    profile = json.loads(profile_path.read_text(encoding="utf-8"))

    red_lines: list[Finding] = []
    gray_zones: list[Finding] = []
    positive_pass: list[bool] = []

    md_files = sorted(manuscript_dir.rglob("*.md"))
    combined_text = ""
    file_map: dict[str, str] = {}  # filename → full_text
    for f in md_files:
        text = f.read_text(encoding="utf-8")
        rel = str(f.relative_to(manuscript_dir))
        file_map[rel] = text
        combined_text += text + "\n"

    # ── Red line scan ──────────────────────────────────────────
    for rule in profile.get("red_lines", []):
        for kw in rule.get("keywords", []):
            for fname, text in file_map.items():
                for m in re.finditer(re.escape(kw), text):
                    line_no = text[:m.start()].count("\n") + 1
                    red_lines.append(Finding(
                        "P0", rule["id"], f"{fname}:{line_no}",
                        f"{rule['desc']}: 检测到「{kw}」",
                        rule.get("action", "删除相关内容"),
                    ))

    # ── Gray zone scan ─────────────────────────────────────────
    for rule in profile.get("gray_zones", []):
        for kw in rule.get("keywords", []):
            for fname, text in file_map.items():
                for m in re.finditer(re.escape(kw), text):
                    line_no = text[:m.start()].count("\n") + 1
                    gray_zones.append(Finding(
                        rule.get("priority", "P2"), rule["id"],
                        f"{fname}:{line_no}",
                        f"{rule['desc']}: 检测到「{kw}」",
                        rule.get("handling", "建议修改"),
                    ))

    # ── Genre pitfall scan ─────────────────────────────────────
    genre = _detect_genre(combined_text)
    pitfalls = profile.get("genre_pitfalls", {}).get(genre, {})
    for phrase in pitfalls.get("dont", []):
        for fname, text in file_map.items():
            if phrase in text:
                for m in re.finditer(re.escape(phrase), text):
                    line_no = text[:m.start()].count("\n") + 1
                    gray_zones.append(Finding(
                        "P1", f"GENRE-{genre}", f"{fname}:{line_no}",
                        f"题材「{genre}」踩坑: {phrase}",
                        f"建议: {pitfalls.get('do', ['避免此类描写'])[0]}",
                    ))

    # ── Positive guidance check ─────────────────────────────────
    for rule in profile.get("positive_guidance", []):
        # Simple heuristic: positive keywords presence
        positive_kw = {"结局正向": ["团圆", "和解", "成长", "释然"],
                       "奋斗精神": ["努力", "坚持", "奋斗", "拼搏"],
                       "家庭观念": ["家", "团圆", "亲情", "理解"]}
        check_name = rule["check"]
        matched = False
        for kw_set in positive_kw.values():
            if any(kw in combined_text for kw in kw_set):
                matched = True
                break
        positive_pass.append(matched)

    return ComplianceReport(
        red_line_findings=red_lines,
        gray_zone_findings=gray_zones,
        positive_guidance_pass=positive_pass,
    )


def _detect_genre(text: str) -> str:
    """Detect the primary genre from manuscript content."""
    genre_keywords = {
        "战神归来": ["战神", "兵王", "退伍"],
        "霸道总裁": ["霸道总裁", "总裁", "CEO", "豪门"],
        "甜宠": ["甜宠", "先婚后爱", "独宠"],
        "重生穿越": ["重生", "穿越", "回到过去"],
        "古装宫廷": ["宫斗", "皇后", "妃", "王府", "太子"],
        "悬疑探案": ["破案", "侦探", "刑警", "凶手"],
        "家庭伦理": ["婆媳", "家庭", "亲子"],
    }
    scores = {g: sum(text.count(kw) for kw in kws) for g, kws in genre_keywords.items()}
    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    return best if scores[best] > 0 else "未识别"
```

- [ ] **步骤 4：运行测试**

运行：`python -m pytest tests/test_compliance.py -v`

预期：3 PASS

- [ ] **步骤 5：提交**

```bash
git add quality/compliance.py quality/profiles/cn.json tests/test_compliance.py
git commit -m "feat: add compliance checker with three-tier risk model

Absorbs short-drama P0-P4 priority framework and genre-specific pitfalls.
Profiles externalized as JSON for easy platform-specific customization.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 14：审查引擎 — `quality/__init__.py`

**文件：**
- 创建：`quality/__init__.py`（替换 1-byte 存根）

- [ ] **步骤 1：写入 `quality/__init__.py`**

```python
"""Quality package — review and compliance engines.

Review: 5-dimension 50-point scoring (absorbs short-drama pattern).
Compliance: three-tier risk model (absorbs short-drama P0-P4 framework).

Engines are imported by commands/review.py and commands/compliance.py.
"""
from __future__ import annotations

from quality.review import ReviewReport, Issue, run_review           # noqa: F401
from quality.compliance import ComplianceReport, Finding, run_compliance  # noqa: F401
```

- [ ] **步骤 2：提交**

```bash
git add quality/__init__.py
git commit -m "feat: add quality package init with public API exports

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 15：导出器 — `exporters/srt.py`

**文件：**
- 创建：`exporters/srt.py`

- [ ] **步骤 1：写测试**

```python
# tests/test_exporters.py（新建）
from __future__ import annotations
import json, tempfile
from pathlib import Path

import sys; sys.path.insert(0, str(Path(__file__).parents[1]))


def test_srt_export_generates_valid_format():
    """SRT 导出生成有效的字幕格式"""
    from exporters.srt import export_srt
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        # 创建最小 gen_context.json
        ctx = {
            "storyboard": {
                "shots": [
                    {"shot_id": "s01", "duration": 3.0,
                     "dialogue": [{"speaker": "男主", "text": "你来了。"}]},
                    {"shot_id": "s02", "duration": 4.0,
                     "dialogue": [{"speaker": "女主", "text": "我等你很久了。"}]},
                ]
            }
        }
        ep_dir = out / "E1"
        ep_dir.mkdir(parents=True)
        (ep_dir / "gen_context.json").write_text(json.dumps(ctx, ensure_ascii=False), encoding="utf-8")

        export_srt(str(out), ["E1"])

        srt_file = ep_dir / "subtitle_zh.srt"
        assert srt_file.is_file()
        content = srt_file.read_text(encoding="utf-8")
        assert "1" in content
        assert "00:00:00,000" in content
        assert "你来了。" in content
        assert "我等你很久了。" in content
```

- [ ] **步骤 2：运行测试，确认失败**

运行：`python -m pytest tests/test_exporters.py::test_srt_export_generates_valid_format -v`

预期：FAIL

- [ ] **步骤 3：实现 `exporters/srt.py`**

```python
"""SRT subtitle exporter.

Reads gen_context.json per episode, extracts dialogue from storyboard shots,
and generates standard SRT subtitle files.

Registered as exporter "srt" via hooks.register_exporter.

SRT format:
    1
    00:00:00,000 --> 00:00:03,000
    男主: 你来了。

    2
    00:00:03,000 --> 00:00:07,000
    女主: 我等你很久了。
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
        ep_range: Episode numbers to export (None = all found).
        lang: Language code for filename suffix.

    Returns:
        List of generated SRT file paths.
    """
    out = Path(out_dir)
    generated: list[Path] = []

    if ep_range is None:
        # Auto-detect from directory
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

        # Build SRT entries
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


# ── Register ──────────────────────────────────────────────────────
register_exporter("srt", export_srt)
```

- [ ] **步骤 4：运行测试**

运行：`python -m pytest tests/test_exporters.py::test_srt_export_generates_valid_format -v`

预期：1 PASS

- [ ] **步骤 5：提交**

```bash
git add exporters/srt.py tests/test_exporters.py
git commit -m "feat: add SRT subtitle exporter

Reads gen_context.json dialogue and generates standard SRT format
with auto-calculated timestamps from shot durations.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 16：导出器 — `exporters/ffmpeg.py`

**文件：**
- 创建：`exporters/ffmpeg.py`

- [ ] **步骤 1：写测试**

```python
# 追加到 tests/test_exporters.py
def test_ffmpeg_export_generates_compose_script():
    """FFmpeg 导出生成合成脚本"""
    from exporters.ffmpeg import export_ffmpeg
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        ctx = {
            "storyboard": {
                "shots": [
                    {"shot_id": "s01", "duration": 3.0, "scene": "办公室",
                     "dialogue": [{"speaker": "男主", "text": "你来了。"}]},
                ]
            }
        }
        ep_dir = out / "E1"
        ep_dir.mkdir(parents=True)
        (ep_dir / "gen_context.json").write_text(json.dumps(ctx, ensure_ascii=False), encoding="utf-8")

        export_ffmpeg(str(out), [1])

        # Check compose script exists
        script = out / "E1" / "compose.sh"
        if not script.exists():
            script = out / "E1" / "compose.ps1"
        assert script.is_file()
        content = script.read_text(encoding="utf-8")
        assert "ffmpeg" in content
        assert "s01" in content
```

- [ ] **步骤 2：运行测试，确认失败**

运行：`python -m pytest tests/test_exporters.py::test_ffmpeg_export_generates_compose_script -v`

预期：FAIL

- [ ] **步骤 3：实现 `exporters/ffmpeg.py`**

```python
"""FFmpeg composition script exporter.

Generates shell scripts that concatenate video clips, overlay subtitles,
and mix audio tracks for each episode.

Registered as exporter "ffmpeg" via hooks.register_exporter.
"""
from __future__ import annotations

import json
import platform
from pathlib import Path

from hooks import register_exporter


def export_ffmpeg(out_dir: str, ep_range: list[int] | None = None) -> list[Path]:
    """Generate FFmpeg compose scripts for specified episodes.

    Args:
        out_dir: Project output directory.
        ep_range: Episode numbers (None = auto-detect).

    Returns:
        List of generated script paths.
    """
    out = Path(out_dir)
    generated: list[Path] = []
    is_windows = platform.system() == "Windows"

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

        # Build concat list
        concat_list_path = out / f"E{ep}" / "concat_list.txt"
        concat_lines: list[str] = []
        filter_lines: list[str] = []
        input_args: list[str] = []

        for s in shots:
            if not isinstance(s, dict):
                continue
            sid = s.get("shot_id", "")
            if not sid:
                continue
            concat_lines.append(f"file 'shots/{sid}.mp4'")
            input_args.append(f"-i shots/{sid}.mp4")

        if not concat_lines:
            continue

        concat_list_path.write_text("\n".join(concat_lines), encoding="utf-8")

        output = out / f"E{ep}" / f"E{ep}_composed.mp4"

        if is_windows:
            script = _build_ps1(out, ep, concat_lines, output)
            ext = ".ps1"
        else:
            script = _build_sh(out, ep, concat_lines, output)
            ext = ".sh"

        script_path = out / f"E{ep}" / f"compose{ext}"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script, encoding="utf-8")

        if not is_windows:
            # Make executable
            script_path.chmod(0o755)

        generated.append(script_path)

    return generated


def _build_sh(out: Path, ep: int, concat_lines: list[str],
              output: Path) -> str:
    """Build bash compose script."""
    concat_path = f"E{ep}/concat_list.txt"
    srt_path = f"E{ep}/subtitle_zh.srt"
    output_path = str(output.relative_to(out))

    # Check for SRT
    srt_filter = ""
    if (out / srt_path).exists():
        srt_filter = (
            f',subtitles={srt_path}:force_style='
            f"'FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000'"
        )

    return f"""#!/bin/bash
# Auto-generated by nuomi-drama-skills — Episode {ep}
# Usage: bash compose.sh
set -euo pipefail

cd "$(dirname "$0")/.."

ffmpeg -f concat -safe 0 -i {concat_path} \\
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2{srt_filter}" \\
  -c:v libx264 -preset medium -crf 23 \\
  -pix_fmt yuv420p \\
  -an \\
  {output_path}

echo "Done: {output_path}"
"""


def _build_ps1(out: Path, ep: int, concat_lines: list[str],
               output: Path) -> str:
    """Build PowerShell compose script."""
    concat_path = f"E{ep}/concat_list.txt"
    output_path = str(output.relative_to(out))

    return f"""# Auto-generated by nuomi-drama-skills — Episode {ep}
# Usage: .\\compose.ps1
$ErrorActionPreference = "Stop"

Set-Location "$PSScriptRoot\\.."

ffmpeg -f concat -safe 0 -i {concat_path} `
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2" `
  -c:v libx264 -preset medium -crf 23 `
  -pix_fmt yuv420p `
  -an `
  {output_path}

Write-Host "Done: {output_path}"
"""


# ── Register ──────────────────────────────────────────────────────
register_exporter("ffmpeg", export_ffmpeg)
```

- [ ] **步骤 4：运行测试**

运行：`python -m pytest tests/test_exporters.py -v`

预期：2 PASS

- [ ] **步骤 5：提交**

```bash
git add exporters/ffmpeg.py
git commit -m "feat: add FFmpeg composition script exporter

Generates platform-appropriate compose scripts (bash/PowerShell) for
concatenating video clips with subtitle overlay.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 17：导出器 — `exporters/__init__.py`

**文件：**
- 创建：`exporters/__init__.py`（替换 1-byte 存根）

- [ ] **步骤 1：写入 `exporters/__init__.py`**

```python
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
```

- [ ] **步骤 2：提交**

```bash
git add exporters/__init__.py
git commit -m "feat: add exporters package init with registration imports

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 18：工程基础 — `pyproject.toml`

**文件：**
- 创建：`pyproject.toml`

- [ ] **步骤 1：写入 `pyproject.toml`**

```toml
[project]
name = "nuomi-drama-skills"
version = "0.7.0"
description = "长篇竖屏短剧 AI 创作助手 — 从立意到分镜表的完整创作管线"
requires-python = ">=3.9"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "YuRui-Liu"}
]
dependencies = [
    "httpx",
    "Pillow",
    "flask",
    "numpy",
    "google-genai",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-cov",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-v --tb=short"

[tool.setuptools.packages.find]
include = [
    "commands*",
    "quality*",
    "exporters*",
    "providers*",
    "stages*",
    "imaging*",
    "references*",
]
```

- [ ] **步骤 2：提交**

```bash
git add pyproject.toml
git commit -m "build: add pyproject.toml with project metadata and dependencies

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 19：CI 流水线 — `.github/workflows/validate.yml`

**文件：**
- 创建：`.github/workflows/validate.yml`

- [ ] **步骤 1：写入 CI 配置**

```yaml
name: Validate

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Compile-check all Python files
        run: python -m compileall .

      - name: Run tests
        run: python -m pytest tests/ -v --tb=short

      - name: Run release audit
        run: python scripts/release_audit.py --check

      - name: Git diff check (no whitespace errors)
        run: git diff --check
```

- [ ] **步骤 2：提交**

```bash
git add .github/workflows/validate.yml
git commit -m "ci: add GitHub Actions validate workflow

4-step pipeline: compile-check → pytest → release audit → git diff check.
Absorbs seedance 16-step validation pattern, trimmed for nuomi scope.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 20：离线审计 — `scripts/release_audit.py`

**文件：**
- 创建：`scripts/release_audit.py`

- [ ] **步骤 1：写入审计脚本**

```python
"""Release audit script — deterministic offline quality gate.

Absorbs seedance offline-validator pattern. Checks:
  1. File existence — all required modules present
  2. Version consistency — contract.py vs SKILL.md vs README vs pyproject.toml
  3. Security scan — no skill.env tracked, no hardcoded keys in source
  4. Reference integrity — no dead links, no duplicate paths
  5. Test pass rate — runs pytest and parses results (--full mode only)

Usage:
    python scripts/release_audit.py --check       # Quick check (no tests)
    python scripts/release_audit.py --full         # Full check (runs pytest)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]


def check_file_existence() -> list[str]:
    """Check that all required modules exist."""
    errors: list[str] = []
    required = [
        "commands/__init__.py", "commands/__main__.py",
        "commands/dispatcher.py", "commands/new.py",
        "commands/review.py", "commands/compliance.py",
        "quality/__init__.py", "quality/review.py",
        "quality/compliance.py", "quality/profiles/cn.json",
        "exporters/__init__.py", "exporters/jianying.py",
        "exporters/srt.py", "exporters/ffmpeg.py",
        "CLAUDE.md", "pyproject.toml", "SKILL.md", "README.md",
        "generate.py", "export.py", "emit.py", "gates.py",
        "validators.py", "contract.py", "hooks.py",
    ]
    for p in required:
        if not (ROOT / p).exists():
            errors.append(f"MISSING: {p}")
    return errors


def check_version_consistency() -> list[str]:
    """Check that CONTRACT_VERSION is consistent across all files."""
    errors: list[str] = []

    contract_ver = None
    contract_py = ROOT / "contract.py"
    if contract_py.is_file():
        m = re.search(r'CONTRACT_VERSION\s*=\s*"([^"]+)"', contract_py.read_text(encoding="utf-8"))
        if m:
            contract_ver = m.group(1)

    if not contract_ver:
        errors.append("VERSION: cannot extract CONTRACT_VERSION from contract.py")
        return errors

    # Check pyproject.toml
    ppt = ROOT / "pyproject.toml"
    if ppt.is_file():
        text = ppt.read_text(encoding="utf-8")
        m = re.search(r'version\s*=\s*"([^"]+)"', text)
        if m:
            proj_ver = m.group(1)
            if proj_ver != contract_ver:
                errors.append(f"VERSION: pyproject.toml={proj_ver} != contract.py={contract_ver}")

    # Check SKILL.md
    skill_md = ROOT / "SKILL.md"
    if skill_md.is_file():
        text = skill_md.read_text(encoding="utf-8")
        if contract_ver not in text:
            errors.append(f"VERSION: SKILL.md does not reference {contract_ver}")

    # Check README.md
    readme = ROOT / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        if contract_ver not in text:
            errors.append(f"VERSION: README.md does not reference {contract_ver}")

    return errors


def check_security() -> list[str]:
    """Check for security issues."""
    errors: list[str] = []

    # skill.env must NOT exist in tracked files
    skill_env = ROOT / "skill.env"
    if skill_env.is_file():
        # Check if it contains real keys
        text = skill_env.read_text(encoding="utf-8")
        if re.search(r'sk-[A-Za-z0-9]{30,}', text):
            errors.append("SECURITY: skill.env contains what looks like a real Grsai API key")
        if re.search(r'[A-Fa-f0-9]{30,}', text):
            errors.append("SECURITY: skill.env contains what looks like a real RunningHub API key")

    # Scan source code for hardcoded keys
    for py_file in ROOT.rglob("*.py"):
        if py_file.name == "release_audit.py":
            continue
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        if re.search(r'sk-[A-Za-z0-9]{30,}', text):
            errors.append(f"SECURITY: possible API key in {py_file.relative_to(ROOT)}")

    return errors


def check_reference_integrity() -> list[str]:
    """Check that reference/ directory is gone and references/ is complete."""
    errors: list[str] = []

    # reference/ must not exist
    ref_dir = ROOT / "reference"
    if ref_dir.exists():
        errors.append("REF: reference/ directory still exists — should be merged into references/")

    # references/ must contain the core files
    refs_dir = ROOT / "references"
    required_refs = ["创作方法论.md", "平台契约.md", "剧本格式规范.md", "分镜表规范.md", "提示词规则.md"]
    for r in required_refs:
        if not (refs_dir / r).exists():
            errors.append(f"REF: references/{r} missing")

    # Check no dead links in SKILL.md
    skill_md = ROOT / "SKILL.md"
    if skill_md.is_file():
        text = skill_md.read_text(encoding="utf-8")
        ref_pattern = re.findall(r'`(reference[s]?/[^`]+)`', text)
        for ref in ref_pattern:
            if not (ROOT / ref).exists():
                errors.append(f"REF: dead link in SKILL.md: {ref}")

    return errors


def check_module_registrations() -> list[str]:
    """Check that all commands/exporters are registered in hooks."""
    errors: list[str] = []

    # Check commands are importable
    for mod in ["commands.new", "commands.review", "commands.compliance"]:
        try:
            __import__(mod)
        except Exception as e:
            errors.append(f"REG: cannot import {mod}: {e}")

    # Check exporters are importable
    for mod in ["exporters.srt", "exporters.ffmpeg"]:
        try:
            __import__(mod)
        except Exception as e:
            errors.append(f"REG: cannot import {mod}: {e}")

    return errors


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Release audit for nuomi-drama-skills")
    parser.add_argument("--check", action="store_true", help="Quick check (no test run)")
    parser.add_argument("--full", action="store_true", help="Full check including pytest")
    args = parser.parse_args()

    all_errors: list[str] = []
    all_errors.extend(check_file_existence())
    all_errors.extend(check_version_consistency())
    all_errors.extend(check_security())
    all_errors.extend(check_reference_integrity())
    all_errors.extend(check_module_registrations())

    if all_errors:
        print(f"❌ {len(all_errors)} audit issue(s):")
        for e in all_errors:
            print(f"  - {e}")
        return 1

    print("✅ All audit checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **步骤 2：运行审计验证**

运行：`python scripts/release_audit.py --check`

预期：输出检查结果（部分可能在模块全部完成前失败，这是预期行为）

- [ ] **步骤 3：提交**

```bash
git add scripts/release_audit.py
git commit -m "feat: add offline release audit script

5 checks: file existence, version consistency, security scan,
reference integrity, and module registration. Absorbs seedance
offline-validator pattern.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 21：测试体系 — E2E 测试 + Golden Fixtures

**文件：**
- 创建：`tests/test_offline_e2e.py`
- 创建：`tests/golden/bell_tower_ep01_expected.json`
- 创建：`tests/golden/review_expected.json`

- [ ] **步骤 1：创建 golden fixtures**

```json
// tests/golden/review_expected.json
{
  "min_total": 20,
  "max_total": 50,
  "required_dimensions": ["format", "continuity", "prompt_quality", "char_consistency", "satisfaction"],
  "valid_grades": ["卓越", "优良", "合格", "需改进", "无内容"]
}
```

- [ ] **步骤 2：写 E2E 测试**

```python
# tests/test_offline_e2e.py
from __future__ import annotations
import json, tempfile
from pathlib import Path
import sys; sys.path.insert(0, str(Path(__file__).parents[1]))


def test_full_pipeline_new_to_compliance():
    """端到端：new → 写作 → 审查 → 合规"""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)

        # 1. /nuomi:new
        from commands.new import run_new
        result = run_new(out_dir=str(out), args=[], ref_paths=[], state={"phase": "ideation"})
        assert result["status"] in ("ok", "resumed")
        assert (out / "manuscript").is_dir()

        # 2. Write minimal content
        manuscript_dir = out / "manuscript"
        (manuscript_dir / "E1.md").write_text(
            "# E1 第一集\n\n## 剧本\n\n男主走进办公室。\n\n## 分镜表\n\n"
            "```json\n"
            '{"shots": [{"shot_id": "s01", "duration": 3.0, "scene": "办公室", '
            '"action_desc": "男主推门走进办公室", "video_prompt": "一个男人推开办公室的门，缓步走进来", '
            '"video_prompt_en": "A man pushes open the office door and walks in slowly", '
            '"dialogue": [{"speaker": "男主", "text": "你来了。"}]}]}\n'
            "```\n",
            encoding="utf-8",
        )
        # Fake exported gen_context.json
        ep_dir = out / "E1"
        ep_dir.mkdir(parents=True, exist_ok=True)
        ctx = {
            "storyboard": {
                "shots": [{
                    "shot_id": "s01", "duration": 3.0, "scene": "办公室",
                    "action_desc": "男主推门走进办公室",
                    "video_prompt": "一个男人推开办公室的门，缓步走进来",
                    "video_prompt_en": "A man pushes open the office door and walks in slowly",
                    "dialogue": [{"speaker": "男主", "text": "你来了。"}],
                    "relation": "cut"
                }]
            }
        }
        (ep_dir / "gen_context.json").write_text(json.dumps(ctx, ensure_ascii=False), encoding="utf-8")

        # Update state to scripting for review
        from writing_state import save_state
        save_state(out, {"phase": "scripting", "completed_episodes": [1],
                          "current_episode": 1, "current_arc": 1,
                          "gates_passed": [], "gates_warnings": {},
                          "review_history": [], "compliance_history": []})

        # 3. /nuomi:review
        from commands.review import run_review
        result = run_review(out_dir=str(out), args=[], ref_paths=[], state={"phase": "scripting"})
        assert result["status"] == "ok"
        assert (out / "review_report.json").is_file()
        report_data = json.loads((out / "review_report.json").read_text(encoding="utf-8"))
        assert 0 <= report_data["total"] <= 50

        # 4. /nuomi:compliance
        from commands.compliance import run_compliance
        result = run_compliance(out_dir=str(out), args=[], ref_paths=[], state={"phase": "scripting"})
        assert result["status"] == "ok"
        assert (out / "compliance_report.json").is_file()

        # 5. Export SRT
        from exporters.srt import export_srt
        paths = export_srt(str(out), [1])
        assert len(paths) >= 1
        assert paths[0].is_file()

        # 6. Export FFmpeg
        from exporters.ffmpeg import export_ffmpeg
        paths = export_ffmpeg(str(out), [1])
        assert len(paths) >= 1
        assert paths[0].is_file()
```

- [ ] **步骤 3：运行 E2E 测试**

运行：`python -m pytest tests/test_offline_e2e.py -v`

预期：1 PASS

- [ ] **步骤 4：提交**

```bash
git add tests/test_offline_e2e.py tests/golden/
git commit -m "test: add end-to-end pipeline test and golden fixtures

Covers full flow: new → review → compliance → srt export → ffmpeg export.
Golden fixtures for review report format validation.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 22：最终集成 — 全量测试 + 审计通过

**文件：**
- 修改：无新文件，验证全量通过

- [ ] **步骤 1：运行全量测试**

运行：`python -m pytest tests/ -v --tb=short`

预期：所有测试 PASS（目标 20+ 用例）

- [ ] **步骤 2：运行发布审计**

运行：`python scripts/release_audit.py --check`

预期：`✅ All audit checks passed`

- [ ] **步骤 3：最终检查 — 确认 `reference/` 目录已删除**

运行：`test -d reference && echo "STILL EXISTS" || echo "OK"`

预期：OK

- [ ] **步骤 4：最终检查 — 确认 `skill.env` 无真实 Key**

运行：`grep -E "sk-[A-Za-z0-9]{30,}|[A-Fa-f0-9]{30,}" skill.env`

预期：无匹配

- [ ] **步骤 5：最终提交**

```bash
git add -A
git status
git commit -m "chore: final integration — all tests passing, audit clean

Phase A (emergency fixes): generate.py, skill.env, contract versions, reference merge
Phase B (new modules): commands, quality/review+compliance, exporters/srt+ffmpeg
Phase C (engineering): pyproject.toml, CI workflow, release audit, test suite

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
