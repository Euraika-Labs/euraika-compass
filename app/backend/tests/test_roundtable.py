import asyncio
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

    async def prepare_roundtable_evidence(self, scope, participant, **options):
        self.prepared.append((scope, participant["id"], options))
        return {
            "evidence": [{"id": "S1", "quote": "Test excerpt", "use_limits": {"external_processing": True}}],
            "grounding": {"collections": ["bible"]}, "warnings": [], "language": "nl",
        }

    async def roundtable_reply(self, scope, participant, *, evidence, history, **options):
        self.replied.append((scope, participant["id"], evidence, list(history), options))
        return {"answer": "Evidence [S1]", "citations": evidence, "warnings": [], "model_id": participant["model_id"]}


def setup(chat=None, *, cloud=True, pinned=False, scope=None):
    chat = chat or Chat()
    connections = Connections()
    service = RoundtableService(chat, connections)
    opened = service.create(RoundtableCreate(
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
    service, room, chat, _ = setup()
    speakers = [UUID(item["id"]) for item in room.participants]
    command = SpeakingRequest(expected_revision=0, moderator_note="Compare these readings")
    assert not chat.replied and not chat.prepared
    result = await service.speak(room, speakers, command)
    assert [turn["participant_id"] for turn in result["turns"]] == [str(item) for item in speakers]
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

    service, room, chat, _ = setup(SlowChat())
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
    service, room, chat, connections = setup(pinned=True)
    participant_id = UUID(room.participants[0]["id"])
    connections.changed = True
    with pytest.raises(APIError) as error:
        await service.speak(room, [participant_id], SpeakingRequest(expected_revision=0))
    assert error.value.code == "connection_changed"
    assert room.participants[0]["status"] == "paused"
    assert not chat.replied and not chat.prepared
    with pytest.raises(APIError) as pinned:
        service.assign(room, participant_id, AssignmentRequest(
            expected_revision=room.revision, connection_id="cloud", pinned=True,
        ))
    assert pinned.value.code == "roundtable_pinned"
    service.assign(room, participant_id, AssignmentRequest(
        expected_revision=room.revision, connection_id="cloud", pinned=False,
    ))
    assert room.participants[0]["status"] == "ready"
    assert room.participants[0]["connection_id"] == "cloud"


@pytest.mark.asyncio
async def test_mixed_manuscript_consent_and_local_snapshot_cannot_add_cloud():
    service, room, chat, _ = setup(scope={
        "manuscript_dossier_id": "1f85420a-9dcc-4a3c-b623-b24a58b4b7a7",
        "manuscript_revision_ids": ["2161c1a5-9e47-49d3-a5fd-a46cbd4c9093"],
    })
    with pytest.raises(APIError) as error:
        await service.speak(room, [UUID(room.participants[0]["id"])], SpeakingRequest(expected_revision=0))
    assert error.value.code == "manuscript_cloud_consent_required"
    assert not chat.prepared

    service, room, chat, _ = setup(cloud=False)
    participant_id = UUID(room.participants[0]["id"])
    await service.speak(room, [participant_id], SpeakingRequest(expected_revision=0))
    assert chat.prepared[0][2]["external_processing"] is False
    with pytest.raises(APIError) as error:
        service.assign(room, participant_id, AssignmentRequest(
            expected_revision=room.revision, connection_id="cloud", pinned=False,
        ))
    assert error.value.code == "roundtable_source_restricted"
