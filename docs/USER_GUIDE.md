# 糯米短剧创作助手 · 用户指南

> **适用版本**：nuomi-drama-skills v2+（契约版本 2026-06-20）
> **前置知识**：你用过 Claude Code，知道如何配置环境变量和运行 Python 脚本。
> **目标产物**：一份可导入"糯米短剧平台"的完整短剧项目文件夹，含剧本、分镜表和后续出图/出视频/配音的所有上游输入。

---

## 一、快速上手（10 分钟出第一部剧）

### 1.1 前置准备

**第一步：配置 skill.env**

从 `skill.env.example` 复制一份为 `skill.env`，至少填一个图片 provider 的凭据。最简配置（用 Gemini 出图）：

```bash
# 至少配一个：
IMAGE_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
```

如果你有 Grsai 或 RunningHub，也可以配到对应字段。完整字段说明见表（见第四节）。

**第二步：触发技能**

在 Claude Code 中打开你的工作目录，直接说：

```
帮我创作一部竖屏短剧
```

Claude 就会按照 nuomi-drama-skills 的方法论，分阶段引导你一步一步完成创作。

### 1.2 5 步出剧

整个创作流程分为 5 个阶段，每阶段产出一批 `manuscript/*.md` 文件：

```
步骤 1 ──→ 立意        → manuscript/00_立意.md
步骤 2 ──→ 大纲        → manuscript/01_大纲.md
步骤 3 ──→ 五表圣经    → manuscript/bible/角色.md / 场景.md / 道具.md / 世界观.md / 伏笔与线索.md
步骤 4 ──→ 分卷+剧本+分镜 → manuscript/02_分卷节拍表.md + episodes/E1.md ... EN.md
步骤 5 ──→ 编译导出    → python export.py manuscript/ out/
```

步骤 5 跑通后，`out/` 文件夹直接丢进糯米短剧平台即可导入。平台读到的所有 JSON 均来自编译——**永远不要手改 `out/` 里的 JSON**，只改 `manuscript/` 手稿然后重新 export。

---

## 二、创作阶段详解

### 2.1 立意与三轴

立意是整部剧的高杠杆上游件——跑偏会污染下面每一集。三轴必须正交：

| 轴 | 含义 | 示例 |
|----|------|------|
| 题材（genre_id） | 故事类型 | `revenge` / `rebirth` / `time-travel` |
| 风格（style_id） | 视觉风格 | `real/cinematic-warm-v1` / `2D/anime-cel-v1` |
| 基调（tone） | 四维 + 人物弧光 | 见下方词表 |

**内置题材（20+）**：

```
ceo-romance / commercial / counterattack / face-slap / mv / oral-skit
short-drama / single-episode / vlog / war-god-return / rebirth / time-travel
son-in-law / chase-wife / revenge / divine-doctor / system-rich / war-god
urban-xianxia / palace-intrigue / school-rising / group-pet
```

**内置风格（11 种）**：

| 类别 | style_id | 中文名 |
|------|----------|--------|
| real | `real/cinematic-warm-v1` | 电影暖调 |
| real | `real/cinematic-cool-v1` | 电影冷调 |
| real | `real/doc-natural-v1` | 纪实自然 |
| real | `real/golden-hour-romance-v1` | 金色浪漫 |
| 2D | `2D/anime-cel-v1` | 赛璐珞动画 |
| 2D | `2D/guofeng-ink-v1` | 国风水墨 |
| 2D | `2D/ghibli-warm-v1` | 吉卜力暖色 |
| 2D | `2D/guofeng-gongbi-v1` | 国风工笔 |
| 3D | `3D/pixar-stylized-v1` | 皮克斯风格 |
| 3D | `3D/photoreal-octane-v1` | Octane 写实 |
| 3D | `3D/pixar-cute-v1` | 皮克斯可爱 |

**基调四维（缺一不可）**：

| 维度 | 可选档位 |
|------|----------|
| 情感温度 | `冷峻` / `克制` / `温暖` / `炽热` |
| 动作密度 | `纯文戏` / `文武均衡` / `强动作` |
| 叙事节奏 | `舒缓` / `稳健` / `快切` / `高频反转` |
| 主题深度 | `纯爽无负担` / `轻寓意` / `厚重思辨` |

**人物弧光**：`成长型` / `觉醒型` / `救赎型` / `双向救赎` / `堕落型` / `悲剧型` / `坚守型`

**一句话控制理念公式**：

> 生活变成 X，当主角做 Y，因为 Z。

举例：「平静的钟表店生活变成一场血腥复仇，当林夏发现父亲的死亡背后藏着钟楼的秘密，因为她不能容忍至亲含冤而死。」

**完整立意示例**（来自 `manuscript/00_立意.md`）：

```markdown
# 立意:《旧约钟楼》

民国上海，钟表匠之女林夏发现父亲死亡背后的钟楼秘密，踏上复仇与自赎之路。

​```json
{"triplet": {"题材": {"genre_id": "revenge", "display_name": "复仇"},
             "风格": {"style_id": "real/cinematic-warm-v1", "category": "real", "name_cn": "电影暖调"},
             "基调": {"levels": {"情感温度": "克制", "动作密度": "文武均衡", "叙事节奏": "稳健", "主题深度": "厚重思辨"}, "arc": "觉醒型"}},
 "mode": "series", "episode_count": 2}
​```
```

