"""Official catalogue and provenance-preserving dossier attachments."""

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from compass.api import find, session_dependency
from compass.errors import APIError
from compass.models import Dossier, ImageAsset
from compass.schemas import ImageRead
from compass.storage import BlobStore, ImageInfo

router = APIRouter(prefix="/api/v1", tags=["manuscripts"])
CatalogueId = Annotated[str, Path(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_-]+$")]
SessionDependency = Annotated[Session, Depends(session_dependency)]
PERMISSIONS = ("preview", "local_storage", "local_ocr", "external_processing")
IMAGE_HEADERS = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}


class ManuscriptImport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dossier_id: UUID


def _permissions(manuscript: dict, folio: dict | None = None) -> dict[str, bool]:
    manuscript_limits = manuscript.get("use_limits")
    manuscript_limits = manuscript_limits if isinstance(manuscript_limits, dict) else {}
    folio_limits = folio.get("use_limits", manuscript_limits) if folio else manuscript_limits
    folio_limits = folio_limits if isinstance(folio_limits, dict) else {}
    return {
        permission: manuscript_limits.get(permission) is True
        and folio_limits.get(permission) is True
        for permission in PERMISSIONS
    }


def _require_permission(limits: dict[str, bool], permission: str) -> None:
    if not limits[permission]:
        message = (
            "The source terms do not permit an in-app preview. Open the official catalogue instead."
            if permission == "preview"
            else "The source terms do not permit saving this scan to a dossier."
        )
        raise APIError(403, "manuscript_use_blocked", message)


def _require_catalog_permission(manuscript_id: str, permission: str) -> None:
    from compass.manuscript_catalog import list_manuscripts

    item = next((item for item in list_manuscripts() if item["id"] == manuscript_id), None)
    if item is None:
        raise APIError(404, "not_found", "This manuscript was not found in the official catalogue.")
    _require_permission(_permissions(item), permission)


@router.get("/manuscripts")
def manuscripts(
    q: Annotated[str | None, Query(max_length=160)] = None,
    language: Annotated[str | None, Query(max_length=30)] = None,
):
    from compass.manuscript_catalog import list_manuscripts

    return {"items": list_manuscripts(q=q, language=language)}


@router.get("/manuscripts/{manuscript_id}/folios")
async def folios(manuscript_id: CatalogueId):
    from compass.manuscript_catalog import list_folios

    listing = await list_folios(manuscript_id)
    items = []
    for folio in listing["items"]:
        limits = _permissions(listing["manuscript"], folio)
        preview_url = (
            f"/api/v1/manuscripts/{manuscript_id}/folios/{folio['id']}/preview"
            if limits["preview"] else None
        )
        items.append({**folio, "preview_url": preview_url, "use_limits": limits})
    return {**listing, "items": items}


def _expected_image(fetched) -> ImageInfo:
    return ImageInfo(fetched.sha256, fetched.media_type, fetched.width, fetched.height)


def _verify_selection(fetched, manuscript_id: str, folio_id: str) -> None:
    if fetched.manuscript["id"] != manuscript_id or fetched.folio["id"] != folio_id:
        raise APIError(502, "scan_metadata_mismatch", "The downloaded scan did not match the selected folio.")


@router.get("/manuscripts/{manuscript_id}/folios/{folio_id}/preview")
async def preview(manuscript_id: CatalogueId, folio_id: CatalogueId, request: Request):
    from compass.manuscript_catalog import fetch_folio

    _require_catalog_permission(manuscript_id, "preview")
    fetched = await fetch_folio(manuscript_id, folio_id, preview=True)
    _verify_selection(fetched, manuscript_id, folio_id)
    _require_permission(_permissions(fetched.manuscript, fetched.folio), "preview")
    info = await run_in_threadpool(request.app.state.blobs.inspect_image, fetched.data)
    if info != _expected_image(fetched):
        raise APIError(502, "scan_metadata_mismatch", "The preview did not match its verified image metadata.")
    return Response(fetched.data, media_type=info.media_type, headers=IMAGE_HEADERS)


def _check_dossier(session: Session, dossier_id: UUID) -> None:
    find(session, Dossier, dossier_id)
    session.rollback()  # Release the read transaction before contacting the official source.


def _save_scan(session: Session, blobs: BlobStore, dossier_id: UUID, fetched) -> ImageAsset:
    manuscript = fetched.manuscript
    folio = fetched.folio
    limits = _permissions(manuscript, folio)
    _require_permission(limits, "local_storage")
    if session.get(Dossier, dossier_id, with_for_update=True) is None:
        raise APIError(404, "not_found", "This dossier was not found.")

    image_info = blobs.store_image(fetched.data, expected=_expected_image(fetched))
    provenance = {
        "kind": "manuscript",
        "manuscript_id": manuscript["id"],
        "manuscript_title": manuscript["title"],
        "institution": manuscript["institution"],
        "shelfmark": manuscript.get("shelfmark"),
        "language": manuscript.get("language"),
        "date": manuscript.get("date"),
        "catalog_url": manuscript.get("catalog_url"),
        "manifest_url": manuscript.get("manifest_url"),
        "manifest_sha256": fetched.manifest_sha256,
        "folio_id": folio["id"],
        "folio_label": folio["label"],
        "canvas_id": folio.get("canvas_id"),
        "canvas_width": folio.get("width"),
        "canvas_height": folio.get("height"),
        "source_url": folio.get("source_url"),
        "image_url": fetched.image_url,
        "image_sha256": image_info.sha256,
        "representation": "repository_delivered_image",
        "attribution": manuscript.get("attribution"),
        "rights_url": manuscript.get("rights_url"),
        "use_limits": limits,
    }
    identity = json.dumps(provenance, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    import_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    existing = session.scalar(select(ImageAsset).where(
        ImageAsset.dossier_id == dossier_id,
        ImageAsset.sha256 == image_info.sha256,
        ImageAsset.provenance["import_key"].astext == import_key,
    ))
    if existing is not None:
        session.commit()
        return existing

    filename = f"{manuscript.get('shelfmark') or manuscript['id']} - {folio['label']}"
    filename = re.sub(r'[\x00-\x1f<>:"/\\|?*]', "_", filename).strip(" .")[:180] or "manuscript"
    extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[image_info.media_type]
    image = ImageAsset(
        dossier_id=dossier_id, filename=filename + extension, **image_info.__dict__,
        provenance={**provenance, "import_key": import_key, "retrieved_at": datetime.now(timezone.utc).isoformat()},
    )
    session.add(image)
    session.commit()
    session.refresh(image)
    return image


@router.post("/manuscripts/{manuscript_id}/folios/{folio_id}/import", response_model=ImageRead, status_code=201)
async def import_scan(
    manuscript_id: CatalogueId, folio_id: CatalogueId, body: ManuscriptImport,
    request: Request, session: SessionDependency,
):
    from compass.manuscript_catalog import fetch_folio

    _require_catalog_permission(manuscript_id, "local_storage")
    await run_in_threadpool(_check_dossier, session, body.dossier_id)
    fetched = await fetch_folio(manuscript_id, folio_id, preview=False)
    _verify_selection(fetched, manuscript_id, folio_id)
    return await run_in_threadpool(_save_scan, session, request.app.state.blobs, body.dossier_id, fetched)
