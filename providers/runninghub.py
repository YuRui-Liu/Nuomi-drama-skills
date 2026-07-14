# .claude/skills/nuomi-drama-skills/providers/runninghub.py
"""RunningHub 图 + 宫格放大 + 视频 + 配音 provider（改编自平台 upscale_gen.py + video_gen.py）。"""
from __future__ import annotations
import mimetypes, ssl, time as _time
from pathlib import Path
from .base import ImageProvider, VideoProvider, DubProvider, GridUpscaleProvider
import httpx

_RETRY_ATTEMPTS = 4
_RETRY_BACKOFFS = (1.0, 2.0, 4.0)
_RATE_LIMIT_BACKOFFS = (30.0, 60.0, 120.0)
_POST_RETRY = (httpx.ConnectError, httpx.ConnectTimeout)


def _sleep(s: float) -> None:
    _time.sleep(s)


def _is_rate_limit(exc: Exception) -> bool:
    """检测 HTTP 429 速率限制响应。"""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429
    return False


def _retry(fn, retry_on=None):
    last = None
    for i in range(_RETRY_ATTEMPTS):
        try:
            return fn()
        except httpx.HTTPStatusError as e:
            last = e
            if _is_rate_limit(e):
                _sleep(_RATE_LIMIT_BACKOFFS[min(i, 2)])
                continue
            raise
        except (httpx.TransportError, ssl.SSLError) as e:
            last = e
            if (retry_on and not isinstance(e, retry_on)) or i >= _RETRY_ATTEMPTS - 1:
                raise
            _sleep(_RETRY_BACKOFFS[min(i, 2)])
    raise last


def _guess_mime(path: Path) -> str:
    return {".png": "image/png", ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg", ".wav": "audio/wav",
            ".mp4": "video/mp4"}.get(path.suffix.lower(), "application/octet-stream")