> **注意**：`genre_id` 不在内置列表时需自定义题材 YAML（见第五节）。

---

### 2.2 大纲

大纲定义整部剧的全集结构。每集必须有钩子（结尾留扣）和爽点节拍（情绪高点序列），集间冲突总体递增。

```json
{"series_logline": "钟表匠之女为父复仇",
 "主线": "林夏揭开钟楼灭门真相",
 "副线": ["林夏与沈砚的信任"],
 "episodes": [
   {"ep": 1, "标题": "停摆的钟", "梗概": "林夏归家见父亡",
    "本集钩子": "钟楼齿轮藏血字",
    "爽点节拍": ["归家", "发现尸体", "血字"],
    "出场角色": ["林夏"], "关键场景": ["钟楼"]},
   {"ep": 2, "标题": "齿轮之名", "梗概": "林夏循血字查到沈砚",
    "本集钩子": "沈砚竟是旧识",
    "爽点节拍": ["追查", "对峙"],
    "出场角色": ["林夏", "沈砚"], "关键场景": ["茶楼"],
    "上集衔接": "承接血字"}]}
```

**大纲纪律**：
- `episode_count` 必须覆盖全部集数，与立意中的声明一致
- 每集钩子是"本集结尾留什么扣子让观众非看下一集不可"
- 爽点节拍不是剧情梗概，是本集情绪高点（打脸/逆袭/反转/真相/奇观）
- 可选字段 `上集衔接` / `出场角色` / `关键场景` 增强可读性，不强制

---

### 2.3 五表圣经

圣经是跨集一致性的唯一载体。逐集创作前，先读圣经再写剧本。

#### 2.3.1 角色

每个角色一条，key 用短名（canonical id）。`外貌` 是出图锚点，必须写实够细以便平台生成一致的参考图。

```json
{"characters": {
  "林夏": {"身份": "钟表匠之女", "外貌": "民国短发，素色旗袍，眼神坚定",
           "性格": "外冷内炽", "动机": "为父复仇",
           "关系网": {"沈砚": "旧识"},
           "arc": [{"at_ep": 1, "情感状态": "震惊", "处境": "丧父", "已知": "血字"}],
           "aliases": []},
  "沈砚": {"身份": "茶楼掌柜", "外貌": "清瘦长衫，左手戴怀表",
           "性格": "深沉", "动机": "守钟楼秘密",
           "关系网": {"林夏": "旧识"},
           "arc": []}}}
```

**关键细节**：
- 键名用短名（`林夏` 而非 `林夏（钟表匠之女）`）。写错了也不怕——`export.py` 会自动剥离括号、括号内容进 `aliases`
- `外貌` 要写到"可以直接生成角色定妆图"的精度：发型/服装/年代/标志物
- `arc` 是可选字段，用来追踪角色在每集的情感状态/处境/已知信息，按需追加
- 声音特征可埋入圣经（语域/音色/口头禅），平台会自动映射到 TTS 音色设计

#### 2.3.2 场景

```json
{"scenes": {"钟楼": {"描述": "废弃钟楼", "appearance": "民国哥特钟楼，锈蚀齿轮，昏黄天光"},
            "茶楼": {"描述": "沈砚茶楼", "appearance": "二层木构茶楼，雕花窗，暖灯"}}}
```

- `appearance` 用于平台出图（空间/年代/光线/材质/氛围）
- `描述` 进资源库说明

#### 2.3.3 道具

```json
{"props": {
  "怀表": {"描述": "沈砚随身携带，左手常握，工艺精细，背面有刻字",
           "appearance": "民国银质怀表，表盖有轻微磨损，背面刻繁体字，附短链"},
  "血字齿轮": {"描述": "钟楼最大齿轮，背面用血写有关键线索文字",
               "appearance": "锈蚀铁质大齿轮，直径约1米，背面有暗红色血迹文字，工业感"}}}
```

#### 2.3.4 世界观

`canon` 是不可违背的硬事实库。每条一个 id 对应一句事实。

```json
{"canon": {
  "C1": "故事发生于1930年代民国上海，无现代科技与通讯",
  "C2": "钟楼是城中地标，常人不得擅入，守门人为林父生前好友",
  "C3": "角色间的信任建立极难、崩塌极易——这是全剧的核心张力"}}
```

后续剧本中任何与 canon 冲突的情节，都会在批判环中被揪出。

#### 2.3.5 伏笔与线索

```json
{"foreshadows": {"F1": {"描述": "齿轮血字", "埋设集": 1, "计划回收集": 2,
                         "状态": "open", "相关人物": ["林夏", "沈砚"]}},
 "threads": {"T1": {"描述": "灭门真相主线", "涉及卷": ["1"],
                     "当前进度": "开端", "状态": "active"}}}
```

**铁律：埋了必响**。每条伏笔必须有明确的埋设集和计划回收集。`open` 的对象/台词必须在指定集内 `paid`（契诃夫之枪原则）。

---

### 2.4 分卷节拍表

把全剧拆成若干卷（arc），每卷一张节拍表。节拍钉到目标集、关联 thread、关联伏笔，且节拍按目标集递增。

