from __future__ import annotations
import json, tempfile
from pathlib import Path
import sys; sys.path.insert(0, str(Path(__file__).parents[1]))


def test_load_aosop_empty_dir():
    from aosop import load_aosop
    with tempfile.TemporaryDirectory() as td:
        state = load_aosop(td)
        assert state.project_phase == "unknown"
        assert state.total_shots == 0
        assert state.acceptance_rate == 0.0


def test_load_aosop_with_episodes():
    from aosop import load_aosop
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        # writing_state
        (out / "writing_state.json").write_text(
            '{"phase": "scripting"}', encoding="utf-8")
        # episode
        ep_dir = out / "E1"
        ep_dir.mkdir()
        (ep_dir / "gen_context.json").write_text(
            '{"storyboard": {"shots": [{"shot_id": "s01"}, {"shot_id": "s02"}]}}',
            encoding="utf-8")
        # one generated product
        shots_dir = ep_dir / "shots_assets"
        shots_dir.mkdir()
        (shots_dir / "s01.jpg").write_bytes(b"fake jpg")

        state = load_aosop(td)
        assert state.project_phase == "scripting"
        assert state.total_shots == 2
        assert state.episodes[0].observed == 1
        assert state.episodes[0].planned == 2  # all shots counted as planned


def test_load_aosop_with_accepted_shots():
    from aosop import load_aosop
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        (out / "E1").mkdir()
        (out / "E1" / "gen_context.json").write_text(
            '{"storyboard": {"shots": [{"shot_id": "s01"}]}}', encoding="utf-8")
        (out / "aosop_state.json").write_text(json.dumps({
            "shots": [{"shot_id": "s01", "state": "accepted",
                        "accepted_at": "2026-07-17T00:00:00Z"}]
        }), encoding="utf-8")

        state = load_aosop(td)
        assert state.episodes[0].accepted == 1
        assert state.acceptance_rate == 1.0


def test_load_aosop_with_errors():
    from aosop import load_aosop
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        (out / "E1").mkdir()
        (out / "E1" / "gen_context.json").write_text(
            '{"storyboard": {"shots": [{"shot_id": "s01"}]}}', encoding="utf-8")
        (out / "generate_log.json").write_text(
            '{"shot_id": "s01", "ep": 1, "stage": "images", "error": "failed"}\n'
            '{"shot_id": "s01", "ep": 1, "stage": "images", "error": "retry"}\n',
            encoding="utf-8")

        state = load_aosop(td)
        assert state.episodes[0].failed == 1
        assert state.episodes[0].shots[0].error_count == 2


def test_aosop_state_to_dict():
    from aosop import AOSOPState, EpisodeAOSOP, ShotState, ShotAOSOPState
    state = AOSOPState(project_phase="scripting", episodes=[
        EpisodeAOSOP(ep=1, total_shots=1, planned=1, shots=[
            ShotState("s01", 1, ShotAOSOPState.PLANNED)
        ])
    ])
    d = state.to_dict()
    assert d["project_phase"] == "scripting"
    assert len(d["episodes"]) == 1
