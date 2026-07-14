"""宫格画布尺寸决策 — 从平台 grid_canvas.py + border_detector.py 精简 vendor。
仅支持 economy 模式（基础模型预设比例）。
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Tuple

_ASPECT_PRESETS = (
    "1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16", "21:9", "1:3", "3:1",
)
_VIP_LONG_SHORT_RATIO = 3.0


@dataclass(frozen=True)
class GridCanvas:
    rows: int
    cols: int
    cell_aspect: Tuple[int, int]
    provider_args: dict


def _aspect_value(s: str) -> float:
    a, b = s.split(":")
    return float(a) / float(b)


def grid_layout(n: int, target_aspect: str | None = None) -> tuple[int, int]:
    """N 张分镜 → (rows, cols)。画幅自适应：竖版偏列多，横版偏行多。"""
    n = max(1, int(n))
    if target_aspect is None:
        cols = math.ceil(math.sqrt(n))
        return math.ceil(n / cols), cols
    a = _aspect_value(target_aspect)
    best = None
    for cols in range(1, n + 1):
        rows = math.ceil(n / cols)
        waste = rows * cols - n
        overall = (cols / rows) * a
        dev = abs(math.log(overall)) if overall > 0 else float("inf")
        extreme = 1 if overall > 2.0 or overall < 0.5 else 0
        key = (extreme, waste, dev)
        if best is None or key < best[:3]:
            best = (extreme, waste, dev, rows, cols)
    return best[3], best[4]


def _pick_economy_preset(canvas_aspect: float) -> str:
    best_loss, best_preset = float("inf"), "1:1"
    for p in _ASPECT_PRESETS:
        v = _aspect_value(p)
        loss = 1 - min(canvas_aspect, v) / max(canvas_aspect, v)
        if loss < best_loss:
            best_loss, best_preset = loss, p
    return best_preset


def compute_grid_canvas(n: int, target_aspect: str, mode: str = "economy",
                        model: str = "gpt-image-2") -> GridCanvas:
    """计算宫格布局 + provider 参数。出/拆共用同一函数保证行列一致。"""
    n = max(1, int(n))
    rows, cols = grid_layout(n, target_aspect)
    asp = _aspect_value(target_aspect)
    # 加行降压：画布长:短 > 3:1 时 rows+1（允许末尾空格）
    for _ in range(2):
        canvas_w, canvas_h = cols * asp, float(rows)
        long_short = max(canvas_w, canvas_h) / max(min(canvas_w, canvas_h), 1e-9)
        if long_short <= _VIP_LONG_SHORT_RATIO + 1e-9:
            break
        rows += 1
    canvas_aspect = (cols * asp) / rows
    best = _pick_economy_preset(canvas_aspect)
    args: dict = {"aspectRatio": best, "imageSize": "4K"}
    bv = _aspect_value(best)
    base = 1000.0
    cw = (base * bv / cols) if bv >= 1.0 else (base / cols)
    ch = (base / rows) if bv >= 1.0 else ((base / bv) / rows)
    return GridCanvas(rows=rows, cols=cols, cell_aspect=(int(cw), int(ch)),
                      provider_args=args)
