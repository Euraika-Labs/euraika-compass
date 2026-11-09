"""Official facsimiles for the initial manuscript browser.

The registry pins catalog identities. A selected folio resolves to one validated
image-service path supplied by that institution. Preview bytes live in memory.
The caller handles explicit dossier storage and checks the attached use limits.
"""

import asyncio
import hashlib
import io
import json
import re
import time
import warnings
from dataclasses import asdict, dataclass, replace
from urllib.parse import urlsplit

import httpx
from PIL import Image, UnidentifiedImageError

from compass.errors import APIError

_CC_BY_NC = "https://creativecommons.org/licenses/by-nc/4.0/"
_MET_TERMS = "https://www.metmuseum.org/policies/image-resources"
_BODLEIAN_TERMS = "https://digital.bodleian.ox.ac.uk/terms/"
_CAMBRIDGE_TERMS = "https://cudl.lib.cam.ac.uk/terms/"
_BODLEIAN_ID = "8c264b23-f6cc-4f18-98cf-9d75f7175b54"
_VAT_ID = "MSS_Vat.gr.1209"
_UUID_PATTERN = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
_USER_AGENT = "EuraikaCompass/0.1 (https://github.com/Euraika-Labs/euraika-compass)"
_MAX_MANIFEST_BYTES = 4 * 1024 * 1024
_MAX_IMAGE_BYTES = 25 * 1024 * 1024
_MAX_IMAGE_PIXELS = 40_000_000
_MAX_FOLIOS = 2000
_CACHE_SECONDS = 120


@dataclass(frozen=True, slots=True)
class UseLimits:
    preview: bool
    local_storage: bool
    local_ocr: bool
    external_processing: bool


_PREVIEW = UseLimits(True, False, False, False)
_PRIVATE_STUDY = UseLimits(True, True, True, False)
_OPEN_ACCESS = UseLimits(True, True, True, True)


@dataclass(frozen=True, slots=True)
class _Manuscript:
    id: str
    title: str
    institution: str
    shelfmark: str
    language: str
    collections: tuple[str, ...]
    date: str
    description: str
    catalog_url: str
    manifest_url: str
    provider: str
    object_key: str
    attribution: str
    rights_url: str
    terms_url: str
    rights_note: str
    use_limits: UseLimits
    default_folio_id: str

    def metadata(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "institution": self.institution,
            "shelfmark": self.shelfmark,
            "language": self.language,
            "collections": list(self.collections),
            "date": self.date,
            "description": self.description,
            "catalog_url": self.catalog_url,
            "manifest_url": self.manifest_url,
            "attribution": self.attribution,
            "rights_url": self.rights_url,
            "terms_url": self.terms_url,
            "rights_note": self.rights_note,
            "use_limits": asdict(self.use_limits),
            "default_folio_id": self.default_folio_id,
        }


def _cambridge(id, title, shelfmark, language, collections, date, description, code, featured):
    return _Manuscript(
        id=id,
        title=title,
        institution="Cambridge University Library",
        shelfmark=shelfmark,
        language=language,
        collections=collections,
        date=date,
        description=description,
        catalog_url=f"https://cudl.lib.cam.ac.uk/view/{code}/1",
        manifest_url=f"https://cudl.lib.cam.ac.uk/iiif/{code}",
        provider="cambridge",
        object_key=code,
        attribution="Cambridge University Library. Image license CC BY-NC 4.0.",
        rights_url=_CC_BY_NC,
        terms_url=_CAMBRIDGE_TERMS,
        rights_note="Personal, noncommercial study permits a private copy and local reading.",
        use_limits=_PRIVATE_STUDY,
        default_folio_id=featured,
    )


