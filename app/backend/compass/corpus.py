"""Traceable text imports and lexical retrieval, with original bytes kept separately.

Only catalog starter URLs are fetched by this module. A user import's
URL is attribution metadata, never an instruction to fetch an arbitrary address.
Starter texts are identified electronic editions. Manuscript images are a separate workflow.
"""

import hashlib
import io
import json
import os
import re
import tempfile
import unicodedata
import zipfile
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator
from sqlalchemy import and_, func, insert, or_, select, text
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from compass.errors import APIError
from compass.models import Edition, Passage, Source

router = APIRouter(prefix="/api/v1", tags=["corpus"])

MAX_SNAPSHOT_BYTES = 20 * 1024 * 1024
MAX_PASSAGES = 40_000
MAX_TOTAL_TEXT_BYTES = 16 * 1024 * 1024
MAX_METADATA_BYTES = 64 * 1024
COLLECTIONS = frozenset({"torah", "bible", "quran"})
TORAH_BOOK_NAMES = ("Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy")
TORAH_BOOKS = frozenset(TORAH_BOOK_NAMES)
SCROLLMAPPER_REVISION = "59b18c5af5845728c275d5b7178ad0d024172b1f"
SCROLLMAPPER_RAW = (
    f"https://raw.githubusercontent.com/scrollmapper/bible_databases/{SCROLLMAPPER_REVISION}"
)
SBLGNT_COMMIT = "d7f35adca9ec410e1d1499c63b4dd989d76c8d4d"


class ImportModel(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


def require_utf8(value: str) -> str:
    if "\x00" in value:
        raise ValueError("NUL characters are not supported by PostgreSQL text fields.")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("Text must be valid Unicode.") from exc
    return value


class ImportedPassage(ImportModel):
    reference: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=50_000)

    @field_validator("reference", "text")
    @classmethod
    def readable_text(cls, value: str) -> str:
        require_utf8(value)
        if not value.strip():
            raise ValueError("References and passage text cannot be empty.")
        # Preserve text byte-for-byte after decoding; normalization is search-only.
        return value


class ImportedEdition(ImportModel):
    title: str = Field(min_length=1, max_length=300)
    language: str = Field(min_length=1, max_length=40)
    revision: str = Field(min_length=1, max_length=100)
    collection_memberships: list[Literal["torah", "bible", "quran"]] = Field(
        min_length=1, max_length=3
    )

    @field_validator("title", "language", "revision")
    @classmethod
    def metadata_text(cls, value: str) -> str:
        require_utf8(value)
        if not value.strip():
            raise ValueError("Edition metadata cannot be empty.")
        return value

    @field_validator("collection_memberships")
    @classmethod
    def unique_memberships(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class UseLimits(ImportModel):
    external_processing: StrictBool = False
    rights_note: str | None = Field(default=None, max_length=8000)

    @field_validator("rights_note")
    @classmethod
    def metadata_text(cls, value: str | None) -> str | None:
        return require_utf8(value) if value is not None else None


class CorpusImport(ImportModel):
    title: str = Field(min_length=1, max_length=300)
    url: str | None = Field(default=None, max_length=3000)
    source_type: str = Field(min_length=1, max_length=50)
    edition: ImportedEdition
    passages: list[ImportedPassage] = Field(min_length=1, max_length=MAX_PASSAGES)
    use_limits: UseLimits = Field(default_factory=UseLimits)
    provenance: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "source_type")
    @classmethod
    def metadata_text(cls, value: str) -> str:
        require_utf8(value)
        if not value.strip():
            raise ValueError("Source metadata cannot be empty.")
        return value

    @field_validator("url")
    @classmethod
    def attribution_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        require_utf8(value)
        try:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"https", "http"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
            ):
                raise ValueError("Use an HTTP(S) attribution URL without credentials.")
            parsed.port  # Validate malformed ports without contacting the host.
        except ValueError as exc:
            raise ValueError("Use a valid HTTP(S) attribution URL without credentials.") from exc
        return value

    @model_validator(mode="after")
    def bounded_unique_content(self):
        references = [passage.reference for passage in self.passages]
        if len(set(references)) != len(references):
            raise ValueError("Each reference must be unique within an edition.")
        if sum(len(passage.text.encode("utf-8")) for passage in self.passages) > MAX_TOTAL_TEXT_BYTES:
            raise ValueError("The edition exceeds the text size limit.")
        try:
            metadata = json.dumps(self.provenance, ensure_ascii=False, allow_nan=False).encode("utf-8")
        except (ValueError, UnicodeEncodeError, TypeError) as exc:
            raise ValueError("Provenance must be valid JSON metadata.") from exc
        if len(metadata) > MAX_METADATA_BYTES or b"\\u0000" in metadata:
            raise ValueError("Provenance exceeds the metadata limit or contains invalid text.")
        return self


@dataclass(frozen=True)
class Starter:
    id: str
    title: str
    edition_title: str
    language: str
    collections: tuple[str, ...]
    description: str
    download_url: str
    source_url: str
    licence_url: str
    sha256: str
    revision: str
    format: str
    passage_count: int
    rights_note: str
    provenance_note: str
    source_type: str = "translation"
    external_processing: bool = True
    verified_on: str = "2026-11-08"
    selection: str | None = None

    def metadata(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "language": self.language,
            "collections": list(self.collections),
            "description": self.description,
            "source_type": self.source_type,
            "url": self.source_url,
            "download_url": self.download_url,
            "revision": self.revision,
            "expected_passage_count": self.passage_count,
            "content_sha256": self.sha256,
            "rights_note": self.rights_note,
            "licence_url": self.licence_url,
            "external_processing": self.external_processing,
        }


