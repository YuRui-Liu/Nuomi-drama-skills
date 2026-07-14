"""Gemini image provider — uses google.genai.Client for Imagen generation.

Requires: pip install google-genai

Env vars used (via providers.load_config()):
    GEMINI_API_KEY  — Google AI API key
    GEMINI_MODEL    — model id (default: "imagen-4.0-generate-001")
"""

from __future__ import annotations

from .base import ImageProvider


class GeminiImageProvider(ImageProvider):
    """Image generation via Google Gemini / Imagen API."""

    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        self.api_key = cfg.get("api_key", "")
        self.model_id = cfg.get("model", "imagen-4.0-generate-001")

    def generate_image(
        self,
        prompt: str,
        *,
        size: dict | str | None = None,
        refs: list[str] | None = None,
    ) -> bytes:
        """Generate a single image via Gemini Imagen.

        Args:
            prompt: Text prompt for image generation.
            size: Either a dict like ``{"aspectRatio": "9:16"}``, a string
                  like ``"9:16"``, or a dict with ``width``/``height``.
            refs: Optional list of reference image paths (not used by Imagen
                  in generate_images mode; kept for interface compatibility).

        Returns:
            Raw image bytes (PNG).
        """
        if not self.api_key:
            raise ValueError("GeminiImageProvider: GEMINI_API_KEY is not configured")

        # Lazy import so the skill remains importable without google-genai installed.
        try:
            from google import genai
        except ImportError:
            raise ImportError(
                "google-genai is required for GeminiImageProvider. "
                "Install it with: pip install google-genai"
            )

        client = genai.Client(api_key=self.api_key)

        # ── Resolve size / aspect ratio ──────────────────────────
        aspect_ratio = "9:16"
        if isinstance(size, dict):
            if "aspectRatio" in size:
                aspect_ratio = str(size["aspectRatio"])
            elif "width" in size and "height" in size:
                # Map common resolutions to aspect ratio strings
                w, h = int(size["width"]), int(size["height"])
                ratio = w / h
                if ratio > 1.7:
                    aspect_ratio = "16:9"
                elif ratio > 1.2:
                    aspect_ratio = "4:3"
                elif ratio > 0.9:
                    aspect_ratio = "1:1"
                elif ratio > 0.6:
                    aspect_ratio = "3:4"
                else:
                    aspect_ratio = "9:16"
        elif isinstance(size, str) and size.strip():
            aspect_ratio = size.strip()

        # ── Config ───────────────────────────────────────────────
        config = {
            "aspect_ratio": aspect_ratio,
            "safety_filter_level": "block_some",
            "person_generation": "allow_adult",
        }

        # ── Generate ─────────────────────────────────────────────
        response = client.models.generate_images(
            model=self.model_id,
            prompt=prompt,
            config=config,
        )

        if not response.generated_images:
            raise RuntimeError(
                f"GeminiImageProvider: no images returned for model={self.model_id}"
            )

        # Return the first generated image
        image = response.generated_images[0]
        if image.image and image.image.image_bytes:
            return image.image.image_bytes

        # Some responses may provide a URL instead of raw bytes.
        if hasattr(image, 'image') and hasattr(image.image, 'uri') and image.image.uri:
            import httpx
            resp = httpx.get(image.image.uri, timeout=60)
            resp.raise_for_status()
            return resp.content

        raise RuntimeError(
            f"GeminiImageProvider: generated image has no image_bytes or uri"
        )
