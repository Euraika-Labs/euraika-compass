import asyncio
import json
from uuid import UUID

import pytest

from compass.errors import APIError
from compass.roundtable import (
    AssignmentRequest,
    RoundtableCreate,
    RoundtableService,
    SpeakingRequest,
)


class Connections:
    changed = False

    def get(self, connection_id):
        return {
            "enabled": True, "configured": True, "local": connection_id == "local",
            "provider": "local" if connection_id == "local" else "mistral",
            "model_id": connection_id,
        }

    def signature(self, connection_id):
        return f"{connection_id}-{self.changed}"

    def settings(self):
        return {"local_only": False}


class Chat:
    def __init__(self):
        self.prepared = []
        self.replied = []

    def roundtable_cloud_allowed(self, scope):
        return True

    async def prepare_roundtable_evidence(self, scope, participant, **options):
        self.prepared.append((scope, participant["id"], options))
        return {
            "evidence": [{"id": "S1", "quote": "Test excerpt", "use_limits": {"external_processing": True}}],
            "grounding": {"collections": ["bible"]}, "warnings": [], "language": "nl",
        }

    async def roundtable_reply(self, scope, participant, *, evidence, history, **options):
        self.replied.append((scope, participant["id"], evidence, list(history), options))
        return {"answer": "Evidence [S1]", "citations": evidence, "warnings": [], "model_id": participant["model_id"]}


async def setup(chat=None, *, cloud=True, pinned=False, scope=None):
    chat = chat or Chat()
    connections = Connections()
    service = RoundtableService(chat, connections)
    opened = await service.create(RoundtableCreate(
        topic="Compare the passages",
        participants=[
            {"name": "Textual", "persona_id": "textual", "connection_id": "local", "pinned": pinned},
            {"name": "Critical", "persona_id": "critical", "connection_id": "cloud" if cloud else "local"},
        ],
        **(scope or {}),
    ))
    return service, service.room(opened["id"]), chat, connections


@pytest.mark.asyncio
async def test_explicit_round_and_synthesis_reuse_the_same_evidence_and_reject_replay():
    service, room, chat, _ = await setup()
    speakers = [UUID(item["id"]) for item in room.participants]
    command = SpeakingRequest(expected_revision=0, moderator_note="Compare these readings")
    assert not chat.replied and not chat.prepared
    result = await service.speak(room, speakers, command)
    assert [turn["participant_id"] for turn in result["turns"]] == [str(item) for item in speakers]
    assert [turn["request_revision"] for turn in result["turns"]] == [0, 0]
    assert len(chat.prepared) == 1
    assert chat.prepared[0][2]["external_processing"] is True
    assert chat.replied[0][2] is chat.replied[1][2]
    assert chat.replied[1][3][0]["participant_id"] == str(speakers[0])
    assert chat.replied[1][4]["moderator_note"] == "Compare these readings"
    assert result["room"]["status"] == "awaiting_moderator"
    assert "signature" not in result["room"]["participants"][0]
    assert result["room"]["evidence_version"] == 1
    with pytest.raises(APIError) as error:
        await service.speak(room, speakers, command)
    assert error.value.code == "roundtable_changed"
    assert len(chat.replied) == 2
    summary = await service.speak(room, [speakers[1]], SpeakingRequest(expected_revision=room.revision), synthesis=True)
    assert summary["turns"][0]["synthesis"]
    assert summary["turns"][0]["request_revision"] > result["turns"][0]["request_revision"]
    assert chat.replied[-1][0]["synthesis"]
    assert chat.replied[-1][0]["resolved_language"] == "nl"
    assert summary["room"]["evidence_sha256"] == result["room"]["evidence_sha256"]
    assert len(chat.prepared) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("stop", [False, True])
async def test_cancel_or_stop_during_reply_discards_late_output_and_never_advances(stop):
    entered = asyncio.Event()

    class SlowChat(Chat):
        async def roundtable_reply(self, *args, **options):
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                return await super().roundtable_reply(*args, **options)

    service, room, chat, _ = await setup(SlowChat())
    speakers = [UUID(item["id"]) for item in room.participants]
    command = SpeakingRequest(expected_revision=0)
    pending = asyncio.create_task(service.speak(room, speakers, command))
    await entered.wait()
    assert room.snapshot()["status"] == "running"
    snapshot = service.cancel(room, stop=stop)
    assert snapshot["status"] == ("stopped" if stop else "awaiting_moderator")
    assert (await pending)["turns"] == []
    assert room.turns == []
    assert len(chat.replied) == 1


