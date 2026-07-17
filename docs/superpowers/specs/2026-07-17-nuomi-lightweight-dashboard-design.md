# 轻量前端 Dashboard — 设计规格

> 状态：已审批  
> 日期：2026-07-17  
> 方案：A — 纯 Python + Flask 单文件，SSE 实时推送

---

## 1. 动机

nuomi-drama-skills 当前只有一个只读的 `preview_server.py`（Flask，内联 HTML），仅能查看分镜表三态标记和资产库。用户无法从浏览器创建项目、触发管线、监控生成进度或处理失败镜头。需要一个轻量 Dashboard 来覆盖项目管理 + 生成监控。

## 2. 约束

- **零额外依赖** — Flask + Jinja2 已在 pyproject.toml 中，不新增库
- **单命令启动** — `python preview_server.py <out_dir> [--port 7788]` 不变
- **无 Node 构建** — 纯内联 CSS + 少量香草 JS
- **不替代 manuscript 编辑** — 剧本仍在编辑器手写，Dashboard 只管理管线
- **保持现有 `/ep/<int>` 和 `/assets` 路由不变**

## 3. 架构

```
preview_server.py
  │
  ├─ Flask app
  ├─ Jinja2 模板（从 Python 字符串移到 templates/web/ 目录）
  ├─ SSE 端点（Flask Response + generator，零额外库）
  └─ 复用已有 Python 模块：
       ├─ observability.py → build_summary()
       ├─ aosop.py → load_aosop()
       ├─ writing_state.py → load_state()
       ├─ generate.py → run_images/run_video/run_dub
       ├─ stages/retake.py → RetakeController
       ├─ quality/review.py → ReviewReport
       └─ exporters/ → export_srt/export_ffmpeg
```

### 路由表

| 路由 | 方法 | 用途 |
|------|------|------|
| `/` | GET | 项目仪表板 |
| `/monitor` | GET | 生成监控页 |
| `/ep/<int:ep>` | GET | 分镜预览（保持现有） |
| `/assets` | GET | 资源库（保持现有） |
| `/img/<path:rel>` | GET | 图片静态文件（保持现有） |
| `/api/monitor/stream` | GET | SSE 实时事件流 |
| `/api/generate/<stage>` | POST | 触发图片/视频/配音生成 |
| `/api/export` | POST | 触发编译 |
| `/api/review` | POST | 运行审查 |
| `/api/compliance` | POST | 运行合规检查 |
| `/api/retry` | POST | 重试失败镜头 |
| `/api/exporters/<fmt>` | POST | 触发导出（srt/ffmpeg/jianying） |
| `/api/status` | GET | 一次性状态快照（JSON） |

---

## 4. 页面设计

### 4.1 项目仪表板 (`/`)

布局：左侧面板（项目信息 + 操作按钮）+ 右侧主区域（进度 + 审查）

**左侧 — 项目信息**：
- 项目标题（来自 series.json）
- 当前阶段（ideation/outline/bible/.../done）
- 完成剧集数（completed_episodes / total）
- 最后活跃时间

**左侧 — 操作按钮**（每个触发 POST 到对应 API）：
- 📝 编译（export.py）
- 🖼 出图（generate.py images）
- 🎬 视频（generate.py video）
- 🎙️ 配音（generate.py dub）
- 📋 审查（quality/review.py）
- 🛡️ 合规（quality/compliance.py）
- 📤 导出 SRT/FFmpeg/剪映

**右侧 — 进度概览**：
- 每集横向卡片（E1, E2, ...），颜色标记全完成/部分/未开始/有失败
- AOSOP 摘要（总数、已接受、已生成、失败、计划中）
- 审查得分（total/50 + grade）
- 合规状态（红线数/灰区数）

### 4.2 生成监控页 (`/monitor`)

**顶部**：整体进度条 + 按阶段统计（图片/视频/配音各 done/total）

**中部**：标签切换（图片/视频/配音），每集折叠面板：
- 每镜色块：绿=完成，蓝=生成中，黄=等待中，红=失败
- 失败镜显示重试按钮 + 剩余尝试次数
- 点击色块展开详情（prompt、error log）

**底部**：Provider 健康状态（绿/黄/红指示器）

### 4.3 SSE 事件类型

```json
{"event": "progress", "data": {"stage": "images", "done": 45, "total": 50}}
{"event": "shot", "data": {"ep": 2, "shot_id": "s04", "state": "generating"}}
{"event": "shot", "data": {"ep": 2, "shot_id": "s07", "state": "failed", "error": "..."}}
{"event": "provider", "data": {"name": "gemini", "status": "degraded"}}
{"event": "complete", "data": {"stage": "images"}}
{"event": "heartbeat", "data": {"ts": "ISO8601"}}
```

SSE 每 2 秒从 `observability.build_summary()` + `aosop.load_aosop()` 推送一次完整快照。

---

## 5. 模板拆分

现有预览模块保留原封不动的 HTML 布局，仅将内联字符串移动到显式的模板文件中。dashboard 和 monitor 模板为全新文件。

| 文件 | 来源 |
|------|------|
| `templates/web/base.html` | 提取——共用布局（sidebar + 顶栏框架） |
| `templates/web/episode.html` | 现有 `_EP_HTML` 逻辑，移动 |
| `templates/web/assets.html` | 现有 `_ASSETS_HTML` 逻辑，移动 |
| `templates/web/dashboard.html` | ✨ 全新——仪表板 |
| `templates/web/monitor.html` | ✨ 全新——监控 |

## 6. 文件清单

| 操作 | 文件 | 内容 |
|------|------|------|
| **重写** | `preview_server.py` | 加入 API 端点 + SSE、路由重组织、模板移到文件 |
| **创建** | `templates/web/base.html` | 共用布局（sidebar + CSS） |
| **创建** | `templates/web/episode.html` | 分镜预览（从 Python 字符串移出） |
| **创建** | `templates/web/assets.html` | 资源库（从 Python 字符串移出） |
| **创建** | `templates/web/dashboard.html` | 项目仪表板 |
| **创建** | `templates/web/monitor.html` | 生成监控 |

**不改动** `pyproject.toml`、所有已有 Python 模块。

## 7. 风险与缓解

| 风险 | 缓解 |
|------|------|
| SSE 长连接在 Windows 上不稳定 | 每 2 秒心跳事件 + 前端自动重连 |
| 后台 generator 进程阻塞 Flask | 用 `threading.Thread` 启动生成，SSE 轮询文件系统状态 |
| 模板文件路径兼容性 | `Path(__file__).parent / "templates/web"` 加载，不依赖 cwd |
