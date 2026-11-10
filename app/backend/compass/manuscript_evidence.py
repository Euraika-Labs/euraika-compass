"""Exact, explicitly chosen manuscript readings from one local dossier."""

import hashlib
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from compass.api import session_dependency
from compass.corpus import STOP_WORDS
from compass.errors import APIError
from compass.models import Dossier, ImageAsset, Transcription

router = APIRouter(prefix="/api/v1", tags=["manuscript readings"])
MAX_REVISIONS = 6
MAX_LISTED_READINGS = 200
MAX_SEARCH_CHARS = 200_000
MAX_EXCERPT_CHARS = 900
HASH = re.compile(r"[a-f0-9]{64}")


@dataclass(frozen=True)
class ManuscriptReading:
    id: UUID
    image_id: UUID
    dossier_id: UUID
    parent_id: UUID | None
    lineage_id: UUID
    text: str
    kind: str
    engine: str
    model_id: str | None
    language: str | None
    created_at: datetime
    regions: list[dict]
    input_region: dict | None
    image_width: int
    image_height: int
    image_sha256: str
    provenance: dict


def _require_dossier(session: Session, dossier_id: UUID) -> None:
    if session.scalar(select(Dossier.id).where(Dossier.id == dossier_id)) is None:
        raise APIError(404, "manuscript_dossier_not_found", "This manuscript dossier was not found.")


def _invalid_selection() -> APIError:
    return APIError(
        422, "invalid_manuscript_selection",
        "Choose up to six distinct saved manuscript readings from the selected dossier.",
    )


def _scope(dossier_id: UUID):
    return (
        ImageAsset.dossier_id == dossier_id,
        ImageAsset.provenance["kind"].astext == "manuscript",
        ImageAsset.provenance["image_sha256"].astext == ImageAsset.sha256,
        Transcription.kind.in_(("automatic", "user_corrected")),
        Transcription.text.regexp_match(r"[^[:space:]]"),
    )


def _official(provenance: dict) -> bool:
    if not isinstance(provenance, dict):
        return False
    fields = ("manuscript_id", "manuscript_title", "institution", "folio_id", "folio_label", "catalog_url")
    return all(isinstance(provenance.get(key), str) and provenance[key].strip() for key in fields) and bool(
        isinstance(provenance.get("manifest_sha256"), str) and HASH.fullmatch(provenance["manifest_sha256"])
    )


def _limits(provenance: dict) -> dict[str, bool]:
    value = provenance.get("use_limits")
    value = value if isinstance(value, dict) else {}
    return {key: value.get(key) is True for key in ("preview", "local_storage", "local_ocr", "external_processing")}


@router.get("/dossiers/{dossier_id}/manuscript-readings")
def manuscript_readings(dossier_id: UUID, session: Session = Depends(session_dependency)):
    _require_dossier(session, dossier_id)
    rows = session.execute(
        select(Transcription.id, Transcription.image_id, Transcription.parent_id, Transcription.kind,
               Transcription.language, Transcription.created_at, ImageAsset.provenance)
        .join(ImageAsset, Transcription.image_id == ImageAsset.id)
        .where(*_scope(dossier_id))
        .order_by(Transcription.created_at.desc(), Transcription.id.desc())
        .limit(MAX_LISTED_READINGS + 1)
    ).all()
    items = []
    for row in rows[:MAX_LISTED_READINGS]:
        provenance = row.provenance
        if not _official(provenance):
            continue
        items.append({
            "id": str(row.id), "image_id": str(row.image_id),
            "parent_id": str(row.parent_id) if row.parent_id else None,
            "title": provenance["manuscript_title"], "folio_label": provenance["folio_label"],
            "kind": row.kind, "language": row.language or provenance.get("language"),
            "created_at": row.created_at.isoformat(),
            "external_processing": _limits(provenance)["external_processing"],
        })
    return {"items": items, "truncated": len(rows) > MAX_LISTED_READINGS}


def _lineage_roots(session: Session, revision_ids: list[UUID]) -> dict[UUID, UUID]:
    ancestors = select(
        Transcription.id.label("revision_id"), Transcription.id.label("node_id"),
        Transcription.image_id, Transcription.parent_id,
    ).where(Transcription.id.in_(revision_ids)).cte("reading_ancestors", recursive=True)
    # UNION ends a malformed cycle as well as an ordinary finite chain.
    ancestors = ancestors.union(select(
        ancestors.c.revision_id, Transcription.id, Transcription.image_id, Transcription.parent_id,
    ).select_from(Transcription).join(ancestors, and_(
        Transcription.id == ancestors.c.parent_id,
        Transcription.image_id == ancestors.c.image_id,
    )))
    roots = session.execute(select(ancestors.c.revision_id, ancestors.c.node_id).where(
        ancestors.c.parent_id.is_(None),
    )).all()
    return {row.revision_id: row.node_id for row in roots}