```json
{"arcs": [{"arc": 1, "目标": "复仇序章", "集": [{"ep": 1}, {"ep": 2}],
          "threads": ["T1"],
          "伏笔计划": [{"id": "F1", "开窗集": 1, "回收集": 2}],
          "节拍": [{"beat": "激励事件", "功能": "开场钩", "目标集": 1,
                   "关联thread": ["T1"], "关联伏笔": ["F1"]},
                  {"beat": "卷末对峙", "功能": "升级冲突", "目标集": 2,
                   "关联thread": ["T1"], "关联伏笔": ["F1"]}],
          "出场角色": ["林夏", "沈砚"]}]}
```

**节拍纪律**（`validate_beats` 会逐卷检查）：
- `目标集` 必须落在本卷 `集` 范围内
- `关联thread` 必须已在卷的 `threads` 里声明
- `关联伏笔` 必须已在卷的 `伏笔计划` 里声明（按 `id`）
- 节拍按 `目标集` 单调递增，不许倒序

---

### 2.5 逐集剧本

剧本采用结构化 Markdown 格式（**非散文**），每集一个 `manuscript/episodes/E{n}.md` 文件。平台用 `## 剧本` 和 `## 分镜表` 两个段落分割。

#### 严格格式

```
# 《剧集名称》第X集《本集标题》
---

## 第N场 地点·时间（日/夜）
**本场人物**：角色A（年龄+身份/标签）、角色B（…）
**场景描述**：一句话讲清场地全貌。

【动作】走位/肢体/环境变化。
**角色名**（神态/语气）：台词内容

【镜头/画面标注】远景/近景/特写/转场/字幕/画外音（按需）

---
**【第X集完】**
```

**硬约束 checklist**：
1. 集名恰为 `# 《剧集名称》第X集《本集标题》`
2. 每场起头恰为 `## 第N场 地点·时间（日/夜）`，N 从 1 递增，时间只取 `日` 或 `夜`
3. 每场含 `**本场人物**：` 和 `**场景描述**：` 两行
4. 台词行恒为 `**角色名**（神态/语气）：台词内容`——**神态括注就是 TTS 情感种子**
5. 动作段以 `【动作】` 起，声音/脚步声/环境音全写进 `【动作】`
6. **禁止**自创 `【音效】` / `【脚步声】` / `【环境音】` 段
7. 场间用单独一行 `---` 分隔
8. 全剧以单独一行 `**【第X集完】**` 收尾

#### 真实示例

```markdown
## 剧本

# 《旧约钟楼》第1集《停摆的钟》
---

## 第1场 钟楼·夜
**本场人物**：林夏（20岁，钟表匠之女）
**场景描述**：废弃钟楼内，巨大齿轮锈迹斑斑，昏黄天光从破窗透入。

【动作】林夏推开沉重木门，逆光而立，缓步走向倒地的父亲。

【动作】她颤抖着蹲下身，抚过父亲冰冷的手背，视线落到最大一枚齿轮背面的血字。

**林夏**（哽咽）：爸……你说了会回家的。

【镜头/画面标注】近景推镜，泪光

---
**【第1集完】**
```

#### 创作判据

每集创作完成后做轻量自审（不必逐集跑完整的批判环——骨架已扛住高杠杆判据）：

- **价值翻转**：每场翻转一个价值（信任<->背叛/希望<->绝望/控制<->无力），标入场态->出场态
- **高幅翻转**：每集至少 1 次（打脸/逆袭/认知双击）
- **删场测试**：删掉这场，本集的钩子/爽点/伏笔链会不会断？不断即废场
- **因果审计**：每场以"因为"承前 N-1，而非"然后"时序堆叠
- **钩子前置**：每集结尾的钩子必须在下一集首场兑现

---

### 2.6 分镜表

分镜表是 `## 分镜表` 段内的一个 JSON 围栏块，结构为 `{"title", "shots":[], "shot_groups":[]}`。**校验全过才写盘**。

#### shot 必填字段

| 字段 | 含义 | 示例 |
|------|------|------|
| `shot_id` | 全表唯一 ID | `"s1"` |
| `shot_number` | 顺序号 | `1` |
| `scene` | 场景名 | `"钟楼"` |
| `shot_type` | 景别 | `"wide"` / `"close-up"` / `"medium"` |
| `action_desc` | 静态可拍画面（供出图首帧） | `"林夏推开木门，逆光剪影，缓步入内"` |
| `duration` | 时长（秒） | `4.0` |
| `group_id` | 所属叙事组 ID | `"g1"` |

#### 推荐增强字段

```json
"characters": ["林夏"],
"dialogue": [{"speaker": "林夏", "text": "爸……你说了会回家的。", "emotion": "哽咽"}],
"video_prompt": "画面：…。运镜：…。音效：…。",
"video_prompt_en": "(english free-text motion)"
```

**重要分工**：
- `action_desc` 写**静态可拍画面**（在场对象 + 动作），给出图/首帧用
- `video_prompt` 写**时间维度运动**（动作起止 + 运镜 + 节拍 + 音效），给 LTX 出视频用
- `dialogue` 写对白数组，`export.py` 自动追加为 `video_prompt` 的 `对白：` 段——**手稿不需手写对白段**
- `characters` 填圣经角色**短名**，如 `["林夏"]`，不含括号描述

#### video_prompt 中文三段格式

```
画面：林夏推门入内，逆光剪影缓步前行。
运镜：固定全景，人物由门口向纵深移动。
音效：木门吱呀声，碎石踩踏声。
```

段头必须含全角冒号「：」。平台 `validate_storyboard` 会逐镜查这三个段头，缺则报错。

