# .claude/skills/nuomi-drama-skills/providers/__init__.py
from __future__ import annotations
import os


def load_config() -> dict:
    """从环境变量读所有生成配置，返回嵌套 dict。"""
    return {
        "image_provider": os.environ.get("IMAGE_PROVIDER", "grsai"),
        "gemini": {
            "api_key": os.environ.get("GEMINI_API_KEY", ""),
            "model": os.environ.get("GEMINI_MODEL", "imagen-4.0-generate-001"),
        },
        "grsai": {
            "api_key": os.environ.get("GRSAI_API_KEY", ""),
            "base_url": os.environ.get("GRSAI_BASE_URL", "https://grsai.dakka.com.cn"),
            "model": os.environ.get("GRSAI_IMAGE_MODEL", "gpt-image-2-vip"),
        },
        "comfyui": {
            "base_url": os.environ.get("COMFYUI_BASE_URL", "http://localhost:8188"),
            "workflow_id": os.environ.get("COMFYUI_WORKFLOW_ID", ""),
        },
        "runninghub": {
            "api_key": os.environ.get("RUNNINGHUB_API_KEY", ""),
            "base_url": os.environ.get("RUNNINGHUB_BASE_URL", "https://www.runninghub.cn"),
            "image_workflow_id": os.environ.get("RUNNINGHUB_IMAGE_WORKFLOW_ID", ""),
            "video_workflow_id": os.environ.get("RUNNINGHUB_VIDEO_WORKFLOW_ID", ""),
            "dub_workflow_id": os.environ.get("RUNNINGHUB_DUB_WORKFLOW_ID", ""),
            "upscale_workflow_id": os.environ.get("RUNNINGHUB_UPSCALE_WORKFLOW_ID", ""),
            "voice_design_workflow_id": os.environ.get("RUNNINGHUB_VOICE_DESIGN_WORKFLOW_ID", ""),
            "dub_clone_workflow_id": os.environ.get("RUNNINGHUB_DUB_CLONE_WORKFLOW_ID", ""),
            "max_parallel": int(os.environ.get("RUNNINGHUB_MAX_PARALLEL", "3")),
        },
        "grid": {
            "target_aspect": os.environ.get("GRID_TARGET_ASPECT", "9:16"),
            "upscale_threshold": int(os.environ.get("GRID_UPSCALE_SHOTS_THRESHOLD", "2")),
            "canvas_mode": os.environ.get("GRID_CANVAS_MODE", "economy"),
            "image_model": os.environ.get("GRID_IMAGE_MODEL", "gpt-image-2"),
        },
        "image_width": int(os.environ.get("IMAGE_WIDTH", "768")),
        "image_height": int(os.environ.get("IMAGE_HEIGHT", "1344")),
        "poll_interval_s": float(os.environ.get("POLL_INTERVAL_S", "5")),
        "poll_timeout_s": float(os.environ.get("POLL_TIMEOUT_S", "300")),
    }


def get_image_provider():
    cfg = load_config()
    name = cfg["image_provider"]
    if name == "gemini":
        from .gemini import GeminiImageProvider
        return GeminiImageProvider(cfg["gemini"])
    if name == "grsai":
        from .grsai import GrsaiProvider
        return GrsaiProvider(cfg["grsai"])
    if name == "comfyui":
        from .comfyui import ComfyUIProvider
        return ComfyUIProvider(cfg["comfyui"])
    if name == "runninghub":
        from .runninghub import RunningHubProvider
        return RunningHubProvider(cfg["runninghub"])
    raise ValueError(f"未知 IMAGE_PROVIDER: {name!r}（gemini|grsai|comfyui|runninghub）")


# Video, dub, and upscale only supported by RunningHub per spec
def get_video_provider():
    from .runninghub import RunningHubProvider
    return RunningHubProvider(load_config()["runninghub"])


# Video, dub, and upscale only supported by RunningHub per spec
def get_dub_provider():
    from .runninghub import RunningHubProvider
    return RunningHubProvider(load_config()["runninghub"])


# Video, dub, and upscale only supported by RunningHub per spec
def get_upscale_provider():
    from .runninghub import RunningHubProvider
    return RunningHubProvider(load_config()["runninghub"])
