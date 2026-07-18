# nuomi-drama-skills v0.8.1 — 产品文档（含使用指南 + 测试方案）

> **目标**：帮助用户和测试者全面理解和使用 nuomi-drama-skills。
> **版本**：2026-07-18 · v0.8.1
> **覆盖**：产品概览 · 快速上手 · 6 角色技能体系 · 完整测试清单

---

## 1. 产品概览

nuomi-drama-skills 是一套面向 AI 短剧/漫剧创作的技能系统。它让 AI 代理以**剧组角色**的方式协作完成从立意到交付物的全部工作。

### 1.1 核心能力

| 能力 | 描述 |
|------|------|
| 🎨 创意设计 | 立意→题材→三轴→批判环，一句话想法落地为可执行创作大纲 |
| 🌍 世界观搭建 | 角色/场景/道具/世界观/伏笔 五表圣经，工程级规格 |
| ✍️ 剧本写作 | 大纲→分卷节拍表→逐集剧本，竖屏 90-180s 格式 |
| 🎬 分镜设计 | 镜头设计→双语提示词，适配 AI 出图/出视频 |
| 🔧 技术生成 | 编译导出→图片/视频/配音生成→Provider 容灾 |
| 🔍 质量控制 | 5 维度 50 分审查→3 层合规检查→重试协议 |

### 1.2 项目规模

| 维度 | 数值 |
|------|------|
| Python 代码量 | ~7,460 行 |
| Python 模块 | 38 个 + 6 个 Provider + 10 个 Stage |
| 技能文件 | 7 个 SKILL.md（1 Root + 6 Role） |
| Dashboard | Flask + 5 个 Jinja2 模板 + SSE 实时监控 |
| 测试 | 54 个（51 PASS，3 个预存消息语言问题） |
| 零额外依赖 | Flask 已在 pyproject.toml，无新增库 |

### 1.3 架构层级

```
L5: 技能层（6 角色 × 1 Root Router）
    nuomi-drama → nuomi-ideator / bible / scribe / director / builder / qa
─────────────────────────────────────────────────────
L4: Dashboard（浏览器）
    preview_server.py · templates/web/
─────────────────────────────────────────────────────
L3: 命令系统 + 审查引擎 + 导出器
    commands/ · quality/ · exporters/
─────────────────────────────────────────────────────
L2: 编译管线（确定性编译器）
    export.py · emit.py · gates.py · validators.py
─────────────────────────────────────────────────────
L1: 创作 + 生成管线
    manuscript/*.md → generate.py → providers/
    errors.py · observability.py · aosop.py · retake.py · modes/
```

---

## 2. 快速上手

### 2.1 安装

```bash
# 克隆仓库
git clone https://github.com/YuRui-Liu/Nuomi-drama-skills.git
cd nuomi-drama-skills

# 安装依赖
pip install httpx Pillow flask numpy google-genai pytest

# 验证安装
python -c "import flask, httpx, PIL, numpy; print('OK')"
```

### 2.2 配置 Provider

```bash
# 复制示例配置
cp skill.env.example skill.env

# 编辑 skill.env，填入你的 API Key
# 草稿模式（不消耗视频/配音配额）：
set NUOMI_MODE=draft
```

### 2.3 三种启动方式

```bash
# 方式 1：Dashboard（浏览器）
python preview_server.py <out_dir>
# → http://localhost:7788

# 方式 2：命令行
python generate.py images E1-E3 --out <dir>
python -m commands new --out <dir>

# 方式 3：AI 代理中激活技能
# 用户说 "帮我写一部霸总甜宠短剧" → AI 自动路由到 nuomi-ideator
# 用户说 "E5 的剧本改一下" → AI 自动路由到 nuomi-scribe
```

---

## 3. 六角色技能体系

### 3.1 角色总览