UXLC_TORAH = Starter(
    id="uxlc-he-torah",
    title="UXLC 2.6 — Torah in Hebrew",
    edition_title="Unicode/XML Leningrad Codex 2.6 (Torah)",
    language="he",
    collections=("torah", "bible"),
    description=(
        "Genesis–Deuteronomy in the publisher's Full/Accents electronic text. "
        "Uses Hebrew Bible verse numbering. The Torah appears in both collections."
    ),
    download_url="https://www.tanach.us/TextFiles/Tanach.txt.zip",
    source_url="https://www.tanach.us/",
    licence_url="https://www.tanach.us/License.html",
    sha256="71d958aec48ec62d11240bc5d13e7a2234ee921c1d162bdd1664f09c4688e446",
    revision="UXLC 2.6 / build 27.7 (18 Oct 2026)",
    format="uxlc-full-accents-torah",
    passage_count=5853,
    rights_note=(
        "Tanach.us permits unrestricted viewing and copying of its biblical Hebrew text "
        "and requests attribution. Cite Unicode/XML Leningrad Codex 2.6, build 27.7, "
        "Tanach.us Inc., West Redding, CT, October 2026. The publisher has separate terms "
        "for site files and fonts."
    ),
    provenance_note=(
        "Official Tanach.us Full/Accents UTF-8 text archive of the Unicode/XML Leningrad "
        "Codex, an electronic transcription derived from WLC 4.20 and revised by Tanach.us. "
        "This Hebrew Bible edition contains Aramaic passages in parts of the Tanakh. The "
        "app reads exact verse payloads with cantillation, vocalization and transcription "
        "markers. The edition preserves the publisher's chapter and verse boundaries."
    ),
    source_type="original_text",
    external_processing=True,
    verified_on="2026-11-09",
    selection="Genesis–Deuteronomy only",
)