class RunningHubProvider(ImageProvider, VideoProvider, DubProvider, GridUpscaleProvider):
    def __init__(self, cfg: dict) -> None:
        # Multiple inheritance: call ImageProvider.__init__ only (all bases share same __init__ signature)
        ImageProvider.__init__(self, cfg)
        self.api_key = cfg.get("api_key", "")
        self.base_url = (cfg.get("base_url") or "https://www.runninghub.cn").rstrip("/")
        self.image_wf = cfg.get("image_workflow_id", "")
        self.video_wf = cfg.get("video_workflow_id", "")
        self.dub_wf = cfg.get("dub_workflow_id", "")
        self.upscale_wf = cfg.get("upscale_workflow_id", "")
        self.poll_interval = float(cfg.get("poll_interval", 5))
        self.poll_timeout = float(cfg.get("poll_timeout", 300))
        self.voice_design_wf = cfg.get("voice_design_workflow_id", "")
        self.dub_clone_wf = cfg.get("dub_clone_workflow_id", "")
        self.max_parallel = int(cfg.get("max_parallel", 3))

    # ── 共用 HTTP ───────────────────────────────────────────────────────
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _upload(self, path: str) -> str:
        p = Path(path)
        def _do():
            with p.open("rb") as f:
                return httpx.request(
                    "POST", f"{self.base_url}/openapi/v2/media/upload/binary",
                    headers=self._headers(),
                    files={"file": (p.name, f, _guess_mime(p))},
                    timeout=30, trust_env=False)
        resp = _retry(_do, retry_on=_POST_RETRY)
        if resp.status_code >= 400:
            raise RuntimeError(f"RH upload HTTP {resp.status_code}: {resp.text[:200]}")
        d = resp.json() or {}
        if d.get("code") != 0:
            raise RuntimeError(f"RH upload code={d.get('code')}: {d.get('msg')}")
        return d["data"]["fileName"]

    def _create_task(self, workflow_id: str, node_info: list[dict]) -> str:
        def _do():
            return httpx.request(
                "POST", f"{self.base_url}/task/openapi/create",
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"apiKey": self.api_key, "workflowId": workflow_id,
                      "nodeInfoList": node_info},
                timeout=30, trust_env=False)
        resp = _retry(_do, retry_on=_POST_RETRY)
        if resp.status_code >= 400:
            raise RuntimeError(f"RH create_task HTTP {resp.status_code}: {resp.text[:200]}")
        d = resp.json() or {}
        if d.get("code") != 0:
            raise RuntimeError(f"RH create_task code={d.get('code')}: {d.get('msg')}")
        return str(d["data"]["taskId"])

    def _wait(self, task_id: str) -> list[dict]:
        """轮询直到任务完成，返回 outputs 列表 [{url, outputType, ...}]。

        RH 平台 v2 响应顶层是 {taskId, status, results, ...}，results 数组元素字段
        为 {url, outputType, nodeId}。同时兼容 v1 结构（{data: {outputs: [{fileUrl}]}}）。
        """
        deadline = _time.monotonic() + self.poll_timeout
        while True:
            resp = httpx.request(
                "POST", f"{self.base_url}/openapi/v2/query",
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"taskId": task_id}, timeout=15, trust_env=False)
            if resp.status_code >= 400:
                raise RuntimeError(f"RH query HTTP {resp.status_code}")
            d = resp.json() or {}
            # v1 兼容：data 嵌套
            if isinstance(d.get("data"), dict):
                d = d["data"]
            status = d.get("status", "UNKNOWN")
            if status == "SUCCESS":
                # v2 顶层 results / v1 嵌套 outputs
                items = d.get("results") or d.get("outputs") or []
                out = []
                for o in items:
                    url = o.get("url") or o.get("fileUrl")
                    if url:
                        out.append({"url": url, "outputType": o.get("outputType", ""),
                                    "nodeId": o.get("nodeId", "")})
                return out
            if status == "FAILED":
                raise RuntimeError(f"RH task FAILED: {d}")
            if _time.monotonic() > deadline:
                raise RuntimeError(f"RH task 超时 id={task_id}")
            _sleep(self.poll_interval)

    def _download(self, url: str) -> bytes:
        resp = httpx.request("GET", url, timeout=60, trust_env=False)
        if resp.status_code >= 400:
            raise RuntimeError(f"RH download HTTP {resp.status_code}")
        return resp.content

    # ── ImageProvider ──────────────────────────────────────────────────
    def generate_image(self, prompt: str, *, size=None, refs=None) -> bytes:
        if not self.image_wf:
            raise ValueError("RH: image_workflow_id 未配置")
        nodes = [{"nodeId": "1", "fieldName": "text", "fieldValue": prompt}]
        task_id = self._create_task(self.image_wf, nodes)
        items = self._wait(task_id)
        if not items:
            raise RuntimeError("RH: 图片无输出 URL")
        return self._download(items[0]["url"])

    # ── GridUpscaleProvider ────────────────────────────────────────────
    def upscale_grid(self, grid_path: str, rows: int, cols: int, out_dir: str) -> list[str]:
        """上传宫格图 → RH 多宫格高清放大裁切 workflow → 下载拆分后的单镜格图。

        RH 该 workflow 输出顺序固定为:
          items[0]   = 4× 放大后的完整宫格大图（中间产物，非分镜格，丢弃）
          items[1..N] = N 张单独裁切好的分镜格图（N = rows × cols）

        调用方只关心中间产物的格图，本方法内部跳过第一张放大宫格。
        """
        if not self.upscale_wf:
            raise ValueError("RH: upscale_workflow_id 未配置")
        filename = self._upload(grid_path)
        nodes = [
            {"nodeId": "23", "fieldName": "image", "fieldValue": filename},
            {"nodeId": "17", "fieldName": "scale_by", "fieldValue": 4.0},
            {"nodeId": "1", "fieldName": "水平张数", "fieldValue": int(cols)},
            {"nodeId": "1", "fieldName": "垂直张数", "fieldValue": int(rows)},
        ]
        task_id = self._create_task(self.upscale_wf, nodes)
        items = self._wait(task_id)
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)

        # items[0] 是放大后的完整宫格图，items[1:] 才是拆分后的单镜格图
        cells = items[1:] if len(items) > 1 else items
        paths = []
        for i, it in enumerate(cells):
            data = self._download(it["url"])
            dst = out / f"cell_{i:03d}.png"
            dst.write_bytes(data)
            paths.append(str(dst))
        return paths

    # ── VideoProvider ──────────────────────────────────────────────────
    def generate_video(self, prompt: str, first_frame_path: str, duration: float) -> bytes:
        if not self.video_wf:
            raise ValueError("RH: video_workflow_id 未配置")
        fname = self._upload(first_frame_path)
        nodes = [
            {"nodeId": "1", "fieldName": "prompt", "fieldValue": prompt},
            {"nodeId": "2", "fieldName": "image", "fieldValue": fname},
            {"nodeId": "3", "fieldName": "length", "fieldValue": float(duration)},
        ]
        task_id = self._create_task(self.video_wf, nodes)
        items = self._wait(task_id)
        if not items:
            raise RuntimeError("RH: 视频无输出 URL")
        return self._download(items[0]["url"])

    # ── DubProvider ────────────────────────────────────────────────────
    def generate_dub(self, text: str, speaker: str, emotion: str,
                     voice_style: str = "") -> bytes:
        if not self.dub_wf:
            raise ValueError("RH: dub_workflow_id 未配置")
        nodes = [
            {"nodeId": "1", "fieldName": "text", "fieldValue": text},
            {"nodeId": "2", "fieldName": "speaker", "fieldValue": speaker},
            {"nodeId": "3", "fieldName": "emotion", "fieldValue": emotion},
        ]
        if voice_style:
            nodes.append({"nodeId": "4", "fieldName": "voice_style",
                          "fieldValue": voice_style})
        task_id = self._create_task(self.dub_wf, nodes)
        items = self._wait(task_id)
        if not items:
            raise RuntimeError("RH: 配音无输出 URL")
        return self._download(items[0]["url"])

    def design_voice(self, name: str, style: str, language: str, out_dir: str) -> str:
        """对齐 Qwen3 TTS 音色设计工作流：节点 14 = 文本，节点 15 = 音色描述。
        节点 22 的 language 固定 "Auto"，无需外传。
        返回值后缀跟随 RH outputType（flac/wav/mp3）。
        """
        if not self.voice_design_wf:
            raise ValueError("RH: voice_design_workflow_id 未配置")
        nodes = [
            {"nodeId": "14", "fieldName": "text", "fieldValue": "音色参考样例"},
            {"nodeId": "15", "fieldName": "text", "fieldValue": style},
        ]
        task_id = self._create_task(self.voice_design_wf, nodes)
        items = self._wait(task_id)
        if not items:
            raise RuntimeError("RH: 音色设计无输出 URL")
        first = items[0]
        data = self._download(first["url"])
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(name))
        ext = (first.get("outputType") or "wav").lower()
        if ext not in ("wav", "flac", "mp3"):
            ext = "wav"
        dst = out / f"{safe_name}.{ext}"
        dst.write_bytes(data)
        return str(dst)

    def clone_voice(self, text: str, speaker_ref: str, emotion: str) -> bytes:
        """对齐 TTS2 情感声音克隆工作流：
        节点 4 = CR Prompt Text (要合成的文本，fieldName=prompt)
        节点 10 = LoadAudio (参考音频，fieldName=audio，值为 RH 上传后的 fileName)
        节点 16 = CR Prompt Text (情感文本，fieldName=prompt)
        """
        if not self.dub_clone_wf:
            raise ValueError("RH: dub_clone_workflow_id 未配置")
        filename = self._upload(speaker_ref)
        nodes = [
            {"nodeId": "4", "fieldName": "prompt", "fieldValue": text},
            {"nodeId": "10", "fieldName": "audio", "fieldValue": filename},
            {"nodeId": "16", "fieldName": "prompt", "fieldValue": emotion or "平静"},
        ]
        task_id = self._create_task(self.dub_clone_wf, nodes)
        items = self._wait(task_id)
        if not items:
            raise RuntimeError("RH: 克隆配音无输出 URL")
        return self._download(items[0]["url"])