_CATALOG = {
    entry.id: entry
    for entry in (
        _Manuscript(
            id="bodleian-kennicott-1",
            title="Kennicott Bible",
            institution="Bodleian Libraries, University of Oxford",
            shelfmark="MS. Kennicott 1",
            language="he",
            collections=("torah", "bible"),
            date="1476 CE",
            description="An illuminated Hebrew Bible copied in La Coruña, including the Torah.",
            catalog_url=f"https://digital.bodleian.ox.ac.uk/objects/{_BODLEIAN_ID}/",
            manifest_url=f"https://iiif.bodleian.ox.ac.uk/iiif/manifest/{_BODLEIAN_ID}.json",
            provider="bodleian",
            object_key=_BODLEIAN_ID,
            attribution="Photo © Bodleian Libraries, University of Oxford. CC BY-NC 4.0.",
            rights_url=_CC_BY_NC,
            terms_url=_BODLEIAN_TERMS,
            rights_note="Personal, noncommercial study permits a private copy and local reading.",
            use_limits=_PRIVATE_STUDY,
            default_folio_id="40b980af-c292-4d67-9639-f04f6e65a8b1",
        ),
        _cambridge(
            "cambridge-nash",
            "Nash Papyrus",
            "MS Or.233",
            "he",
            ("torah", "bible"),
            "Middle of the second century BCE",
            "A Hebrew papyrus with the Decalogue and the beginning of the Shema.",
            "MS-OR-00233",
            "p0001",
        ),
        _cambridge(
            "cambridge-bezae",
            "Codex Bezae",
            "MS Nn.2.41",
            "grc",
            ("bible",),
            "Late fourth or early fifth century CE",
            "A Greek and Latin manuscript of the Gospels and Acts.",
            "MS-NN-00002-00041",
            "p0120",
        ),
        _Manuscript(
            id="vatican-vat-gr-1209",
            title="Codex Vaticanus",
            institution="Biblioteca Apostolica Vaticana",
            shelfmark="Vat.gr.1209",
            language="grc",
            collections=("bible",),
            date="Fourth century CE",
            description="The Vatican Library's digitized Greek Bible manuscript.",
            catalog_url=f"https://digi.vatlib.it/view/{_VAT_ID}/0050",
            manifest_url=f"https://digi.vatlib.it/iiif/{_VAT_ID}/manifest.json",
            provider="vatican",
            object_key=_VAT_ID,
            attribution="Images Copyright Biblioteca Apostolica Vaticana.",
            rights_url=f"https://digi.vatlib.it/view/{_VAT_ID}/0050",
            terms_url=f"https://digi.vatlib.it/view/{_VAT_ID}/0050",
            rights_note="Personal viewing. Use the Vatican Library viewer for its own download and permission options.",
            use_limits=_PREVIEW,
            default_folio_id="p0050",
        ),
        _Manuscript(
            id="met-tashkent-quran",
            title="Folio from the Tashkent Qur’an",
            institution="The Metropolitan Museum of Art",
            shelfmark="2004.87",
            language="ar",
            collections=("quran",),
            date="Late eighth to early ninth century CE",
            description="A parchment Qur’an folio in early Kufic script, catalogued as part of the Tashkent Qur’an.",
            catalog_url="https://www.metmuseum.org/art/collection/search/454661",
            manifest_url="https://collectionapi.metmuseum.org/public/collection/v1/objects/454661",
            provider="met",
            object_key="454661",
            attribution="The Metropolitan Museum of Art. Purchase, Lila Acheson Wallace Gift, 2004. Open Access.",
            rights_url=_MET_TERMS,
            terms_url=_MET_TERMS,
            rights_note="The Met identifies this object image as public domain under its CC0 Open Access policy.",
            use_limits=_OPEN_ACCESS,
            default_folio_id="primary",
        ),
    )
}


@dataclass(frozen=True, slots=True)
class _Folio:
    id: str
    label: str
    index: int
    canvas_id: str
    width: int | None
    height: int | None
    source_url: str
    preview_url: str
    save_url: str | None
    use_limits: UseLimits

    def metadata(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "index": self.index,
            "canvas_id": self.canvas_id,
            "width": self.width,
            "height": self.height,
            "source_url": self.source_url,
            "use_limits": asdict(self.use_limits),
        }


@dataclass(frozen=True, slots=True)
class FolioImage:
    data: bytes
    media_type: str
    width: int
    height: int
    sha256: str
    image_url: str
    manuscript: dict
    folio: dict
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class _Record:
    manuscript: _Manuscript
    folios: tuple[_Folio, ...]
    manifest_sha256: str


_CACHE: dict[str, tuple[float, _Record]] = {}


def list_manuscripts(q: str | None = None, language: str | None = None) -> list[dict]:
    terms = (q or "").casefold().split()
    language = (language or "").casefold().strip()
    language = {"hebrew": "he", "greek": "grc", "arabic": "ar"}.get(language, language)
    items = []
    for entry in _CATALOG.values():
        text = " ".join(
            (
                entry.title,
                entry.institution,
                entry.shelfmark,
                entry.language,
                *entry.collections,
                entry.description,
            )
        ).casefold()
        if (not language or language == entry.language) and all(term in text for term in terms):
            items.append(entry.metadata())
    return items


def _catalog_entry(manuscript_id: str) -> _Manuscript:
    entry = _CATALOG.get(manuscript_id)
    if entry is None:
        raise APIError(404, "unknown_manuscript", "This manuscript is outside the current catalog.")
    return entry


