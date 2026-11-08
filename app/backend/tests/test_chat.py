import asyncio
import json
from uuid import UUID

import pytest
from sqlalchemy import func, select

from compass.adapters.base import AdapterError
from compass.chat import ChatService, checked_answer, while_connected
from compass.errors import APIError
from compass.models import ChatTurn, Conversation, Edition, Passage, Source

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


def test_full_temporary_session_can_still_be_saved():
    service = ChatService(None, None)
    key, value = service.session(None)
    value["turns"] = [{}] * 40
    with pytest.raises(APIError) as error:
        service.session(UUID(key))
    assert error.value.code == "session_full"
    assert service.session(UUID(key), allow_full=True)[1] is value


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
        self.remote = False
        self.ranked_ids = ["C1"]

    def get(self, connection_id):
        if connection_id != "actual-test-boundary":
            raise AdapterError("unknown_connection", "Choose a connection.")
        return {"enabled": True, "configured": True, "local": not (self.cloud_blocked or self.remote)}

    def settings(self):
        return {"local_only": self.cloud_blocked}

    def signature(self, connection_id):
        return "controlled-configuration"

    async def complete(self, connection_id, messages, max_tokens=1500, expected_signature=None):
        # Inference is outside DB transactions; no network is faked inside retrieval itself.
        assert self.application.state.database.engine.pool.checkedout() == 0
        self.calls.append((connection_id, messages))
        if max_tokens == 1200:
            text = json.dumps({"queries": ["mourning comfort"]})
        elif max_tokens == 800:
            text = json.dumps({"ids": self.ranked_ids})
        elif self.invalid:
            text = json.dumps({"answer": "A fabricated source [S99]"})
        else:
            text = json.dumps({"answer": "A gentle reflection on the retrieved test passage [S1].", "limitations": ["Synthetic transport fixture."]})
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


def configure_chat(application, invalid=False):
    connection = ControlledConnection(application, invalid)
    application.state.connections = connection
    application.state.chat = ChatService(application.state.database, connection)
    return connection


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
    saved = client.post("/api/v1/conversations", json={"title": "Explicit saved conversation", "session_id": turn["session_id"]})
    assert saved.status_code == 201, saved.text
    conversation = client.get("/api/v1/conversations/" + saved.json()["id"]).json()
    assert len(conversation["turns"]) == 1
    assert conversation["turns"][0]["citations"] == turn["citations"]
    followup = client.post("/api/v1/chat", json={"message": "What can I reflect on?", "connection_id": "actual-test-boundary", "conversation_id": saved.json()["id"]})
    assert followup.status_code == 200, followup.text
    assert len(client.get("/api/v1/conversations/" + saved.json()["id"]).json()["turns"]) == 2
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
