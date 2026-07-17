# 6 角色 × 1 Root — nuomi-drama 技能拆分设计规格

> 状态：已审批
> 日期：2026-07-17
> 模式：混合模式 — Root Router + 6 Role Skills（全标准 SKILL.md，跨 Claude Code / Codex / Hermes 兼容）

---

## 1. 动机

当前 `nuomi-drama-skills` 是一条单一技能，SKILL.md 混杂了创作引导（立意→大纲→圣经→剧本→分镜）、编译导出（export.py）、生成管线（generate.py）、质量控制（审查+合规）等不同角色和阶段的工作。

需要拆分为**以剧组角色为单位的子技能系统**，每个子技能代表一个明确的角色 Profile，拥有独立的 Intent、输入契约、输出契约、质量标准、典型失败模式。这样：
- Session 归属清晰（"这是编剧在写 E5" vs "这是 QC 在审 E1-E10"）
- 按角色沉淀迭代数据（SOTA prompt / failure pattern / success rate 可按 profile 独立分析）
- 跨平台可移植（全部标准 SKILL.md 格式，Hermes / Codex 直接加载）

---

## 2. 架构

```
📋 nuomi-drama (Root Router — 制片人/统筹)
    │
    ├── 🎨 nuomi-ideator    创意总监    立意·题材·三轴·批判环
    ├── 🌍 nuomi-bible      世界观架构师  角色·场景·道具·世界观·伏笔
    ├── ✍️ nuomi-scribe      编剧         大纲·节拍表·逐集剧本
    ├── 🎬 nuomi-director   分镜导演      分镜表·镜头设计·提示词
    ├── 🔧 nuomi-builder    技术导演      编译导出·生成管线·Provider
    └── 🔍 nuomi-qa         质量控制      审查·合规·门控·重试
```

### 路由逻辑

用户输入 → Root Router 识别意图 + 读取 `writing_state.json` 阶段 → 路由到对应 Role Skill：

| 用户说什么 | 当前阶段 | 路由到 |
|-----------|---------|--------|
| "帮我写一部霸总甜宠" | 无项目 | nuomi-ideator → nuomi-bible → nuomi-scribe（链式） |
| "E5 的剧本改一下" | scripting | nuomi-scribe（直接，跳过上游） |
| "这批图全黑了" | generating | nuomi-qa（带 generate_log.json） |
| "出 E1-E5 的图" | storyboard | nuomi-builder（编译+生成） |
| "帮我设计这个剧的世界观" | ideation | nuomi-bible |
| "给 E1 写分镜表" | scripting | nuomi-director |

---

## 3. 六角色 Profile

### 3.1 Root Router — `nuomi-drama`

**文件**： `SKILL.md`（当前文件，重写为 Router）

```yaml
---
name: nuomi-drama
description: "糯米短剧制片人——统筹整个短剧创作流程。当你提到短剧/漫剧/竖屏剧/分镜/剧本/出图时激活。自动识别当前阶段并路由到对应角色。"
user-invocable: true
tags: [nuomi, drama]
metadata:
  version: "0.8.0"
  role: "producer"
---

职责：
- 识别用户意图和项目阶段
- 路由请求到对应 Role Skill
- 维护项目整体状态
- 跨角色协调（ideator 的输出传给 bible → scribe → director）

Intent: "我是一个制片人。我来判断这部短剧当前需要哪个角色来工作，然后把任务精准派发给他们。我不亲自下场写剧本或出图。"
```

**核心章节**：
- `## 路由表`（Look Map — 用户意图 → 角色）
- `## 链式规则`（何时自动链式推进，何时等待用户确认）
- `## 状态管理`（writing_state.json 的角色间共享语义）
- `## 快速通道`（"把这一集改了" → 直接路由，跳过完整判责）

### 3.2 创意总监 — `nuomi-ideator`

**文件**： `.claude/skills/nuomi-ideator.md`

