"""Trusted parallel passages across the pinned starter editions.

Reference matching preserves the editions' original stored wording. The compact
Hebrew/English verse ranges are adapted from the Open Scriptures Hebrew Bible
VerseMap.xml at 65214d2bdf57f01feb4822c22c5b0d4de032891f, CC BY 4.0.
Original work of the Open Scriptures Hebrew Bible available at
https://github.com/openscriptures/morphhb. Ambiguous and partial pairs are held
out. See docs/development/parallel-reading.md for scope and attribution.
"""

import re
import unicodedata
from collections import defaultdict
from typing import NamedTuple
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from compass.corpus import STARTERS, SessionDependency, citation_dto
from compass.errors import APIError
from compass.models import Edition, Passage, Source

# OSIS book key, canonical name, and edition-specific aliases.
_BOOK_ROWS = """\
Gen|Genesis|Gn
Exod|Exodus|Exo
Lev|Leviticus
Num|Numbers
Deut|Deuteronomy|Deu
Josh|Joshua|Jos
Judg|Judges|Jdg
Ruth|Ruth|Rut
1Sam|1 Samuel|1 Sa|1SA
2Sam|2 Samuel|2 Sa|2SA
1Kgs|1 Kings|1 Ki|1KI
2Kgs|2 Kings|2 Ki|2KI
1Chr|1 Chronicles|1 Ch
2Chr|2 Chronicles|2 Ch
Ezra|Ezra|Ezr
Neh|Nehemiah
Esth|Esther|Est
Job|Job
Ps|Psalms|Psalm|Psa
Prov|Proverbs|Pro
Eccl|Ecclesiastes|Ecc|Qoheleth
Song|Song of Songs|Song of Solomon|Canticles|Sng|Cant
Isa|Isaiah
Jer|Jeremiah
Lam|Lamentations
Ezek|Ezekiel|Eze|Ezk
Dan|Daniel
Hos|Hosea
Joel|Joel|Jol
Amos|Amos|Amo
Obad|Obadiah|Oba
Jonah|Jonah|Jon
Mic|Micah
Nah|Nahum|Nam
Hab|Habakkuk
Zeph|Zephaniah|Zep
Hag|Haggai
Zech|Zechariah|Zec
Mal|Malachi
Matt|Matthew|Mat|Mt
Mark|Mark|Mrk|Mk
Luke|Luke|Luk|Lk
John|John|Jhn|Jn
Acts|Acts|Act
Rom|Romans
1Cor|1 Corinthians|1 Co
2Cor|2 Corinthians|2 Co
Gal|Galatians
Eph|Ephesians
Phil|Philippians|Php
Col|Colossians
1Thess|1 Thessalonians|1 Th
2Thess|2 Thessalonians|2 Th
1Tim|1 Timothy|1 Ti
2Tim|2 Timothy|2 Ti
Titus|Titus|Tit
Phlm|Philemon|Phm
Heb|Hebrews
Jas|James
1Pet|1 Peter|1 Pe
2Pet|2 Peter|2 Pe
1John|1 John|1 Jn|1JN
2John|2 John|2 Jn|2JN
3John|3 John|3 Jn|3JN
Jude|Jude|Jud
Rev|Revelation|Revelation of John|Apocalypse
"""