STARTERS = {
    "jps-1917-torah": Starter(
        id="jps-1917-torah",
        title="JPS 1917 Torah — English electronic edition",
        edition_title="JPS 1917 Torah (eBible electronic text)",
        language="en",
        collections=("torah", "bible"),
        description=(
            "Complete Genesis–Deuteronomy from a traceable Jewish English translation. "
            "Torah and Bible membership refers "
            "to the same text, not two independent witnesses."
        ),
        download_url="https://ebible.org/Scriptures/engjps_vpl.zip",
        source_url="https://ebible.org/engjps/",
        licence_url="https://ebible.org/find/show.php?id=engjps",
        sha256="fd75cfc7aca9591b4cab773e8a09a2cd53a7adc393110e5fd6561273462307d6",
        revision="1917 / eBible ENGJPS snapshot verified 2026-11-08",
        format="ebible-vpl-torah",
        passage_count=5852,
        rights_note=(
            "eBible identifies this Old JPS 1917 electronic edition as public domain. "
            "Retain the edition and electronic-source attribution. The local snapshot "
            "contains the full Tanakh VPL archive; only its five Torah books are indexed."
        ),
        provenance_note=(
            "Direct eBible ENGJPS BibleWorks verse-per-line download, identified by its "
            "download page as the Jewish Publication Society 1917 translation. The exact "
            "engjps_vpl.txt member is read in memory; SQL and other archive members are never "
            "executed or extracted. This is a translation, not a Hebrew manuscript or "
            "facsimile of the 1917 printed edition."
        ),
    ),
    "kjv-1769": Starter(
        id="kjv-1769",
        title="King James Version — complete English Bible",
        edition_title="KJV 1769 (Scrollmapper/CrossWire electronic text)",
        language="en",
        collections=("bible",),
        description=(
            "Complete 66-book English Bible from the labelled KJV electronic edition. "
            "This translation's wording and canon are identified, not treated as universal."
        ),
        download_url=f"{SCROLLMAPPER_RAW}/formats/json/KJV.json",
        source_url="https://github.com/scrollmapper/bible_databases/tree/"
        f"{SCROLLMAPPER_REVISION}/sources/en/KJV",
        licence_url="https://www.crosswire.org/sword/modules/ModInfo.jsp?modName=KJV",
        sha256="f0b09dc49dfb97bb84f03aae1fbf026485048c3cab31a7a41017e2d86ac1d11c",
        revision=f"1769 / electronic snapshot {SCROLLMAPPER_REVISION[:12]}",
        format="scrollmapper-bible",
        passage_count=31102,
        rights_note=(
            "The electronic KJV source is labelled GPL. CrossWire grants use of its text "
            "for any purpose and notes that rights to the underlying KJV text are held by "
            "the Crown of England. Preserve attribution/licence information; this import "
            "does not make a worldwide public-domain or unrestricted-redistribution claim."
        ),
        provenance_note=(
            "Pinned Scrollmapper JSON conversion of the CrossWire KJV electronic source. "
            "Only its verse text is indexed; Strong's numbers, cross-references, notes and "
            "morphology are not admitted as interpretive authority."
        ),
    ),
    "pickthall-en": Starter(
        id="pickthall-en",
        title="Quran — Pickthall English translation",
        edition_title="Pickthall English Quran (Tanzil electronic text)",
        language="en",
        collections=("quran",),
        description=(
            "Complete 114-surah translation by Mohammed Marmaduke William Pickthall. "
            "English translation, separate from the Arabic Quran; no hadith or tafsir pack."
        ),
        download_url="https://tanzil.net/trans/en.pickthall",
        source_url="https://tanzil.net/trans/en.pickthall",
        licence_url="https://tanzil.net/trans/",
        sha256="4aabbfa9d96796f5a6b0217d2c39dce1a3084f772bf6f2650e37082a774e3cc7",
        revision="Pickthall / Tanzil 2010-09-04 / snapshot verified 2026-11-08",
        format="tanzil-translation",
        passage_count=6236,
        rights_note=(
            "Tanzil supplies this translation download for non-commercial use. Imported "
            "for private personal research, including processing explicitly requested by "
            "the user. Retain translator and Tanzil attribution. This does not grant "
            "commercial redistribution, publication, model-training or other rights. "
            "See https://tanzil.net/trans/ for the host's terms and translation disclaimer."
        ),
        provenance_note=(
            "Direct Tanzil UTF-8 surah|ayah|text download. The source footer identifies "
            "Pickthall, English, en.pickthall and update date September 4, 2010. Tanzil "
            "itself cautions that translations are not replacements for the Arabic text."
        ),
    ),
    UXLC_TORAH.id: UXLC_TORAH,
    "uxlc-he-tanakh-rest": replace(
        UXLC_TORAH,
        id="uxlc-he-tanakh-rest",
        title="UXLC 2.6 — Tanakh Prophets and Writings",
        edition_title="Unicode/XML Leningrad Codex 2.6 (Prophets and Writings)",
        collections=("bible",),
        description=(
            "Prophets and Writings in Hebrew and Aramaic from the same UXLC edition as "
            "the Torah starter. Includes all 34 book files outside Genesis–Deuteronomy."
        ),
        format="uxlc-full-accents-rest",
        passage_count=17360,
        selection="Prophets and Writings, excluding Genesis–Deuteronomy",
    ),
    "sblgnt-grc": Starter(
        id="sblgnt-grc",
        title="SBLGNT 1.2 — Greek New Testament",
        edition_title="SBL Greek New Testament 1.2 (Holmes)",
        language="grc",
        collections=("bible",),
        description=(
            "Michael W. Holmes's Greek critical edition of the 27 New Testament books. "
            "Retains the publisher's punctuation, accents and editorial brackets."
        ),
        download_url=f"https://codeload.github.com/Faithlife/SBLGNT/zip/{SBLGNT_COMMIT}",
        source_url=f"https://github.com/Faithlife/SBLGNT/tree/{SBLGNT_COMMIT}",
        licence_url="https://sblgnt.com/license/",
        sha256="bcb9cfd8678a863be77c01641aab14c31515e7057852b5abfe0920aac73cbf56",
        revision=f"SBLGNT 1.2 / publisher commit {SBLGNT_COMMIT[:12]}",
        format="sblgnt-text-zip",
        passage_count=7939,
        rights_note=(
            "SBL Greek New Testament, edited by Michael W. Holmes. Copyright 2010 by the "
            "Society of Biblical Literature and Logos Bible Software. Creative Commons "
            "Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/. "
            "Retain attribution and a link to the source edition and licence."
        ),
        provenance_note=(
            "Publisher GitHub archive linked from the SBLGNT download site. The 27 text "
            "files under data/sblgnt/text supply the base text. Each stored passage keeps "
            "the exact tab-delimited Greek payload, including the editorial brackets "
            "around John 7:53–8:11 added in version 1.2. The separate apparatus stays in "
            "the original archive."
        ),
        source_type="original_text",
        external_processing=True,
        verified_on="2026-11-09",
        selection="Complete Greek New Testament base text",
    ),
    "tanzil-uthmani-ar": Starter(
        id="tanzil-uthmani-ar",
        title="Tanzil 1.1 — Uthmani Arabic Quran",
        edition_title="Tanzil Quran Text (Uthmani, Version 1.1)",
        language="ar",
        collections=("quran",),
        description=(
            "Complete Arabic Uthmani encoding of the Medina Mushaf, with pause, "
            "sajdah and rub-el-hizb marks."
        ),
        download_url=(
            "https://tanzil.net/pub/download/index.php?quranType=uthmani&outType=txt-2"
            "&marks=true&sajdah=true&rub=true&alef=true&tatweel=true&agree=true"
        ),
        source_url="https://tanzil.net/download/",
        licence_url="https://tanzil.net/docs/text_license",
        sha256="7f30c647331a61100ebf24a80507dc0fcdd9f2df97f1312b5b2dfcb982a7f326",
        revision="Tanzil Uthmani 1.1 / fully marked snapshot 2026-11-09",
        format="tanzil-uthmani-text",
        passage_count=6236,
        rights_note=(
            "Tanzil Quran Text (Uthmani, Version 1.1). Copyright (C) 2007-2026 Tanzil "
            "Project, as printed in the downloaded snapshot. Creative Commons Attribution "
            "3.0 and Tanzil's verbatim-copy terms. Attribute the Tanzil Project, retain its "
            "copyright notice and link to https://tanzil.net/. The app uses this original "
            "edition locally."
        ),
        provenance_note=(
            "Official Tanzil UTF-8 surah|ayah|text download with pause, sajdah and "
            "rub-el-hizb marks, superscript alefs and tatweel selected. The exact verse "
            "payloads are retained. The complete private download includes the publisher's "
            "copyright footer."
        ),
        source_type="original_text",
        external_processing=False,
        verified_on="2026-11-09",
        selection="Complete 114-surah Uthmani Arabic Quran",
    ),
}


def normalize_search_text(value: str, *, with_original_lexemes: bool = False) -> str:
    """Search derivative only: canonical Unicode compatibility, case and spacing."""
    normalized = " ".join(unicodedata.normalize("NFKC", value).casefold().split())
    if with_original_lexemes:
        return " ".join([normalized, *original_search_lexemes(value)])
    return normalized


ORIGINAL_SCRIPT = re.compile(r"[\u0370-\u03ff\u0590-\u06ff\u0750-\u077f\u08a0-\u08ff\u1f00-\u1fff]")
WORD = re.compile(r"[^\W_]+", re.UNICODE)


def original_search_lexemes(value: str) -> list[str]:
    """Use ASCII lexemes so PostgreSQL's simple parser can index them even under locale C."""
    folded = "".join(
        char for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.category(char).startswith("M") and char != "\u0640"
    ).replace("\u0671", "\u0627").casefold()
    lexemes = []
    for word in WORD.findall(folded):
        if len(word) <= 1 or not ORIGINAL_SCRIPT.search(word):
            continue
        encoded = word.encode("utf-8")
        if len(encoded) <= 512:
            lexemes.append("cmpx" + encoded.hex())
    return lexemes


def invalid_format() -> APIError:
    return APIError(422, "invalid_source_format", "The source snapshot has an invalid or unsupported format.")


