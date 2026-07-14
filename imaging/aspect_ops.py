"""去边 + 画幅裁切工具 — vendor 自平台 shot_agent/vendor/imaging/aspect_ops.py。"""
from __future__ import annotations
import numpy as np
from PIL import Image
from imaging.specs import AspectRatio


def trim_white_edges(img: Image.Image, t_bright: int = 234,
                     max_std: float = 8.0, max_iter: int = 5) -> Image.Image:
    for _ in range(max_iter):
        arr = np.array(img.convert("RGB")).astype("float32")
        h, w = arr.shape[:2]
        if h == 0 or w == 0:
            return img
        row_mean = arr.mean(axis=(1, 2))
        col_mean = arr.mean(axis=(0, 2))
        row_std = arr.reshape(h, -1).std(axis=1)
        col_std = arr.transpose(1, 0, 2).reshape(w, -1).std(axis=1)
        content_rows = np.where(~((row_mean >= t_bright) & (row_std <= max_std)))[0]
        content_cols = np.where(~((col_mean >= t_bright) & (col_std <= max_std)))[0]
        if len(content_rows) == 0 or len(content_cols) == 0:
            return img
        y0, y1 = int(content_rows[0]), int(content_rows[-1]) + 1
        x0, x1 = int(content_cols[0]), int(content_cols[-1]) + 1
        if y0 == 0 and y1 == h and x0 == 0 and x1 == w:
            break
        img = img.crop((x0, y0, x1, y1))
    return img


def trim_seam_edges(img: Image.Image, max_frac: float = 0.04,
                    std_max: float = 12.0, bright_margin: float = 15.0,
                    bright_floor: float = 150.0) -> Image.Image:
    arr = np.array(img.convert("RGB")).astype("float32")
    h, w = arr.shape[:2]
    if h < 8 or w < 8:
        return img
    bright = arr.mean(axis=2)
    base = float(np.median(bright[h // 4:h - h // 4, w // 4:w - w // 4]))
    thr = max(base + bright_margin, bright_floor)
    row_mean = bright.mean(axis=1)
    col_mean = bright.mean(axis=0)
    row_std = arr.reshape(h, -1).std(axis=1)
    col_std = arr.transpose(1, 0, 2).reshape(w, -1).std(axis=1)

    def _seam(means, stds, n) -> int:
        cap = max(0, int(n * max_frac))
        c = 0
        while c < cap and means[c] >= thr and stds[c] <= std_max:
            c += 1
        return c

    top = _seam(row_mean, row_std, h)
    bottom = _seam(row_mean[::-1], row_std[::-1], h)
    left = _seam(col_mean, col_std, w)
    right = _seam(col_mean[::-1], col_std[::-1], w)
    if top + bottom >= h or left + right >= w:
        return img
    if top or bottom or left or right:
        return img.crop((left, top, w - right, h - bottom))
    return img


def center_crop_to_aspect(img: Image.Image, aspect: AspectRatio) -> Image.Image:
    target = aspect.value
    cur = img.width / img.height
    if cur > target:
        new_w = int(img.height * target)
        x0 = (img.width - new_w) // 2
        return img.crop((x0, 0, x0 + new_w, img.height))
    if cur < target:
        new_h = int(img.width / target)
        y0 = (img.height - new_h) // 2
        return img.crop((0, y0, img.width, y0 + new_h))
    return img
