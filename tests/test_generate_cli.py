from __future__ import annotations
import json, tempfile
from pathlib import Path


def test_episode_count_returns_tuple():
    """_episode_count returns episode_count int from series.json"""
    import generate
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        series = {"episode_count": 3, "episodes": [
            {"episode_id": "E1", "script": "..."},
            {"episode_id": "E2", "script": "..."},
            {"episode_id": "E3"},
        ]}
        (out / "series.json").write_text(json.dumps(series, ensure_ascii=False), encoding="utf-8")
        count = generate._episode_count(str(out))
        assert count == 3


def test_episode_count_missing_series_json():
    """series.json not found returns 1"""
    import generate
    with tempfile.TemporaryDirectory() as td:
        count = generate._episode_count(td)
        assert count == 1
