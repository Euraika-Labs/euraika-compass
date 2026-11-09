"""Bounded discovery and source-returned excerpts from official search APIs.

Callers supply an explicit topic query after checking their online-use policy.
The adapter contacts only fixed provider hosts and never fetches result URLs.
See DOAJ metadata terms, OpenAlex Work attributes, and MediaWiki TextExtracts
for the distinction between indexed abstracts, page extracts and full works.
"""

import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from compass.adapters.base import AdapterError

DEFAULT_PROVIDERS = ("doaj", "openalex", "wikimedia")
_LABELS = {"doaj": "DOAJ", "openalex": "OpenAlex", "wikimedia": "Wikimedia"}
_WIKI_HOSTS = {
    language: f"{language}.wikipedia.org" for language in ("en", "nl", "fr", "de", "ar", "he", "el")
}
_OPENALEX = "https://api.openalex.org/works"
_DOAJ = "https://doaj.org/api/v4/search/articles/"
_CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"
_USER_AGENT = "EuraikaCompass/0.1 (https://github.com/Euraika-Labs/euraika-compass)"
_MAX_BYTES = 2 * 1024 * 1024
_MAX_RESULTS = 12
_MAX_WORDS = 25
_MAX_EXCERPT = 400


class _Unavailable(Exception):
    pass


def _text(value, limit):
    if not isinstance(value, str) or any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        return None
    value = " ".join(value.replace("\x00", " ").split())
    return value[:limit] or None


def _excerpt(value):
    value = _text(value, 24_000)
    if value is None:
        return None
    # Preserve a contiguous beginning. The provider may append an ellipsis.
    words = value.split()[:_MAX_WORDS]
    while words and len(" ".join(words)) > _MAX_EXCERPT:
        words.pop()
    return " ".join(words).rstrip("…").rstrip() or None


def _date(value):
    if isinstance(value, str) and re.fullmatch(r"\d{4}(?:-\d{2}(?:-\d{2})?)?", value):
        return value
    return None


def _doi_url(value):
    if not isinstance(value, str):
        return None
    value = value.removeprefix("https://doi.org/").strip()
    if len(value) > 300 or not re.fullmatch(r"10\.\d{4,9}/[^\s<>#?]+", value, re.ASCII):
        return None
    try:
        return "https://doi.org/" + quote(value, safe="/().:_-")
    except UnicodeEncodeError:
        return None


def _license_url(value):
    if not isinstance(value, str):
        return None
    match = re.fullmatch(
        r"https://creativecommons\.org/(licenses/(?:by|by-sa)/(?:3\.0|4\.0)|publicdomain/zero/1\.0)"
        r"(?:/|/deed(?:\.[a-zA-Z-]+)?)?",
        value,
    )
    return f"https://creativecommons.org/{match[1]}/" if match else None


def _record(
    *,
    provider,
    record_id,
    title,
    url,
    excerpt,
    evidence_type,
    source_type,
    source_date,
    authors,
    publication,
    retrieved_at,
    license_url,
    external_processing,
    provenance,
):
    if not title or not url:
        return None
    data = {
        "id": f"{provider}:{record_id}",
        "provider": provider,
        "title": title,
        "url": url,
        "excerpt": excerpt,
        "evidence_type": evidence_type if excerpt else "metadata_only",
        "source_type": source_type,
        "source_date": source_date,
        "authors": authors,
        "publication": publication,
        "license_url": license_url,
        "use_limits": {"external_processing": bool(excerpt and external_processing)},
        "provenance": provenance,
    }
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        **data,
        "retrieved_at": retrieved_at,
        "content_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
    }


async def _get_json(client, url, params):
    try:
        async with asyncio.timeout(18):
            async with client.stream("GET", url, params=params) as response:
                if response.status_code == 429:
                    raise _Unavailable("is rate limited; try again later")
                if response.status_code != 200:
                    raise _Unavailable(f"returned HTTP {response.status_code}")
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise _Unavailable("returned an unsupported content encoding")
                data = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    if len(data) + len(chunk) > _MAX_BYTES:
                        raise _Unavailable("exceeded the response size limit")
                    data.extend(chunk)
            return json.loads(data)
    except (httpx.TimeoutException, TimeoutError):
        raise _Unavailable("timed out") from None
    except httpx.HTTPError:
        raise _Unavailable("could not be reached") from None
    except (ValueError, RecursionError):
        raise _Unavailable("returned unreadable data") from None


