# nuomi-drama-skills v3 架构升级设计

**日期**: 2026-07-13
**状态**: 设计确认，待实施
**借鉴来源**: seedance-2.0（门控/导演引擎）、short-drama-main（状态机）、Micro-Drama-Skills（source 字段/仿真模式）

---

## 1. 目标

将 nuomi-drama-skills 从"工具箱模式"升级为"操作系统模式"：

- **当前问题**: 创作质量完全依赖 Agent 单次能力；无状态中断需从零推；单 provider 挂了全停；无前置条件强制检查
- **目标**: 门控链强制质量关卡；状态持久化支持中断恢复；多 provider 容灾自动降级；题材特定参数自动注入

---

## 2. 架构全景

```
nuomi-drama-skills v3
├── SKILL.md（路由器 ~120行）
│   ├── 门控矩阵表（Agent 可见）
│   └── 按阶段渐进式加载 reference
├── 创作阶段（软提醒 ⚠️）
│   G1 三轴 → G2 大纲 → G3 圣经 → G4 节拍
├── 生成阶段（硬阻断 🛑）
│   G5 分镜 → G6 提示词 → G7 首帧 → G8 Provider
├── writing_state.py          # 状态机读写
├── gates.py                  # 8 个 Gate 纯函数
├── provider_chain.py         # 按角色降级链
├── director.py               # 导演引擎
├── prompt_rules.json         # 提示词规则配置
├── manuscript/*.md           # 唯一创作事实源（不变）
├── export.py                 # 确定性编译（不变，增加 --jianying）
└── generate.py               # 生成 CLI（不变，增加 --dry-run 已有）
```

---

## 3. 核心设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 门控阻断策略 | 分层：创作软提醒 / 生成硬阻断 | 创作需灵活性，生成需确定性 |
| 状态粒度 | 混合：阶段+集级写入 / 镜级产物判定 | 轻量不漂移，复用已有 status.py |
| 门控实现 | 双层：SKILL.md 清单 + gates.py 纯函数 | Agent 可见 + 可测可 CI |
| Provider 容灾 | 按角色：锚图降级 / 分镜降级打标记 / 视频不伪装 | 不同素材对风格一致性要求不同 |
| 导演引擎范围 | 5 判决协议 + 单变量规则 + 尝试预算 | 选种子 dance-2.0 核心子集 |
| 剪映集成 | export 完可选 --jianying | 已有 exporters/jianying.py，改动最小 |

---

## 4. 各项详细设计

### 4.1 writing_state.json 状态机

**文件**: `writing_state.py`（新）+ SKILL.md 引用

**数据结构**:
```json
{
  "phase": "scripting",
  "completed_episodes": [1, 2, 3],
  "current_episode": 4,
  "current_arc": 1,
  "gates_passed": ["triplet", "outline", "bible", "beats"],
  "gates_warnings": {
    "E5_duration": "142s 超出 90-180s 推荐区间"
  },
  "created_at": "2026-07-13T15:00:00Z",
  "last_updated": "2026-07-13T15:30:00Z"
}
```

**行为规则**:
- 新项目首次进入时自动创建（phase: "ideation"）
- 每次阶段推进时 `phase` 更新 + `last_updated` 刷新
- `gates_passed` 记录已通过的 gate（同名 gate 重跑时覆盖）
- `gates_warnings` 记录软提醒级问题（不影响推进）
- 镜级状态（ready/pending/failed）→ 由 `generate.py status` 实时扫描产物目录，不写入 state
- 中断恢复：Agent 开局读 `writing_state.json`，从 `phase` + `current_episode` 恢复上下文

**API**:
```python
def load_state(manuscript_dir: Path) -> dict
def save_state(manuscript_dir: Path, state: dict) -> None
def advance_phase(manuscript_dir: Path, new_phase: str) -> dict
def mark_gate(manuscript_dir: Path, gate_name: str, passed: bool, warnings: list[str]) -> dict
def mark_episode_complete(manuscript_dir: Path, ep: int) -> dict
```

