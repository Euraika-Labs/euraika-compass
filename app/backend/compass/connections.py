"""Private chat connections and explicit, bounded provider requests.

No discovery or inference happens during construction or metadata reads. Keys stay
in backend-only ``data/private/connections.json`` (or the supplied environment),
never in a DTO. The single-user backend must keep its data directory private.

Transport references checked against official documentation on 2026-11-08:
https://docs.mistral.ai/api/endpoint/models
https://docs.mistral.ai/inference/conversations/chat-completion
https://developers.openai.com/api/reference/resources/responses/methods/create
https://platform.claude.com/docs/en/api/messages/create
https://platform.claude.com/docs/en/api/models/list
https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion
https://openrouter.ai/docs/api/api-reference/models/list-models-filtered-by-user-provider-preferences-privacy-settings-and-guardrails
https://www.alibabacloud.com/help/en/model-studio/base-url
https://platform.minimax.io/docs/api-reference/text-openai-api
https://platform.minimax.io/docs/api-reference/models/openai/list-models
"""

import asyncio
import hashlib
import hmac
import json
import os
import tempfile
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictBool

from compass.adapters.base import AdapterError
from compass.errors import APIError

Provider = Literal["local", "mistral", "openrouter", "alibaba", "anthropic", "openai", "minimax"]
BASE_URLS = {
    "local": "http://127.0.0.1:8081/v1",
    "mistral": "https://api.mistral.ai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "alibaba": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "openai": "https://api.openai.com/v1",
    "minimax": "https://api.minimax.io/v1",
}
ALIBABA_BASE_URLS = {
    BASE_URLS["alibaba"],
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "https://dashscope-us.aliyuncs.com/compatible-mode/v1",
    "https://cn-hongkong.dashscope.aliyuncs.com/compatible-mode/v1",
}
KEY_ENV = {
    "local": "COMPASS_LOCAL_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "alibaba": "DASHSCOPE_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "minimax": "MINIMAX_API_KEY",
}
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_MESSAGES = 200
MAX_INPUT_CHARS = 400_000
MAX_OUTPUT_TOKENS = 16_000
ANTHROPIC_VERSION = "2026-10-21"
MISTRAL_LARGE_4_MODELS = {"mistral-large-4", "mistral-large-4-0"}


def _invalid(message="The connection contains invalid or missing fields."):
    return AdapterError("invalid_connection", message)


def _text(value, maximum, *, empty=False):
    if not isinstance(value, str) or len(value) > maximum or "\x00" in value:
        raise _invalid()
    value = value.strip()
    if not value and not empty:
        raise _invalid()
    return value


def _base_url(provider, value):
    value = BASE_URLS[provider] if value is None else _text(value, 500).rstrip("/")
    if provider != "local":
        allowed = ALIBABA_BASE_URLS if provider == "alibaba" else {BASE_URLS[provider]}
        if value not in allowed:
            raise _invalid("Choose an official endpoint for this cloud provider.")
        return value
    try:
        parsed = urlsplit(value)
        valid = (
            parsed.scheme in {"http", "https"}
            and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
            and parsed.port != 0
            and not any(part in {".", ".."} for part in parsed.path.split("/"))
            and "%" not in value
            and "\\" not in value
        )
    except ValueError:
        valid = False
    if not valid:
        raise _invalid("A local connection requires a loopback URL without credentials or queries.")
    return value


def _key(value):
    if isinstance(value, SecretStr):
        value = value.get_secret_value()
    if value is None:
        return None  # Use only the explicitly named provider environment variable.
    value = _text(value, 8192, empty=True)
    if any(char.isspace() for char in value) or any(not 32 <= ord(char) < 127 for char in value):
        raise _invalid("The API key contains invalid characters.")
    return value  # An explicit empty key clears it, including environment fallback.


