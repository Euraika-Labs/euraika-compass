"""Temporary, moderator-controlled discussions over a fixed evidence snapshot."""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from compass.adapters.base import AdapterError
from compass.chat import COLLECTIONS, while_connected
from compass.errors import APIError
from compass.personas import ROUNDTABLE_PERSONAS
from compass.roundtable_allocation import rank_roundtable_routes

router = APIRouter(prefix="/api/v1/roundtables", tags=["roundtable"])


class ParticipantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(default="", max_length=80)
    perspective: str = Field(default="", max_length=300)
    persona_id: str
    connection_id: str | None = Field(default=None, min_length=1, max_length=100)
    pinned: StrictBool = False

    @model_validator(mode="after")
    def validate_pin(self):
        if self.pinned and self.connection_id is None:
            raise ValueError("Choose a model before pinning the assignment.")
        return self


class RoundtableCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    topic: str = Field(min_length=1, max_length=10_000)
    language: str = Field(default="auto", min_length=2, max_length=40)
    participants: list[ParticipantCreate] = Field(min_length=2, max_length=4)
    collection_filter: list[str] = Field(default_factory=list, max_length=3)
    source_ids: list[UUID] | None = Field(default=None, max_length=50)
    web_research: StrictBool = False
    manuscript_dossier_id: UUID | None = None
    manuscript_revision_ids: list[UUID] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def validate_scope(self):
        if any(item.persona_id not in ROUNDTABLE_PERSONAS for item in self.participants):
            raise ValueError("Choose a known persona for each participant.")
        names = [item.name or f"AI participant {i}" for i, item in enumerate(self.participants, 1)]
        if len({name.casefold() for name in names}) != len(names):
            raise ValueError("Give each participant a distinct name.")
        if set(self.collection_filter) - COLLECTIONS:
            raise ValueError("Choose a known collection.")
        if bool(self.manuscript_dossier_id) != bool(self.manuscript_revision_ids):
            raise ValueError("Choose a dossier and at least one saved manuscript reading.")
        if len(set(self.manuscript_revision_ids)) != len(self.manuscript_revision_ids):
            raise ValueError("Choose each manuscript reading only once.")
        return self


class SpeakingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    expected_revision: int = Field(ge=0)
    moderator_note: str = Field(default="", max_length=2000)
    allow_manuscript_cloud: StrictBool = False


class TurnRequest(SpeakingRequest):
    participant_id: UUID
    synthesis: StrictBool = False


class RoundRequest(SpeakingRequest):
    participant_ids: list[UUID] = Field(min_length=1, max_length=4)


class AssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    expected_revision: int = Field(ge=0)
    connection_id: str | None = Field(default=None, min_length=1, max_length=100)
    pinned: StrictBool

    @model_validator(mode="after")
    def validate_pin(self):
        if self.pinned and self.connection_id is None:
            raise ValueError("Choose a model before pinning the assignment.")
        return self


@dataclass
class Room:
    id: str
    topic: str
    language: str
    scope: dict
    participants: list[dict]
    turns: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    evidence_sha256: str | None = None
    grounding: dict | None = None
    source_warnings: list[str] = field(default_factory=list)
    shared_with_cloud: bool = False
    stopped: bool = False
    task: asyncio.Task | None = None
    active: str | None = None
    revision: int = 0
    touched: float = field(default_factory=time.monotonic)

    def update(self):
        self.revision += 1
        self.touched = time.monotonic()

    def snapshot(self):
        return {
            "id": self.id,
            "topic": self.topic,
            "language": self.language,
            "scope": self.scope,
            "participants": [{key: value for key, value in item.items() if key != "signature"}
                             for item in self.participants],
            "turns": list(self.turns),
            "evidence": self.evidence,
            "evidence_version": 1 if self.evidence_sha256 is not None else None,
            "evidence_sha256": self.evidence_sha256,
            "grounding": self.grounding,
            "status": "stopped" if self.stopped else "running" if self.task else "awaiting_moderator",
            "active_participant_id": self.active,
            "revision": self.revision,
        }