@pytest.mark.asyncio
async def test_changed_pinned_route_pauses_without_eligible_replacement():
    service, room, chat, connections = await setup(pinned=True)
    participant_id = UUID(room.participants[0]["id"])
    connections.changed = True
    with pytest.raises(APIError) as error:
        await service.speak(room, [participant_id], SpeakingRequest(expected_revision=0))
    assert error.value.code == "connection_changed"
    assert room.participants[0]["status"] == "paused"
    assert not chat.replied and not chat.prepared
    with pytest.raises(APIError) as pinned:
        await service.assign(room, participant_id, AssignmentRequest(
            expected_revision=room.revision, connection_id="cloud", pinned=True,
        ))
    assert pinned.value.code == "roundtable_pinned"
    await service.assign(room, participant_id, AssignmentRequest(
        expected_revision=room.revision, connection_id="cloud", pinned=False,
    ))
    assert room.participants[0]["status"] == "ready"
    assert room.participants[0]["connection_id"] == "cloud"


@pytest.mark.asyncio
async def test_mixed_manuscript_consent_and_local_snapshot_cannot_add_cloud():
    service, room, chat, _ = await setup(scope={
        "manuscript_dossier_id": "1f85420a-9dcc-4a3c-b623-b24a58b4b7a7",
        "manuscript_revision_ids": ["2161c1a5-9e47-49d3-a5fd-a46cbd4c9093"],
    })
    with pytest.raises(APIError) as error:
        await service.speak(room, [UUID(room.participants[0]["id"])], SpeakingRequest(expected_revision=0))
    assert error.value.code == "manuscript_cloud_consent_required"
    assert not chat.prepared

    service, room, chat, _ = await setup(cloud=False)
    participant_id = UUID(room.participants[0]["id"])
    await service.speak(room, [participant_id], SpeakingRequest(expected_revision=0))
    assert chat.prepared[0][2]["external_processing"] is False
    with pytest.raises(APIError) as error:
        await service.assign(room, participant_id, AssignmentRequest(
            expected_revision=room.revision, connection_id="cloud", pinned=False,
        ))
    assert error.value.code == "roundtable_source_restricted"


def import_allocation_source(client, external_processing):
    imported = client.post("/api/v1/corpus/import", json={
        "title": "Synthetic allocation source",
        "source_type": "translation",
        "edition": {"title": "Synthetic edition", "language": "en", "revision": "1",
                    "collection_memberships": ["bible"]},
        "passages": [{"reference": "Testbook 1:1", "text": "Locally stored fixture passage."}],
        "use_limits": {"external_processing": external_processing},
    })
    assert imported.status_code == 201, imported.text
    return imported.json()["id"]


@pytest.mark.parametrize("local_only", [True, False], ids=["local-only-policy", "restricted-corpus-source"])
def test_automatic_roundtable_excludes_cloud_and_disabled_routes(postgres_app, monkeypatch, local_only):
    client, application, _ = postgres_app
    connections = application.state.connections
    connections.set_local_only(local_only)
    local = connections.create(title="Local QA", provider="local", model_id="local-model",
                               base_url="http://127.0.0.1:9999/v1")
    connections.create(title="Disabled QA", provider="local", model_id="disabled-model",
                       base_url="http://127.0.0.1:9999/v1", enabled=False)
    cloud = connections.create(title="Cloud QA", provider="mistral", model_id="cloud-model", api_key="fixture-key")

    async def unexpected_inference(*args, **kwargs):
        pytest.fail("One eligible connection must not invoke a model for allocation.")

    monkeypatch.setattr(connections, "complete", unexpected_inference)
    body = {
        "topic": "Compare the test passage",
        "source_ids": [import_allocation_source(client, external_processing=local_only)],
        "participants": [{"persona_id": "textual"}, {"persona_id": "critical", "connection_id": None}],
    }
    opened = client.post("/api/v1/roundtables", json=body)
    assert opened.status_code == 201, opened.text
    room = opened.json()
    assert room["turns"] == [] and room["evidence_version"] is None
    assert [(item["connection_id"], item["allocation"], item["allocation_basis"]) for item in room["participants"]] == [
        (local["id"], "automatic", "single_candidate"),
        (local["id"], "automatic", "single_candidate"),
    ]

    participant_id = room["participants"][0]["id"]
    override = client.patch(f"/api/v1/roundtables/{room['id']}/participants/{participant_id}", json={
        "expected_revision": room["revision"], "connection_id": cloud["id"], "pinned": True,
    })
    assert override.status_code == (409 if local_only else 403), override.text
    assert override.json()["error"]["code"] == ("local_only" if local_only else "roundtable_source_restricted")

    connections.patch(local["id"], enabled=False)
    unavailable = client.post("/api/v1/roundtables", json=body)
    assert unavailable.status_code == 409, unavailable.text
    assert unavailable.json()["error"]["code"] == "roundtable_no_eligible_connection"


