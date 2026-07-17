# nuomi-drama-skills 全面修复与优化 — 设计规格

> 状态：已审批  
> 日期：2026-07-16  
> 方案：B — 模式注入式补全  
> 参考项目：Micro-Drama-Skills-main, seedance-2.0-main, short-drama-main

---

## 1. 动机与范围

### 现状问题

nuomi-drama-skills 是一个 Python + Markdown 的 AI 短剧创作技能项目。四项目深度调研发现三项严重阻断性问题和系统性完成度不足：

| 层级 | 问题 | 位置 |
|------|------|------|
| 🔴 阻断 | `_episode_count` 函数缺失导致 CLI 崩溃 | `generate.py` |
| 🔴 阻断 | `_dry_run_dub()` 含孤立死代码 | `generate.py:152-155` |
| 🔴 安全 | 真实 API Key 暴露在已提交的 `skill.env` | 根目录 |
| 🟡 高 | 契约版本不一致（4 处 `2026-06-18` vs 实际 `2026-06-20`） | `SKILL.md`, `USER_GUIDE.md`, `names.py` |
| 🟡 高 | `reference/` vs `references/` 双目录 + 死链 | 多处 |
| 🟡 高 | 15+ 个计划模块缺失（commands/、quality/、exporters/、tests/、CLAUDE.md、pyproject.toml 等） | 全局 |
| 🟡 中 | 空目录残留（`modes/`、`commands/`、`quality/` 等） | 多处 |

### 范围

本规格覆盖：
- **阶段 A**：6 项紧急修复（bug + 安全 + 版本一致性）
- **阶段 B**：4 个新模块域（命令系统、审查引擎、导出器、测试体系 + CI）
- **阶段 C**：工程基础设施补全

本规格不改动已有工作代码（`providers/`、`stages/`、`gates.py`、`export.py`、`emit.py`、`validators.py` 等保持不变）。

### 非范围

- API Key 轮换（需用户在对应平台操作，本文档仅提供指引）
- `modes/` 目录的利用（标记为未来预留，本次不删除）
- 现有 `stages/`、`providers/` 的功能变更

---

## 2. 吸收的外部模式

从三个参考项目中，为 nuomi 的缺失模块注入以下经过验证的模式：

| 来源 | 吸收模式 | 注入位置 |
|------|---------|---------|
| seedance-2.0 | 渐进披露加载映射表 | `SKILL.md` 新增 Load Map 章节 |
| seedance-2.0 | 源日期事实标注 | `references/平台契约.md` 补充 `last_verified` 字段 |
| seedance-2.0 | 快速通道 + 门控路由 | `commands/dispatcher.py` |
| seedance-2.0 | 离线验证脚本 | `scripts/release_audit.py` |
| short-drama | JSON 状态机命令系统 | `commands/dispatcher.py` + `writing_state.json` 扩展 |
| short-drama | 5×10 多维度评分审查 | `quality/review.py` |
| short-drama | P0-P4 合规优先级框架 | `quality/compliance.py` + `profiles/cn.json` |
| short-drama | 按需上下文加载矩阵 | `commands/dispatcher.py` 内建映射表 |
| Micro-Drama | `visual_styles.json` 风格注入理念 | `references/` 文档化（非代码变更） |
| Micro-Drama | composite+crop 策略 | `references/` 文档化（非代码变更） |

---

## 3. 阶段 A：紧急修复

### 3.1 修复 `generate.py` — `_episode_count` 缺失

**根因**：重构时将原本 `main()` 中的内联逻辑（读 `series.json` → 统计有/无剧本的 episode）错误地片段化粘贴到 `_dry_run_dub()` 函数体内，且遗漏了完整的函数定义。

**修复**：
1. 在 `_dry_run_dub()` 之前（约第 150 行之前）插入完整的 `_episode_count` 函数定义
2. 删除 `_dry_run_dub()` 内第 152-155 行的孤儿代码片段
3. `_episode_count` 签名：`def _episode_count(out_dir: str) -> tuple[int, int]`，返回 `(with_script, skeleton_only)`

### 3.2 安全清理 — `skill.env` API Key 暴露

- 当前 `.gitignore` 已包含 `skill.env`，但文件在添加前已提交
- **仓库内操作**：将 `skill.env` 中的 Key 值替换为占位符
- **用户需执行**：在 Grsai 和 RunningHub 平台轮换 Key（本文档提供平台链接指引）

### 3.3 契约版本一致性

统一为 `2026-06-20`：

```
contract.py:            CONTRACT_VERSION = "2026-06-20"     [不变]
SKILL.md:250            更正 "2026-06-18" → "2026-06-20"
docs/USER_GUIDE.md:     更正头部 "2026-06-18" → "2026-06-20"
names.py:               更正 docstring "@ CONTRACT 2026-06-18" → "2026-06-20"
```

### 3.4 合并 `reference/` + `references/` → 统一 `references/`

- 将 `reference/` 中 5 个文件移入 `references/`
- 删除空目录 `reference/`
- 更新 `README.md`、`SKILL.md`、`docs/USER_GUIDE.md` 中所有引用路径

