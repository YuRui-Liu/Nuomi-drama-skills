"""Content compliance checker.

Absorbs short-drama three-tier risk model (red_lines / gray_zones / positive)
and P0-P4 priority framework.

Uses quality/profiles/cn.json as the compliance rule source.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Finding:
    """A single compliance finding."""
    priority: str        # P0 / P1 / P2 / P3
    rule_id: str         # e.g. "RL-001", "GZ-002"
    location: str        # "E1.md:15"
    description: str
    suggestion: str

    def to_dict(self) -> dict:
        return {
            "priority": self.priority,
            "rule_id": self.rule_id,
            "location": self.location,
            "description": self.description,
            "suggestion": self.suggestion,
        }


@dataclass
class ComplianceReport:
    """Complete compliance report."""
    red_line_findings: list[Finding] = field(default_factory=list)
    gray_zone_findings: list[Finding] = field(default_factory=list)
    positive_guidance_pass: list[bool] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "red_lines_hit": len(self.red_line_findings),
            "gray_zones_hit": len(self.gray_zone_findings),
            "positive_pass_count": sum(1 for p in self.positive_guidance_pass if p),
            "red_line_findings": [f.to_dict() for f in self.red_line_findings],
            "gray_zone_findings": [f.to_dict() for f in self.gray_zone_findings],
            "positive_checks": [
                {"id": f"PG-{i+1:03d}", "passed": p}
                for i, p in enumerate(self.positive_guidance_pass)
            ],
        }

    def to_markdown(self) -> str:
        lines = [
            f"# 合规检查报告",
            f"",
            f"**红线**: {len(self.red_line_findings)} 条 | "
            f"**灰区**: {len(self.gray_zone_findings)} 条 | "
            f"**正向**: {sum(1 for p in self.positive_guidance_pass if p)}"
            f"/{len(self.positive_guidance_pass)}",
            f"",
        ]
        if self.red_line_findings:
            lines.append("## 🔴 红线（P0 — 立即删除）")
            for f in self.red_line_findings:
                lines.append(f"- **{f.location}**: {f.description}")
                lines.append(f"  → {f.suggestion}")
            lines.append("")
        if self.gray_zone_findings:
            lines.append("## 🟡 灰区")
            for f in self.gray_zone_findings:
                lines.append(f"- [{f.priority}] **{f.location}**: {f.description}")
                lines.append(f"  → {f.suggestion}")
            lines.append("")
        if not self.red_line_findings and not self.gray_zone_findings:
            lines.append("✅ 未检测到红线或灰区问题")
        return "\n".join(lines)


def run_compliance(manuscript_dir: Path, profile_path: Path) -> ComplianceReport:
    """Run compliance check against the given profile."""
    profile = json.loads(profile_path.read_text(encoding="utf-8"))

    red_lines: list[Finding] = []
    gray_zones: list[Finding] = []
    positive_pass: list[bool] = []

    md_files = sorted(manuscript_dir.rglob("*.md"))
    file_map: dict[str, str] = {}
    combined_text = ""
    for f in md_files:
        text = f.read_text(encoding="utf-8")
        rel = str(f.relative_to(manuscript_dir))
        file_map[rel] = text
        combined_text += text + "\n"

    # ── Red line scan ──────────────────────────────────────────
    for rule in profile.get("red_lines", []):
        for kw in rule.get("keywords", []):
            for fname, text in file_map.items():
                for m in re.finditer(re.escape(kw), text):
                    line_no = text[:m.start()].count("\n") + 1
                    red_lines.append(Finding(
                        "P0", rule["id"], f"{fname}:{line_no}",
                        f"{rule['desc']}: 检测到「{kw}」",
                        rule.get("action", "删除相关内容"),
                    ))

    # ── Gray zone scan ─────────────────────────────────────────
    for rule in profile.get("gray_zones", []):
        for kw in rule.get("keywords", []):
            for fname, text in file_map.items():
                for m in re.finditer(re.escape(kw), text):
                    line_no = text[:m.start()].count("\n") + 1
                    gray_zones.append(Finding(
                        rule.get("priority", "P2"), rule["id"],
                        f"{fname}:{line_no}",
                        f"{rule['desc']}: 检测到「{kw}」",
                        rule.get("handling", "建议修改"),
                    ))

    # ── Genre pitfall scan ─────────────────────────────────────
    genre = _detect_genre(combined_text)
    pitfalls = profile.get("genre_pitfalls", {}).get(genre, {})
    for phrase in pitfalls.get("dont", []):
        for fname, text in file_map.items():
            if phrase in text:
                for m in re.finditer(re.escape(phrase), text):
                    line_no = text[:m.start()].count("\n") + 1
                    do_items = pitfalls.get("do", ["避免此类描写"])
                    gray_zones.append(Finding(
                        "P1", f"GENRE-{genre}", f"{fname}:{line_no}",
                        f"题材「{genre}」踩坑: {phrase}",
                        f"建议: {do_items[0]}",
                    ))

    # ── Positive guidance check ─────────────────────────────────
    positive_kw = {
        "结局正向": ["团圆", "和解", "成长", "释然"],
        "奋斗精神": ["努力", "坚持", "奋斗", "拼搏"],
        "家庭观念": ["家", "团圆", "亲情", "理解"],
    }
    for rule in profile.get("positive_guidance", []):
        check_name = rule.get("check", "")
        matched = any(
            any(kw in combined_text for kw in kw_set)
            for kw_set in positive_kw.values()
        )
        positive_pass.append(matched)

    return ComplianceReport(
        red_line_findings=red_lines,
        gray_zone_findings=gray_zones,
        positive_guidance_pass=positive_pass,
    )


def _detect_genre(text: str) -> str:
    """Detect the primary genre from manuscript content."""
    genre_keywords = {
        "战神归来": ["战神", "兵王", "退伍"],
        "霸道总裁": ["霸道总裁", "总裁", "CEO", "豪门"],
        "甜宠": ["甜宠", "先婚后爱", "独宠"],
        "重生穿越": ["重生", "穿越", "回到过去"],
        "古装宫廷": ["宫斗", "皇后", "妃", "王府", "太子"],
        "悬疑探案": ["破案", "侦探", "刑警", "凶手"],
        "家庭伦理": ["婆媳", "家庭", "亲子"],
    }
    scores = {g: sum(text.count(kw) for kw in kws)
              for g, kws in genre_keywords.items()}
    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    return best if scores[best] > 0 else "未识别"