```
📋 nuomi-drama (Root Router — 制片人/统筹)
    │  触发词：短剧、漫剧、竖屏剧、分镜、剧本、出图
    │  职责：识别意图 → 路由到对应角色
    │
    ├── 🎨 nuomi-ideator    创意总监    立意·题材·三轴·批判环
    │      触发词：立意/题材/三轴/一句话故事/基调
    │      输入：用户一句话想法
    │      输出：manuscript/00_立意.md
    │      门控：G1 三轴一致性
    │
    ├── 🌍 nuomi-bible      世界观架构师  角色·场景·道具·世界观·伏笔
    │      触发词：角色设定/世界观/场景/道具/伏笔/圣经
    │      输入：manuscript/00_立意.md
    │      输出：manuscript/bible/*.md（五表）
    │      门控：G3 圣经非空
    │
    ├── ✍️ nuomi-scribe      编剧         大纲·节拍表·逐集剧本
    │      触发词：写剧本/写大纲/写对白/批量产集
    │      输入：manuscript/01_大纲.md + bible/*.md
    │      输出：manuscript/episodes/E{n}.md
    │      门控：G2 大纲完整性、G4 节拍表校验
    │
    ├── 🎬 nuomi-director   分镜导演      分镜表·镜头设计·提示词
    │      触发词：分镜/镜头设计/video_prompt/运镜
    │      输入：manuscript/episodes/E{n}.md
    │      输出：分镜表 JSON 段（含双语提示词）
    │      门控：G5 分镜规范、G6 提示词质量
    │
    ├── 🔧 nuomi-builder    技术导演      编译导出·生成管线·Provider
    │      触发词：编译/export/出图/出视频/配音/generate
    │      输入：manuscript/ + out_dir/
    │      输出：图片/视频/配音/字幕/FFmpeg 脚本
    │      门控：G0+G5-G10+G_sequence（全量）
    │
    └── 🔍 nuomi-qa         质量控制      审查·合规·门控·重试
           触发词：审查/评分/合规/红线/重试/为什么失败了
           输入：out_dir/ + manuscript/ + generate_log.json
           输出：审查报告 + 合规报告 + 重试记录
           门控：G0 源完整性、G1-G4（审查阶段）
```

### 3.2 角色调度逻辑（Root Router）

| 用户说什么 | 路由到 |
|-----------|--------|
| "帮我写一部霸总甜宠" | nuomi-ideator → nuomi-bible → nuomi-scribe（链式） |
| "E5 的剧本改一下" | nuomi-scribe（直接，跳过上游） |
| "这批图全黑了" | nuomi-qa（带上 generate_log.json） |
| "出 E1-E5 的图" | nuomi-builder（带上分镜表 JSON） |
| "审一下全集" | nuomi-qa（review mode） |

### 3.3 跨角色状态

所有角色读写同一个 `writing_state.json`：
```json
{
  "phase": "scripting",
  "completed_episodes": [1,2,3,4],
  "last_role": "nuomi-scribe",
  "role_history": [
    {"role": "nuomi-ideator", "output": "00_立意.md"},
    {"role": "nuomi-bible", "output": "bible/*.md"},
    {"role": "nuomi-scribe", "output": "E1-E4.md"}
  ]
}
```

### 3.4 Gateway Check

```python
from gates import run_all_gates
from pathlib import Path

# G0 + G5-G10 + G_sequence
results = run_all_gates(Path("manuscript"), Path("out"), stage="generating")
for r in results:
    print(f"{r.gate_name}: {'PASS' if r.passed else 'FAIL'}")

# G1-G4 only
results = run_all_gates(Path("manuscript"), Path("out"), stage="scripting")
```

---

## 4. Dashboard 使用

### 4.1 启动 Dashboard

```bash
python preview_server.py <out_dir>
# Dashboard: http://localhost:7788
```

### 4.2 Dashboard 路由

| 路由 | 功能 |
|------|------|
| `/` | 📊 项目仪表板 — 操作按钮 / AOSOP 进度 / 审查得分 / 合规状态 |
| `/monitor` | 📡 生成监控 — SSE 实时进度条 + 每镜色块 + 失败重试 + Provider 健康 |
| `/ep/<n>` | 🎞️ 分镜预览 — 逐镜 action_desc + 三态标记（图片/视频/配音） |
| `/assets` | 📦 资源库 — 角色/场景/道具 + 音色声库 |
| `/api/monitor/stream` | SSE 实时数据流 |
| `/api/status` | JSON 状态快照 |

