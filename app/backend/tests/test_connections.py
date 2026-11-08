import asyncio
import json
import os

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from compass.adapters.base import AdapterError
from compass.connections import ConnectionStore, router
from compass.errors import install_error_handlers


@pytest.fixture
def transport(monkeypatch):
    original = httpx.AsyncClient
    requests = []
    replies = []

    async def handle(request):
        requests.append(request)
        reply = replies.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        return reply

    def client(**kwargs):
        assert kwargs["follow_redirects"] is False
        assert kwargs["trust_env"] is False
        return original(transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr("compass.connections.httpx.AsyncClient", client)
    return requests, replies


def add(store, provider="local", **extra):
    return store.create(
        title="My research model", provider=provider, model_id="account-model", **extra
    )


def test_private_atomic_persistence_and_safe_metadata(tmp_path):
    store = ConnectionStore(tmp_path, environ={})
    item = add(store, "openai", api_key="private-test-key")
    assert item["configured"] and item["api_key_set"]
    assert store.settings() == {"local_only": True}
    assert "private-test-key" not in json.dumps(store.metadata())
    assert "api_key" not in item
    reopened = ConnectionStore(tmp_path, environ={})
    assert reopened.get(item["id"]) == item
    assert len(list(tmp_path.rglob("*.json"))) == 1
    assert not list(tmp_path.rglob("*.tmp"))
    if os.name != "nt":
        assert reopened.path.stat().st_mode & 0o077 == 0


def test_explicit_environment_keys_without_invented_models(tmp_path):
    store = ConnectionStore(tmp_path, environ={"OPENAI_API_KEY": "environment-test-key"})
    assert store.metadata() == []
    item = add(store, "openai")
    assert item["api_key_set"] and item["configured"]
    assert "environment-test-key" not in store.path.read_text()
    store.patch(item["id"], api_key="")
    assert not store.get(item["id"])["configured"]
    assert not store.get(item["id"])["api_key_set"]


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/v1",
        "http://192.168.1.5:8080/v1",
        "http://user:password@127.0.0.1/v1",
        "http://127.0.0.1/v1?key=secret",
        "http://127.0.0.1/v1#secret",
        "http://localhost.evil.example/v1",
    ],
)
def test_local_urls_cannot_send_to_remote_or_embed_credentials(tmp_path, url):
    with pytest.raises(AdapterError, match="loopback"):
        add(ConnectionStore(tmp_path, environ={}), base_url=url)


def test_cloud_hosts_and_provider_changes_do_not_reuse_secrets(tmp_path):
    store = ConnectionStore(tmp_path, environ={})
    item = add(store, "mistral", api_key="mistral-private")
    with pytest.raises(AdapterError):
        store.patch(item["id"], base_url="https://evil.example/v1")
    changed = store.patch(item["id"], provider="openai")
    assert changed["base_url"] == "https://api.openai.com/v1"
    assert not changed["api_key_set"]
    assert not changed["configured"]


@pytest.mark.asyncio
async def test_policy_and_current_enabled_state_gate_every_dispatch(tmp_path, transport):
    store = ConnectionStore(tmp_path, environ={})
    item = add(store, "openai", api_key="private-key")
    with pytest.raises(AdapterError) as blocked:
        await store.complete(item["id"], [{"role": "user", "content": "Question"}])
    assert blocked.value.code == "local_only"
    store.set_local_only(False)
    store.patch(item["id"], enabled=False)
    for operation in [store.test, store.models]:
        with pytest.raises(AdapterError) as disabled:
            await operation(item["id"])
        assert disabled.value.code == "connection_disabled"
    assert transport[0] == []
    assert ConnectionStore(tmp_path, environ={}).settings() == {"local_only": False}


@pytest.mark.asyncio
async def test_openai_responses_body_and_actual_output(tmp_path, transport):
    store = ConnectionStore(tmp_path, environ={"COMPASS_LOCAL_ONLY": "false"})
    item = add(store, "openai", api_key="private-key")
    transport[1].append(
        httpx.Response(
            200,
            json={
                "model": "actual-model-version",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Evidence-based answer"}],
                    }
                ],
                "usage": {"input_tokens": 20, "output_tokens": 7, "total_tokens": 27},
            },
        )
    )
    result = await store.complete(
        item["id"],
        [{"role": "system", "content": "Be neutral"}, {"role": "user", "content": "Question"}],
        123,
    )
    request = transport[0][0]
    body = json.loads(request.content)
    assert str(request.url) == "https://api.openai.com/v1/responses"
    assert body["max_output_tokens"] == 123 and body["store"] is False
    assert body["input"][0] == {"role": "system", "content": "Be neutral"}
    assert "response_format" not in body and "tools" not in body
    assert result == {
        "text": "Evidence-based answer",
        "model_id": "actual-model-version",
        "usage": {"input_tokens": 20, "output_tokens": 7, "total_tokens": 27},
    }