---

### 4.2 门控表 + gates.py

**文件**: `gates.py`（新）+ SKILL.md 重构

**SKILL.md 门控矩阵**（Agent 面，约 30 行）:
```
## 门控序列

| Gate | 阶段 | 阻断? | 触发 | 校验内容 |
|------|------|-------|------|---------|
| G1 三轴 | 立意后 | ⚠️ 软 | export | genre_id/style_id 命中注册表, 基调四维全齐 |
| G2 大纲 | 大纲后 | ⚠️ 软 | export | episodes 数组完整, 每集必填字段 |
| G3 圣经 | 角色/场景后 | ⚠️ 软 | export | characters/scenes/props 非空 |
| G4 节拍 | 分卷后 | ⚠️ 软 | export | 目标集在卷内, thread/伏笔已声明, 递增 |
| G5 分镜 | 分镜表后 | 🛑 硬 | generate images | shot/group 必填字段, relation 合法, 交叉引用 |
| G6 提示词 | 分镜表后 | 🛑 硬 | generate video | video_prompt 无抽象情绪/无文本Logo |
| G7 首帧 | 出图后 | 🛑 硬 | generate video | 所有镜 jpg 存在 |
| G8 Provider | 生成前 | 🛑 硬 | 每次 API 调用 | provider 配置完整, 健康检查通过 |
```

**gates.py 纯函数**（机器面）:
```python
@dataclass
class GateResult:
    gate_name: str
    passed: bool
    hard_block: bool
    errors: list[str]     # 阻断级
    warnings: list[str]   # 提醒级

def gate_triplet(manuscript_dir: Path) -> GateResult  # G1, 复用 validators.validate_triplet
def gate_outline(manuscript_dir: Path) -> GateResult   # G2, 复用 validators.validate_outline
def gate_bible(manuscript_dir: Path) -> GateResult     # G3, 圣经五表非空检查
def gate_beats(manuscript_dir: Path) -> GateResult     # G4, 复用 validators.validate_beats
def gate_storyboard(ep_path: Path) -> GateResult       # G5, 复用 validators.validate_storyboard
def gate_prompts(ep_path: Path) -> GateResult          # G6, 复用 prompt_checker
def gate_first_frames(out_dir: Path, ep: int) -> GateResult  # G7, 逐镜 jpg 存在检查
def gate_provider_health(cfg: dict) -> GateResult      # G8, 各 provider 配置完整性 + ping

def run_all_gates(manuscript_dir: Path, out_dir: Path, stage: str) -> list[GateResult]
```

**与已有代码的关系**:
- G1/G2/G4/G5 直接调用 `validators.py` 已有函数，包装为 GateResult
- G6 调用 `prompt_checker.py` 的 `check_video_prompt`
- G3/G7/G8 为新增逻辑

---

### 4.3 题材特定参数表

**文件**: `templates/genres/*.yaml`（已有，字段扩展）

**新增字段**（每个题材 yaml 可选）:
```yaml
# 已有字段保持不变...

# 新增：视觉风格覆盖
style_defaults:
  style_id_override: "real/cinematic-cool-v1"   # 覆盖用户选择的 style_id（可选）
  color_bias: "desaturated cold, teal shadows"  # 附加到 prompt_suffix（可选）
  negative_extra: "no warm sunlight"            # 附加到 negative_suffix（可选）

# 新增：基调软提示
tone_defaults:
  情感温度: "冷峻"
  动作密度: "强动作"
  叙事节奏: "高频反转"
# (仅当用户未显式设定时才生效，不覆盖用户选择)

# 新增：生成护栏
generation_guardrails:
  max_characters_per_shot: 3     # 单镜最大角色数（可选）
  preferred_shot_types: ["近景", "特写", "中景"]  # 偏好镜型（可选）
  avoid_shot_types: ["全景"]     # 避用镜型（可选）
```

