from __future__ import annotations
import json, tempfile
from pathlib import Path
import sys; sys.path.insert(0, str(Path(__file__).parents[1]))


def test_full_pipeline_new_to_compliance():
    """End-to-end: new → review → compliance → srt export → ffmpeg export"""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)

        # 1. /nuomi:new
        from commands.new import run_new
        result = run_new(out_dir=str(out), args=[], ref_paths=[], state={"phase": "ideation"})
        assert result["status"] in ("ok", "resumed")
        assert (out / "manuscript").is_dir()

        # 2. Create minimal content
        manuscript_dir = out / "manuscript"
        (manuscript_dir / "E1.md").write_text(
            "# E1 第一集\n\n## 剧本\n\n男主走进办公室。\n\n## 分镜表\n\n"
            "```json\n"
            '{"shots": [{"shot_id": "s01", "duration": 3.0, "scene": "办公室", '
            '"action_desc": "男主推门走进办公室", '
            '"video_prompt": "一个男人推开办公室的门，缓步走进来", '
            '"video_prompt_en": "A man pushes open the office door and walks in slowly", '
            '"dialogue": [{"speaker": "男主", "text": "你来了。"}], "relation": "cut"}]}\n'
            "```\n",
            encoding="utf-8",
        )

        # Create fake gen_context.json
        ep_dir = out / "E1"
        ep_dir.mkdir(parents=True, exist_ok=True)
        ctx = {
            "storyboard": {
                "shots": [{
                    "shot_id": "s01", "duration": 3.0, "scene": "办公室",
                    "action_desc": "男主推门走进办公室",
                    "video_prompt": "一个男人推开办公室的门，缓步走进来",
                    "video_prompt_en": "A man pushes open the office door and walks in slowly",
                    "dialogue": [{"speaker": "男主", "text": "你来了。"}],
                    "relation": "cut"
                }]
            }
        }
        (ep_dir / "gen_context.json").write_text(
            json.dumps(ctx, ensure_ascii=False), encoding="utf-8")

        # Set state to scripting
        from writing_state import save_state
        save_state(out, {"phase": "scripting", "completed_episodes": [1],
                          "current_episode": 1, "current_arc": 1,
                          "gates_passed": [], "gates_warnings": {},
                          "review_history": [], "compliance_history": []})

        # 3. Review
        from commands.review import run_review
        result = run_review(out_dir=str(out), args=[], ref_paths=[], state={"phase": "scripting"})
        assert result["status"] == "ok"
        assert (out / "review_report.json").is_file()
        report_data = json.loads((out / "review_report.json").read_text(encoding="utf-8"))
        assert 0 <= report_data["total"] <= 50

        # 4. Compliance
        from commands.compliance import run_compliance
        result = run_compliance(out_dir=str(out), args=[], ref_paths=[], state={"phase": "scripting"})
        assert result["status"] == "ok"
        assert (out / "compliance_report.json").is_file()

        # 5. SRT export
        from exporters.srt import export_srt
        paths = export_srt(str(out), [1])
        assert len(paths) >= 1
        assert paths[0].is_file()

        # 6. FFmpeg export
        from exporters.ffmpeg import export_ffmpeg
        paths = export_ffmpeg(str(out), [1])
        assert len(paths) >= 1
        assert paths[0].is_file()
