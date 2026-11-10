import asyncio
import json
from uuid import UUID

import pytest
from sqlalchemy import func, select

from compass.adapters.base import AdapterError
from compass.chat import ChatService, checked_answer, web_queries, while_connected
from compass.corpus import STARTERS
from compass.errors import APIError
from compass.models import (
    ChatTurn,
    Conversation,
    Dossier,
    Edition,
    ImageAsset,
    Passage,
    Source,
    Transcription,
)

EVIDENCE = [{"id": "S1", "quote": "The exact visible words in the named edition.", "reference": "Example 1:1"}]


def test_citations_are_real_snapshots_and_explicit_quotes_must_match():
    answer, citations, warnings = checked_answer(json.dumps({
        "answer": 'The passage says “The exact visible words in the named edition.” [S1]',
        "limitations": ["This is a test fixture, not scripture."],
    }), EVIDENCE)
    assert "[S1]" in answer and citations == EVIDENCE
    assert "fixture" in warnings[0]


@pytest.mark.parametrize("answer,code", [
    ("An answer without a source", "invalid_citations"),
    ("A claim [S99]", "invalid_citations"),
    ("A claim [S1] and another [S2]", "invalid_citations"),
    ('It says “An invented quotation that does not exist.” [S1]', "unverified_quote"),
    ('It says «An invented quotation that does not exist.» [S1]', "unverified_quote"),
])
def test_unknown_missing_and_fabricated_quotes_are_rejected(answer, code):
    with pytest.raises(APIError) as error:
        checked_answer(json.dumps({"answer": answer}), EVIDENCE)
    assert error.value.code == code


def test_visible_ellipsis_can_omit_but_not_invent_quoted_words():
    answer, _, _ = checked_answer(json.dumps({"answer": "It says «The exact visible ... named edition.» [S1]"}), EVIDENCE)
    assert "[S1]" in answer
    with pytest.raises(APIError):
        checked_answer(json.dumps({"answer": "It says «The exact visible ... invented edition.» [S1]"}), EVIDENCE)


def test_roundtable_expands_explicit_citation_lists_without_admitting_unknown_ids():
    evidence = [*EVIDENCE, {"id": "S2", "quote": "Another visible source."}]
    answer, citations, _ = checked_answer('{"answer":"Compare these sources [S1, S2]."}', evidence,
                                          grouped_citations=True)
    assert answer == "Compare these sources [S1] [S2]."
    assert citations == evidence
    with pytest.raises(APIError, match="unknown passage"):
        checked_answer('{"answer":"Compare these sources [S1, S99]."}', evidence, grouped_citations=True)


def test_full_temporary_session_can_still_be_saved():
    service = ChatService(None, None)
    key, value = service.session(None)
    value["turns"] = [{}] * 40
    with pytest.raises(APIError) as error:
        service.session(UUID(key))
    assert error.value.code == "session_full"
    assert service.session(UUID(key), allow_full=True)[1] is value


@pytest.mark.parametrize("sensitive_query", [
    "qa-private@example.org", "https://example.org", "record 123456789",
    "mourning comfort\nsecret", "site:example.org",
])
def test_web_query_boundary_rejects_identifiers_and_urls(sensitive_query):
    assert web_queries([sensitive_query, "mortuary rites Psalm 23:4"]) == ["mortuary rites Psalm 23:4"]


@pytest.mark.asyncio
async def test_disconnect_cancels_owned_generation():
    cancelled = asyncio.Event()

    class Disconnected:
        async def is_disconnected(self):
            return True

    async def generation():
        try:
            await asyncio.sleep(30)
        finally:
            cancelled.set()

    with pytest.raises(APIError) as error:
        await while_connected(Disconnected(), generation())
    assert error.value.code == "chat_cancelled"
    assert cancelled.is_set()


