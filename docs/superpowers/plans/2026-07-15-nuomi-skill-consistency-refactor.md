# Nuomi 漫剧技能一致性重构实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 修复已确认的 CLI、门控、剪映导出和文档漂移问题，建立可复现依赖与离线回归测试，并把 `SKILL.md` 优化为兼容现有手稿和平台契约的阶段路由。

**架构：** 保留 `manuscript → export → generate` 三层结构和现有顶层 CLI。测试先固定真实行为，再对已确认缺陷做局部修复；`SKILL.md` 只承担触发、阶段路由、安全边界和参考资料导航，详细规则统一放入 `references/`。

**技术栈：** Python 3.9+、pytest、httpx、Pillow、NumPy、PyYAML、Flask、Markdown/YAML 技能元数据。

---

## 文件结构

- 创建 `requirements.txt`、`requirements-dev.txt`：运行与测试依赖。
- 创建 `tests/test_release_baseline.py`：依赖、忽略规则和离线导入基线。
- 创建 `tests/test_generate_cli.py`：集数读取、状态、dry-run 和参数回归。
- 创建 `tests/test_gates.py`：阶段门控与 Provider 能力预检。
- 创建 `tests/test_export_regression.py`、`tests/test_jianying_export.py`：编译不变量和剪映路径。
- 创建 `tests/test_writing_state.py`：状态恢复与兼容读取。
- 创建 `tests/test_docs_sync.py`：技能、CLI、引用和契约版本一致性。
- 创建 `agents/openai.yaml`：Codex 技能界面元数据。
- 修改 `generate.py`：修复 `_episode_count` 丢失、支持可测试 `main(argv)`、修复 `voice_design --dry-run`，生成前执行能力相关预检。
- 修改 `gates.py`：让 export/images/video/dub 使用准确门控集合，并按能力检查 Provider 配置。
- 修改 `exporters/jianying.py`：输出真实媒体路径。
- 修改 `writing_state.py`：仅在测试证明需要时修复兼容读取或进度推断。
- 修改 `SKILL.md`、`README.md`、`docs/USER_GUIDE.md`：统一真实能力、命令、契约和职责边界。
- 移动 `reference/*.md` 到 `references/`：统一技能参考资料目录，并更新所有内部引用。

## 任务 1：建立可复现环境与真实测试基线

**文件：**
- 创建：`requirements.txt`
- 创建：`requirements-dev.txt`
- 创建：`tests/test_release_baseline.py`
- 修改：`.gitignore`（仅当测试发现缺项）

- [ ] **步骤 1：创建仓库内虚拟环境**

运行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
```

预期：`.venv/bin/python` 存在，`git status --short` 不显示 `.venv/`。

- [ ] **步骤 2：编写失败的发布基线测试**

创建 `tests/test_release_baseline.py`：

```python
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_dependency_manifests_cover_imported_runtime_packages():
    runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    for package in ("flask", "httpx", "numpy", "pillow", "pyyaml"):
        assert package in runtime


def test_dev_manifest_declares_pytest():
    dev = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8").lower()
    assert "-r requirements.txt" in dev
    assert "pytest" in dev


def test_local_environment_and_credentials_are_ignored():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for entry in (".venv/", "skill.env", ".env"):
        assert entry in ignored