def parse_bible_snapshot(raw: bytes, *, torah_only: bool = False) -> list[ImportedPassage]:
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise APIError(413, "source_too_large", "The source snapshot exceeds the import size limit.")
    try:
        document = json.loads(raw.decode("utf-8-sig"))
        books = document["books"]
        if not isinstance(books, list) or not 1 <= len(books) <= 100:
            raise ValueError("Invalid books.")
        passages = []
        seen_books = set()
        total_rows = 0
        for book in books:
            name = book["name"]
            if not isinstance(name, str) or name in seen_books or not 1 <= len(name) <= 80:
                raise ValueError("Invalid book name.")
            seen_books.add(name)
            chapters = book["chapters"]
            if not isinstance(chapters, list) or len(chapters) > 200:
                raise ValueError("Invalid chapters.")
            for chapter in chapters:
                number = chapter["chapter"]
                if type(number) is not int or not 1 <= number <= 200:
                    raise ValueError("Invalid chapter.")
                verses = chapter["verses"]
                if not isinstance(verses, list) or len(verses) > 200:
                    raise ValueError("Invalid verses.")
                for verse in verses:
                    total_rows += 1
                    if total_rows > MAX_PASSAGES:
                        raise ValueError("Too many rows.")
                    verse_number = verse["verse"]
                    if type(verse_number) is not int or not 1 <= verse_number <= 200:
                        raise ValueError("Invalid verse.")
                    if not torah_only or name in TORAH_BOOKS:
                        passages.append(ImportedPassage(
                            reference=f"{name} {number}:{verse_number}", text=verse["text"]
                        ))
        if not passages:
            raise ValueError("No passages.")
        if len({item.reference for item in passages}) != len(passages):
            raise ValueError("Duplicate reference.")
        return passages
    except (KeyError, IndexError, TypeError, ValueError, RecursionError) as exc:
        raise invalid_format() from exc


def parse_tanzil_snapshot(raw: bytes) -> list[ImportedPassage]:
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise APIError(413, "source_too_large", "The source snapshot exceeds the import size limit.")
    try:
        passages = []
        seen = set()
        for line in raw.decode("utf-8-sig").splitlines():
            if not line or line.startswith("#"):
                continue
            parts = line.split("|", 2)
            if len(parts) != 3:
                raise ValueError("Invalid row.")
            surah, ayah = int(parts[0]), int(parts[1])
            if not 1 <= surah <= 114 or not 1 <= ayah <= 286:
                raise ValueError("Invalid reference.")
            reference = f"{surah}:{ayah}"
            if reference in seen or len(passages) >= MAX_PASSAGES:
                raise ValueError("Duplicate or excess row.")
            seen.add(reference)
            passages.append(ImportedPassage(reference=reference, text=parts[2]))
        if not passages:
            raise ValueError("No passages.")
        return passages
    except (ValueError, TypeError) as exc:
        raise invalid_format() from exc


def parse_ebible_torah_snapshot(raw: bytes) -> list[ImportedPassage]:
    """Read one named VPL member in memory; never extract files or execute bundled SQL."""
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise APIError(413, "source_too_large", "The source snapshot exceeds the import size limit.")
    names = {"GEN": "Genesis", "EXO": "Exodus", "LEV": "Leviticus",
             "NUM": "Numbers", "DEU": "Deuteronomy"}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            if (
                len(members) > 20
                or len({member.filename for member in members}) != len(members)
                or sum(member.file_size for member in members) > MAX_SNAPSHOT_BYTES
                or any(member.flag_bits & 1 for member in members)
            ):
                raise ValueError("Unsupported archive.")
            member = archive.getinfo("engjps_vpl.txt")
            if member.file_size > MAX_TOTAL_TEXT_BYTES:
                raise ValueError("Oversized member.")
            with archive.open(member) as stream:
                expanded = stream.read(MAX_TOTAL_TEXT_BYTES + 1)
            if len(expanded) > MAX_TOTAL_TEXT_BYTES:
                raise ValueError("Oversized member.")
        passages = []
        seen = set()
        found_books = set()
        lines = expanded.decode("utf-8-sig").splitlines()
        if len(lines) > MAX_PASSAGES:
            raise ValueError("Too many rows.")
        for line in lines:
            if not line:
                continue
            match = re.fullmatch(r"([A-Z0-9]{3}) ([0-9]{1,3}):([0-9]{1,3}) (.+)", line)
            if match is None:
                raise ValueError("Invalid VPL row.")
            book, chapter, verse, verse_text = match.groups()
            if book not in names:
                continue
            found_books.add(book)
            reference = f"{names[book]} {int(chapter)}:{int(verse)}"
            if int(chapter) < 1 or int(verse) < 1 or reference in seen:
                raise ValueError("Invalid reference.")
            seen.add(reference)
            passages.append(ImportedPassage(reference=reference, text=verse_text))
        if found_books != set(names):
            raise ValueError("Incomplete Torah selection.")
        return passages
    except (ValueError, TypeError, KeyError, RuntimeError, zipfile.BadZipFile) as exc:
        raise invalid_format() from exc


UXLC_OTHER_BOOKS = (
    "Joshua", "Judges", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "Isaiah",
    "Jeremiah", "Ezekiel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah",
    "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi", "Psalms",
    "Proverbs", "Job", "Song of Songs", "Ruth", "Lamentations", "Ecclesiastes", "Esther",
    "Daniel", "Ezra", "Nehemiah", "1 Chronicles", "2 Chronicles",
)
SBLGNT_BOOKS = {
    "Matt": "Matthew", "Mark": "Mark", "Luke": "Luke", "John": "John", "Acts": "Acts",
    "Rom": "Romans", "1Cor": "1 Corinthians", "2Cor": "2 Corinthians", "Gal": "Galatians",
    "Eph": "Ephesians", "Phil": "Philippians", "Col": "Colossians", "1Thess": "1 Thessalonians",
    "2Thess": "2 Thessalonians", "1Tim": "1 Timothy", "2Tim": "2 Timothy", "Titus": "Titus",
    "Phlm": "Philemon", "Heb": "Hebrews", "Jas": "James", "1Pet": "1 Peter", "2Pet": "2 Peter",
    "1John": "1 John", "2John": "2 John", "3John": "3 John", "Jude": "Jude", "Rev": "Revelation",
}
UXLC_VERSE_LINE = re.compile(
    r"\u202b\xa0(?P<verse>[1-9][0-9\xa0]{2})\u05c3"
    r"(?P<chapter>[1-9][0-9\xa0]{2})\xa0(?P<text>.+)\u202c"
)
SBLGNT_VERSE_LINE = re.compile(
    r"(?P<book>[A-Za-z0-9]+) (?P<chapter>[1-9][0-9]{0,2}):(?P<verse>[1-9][0-9]{0,2})\t(?P<text>.+)"
)