class ControlledConnection:
    def __init__(self, application, invalid=False):
        self.application = application
        self.calls = []
        self.invalid = invalid
        self.cloud_blocked = False
        self.local_only = False
        self.remote = False
        self.ranked_ids = ["C1"]
        self.reference = None
        self.web_queries = []
        self.manuscript_ranking = ["M1"]
        self.answer = "A gentle reflection on the retrieved test passage [S1]."

    def get(self, connection_id):
        if connection_id != "actual-test-boundary":
            raise AdapterError("unknown_connection", "Choose a connection.")
        return {"enabled": True, "configured": True, "local": not (self.cloud_blocked or self.remote)}

    def settings(self):
        return {"local_only": self.cloud_blocked or self.local_only}

    def signature(self, connection_id):
        return "controlled-configuration"

    async def complete(self, connection_id, messages, max_tokens=1500, expected_signature=None):
        # Inference is outside DB transactions; no network is faked inside retrieval itself.
        assert self.application.state.database.engine.pool.checkedout() == 0
        self.calls.append((connection_id, messages))
        if max_tokens == 1200:
            text = json.dumps({"queries": ["mourning comfort"], "references": [self.reference] if self.reference else [], "web_queries": self.web_queries})
        elif max_tokens == 800:
            payload = json.loads(messages[-1]["content"])
            selection = {"selections": {collection: self.ranked_ids for collection in payload["collections"]}}
            if "manuscript_candidates" in payload:
                selection["manuscript_selections"] = self.manuscript_ranking
            text = json.dumps(selection)
        elif self.invalid:
            text = json.dumps({"answer": "A fabricated source [S99]"})
        else:
            text = json.dumps({"answer": self.answer, "limitations": ["Synthetic transport fixture."]})
        return {"text": text, "model_id": "boundary-model", "usage": {}}


def add_test_source(application, external_processing=True, content=None):
    with application.state.database.sessions() as session:
        source = Source(title="Synthetic source for integration checks", url="https://example.org/fixture", source_type="primary_text", use_limits={"external_processing": external_processing})
        session.add(source)
        session.flush()
        edition = Edition(source_id=source.id, title="Fixture edition", language="en", revision="fixture-v1", collection_memberships=["torah", "bible", "quran"])
        session.add(edition)
        session.flush()
        passage = Passage(edition_id=edition.id, reference="Fixture 1:1", text=content or "The fixture mentions mourning and comfort.", search_text="mourning comfort")
        session.add(passage)
        session.commit()
        return str(source.id)


def configure_chat(application, invalid=False):
    connection = ControlledConnection(application, invalid)
    application.state.connections = connection
    application.state.chat = ChatService(application.state.database, connection)
    return connection


@pytest.mark.postgres
@pytest.mark.asyncio
async def test_roundtable_freezes_common_evidence_with_local_planner_and_cloud_speaker(postgres_app):
    _, application, _ = postgres_app
    connection = configure_chat(application)
    chat = application.state.chat
    add_test_source(application)
    restricted = add_test_source(application, external_processing=False, content="mourning comfort PRIVATE_ROUND_TABLE")
    participant = {"name": "Textual", "persona_id": "textual", "connection_id": "actual-test-boundary"}
    scope = {"topic": "Discuss mourning and comfort", "language": "en"}
    signature = connection.signature(participant["connection_id"])

    with pytest.raises(APIError) as exc:
        await chat.prepare_roundtable_evidence({**scope, "source_ids": [restricted]}, participant,
                                              external_processing=True, expected_signature=signature,
                                              allow_manuscript_cloud=False)
    assert exc.value.code == "roundtable_source_restricted"
    assert not connection.calls

    prepared = await chat.prepare_roundtable_evidence(scope, participant, external_processing=True,
                                                      expected_signature=signature, allow_manuscript_cloud=False)
    assert len(connection.calls) == 2
    assert prepared["evidence"] and all(source["use_limits"]["external_processing"] for source in prepared["evidence"])
    assert "PRIVATE_ROUND_TABLE" not in json.dumps(connection.calls)
    assert not chat.temporary

    # Adding another eligible edition after preparation must not change either participant's evidence.
    add_test_source(application, content="mourning comfort NEW_EDITION_AFTER_FREEZE")
    first = await chat.roundtable_reply(scope, participant, evidence=prepared["evidence"], history=[],
                                       moderator_note="", expected_signature=signature, allow_manuscript_cloud=False)
    connection.remote = True
    second = await chat.roundtable_reply(scope, {**participant, "name": "Critical", "persona_id": "critical"},
                                        evidence=prepared["evidence"], history=[{"name": "Textual", "answer": first["answer"]}],
                                        moderator_note="Respond to the first contribution", expected_signature=signature,
                                        allow_manuscript_cloud=False)
    first_payload, second_payload = [json.loads(messages[-1]["content"]) for _, messages in connection.calls[-2:]]
    assert first_payload["evidence"] == second_payload["evidence"]
    assert second_payload["earlier_contributions"] == [{"speaker": "Textual", "text": first["answer"]}]
    assert first["citations"] == second["citations"]
    assert "NEW_EDITION_AFTER_FREEZE" not in json.dumps(connection.calls)