```

- [ ] **步骤 3：运行测试并确认失败**

运行：`.venv/bin/python -m pytest tests/test_release_baseline.py -v`

预期：FAIL，指出 `requirements.txt` 或 `requirements-dev.txt` 不存在。

- [ ] **步骤 4：添加最小依赖清单**

`requirements.txt`：

```text
Flask>=3.0,<4
httpx>=0.27,<1
numpy>=1.26,<3
Pillow>=10,<12
PyYAML>=6,<7
```

`requirements-dev.txt`：

```text
-r requirements.txt
pytest>=8,<10
```

- [ ] **步骤 5：安装依赖并运行未修改代码的完整基线**

运行：

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

预期：依赖安装成功；记录所有失败测试的测试名和堆栈。不得在此步骤修改生产代码。

- [ ] **步骤 6：验证发布基线测试通过**

运行：`.venv/bin/python -m pytest tests/test_release_baseline.py -v`

预期：PASS。

- [ ] **步骤 7：提交环境基线**

```bash
git add requirements.txt requirements-dev.txt tests/test_release_baseline.py .gitignore
git commit -m "build: establish reproducible nuomi test environment"
```

## 任务 2：修复生成 CLI 的确定性缺陷

**文件：**
- 创建：`tests/test_generate_cli.py`
- 修改：`generate.py`

- [ ] **步骤 1：编写 `_episode_count` 和状态命令失败测试**

```python
import json

import generate


def test_episode_count_reads_series_json(tmp_path):
    (tmp_path / "series.json").write_text(
        json.dumps({"episode_count": 3}), encoding="utf-8"
    )
    assert generate._episode_count(str(tmp_path)) == 3


def test_status_main_accepts_injected_argv(tmp_path, capsys):
    (tmp_path / "series.json").write_text(
        json.dumps({"episode_count": 1}), encoding="utf-8"
    )
    (tmp_path / "E1").mkdir()
    (tmp_path / "E1" / "gen_context.json").write_text(
        json.dumps({"storyboard": {"shots": []}}), encoding="utf-8"
    )
    assert generate.main(["status", "all", "--out", str(tmp_path)]) == 0
    assert "E1:" in capsys.readouterr().out
```

- [ ] **步骤 2：编写 `voice_design --dry-run` 无网络测试**

```python
def test_voice_design_dry_run_needs_no_episode_range_or_provider(tmp_path, monkeypatch):
    def forbidden_provider():
        raise AssertionError("dry-run must not create a provider")

    monkeypatch.setattr(generate, "run_voice_design", forbidden_provider)
    assert generate.main(["voice_design", "--out", str(tmp_path), "--dry-run"]) == 0
```

- [ ] **步骤 3：运行测试并确认失败**

运行：`.venv/bin/python -m pytest tests/test_generate_cli.py -v`

预期：FAIL；至少暴露 `_episode_count` 未定义、`main` 不接受 argv 或 `None.strip()`。

- [ ] **步骤 4：恢复独立 `_episode_count` 并让 main 可注入参数**

在 `generate.py` 中将误缩进在 `_dry_run_dub` 尾部的集数读取逻辑提取为：

```python
def _episode_count(out_dir: str) -> int:
    series_path = Path(out_dir) / "series.json"
    if not series_path.is_file():
        return 1
    data = json.loads(series_path.read_text(encoding="utf-8"))
    return max(1, int(data.get("episode_count", 1)))
```

并改为：

```python
def main(argv=None) -> int:
    # parser 定义保持不变
    args = parser.parse_args(argv)
```

- [ ] **步骤 5：为 voice design dry-run 添加无副作用分支**

在解析集号前处理：

```python
if args.dry_run and args.stage == "voice_design":
    stats = {"done": 0, "skipped": 0, "failed": 0, "failures": [],
             "checks": ["voice_design dry-run: 未调用 provider"]}
    _emit_stats("voice_design", stats, args.as_json)
    return 0
```

- [ ] **步骤 6：验证针对性测试与现有生成测试**

运行：

```bash
.venv/bin/python -m pytest tests/test_generate_cli.py tests/test_video_grouping.py -v
.venv/bin/python generate.py --help
```

预期：测试 PASS；帮助中仍列出 `images|video|dub|voice_design|status`。

- [ ] **步骤 7：提交 CLI 修复**

```bash
git add generate.py tests/test_generate_cli.py
git commit -m "fix: restore deterministic generation cli behavior"
```

## 任务 3：使门控阶段与真实操作一致

**文件：**
- 创建：`tests/test_gates.py`
- 修改：`gates.py`
- 修改：`generate.py`

- [ ] **步骤 1：编写能力相关 Provider 健康测试**

```python
from gates import gate_provider_health


