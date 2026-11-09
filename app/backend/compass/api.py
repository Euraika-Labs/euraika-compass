import asyncio
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from compass import __version__
from compass.adapters.base import AdapterError
from compass.errors import APIError
from compass.jobs import TERMINAL
from compass.models import Dossier, ImageAsset, Source, Transcription, TranscriptionJob
from compass.routing import require_route
from compass.schemas import (
    DossierCreate,
    DossierPatch,
    DossierRead,
    ImageRead,
    JobRead,
    ManualTranscription,
    RevisionCreate,
    RoutePatch,
    TranscriptionRead,
    TranscriptionRequest,
)

router = APIRouter(prefix="/api/v1")


def session_dependency(request: Request):
    yield from request.app.state.database.session()


def find(session: Session, model, object_id: UUID):
    value = session.get(model, object_id)
    if value is None:
        raise APIError(404, "not_found", "This resource was not found.")
    return value


def adapter_error(exc: AdapterError) -> APIError:
    return APIError(409, exc.code, exc.message)


@router.get("/health")
def health(request: Request):
    ready, message = request.app.state.database.ready()
    return {
        "status": "ok" if ready else "degraded",
        "version": __version__,
        "database": {"ready": ready, "message": message},
        "features": {
            "dossiers": ready,
            "image_import": ready,
            "manual_transcription": ready,
            "configured_model_adapters": True,
            "grounded_chat": ready,
            "web_research": ready,
            "roundtable_generation": False,
        },
    }


@router.get("/models")
def models(request: Request):
    return {"items": request.app.state.registry.list_routes()}


@router.patch("/models/{route_id}")
def update_model(route_id: str, body: RoutePatch, request: Request):
    try:
        return request.app.state.registry.set_enabled(route_id, body.enabled)
    except AdapterError as exc:
        raise adapter_error(exc) from exc


@router.get("/personas")
def personas(request: Request):
    path = request.app.state.settings.config_dir / "personas.json"
    if not path.is_file():
        return {"items": []}
    value = json.loads(path.read_text(encoding="utf-8"))
    return {"items": value.get("items", []) if isinstance(value, dict) else value}


@router.get("/source-policy")
def source_policy(request: Request):
    path = request.app.state.settings.config_dir / "source-policy.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


@router.get("/dossiers")
def dossiers(session: Session = Depends(session_dependency)):
    items = session.scalars(select(Dossier).order_by(Dossier.updated_at.desc(), Dossier.id).limit(100))
    return {"items": [DossierRead.model_validate(item) for item in items]}


@router.post("/dossiers", response_model=DossierRead, status_code=201)
def create_dossier(body: DossierCreate, session: Session = Depends(session_dependency)):
    dossier = Dossier(title=body.title, question=body.question)
    session.add(dossier)
    session.commit()
    session.refresh(dossier)
    return dossier


@router.get("/dossiers/{dossier_id}", response_model=DossierRead)
def get_dossier(dossier_id: UUID, session: Session = Depends(session_dependency)):
    return find(session, Dossier, dossier_id)