def _path_match(url, host, pattern, *, legacy_http=False):
    if not isinstance(url, str) or len(url) > 600 or any(ord(char) < 33 for char in url):
        return None
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if (
        parsed.netloc != host
        or parsed.scheme not in ({"http", "https"} if legacy_http else {"https"})
        or parsed.query
        or parsed.fragment
    ):
        return None
    return re.fullmatch(pattern, parsed.path)


async def _fetch(url: str, *, image: bool) -> bytes:
    cap = _MAX_IMAGE_BYTES if image else _MAX_MANIFEST_BYTES
    accept = "image/jpeg,image/png,image/webp" if image else "application/ld+json,application/json"
    try:
        async with asyncio.timeout(25):
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(18, connect=8),
                follow_redirects=False,
                trust_env=False,
                headers={
                    "Accept": accept,
                    "Accept-Encoding": "identity",
                    "User-Agent": _USER_AGENT,
                },
            ) as client:
                async with client.stream("GET", url) as response:
                    if response.status_code in {401, 403, 451}:
                        raise APIError(
                            403,
                            "manuscript_access_restricted",
                            "The institution restricted this request. Open its catalog to review access.",
                        )
                    if response.status_code != 200:
                        raise APIError(
                            502,
                            "manuscript_unavailable",
                            "The institution could not serve this resource.",
                        )
                    if response.headers.get("content-encoding", "identity").lower() != "identity":
                        raise APIError(
                            502,
                            "invalid_manuscript_response",
                            "The institution returned an unsupported encoding.",
                        )
                    media_type = (
                        response.headers.get("content-type", "").split(";", 1)[0].lower().strip()
                    )
                    allowed = (
                        {"image/jpeg", "image/jpg", "image/png", "image/webp"}
                        if image
                        else {"application/json", "application/ld+json"}
                    )
                    if media_type not in allowed:
                        raise APIError(
                            502,
                            "invalid_manuscript_response",
                            "The institution returned an unexpected media type.",
                        )
                    declared = response.headers.get("content-length")
                    if declared is not None and (
                        not declared.isascii()
                        or not declared.isdecimal()
                        or len(declared) > 10
                        or int(declared) > cap
                    ):
                        raise APIError(
                            413,
                            "manuscript_resource_too_large",
                            "The institutional resource exceeds the size limit.",
                        )
                    data = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        if len(data) + len(chunk) > cap:
                            raise APIError(
                                413,
                                "manuscript_resource_too_large",
                                "The institutional resource exceeds the size limit.",
                            )
                        data.extend(chunk)
                    return bytes(data)
    except (httpx.TimeoutException, TimeoutError):
        raise APIError(
            504, "manuscript_timeout", "The institution did not respond before the timeout."
        ) from None
    except httpx.HTTPError:
        raise APIError(
            502, "manuscript_unavailable", "The institution could not be reached."
        ) from None


def _label(value, fallback):
    if not isinstance(value, str):
        return fallback
    return " ".join(value.replace("\x00", "").split())[:160] or fallback


def _dimension(value):
    return value if type(value) is int and 0 < value <= 100_000 else None


def _cc_by_nc(value):
    return isinstance(value, str) and (
        _CC_BY_NC in value or re.search(r"\bCC BY-NC 4\.0\b", value, re.IGNORECASE) is not None
    )


def _image_service(entry, canvas_id, service_id):
    """Return a folio key, official viewer URL and verified IIIF service URL."""
    if entry.provider == "bodleian":
        match = _path_match(
            canvas_id, "iiif.bodleian.ox.ac.uk", rf"/iiif/canvas/({_UUID_PATTERN})\.json"
        )
        if match and _path_match(service_id, "iiif.bodleian.ox.ac.uk", f"/iiif/image/{match[1]}"):
            return match[1], f"{entry.catalog_url}surfaces/{match[1]}/", service_id
    elif entry.provider == "cambridge":
        code = re.escape(entry.object_key)
        match = _path_match(
            canvas_id,
            "cudl.lib.cam.ac.uk",
            rf"/iiif/{code}/canvas/([1-9][0-9]{{0,3}})",
            legacy_http=True,
        )
        if match:
            number = int(match[1])
            volume, image_number = 0, number
            if entry.object_key == "MS-NN-00002-00041":
                # Bezae's second volume starts at canvas 328. The institution
                # restarts its image-file counter within that volume.
                volume, image_number = (1, number) if number <= 327 else (2, number - 327)
            if _path_match(
                service_id,
                "images.lib.cam.ac.uk",
                rf"/iiif/{code}-{volume:03d}-{image_number:05d}\.jp2",
            ):
                return (
                    f"p{number:04d}",
                    f"https://cudl.lib.cam.ac.uk/view/{entry.object_key}/{number}",
                    service_id,
                )
    elif entry.provider == "vatican":
        code = re.escape(entry.object_key)
        match = _path_match(canvas_id, "digi.vatlib.it", rf"/iiif/{code}/canvas/p([0-9]{{4}})")
        if match and _path_match(
            service_id,
            "digi.vatlib.it",
            rf"/iiifimage/{code}/Vat\.gr\.1209_{match[1]}(?:_[A-Za-z0-9_-]+)?\.jp2",
        ):
            return (
                "p" + match[1],
                f"https://digi.vatlib.it/view/{entry.object_key}/{match[1]}",
                service_id,
            )
    return None