@pytest.mark.asyncio
async def test_anthropic_messages_separate_system_and_text_only(tmp_path, transport):
    store = ConnectionStore(tmp_path, environ={"COMPASS_LOCAL_ONLY": "false"})
    item = add(store, "anthropic", api_key="private-key")
    transport[1].append(
        httpx.Response(
            200,
            json={
                "model": "actual-claude",
                "content": [
                    {"type": "thinking", "thinking": "Do not expose reasoning"},
                    {"type": "text", "text": "Attributed answer"},
                ],
                "usage": {"input_tokens": 10, "output_tokens": 3},
            },
        )
    )
    result = await store.complete(
        item["id"],
        [
            {"role": "system", "content": "Neutral instruction"},
            {"role": "user", "content": "Question"},
        ],
    )
    request = transport[0][0]
    body = json.loads(request.content)
    assert str(request.url) == "https://api.anthropic.com/v1/messages"
    assert body["system"] == "Neutral instruction"
    assert body["messages"] == [{"role": "user", "content": "Question"}]
    assert request.headers["anthropic-version"] == "2026-10-21"
    assert result["text"] == "Attributed answer"


@pytest.mark.parametrize(
    "provider,expected",
    [
        ("local", "http://127.0.0.1:8081/v1/chat/completions"),
        ("mistral", "https://api.mistral.ai/v1/chat/completions"),
        ("openrouter", "https://openrouter.ai/api/v1/chat/completions"),
        ("alibaba", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"),
        ("minimax", "https://api.minimax.io/v1/chat/completions"),
    ],
)
@pytest.mark.asyncio
async def test_compatible_provider_transports(tmp_path, transport, provider, expected):
    store = ConnectionStore(tmp_path, environ={"COMPASS_LOCAL_ONLY": "false"})
    item = add(store, provider, api_key="private-key")
    transport[1].append(
        httpx.Response(
            200,
            json={
                "model": "account-model",
                "choices": [{"message": {"content": [{"type": "text", "text": "Visible answer"}]}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            },
        )
    )
    result = await store.complete(item["id"], [{"role": "user", "content": "Question"}], 150)
    assert str(transport[0][0].url) == expected
    body = json.loads(transport[0][0].content)
    assert body["model"] == "account-model" and body["max_tokens"] == 150
    assert body["stream"] is False
    assert result["text"] == "Visible answer"


@pytest.mark.asyncio
async def test_actual_model_listing_and_explicit_test(tmp_path, transport):
    store = ConnectionStore(tmp_path, environ={})
    item = add(store)
    transport[1].append(httpx.Response(200, json={"data": [{"id": "served-model"}]}))
    assert (await store.models(item["id"]))["items"] == [
        {"id": "served-model", "title": "served-model"}
    ]
    transport[1].append(
        httpx.Response(
            200, json={"model": "served-model", "choices": [{"message": {"content": "OK"}}]}
        )
    )
    result = await store.test(item["id"])
    assert result["ok"] and result["model_id"] == "served-model"
    assert json.loads(transport[0][1].content)["max_tokens"] <= 128


@pytest.mark.asyncio
async def test_error_payloads_redirects_and_large_responses_are_never_echoed(tmp_path, transport):
    store = ConnectionStore(tmp_path, environ={})
    item = add(store)
    for response, code in [
        (httpx.Response(401, text="private-key private prompt"), "provider_authentication"),
        (httpx.Response(302, headers={"location": "https://evil.example"}), "provider_redirect"),
        (httpx.Response(200, text="private prompt"), "provider_response"),
        (httpx.Response(200, content=b"x" * (4 * 1024 * 1024 + 1)), "response_too_large"),
    ]:
        transport[1].append(response)
        with pytest.raises(AdapterError) as error:
            await store.complete(item["id"], [{"role": "user", "content": "private prompt"}])
        assert error.value.code == code
        assert "private" not in str(error.value)


@pytest.mark.asyncio
async def test_cancellation_propagates_without_a_retry(tmp_path, transport):
    store = ConnectionStore(tmp_path, environ={})
    item = add(store)
    transport[1].append(asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        await store.complete(item["id"], [{"role": "user", "content": "Question"}])
    assert len(transport[0]) == 1


def test_connection_router_redacts_keys_and_validates_boolean_policy(tmp_path):
    application = FastAPI()
    application.state.connections = ConnectionStore(tmp_path, environ={})
    install_error_handlers(application)
    application.include_router(router)
    with TestClient(application) as client:
        response = client.post(
            "/api/v1/connections",
            json={
                "title": "My model",
                "provider": "mistral",
                "model_id": "account-model",
                "api_key": "private-test-key",
                "enabled": True,
            },
        )
        assert response.status_code == 200
        assert "private-test-key" not in response.text
        assert response.json()["api_key_set"]
        assert client.get("/api/v1/connections").json()["items"][0]["id"] == response.json()["id"]
        assert client.patch("/api/v1/chat-settings", json={"local_only": False}).json() == {
            "local_only": False
        }
        invalid = client.patch("/api/v1/chat-settings", json={"local_only": "false"})
        assert invalid.status_code == 422
        invalid_key = client.post(
            "/api/v1/connections",
            json={
                "title": "My model",
                "provider": "mistral",
                "model_id": "account-model",
                "api_key": {"invalid": "private-test-key"},
            },
        )
        assert invalid_key.status_code == 422 and "private-test-key" not in invalid_key.text


@pytest.mark.asyncio
async def test_mistral_model_listing_filters_ocr_and_test_uses_exact_selected_model(
    tmp_path, transport
):
    store = ConnectionStore(tmp_path, environ={"MISTRAL_API_KEY": "environment-key"})
    item = add(store, "mistral")
    store.set_local_only(False)
    transport[1].append(
        httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "account-chat",
                        "name": "My chat",
                        "capabilities": {"completion_chat": True},
                    },
                    {"id": "account-ocr", "capabilities": {"completion_chat": False}},
                ]
            },
        )
    )
    listing = await store.models(item["id"])
    assert listing["items"] == [{"id": "account-chat", "title": "My chat"}]
    assert str(transport[0][0].url) == "https://api.mistral.ai/v1/models"
    store.patch(item["id"], model_id="account-chat")
    transport[1].append(
        httpx.Response(
            200, json={"model": "account-chat-version", "choices": [{"message": {"content": "OK"}}]}
        )
    )
    assert (await store.test(item["id"]))["ok"]
    assert json.loads(transport[0][1].content)["model"] == "account-chat"