def original_archive_texts(raw: bytes, members: list[str]):
    """Read explicitly named publisher text members in memory."""
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise APIError(413, "source_too_large", "The source snapshot exceeds the import size limit.")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if (
                len(entries) > 128
                or len({entry.filename for entry in entries}) != len(entries)
                or sum(entry.file_size for entry in entries) > MAX_SNAPSHOT_BYTES
                or any(entry.flag_bits & 1 for entry in entries)
            ):
                raise ValueError("Unsupported archive.")
            remaining = MAX_TOTAL_TEXT_BYTES
            for name in members:
                entry = archive.getinfo(name)
                if entry.is_dir() or entry.file_size > remaining:
                    raise ValueError("Oversized or invalid text member.")
                with archive.open(entry) as member:
                    data = member.read(remaining + 1)
                if len(data) != entry.file_size or len(data) > remaining:
                    raise ValueError("Invalid decompressed text size.")
                remaining -= len(data)
                yield data.decode("utf-8-sig")
    except (ValueError, OSError, KeyError, RuntimeError, zipfile.BadZipFile) as exc:
        raise invalid_format() from exc


def parse_uxlc_snapshot(raw: bytes, *, torah_only: bool) -> list[ImportedPassage]:
    books = TORAH_BOOK_NAMES if torah_only else UXLC_OTHER_BOOKS
    members = []
    for book in books:
        file_name = f"{book[2:]}_{book[0]}" if book[0].isdigit() else book.replace(" ", "_")
        members.append(f"TextFiles/{file_name}.txt")
    passages = []
    try:
        for book, content in zip(books, original_archive_texts(raw, members), strict=True):
            previous = (0, 0)
            for raw_line in content.split("\n"):
                line = raw_line.removesuffix("\r")
                if not line or line.startswith("\u202axxxx"):
                    continue
                match = UXLC_VERSE_LINE.fullmatch(line)
                if match is None:
                    raise ValueError("Invalid UXLC verse line.")
                chapter, verse = int(match["chapter"]), int(match["verse"])
                if (chapter, verse) <= previous or len(passages) >= MAX_PASSAGES:
                    raise ValueError("Duplicate, out-of-order, or excess verse.")
                previous = (chapter, verse)
                passages.append(ImportedPassage(reference=f"{book} {chapter}:{verse}", text=match["text"]))
            if previous == (0, 0):
                raise ValueError("Missing UXLC book text.")
        return passages
    except ValueError as exc:
        raise invalid_format() from exc


def parse_sblgnt_snapshot(raw: bytes) -> list[ImportedPassage]:
    members = [f"SBLGNT-{SBLGNT_COMMIT}/data/sblgnt/text/{code}.txt" for code in SBLGNT_BOOKS]
    passages = []
    try:
        for (code, book), content in zip(SBLGNT_BOOKS.items(), original_archive_texts(raw, members), strict=True):
            title, separator, text_rows = content.partition("\n")
            if not separator or not title.strip():
                raise ValueError("Missing SBLGNT title line.")
            previous = (0, 0)
            for raw_line in text_rows.split("\n"):
                line = raw_line.removesuffix("\r")
                if not line:
                    continue
                match = SBLGNT_VERSE_LINE.fullmatch(line)
                if match is None or match["book"] != code:
                    raise ValueError("Invalid SBLGNT verse line.")
                chapter, verse = int(match["chapter"]), int(match["verse"])
                if (chapter, verse) <= previous or len(passages) >= MAX_PASSAGES:
                    raise ValueError("Duplicate, out-of-order, or excess verse.")
                previous = (chapter, verse)
                passages.append(ImportedPassage(reference=f"{book} {chapter}:{verse}", text=match["text"]))
            if previous == (0, 0):
                raise ValueError("Missing SBLGNT book text.")
        return passages
    except ValueError as exc:
        raise invalid_format() from exc


def parse_starter(starter: Starter, raw: bytes) -> CorpusImport:
    if hashlib.sha256(raw).hexdigest() != starter.sha256:
        raise APIError(
            502, "source_snapshot_changed",
            "The source has changed since verification. Import stopped; review the new edition first.",
        )
    if starter.format in {"tanzil-translation", "tanzil-uthmani-text"}:
        passages = parse_tanzil_snapshot(raw)
    elif starter.format == "ebible-vpl-torah":
        passages = parse_ebible_torah_snapshot(raw)
    elif starter.format in {"uxlc-full-accents-torah", "uxlc-full-accents-rest"}:
        passages = parse_uxlc_snapshot(raw, torah_only=starter.format.endswith("torah"))
    elif starter.format == "sblgnt-text-zip":
        passages = parse_sblgnt_snapshot(raw)
    else:
        passages = parse_bible_snapshot(raw, torah_only=starter.format == "scrollmapper-torah")
    if len(passages) != starter.passage_count:
        raise invalid_format()
    return CorpusImport(
        title=starter.title,
        url=starter.source_url,
        source_type=starter.source_type,
        edition=ImportedEdition(
            title=starter.edition_title,
            language=starter.language,
            revision=starter.revision,
            collection_memberships=list(starter.collections),
        ),
        passages=passages,
        use_limits=UseLimits(external_processing=starter.external_processing, rights_note=starter.rights_note),
        provenance={
            "starter_id": starter.id,
            "download_url": starter.download_url,
            "licence_url": starter.licence_url,
            "provenance_note": starter.provenance_note,
            "verified_on": starter.verified_on,
            "format": starter.format,
            "selection": starter.selection or (
                "Genesis–Deuteronomy only" if starter.format.endswith("torah") else "complete"
            ),
        },
    )


