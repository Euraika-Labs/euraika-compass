import logging
import os
import re
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from compass import __version__
from compass.adapters.registry import ModelRegistry
from compass.api import router
from compass.config import Settings
from compass.db import Database
from compass.errors import error_response, install_error_handlers
from compass.jobs import JobService
from compass.middleware import UploadBodyLimitMiddleware
from compass.storage import BlobStore

logger = logging.getLogger("compass")


def local_hostname(hostname: str | None) -> bool:
    return hostname in {"localhost", "127.0.0.1", "::1"} or bool(
        hostname and re.fullmatch(r"\d+\.localhost", hostname)
    )


def allowed_origin(origin: str) -> bool:
    try:
        parsed = urlsplit(origin)
        return (
            parsed.scheme in {"http", "https"}
            and local_hostname(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and parsed.path in {"", "/"}
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError:
        return False


def create_app(settings: Settings | None = None, registry=None) -> FastAPI:
    settings = settings or Settings()
    database = Database(settings.database_url)
    blobs = BlobStore(settings.data_dir, settings.max_upload_bytes, settings.max_image_pixels)
    if registry is None:
        registry = ModelRegistry(
            settings.config_dir / "models.json",
            settings.data_dir / "routes.json",
            environ={**os.environ, "COMPASS_LOCAL_ONLY": str(settings.local_only).lower()},
        )
    jobs = JobService(database, registry, blobs)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        ready, _ = database.ready()
        if ready:
            jobs.recover()
        try:
            yield
        finally:
            await jobs.shutdown()
            database.dispose()

    application = FastAPI(
        title="Euraika Compass",
        description="Personal neutral theological research skeleton; no synthetic research results.",
        version=__version__,
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.database = database
    application.state.blobs = blobs
    application.state.registry = registry
    application.state.jobs = jobs
    install_error_handlers(application)
    application.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|\d+\.localhost)(:\d+)?",
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    application.add_middleware(UploadBodyLimitMiddleware, max_upload_bytes=settings.max_upload_bytes)

    @application.middleware("http")
    async def local_access(request: Request, call_next):
        try:
            host = urlsplit("//" + request.headers.get("host", "")).hostname
        except ValueError:
            host = None
        if not local_hostname(host):
            return error_response(400, "invalid_host", "Only local hostnames are accepted.")
        origin = request.headers.get("origin")
        if origin and not allowed_origin(origin):
            return error_response(403, "origin_denied", "This browser origin is not allowed.")
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    application.include_router(router)
    frontend = settings.frontend_dir
    if (frontend / "assets").is_dir():
        application.mount("/assets", StaticFiles(directory=frontend / "assets"), name="static-assets")

    @application.get("/{path:path}", include_in_schema=False)
    def frontend_app(path: str):
        if path == "api" or path.startswith("api/"):
            return error_response(404, "not_found", "This API route was not found.")
        candidate = (frontend / path).resolve()
        if candidate.is_relative_to(frontend) and candidate.is_file():
            return FileResponse(candidate)
        if (frontend / "index.html").is_file():
            return FileResponse(frontend / "index.html")
        return JSONResponse(
            {
                "name": "Euraika Compass",
                "stage": "skeleton",
                "message": "Build app/frontend to serve the workbench. API documentation is at /docs.",
            }
        )

    return application


app = create_app()