### 3.5 清理 `skill.env` 默认模型名

`skill.env` 使用 `gpt-image-2`（无 `-vip` 后缀），与 `skill.env.example` 和代码默认值不一致。修正为 `gpt-image-2-vip`。

### 3.6 补充 `CLAUDE.md`

写入项目约定文件，包含：
- 架构概览
- 技能触发条件（短剧、微短剧、AI 漫剧等关键词）
- 核心不变原则（Manuscript as Source of Truth）
- 工作流阶段说明
- Provider 配置指引

---

## 4. 阶段 B — 命令系统

### 4.1 架构

```
用户 /nuomi:<command> [args]
  → commands/__main__.py           (python -m 入口)
  → commands/dispatcher.py         (中央路由器)
    ├─ Load Gate: 读取 writing_state.json + 前置条件验证
    ├─ Route Gate: 门控检查（阶段不匹配 → 阻断 + 建议下一步）
    ├─ Context Load: 按需加载 references/（加载映射表）
    └─ Dispatch: → commands/{command}.py
```

### 4.2 三条命令合约

| 命令 | 前置条件 | 加载的 References | 输出 |
|------|---------|------------------|------|
| `/nuomi:new` | 无（新项目）或已有 state（恢复模式） | `创作方法论.md`, `templates/` | `manuscript/` 骨架 + `writing_state.json` |
| `/nuomi:review` | `state.phase >= "scripting"` | `分镜表规范.md`, `提示词规则.md` | 审查报告 `{out_dir}/review_report.json` + `.md` |
| `/nuomi:compliance` | 内容存在（任意阶段） | `平台契约.md`, `quality/profiles/cn.json` | 合规报告 `{out_dir}/compliance_report.json` + `.md` |

### 4.3 加载映射表（dispatcher.py 内建）

```python
COMMAND_REFERENCES = {
    "new":        ["创作方法论.md"],
    "review":     ["分镜表规范.md", "提示词规则.md"],
    "compliance": ["平台契约.md"],
}
```

### 4.4 与现有 hooks.py 的关系

- `hooks.py` 保留不动 — 作为底层注册表（`register_command` / `on_command`）
- `commands/dispatcher.py` 是高层封装：加入门控、前置检查、上下文加载
- 命令模块在 `commands/__init__.py` 中通过 `hooks.register_command()` 注册（沿用 `quality/gate_g2.py` 注册 `"pre_generate"` 的模式）

### 4.5 writing_state.json 扩展

在现有状态机字段基础上增加：

```json
{
  "current_command": "new|review|compliance|null",
  "last_command_at": "ISO8601",
  "review_history": [
    { "at": "ISO8601", "total": 42, "grade": "优良" }
  ],
  "compliance_history": [
    { "at": "ISO8601", "red_lines_hit": 0, "gray_zones_hit": 2 }
  ]
}
```

---

## 5. 阶段 B — 审查引擎

### 5.1 review.py — 多维度评分引擎

吸收 short-drama 的 5 维度 50 分制，映射到 nuomi 生成管线语境：

| 维度 | 满分 | 检查方式 | 复用 |
|------|------|---------|------|
| 剧本格式 | 10 | Markdown 结构 + JSON fence 合法性 | `validators.py` |
| 分镜连贯 | 10 | shot_id 无重复、relation 枚举正确、跨场逻辑 | `validators.py` + gates G3/G4 |
| 提示词质量 | 10 | LTX prompt 合规、双语规范、长度上限 | `prompt_checker.py` + gate G2 |
| 角色一致性 | 10 | 人物名标准化、bible 交叉引用 | `names.py` + gate G1 |
| 爽点节奏 | 10 | 钩子密度、爽点分布、付费卡点 | ✨ 新增分析器 |

输出合约：

```python
@dataclass
class ReviewReport:
    scores: dict[str, int]         # {"format": 9, "continuity": 7, ...}
    total: int                      # 0-50
    grade: str                      # "卓越" / "优良" / "合格" / "需改进"
    highlights: list[str]
    issues: list[Issue]

@dataclass
class Issue:
    severity: str   # "⛔阻断" / "⚠️建议" / "ℹ️微调"
    dimension: str
    location: str   # "ep01:shot03" or "稿件:行号"
    description: str
    suggestion: str
```

### 5.2 compliance.py — 合规检查器

吸收 short-drama 三层风险模型 + P0-P4 优先级：

```
red_lines   → P0 立即删除
gray_zones  → P1 必须修改 / P2 建议优化
positive    → P3 锦上添花
```

### 5.3 profiles/cn.json — 合规配置

JSON 配置文件，包含：
- `red_lines`：涉政隐喻、色情描写等绝对禁止项
- `gray_zones`：暴力场面、敏感职业等可处理项（含处理方式指引）
- `positive_guidance`：正向价值观检查规则
- `genre_pitfalls`：按题材划分的踩坑清单（吸收 short-drama 7 种题材）

---

## 6. 阶段 B — 导出器

### 6.1 srt.py — SRT 字幕导出