#### shot_group 必填字段

| 字段 | 含义 |
|------|------|
| `group_id` | 组 ID（与 shots 的 `group_id` 对应） |
| `relation` | 组内镜头关系：`montage` / `progressive` / `causal` / `contrast` / `single` |
| `shot_ids` | 本组包含的 shot_id 列表 |

#### 叙事组（relation）五值语义

| 值 | 含义 | 使用场景 |
|----|------|----------|
| `montage` | 并列蒙太奇 | 同一主题下并列呈现 |
| `progressive` | 递进 | 镜头推进叙事（推门→发现） |
| `causal` | 因果 | 前镜是因、后镜是果 |
| `contrast` | 对比反差 | 情绪/节奏强对比 |
| `single` | 单镜独立 | 一段完整情绪由一个镜头扛 |

#### 完整分镜表示例

```json
{"title": "停摆的钟", "shots": [
  {"shot_id": "s1", "shot_number": 1, "scene": "钟楼", "shot_type": "wide",
   "action_desc": "林夏推开木门，逆光剪影，缓步入内",
   "duration": 4.0, "group_id": "g1",
   "video_prompt": "画面：林夏推门入内，逆光剪影缓步前行。运镜：固定全景，人物由门口向纵深移动。音效：木门吱呀声，碎石踩踏声。",
   "video_prompt_en": "static wide shot, silhouette pushes door open and walks into darkness, creaking wood",
   "characters": ["林夏"], "dialogue": []},
  {"shot_id": "s2", "shot_number": 2, "scene": "钟楼", "shot_type": "close-up",
   "action_desc": "最大齿轮背面血字特写",
   "duration": 3.0, "group_id": "g1",
   "video_prompt": "画面：镜头缓缓推入齿轮背面，血字逐渐清晰。运镜：缓推，焦点落在血字上。音效：金属低鸣，心跳声渐强。",
   "video_prompt_en": "slow push-in to blood inscription on gear, focus pulls to reveal the writing",
   "characters": [], "dialogue": []},
  {"shot_id": "s3", "shot_number": 3, "scene": "钟楼", "shot_type": "medium",
   "action_desc": "林夏蹲身抚摸父亲手背，泪光闪烁，低语",
   "duration": 5.0, "group_id": "g2",
   "video_prompt": "画面：林夏蹲身，手颤抖抚过父亲手背，嘴唇微动低语。运镜：固定中景，微微下压。音效：低声呜咽，远处钟楼机械声。",
   "video_prompt_en": "fixed medium shot tilting slightly down, she kneels trembling beside him, lips barely moving",
   "characters": ["林夏"],
   "dialogue": [{"speaker": "林夏", "text": "爸……你说了会回家的。", "emotion": "哽咽"}]}],
 "shot_groups": [
   {"group_id": "g1", "relation": "progressive", "shot_ids": ["s1", "s2"], "name": "发现"},
   {"group_id": "g2", "relation": "single", "shot_ids": ["s3"], "name": "悲痛"}]}
```

#### 交叉引用规则

- 每个 shot 的 `group_id` 必须能在某个 `shot_groups[*].group_id` 中找到
- 每个 `shot_groups[*].shot_ids` 中的每个 id 必须是真实存在的 `shot.shot_id`
- 两者的引用关系必须双向闭合

#### LTX 2.3 提示词关键约束

LTX 模型对 `video_prompt` 有硬性限制，违反会在 G6 gate 被拦截：

1. **禁止抽象情感词**：写 `fists clenched, jaw tight`，不写 `is angry`
2. **禁止文字/Logo 描述**：LTX 无法可靠渲染屏上文字
3. **使用标准运镜术语**：`tracking shot` / `slow push-in` / `static wide`，不写 `the camera moves closer`
4. **现在进行时**：写 `she pushes the door open`，不写 `she pushed`
5. **英文 4-8 句**为最优区间，太短缺乏运动约束，太长稀释关键动作

---

## 三、门控质量体系

门控分两类：创作阶段软提醒（G1-G4）和生成阶段硬阻断（G5-G8）。软提醒不过可继续但需告知用户风险；硬阻断不过必须修完才能进生成。

| Gate | 名称 | 阶段 | 阻断? | 触发时机 | 校验内容 |
|------|------|------|:----:|----------|----------|
| G1 | 三轴一致性 | 立意后 | 软 | 推进到大纲前 | genre_id 命中注册表, style_id 命中, 四维全齐 |
| G2 | 大纲完整性 | 大纲后 | 软 | 推进到圣经前 | episodes 数组完整, 每集必填字段齐全 |
| G3 | 圣经非空 | 圣经后 | 软 | 推进到节拍前 | 角色/场景/道具/世界观/伏笔五表非空 |
| G4 | 节拍表校验 | 分卷后 | 软 | 推进到剧本前 | 目标集在卷内, thread/伏笔已声明, 递增 |
| G5 | 分镜规范 | 分镜后 | **硬** | 出图前 | shot/group 必填字段, relation 合法, 交叉引用 |
| G6 | 提示词质量 | 分镜后 | **硬** | 出视频前 | 无抽象情绪/无文本Logo/无冲突光照 |
| G7 | 首帧完整 | 出图后 | **硬** | 出视频前 | 所有镜 jpg 首帧存在 |
| G8 | Provider 健康 | 生成前 | **硬** | 每次调用前 | API key 完整, workflow ID 配置 |

