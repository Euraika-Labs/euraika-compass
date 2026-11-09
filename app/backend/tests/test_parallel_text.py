from types import SimpleNamespace
from uuid import uuid4

import pytest

from compass.corpus import STARTERS
from compass.models import Edition, Passage, Source
from compass.parallel_text import (
    VerseReference,
    _alignment,
    _trusted_id,
    normalize_reference,
    parallel_evidence,
)


@pytest.mark.parametrize(
    "reference,expected",
    [
        ("II Samuel 19:1", VerseReference("2Sam", 19, 1)),
        ("Ⅱ Samuel 19:1", VerseReference("2Sam", 19, 1)),
        ("1John.4.8", VerseReference("1John", 4, 8)),
        ("Revelation of John 13:1", VerseReference("Rev", 13, 1)),
        ("Song of Solomon 6:13", VerseReference("Song", 6, 13)),
        ("Qur’an ٢:١٥٦", VerseReference(None, 2, 156)),
        ("سورة ۲:۱۵۶", VerseReference(None, 2, 156)),
        ("John 7:53–8:11", None),
        ("Genesis 1:0", None),
        ("Surah 115:1", None),
    ],
)
def test_single_reference_normalization_preserves_book_identity(reference, expected):
    assert normalize_reference(reference) == expected


@pytest.mark.parametrize(
    "english,hebrew,starter_id",
    [
        ("Genesis 31:55", "Genesis 32:1", "uxlc-he-torah"),
        ("Genesis 32:1", "Genesis 32:2", "uxlc-he-torah"),
        ("Exodus 8:1", "Exodus 7:26", "uxlc-he-torah"),
        ("Leviticus 6:1", "Leviticus 5:20", "uxlc-he-torah"),
        ("Numbers 17:1", "Numbers 17:16", "uxlc-he-torah"),
        ("Deuteronomy 29:1", "Deuteronomy 28:69", "uxlc-he-torah"),
        ("Psalm 3:1", "Psalm 3:2", "uxlc-he-tanakh-rest"),
        ("Joel 3:1", "Joel 4:1", "uxlc-he-tanakh-rest"),
        ("Malachi 4:6", "Malachi 3:24", "uxlc-he-tanakh-rest"),
    ],
)
def test_documented_hebrew_versification_shifts_are_bidirectional(english, hebrew, starter_id):
    left, right = normalize_reference(english), normalize_reference(hebrew)
    assert _alignment("kjv-1769", starter_id, left)[:2] == (right, "mapped_reference")
    assert _alignment(starter_id, "kjv-1769", right)[:2] == (left, "mapped_reference")


def test_uncertain_boundaries_and_other_collections_do_not_become_evidence_pairs():
    assert _alignment("kjv-1769", "uxlc-he-tanakh-rest", normalize_reference("Psalm 51:1")) is None
    assert (
        _alignment("kjv-1769", "uxlc-he-tanakh-rest", normalize_reference("I Kings 18:33")) is None
    )
    assert _alignment("uxlc-he-tanakh-rest", "kjv-1769", normalize_reference("Psalm 3:1")) is None
    assert (
        _alignment("kjv-1769", "sblgnt-grc", normalize_reference("II Corinthians 13:13"))[1]
        == "compare_only"
    )
    assert (
        _alignment("kjv-1769", "sblgnt-grc", normalize_reference("John 8:1"))[1] == "compare_only"
    )
    assert _alignment("kjv-1769", "tanzil-uthmani-ar", normalize_reference("Genesis 2:1")) is None
    assert _alignment("kjv-1769", "uxlc-he-torah", normalize_reference("Psalm 3:1")) is None


def starter_rows(starter_id, *, permission=True, **provenance_changes):
    starter = STARTERS[starter_id]
    source = Source(
        title=starter.title,
        url=starter.source_url,
        source_type=starter.source_type,
        use_limits={"external_processing": permission},
        provenance={
            "starter_id": starter.id,
            "content_sha256": starter.sha256,
            "snapshot_format": "original_download",
            "snapshot_path": f"sources/{starter.sha256}/original",
            "download_url": starter.download_url,
            **provenance_changes,
        },
    )
    edition = Edition(
        title=starter.edition_title,
        language=starter.language,
        revision=starter.revision,
        collection_memberships=list(starter.collections),
    )
    return source, edition


def test_starter_identity_requires_server_snapshot_and_exact_edition_metadata():
    source, edition = starter_rows("jps-1917-torah")
    assert _trusted_id(source, edition) == "jps-1917-torah"
    source.provenance["snapshot_format"] = "canonical_import_json"
    assert _trusted_id(source, edition) is None
    source.provenance["snapshot_format"] = "original_download"
    source.provenance["content_sha256"] = "incorrect"
    assert _trusted_id(source, edition) is None
    source.provenance["content_sha256"] = STARTERS["jps-1917-torah"].sha256
    edition.revision = "User-provided revision"
    assert _trusted_id(source, edition) is None


def add_edition(session, starter_id, passages, *, permission=True, **provenance_changes):
    source, edition = starter_rows(starter_id, permission=permission, **provenance_changes)
    session.add(source)
    session.flush()
    edition.source_id = source.id
    session.add(edition)
    session.flush()
    rows = {
        ref: Passage(edition_id=edition.id, reference=ref, text=text)
        for ref, text in passages.items()
    }
    session.add_all(rows.values())
    session.flush()
    return SimpleNamespace(source_id=source.id, ids={ref: row.id for ref, row in rows.items()})


