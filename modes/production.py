"""Production mode configuration — full quality, all gates enabled."""
from __future__ import annotations

PRODUCTION_CONFIG = {
    "image": {
        "provider": "grsai", "width": 768, "height": 1344,
        "quality": 92, "skip_upscale": False, "skip_anchors": False,
    },
    "video": {"skip": False},
    "dub": {"skip": False},
    "gates": {"hard_block_on": "all"},
    "retake": {"enabled": True, "max_attempts": 5},
}