def test_image_preflight_does_not_require_runninghub():
    cfg = {
        "image_provider": "gemini",
        "gemini": {"api_key": "test-key"},
        "runninghub": {},
    }
    result = gate_provider_health(cfg, required={"image"})
    assert result.passed


def test_video_preflight_requires_only_video_credentials():
    cfg = {
        "image_provider": "grsai",
        "grsai": {"api_key": ""},
        "runninghub": {"api_key": "rh-test", "video_workflow_id": "wf-video"},
    }
    result = gate_provider_health(cfg, required={"video"})
    assert result.passed
```

- [ ] **步骤 2：编写阶段选择测试**

```python
def test_export_stage_runs_g1_through_g6(monkeypatch, tmp_path):
    names = []

    def fake(name):
        def run(*args, **kwargs):
            names.append(name)
            from gates import GateResult
            return GateResult(name, True, name in {"storyboard", "prompts"})
        return run

    import gates
    for attr, name in (
        ("gate_triplet", "triplet"), ("gate_outline", "outline"),
        ("gate_bible", "bible"), ("gate_beats", "beats"),
        ("gate_storyboard", "storyboard"), ("gate_prompts", "prompts"),
    ):
        monkeypatch.setattr(gates, attr, fake(name))
    ep_dir = tmp_path / "manuscript" / "episodes"
    ep_dir.mkdir(parents=True)
    (ep_dir / "E1.md").write_text("x", encoding="utf-8")
    gates.run_all_gates(tmp_path / "manuscript", tmp_path / "out", "export")
    assert names == ["triplet", "outline", "bible", "beats", "storyboard", "prompts"]
```

- [ ] **步骤 3：运行测试并确认失败**

运行：`.venv/bin/python -m pytest tests/test_gates.py -v`

预期：FAIL；当前 `gate_provider_health` 不接受 `required`，且 `export` 阶段未定义。

- [ ] **步骤 4：实现能力相关预检**

将签名改为：

```python
def gate_provider_health(cfg: dict, required: set[str] | None = None) -> GateResult:
    required = required or {"image", "video", "dub"}
```

仅在 `image` 中检查所选图片 Provider；仅在 `video` 中检查 RunningHub API key 与视频 workflow；仅在 `dub` 中检查 API key 与配音 workflow。保留未传 `required` 时的旧全量行为。

- [ ] **步骤 5：实现兼容的阶段路由**

`run_all_gates` 支持：

```text
export     -> G1-G6
images     -> G5 + G8(image)
video      -> G5-G8，G8 只检查 video
dub        -> G5 + G8(dub)
scripting  -> 保留旧行为 G1-G4
generating -> 保留旧行为 G5-G8
all        -> 保留旧行为 G1-G8
```

允许传入 `provider_cfg` 供测试注入；未提供时才调用 `providers.load_config()`。

- [ ] **步骤 6：在真实生成前调用准确预检**

在 `generate.main()` 的非 dry-run 分支、Provider 构造之前调用 `gate_provider_health(load_config(), required={args.stage})`，失败时逐条打印错误并返回 1。`images`、`video`、`dub` 分别映射到 `image`、`video`、`dub`；`voice_design` 映射到 `dub`。

- [ ] **步骤 7：验证门控与 CLI 回归**

运行：

```bash
.venv/bin/python -m pytest tests/test_gates.py tests/test_generate_cli.py -v
```

预期：PASS，且测试未创建 Provider、未访问网络。

- [ ] **步骤 8：提交门控修复**

```bash
git add gates.py generate.py tests/test_gates.py tests/test_generate_cli.py
git commit -m "fix: align generation gates with required capabilities"
```

## 任务 4：冻结编译不变量并修复剪映媒体路径

**文件：**
- 创建：`tests/test_export_regression.py`
- 创建：`tests/test_jianying_export.py`
- 修改：`exporters/jianying.py`
- 修改：`export.py`（仅当测试暴露入口问题）

- [ ] **步骤 1：编写编译不变量测试**

```python
import json
import shutil
from pathlib import Path

