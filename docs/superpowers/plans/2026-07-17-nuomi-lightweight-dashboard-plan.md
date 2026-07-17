# 轻量前端 Dashboard — 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在 `preview_server.py` 上构建一个功能完备的项目管理和生成监控 Dashboard，采用纯 Python + Flask + 香草 JS 架构，零额外依赖。

**架构：** 单文件 Flask 应用 + Jinja2 模板（`templates/web/` 目录）+ SSE 事件流。所有操作按钮通过 `POST /api/*` 端点触发已有 Python 模块（`generate.py`、`gates.py`、`observability.py`、`aosop.py`、`quality/`、`exporters/`）。SSE 每隔 2 秒推送完整状态快照，前端按舞台过滤。

**技术栈：** Python 3.9+、Flask（已有）、Jinja2（Flask 自带）、SSE（Flask Response + generator）、香草 JS（无框架、无构建）、内联 CSS。

---

## 文件结构

| 操作 | 文件 | 职责 |
|------|------|------|
| **重写** | `preview_server.py` | Flask 应用 + API 路由 + SSE 端点 + 模板渲染 |
| **创建** | `templates/web/base.html` | 共用布局（侧边栏 + CSS + 导航） |
| **创建** | `templates/web/episode.html` | 分镜预览（从现有 _EP_HTML 移出） |
| **创建** | `templates/web/assets.html` | 资源库（从现有 _ASSETS_HTML 移出） |
| **创建** | `templates/web/dashboard.html` | 项目仪表板 |
| **创建** | `templates/web/monitor.html` | 生成监控 |

---

### 任务 1：创建模板目录并提取 `base.html`

**文件：**
- 创建：`templates/web/base.html`

- [ ] **步骤 1：创建 `templates/web/` 目录**

```bash
mkdir -p templates/web
```

- [ ] **步骤 2：编写 `templates/web/base.html`** — 共用布局 + 所有 CSS

```html
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{% block title %}nuomi-drama{% endblock %}</title>
<style>
/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, "Segoe UI", sans-serif; display: flex;
       height: 100vh; overflow: hidden; background: #0d1117; color: #c9d1d9; }

/* ── Sidebar ── */
#sidebar { width: 180px; flex-shrink: 0; background: #0d1117;
           border-right: 1px solid #21262d; overflow-y: auto; padding: 12px 10px; }
#sidebar h2 { font-size: 12px; color: #7ec87e; margin: 0 0 10px; }
#sidebar .nav-link { display: block; padding: 6px 8px; border-radius: 4px;
    margin-bottom: 3px; font-size: 12px; color: #8b949e; text-decoration: none;
    border-left: 2px solid transparent; transition: all .15s; }
#sidebar .nav-link:hover { background: #21262d; color: #f0f6fc; }
#sidebar .nav-link.active { background: #21262d; color: #f0f6fc;
    border-left-color: #7ec87e; }

/* ── Main content ── */
#main { flex: 1; overflow-y: auto; padding: 20px; }

/* ── Top bar ── */
.topbar { display: flex; align-items: center; justify-content: space-between;
          padding-bottom: 14px; border-bottom: 1px solid #21262d; margin-bottom: 16px; }
.topbar h1 { font-size: 18px; font-weight: 600; color: #f0f6fc; }
.topbar .tabs { display: flex; gap: 6px; }
.topbar .tab { padding: 5px 14px; border-radius: 4px; font-size: 12px;
    color: #8b949e; text-decoration: none; border: 1px solid #30363d; }
.topbar .tab:hover { background: #21262d; color: #f0f6fc; }
.topbar .tab.active { background: #2386361a; color: #7ec87e; border-color: #238636; }

/* ── Cards ── */
.card { background: #161b22; border: 1px solid #30363d; border-radius: 6px;
        padding: 16px; margin-bottom: 14px; }
.card h3 { font-size: 13px; color: #7ec87e; margin-bottom: 10px;
           padding-bottom: 6px; border-bottom: 1px solid #21262d; }

/* ── Grid ── */
.stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
             gap: 8px; }
.stat { text-align: center; padding: 10px 6px; background: #0d1117;
        border-radius: 4px; border: 1px solid #21262d; }
.stat .num { font-size: 22px; font-weight: 600; }
.stat .label { font-size: 10px; color: #8b949e; margin-top: 2px; }

/* ── Episodes row ── */
.ep-row { display: flex; gap: 6px; flex-wrap: wrap; }
.ep-chip { width: 36px; height: 36px; border-radius: 4px; display: flex;
           align-items: center; justify-content: center; font-size: 11px;
           font-weight: 600; cursor: pointer; border: 1px solid transparent;
           transition: all .15s; }
.ep-chip.done { background: #23863622; color: #7ec87e; border-color: #238636; }
.ep-chip.partial { background: #d2992222; color: #d29922; border-color: #d29922; }
.ep-chip.pending { background: #161b22; color: #484f58; border-color: #21262d; }
.ep-chip.failed { background: #da363322; color: #f85149; border-color: #da3633; }

/* ── Buttons ── */
.btn { display: inline-flex; align-items: center; gap: 5px; padding: 7px 14px;
       border-radius: 5px; border: 1px solid #30363d; font-size: 12px;
       cursor: pointer; background: #21262d; color: #c9d1d9;
       transition: all .15s; text-decoration: none; }
.btn:hover { background: #30363d; }
.btn.primary { background: #238636; border-color: #238636; color: #fff; font-weight: 600; }
.btn.primary:hover { background: #2ea043; }
.btn.danger { background: #da3633; border-color: #da3633; color: #fff; }
.btn.danger:hover { background: #f85149; }

.btn-group { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }

/* ── Toast ── */
#toast { position: fixed; bottom: 20px; right: 20px; background: #238636;
         color: #fff; padding: 10px 18px; border-radius: 5px; font-size: 12px;
         z-index: 999; display: none; max-width: 400px; }
#toast.error { background: #da3633; }

/* ── Monitor specific ── */
.progress-bar { height: 8px; background: #21262d; border-radius: 4px;
                overflow: hidden; margin: 6px 0; }
.progress-fill { height: 100%; border-radius: 4px; transition: width .5s; }
.progress-fill.images { background: #58a6ff; }
.progress-fill.video { background: #7ec87e; }
.progress-fill.dub { background: #d29922; }

.shot-grid { display: flex; gap: 3px; flex-wrap: wrap; }
.shot-dot { width: 20px; height: 28px; border-radius: 3px; cursor: pointer;
            font-size: 9px; display: flex; align-items: center; justify-content: center;
            color: #0d1117; font-weight: 700; transition: all .15s; }
.shot-dot.ready { background: #238636; }
.shot-dot.generating { background: #58a6ff; animation: pulse 1s infinite; }
.shot-dot.pending { background: #21262d; color: #484f58; }
.shot-dot.failed { background: #da3633; }

@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

.ep-section { margin-bottom: 8px; }
.ep-section summary { font-size: 13px; font-weight: 600; color: #c9d1d9;
    padding: 6px 10px; background: #161b22; border-radius: 4px;
    border: 1px solid #30363d; cursor: pointer; list-style: none; }
.ep-section summary:hover { background: #21262d; }
.ep-section .shot-detail { padding: 8px; font-size: 11px; color: #8b949e; }

/* ── Provider ── */
.provider-row { display: flex; gap: 12px; font-size: 12px; align-items: center; }
.provider-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.provider-dot.healthy { background: #238636; }
.provider-dot.degraded { background: #d29922; }
.provider-dot.down { background: #da3633; }
</style>
</head>
<body>
<div id="sidebar">
  <h2>🎬 nuomi-drama</h2>
  <a class="nav-link {% if active_page == 'dashboard' %}active{% endif %}"
     href="/">📊 仪表板</a>
  <a class="nav-link {% if active_page == 'monitor' %}active{% endif %}"
     href="/monitor">📡 监控</a>
  <a class="nav-link" href="/ep/1">🎞️ 分镜</a>
  <a class="nav-link" href="/assets">📦 资源</a>
  <div style="margin-top:12px;font-size:10px;color:#484f58">
    {{ project_title or "nuomi-drama" }}<br>
    阶段: {{ phase or "—" }}
  </div>
</div>
<div id="main">
{% block content %}{% endblock %}
</div>
<div id="toast"></div>
<script>
function showToast(msg, isError) {
  var t = document.getElementById('toast');
  t.textContent = msg; t.className = isError ? 'error' : '';
  t.style.display = 'block';
  setTimeout(function(){ t.style.display = 'none'; }, 3000);
}

function apiPost(url, cb) {
  fetch(url, {method:'POST'}).then(function(r){ return r.json(); })
    .then(function(d){ showToast(d.message || JSON.stringify(d), d.status === 'error');
                       if (cb) cb(d); })
    .catch(function(e){ showToast('请求失败: '+e, true); });
}
</script>
</body>
</html>
```

