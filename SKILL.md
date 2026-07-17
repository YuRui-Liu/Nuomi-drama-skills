---
name: nuomi-drama-skills
description: 长篇短剧创作助手。带方法论引导用户用 Claude 中长篇批量创作「立意/大纲/角色/场景/道具/分卷节拍表/剧本/分镜表」,产出 manuscript/*.md,经 export.py 确定性编译成可导入 nuomi-drama 平台的项目文件夹,后续出图/出视频/后期在平台完成。务必触发:长篇短剧、分卷、节拍表、剧本圣经、导出导入项目、批量产集。
---

# nuomi-drama-skills · 长篇短剧创作 → 平台导入

帮创作者用 Claude 把一部中长篇竖屏短剧从**立意写到分镜表**,落成一摞人类可读的 `manuscript/*.md`,再用确定性编译器 `export.py` 把它们编成可直接丢进 nuomi-drama 平台的项目文件夹。**出图、出视频、后期都在平台里做,本 skill 不碰。**

---

## 1. 职责边界(本 skill ↔ 平台)

- **本 skill 负责**:立意 → 三轴 → 大纲 → 角色/场景/道具/世界观/伏笔(五表圣经)→ 分卷节拍表 → 逐集剧本 → 逐集分镜表。全部以 Markdown 手稿形式产出。
- **平台负责**:出图(角色/场景/道具锚图、分镜首帧)、出视频、配音、后期剪辑。

**单向流(铁律)**:`manuscript/*.md`(唯一事实源)→ `export.py`(确定性编译)→ 平台 JSON(`series.json` / `arcs.json` / `story_bible.json` / `E{n}/gen_context.json` / `assets/registry.json` / `harness_state.json`)。

只改手稿、永不手改编出来的 JSON——编译是幂等且并入安全的,会保留平台已生成的产物(`episode_digests` / registry 的 `ready` 状态与锚图 / `shots_assets` / `anchors` / `audio` 等)。手改 JSON 会在下次编译被你的手稿覆盖,也会和平台运行态打架。

---

## 2. 方法论引用(不要从零重写,蒸馏下列已有源)

创作方法论(各阶段宪章 / 批判环判据 / 三轴基调 / 叙事组法 / 音频上游)全部见 `references/创作方法论.md`(skill 自包含,不依赖外部文件);剧本格式见 `references/剧本格式规范.md`;运动提示词见 `references/提示词规则.md`。下面只给引导各件落地时的**检查表**,详细 rubric 回查上述 reference。

- **三轴正交**(题材 × 基调 × 风格):见 `references/创作方法论.md` 的"控制理念≈立意"与三轴/基调词表。基调(tone)必须进**批判环**——它是高杠杆上游件,跑偏会污染下面每一集。
- **批判环**:对每件高杠杆上游件(立意/大纲/分卷)做"提问 → 起草 → 批判 → 迭代",不一次成稿。价值翻转硬判据、删场测试、因果"因为 vs 然后"审计是核心判据(见对照笔记一档)。
- **五表圣经纪律**:角色 / 场景 / 道具 / 世界观(canon)/ 伏笔与线索(foreshadows+threads)。圣经是跨集一致性的载体,逐集创作时**先读再写**。伏笔遵"埋了必响":`open` 的对象/台词须在计划集内 `paid`(契诃夫之枪)。
- **卷级节拍表**:把大纲拆成分卷,每卷一张节拍表,节拍钉到目标集、关联 thread、关联伏笔,且节拍按目标集递增。

**引导档每件的检查表**:
- **立意**:三轴是否正交且各轴明确?基调是否进批判环?是否能压成一句话控制理念("生活变成 X,当主角做 Y,因为 Z")?
- **大纲**:每集是否都有钩子(`本集钩子`)+ 至少一组爽点节拍(`爽点节拍`)?集间冲突是否总体递增(可憋屈—爆发波浪,不可长段递减)?集内/系列首尾是否押韵?
- **分卷节拍表**:每个节拍是否钉了目标集?关联 thread / 关联伏笔是否都已在本卷声明?目标集是否按节拍递增不倒序?伏笔计划的开窗集/回收集是否落在卷内?(这些正是 `export.py` 的 `validate_beats` 会拦的)
- **角色**:外貌锚点是否够具体到能出图(发型/服装/标志物/年代质感)?aliases 是否齐?主角是否有可辨声音(长度/语域/口头禅/独特称呼之一)?

---

## 2.5. 门控序列（创作软提醒 · 生成硬阻断）

每次阶段推进时，Agent 应按需跑对应 gate。软提醒 gate 不过可继续但需告知用户风险；
硬阻断 gate 不过必须修完才能进生成。

| Gate | 名称 | 阶段 | 阻断? | 触发时机 | 校验内容 |
|------|------|------|-------|----------|---------|
| G1 | 三轴一致性 | 立意后 | ⚠️ 软 | export / 推进到大纲前 | genre_id 命中注册表, style_id 命中, 基调四维全齐 + arc 合法 |
| G2 | 大纲完整性 | 大纲后 | ⚠️ 软 | export / 推进到圣经前 | episodes 数组完整, 每集必填字段(ep/标题/梗概/钩子/爽点) |
| G3 | 圣经非空 | 角色/场景后 | ⚠️ 软 | export / 推进到节拍前 | 角色/场景/道具/世界观/伏笔五表非空 |
| G4 | 节拍表校验 | 分卷后 | ⚠️ 软 | export / 推进到剧本前 | 目标集在卷内, thread/伏笔已声明, 节拍递增不倒序 |
| G5 | 分镜规范 | 分镜表后 | 🛑 硬 | generate images 前 | shot/group 必填字段, relation 合法, 交叉引用一致 |
| G6 | 提示词质量 | 分镜表后 | 🛑 硬 | generate video 前 | video_prompt 无抽象情绪/无文本Logo/无冲突光照 |
| G7 | 首帧完整 | 出图后 | 🛑 硬 | generate video 前 | 所有镜 jpg 首帧存在 |
| G8 | Provider 健康 | 生成前 | 🛑 硬 | 每次 provider 调用前 | API key 完整, workflow ID 配置, 连通性预检 |

**运行 gate**: Agent 可通过 Python 直接调用 `gates.py` 的对应函数，或调 `run_all_gates()` 批量：
```bash
python -c "from gates import run_all_gates; from pathlib import Path; \
  results = run_all_gates(Path('manuscript'), Path('out'), 'all'); \
  [print(f'{r.gate_name}: {\"PASS\" if r.passed else \"FAIL\"}') for r in results]"
```

**Gate 结果解读**:
- `hard_block=True` + `passed=False` → 🛑 必须修完 `errors` 列表的问题才能继续
- `hard_block=False` + `passed=False` → ⚠️ 看 `warnings` 列表，用户决定是否继续
- `hard_block=False` + `passed=True` → ✅ 通过
- `hard_block=True` + `passed=True` → ✅ 通过（硬阻断但全过 = 无问题）

---

## 3. 两档工作流

### 引导档(立意 / 三轴 / 大纲 / 角色场景道具 / 分卷节拍表)\n\n骨架阶段,**一步一件、慢工**:提问 → 给一个带论据的备选(不堆 5 选项)→ 起草 → 批判环迭代 → 用户拍板 → 写入对应 `manuscript/*.md`。\n\n**用户极度简短时的策略**:当用户只回"ok"/"B"/"你来设计"时——主动给单一推荐+理由，而非抛开放问题。每轮只问 1-2 个窄选择，用户只需确认或微调即可推进。

每件的落点模板见 `templates/`:
- 立意 → `templates/00_立意.md`
- 大纲 → `templates/01_大纲.md`
- 分卷节拍表 → `templates/02_分卷节拍表.md`
- 五表圣经 → `templates/bible/角色.md` · `场景.md` · `道具.md` · `世界观.md` · `伏笔与线索.md`

缺信息时问**一个窄二元问题**("这场他在保护还是利用?"),只改用户要求改的,不顺手改邻件。

### 批量档(逐集剧本 + 分镜表)

骨架(立意/大纲/分卷/圣经)锁定后,进**批量产集**模式。按用户给的范围(如 E5–E20 / 整卷 / 全集)逐集:

1. **取本集工作集**:从 arcs 里挑"目标集 == 本集"的节拍 + 本集出场角色 + 关联 thread/伏笔的开窗回收窗口 + bible 五表。
2. **起草剧本**:遵 `references/剧本格式规范.md` 的**结构化剧本格式**(场/本场人物/场景描述/`**角色名**（神态）：台词`/【动作】/`**【第X集完】**`);判据见 `references/创作方法论.md`(只写可拍、每场翻转一个价值、本集≥1 高幅翻转、神态括注即配音情感种子)。
3. **起草分镜表**:遵 `references/分镜表规范.md`(必填字段、`relation` 合法值、叙事组↔镜头交叉引用规则)。**每镜写双语运动提示词**(规则见 `references/提示词规则.md`):`video_prompt`(中文三段,段头含 `画面：/运镜：/音效：`,只写时间维度——动作起止/运镜/节拍/音效,禁复述首帧静态构图)+ `video_prompt_en`(英文自由文本 motion);`action_desc` 仍写静态可拍画面,二者分工别混。shot 的 `characters` 数组填圣经角色**短名**（`normalize_character_name` 后的形式，不含括号描述，如 `["林夏"]` 而非 `["林夏（钟表匠之女）"]`）。缺 video_prompt 不阻断编译但 export 会软提醒、出视频会回退 action_desc。有台词的镜头填 `dialogue: [{"speaker":"角色名","text":"台词","emotion":"情感"}]`；`export.py` 会自动把它追加为 `video_prompt` 的第四段 `对白：`（见 `references/提示词规则.md §2.5`），**手稿不需要手写 `对白：` 段**。无台词镜头省略 `dialogue` 或写 `[]`。
4. **轻量自审**:删场测试 + 因果"因为承前"审计;伏笔窗口是否对齐圣经。
5. **写入** `episodes/E{n}.md`(`## 剧本` 段 + `## 分镜表` 段含一个 json 块)。

批量档不必逐集跑完整批判环——骨架已扛住高杠杆判据;逐集做轻量自审即可,保产能。

**单集时长**:竖屏短剧每集总时长目标 **90–180s**,每镜 4–8s,约 **15–30 镜**。`export.py` 会软提醒不在区间的集(详见 `references/创作方法论.md`)。\n\n> **超短剧例外**:1-3集超短剧(无前后集分摊叙事量)单集可到 180–210s、25–35 镜，每集承担首尾结构。E1 含建置+钩子，E2 含高潮+收尾，都超过标准区间——`export.py` 的软提醒属于信息性警告，不影响编译和生成。

---

## 4. 导出与交付

编译命令(从手稿目录所在处或绝对路径均可):

```bash
python export.py <manuscript_dir> <out_project_dir>
```

- **全集可见**:即便某集还是骨架(没写剧本/分镜),`export.py` 也会为 1..N 每一集建出 `E{n}/gen_context.json`(空但在),平台里整部剧的集结构都看得见。
- **骨架集**:报告里会列出仅骨架的集号,提醒哪些还没填。
- **校验失败不写盘**:大纲/分镜/节拍任一不过内置校验(`validate_outline` / `validate_storyboard` / `validate_beats`),`export.py` 报错列出问题、**不落盘**,避免把脏数据带进平台。
- **交付**:编出来的 `<out_project_dir>` 文件夹整个丢进对方平台的 projects 根目录即完成导入(平台靠 `harness_state.json` 标记识别)。

跑通后,可在 in-repo 用真平台 loader 复核(`GenContext.load` + 真 `validate_storyboard`)做并行校验,防契约漂移。

---

## 5. 资源边界(文字进手稿,图全平台生)

角色 / 场景 / 道具在手稿里**只写文字规格**:`外貌` / `appearance`(出图描述)、`aliases`(别名)、`描述`(资源库说明)。**不在手稿里放任何图片**。

`export.py` 把这些文字规格 upsert 进 `assets/registry.json`,新条目 `status="pending"`;角色 key 用规范化短名(括号描述进 aliases)。锚图、`ready` 状态、`overrides` 全部由**平台出图阶段**生成并保留,本 skill 永不下调。

---

## 6. 独立生成工作流（不需要平台 GUI）

手稿 → `export.py` 编译 → `generate.py` 出图/视频/配音，全链路可在命令行完成。

### generate.py CLI

| 子命令 | 用法 | 说明 |
|--------|------|------|
| images | `python generate.py images <ep-range> --out <dir>` | 宫格出图 → 高清拆分 → 9:16 归一 |
| video | `python generate.py video <ep-range> --out <dir>` | LTX 分组生成，按叙事组批处理 |
| dub | `python generate.py dub <ep-range> --out <dir>` | TTS 配音 + 声音克隆 |
| voice-design | `python generate.py voice-design <ep-range> --out <dir>` | 音色设计 |
| all | `python generate.py all <ep-range> --out <dir>` | 全阶段顺序执行 |

选项：
- `--provider <name>` — 指定 provider（grsai / gemini / comfyui / runninghub）
- `--force` — 强制重新生成已存在的文件
- `--dry-run` — 只打印计划，不实际生成

图片生成统一走**宫格路径**：叙事组宫格大图 → RunningHub 多宫格高清放大裁切 workflow（或本地拆分）→ Pillow 去边 → 单镜 JPG。

Provider 配置通过 `skill.env` 或环境变量注入（详见 USER_GUIDE.md）。

### 产物与平台兼容

产物写入平台兼容路径（`out/E1/shots_assets/` · `out/audio/E1/dub/`），`out/` 文件夹可直接导入糯米短剧平台；平台看到 `status=ready` 的条目不会重复出图。

失败记录在 `out/generate_log.json`（每行一个 JSON），单镜失败不中断整集。

### 诊断已有出图状态

运行以下 Python 片段诊断一个已编译项目的出图状态（无需 GUI / provider）：

```python
from pathlib import Path
import json

project_dir = Path("out/E1")  # 或绝对路径
ctx_file = project_dir / "gen_context.json"
ctx = json.loads(ctx_file.read_text(encoding="utf-8"))
sb = ctx.get("storyboard", {})
shots = sb.get("shots", [])
groups = sb.get("shot_groups", [])

assets_dir = project_dir / "shots_assets"
grids_dir = project_dir / "imggen/grids"

for g in groups:
    gid = g["group_id"]
    g_shots = [s for s in shots if s.get("group_id") == gid]
    grid_path = grids_dir / f"group_{gid}.png"
    grid_ok = grid_path.is_file()
    shot_files = [(s["shot_id"], (assets_dir / f"{s['shot_id']}.jpg").is_file()) for s in g_shots]
    print(f"{gid} ({g['name']}): {'✓' if grid_ok else '✗'} group_grid | "
          f"{' '.join(f'{sid}={\"✓\" if ok else \"✗\"}' for sid, ok in shot_files)}")
```

### 图片生成路径（统一宫格）

- **所有叙事组统一走宫格路径**：出宫格大图 → RunningHub `多宫格高清放大裁切` workflow 高清拆分（或本地拆分）→ Pillow 去边 → N 张单镜图。
  实现见 `shot_agent.tools.grid_gen.GridGenTool` + `shot_agent.tools.grid_split.GridSplitTool`。
- 已出图的 group 对应栅格图：`imggen/grids/group_{gid}.png`（如 `group_g1.png`）
- 拆分后的单镜图：`shots_assets/{shot_id}.jpg`（如 `s3.jpg`）

---

## 8. 开发工作流（针对 skill 代码本身的开发 ⚠️ 与第6节内容创作模式不同）

当你在开发 nuomi-drama-skills 的**代码本身**（插件架构、命令系统、exporters、质量门禁等技能基础设施）时，遵循以下规则：

### 8.1 两种模式区分

| 模式 | 触发条件 | 目标 | 调什么 |
|------|---------|------|--------|
| **内容创作模式** | 用户想写/生成一部具体漫剧 | 产出内容（图片/视频/配音） | export.py → generate.py → preview_server.py |
| **技能开发模式** | 用户讨论 skill 架构、实现新任务 | 写/改 skill 代码 | 只写代码 + 跑测试 + git commit |

**核心铁律**：技能开发模式中**绝不调用 `generate.py images/video/dub`**——图片生成耗时长、消耗 API 配额，会打断开发节奏。用户明确要求出图时才进入内容创作模式。

### 8.2 开发测试替代方案

验证代码改动不需要跑完整生成管线：

| 要验证的东西 | 替代方案 |
|-------------|---------|
| export.py 编译 | `python export.py manuscript/ out/`（纯本地，几秒钟） |
| prompt_checker | `python -m pytest tests/test_prompt_checker.py -v` |
| providers 初始化 | `python -c "from providers import get_image_provider; p = get_image_provider(); print(p)"` |
| gate_g2 质量门禁 | `python -c "from gate_g2 import check_quality; print(check_quality(...))"` |
| json 结构正确性 | `python -m json.tool out/series.json > /dev/null` |
| 分镜表校验 | export.py 内置 validate_storyboard |
| 命令调度器 | `python -c "from commands.dispatcher import dispatch; print(dispatch('/review E1'))"` |

### 8.3 插件架构文件结构（v2 新增）

```
skill/
├── commands/          # 命令处理系统（任务 10-13）
│   ├── __init__.py
│   ├── dispatcher.py  # 路由 /xxx args → on_command 钩子
│   ├── new.py         # /new - 题材选择 → 模板填充
│   ├── review.py      # /review - 五维评分
│   └── compliance.py  # /compliance - 红线检测
├── exporters/         # 导出器（任务 14-15）
│   ├── __init__.py
│   ├── srt.py         # SRT 字幕导出
│   └── ffmpeg.py      # FFmpeg 合成脚本导出
├── hooks.py           # 3 个钩子: on_command / on_gate / on_export
├── prompt_checker.py  # LTX 2.3 提示词校验器（任务 1，已实现）
├── gate_g2.py         # 质量门禁 G2（任务 6，已实现）
├── jianying.py        # 剪映草稿导出（任务 8，已实现）
└── ...
```

### 8.4 开发 pitfall

- **不要混模式**：在写代码时顺手跑 generate.py images = 浪费时间 + 烧 API。等用户主动说"出图/出视频"再切内容创作模式。
- **测试优先**：新功能配上测试（`tests/` 目录），用 pytest 验证而非目测。
- **git 小步提交**：每个逻辑任务一个 commit，备注 `Task N: <描述>` 格式。
- **worktree 隔离**：复杂改动开 git worktree，完工后 merge 回 feat/ 分支。

---

## 7. 离线事实源与版本（原第7节）

- `references/平台契约.md` —— 冻结的平台契约(导入机制、各文件 JSON 顶层键、各 loader 的惰性默认与未知键过滤规则),离线查这里。\n- `references/分镜表规范.md` —— 分镜表必填字段与叙事组规则。\n- `references/提示词规则.md` —— 双语运动提示词(`video_prompt` 中三段 + `video_prompt_en` 英)规则,镜像平台 storyboard/video_clips。\n- `references/图像生成管线实操.md` —— 截至当前代码的实际出图操作方法（generate.py 未实现时的替代方案、诊断脚本、Grsai 失败模式）。
- `references/自定义题材创作.md` —— 自定义题材 YAML 编写指南（必填字段/冲突设计/爽点库/风格选型建议），题材不在内置列表时必须创建。\n- 本 skill 对齐的契约版本见 `contract.py` 的 `CONTRACT_VERSION`(当前 `2026-06-20`)。平台契约升级时重新同步 vendored 校验器并 bump 此版本。