MANUSCRIPT_TEXT = "Mourning comfort in this PRIVATE_FOLIO_MARKER reading."


def add_manuscript_reading(application, *, external_processing=False):
    with application.state.database.sessions() as session:
        dossier = Dossier(title="Folio experiment")
        session.add(dossier)
        session.flush()
        image = ImageAsset(
            dossier_id=dossier.id, filename="folio-5v.jpg", media_type="image/jpeg", width=800, height=1200,
            sha256="3" * 64, provenance={"kind": "manuscript", "manuscript_id": "fixture-witness",
                "manuscript_title": "Manuscript fixture", "institution": "Fixture University Library",
                "shelfmark": "MS Fixture 8", "folio_label": "fol. 5v", "folio_id": "folio-5v",
                "image_sha256": "3" * 64, "manifest_sha256": "4" * 64,
                "catalog_url": "https://example.org/manuscript", "language": "en",
                "use_limits": {"local_ocr": True, "local_storage": True, "preview": True,
                               "external_processing": external_processing}},
        )
        session.add(image)
        session.flush()
        reading = Transcription(
            image_id=image.id, text=MANUSCRIPT_TEXT, kind="automatic", engine="kraken", language="en",
            input_region={"x": 100, "y": 300, "width": 300, "height": 250},
            regions=[{"text": MANUSCRIPT_TEXT, "page": 0, "type": "line", "coordinate_system": "input_pixels",
                      "bbox": {"x": 12, "y": 20, "width": 90, "height": 15}}],
        )
        session.add(reading)
        session.commit()
        return str(dossier.id), str(reading.id), str(image.id)


@pytest.mark.postgres
@pytest.mark.parametrize("remote", [False, True])
def test_manuscript_only_citation_keeps_saved_revision_after_correction(postgres_app, remote):
    client, application, _ = postgres_app
    connection = configure_chat(application)
    connection.remote = remote
    dossier, reading, image = add_manuscript_reading(application, external_processing=remote)
    response = client.post("/api/v1/chat", json={
        "message": "What about mourning comfort in this folio?", "connection_id": "actual-test-boundary",
        "source_ids": [], "manuscript_dossier_id": dossier, "manuscript_revision_ids": [reading],
        "allow_manuscript_cloud": remote,
    })
    assert response.status_code == 200, response.text
    turn = response.json()
    assert turn["grounding"]["manuscripts"] == {
        "status": "used", "retrieved_count": 1, "source_count": 1, "blocked_count": 0, "dossier_id": dossier,
    }
    assert turn["grounding"]["cited_collections"] == []
    citation = turn["citations"][0]
    assert citation["kind"] == "manuscript" and citation["quote"] == MANUSCRIPT_TEXT
    assert citation["transcription_id"] == reading and citation["image_id"] == image
    assert citation["image_sha256"] == "3" * 64
    assert citation["region"] == {"kind": "text_region", "coordinate_system": "original_image_pixels",
                                  "x": 112, "y": 320, "width": 90, "height": 15}
    prompt = json.loads(connection.calls[-1][1][-1]["content"])
    assert prompt["evidence"][0]["quote"] == MANUSCRIPT_TEXT
    assert "image_id" not in prompt["evidence"][0]

    saved = client.post("/api/v1/conversations", json={"title": "Saved folio citation", "session_id": turn["session_id"]})
    assert saved.status_code == 201
    correction = client.post(f"/api/v1/transcriptions/{reading}/revisions", json={"text": "Later correction"})
    assert correction.status_code == 201
    reopened = client.get("/api/v1/conversations/" + saved.json()["id"]).json()["turns"][0]
    assert reopened["citations"] == turn["citations"]


