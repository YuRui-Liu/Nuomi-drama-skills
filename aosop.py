"""AOSOP state model — Accepted / Observed / Specific Overrides / Planned.

AOSOP is a VIEW layer over existing state sources. READS from:
- writing_state.json (phase, completed_episodes, gates_passed)
- gen_context.json (storyboard shots definition)
- filesystem (shot product existence — jpg/mp4/wav)
- generate_log.json (error history)

WRITES only:
- aosop_state.json: accepted markers + override settings

Inspired by seedance-2.0's scene/shot state tracking.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ShotAOSOPState(str, Enum):
    PLANNED = "planned"        # In storyboard, not yet generated
    GENERATING = "generating"  # Generation in progress (no product yet)
    OBSERVED = "observed"      # Product exists on disk
    ACCEPTED = "accepted"      # Human-approved, locked against regeneration
    FAILED = "failed"          # Generation failed (in GenerateLog)
    OVERRIDDEN = "overridden"  # Has specific override applied


@dataclass
class ShotState:
    shot_id: str
    episode: int
    aosop_state: ShotAOSOPState
    product_exists: bool = False
    error_count: int = 0
    retake_remaining: int = 5
    overrides: dict = field(default_factory=dict)
    accepted_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "shot_id": self.shot_id, "episode": self.episode,
            "state": self.aosop_state.value,
            "product_exists": self.product_exists,
            "error_count": self.error_count,
            "retake_remaining": self.retake_remaining,
            "overrides": self.overrides,
            "accepted_at": self.accepted_at,
        }


@dataclass
class EpisodeAOSOP:
    ep: int
    total_shots: int = 0
    planned: int = 0
    generating: int = 0
    observed: int = 0
    accepted: int = 0
    failed: int = 0
    overridden: int = 0
    shots: list[ShotState] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ep": self.ep, "total_shots": self.total_shots,
            "planned": self.planned, "observed": self.observed,
            "accepted": self.accepted, "failed": self.failed,
            "overridden": self.overridden,
            "shots": [s.to_dict() for s in self.shots],
        }


@dataclass
class AOSOPState:
    project_phase: str
    episodes: list[EpisodeAOSOP] = field(default_factory=list)
    global_overrides: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "project_phase": self.project_phase,
            "episodes": [e.to_dict() for e in self.episodes],
            "global_overrides": self.global_overrides,
        }

    @property
    def acceptance_rate(self) -> float:
        total = sum(e.total_shots for e in self.episodes)
        accepted = sum(e.accepted for e in self.episodes)
        return accepted / total if total > 0 else 0.0

    @property
    def total_shots(self) -> int:
        return sum(e.total_shots for e in self.episodes)


def load_aosop(out_dir: str) -> AOSOPState:
    """Build AOSOP state from existing data sources.

    1. Read writing_state.json for project phase
    2. Read gen_context.json for each episode's shot definitions
    3. Check filesystem for product existence
    4. Read generate_log.json for error counts
    5. Read aosop_state.json for accepted/override markers (if exists)
    """
    out = Path(out_dir)

    # 1. Phase from writing_state
    phase = "unknown"
    ws_path = out / "writing_state.json"
    if ws_path.is_file():
        try:
            ws = json.loads(ws_path.read_text(encoding="utf-8"))
            phase = ws.get("phase", "unknown")
        except (OSError, json.JSONDecodeError):
            pass

    # 5. Load existing AOSOP markers
    aosop_path = out / "aosop_state.json"
    accepted_shots: dict[str, dict] = {}
    override_shots: dict[str, dict] = {}
    if aosop_path.is_file():
        try:
            existing = json.loads(aosop_path.read_text(encoding="utf-8"))
            for shot in existing.get("shots", []):
                sid = shot.get("shot_id", "")
                if shot.get("state") == "accepted":
                    accepted_shots[sid] = shot
                if shot.get("overrides"):
                    override_shots[sid] = shot
        except (OSError, json.JSONDecodeError):
            pass

    # 2-4. Scan episodes
    episodes: list[EpisodeAOSOP] = []
    log_errors: dict[str, dict[int, int]] = {}  # shot_id -> {ep: count}

    # Read generate_log for error counts
    log_path = out / "generate_log.json"
    if log_path.is_file():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            sid = entry.get("shot_id", "")
            ep = entry.get("ep", 0)
            if sid:
                log_errors.setdefault(sid, {}).setdefault(ep, 0)
                log_errors[sid][ep] += 1

    ep_dirs = sorted(out.glob("E*"))
    for ed in ep_dirs:
        try:
            ep_num = int(ed.name.lstrip("E"))
        except ValueError:
            continue

        ctx_path = ed / "gen_context.json"
        if not ctx_path.is_file():
            continue
        try:
            ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        sb = ctx.get("storyboard") or {}
        shots = sb.get("shots") or []
        shots_dir = ed / "shots_assets"

        shot_states: list[ShotState] = []
        counts = {"planned": 0, "observed": 0, "accepted": 0,
                   "failed": 0, "overridden": 0}

        for s in shots:
            if not isinstance(s, dict):
                continue
            sid = str(s.get("shot_id", ""))
            if not sid:
                continue
            counts["planned"] += 1

            # Determine state
            has_product = (shots_dir / f"{sid}.jpg").exists() or \
                          (shots_dir / f"{sid}.mp4").exists()
            err_count = log_errors.get(sid, {}).get(ep_num, 0)

            if sid in accepted_shots:
                aosop_st = ShotAOSOPState.ACCEPTED
                counts["accepted"] += 1
            elif sid in override_shots:
                aosop_st = ShotAOSOPState.OVERRIDDEN
                counts["overridden"] += 1
            elif has_product:
                aosop_st = ShotAOSOPState.OBSERVED
                counts["observed"] += 1
            elif err_count > 0:
                aosop_st = ShotAOSOPState.FAILED
                counts["failed"] += 1
            else:
                aosop_st = ShotAOSOPState.PLANNED

            overrides = override_shots.get(sid, {}).get("overrides", {})
            accepted_at = accepted_shots.get(sid, {}).get("accepted_at")

            shot_states.append(ShotState(
                shot_id=sid, episode=ep_num, aosop_state=aosop_st,
                product_exists=has_product, error_count=err_count,
                retake_remaining=max(0, 5 - err_count),
                overrides=overrides, accepted_at=accepted_at,
            ))

        total = counts["planned"]
        episodes.append(EpisodeAOSOP(
            ep=ep_num, total_shots=total,
            planned=counts["planned"], observed=counts["observed"],
            accepted=counts["accepted"], failed=counts["failed"],
            overridden=counts["overridden"], shots=shot_states,
        ))

    return AOSOPState(project_phase=phase, episodes=episodes)