### 如何运行门控

**运行所有 gate**：

```bash
python -c "from gates import run_all_gates; from pathlib import Path; \
  results = run_all_gates(Path('manuscript'), Path('out'), 'all'); \
  [print(f'{r.gate_name}: {\"PASS\" if r.passed else \"FAIL\"}') for r in results]"
```

**运行单个 gate**（例如只查分镜规范）：

```bash
python -c "from gates import gate_storyboard; from pathlib import Path; \
  r = gate_storyboard(Path('manuscript/episodes/E1.md')); \
  print(f'{r.gate_name}: {\"PASS\" if r.passed else \"FAIL\"}'); \
  [print(f'  ERR: {e}') for e in r.errors]; \
  [print(f'  WARN: {w}') for w in r.warnings]"
```

**结果解读**：

| 组合 | 含义 |
|------|------|
| `hard_block=True` + `passed=False` | **硬阻断**：必须修完 `errors` 列表的所有问题才能继续 |
| `hard_block=False` + `passed=False` | **软提醒**：看 `warnings` 列表，用户决定是否继续 |
| `passed=True` | 通过 |

---

## 四、生成管线

手稿完成后，用 `export.py` 编译，然后用 `generate.py` 分阶段生成媒体产物。

### 4.1 编译导出

```bash
python export.py manuscript/ out/
```

编译做的事：
- 读 `manuscript/*.md` 的全部手稿
- 跑所有内置校验（大纲/分镜/节拍），**任一不过就不落盘**
- 生成平台兼容的 JSON（`series.json` / `arcs.json` / `story_bible.json` / `E{n}/gen_context.json` / `assets/registry.json`）
- 全集可见：就算某集还没写剧本/分镜，`export.py` 也为它建骨架集（`script=null`），平台里集结构都看得见
- 幂等且并入安全：重新编译不会覆盖平台已生成的图片/音频/状态

### 4.2 skill.env 完整配置字段

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `IMAGE_PROVIDER` | 默认图片 provider | `grsai` |
| `GEMINI_API_KEY` | Gemini API 密钥 | - |
| `GEMINI_MODEL` | Gemini 模型 ID | `imagen-4.0-generate-001` |
| `GRSAI_API_KEY` | Grsai API 密钥 | - |
| `GRSAI_BASE_URL` | Grsai 服务地址 | `https://grsai.dakka.com.cn` |
| `GRSAI_IMAGE_MODEL` | Grsai 图片模型 | `gpt-image-2-vip` |
| `COMFYUI_BASE_URL` | ComfyUI 本地地址 | `http://localhost:8188` |
| `COMFYUI_WORKFLOW_ID` | ComfyUI workflow UUID | - |
| `RUNNINGHUB_API_KEY` | RunningHub API 密钥 | - |
| `RUNNINGHUB_BASE_URL` | RunningHub 地址 | `https://www.runninghub.cn` |
| `RUNNINGHUB_IMAGE_WORKFLOW_ID` | 文生图 workflow ID | - |
| `RUNNINGHUB_VIDEO_WORKFLOW_ID` | LTX 视频 workflow ID | - |
| `RUNNINGHUB_DUB_WORKFLOW_ID` | TTS 配音 workflow ID | - |
| `RUNNINGHUB_UPSCALE_WORKFLOW_ID` | 宫格高清放大裁切 workflow ID | - |
| `RUNNINGHUB_VOICE_DESIGN_WORKFLOW_ID` | 音色设计 workflow ID | - |
| `RUNNINGHUB_DUB_CLONE_WORKFLOW_ID` | 克隆配音 workflow ID | - |
| `RUNNINGHUB_MAX_PARALLEL` | 并发任务数 | `3` |
| `IMAGE_PROVIDER_ANCHOR` | 锚图专用 provider（可选） | 沿用 `IMAGE_PROVIDER` |
| `IMAGE_PROVIDER_ANCHOR_FALLBACK` | 锚图降级 provider | `gemini` |
| `IMAGE_PROVIDER_SHOT` | 分镜专用 provider（可选） | 沿用 `IMAGE_PROVIDER` |
| `IMAGE_PROVIDER_SHOT_FALLBACK` | 分镜降级 provider | `gemini` |
| `IMAGE_WIDTH` | 图片宽度 | `768` |
| `IMAGE_HEIGHT` | 图片高度（9:16 竖屏） | `1344` |
| `POLL_INTERVAL_S` | 轮询间隔（秒） | `5` |
| `POLL_TIMEOUT_S` | 轮询超时（秒） | `300` |

### 4.3 图片生成

图片生成分三层：锚图（角色/场景/道具）-> 宫格分镜首帧 -> 拆图归一化。

```bash
# 为 E1-E3 生成分镜首帧
python generate.py images E1-E3 --out ./out

# 只生成第 1 集
python generate.py images E1 --out ./out

# 全量生成
python generate.py images all --out ./out

# 强制重生成（覆盖已有产物）
python generate.py images E1-E3 --out ./out --force
```

**定向重试选项**：

```bash
# 只重试特定镜号
python generate.py images E1 --out ./out --only s3,s7

# 只重试之前失败的镜
python generate.py images E1 --out ./out --retry-failed

# 单镜独立生成（不按组出宫格）
python generate.py images E1 --out ./out --solo s5
```

