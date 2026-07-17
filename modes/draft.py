"""Draft mode configuration — fast iteration, relaxed gates."""
from __future__ import annotations

DRAFT_CONFIG = {
    "image": {
        "provider": "gemini", "width": 512, "height": 896,
        "quality": 75, "skip_upscale": True, "skip_anchors": True,
    },
    "video": {"skip": True},
    "dub": {"skip": True},
    "gates": {
        "hard_block_on": ["source_integrity"],
        "relaxed": ["storyboard", "prompts", "first_frames", "provider_health"],
        "skip": ["video_health", "audio_health"],
    },
    "retake": {"enabled": False},
}