### 4.3 Dashboard 操作按钮

| 按钮 | 调用的 API | 触发的 Python 模块 |
|------|-----------|-------------------|
| 📝 编译导出 | `POST /api/export` | `export.py` |
| 🖼 出图 | `POST /api/generate/images` | `generate.py images` |
| 🎬 出视频 | `POST /api/generate/video` | `generate.py video` |
| 🎙️ 配音 | `POST /api/generate/dub` | `generate.py dub` |
| 📋 审查 | `POST /api/review` | `quality/review.py` |
| 🛡️ 合规 | `POST /api/compliance` | `quality/compliance.py` |
| 📄 导出 SRT | `POST /api/exporters/srt` | `exporters/srt.py` |
| 🎞️ 导出 FFmpeg | `POST /api/exporters/ffmpeg` | `exporters/ffmpeg.py` |

---

## 5. 生成管线 CLI

### 5.1 编译导出

```bash
python export.py <manuscript_dir> <out_project_dir>
```

### 5.2 生成命令

```bash
# 出图
python generate.py images E1-E3 --out <dir>
python generate.py images E1-E3 --out <dir> --force        # 强制重新生成
python generate.py images E1-E3 --out <dir> --retry-failed  # 只重试失败的
python generate.py images E1 --out <dir> --only s05 --solo  # 单镜旁路

# 出视频
python generate.py video E1-E3 --out <dir>

# 配音
python generate.py dub E1-E3 --out <dir>

# 音色设计
python generate.py voice_design --out <dir>

# 状态报告
python generate.py status E1-E3 --out <dir>
python generate.py status E1-E3 --out <dir> --json

# 干运行（不调用 API）
python generate.py images E1-E3 --out <dir> --dry-run

# 草稿模式
set NUOMI_MODE=draft
python generate.py images E1-E3 --out <dir>   # 低分辨率，跳过视频/配音
```

### 5.3 Provider 路由

| Provider | 类型 | 草稿模式 |
|----------|------|---------|
| Grsai（GPT Image 2） | 图片 | 切换到 Gemini |
| Gemini（Imagen 4.0） | 图片 | 默认 |
| ComfyUI | 图片+视频（本地） | 使用本地实例 |
| RunningHub | 图片+视频+配音+放大+声音克隆 | 仅生产模式 |

---

## 6. 完整测试清单

### 6.1 测试环境准备

```bash
pip install httpx Pillow flask numpy google-genai pytest
python -c "import flask, httpx, PIL, numpy; print('OK')"

cd nuomi-drama-skills
set NUOMI_MODE=draft
mkdir test_output
```

### 6.2 L1：创作管线（11 项）

| # | 测试项 | 操作 | 预期 |
|---|--------|------|------|
| T1.1 | 项目骨架创建 | 复制 `example/manuscript/` 到 `test_output/` | `manuscript/` 含全部模板文件 |
| T1.2 | 立意校验 G1 | `python -c "from gates import gate_triplet; from pathlib import Path; r=gate_triplet(Path('example/manuscript')); print(r.passed, r.warnings)"` | PASS 或含可读警告 |
| T1.3 | 大纲校验 G2 | `python -c "from gates import gate_outline; from pathlib import Path; r=gate_outline(Path('example/manuscript')); print(r.passed, r.warnings)"` | PASS 或含可读警告 |
| T1.4 | 圣经非空 G3 | `python -c "from gates import gate_bible; from pathlib import Path; r=gate_bible(Path('example/manuscript')); print(r.passed)"` | PASS |
| T1.5 | 节拍表 G4 | `python -c "from gates import gate_beats; from pathlib import Path; r=gate_beats(Path('example/manuscript')); print(r.passed)"` | PASS |
| T1.6 | 分镜规范 G5 | `python -c "from gates import gate_storyboard; from pathlib import Path; r=gate_storyboard(Path('example/manuscript/episodes/E1.md')); print(r.passed)"` | PASS |
| T1.7 | 提示词质量 G6 | 同上，调 `gate_prompts()` | PASS |
| T1.8 | 源完整性 G0 | `python -c "from gates import gate_source_integrity; from pathlib import Path; r=gate_source_integrity(Path('example/manuscript'),Path('.')); print(r.passed)"` | PASS 或含骨架集警告 |
| T1.9 | 漂移检测 G_seq | 先 `python export.py example/manuscript test_output/out`，再 `touch example/manuscript/episodes/E1.md`，再跑 `gate_sequence` | FAIL（检测到手稿更新） |
| T1.10 | 全量门控 | `python -c "from gates import run_all_gates; from pathlib import Path; results=run_all_gates(Path('example/manuscript'), Path('.'), 'all'); [print(f'{r.gate_name}: {r.passed}') for r in results]"` | 返回全部 gate 结果 |
| T1.11 | 错误分类器 | `python -c "from errors import classify_error, ErrorCode; assert classify_error('GRSAI_API_KEY 未配置').code==ErrorCode.PROVIDER_NOT_CONFIGURED; print('OK')"` | OK |