**预检（不实际调用 API）**：

```bash
python generate.py images E1-E5 --out ./out --dry-run
```

预检会告诉你：哪些会跳过（已有产物）、哪些会生成、哪些会因缺字段而失败。

**出图路径**：
- 宫格大图：`out/E{n}/imggen/grids/group_{gid}.png`
- 拆分单镜：`out/E{n}/shots_assets/{shot_id}.jpg`

### 4.4 视频生成

视频使用 LTX Director 按叙事组分段调用。**首帧是前提条件**——必须先跑完图片生成。

```bash
python generate.py video E1 --out ./out
python generate.py video E1-E3 --out ./out --force
```

内部逻辑：
- 同场景且总时长 <=18s 的连续镜头合并为一个 Director call（`motion_mode="smooth"`）
- 换场或超 18s 则切新 call（hard cut）

预检会标记"首帧缺失"的镜头并阻止生成。

### 4.5 配音生成

读取分镜表中每条 `dialogue` 的 speaker/text/emotion，调用 TTS 逐条生成。

```bash
python generate.py dub E1 --out ./out
```

配音产出路径：`out/audio/E{n}/dub/{shot_id}_{speaker}_line{idx}.wav`

**音色设计**（先跑一次，设计所有角色的声音）：

```bash
python generate.py voice_design --out ./out
```

这步调用 RunningHub 音色设计 workflow，产出 `out/assets/voices.json`，后续配音阶段引用。

**声音克隆路径**：如果 RunningHub 配置了 `DUB_CLONE_WORKFLOW_ID`，配音阶段会优先读取 `voices.json` 中的 `speaker_ref`（本地音频锚），用克隆模式生成更高保真度的配音。

### 4.6 预览服务器

启动本地 Flask 服务器，在浏览器中预览分镜表 + 出图状态：

```bash
python preview_server.py out/ --port 7788
```

打开浏览器访问 `http://localhost:7788`。

**三态标记**：
- 分镜列表中每个 shot 根据产物存在性自动显示状态图标

| 产物 | 图标 | 含义 |
|------|:----:|------|
| 首帧图 | 🖼 | `shots_assets/{shot_id}.jpg` 存在 |
| 视频 | 🎬 | `shots_assets/{shot_id}.mp4` 存在 |
| 配音 | 🎙️ | `audio/E{n}/dub/{shot_id}_*.wav` 有文件 |

左侧边栏列出所有集，点击切换。资源库入口可检视角色/场景/道具锚图。

---

## 五、题材特定参数

### 5.1 内置题材列表

| genre_id | 中文名 | 特点 |
|----------|--------|------|
| `ceo-romance` | 总裁豪门 | 霸总/契约/甜宠 |
| `rebirth` | 重生 | 前世记忆/逆天改命 |
| `time-travel` | 穿越 | 现代魂穿古代/异世界 |
| `revenge` | 复仇 | 隐忍/布局/清算 |
| `son-in-law` | 赘婿 | 身份反转/打脸 |
| `chase-wife` | 追妻 | 火葬场/破镜重圆 |
| `face-slap` | 打脸 | 逆袭/反转/啪啪响 |
| `counterattack` | 逆袭 | 底层崛起 |
| `war-god-return` | 战神归来 | 低调回归/身份揭晓 |
| `divine-doctor` | 神医 | 医术碾压/济世 |
| `system-rich` | 神豪系统 | 系统加持/升级 |
| `war-god` | 战神 | 武力碾压/守护 |
| `urban-xianxia` | 都市修仙 | 现代背景+仙侠设定 |
| `palace-intrigue` | 宫斗 | 后宫/权谋 |
| `school-rising` | 校园崛起 | 学霸/逆袭 |
| `group-pet` | 团宠 | 被所有人宠爱 |
| `single-episode` | 单集短篇 | 独立完整故事 |
| `vlog` | Vlog | 第一人称记录 |
| `mv` | MV | 音乐驱动叙事 |

### 5.2 自定义题材

当你的故事不在内置列表中，创建 `manuscript/genres/<id>.yaml`，export 会自动拷进项目。

**完整示例**（丧尸求生题材）：

```yaml
genre_id: zombie-survival
name: 丧尸求生

typical_setup: |
  末日爆发后N天，幸存者小团体在废墟中挣扎求生。
  主角因某个机缘踏上旅程，途中遇队友、遭遇丧尸潮、遭遇人性背叛。

core_conflict:
  - 资源匮乏 vs 团队生存需求
  - 人性底线 vs 末日道德崩坏
  - 团队信任 vs 背叛与猜疑

satisfaction_types:
  - 绝境反杀
  - 人性反转
  - 紧张脱逃
  - 资源战
  - 温情瞬间

taboos:
  - 不要过度渲染血腥暴力压低代入感
  - 不要让末日沦为背景布景，生存压力要贯穿全程
  - 不要轻易"免疫"/"解药"消解末日张力

recommended_episodes:
  min: 20
  max: 60
  typical: 30
  unit_duration_sec: 90

# 以下为可选 v3 字段
style_defaults:
  style_id_override: "real/cinematic-cool-v1"
  color_bias: "desaturated cold, teal shadows, muted skin tones"
  negative_extra: "no vibrant colors, no warm sunlight, no clean environments"

tone_defaults:
  情感温度: "冷峻"
  动作密度: "强动作"
  叙事节奏: "高频反转"

generation_guardrails:
  max_characters_per_shot: 3
  preferred_shot_types: ["近景", "特写", "中景"]
```

