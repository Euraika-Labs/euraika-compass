import hashlib
import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from compass.corpus import (
    STARTERS,
    CorpusImport,
    context_passages,
    download_starter,
    import_corpus,
    neighbor_references,
    normalize_search_text,
    original_search_lexemes,
    parse_bible_snapshot,
    parse_ebible_torah_snapshot,
    parse_starter,
    parse_tanzil_snapshot,
    parse_uxlc_snapshot,
    reference_values,
    retrieve_passages,
    router,
)
from compass.errors import APIError
from compass.models import Passage, Source


def payload(**changes):
    value = {
        "title": "A labelled test source",
        "url": "https://example.org/test-edition",
        "source_type": "translation",
        "edition": {
            "title": "Test edition",
            "language": "en",
            "revision": "test-1",
            "collection_memberships": ["torah", "bible"],
        },
        "passages": [
            {"reference": "Testbook 1:1", "text": "  Father, grief and comfort.\n"},
            {"reference": "Testbook 1:2", "text": "Care for neighbours and strangers."},
        ],
        "use_limits": {"external_processing": False, "rights_note": "Synthetic test data."},
    }
    value.update(changes)
    return CorpusImport.model_validate(value)


def test_import_validation_keeps_exact_text_and_rejects_invalid_references():
    value = payload()
    assert value.passages[0].text == "  Father, grief and comfort.\n"
    with pytest.raises(ValidationError):
        payload(passages=[{"reference": "same", "text": "a"}, {"reference": "same", "text": "b"}])
    with pytest.raises(ValidationError):
        payload(passages=[{"reference": "a", "text": "bad\x00text"}])
    with pytest.raises(ValidationError):
        payload(use_limits={"external_processing": "true"})


def test_search_normalization_is_separate_from_original_text():
    original = "  ＦＡＴＨＥＲ e\u0301 \u05d0\u05b8\u05d1 \u0623\u0628  "
    assert normalize_search_text(original) == "father é \u05d0\u05b8\u05d1 \u0623\u0628"
    assert original.startswith("  ＦＡＴＨＥＲ")


def test_bible_parser_preserves_spelling_and_whitespace_and_torah_scope():
    raw = json.dumps({"books": [
        {"name": "Genesis", "chapters": [{"chapter": 1, "verses": [
            {"verse": 1, "text": "  Exact electronic spelling.  "}]}]},
        {"name": "Joshua", "chapters": [{"chapter": 1, "verses": [
            {"verse": 1, "text": "Outside the Torah selection."}]}]},
    ]}).encode()
    items = parse_bible_snapshot(raw, torah_only=True)
    assert [(item.reference, item.text) for item in items] == [
        ("Genesis 1:1", "  Exact electronic spelling.  ")
    ]
    assert len(parse_bible_snapshot(raw)) == 2


def test_tanzil_parser_excludes_metadata_and_never_rewrites_text():
    raw = b"1|1|  Exact text, including | punctuation.  \r\n# Source metadata\r\n1|2|Next line.\r\n"
    items = parse_tanzil_snapshot(raw)
    assert [(item.reference, item.text) for item in items] == [
        ("1:1", "  Exact text, including | punctuation.  "), ("1:2", "Next line.")
    ]
    with pytest.raises(APIError) as error:
        parse_tanzil_snapshot(b"1|1|first\n1|1|duplicate\n")
    assert error.value.code == "invalid_source_format"


def test_starter_hash_rejects_changed_source_before_import():
    with pytest.raises(APIError) as error:
        parse_starter(STARTERS["pickthall-en"], b"not the verified source")
    assert error.value.code == "source_snapshot_changed"


def test_ebible_zip_reads_only_named_text_member_and_bounds_decompression(monkeypatch):
    import compass.corpus as module

    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("engjps_vpl.sql", "Never execute this member.")
        archive.writestr("engjps_vpl.txt", "\n".join(
            f"{name} 1:1  Exact VPL text.  " for name in ["GEN", "EXO", "LEV", "NUM", "DEU"]
        ))
    raw = stream.getvalue()
    items = parse_ebible_torah_snapshot(raw)
    assert len(items) == 5
    assert items[0].text == " Exact VPL text.  "
    assert items[-1].reference == "Deuteronomy 1:1"
    monkeypatch.setattr(module, "MAX_TOTAL_TEXT_BYTES", 10)
    with pytest.raises(APIError) as error:
        parse_ebible_torah_snapshot(raw)
    assert error.value.code == "invalid_source_format"


