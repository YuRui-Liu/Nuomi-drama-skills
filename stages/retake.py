"""Retake controller — connects ShootProtocol to the generation pipeline.

Bridges director.py's ShootProtocol (5-verdict decision logic) with
stages/images.py (actual image generation). This is the missing integration
piece — ShootProtocol already has all the decision logic; this module
enforces the one-variable rule and manages the retry loop.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from director import ShootProtocol, Verdict
from errors import classify_error, Severity


@dataclass
class RetakeResult:
    shot_id: str
    success: bool
    attempts_used: int
    final_verdict: str
    history: list[dict]


class RetakeController:
    """Wraps ShootProtocol with one-variable rule enforcement for generation."""

    def __init__(self, max_attempts: int = 5,
                 history_path: Path | None = None):
        self.protocol = ShootProtocol(max_attempts=max_attempts)
        self._variable_log: dict[str, list[str]] = {}
        self._history_path = history_path
        if history_path:
            self.protocol.load_history(history_path)

    def should_retry(self, shot_id: str, error_msg: str) -> bool:
        """Budget check + verdict suggestion."""
        if not self.protocol.can_retry(shot_id):
            return False
        info = classify_error(error_msg)
        if info.severity == Severity.BLOCK and info.code.name.startswith("GATE"):
            return False
        return True

    def apply_one_variable_rule(self, shot_id: str, prompt: str,
                                 current_seed: int | None = None
                                 ) -> tuple[str, int | None]:
        """Change exactly one variable per retry attempt.
        Priority: seed > prompt phrasing > style suffix > escalate.
        """
        changed = self._variable_log.get(shot_id, [])
        if "seed" not in changed:
            new_seed = ((current_seed or 42) +
                        self.protocol._budget.get(shot_id, 0) * 137)
            self._variable_log.setdefault(shot_id, []).append("seed")
            return prompt, new_seed
        if "prompt" not in changed:
            self._variable_log.setdefault(shot_id, []).append("prompt")
            return (prompt + "\n（重新生成：微调构图角度和光影方向）",
                    current_seed)
        if "style" not in changed and "画风：" in prompt:
            self._variable_log.setdefault(shot_id, []).append("style")
            return prompt.split("\n画风：")[0], current_seed
        self._variable_log.setdefault(shot_id, []).append("escalate")
        return (prompt + "\n（紧急重试：简化场景描述，减少细节）",
                current_seed)

    def record(self, shot_id: str, success: bool, note: str = ""):
        verdict = Verdict.KEEP if success else Verdict.REGEN
        self.protocol.record_attempt(shot_id, verdict, change="", note=note)
        if self._history_path:
            self.protocol.save_history(self._history_path)

    def get_result(self, shot_id: str) -> RetakeResult:
        history = self.protocol._history.get(shot_id, [])
        return RetakeResult(
            shot_id=shot_id,
            success=any(e["verdict"] == Verdict.KEEP.value
                       for e in history),
            attempts_used=self.protocol._budget.get(shot_id, 0),
            final_verdict=history[-1]["verdict"] if history else "unknown",
            history=history,
        )