def _results(data, key):
    if not isinstance(data, dict) or not isinstance(data.get(key), list):
        raise _Unavailable("returned an unexpected result format")
    return [item for item in data[key][:_MAX_RESULTS] if isinstance(item, dict)]


def _abstract_index(index):
    if not isinstance(index, dict) or not 0 < len(index) <= 1200:
        return None
    ordered = {}
    for token, positions in index.items():
        if (
            not isinstance(token, str)
            or not token
            or len(token) > 256
            or not isinstance(positions, list)
        ):
            return None
        if len(positions) > 1200:
            return None
        for position in positions:
            if type(position) is not int or not 0 <= position < 1200 or position in ordered:
                return None
            ordered[position] = token
    if set(ordered) != set(range(len(ordered))):
        return None
    return _excerpt(" ".join(ordered[index] for index in range(len(ordered))))


async def _search_openalex(client, query, _language, limit, retrieved_at):
    fields = "id,doi,display_name,publication_date,type,authorships,primary_location,abstract_inverted_index,is_retracted"
    data = await _get_json(
        client, _OPENALEX, {"search": query, "per_page": limit, "select": fields}
    )
    items = []
    for row in _results(data, "results"):
        identifier = row.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(
            r"https://openalex\.org/W[0-9]{1,20}", identifier
        ):
            continue
        if row.get("is_retracted") is True:
            continue
        location = row.get("primary_location")
        location = location if isinstance(location, dict) else {}
        source = location.get("source")
        source = source if isinstance(source, dict) else {}
        authorships = row.get("authorships")
        authors = []
        for author in authorships[:12] if isinstance(authorships, list) else []:
            metadata = author.get("author") if isinstance(author, dict) else None
            if isinstance(metadata, dict) and (name := _text(metadata.get("display_name"), 120)):
                authors.append(name)
        item = _record(
            provider="openalex",
            record_id=identifier.rsplit("/", 1)[-1],
            title=_text(row.get("display_name"), 300),
            url=_doi_url(row.get("doi")) or identifier,
            excerpt=_abstract_index(row.get("abstract_inverted_index")),
            evidence_type="abstract",
            source_type="article",
            source_date=_date(row.get("publication_date")),
            authors=authors,
            publication=_text(source.get("display_name"), 200),
            retrieved_at=retrieved_at,
            license_url=None,
            external_processing=False,
            provenance={
                "record_url": identifier,
                "work_type": _text(row.get("type"), 70),
                "reported_location_license": _text(location.get("license"), 70),
                "location_version": _text(location.get("version"), 70),
                "excerpt_field": "abstract_inverted_index",
            },
        )
        if item:
            items.append(item)
    return items


def _doaj_expression(query):
    def literal(value):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    # Keep a precise verse address while letting surrounding topical terms vary.
    reference = re.search(r"\b(?:[1-3]\s+)?[^\W\d_][\w.-]*\s+\d{1,3}:\d{1,3}\b", query)
    if reference:
        terms = (query[: reference.start()] + " " + query[reference.end() :]).split()
        expression = literal(reference.group())
        if terms:
            expression += " AND (" + " OR ".join(literal(term) for term in terms) + ")"
    else:
        terms = query.split()
        expression = literal(query)
        if len(terms) > 1:
            expression += " OR (" + " AND ".join(literal(term) for term in terms) + ")"
    return f"({expression}) AND _exists_:bibjson.abstract"