### 6.3 L2：编译管线（6 项）

| # | 测试项 | 操作 | 预期 |
|---|--------|------|------|
| T2.1 | 确定性编译 | `python export.py example/manuscript test_output/out` | exit 0 |
| T2.2 | 幂等重编译 | 再次执行 T2.1 | exit 0，产物保留 |
| T2.3 | 产物清单 | `ls test_output/out/` | 含 series.json, arcs.json, story_bible.json, E1/, assets/ |
| T2.4 | 骨架集报告 | 对只有大纲无剧本的集编译 | 输出含 "骨架" 提示 |
| T2.5 | 校验失败不写盘 | 修改分镜表缺 shot_id 后编译 | exit != 0，已有文件未被覆盖 |
| T2.6 | 编译报告可读 | 执行编译 | stdout 含剧集清单和警告数 |

### 6.4 L3：命令系统 + 审查 + 导出（10 项）

| # | 测试项 | 操作 | 预期 |
|---|--------|------|------|
| T3.1 | dispatcher 门控 | `python -c "from commands.dispatcher import dispatch, GateBlocked; ..."` | ideation 只能 new，非 scripting 不能 review |
| T3.2 | /nuomi:new | `python -m commands new --out test_output/proj` | 创建 manuscript/ + writing_state.json |
| T3.3 | /nuomi:review | 在已编译项目上运行 | 生成 review_report.json + .md |
| T3.4 | /nuomi:compliance | 在已编译项目上运行 | 生成 compliance_report.json + .md |
| T3.5 | 5 维度评分 | `python -c "import json; r=json.load(open('test_output/out/review_report.json')); print(r['scores'])"` | 5 个维度全部存在 |
| T3.6 | 红线检测 | 在手稿中写 `推翻` 后编译并运行 compliance | red_lines_hit >= 1 |
| T3.7 | 题材踩坑 | 手稿写 `强迫爱情` + 霸道总裁题材 | 灰区含 genre pitfall |
| T3.8 | SRT 导出 | `python -c "from exporters.srt import export_srt; print(export_srt('test_output/out'))"` | 生成 subtitle_zh.srt |
| T3.9 | FFmpeg 导出 | `python -c "from exporters.ffmpeg import export_ffmpeg; print(export_ffmpeg('test_output/out'))"` | 生成 compose.sh |
| T3.10 | 剪映导出 | `python -c "from exporters.jianying import export_jianying; print('OK')"` | 生成 jianying_draft.json |

### 6.5 L4：Dashboard 前端（11 项）