from export import export_project

ROOT = Path(__file__).parents[1]


def test_example_export_is_idempotent_and_preserves_runtime_state(tmp_path):
    manuscript = tmp_path / "manuscript"
    shutil.copytree(ROOT / "example" / "manuscript", manuscript)
    out = tmp_path / "out"
    assert export_project(manuscript, out)["ok"]

    ctx_path = out / "E1" / "gen_context.json"
    ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
    ctx["anchors"] = {"character/林夏": {"status": "ready"}}
    ctx["shots_assets"] = {"s1": {"status": "ready"}}
    ctx_path.write_text(json.dumps(ctx, ensure_ascii=False), encoding="utf-8")

    assert export_project(manuscript, out)["ok"]
    merged = json.loads(ctx_path.read_text(encoding="utf-8"))
    assert merged["anchors"] == ctx["anchors"]
    assert merged["shots_assets"] == ctx["shots_assets"]


def test_invalid_manuscript_does_not_create_output(tmp_path):
    manuscript = tmp_path / "manuscript"
    manuscript.mkdir()
    out = tmp_path / "out"
    report = export_project(manuscript, out)
    assert not report["ok"]
    assert not out.exists()


def test_invalid_manuscript_leaves_existing_output_unchanged(tmp_path):
    manuscript = tmp_path / "manuscript"
    manuscript.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    marker = out / "existing.json"
    marker.write_bytes(b'{"keep": true}')
    before = marker.read_bytes()
    report = export_project(manuscript, out)
    assert not report["ok"]
    assert marker.read_bytes() == before
```

- [ ] **步骤 2：运行编译测试并记录结果**

运行：`.venv/bin/python -m pytest tests/test_export_regression.py -v`

预期：现有正确不变量 PASS；若失败，先确认平台契约，再对 `emit.py` 或 `export.py` 做最小修复，并把对应失败保留为回归测试。

- [ ] **步骤 3：编写剪映路径失败测试**

```python
import json

from exporters.jianying import export_jianying


def test_jianying_uses_generated_media_paths(tmp_path):
    ep_dir = tmp_path / "E1"
    ep_dir.mkdir()
    ctx = {
        "episode_id": "E1",
        "storyboard": {"shots": [{
            "shot_id": "s1", "shot_number": 1, "duration": 4,
            "dialogue": [{"speaker": "林夏", "text": "走。", "emotion": "克制"}],
        }]},
    }
    (ep_dir / "gen_context.json").write_text(json.dumps(ctx), encoding="utf-8")
    export_jianying({"episodes": [{"episode_id": "E1"}]}, str(tmp_path))
    draft = json.loads((ep_dir / "jianying_draft.json").read_text(encoding="utf-8"))
    assert draft["tracks"][0]["clips"][0]["source"] == str(
        tmp_path / "E1" / "shots_assets" / "s1.mp4"
    )
    assert draft["tracks"][1]["clips"][0]["source"] == str(
        tmp_path / "audio" / "E1" / "dub" / "s1_林夏_line0.wav"
    )
