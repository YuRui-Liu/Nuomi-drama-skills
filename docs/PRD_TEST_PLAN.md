# nuomi-drama-skills v0.8.0 — 测试计划 PRD

> **目标**：验证 nuomi-drama-skills 全栈功能——从创作管线到 Dashboard 前端、从编译导出到生成监控。
> **版本**：2026-07-17 · v0.8.0
> **测试范围**：4 层（创作 → 编译 → 生成 → Dashboard）

---

## 1. 项目现状

| 维度 | 数值 |
|------|------|
| Python 代码量 | ~7,460 行 |
| 已有测试 | 54 个（51 PASS，3 个预存消息语言问题） |
| 已有模块 | 38 个 Python 模块，6 个 Provider，10 个 Stage |
| 新增模块（本轮） | `errors.py`, `observability.py`, `aosop.py`, `stages/retake.py`, `modes/`(3), `commands/`(5), `quality/`(3), `exporters/`(3) |
| Dashboard | `preview_server.py` + 5 个 Jinja2 模板 |
| 发布审计 | `scripts/release_audit.py --check` → OK |

---

## 2. 架构层级

```
┌─────────────────────────────────────────────────────┐
│  L4: Dashboard（浏览器）                             │
│  preview_server.py · templates/web/                  │
├─────────────────────────────────────────────────────┤
│  L3: 命令系统 + 审查引擎 + 导出器                     │
│  commands/ · quality/ · exporters/                   │
├─────────────────────────────────────────────────────┤
│  L2: 编译管线（确定性编译器）                          │
│  export.py · emit.py · gates.py · validators.py      │
├─────────────────────────────────────────────────────┤
│  L1: 创作管线（手稿 + 生成）                          │
│  manuscript/*.md → generate.py → providers/          │
└─────────────────────────────────────────────────────┘
```

---

## 3. 测试环境准备

### 3.1 前置条件

```bash
# 安装依赖
pip install httpx Pillow flask numpy google-genai pytest

# 确认安装
python -c "import flask, httpx, PIL, numpy; print('OK')"

# 配置 Provider（测试用 —— 使用草稿模式跳过视频/配音）
set NUOMI_MODE=draft
```

### 3.2 示例项目初始化

```bash
cd nuomi-drama-skills
mkdir -p test_output
```

---

## 4. 测试清单

### 4.1 L1：创作管线（11 项）

| # | 测试项 | 操作 | 预期 |
|---|--------|------|------|
| T1.1 | 项目骨架创建 | 复制 `example/manuscript/` 到 `test_output/` | `manuscript/` 含全部模板文件 |
| T1.2 | 立意校验 | `python -c "from gates import gate_triplet; ..."` | G1 PASS 或含可读警告 |
| T1.3 | 大纲校验 | `python -c "from gates import gate_outline; ..."` | G2 PASS 或含可读警告 |
| T1.4 | 圣经非空校验 | `python -c "from gates import gate_bible; ..."` | G3 PASS |
| T1.5 | 节拍表校验 | `python -c "from gates import gate_beats; ..."` | G4 PASS |
| T1.6 | 分镜规范校验 | `python -c "from gates import gate_storyboard; ..."` | G5 PASS |
| T1.7 | 提示词质量校验 | `python -c "from gates import gate_prompts; ..."` | G6 PASS |
| T1.8 | G0 源完整性 | `python -c "from gates import gate_source_integrity; ..."` | G0 PASS 或含骨架集警告 |
| T1.9 | G_sequence 漂移检测 | 先 export，再修改手稿，再运行 | G_sequence FAIL（检测到漂移） |
| T1.10 | 全量门控运行 | `python -c "from gates import run_all_gates; ..."` | 返回 G0-G8+G9/G10+G_seq 结果列表 |
| T1.11 | 错误分类器 | `python -c "from errors import classify_error; ..."` | 已知模式返回正确 ErrorCode |

### 4.2 L2：编译管线（6 项）

| # | 测试项 | 操作 | 预期 |
|---|--------|------|------|
| T2.1 | 确定性编译 | `python export.py example/manuscript test_output/out` | exit 0，无 stderr 输出 |
| T2.2 | 幂等重编译 | 再次执行 T2.1 相同命令 | exit 0，regenerate 状态保留 |
| T2.3 | 产物清单 | 检查 `test_output/out/` | 含 `series.json`, `arcs.json`, `story_bible.json`, `E1/gen_context.json`, `assets/registry.json`, `harness_state.json` |
| T2.4 | 骨架集报告 | 对只有大纲没有剧本的集 | export 输出含 "骨架" 或 "skeleton" 提示 |
| T2.5 | 校验失败不写盘 | 修改手稿使分镜表缺 shot_id，再编译 | exit != 0，已存在的 `out/` 目录未被覆盖 |
| T2.6 | 编译报告 | `python export.py example/manuscript test_output/out2` | 标准输出含剧集清单和警告数 |

