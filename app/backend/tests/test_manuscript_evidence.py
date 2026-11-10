import hashlib
from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from compass.errors import APIError
from compass.manuscript_evidence import (
    MAX_EXCERPT_CHARS,
    ManuscriptReading,
    manuscript_candidates,
    selected_manuscript_readings,
)
from compass.models import Dossier, ImageAsset, Transcription


def provenance(*, external_processing=False):
    return {
        "kind": "manuscript", "manuscript_id": "fixture", "manuscript_title": "Fixture manuscript",
        "institution": "Fixture library", "shelfmark": "MS Test. 1", "language": "he",
        "folio_id": "folio-1r", "folio_label": "f. 1r", "canvas_id": "https://example.org/canvas/1",
        "catalog_url": "https://example.org/catalog/fixture", "image_sha256": "a" * 64,
        "manifest_sha256": "b" * 64, "use_limits": {"local_storage": True, "local_ocr": True,
                                                       "external_processing": external_processing},
    }


def reading(text, **changes):
    revision_id = uuid4()
    base = ManuscriptReading(
        id=revision_id, image_id=uuid4(), dossier_id=uuid4(), parent_id=None, lineage_id=revision_id,
        text=text, kind="automatic", engine="kraken", model_id="fixture-model", language="he",
        created_at=datetime.now(timezone.utc), regions=[], input_region=None,
        image_width=1000, image_height=1200, image_sha256="a" * 64, provenance=provenance(),
    )
    return replace(base, **changes)


@pytest.mark.parametrize(("marked", "plain"), [
    ("מֶלֶךְ", "מלך"), ("Ἀγάπη", "αγαπη"), ("ٱلرَّحْمَـٰنِ", "الرحمن"),
])
def test_normalized_lookup_preserves_original_excerpt_and_offsets(marked, plain):
    line = f"  {marked}  "
    saved = reading(f"Unrelated opening\n{line}\nEnd of the saved reading.")
    item = manuscript_candidates([saved], [plain])[0]
    assert item["match_type"] == "lexical"
    assert item["quote"] == line
    assert item["quote"] == saved.text[item["excerpt_start"]:item["excerpt_end"]]
    assert item["quote_sha256"] == hashlib.sha256(line.encode()).hexdigest()
    assert item["transcription_id"] == str(saved.id)
    assert item["image_content_url"] == f"/api/v1/images/{saved.image_id}/content"
    assert item["image_sha256"] == saved.image_sha256
    assert item["collection_memberships"] == []


def test_cropped_kraken_line_has_original_coordinates_only_with_exact_correspondence():
    line = "  A distinctive word.  "
    box = {"x": 12.5, "y": 30, "width": 120, "height": 20}
    region = {"type": "line", "text": line, "bbox": box, "coordinate_system": "input_pixels", "page": 0}
    crop = {"x": 100, "y": 200, "width": 300, "height": 500}
    saved = reading("First line\n" + line, input_region=crop, regions=[region])
    item = manuscript_candidates([saved], ["distinctive"])[0]
    assert item["region"] == {
        "x": 112.5, "y": 230, "width": 120, "height": 20,
        "kind": "text_region", "coordinate_system": "original_image_pixels",
    }
    ambiguous = replace(saved, text=f"{line}\n{line}")
    changed = replace(saved, kind="user_corrected", engine="manual")
    wrong_space = replace(saved, regions=[{**region, "coordinate_system": "provider_page_pixels"}])
    out_of_crop = replace(saved, regions=[{**region, "bbox": {**box, "x": 250}}])
    for revision in (ambiguous, changed, wrong_space, out_of_crop):
        assert manuscript_candidates([revision], ["distinctive"])[0]["region"] == {
            **crop, "kind": "input_crop", "coordinate_system": "original_image_pixels",
        }
    invalid_crop = replace(saved, input_region={**crop, "x": 900})
    assert manuscript_candidates([invalid_crop], ["distinctive"])[0]["region"] is None


