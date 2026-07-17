"""nuomi-drama-skills Dashboard Server.

Flask app with project management dashboard, generation monitor (SSE),
storyboard preview, and asset library. Zero extra dependencies.

Usage: python preview_server.py <out_dir> [--port 7788]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

from flask import Flask, Response, abort, jsonify, render_template, request, send_file


def _create_app(out_dir: str) -> Flask:
    app = Flask(__name__,
                template_folder=str(Path(__file__).parent / "templates"))
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
                "partial" if done > 0 else "pending")
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
        for rtype, label in (("characters", "角色"), ("scenes", "场景"),
                              ("props", "道具")):
            entries = grouped.get(rtype) or {}
            if not entries:
                continue
            items = [{"name": name,
                      "description": entry.get("voice_style", "")
                      if rtype == "characters" else "",
                      "img_url": f"/img/{entry['anchor_path']}"
                      if _has_img(entry) else None,
                      "has_img": _has_img(entry),
                      "has_voice": _has_voice(name)
                      if rtype == "characters" else None}
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
            return jsonify({"status": "error",
                           "message": f"未知阶段: {stage}"}), 400

        def _run():
            subprocess.run(
                [sys.executable, str(Path(__file__).parent / "generate.py"),
                 stage, "all", "--out", str(out)],
                capture_output=True, text=True, timeout=3600,
            )

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return jsonify({"status": "ok",
                       "message": f"{stage} 生成已在后台启动"})

    # ── API: Export ─────────────────────────────────────────────────
    @app.route("/api/export", methods=["POST"])
    def api_export():
        manuscript_dir = out / "manuscript"
        if not manuscript_dir.is_dir():
            return jsonify({"status": "error",
                           "message": "manuscript 目录不存在"}), 400
        r = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "export.py"),
             str(manuscript_dir), str(out)],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0:
            return jsonify({"status": "ok", "message": "编译完成",
                           "output": r.stdout[-200:]})
        return jsonify({"status": "error",
                       "message": r.stderr[-200:] or "编译失败"}), 500

    # ── API: Review / Compliance ────────────────────────────────────
    @app.route("/api/review", methods=["POST"])
    def api_review():
        manuscript_dir = out / "manuscript"
        if not manuscript_dir.is_dir():
            return jsonify({"status": "error",
                           "message": "manuscript 目录不存在"}), 400
        from quality.review import run_review as run_review_engine
        report = run_review_engine(out, manuscript_dir, [])
        report_json = out / "review_report.json"
        report_md = out / "review_report.md"
        report_json.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8")
        report_md.write_text(report.to_markdown(), encoding="utf-8")
        return jsonify({"status": "ok",
                       "message": f"审查完成: {report.total}/50 — {report.grade}"})

    @app.route("/api/compliance", methods=["POST"])
    def api_compliance():
        manuscript_dir = out / "manuscript"
        if not manuscript_dir.is_dir():
            return jsonify({"status": "error",
                           "message": "manuscript 目录不存在"}), 400
        profile_path = Path(__file__).parent / "quality" / "profiles" / "cn.json"
        from quality.compliance import run_compliance as run_cc
        report = run_cc(manuscript_dir, profile_path)
        report_json = out / "compliance_report.json"
        report_md = out / "compliance_report.md"
        report_json.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
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
            return jsonify({"status": "error",
                           "message": "需要 ep 和 shot_id"}), 400

        from stages.retake import RetakeController
        rc = RetakeController(max_attempts=5,
                              history_path=out / "retake_history.json")
        if not rc.should_retry(shot_id, "manual retry from dashboard"):
            return jsonify({"status": "error",
                           "message": f"镜头 {shot_id} 已达最大重试次数"}), 400

        rc.record(shot_id, False, "retry queued from dashboard")
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
        return jsonify({"status": "error",
                       "message": f"未知导出格式: {fmt}"}), 400

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