class RoundtableService:
    def __init__(self, chat, connections):
        self.chat = chat
        self.connections = connections
        self.rooms: dict[str, Room] = {}
        self.allocation_gate = asyncio.Semaphore(2)

    def _cleanup(self):
        cutoff = time.monotonic() - 1800
        for key, room in list(self.rooms.items()):
            if room.task is None and room.touched < cutoff:
                del self.rooms[key]

    def room(self, room_id):
        self._cleanup()
        room = self.rooms.get(str(room_id))
        if room is None:
            raise APIError(404, "roundtable_not_found", "This temporary roundtable is unavailable.")
        room.touched = time.monotonic()
        return room

    def _route(self, connection_id):
        try:
            signature = self.connections.signature(connection_id)
            route = self.connections.get(connection_id)
            if self.connections.signature(connection_id) != signature:
                raise APIError(409, "connection_changed", "The selected connection changed.")
        except AdapterError as exc:
            raise APIError(409, exc.code, exc.message) from exc
        if not route["enabled"] or not route["configured"] or route.get("available") is False:
            raise APIError(409, "connection_unavailable", "Choose an enabled and configured model.")
        if not route["local"] and self.connections.settings()["local_only"]:
            raise APIError(409, "local_only", "Local-only mode blocks this cloud model.")
        return {key: route[key] for key in ("model_id", "provider", "local")} | {
            "connection_id": connection_id, "signature": signature,
        }

    async def _allocate(self, personas, language, *, allow_cloud):
        candidates = {}
        for item in self.connections.metadata():
            try:
                route = self._route(item["id"])
            except APIError:
                continue
            if route["local"] or allow_cloud:
                candidates[item["id"]] = route
        if not candidates:
            raise APIError(
                409, "roundtable_no_eligible_connection",
                "No connected model can be assigned under this roundtable's source and processing settings.",
            )
        async with self.allocation_gate:
            ranked = await rank_roundtable_routes(self.connections, list(candidates.values()), personas, language)
        allocation = {}
        for persona in personas:
            connection_id, basis = ranked[persona]
            route = self._route(connection_id)
            if route != candidates[connection_id]:
                raise APIError(409, "connection_changed", "The selected connection changed. Choose the assignment again.")
            allocation[persona] = {**route, "allocation": "automatic", "allocation_basis": basis}
        return allocation

    async def create(self, body):
        self._cleanup()
        if len(self.rooms) >= 32:
            raise APIError(429, "roundtable_limit", "The temporary roundtable limit was reached.")
        scope = body.model_dump(mode="json", exclude={"topic", "language", "participants"})
        manual = {item.connection_id: self._route(item.connection_id) for item in body.participants if item.connection_id}
        auto = list(dict.fromkeys(item.persona_id for item in body.participants if item.connection_id is None))
        allocation = {}
        if auto:
            allow_cloud = not self.connections.settings()["local_only"] and self.chat.roundtable_cloud_allowed(scope)
            if not allow_cloud and any(not route["local"] for route in manual.values()):
                raise APIError(403, "roundtable_source_restricted", "Choose eligible sources or a local roster.")
            allocation = await self._allocate(auto, body.language, allow_cloud=allow_cloud)
            for connection_id, route in manual.items():
                if self._route(connection_id) != route:
                    raise APIError(409, "connection_changed", "A selected connection changed. Create the roundtable again.")
            if any(not route["local"] for route in (*manual.values(), *allocation.values())):
                if not self.chat.roundtable_cloud_allowed(scope):
                    raise APIError(403, "roundtable_source_restricted", "Choose eligible sources or a local roster.")
            if len(self.rooms) >= 32:
                raise APIError(429, "roundtable_limit", "The temporary roundtable limit was reached.")
        participants = [{
            **(allocation[item.persona_id] if item.connection_id is None else {
                **manual[item.connection_id], "allocation": "manual", "allocation_basis": "moderator",
            }),
            "id": str(uuid4()), "name": item.name or f"AI participant {i}",
            "persona_id": item.persona_id, "perspective": item.perspective, "pinned": item.pinned,
            "status": "ready", "last_error": None,
        } for i, item in enumerate(body.participants, 1)]
        room = Room(str(uuid4()), body.topic, body.language, scope, participants)
        self.rooms[room.id] = room
        return room.snapshot()

    @staticmethod
    def _idle(room, expected_revision):
        if room.stopped:
            raise APIError(409, "roundtable_stopped", "This roundtable has ended.")
        if room.task:
            raise APIError(409, "roundtable_busy", "Wait for the current contribution or cancel it.")
        if room.revision != expected_revision:
            raise APIError(409, "roundtable_changed", "Refresh the roundtable and choose the speaker again.")

    @staticmethod
    def _participant(room, participant_id):
        participant = next((item for item in room.participants if item["id"] == str(participant_id)), None)
        if participant is None:
            raise APIError(404, "participant_not_found", "This participant is unavailable.")
        return participant

    async def assign(self, room, participant_id, body):
        self._idle(room, body.expected_revision)
        participant = self._participant(room, participant_id)
        same = body.connection_id == participant["connection_id"]
        if participant["pinned"] and not same and (body.pinned or body.connection_id is None):
            raise APIError(409, "roundtable_pinned", "Release the pinned assignment before choosing another model.")
        if same and (participant["pinned"] or body.pinned):
            if participant["pinned"] != body.pinned:
                participant["pinned"] = body.pinned
                room.update()
            return room.snapshot()
        if body.connection_id is None:
            allow_cloud = not self.connections.settings()["local_only"] and (
                room.shared_with_cloud if room.evidence_sha256 is not None
                else self.chat.roundtable_cloud_allowed(room.scope)
            )
            persona = participant["persona_id"]
            route = (await self._allocate([persona], room.language, allow_cloud=allow_cloud))[persona]
            self._idle(room, body.expected_revision)
        else:
            route = {
                **self._route(body.connection_id), "allocation": "manual", "allocation_basis": "moderator",
            }
        if not route["local"]:
            if room.evidence_sha256 is not None and not room.shared_with_cloud:
                raise APIError(403, "roundtable_source_restricted", "Start a new roundtable for cloud processing.")
            if room.evidence_sha256 is None and not self.chat.roundtable_cloud_allowed(room.scope):
                raise APIError(403, "roundtable_source_restricted", "Choose a local model for these sources.")
        participant.update(route, pinned=body.pinned, status="ready", last_error=None)
        room.update()
        return room.snapshot()

    @staticmethod
    def _pause(room, participant, exc):
        participant.update(status="paused", last_error={"code": exc.code, "message": exc.message})
        room.update()

    async def speak(self, room, participant_ids, body, *, synthesis=False):
        self._idle(room, body.expected_revision)
        if len(set(participant_ids)) != len(participant_ids):
            raise APIError(422, "duplicate_participant", "Choose each speaker only once per round.")
        if len(room.turns) + len(participant_ids) > 40:
            raise APIError(409, "roundtable_turn_limit", "This roundtable has reached its contribution limit.")
        if synthesis and len(room.turns) < 2:
            raise APIError(422, "roundtable_needs_contributions", "Add at least two contributions before asking for a synthesis.")
        participants = [self._participant(room, item) for item in participant_ids]
        if any(item["status"] != "ready" for item in participants):
            raise APIError(409, "roundtable_assignment_paused", "Review the paused assignment before asking it to speak.")
        has_manuscripts = (any(item.get("kind") == "manuscript" for item in room.evidence)
                           if room.evidence_sha256 is not None else bool(room.scope["manuscript_dossier_id"]))
        consent_routes = room.participants if room.evidence_sha256 is None else participants
        if has_manuscripts and any(not item["local"] for item in consent_routes) and not body.allow_manuscript_cloud:
            raise APIError(403, "manuscript_cloud_consent_required", "Confirm sharing permitted excerpts before starting.")

        task = asyncio.current_task()
        room.task = task
        room.update()
        turns = []
        try:
            for participant in participants:
                if room.task is not task:
                    break
                turn = await self._speak_one(room, participant, task, body, synthesis)
                if turn is not None:
                    turns.append(turn)
        except asyncio.CancelledError:
            if room.task is task:
                raise
        finally:
            if room.task is task:
                self._clear_speaker(room)
        return {"room": room.snapshot(), "turns": turns}

    async def _speak_one(self, room, participant, task, body, synthesis):
        participant["status"] = "speaking"
        room.active = participant["id"]
        room.update()
        scope = {**room.scope, "topic": room.topic, "language": room.language}
        try:
            route = self._route(participant["connection_id"])
            if route["signature"] != participant["signature"]:
                raise APIError(409, "connection_changed", "Review the changed connection before continuing.")
            if room.evidence_sha256 is None:
                shared_with_cloud = any(not item["local"] for item in room.participants)
                prepared = await self.chat.prepare_roundtable_evidence(
                    scope, participant, external_processing=shared_with_cloud,
                    expected_signature=participant["signature"], allow_manuscript_cloud=body.allow_manuscript_cloud,
                )
                if room.task is not task:
                    return None
                evidence = prepared["evidence"]
                serialized = json.dumps(evidence, sort_keys=True, ensure_ascii=False, default=str)
                room.evidence_sha256 = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
                room.evidence = evidence
                room.grounding = prepared["grounding"]
                room.source_warnings = prepared["warnings"]
                room.language = prepared["language"]
                room.shared_with_cloud = shared_with_cloud
                room.update()
            reply = await self.chat.roundtable_reply(
                {**scope, "resolved_language": room.language, "synthesis": synthesis},
                participant, evidence=room.evidence, history=room.turns,
                moderator_note=body.moderator_note, expected_signature=participant["signature"],
                allow_manuscript_cloud=body.allow_manuscript_cloud,
            )
        except (AdapterError, APIError) as exc:
            if room.task is task:
                self._pause(room, participant, exc)
            if isinstance(exc, AdapterError):
                raise APIError(409, exc.code, exc.message) from exc
            raise
        if room.task is not task:
            return None
        turn = {
            **reply, "id": str(uuid4()), "participant_id": participant["id"], "name": participant["name"],
            "connection_id": participant["connection_id"], "persona_id": participant["persona_id"],
            "moderator_note": body.moderator_note, "request_revision": body.expected_revision, "synthesis": synthesis,
            "warnings": [*room.source_warnings, *reply["warnings"]], "grounding": room.grounding,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        room.turns.append(turn)
        participant["status"] = "ready"
        room.active = None
        room.update()
        return turn

    @staticmethod
    def _clear_speaker(room):
        for participant in room.participants:
            if participant["status"] == "speaking":
                participant["status"] = "ready"
        room.task = None
        room.active = None
        room.update()

    def cancel(self, room, *, stop=False):
        task = room.task
        if stop:
            room.stopped = True
        if task or stop:
            self._clear_speaker(room)
        if task:
            task.cancel()
        return room.snapshot()


def _service(request):
    return request.app.state.roundtable


@router.post("", status_code=201)
async def create_roundtable(body: RoundtableCreate, request: Request):
    if not request.app.state.database.ready()[0]:
        raise APIError(503, "database_unavailable", "Research storage is unavailable.")
    return await while_connected(request, _service(request).create(body))


@router.get("/{room_id}")
async def get_roundtable(room_id: UUID, request: Request):
    return _service(request).room(room_id).snapshot()


@router.post("/{room_id}/turns")
async def roundtable_turn(room_id: UUID, body: TurnRequest, request: Request):
    service = _service(request)
    result = await while_connected(request, service.speak(
        service.room(room_id), [body.participant_id], body, synthesis=body.synthesis,
    ))
    return {"room": result["room"], "turn": result["turns"][0] if result["turns"] else None}


@router.post("/{room_id}/rounds")
async def roundtable_round(room_id: UUID, body: RoundRequest, request: Request):
    service = _service(request)
    return await while_connected(request, service.speak(service.room(room_id), body.participant_ids, body))


@router.patch("/{room_id}/participants/{participant_id}")
async def assign_participant(room_id: UUID, participant_id: UUID, body: AssignmentRequest, request: Request):
    service = _service(request)
    return await while_connected(request, service.assign(service.room(room_id), participant_id, body))


@router.post("/{room_id}/cancel")
async def cancel_roundtable(room_id: UUID, request: Request):
    service = _service(request)
    return service.cancel(service.room(room_id))


@router.post("/{room_id}/stop")
async def stop_roundtable(room_id: UUID, request: Request):
    service = _service(request)
    return service.cancel(service.room(room_id), stop=True)