@pytest.mark.postgres
def test_reader_returns_all_trusted_named_editions_and_preserves_original_text(postgres_app):
    client, app, _ = postgres_app
    with app.state.database.sessions() as session:
        jps = add_edition(session, "jps-1917-torah", {"Exodus 8:1": "JPS test fixture."})
        kjv = add_edition(session, "kjv-1769", {"Exodus 8:1": "KJV test fixture."})
        hebrew = add_edition(
            session,
            "uxlc-he-torah",
            {"Exodus 7:26": "  מִבְחָן׃  ", "Exodus 8:1": "Adjacent numbered test fixture."},
        )
        add_edition(
            session,
            "uxlc-he-torah",
            {"Exodus 7:26": "Untrusted fixture."},
            snapshot_format="canonical_import_json",
        )
        session.commit()
    response = client.get(f"/api/v1/passages/{jps.ids['Exodus 8:1']}/parallel")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["anchor"]["passage_id"] == str(jps.ids["Exodus 8:1"])
    assert [(item["passage_id"], item["alignment"]) for item in result["parallels"]] == [
        (str(hebrew.ids["Exodus 7:26"]), "mapped_reference"),
        (str(kjv.ids["Exodus 8:1"]), "same_reference"),
    ]
    assert result["parallels"][0]["quote"] == "  מִבְחָן׃  "
    reverse = client.get(f"/api/v1/passages/{hebrew.ids['Exodus 7:26']}/parallel").json()
    assert {item["passage_id"] for item in reverse["parallels"]} == {
        str(jps.ids["Exodus 8:1"]),
        str(kjv.ids["Exodus 8:1"]),
    }
    missing = client.get(f"/api/v1/passages/{uuid4()}/parallel")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "not_found"


@pytest.mark.postgres
def test_parallel_evidence_applies_selection_permissions_dedup_and_preferred_translation(
    postgres_app,
):
    _client, app, _ = postgres_app
    with app.state.database.sessions() as session:
        jps = add_edition(session, "jps-1917-torah", {"Genesis 1:1": "JPS fixture."})
        kjv = add_edition(session, "kjv-1769", {"Genesis 1:1": "KJV fixture."}, permission="true")
        he = add_edition(session, "uxlc-he-torah", {"Genesis 1:1": "Hebrew fixture."})
        session.commit()
        ja, ka, ha = (str(item.ids["Genesis 1:1"]) for item in (jps, kjv, he))
        anchors = [{"passage_id": ja}, {"passage_id": ka}]
        companions = parallel_evidence(session, anchors)
        assert [(item["passage_id"], item["parallel_for"]) for item in companions] == [
            (ha, [ja, ka])
        ]
        assert parallel_evidence(session, anchors, external_processing=True)[0]["parallel_for"] == [
            ja
        ]
        assert parallel_evidence(session, anchors, source_ids=[jps.source_id]) == []
        assert parallel_evidence(session, anchors + [{"passage_id": ha}]) == []
        preferred = parallel_evidence(session, [{"passage_id": ha}])
        assert [item["passage_id"] for item in preferred] == [ja]
        only_kjv = [he.source_id, kjv.source_id]
        assert (
            parallel_evidence(session, [{"passage_id": ha}], source_ids=only_kjv)[0]["passage_id"]
            == ka
        )
        assert (
            parallel_evidence(
                session, [{"passage_id": ha}], source_ids=only_kjv, external_processing=True
            )
            == []
        )
        assert parallel_evidence(session, anchors, limit=0) == []


@pytest.mark.postgres
def test_quran_same_ayah_and_greek_missing_or_variant_verses(postgres_app):
    client, app, _ = postgres_app
    with app.state.database.sessions() as session:
        en = add_edition(session, "pickthall-en", {"2:156": "Pickthall fixture."})
        ar = add_edition(session, "tanzil-uthmani-ar", {"2:156": "مثال"})
        kjv = add_edition(
            session,
            "kjv-1769",
            {
                "I John 4:8": "English fixture.",
                "I John 5:7": "English variant fixture.",
                "Acts 8:37": "Absent Greek verse fixture.",
            },
        )
        grc = add_edition(
            session,
            "sblgnt-grc",
            {
                "1 John 4:8": "Greek fixture.",
                "1 John 5:7": "Greek variant fixture.",
                "Acts 8:36": "Different Greek verse fixture.",
            },
        )
        session.commit()
        assert parallel_evidence(session, [{"passage_id": kjv.ids["I John 5:7"]}]) == []
    for anchor, target in [
        (en.ids["2:156"], ar.ids["2:156"]),
        (ar.ids["2:156"], en.ids["2:156"]),
        (kjv.ids["I John 4:8"], grc.ids["1 John 4:8"]),
    ]:
        data = client.get(f"/api/v1/passages/{anchor}/parallel").json()
        assert [(item["passage_id"], item["alignment"]) for item in data["parallels"]] == [
            (str(target), "same_reference")
        ]
    variant = client.get(f"/api/v1/passages/{kjv.ids['I John 5:7']}/parallel").json()
    assert variant["parallels"][0]["alignment"] == "compare_only"
    assert variant["warnings"]
    omitted = client.get(f"/api/v1/passages/{kjv.ids['Acts 8:37']}/parallel").json()
    assert omitted["parallels"] == [] and omitted["warnings"]
