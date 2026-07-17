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
        assert r.get_json()["status"] == "ok"