async def download_starter(starter: Starter, *, client: httpx.AsyncClient | None = None) -> bytes:
    """No redirects or HTTP compression, and a cap on declared and actual bytes."""
    if client is None:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(40.0, connect=10.0), follow_redirects=False, trust_env=False
        ) as owned_client:
            return await download_starter(starter, client=owned_client)
    try:
        async with client.stream(
            "GET", starter.download_url,
            headers={"Accept-Encoding": "identity", "User-Agent": "EuraikaCompass/0.1 personal-research"},
            follow_redirects=False,
        ) as response:
            if response.status_code != 200:
                raise APIError(502, "source_download_failed", "The preset source could not be downloaded.")
            encoding = response.headers.get("content-encoding", "identity").lower()
            if encoding not in {"", "identity"}:
                raise APIError(502, "source_download_failed", "The preset returned an unsupported encoding.")
            declared = response.headers.get("content-length")
            if declared and (not declared.isdigit() or int(declared) > MAX_SNAPSHOT_BYTES):
                raise APIError(413, "source_too_large", "The source snapshot exceeds the import size limit.")
            data = bytearray()
            async for chunk in response.aiter_raw():
                if len(data) + len(chunk) > MAX_SNAPSHOT_BYTES:
                    raise APIError(413, "source_too_large", "The source snapshot exceeds the import size limit.")
                data.extend(chunk)
            return bytes(data)
    except httpx.HTTPError as exc:
        raise APIError(502, "source_download_failed", "The preset source could not be downloaded.") from exc


def canonical_snapshot(payload: CorpusImport) -> bytes:
    return json.dumps(
        payload.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def save_snapshot(data_dir: Path, raw: bytes, content_hash: str) -> str:
    # All path components after data_dir are generated from a SHA256; no user path is accepted.
    relative = Path("sources") / content_hash / "original"
    destination = data_dir / relative
    temporary = None
    try:
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not destination.resolve().is_relative_to(data_dir.resolve()):
            raise OSError("Source storage is outside the configured data directory.")
        if destination.is_file() and hashlib.sha256(destination.read_bytes()).hexdigest() == content_hash:
            return relative.as_posix()
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".import-", delete=False) as file:
            temporary = Path(file.name)
            file.write(raw)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, destination)
        return relative.as_posix()
    except OSError as exc:
        raise APIError(503, "source_storage_unavailable", "The private source snapshot could not be saved.") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def source_dto(session: Session, source: Source) -> dict:
    editions = session.execute(
        select(Edition, func.count(Passage.id))
        .outerjoin(Passage, Passage.edition_id == Edition.id)
        .where(Edition.source_id == source.id)
        .group_by(Edition.id)
        .order_by(Edition.title, Edition.id)
    ).all()
    return {
        "id": str(source.id),
        "source_id": str(source.id),
        "title": source.title,
        "url": source.url,
        "source_type": source.source_type,
        "provenance": source.provenance,
        "use_limits": source.use_limits,
        "editions": [
            {"id": str(edition.id), "title": edition.title, "language": edition.language,
             "revision": edition.revision, "collection_memberships": edition.collection_memberships,
             "passage_count": count}
            for edition, count in editions
        ],
    }