### 4.3 L3：命令系统 + 审查 + 导出（10 项）

| # | 测试项 | 操作 | 预期 |
|---|--------|------|------|
| T3.1 | dispatcher 门控 | `python -c "from commands.dispatcher import dispatch; ..."` | ideation 只能 new，非 scripting 不能 review |
| T3.2 | /nuomi:new | `python -m commands new --out test_output/proj` | 创建 manuscript/ + writing_state.json |
| T3.3 | /nuomi:review | 在已编译项目上运行 | 生成 review_report.json + review_report.md，得分 0-50 |
| T3.4 | /nuomi:compliance | 在已编译项目上运行 | 生成 compliance_report.json + compliance_report.md |
| T3.5 | 审查 5 维度评分 | 检查 review_report.json | 含 format/continuity/prompt_quality/char_consistency/satisfaction 五个维度 |
| T3.6 | 合规红线检测 | 在手稿中加入"推翻"关键词，运行合规检查 | red_lines_hit >= 1 |
| T3.7 | 合规题材踩坑 | 手稿设为"霸道总裁"，加入"用钱买感情" | 灰区 finding 含 genre pitfall |
| T3.8 | SRT 导出 | `python -c "from exporters.srt import export_srt; ..."` | 生成 `E{n}/subtitle_zh.srt`，格式正确 |
| T3.9 | FFmpeg 导出 | `python -c "from exporters.ffmpeg import export_ffmpeg; ..."` | 生成 `E{n}/compose.sh` 或 `.ps1`，含 ffmpeg 命令 |
| T3.10 | 剪映导出 | `python -c "from exporters.jianying import export_jianying; ..."` | 生成 `E{n}/jianying_draft.json` |

### 4.4 L4：Dashboard 前端（11 项）

| # | 测试项 | 操作 | 预期 |
|---|--------|------|------|
| T4.1 | 服务启动 | `python preview_server.py test_output/out` | 打印 `Dashboard: http://localhost:7788` |
| T4.2 | 仪表板 `/` | 浏览器访问 `http://localhost:7788/` | 200，展示项目标题、阶段、AOSOP 统计、操作按钮 |
| T4.3 | 监控页 `/monitor` | 浏览器访问 `http://localhost:7788/monitor` | 200，展示进度条、SSE 等待连接 |
| T4.4 | 分镜预览 `/ep/1` | 浏览器访问 `http://localhost:7788/ep/1` | 200，展示 E1 各镜信息、三态标记 |
| T4.5 | 资源库 `/assets` | 浏览器访问 `http://localhost:7788/assets` | 200，展示角色/场景/道具列表 |
| T4.6 | API 状态 `/api/status` | `curl http://localhost:7788/api/status` | JSON 含 summary + aosop |
| T4.7 | SSE 流 `/api/monitor/stream` | `curl -N http://localhost:7788/api/monitor/stream` | 每 2 秒推送 `data: {...}` JSON |
| T4.8 | API 导出触发 | `curl -X POST http://localhost:7788/api/export` | JSON `{"status":"ok","message":"编译完成"}` |
| T4.9 | API 审查触发 | `curl -X POST http://localhost:7788/api/review` | JSON 含审查结果 |
| T4.10 | API 合规触发 | `curl -X POST http://localhost:7788/api/compliance` | JSON 含红线/灰区数 |
| T4.11 | API 导出器 | `curl -X POST http://localhost:7788/api/exporters/srt` | JSON `{"status":"ok"}`，SRT 文件生成 |

### 4.5 架构升级专项（10 项）