**加载逻辑**（在 `styles_table.py` 或新 `genre_params.py` 中）:
```python
def load_genre_params(genre_id: str, manuscript_dir: Path) -> dict:
    """加载题材特定参数。先查 project/genres/, 再查 vendored templates/genres/。
    返回 {} 表示无特定配置，使用默认行为。
    """
```

---

### 4.4 Provider 容灾 + 健康检查

**文件**: `provider_chain.py`（新）+ `skill.env.example`（扩展）

**skill.env 新字段**:
```bash
# Provider 容灾（按角色分离）
IMAGE_PROVIDER_ANCHOR=grsai
IMAGE_PROVIDER_ANCHOR_FALLBACK=gemini
IMAGE_PROVIDER_SHOT=grsai
IMAGE_PROVIDER_SHOT_FALLBACK=gemini
# VIDEO_PROVIDER 和 DUB_PROVIDER 沿用现有 RUNNINGHUB（无 fallback）
```

**ProviderChain 包装类**:
```python
class ProviderChain:
    """按角色分 provider 的降级链。
    - 锚图：主 provider 挂了自动切 fallback（对风格影响小）
    - 分镜首帧：主 provider 挂了切 fallback，但打 ⚠️ 标记在日志
    - 视频/配音：无 fallback，主 provider 挂了直接报错
    """
    def generate_anchor(self, prompt: str) -> bytes: ...
    def generate_shot(self, prompt: str, size=None) -> bytes: ...
    def generate_video(self, prompt: str, first_frame: str, duration: float) -> bytes: ...
    def generate_dub(self, text: str, speaker: str, emotion: str, voice_style: str) -> bytes: ...

def health_check(cfg: dict) -> dict[str, bool]:
    """预检各 provider 连通性。返回 {provider_name: is_healthy}。
    非阻塞——只报告，不阻断（除非 --strict-health 标志）。
    """
```

**降级行为**:
| 角色 | 主挂行为 | 降级后果 |
|------|---------|---------|
| 锚图 | 自动切 fallback | 风格可能略有差异但跨集复用优先级高 |
| 分镜首帧 | 切 fallback + 打 ⚠️ | `generate_log.json` 记录标记，提醒用户本集首帧为降级产物 |
| 视频 | 直接报错 | 无备选 provider |
| 配音 | 直接报错 | 无备选 provider |

---

### 4.5 导演引擎 · 拍摄评估协议

**文件**: `director.py`（新）+ `reference/导演引擎.md`（新）

**借鉴范围**: seedance-2.0 拍摄评估协议的核心子集，适配 nuomi 剧集场景。

**5 判决协议**:
```
        生成结果
           |
    ┌──────┼──────┐
    ▼      ▼      ▼
  KEEP    FIX   REJECT
 (保留)  (后期修)  |
            ┌─────┼─────┐
            ▼     ▼     ▼
          EDIT  REGEN  REWRITE
         (剪辑) (重生成) (重写提示词)
```

| 判决 | 含义 | 适用场景 |
|------|------|---------|
| KEEP | 直接使用 | 画面符合预期 |
| FIX | 后期修（不在生成侧改动） | 小瑕疵可后期处理 |
| EDIT | 调整参数重生成（同 prompt 不同 seed） | 构图正确但细节不对 |
| REGEN | 修改 prompt 重生成 | 方向偏差，需调 prompt |
| REWRITE | 回创作侧改 action_desc/video_prompt | 系统性偏差，同组多镜出问题 |

**单变量规则**: 每次重拍只改一个变量（seed / prompt 单句 / 参数），否则无法判断哪个改动产生了效果。

**尝试预算**: 首次拍摄前设定上限（默认 5 次/镜），防止无限循环。

**适用阶段**: 导演引擎适用于**生成阶段**（出图/出视频）。创作阶段用已有批判环。

---

### 4.6 剪映导出集成

**文件**: `export.py`（修改）+ `exporters/jianying.py`（已有，不改）