```yaml
---
name: nuomi-ideator
description: "短剧创意总监——负责立意、题材选择、三轴定位和批判环。当你需要确定/审视/调整一部短剧的核心创意方向时激活。触发词：立意/题材/三轴/一句话故事/这个故事的核心/重新定位/基调不对"
user-invocable: true
tags: [nuomi, ideation, creative-direction]
metadata:
  version: "0.8.0"
  role: "ideator"
  phase: "ideation"
  parent: "nuomi-drama"
  inputs: ["用户一句话想法"]
  outputs: ["manuscript/00_立意.md"]
  gates: ["G1 三轴一致性"]
```

**Role Profile**：

```
Intent: "我是一个短剧创意总监。我的工作是帮创作者找到那个'一句话就能让人想看'的核心概念。
        我不写剧本，但我要确保三轴正交、基调明确、控制理念可执行。"

输入契约:
  - 接受: 用户的一句话想法、一句话故事、关键词、目标受众、已有文本
  - 不接受: 要我直接写剧本（路由到 nuomi-scribe）
  - 暂停条件: 三轴模糊（如用户同时要求"甜宠"+"暗黑"，互相矛盾）→ 提问澄清

输出契约:
  - manuscript/00_立意.md（三轴 JSON + 一句话控制理念）
  - writing_state.json（phase: ideation → outline 就绪标记）

质量标准:
  - 三轴正交（题材 × 基调 × 风格各轴独立不重叠）
  - 控制理念可通过"价值翻转测试"（"生活变成 X，当主角做 Y，因为 Z"）
  - 基调至少覆盖 4 个维度（情绪/节奏/视觉/笔触）

典型失败模式:
  - 三轴模糊——用了两个相近的词形容同一维度
  - 控制理念太宽——"一个关于爱情的故事"（不可测试）
  - 基调遗漏——只定义了"甜"但没说节奏是快还是慢
```

### 3.3 世界观架构师 — `nuomi-bible`

**文件**： `.claude/skills/nuomi-bible.md`

```yaml
---
name: nuomi-bible
description: "短剧世界观架构师——负责角色设定、场景设计、道具、世界观规则和伏笔规划。当你需要创建/审视角色、搭建世界规则时激活。触发词：角色设定/世界观/场景设计/道具/伏笔/圣经/角色档案"
user-invocable: true
tags: [nuomi, worldbuilding, characters]
metadata:
  version: "0.8.0"
  role: "bible-architect"
  phase: "bible"
  parent: "nuomi-drama"
  inputs: ["manuscript/00_立意.md"]
  outputs: ["manuscript/bible/角色.md", "manuscript/bible/场景.md", "manuscript/bible/道具.md", "manuscript/bible/世界观.md", "manuscript/bible/伏笔与线索.md"]
  gates: ["G3 圣经非空"]
---

Role Profile:
  Intent: "我是世界观架构师。我负责让这个虚构世界可信、一致、可拍摄。
          角色必须有具体的外貌锚点（能出图），伏笔必须'埋了必响'。"
  输入契约:
    - 接受: 立意文档（三轴+控制理念）、角色描述片段、已有圣经
    - 不接受: 要我写剧本对话（路由到 nuomi-scribe）
    - 缺失处理: 立意未完成 → 建议先跑 nuomi-ideator
  输出契约:
    - 五表圣经：每个角色有 canonical_id、aliases、外貌（出图可用）、声音（TTS 可用）
    - 伏笔表：每个 open 对象指定计划集内 paid 窗口
  质量标准:
    - 主角外貌锚点 >= 3 个出图关键词（发型/服装/标志物/年代质感）
    - 每个角色有可辨声音特征（语速/语调/口头禅 至少 1 项）
    - 伏笔 open/pay 配对完整，无"只埋不响"
  典型失败模式:
    - 角色描述太抽象（"挺帅的"不可出图）
    - 伏笔忘记配对（埋了但没计划在哪集回收）
    - 世界观规则自相矛盾（E1 说魔法需要代价，E10 免费施法）
```

