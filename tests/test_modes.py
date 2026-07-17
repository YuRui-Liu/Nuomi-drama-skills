from __future__ import annotations
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))


def test_resolve_defaults_to_production():
    from modes import resolve_mode
    assert resolve_mode() == "production"


def test_resolve_explicit_overrides_env(monkeypatch):
    from modes import resolve_mode
    monkeypatch.setenv("NUOMI_MODE", "production")
    assert resolve_mode("draft") == "draft"


def test_resolve_env_var_works(monkeypatch):
    from modes import resolve_mode
    monkeypatch.setenv("NUOMI_MODE", "draft")
    assert resolve_mode() == "draft"


def test_draft_and_production_are_valid():
    from modes import get_config
    draft = get_config("draft")
    prod = get_config("production")
    assert "image" in draft
    assert draft["video"]["skip"] is True
    assert prod["gates"]["hard_block_on"] == "all"
    assert prod["retake"]["enabled"] is True
