from __future__ import annotations
import json, tempfile
from pathlib import Path
import sys; sys.path.insert(0, str(Path(__file__).parents[1]))


def test_empty_dir_returns_healthy():
    from observability import build_summary
    with tempfile.TemporaryDirectory() as td:
        summary = build_summary(td)
        assert summary.total_episodes == 0
        assert summary.overall_health == "healthy"


def test_full_pipeline_summary():
    from observability import build_summary
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        ep_dir = out / "E1"
        ep_dir.mkdir(parents=True)
        ctx = {"storyboard": {"shots": [
            {"shot_id": "s01"}, {"shot_id": "s02"}, {"shot_id": "s03"}
        ]}}
        (ep_dir / "gen_context.json").write_text(
            json.dumps(ctx, ensure_ascii=False), encoding="utf-8")
        shots_dir = ep_dir / "shots_assets"
        shots_dir.mkdir()
        (shots_dir / "s01.jpg").write_bytes(b"fake jpg")

        summary = build_summary(td)
        assert summary.total_episodes == 1
        ep = summary.episodes[0]
        assert ep.images.done == 1
        assert ep.images.total == 3


def test_summary_markdown_output():
    from observability import build_summary
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        (out / "E1").mkdir()
        (out / "E1" / "gen_context.json").write_text(
            '{"storyboard": {"shots": []}}', encoding="utf-8")
        summary = build_summary(td)
        md = summary.to_markdown()
        assert "生成摘要" in md
        assert "E1" in md


def test_summary_with_generate_log():
    from observability import build_summary
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        (out / "E1").mkdir()
        (out / "E1" / "gen_context.json").write_text(
            '{"storyboard": {"shots": [{"shot_id": "s01"}]}}', encoding="utf-8")
        (out / "generate_log.json").write_text(
            '{"ep": 1, "stage": "images", "error": "test"}\n', encoding="utf-8")
        summary = build_summary(td)
        assert summary.episodes[0].images.failed == 1
