from urllib.parse import unquote

import httpx
import pytest

from compass.adapters.base import AdapterError
from compass.web_research import search_web


@pytest.fixture
def web_transport(monkeypatch):
    requests = []
    responses = {}
    client = httpx.AsyncClient

    async def handle(request):
        requests.append(request)
        response = responses[request.url.host]
        if isinstance(response, Exception):
            raise response
        return response

    def create_client(**kwargs):
        assert kwargs["follow_redirects"] is False and kwargs["trust_env"] is False
        return client(transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr("compass.web_research.httpx.AsyncClient", create_client)
    return requests, responses


def doaj_fixture(abstract="This publisher abstract supplies several genuine words for comparison."):
    return httpx.Response(
        200,
        json={
            "results": [
                {
                    "id": "1234567890abcdef1234567890abcdef",
                    "bibjson": {
                        "title": "A Johannine study",
                        "abstract": abstract,
                        "year": "2022",
                        "author": [{"name": "An Author"}],
                        "journal": {"title": "A Journal"},
                        "identifier": [{"type": "doi", "id": "10.1234/fixture"}],
                    },
                }
            ]
        },
    )


def wiki_fixture(
    *, license_url="https://creativecommons.org/licenses/by-sa/4.0/deed.en", revision=41
):
    return httpx.Response(
        200,
        json={
            "query": {
                "rightsinfo": {"url": license_url},
                "pages": [
                    {
                        "pageid": 12,
                        "ns": 0,
                        "title": "Textual criticism",
                        "lastrevid": 41,
                        "revisions": [{"revid": revision, "timestamp": "2026-10-12T07:08:09Z"}],
                        "extract": "This is the actual plain-text lead returned by TextExtracts.",
                        "fullurl": "http://127.0.0.1/private",
                        "index": 1,
                    }
                ],
            }
        },
    )


@pytest.mark.asyncio
async def test_cloud_search_uses_publisher_abstract_and_pinned_wikipedia_extract(web_transport):
    requests, responses = web_transport
    text = " ".join(f"word{number}" for number in range(40))
    responses.update({"doaj.org": doaj_fixture(text), "nl.wikipedia.org": wiki_fixture()})
    result = await search_web(
        "logos John 1:1 Greek philosophical context", language="nl-BE", external_processing=True
    )
    assert result["providers"] == {"doaj": "ok", "wikimedia": "ok"}
    assert result["unavailable"] is False and result["warnings"] == []
    assert {request.url.host for request in requests} == {"doaj.org", "nl.wikipedia.org"}
    assert all(request.method == "GET" and not request.content for request in requests)
    assert all("authorization" not in request.headers for request in requests)
    doaj_request = next(request for request in requests if request.url.host == "doaj.org")
    assert '"John 1:1" AND ("logos" OR "Greek" OR "philosophical" OR "context")' in unquote(
        doaj_request.url.path
    )
    first, second = result["items"]
    assert first["excerpt"] == " ".join(text.split()[:25])
    assert first["evidence_type"] == "abstract" and first["source_type"] == "article"
    assert first["url"] == "https://doi.org/10.1234/fixture"
    assert first["license_url"] == "https://creativecommons.org/publicdomain/zero/1.0/"
    assert first["provenance"]["rights_scope"] == "DOAJ article metadata only"
    assert first["authors"] == ["An Author"] and first["source_date"] == "2022"
    assert len(first["content_sha256"]) == 64
    assert second["url"] == "https://nl.wikipedia.org/w/index.php?oldid=41"
    assert second["evidence_type"] == "article_extract" and second["source_type"] == "context"
    assert second["source_date"] is None
    assert second["provenance"]["revision_timestamp"] == "2026-10-12T07:08:09Z"
    assert second["authors"] == ["Wikipedia contributors"]
    assert all(item["use_limits"]["external_processing"] is True for item in result["items"])


@pytest.mark.asyncio
async def test_openalex_reconstructs_ordered_words_and_keeps_unclear_rights_local(web_transport):
    requests, responses = web_transport
    responses["api.openalex.org"] = httpx.Response(
        200,
        json={
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "display_name": "A scholarly record",
                    "abstract_inverted_index": {"research": [1], "Actual": [0], "excerpt.": [2]},
                    "primary_location": {"license": "cc-by", "version": "publishedVersion"},
                },
                {
                    "id": "https://openalex.org/W2",
                    "display_name": "Malformed excerpt metadata",
                    "abstract_inverted_index": {"Missing": [0], "word": [2]},
                },
                {
                    "id": "https://openalex.org/W3",
                    "display_name": "Retracted work",
                    "is_retracted": True,
                    "abstract_inverted_index": {"Text.": [0]},
                },
                {"id": "http://127.0.0.1/record", "display_name": "Untrusted provider ID"},
            ]
        },
    )
    result = await search_web("Greek textual criticism", providers=["openalex"])
    assert [item["excerpt"] for item in result["items"]] == ["Actual research excerpt.", None]
    assert [item["evidence_type"] for item in result["items"]] == ["abstract", "metadata_only"]
    assert result["items"][0]["license_url"] is None
    assert all(item["use_limits"]["external_processing"] is False for item in result["items"])
    blocked = await search_web(
        "Greek textual criticism", providers=["openalex"], external_processing=True
    )
    assert blocked["items"] == [] and blocked["warnings"] and blocked["providers"] == {}
    assert blocked["unavailable"] is False
    assert len(requests) == 1