def _book_key(text: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKC", text).casefold() if char.isalnum())


def _book_aliases() -> tuple[dict[str, tuple[str, ...]], dict[str, str]]:
    names, lookup = {}, {}
    numerals = {"1": "I", "2": "II", "3": "III"}
    for row in _BOOK_ROWS.splitlines():
        code, *aliases = row.split("|")
        names[code] = tuple(
            dict.fromkeys(
                [*aliases, code]
                + [
                    numerals[alias[0]] + " " + alias[1:].strip()
                    for alias in aliases
                    if alias[0] in numerals
                ]
            )
        )
        for alias in names[code]:
            lookup[_book_key(alias)] = code
    return names, lookup


_BOOK_NAMES, _BOOK_LOOKUP = _book_aliases()
_TORAH_BOOKS = frozenset(tuple(_BOOK_NAMES)[:5])
_HEBREW_BOOKS = frozenset(tuple(_BOOK_NAMES)[:39])
_GREEK_BOOKS = frozenset(tuple(_BOOK_NAMES)[39:])
_HEBREW_STARTERS = {"uxlc-he-torah", "uxlc-he-tanakh-rest"}
_QURAN_STARTERS = {"pickthall-en", "tanzil-uthmani-ar"}
_ORIGINAL_STARTERS = _HEBREW_STARTERS | {"sblgnt-grc", "tanzil-uthmani-ar"}
_TRUSTED_STARTERS = _ORIGINAL_STARTERS | {"jps-1917-torah", "kjv-1769", "pickthall-en"}
_QURAN_PREFIXES = {"", "quran", "koran", "sura", "surah", "القرآن", "سورة"}
_REF_PATTERN = re.compile(
    r"(?:(?P<book>.+?)[.\s]+)?(?P<chapter>\d{1,3})\s*[:.]\s*(?P<verse>\d{1,3})"
)
_MAX_ANCHORS = 9


class VerseReference(NamedTuple):
    book: str | None
    chapter: int
    verse: int


def normalize_reference(reference: str) -> VerseReference | None:
    """Read a single chapter/verse address while retaining its canonical book identity."""
    match = _REF_PATTERN.fullmatch(unicodedata.normalize("NFKC", reference).strip())
    if match is None:
        return None
    label = _book_key(match["book"] or "")
    chapter, verse = int(match["chapter"]), int(match["verse"])
    if not chapter or not verse:
        return None
    if label in _QURAN_PREFIXES:
        return VerseReference(None, chapter, verse) if chapter <= 114 and verse <= 286 else None
    book = _BOOK_LOOKUP.get(label)
    return VerseReference(book, chapter, verse) if book else None


# One-to-one WLC => KJV differences. Each line gives a Hebrew verse range and
# the first English verse. Known partial or non-bijective rows are listed below.
_WLC_SPANS = """\
Gen 32:1-1 31:55
Gen 32:2-33 32:1
Exod 7:26-29 8:1
Exod 8:1-28 8:5
Exod 21:37-37 22:1
Exod 22:1-30 22:2
Lev 5:20-26 6:1
Lev 6:1-23 6:8
Num 17:1-15 16:36
Num 17:16-28 17:1
Num 25:19-19 26:1
Num 30:1-1 29:40
Num 30:2-17 30:1
Deut 13:1-1 12:32
Deut 13:2-19 13:1
Deut 23:1-1 22:30
Deut 23:2-26 23:1
Deut 28:69-69 29:1
Deut 29:1-28 29:2
1Sam 21:1-1 20:42
1Sam 21:2-16 21:1
1Sam 24:1-1 23:29
1Sam 24:2-23 24:1
2Sam 19:1-1 18:33
2Sam 19:2-44 19:1
1Kgs 5:1-14 4:21
1Kgs 5:15-32 5:1
1Kgs 22:45-54 22:44
2Kgs 12:1-1 11:21
2Kgs 12:2-22 12:1
Isa 8:23-23 9:1
Isa 9:1-20 9:2
Isa 64:1-11 64:2
Jer 8:23-23 9:1
Jer 9:1-25 9:2
Ezek 21:1-5 20:45
Ezek 21:6-37 21:1
Hos 2:1-2 1:10
Hos 2:3-25 2:1
Hos 12:1-1 11:12
Hos 12:2-15 12:1
Hos 14:1-1 13:16
Hos 14:2-10 14:1
Joel 3:1-5 2:28
Joel 4:1-21 3:1
Jonah 2:1-1 1:17
Jonah 2:2-11 2:1
Mic 4:14-14 5:1
Mic 5:1-14 5:2
Nah 2:1-1 1:15
Nah 2:2-14 2:1
Zech 2:1-4 1:18
Zech 2:5-17 2:1
Mal 3:19-24 4:1
Ps 3:2-9 3:1
Ps 4:2-9 4:1
Ps 5:2-13 5:1
Ps 6:2-11 6:1
Ps 7:2-18 7:1
Ps 8:2-10 8:1
Ps 9:2-21 9:1
Ps 12:2-9 12:1
Ps 13:2-5 13:1
Ps 18:2-51 18:1
Ps 19:2-15 19:1
Ps 20:2-10 20:1
Ps 21:2-14 21:1
Ps 22:2-32 22:1
Ps 30:2-13 30:1
Ps 31:2-25 31:1
Ps 34:2-23 34:1
Ps 36:2-13 36:1
Ps 38:2-23 38:1
Ps 39:2-14 39:1
Ps 40:2-18 40:1
Ps 41:2-14 41:1
Ps 42:2-12 42:1
Ps 44:2-27 44:1
Ps 45:2-18 45:1
Ps 46:2-12 46:1
Ps 47:2-10 47:1
Ps 48:2-15 48:1
Ps 49:2-21 49:1
Ps 51:4-21 51:2
Ps 52:4-11 52:2
Ps 53:2-7 53:1
Ps 54:4-9 54:2
Ps 55:2-24 55:1
Ps 56:2-14 56:1
Ps 57:2-12 57:1
Ps 58:2-12 58:1
Ps 59:2-18 59:1
Ps 60:4-14 60:2
Ps 61:2-9 61:1
Ps 62:2-13 62:1
Ps 63:2-12 63:1
Ps 64:2-11 64:1
Ps 65:2-14 65:1
Ps 67:2-8 67:1
Ps 68:2-36 68:1
Ps 69:2-37 69:1
Ps 70:2-6 70:1
Ps 75:2-11 75:1
Ps 76:2-13 76:1
Ps 77:2-21 77:1
Ps 80:2-20 80:1
Ps 81:2-17 81:1
Ps 83:2-19 83:1
Ps 84:2-13 84:1
Ps 85:2-14 85:1
Ps 88:2-19 88:1
Ps 89:2-53 89:1
Ps 92:2-16 92:1
Ps 102:2-29 102:1
Ps 108:2-14 108:1
Ps 140:2-14 140:1
Ps 142:2-8 142:1
Job 40:25-32 41:1
Job 41:1-26 41:9
Song 7:1-1 6:13
Song 7:2-14 7:1
Eccl 4:17-17 5:1
Eccl 5:1-19 5:2
Dan 3:31-33 4:1
Dan 4:1-34 4:4
Dan 6:1-1 5:31
Dan 6:2-29 6:1
Neh 3:33-38 4:1
Neh 4:1-17 4:7
Neh 7:68-72 7:69
Neh 10:1-1 9:38
Neh 10:2-40 10:1
1Chr 5:27-41 6:1
1Chr 6:1-66 6:16
1Chr 12:5-41 12:4
2Chr 1:18-18 2:1
2Chr 2:1-17 2:2
2Chr 13:23-23 14:1
2Chr 14:1-14 14:2
"""
_WLC_BLOCKED = (
    "1Kgs.18.34 1Kgs.20.3 1Kgs.22.21 1Kgs.22.44 Isa.63.19 "
    "Ps.13.6 Ps.51.2 Ps.51.3 Ps.52.2 Ps.52.3 Ps.54.2 Ps.54.3 Ps.60.2 Ps.60.3"
)
_KJV_BLOCKED = (
    "1Kgs.18.33 1Kgs.20.2 1Kgs.22.22 1Kgs.22.43 Isa.64.1 "
    "Ps.13.5 Ps.13.6 Ps.51.1 Ps.52.1 Ps.54.1 Ps.60.1"
)


def _verse_maps() -> tuple[dict[VerseReference, VerseReference], dict[VerseReference, VerseReference]]:
    hebrew_to_english = {}
    for line in _WLC_SPANS.splitlines():
        book, hebrew, english = line.split()
        hebrew_chapter, verse_range = hebrew.split(":")
        first, last = map(int, verse_range.split("-"))
        english_chapter, english_first = map(int, english.split(":"))
        for verse in range(first, last + 1):
            hebrew_to_english[VerseReference(book, int(hebrew_chapter), verse)] = VerseReference(
                book, english_chapter, english_first + verse - first
            )
    return hebrew_to_english, {target: source for source, target in hebrew_to_english.items()}


_WLC_TO_KJV, _KJV_TO_WLC = _verse_maps()
_HEBREW_BLOCKED = frozenset(normalize_reference(ref) for ref in _WLC_BLOCKED.split())
_ENGLISH_BLOCKED = frozenset(normalize_reference(ref) for ref in _KJV_BLOCKED.split())
_NUMBERING_CHAPTERS = {
    (ref.book, ref.chapter)
    for ref in {*_WLC_TO_KJV, *_KJV_TO_WLC, *_HEBREW_BLOCKED, *_ENGLISH_BLOCKED}
    if ref is not None
}

# Editions differ in verse divisions and inclusion of editorial variant blocks
# at these references. The reader may compare them, while chat uses verified
# single-verse pairs only.
_GREEK_COMPARISONS = {
    *(VerseReference("Mark", 16, verse) for verse in range(9, 21)),
    VerseReference("John", 7, 53),
    *(VerseReference("John", 8, verse) for verse in range(1, 12)),
    VerseReference("Luke", 22, 43),
    VerseReference("Luke", 22, 44),
    VerseReference("Luke", 23, 34),
    VerseReference("Acts", 19, 40),
    VerseReference("Rom", 16, 24),
    *(VerseReference("2Cor", 13, verse) for verse in range(12, 15)),
    VerseReference("3John", 1, 14),
    VerseReference("3John", 1, 15),
    VerseReference("1John", 5, 7),
    VerseReference("1John", 5, 8),
    VerseReference("Rev", 12, 18),
    VerseReference("Rev", 13, 1),
}

_SAME_NOTE = "The stored editions share this verse address. Wording and textual variants may differ."
_MAPPED_NOTE = "The Hebrew and English verse numbers differ here. A documented WLC/KJV map links these verse addresses."
_COMPARE_NOTE = "Compare these readings independently. Their shared number does not establish a one-to-one textual correspondence."


def _in_scope(starter_id: str, reference: VerseReference) -> bool:
    if starter_id in _QURAN_STARTERS:
        return reference.book is None
    if starter_id in {"jps-1917-torah", "uxlc-he-torah"}:
        return reference.book in _TORAH_BOOKS
    if starter_id == "uxlc-he-tanakh-rest":
        return reference.book in _HEBREW_BOOKS - _TORAH_BOOKS
    if starter_id == "sblgnt-grc":
        return reference.book in _GREEK_BOOKS
    return starter_id == "kjv-1769" and reference.book in _BOOK_NAMES


def _alignment(
    anchor_id: str, target_id: str, reference: VerseReference
) -> tuple[VerseReference, str, str] | None:
    if anchor_id == target_id or not (
        _in_scope(anchor_id, reference) and _in_scope(target_id, reference)
    ):
        return None
    if anchor_id in _QURAN_STARTERS:
        return reference, "same_reference", (
            "Both Tanzil editions use the same surah and ayah address. "
            "The Arabic text and published translation retain their own wording."
        )
    if "sblgnt-grc" in {anchor_id, target_id}:
        if reference in _GREEK_COMPARISONS:
            return reference, "compare_only", _COMPARE_NOTE
        return reference, "same_reference", _SAME_NOTE
    if anchor_id in _HEBREW_STARTERS or target_id in _HEBREW_STARTERS:
        hebrew_anchor = anchor_id in _HEBREW_STARTERS
        forward, reverse = (
            (_WLC_TO_KJV, _KJV_TO_WLC) if hebrew_anchor else (_KJV_TO_WLC, _WLC_TO_KJV)
        )
        if reference in (_HEBREW_BLOCKED if hebrew_anchor else _ENGLISH_BLOCKED):
            return None
        if reference in forward:
            return forward[reference], "mapped_reference", _MAPPED_NOTE
        if reference in reverse or reference in (
            _ENGLISH_BLOCKED if hebrew_anchor else _HEBREW_BLOCKED
        ):
            return None
        if (reference.book, reference.chapter) in _NUMBERING_CHAPTERS:
            return reference, "compare_only", _COMPARE_NOTE
    return reference, "same_reference", _SAME_NOTE


def _trusted_id(source: Source, edition: Edition) -> str | None:
    """Trust identity set by snapshot import, including its server-assigned hash."""
    provenance = source.provenance
    if not isinstance(provenance, dict):
        return None
    starter_id = provenance.get("starter_id")
    if not isinstance(starter_id, str) or starter_id not in _TRUSTED_STARTERS:
        return None
    starter = STARTERS.get(starter_id)
    if starter is None:
        return None
    if (
        provenance.get("snapshot_format") != "original_download"
        or provenance.get("content_sha256") != starter.sha256
        or provenance.get("snapshot_path") != f"sources/{starter.sha256}/original"
        or provenance.get("download_url") != starter.download_url
        or source.url != starter.source_url
        or source.source_type != starter.source_type
        or edition.title != starter.edition_title
        or edition.revision != starter.revision
        or edition.language != starter.language
        or edition.collection_memberships != list(starter.collections)
    ):
        return None
    return starter_id


def _reference_spellings(reference: VerseReference) -> set[str]:
    chapter, verse = reference.chapter, reference.verse
    if reference.book is None:
        value = f"{chapter}:{verse}"
        return {
            value,
            value.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")),
            value.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")),
        }
    return {
        value
        for name in _BOOK_NAMES[reference.book]
        for value in (f"{name} {chapter}:{verse}", f"{name}.{chapter}.{verse}")
    }


def _passage_rows(session: Session, passage_ids: list[UUID]) -> dict:
    return {
        passage.id: (passage, edition, source)
        for passage, edition, source in session.execute(
            select(Passage, Edition, Source)
            .join(Edition, Passage.edition_id == Edition.id)
            .join(Source, Edition.source_id == Source.id)
            .where(Passage.id.in_(passage_ids))
        )
    }


def _parallel_lookup(session: Session, anchors: list[tuple]) -> dict[UUID, list[dict]]:
    """Resolve all candidate addresses with one bounded indexed passage lookup."""
    profiles = {
        edition.id: (edition, source, starter_id)
        for edition, source in session.execute(
            select(Edition, Source)
            .join(Source, Edition.source_id == Source.id)
            .where(Source.provenance["starter_id"].astext.in_(_TRUSTED_STARTERS))
        )
        if (starter_id := _trusted_id(source, edition)) is not None
    }
    plans, spellings = defaultdict(list), defaultdict(set)
    for passage, edition, _source in anchors:
        anchor_profile = profiles.get(edition.id)
        reference = normalize_reference(passage.reference)
        if anchor_profile is None or reference is None:
            continue
        for target_edition_id, (_, _, target_id) in profiles.items():
            if target_edition_id == edition.id:
                continue
            match = _alignment(anchor_profile[2], target_id, reference)
            if match is None:
                continue
            target, alignment, note = match
            plans[passage.id].append((target_edition_id, target, alignment, note))
            spellings[target_edition_id].update(_reference_spellings(target))
    if not spellings:
        return {}
    found = defaultdict(list)
    conditions = [
        and_(Passage.edition_id == edition_id, Passage.reference.in_(values))
        for edition_id, values in spellings.items()
    ]
    for passage in session.scalars(select(Passage).where(or_(*conditions))):
        found[(passage.edition_id, normalize_reference(passage.reference))].append(passage)
    result = defaultdict(list)
    for anchor_id, choices in plans.items():
        for edition_id, reference, alignment, note in choices:
            matches = found[(edition_id, reference)]
            if len(matches) != 1:
                continue
            edition, source, _ = profiles[edition_id]
            result[anchor_id].append(
                {**citation_dto(matches[0], edition, source), "alignment": alignment,
                 "alignment_note": note}
            )
        result[anchor_id].sort(key=lambda item: (
            item["alignment"] == "compare_only",
            item["language"] == "en",
            item["edition_title"],
            item["passage_id"],
        ))
    return dict(result)


def parallel_passages(session: Session, passage_id: UUID) -> dict:
    rows = _passage_rows(session, [passage_id])
    row = rows.get(passage_id)
    if row is None:
        raise APIError(404, "not_found", "This passage was not found.")
    passage, edition, source = row
    parallels = _parallel_lookup(session, [row]).get(passage_id, [])
    warnings = []
    if _trusted_id(source, edition) is None:
        warnings.append("This edition has no verified parallel alignment profile.")
    elif not parallels:
        warnings.append(
            "No trusted companion is available among the imported editions for this verse. "
            "Coverage, an omitted verse or uncertain verse boundaries can leave a gap."
        )
    if any(item["alignment"] == "compare_only" for item in parallels):
        warnings.append("Comparison-only passages need manual review before treating them as equivalents.")
    return {"anchor": citation_dto(passage, edition, source), "parallels": parallels, "warnings": warnings}


def parallel_evidence(
    session: Session,
    anchors: list[dict],
    *,
    source_ids: list[UUID] | None = None,
    external_processing: bool = False,
    limit: int = 9,
) -> list[dict]:
    """Add at most one trusted opposite-kind companion for each selected anchor."""
    limit = min(limit, _MAX_ANCHORS)
    if limit <= 0:
        return []
    passage_ids = list(dict.fromkeys(UUID(str(item["passage_id"])) for item in anchors[:_MAX_ANCHORS]))
    if not passage_ids:
        return []
    rows = _passage_rows(session, passage_ids)
    allowed_ids = {str(value) for value in source_ids} if source_ids is not None else None

    def permitted(source_id, use_limits):
        return (
            (allowed_ids is None or str(source_id) in allowed_ids)
            and (
                not external_processing
                or (isinstance(use_limits, dict) and use_limits.get("external_processing") is True)
            )
        )

    allowed_rows = [
        rows[passage_id]
        for passage_id in passage_ids
        if passage_id in rows and permitted(rows[passage_id][2].id, rows[passage_id][2].use_limits)
    ]
    parallels = _parallel_lookup(session, allowed_rows)
    known = {str(passage_id) for passage_id in passage_ids}
    selected = {}
    for passage_id in passage_ids:
        if passage_id not in parallels:
            continue
        original = rows[passage_id][2].source_type == "original_text"
        companion_type = "translation" if original else "original_text"
        for item in parallels.get(passage_id, []):
            companion_id = item["passage_id"]
            if (
                item["alignment"] == "compare_only"
                or item["source_type"] != companion_type
                or companion_id in known
                or not permitted(item["source_id"], item["use_limits"])
            ):
                continue
            if companion_id in selected:
                selected[companion_id]["parallel_for"].append(str(passage_id))
            elif len(selected) < limit:
                selected[companion_id] = {**item, "parallel_for": [str(passage_id)]}
            else:
                continue
            break
    return list(selected.values())


router = APIRouter(prefix="/api/v1")


@router.get("/passages/{passage_id}/parallel")
def get_parallel_passages(passage_id: UUID, session: SessionDependency):
    return parallel_passages(session, passage_id)