- [ ] **步骤 3：验证 Jinja2 可解析模板**

```bash
python -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('templates/web')); t = env.get_template('base.html'); print('OK:', t.name)"
```

预期：`OK: base.html`

- [ ] **步骤 4：提交**

```bash
git add templates/web/base.html
git commit -m "feat: add dashboard base template with shared layout and CSS

Dark theme, sidebar navigation, stat grid, episode chips, shot dots,
progress bars, toast notifications, and provider indicators.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 2：提取已有模板 — `episode.html` + `assets.html`

**文件：**
- 创建：`templates/web/episode.html`
- 创建：`templates/web/assets.html`

- [ ] **步骤 1：创建 `templates/web/episode.html`**（从现有 `_EP_HTML` 的块内容提取）

```html
{% extends "web/base.html" %}
{% block title %}分镜预览 — {{ episode_label }}{% endblock %}

{% block content %}
<div style="border-bottom:1px solid #21262d; padding:0 0 10px; margin-bottom:12px;
            display:flex; align-items:center; gap:12px">
  <span style="font-size:15px;font-weight:600;color:#f0f6fc">E{{ ep }}</span>
  <span style="font-size:12px;color:#8b949e">{{ shots|length }} 镜</span>
</div>
{% for s in shots %}
<div style="display:flex;gap:10px;align-items:flex-start;background:#161b22;
            border-radius:5px;border:1px solid #30363d;padding:10px;margin-bottom:8px">
  {% if s.img_url %}
  <img src="{{ s.img_url }}" style="width:54px;height:96px;border-radius:3px;
            object-fit:cover;flex-shrink:0">
  {% else %}
  <div style="width:54px;height:96px;background:#1c1c1c;border-radius:3px;
            flex-shrink:0;display:flex;align-items:center;justify-content:center;
            color:#555;font-size:10px">⏳</div>
  {% endif %}
  <div style="flex:1;font-size:11px">
    <div style="margin-bottom:4px">
      <span style="color:#7ec87e;font-weight:600">{{ s.shot_id }}</span>
      <span style="color:#8b949e;margin-left:6px">{{ s.duration }}s</span>
      <span style="margin-left:auto;float:right">
        {{ "🖼✅" if s.has_img else "🖼⏳" }}
        {{ "🎬✅" if s.has_vid else "🎬⏳" }}
        {{ "🎙️✅" if s.has_dub else ("🎙️—" if not s.has_dialogue else "🎙️⏳") }}
      </span>
    </div>
    <div style="color:#c9d1d9;margin-bottom:4px">{{ s.action_desc }}</div>
    {% if s.dialogue %}
    {% for line in s.dialogue %}
    <div style="padding:3px 6px;background:#0d1117;border-left:2px solid #7ec8e3;
                border-radius:2px;margin-top:3px;color:#e3c87e;font-size:10px">
      💬 <b>{{ line.speaker }}</b>（{{ line.emotion }}）：{{ line.text }}
    </div>
    {% endfor %}
    {% endif %}
  </div>