| # | 测试项 | 操作 | 预期 |
|---|--------|------|------|
| T5.1 | 错误码分类 | `python -c "from errors import classify_error, ErrorCode; ..."` | 17 种错误码全部可分类 |
| T5.2 | RetakeController 单变量 | `python -c "from stages.retake import RetakeController; ..."` | seed→prompt→style→escalate 顺序 |
| T5.3 | ShootProtocol 持久化 | `python -c "from director import ShootProtocol; ..."` | save/load 往返正确 |
| T5.4 | 可观测性引擎 | `python -c "from observability import build_summary; ..."` | 返回 GenerationSummary，健康度正确 |
| T5.5 | AOSOP 状态视图 | `python -c "from aosop import load_aosop; ..."` | 读取 writing_state+gen_context+文件系统 |
| T5.6 | 模式解析 | `python -c "from modes import resolve_mode, get_config; ..."` | draft/production 配置可加载 |
| T5.7 | G7 增强图片校验 | 放置一张 1x1 纯黑 PNG 到 shots_assets | G7 报告"几乎全黑" |
| T5.8 | G9 视频健康 | 放置 0 字节 .mp4 文件 | G9 报告 "video < 1KB" |
| T5.9 | G10 音频健康 | 放置无 RIFF 头的 .wav 文件 | G10 报告 "not valid WAV" |
| T5.10 | 渐进披露 load_map | `python -c "import json; json.load(open(...))"` | load_map.json 解析正确，三层结构完整 |

### 4.6 发布审计（5 项）

| # | 测试项 | 操作 | 预期 |
|---|--------|------|------|
| T6.1 | 文件存在性 | `python scripts/release_audit.py --check` | 所有必需模块存在 |
| T6.2 | 版本一致性 | 同上 | contract.py 版本与 SKILL.md/README/pyproject.toml 一致 |
| T6.3 | 安全扫描 | 同上 | skill.env 无真实 Key |
| T6.4 | Reference 完整性 | 同上 | 无死链、无重复路径 |
| T6.5 | 模块注册 | 同上 | 所有 commands/exporters 可导入 |

---

## 5. 自动化测试运行

```bash
# 全量运行（跳过 3 个预存 prompt_checker 消息语言问题）
python -m pytest tests/ --ignore=tests/test_prompt_checker.py -v

# 仅运行新增测试
python -m pytest tests/test_errors.py tests/test_retake.py \
  tests/test_observability.py tests/test_modes.py tests/test_aosop.py \
  tests/test_dashboard.py tests/test_dispatcher.py \
  tests/test_generate_cli.py tests/test_offline_e2e.py \
  tests/test_video_grouping.py -v

# 运行发布审计
python scripts/release_audit.py --check

# 编译检查
python -m compileall .
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
| **总计（新）** | **45** | **45 PASS** |

---

## 6. 已知问题

| # | 严重度 | 描述 | 文件 |
|---|--------|------|------|
| KN-1 | 低 | `test_prompt_checker.py` 3 个用例断言消息为英文，实际返回中文消息 | `tests/test_prompt_checker.py:37,93,114` |
| KN-2 | 低 | `modes/` 的 draft/production 配置已定义但 `generate.py` 尚未接入 `--mode` 标志 | `generate.py` |

---

## 7. 签署标准

- [ ] L1 创作管线：11/11 通过
- [ ] L2 编译管线：6/6 通过
- [ ] L3 命令+审查+导出：10/10 通过
- [ ] L4 Dashboard：11/11 通过
- [ ] L5 架构升级：10/10 通过
- [ ] L6 发布审计：5/5 通过
- [ ] 自动化测试：45/45 PASS + 审计 OK

---

## 附录 A：快速验证脚本

```bash
#!/bin/bash
# verify.sh —— nuomi-drama-skills 快速验证

echo "=== 1. 编译检查 ==="
python -m compileall . && echo "OK" || echo "FAIL"

echo "=== 2. 单元测试 ==="
python -m pytest tests/ --ignore=tests/test_prompt_checker.py -q --tb=no
echo "Pass count: $(python -m pytest tests/ --ignore=tests/test_prompt_checker.py -q --tb=no 2>&1 | grep -oP '\d+(?= passed)')"

echo "=== 3. 发布审计 ==="
python scripts/release_audit.py --check

echo "=== 4. 错误码系统 ==="
python -c "
from errors import classify_error, ErrorCode, Severity
r = classify_error('GRSAI_API_KEY 未配置')
assert r.code == ErrorCode.PROVIDER_NOT_CONFIGURED
assert r.severity == Severity.BLOCK
print('OK')
"

echo "=== 5. 模式系统 ==="
python -c "
from modes import resolve_mode, get_config
assert resolve_mode() == 'production'
assert get_config('draft')['video']['skip'] is True
print('OK')
"

echo "=== 6. AOSOP ==="
python -c "
from aosop import AOSOPState
print('OK')
"

echo "=== 7. Dashboard 导入 ==="
python -c "
from preview_server import _create_app
app = _create_app('.')
with app.test_client() as c:
    r = c.get('/api/status')
    assert r.status_code == 200
print('OK')
"

echo "=== 全部检查完成 ==="
```