**改动**: `export.py` 增加 `--jianying` 标志，编译完自动调用 `export_jianying()`:
```python
# export.py main() 新增
if args.jianying:
    from exporters.jianying import export_jianying
    export_jianying(compiled_data, args.out_project_dir)
    print("  · 剪映草稿已导出")
```

**理由**: `exporters/jianying.py` 已实现完整，只是未集成到主流程。

---

### 4.7 提示词规则配置化

**文件**: `prompt_rules.json`（新）+ `prompt_checker.py`（修改）

**当前问题**: LTX 2.3 规则（抽象情绪/文本Logo/复杂物理/冲突光照）硬编码为 Python 正则。升级 LTX 版本需改代码。

**prompt_rules.json 结构**:
```json
{
  "version": "ltx-2.3",
  "hard_blocks": [
    {
      "rule": "no_abstract_emotion",
      "patterns_zh": ["很难过", "很生气", "很害怕", "..."],
      "patterns_en": ["\\b(is|feels|looks)\\s+(sad|angry|...)"],
      "message_zh": "抽象情绪标签，请用身体线索替代",
      "message_en": "Abstract emotion label, use physical cues instead"
    },
    {
      "rule": "no_text_logo",
      "patterns": ["\\b(text|logo|lettering|...)"],
      "message_zh": "文本/Logo 描述，LTX 无法可靠渲染",
      "message_en": "Text/logo description, LTX cannot reliably render"
    }
  ],
  "soft_warnings": [
    {
      "rule": "complex_physics_warning",
      "patterns": ["\\b(shatters?|explodes?|...)"],
      "message_zh": "复杂物理效果可能产生可见伪影",
      "message_en": "Complex physics may produce visible artifacts"
    }
  ]
}
```

**prompt_checker.py 改动**: 启动时加载 `prompt_rules.json`，规则匹配逻辑抽取为通用引擎。版本升级只需换 JSON。

---

## 5. 实施顺序

| 阶段 | 项 | 依赖 | 预估工时 |
|------|----|------|---------|
| **P2-A** | 状态机 writing_state.py | 无 | 小 |
| **P2-B** | 门控表 gates.py + SKILL.md 重构 | 无（复用 validators.py） | 中 |
| **P2-C** | 题材参数表扩展 | 无（已有 templates/genres/） | 小 |
| **P3-A** | Provider 容灾 provider_chain.py | 无（已有 provider 抽象层） | 中 |
| **P3-B** | 导演引擎 director.py | 无 | 大 |
| **P3-C** | 剪映导出集成 | 无 | 小 |
| **P3-D** | 提示词规则配置化 | 无 | 小 |

P2 三项可并行实施。P3 四项也可并行。

---

## 6. 不变项（本轮不碰）

以下现有组件**不做改动**:
- `export.py` 核心编译逻辑（只加 --jianying 标志）
- `generate.py` 四阶段命令（P0/P1 已加固）
- `manuscript_parse.py` / `emit.py` / `validators.py`（gates.py 是包装层，不修改这些）
- `stages/` 生成流水线（P0/P1 已加固）
- `reference/` 方法论文档（导演引擎新增 reference，不改已有）
- `providers/` 各 provider（provider_chain.py 是包装层，不修改 provider 实现）

---

## 7. 风险与注意事项

1. **门控不过时的用户体验**: 硬阻断不准进生成，需给出明确的问题清单和修复建议，不要让用户面对"被拒绝但不知道为什么"
2. **状态漂移**: writing_state.json 和 manuscript/*.md 之间的不一致——状态机只做快捷索引，手稿始终是唯一事实源
3. **题材参数覆盖度**: 不是所有题材都需要 style override，默认留空 = 不干预用户选择
4. **导演引擎的适用边界**: 拍摄评估不替代创作阶段的批判环——批判环审"叙事对不对"，导演引擎审"画面好不好"
5. **Provider 降级的风格一致性**: 降级产物打标记是为了让用户知道"这批图是 fallback 出的"，方便后续决定是否重出