def import_corpus(
    session: Session, payload: CorpusImport, data_dir: Path, *, snapshot: bytes | None = None
) -> dict:
    """Commit an immutable source edition; repeated bytes + edition identity reuse it."""
    raw = canonical_snapshot(payload) if snapshot is None else snapshot
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise APIError(413, "source_too_large", "The source snapshot exceeds the import size limit.")
    content_hash = hashlib.sha256(raw).hexdigest()
    identity = json.dumps(
        {"content_sha256": content_hash, "edition": payload.edition.model_dump(mode="json")},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    import_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    # Schema changes are unnecessary: a transaction advisory lock serializes identical imports.
    lock_id = int.from_bytes(bytes.fromhex(import_key[:16]), "big", signed=True)
    session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
    existing = session.scalar(select(Source).where(Source.provenance["import_key"].astext == import_key))
    snapshot_path = save_snapshot(data_dir, raw, content_hash)
    if existing is not None:
        result = source_dto(session, existing)
        session.commit()
        return result
    original_text = payload.source_type == "original_text"
    provenance = {
        **payload.provenance,
        "import_key": import_key,
        "content_sha256": content_hash,
        "snapshot_path": snapshot_path,
        "snapshot_bytes": len(raw),
        "snapshot_format": "original_download" if snapshot is not None else "canonical_import_json",
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "search_normalization": (
            "Unicode NFKC + casefold + whitespace, with additional ASCII hex search lexemes "
            "from NFKD, mark and tatweel removal, alef-wasla folding, and casefold. "
            "The original text is unchanged."
            if original_text else "Unicode NFKC + casefold + whitespace; original text unchanged"
        ),
        "source_assessment": "User-selected traceable source; authenticity is not a truth or authority rating.",
    }
    source = Source(
        title=payload.title, url=payload.url, source_type=payload.source_type,
        provenance=provenance, use_limits=payload.use_limits.model_dump(mode="json", exclude_none=True),
    )
    session.add(source)
    session.flush()
    edition = Edition(source_id=source.id, **payload.edition.model_dump(mode="json"))
    session.add(edition)
    session.flush()
    for offset in range(0, len(payload.passages), 1000):
        session.execute(insert(Passage), [
            {"edition_id": edition.id, "reference": passage.reference, "text": passage.text,
             "search_text": normalize_search_text(passage.text, with_original_lexemes=original_text)}
            for passage in payload.passages[offset:offset + 1000]
        ])
    result = source_dto(session, source)
    session.commit()
    return result


def citation_dto(passage: Passage, edition: Edition, source: Source) -> dict:
    return {
        "passage_id": str(passage.id),
        "source_id": str(source.id),
        "source_title": source.title,
        "source_type": source.source_type,
        "edition_id": str(edition.id),
        "edition_title": edition.title,
        "reference": passage.reference,
        "quote": passage.text,
        "url": source.url,
        "licence_url": source.provenance.get("licence_url"),
        "collection_memberships": edition.collection_memberships,
        "language": edition.language,
        "revision": edition.revision,
        "content_sha256": source.provenance.get("content_sha256"),
        "quote_sha256": hashlib.sha256(passage.text.encode("utf-8")).hexdigest(),
        "use_limits": source.use_limits,
        "evidence_role": "context" if source.source_type in {"commentary", "article", "context"} else "source_text",
    }


REFERENCE = re.compile(
    r"^(?:(?:qur['’]?an|koran|surah)\s+)?"
    r"(?:(?P<book>(?:[1-3]\s+)?[^\W\d_][^\d:]{0,75}?)\s+)?"
    r"(?P<chapter>\d{1,3}):(?P<verse>\d{1,3})(?:-(?P<end>\d{1,3}))?$",
    re.IGNORECASE,
)
STOP_WORDS = frozenset(
    "a an and are as at be by can could do does for from had has have how i if in is it its "
    "me my of on or our should that the their them they this to was we were what when where "
    "which who why will with would you your".split()
)
BOOK_ALIASES = {
    "gen": ("genesis",), "exo": ("exodus",), "lev": ("leviticus",),
    "numeri": ("numbers",), "num": ("numbers",),
    "deuteronomium": ("deuteronomy",), "deut": ("deuteronomy",),
    "jozua": ("joshua",), "rechters": ("judges",),
    "koningen": ("kings",), "kronieken": ("chronicles",),
    "ps": ("psalms",), "psalm": ("psalms",), "psalmen": ("psalms",),
    "spreuken": ("proverbs",), "prediker": ("ecclesiastes",),
    "hooglied": ("song of songs", "song of solomon"),
    "song of songs": ("song of solomon",), "song of solomon": ("song of songs",),
    "jesaja": ("isaiah",), "jeremia": ("jeremiah",), "ezechiël": ("ezekiel",),
    "matteüs": ("matthew",), "mattheüs": ("matthew",), "marcus": ("mark",),
    "markus": ("mark",), "lucas": ("luke",), "lukas": ("luke",),
    "johannes": ("john",), "joh": ("john",), "handelingen": ("acts",),
    "romeinen": ("romans",), "korintiërs": ("corinthians",), "korinthiërs": ("corinthians",),
    "petrus": ("peter",), "hebreeën": ("hebrews",), "jakobus": ("james",),
    "openbaring": ("revelation", "revelation of john"),
    "revelation": ("revelation of john",), "revelation of john": ("revelation",),
}
BOOK_PREFIXES = {"1": "i", "2": "ii", "3": "iii", "i": "1", "ii": "2", "iii": "3"}


def reference_values(query: str) -> list[str] | None:
    match = REFERENCE.fullmatch(normalize_search_text(query))
    if match is None:
        return None
    chapter, verse = int(match["chapter"]), int(match["verse"])
    end = int(match["end"] or verse)
    if chapter < 1 or verse < 1 or end < verse or end - verse > 49:
        return []
    book = match["book"]
    books = {book.strip()} if book else {""}
    if book:
        prefix, _, unprefixed_book = book.strip().partition(" ")
        alternate_prefix = BOOK_PREFIXES.get(prefix)
        if alternate_prefix and unprefixed_book:
            for name in (unprefixed_book, *BOOK_ALIASES.get(unprefixed_book.removesuffix("."), ())):
                books.update((f"{prefix} {name}", f"{alternate_prefix} {name}"))
        else:
            books.update(BOOK_ALIASES.get(book.strip().removesuffix("."), ()))
    return [f"{name + ' ' if name else ''}{chapter}:{number}"
            for name in sorted(books) for number in range(verse, end + 1)]


def retrieve_passages(
    session: Session,
    query: str,
    collection_filter: list[str] | None = None,
    source_ids: list[UUID] | None = None,
    limit: int = 12,
    external_processing: bool = False,
) -> list[dict]:
    """Retrieve real matches only. Cloud callers must opt into the explicit rights filter.

    FTS is lexical, not an interpretation, semantic search or completeness guarantee.
    Query planners should supply English topic terms for the English starter editions.
    """
    if len(query) > 2000:
        raise APIError(422, "invalid_query", "The search query exceeds the supported length.")
    if collection_filter is not None and not set(collection_filter) <= COLLECTIONS:
        raise APIError(422, "invalid_collection", "Choose Torah, Bible or Quran collections.")
    if not query.strip() or collection_filter == [] or source_ids == []:
        return []
    limit = max(1, min(int(limit), 50))
    statement = (
        select(Passage, Edition, Source)
        .join(Edition, Passage.edition_id == Edition.id)
        .join(Source, Edition.source_id == Source.id)
    )
    if collection_filter:
        statement = statement.where(or_(*[
            Edition.collection_memberships.contains([collection]) for collection in collection_filter
        ]))
    if source_ids is not None:
        statement = statement.where(Source.id.in_(source_ids))
    if external_processing:
        # JSONB containment distinguishes the boolean true from a string such as "true".
        statement = statement.where(Source.use_limits.contains({"external_processing": True}))
    references = reference_values(query)
    if references is not None:
        if not references:
            return []
        statement = statement.where(func.lower(Passage.reference).in_(references))
    else:
        words = list(dict.fromkeys(
            word for word in WORD.findall(normalize_search_text(query))
            if len(word) > 1 and word not in STOP_WORDS
        ))[:32]
        words.extend(list(dict.fromkeys(original_search_lexemes(query)))[:32])
        if not words:
            return []
        # Only Unicode alphanumerics enter tsquery syntax. The expression is bound, never SQL.
        tsquery = func.to_tsquery("simple", " | ".join(f"{word}:*" for word in words))
        statement = statement.where(Passage.search_vector.op("@@")(tsquery))
        statement = statement.order_by(func.ts_rank_cd(Passage.search_vector, tsquery).desc())
    statement = statement.order_by(Edition.title, Passage.reference, Passage.id).limit(limit)
    return [citation_dto(passage, edition, source) for passage, edition, source in session.execute(statement)]


CONTEXT_REFERENCE = re.compile(
    r"^(?:(?P<book>(?:[1-3] )?[^\W\d_][^:\r\n]{0,80}?) )?"
    r"(?P<chapter>[1-9][0-9]{0,2}):(?P<verse>[1-9][0-9]{0,2})$",
    re.UNICODE,
)


def neighbor_references(reference: str, radius: int) -> list[str] | None:
    """Generate bounded lookup keys, never a claim that those verses exist."""
    match = CONTEXT_REFERENCE.fullmatch(reference)
    if match is None:
        return None
    book = match["book"]
    prefix = f"{book} " if book else ""
    chapter, verse = match["chapter"], int(match["verse"])
    return [f"{prefix}{chapter}:{number}"
            for number in range(max(1, verse - radius), min(999, verse + radius) + 1)]


def context_passages(
    session: Session, passage_ids: list[UUID], radius: int = 1
) -> list[dict]:
    """Return exact centers and existing neighbors, bounded to their edition/chapter.

    This is adjacent textual context, not an assurance of whole-book interpretation.
    The caller must apply any cloud-use policy when choosing its seed passages; all
    neighbors necessarily retain those seeds' source/edition and their use limits.
    """
    if len(passage_ids) > 9:
        raise APIError(422, "too_many_context_seeds", "Choose at most nine context passages.")
    if type(radius) is not int or not 0 <= radius <= 2:
        raise APIError(422, "invalid_context_radius", "The context radius must be between zero and two.")
    unique_ids = list(dict.fromkeys(passage_ids))
    if not unique_ids:
        return []
    base = (
        select(Passage, Edition, Source)
        .join(Edition, Passage.edition_id == Edition.id)
        .join(Source, Edition.source_id == Source.id)
    )
    seeds = {passage.id: (passage, edition, source)
             for passage, edition, source in session.execute(base.where(Passage.id.in_(unique_ids)))}
    if not seeds:
        return []
    requested = {}
    for seed_id in unique_ids:
        if seed_id not in seeds:
            continue
        passage, edition, _source = seeds[seed_id]
        requested[seed_id] = (
            edition.id, neighbor_references(passage.reference, radius) or [passage.reference]
        )
    conditions = [and_(Passage.edition_id == edition_id, Passage.reference.in_(references))
                  for edition_id, references in requested.values()]
    found = {(edition.id, passage.reference): (passage, edition, source)
             for passage, edition, source in session.execute(base.where(or_(*conditions)))}
    items = {}
    for seed_id, (edition_id, references) in requested.items():
        for reference in references:
            row = found.get((edition_id, reference))
            if row is None:
                # Versification gaps stay gaps. Never invent text or cross into another edition.
                continue
            passage, edition, source = row
            if passage.id not in items:
                items[passage.id] = {
                    **citation_dto(passage, edition, source),
                    "is_center": passage.id in seeds,
                    "context_for": [],
                }
            items[passage.id]["context_for"].append(str(seed_id))
    return list(items.values())


def session_dependency(request: Request):
    yield from request.app.state.database.session()


SessionDependency = Annotated[Session, Depends(session_dependency)]


@router.get("/corpus")
def list_corpus(session: SessionDependency):
    sources = session.scalars(select(Source).order_by(Source.created_at, Source.id)).all()
    return {"items": [source_dto(session, source) for source in sources]}


@router.post("/corpus/import", status_code=201)
def post_import(payload: CorpusImport, request: Request, session: SessionDependency):
    return import_corpus(session, payload, request.app.state.settings.data_dir)


@router.get("/corpus/starters")
def list_starters():
    return {"items": [starter.metadata() for starter in STARTERS.values()]}


@router.post("/corpus/starters/{starter_id}/import", status_code=201)
async def post_starter_import(starter_id: str, request: Request, session: SessionDependency):
    starter = STARTERS.get(starter_id)
    if starter is None:
        raise APIError(404, "not_found", "This source starter was not found.")
    raw = await download_starter(starter)
    payload = await run_in_threadpool(parse_starter, starter, raw)
    return await run_in_threadpool(
        import_corpus, session, payload, request.app.state.settings.data_dir, snapshot=raw
    )


@router.get("/corpus/search")
def search_corpus(
    session: SessionDependency,
    q: str = Query(min_length=1, max_length=2000),
    collection: list[str] | None = Query(default=None),
    source_id: list[UUID] | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=50),
    external_processing: bool = False,
):
    return {"items": retrieve_passages(
        session, q, collection_filter=collection, source_ids=source_id,
        limit=limit, external_processing=external_processing,
    )}


@router.get("/passages/{passage_id}")
def get_passage(passage_id: UUID, session: SessionDependency):
    row = session.execute(
        select(Passage, Edition, Source)
        .join(Edition, Passage.edition_id == Edition.id)
        .join(Source, Edition.source_id == Source.id)
        .where(Passage.id == passage_id)
    ).first()
    if row is None:
        raise APIError(404, "not_found", "This passage was not found.")
    return citation_dto(*row)


@router.get("/passages/{passage_id}/context")
def get_passage_context(
    passage_id: UUID, session: SessionDependency, radius: int = Query(default=1, ge=0, le=2)
):
    items = context_passages(session, [passage_id], radius=radius)
    if not items:
        raise APIError(404, "not_found", "This passage was not found.")
    return {"items": items, "center_passage_id": str(passage_id), "radius": radius}