class ConnectionStore:
    """One backend process owns this atomic, private JSON store.

    ``get`` and ``metadata`` return safe metadata only. ``create`` and ``patch``
    accept either a mapping or keyword fields. Model IDs always come from the
    user or a real provider listing; there are no fabricated default models.
    """

    def __init__(self, data_dir: Path, environ: Mapping[str, str] | None = None):
        self.path = Path(data_dir) / "private" / "connections.json"
        source = os.environ if environ is None else environ
        self._environ = {name: source.get(name, "") for name in KEY_ENV.values()}
        self._lock = threading.RLock()
        self._items = []
        self._local_only = str(source.get("COMPASS_LOCAL_ONLY", "true")).lower() != "false"
        if self.path.is_file():
            try:
                if self.path.stat().st_size > 1024 * 1024:
                    raise ValueError("Oversized state")
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict) or type(payload.get("local_only")) is not bool:
                    raise ValueError("Invalid state")
                items = payload.get("items")
                if not isinstance(items, list) or len(items) > 100:
                    raise ValueError("Invalid state")
                seen = set()
                for item in items:
                    if not isinstance(item, dict):
                        raise ValueError("Invalid item")
                    item_id = _text(item.get("id"), 100)
                    if item_id in seen:
                        raise ValueError("Duplicate item")
                    seen.add(item_id)
                    normalized = self._normalize({k: v for k, v in item.items() if k != "id"})
                    self._items.append({"id": item_id, **normalized})
                self._local_only = payload["local_only"]
            except (OSError, ValueError, TypeError, AdapterError):
                raise AdapterError(
                    "connection_state", "The private connection state could not be read."
                ) from None

    def _normalize(self, fields):
        if set(fields) - {"title", "provider", "model_id", "base_url", "enabled", "api_key"}:
            raise _invalid()
        provider = fields.get("provider")
        if not isinstance(provider, str) or provider not in BASE_URLS:
            raise _invalid("Choose a supported model provider.")
        enabled = fields.get("enabled", True)
        if type(enabled) is not bool:
            raise _invalid()
        return {
            "title": _text(fields.get("title"), 120),
            "provider": provider,
            "model_id": _text(fields.get("model_id"), 200),
            "base_url": _base_url(provider, fields.get("base_url")),
            "enabled": enabled,
            "api_key": _key(fields.get("api_key")),
        }

    def _find(self, connection_id):
        item = next((item for item in self._items if item["id"] == connection_id), None)
        if item is None:
            raise AdapterError("unknown_connection", "This connection was not found.")
        return item

    def _credential(self, item):
        value = item["api_key"]
        if value is None:
            value = self._environ[KEY_ENV[item["provider"]]]
        # Environment values receive the same validation, without exposing them.
        return _key(value) or ""

    def _metadata(self, item):
        key_set = bool(self._credential(item))
        local = item["provider"] == "local"
        return {
            key: item[key] for key in ("id", "title", "provider", "model_id", "base_url", "enabled")
        } | {
            "configured": local or key_set,
            "local": local,
            "api_key_set": key_set,
        }

    def metadata(self):
        with self._lock:
            return [self._metadata(item) for item in self._items]

    def get(self, connection_id):
        with self._lock:
            return self._metadata(self._find(connection_id))

    def settings(self):
        with self._lock:
            return {"local_only": self._local_only}

    def reader_environ(self):
        """Internal credential bridge for rebuilding image-reader adapters.

        This contains secrets: never serialize it into an API response or log.
        It supplies configuration only and never enables an OCR/vision route.
        """
        with self._lock:
            values = {**self._environ, "COMPASS_LOCAL_ONLY": str(self._local_only).lower()}
            for item in self._items:
                if item["provider"] == "mistral" and item["enabled"]:
                    key = self._credential(item)
                    if key:
                        values["MISTRAL_API_KEY"] = key
                        break
            return values

    def _signature(self, item):
        selection = {key: item[key] for key in ("provider", "model_id", "base_url", "enabled")}
        selection.update(credential=self._credential(item), local_only=self._local_only)
        return hashlib.sha256(json.dumps(selection, sort_keys=True).encode("utf-8")).hexdigest()

    def signature(self, connection_id):
        """Internal opaque selection token; never return it through the public API."""
        with self._lock:
            return self._signature(self._find(connection_id))

    def _save(self):
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if os.name != "nt":
                self.path.parent.chmod(0o700)
            descriptor, temporary = tempfile.mkstemp(
                prefix="connections-", suffix=".tmp", dir=self.path.parent
            )
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(
                    {"version": 1, "local_only": self._local_only, "items": self._items}, handle
                )
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        except OSError:
            raise AdapterError(
                "connection_state", "The private connection state could not be saved."
            ) from None
        finally:
            if temporary is not None:
                try:
                    Path(temporary).unlink(missing_ok=True)
                except OSError:
                    pass

    def create(self, data: Mapping | None = None, **fields):
        with self._lock:
            if len(self._items) >= 100:
                raise _invalid("The connection limit has been reached.")
            item = {"id": uuid4().hex, **self._normalize({**(data or {}), **fields})}
            self._items.append(item)
            try:
                self._save()
            except AdapterError:
                self._items.pop()
                raise
            return self._metadata(item)

    def patch(self, connection_id, data: Mapping | None = None, **fields):
        with self._lock:
            original = self._find(connection_id)
            changes = {**(data or {}), **fields}
            values = {k: v for k, v in original.items() if k != "id"}
            if "provider" in changes and changes["provider"] != original["provider"]:
                values.update(api_key=None, base_url=None)
            item = {"id": original["id"], **self._normalize({**values, **changes})}
            index = self._items.index(original)
            self._items[index] = item
            try:
                self._save()
            except AdapterError:
                self._items[index] = original
                raise
            return self._metadata(item)

    def set_local_only(self, value):
        if type(value) is not bool:
            raise _invalid("The local-only policy must be a boolean.")
        with self._lock:
            original = self._local_only
            self._local_only = value
            try:
                self._save()
            except AdapterError:
                self._local_only = original
                raise
            return self.settings()

    def _dispatch(self, connection_id, expected_signature=None):
        with self._lock:
            item = self._find(connection_id).copy()
            if expected_signature is not None and (
                not isinstance(expected_signature, str)
                or not hmac.compare_digest(self._signature(item), expected_signature)
            ):
                raise AdapterError(
                    "connection_changed",
                    "This connection or its processing policy changed. Submit the request again with the selected model.",
                )
            if not item["enabled"]:
                raise AdapterError("connection_disabled", "Enable this connection before using it.")
            if self._local_only and item["provider"] != "local":
                raise AdapterError("local_only", "Local-only mode blocks cloud model requests.")
            item["base_url"] = _base_url(item["provider"], item["base_url"])
            key = self._credential(item)
            if not key and item["provider"] != "local":
                raise AdapterError("missing_api_key", "Add an API key for this connection.")
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            if key:
                headers["Authorization"] = "Bearer " + key
            if item["provider"] == "anthropic":
                headers["anthropic-version"] = ANTHROPIC_VERSION
            return item, headers

    async def _request(
        self,
        method,
        connection_id,
        suffix,
        payload=None,
        *,
        expected=None,
        expected_signature=None,
    ):
        # Recheck the current connection and policy immediately before dispatch.
        item, headers = self._dispatch(connection_id, expected_signature)
        if expected is not None and any(
            item[key] != expected[key] for key in ("provider", "model_id", "base_url")
        ):
            raise AdapterError(
                "connection_changed",
                "This connection changed before dispatch. Submit the request again with the selected model.",
            )
        try:
            async with asyncio.timeout(90):
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(60, connect=10),
                    follow_redirects=False,
                    trust_env=False,
                ) as client:
                    async with client.stream(
                        method, item["base_url"] + suffix, headers=headers, json=payload
                    ) as response:
                        if 300 <= response.status_code < 400:
                            raise AdapterError(
                                "provider_redirect", "The provider returned an unexpected redirect."
                            )
                        if response.status_code in {401, 403}:
                            raise AdapterError(
                                "provider_authentication",
                                "The provider rejected this key or its model permissions.",
                            )
                        if response.status_code == 429:
                            raise AdapterError(
                                "provider_rate_limit",
                                "The provider quota or request rate limit was reached.",
                            )
                        if response.status_code in {404, 405} and method == "GET":
                            raise AdapterError(
                                "model_listing_unsupported",
                                "This endpoint does not support model listing. Enter a model ID from the provider account.",
                            )
                        if response.status_code >= 400:
                            raise AdapterError(
                                "provider_request",
                                "The provider could not process this request. Check the model ID, account access and request limits.",
                            )
                        content = bytearray()
                        async for chunk in response.aiter_bytes(chunk_size=65536):
                            content.extend(chunk)
                            if len(content) > MAX_RESPONSE_BYTES:
                                raise AdapterError(
                                    "response_too_large",
                                    "The provider response exceeded the size limit.",
                                )
            result = json.loads(content)
            if not isinstance(result, dict) or "error" in result:
                raise ValueError("Invalid provider result")
            return result
        except (httpx.TimeoutException, TimeoutError):
            raise AdapterError(
                "provider_timeout", "The provider did not respond before the timeout."
            ) from None
        except httpx.HTTPError:
            raise AdapterError(
                "provider_connection", "The provider connection could not be completed."
            ) from None
        except (ValueError, UnicodeError):
            raise AdapterError(
                "provider_response", "The provider returned an unreadable response."
            ) from None

    async def complete(
        self,
        connection_id,
        messages: list[dict],
        max_tokens: int = 1500,
        expected_signature: str | None = None,
        reasoning_effort: str | None = None,
    ):
        item, _ = self._dispatch(connection_id, expected_signature)
        if reasoning_effort is not None and (
            type(reasoning_effort) is not str
            or reasoning_effort not in {"low", "medium", "high"}
            or item["provider"] != "mistral"
            or item["model_id"] not in MISTRAL_LARGE_4_MODELS
        ):
            raise AdapterError(
                "invalid_reasoning_effort",
                "Choose low, medium or high reasoning for a supported Mistral Large 4 model.",
            )
        if type(max_tokens) is not int or not 16 <= max_tokens <= MAX_OUTPUT_TOKENS:
            raise AdapterError(
                "invalid_messages", "Choose an output limit between 16 and 16000 tokens."
            )
        if not isinstance(messages, list) or not 1 <= len(messages) <= MAX_MESSAGES:
            raise AdapterError(
                "invalid_messages", "The conversation is empty or exceeds the message limit."
            )
        normalized = []
        for message in messages:
            if (
                not isinstance(message, dict)
                or message.get("role") not in {"system", "user", "assistant", "developer"}
                or not isinstance(message.get("content"), str)
            ):
                raise AdapterError(
                    "invalid_messages",
                    "Messages must contain a supported role and plain text content.",
                )
            normalized.append({"role": message["role"], "content": message["content"]})
        if sum(len(message["content"]) for message in normalized) > MAX_INPUT_CHARS:
            raise AdapterError("invalid_messages", "The conversation exceeds the input size limit.")
        provider = item["provider"]
        if provider == "openai":
            suffix = "/responses"
            body = {
                "model": item["model_id"],
                "input": normalized,
                "max_output_tokens": max_tokens,
                "store": False,
            }
        elif provider == "anthropic":
            suffix = "/messages"
            body = {
                "model": item["model_id"],
                "max_tokens": max_tokens,
                "stream": False,
                "messages": [
                    message for message in normalized if message["role"] in {"user", "assistant"}
                ],
            }
            system = "\n\n".join(
                message["content"]
                for message in normalized
                if message["role"] in {"system", "developer"}
            )
            if system:
                body["system"] = system
            if not body["messages"]:
                raise AdapterError("invalid_messages", "Include a user message for this model.")
        else:
            suffix = "/chat/completions"
            body = {
                "model": item["model_id"],
                "messages": [
                    {
                        **message,
                        "role": "system" if message["role"] == "developer" else message["role"],
                    }
                    for message in normalized
                ],
                "max_tokens": max_tokens,
                "stream": False,
            }
            if provider == "openrouter":
                body["provider"] = {"allow_fallbacks": False}
        if reasoning_effort is not None:
            body["reasoning_effort"] = reasoning_effort
        result = await self._request(
            "POST",
            connection_id,
            suffix,
            body,
            expected=item,
            expected_signature=expected_signature,
        )
        try:
            if provider == "openai":
                text = "\n".join(
                    block["text"]
                    for output in result.get("output", [])
                    if output.get("type") == "message"
                    for block in output.get("content", [])
                    if block.get("type") == "output_text"
                )
            elif provider == "anthropic":
                text = _content_text(result.get("content"))
            else:
                text = _content_text(result["choices"][0]["message"]["content"])
            if not isinstance(text, str) or not text.strip():
                raise ValueError("No visible output")
            returned_model = result.get("model", item["model_id"])
            if not isinstance(returned_model, str) or len(returned_model) > 200:
                raise ValueError("Invalid model ID")
            return {
                "text": text,
                "model_id": returned_model,
                "usage": _safe_usage(result.get("usage")),
            }
        except (KeyError, IndexError, TypeError, ValueError, AttributeError):
            raise AdapterError(
                "provider_response",
                "The provider returned no readable assistant text. Check model support and the output token limit.",
            ) from None

    async def test(self, connection_id):
        item = self.get(connection_id)
        large_4 = item["provider"] == "mistral" and item["model_id"] in MISTRAL_LARGE_4_MODELS
        result = await self.complete(
            connection_id,
            [{"role": "user", "content": "Reply with OK."}],
            max_tokens=512 if large_4 else 64,
            reasoning_effort="low" if large_4 else None,
        )
        return {
            "ok": True,
            "model_id": result["model_id"],
            "message": "The selected model returned a real response.",
        }

    async def models(self, connection_id):
        item, _ = self._dispatch(connection_id)
        if item["provider"] == "alibaba":
            # Native /api/v1/models is documented for workspace-specific endpoints;
            # the fixed legacy shared inference domains do not promise discovery.
            raise AdapterError(
                "model_listing_unsupported",
                "Enter the model ID from your Alibaba Model Studio account. Model listing requires its workspace-specific endpoint.",
            )
        suffix = "/models/user" if item["provider"] == "openrouter" else "/models"
        result = await self._request("GET", connection_id, suffix, expected=item)
        data = result.get("data")
        if not isinstance(data, list):
            raise AdapterError("provider_response", "The provider returned no readable model list.")
        items = []
        for model in data[:1000]:
            if not isinstance(model, dict):
                continue
            model_id = model.get("id")
            if not isinstance(model_id, str) or not model_id or len(model_id) > 200:
                continue
            # Mistral lists embeddings/OCR as well; offer chat-capable entries only.
            capabilities = model.get("capabilities")
            if (
                item["provider"] == "mistral"
                and isinstance(capabilities, dict)
                and capabilities.get("completion_chat") is False
            ):
                continue
            title = model.get("display_name") or model.get("name") or model_id
            items.append(
                {"id": model_id, "title": title[:200] if isinstance(title, str) else model_id}
            )
        return {
            "items": items,
            "has_more": result.get("has_more") is True or len(data) > 1000,
            "message": "Provider model listing; a successful inference test confirms access to the selected model.",
        }


