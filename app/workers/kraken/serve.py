"""Optional loopback HTR sidecar. Does not install runtimes or download weights."""

import argparse
import asyncio
import base64
import binascii
import io
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from compass.adapters.base import AdapterError
from compass.adapters.registry import ModelRegistry

MAX_BYTES = 25 * 1024 * 1024
MAX_PIXELS = 40_000_000
APP_ROOT = Path(__file__).resolve().parents[2]


class BodyLimitExceeded(Exception):
    pass


class BodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        received = 0

        async def bounded_receive():
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > 37 * 1024 * 1024:
                raise BodyLimitExceeded
            return message

        try:
            await self.app(scope, bounded_receive, send)
        except BodyLimitExceeded:
            response = JSONResponse(
                {
                    "error": {
                        "code": "image_too_large",
                        "message": "Image request exceeds the worker limit.",
                    }
                },
                status_code=413,
            )
            await response(scope, receive, send)


class ReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: str = Field(min_length=1, max_length=64)
    image_data: str = Field(max_length=36 * 1024 * 1024)
    language: str | None = Field(default=None, max_length=80)


def create_app(environ: dict[str, str] | None = None) -> FastAPI:
    values = dict(os.environ if environ is None else environ)
    # This process reads its own installed weights, never proxies itself recursively.
    values.pop("COMPASS_KRAKEN_WORKER_URL", None)
    values["COMPASS_LOCAL_ONLY"] = "true"
    registry = ModelRegistry(APP_ROOT / "config" / "models.json", environ=values)
    app = FastAPI(title="Compass local HTR worker", docs_url=None, redoc_url=None)
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "[::1]", "testserver"],
    )
    reading_slot = asyncio.Semaphore(1)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        return JSONResponse(
            {
                "error": {
                    "code": "invalid_worker_request",
                    "message": "The worker request is invalid.",
                }
            },
            status_code=422,
        )

    @app.middleware("http")
    async def loopback_browser_origin(request, call_next):
        origin = request.headers.get("origin")
        if origin:
            try:
                parsed = urlsplit(origin)
                allowed = parsed.scheme in {"http", "https"} and parsed.hostname in {
                    "localhost",
                    "127.0.0.1",
                    "::1",
                }
            except ValueError:
                allowed = False
            if not allowed:
                return JSONResponse(
                    {
                        "error": {
                            "code": "origin_denied",
                            "message": "Origin not allowed.",
                        }
                    },
                    status_code=403,
                )
        size = request.headers.get("content-length", "0")
        try:
            too_large = int(size) > 37 * 1024 * 1024
        except ValueError:
            too_large = True
        if too_large:
            return JSONResponse(
                {
                    "error": {
                        "code": "image_too_large",
                        "message": "Image request exceeds the worker limit.",
                    }
                },
                status_code=413,
            )
        return await call_next(request)

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "profiles": [
                route
                for route in registry.list_routes()
                if route["provider"] == "kraken"
            ],
        }

    @app.post("/transcribe")
    async def transcribe(body: ReadRequest, request: Request):
        try:
            route = registry.get_route(body.profile_id)
            if route["provider"] != "kraken":
                raise AdapterError(
                    "unsupported_profile",
                    "This worker only executes known historical HTR profiles.",
                )
            if not route["available"]:
                raise AdapterError(route["status"], route["message"])
            header, encoded = body.image_data.split(",", 1)
            if header not in {
                "data:image/png;base64",
                "data:image/jpeg;base64",
                "data:image/webp;base64",
            }:
                raise ValueError
            data = base64.b64decode(encoded, validate=True)
            if not data or len(data) > MAX_BYTES:
                raise ValueError
            with Image.open(io.BytesIO(data)) as image:
                if (
                    image.format not in {"PNG", "JPEG", "WEBP"}
                    or image.width * image.height > MAX_PIXELS
                ):
                    raise ValueError
                suffix = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}[image.format]
                image.verify()
            with tempfile.TemporaryDirectory(prefix="compass-htr-upload-") as directory:
                path = Path(directory) / ("input" + suffix)
                path.write_bytes(data)
                async with reading_slot:
                    if await request.is_disconnected():
                        return JSONResponse(
                            {
                                "error": {
                                    "code": "cancelled",
                                    "message": "The image-reading request was cancelled.",
                                }
                            },
                            status_code=499,
                        )
                    task = asyncio.create_task(
                        registry.transcribe(body.profile_id, path, body.language)
                    )
                    try:
                        while not task.done():
                            if await request.is_disconnected():
                                task.cancel()
                                break
                            await asyncio.sleep(0.2)
                        return asdict(await task)
                    finally:
                        if not task.done():
                            task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
        except AdapterError as error:
            return JSONResponse(
                {"error": {"code": error.code, "message": error.message}},
                status_code=409,
            )
        except (
            ValueError,
            binascii.Error,
            UnidentifiedImageError,
            OSError,
            Image.DecompressionBombError,
        ):
            return JSONResponse(
                {
                    "error": {
                        "code": "invalid_image",
                        "message": "Use a supported image within the worker size limits.",
                    }
                },
                status_code=422,
            )

    return app


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(
        description="Optional Compass local historical HTR worker"
    )
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    uvicorn.run(create_app(), host="127.0.0.1", port=args.port)
