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


def image_route_is_local(route: dict) -> bool:
    return route.get("provider") in {"local", "kraken", "llama.cpp"}


def require_route(route: dict, local_only: bool) -> None:
    if not route.get("enabled"):
        raise APIError(409, "route_disabled", "Enable this route before using it.")
    if not route.get("configured") or not route.get("available"):
        raise APIError(409, "route_unavailable", route.get("message") or "This route is unavailable.")
    if local_only and not image_route_is_local(route):
        raise APIError(409, "local_only", "Local-only mode blocks cloud image processing.")
    if "image_transcription" not in route.get("capabilities", []):
        raise APIError(409, "capability_missing", "This route cannot transcribe images.")


def require_image_processing(provenance: dict | None, route: dict, local_only: bool) -> None:
    if provenance is not None:
        limits = provenance.get("use_limits") if isinstance(provenance, dict) else None
        limits = limits if isinstance(limits, dict) else {}
        if image_route_is_local(route) and limits.get("local_ocr") is not True:
            raise APIError(403, "source_local_processing_blocked", "The scan's source terms do not permit local OCR.")
        if not image_route_is_local(route) and limits.get("external_processing") is not True:
            raise APIError(403, "source_cloud_processing_blocked", "The scan's source terms do not permit cloud OCR.")
    require_route(route, local_only)