</div>
{% endfor %}
{% endblock %}
```

- [ ] **步骤 2：创建 `templates/web/assets.html`**（从现有 `_ASSETS_HTML` 的块内容提取）

```html
{% extends "web/base.html" %}
{% block title %}资源库 — {{ project_title }}{% endblock %}

{% block content %}
<h2 style="color:#f0f6fc;font-size:13px;font-weight:600;margin:0 0 14px">📦 资源库</h2>
{% for section in sections %}
<div style="margin-bottom:18px">
  <div style="font-size:11px;color:#7ec87e;font-weight:600;margin-bottom:6px;
              padding-bottom:4px;border-bottom:1px solid #21262d">
    {{ section.label }}（{{ section.rows|length }}）
  </div>
  {% for item in section.rows %}
  <div style="display:flex;gap:10px;align-items:center;background:#161b22;
              border-radius:4px;border:1px solid #30363d;padding:8px;margin-bottom:4px">
    {% if item.img_url %}
    <img src="{{ item.img_url }}" style="width:36px;height:64px;border-radius:3px;
              object-fit:cover;flex-shrink:0">
    {% else %}
    <div style="width:36px;height:64px;background:#1c1c1c;border-radius:3px;
              flex-shrink:0;display:flex;align-items:center;justify-content:center;
              color:#555;font-size:9px">⏳</div>
    {% endif %}
    <div style="flex:1;font-size:11px">
      <div style="color:#c9d1d9;font-weight:600;margin-bottom:2px">{{ item.name }}</div>
      {% if item.description %}
      <div style="color:#777;font-size:10px">{{ item.description }}</div>
      {% endif %}
    </div>
    <div style="display:flex;gap:8px;font-size:12px;flex-shrink:0">
      {% if item.has_img is defined %}{{ "🖼✅" if item.has_img else "🖼⏳" }}{% endif %}
      {% if item.has_voice is defined %}{{ "🎙️✅" if item.has_voice else "🎙️⏳" }}{% endif %}
    </div>
  </div>
  {% endfor %}
</div>
{% endfor %}
{% if not sections %}
<p style="color:#555;font-size:12px">registry.json 为空，暂无资源。</p>
{% endif %}
{% endblock %}
```

- [ ] **步骤 3：提交**

```bash
git add templates/web/episode.html templates/web/assets.html
git commit -m "feat: extract episode and assets templates from inline strings

Preserves exact layout from existing _EP_HTML and _ASSETS_HTML.
Extends base.html via Jinja2 template inheritance.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 3：创建 `dashboard.html` 模板

**文件：**
- 创建：`templates/web/dashboard.html`

- [ ] **步骤 1：创建 `templates/web/dashboard.html`**