def selected_manuscript_readings(
    session: Session, dossier_id: UUID, revision_ids: list[UUID], *, external_processing: bool,
) -> tuple[list[ManuscriptReading], int]:
    """Validate the entire selection, then admit permitted readings in selection order."""
    if not 1 <= len(revision_ids) <= MAX_REVISIONS or len(set(revision_ids)) != len(revision_ids):
        raise _invalid_selection()
    _require_dossier(session, dossier_id)
    rows = session.execute(
        select(Transcription, ImageAsset)
        .join(ImageAsset, Transcription.image_id == ImageAsset.id)
        .where(*_scope(dossier_id), Transcription.id.in_(revision_ids))
    ).all()
    if len(rows) != len(revision_ids) or any(not _official(image.provenance) for _, image in rows):
        raise _invalid_selection()
    roots = _lineage_roots(session, revision_ids)
    if len(roots) != len(revision_ids):
        raise _invalid_selection()
    by_id = {revision.id: (revision, image) for revision, image in rows}
    readings = []
    blocked = 0
    for revision_id in revision_ids:
        revision, image = by_id[revision_id]
        provenance = image.provenance
        if external_processing and not _limits(provenance)["external_processing"]:
            blocked += 1
            continue
        readings.append(ManuscriptReading(
            id=revision.id, image_id=image.id, dossier_id=image.dossier_id,
            parent_id=revision.parent_id, lineage_id=roots[revision.id], text=revision.text,
            kind=revision.kind, engine=revision.engine, model_id=revision.model_id,
            language=revision.language or provenance.get("language"), created_at=revision.created_at,
            regions=revision.regions, input_region=revision.input_region,
            image_width=image.width, image_height=image.height, image_sha256=image.sha256,
            provenance=provenance,
        ))
    return readings, blocked


def _word_spans(value: str) -> Iterator[tuple[str, int, int]]:
    start = None
    for index, char in enumerate(value):
        if char.isalnum():
            if start is None:
                start = index
        elif start is not None and not unicodedata.category(char).startswith("M"):
            if index - start <= MAX_EXCERPT_CHARS:
                yield _fold(value[start:index]), start, index
            start = None
    if start is not None and len(value) - start <= MAX_EXCERPT_CHARS:
        yield _fold(value[start:]), start, len(value)


def _fold(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.category(char).startswith("M") and char != "\u0640"
    ).replace("\u0671", "\u0627").casefold()


@dataclass(frozen=True)
class _Excerpt:
    start: int
    end: int
    score: int
    line: str | None = None


