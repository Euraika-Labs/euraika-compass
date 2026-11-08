import base64
import io
import math
import warnings
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from PIL import Image, UnidentifiedImageError

from .base import READING_INSTRUCTION, REVIEW_WARNING, AdapterError, TranscriptionResult


def local_base_url(value: str) -> str:
    """Local model endpoints are loopback-only and cannot smuggle URL credentials."""
    try:
        url = urlsplit(value)
        if (
            url.scheme not in {"http", "https"}
            or url.hostname not in {"127.0.0.1", "localhost", "::1"}
            or url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
        ):
            raise ValueError
        _ = url.port
    except ValueError:
        raise AdapterError(
            "invalid_local_endpoint",
            "The local image-model endpoint must use loopback without URL credentials.",
        ) from None
    return value.rstrip("/")


def image_data_url(path: Path) -> str:
    if not path.is_file() or path.stat().st_size > 25 * 1024 * 1024:
        raise AdapterError(
            "invalid_image", "The image is missing or exceeds the adapter size limit."
        )
    try:
        data = path.read_bytes()
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in {"PNG", "JPEG", "WEBP"}:
                    raise AdapterError(
                        "unsupported_image", "Use a validated PNG, JPEG or WebP image."
                    )
                media_type = Image.MIME[image.format]
                image.verify()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise AdapterError("invalid_image", "The file is not a valid supported image.") from None
    return f"data:{media_type};base64,{base64.b64encode(data).decode('ascii')}"


async def _request_json(
    url: str,
    payload: dict,
    *,
    headers: dict[str, str] | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict:
    try:
        if client is None:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(120, connect=10), follow_redirects=False, trust_env=False
            ) as owned:
                response = await owned.post(url, json=payload, headers=headers)
        else:
            response = await client.post(url, json=payload, headers=headers)
        if response.status_code in {401, 403}:
            raise AdapterError(
                "provider_access_denied", "The provider rejected access for this configured route."
            )
        if response.status_code == 429:
            raise AdapterError(
                "provider_rate_limited",
                "The configured provider has reached a rate or quota limit.",
            )
        if not response.is_success:
            raise AdapterError(
                "provider_error", "The image-reading provider did not complete the request."
            )
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError
        return body
    except httpx.TimeoutException:
        raise AdapterError("provider_timeout", "The image-reading request timed out.") from None
    except httpx.HTTPError:
        raise AdapterError(
            "provider_unreachable", "The configured image-reading endpoint is unreachable."
        ) from None
    except (ValueError, TypeError):
        raise AdapterError(
            "invalid_provider_output", "The image reader returned an unsupported response."
        ) from None


async def transcribe_qwen(
    image_path: Path,
    model_id: str,
    base_url: str,
    language: str | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> TranscriptionResult:
    base = local_base_url(base_url)
    endpoint = base + ("/chat/completions" if base.endswith("/v1") else "/v1/chat/completions")
    instruction = READING_INSTRUCTION
    if language:
        instruction += f" The user's script/language hint is: {language[:80]}."
    body = await _request_json(
        endpoint,
        {
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {"type": "image_url", "image_url": {"url": image_data_url(image_path)}},
                    ],
                }
            ],
            "temperature": 0,
            "max_tokens": 4096,
            "stream": False,
        },
        client=client,
    )
    try:
        text = body["choices"][0]["message"]["content"]
        if not isinstance(text, str) or not text.strip():
            raise ValueError
    except (KeyError, IndexError, TypeError, ValueError):
        raise AdapterError(
            "invalid_provider_output", "The local image model did not return transcription text."
        ) from None
    return TranscriptionResult(
        text=text,
        engine="openai-compatible-local-vision",
        model_id=model_id,
        warnings=[REVIEW_WARNING, "This route does not supply verified text-region coordinates."],
    )


async def transcribe_kraken_http(
    image_path: Path,
    model_id: str,
    profile_id: str,
    worker_url: str,
    language: str | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> TranscriptionResult:
    body = await _request_json(
        local_base_url(worker_url) + "/transcribe",
        {"profile_id": profile_id, "image_data": image_data_url(image_path), "language": language},
        client=client,
    )
    text = body.get("text")
    regions = body.get("regions", [])
    warnings = body.get("warnings", [])
    if (
        not isinstance(text, str)
        or not text.strip()
        or not isinstance(regions, list)
        or not all(isinstance(region, dict) for region in regions)
        or not isinstance(warnings, list)
        or not all(isinstance(warning, str) for warning in warnings)
        or body.get("model_id") != model_id
    ):
        raise AdapterError(
            "invalid_worker_output", "The local HTR worker returned unsupported reading data."
        )
    return TranscriptionResult(
        text=text,
        engine="kraken",
        model_id=model_id,
        regions=regions,
        warnings=[REVIEW_WARNING, *warnings[:20]],
    )


def _finite_number(value: object) -> float | None:
    if isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value):
        return float(value)
    return None


async def transcribe_mistral(
    image_path: Path,
    model_id: str,
    api_key: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> TranscriptionResult:
    body = await _request_json(
        "https://api.mistral.ai/v1/ocr",
        {
            "model": model_id,
            "document": {"type": "image_url", "image_url": image_data_url(image_path)},
            "include_image_base64": False,
            "include_blocks": True,
        },
        headers={"Authorization": f"Bearer {api_key}"},
        client=client,
    )
    pages = body.get("pages")
    if not isinstance(pages, list) or not pages:
        raise AdapterError("invalid_provider_output", "The OCR provider did not return pages.")
    texts: list[str] = []
    regions: list[dict] = []
    for index, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        text = page.get("markdown", "")
        if isinstance(text, str):
            texts.append(text)
        dimensions = page.get("dimensions") or {}
        if not isinstance(dimensions, dict):
            dimensions = {}
        blocks = page.get("blocks") or []
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            coords = [
                _finite_number(block.get(name))
                for name in ("top_left_x", "top_left_y", "bottom_right_x", "bottom_right_y")
            ]
            if any(value is None for value in coords):
                continue
            x, y, right, bottom = coords
            if x < 0 or y < 0 or right < x or bottom < y:
                continue
            regions.append(
                {
                    "type": str(block.get("type", "text")),
                    "text": str(block.get("content", "")),
                    "bbox": {"x": x, "y": y, "width": right - x, "height": bottom - y},
                    "coordinate_system": "provider_page_pixels",
                    "page": index,
                    "page_width": _finite_number(dimensions.get("width")),
                    "page_height": _finite_number(dimensions.get("height")),
                }
            )
    text = "\n\n".join(texts)
    if not text.strip():
        raise AdapterError("empty_transcription", "The OCR provider did not find readable text.")
    return TranscriptionResult(
        text=text,
        engine="mistral-ocr",
        model_id=model_id,
        regions=regions,
        warnings=[
            REVIEW_WARNING,
            "Provider block coordinates are not verified word-level geometry.",
        ],
    )