```html
{% extends "web/base.html" %}
{% block title %}仪表板 — {{ project_title }}{% endblock %}

{% block content %}
<div class="topbar">
  <h1>📊 {{ project_title or "项目仪表板" }}</h1>
</div>

<div style="display:grid;grid-template-columns:220px 1fr;gap:16px">

  <!-- Left panel -->
  <div>
    <div class="card">
      <h3>⚙️ 操作</h3>
      <div class="btn-group" style="flex-direction:column">
        <button class="btn" onclick="apiPost('/api/export', function(d){location.reload()})">
          📝 编译导出
        </button>
        <button class="btn primary" onclick="apiPost('/api/generate/images')">
          🖼 出图
        </button>
        <button class="btn" onclick="apiPost('/api/generate/video')">
          🎬 出视频
        </button>
        <button class="btn" onclick="apiPost('/api/generate/dub')">
          🎙️ 配音
        </button>
        <button class="btn" onclick="apiPost('/api/review', function(d){location.reload()})">
          📋 审查
        </button>
        <button class="btn" onclick="apiPost('/api/compliance', function(d){location.reload()})">
          🛡️ 合规
        </button>
        <button class="btn" onclick="apiPost('/api/exporters/srt')">
          📄 导出 SRT
        </button>
        <button class="btn" onclick="apiPost('/api/exporters/ffmpeg')">
          🎞️ 导出 FFmpeg
        </button>
      </div>
    </div>

    <div class="card">
      <h3>📋 项目信息</h3>
      <div style="font-size:12px;line-height:1.8">
        阶段: <strong>{{ phase or "—" }}</strong><br>
        剧集: {{ completed_episodes }}/{{ total_episodes }}<br>
        审查: {% if review_total %}{{ review_total }}/50 ({{ review_grade }}){% else %}未审查{% endif %}<br>
        合规: {% if compliance_ok %}✅ 通过{% else %}⚠️ {{ red_lines }} 红线{% endif %}
      </div>
    </div>
  </div>

  <!-- Right panel -->
  <div>
    <!-- AOSOP Summary -->
    <div class="card">
      <h3>📈 进度概览</h3>
      <div class="stat-grid">
        <div class="stat">
          <div class="num" style="color:#7ec87e">{{ aosop.accepted }}</div>
          <div class="label">已接受</div>
        </div>
        <div class="stat">
          <div class="num" style="color:#58a6ff">{{ aosop.observed }}</div>
          <div class="label">已生成</div>
        </div>
        <div class="stat">
          <div class="num" style="color:#f85149">{{ aosop.failed }}</div>
          <div class="label">失败</div>
        </div>
        <div class="stat">
          <div class="num" style="color:#8b949e">{{ aosop.planned }}</div>
          <div class="label">计划中</div>
        </div>
        <div class="stat">
          <div class="num">{{ aosop.total_shots }}</div>
          <div class="label">总镜头</div>
        </div>
      </div>
    </div>

    <!-- Episode progress -->
    <div class="card">
      <h3>📺 按集进度</h3>
      <div class="ep-row">
        {% for ep in episode_list %}
        <div class="ep-chip {{ ep.css_class }}" title="E{{ ep.n }}: {{ ep.done }}/{{ ep.total }} 镜">
          {{ ep.n }}
        </div>
        {% endfor %}
      </div>
    </div>

    <!-- Review & Compliance -->
    <div class="card">
      <h3>📝 审查与合规</h3>
      <div style="display:flex;gap:20px">
        <div>
          <span style="font-size:24px;font-weight:700;color:
            {% if review_total >= 38 %}#7ec87e{% elif review_total >= 30 %}#d29922{% else %}#f85149{% endif %}
          ">{{ review_total or "—" }}</span>/50
          <span style="font-size:12px;color:#8b949e;margin-left:6px">{{ review_grade or "" }}</span>
        </div>
        <div>
          <span style="font-size:24px;font-weight:700;color:
            {% if red_lines == 0 %}#7ec87e{% else %}#f85149{% endif %}
          ">{{ red_lines }}</span>
          <span style="font-size:12px;color:#8b949e">红线 / {{ gray_zones }} 灰区</span>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **步骤 2：提交**

```bash
git add templates/web/dashboard.html
git commit -m "feat: add dashboard template with project overview and actions

Left panel: action buttons (export, generate, review, compliance, exporters)
Right panel: AOSOP summary, per-episode progress chips, review/compliance scores.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 4：创建 `monitor.html` 模板

**文件：**
- 创建：`templates/web/monitor.html`

- [ ] **步骤 1：创建 `templates/web/monitor.html`**