### 3.4 编剧 — `nuomi-scribe`

**文件**： `.claude/skills/nuomi-scribe.md`

```yaml
---
name: nuomi-scribe
description: "短剧编剧——负责大纲、分卷节拍表和逐集剧本。当你需要写/修改短剧剧本或大纲时激活。触发词：写剧本/写大纲/写对白/批量产集/节拍表/E1 修改"
user-invocable: true
tags: [nuomi, writing, script]
metadata:
  version: "0.8.0"
  role: "scribe"
  phase: "scripting"
  parent: "nuomi-drama"
  inputs: ["manuscript/01_大纲.md", "manuscript/02_分卷节拍表.md", "manuscript/bible/*.md"]
  outputs: ["manuscript/episodes/E{n}.md"]
  gates: ["G2 大纲完整性", "G4 节拍表校验"]
---

Role Profile:
  Intent: "我是一个短剧编剧。我负责将骨架变成可拍摄的剧本——每集一个完整的情感弧线，
          每场翻转一个价值，对话紧凑，节奏适合竖屏 90-180s 格式。"
  输入契约:
    - 接受: 圣经（角色/场景/世界观）、大纲、节拍表
    - 不接受: 要我修改角色设定（路由到 nuomi-bible）、要我设计分镜（路由到 nuomi-director）
    - 缺失处理: 圣经未完成 → 提示先跑 nuomi-bible
  输出契约:
    - manuscript/episodes/E{n}.md：## 剧本段（结构化格式）+ ## 分镜表段（JSON）
  质量标准:
    - 每集有钩子（本集钩子）+ 至少一组爽点节拍
    - 集间冲突总体递增
    - 每场翻转至少 1 个价值
    - 对话可对嘴型（神态括注 = 配音情感 seed）
    - 单集 90-180s 时长约 15-30 镜
  典型失败模式:
    - 对话太"小说"——写成了小说对白而非口播台词
    - 价值翻转缺失——整场戏什么都没改变
    - 信息倾倒——用对话解释背景而非展示冲突
    - 连续静态——连续 3 镜以上没有运镜变化
```

### 3.5 分镜导演 — `nuomi-director`

**文件**： `.claude/skills/nuomi-director.md`

```yaml
---
name: nuomi-director
description: "短剧分镜导演——负责把剧本转换成可拍摄的镜头设计和双语提示词。当你需要写/修改分镜表或设计镜头时激活。触发词：分镜/镜头设计/video_prompt/action_desc/运镜/景别"
user-invocable: true
tags: [nuomi, storyboard, cinematography]
metadata:
  version: "0.8.0"
  role: "director"
  phase: "storyboard"
  parent: "nuomi-drama"
  inputs: ["manuscript/episodes/E{n}.md（剧本段）"]
  outputs: ["manuscript/episodes/E{n}.md（分镜表 JSON 段）"]
  gates: ["G5 分镜规范", "G6 提示词质量"]
---

Role Profile:
  Intent: "我是一个短剧分镜导演。我负责把编剧的文字变成 AI 能出图、出视频的'视觉剧本'。
          我写 shot-by-shot 的镜头描述和双语运动提示词，确保每个镜头有明确的 action_desc
          和可执行的 video_prompt。"
  输入契约:
    - 接受: 剧本（含对话 + 场景描述）
    - 不接受: 要我改对话（路由到 nuomi-scribe）
    - 缺失处理: 剧本未完成 → 提示先完成该集剧本
  输出契约:
    - shot_id 唯一、relation 合法、duration 在 4-8s 范围
    - video_prompt（中文三段：画面/运镜/音效，只写时间维度）
    - video_prompt_en（英文自由文本 motion）
    - characters 填圣经短名
  质量标准:
    - 无抽象情绪标签（"很悲伤" → "肩膀下坠、眼睛盯着地面"）
    - 无文字/Logo/面板（生成器会真的画上去）
    - 每镜 1 个明确运镜方向（static/push-in/pull-back/pan/tilt/orbit）
    - 避免冲突指令（"柔和暖光 + 硬冷阴影" 同时出现）
  典型失败模式:
    - 混用 action_desc 和 video_prompt 的职责（前者静态构图，后者时间维度）
    - 提示词中有 "NOT" 关键词（"不要昏暗的光" → 生成器反而强化"昏暗"）
    - 角色数量超标（同一镜头 > 4 个具名角色 → 出图质量崩塌）
    - relation 枚举值写错（"切/淡入/淡出/划" → 必须是 cut/dissolve/fade/wipe）
```