@router.patch("/dossiers/{dossier_id}", response_model=DossierRead)
def update_dossier(
    dossier_id: UUID, body: DossierPatch, session: Session = Depends(session_dependency)
):
    find(session, Dossier, dossier_id)
    changes = body.model_dump(exclude={"expected_revision"}, exclude_none=True, exclude_unset=True)
    if not changes:
        raise APIError(422, "no_changes", "Provide at least one field to update.")
    result = session.execute(
        update(Dossier)
        .where(Dossier.id == dossier_id, Dossier.revision == body.expected_revision)
        .values(**changes, revision=Dossier.revision + 1, updated_at=datetime.now(timezone.utc))
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        session.rollback()
        raise APIError(409, "revision_conflict", "The dossier changed. Reload it before saving.")
    session.commit()
    session.expire_all()
    return find(session, Dossier, dossier_id)


@router.post("/images", response_model=ImageRead, status_code=201)
async def import_image(
    request: Request,
    dossier_id: UUID = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(session_dependency),
):
    find(session, Dossier, dossier_id)
    session.commit()  # End the read transaction before consuming/validating image content.
    limit = request.app.state.settings.max_upload_bytes
    content = bytearray()
    try:
        while chunk := await file.read(min(1024 * 1024, limit + 1)):
            content.extend(chunk)
            if len(content) > limit:
                raise APIError(413, "image_too_large", "The image exceeds the upload size limit.")
        image_info = request.app.state.blobs.store_image(bytes(content))
    finally:
        await file.close()
    filename = (file.filename or "image").replace("\\", "/").rsplit("/", 1)[-1][:200] or "image"
    image = ImageAsset(dossier_id=dossier_id, filename=filename, **image_info.__dict__)
    session.add(image)
    session.commit()
    session.refresh(image)
    return image


@router.get("/dossiers/{dossier_id}/images")
def dossier_images(dossier_id: UUID, session: Session = Depends(session_dependency)):
    find(session, Dossier, dossier_id)
    items = session.scalars(
        select(ImageAsset).where(ImageAsset.dossier_id == dossier_id).order_by(ImageAsset.created_at)
    )
    return {"items": [ImageRead.model_validate(item) for item in items]}


@router.get("/images/{image_id}/content")
def image_content(image_id: UUID, request: Request, session: Session = Depends(session_dependency)):
    image = find(session, ImageAsset, image_id)
    path = request.app.state.blobs.path(image.sha256)
    if not path.is_file():
        raise APIError(404, "asset_unavailable", "The saved image file is unavailable.")
    return FileResponse(
        path,
        media_type=image.media_type,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )


@router.post("/transcription-jobs", response_model=JobRead, status_code=202)
async def create_transcription_job(
    body: TranscriptionRequest, request: Request, session: Session = Depends(session_dependency)
):
    image = find(session, ImageAsset, body.image_id)
    try:
        route = request.app.state.registry.get_route(body.route_id)
    except AdapterError as exc:
        raise adapter_error(exc) from exc
    require_route(route, request.app.state.settings.local_only)
    region = body.region.model_dump() if body.region else None
    if region and (
        region["x"] + region["width"] > image.width
        or region["y"] + region["height"] > image.height
    ):
        raise APIError(422, "invalid_region", "The region lies outside the original image.")
    job = TranscriptionJob(
        image_id=image.id, route_id=body.route_id, language=body.language, region=region
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    response = JobRead.model_validate(job)
    request.app.state.jobs.start(job.id)
    return response


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: UUID, session: Session = Depends(session_dependency)):
    return find(session, TranscriptionJob, job_id)


@router.post("/jobs/{job_id}/cancel", response_model=JobRead)
async def cancel_job(job_id: UUID, request: Request, session: Session = Depends(session_dependency)):
    await request.app.state.jobs.cancel(job_id)
    session.expire_all()
    return find(session, TranscriptionJob, job_id)


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: UUID, request: Request, session: Session = Depends(session_dependency)):
    find(session, TranscriptionJob, job_id)
    session.commit()

    async def events():
        previous = None
        while not await request.is_disconnected():
            with request.app.state.database.sessions() as event_session:
                job = find(event_session, TranscriptionJob, job_id)
                snapshot = JobRead.model_validate(job)
            payload = snapshot.model_dump_json()
            if payload != previous:
                yield f"event: job\ndata: {payload}\n\n"
                previous = payload
            else:
                yield ": keepalive\n\n"
            if snapshot.status in TERMINAL:
                return
            await asyncio.sleep(0.5)

    return StreamingResponse(
        events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
    )


@router.get("/images/{image_id}/transcriptions")
def transcriptions(image_id: UUID, session: Session = Depends(session_dependency)):
    find(session, ImageAsset, image_id)
    items = session.scalars(
        select(Transcription).where(Transcription.image_id == image_id).order_by(Transcription.created_at)
    )
    return {"items": [TranscriptionRead.model_validate(item) for item in items]}


@router.post("/images/{image_id}/transcriptions", response_model=TranscriptionRead, status_code=201)
def manual_transcription(
    image_id: UUID, body: ManualTranscription, session: Session = Depends(session_dependency)
):
    find(session, ImageAsset, image_id)
    reading = Transcription(
        image_id=image_id,
        text=body.text,
        kind="user_corrected",
        engine="manual",
        model_id=None,
        language=body.language,
        regions=[],
        warnings=["User-provided reading; compare it with the original image."],
    )
    session.add(reading)
    session.commit()
    session.refresh(reading)
    return reading


@router.post("/transcriptions/{transcription_id}/revisions", response_model=TranscriptionRead, status_code=201)
def correct_transcription(
    transcription_id: UUID, body: RevisionCreate, session: Session = Depends(session_dependency)
):
    previous = find(session, Transcription, transcription_id)
    reading = Transcription(
        image_id=previous.image_id,
        parent_id=previous.id,
        text=body.text,
        kind="user_corrected",
        engine="manual",
        model_id=previous.model_id,
        language=previous.language,
        regions=[],  # Edited text has no automatic character/line alignment to the old boxes.
        warnings=["User-corrected reading; no automatic verification of the object's origin."],
        input_region=previous.input_region,
    )
    session.add(reading)
    session.commit()
    session.refresh(reading)
    return reading


@router.get("/sources")
def sources(session: Session = Depends(session_dependency)):
    items = session.scalars(select(Source).order_by(Source.created_at.desc()).limit(100))
    return {
        "items": [
            {
                "id": str(source.id),
                "title": source.title,
                "url": source.url,
                "source_type": source.source_type,
                "provenance": source.provenance,
                "use_limits": source.use_limits,
            }
            for source in items
        ]
    }


@router.post("/research-runs")
@router.post("/roundtables/{roundtable_id}/commands")
def generation_not_implemented():
    raise APIError(
        501,
        "not_implemented",
        "Grounded conversation, research generation and Roundtable turns are not implemented yet. "
        "No model call was started.",
    )