def test_reference_lookup_accepts_actual_edition_naming_without_rewriting_citations():
    assert reference_values("Quran 2:156") == ["2:156"]
    assert set(reference_values("1 John 4:8")) == {"1 john 4:8", "i john 4:8"}
    assert "revelation of john 1:1" in reference_values("Revelation 1:1")
    assert reference_values("John 11:35-34") == []
    assert "john 1:1" in reference_values("Johannes 1:1")
    assert "psalms 23:1" in reference_values("Psalmen 23:1")
    assert "genesis 1:1" in reference_values("Gen. 1:1")
    assert {"1 john 4:8", "i john 4:8"} <= set(reference_values("I Johannes 4:8"))


def test_uxlc_preserves_exact_payload_with_internal_bidi_and_native_versification():
    verse = "\xa0מֶלֶךְ־שָׁלוֹם׃ \u202a[x]\u202c "
    line = f"\u202b\xa026\xa0\u05c320\xa0\xa0{verse}\u202c\r\n"
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for book in ("Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"):
            archive.writestr(
                f"TextFiles/{book}.txt",
                "\u202axxxx    Title\u202c\r\n" + line + "\u202axxxx    End of book.",
            )
        archive.writestr("TextFiles/Joshua.txt", "Outside the Torah selection.")
    parsed = parse_uxlc_snapshot(stream.getvalue(), torah_only=True)
    assert len(parsed) == 5
    assert parsed[1].reference == "Exodus 20:26"
    assert parsed[1].text.encode("utf-8") == verse.encode("utf-8")


@pytest.mark.parametrize(("marked", "unmarked"), [
    ("מֶלֶךְ", "מלך"),
    ("ΛΌΓΟς", "λογος"),
    ("ٱلرَّحْمَـٰنِ", "الرحمن"),
])
def test_original_script_search_lexemes_match_with_or_without_marks(marked, unmarked):
    tokens = original_search_lexemes(marked)
    assert len(tokens) == 1 and tokens[0].isascii()
    assert tokens == original_search_lexemes(unmarked)
    assert original_search_lexemes("English topic search") == []


def test_context_lookup_keys_stay_in_chapter_and_reject_ambiguous_references():
    assert neighbor_references("Genesis 1:1", 1) == ["Genesis 1:1", "Genesis 1:2"]
    assert neighbor_references("2:156", 1) == ["2:155", "2:156", "2:157"]
    assert neighbor_references("I John 4:8", 0) == ["I John 4:8"]
    assert neighbor_references("Genesis 1:1-3", 1) is None
    assert neighbor_references("See an editorial paragraph", 1) is None
    with pytest.raises(APIError) as error:
        context_passages(None, [uuid4() for _ in range(10)])
    assert error.value.code == "too_many_context_seeds"
    with pytest.raises(APIError) as error:
        context_passages(None, [], radius=3)
    assert error.value.code == "invalid_context_radius"


@pytest.mark.asyncio
async def test_download_only_uses_preset_and_rejects_redirects_and_oversize():
    starter = STARTERS["pickthall-en"]
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(APIError) as error:
            await download_starter(starter, client=client)
    assert error.value.code == "source_download_failed"
    assert seen == [starter.download_url]

    def oversized(_request):
        return httpx.Response(200, headers={"content-length": str(21 * 1024 * 1024)})

    async with httpx.AsyncClient(transport=httpx.MockTransport(oversized)) as client:
        with pytest.raises(APIError) as error:
            await download_starter(starter, client=client)
    assert error.value.status == 413


@pytest.mark.asyncio
async def test_download_bounds_actual_stream_even_without_content_length(monkeypatch):
    import compass.corpus as module

    monkeypatch.setattr(module, "MAX_SNAPSHOT_BYTES", 8)
    transport = httpx.MockTransport(lambda _: httpx.Response(200, content=b"123456789"))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(APIError) as error:
            await download_starter(STARTERS["pickthall-en"], client=client)
    assert error.value.code == "source_too_large"


@pytest.fixture
def corpus_app(postgres_app):
    client, application, registry = postgres_app
    # The module is an independently mountable router; root integrates it in create_app.
    if not any(getattr(route, "path", None) == "/api/v1/corpus" for route in application.routes):
        # A catch-all frontend route may already exist. Put API routes before that route.
        application.router.routes = [
            route for route in application.router.routes
            if getattr(route, "path", None) != "/{path:path}"
        ]
        application.include_router(router)
    return client, application, registry


