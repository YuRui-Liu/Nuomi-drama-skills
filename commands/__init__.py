"""Commands package — interactive project-management commands.

Registration follows the same hooks.py pattern as quality/gate_g2.py
and exporters/jianying.py.

Commands:
    /nuomi:new          Create a new project skeleton
    /nuomi:review       Run multi-dimension quality review
    /nuomi:compliance   Run content compliance check
"""
from __future__ import annotations

from hooks import register_command

# ── Import handlers to trigger side-effect registration ────────────
import commands.new         # noqa: F401 — registers "new"
import commands.review      # noqa: F401 — registers "review"
import commands.compliance  # noqa: F401 — registers "compliance"