@pytest.mark.asyncio
async def test_openrouter_lists_account_filtered_models(tmp_path, transport):
    store = ConnectionStore(tmp_path, environ={"COMPASS_LOCAL_ONLY": "false"})
    item = add(store, "openrouter", api_key="private-key")
    transport[1].append(httpx.Response(200, json={"data": [{"id": "available/model"}]}))
    assert (await store.models(item["id"]))["items"][0]["id"] == "available/model"
    assert str(transport[0][0].url) == "https://openrouter.ai/api/v1/models/user"


@pytest.mark.asyncio
async def test_missing_keys_and_unsupported_listing_never_make_requests(tmp_path, transport):
    store = ConnectionStore(tmp_path, environ={"COMPASS_LOCAL_ONLY": "false"})
    item = add(store, "mistral")
    assert not item["configured"]
    with pytest.raises(AdapterError) as error:
        await store.test(item["id"])
    assert error.value.code == "missing_api_key"
    other = add(store, "alibaba", api_key="private-key")
    with pytest.raises(AdapterError) as error:
        await store.models(other["id"])
    assert error.value.code == "model_listing_unsupported"
    assert transport[0] == []


def test_failed_atomic_write_preserves_saved_and_in_memory_state(tmp_path, monkeypatch):
    store = ConnectionStore(tmp_path, environ={})
    item = add(store)
    saved = store.path.read_bytes()

    def failed_replace(*_args):
        raise OSError("A private filesystem path must not be exposed")

    monkeypatch.setattr("compass.connections.os.replace", failed_replace)
    with pytest.raises(AdapterError) as error:
        store.patch(item["id"], model_id="changed-model")
    assert error.value.code == "connection_state"
    assert "filesystem path" not in str(error.value)
    assert store.get(item["id"])["model_id"] == "account-model"
    assert store.path.read_bytes() == saved
    assert not list(store.path.parent.glob("*.tmp"))