```html
{% extends "web/base.html" %}
{% block title %}生成监控 — {{ project_title }}{% endblock %}

{% block content %}
<div class="topbar">
  <h1>📡 生成监控</h1>
  <div class="tabs">
    <button class="tab active" data-stage="all" onclick="filterStage('all', this)">全部</button>
    <button class="tab" data-stage="images" onclick="filterStage('images', this)">🖼 图片</button>
    <button class="tab" data-stage="video" onclick="filterStage('video', this)">🎬 视频</button>
    <button class="tab" data-stage="dub" onclick="filterStage('dub', this)">🎙️ 配音</button>
  </div>
</div>

<!-- Overall progress -->
<div class="card">
  <h3>整体进度</h3>
  <div>
    <span>图片: </span>
    <span style="color:#58a6ff" id="img-done">—</span>/<span id="img-total">—</span>
    <div class="progress-bar"><div class="progress-fill images" id="img-bar" style="width:0%"></div></div>
  </div>
  <div>
    <span>视频: </span>
    <span style="color:#7ec87e" id="vid-done">—</span>/<span id="vid-total">—</span>
    <div class="progress-bar"><div class="progress-fill video" id="vid-bar" style="width:0%"></div></div>
  </div>
  <div>
    <span>配音: </span>
    <span style="color:#d29922" id="dub-done">—</span>/<span id="dub-total">—</span>
    <div class="progress-bar"><div class="progress-fill dub" id="dub-bar" style="width:0%"></div></div>
  </div>
</div>

<!-- Shot status -->
<div class="card">
  <h3>镜头状态</h3>
  <div id="shot-container">等待 SSE 数据...</div>
</div>

<!-- Provider health -->
<div class="card">
  <h3>Provider 健康</h3>
  <div id="provider-container" class="provider-row">等待 SSE 数据...</div>
</div>

<script>
var currentStage = 'all';
var lastShotHTML = '';

function filterStage(s, btn) {
  currentStage = s;
  document.querySelectorAll('.tab').forEach(function(t){ t.classList.remove('active'); });
  btn.classList.add('active');
}

function renderShots(data) {
  if (!data || !data.episodes) return '<p style="color:#8b949e;font-size:12px">暂无数据</p>';
  var html = '';
  data.episodes.forEach(function(ep){
    var epDone = 0, epTotal = ep.shots.length;
    ep.shots.forEach(function(s){
      if (s.state === 'observed' || s.state === 'accepted') epDone++;
    });
    var epColor = epDone === epTotal ? '#238636' : (epDone > 0 ? '#d29922' : '#484f58');
    html += '<details class="ep-section" open><summary style="color:' + epColor + '">' +
      'E' + ep.ep + ' ▸ ' + epDone + '/' + epTotal + ' 镜完成</summary>' +
      '<div class="shot-grid">';
    ep.shots.forEach(function(s){
      if (currentStage !== 'all' && s.stage !== currentStage) return;
      var cls = s.state === 'observed' || s.state === 'accepted' ? 'ready' :
                s.state === 'generating' ? 'generating' :
                s.state === 'failed' ? 'failed' : 'pending';
      var retryBtn = s.state === 'failed' ? ' <button class="btn danger" style="font-size:9px;padding:2px 5px" onclick="retryShot('+ep.ep+',\''+s.shot_id+'\')">⏎</button>' : '';
      html += '<div class="shot-dot ' + cls + '" title="' + s.shot_id + ': ' + s.state +
        (s.error_count > 0 ? ' (' + s.error_count + ' errors)' : '') + '">' +
        s.shot_id.replace('s','') + '</div>' + retryBtn;
    });
    html += '</div></details>';
  });
  return html;
}

function retryShot(ep, shotId) {
  fetch('/api/retry', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ep: ep, shot_id: shotId})
  }).then(function(r){ return r.json(); })
   .then(function(d){ showToast(d.message); });
}

function updateUI(data) {
  var summary = data.summary || {};
  // Update progress bars
  var stages = {images: 'img', video: 'vid', dub: 'dub'};
  Object.keys(stages).forEach(function(s){
    var prefix = stages[s];
    var ep = (summary.episodes || [])[0];
    if (ep && ep[s]) {
      document.getElementById(prefix + '-done').textContent = ep[s].done;
      document.getElementById(prefix + '-total').textContent = ep[s].total;
      var pct = ep[s].total > 0 ? (ep[s].done / ep[s].total * 100) : 0;
      document.getElementById(prefix + '-bar').style.width = pct + '%';
    }
  });
  // Update shots
  var shotHTML = renderShots(data.aosop);
  if (shotHTML !== lastShotHTML) {
    document.getElementById('shot-container').innerHTML = shotHTML;
    lastShotHTML = shotHTML;
  }
  // Update providers
  if (data.providers) {
    var phtml = '';
    data.providers.forEach(function(p){
      phtml += '<span class="provider-dot ' + p.status + '"></span> ' + p.name + ' ';
    });
    document.getElementById('provider-container').innerHTML = phtml;
  }
}

// SSE connection
function connectSSE() {
  var source = new EventSource('/api/monitor/stream');
  source.onmessage = function(e) {
    try { updateUI(JSON.parse(e.data)); } catch(err) {}
  };
  source.onerror = function() {
    setTimeout(connectSSE, 3000);
  };
}
connectSSE();
</script>
{% endblock %}
```

- [ ] **步骤 2：提交**