@pytest.mark.parametrize(
    "license_url,revision",
    [
        ("https://unknown.example/rights", 41),
        ("https://creativecommons.org/licenses/by-sa/4.0/", 42),
    ],
)
@pytest.mark.asyncio
async def test_unknown_rights_or_unpinned_revision_is_not_cloud_evidence(
    web_transport, license_url, revision
):
    _, responses = web_transport
    responses["en.wikipedia.org"] = wiki_fixture(license_url=license_url, revision=revision)
    result = await search_web(
        "Textual criticism", providers=["wikimedia"], external_processing=True
    )
    assert result["items"] == [] and result["warnings"]
    assert result["providers"] == {"wikimedia": "ok"} and result["unavailable"] is False


@pytest.mark.asyncio
async def test_partial_provider_failure_keeps_real_excerpts_and_redacts_failure_bodies(
    web_transport,
):
    requests, responses = web_transport
    responses.update(
        {
            "doaj.org": httpx.ReadTimeout("private provider details"),
            "en.wikipedia.org": wiki_fixture(),
        }
    )
    result = await search_web(
        "Dead Sea Scrolls", providers=["doaj", "wikimedia"], external_processing=True
    )
    assert result["providers"] == {"doaj": "unavailable", "wikimedia": "ok"}
    assert result["unavailable"] is False and result["items"][0]["provider"] == "wikimedia"
    assert result["warnings"] == ["DOAJ timed out."]
    assert len(requests) == 2


@pytest.mark.asyncio
async def test_empty_result_is_distinct_from_all_providers_unavailable(web_transport):
    requests, responses = web_transport
    responses["doaj.org"] = httpx.Response(200, json={"results": []})
    empty = await search_web("No matching article", providers=["doaj"])
    assert empty == {"items": [], "warnings": [], "providers": {"doaj": "ok"}, "unavailable": False}
    responses["doaj.org"] = httpx.Response(302, headers={"location": "http://127.0.0.1/private"})
    error = await search_web("No matching article", providers=["doaj"])
    assert error["unavailable"] is True and error["providers"] == {"doaj": "unavailable"}
    assert error["items"] == [] and error["warnings"] == ["DOAJ returned HTTP 302."]
    assert {request.url.host for request in requests} == {"doaj.org"}


@pytest.mark.asyncio
async def test_provider_result_without_an_excerpt_is_a_lead_only(web_transport):
    _, responses = web_transport
    responses["doaj.org"] = doaj_fixture(None)
    local = await search_web("John 1:1", providers=["doaj"])
    assert local["items"][0]["excerpt"] is None
    assert local["items"][0]["evidence_type"] == "metadata_only"
    cloud = await search_web("John 1:1", providers=["doaj"], external_processing=True)
    assert cloud["items"] == [] and cloud["unavailable"] is False


@pytest.mark.parametrize("query", ["", "private\nchat", "x" * 201, "word " * 21])
@pytest.mark.asyncio
async def test_query_bounds_reject_before_network(web_transport, query):
    requests, _ = web_transport
    with pytest.raises(AdapterError) as error:
        await search_web(query)
    assert error.value.code == "invalid_web_query" and requests == []


@pytest.mark.asyncio
async def test_oversized_provider_response_is_bounded(web_transport):
    _, responses = web_transport
    responses["doaj.org"] = httpx.Response(200, content=b"x" * (2 * 1024 * 1024 + 1))
    result = await search_web("John 1:1", providers=["doaj"])
    assert result["unavailable"] is True
    assert result["warnings"] == ["DOAJ exceeded the response size limit."]
