# .claude/skills/nuomi-drama-skills/preview_server.py
"""Flask 分镜预览服务器。
用法: python preview_server.py <out_project_dir> [--port 7788]
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from flask import Flask, abort, send_file, render_template_string

OUT_DIR = ""  # 测试时由 fixture 覆盖

_INDEX_HTML = """
<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>分镜预览 — {{ title }}</title>
<style>
body{margin:0;font-family:sans-serif;display:flex;height:100vh;overflow:hidden;background:#0d1117;color:#ccc}
#sidebar{width:140px;flex-shrink:0;background:#0d1117;border-right:1px solid #21262d;overflow-y:auto;padding:8px}
#sidebar h2{font-size:11px;color:#7ec87e;margin:0 0 8px}
.ep-input{display:flex;gap:4px;margin-bottom:8px}
.ep-input input{width:50px;background:#161b22;border:1px solid #333;border-radius:3px;color:#fff;font-size:11px;padding:3px 5px}
.ep-input button{background:#238636;border:none;border-radius:3px;color:#fff;font-size:10px;padding:3px 6px;cursor:pointer}
.ep-link{display:block;padding:5px 7px;border-radius:3px;margin-bottom:2px;font-size:11px;color:#aaa;text-decoration:none;border-left:2px solid transparent}
.ep-link:hover{background:#21262d;color:#fff}
.ep-link.active{background:#21262d;color:#fff;border-left-color:#7ec87e}
#main{flex:1;overflow-y:auto;padding:12px}
</style></head><body>
<div id="sidebar">
  <h2>{{ title }}</h2>
  <a href="/assets" style="display:block;padding:4px 7px;border-radius:3px;margin-bottom:6px;font-size:11px;color:#7ec87e;text-decoration:none;border:1px solid #21262d">📦 资源库</a>
  <div class="ep-input">
    <input id="ep-input" placeholder="E?" onkeydown="if(event.key==='Enter'){goEp()}">
    <button onclick="goEp()">→</button>
  </div>
  {% for ep in episodes %}
  <a class="ep-link {% if current_ep == ep.n %}active{% endif %}"
     href="/ep/{{ ep.n }}">E{{ ep.n }} {{ ep.status }}</a>
  {% endfor %}
</div>
<div id="main">{% block content %}{% endblock %}</div>
<script>
function goEp(){var v=document.getElementById('ep-input').value.replace(/^[Ee]/,'');
if(v)window.location='/ep/'+parseInt(v);}
</script>
</body></html>
"""

_EP_HTML = _INDEX_HTML.replace("{% block content %}{% endblock %}", """
<div style="border-bottom:1px solid #21262d;padding:0 0 10px;margin-bottom:12px;display:flex;align-items:center;gap:12px">
  <span style="font-size:15px;font-weight:600;color:#fff">E{{ ep }}</span>
  <span style="font-size:12px;color:#aaa">{{ shots|length }} 镜</span>
</div>
{% for s in shots %}
<div style="display:flex;gap:10px;align-items:flex-start;background:#161b22;border-radius:5px;border:1px solid #30363d;padding:10px;margin-bottom:8px">
  {% if s.img_url %}
  <img src="{{ s.img_url }}" style="width:54px;height:96px;border-radius:3px;object-fit:cover;flex-shrink:0">
  {% else %}
  <div style="width:54px;height:96px;background:#1c1c1c;border-radius:3px;flex-shrink:0;display:flex;align-items:center;justify-content:center;color:#555;font-size:10px">⏳</div>
  {% endif %}
  <div style="flex:1;font-size:11px">
    <div style="margin-bottom:4px"><span style="color:#7ec87e;font-weight:600">{{ s.shot_id }}</span>
      <span style="color:#aaa;margin-left:6px">{{ s.duration }}s</span>
      <span style="margin-left:auto;float:right">
        {{ "🖼✅" if s.has_img else "🖼⏳" }}
        {{ "🎬✅" if s.has_vid else "🎬⏳" }}
        {{ "🎙️✅" if s.has_dub else ("🎙️—" if not s.has_dialogue else "🎙️⏳") }}
      </span>
    </div>
    <div style="color:#ccc;margin-bottom:4px">{{ s.action_desc }}</div>
    {% if s.dialogue %}
    {% for line in s.dialogue %}
    <div style="padding:3px 6px;background:#0d1117;border-left:2px solid #7ec8e3;border-radius:2px;margin-top:3px;color:#e3c87e;font-size:10px">
      💬 <b>{{ line.speaker }}</b>（{{ line.emotion }}）：{{ line.text }}
    </div>
    {% endfor %}
    {% endif %}
  </div>
</div>
{% endfor %}
""")

_ASSETS_HTML = _INDEX_HTML.replace("{% block content %}{% endblock %}", """
<h2 style="color:#fff;font-size:13px;font-weight:600;margin:0 0 14px">📦 资源库</h2>
{% for section in sections %}
<div style="margin-bottom:18px">
  <div style="font-size:11px;color:#7ec87e;font-weight:600;margin-bottom:6px;padding-bottom:4px;border-bottom:1px solid #21262d">
    {{ section.label }}（{{ section.rows|length }}）
  </div>
  {% for item in section.rows %}
  <div style="display:flex;gap:10px;align-items:center;background:#161b22;border-radius:4px;border:1px solid #30363d;padding:8px;margin-bottom:4px">
    {% if item.img_url %}
    <img src="{{ item.img_url }}" style="width:36px;height:64px;border-radius:3px;object-fit:cover;flex-shrink:0">
    {% else %}
    <div style="width:36px;height:64px;background:#1c1c1c;border-radius:3px;flex-shrink:0;display:flex;align-items:center;justify-content:center;color:#555;font-size:9px">⏳</div>
    {% endif %}
    <div style="flex:1;font-size:11px">
      <div style="color:#ccc;font-weight:600;margin-bottom:2px">{{ item.name }}</div>
      {% if item.description %}<div style="color:#777;font-size:10px">{{ item.description }}</div>{% endif %}
    </div>
    <div style="display:flex;gap:8px;font-size:12px;flex-shrink:0">
      {% if item.has_img is defined %}{{ "🖼✅" if item.has_img else "🖼⏳" }}{% endif %}
      {% if item.has_voice is defined %}{{ "🎙️✅" if item.has_voice else "🎙️⏳" }}{% endif %}
    </div>
  </div>
  {% endfor %}
</div>
{% endfor %}
{% if not sections %}<p style="color:#555;font-size:12px">registry.json 为空，暂无资源。</p>{% endif %}
""")


def _ep_status(out: Path, ep: int, shot_count: int) -> str:
    sa = out / f"E{ep}" / "shots_assets"
    imgs = list(sa.glob("*.jpg")) if sa.exists() else []
    if len(imgs) >= shot_count:
        return "✅"
    if imgs:
        return "🔄"
    return "⏳"


def create_app(out_dir: str) -> Flask:
    app = Flask(__name__)
    out = Path(out_dir)

    def _series():
        p = out / "series.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    def _ctx(ep: int):
        p = out / f"E{ep}" / "gen_context.json"
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    @app.route("/")
    def index():
        series = _series()
        count = int(series.get("episode_count", 0))
        eps = []
        for n in range(1, count + 1):
            ctx = _ctx(n)
            shots = ((ctx or {}).get("storyboard") or {}).get("shots") or []
            eps.append({"n": n, "status": _ep_status(out, n, len(shots))})
        return render_template_string(_INDEX_HTML, title=series.get("title", "预览"),
                                      episodes=eps, current_ep=None)

    @app.route("/ep/<int:ep>")
    def episode(ep: int):
        ctx = _ctx(ep)
        if ctx is None:
            abort(404)
        series = _series()
        count = int(series.get("episode_count", 0))
        eps = []
        for n in range(1, count + 1):
            c2 = _ctx(n)
            s2 = ((c2 or {}).get("storyboard") or {}).get("shots") or []
            eps.append({"n": n, "status": _ep_status(out, n, len(s2))})

        shots_raw = (ctx.get("storyboard") or {}).get("shots") or []
        sa = out / f"E{ep}" / "shots_assets"
        audio_dir = out / "audio" / f"E{ep}" / "dub"
        shots = []
        for s in shots_raw:
            sid = str(s.get("shot_id", ""))
            has_img = (sa / f"{sid}.jpg").exists()
            has_vid = (sa / f"{sid}.mp4").exists()
            dialogue = s.get("dialogue") or []
            has_dub = bool(dialogue) and (audio_dir / f"{sid}_{(dialogue[0].get('speaker','x'))}_line0.wav").exists()
            shots.append({
                "shot_id": sid,
                "duration": s.get("duration", "?"),
                "action_desc": s.get("action_desc", ""),
                "dialogue": dialogue,
                "has_dialogue": bool(dialogue),
                "has_img": has_img,
                "has_vid": has_vid,
                "has_dub": has_dub,
                "img_url": f"/img/E{ep}/shots_assets/{sid}.jpg" if has_img else None,
            })
        return render_template_string(_EP_HTML, title=series.get("title", "预览"),
                                      episodes=eps, current_ep=ep, ep=ep, shots=shots)

    @app.route("/assets")
    def assets():
        series = _series()
        count = int(series.get("episode_count", 0))
        eps = []
        for n in range(1, count + 1):
            ctx = _ctx(n)
            shots = ((ctx or {}).get("storyboard") or {}).get("shots") or []
            eps.append({"n": n, "status": _ep_status(out, n, len(shots))})

        reg_path = out / "assets" / "registry.json"
        registry = (json.loads(reg_path.read_text(encoding="utf-8"))
                    if reg_path.exists() else {})
        voices_path = out / "assets" / "voices.json"
        voices = (json.loads(voices_path.read_text(encoding="utf-8"))
                  if voices_path.exists() else {})

        def _has_img(entry):
            ap = entry.get("anchor_path")
            return bool(ap and (out / ap).exists())

        def _has_voice(name):
            v = voices.get(name, {})
            return v.get("status") == "ready" and bool(v.get("anchor_path"))

        # 兼容两种 registry 结构：
        #   1) 扁平键 "character/沈云晚" / "scene/xxx" / "prop/xxx" (平台 v1 实际格式)
        #   2) 分组 {"characters": {...}, "scenes": {...}, "props": {...}} (测试用旧格式)
        grouped = {"characters": {}, "scenes": {}, "props": {}}
        if any("/" in k for k in registry.keys()):
            for key, entry in registry.items():
                prefix, _, name = key.partition("/")
                bucket = {"character": "characters", "scene": "scenes", "prop": "props"}.get(prefix)
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
            items = []
            for name, entry in entries.items():
                has_img = _has_img(entry)
                item = {
                    "name": name,
                    "description": entry.get("voice_style", "") if rtype == "characters" else "",
                    "img_url": f"/img/{entry['anchor_path']}" if has_img else None,
                    "has_img": has_img,
                }
                if rtype == "characters":
                    item["has_voice"] = _has_voice(name)
                items.append(item)
            sections.append({"label": label, "rows": items})

        if voices:
            rows = [{"name": n, "description": v.get("voice_style", ""),
                     "has_voice": v.get("status") == "ready"}
                    for n, v in voices.items()]
            sections.append({"label": "音色", "rows": rows})

        return render_template_string(
            _ASSETS_HTML, title=series.get("title", "预览"),
            episodes=eps, current_ep=None, sections=sections)

    @app.route("/img/<path:rel>")
    def img(rel: str):
        p = out / rel
        if not p.exists() or not p.is_file():
            abort(404)
        return send_file(str(p))

    return app


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out_dir", help="编译输出目录")
    parser.add_argument("--port", type=int, default=7788)
    args = parser.parse_args()
    app = create_app(args.out_dir)
    print(f"预览服务器：http://localhost:{args.port}")
    app.run(host="0.0.0.0", port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