def _parse_iiif(entry, document):
    identifiers = {entry.manifest_url}
    if entry.provider == "cambridge":
        identifiers.add(entry.manifest_url.replace("https://", "http://", 1))
    identity = document.get("@id")
    if not isinstance(identity, str) or identity not in identifiers:
        raise APIError(
            502,
            "invalid_manuscript_manifest",
            "The returned manifest has a different catalog identity.",
        )
    sequences = document.get("sequences")
    sequence = sequences[0] if isinstance(sequences, list) and sequences else None
    canvases = sequence.get("canvases") if isinstance(sequence, dict) else None
    if not isinstance(canvases, list) or not 0 < len(canvases) <= _MAX_FOLIOS:
        raise APIError(
            502, "invalid_manuscript_manifest", "The institution returned an invalid folio list."
        )
    if entry.use_limits.local_storage:
        license_value = (
            document.get("license") or document.get("rights") or document.get("attribution")
        )
        if not _cc_by_nc(license_value):
            entry = replace(
                entry,
                use_limits=_PREVIEW,
                rights_url=entry.terms_url,
                rights_note="Review the institution’s current use terms before saving a copy.",
            )
    folios = []
    seen = set()
    for index, canvas in enumerate(canvases, 1):
        if not isinstance(canvas, dict):
            continue
        images = canvas.get("images")
        annotation = images[0] if isinstance(images, list) and len(images) == 1 else None
        resource = annotation.get("resource") if isinstance(annotation, dict) else None
        service = resource.get("service") if isinstance(resource, dict) else None
        canvas_id = canvas.get("@id")
        verified = (
            _image_service(entry, canvas_id, service.get("@id"))
            if isinstance(service, dict)
            else None
        )
        if verified is None:
            continue
        folio_id, source_url, service_id = verified
        if folio_id in seen:
            raise APIError(
                502,
                "invalid_manuscript_manifest",
                "The institution returned duplicate folio identities.",
            )
        seen.add(folio_id)
        width = _dimension(canvas.get("width")) or _dimension(resource.get("width"))
        height = _dimension(canvas.get("height")) or _dimension(resource.get("height"))
        preview_width, save_width = min(width or 1200, 1200), min(width or 2500, 2500)
        limits = entry.use_limits
        declared = [
            value
            for item in (canvas, resource)
            for key in ("rights", "license")
            if (value := item.get(key)) is not None
        ]
        if limits.local_storage and any(not _cc_by_nc(value) for value in declared):
            limits = _PREVIEW
        folios.append(
            _Folio(
                id=folio_id,
                label=_label(canvas.get("label"), f"Image {index}"),
                index=index,
                canvas_id=canvas_id,
                width=width,
                height=height,
                source_url=source_url,
                preview_url=f"{service_id}/full/{preview_width},/0/default.jpg",
                save_url=f"{service_id}/full/{save_width},/0/default.jpg"
                if limits.local_storage
                else None,
                use_limits=limits,
            )
        )
    return entry, tuple(folios)


def _met_image(url, size):
    return (
        _path_match(
            url, "images.metmuseum.org", rf"/CRDImages/is/{size}/[A-Za-z0-9_.-]+\.[jJ][pP][gG]"
        )
        is not None
    )


