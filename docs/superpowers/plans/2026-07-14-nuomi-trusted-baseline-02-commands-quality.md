# nuomi 可信基线（二）：命令与质量报告实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 交付 `/use-nuomi:new|review|compliance`，默认只读审查，并生成同源终端摘要、JSON 和 Markdown 报告。

**架构：** `commands/dispatcher.py` 只解析与路由；每个命令调用独立应用函数。`reports.py` 定义统一报告对象；review 规则和 `cn` 合规规则位于 `quality/`。

**技术栈：** Python、argparse、dataclasses、现有 Markdown/JSON 解析器、pytest。

---

## 文件结构

- 创建 `commands/__main__.py`、`dispatcher.py`、`new.py`、`review.py`、`compliance.py`。
- 创建 `reports.py`、`quality/review.py`、`quality/compliance.py`、`quality/profiles/cn.json`。
- 创建命令、报告和规则测试。

### 任务 1：命名空间调度与退出码

**文件：** 创建 `commands/dispatcher.py`、`commands/__main__.py`、`tests/test_dispatcher.py`；修改 `commands/__init__.py`。

- [ ] **步骤 1：写失败测试**

```python
def test_dispatches_namespaced_command():
    from commands.dispatcher import parse_command
    parsed = parse_command('/use-nuomi:review E1 --project "demo"')
    assert parsed.name == "review"
    assert parsed.argv == ["E1", "--project", "demo"]

def test_rejects_legacy_unscoped_command():
    from commands.dispatcher import parse_command
    import pytest
    with pytest.raises(ValueError, match="/use-nuomi:"):
        parse_command("/review E1")
```

- [ ] **步骤 2：运行测试，预期 FAIL。**
- [ ] **步骤 3：实现不可变 `ParsedCommand(name, argv)`、shlex 解析、`dispatch(text, stdin, stdout) -> int` 和集中退出码。**
- [ ] **步骤 4：`python -m commands '/use-nuomi:review E1 --project demo'` 必须走同一 dispatcher。**
- [ ] **步骤 5：运行测试并提交 `feat: add namespaced command dispatcher`。**

### 任务 2：统一报告模型与双格式渲染

**文件：** 创建 `reports.py`、`tests/test_reports.py`。

- [ ] **步骤 1：测试 JSON 与 Markdown 由同一 `QualityReport` 生成，均包含 schema/tool version、范围、严重级别、规则 ID、位置、摘要和建议。**
- [ ] **步骤 2：运行测试，预期 FAIL。**
- [ ] **步骤 3：实现 `Finding`、`Score`、`QualityReport` dataclass，以及 `to_dict()`、`to_markdown()`、`write_report(report, root, kind)`；输出路径使用时间戳与稳定 `latest` 副本。**
- [ ] **步骤 4：用计划一的 report Schema 验证 JSON，运行测试预期 PASS。**
- [ ] **步骤 5：提交 `feat: add versioned quality reports`。**

### 任务 3：`/use-nuomi:new` 双模式

**文件：** 创建 `commands/new.py`、`tests/test_command_new.py`；复用 `templates/`、`writing_state.py`。

- [ ] **步骤 1：测试完整参数零提问创建全部模板；缺 `tone` 时只询问 tone；目标存在无 `--resume` 时拒绝；`--resume` 不覆盖已有内容。**
- [ ] **步骤 2：运行测试，预期 FAIL。**
- [ ] **步骤 3：实现 `NewRequest` 与 `create_project(request, ask, confirm) -> Path`；参数为 `title/genre/episodes/style/tone/output/resume`。**
- [ ] **步骤 4：渲染 `00_立意.md` 时写入合法 triplet 与 episode_count，复制大纲、分卷、五表和 E1 模板；写入前输出摘要并调用 confirm。**
- [ ] **步骤 5：测试模拟 `ask`/`confirm`，不得访问 Provider；运行预期 PASS。**
- [ ] **步骤 6：提交 `feat: implement use-nuomi new wizard`。**

### 任务 4：只读 review 引擎

**文件：** 创建 `quality/review.py`、`commands/review.py`、`tests/test_review.py`、`tests/fixtures/review/`。

- [ ] **步骤 1：建立包含钩子缺失、角色未声明、伏笔窗口错误、非结构化剧本和不可拍抽象描述的 fixture。**
- [ ] **步骤 2：测试 `review_project(path, "E1-E3")` 返回结构、钩子爽点、台词、角色一致性、伏笔、格式、可拍性七维结果，且手稿哈希前后相同。**
- [ ] **步骤 3：运行测试，预期 FAIL。**
- [ ] **步骤 4：实现范围解析并复用 `manuscript_parse`、`validators`、`gates`；规则只产生 finding/score，不写文件。**
- [ ] **步骤 5：命令写 `reports/review/*.json|md` 并打印摘要；有问题返回质量退出码。**
- [ ] **步骤 6：运行测试预期 PASS，提交 `feat: add read-only drama review command`。**

### 任务 5：可扩展 compliance 与 `cn` profile

**文件：** 创建 `quality/compliance.py`、`quality/profiles/cn.json`、`commands/compliance.py`、`tests/test_compliance.py`。

- [ ] **步骤 1：fixture 覆盖阻断、风险、提示和无命中四类；测试每项均有 rule_id、location、evidence、suggestion。**
- [ ] **步骤 2：测试未知 profile 明确失败，默认 profile 为 `cn`，扫描不改手稿。**
- [ ] **步骤 3：运行测试，预期 FAIL。**
- [ ] **步骤 4：实现 `ProfileRegistry.register/load` 和数据驱动规则；`cn.json` 中每条规则声明 pattern、severity、message、suggestion、applies_to。**
- [ ] **步骤 5：生成 `reports/compliance/*.json|md`；阻断与风险映射到质量退出码。**
- [ ] **步骤 6：运行测试预期 PASS，提交 `feat: add cn compliance profile`。**

### 任务 6：命令集成验收

**文件：** 创建 `tests/test_commands_integration.py`；修改 `pyproject.toml` 增加 `use-nuomi = "commands.__main__:main"`。

- [ ] **步骤 1：在临时目录串行运行 new、review、compliance，断言模板和两类双格式报告存在。**
- [ ] **步骤 2：断言三个命令执行前后没有网络调用，review/compliance 前后手稿哈希一致。**
- [ ] **步骤 3：运行 `python -m pytest tests/test_commands_integration.py -v`，先确认失败，再补最小 CLI 接线。**
- [ ] **步骤 4：运行计划二全部测试，预期 PASS。**
- [ ] **步骤 5：提交 `feat: expose trusted use-nuomi commands`。**