def test_internal_reader_environment_uses_known_keys_and_current_policy(tmp_path):
    store = ConnectionStore(
        tmp_path,
        environ={
            "OPENAI_API_KEY": "environment-openai-key",
            "MISTRAL_API_KEY": "environment-mistral-key",
            "CODEX_PRIVATE_VALUE": "must-not-be-copied",
        },
    )
    add(store, "mistral", api_key="disabled-key", enabled=False)
    chosen = add(store, "mistral", api_key="reader-private-key")
    values = store.reader_environ()
    assert values["MISTRAL_API_KEY"] == "reader-private-key"
    assert values["OPENAI_API_KEY"] == "environment-openai-key"
    assert values["COMPASS_LOCAL_ONLY"] == "true"
    assert "CODEX_PRIVATE_VALUE" not in values
    assert not any("ENABLED" in name for name in values)
    store.set_local_only(False)
    assert store.reader_environ()["COMPASS_LOCAL_ONLY"] == "false"
    store.patch(chosen["id"], enabled=False)
    assert store.reader_environ()["MISTRAL_API_KEY"] == "environment-mistral-key"
    assert "reader-private-key" not in json.dumps(store.metadata())


def test_mutations_refresh_readers_after_private_state_commit(tmp_path):
    application = FastAPI()
    store = ConnectionStore(tmp_path, environ={})
    application.state.connections = store
    observed = []

    def refresh():
        reopened = ConnectionStore(tmp_path, environ={})
        observed.append((reopened.metadata(), reopened.settings()))

    application.state.refresh_readers = refresh
    install_error_handlers(application)
    application.include_router(router)
    with TestClient(application) as client:
        created = client.post(
            "/api/v1/connections",
            json={
                "title": "Mistral",
                "provider": "mistral",
                "model_id": "account-model",
                "api_key": "private-key",
            },
        )
        assert created.status_code == 200
        connection_id = created.json()["id"]
        assert observed[0][0][0]["id"] == connection_id
        patched = client.patch(f"/api/v1/connections/{connection_id}", json={"enabled": False})
        assert patched.status_code == 200 and observed[1][0][0]["enabled"] is False
        assert client.patch("/api/v1/chat-settings", json={"local_only": False}).status_code == 200
        assert observed[2][1] == {"local_only": False}
        client.get("/api/v1/connections")
        client.get("/api/v1/chat-settings")
        client.patch(f"/api/v1/connections/{connection_id}", json={"enabled": "false"})
        assert len(observed) == 3


@pytest.mark.parametrize(
    "change",
    [
        {"model_id": "another-model"},
        {"base_url": "http://127.0.0.1:9099/v1"},
        {"enabled": False},
        {"api_key": "rotated-private-key"},
        {"provider": "mistral", "api_key": "mistral-private-key"},
        {"local_only": True},
    ],
)
@pytest.mark.asyncio
async def test_frozen_selection_rejects_every_material_change_before_network(
    tmp_path, transport, change
):
    store = ConnectionStore(tmp_path, environ={"COMPASS_LOCAL_ONLY": "false"})
    item = add(store, api_key="initial-private-key")
    frozen = store.signature(item["id"])
    assert "initial-private-key" not in frozen
    if "local_only" in change:
        store.set_local_only(change["local_only"])
    else:
        store.patch(item["id"], change)
    with pytest.raises(AdapterError) as error:
        await store.complete(
            item["id"], [{"role": "user", "content": "Question"}], expected_signature=frozen
        )
    assert error.value.code == "connection_changed"
    assert transport[0] == []
    assert frozen not in json.dumps(store.metadata())


