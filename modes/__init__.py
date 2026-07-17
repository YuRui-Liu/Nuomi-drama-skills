"""Mode system — draft vs production behavior differentiation.

Resolution priority: explicit arg > NUOMI_MODE env var > "production" default.

Usage:
    from modes import resolve_mode, get_config
    config = get_config("draft")
"""
from __future__ import annotations

import os

from modes.draft import DRAFT_CONFIG
from modes.production import PRODUCTION_CONFIG

MODES: dict[str, dict] = {"draft": DRAFT_CONFIG, "production": PRODUCTION_CONFIG}


def resolve_mode(explicit: str | None = None) -> str:
    """Resolve active mode: explicit arg > env var > 'production'."""
    if explicit and explicit in MODES:
        return explicit
    env = os.environ.get("NUOMI_MODE", "").strip().lower()
    return env if env in MODES else "production"


def get_config(mode: str | None = None) -> dict:
    """Return the full config dict for the resolved mode."""
    return MODES[resolve_mode(mode)]
