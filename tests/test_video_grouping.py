"""Unit tests for narrative group batching in stages/video.py."""

from __future__ import annotations

import pytest

from stages.video import DirectorCall, build_director_calls, _MAX_GROUP_DURATION


# ── Helper factories ──────────────────────────────────────────────────────────

def _shot(sid: str, duration: float, scene: str, prompt: str = "") -> dict:
    return {"shot_id": sid, "duration": duration, "scene": scene, "video_prompt_en": prompt}


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestBuildDirectorCalls:
    """Unit tests for build_director_calls grouping logic."""

    def test_same_scene_under_18s_merged(self) -> None:
        """Shots in the same scene under 18s total → single DirectorCall."""
        shot_group = {"shot_ids": ["s1", "s2", "s3"]}
        shots = [
            _shot("s1", 4, "park", "walking in the park"),
            _shot("s2", 5, "park", "running through trees"),
            _shot("s3", 6, "park", "sitting on a bench"),
        ]
        calls = build_director_calls(shot_group, shots)

        assert len(calls) == 1
        assert calls[0].motion_mode == "smooth"
        assert len(calls[0].segments) == 3
        assert [s["shot_id"] for s in calls[0].segments] == ["s1", "s2", "s3"]

    def test_different_scenes_split(self) -> None:
        """Scene change forces a new DirectorCall even under 18s total."""
        shot_group = {"shot_ids": ["s1", "s2", "s3"]}
        shots = [
            _shot("s1", 4, "park", "walking"),
            _shot("s2", 5, "office", "typing"),
            _shot("s3", 3, "park", "sitting"),
        ]
        calls = build_director_calls(shot_group, shots)

        # s1(park)→s2(office): split. s2(office)→s3(park): split.
        assert len(calls) == 3
        assert [len(c.segments) for c in calls] == [1, 1, 1]
        assert [c.segments[0]["shot_id"] for c in calls] == ["s1", "s2", "s3"]

    def test_over_18s_splits(self) -> None:
        """Same scene but total >18s → split into multiple calls."""
        shot_group = {"shot_ids": ["s1", "s2", "s3"]}
        shots = [
            _shot("s1", 10, "park", "slow walk"),
            _shot("s2", 8, "park", "start running"),
            _shot("s3", 5, "park", "stop at fountain"),
        ]
        calls = build_director_calls(shot_group, shots)

        # s1(10) + s2(8) = 18 ≤ 18 → one call; s3(5) alone → new call
        assert len(calls) == 2
        assert [len(c.segments) for c in calls] == [2, 1]

        all_shot_ids = [s["shot_id"] for c in calls for s in c.segments]
        assert all_shot_ids == ["s1", "s2", "s3"]
