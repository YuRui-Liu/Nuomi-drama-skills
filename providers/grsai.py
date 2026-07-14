"""Grsai 图片 provider（改编自平台 shot_agent/vendor/providers/image_gen.py）。"""
from __future__ import annotations
import base64, mimetypes, ssl, time as _time
from pathlib import Path
from .base import ImageProvider

import httpx

_POST_RETRY_ON = (httpx.ConnectError, httpx.ConnectTimeout)
_POLL_INTERVAL = 3.0
_RETRY_ATTEMPTS = 4
_RETRY_BACKOFFS = (1.0, 2.0, 4.0)


def _sleep(seconds: float) -> None:
    _time.sleep(seconds)


def _retry(fn, retry_on=None):
    last = None
    for attempt in range(_RETRY_ATTEMPTS):
        try:
            return fn()
        except (httpx.TransportError, ssl.SSLError) as e:
            last = e
            retriable = isinstance(e, retry_on) if retry_on else True
            if not retriable or attempt >= _RETRY_ATTEMPTS - 1:
                raise
            _sleep(_RETRY_BACKOFFS[min(attempt, len(_RETRY_BACKOFFS) - 1)])
    raise last


def _to_data_url(path: str) -> str:
    p = Path(path)
    mime = mimetypes.guess_type(str(p))[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


class GrsaiProvider(ImageProvider):
    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        self.api_key = cfg.get("api_key", "")
        self.base_url = (cfg.get("base_url") or "https://grsai.dakka.com.cn").rstrip("/")
        self.model = cfg.get("model", "gpt-image-2-vip")
        self.timeout = float(cfg.get("timeout", 1800))
        self.request_timeout = float(cfg.get("request_timeout", 60))

    def generate_image(self, prompt: str, *, size: dict | str | None = None,
                       refs: list[str] | None = None) -> bytes:
        if not self.api_key:
            raise ValueError("GrsaiProvider: api_key 未配置")
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": "application/json"}
        model = self.model.removeprefix("grsai/")
        body: dict = {"model": model, "prompt": prompt, "replyType": "async"}
        if refs:
            body["images"] = [_to_data_url(r) for r in refs]
        if isinstance(size, dict):
            body.update({k: v for k, v in size.items()
                         if k in ("aspectRatio", "imageSize", "size")})
        elif size:
            body["aspectRatio"] = size

        def _do_post():
            return httpx.request("POST", f"{self.base_url}/v1/api/generate",
                                 headers=headers, json=body, timeout=self.request_timeout,
                                 trust_env=False)

        resp = _retry(_do_post, retry_on=_POST_RETRY_ON)
        if resp.status_code >= 400:
            raise RuntimeError(f"Grsai HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json() or {}
        if data.get("status") == "running":
            data = self._poll(data["id"], headers)
        if data.get("status") != "succeeded":
            raise RuntimeError(f"Grsai 生成失败: {data.get('error') or data}")
        urls = [r["url"] for r in (data.get("results") or []) if r.get("url")]
        if not urls:
            raise RuntimeError(f"Grsai 无图片 URL: {data}")
        return self._fetch(urls[0])

    def _poll(self, task_id: str, headers: dict) -> dict:
        url = f"{self.base_url}/v1/api/result?id={task_id}"
        deadline = _time.monotonic() + self.timeout
        while True:
            resp = httpx.request("GET", url, headers=headers,
                                 timeout=self.request_timeout, trust_env=False)
            if resp.status_code >= 400:
                raise RuntimeError(f"Grsai 轮询 HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json() or {}
            if data.get("status") != "running":
                return data
            if _time.monotonic() >= deadline:
                raise RuntimeError(f"Grsai 轮询超时 id={task_id}")
            _sleep(_POLL_INTERVAL)

    def _fetch(self, url: str) -> bytes:
        resp = httpx.request("GET", url, timeout=60, trust_env=False)
        if resp.status_code >= 400:
            raise RuntimeError(f"拉取图片失败 HTTP {resp.status_code}")
        return resp.content