```
输入：registry.json (dub 文件列表) + gen_context.json (对话文本)
输出：episodes/ep{N}_subtitle_{lang}.srt
逻辑：per-shot 默认 3-5s，按 shot 序列累加时间轴
```

### 6.2 ffmpeg.py — FFmpeg 合成脚本

```
输入：registry.json (视频 + 配音 + 字幕)
输出：compose.sh / compose.ps1
逻辑：按 episode 分组 → concat filter → 字幕 overlay → 输出
```

### 6.3 注册模式

导出器在 `exporters/__init__.py` 中通过 `hooks.register_exporter()` 注册（沿用 `jianying.py` 的注册模式）。

---

## 7. 阶段 C — 测试体系

### 7.1 测试文件

| 文件 | 测试目标 | 预估用例 |
|------|---------|---------|
| `tests/test_dispatcher.py` | 命令路由、门控逻辑、前置条件验证 | 8+ |
| `tests/test_command_new.py` | /nuomi:new 创建 + 恢复流程 | 6+ |
| `tests/test_review.py` | 审查引擎 5 维度评分正确性 | 10+ |
| `tests/test_compliance.py` | 合规红线/灰区/正向检测 | 8+ |
| `tests/test_offline_e2e.py` | new → 编译 → 审查 → 合规 → 导出 | 3+ |
| `tests/golden/` | 黄金测试夹具 | 若干 |

### 7.2 目标覆盖率

- `commands/` → 85%+（纯逻辑）
- `quality/` → 90%+（规则明确）
- `exporters/` → 80%+（格式固定）

---

## 8. 阶段 C — CI + 工程基础

### 8.1 pyproject.toml

```toml
[project]
name = "nuomi-drama-skills"
version = "0.7.0"
requires-python = ">=3.9"
dependencies = ["httpx", "Pillow", "flask", "numpy", "google-genai"]

[project.optional-dependencies]
dev = ["pytest", "pytest-cov"]
```

### 8.2 .github/workflows/validate.yml

吸收 seedance 16 步验证模式，裁剪为：
1. `python -m compileall .`
2. `python -m pytest tests/ -v --tb=short`
3. `python scripts/release_audit.py --check`
4. `git diff --check`

### 8.3 scripts/release_audit.py

离线验证脚本，执行 5 项检查：
1. **文件存在性**：commands/、quality/、exporters/ 模块完整
2. **版本一致性**：contract.py vs SKILL.md vs README vs pyproject.toml
3. **安全扫描**：skill.env 未跟踪、无硬编码密钥
4. **Reference 完整性**：无死链、无重复
5. **测试通过率**：运行 pytest 并解析结果

---

## 9. 文件清单总览

### 修改的文件（5 个）

| 文件 | 变更 |
|------|------|
| `generate.py` | 修复 `_episode_count` + 删除孤儿代码 |
| `SKILL.md` | 更新契约版本 + 新增 Load Map 章节 |
| `README.md` | 更新路径引用 + 版本号 |
| `docs/USER_GUIDE.md` | 更新契约版本 |
| `names.py` | 更新 docstring 契约版本 |

### 新增的文件（22 个）

| 文件 | 阶段 |
|------|------|
| `CLAUDE.md` | A |
| `commands/__init__.py` | B |
| `commands/__main__.py` | B |
| `commands/dispatcher.py` | B |
| `commands/new.py` | B |
| `commands/review.py` | B |
| `commands/compliance.py` | B |
| `quality/__init__.py` | B |
| `quality/review.py` | B |
| `quality/compliance.py` | B |
| `quality/profiles/cn.json` | B |
| `exporters/__init__.py` | B |
| `exporters/srt.py` | B |
| `exporters/ffmpeg.py` | B |
| `tests/test_dispatcher.py` | C |
| `tests/test_command_new.py` | C |
| `tests/test_review.py` | C |
| `tests/test_compliance.py` | C |
| `tests/test_offline_e2e.py` | C |
| `tests/golden/` (目录 + 夹具) | C |
| `scripts/release_audit.py` | C |
| `pyproject.toml` | C |
| `.github/workflows/validate.yml` | C |

### 删除/移动

| 操作 | 目标 |
|------|------|
| `reference/` → `references/` | 5 个文件移动 |
| 删除 `reference/` | 空目录 |
| `skill.env` 敏感值替换 | 7 个 Key 占位符化 |

---

## 10. 风险与缓解

| 风险 | 缓解 |
|------|------|
| `_episode_count` 恢复后签名不兼容 | 审查所有调用处（3 处），确保返回 tuple 解包正确 |
| 新命令系统与现有 hooks.py 冲突 | 新系统封装 hooks 而非替代，`__init__.py` 中注册采用相同 API |
| 审查引擎评分标准主观 | 复用已有 `validators.py` + `prompt_checker.py` 的客观规则，新增维度有明确判定标准 |
| 依赖 `pyproject.toml` 后安装方式变更 | 同时保留 README 中的手动安装说明 |
| `reference/` 移动后内部引用遗漏 | `release_audit.py` 自动校验 + grep 全量扫描 |
