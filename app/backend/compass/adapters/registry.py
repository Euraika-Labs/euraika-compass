import json
import os
import re
import shutil
import tempfile
import threading
from collections.abc import Mapping
from pathlib import Path

from .base import AdapterError, TranscriptionResult
from .http_readers import (
    local_base_url,
    transcribe_kraken_http,
    transcribe_mistral,
    transcribe_qwen,
)
from .kraken_reader import transcribe_kraken


class ModelRegistry:
    """No network probing, model loading or credential disclosure during discovery."""

    def __init__(
        self,
        config_path: Path,
        state_path: Path | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        path = Path(config_path)
        if path.is_dir():
            path = path / "models.json"
        try:
            body = json.loads(path.read_text(encoding="utf-8"))
            items = body["items"]
            if not isinstance(items, list):
                raise ValueError
            self._routes: dict[str, dict] = {}
            for item in items:
                if not isinstance(item, dict) or not all(
                    isinstance(item.get(key), str)
                    for key in ("id", "title", "model_id", "provider", "kind", "adapter")
                ):
                    raise ValueError
                if item["id"] in self._routes:
                    raise ValueError
                if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", item["id"]):
                    raise ValueError
                if item["kind"] not in {"htr", "ocr", "vision", "chat"}:
                    raise ValueError
                if not isinstance(item.get("capabilities"), list) or not all(
                    isinstance(capability, str) for capability in item["capabilities"]
                ):
                    raise ValueError
                if item["adapter"] == "kraken" and not isinstance(item.get("model_path_env"), str):
                    raise ValueError
                self._routes[item["id"]] = item
        except (OSError, ValueError, KeyError, TypeError):
            raise AdapterError(
                "invalid_model_config", "The model catalog is missing or invalid."
            ) from None
        self._environ = dict(os.environ if environ is None else environ)
        self.local_only = self._environ.get("COMPASS_LOCAL_ONLY", "true").strip().lower() not in {
            "false",
            "0",
            "no",
        }
        self._state_path = Path(state_path) if state_path is not None else None
        self._lock = threading.Lock()
        self._enabled: dict[str, bool] = {}
        if self._state_path is not None and self._state_path.exists():
            try:
                state = json.loads(self._state_path.read_text(encoding="utf-8"))
                values = state.get("routes", {})
                if not isinstance(values, dict):
                    raise ValueError
                for route_id, entry in values.items():
                    if (
                        route_id in self._routes
                        and isinstance(entry, dict)
                        and type(entry.get("enabled")) is bool
                    ):
                        self._enabled[route_id] = entry["enabled"]
            except (OSError, ValueError, TypeError, AttributeError):
                raise AdapterError(
                    "invalid_route_state", "Saved model route settings could not be read."
                ) from None

    def _catalog_route(self, route_id: str) -> dict:
        try:
            return self._routes[route_id]
        except KeyError:
            raise AdapterError(
                "unknown_route", "This model route is not in the configured catalog."
            ) from None

    def _availability(self, route: dict) -> tuple[bool, str, str]:
        adapter = route["adapter"]
        if adapter == "kraken":
            worker_url = self._environ.get("COMPASS_KRAKEN_WORKER_URL", "")
            if worker_url:
                try:
                    local_base_url(worker_url)
                except AdapterError:
                    return (
                        False,
                        "invalid_endpoint",
                        "The HTR worker endpoint must use loopback without URL credentials.",
                    )
                return (
                    True,
                    "configured",
                    "Local HTR worker is configured; its installed profiles have not been probed.",
                )
            executable = self._environ.get("COMPASS_KRAKEN_EXECUTABLE", "")
            if (
                not executable
                or not shutil.which(executable)
                or Path(executable).suffix.lower() in {".cmd", ".bat"}
                or Path(executable).name.lower()
                in {"wsl", "wsl.exe", "cmd.exe", "bash", "bash.exe", "powershell.exe"}
            ):
                return (
                    False,
                    "not_installed",
                    "Configure COMPASS_KRAKEN_EXECUTABLE with the installed reader executable.",
                )
            model = self._environ.get(route["model_path_env"], "")
            segmenter = self._environ.get("COMPASS_KRAKEN_SEGMENTATION_MODEL", "")
            if not model or not Path(model).is_file():
                return (
                    False,
                    "missing_model",
                    f"Install this profile separately and set {route['model_path_env']}.",
                )
            if not segmenter or not Path(segmenter).is_file():
                return (
                    False,
                    "missing_model",
                    "Set COMPASS_KRAKEN_SEGMENTATION_MODEL to installed segmentation weights.",
                )
            return (
                True,
                "configured",
                "Local reader and weight paths are configured; runtime quality has not been tested.",
            )
        if adapter == "qwen_local":
            endpoint = self._environ.get("COMPASS_QWEN_BASE_URL", "")
            if not endpoint:
                return (
                    False,
                    "not_configured",
                    "Set COMPASS_QWEN_BASE_URL for an already-running local vision endpoint.",
                )
            try:
                local_base_url(endpoint)
            except AdapterError:
                return (
                    False,
                    "invalid_endpoint",
                    "The local image-model endpoint must use loopback without URL credentials.",
                )
            return (
                True,
                "configured",
                "Local endpoint is configured; model/projector availability has not been probed.",
            )
        if adapter == "mistral_ocr":
            if not self._environ.get("MISTRAL_API_KEY"):
                return (
                    False,
                    "not_configured",
                    "Configure MISTRAL_API_KEY in private backend settings.",
                )
            return (
                True,
                "configured",
                "Credentials are configured; account access has not been tested.",
            )
        return (
            False,
            "not_implemented",
            "This catalog profile has no inference adapter in the skeleton yet.",
        )

    def get_route(self, route_id: str) -> dict:
        route = self._catalog_route(route_id)
        configured, status, message = self._availability(route)
        enabled = self._enabled.get(route_id, route.get("enabled", False)) is True
        remote = route["provider"] not in {"local", "kraken", "llama.cpp"}
        available = configured and enabled
        if not enabled:
            status, message = (
                "disabled",
                "This route is disabled. Enabling it does not configure or download a model.",
            )
        elif remote and self.local_only:
            available = False
            status, message = "local_only", "Local-only mode blocks external image processing."
        return {
            "id": route["id"],
            "title": route["title"],
            "model_id": route["model_id"],
            "provider": route["provider"],
            "kind": route["kind"],
            "enabled": enabled,
            "configured": configured,
            "available": available,
            "status": status,
            "message": message,
            "capabilities": list(route.get("capabilities", [])),
        }

    def list_routes(self) -> list[dict]:
        return [self.get_route(route_id) for route_id in self._routes]

    def set_enabled(self, route_id: str, enabled: bool) -> dict:
        self._catalog_route(route_id)
        if type(enabled) is not bool:
            raise AdapterError("invalid_route_setting", "Enabled must be a boolean.")
        with self._lock:
            previous = self._enabled.copy()
            self._enabled[route_id] = enabled
            if self._state_path is not None:
                temporary = None
                try:
                    self._state_path.parent.mkdir(parents=True, exist_ok=True)
                    with tempfile.NamedTemporaryFile(
                        mode="w",
                        encoding="utf-8",
                        dir=self._state_path.parent,
                        prefix=".route-settings-",
                        suffix=".tmp",
                        delete=False,
                    ) as output:
                        temporary = Path(output.name)
                        json.dump(
                            {
                                "routes": {
                                    key: {"enabled": value} for key, value in self._enabled.items()
                                }
                            },
                            output,
                            indent=2,
                        )
                        output.write("\n")
                    os.replace(temporary, self._state_path)
                except OSError:
                    self._enabled = previous
                    raise AdapterError(
                        "settings_save_failed", "Model route settings could not be saved."
                    ) from None
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
        return self.get_route(route_id)

    async def transcribe(
        self,
        route_id: str,
        image_path: Path,
        language: str | None = None,
    ) -> TranscriptionResult:
        route = self._catalog_route(route_id)
        public = self.get_route(route_id)
        if not public["available"]:
            raise AdapterError(public["status"], public["message"])
        if "image_transcription" not in public["capabilities"]:
            raise AdapterError("missing_capability", "This route cannot read image text.")
        path = Path(image_path)
        if route["adapter"] == "kraken":
            worker_url = self._environ.get("COMPASS_KRAKEN_WORKER_URL", "")
            if worker_url:
                return await transcribe_kraken_http(
                    path, route["model_id"], route_id, worker_url, language
                )
            return await transcribe_kraken(
                path,
                self._environ["COMPASS_KRAKEN_EXECUTABLE"],
                Path(self._environ[route["model_path_env"]]),
                route["model_id"],
                segmentation_model=Path(self._environ["COMPASS_KRAKEN_SEGMENTATION_MODEL"]),
            )
        if route["adapter"] == "qwen_local":
            return await transcribe_qwen(
                path, route["model_id"], self._environ["COMPASS_QWEN_BASE_URL"], language
            )
        if route["adapter"] == "mistral_ocr":
            return await transcribe_mistral(
                path, route["model_id"], self._environ["MISTRAL_API_KEY"]
            )
        raise AdapterError(
            "not_implemented", "This route has no inference adapter in the skeleton."
        )
