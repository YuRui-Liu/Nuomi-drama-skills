# .claude/skills/nuomi-drama-skills/providers/base.py
from __future__ import annotations
from abc import ABC, abstractmethod


class ImageProvider(ABC):
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg

    @abstractmethod
    def generate_image(self, prompt: str, *, size: dict | str | None = None,
                       refs: list[str] | None = None) -> bytes:
        """返回图片字节（PNG/JPEG）。size 为 dict 时形如 {"aspectRatio":"9:16"}，str 时形如 "9:16"。"""


class VideoProvider(ABC):
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg

    @abstractmethod
    def generate_video(self, prompt: str, first_frame_path: str,
                       duration: float) -> bytes:
        """返回视频字节（MP4）。"""


class VideoGroupProvider(VideoProvider):
    """支持多段视频分组生成的 provider。"""

    @abstractmethod
    def generate_video_group(self, global_prompt: str, segments: list[dict],
                             motion_segments: list[str] | None = None) -> bytes:
        """生成多段视频，返回 MP4 字节。"""
        raise NotImplementedError


class DubProvider(ABC):
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg

    @abstractmethod
    def generate_dub(self, text: str, speaker: str, emotion: str,
                     voice_style: str = "") -> bytes:
        """返回音频字节（WAV）。"""

    def design_voice(self, name: str, style: str, language: str,
                     out_dir: str) -> str:
        """生成音色参考音频，写入 out_dir/{name}.wav，返回本地路径。"""
        raise NotImplementedError("provider 不支持音色设计")

    def clone_voice(self, text: str, speaker_ref: str, emotion: str) -> bytes:
        """用参考音频克隆配音，返回 WAV bytes。"""
        raise NotImplementedError("provider 不支持声音克隆")


class GridUpscaleProvider(ABC):
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg

    @abstractmethod
    def upscale_grid(self, grid_path: str, rows: int, cols: int,
                     out_dir: str) -> list[str]:
        """放大并拆分宫格图，返回 N 张单镜图路径列表。"""