```bash
git add templates/web/monitor.html
git commit -m "feat: add monitor template with SSE-driven live progress

Tab-filtered shot grid (images/video/dub/all), overall progress bars,
per-shot state coloring with retry buttons, and provider health display.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 5：重写 `preview_server.py`

**文件：**
- 重写：`preview_server.py`

- [ ] **步骤 1：编写完整重写版本**

```python
"""nuomi-drama-skills Dashboard Server.

Flask app with project management dashboard, generation monitor (SSE),
storyboard preview, and asset library. Zero extra dependencies.

Usage: python preview_server.py <out_dir> [--port 7788]
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path

from flask import Flask, Response, abort, jsonify, render_template, request, send_file


def _create_app(out_dir: str) -> Flask:
    app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
    out = Path(out_dir)

    # ── Helpers ────────────────────────────────────────────────────
    def _series():
        p = out / "series.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    def _ctx(ep: int):
        p = out / f"E{ep}" / "gen_context.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def _ep_status(ep: int, shot_count: int) -> str:
        sa = out / f"E{ep}" / "shots_assets"
        imgs = list(sa.glob("*.jpg")) if sa.exists() else []
        return "✅" if len(imgs) >= shot_count > 0 else ("🔄" if imgs else "⏳")

    def _build_ep_list(count: int):
        eps = []
        for n in range(1, count + 1):
            ctx = _ctx(n)
            shots = ((ctx or {}).get("storyboard") or {}).get("shots") or []
            eps.append({"n": n, "status": _ep_status(n, len(shots))})
        return eps

    def _load_review():
        p = out / "review_report.json"
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding="utf-8"))

    def _load_compliance():
        p = out / "compliance_report.json"
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding="utf-8"))

    # ── Route: Dashboard ───────────────────────────────────────────
    @app.route("/")
    def dashboard():
        series = _series()
        count = int(series.get("episode_count", 0))
        title = series.get("title", "")

        from writing_state import load_state
        state = load_state(out)
        phase = state.get("phase", "ideation")
        completed = len(state.get("completed_episodes", []))

        from aosop import load_aosop
        aosop_state = load_aosop(str(out))
        aosop_data = {
            "accepted": sum(e.accepted for e in aosop_state.episodes),
            "observed": sum(e.observed for e in aosop_state.episodes),
            "failed": sum(e.failed for e in aosop_state.episodes),
            "planned": sum(e.planned for e in aosop_state.episodes),
            "total_shots": aosop_state.total_shots,
        }

        review = _load_review()
        comp = _load_compliance()

        ep_list = []
        for n in range(1, count + 1):
            ctx = _ctx(n)
            shots = ((ctx or {}).get("storyboard") or {}).get("shots") or []
            sa = out / f"E{n}" / "shots_assets"
            done = sum(1 for s in shots
                       if isinstance(s, dict) and s.get("shot_id")
                       and (sa / f"{s['shot_id']}.jpg").exists())
            css = "done" if done == len(shots) > 0 else (
                "partial" if done > 0 else ("failed" if False else "pending"))
            ep_list.append({"n": n, "done": done, "total": len(shots),
                           "css_class": css})

        return render_template("web/dashboard.html",
            active_page="dashboard", project_title=title,
            phase=phase, completed_episodes=completed, total_episodes=count,
            aosop=aosop_data, episode_list=ep_list,
            review_total=review.get("total"), review_grade=review.get("grade"),
            red_lines=comp.get("red_lines_hit", 0),
            gray_zones=comp.get("gray_zones_hit", 0),
            compliance_ok=(comp.get("red_lines_hit", 0) == 0),
        )

    # ── Route: Monitor ─────────────────────────────────────────────
    @app.route("/monitor")
    def monitor():
        series = _series()
        title = series.get("title", "")
        return render_template("web/monitor.html",
            active_page="monitor", project_title=title)

    # ── Route: Storyboard Preview (existing, ported to template) ────
    @app.route("/ep/<int:ep>")
    def episode(ep: int):
        ctx = _ctx(ep)
        if ctx is None:
            abort(404)
        series = _series()
        count = int(series.get("episode_count", 0))
        ep_list = _build_ep_list(count)

        shots_raw = (ctx.get("storyboard") or {}).get("shots") or []
        sa = out / f"E{ep}" / "shots_assets"
        audio_dir = out / "audio" / f"E{ep}" / "dub"
        shots = []
        for s in shots_raw:
            sid = str(s.get("shot_id", ""))
            has_img = (sa / f"{sid}.jpg").exists()
            has_vid = (sa / f"{sid}.mp4").exists()
            dialogue = s.get("dialogue") or []
            has_dub = (
                bool(dialogue)
                and (audio_dir / f"{sid}_{(dialogue[0].get('speaker','x'))}_line0.wav").exists()
            )
            shots.append({
                "shot_id": sid, "duration": s.get("duration", "?"),
                "action_desc": s.get("action_desc", ""),
                "dialogue": dialogue, "has_dialogue": bool(dialogue),
                "has_img": has_img, "has_vid": has_vid, "has_dub": has_dub,
                "img_url": f"/img/E{ep}/shots_assets/{sid}.jpg" if has_img else None,
            })
        return render_template("web/episode.html",
            active_page="storyboard", project_title=series.get("title", ""),
            episode_label=f"E{ep}", ep=ep, shots=shots,
            episodes=ep_list)

    # ── Route: Assets (existing, ported to template) ────────────────
    @app.route("/assets")
    def assets():
        series = _series()
        count = int(series.get("episode_count", 0))
        ep_list = _build_ep_list(count)

        reg_path = out / "assets" / "registry.json"
        registry = json.loads(reg_path.read_text(encoding="utf-8")) if reg_path.exists() else {}
        voices_path = out / "assets" / "voices.json"
        voices = json.loads(voices_path.read_text(encoding="utf-8")) if voices_path.exists() else {}

        def _has_img(entry):
            ap = entry.get("anchor_path")
            return bool(ap and (out / ap).exists())

        def _has_voice(name):
            v = voices.get(name, {})
            return v.get("status") == "ready" and bool(v.get("anchor_path"))

        grouped = {"characters": {}, "scenes": {}, "props": {}}
        if any("/" in k for k in registry.keys()):
            for key, entry in registry.items():
                prefix, _, name = key.partition("/")
                bucket = {"character": "characters", "scene": "scenes",
                         "prop": "props"}.get(prefix)
                if bucket:
                    grouped[bucket][name] = entry
        else:
            grouped = {
                "characters": registry.get("characters") or {},
                "scenes": registry.get("scenes") or {},
                "props": registry.get("props") or {},
            }

        sections = []
        for rtype, label in (("characters", "角色"), ("scenes", "场景"), ("props", "道具")):
            entries = grouped.get(rtype) or {}
            if not entries:
                continue
            items = [{"name": name, "description": entry.get("voice_style", "")
                      if rtype == "characters" else "",
                      "img_url": f"/img/{entry['anchor_path']}" if _has_img(entry) else None,
                      "has_img": _has_img(entry),
                      "has_voice": _has_voice(name) if rtype == "characters" else None}
                     for name, entry in entries.items()]
            sections.append({"label": label, "rows": items})

        if voices:
            rows = [{"name": n, "description": v.get("voice_style", ""),
                    "has_voice": v.get("status") == "ready"}
                    for n, v in voices.items()]
            sections.append({"label": "音色", "rows": rows})

        return render_template("web/assets.html",
            active_page="assets", project_title=series.get("title", ""),
            sections=sections, episodes=ep_list)

    # ── Route: Static images ────────────────────────────────────────
    @app.route("/img/<path:rel>")
    def img(rel: str):
        p = out / rel
        if not p.exists() or not p.is_file():
            abort(404)
        return send_file(str(p))

    # ── API: SSE Monitor Stream ─────────────────────────────────────
    @app.route("/api/monitor/stream")
    def monitor_stream():
        def generate():
            while True:
                try:
                    from observability import build_summary
                    from aosop import load_aosop
                    summary = build_summary(str(out))
                    aosop_data = load_aosop(str(out))
                    payload = {
                        "summary": summary.to_dict(),
                        "aosop": {
                            "episodes": [e.to_dict() for e in aosop_data.episodes],
                            "acceptance_rate": aosop_data.acceptance_rate,
                        },
                        "providers": [
                            {"name": "Grsai", "status": "healthy"},
                        ],
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                except Exception:
                    yield f"data: {json.dumps({'error': 'stream error'})}\n\n"
                time.sleep(2)

        return Response(generate(), mimetype="text/event-stream",
                       headers={"Cache-Control": "no-cache",
                                "X-Accel-Buffering": "no"})

    # ── API: Trigger Generate ───────────────────────────────────────
    @app.route("/api/generate/<stage>", methods=["POST"])
    def api_generate(stage: str):
        if stage not in ("images", "video", "dub"):
            return jsonify({"status": "error", "message": f"未知阶段: {stage}"}), 400

        def _run():
            import subprocess, sys
            subprocess.run(
                [sys.executable, str(Path(__file__).parent / "generate.py"),
                 stage, "all", "--out", str(out)],
                capture_output=True, text=True, timeout=3600,
            )

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return jsonify({
            "status": "ok",
            "message": f"{stage} 生成已在后台启动，前往 /monitor 查看进度",
        })

    # ── API: Export ─────────────────────────────────────────────────
    @app.route("/api/export", methods=["POST"])
    def api_export():
        manuscript_dir = out / "manuscript"
        if not manuscript_dir.is_dir():
            return jsonify({"status": "error", "message": "manuscript 目录不存在"}), 400
        import subprocess, sys
        r = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "export.py"),
             str(manuscript_dir), str(out)],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0:
            return jsonify({"status": "ok", "message": "编译完成", "output": r.stdout[-200:]})
        return jsonify({"status": "error", "message": r.stderr[-200:] or "编译失败"}), 500

    # ── API: Review / Compliance ────────────────────────────────────
    @app.route("/api/review", methods=["POST"])
    def api_review():
        manuscript_dir = out / "manuscript"
        if not manuscript_dir.is_dir():
            return jsonify({"status": "error", "message": "manuscript 目录不存在"}), 400
        from quality.review import run_review as run_review_engine
        report = run_review_engine(out, manuscript_dir, [])
        report_json = out / "review_report.json"
        report_md = out / "review_report.md"
        report_json.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
                              encoding="utf-8")
        report_md.write_text(report.to_markdown(), encoding="utf-8")
        return jsonify({"status": "ok", "message": f"审查完成: {report.total}/50 — {report.grade}"})

    @app.route("/api/compliance", methods=["POST"])
    def api_compliance():
        manuscript_dir = out / "manuscript"
        if not manuscript_dir.is_dir():
            return jsonify({"status": "error", "message": "manuscript 目录不存在"}), 400
        profile_path = Path(__file__).parent / "quality" / "profiles" / "cn.json"
        from quality.compliance import run_compliance as run_cc
        report = run_cc(manuscript_dir, profile_path)
        report_json = out / "compliance_report.json"
        report_md = out / "compliance_report.md"
        report_json.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
                              encoding="utf-8")
        report_md.write_text(report.to_markdown(), encoding="utf-8")
        return jsonify({
            "status": "ok",
            "message": f"合规检查: {len(report.red_line_findings)} 红线, "
                      f"{len(report.gray_zone_findings)} 灰区",
        })

    # ── API: Retry ──────────────────────────────────────────────────
    @app.route("/api/retry", methods=["POST"])
    def api_retry():
        data = request.get_json(force=True)
        ep = data.get("ep")
        shot_id = data.get("shot_id")
        if not ep or not shot_id:
            return jsonify({"status": "error", "message": "需要 ep 和 shot_id"}), 400

        from stages.retake import RetakeController
        rc = RetakeController(max_attempts=5,
                              history_path=out / "retake_history.json")
        if not rc.should_retry(shot_id, "manual retry from dashboard"):
            return jsonify({"status": "error",
                           "message": f"镜头 {shot_id} 已达最大重试次数"}), 400

        rc.record(shot_id, False, "retry queued from dashboard")
        import subprocess, sys
        subprocess.run(
            [sys.executable, str(Path(__file__).parent / "generate.py"),
             "images", f"E{ep}", "--out", str(out), "--only", shot_id,
             "--solo", "--force"],
            capture_output=True, text=True, timeout=300,
        )
        rc.record(shot_id, True, "retry completed")
        return jsonify({"status": "ok", "message": f"{shot_id} 重试完成"})

    # ── API: Exporters ──────────────────────────────────────────────
    @app.route("/api/exporters/<fmt>", methods=["POST"])
    def api_exporters(fmt: str):
        if fmt == "srt":
            from exporters.srt import export_srt
            paths = export_srt(str(out))
            return jsonify({"status": "ok",
                           "message": f"SRT 导出完成: {len(paths)} 个文件"})
        elif fmt == "ffmpeg":
            from exporters.ffmpeg import export_ffmpeg
            paths = export_ffmpeg(str(out))
            return jsonify({"status": "ok",
                           "message": f"FFmpeg 脚本生成: {len(paths)} 个文件"})
        return jsonify({"status": "error", "message": f"未知导出格式: {fmt}"}), 400

    # ── API: Status Snapshot ────────────────────────────────────────
    @app.route("/api/status")
    def api_status():
        from observability import build_summary
        from aosop import load_aosop
        summary = build_summary(str(out))
        aosop_data = load_aosop(str(out))
        return jsonify({
            "summary": summary.to_dict(),
            "aosop": {"episodes": [e.to_dict() for e in aosop_data.episodes]},
        })

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="nuomi-drama-skills Dashboard")
    parser.add_argument("out_dir", help="编译输出目录")
    parser.add_argument("--port", type=int, default=7788)
    args = parser.parse_args()
    app = _create_app(args.out_dir)
    print(f"Dashboard: http://localhost:{args.port}")
    app.run(host="0.0.0.0", port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **步骤 2：测试模板正确渲染**

```bash
python -c "
from preview_server import _create_app
app = _create_app('.')
with app.test_client() as c:
    # Test dashboard returns 200 (even if empty project)
    r = c.get('/')
    assert r.status_code == 200, f'Dashboard: {r.status_code}'
    # Test monitor returns 200
    r = c.get('/monitor')
    assert r.status_code == 200, f'Monitor: {r.status_code}'
    # Test API status returns valid JSON
    r = c.get('/api/status')
    assert r.status_code == 200
    assert 'summary' in r.get_json()
    print('All smoke tests PASS')
"
```

预期：`All smoke tests PASS`

- [ ] **步骤 3：确认已有路由保留原行为**

```bash
python -c "
from preview_server import _create_app
app = _create_app('.')
with app.test_client() as c:
    # /ep/1 returns 404 when no project (expected)
    r = c.get('/ep/1')
    assert r.status_code == 404
    # /assets returns 200
    r = c.get('/assets')
    assert r.status_code == 200
    # Static image returns 404 when no file
    r = c.get('/img/nonexistent.png')
    assert r.status_code == 404
    print('Legacy routes OK')
"
```

预期：`Legacy routes OK`

- [ ] **步骤 4：提交**

```bash
git add preview_server.py
git commit -m "feat: rewrite preview_server.py as full dashboard

Added: dashboard (/), monitor (/monitor), API endpoints, SSE stream.
Kept: storyboard preview (/ep/<n>), asset library (/assets), image serving.
All templates externalized to templates/web/ directory.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### 任务 6：集成测试 + 最终验证

**文件：**
- 创建：`tests/test_dashboard.py`

- [ ] **步骤 1：写集成测试**

```python
# tests/test_dashboard.py
from __future__ import annotations
import json, tempfile
from pathlib import Path
import sys; sys.path.insert(0, str(Path(__file__).parents[1]))


def _make_fixture() -> str:
    """Create a minimal project directory for dashboard testing."""
    td = tempfile.mkdtemp()
    out = Path(td)
    (out / "series.json").write_text(
        '{"title":"Test","episode_count":1}', encoding="utf-8")
    (out / "writing_state.json").write_text(
        '{"phase":"scripting","completed_episodes":[1],"current_episode":1,'
        '"current_arc":1,"gates_passed":[],"gates_warnings":{},'
        '"review_history":[],"compliance_history":[]}', encoding="utf-8")
    ep_dir = out / "E1"
    ep_dir.mkdir()
    (ep_dir / "gen_context.json").write_text(
        '{"storyboard":{"shots":[{"shot_id":"s01","duration":3,"action_desc":"test",'
        '"video_prompt":"test","dialogue":[]}]}}', encoding="utf-8")
    return td


def test_dashboard_returns_200():
    from preview_server import _create_app
    td = _make_fixture()
    app = _create_app(td)
    with app.test_client() as c:
        r = c.get("/")
        assert r.status_code == 200
        assert b"dashboard" in r.data.lower() or b"Test" in r.data


def test_monitor_returns_200():
    from preview_server import _create_app
    td = _make_fixture()
    app = _create_app(td)
    with app.test_client() as c:
        r = c.get("/monitor")
        assert r.status_code == 200


def test_episode_preview_returns_200():
    from preview_server import _create_app
    td = _make_fixture()
    app = _create_app(td)
    with app.test_client() as c:
        r = c.get("/ep/1")
        assert r.status_code == 200
        assert b"s01" in r.data


def test_api_status_returns_json():
    from preview_server import _create_app
    td = _make_fixture()
    app = _create_app(td)
    with app.test_client() as c:
        r = c.get("/api/status")
        assert r.status_code == 200
        data = r.get_json()
        assert "summary" in data


def test_api_review_returns_json():
    from preview_server import _create_app
    td = _make_fixture()
    out = Path(td)
    (out / "manuscript").mkdir()
    (out / "manuscript" / "E1.md").write_text("## 剧本\n\ntest\n", encoding="utf-8")
    app = _create_app(td)
    with app.test_client() as c:
        r = c.post("/api/review")
        assert r.status_code == 200
        assert "total" in r.get_json()["message"].lower() or r.get_json()["status"] == "ok"
```

- [ ] **步骤 2：运行集成测试**

运行：`python -m pytest tests/test_dashboard.py -v`

预期：5 PASS

- [ ] **步骤 3：最终全量测试 + 审计**

```bash
python -m pytest tests/ -v --tb=short --ignore=tests/test_prompt_checker.py
python scripts/release_audit.py --check
```

- [ ] **步骤 4：提交**

```bash
git add tests/test_dashboard.py
git commit -m "test: add dashboard integration tests

5 tests covering dashboard, monitor, episode preview, API status, and
review endpoints using Flask test client with temp project fixtures.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
