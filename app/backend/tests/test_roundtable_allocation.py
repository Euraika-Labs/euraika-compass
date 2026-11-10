import asyncio
import json

import pytest

from compass.adapters.base import AdapterError
from compass.roundtable_allocation import rank_roundtable_routes


class Connections:
    def __init__(self, answer=None, error=None):
        self.answer = answer
        self.error = error
        self.calls = []

    async def complete(self, connection_id, messages, **options):
        self.calls.append((connection_id, messages, options))
        if self.error:
            raise self.error
        return {"text": self.answer}


def route(connection_id, provider, model_id):
    return {
        "connection_id": connection_id,
        "provider": provider,
        "model_id": model_id,
        "local": provider == "local",
        "signature": "private-signature",
        "base_url": "http://localhost:11434/private",
        "title": "Private connection title",
        "api_key": "private-api-key",
    }


@pytest.mark.asyncio
async def test_orchestrator_ranks_personas_using_only_aliased_candidate_metadata():
    connections = Connections('{"textual":"C2","critical":"C1"}')
    candidates = [route("local-id", "local", "qwen3-vl:8b"), route("cloud-id", "mistral", "mistral-large-4-0")]
    result = await rank_roundtable_routes(connections, candidates, ["textual", "critical", "textual"], "ar")

    assert result == {"textual": ("cloud-id", "orchestrator"), "critical": ("local-id", "orchestrator")}
    [(connection_id, messages, options)] = connections.calls
    assert connection_id == "cloud-id"
    assert options["expected_signature"] == "private-signature"
    assert options["reasoning_effort"] == "low"
    assert options["max_tokens"] <= 1600
    data = json.loads(messages[-1]["content"])
    assert data["answer_language"] == "ar"
    assert list(data["personas"]) == ["textual", "critical"]
    assert data["candidates"] == {
        "C1": {"provider": "local", "model_id": "qwen3-vl:8b", "local": True},
        "C2": {"provider": "mistral", "model_id": "mistral-large-4-0", "local": False},
    }
    prompt = json.dumps(messages)
    for value in ("local-id", "cloud-id", "private-signature", "localhost", "private-api-key", "Private connection title"):
        assert value not in prompt


@pytest.mark.asyncio
@pytest.mark.parametrize("candidates, expected", [
    ([], {}),
    ([route("local-id", "local", "qwen3-vl:8b")], {"textual": ("local-id", "single_candidate")}),
])
async def test_single_or_no_eligible_candidate_requires_no_model_call(candidates, expected):
    connections = Connections()
    assert await rank_roundtable_routes(connections, candidates, ["textual"], "auto") == expected
    assert connections.calls == []


@pytest.mark.asyncio
async def test_unknown_alias_and_omitted_persona_fall_back_without_untrusted_metadata():
    connections = Connections('{"critical":"unknown-route","textual":"C2","invented":"C1"}')
    candidates = [route("first", "local", "http://localhost:11434/private"), route("second", "local", "qwen3:8b")]
    assert await rank_roundtable_routes(connections, candidates, ["textual", "critical", "wisdom"], "ar\nsecret") == {
        "textual": ("second", "orchestrator"),
        "critical": ("first", "configured_order"),
        "wisdom": ("first", "configured_order"),
    }
    [(_, messages, _)] = connections.calls
    data = json.loads(messages[-1]["content"])
    assert data["answer_language"] == "auto"
    assert data["candidates"]["C1"]["model_id"] is None
    assert "localhost" not in messages[-1]["content"]


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [AdapterError("provider_response", "Unreadable"), TimeoutError(), None])
async def test_unusable_ranking_preserves_configured_order(error):
    connections = Connections("unusable response", error)
    candidates = [route("first", "local", "model-a"), route("second", "local", "model-b")]
    assert await rank_roundtable_routes(connections, candidates, ["textual"], "nl") == {
        "textual": ("first", "configured_order"),
    }
    assert len(connections.calls) == 1


@pytest.mark.asyncio
async def test_known_allocator_failure_uses_another_eligible_route_without_retrying_it():
    connections = Connections(error=AdapterError("provider_rate_limit", "Quota exhausted"))
    candidates = [route("first", "mistral", "mistral-large-4-0"), route("second", "local", "model-b")]
    assert await rank_roundtable_routes(connections, candidates, ["textual", "critical"], "nl") == {
        "textual": ("second", "configured_order"),
        "critical": ("second", "configured_order"),
    }
    assert [call[0] for call in connections.calls] == ["first"]


@pytest.mark.asyncio
async def test_request_cancellation_is_not_converted_into_fallback():
    connections = Connections(error=asyncio.CancelledError())
    candidates = [route("first", "local", "model-a"), route("second", "local", "model-b")]
    with pytest.raises(asyncio.CancelledError):
        await rank_roundtable_routes(connections, candidates, ["textual"], "nl")