@pytest.mark.postgres
def test_real_pg_import_search_citation_snapshot_and_idempotency(corpus_app):
    client, application, _ = corpus_app
    body = payload().model_dump(mode="json")
    response = client.post("/api/v1/corpus/import", json=body)
    assert response.status_code == 201, response.text
    source = response.json()
    assert source["editions"][0]["passage_count"] == 2
    assert source["use_limits"]["external_processing"] is False
    repeated = client.post("/api/v1/corpus/import", json=body)
    assert repeated.json()["id"] == source["id"]

    # OR topic retrieval must still find a verse when another term has no lexical match.
    results = client.get("/api/v1/corpus/search", params={"q": "grief nonexistenttoken"}).json()
    assert len(results["items"]) == 1
    item = results["items"][0]
    assert item["quote"] == body["passages"][0]["text"]
    assert item["source_type"] == "translation"
    assert item["collection_memberships"] == ["torah", "bible"]
    passage = client.get(f"/api/v1/passages/{item['passage_id']}").json()
    assert passage["quote"] == item["quote"]
    assert passage["reference"] == "Testbook 1:1"
    assert passage["url"] == body["url"]
    assert client.get("/api/v1/corpus/search", params={"q": "unfindabletoken"}).json() == {"items": []}
    exact = client.get("/api/v1/corpus/search", params={"q": "testbook 1:2"}).json()["items"]
    assert [row["reference"] for row in exact] == ["Testbook 1:2"]
    assert client.get("/api/v1/corpus").json()["items"][0]["id"] == source["id"]

    snapshot = Path(application.state.settings.data_dir) / source["provenance"]["snapshot_path"]
    assert snapshot.is_file()
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == item["content_sha256"]
    with application.state.database.sessions() as session:
        assert session.scalar(select(func.count()).select_from(Source)) == 1
        row = session.scalar(select(Passage).where(Passage.reference == "Testbook 1:1"))
        assert row.text == body["passages"][0]["text"]
        assert row.search_text == "father, grief and comfort."


@pytest.mark.postgres
def test_retrieval_requires_explicit_cloud_permission_and_respects_collections(corpus_app):
    _, application, _ = corpus_app
    with application.state.database.sessions() as session:
        private = import_corpus(session, payload(), application.state.settings.data_dir)
        public = import_corpus(session, payload(
            title="Explicitly permitted source",
            edition={"title": "Another edition", "language": "en", "revision": "v1",
                     "collection_memberships": ["quran"]},
            passages=[{"reference": "2:1", "text": "Comfort in grief."}],
            use_limits={"external_processing": True},
        ), application.state.settings.data_dir)
        assert len(retrieve_passages(session, "comfort")) == 2
        assert [row["source_id"] for row in retrieve_passages(
            session, "comfort", external_processing=True
        )] == [public["id"]]
        assert [row["source_id"] for row in retrieve_passages(
            session, "comfort", collection_filter=["torah"]
        )] == [private["id"]]
        assert [row["source_id"] for row in retrieve_passages(
            session, "comfort", source_ids=[UUID(public["id"])]
        )] == [public["id"]]
        legacy = session.get(Source, UUID(private["id"]))
        legacy.use_limits = {"external_processing": "true"}
        session.flush()
        assert [row["source_id"] for row in retrieve_passages(
            session, "comfort", external_processing=True
        )] == [public["id"]]
        assert retrieve_passages(session, "comfort", collection_filter=[]) == []
        assert retrieve_passages(session, "comfort", source_ids=[]) == []
        assert retrieve_passages(session, "Quran 2:1")[0]["quote"] == "Comfort in grief."


@pytest.mark.postgres
def test_http_starter_import_uses_verified_snapshot_and_is_repeatable(corpus_app, monkeypatch):
    import compass.corpus as module

    raw = b"1|1|Boundary fixture text.\n"
    starter = replace(STARTERS["pickthall-en"], sha256=hashlib.sha256(raw).hexdigest(), passage_count=1)
    monkeypatch.setitem(module.STARTERS, "pickthall-en", starter)

    async def controlled_download(_starter):
        return raw

    monkeypatch.setattr(module, "download_starter", controlled_download)
    client, application, _ = corpus_app
    metadata = client.get("/api/v1/corpus/starters").json()["items"]
    assert {row["id"] for row in metadata if row["source_type"] == "translation"} == {
        "jps-1917-torah", "kjv-1769", "pickthall-en"
    }
    assert {row["id"] for row in metadata if row["source_type"] == "original_text"} == {
        "uxlc-he-torah", "uxlc-he-tanakh-rest", "sblgnt-grc", "tanzil-uthmani-ar"
    }
    response = client.post("/api/v1/corpus/starters/pickthall-en/import")
    assert response.status_code == 201, response.text
    source = response.json()
    assert source["provenance"]["download_url"] == starter.download_url
    assert source["provenance"]["content_sha256"] == hashlib.sha256(raw).hexdigest()
    snapshot = application.state.settings.data_dir / source["provenance"]["snapshot_path"]
    assert snapshot.read_bytes() == raw
    assert client.post("/api/v1/corpus/starters/pickthall-en/import").json()["id"] == source["id"]
    assert client.post("/api/v1/corpus/starters/not-a-preset/import").status_code == 404


