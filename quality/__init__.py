"""Quality package — review and compliance engines.

Review: 5-dimension 50-point scoring (absorbs short-drama pattern).
Compliance: three-tier risk model (absorbs short-drama P0-P4 framework).

Engines are imported by commands/review.py and commands/compliance.py.
"""
from __future__ import annotations

from quality.review import ReviewReport, Issue, run_review           # noqa: F401
from quality.compliance import ComplianceReport, Finding, run_compliance  # noqa: F401
