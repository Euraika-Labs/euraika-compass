import pytest

from compass.errors import APIError
from compass.routing import Assignment, require_route, resolve_after_failure


def test_pin_prevents_approved_available_fallback():
    assignment = Assignment("chosen", pinned=True)
    assert resolve_after_failure(assignment, {"alternative"}, "alternative") is None
    assert assignment.route_id == "chosen"
    assert assignment.pinned


def test_unpinned_fallback_still_requires_approved_eligible_route():
    assignment = Assignment("chosen")
    assert resolve_after_failure(assignment, {"alternative"}, "alternative") == Assignment("alternative")
    assert resolve_after_failure(assignment, {"alternative"}, None) is None
    assert resolve_after_failure(assignment, set(), "alternative") is None


def test_local_only_blocks_even_configured_cloud_route():
    with pytest.raises(APIError) as error:
        require_route(
            {"enabled": True, "configured": True, "available": True, "provider": "mistral", "capabilities": ["image_transcription"]},
            local_only=True,
        )
    assert error.value.code == "local_only"