@pytest.mark.postgres
def test_pg_original_scripts_match_unmarked_queries_and_return_exact_quotes(corpus_app):
    client, application, _ = corpus_app
    cases = (
        ("he", "torah", "Genesis 1:1", "מֶלֶךְ־שָׁלוֹם׃ ", "מלך"),
        ("grc", "bible", "John 1:1", " ⟦Λόγος⟧ ", "λογος"),
        ("ar", "quran", "1:1", "ٱلرَّحْمَـٰنِ ۩ ۞\n", "الرحمن"),
    )
    licence_url = "https://example.org/fixture-licence"
    for language, collection, reference, original, query in cases:
        body = payload(
            title=f"Original-script fixture ({language})",
            source_type="original_text",
            edition={"title": f"Test {language}", "language": language, "revision": "v1",
                     "collection_memberships": [collection]},
            passages=[{"reference": reference, "text": original}],
            provenance={"licence_url": licence_url},
        )
        with application.state.database.sessions() as session:
            imported = import_corpus(session, body, application.state.settings.data_dir)
        response = client.get("/api/v1/corpus/search", params={
            "q": query, "collection": collection, "source_id": imported["id"],
        })
        assert response.status_code == 200, response.text
        results = response.json()["items"]
        assert len(results) == 1
        passage = results[0]
        assert passage["quote"].encode("utf-8") == original.encode("utf-8")
        assert passage["quote_sha256"] == hashlib.sha256(original.encode("utf-8")).hexdigest()
        assert passage["licence_url"] == licence_url
        assert client.get(f"/api/v1/passages/{passage['passage_id']}").json()["quote"] == original


@pytest.mark.postgres
def test_context_is_exact_existing_same_edition_and_does_not_fill_missing_verses(corpus_app):
    client, application, _ = corpus_app
    body = payload(passages=[
        {"reference": "Testbook 1:1", "text": "First visible verse."},
        {"reference": "Testbook 1:3", "text": "  Center wording stays verbatim.\n"},
        {"reference": "Testbook 1:4", "text": "Actual next verse."},
        {"reference": "Testbook 2:1", "text": "A different chapter."},
        {"reference": "Editorial paragraph", "text": "Nonstandard reference is still exact."},
    ])
    with application.state.database.sessions() as session:
        imported = import_corpus(session, body, application.state.settings.data_dir)
        other = payload(
            title="Another source",
            edition={"title": "Another edition", "language": "en", "revision": "v1",
                     "collection_memberships": ["bible"]},
            passages=[{"reference": "Testbook 1:2", "text": "A verse in another edition."}],
        )
        import_corpus(session, other, application.state.settings.data_dir)
        seeds = retrieve_passages(session, "Testbook 1:3", source_ids=[UUID(imported["id"])])
        center_id = UUID(seeds[0]["passage_id"])
        contexts = context_passages(session, [center_id], radius=2)
        assert [row["reference"] for row in contexts] == [
            "Testbook 1:1", "Testbook 1:3", "Testbook 1:4"
        ]
        assert all(row["source_id"] == imported["id"] for row in contexts)
        center = next(row for row in contexts if row["is_center"])
        assert center["quote"] == body.passages[1].text
        assert center["context_for"] == [str(center_id)]
        editorial = retrieve_passages(session, "nonstandard", source_ids=[UUID(imported["id"])])[0]
        assert [row["quote"] for row in context_passages(
            session, [UUID(editorial["passage_id"])]
        )] == ["Nonstandard reference is still exact."]
    response = client.get(f"/api/v1/passages/{center_id}/context")
    assert response.status_code == 200, response.text
    assert response.json()["center_passage_id"] == str(center_id)
    assert [row["reference"] for row in response.json()["items"]] == ["Testbook 1:3", "Testbook 1:4"]
    original = client.get(f"/api/v1/passages/{center_id}").json()
    assert original["quote"] == body.passages[1].text
    assert "is_center" not in original
    assert client.get(f"/api/v1/passages/{center_id}/context?radius=3").status_code == 422
    assert client.get(f"/api/v1/passages/{uuid4()}/context").status_code == 404