def _matched_window(line: str, terms: set[str]) -> tuple[int, int, int] | None:
    hits = [(word, start, end) for word, start, end in _word_spans(line) if word in terms]
    if not hits:
        return None
    if len(line) <= MAX_EXCERPT_CHARS:
        return 0, len(line), len({word for word, _, _ in hits})
    counts = Counter()
    left = 0
    best_score = 0
    best_start, best_end = 0, 0
    for word, _, end in hits:
        counts[word] += 1
        while end - hits[left][1] > MAX_EXCERPT_CHARS:
            first = hits[left][0]
            counts[first] -= 1
            if counts[first] == 0:
                del counts[first]
            left += 1
        if len(counts) > best_score:
            best_start, best_end, best_score = hits[left][1], end, len(counts)
    spare = MAX_EXCERPT_CHARS - (best_end - best_start)
    start = min(max(0, best_start - spare // 2), len(line) - MAX_EXCERPT_CHARS)
    return start, start + MAX_EXCERPT_CHARS, best_score


def _excerpt(text: str, terms: set[str]) -> _Excerpt | None:
    scanned = text[:MAX_SEARCH_CHARS]
    if terms:
        position = 0
        best = None
        for raw_line in scanned.splitlines(keepends=True):
            line = raw_line.rstrip("\r\n")
            match = _matched_window(line, terms)
            if match is not None:
                start, end, score = match
                if best is None or score > best.score:
                    best = _Excerpt(position + start, position + end, score, line)
            position += len(raw_line)
        if best is not None:
            return best
    # The user explicitly picked this revision. Offer its bounded opening to the relevance selector.
    start = len(scanned) - len(scanned.lstrip())
    if start == len(scanned):
        return None
    return _Excerpt(start, min(len(scanned), start + MAX_EXCERPT_CHARS), 0)


def _box(value, width: int, height: int, *, integers: bool = False) -> dict | None:
    keys = ("x", "y", "width", "height")
    if not isinstance(value, dict):
        return None
    allowed = (int,) if integers else (int, float)
    if any(type(value.get(key)) not in allowed for key in keys):
        return None
    x, y, w, h = (value[key] for key in keys)
    if any(isinstance(n, float) and not math.isfinite(n) for n in (x, y, w, h)):
        return None
    if x < 0 or y < 0 or not 0 < w <= width or not 0 < h <= height or x > width - w or y > height - h:
        return None
    return {"x": x, "y": y, "width": w, "height": h}


def _region(reading: ManuscriptReading, excerpt: _Excerpt) -> dict | None:
    width, height = reading.image_width, reading.image_height
    crop = _box(reading.input_region, width, height, integers=True)
    if reading.input_region is not None and crop is None:
        return None
    system = {"coordinate_system": "original_image_pixels"}
    if (
        reading.kind == "automatic" and reading.engine == "kraken" and excerpt.line
        and reading.text.count(excerpt.line) == 1 and len(reading.regions) <= 2048
    ):
        matches = [region for region in reading.regions if (
            isinstance(region, dict) and region.get("type") == "line"
            and region.get("coordinate_system") == "input_pixels" and type(region.get("page")) is int
            and region["page"] == 0 and region.get("text") == excerpt.line
        )]
        if len(matches) == 1:
            box = _box(matches[0].get("bbox"), crop["width"] if crop else width, crop["height"] if crop else height)
            if box is not None:
                if crop:
                    box["x"] += crop["x"]
                    box["y"] += crop["y"]
                return {**box, **system, "kind": "text_region"}
    if crop:
        return {**crop, **system, "kind": "input_crop"}
    return None


def manuscript_candidates(
    readings: list[ManuscriptReading], queries: list[str], *, limit: int = MAX_REVISIONS,
) -> list[dict]:
    terms = set()
    for query in queries[:4]:
        for word, _, _ in _word_spans(query[:240]):
            if len(word) > 1 and word not in STOP_WORDS and len(terms) < 32:
                terms.add(word)
    ranked = []
    for reading in readings[:MAX_REVISIONS]:
        excerpt = _excerpt(reading.text, terms)
        if excerpt is not None:
            ranked.append((excerpt, reading))
    ranked.sort(key=lambda item: item[0].score, reverse=True)
    candidates = []
    for excerpt, reading in ranked[:max(0, min(limit, MAX_REVISIONS))]:
        source = reading.provenance
        quote = reading.text[excerpt.start:excerpt.end]
        image_url = f"/api/v1/images/{reading.image_id}/content"
        reference = " · ".join(str(value) for value in (source.get("shelfmark"), source["folio_label"]) if value)
        candidates.append({
            "kind": "manuscript", "source_type": "manuscript_transcription", "evidence_type": reading.kind,
            "evidence_role": "manuscript_reading", "title": source["manuscript_title"],
            "edition_title": source["manuscript_title"], "reference": reference, "quote": quote,
            "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
            "excerpt_start": excerpt.start, "excerpt_end": excerpt.end,
            "excerpt_coordinate_system": "unicode_codepoints",
            "match_type": "lexical" if excerpt.score else "opening",
            "image_id": str(reading.image_id), "image_content_url": image_url,
            "image_width": reading.image_width, "image_height": reading.image_height,
            "image_sha256": reading.image_sha256, "dossier_id": str(reading.dossier_id),
            "transcription_id": str(reading.id), "parent_id": str(reading.parent_id) if reading.parent_id else None,
            "lineage_id": str(reading.lineage_id), "language": reading.language, "engine": reading.engine,
            "model_id": reading.model_id, "created_at": reading.created_at.isoformat(),
            "folio_label": source["folio_label"], "source_url": source.get("source_url") or source["catalog_url"],
            "provenance": source, "use_limits": _limits(source), "region": _region(reading, excerpt),
            "collection_memberships": [],
        })
    return candidates