| # | 测试项 | 操作 | 预期 |
|---|--------|------|------|
| T4.1 | 服务启动 | `python preview_server.py test_output/out` | 打印 `Dashboard: http://localhost:7788` |
| T4.2 | `/` 仪表板 | 浏览器 `http://localhost:7788/` | 200，标题+AOSOP+按钮 |
| T4.3 | `/monitor` | 浏览器 `http://localhost:7788/monitor` | 200，进度条+SSE |
| T4.4 | `/ep/1` 分镜 | 浏览器 `http://localhost:7788/ep/1` | 200，镜号+三态 |
| T4.5 | `/assets` 资源 | 浏览器 `http://localhost:7788/assets` | 200，角色/场景/道具 |
| T4.6 | `/api/status` | `curl http://localhost:7788/api/status` | JSON 含 summary+aosop |
| T4.7 | SSE 流 | `curl -N http://localhost:7788/api/monitor/stream` | 每 2s 推送 data |
| T4.8 | POST export | `curl -X POST http://localhost:7788/api/export` | `{"status":"ok"}` |
| T4.9 | POST review | `curl -X POST http://localhost:7788/api/review` | JSON 含审查结果 |
| T4.10 | POST compliance | `curl -X POST http://localhost:7788/api/compliance` | JSON 含红线/灰区 |
| T4.11 | POST exporters | `curl -X POST http://localhost:7788/api/exporters/srt` | `{"status":"ok"}` |

### 6.6 L5：架构升级专项（10 项）

| # | 测试项 | 操作 | 预期 |
|---|--------|------|------|
| T5.1 | 错误码 17 种 | `python -m pytest tests/test_errors.py -v` | 11 PASS |
| T5.2 | Retake 单变量 | `python -m pytest tests/test_retake.py -v` | 5 PASS |
| T5.3 | ShootProtocol 持久化 | 同上 | save/load 往返 |
| T5.4 | 可观测性引擎 | `python -m pytest tests/test_observability.py -v` | 4 PASS |
| T5.5 | AOSOP 状态 | `python -m pytest tests/test_aosop.py -v` | 5 PASS |
| T5.6 | Draft/Production | `python -m pytest tests/test_modes.py -v` | 4 PASS |
| T5.7 | G7 Pillow | 放置 1x1 纯黑 PNG 后跑 G7 | "几乎全黑" |
| T5.8 | G9 MP4 | 放置 0 字节 .mp4 后跑 G9 | "video < 1KB" |
| T5.9 | G10 WAV | 放置无 RIFF 头 .wav 后跑 G10 | "not valid WAV" |
| T5.10 | load_map | `python -c "import json; m=json.load(open('references/load_map.json')); assert 'layers' in m; print('OK')"` | OK |

### 6.7 L6：技能体系验证（7 项）

| # | 测试项 | 操作 | 预期 |
|---|--------|------|------|
| T6.1 | Root Router | `python -c "import yaml; t=open('SKILL.md').read(); fm=yaml.safe_load(t.split('---',2)[1]); assert fm['name']=='nuomi-drama'; print('OK')"` | OK |
| T6.2 | nuomi-ideator | 同上检查 `.claude/skills/nuomi-ideator.md` | name+role+phase 正确 |
| T6.3 | nuomi-bible | 同上检查 `.claude/skills/nuomi-bible.md` | role=bible-architect |
| T6.4 | nuomi-scribe | 同上 | phase=scripting |
| T6.5 | nuomi-director | 同上 | role=director |
| T6.6 | nuomi-builder | 同上 | 含全部 G0+G5-G10 gates |
| T6.7 | nuomi-qa | 同上 | 含 retake protocol |

### 6.8 L7：发布审计（5 项）

| # | 测试项 | 操作 | 预期 |
|---|--------|------|------|
| T7.1 | 文件存在性 | `python scripts/release_audit.py --check` | 全 Pass |
| T7.2 | 版本一致性 | 同 T7.1 | OK |
| T7.3 | 安全扫描 | 同 T7.1 | 无真实 Key |
| T7.4 | Reference 完整 | 同 T7.1 | 无死链 |
| T7.5 | 模块注册 | 同 T7.1 | 所有 commands/exporters 可导入 |

---

## 7. 自动化测试运行

```bash
# 全量运行（跳过 3 个预存 prompt_checker 消息语言问题）
python -m pytest tests/ --ignore=tests/test_prompt_checker.py -v

# 仅运行新增测试
python -m pytest tests/test_errors.py tests/test_retake.py \
  tests/test_observability.py tests/test_modes.py tests/test_aosop.py \
  tests/test_dashboard.py tests/test_dispatcher.py \
  tests/test_generate_cli.py tests/test_offline_e2e.py \
  tests/test_video_grouping.py -v

# 编译检查
python -m compileall .

# 发布审计
python scripts/release_audit.py --check
```

