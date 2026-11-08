from dataclasses import dataclass

from compass.errors import APIError


@dataclass(frozen=True)
class Assignment:
    route_id: str
    pinned: bool = False


def resolve_after_failure(
    assignment: Assignment, eligible_ids: set[str], approved_fallback: str | None
) -> Assignment | None:
    """Pins always win; only an explicit user reassignment can change a pinned role."""
    if assignment.pinned:
        return None
    if approved_fallback and approved_fallback in eligible_ids:
        return Assignment(approved_fallback)
    return None


def require_route(route: dict, local_only: bool) -> None:
    if not route.get("enabled"):
        raise APIError(409, "route_disabled", "Enable this route before using it.")
    if not route.get("configured") or not route.get("available"):
        raise APIError(409, "route_unavailable", route.get("message") or "This route is unavailable.")
    if local_only and route.get("provider") not in {"local", "kraken", "llama.cpp"}:
        raise APIError(409, "local_only", "Local-only mode blocks cloud image processing.")
    if "image_transcription" not in route.get("capabilities", []):
        raise APIError(409, "capability_missing", "This route cannot transcribe images.")