然后在 `00_立意.md` 中引用 `"genre_id": "zombie-survival"` 即可。

**v3 字段说明**：

| 字段组 | 作用 |
|--------|------|
| `style_defaults` | 覆盖默认视觉风格（style_id / color_bias / negative_extra） |
| `tone_defaults` | 覆盖默认基调档位（四维词表取值） |
| `generation_guardrails` | 出图护栏（每镜最大角色数 / 优先景别） |

**风格选型建议**：
- 古装仙侠 -> `2D/guofeng-ink-v1`（水墨）或 `2D/anime-cel-v1`（赛璐珞）
- 现代甜宠 -> `real/cinematic-warm-v1`（电影暖调）或 `real/golden-hour-romance-v1`
- 玄幻 -> `2D/guofeng-gongbi-v1`（工笔）
- 末日科幻 -> `real/cinematic-cool-v1`（电影冷调）
- 温馨日常 -> `3D/pixar-cute-v1`（皮克斯可爱）

---

## 六、导演引擎

导演引擎是生成阶段的拍摄评估协议，5 个判决 + 单变量规则 + 尝试预算。**只适用于生成阶段（出图/出视频），不替代创作阶段的批判环。**

### 6.1 5 判决

```python
from director import Verdict

# KEEP     → 直接使用，产物合格
# FIX      → 后期修（不在生成侧改动），微瑕可P
# EDIT     → 同 prompt 不同 seed 重生成
# REGEN    → 修改 prompt 重生成
# REWRITE  → 回创作侧改 action_desc / video_prompt
```

### 6.2 单变量规则

每次重试只改一个变量：
- EDIT 模式下只改 seed
- REGEN 模式下只改 prompt 中的一个关键句
- REWRITE 模式下回到手稿改 action_desc 或 video_prompt

### 6.3 尝试预算

每镜默认最多 5 次尝试。连续 2 次 REGEN/EDIT 未解决问题时，引擎建议直接 REWRITE（回创作侧改手稿）。

```python
from director import ShootProtocol

protocol = ShootProtocol(max_attempts=5)

# ... 生成 s1 的图片后 ...
protocol.record_attempt("s1", Verdict.REGEN, change="修改运镜术语")

if protocol.remaining("s1") <= 1:
    print("最后一次尝试，建议改变策略")

advice = protocol.analyze_failures("s1")
# 连续2次 REGEN → 返回 "建议回创作侧修改 action_desc 或 video_prompt"
```

---

## 七、Provider 容灾

### 7.1 容灾策略一览

| 产物类型 | 主 Provider | 降级策略 |
|----------|-------------|----------|
| 锚图（角色/场景/道具） | `IMAGE_PROVIDER_ANCHOR`（或 `IMAGE_PROVIDER`） | 静默降级到 `IMAGE_PROVIDER_ANCHOR_FALLBACK` |
| 分镜首帧 | `IMAGE_PROVIDER_SHOT`（或 `IMAGE_PROVIDER`） | 降级到 `IMAGE_PROVIDER_SHOT_FALLBACK`，打 warn 日志标记 |
| 视频 | RunningHub 专用 | **不降级**：失败直接报错 |
| 配音 | RunningHub 专用 | **不降级**：失败直接报错 |

### 7.2 降级机制细节

- **锚图降级（静默）**：角色/场景/道具锚图出图失败时，自动切换到 fallback provider 重试，但对用户不可见（静默）。因为锚图不是用户直接关心的产物。
- **分镜降级（打标记）**：分镜首帧失败时切换到 fallback provider，并在 `generate_log.json` 打标记，用户可通过预览服务器看到哪些镜走了降级。
- **视频/配音**：只有 RunningHub 能出视频和配音，无备选 provider。失败必须修配置或 prompt 后重试。

### 7.3 切换 Provider

有三种方式切换 provider：

```bash
# 方式 1：改 skill.env，然后重新跑命令
IMAGE_PROVIDER=gemini python generate.py images E1 --out ./out

# 方式 2：命令行临时覆盖
IMAGE_PROVIDER=grsai python generate.py images E1 --out ./out

# 方式 3：Python API 直接指定
python -c "
from providers import make_image_provider
provider = make_image_provider({'provider': 'gemini', 'api_key': '...'})
"
```

---

## 八、编译与交付

### 8.1 确定性编译

```bash
python export.py manuscript/ out/
```

编译是**幂等**且**并入安全**的：
- 重复运行不会损坏已有产物
- 只读 `manuscript/` 手稿，不读平台运行时状态
- 保留 `episode_digests` / registry 的 `ready` 状态 / 锚图 / `shots_assets` / `anchors` / `audio`

### 8.2 诊断出图状态

无需 provider / API，纯本地检查：

```python
from pathlib import Path
import json

project_dir = Path("out/E1")
ctx = json.loads((project_dir / "gen_context.json").read_text(encoding="utf-8"))
sb = ctx.get("storyboard", {})
shots = sb.get("shots", [])
groups = sb.get("shot_groups", [])

for g in groups:
    gid = g["group_id"]
    g_shots = [s for s in shots if s.get("group_id") == gid]
    shot_files = [(s["shot_id"], (project_dir / "shots_assets" / f"{s['shot_id']}.jpg").is_file())
                  for s in g_shots]
    print(f"{gid} ({g['name']}): {' '.join(f'{sid}={\"ok\" if ok else \"miss\"}' for sid, ok in shot_files)}")
```