def _content_text(content):
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        raise ValueError("Invalid content")
    return "\n".join(
        block["text"]
        for block in content
        if isinstance(block, dict)
        and block.get("type") == "text"
        and isinstance(block.get("text"), str)
    )


def _safe_usage(value):
    if not isinstance(value, dict):
        return {}
    allowed = {
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "prompt_tokens",
        "completion_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    }
    return {
        key: number
        for key, number in value.items()
        if key in allowed and type(number) is int and number >= 0
    }


class ConnectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    provider: Provider
    model_id: str = Field(min_length=1, max_length=200)
    api_key: SecretStr | None = Field(default=None, max_length=8192)
    base_url: str | None = Field(default=None, max_length=500)
    enabled: StrictBool = True


class ConnectionPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=120)
    provider: Provider | None = None
    model_id: str | None = Field(default=None, min_length=1, max_length=200)
    api_key: SecretStr | None = Field(default=None, max_length=8192)
    base_url: str | None = Field(default=None, max_length=500)
    enabled: StrictBool | None = None


class ChatSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    local_only: StrictBool


def _api_error(exc):
    status = 404 if exc.code == "unknown_connection" else 409
    if exc.code == "invalid_connection":
        status = 422
    return APIError(status, exc.code, exc.message)


router = APIRouter(prefix="/api/v1")


