"""导演引擎 —— 生成结果的拍摄评估协议。

借鉴 seedance-2.0 的 5 判决 + 单变量规则 + 尝试预算。
只适用于生成阶段（出图/出视频），不替代创作阶段的批判环。

Usage:
    from director import ShootProtocol, Verdict

    protocol = ShootProtocol(max_attempts=5)
    result = protocol.evaluate(shot_id, image_path, expected_desc)
    if result.verdict == Verdict.RETRY:
        protocol.retry(shot_id, new_seed=True)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Verdict(str, Enum):
    KEEP = "keep"           # 直接使用
    FIX = "fix"             # 后期修（不在生成侧改动）
    EDIT = "edit"           # 同 prompt 不同 seed 重生成
    REGEN = "regen"         # 修改 prompt 重生成
    REWRITE = "rewrite"     # 回创作侧改 action_desc/video_prompt


@dataclass
class ShotVerdict:
    shot_id: str
    verdict: Verdict
    reason: str = ""
    suggestion: str = ""     # 修复建议（RETRY/REWRITE 时提供）


@dataclass
class ShootProtocol:
    """拍摄协议：管理每个镜头的尝试预算和重拍历史。

    max_attempts: 每镜最大尝试次数（默认 5）
    """
    max_attempts: int = 5
    _history: dict[str, list[dict]] = field(default_factory=dict)
    _budget: dict[str, int] = field(default_factory=dict)

    def remaining(self, shot_id: str) -> int:
        """返回该镜剩余可用尝试次数。"""
        used = self._budget.get(shot_id, 0)
        return max(0, self.max_attempts - used)

    def can_retry(self, shot_id: str) -> bool:
        return self.remaining(shot_id) > 0

    def record_attempt(self, shot_id: str, verdict: Verdict,
                       change: str = "", note: str = ""):
        """记录一次尝试。"""
        self._budget[shot_id] = self._budget.get(shot_id, 0) + 1
        entry = {
            "attempt": self._budget[shot_id],
            "verdict": verdict.value,
            "change": change,
            "note": note,
        }
        self._history.setdefault(shot_id, []).append(entry)

    def analyze_failures(self, shot_id: str) -> str | None:
        """分析该镜历史尝试，给出建议。连续 2 次 REGEN → 建议 REWRITE。"""
        entries = self._history.get(shot_id, [])
        if len(entries) >= 2:
            last_two = entries[-2:]
            if all(e["verdict"] in (Verdict.REGEN.value, Verdict.EDIT.value)
                   for e in last_two):
                return (
                    f"连续 {len(last_two)} 次重生成未解决问题，"
                    f"建议回创作侧修改 action_desc 或 video_prompt（REWRITE）"
                )
        if self.remaining(shot_id) <= 1:
            return "最后一次尝试，建议改变策略（尝试不同 seed 或修改 prompt 关键句）"
        return None

    # ── 持久化 ─────────────────────────────────────────────────────
    def save_history(self, path: Path) -> None:
        """Persist retake history to a JSON file."""
        import json
        p = path if isinstance(path, Path) else Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self._history, ensure_ascii=False, indent=2),
                       encoding="utf-8")

    def load_history(self, path: Path) -> None:
        """Restore retake history from a JSON file. Rebuilds budget from entries."""
        import json
        p = path if isinstance(path, Path) else Path(path)
        if p.is_file():
            self._history = json.loads(p.read_text(encoding="utf-8"))
            for shot_id, entries in self._history.items():
                self._budget[shot_id] = len(entries)

    # ── 判决辅助逻辑（供 Agent 参考，非自动判定） ──────────────────
    @staticmethod
    def suggest_verdict(issues: list[str]) -> ShotVerdict:
        """根据问题列表给出初步判决建议。
        这是 Agent 的参考框架，最终判决由人工/AI Agent 做出。
        """
        if not issues:
            return ShotVerdict(shot_id="?", verdict=Verdict.KEEP,
                               reason="无问题")
        critical = [i for i in issues if any(
            kw in i for kw in ("角色", "身份", "人脸", "character", "face", "identity"))]
        composition = [i for i in issues if any(
            kw in i for kw in ("构图", "composition", "景别", "角度", "crop"))]
        minor = [i for i in issues if any(
            kw in i for kw in ("色调", "color", "亮度", "brightness", "对比度", "contrast"))]

        if critical:
            return ShotVerdict(
                shot_id="?", verdict=Verdict.REGEN,
                reason=f"角色/身份问题: {', '.join(critical[:2])}",
                suggestion="检查角色 reference 是否已加载，修改 action_desc 的角色描述")
        if composition:
            return ShotVerdict(
                shot_id="?", verdict=Verdict.EDIT,
                reason=f"构图问题: {', '.join(composition[:2])}",
                suggestion="同 prompt 换 seed 重试，或微调景别/角度描述")
        if minor:
            return ShotVerdict(
                shot_id="?", verdict=Verdict.FIX,
                reason=f"后期可修: {', '.join(minor[:2])}",
                suggestion="后期调色/亮度修正即可")
        return ShotVerdict(
            shot_id="?", verdict=Verdict.KEEP,
            reason="问题不严重，可使用")
