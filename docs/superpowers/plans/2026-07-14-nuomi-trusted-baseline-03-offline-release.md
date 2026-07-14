# nuomi 可信基线（三）：离线端到端与发布实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 用 fake Provider 和 Golden fixtures 证明完整离线链路，统一任务日志，消除文档漂移并建立发布门禁。

**架构：** fake Provider 实现现有抽象并生成确定性小产物；`GenerateLog` 升级为状态事件；端到端测试串起命令、导出、生成和状态；发布审计脚本校验文档、敏感文件与包内容。

**技术栈：** Python、pytest markers、JSONL、GitHub Actions、现有 CLI。

---

## 文件结构

- 创建 `providers/fake.py`、`tests/test_fake_provider.py`。
- 修改 `stages/__init__.py`、`stages/status.py`、生成阶段和 `provider_chain.py`。
- 创建 `tests/golden/`、`tests/test_offline_e2e.py`、`scripts/release_audit.py`、CI 配置。
- 修改 README、SKILL、USER_GUIDE、CHANGELOG 与迁移文档。

### 任务 1：确定性 fake Provider

**文件：** 创建 `providers/fake.py`、`tests/test_fake_provider.py`；修改 `providers/__init__.py`、`provider_chain.py`。

- [ ] **步骤 1：测试同一输入生成相同 PNG/WAV/MP4 fixture 字节，不访问 socket；可通过配置按 shot 注入 retryable 或 terminal failure。**
- [ ] **步骤 2：运行测试，预期 FAIL。**
- [ ] **步骤 3：实现同时满足 ImageProvider、VideoGroupProvider、DubProvider、GridUpscaleProvider 的 `FakeProvider`；输出由输入 SHA-256 决定。**
- [ ] **步骤 4：`IMAGE_PROVIDER=fake` 和显式测试注入都能选择它，但生产默认值保持不变。**
- [ ] **步骤 5：运行测试预期 PASS，提交 `test: add deterministic fake media provider`。**

### 任务 2：结构化任务状态与安全日志

**文件：** 修改 `stages/__init__.py`、`stages/status.py`、`stages/images.py`、`stages/video.py`、`stages/dub.py`、`stages/voice_design.py`；创建 `tests/test_generate_log.py`。

- [ ] **步骤 1：测试事件包含 task_id、stage、ep、shot_id、state、attempt、provider、error_code、retryable、timestamp，且密钥被脱敏。**
- [ ] **步骤 2：测试状态只允许 `pending/running/succeeded/failed/skipped`，非法转换拒绝。**
- [ ] **步骤 3：运行测试，预期 FAIL。**
- [ ] **步骤 4：将 `GenerateLog.append(error)` 升级为 `record(TaskEvent)`；保留旧 JSONL 读取迁移，写出只用新格式。**
- [ ] **步骤 5：所有 stage 在调用前写 running，完成写 succeeded，异常写 failed；重试次数有上限且只针对 retryable。**
- [ ] **步骤 6：运行测试预期 PASS，提交 `feat: add resumable structured generation log`。**

### 任务 3：Golden 编译基线

**文件：** 创建 `tests/golden/minimal-series/manuscript/`、`expected/`、`tests/test_golden_export.py`。

- [ ] **步骤 1：从现有 example 蒸馏最小两集 fixture，expected 包含 series、arcs、story_bible、registry、harness_state 与两个 gen_context。**
- [ ] **步骤 2：测试导出 JSON 去除绝对路径和时间字段后逐字段等于 expected；重复导出结果相同。**
- [ ] **步骤 3：运行测试，确认当前结果与批准 expected 的差异并人工核对一次。**
- [ ] **步骤 4：只修复契约或合并差异，不通过更新 expected 掩盖回归。**
- [ ] **步骤 5：运行预期 PASS，提交 `test: freeze golden platform export contract`。**

### 任务 4：完整离线端到端

**文件：** 创建 `tests/test_offline_e2e.py`、`tests/conftest.py`。

- [ ] **步骤 1：临时目录执行 `new → review → compliance → export → fake images/video/dub → status`。**
- [ ] **步骤 2：断言所有 JSON 通过 Schema、报告双格式存在、状态最终 succeeded、`--dry-run` 零 Provider 调用。**
- [ ] **步骤 3：注入一次 retryable 和一次 terminal failure，验证有限重试、批次继续及 `--retry-failed`。**
- [ ] **步骤 4：运行 `python -m pytest tests/test_offline_e2e.py -v`，先确认失败，再补最小接线。**
- [ ] **步骤 5：运行预期 PASS，提交 `test: cover complete offline production flow`。**

### 任务 5：文档与 CLI 一致性门禁

**文件：** 创建 `scripts/release_audit.py`、`tests/test_docs_sync.py`；修改 `README.md`、`SKILL.md`、`docs/USER_GUIDE.md`。

- [ ] **步骤 1：测试文档引用的本地文件存在，SKILL 不含字面量 `\\n`，章节顺序递增，契约版本等于 `contract.py`。**
- [ ] **步骤 2：测试文档声明的 stage/option 是真实 `--help` 子集，命令只使用 `/use-nuomi:*`。**
- [ ] **步骤 3：运行测试，预期暴露当前 dispatcher、`all`、`voice-design`、版本和章节漂移。**
- [ ] **步骤 4：以真实实现为准修正文档；能力存在才写已交付，否则明确标注路线图。**
- [ ] **步骤 5：运行预期 PASS，提交 `docs: align skill documentation with runtime`。**

### 任务 6：发布审计与 CI

**文件：** 创建 `.github/workflows/ci.yml`、`CHANGELOG.md`、`docs/MIGRATION.md`；修改 `scripts/release_audit.py`、`pyproject.toml`。

- [ ] **步骤 1：release audit 扫描 `.env`、`skill.env`、私钥/API Key 模式、缓存、生成产物、缺失许可证和未声明依赖。**
- [ ] **步骤 2：CI 在 3.10、3.11、3.12 运行 `pytest -m "not live"`、Schema、Golden、文档同步和 build；3.9 作为允许失败的兼容任务。**
- [ ] **步骤 3：真实冒烟测试标记 `@pytest.mark.live`，无凭据时 skip，默认工作流永不选择 live。**
- [ ] **步骤 4：运行 `python scripts/release_audit.py .` 与 `python -m pytest -m "not live" -q`，预期均为 0。**
- [ ] **步骤 5：在空临时目录安装构建产物并执行命令帮助与离线 e2e。**
- [ ] **步骤 6：提交 `build: enforce trusted offline release gate`。**