```

- [ ] **步骤 4：运行测试并确认失败**

运行：`.venv/bin/python -m pytest tests/test_jianying_export.py -v`

预期：FAIL；当前路径使用不存在的 `shots/` 和 `dub/{shot}_dN.wav`。

- [ ] **步骤 5：修复路径构造**

让 `_build_jianying_draft` 始终接收项目根目录，构造：

```python
project = Path(out_dir)
video_source = project / f"E{ep}" / "shots_assets" / f"{shot_id}.mp4"
audio_source = project / "audio" / f"E{ep}" / "dub" / f"{shot_id}_{speaker}_line{di}.wav"
```

把 `source` 写为 `str(video_source)` 和 `str(audio_source)`；多集循环不再把 `E1` 目录误传为项目根目录。

- [ ] **步骤 6：验证 CLI 剪映导出**

运行：

```bash
.venv/bin/python -m pytest tests/test_export_regression.py tests/test_jianying_export.py -v
.venv/bin/python export.py example/manuscript /tmp/nuomi-plan-jianying --jianying
```

预期：测试 PASS；`/tmp/nuomi-plan-jianying/E1/jianying_draft.json` 存在。

- [ ] **步骤 7：提交编译与剪映回归**

```bash
git add export.py emit.py exporters/jianying.py tests/test_export_regression.py tests/test_jianying_export.py
git commit -m "fix: preserve export invariants and jianying media paths"
```

只添加实际修改的生产文件；若 `export.py` 或 `emit.py` 未修改，不将其加入提交。

## 任务 5：验证状态恢复并补齐可靠进度摘要

**文件：**
- 创建：`tests/test_writing_state.py`
- 修改：`writing_state.py`

- [ ] **步骤 1：编写状态兼容和手稿优先测试**

```python
import json

from writing_state import infer_progress, load_state


def test_load_state_recovers_from_corrupt_file(tmp_path):
    (tmp_path / "writing_state.json").write_text("{broken", encoding="utf-8")
    assert load_state(tmp_path)["phase"] == "ideation"


def test_infer_progress_uses_manuscript_files_without_overwriting_them(tmp_path):
    (tmp_path / "00_立意.md").write_text("idea", encoding="utf-8")
    (tmp_path / "01_大纲.md").write_text("outline", encoding="utf-8")
    episodes = tmp_path / "episodes"
    episodes.mkdir()
    (episodes / "E1.md").write_text("## 剧本\n正文\n\n## 分镜表\n```json\n{}\n```", encoding="utf-8")
    before = (episodes / "E1.md").read_bytes()
    progress = infer_progress(tmp_path)
    assert progress["suggested_phase"] == "bible"
    assert progress["episode_files"] == [1]
    assert (episodes / "E1.md").read_bytes() == before
```

- [ ] **步骤 2：运行测试并确认失败**

运行：`.venv/bin/python -m pytest tests/test_writing_state.py -v`

预期：`load_state` 用例 PASS，`infer_progress` 不存在导致 FAIL。

- [ ] **步骤 3：实现只读进度推断**

在 `writing_state.py` 添加：

```python
def infer_progress(manuscript_dir: Path) -> dict[str, Any]:
    root = Path(manuscript_dir)
    episode_files = sorted(
        int(p.stem[1:]) for p in (root / "episodes").glob("E*.md")
        if p.stem[1:].isdigit()
    ) if (root / "episodes").is_dir() else []
    if not (root / "00_立意.md").is_file():
        phase = "ideation"
    elif not (root / "01_大纲.md").is_file():
        phase = "outline"
    elif not (root / "bible").is_dir():
        phase = "bible"
    elif not (root / "02_分卷节拍表.md").is_file():
        phase = "beats"
    elif not episode_files:
        phase = "scripting"
    else:
        phase = "storyboard"
    return {"suggested_phase": phase, "episode_files": episode_files,
            "saved_state": load_state(root)}