def test_orchestrated_assignment_is_private_and_moderator_pin_survives_failure(postgres_app, monkeypatch):
    client, application, _ = postgres_app
    connections = application.state.connections
    connections.set_local_only(False)
    local = connections.create(title="Local private label", provider="local", model_id="qwen3-vl:8b",
                               base_url="http://127.0.0.1:9999/v1")
    cloud = connections.create(title="Cloud private label", provider="mistral", model_id="mistral-large-4-0",
                               api_key="fixture-secret-credential")
    source_id = import_allocation_source(client, external_processing=True)
    dispatched = []

    async def complete(connection_id, messages, *, expected_signature, **options):
        assert not dispatched, "No replacement or turn should invoke a model."
        dispatched.append(connection_id)
        assert connection_id == cloud["id"]
        assert expected_signature == connections.signature(connection_id)
        assert application.state.database.engine.pool.checkedout() == 0
        prompt = json.dumps(messages)
        for forbidden in ("Private discussion topic", "Private reader name", "Private perspective", source_id,
                          "Locally stored fixture passage", "private label", "127.0.0.1", "fixture-secret-credential",
                          local["id"], cloud["id"], expected_signature):
            assert forbidden not in prompt
        payload = json.loads(messages[-1]["content"])
        assert "source_verification" in payload["personas"]
        aliases = {model["model_id"]: alias for alias, model in payload["candidates"].items()}
        return {"text": json.dumps({
            "textual": aliases[cloud["model_id"]], "source_verification": aliases[local["model_id"]],
        })}

    monkeypatch.setattr(connections, "complete", complete)
    response = client.post("/api/v1/roundtables", json={
        "topic": "Private discussion topic",
        "language": "nl",
        "source_ids": [source_id],
        "participants": [
            {"persona_id": "textual", "name": "Private reader name", "perspective": "Private perspective"},
            {"persona_id": "source_verification"},
        ],
    })
    assert response.status_code == 201, response.text
    room = response.json()
    selected = room["participants"][0]
    assert [item["connection_id"] for item in room["participants"]] == [cloud["id"], local["id"]]
    assert all(item["allocation_basis"] == "orchestrator" for item in room["participants"])
    assert room["turns"] == []
    room_url = f"/api/v1/roundtables/{room['id']}"
    assignment_url = f"{room_url}/participants/{selected['id']}"

    def assign(snapshot, connection_id, pinned):
        return client.patch(assignment_url, json={
            "expected_revision": snapshot["revision"], "connection_id": connection_id, "pinned": pinned,
        })

    pinned = assign(room, cloud["id"], True)
    assert pinned.status_code == 200, pinned.text
    room = pinned.json()
    assert room["participants"][0]["pinned"]
    assert room["participants"][0]["allocation"] == "automatic"
    refused = assign(room, None, False)
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["code"] == "roundtable_pinned"

    connections.patch(cloud["id"], enabled=False)
    failed = client.post(f"{room_url}/turns", json={"participant_id": selected["id"], "expected_revision": room["revision"]})
    assert failed.status_code == 409, failed.text
    room = client.get(room_url).json()
    paused = room["participants"][0]
    assert paused["pinned"] and paused["status"] == "paused" and paused["connection_id"] == cloud["id"]
    assert room["turns"] == []

    released = assign(room, cloud["id"], False)
    assert released.status_code == 200, released.text
    room = released.json()
    assert not room["participants"][0]["pinned"]
    assert room["participants"][0]["connection_id"] == cloud["id"]
    replaced = assign(room, local["id"], True)
    assert replaced.status_code == 200, replaced.text
    updated = replaced.json()["participants"][0]
    assert updated["pinned"] and updated["status"] == "ready" and updated["connection_id"] == local["id"]
    assert updated["allocation"] == "manual" and updated["allocation_basis"] == "moderator"
    assert dispatched == [cloud["id"]]
