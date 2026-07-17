# nuomi-drama-skills · 长篇短剧创作操作系统

从立意到分镜表，落成 `manuscript/*.md`，经 `export.py` 确定性编译成可导入糯米短剧平台的项目文件夹。

**Contract Version** `2026-06-20` · **Python** 3.9+

---

## 概览 / Overview

nuomi-drama-skills 是一个 Claude Code 技能，引导创作者完成**长篇竖屏短剧**的全流程创作。覆盖从立意构思到最终交付的完整链路：

**创作阶段** — 立意 → 三轴（题材×风格×基调）→ 大纲 → 角色/场景/道具/世界观/伏笔五表圣经 → 分卷节拍表 → 逐集剧本 → 逐集分镜表，全部产出人类可读的 `manuscript/*.md`。

**编译阶段** — `export.py` 将手稿确定性编译为平台 JSON（`series.json` / `arcs.json` / `story_bible.json` / `E{n}/gen_context.json` / `assets/registry.json` / `harness_state.json`），编译幂等且并入安全。

**生成阶段** — `generate.py` 通过多 Provider 后端完成图片（宫格出图+超分裁切+9:16 归一）、视频（LTX 分组生成）、配音（TTS+声音克隆）和音色设计，产物写入平台兼容路径，可直接导入糯米短剧平台。

**预览阶段** — `preview_server.py` 启动 Flask 本地服务器，浏览器逐镜预览分镜表，三态标记（有图/缺图/未出图）。

---

## 架构 / Architecture

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
   generate.py ────── provider_chain.py
  (images/video/dub/voice_design)
       │
       ▼
   preview_server.py ── 浏览器预览
       │
       ▼
   exporters/jianying.py ── 剪映草稿导出