### 8.3 交付平台

```bash
# 1. 编译
python export.py manuscript/ out/

# 2. 把 out/ 整个文件夹复制到糯米短剧平台的 projects/ 目录下
# 平台靠 harness_state.json 自动识别和导入
```

---

## 九、常见问题（FAQ）

### Q1：genre_id 不在内置列表怎么办？

A：创建 `manuscript/genres/<id>.yaml`（参考第五节的自定义题材示例），export.py 会自动将其拷贝进项目。平台优先读项目级题材，与内置题材重名时以项目级为准。

### Q2：分镜表校验不过，`export.py` 报错？

A：逐个排查以下常见原因：
- shot 缺必填字段（`shot_id` / `shot_number` / `scene` / `shot_type` / `action_desc` / `duration` / `group_id`）
- `shot_id` 重复（全表唯一）
- group 缺必填字段（`group_id` / `relation` / `shot_ids`）
- `relation` 值不在枚举内（合法值只有 `montage` / `progressive` / `causal` / `contrast` / `single`）
- shot 的 `group_id` 在 `shot_groups` 中找不到对应的组
- group 的 `shot_ids` 引用了不存在的 `shot_id`

```bash
# 单独校验一集的分镜表
python -c "from gates import gate_storyboard; from pathlib import Path;
r = gate_storyboard(Path('manuscript/episodes/E1.md'));
print(r.errors) if r.errors else print('PASS')"
```

### Q3：出图失败怎么重试？

A：三种重试方式：

```bash
# 只重试失败的镜
python generate.py images E1 --out ./out --retry-failed

# 只重试指定镜号
python generate.py images E1 --out ./out --only s3,s7

# 强制全部重生成
python generate.py images E1 --out ./out --force
```

先用 `--dry-run` 预检，再动手：

```bash
python generate.py images E1-E5 --out ./out --dry-run
```

### Q4：如何切换 Provider？

A：改 `skill.env` 中的 `IMAGE_PROVIDER` 值（`gemini` / `grsai` / `comfyui` / `runninghub`），或在命令行临时设置环境变量覆盖。锚图和分镜还可以分别指定独立的 provider（`IMAGE_PROVIDER_ANCHOR` / `IMAGE_PROVIDER_SHOT`），并为各自配置 fallback。

### Q5：中断后如何恢复？

A：`export.py` 幂等，随时可重跑。生成管线（`generate.py`）通过产物存在性判断跳过已完成项，加上 `--force` 可强制覆盖。

恢复流程：

```bash
# 1. 确认当前状态
python preview_server.py out/ --port 7788    # 浏览器打开看三态标记

# 2. 修复手稿（如有需要）
# 编辑 manuscript/episodes/E{n}.md

# 3. 重新编译
python export.py manuscript/ out/

# 4. 继续生成（只生成缺失的）
python generate.py images all --out ./out    # 自动跳过已存在的
python generate.py video all --out ./out
python generate.py dub all --out ./out
```

### Q6：剧本写了但 export 说格式不对？

A：检查：
- 首行是否是 `# 《剧集名称》第X集《本集标题》`
- 每场是否以 `## 第N场 地点·时间（日/夜）` 起头
- 是否有 `**本场人物**：` 和 `**场景描述**：`
- 台词行是否是 `**角色名**（神态/语气）：台词内容`
- 是否用 `---` 分隔场、用 `**【第X集完】**` 收尾
- 有没有自创的 `【音效】` / `【脚步声】` 段——所有声音写进 `【动作】`

### Q7：video_prompt 怎么写才不会在 G6 被拦？

A：遵守 LTX 2.3 的核心约束：
1. 用物理线索代替抽象情感：写 `fists clenched, jaw tight` 不写 `is angry`
2. 不用 `text` / `logo` / `lettering` 等词（LTX 无法渲染屏上文字）
3. 运镜用标准术语：`tracking shot` / `slow push-in` / `static wide` / `handheld`
4. 英文 4-8 句最优，中文三段 `画面：/运镜：/音效：` 密度等效
5. 不写冲突光照（同镜不要同时有 front light + backlight）
6. 单镜角色数不超过 3 个

### Q8：大纲写了 30 集但剧本只写了 5 集，export 会报错吗？

A：不会。`export.py` 全集可见：1..N 每集都会建出 `E{n}/gen_context.json`。写了剧本/分镜的集完整编译，没写的集生成骨架（`script=null`）。报告会列出骨架集号，方便你知道哪些还没填。

### Q9：手稿中的 JSON 写错了 export 能帮忙发现吗？

A：能。export 阶段跑三道校验：
- `validate_outline`：大纲完整性检查
- `validate_storyboard`：分镜表字段/交叉引用检查
- `validate_beats`：节拍表一致性检查
任一校验不过，export 报错列出所有问题、**不落盘**，确保平台不会读到脏数据。

### Q10：能否直接在 out/ 里改 JSON 来微调？

A：**绝对不要**。`out/` 里的 JSON 是编译产物，下次 `python export.py manuscript/ out/` 会覆盖你的手改。所有修改应在 `manuscript/*.md` 手稿中完成，然后重新编译。