def test_selected_correction_can_find_long_line_match_or_supply_opening():
    phrase = "deliberate corrected word"
    saved = reading("baseline " * 220 + phrase + " continue", kind="user_corrected", engine="manual")
    item = manuscript_candidates([saved], [phrase])[0]
    assert item["match_type"] == "lexical" and phrase in item["quote"]
    assert len(item["quote"]) <= MAX_EXCERPT_CHARS
    assert item["quote"] == saved.text[item["excerpt_start"]:item["excerpt_end"]]
    assert item["region"] is None
    opening = manuscript_candidates([saved], ["what does this folio say?"])[0]
    assert opening["match_type"] == "opening"
    assert opening["quote"] == saved.text[:MAX_EXCERPT_CHARS]


def create_image(session, dossier, source):
    image = ImageAsset(
        dossier_id=dossier.id, filename="fixture.png", media_type="image/png", width=1000,
        height=1200, sha256="a" * 64, provenance=source,
    )
    session.add(image)
    session.flush()
    return image


def save_revision(session, image, text, *, parent=None, kind="automatic"):
    saved = Transcription(
        image_id=image.id, parent_id=parent.id if parent else None, text=text,
        kind=kind, engine="kraken" if kind == "automatic" else "manual", language=None,
    )
    session.add(saved)
    session.flush()
    return saved


@pytest.mark.postgres
def test_exact_selected_lineages_and_scope_on_real_postgres(postgres_app):
    client, application, _ = postgres_app
    with application.state.database.sessions() as session:
        dossier, other = Dossier(title="Scoped dossier"), Dossier(title="Another dossier")
        session.add_all((dossier, other))
        session.flush()
        allowed = create_image(session, dossier, provenance(external_processing=True))
        blocked = create_image(session, dossier, provenance(external_processing="true"))
        upload = create_image(session, dossier, None)
        outside = create_image(session, other, provenance(external_processing=True))
        original = save_revision(session, allowed, "Old exact reading")
        correction = save_revision(session, allowed, "Chosen correction", parent=original, kind="user_corrected")
        save_revision(session, allowed, "A newer correction", parent=correction, kind="user_corrected")
        independent = save_revision(session, allowed, "Independent manual reading", kind="user_corrected")
        local = save_revision(session, blocked, "Private local reading")
        photo = save_revision(session, upload, "Unknown provenance reading", kind="user_corrected")
        foreign = save_revision(session, outside, "Wrong dossier reading")
        session.commit()
        selected = [original.id, correction.id, independent.id]
        rows, excluded = selected_manuscript_readings(session, dossier.id, selected, external_processing=False)
        assert [row.id for row in rows] == selected and excluded == 0
        assert [row.text for row in rows] == ["Old exact reading", "Chosen correction", "Independent manual reading"]
        assert [row.lineage_id for row in rows] == [original.id, original.id, independent.id]
        assert rows[1].parent_id == original.id and rows[1].language == "he"
        cloud, excluded = selected_manuscript_readings(
            session, dossier.id, [local.id, correction.id], external_processing=True,
        )
        assert [row.id for row in cloud] == [correction.id] and excluded == 1
        for invalid in ([photo.id], [local.id, foreign.id], [correction.id, correction.id]):
            with pytest.raises(APIError) as error:
                selected_manuscript_readings(session, dossier.id, invalid, external_processing=True)
            assert error.value.code == "invalid_manuscript_selection"
        dossier_id = dossier.id
        rejected_ids = {str(photo.id), str(foreign.id)}
        expected_ids = {str(original.id), str(correction.id), str(independent.id), str(local.id)}

    response = client.get(f"/api/v1/dossiers/{dossier_id}/manuscript-readings")
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    listed = {item["id"] for item in items}
    assert expected_ids <= listed and not listed & rejected_ids
    assert all("text" not in item for item in items)
    assert not response.json()["truncated"]
