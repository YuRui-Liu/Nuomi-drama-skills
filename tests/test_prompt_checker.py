"""Unit tests for prompt_checker — LTX 2.3 prompt validation rules."""

from __future__ import annotations

import pytest

from prompt_checker import (
    LTXPromptError,
    LTXPromptWarning,
    check_video_prompt,
)


# ── Hard blocks ──────────────────────────────────────────────────────────────

def test_rejects_abstract_emotion_in_en() -> None:
    """English prompts with abstract emotion labels must be rejected."""
    prompt = (
        "She looks sad and feels angry about what happened. "
        "Her hands tremble as she grips the table edge. "
        "The room is silent except for the ticking clock. "
        "She closes her eyes and takes a slow breath."
    )
    warnings, errors = check_video_prompt(prompt, lang="en")
    assert len(errors) == 1
    assert "Abstract emotion label detected" in errors[0].message
    assert errors[0].rule == "no_abstract_emotion"
    # The prompt is 4 sentences, so no length warning expected.
    assert len(warnings) == 0


def test_rejects_abstract_emotion_in_zh() -> None:
    """Chinese prompts with abstract emotion labels must be rejected."""
    prompt = "她很难过，也很生气，站在那里一动不动。"
    warnings, errors = check_video_prompt(prompt, lang="zh")
    assert len(errors) == 1
    assert "Abstract emotion label detected" in errors[0].message
    assert errors[0].rule == "no_abstract_emotion"
    assert len(warnings) == 0


def test_rejects_text_logo() -> None:
    """Prompts describing text or logos on screen must be rejected."""
    prompt = "A man walks past a billboard with a headline that reads 'SALE'."
    warnings, errors = check_video_prompt(prompt, lang="en")
    assert len(errors) >= 1
    # At least one error should mention text/logo
    assert any("text" in e.message.lower() or "logo" in e.message.lower()
               for e in errors)
    assert any(e.rule == "no_text_logo" for e in errors)


# ── Soft warnings ────────────────────────────────────────────────────────────

def test_warns_complex_physics() -> None:
    """Prompts with shatter/explode/fragment should trigger a warning."""
    prompt = (
        "A glass window shatters into a thousand pieces. "
        "The fragments scatter across the floor. "
        "The room is silent. "
        "Then a figure steps through the broken frame."
    )
    warnings, errors = check_video_prompt(prompt, lang="en")
    assert len(errors) == 0
    assert len(warnings) >= 1
    assert any("Complex physics" in w.message for w in warnings)
    assert any(w.rule == "complex_physics_warning" for w in warnings)


def test_warns_too_many_characters() -> None:
    """Character count >3 must trigger a warning."""
    prompt = (
        "Four people stand in a room. "
        "The first adjusts their tie. "
        "The second crosses their arms. "
        "The third shifts their weight. "
        "The fourth looks out the window."
    )
    warnings, errors = check_video_prompt(prompt, lang="en", character_count=4)
    assert len(errors) == 0
    assert len(warnings) >= 1
    assert any("character" in w.message.lower() and "4" in w.message
               for w in warnings)
    assert any(w.rule == "character_count_warning" for w in warnings)


def test_warns_short_prompt() -> None:
    """English prompts with fewer than 4 sentences should warn."""
    prompt = "A woman walks through a park. The sun sets behind her."
    warnings, errors = check_video_prompt(prompt, lang="en")
    assert len(errors) == 0
    assert len(warnings) >= 1
    assert any("short" in w.message.lower() or "2 sentences" in w.message
               for w in warnings)
    assert any(w.rule == "prompt_length_warning" for w in warnings)


def test_warns_long_prompt() -> None:
    """English prompts with more than 8 sentences should warn."""
    prompt = (
        "The camera pans across a dimly lit room. "
        "A man sits at a wooden desk. "
        "He opens a leather-bound journal. "
        "His fingers trace faded ink on the page. "
        "A clock ticks loudly in the background. "
        "Shadows stretch across the wall behind him. "
        "He glances toward the doorway. "
        "A floorboard creaks in the hallway. "
        "His hand freezes mid-motion."
    )
    warnings, errors = check_video_prompt(prompt, lang="en")
    assert len(errors) == 0
    assert len(warnings) >= 1
    assert any("long" in w.message.lower() or "9 sentences" in w.message
               for w in warnings)
    assert any(w.rule == "prompt_length_warning" for w in warnings)


def test_warns_conflicting_lighting() -> None:
    """Simultaneous front light and backlight should trigger a warning."""
    prompt = (
        "The subject is lit by strong front lighting. "
        "A backlight rim highlights their silhouette. "
        "The camera holds steady. "
        "Dust motes float through the beams of light."
    )
    warnings, errors = check_video_prompt(prompt, lang="en")
    assert len(errors) == 0
    assert len(warnings) >= 1
    assert any("conflicting" in w.message.lower() or "light" in w.message.lower()
               for w in warnings)
    assert any(w.rule == "conflicting_light_warning" for w in warnings)


def test_passes_clean_prompt() -> None:
    """A clean, well-structured prompt should pass all checks."""
    prompt = (
        "A woman leans against a rain-streaked window. "
        "Her shoulders slump and her eyes fix on the floor. "
        "Droplets race down the glass in uneven trails. "
        "She exhales slowly, breath fogging the pane. "
        "The room behind her is dim and still."
    )
    warnings, errors = check_video_prompt(prompt, lang="en")
    assert len(warnings) == 0, f"Unexpected warnings: {warnings}"
    assert len(errors) == 0, f"Unexpected errors: {errors}"
