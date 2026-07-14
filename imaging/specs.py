from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class AspectRatio:
    width: int
    height: int

    @property
    def value(self) -> float:
        return self.width / max(1, self.height)

    def __str__(self) -> str:
        return f"{self.width}:{self.height}"
