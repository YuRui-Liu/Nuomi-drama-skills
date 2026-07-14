# nuomi-drama-skills 可信基线设计

**日期：** 2026-07-14

**状态：** 已批准

**目标：** 在保留创作、编译、图片、视频、配音、预览与剪映能力的前提下，建立安全、可安装、契约明确、默认离线可验证的可信基线。

## 1. 成功标准

- 发布包不包含真实凭据、缓存和生成产物。
- 空目录安装后可完成离线演示。
- `/use-nuomi:new|review|compliance` 行为稳定且有回归测试。
- 手稿、平台 JSON、质量报告和 Provider 错误拥有版本化契约。
- 默认测试完全离线，不调用 Provider、不消耗 API 额度。
- README、SKILL、CLI 帮助和真实模块一致。

## 2. 范围

第一阶段包含安全配置、Python 项目元数据、版本化 Schema、统一错误码、命名空间命令、JSON/Markdown 报告、fake Provider、Golden fixtures、离线端到端测试、文档及发布验收。

第一阶段不包含 review 自动改稿、`cn` 之外的合规规则、新增真实 Provider、Seedance 在线提交与 SSE、全面包结构重写、Web 预览重做或 CI 真实媒体生成。

## 3. 架构

保留 `export.py`、`generate.py` 等现有入口。新增命令适配层；旧 CLI 与新命令调用同一应用服务，禁止复制规则。

1. **命令层**：命名空间、参数、终端输出、退出码。
2. **应用层**：新建、审查、合规、导出、媒体生成。
3. **契约与领域层**：手稿模型、平台 Schema、报告 Schema、Gate、评分、状态机。
4. **基础设施层**：配置、文件报告、Provider、平台适配、日志、原子写入。

数据流为：`命令或 Skill 对话 → 应用服务 → 契约校验 → 手稿或报告 → export → 平台项目 → generate`。

`manuscript/` 是创作事实源；媒体产物与运行状态不回写手稿；review 与 compliance 默认只读；网络能力只能位于 Provider 边界。

## 4. 命令契约

### `/use-nuomi:new`

- 无参数进入逐问向导；支持 `--title`、`--genre`、`--episodes`、`--style`、`--tone`、`--output` 快速参数。
- 参数不完整时只追问缺失项；写入前显示摘要并确认。
- 只创建模板、状态和项目配置，不调用媒体 Provider。
- 目标存在时默认拒绝覆盖；`--resume` 恢复未完成项目。

### `/use-nuomi:review`

- 支持单集、范围、整卷和 `all`。
- 默认只读，检查结构、钩子与爽点、台词、角色一致性、伏笔、格式和可拍性。
- 终端显示摘要，同时输出版本化 JSON 与 Markdown 报告。
- 第一阶段不提供自动修复。

### `/use-nuomi:compliance`

- 第一阶段只交付 `cn`，但保留 profile 注册接口。
- 结果分为阻断、风险、提示；每项包含规则 ID、位置、证据摘要和建议。
- 默认只读，同时输出终端摘要、JSON 与 Markdown 报告。

退出码集中定义并区分成功、质量或合规问题、输入无效、契约失败、Provider 失败和系统错误。

## 5. 配置与安全

配置优先级为：`命令行显式参数 > 系统环境变量 > 项目本地 .env > 安全默认值`。

- `.env` 被 Git 与发布包忽略，只发布无真实值的 `.env.example`。
- `skill.env` 退出正式配置路径；迁移只提示，不输出或复制密钥。
- 已随目录存在的真实凭据按可能暴露处理并轮换。
- 日志不得打印 API Key、认证头、含密钥 URL 或敏感响应。

## 6. 数据与报告契约

分镜 JSON、`series.json`、`arcs.json`、`story_bible.json`、`gen_context.json`、资源注册表、运行状态、review/compliance 报告以及 Provider 请求/结果/错误均拥有版本化 Schema。

兼容策略是“读取当前版及明确支持的旧版，只写当前版”。导出先在同盘临时目录完成编译和校验，再替换正式输出；平台媒体资产按集中 merge policy 保留。

JSON 与 Markdown 报告由同一内存对象渲染，包含工具版本、Schema 版本、范围、时间、结果、位置、严重级别、摘要和建议。

## 7. 错误与恢复

错误分为输入、契约、质量、Provider 和系统五类，映射到稳定错误码、退出码和脱敏消息。

媒体任务状态为 `pending → running → succeeded | failed | skipped`。单镜失败不终止整批；仅超时、限流和临时异常有限重试；鉴权、参数、内容拒绝不重试；`--retry-failed` 只处理失败且无产物任务；`--force` 才覆盖成功产物；`--dry-run` 保证零网络调用。

## 8. 测试与发布

测试包含单元、契约、Golden、离线端到端和显式真实冒烟五层。暂保 Python 3.9，主要矩阵为 3.10–3.12。`pyproject.toml` 统一依赖、CLI、pytest 与打包规则。

发布前必须通过全部离线测试、文档/CLI 一致性、敏感文件扫描和空目录安装演示；真实 Provider 冒烟结果独立记录，不是默认 CI 阻断项。

## 9. 实施顺序

1. 安全、配置、契约与原子导出。
2. `/use-nuomi:new|review|compliance` 与统一报告。
3. fake Provider、离线端到端、文档同步和发布验收。
