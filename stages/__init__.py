# .claude/skills/nuomi-drama-skills/stages/__init__.py
from __future__ import annotations
import json, time
from pathlib import Path


class GenerateLog:
    def __init__(self, out_dir: str):
        self.path = Path(out_dir) / "generate_log.json"

    def append(self, stage: str, ep: int | None, shot_id: str, error: str) -> None:
        entry = {"ts": int(time.time()), "stage": stage,
                 "ep": ep, "shot_id": shot_id, "error": error}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
