# nuomi 可信基线（一）：安全、配置与契约实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 清除凭据发布风险，建立可复现安装、统一配置、稳定错误类型、版本化 JSON 契约与安全原子导出。

**架构：** 保留顶层模块入口，新增小型 `config.py`、`errors.py` 与 `contracts/`。`export_project` 先写同盘 staging，再经 Schema 验证和目录交换发布；现有运行资产由集中 merge policy 保留。

**技术栈：** Python 3.9–3.12、pytest、jsonschema、pathlib、argparse。

---

## 文件结构

- 创建 `.gitignore`、`.env.example`、`pyproject.toml`：发布与依赖基线。
- 创建 `config.py`：`.env`、系统环境与显式覆盖的唯一加载入口。
- 创建 `errors.py`：错误码、退出码和脱敏异常。
- 创建 `contracts/validator.py` 与 `contracts/schemas/*.json`：版本化契约。
- 创建 `merge_policy.py`、`atomic_output.py`：资产保留和目录交换。
- 修改 `providers/__init__.py`、`generate.py`、`export.py`、`emit.py`、`contract.py`。
- 创建对应 `tests/` 与 fixtures。

### 任务 1：发布卫生与依赖清单

**文件：** 创建 `.gitignore`、`.env.example`、`pyproject.toml`、`tests/test_release_hygiene.py`；删除 `skill.env`；保留 `skill.env.example` 一个版本后仅作迁移提示。

- [ ] **步骤 1：写失败测试**

```python
from pathlib import Path

ROOT = Path(__file__).parents[1]

def test_release_tree_has_no_secrets_or_caches():
    assert not (ROOT / "skill.env").exists()
    assert not list(ROOT.rglob("__pycache__"))
    assert (ROOT / ".env.example").is_file()

def test_project_metadata_declares_runtime_and_test_dependencies():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for name in ("flask", "numpy", "pillow", "jsonschema", "pytest"):
        assert name in text.lower()
```

- [ ] **步骤 2：运行并确认失败**

运行：`python -m pytest tests/test_release_hygiene.py -v`

预期：FAIL，指出 `skill.env`、缓存和 `pyproject.toml` 问题。

- [ ] **步骤 3：最小实现**：补齐元数据与忽略规则，删除真实配置和缓存；`.env.example` 只保留空值或明显占位符。
- [ ] **步骤 4：运行 `python -m pytest tests/test_release_hygiene.py -v`，预期 PASS。**
- [ ] **步骤 5：提交**：`git commit -m "build: establish secure package metadata"`。

### 任务 2：统一配置优先级

**文件：** 创建 `config.py`、`tests/test_config.py`；修改 `providers/__init__.py`、`generate.py`。

- [ ] **步骤 1：写失败测试**

```python
def test_cli_overrides_environment_and_dotenv(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("IMAGE_PROVIDER=grsai\nIMAGE_WIDTH=640\n", encoding="utf-8")
    monkeypatch.setenv("IMAGE_PROVIDER", "gemini")
    from config import load_config
    cfg = load_config(tmp_path, {"IMAGE_PROVIDER": "comfyui"})
    assert cfg["image_provider"] == "comfyui"
    assert cfg["image_width"] == 640

def test_config_repr_never_contains_secret(tmp_path):
    (tmp_path / ".env").write_text("GRSAI_API_KEY=top-secret\n", encoding="utf-8")
    from config import load_config
    assert "top-secret" not in repr(load_config(tmp_path))
```

- [ ] **步骤 2：运行测试，预期 FAIL，`config` 模块不存在。**
- [ ] **步骤 3：实现 `load_config(project_dir: Path, overrides: dict | None = None) -> dict`，仅解析 `KEY=VALUE`，按 `.env → os.environ → overrides` 合并并转换数值。**
- [ ] **步骤 4：让 `providers.load_config()` 委托新模块；`generate.main()` 不再读取 `skill.env`。**
- [ ] **步骤 5：运行 `python -m pytest tests/test_config.py -v`，预期 PASS。**
- [ ] **步骤 6：提交**：`git commit -m "feat: centralize secure configuration loading"`。

### 任务 3：错误码与脱敏

**文件：** 创建 `errors.py`、`tests/test_errors.py`；修改 `generate.py`、`provider_chain.py`。

