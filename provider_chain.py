"""Provider chain — role-based fallback for image generation.

- Anchors (characters/scenes/props): primary → fallback silently
- Shots (storyboard frames): primary → fallback with warning log marker
- Video / Dub: single provider only (RunningHub), no fallback

Usage:
    from provider_chain import ProviderChain, health_check

    chain = ProviderChain(cfg)
    img = chain.generate_anchor("a warrior in armor")
    img = chain.generate_shot("close-up of a hand reaching for a door")
    vid = chain.generate_video("camera pans left", "s1.jpg", 4.0)
    aud = chain.generate_dub("你好", "沈云晚", "悲伤", "温柔女声")
"""
from __future__ import annotations

from typing import Any


class ProviderChain:
    def __init__(self, cfg: dict[str, Any]) -> None:
        self._cfg = cfg
        self._anchor_primary = self._make_image_provider("anchor", "primary")
        self._anchor_fallback = self._make_image_provider("anchor", "fallback")
        self._shot_primary = self._make_image_provider("shot", "primary")
        self._shot_fallback = self._make_image_provider("shot", "fallback")
        self._video_provider = self._make_video_provider()
        self._dub_provider = self._make_dub_provider()
        self._fallback_log: list[dict] = []

    # ── 工厂方法 ──────────────────────────────────────────────────
    def _make_image_provider(self, role: str, tier: str):
        from providers import load_config as _lc
        c = _lc()
        env_img = c.get("image_provider", "grsai")
        if role == "anchor":
            name = c.get("image_provider_anchor", env_img)
            fallback_name = c.get("image_provider_anchor_fallback",
                                  c.get("image_provider_shot_fallback", "gemini"))
        else:
            name = c.get("image_provider_shot", env_img)
            fallback_name = c.get("image_provider_shot_fallback",
                                  c.get("image_provider_anchor_fallback", "gemini"))
        chosen = name if tier == "primary" else fallback_name
        if not chosen:
            return None
        # 如果 fallback 和 primary 同名，说明未单独配置 fallback，不创建
        if tier == "fallback" and chosen == name:
            return None

        if chosen == "grsai":
            from providers.grsai import GrsaiProvider
            return GrsaiProvider(c.get("grsai", {}))
        if chosen == "gemini":
            from providers.gemini import GeminiImageProvider
            return GeminiImageProvider(c.get("gemini", {}))
        if chosen == "comfyui":
            from providers.comfyui import ComfyUIProvider
            return ComfyUIProvider(c.get("comfyui", {}))
        if chosen == "runninghub":
            from providers.runninghub import RunningHubProvider
            return RunningHubProvider(c.get("runninghub", {}))
        return None

    def _make_video_provider(self):
        from providers import get_video_provider
        return get_video_provider()

    def _make_dub_provider(self):
        from providers import get_dub_provider
        return get_dub_provider()

    # ── Fallback 日志 ─────────────────────────────────────────────
    def get_fallback_events(self) -> list[dict]:
        return list(self._fallback_log)

    # ── 锚图生成（可降级） ──────────────────────────────────────────
    def generate_anchor(self, prompt: str) -> bytes:
        if self._anchor_primary is not None:
            try:
                return self._anchor_primary.generate_image(prompt)
            except Exception as e:
                if self._anchor_fallback is not None:
                    self._fallback_log.append({
                        "role": "anchor", "action": "fallback",
                        "primary_error": str(e)[:200],
                    })
                    return self._anchor_fallback.generate_image(prompt)
                raise
        if self._anchor_fallback is not None:
            self._fallback_log.append({
                "role": "anchor", "action": "direct_fallback",
            })
            return self._anchor_fallback.generate_image(prompt)
        raise RuntimeError("锚图生成: 无可用 provider（请配置 IMAGE_PROVIDER_ANCHOR）")

    # ── 分镜首帧生成（降级打 ⚠️ 标记） ──────────────────────────────
    def generate_shot(self, prompt: str, size=None) -> bytes:
        if self._shot_primary is not None:
            try:
                return self._shot_primary.generate_image(prompt, size=size)
            except Exception as e:
                if self._shot_fallback is not None:
                    self._fallback_log.append({
                        "role": "shot", "action": "fallback",
                        "warning": "分镜首帧降级为 fallback provider，风格可能不一致",
                        "primary_error": str(e)[:200],
                    })
                    return self._shot_fallback.generate_image(prompt, size=size)
                raise
        if self._shot_fallback is not None:
            self._fallback_log.append({
                "role": "shot", "action": "direct_fallback",
                "warning": "分镜首帧使用 fallback provider（无主 provider 配置）",
            })
            return self._shot_fallback.generate_image(prompt, size=size)
        raise RuntimeError("分镜生成: 无可用 provider（请配置 IMAGE_PROVIDER_SHOT）")

    # ── 视频生成（无降级） ────────────────────────────────────────
    def generate_video(self, prompt: str, first_frame_path: str,
                       duration: float) -> bytes:
        if self._video_provider is None:
            raise RuntimeError("视频生成: 无可用 provider（仅 RunningHub 支持）")
        return self._video_provider.generate_video(prompt, first_frame_path, duration)

    def generate_video_group(self, global_prompt: str, segments: list[dict],
                             motion_segments: list[str] | None = None) -> bytes:
        if self._video_provider is None:
            raise RuntimeError("视频分组生成: 无可用 provider")
        return self._video_provider.generate_video_group(
            global_prompt, segments, motion_segments)

    # ── 配音生成（无降级） ────────────────────────────────────────
    def generate_dub(self, text: str, speaker: str, emotion: str,
                     voice_style: str = "") -> bytes:
        if self._dub_provider is None:
            raise RuntimeError("配音: 无可用 provider（仅 RunningHub 支持）")
        return self._dub_provider.generate_dub(text, speaker, emotion, voice_style)

    def design_voice(self, name: str, style: str, language: str,
                     out_dir: str) -> str:
        if self._dub_provider is None:
            raise RuntimeError("音色设计: 无可用 provider")
        return self._dub_provider.design_voice(name, style, language, out_dir)

    def clone_voice(self, text: str, speaker_ref: str, emotion: str) -> bytes:
        if self._dub_provider is None:
            raise RuntimeError("声音克隆: 无可用 provider")
        return self._dub_provider.clone_voice(text, speaker_ref, emotion)


def health_check(cfg: dict) -> dict[str, bool]:
    """预检各 provider 配置完整性（不做网络 ping，避免超时阻塞）。
    返回 {provider_name: is_healthy}。
    """
    results: dict[str, bool] = {}
    img = cfg.get("image_provider", "")
    for name in ("grsai", "gemini", "comfyui", "runninghub"):
        section = cfg.get(name, {})
        if name == img or name in ("grsai", "gemini", "comfyui", "runninghub"):
            results[name] = bool(section.get("api_key") or section.get("base_url"))
    results["runninghub_video"] = bool(
        cfg.get("runninghub", {}).get("api_key")
        and cfg.get("runninghub", {}).get("video_workflow_id"))
    results["runninghub_dub"] = bool(
        cfg.get("runninghub", {}).get("api_key")
        and cfg.get("runninghub", {}).get("dub_workflow_id"))
    return results