async def _search_doaj(client, query, _language, limit, retrieved_at):
    expression = _doaj_expression(query)
    data = await _get_json(client, _DOAJ + quote(expression, safe=""), {"pageSize": limit})
    items = []
    for row in _results(data, "results"):
        identifier = row.get("id")
        bib = row.get("bibjson")
        if (
            not isinstance(identifier, str)
            or not re.fullmatch(r"[a-fA-F0-9]{32}", identifier)
            or not isinstance(bib, dict)
        ):
            continue
        record_url = f"https://doaj.org/article/{identifier}"
        identifiers = bib.get("identifier")
        doi = (
            next(
                (
                    entry.get("id")
                    for entry in identifiers
                    if isinstance(entry, dict) and entry.get("type") == "doi"
                ),
                None,
            )
            if isinstance(identifiers, list)
            else None
        )
        journal = bib.get("journal")
        journal = journal if isinstance(journal, dict) else {}
        authors = bib.get("author")
        author_names = (
            [
                name
                for person in authors[:12]
                if isinstance(person, dict) and (name := _text(person.get("name"), 120))
            ]
            if isinstance(authors, list)
            else []
        )
        abstract = bib.get("abstract")
        # DOAJ requires plaintext abstract metadata. Skip markup-bearing anomalies.
        excerpt = (
            _excerpt(abstract)
            if isinstance(abstract, str) and not re.search(r"<\s*/?\w", abstract)
            else None
        )
        item = _record(
            provider="doaj",
            record_id=identifier,
            title=_text(bib.get("title"), 300),
            url=_doi_url(doi) or record_url,
            excerpt=excerpt,
            evidence_type="abstract",
            source_type="article",
            source_date=_date(bib.get("year")),
            authors=author_names,
            publication=_text(journal.get("title"), 200),
            retrieved_at=retrieved_at,
            license_url=_CC0,
            external_processing=True,
            provenance={
                "record_url": record_url,
                "excerpt_field": "bibjson.abstract",
                "rights_scope": "DOAJ article metadata only",
                "rights_url": "https://doaj.org/terms/",
            },
        )
        if item:
            items.append(item)
    return items


async def _search_wikimedia(client, query, language, limit, retrieved_at):
    host = _WIKI_HOSTS[language]
    data = await _get_json(
        client,
        f"https://{host}/w/api.php",
        {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 0,
            "gsrlimit": limit,
            "prop": "extracts|info|revisions|pageprops",
            "exintro": 1,
            "explaintext": 1,
            "exlimit": "max",
            "exchars": _MAX_EXCERPT,
            "rvprop": "ids|timestamp",
            "ppprop": "disambiguation",
            "meta": "siteinfo",
            "siprop": "rightsinfo",
            "format": "json",
            "formatversion": 2,
        },
    )
    if not isinstance(data, dict) or "error" in data:
        raise _Unavailable("returned an API error")
    result = data.get("query")
    if result is None and "batchcomplete" in data:
        return []
    if not isinstance(result, dict):
        raise _Unavailable("returned an unexpected result format")
    rights = result.get("rightsinfo")
    license_url = _license_url(rights.get("url")) if isinstance(rights, dict) else None
    pages = result.get("pages", [])
    if not isinstance(pages, list):
        raise _Unavailable("returned an unexpected result format")
    items = []
    ranked = [row for row in pages[:_MAX_RESULTS] if isinstance(row, dict)]
    ranked.sort(key=lambda row: row["index"] if type(row.get("index")) is int else _MAX_RESULTS + 1)
    for row in ranked:
        page_id, rev_id = row.get("pageid"), row.get("lastrevid")
        if type(page_id) is not int or page_id <= 0 or row.get("ns") != 0:
            continue
        props = row.get("pageprops")
        if isinstance(props, dict) and "disambiguation" in props:
            continue
        revisions = row.get("revisions")
        revision = revisions[0] if isinstance(revisions, list) and revisions else None
        revision = revision if isinstance(revision, dict) else {}
        pinned = type(rev_id) is int and rev_id > 0 and revision.get("revid") == rev_id
        url = (
            f"https://{host}/w/index.php?oldid={rev_id}"
            if pinned
            else f"https://{host}/?curid={page_id}"
        )
        stamp = _text(revision.get("timestamp"), 40)
        item = _record(
            provider="wikimedia",
            record_id=f"{language}:{page_id}:{rev_id if pinned else 'current'}",
            title=_text(row.get("title"), 300),
            url=url,
            excerpt=_excerpt(row.get("extract")) if pinned else None,
            evidence_type="article_extract",
            source_type="context",
            source_date=None,
            authors=["Wikipedia contributors"],
            publication=f"Wikipedia ({language})",
            retrieved_at=retrieved_at,
            license_url=license_url,
            external_processing=license_url is not None,
            provenance={
                "page_id": page_id,
                "revision_id": rev_id if pinned else None,
                "revision_timestamp": stamp if pinned else None,
                "language": language,
                "excerpt_field": "TextExtracts article lead",
            },
        )
        if item:
            items.append(item)
    return items