- [ ] **步骤 1：测试 `NuomiError(code, message, exit_code, retryable)` 的字符串表示会把 `sk-*`、`rh-*`、Bearer token 替换为 `[REDACTED]`。**
- [ ] **步骤 2：运行测试，预期 FAIL。**
- [ ] **步骤 3：实现 `ErrorCode` 枚举、`ExitCode` IntEnum、`redact(text)` 和 `NuomiError`；Provider 异常映射只保存脱敏摘要。**
- [ ] **步骤 4：运行 `python -m pytest tests/test_errors.py -v`，预期 PASS。**
- [ ] **步骤 5：提交**：`git commit -m "feat: add stable redacted error contracts"`。

### 任务 4：版本化 Schema 验证器

**文件：** 创建 `contracts/__init__.py`、`contracts/validator.py`、`contracts/schemas/{series,arcs,story-bible,gen-context,registry,report,provider-error}.schema.json`、`tests/test_contracts.py`。

- [ ] **步骤 1：测试 `validate_document("series", valid)` 返回空列表，缺 `schema_version` 或错误 `episode_count` 返回带 JSON Pointer 的问题。**
- [ ] **步骤 2：运行测试，预期 FAIL。**
- [ ] **步骤 3：实现接口：**

```python
import json
from dataclasses import dataclass
from pathlib import Path
from jsonschema import Draft202012Validator

@dataclass(frozen=True)
class ContractIssue:
    document: str
    pointer: str
    message: str

def validate_document(name: str, data: dict) -> list[ContractIssue]:
    schema_path = Path(__file__).parent / "schemas" / f"{name}.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    return [ContractIssue(name, "/" + "/".join(map(str, e.path)), e.message) for e in errors]

def validate_project(project_dir: Path) -> list[ContractIssue]:
    files = {"series": "series.json", "arcs": "arcs.json",
             "story-bible": "story_bible.json", "registry": "assets/registry.json"}
    issues = []
    for name, relative in files.items():
        path = project_dir / relative
        data = json.loads(path.read_text(encoding="utf-8"))
        issues.extend(validate_document(name, data))
    for path in sorted(project_dir.glob("E*/gen_context.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        issues.extend(validate_document("gen-context", data))
    return issues
```

- [ ] **步骤 4：Schema 统一要求 `schema_version`，并对现有平台 loader 允许的顶层键使用明确 `properties`；不得凭空收紧现有可选字段。**
- [ ] **步骤 5：用 `example/manuscript` 导出结果建立 fixtures，运行 `python -m pytest tests/test_contracts.py -v`，预期 PASS。**
- [ ] **步骤 6：提交**：`git commit -m "feat: add versioned platform schemas"`。

### 任务 5：集中资产合并策略

**文件：** 创建 `merge_policy.py`、`tests/test_merge_policy.py`；修改 `emit.py`。

- [ ] **步骤 1：覆盖 `episode_digests`、ready 锚图、`shots_assets`、`anchors`、`audio`、未知运行键在重复导出后仍保留，手稿拥有字段更新。**
- [ ] **步骤 2：运行测试，预期至少一项失败。**
- [ ] **步骤 3：实现 `merge_owned(existing, owned, defaults, preserved_paths)`，所有保留路径集中声明；`emit.py` 不再散落特殊分支。**
- [ ] **步骤 4：运行 `python -m pytest tests/test_merge_policy.py -v`，预期 PASS。**
- [ ] **步骤 5：提交**：`git commit -m "refactor: centralize platform asset merge policy"`。

### 任务 6：验证后发布的目录交换

**文件：** 创建 `atomic_output.py`、`tests/test_atomic_export.py`；修改 `export.py`、`contract.py`。

- [ ] **步骤 1：测试契约失败时正式目录字节不变；成功时正式目录更新且运行资产保留；交换异常时恢复原目录。**
- [ ] **步骤 2：运行测试，预期 FAIL。**
- [ ] **步骤 3：实现同盘 staging：复制现有输出到 staging、调用 emit、运行 `validate_project`、将旧目录改名为 backup、staging 改名为正式目录，异常时回滚。**
- [ ] **步骤 4：把 `CONTRACT_VERSION` 与 `schema_version` 更新为同一发布日期，并在导出报告中返回。**
- [ ] **步骤 5：运行 `python -m pytest tests/test_atomic_export.py tests/test_contracts.py -v`，预期 PASS。**
- [ ] **步骤 6：运行完整离线测试 `python -m pytest -m "not live" -q`。**
- [ ] **步骤 7：提交**：`git commit -m "feat: validate and atomically publish exports"`。