def _refresh_readers(request):
    hook = getattr(request.app.state, "refresh_readers", None)
    if callable(hook):
        hook()


@router.get("/connections")
def list_connections(request: Request):
    return {"items": request.app.state.connections.metadata()}


@router.post("/connections")
def create_connection(body: ConnectionCreate, request: Request):
    try:
        item = request.app.state.connections.create(body.model_dump())
        _refresh_readers(request)
        return item
    except AdapterError as exc:
        raise _api_error(exc) from None


@router.patch("/connections/{connection_id}")
def patch_connection(connection_id: str, body: ConnectionPatch, request: Request):
    try:
        item = request.app.state.connections.patch(
            connection_id, body.model_dump(exclude_unset=True)
        )
        _refresh_readers(request)
        return item
    except AdapterError as exc:
        raise _api_error(exc) from None


@router.post("/connections/{connection_id}/test")
async def test_connection(connection_id: str, request: Request):
    try:
        return await request.app.state.connections.test(connection_id)
    except AdapterError as exc:
        raise _api_error(exc) from None


@router.get("/connections/{connection_id}/models")
async def connection_models(connection_id: str, request: Request):
    try:
        return await request.app.state.connections.models(connection_id)
    except AdapterError as exc:
        raise _api_error(exc) from None


@router.get("/chat-settings")
def chat_settings(request: Request):
    return request.app.state.connections.settings()


@router.patch("/chat-settings")
def patch_chat_settings(body: ChatSettingsPatch, request: Request):
    try:
        policy = request.app.state.connections.set_local_only(body.local_only)
        _refresh_readers(request)
        return policy
    except AdapterError as exc:
        raise _api_error(exc) from None