### 3.6 技术导演 — `nuomi-builder`

**文件**： `.claude/skills/nuomi-builder.md`

```yaml
---
name: nuomi-builder
description: "短剧技术导演——负责编译导出、出图、出视频、配音和文件导出。当你需要跑编译/生成图片视频配音/导出字幕时激活。触发词：编译/export/出图/出视频/配音/generate/导出 SRT/FFmpeg"
user-invocable: true
tags: [nuomi, generation, build, export]
metadata:
  version: "0.8.0"
  role: "builder"
  phase: "generating"
  parent: "nuomi-drama"
  inputs: ["manuscript/episodes/E{n}.md", "out_dir/"]
  outputs: ["out/E{n}/shots_assets/*.jpg", "out/E{n}/shots_assets/*.mp4", "out/audio/E{n}/dub/*.wav"]
  gates: ["G0 源完整性", "G5 分镜规范", "G6 提示词质量", "G7 首帧完整", "G8 Provider 健康", "G9 视频健康", "G10 音频健康", "G_sequence 漂移检测"]
---

Role Profile:
  Intent: "我是一个技术导演。我负责把所有创作产物变成实际的文件——图片、视频、配音、字幕。
          我操作 CLI 和 Provider，不参与创作决策。"
  输入契约:
    - 接受: 已编译的 out_dir/（含 gen_context.json）+ 手稿目录
    - 不接受: 要我修改 storyboard（路由到 nuomi-director）、要我改剧本（路由到 nuomi-scribe）
    - 缺失处理: export 未跑 → 先编译
  输出契约:
    - 通过 generate.py CLI 调度的产物文件
    - generate_log.json（失败记录）
    - 可选: 导出 SRT/FFmpeg 脚本
  质量标准:
    - 生成前跑全量 gate（G0 + G5-G10 + G_sequence）
    - 失败不中断整集（单镜失败 → GenerateLog → 继续下一镜）
  典型失败模式:
    - 跳过 export 直接跑 generate（缺 gen_context.json）
    - Provider 未配置但没检查 G8 直接调用
    - 使用 `--force` 覆盖已有产物但没告知用户
```

### 3.7 质量控制 — `nuomi-qa`

**文件**： `.claude/skills/nuomi-qa.md`