@pytest.mark.postgres
@pytest.mark.parametrize("case,code", [
    ("wrong_dossier", "invalid_manuscript_selection"),
    ("no_consent", "manuscript_cloud_consent_required"),
    ("no_rights", "manuscript_processing_blocked"),
])
def test_manuscript_scope_and_cloud_permissions_checked_before_provider(postgres_app, case, code):
    client, application, _ = postgres_app
    connection = configure_chat(application)
    connection.remote = True
    dossier, reading, _ = add_manuscript_reading(application, external_processing=case != "no_rights")
    if case == "wrong_dossier":
        dossier = client.post("/api/v1/dossiers", json={"title": "Other dossier"}).json()["id"]
    response = client.post("/api/v1/chat", json={
        "message": "Read this folio", "connection_id": "actual-test-boundary", "source_ids": [],
        "manuscript_dossier_id": dossier, "manuscript_revision_ids": [reading],
        "allow_manuscript_cloud": case != "no_consent",
    })
    assert response.status_code in {403, 422}
    assert response.json()["error"]["code"] == code
    assert connection.calls == []


@pytest.mark.postgres
def test_uncited_private_manuscript_does_not_enter_later_cloud_history(postgres_app):
    client, application, _ = postgres_app
    connection = configure_chat(application)
    add_test_source(application)
    dossier, reading, _ = add_manuscript_reading(application)
    question = {"message": "What evidence mentions mourning comfort?", "connection_id": "actual-test-boundary"}
    connection.answer = "The private reading mentions PRIVATE_FOLIO_MARKER, and here is a passage [S1]."
    first = client.post("/api/v1/chat", json={**question, "manuscript_dossier_id": dossier, "manuscript_revision_ids": [reading]})
    assert first.status_code == 200, first.text
    assert first.json()["grounding"]["manuscripts"]["status"] == "not_used"
    assert first.json()["citations"][0].get("kind") != "manuscript"
    assert "PRIVATE_FOLIO_MARKER" in json.dumps(connection.calls[-1][1])
    connection.calls.clear()
    connection.remote = True
    connection.answer = "This edition refers to mourning and comfort [S1]."
    response = client.post("/api/v1/chat", json={**question, "session_id": first.json()["session_id"]})
    assert response.status_code == 200, response.text
    assert all("PRIVATE_FOLIO_MARKER" not in json.dumps(messages) for _, messages in connection.calls)


@pytest.mark.postgres
def test_restricted_folio_is_excluded_while_permitted_edition_still_answers(postgres_app):
    client, application, _ = postgres_app
    connection = configure_chat(application)
    connection.remote = True
    add_test_source(application)
    dossier, reading, _ = add_manuscript_reading(application)
    response = client.post("/api/v1/chat", json={
        "message": "What evidence mentions mourning comfort?", "connection_id": "actual-test-boundary",
        "manuscript_dossier_id": dossier, "manuscript_revision_ids": [reading], "allow_manuscript_cloud": True,
    })
    assert response.status_code == 200, response.text
    grounding = response.json()["grounding"]["manuscripts"]
    assert grounding["status"] == "restricted" and grounding["blocked_count"] == 1
    assert all("PRIVATE_FOLIO_MARKER" not in json.dumps(messages) for _, messages in connection.calls)


