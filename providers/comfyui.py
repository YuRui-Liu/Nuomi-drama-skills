"""ComfyUI 本地 API 图片/视频 provider。"""
from __future__ import annotations
import json, time as _time, uuid, base64
from pathlib import Path
from .base import ImageProvider, VideoGroupProvider
import httpx

_POLL_INTERVAL = 2.0
_POLL_TIMEOUT = 300.0
_DEFAULT_FRAME_RATE = 24


def _sleep(s: float) -> None:
    _time.sleep(s)


class ComfyUIProvider(VideoGroupProvider, ImageProvider):
    def __init__(self, cfg: dict) -> None:
        # Both parent __init__s set self.cfg = cfg; VideoGroupProvider is first in MRO
        super().__init__(cfg)
        self.base_url = (cfg.get("base_url") or "http://localhost:8188").rstrip("/")
        self.workflow_json = cfg.get("workflow_json", "")

    # ------------------------------------------------------------------
    # Image generation (unchanged)
    # ------------------------------------------------------------------
    def generate_image(self, prompt: str, *, size: dict | str | None = None,
                       refs: list[str] | None = None) -> bytes:
        if not self.workflow_json:
            raise ValueError("ComfyUIProvider: workflow_json 未配置")
        wf = json.loads(self.workflow_json)
        # 注入 positive prompt：找第一个 CLIPTextEncode 节点替换 text
        for node in wf.values():
            if node.get("class_type") == "CLIPTextEncode":
                node["inputs"]["text"] = prompt
                break
        client_id = str(uuid.uuid4())
        resp = httpx.request("POST", f"{self.base_url}/prompt",
                             json={"prompt": wf, "client_id": client_id},
                             timeout=30, trust_env=False)
        if resp.status_code >= 400:
            raise RuntimeError(f"ComfyUI /prompt HTTP {resp.status_code}: {resp.text[:300]}")
        prompt_id = resp.json().get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"ComfyUI 无 prompt_id: {resp.text[:200]}")
        return self._wait_and_fetch(prompt_id)

    # ------------------------------------------------------------------
    # Video generation – backward-compatible single-shot wrapper
    # ------------------------------------------------------------------
    def generate_video(self, prompt: str, first_frame_path: str,
                       duration: float) -> bytes:
        """单镜视频：将参数转为单段 segment 列表后调用 generate_video_group。"""
        frame_rate = _DEFAULT_FRAME_RATE
        length_frames = max(1, int(round(duration * frame_rate)))
        segments = [{
            "prompt": prompt,
            "image_path": first_frame_path,
            "length": length_frames,
            "type": "image",
        }]
        return self.generate_video_group(prompt, segments)

    # ------------------------------------------------------------------
    # Multi-segment video group generation
    # ------------------------------------------------------------------
    def generate_video_group(self, global_prompt: str, segments: list[dict],
                             motion_segments: list[str] | None = None) -> bytes:
        """多段视频分组生成。

        segments: 每个 dict 包含 prompt, image_path, length（帧数）, type（可选，默认 "image"）。
        """
        if not self.workflow_json:
            raise ValueError("ComfyUIProvider: workflow_json 未配置")

        wf = json.loads(self.workflow_json)

        # 查找 LTXDirector 节点
        director_node = None
        for node in wf.values():
            if node.get("class_type") == "LTXDirector":
                director_node = node
                break

        if director_node is None:
            raise RuntimeError("ComfyUIProvider: 未找到 LTXDirector 节点")

        # 获取节点当前的 frame_rate（保留原工作流设置，默认为 24）
        frame_rate = director_node.get("inputs", {}).get("frame_rate", _DEFAULT_FRAME_RATE)
        if not isinstance(frame_rate, (int, float)):
            frame_rate = _DEFAULT_FRAME_RATE

        # 构建 timeline_data 并计算总帧数
        timeline_json, total_frames = self._build_timeline_segments(segments)

        # 更新 LTXDirector 节点输入
        segment_lengths_list = [str(s.get("length", 0)) for s in segments]
        local_prompts = " | ".join(
            s.get("prompt", "") for s in segments
        )

        director_node["inputs"]["global_prompt"] = global_prompt
        director_node["inputs"]["timeline_data"] = timeline_json
        director_node["inputs"]["duration_frames"] = total_frames
        director_node["inputs"]["duration_seconds"] = total_frames / frame_rate
        director_node["inputs"]["segment_lengths"] = ",".join(segment_lengths_list)
        director_node["inputs"]["local_prompts"] = local_prompts

        # 提交到 ComfyUI
        client_id = str(uuid.uuid4())
        resp = httpx.request("POST", f"{self.base_url}/prompt",
                             json={"prompt": wf, "client_id": client_id},
                             timeout=30, trust_env=False)
        if resp.status_code >= 400:
            raise RuntimeError(f"ComfyUI /prompt HTTP {resp.status_code}: {resp.text[:300]}")
        prompt_id = resp.json().get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"ComfyUI 无 prompt_id: {resp.text[:200]}")
        return self._wait_and_fetch(prompt_id)

    # ------------------------------------------------------------------
    # Timeline helpers
    # ------------------------------------------------------------------
    def _build_timeline_segments(self, segments: list[dict]) -> tuple[str, int]:
        """将 segment 列表转为 LTX Director timeline_data JSON 字符串。

        返回 (timeline_json_str, total_frames)。
        """
        segs = []
        cumulative_start = 0
        for seg in segments:
            image_path = seg["image_path"]
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("ascii")

            # 提取文件名作为 imageFile
            image_file = Path(image_path).name

            seg_entry = {
                "id": str(uuid.uuid4()).replace("-", ""),
                "start": cumulative_start,
                "length": seg.get("length", 0),
                "prompt": seg.get("prompt", ""),
                "type": seg.get("type", "image"),
                "imageFile": image_file,
                "imageB64": image_b64,
            }
            segs.append(seg_entry)
            cumulative_start += seg_entry["length"]

        timeline = {"segments": segs, "audioSegments": []}
        return json.dumps(timeline, ensure_ascii=False), cumulative_start

    # ------------------------------------------------------------------
    # Polling & download (unchanged)
    # ------------------------------------------------------------------
    def _wait_and_fetch(self, prompt_id: str) -> bytes:
        deadline = _time.monotonic() + _POLL_TIMEOUT
        while True:
            resp = httpx.request("GET", f"{self.base_url}/history/{prompt_id}",
                                 timeout=10, trust_env=False)
            if resp.status_code >= 400:
                raise RuntimeError(f"ComfyUI /history HTTP {resp.status_code}")
            history = resp.json() or {}
            if prompt_id in history:
                outputs = history[prompt_id].get("outputs") or {}
                for node_out in outputs.values():
                    images = node_out.get("images") or []
                    if images:
                        img_info = images[0]
                        return self._download(img_info["filename"],
                                              img_info.get("subfolder", ""),
                                              img_info.get("type", "output"))
            if _time.monotonic() > deadline:
                raise RuntimeError(f"ComfyUI 轮询超时 prompt_id={prompt_id}")
            _sleep(_POLL_INTERVAL)

    def _download(self, filename: str, subfolder: str, ftype: str) -> bytes:
        resp = httpx.request("GET", f"{self.base_url}/view",
                             params={"filename": filename, "subfolder": subfolder, "type": ftype},
                             timeout=30, trust_env=False)
        if resp.status_code >= 400:
            raise RuntimeError(f"ComfyUI /view HTTP {resp.status_code}")
        return resp.content