```

只读取文件系统，不自动写入或推进状态。

- [ ] **步骤 4：验证状态测试**

运行：`.venv/bin/python -m pytest tests/test_writing_state.py -v`

预期：PASS。

- [ ] **步骤 5：提交状态恢复支持**

```bash
git add writing_state.py tests/test_writing_state.py
git commit -m "feat: infer nuomi manuscript progress safely"
```

## 任务 6：重构技能说明并建立文档同步门禁

**文件：**
- 创建：`tests/test_docs_sync.py`
- 创建：`agents/openai.yaml`
- 修改：`SKILL.md`
- 修改：`README.md`
- 修改：`docs/USER_GUIDE.md`
- 移动：`reference/*.md` → `references/*.md`
- 修改：包含旧 `reference/` 路径或旧契约版本的代码与文档

- [ ] **步骤 1：编写当前必然失败的文档同步测试**

```python
from pathlib import Path

import contract

ROOT = Path(__file__).parents[1]


def test_skill_has_no_rendering_or_stale_module_defects():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "\\n" not in skill
    for stale in (
        "commands.dispatcher", "exporters.srt", "exporters.ffmpeg",
        "from gate_g2 import", "├── gate_g2.py", "├── jianying.py",
    ):
        assert stale not in skill


def test_all_skill_references_use_existing_references_directory():
    expected = (
        "创作方法论.md", "剧本格式规范.md", "分镜表规范.md", "提示词规则.md",
        "平台契约.md", "图像生成管线实操.md", "自定义题材创作.md",
    )
    for name in expected:
        assert (ROOT / "references" / name).is_file()
    for path in (ROOT / "SKILL.md", ROOT / "README.md", ROOT / "docs" / "USER_GUIDE.md"):
        assert "reference/" not in path.read_text(encoding="utf-8")


def test_contract_version_is_consistent():
    for path in (ROOT / "SKILL.md", ROOT / "README.md", ROOT / "docs" / "USER_GUIDE.md"):
        assert contract.CONTRACT_VERSION in path.read_text(encoding="utf-8")


def test_skill_frontmatter_is_trigger_focused():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "name: nuomi-drama-skills" in skill
    assert "description: Use when" in skill
```

- [ ] **步骤 2：运行测试并确认失败**

运行：`.venv/bin/python -m pytest tests/test_docs_sync.py -v`

预期：FAIL，明确暴露字面量换行、旧路径、过时模块、`2026-06-18` 和非触发式 description。

- [ ] **步骤 3：统一参考资料目录**

运行 `git mv` 将以下文件移入 `references/`：

```text
创作方法论.md
剧本格式规范.md
分镜表规范.md
提示词规则.md
平台契约.md
```

更新仓库中所有以 `reference/` 开头的旧路径为对应的 `references/` 路径，包括 Python warning、README、用户指南、模板说明和 `SKILL.md`。

- [ ] **步骤 4：重写 SKILL.md 为阶段路由**

frontmatter 使用：

```yaml
---
name: nuomi-drama-skills
description: Use when creating, resuming, reviewing, exporting, or independently generating a Chinese vertical micro-drama or comic-drama project with nuomi manuscript files, story bibles, arc beat sheets, episode scripts, storyboards, or platform-compatible JSON.
---
```

正文控制在 500 行以内，并按以下顺序组织：

```text
核心原则与职责边界
启动或恢复项目
策划阶段
批量产集阶段
审核与门控
导出
独立生成（明确请求才允许）
参考资料路由
错误处理与交付检查
```

删除开发任务编号、虚假目录树、过时命令、重复诊断脚本和职责矛盾。保留现有模板、手稿格式、CLI 和平台兼容规则所需的最小信息。

- [ ] **步骤 5：同步 README 与用户指南**

以真实 `export.py --help`、`generate.py --help`、`contract.CONTRACT_VERSION` 和实际文件树为准：

- `generate.py` 不再声称支持不存在的 `all` 子命令。
- Provider 列表与 `providers/__init__.py` 一致。
- 所有引用统一为 `references/`。
- 用户指南使用当前契约版本 `2026-06-20`。
- 明确平台 GUI 和独立 CLI 都是可选下游，只有显式生成请求才访问 Provider。

- [ ] **步骤 6：生成 Codex 界面元数据**

先阅读 skill-creator 的 `references/openai_yaml.md`，然后使用其生成脚本创建 `agents/openai.yaml`：

```bash
python /Users/liuyuxiang05/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py . \
  --interface display_name="Nuomi 漫剧创作" \
  --interface short_description="创作、续写、审核并导出糯米短剧与漫剧项目" \
  --interface default_prompt="使用 $nuomi-drama-skills 检查当前项目进度，并建议下一步。"
```

若脚本实际参数格式与帮助不符，以 `--help` 为准调整命令，但三个界面值保持不变。

- [ ] **步骤 7：运行文档同步和技能结构验证**

运行：

```bash
.venv/bin/python -m pytest tests/test_docs_sync.py -v
python /Users/liuyuxiang05/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
rg -n 'reference/|2026-06-18|commands\.dispatcher|\\\\n' SKILL.md README.md docs/USER_GUIDE.md
```

预期：pytest 和 quick_validate PASS；`rg` 无输出。

- [ ] **步骤 8：提交技能与文档重构**

```bash
git add SKILL.md README.md docs/USER_GUIDE.md agents/openai.yaml references tests/test_docs_sync.py
git add -u reference
git commit -m "docs: align nuomi skill workflow with runtime"
```

## 任务 7：完整离线验证与技能盲测

**文件：**
- 修改：前述文件（仅当验证暴露已复现缺陷）
- 不创建：真实媒体产物、凭据文件或 live 测试产物

- [ ] **步骤 1：运行完整测试套件**

```bash
.venv/bin/python -m pytest -q
```

预期：全部 PASS，无 skip 掩盖核心离线行为。

- [ ] **步骤 2：运行语法、CLI 和示例导出验证**

```bash
.venv/bin/python -m compileall -q -x '/\.venv/' .
.venv/bin/python export.py example/manuscript /tmp/nuomi-final-export
.venv/bin/python generate.py status all --out /tmp/nuomi-final-export --json
.venv/bin/python generate.py images all --out /tmp/nuomi-final-export --dry-run --json
.venv/bin/python generate.py video all --out /tmp/nuomi-final-export --dry-run --json
python /Users/liuyuxiang05/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

预期：所有命令退出 0；导出报告 contract 为 `2026-06-20`；dry-run 不访问网络、不创建媒体文件。

- [ ] **步骤 3：验证无真实 Provider 副作用**

运行：

```bash
find /tmp/nuomi-final-export -type f \( -name '*.png' -o -name '*.jpg' -o -name '*.mp4' -o -name '*.wav' \) -print
git status --short
```

预期：find 无媒体输出；git 仅显示尚未提交的本任务相关改动或完全干净。

- [ ] **步骤 4：独立子智能体盲测技能**

使用全新子智能体，仅提供优化后的技能路径和真实用户式请求，不泄露预期答案或已修复问题：

```text
Use $nuomi-drama-skills at /Users/liuyuxiang05/Projects/liu/Skills/Nuomi-drama-skills/SKILL.md. A user opens an existing manuscript with 00_立意.md, 01_大纲.md and E1.md, then says: “继续做这部漫剧，先告诉我目前进度，不要出图。” Explain the actions you would take and which local references you would load. Do not modify files.
```

验收：子智能体先恢复进度，只加载当前阶段需要的参考资料，不调用 `generate.py` 或 Provider，不声称不存在的命令。

- [ ] **步骤 5：对盲测失败执行红—绿修订**

若盲测失败，记录其原话和误判点；先把该场景加入 `tests/test_docs_sync.py` 可机械验证的部分，再对 `SKILL.md` 做最小修订并重新盲测。若盲测通过，不做额外扩写。

- [ ] **步骤 6：最终提交**

```bash
git add SKILL.md README.md docs/USER_GUIDE.md tests
git commit -m "test: verify nuomi skill offline workflow"
```

若步骤 5 未产生修改，则跳过空提交。

- [ ] **步骤 7：检查最终历史和差异**

```bash
git status --short
git log --oneline --decorate -8
git diff b3cef09..HEAD --check
```

预期：工作树干净；所有提交均与本规格相关；diff check 无错误。