_SEARCHERS = {"doaj": _search_doaj, "openalex": _search_openalex, "wikimedia": _search_wikimedia}


async def search_web(
    query: str,
    *,
    language: str = "en",
    limit: int = 8,
    providers: list[str] | tuple[str, ...] | None = None,
    external_processing: bool = False,
) -> dict:
    """Return short source excerpts and discovery leads for one explicit search query."""
    if not isinstance(query, str) or any(ord(char) < 32 for char in query):
        raise AdapterError("invalid_web_query", "Provide a short, single-line web research topic.")
    query = query.strip()
    if not query or len(query) > 200 or len(query.split()) > 20 or _text(query, 200) is None:
        raise AdapterError(
            "invalid_web_query",
            "Provide a web research topic of up to 200 characters and 20 words.",
        )
    if (
        type(limit) is not int
        or not 1 <= limit <= _MAX_RESULTS
        or type(external_processing) is not bool
    ):
        raise AdapterError("invalid_web_query", "Choose valid web research limits.")
    default_providers = providers is None
    providers = DEFAULT_PROVIDERS if default_providers else providers
    if (
        not isinstance(providers, (list, tuple))
        or not 1 <= len(providers) <= 3
        or any(
            not isinstance(provider, str) or provider not in _SEARCHERS for provider in providers
        )
    ):
        raise AdapterError(
            "invalid_web_provider", "Choose up to three supported web research providers."
        )
    selected = tuple(
        provider
        for provider in dict.fromkeys(providers)
        if not external_processing or provider != "openalex"
    )
    warnings = []
    if external_processing and not default_providers and "openalex" in providers:
        warnings.append("OpenAlex abstracts are available for local processing.")
    if not isinstance(language, str) or len(language) > 40:
        raise AdapterError("invalid_web_query", "Choose a valid web research language.")
    wiki_language = language.casefold().split("-", 1)[0]
    if wiki_language not in _WIKI_HOSTS:
        wiki_language = "en"
    if not selected:
        return {"items": [], "warnings": warnings, "providers": {}, "unavailable": False}
    retrieved_at = datetime.now(timezone.utc).isoformat()
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(12, connect=5),
        follow_redirects=False,
        trust_env=False,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        },
    ) as client:

        async def attempt(provider):
            try:
                return await _SEARCHERS[provider](
                    client, query, wiki_language, limit, retrieved_at
                ), None
            except _Unavailable as exc:
                return [], f"{_LABELS[provider]} {exc}."

        results = await asyncio.gather(*(attempt(provider) for provider in selected))
    availability = {
        provider: "unavailable" if error else "ok"
        for provider, (_items, error) in zip(selected, results, strict=True)
    }
    warnings.extend(error for _items, error in results if error)
    items, seen_urls = [], set()
    excluded = False
    # Interleave the providers' rankings while preferring actual excerpts to leads.
    for has_excerpt in (True, False):
        for rank in range(limit):
            for bucket, _error in results:
                if rank >= len(bucket):
                    continue
                item = bucket[rank]
                if bool(item["excerpt"]) != has_excerpt or item["url"] in seen_urls:
                    continue
                if external_processing and item["use_limits"]["external_processing"] is not True:
                    excluded = True
                    continue
                if len(items) < limit:
                    seen_urls.add(item["url"])
                    items.append(item)
    if excluded:
        warnings.append("Some search results lacked an excerpt with clear cloud-processing rights.")
    return {
        "items": items,
        "warnings": warnings,
        "providers": availability,
        "unavailable": all(status == "unavailable" for status in availability.values()),
    }
