"""Small routing rules shared by transcription and future participant allocation."""

from collections.abc import Iterable, Mapping

from .base import AdapterError


def select_route(
    routes: Iterable[Mapping],
    requested_id: str,
    *,
    pinned: bool = True,
    fallback_ids: tuple[str, ...] = (),
    local_only: bool = True,
    capability: str = "image_transcription",
    external_processing_allowed: bool = False,
) -> str:
    """A pin wins over a previously approved fallback list.

    Manual reassignment calls this function with the new explicitly selected ID.
    Fallback is limited to the supplied allowlist, never a global model catalog.
    """
    registry = {route["id"]: route for route in routes}

    def eligible(route_id: str) -> bool:
        route = registry.get(route_id)
        if not route or not route.get("enabled") or not route.get("available"):
            return False
        if capability not in route.get("capabilities", []):
            return False
        remote = route.get("provider") not in {"local", "kraken", "llama.cpp"}
        return not remote or (not local_only and external_processing_allowed)

    if eligible(requested_id):
        return requested_id
    if requested_id not in registry:
        raise AdapterError("unknown_route", "This model route is not configured.")
    if pinned:
        raise AdapterError(
            "pinned_route_unavailable",
            "The pinned route is unavailable. Explicitly unpin or reassign it to continue.",
        )
    for route_id in fallback_ids:
        if eligible(route_id):
            return route_id
    raise AdapterError("no_eligible_route", "No eligible configured route is available.")