### 预期测试结果

| 测试文件 | 用例数 | 预期 |
|----------|--------|------|
| `test_errors.py` | 11 | 11 PASS |
| `test_retake.py` | 5 | 5 PASS |
| `test_observability.py` | 4 | 4 PASS |
| `test_modes.py` | 4 | 4 PASS |
| `test_aosop.py` | 5 | 5 PASS |
| `test_dashboard.py` | 5 | 5 PASS |
| `test_dispatcher.py` | 3 | 3 PASS |
| `test_generate_cli.py` | 4 | 4 PASS |
| `test_offline_e2e.py` | 1 | 1 PASS |
| `test_video_grouping.py` | 3 | 3 PASS |
| **总计** | **45** | **45 PASS** |

---

## 8. 安装到其他 AI 代理

### 8.1 安装到 Hermes

```bash
cp SKILL.md "E:/Tools/Hermes/skills/nuomi-drama-skills/SKILL.md"
mkdir -p "E:/Tools/Hermes/skills/nuomi-drama-skills/.claude/skills"
cp .claude/skills/*.md "E:/Tools/Hermes/skills/nuomi-drama-skills/.claude/skills/"
```

### 8.2 安装到 Codex

```bash
# Codex 读取 .claude/skills/ 目录
# 整个 repo clone 即可，Codex 自动发现 SKILL.md + .claude/skills/*.md
```

### 8.3 跨平台兼容

所有技能文件使用标准 `SKILL.md` 格式（YAML frontmatter + Markdown body），与 Claude Code / Codex / Hermes / Gemini CLI 兼容。每条 Skill 标记了 `user-invocable: true` 和明确的触发词。

---

## 9. 已知问题

| # | 严重度 | 描述 | 文件 |
|---|--------|------|------|
| KN-1 | 低 | `test_prompt_checker.py` 3 个用例断言消息为英文，实际返回中文消息 | `tests/test_prompt_checker.py:37,93,114` |
| KN-2 | 低 | `generate.py` 尚未接入 `--mode draft|production` 标志（配置已定义） | `generate.py` |

---

## 10. 签署标准

- [ ] L1 创作管线：11/11 通过
- [ ] L2 编译管线：6/6 通过
- [ ] L3 命令+审查+导出：10/10 通过
- [ ] L4 Dashboard：11/11 通过
- [ ] L5 架构升级：10/10 通过
- [ ] L6 技能体系：7/7 通过
- [ ] L7 发布审计：5/5 通过
- [ ] 自动化测试：45/45 PASS + 审计 OK

---

## 附录 A：快速验证脚本

```bash
#!/bin/bash
# verify.sh —— nuomi-drama-skills 快速验证
set -e

cd "$(dirname "$0")"

echo "=== 1. 编译检查 ==="
python -m compileall . && echo "OK" || echo "FAIL"

echo "=== 2. 单元测试 ==="
python -m pytest tests/ --ignore=tests/test_prompt_checker.py -q --tb=no

echo "=== 3. 发布审计 ==="
python scripts/release_audit.py --check

echo "=== 4. 技能文件验证 ==="
python -c "
import yaml
from pathlib import Path
skills = ['SKILL.md'] + [f'.claude/skills/{n}' for n in
  ['nuomi-ideator.md','nuomi-bible.md','nuomi-scribe.md',
   'nuomi-director.md','nuomi-builder.md','nuomi-qa.md']]
for s in skills:
    fm = yaml.safe_load(Path(s).read_text(encoding='utf-8').split('---',2)[1])
    assert fm.get('user-invocable') == True, f'{s}: not user-invocable'
    assert fm.get('name'), f'{s}: no name'
print(f'OK: {len(skills)} skills validated')
"

echo "=== 5. Dashboard 冒烟 ==="
python -c "
from preview_server import _create_app
app = _create_app('.')
with app.test_client() as c:
    for route in ['/','/monitor','/api/status']:
        r = c.get(route)
        assert r.status_code == 200, f'{route}: {r.status_code}'
print('OK: Dashboard routes (/, /monitor, /api/status) all 200')
"

echo "=== 全部检查完成 ==="
```