@pytest.mark.postgres
def test_dossier_bound_conversation_rejects_valid_reading_from_other_dossier(postgres_app):
    client, application, _ = postgres_app
    connection = configure_chat(application)
    own_dossier = client.post("/api/v1/dossiers", json={"title": "Conversation dossier"}).json()["id"]
    conversation = client.post("/api/v1/conversations", json={"title": "Bound conversation", "dossier_id": own_dossier}).json()["id"]
    other_dossier, reading, _ = add_manuscript_reading(application)
    response = client.post("/api/v1/chat", json={
        "message": "Read this folio", "connection_id": "actual-test-boundary", "conversation_id": conversation,
        "manuscript_dossier_id": other_dossier, "manuscript_revision_ids": [reading],
    })
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "manuscript_dossier_conflict"
    assert connection.calls == []


@pytest.mark.postgres
@pytest.mark.parametrize("cite_web", [True, False])
def test_web_and_edition_citations_save_with_distinct_evidence_and_search_provenance(postgres_app, monkeypatch, cite_web):
    client, application, _ = postgres_app
    connection = configure_chat(application)
    connection.remote = True
    connection.web_queries = ["mourning rituals ancient Judaism", "qa-private@example.org"]
    connection.answer = "A textual observation [S1]."
    if cite_web:
        connection.answer += " An academic interpretation [S2]."
    add_test_source(application)
    seen = []
    abstract = "The study surveys rituals and practices across different communities."

    async def search(query, *, language, limit, external_processing):
        assert application.state.database.engine.pool.checkedout() == 0
        seen.append((query, external_processing))
        return {"items": [{
            "title": "Synthetic publisher record",
            "url": "https://example.org/paper",
            "excerpt": abstract,
            "provider": "publisher_index",
            "source_type": "article",
            "evidence_type": "abstract",
            "source_date": "2020-01-01",
            "retrieved_at": "2026-11-09T00:00:00+00:00",
            "content_sha256": "a" * 64,
            "use_limits": {"external_processing": True},
        }, {
            "url": "https://example.org/private",
            "excerpt": "LOCAL_WEB_EXCERPT",
            "use_limits": {"external_processing": False},
        }]}

    monkeypatch.setattr("compass.web_research.search_web", search)
    body = {"message": "Private concern: qa-private@example.org", "connection_id": "actual-test-boundary", "web_research": True}
    response = client.post("/api/v1/chat", json=body)
    assert response.status_code == 200, response.text
    turn = response.json()
    assert seen == [("mourning rituals ancient Judaism", True)]
    assert turn["grounding"]["web_research"]["status"] == ("used" if cite_web else "not_used")
    assert turn["grounding"]["web_research"]["source_count"] == int(cite_web)
    assert turn["grounding"]["web_research"]["retrieved_count"] == 1
    assert set(turn["grounding"]["cited_collections"]) == {"torah", "bible", "quran"}
    assert turn["citations"][0]["passage_id"]
    if cite_web:
        web = turn["citations"][1]
        assert web["kind"] == "web" and "passage_id" not in web and web["collection_memberships"] == []
        assert web["source_url"] == "https://example.org/paper" and web["quote"] == abstract
    else:
        assert len(turn["citations"]) == 1
    sent = json.loads(connection.calls[-1][1][-1]["content"])
    assert sent["evidence"][-1]["quote"] == abstract
    assert "LOCAL_WEB_EXCERPT" not in json.dumps(sent)
    saved = client.post("/api/v1/conversations", json={"title": "Web provenance fixture", "session_id": turn["session_id"]})
    assert saved.status_code == 201
    reopened = client.get("/api/v1/conversations/" + saved.json()["id"]).json()["turns"][0]
    assert reopened["citations"] == turn["citations"]
    assert reopened["grounding"] == turn["grounding"]