```

### 数据流铁律

- `manuscript/*.md` 是唯一创作事实源，手稿改，JSON 跟。
- 编译是幂等且并入安全的——重复编译不丢失平台已生成的产物（`episode_digests`、锚图、`shots_assets`、`anchors`、`audio` 等）。
- 永不手改 JSON——手改会在下次编译被手稿覆盖，也会和平台运行态打架。

---

## 核心特性 / Key Features

- **三阶段创作方法论**：立意 → 大纲 → 五表圣经 → 分卷节拍表，配合批判环（提问→起草→批判→迭代），保证上游高杠杆件质量。
- **结构化剧本+分镜表批量产集**：骨架锁定后逐集自动生成，每集自带 `## 剧本` + `## 分镜表` JSON，单集 90-180s / 15-30 镜。
- **8 门控质量关卡（G1-G8）**：G1-G4 为创作软提醒（不过可继续但告知风险），G5-G8 为生成硬阻断（不过不能进生成），复用 `validators.py` + `prompt_checker.py`。
- **确定性编译管道**：幂等、并入安全、校验不过不落盘——大纲/分镜/节拍任一失败即报错拒绝写入，杜绝脏数据。
- **四 Provider 后端**：Grsai（GPT Image 2）/ Gemini（Imagen 4.0）/ ComfyUI（本地）/ RunningHub（云端工作流），`IMAGE_PROVIDER` 环境变量一键切换。
- **宫格出图 + RunningHub 超分裁切 + 9:16 归一**：叙事组统一走宫格路径——宫格大图 → RunningHub 多宫格高清放大裁切 workflow 高清拆分（或本地拆分）→ Pillow 去边 → 单镜 JPG。`GRID_TARGET_ASPECT=9:16`。
- **LTX 视频分组生成 + TTS 配音 + 声音克隆**：按叙事组分镜发视频任务，对白镜自动 TTS 配音，支持声音克隆（`RUNNINGHUB_DUB_CLONE_WORKFLOW_ID`）。
- **题材特定参数自动注入**：从 `templates/genres/<genre_id>.yaml` 加载风格/色调/基调/生成护栏，自动注入分镜提示词。
- **Provider 容灾降级链**：按角色分离——锚图（角色/场景/道具）和分镜首帧各可指定主/备 provider（`IMAGE_PROVIDER_ANCHOR` / `IMAGE_PROVIDER_ANCHOR_FALLBACK` / `IMAGE_PROVIDER_SHOT` / `IMAGE_PROVIDER_SHOT_FALLBACK`）。
- **导演引擎 5 判决协议**：`director.py` 的 `ShootProtocol` 对每镜出图结果做 KEEP / FIX / EDIT / REGEN / REWRITE 五级判决，每镜最多 5 次尝试预算。
- **Flask 预览服务器**：`preview_server.py` 启动本地 Web 服务，浏览器逐镜预览分镜表，三态标记（已出图 ✓ / 缺失 ✗ / 未出图 ○），支持资源库查看。
- **剪映草稿导出**：`exporters/jianying.py` 产出剪映 JSON 草稿，含视频轨道、音频轨道和字幕轨道。

---

## 快速开始 / Quick Start

### Step 1: 安装技能

将 `nuomi-drama-skills/` 目录放入你的 Claude Code 技能的 `.claude/skills/` 下：

```bash
cp -r nuomi-drama-skills /path/to/your-project/.claude/skills/
```

### Step 2: 配置凭据

```bash
cp skill.env.example skill.env
```

编辑 `skill.env`，根据你使用的 Provider 填入 API Key。最小配置（仅 Grsai 出图）：

```ini
IMAGE_PROVIDER=grsai
GRSAI_API_KEY=sk-...
```

如需出视频/配音，额外配置 RunningHub：

```ini
RUNNINGHUB_API_KEY=rh-...
RUNNINGHUB_VIDEO_WORKFLOW_ID=<LTX 视频 workflow ID>
RUNNINGHUB_DUB_WORKFLOW_ID=<TTS 配音 workflow ID>
```

### Step 3: 触发技能

在 Claude Code 会话中触发技能：

> "帮我创作一部短剧"

或使用任何触发词：长篇短剧、分卷、节拍表、剧本圣经、批量产集。

### Step 4: 跟随引导工作流

技能会按三阶段方法轮引导你：
1. **引导档**：立意 → 三轴 → 大纲 → 五表圣经 → 分卷节拍表（一步一件、慢工出细活）
2. **批量档**：逐集生成剧本 + 分镜表
3. **导出交付**：`python export.py manuscript/ out/`

---

## CLI 参考 / CLI Reference

### `export.py` — 确定性编译

```bash
python export.py <manuscript_dir> <out_project_dir> [--jianying]
```

将手稿目录编译为平台 JSON 项目文件夹。`--jianying` 同时导出剪映草稿。校验失败不落盘。

### `generate.py` — 图片生成

```bash
python generate.py images E1-E3 --out ./out [--force] [--dry-run] [--only s3,s7] [--solo] [--retry-failed] [--json]
```

按叙事组走宫格路径出分镜首帧。选项：

| 选项 | 说明 |
|------|------|
| `--force` | 覆盖已有产物 |
| `--dry-run` | 只打印计划，不发 API |
| `--only s3,s7` | 只出指定镜号 |
| `--solo` | 逐镜单独出（不走宫格合并） |
| `--retry-failed` | 重试 `generate_log.json` 中的失败项 |
| `--json` | JSON 格式输出 |

### `generate.py` — 视频生成

```bash
python generate.py video E1 --out ./out [--force] [--dry-run]
```

按叙事组调用 LTX 视频生成 workflow。默认需首帧就绪（G7 硬阻断）。

### `generate.py` — 配音生成

```bash
python generate.py dub E1-E3 --out ./out [--force] [--dry-run]
```

为有对白的镜头生成 TTS 配音，支持声音克隆。

### `generate.py` — 音色设计

```bash
python generate.py voice_design --out ./out [--force]
```

为角色设计专属音色，产出音色参考文件。

### `generate.py` — 状态查询

```bash
python generate.py status E1-E3 --out ./out [--json]
```

诊断指定集的出图/出视频/配音完成状态。

### `preview_server.py` — 本地预览

```bash
python preview_server.py <out_project_dir> [--port 7788]
```

启动 Flask 服务器，浏览器打开 `http://localhost:7788` 逐镜预览分镜表。

---

## Provider 配置 / Provider Configuration

| 环境变量 | 说明 | 默认值 |
|---|---|---|
| `IMAGE_PROVIDER` | 图片 Provider：`grsai` / `gemini` / `comfyui` / `runninghub` | `grsai` |
| `GEMINI_API_KEY` | Gemini API 密钥 | - |
| `GEMINI_MODEL` | Gemini 图片模型 | `imagen-4.0-generate-001` |
| `GRSAI_API_KEY` | Grsai API 密钥 | - |
| `GRSAI_BASE_URL` | Grsai 服务地址 | `https://grsai.dakka.com.cn` |
| `GRSAI_IMAGE_MODEL` | Grsai 图片模型 | `gpt-image-2-vip` |
| `COMFYUI_BASE_URL` | ComfyUI 本地地址 | `http://localhost:8188` |
| `COMFYUI_WORKFLOW_ID` | ComfyUI 文生图 workflow UUID | - |
| `RUNNINGHUB_API_KEY` | RunningHub API 密钥 | - |
| `RUNNINGHUB_BASE_URL` | RunningHub 服务地址 | `https://www.runninghub.cn` |
| `RUNNINGHUB_IMAGE_WORKFLOW_ID` | 文生图 workflow ID | - |
| `RUNNINGHUB_VIDEO_WORKFLOW_ID` | LTX 视频 workflow ID | - |
| `RUNNINGHUB_DUB_WORKFLOW_ID` | TTS 配音 workflow ID | - |
| `RUNNINGHUB_UPSCALE_WORKFLOW_ID` | 多宫格高清放大裁切 workflow ID | - |
| `RUNNINGHUB_VOICE_DESIGN_WORKFLOW_ID` | 音色设计 workflow ID | - |
| `RUNNINGHUB_DUB_CLONE_WORKFLOW_ID` | 克隆配音 workflow ID | - |
| `RUNNINGHUB_MAX_PARALLEL` | RunningHub 任务并发数 | `3` |

### Provider 容灾（按角色分离）

| 环境变量 | 说明 | 默认值 |
|---|---|---|
| `IMAGE_PROVIDER_ANCHOR` | 锚图（角色/场景/道具）主 Provider | 沿用 `IMAGE_PROVIDER` |
| `IMAGE_PROVIDER_ANCHOR_FALLBACK` | 锚图备选 Provider | `gemini` |
| `IMAGE_PROVIDER_SHOT` | 分镜首帧主 Provider | 沿用 `IMAGE_PROVIDER` |
| `IMAGE_PROVIDER_SHOT_FALLBACK` | 分镜首帧备选 Provider | `gemini` |

### 宫格参数

| 环境变量 | 说明 | 默认值 |
|---|---|---|
| `GRID_TARGET_ASPECT` | 目标宽高比 | `9:16` |
| `GRID_UPSCALE_SHOTS_THRESHOLD` | 走超分裁切的最少镜数阈值 | `2` |
| `GRID_CANVAS_MODE` | 宫格画布模式：`economy` / `precise` | `economy` |
| `GRID_IMAGE_MODEL` | 宫格图所用的模型 | `gpt-image-2` |
| `IMAGE_WIDTH` | 单图宽度 | `768` |
| `IMAGE_HEIGHT` | 单图高度 | `1344` |
| `POLL_INTERVAL_S` | 异步任务轮询间隔（秒） | `5` |
| `POLL_TIMEOUT_S` | 异步任务超时（秒） | `300` |

---

## 门控系统 / Gate System

8 个质量关卡贯穿创作到生成的完整链路。软提醒不过可继续但需知风险；硬阻断不过必须修完才能进生成。

| Gate | 名称 | 阶段 | 阻断? | 触发时机 | 校验内容 |
|------|------|------|-------|----------|----------|
| G1 | 三轴一致性 | 立意后 | 软 | export / 推进到大纲前 | genre_id 命中注册表，style_id 命中，基调四维全齐 + arc 合法 |
| G2 | 大纲完整性 | 大纲后 | 软 | export / 推进到圣经前 | episodes 数组完整，每集必填字段（ep / 标题 / 梗概 / 钩子 / 爽点） |
| G3 | 圣经非空 | 角色/场景后 | 软 | export / 推进到节拍前 | 角色 / 场景 / 道具 / 世界观 / 伏笔五表非空 |
| G4 | 节拍表校验 | 分卷后 | 软 | export / 推进到剧本前 | 目标集在卷内，thread/伏笔已声明，节拍递增不倒序 |
| G5 | 分镜规范 | 分镜表后 | 硬 | generate images 前 | shot/group 必填字段，relation 合法，交叉引用一致 |
| G6 | 提示词质量 | 分镜表后 | 硬 | generate video 前 | video_prompt 无抽象情绪 / 无文本 Logo / 无冲突光照 |
| G7 | 首帧完整 | 出图后 | 硬 | generate video 前 | 所有镜 JPG 首帧存在 |
| G8 | Provider 健康 | 生成前 | 硬 | 每次 provider 调用前 | API key 完整，workflow ID 配置，连通性预检 |

运行全部 gate：

```bash
python -c "from gates import run_all_gates; from pathlib import Path; \
  results = run_all_gates(Path('manuscript'), Path('out'), 'all'); \
  [print(f'{r.gate_name}: {\"PASS\" if r.passed else \"FAIL\"}') for r in results]"
```

---

## 项目结构 / Project Structure

```
nuomi-drama-skills/
├── SKILL.md                     # 技能入口：方法论 + 工作流 + 检查表
├── README.md                    # 本文件
├── contract.py                  # CONTRACT_VERSION = "2026-06-20"
├── skill.env.example            # 环境变量模板
│
├── export.py                    # 确定性编译器：manuscript/*.md → 平台 JSON
├── emit.py                      # JSON 发射器
├── manuscript_parse.py          # 手稿解析器（Markdown → 结构化数据）
├── validators.py                # 冻结校验器（大纲/分镜/节拍/三轴）
├── writing_state.py             # 创作进度状态机（会话恢复）
│
├── generate.py                  # 独立生成 CLI（images/video/dub/voice_design/status）
├── provider_chain.py            # Provider 容灾降级链（按角色分离）
├── director.py                  # 导演引擎 5 判决协议
├── gates.py                     # G1-G8 门控函数
├── prompt_checker.py            # LTX 2.3 提示词质量校验
├── genre_params.py              # 题材特定参数加载器
├── names.py                     # 角色名规范化
│
├── preview_server.py            # Flask 分镜预览服务器
├── hooks.py                     # on_command / on_gate / on_export 钩子
├── styles_table.py              # 风格参数表
│
├── providers/                   # Provider 后端适配层
│   ├── __init__.py              # load_config / get_*_provider 工厂
│   ├── base.py                  # ImageProvider / GridUpscaleProvider 抽象
│   ├── grsai.py                 # Grsai（GPT Image 2）适配器
│   ├── gemini.py                # Gemini（Imagen 4.0）适配器
│   ├── comfyui.py               # ComfyUI 本地适配器
│   └── runninghub.py            # RunningHub 云端工作流适配器
│
├── stages/                      # 生成阶段子命令实现
│   ├── __init__.py              # GenerateLog
│   ├── images.py                # 图片生成（锚图 + 宫格 + 拆分）
│   ├── video.py                 # 视频分组生成
│   ├── dub.py                   # TTS 配音
│   ├── voice_design.py          # 音色设计
│   ├── targeting.py             # 镜号 → 叙事组解析
│   └── status.py                # 产物状态诊断
│
├── imaging/                     # 图像处理工具
│   ├── __init__.py
│   ├── specs.py                 # AspectRatio 等规格定义
│   ├── grid_canvas.py           # 宫格画布计算
│   └── aspect_ops.py            # 裁切 / 去边 / 比例归一
│
├── templates/                   # 手稿模板
│   ├── __init__.py
│   ├── 00_立意.md
│   ├── 01_大纲.md
│   ├── 02_分卷节拍表.md
│   ├── bible/                   # 五表圣经模板
│   │   ├── __init__.py
│   │   ├── 角色.md
│   │   ├── 场景.md
│   │   ├── 道具.md
│   │   ├── 世界观.md
│   │   └── 伏笔与线索.md
│   └── genres/                  # Vendored 题材 YAML（风格/色调/护栏）
│       └── __init__.py
│
├── exporters/                   # 导出器
│   ├── __init__.py
│   └── jianying.py              # 剪映草稿导出
│
├── commands/                    # 命令处理系统
│   ├── __init__.py
│   ├── dispatcher.py            # /xxx args → on_command 钩子
│   ├── new.py                   # /new — 题材选择 → 模板填充
│   ├── review.py                # /review — 五维评分
│   └── compliance.py            # /compliance — 红线检测
│
├── quality/                     # 质量门禁
│   ├── __init__.py
│   └── gate_g2.py               # G2 质量门禁实现
│
├── modes/                       # 模式切换
│   └── __init__.py
│
├── references/                   # 离线参考文档
│   ├── 创作方法论.md             # 各阶段宪章 + 批判环判据
│   ├── 平台契约.md               # 冻结平台契约（导入机制 / JSON 结构）
│   ├── 剧本格式规范.md           # 结构化剧本格式
│   ├── 分镜表规范.md             # 分镜表 schema + 叙事组规则
│   ├── 提示词规则.md             # 双语运动提示词规范
│   ├── 图像生成管线实操.md       # 实际出图操作指南
│   └── 自定义题材创作.md         # 自定义题材 YAML 编写指南
│
└── tests/                       # 测试
    ├── test_prompt_checker.py
    └── test_video_grouping.py
```

---

## 依赖 / Dependencies

核心运行时依赖（不含 stdlib）：

| 包 | 用途 | 必需? |
|---|---|---|
| `httpx` | HTTP 客户端（Grsai / RunningHub API 调用） | 是 |
| `Pillow` | 图片处理（去边 / 裁切 / 比例归一） | 是 |
| `flask` | 预览服务器 | 是 |
| `numpy` | 宫格画布计算（imaging） | 是 |
| `google-genai` | Gemini Provider（仅 Gemini 后端需要） | 可选 |

开发依赖：

| 包 | 用途 |
|---|---|
| `pytest` | 测试框架 |

---

## 契约版本 / Contract Version

`contract.py` 中定义了 `CONTRACT_VERSION = "2026-06-20"`，标识本技能对齐的平台契约版本。

这意味着：

- `export.py` 内置的冻结校验器（`validators.py`）和 JSON 发射器（`emit.py`）镜像了糯米短剧平台 `2026-06-20` 源码快照的导入模型。
- 产物文件夹"丢进去就能用"——平台各 loader 对缺文件惰性建默认、对未知字段过滤丢弃。
- 平台升级时，需重新同步 vendored 校验器并 bump 此版本。

---

## 许可 / License

MIT

---

## 相关文档

- [创作方法论](references/创作方法论.md) — 各阶段宪章、批判环判据、三轴基调、叙事组方法
- [平台契约](references/平台契约.md) — 冻结的平台导入机制与 JSON 结构说明
- [剧本格式规范](references/剧本格式规范.md) — 结构化剧本格式
- [分镜表规范](references/分镜表规范.md) — 分镜表 schema 与叙事组规则
- [提示词规则](references/提示词规则.md) — 双语运动提示词（video_prompt 中文三段 + video_prompt_en）
- [图像生成管线实操](references/图像生成管线实操.md) — 出图替代方案与诊断脚本
- [自定义题材创作](references/自定义题材创作.md) — 自定义题材 YAML 编写指南