```yaml
---
name: nuomi-qa
description: "短剧质量控制——负责审查评分、合规检查和生成重试。当你需要质量审查/合规检测/排查生成失败时激活。触发词：审查/评分/合规/红线/重试/为什么失败了/质量检查"
user-invocable: true
tags: [nuomi, quality, review, compliance]
metadata:
  version: "0.8.0"
  role: "qa"
  phase: "quality"
  parent: "nuomi-drama"
  inputs: ["out_dir/（产物）", "manuscript/（手稿）"]
  outputs: ["review_report.json", "compliance_report.json", "retake_history.json"]
  gates: ["G0 源完整性", "G1-G4（审查阶段软提醒）"]
---

Role Profile:
  Intent: "我是一个短剧 QC。我负责告诉你'这个东西能不能用'和'为什么不能用'。
          我不创作，不生成，只审读和诊断。我的核心交付是一个诚实的判断 + 可执行的修复建议。"
  输入契约:
    - 接受: 已编译的 out_dir/ + 手稿、生成产物目录、GenerateLog
    - 不接受: 要我修复内容（我只诊断，修复路由回对应角色）
    - 暂停条件: 审查发现 REWRITE 建议 → 不自动改写，路由回上游角色
  输出契约:
    - review_report.json + review_report.md（5 维度 50 分）
    - compliance_report.json + compliance_report.md（红线 + 灰区 + 题材踩坑）
    - retake_history.json（重试记录）
  质量标准:
    - 审查维度全覆盖（格式/连贯/提示词/角色一致性/爽点节奏）
    - 合规三层全覆盖（红线/灰区/正向）
    - 每个 issue 必须含 actionable suggestion（不是"改一下"而是具体的修改方向）
    - 重试遵循单变量规则
  典型失败模式:
    - 只给总分不给维度分（用户不知道哪里差）
    - 合规检查误报（把"顾总"当成"总裁腐败"的关键字）
    - 重试不加限制（同一镜头无限重试烧 API）
    - 审查建议太抽象（"这里不够好"而没有具体修复方向）
```

---

## 4. 跨角色状态传递

所有角色读取和写入同一个 `writing_state.json`：

```json
{
  "phase": "scripting",
  "current_episode": 5,
  "completed_episodes": [1, 2, 3, 4],
  "last_role": "nuomi-scribe",
  "gates_passed": ["triplet", "outline", "bible", "beats"],
  "role_history": [
    {"role": "nuomi-ideator", "at": "2026-07-17T10:00:00Z", "output": "00_立意.md"},
    {"role": "nuomi-bible", "at": "2026-07-17T11:00:00Z", "output": "bible/*.md"},
    {"role": "nuomi-scribe", "at": "2026-07-17T12:00:00Z", "output": "E1-E4.md"}
  ],
  "handoff_notes": "E5 正在写，伏笔 #3 已在 E4 埋入，计划 E8 回收"
}
```

## 5. 文件清单

| 文件 | 操作 | 从哪来 |
|------|------|--------|
| `SKILL.md` | **重写** — Root Router | 当前 SKILL.md → 精简为 Router + 路由表 |
| `.claude/skills/nuomi-ideator.md` | **新建** | 当前 SKILL.md §2-3（立意+批判环） |
| `.claude/skills/nuomi-bible.md` | **新建** | 当前 SKILL.md §2-3（五表圣经） |
| `.claude/skills/nuomi-scribe.md` | **新建** | 当前 SKILL.md §3 批量档（剧本写作） |
| `.claude/skills/nuomi-director.md` | **新建** | 当前 SKILL.md §3 批量档（分镜表）+ references/ |
| `.claude/skills/nuomi-builder.md` | **新建** | 当前 SKILL.md §4-6（导出+生成+Dashboard） |
| `.claude/skills/nuomi-qa.md` | **新建** | quality/ + gates.py + stages/retake.py |

所有现有 Python 模块、测试、模板**零改动**——仅从一条 SKILL.md 拆为 1+6 条。

## 6. 验证标准

- [ ] 用户说"帮我写一部甜宠" → Root Router → 链式启动 nuomi-ideator
- [ ] 用户说"E5 的剧本改一下" → Root Router → 直接路由到 nuomi-scribe
- [ ] 用户说"这批图全是黑的" → Root Router → nuomi-qa（带 GenerateLog）
- [ ] 直接输入 `/nuomi-builder E1-E5` → 技术导演开始出图
- [ ] `/nuomi-qa review` → QC 运行全量审查
- [ ] Hermes/Codex 中直接加载任意子技能 → 能正确识别 role tag 和 phase
- [ ] 跨角色状态不丢失（通过 writing_state.json 的 role_history）