@pytest.mark.postgres
@pytest.mark.parametrize("web_enabled,local_only,status,called", [
    (False, False, "off", False),
    (True, True, "restricted", False),
    (True, False, "unavailable", True),
])
def test_web_switch_and_provider_failure_preserve_local_evidence(
    postgres_app, monkeypatch, web_enabled, local_only, status, called,
):
    client, application, _ = postgres_app
    connection = configure_chat(application)
    connection.local_only = local_only
    connection.web_queries = ["mourning customs"]
    add_test_source(application)
    seen = []

    async def unavailable(query, **_):
        seen.append(query)
        return {"items": [], "unavailable": True}

    monkeypatch.setattr("compass.web_research.search_web", unavailable)
    response = client.post("/api/v1/chat", json={
        "message": "mourning", "connection_id": "actual-test-boundary", "web_research": web_enabled,
    })
    assert response.status_code == 200, response.text
    assert response.json()["grounding"]["web_research"]["status"] == status
    assert response.json()["citations"][0]["passage_id"]
    assert bool(seen) is called


@pytest.mark.postgres
def test_grounded_chat_stays_temporary_until_explicit_save_and_reopens(postgres_app):
    client, application, _ = postgres_app
    connection = configure_chat(application)
    add_test_source(application)
    response = client.post("/api/v1/chat", json={"message": "How can I cope with mourning?", "connection_id": "actual-test-boundary"})
    assert response.status_code == 200, response.text
    turn = response.json()
    assert len(turn["citations"]) == 1 and turn["citations"][0]["id"] == "S1"
    assert turn["citations"][0]["quote"] == "The fixture mentions mourning and comfort."
    assert len(connection.calls) == 3
    assert client.get("/api/v1/conversations").json()["items"] == []
    second = client.post("/api/v1/chat", json={"message": "A second temporary question", "connection_id": "actual-test-boundary", "session_id": turn["session_id"]})
    assert second.status_code == 200, second.text
    saved = client.post("/api/v1/conversations", json={"title": "Explicit saved conversation", "session_id": turn["session_id"]})
    assert saved.status_code == 201, saved.text
    conversation = client.get("/api/v1/conversations/" + saved.json()["id"]).json()
    assert [item["question"] for item in conversation["turns"]] == ["How can I cope with mourning?", "A second temporary question"]
    assert conversation["turns"][0]["citations"] == turn["citations"]
    followup = client.post("/api/v1/chat", json={"message": "What can I reflect on?", "connection_id": "actual-test-boundary", "conversation_id": saved.json()["id"]})
    assert followup.status_code == 200, followup.text
    assert len(client.get("/api/v1/conversations/" + saved.json()["id"]).json()["turns"]) == 3
    assert len(connection.calls[-3][1]) > 2  # Saved prior turns reach the query planner.


@pytest.mark.postgres
def test_invalid_references_never_save_and_no_hidden_model_fallback(postgres_app):
    client, application, _ = postgres_app
    connection = configure_chat(application, invalid=True)
    add_test_source(application)
    response = client.post("/api/v1/chat", json={"message": "mourning", "connection_id": "actual-test-boundary"})
    assert response.status_code == 502 and response.json()["error"]["code"] == "invalid_citations"
    assert len(connection.calls) == 4  # Planner, selection, draft, one bounded same-model repair.
    assert {call[0] for call in connection.calls} == {"actual-test-boundary"}
    with application.state.database.sessions() as session:
        assert session.scalar(select(func.count()).select_from(ChatTurn)) == 0
        assert session.scalar(select(func.count()).select_from(Conversation)) == 0


@pytest.mark.postgres
def test_no_sources_or_cloud_permission_prevents_inference(postgres_app):
    client, application, _ = postgres_app
    connection = configure_chat(application)
    body = {"message": "mourning", "connection_id": "actual-test-boundary"}
    response = client.post("/api/v1/chat", json=body)
    assert response.status_code == 409 and response.json()["error"]["code"] == "corpus_empty"
    connection.cloud_blocked = True
    response = client.post("/api/v1/chat", json=body)
    assert response.status_code == 409 and response.json()["error"]["code"] == "local_only"
    assert not connection.calls


