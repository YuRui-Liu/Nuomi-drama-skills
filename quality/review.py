"""Multi-dimension quality review engine.

Absorbs short-drama 5-dimension 50-point scoring system, mapped to
nuomi's generation pipeline context.

Dimensions:
    1. 剧本格式 (format)           — Markdown structure, JSON fence validity
    2. 分镜连贯 (continuity)        — shot_id uniqueness, relation enum, scene flow
    3. 提示词质量 (prompt_quality)   — LTX prompt compliance, bilingual, length
    4. 角色一致性 (char_consistency) — name normalization, bible cross-reference
    5. 爽点节奏 (satisfaction)       — hook density, satisfaction distribution

Output: ReviewReport with scores, total, grade, highlights, issues.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Issue:
    """A single review finding."""
    severity: str       # "⛔阻断" / "⚠️建议" / "ℹ️微调"
    dimension: str
    location: str       # "E1:s01" or "manuscript/01_大纲.md:5"
    description: str
    suggestion: str

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "dimension": self.dimension,
            "location": self.location,
            "description": self.description,
            "suggestion": self.suggestion,
        }


@dataclass
class ReviewReport:
    """Complete review report with scores, grade, and issue list."""
    scores: dict[str, int]
    total: int
    grade: str
    highlights: list[str] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scores": self.scores,
            "total": self.total,
            "grade": self.grade,
            "highlights": self.highlights,
            "issues": [i.to_dict() for i in self.issues],
        }

    def to_markdown(self) -> str:
        dim_cn = {
            "format": "剧本格式", "continuity": "分镜连贯",
            "prompt_quality": "提示词质量", "char_consistency": "角色一致性",
            "satisfaction": "爽点节奏",
        }
        lines = [
            f"# 审查报告",
            f"",
            f"**总分**: {self.total}/50 — **{self.grade}**",
            f"",
            f"| 维度 | 得分 |",
            f"|------|------|",
        ]
        for dim, score in self.scores.items():
            name = dim_cn.get(dim, dim)
            lines.append(f"| {name} | {score}/10 |")
        lines.append("")
        if self.highlights:
            lines.append("## 亮点")
            for h in self.highlights:
                lines.append(f"- ✅ {h}")
            lines.append("")
        if self.issues:
            lines.append("## 问题")
            for issue in self.issues:
                lines.append(f"- {issue.severity} **{issue.location}**: {issue.description}")
                lines.append(f"  → {issue.suggestion}")
        return "\n".join(lines)


def _grade(total: int) -> str:
    if total == 0:
        return "无内容"
    if total >= 45:
        return "卓越"
    if total >= 38:
        return "优良"
    if total >= 30:
        return "合格"
    return "需改进"


def run_review(out_dir: Path, manuscript_dir: Path,
               ref_paths: list[Path]) -> ReviewReport:
    """Run 5-dimension review on manuscript content."""
    scores: dict[str, int] = {}
    all_issues: list[Issue] = []
    highlights: list[str] = []

    md_files = sorted(manuscript_dir.rglob("*.md"))
    if not md_files:
        return ReviewReport(
            scores={"format": 0, "continuity": 0, "prompt_quality": 0,
                    "char_consistency": 0, "satisfaction": 0},
            total=0, grade="无内容",
        )

    format_score, format_issues = _check_format(manuscript_dir, md_files)
    scores["format"] = format_score
    all_issues.extend(format_issues)

    cont_score, cont_issues = _check_continuity(out_dir, md_files)
    scores["continuity"] = cont_score
    all_issues.extend(cont_issues)

    pq_score, pq_issues = _check_prompt_quality(out_dir)
    scores["prompt_quality"] = pq_score
    all_issues.extend(pq_issues)

    cc_score, cc_issues = _check_char_consistency(manuscript_dir)
    scores["char_consistency"] = cc_score
    all_issues.extend(cc_issues)

    sat_score, sat_issues = _check_satisfaction_rhythm(manuscript_dir, md_files)
    scores["satisfaction"] = sat_score
    all_issues.extend(sat_issues)

    total = sum(scores.values())
    return ReviewReport(
        scores=scores, total=total, grade=_grade(total),
        highlights=highlights, issues=all_issues,
    )


def _check_format(manuscript_dir: Path,
                  md_files: list[Path]) -> tuple[int, list[Issue]]:
    issues: list[Issue] = []
    score = 10

    for f in md_files:
        text = f.read_text(encoding="utf-8")
        opens = text.count("```json")
        closes = text.count("```")
        if opens > 0 and opens != closes // 2:
            issues.append(Issue("⚠️建议", "format",
                                str(f.relative_to(manuscript_dir)),
                                "JSON fence 不配对", "检查 ```json 和 ``` 数量是否一致"))
            score = max(0, score - 1)

        blocks = re.findall(r"```json\n(.*?)```", text, re.DOTALL)
        for i, block in enumerate(blocks):
            try:
                json.loads(block)
            except json.JSONDecodeError as e:
                issues.append(Issue("⛔阻断", "format",
                                    f"{f.relative_to(manuscript_dir)}:block{i+1}",
                                    f"JSON 解析失败: {e}", "修正 JSON 语法"))
                score = max(0, score - 2)

    return max(0, score), issues


def _check_continuity(out_dir: Path,
                      md_files: list[Path]) -> tuple[int, list[Issue]]:
    issues: list[Issue] = []
    score = 10
    valid_relations = {"cut", "dissolve", "fade", "wipe", ""}

    for ctx_file in sorted(out_dir.rglob("gen_context.json")):
        try:
            data = json.loads(ctx_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sb = data.get("storyboard") or {}
        shots = sb.get("shots") or []
        if not isinstance(shots, list):
            continue

        shot_ids: set[str] = set()
        for s in shots:
            if not isinstance(s, dict):
                continue
            sid = str(s.get("shot_id", ""))
            if not sid:
                issues.append(Issue("⛔阻断", "continuity",
                                    str(ctx_file.relative_to(out_dir)),
                                    "shot 缺少 shot_id", "为每个镜头分配唯一 ID"))
                score = max(0, score - 3)
                continue
            if sid in shot_ids:
                issues.append(Issue("⛔阻断", "continuity",
                                    str(ctx_file.relative_to(out_dir)),
                                    f"shot_id {sid} 重复", "确保每个 shot_id 唯一"))
                score = max(0, score - 3)
            shot_ids.add(sid)

            rel = s.get("relation", "")
            if rel and rel not in valid_relations:
                issues.append(Issue("⚠️建议", "continuity",
                                    f"{ctx_file.relative_to(out_dir)}:{sid}",
                                    f"非法 relation: {rel}",
                                    f"使用 {valid_relations} 之一"))

    return max(0, score), issues


def _check_prompt_quality(out_dir: Path) -> tuple[int, list[Issue]]:
    issues: list[Issue] = []
    score = 10

    for ctx_file in sorted(out_dir.rglob("gen_context.json")):
        try:
            data = json.loads(ctx_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sb = data.get("storyboard") or {}
        shots = sb.get("shots") or []
        if not isinstance(shots, list):
            continue

        for s in shots:
            if not isinstance(s, dict):
                continue
            sid = str(s.get("shot_id", "?"))
            vp_zh = str(s.get("video_prompt") or "").strip()
            vp_en = str(s.get("video_prompt_en") or "").strip()

            if not vp_zh and not vp_en:
                issues.append(Issue("⚠️建议", "prompt_quality",
                                    f"{ctx_file.relative_to(out_dir)}:{sid}",
                                    "video_prompt 和 video_prompt_en 均为空",
                                    "填写至少一种语言的提示词"))
                score = max(0, score - 1)
                continue

            if vp_zh and len(vp_zh) > 1500:
                issues.append(Issue("⚠️建议", "prompt_quality",
                                    f"{ctx_file.relative_to(out_dir)}:{sid}",
                                    f"video_prompt 过长 ({len(vp_zh)} 字)",
                                    "精简到 1500 字以内"))
                score = max(0, score - 1)
            if vp_en and len(vp_en) > 2000:
                issues.append(Issue("⚠️建议", "prompt_quality",
                                    f"{ctx_file.relative_to(out_dir)}:{sid}",
                                    f"video_prompt_en 过长 ({len(vp_en)} chars)",
                                    "精简到 2000 字符以内"))
                score = max(0, score - 1)

    return max(0, score), issues


def _check_char_consistency(manuscript_dir: Path) -> tuple[int, list[Issue]]:
    issues: list[Issue] = []
    score = 10

    bible = manuscript_dir / "bible" / "角色.md"
    if not bible.is_file():
        issues.append(Issue("ℹ️微调", "char_consistency", "bible/角色.md",
                            "角色圣经未创建", "运行 /nuomi:new 后完成角色设定"))
        score = max(0, score - 2)
        return score, issues

    from names import normalize_character_name
    text = bible.read_text(encoding="utf-8")
    names_in_bible = set()
    for m in re.finditer(r"^##\s+(.+)$", text, re.MULTILINE):
        raw = m.group(1).strip()
        norm = normalize_character_name(raw)
        if norm:
            names_in_bible.add(norm)

    if not names_in_bible:
        issues.append(Issue("⚠️建议", "char_consistency", "bible/角色.md",
                            "未检测到角色定义", "以 ## 角色名 格式定义角色"))

    return max(0, score), issues


def _check_satisfaction_rhythm(manuscript_dir: Path,
                                md_files: list[Path]) -> tuple[int, list[Issue]]:
    """Check hook density and satisfaction distribution.

    Absorbs short-drama rhythm-curve + satisfaction-matrix patterns.
    """
    issues: list[Issue] = []
    score = 10

    ep_files = [f for f in md_files
                if f.name.startswith("E") and f.name.endswith(".md")]
    if not ep_files:
        issues.append(Issue("ℹ️微调", "satisfaction", "manuscript/",
                            "未找到 episode 文件",
                            "至少完成 E1.md 的剧本和分镜表"))
        return 5, issues

    hooks_found = 0
    for epf in ep_files:
        text = epf.read_text(encoding="utf-8")
        hooks_found += (text.count("反转") + text.count("悬念") +
                        text.count("钩子") + text.count("△ 特写") +
                        text.count("△ 近景"))

    expected_min = len(ep_files)
    if hooks_found < expected_min:
        issues.append(Issue("⚠️建议", "satisfaction", "manuscript/",
                            f"钩子密度偏低（检测到 {hooks_found}，建议 >= {expected_min}）",
                            "每集确保至少 1 个钩子/反转/悬念点"))
        score = max(0, score - 3)

    return max(0, score), issues