def _parse_met(entry, document):
    if (
        document.get("objectID") != int(entry.object_key)
        or document.get("accessionNumber") != entry.shelfmark
        or document.get("objectURL") != entry.catalog_url
    ):
        raise APIError(
            502,
            "invalid_manuscript_manifest",
            "The returned record has a different catalog identity.",
        )
    if document.get("isPublicDomain") is not True:
        raise APIError(
            403,
            "manuscript_access_restricted",
            "The current catalog record does not grant Open Access to this image.",
        )
    primary = document.get("primaryImage")
    thumbnail = document.get("primaryImageSmall")
    if not _met_image(primary, "original"):
        return entry, ()
    if not _met_image(thumbnail, "web-large"):
        thumbnail = primary
    folios = [
        _Folio(
            "primary",
            "Primary catalog image",
            1,
            entry.catalog_url + "#primary-image",
            None,
            None,
            entry.catalog_url,
            thumbnail,
            primary,
            _OPEN_ACCESS,
        )
    ]
    extra = document.get("additionalImages")
    seen = {primary}
    for url in extra[:15] if isinstance(extra, list) else []:
        if not _met_image(url, "original") or url in seen:
            continue
        seen.add(url)
        folio_id = "image-" + hashlib.sha256(url.encode()).hexdigest()[:16]
        index = len(folios) + 1
        folios.append(
            _Folio(
                folio_id,
                f"Catalog image {index}",
                index,
                entry.catalog_url + "#" + folio_id,
                None,
                None,
                entry.catalog_url,
                url,
                url,
                _OPEN_ACCESS,
            )
        )
    return entry, tuple(folios)


async def _load_record(entry: _Manuscript, *, fresh=False) -> _Record:
    cached = _CACHE.get(entry.id)
    if not fresh and cached is not None and cached[0] > time.monotonic():
        return cached[1]
    data = await _fetch(entry.manifest_url, image=False)
    try:
        document = json.loads(data)
    except (ValueError, RecursionError):
        raise APIError(
            502, "invalid_manuscript_manifest", "The institution returned unreadable catalog data."
        ) from None
    if not isinstance(document, dict):
        raise APIError(
            502, "invalid_manuscript_manifest", "The institution returned unreadable catalog data."
        )
    manuscript, folios = (
        _parse_met(entry, document) if entry.provider == "met" else _parse_iiif(entry, document)
    )
    if not folios:
        raise APIError(
            502,
            "manuscript_folios_unavailable",
            "No supported scans were available from this catalog record.",
        )
    if manuscript.default_folio_id not in {folio.id for folio in folios}:
        manuscript = replace(manuscript, default_folio_id=folios[0].id)
    record = _Record(manuscript, folios, hashlib.sha256(data).hexdigest())
    _CACHE[entry.id] = (time.monotonic() + _CACHE_SECONDS, record)
    return record


async def list_folios(manuscript_id: str) -> dict:
    record = await _load_record(_catalog_entry(manuscript_id))
    return {
        "manuscript": record.manuscript.metadata(),
        "items": [folio.metadata() for folio in record.folios],
        "manifest_sha256": record.manifest_sha256,
    }


def _inspect_image(data: bytes):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if (
                    image.format not in {"JPEG", "PNG", "WEBP"}
                    or getattr(image, "n_frames", 1) != 1
                ):
                    raise ValueError("Unsupported raster image")
                width, height = image.size
                if not 0 < width * height <= _MAX_IMAGE_PIXELS:
                    raise APIError(
                        413,
                        "manuscript_resource_too_large",
                        "The folio exceeds the image pixel limit.",
                    )
                media_type = Image.MIME[image.format]
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                image.load()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise APIError(
            502, "invalid_manuscript_image", "The institution returned an invalid raster image."
        ) from None
    return media_type, width, height


async def fetch_folio(manuscript_id: str, folio_id: str, *, preview: bool) -> FolioImage:
    entry = _catalog_entry(manuscript_id)
    if not isinstance(folio_id, str) or not re.fullmatch(r"[a-zA-Z0-9-]{1,64}", folio_id):
        raise APIError(
            404, "unknown_manuscript_folio", "This folio is outside the current catalog record."
        )
    if not preview and not entry.use_limits.local_storage:
        raise APIError(
            403,
            "manuscript_save_restricted",
            "Use the institution’s viewer for its download options.",
        )
    record = await _load_record(entry, fresh=not preview)
    folio = next((item for item in record.folios if item.id == folio_id), None)
    if folio is None:
        raise APIError(
            404, "unknown_manuscript_folio", "This folio is outside the current catalog record."
        )
    url = folio.preview_url if preview else folio.save_url
    if url is None or (preview and not folio.use_limits.preview):
        raise APIError(
            403,
            "manuscript_save_restricted",
            "Use the institution’s viewer for its access options.",
        )
    data = await _fetch(url, image=True)
    media_type, width, height = await asyncio.to_thread(_inspect_image, data)
    return FolioImage(
        data=data,
        media_type=media_type,
        width=width,
        height=height,
        sha256=hashlib.sha256(data).hexdigest(),
        image_url=url,
        manuscript=replace(record.manuscript, use_limits=folio.use_limits).metadata(),
        folio=folio.metadata(),
        manifest_sha256=record.manifest_sha256,
    )