@pytest.mark.postgres
def test_local_source_answers_do_not_leak_through_cloud_chat_history(postgres_app):
    client, application, _ = postgres_app
    connection = configure_chat(application)
    add_test_source(application, external_processing=False, content="Restricted fixture about mourning: PRIVATE_SOURCE_MARKER.")
    body = {"message": "mourning", "connection_id": "actual-test-boundary"}
    first = client.post("/api/v1/chat", json=body)
    assert first.status_code == 200, first.text
    add_test_source(application, external_processing=True)
    connection.remote = True
    second = client.post("/api/v1/chat", json={**body, "session_id": first.json()["session_id"]})
    assert second.status_code == 200, second.text
    new_calls = connection.calls[3:]
    assert all("PRIVATE_SOURCE_MARKER" not in json.dumps(messages) for _, messages in new_calls)
    assert not any(message["role"] == "assistant" for _, messages in new_calls for message in messages)
    assert any("omitted" in warning for warning in second.json()["warnings"])


@pytest.mark.postgres
@pytest.mark.parametrize("selected,code", [([], "no_evidence"), (["C999"], "invalid_selection")])
def test_irrelevant_or_invented_candidate_ids_never_become_answer_sources(postgres_app, selected, code):
    client, application, _ = postgres_app
    connection = configure_chat(application)
    connection.ranked_ids = selected
    add_test_source(application)
    response = client.post("/api/v1/chat", json={"message": "mourning", "connection_id": "actual-test-boundary"})
    assert response.status_code in {422, 502} and response.json()["error"]["code"] == code
    assert len(connection.calls) == 2  # No final generation and no invented answer.


@pytest.mark.postgres
@pytest.mark.parametrize("translation_only", [False, True])
def test_chat_cites_aligned_original_without_ignoring_source_filter(postgres_app, translation_only):
    client, application, _ = postgres_app
    ids = {}
    with application.state.database.sessions() as session:
        # Model only sees this synthetic fixture; alignment still runs against the
        # same DB identity and passage joins used for imported starter editions.
        for starter_id, content in [("kjv-1769", "Fixture translation"), ("sblgnt-grc", "Δεῖγμα")]:
            starter = STARTERS[starter_id]
            source = Source(title=starter.title, url=starter.source_url, source_type=starter.source_type,
                            provenance={"starter_id": starter_id, "content_sha256": starter.sha256,
                                        "snapshot_format": "original_download", "format": starter.format,
                                        "snapshot_path": f"sources/{starter.sha256}/original",
                                        "download_url": starter.download_url},
                            use_limits={"external_processing": True})
            session.add(source)
            session.flush()
            ids[starter_id] = str(source.id)
            edition = Edition(source_id=source.id, title=starter.edition_title, language=starter.language,
                              revision=starter.revision, collection_memberships=list(starter.collections))
            session.add(edition)
            session.flush()
            session.add(Passage(edition_id=edition.id, reference="John 1:1", text=content))
        session.commit()
    connection = configure_chat(application)
    connection.remote = True
    connection.reference = {"collection": "bible", "reference": "John 1:1"}
    connection.answer = "The English edition is stored [S1]." if translation_only else "The English [S1] and Greek [S2] editions are stored."
    response = client.post("/api/v1/chat", json={
        "message": "Compare John 1:1", "connection_id": "actual-test-boundary",
        "collection_filter": ["bible"], "source_ids": [ids["kjv-1769"]] if translation_only else None,
    })
    assert response.status_code == 200, response.text
    citations = response.json()["citations"]
    assert [item["language"] for item in citations] == (["en"] if translation_only else ["en", "grc"])
    assert citations[-1]["quote"] == ("Fixture translation" if translation_only else "Δεῖγμα")