@pytest.mark.asyncio
async def test_frozen_selection_accepts_title_changes_and_rechecks_at_dispatch(
    tmp_path, transport, monkeypatch
):
    store = ConnectionStore(tmp_path, environ={})
    item = add(store)
    frozen = store.signature(item["id"])
    store.patch(item["id"], title="A different label")
    assert store.signature(item["id"]) == frozen
    transport[1].append(
        httpx.Response(
            200,
            json={
                "model": "account-model",
                "choices": [{"message": {"content": "Visible answer"}}],
            },
        )
    )
    assert (
        await store.complete(
            item["id"], [{"role": "user", "content": "Question"}], expected_signature=frozen
        )
    )["text"] == "Visible answer"
    transport[0].clear()
    request = store._request

    async def change_before_dispatch(*args, **kwargs):
        store.patch(item["id"], api_key="new-private-key")
        return await request(*args, **kwargs)

    monkeypatch.setattr(store, "_request", change_before_dispatch)
    with pytest.raises(AdapterError) as error:
        await store.complete(
            item["id"], [{"role": "user", "content": "Question"}], expected_signature=frozen
        )
    assert error.value.code == "connection_changed"
    assert transport[0] == []


@pytest.mark.parametrize("effort", ["low", "medium", "high"])
@pytest.mark.asyncio
async def test_large_4_accepts_explicit_supported_reasoning_effort(tmp_path, transport, effort):
    store = ConnectionStore(tmp_path, environ={"COMPASS_LOCAL_ONLY": "false"})
    item = add(store, "mistral", api_key="private-key")
    store.patch(item["id"], model_id="mistral-large-4-0")
    transport[1].append(
        httpx.Response(
            200,
            json={
                "model": "mistral-large-4-0",
                "choices": [
                    {
                        "message": {
                            "content": [
                                {
                                    "type": "thinking",
                                    "thinking": [{"type": "text", "text": "Private reasoning"}],
                                },
                                {"type": "text", "text": "Visible answer"},
                            ]
                        }
                    }
                ],
                "usage": {"prompt_tokens": 20, "completion_tokens": 70},
            },
        )
    )
    result = await store.complete(
        item["id"],
        [{"role": "user", "content": "Question"}],
        max_tokens=8192,
        reasoning_effort=effort,
    )
    body = json.loads(transport[0][0].content)
    assert body["reasoning_effort"] == effort and body["max_tokens"] == 8192
    assert body["model"] == "mistral-large-4-0"
    assert result["text"] == "Visible answer"
    assert result["usage"]["completion_tokens"] == 70


@pytest.mark.parametrize("effort", ["none", "max", "HIGH", 1, True, ["high"]])
@pytest.mark.asyncio
async def test_invalid_reasoning_effort_never_makes_a_request(tmp_path, transport, effort):
    store = ConnectionStore(tmp_path, environ={"COMPASS_LOCAL_ONLY": "false"})
    item = add(store, "mistral", api_key="private-key")
    store.patch(item["id"], model_id="mistral-large-4-0")
    with pytest.raises(AdapterError) as error:
        await store.complete(
            item["id"], [{"role": "user", "content": "Question"}], reasoning_effort=effort
        )
    assert error.value.code == "invalid_reasoning_effort"
    assert transport[0] == []


@pytest.mark.parametrize("provider", ["local", "mistral", "openai"])
@pytest.mark.asyncio
async def test_reasoning_effort_requires_explicitly_supported_provider_and_model(
    tmp_path, transport, provider
):
    store = ConnectionStore(tmp_path, environ={"COMPASS_LOCAL_ONLY": "false"})
    item = add(store, provider, api_key="private-key")
    with pytest.raises(AdapterError) as error:
        await store.complete(
            item["id"], [{"role": "user", "content": "Question"}], reasoning_effort="high"
        )
    assert error.value.code == "invalid_reasoning_effort"
    assert transport[0] == []


@pytest.mark.parametrize("model_id", ["mistral-large-4", "mistral-large-4-0"])
@pytest.mark.asyncio
async def test_large_4_connection_test_has_bounded_low_effort_budget(tmp_path, transport, model_id):
    store = ConnectionStore(tmp_path, environ={"COMPASS_LOCAL_ONLY": "false"})
    item = add(store, "mistral", api_key="private-key")
    store.patch(item["id"], model_id=model_id)
    transport[1].append(
        httpx.Response(200, json={"model": model_id, "choices": [{"message": {"content": "OK"}}]})
    )
    result = await store.test(item["id"])
    body = json.loads(transport[0][0].content)
    assert body["reasoning_effort"] == "low" and body["max_tokens"] == 512
    assert body["model"] == model_id
    assert result["ok"] and result["model_id"] == model_id
