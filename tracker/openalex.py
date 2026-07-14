"""OpenAlex als Quelle (https://docs.openalex.org/) – deckt auch Journals ab."""

from __future__ import annotations

import datetime as dt
import os
import re
import time

from . import http
from .config import Researcher
from .model import Publication
from .names import matches

API_URL = "https://api.openalex.org/works"
MIN_INTERVAL_SECONDS = 0.25
PER_PAGE = 50

_SELECT = "id,display_name,publication_date,doi,primary_location,authorships"

_ARXIV_DOI_RE = re.compile(r"^10\.48550/arxiv\.(?P<id>.+)$", re.IGNORECASE)
_ARXIV_URL_RE = re.compile(
    r"arxiv\.org/(?:abs|pdf)/(?P<id>.+?)(?:v\d+)?(?:\.pdf)?/?$", re.IGNORECASE
)

_last_request = 0.0


def _throttle() -> None:
    global _last_request
    wait = _last_request + MIN_INTERVAL_SECONDS - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


def _canonical_id(work: dict) -> str:
    """arXiv-ID > DOI > OpenAlex-ID, damit Duplikate über Quellen hinweg zusammenfallen."""
    doi = (work.get("doi") or "").removeprefix("https://doi.org/").strip()
    doi_match = _ARXIV_DOI_RE.match(doi)
    if doi_match:
        return f"arxiv:{doi_match.group('id')}"
    primary = work.get("primary_location") or {}
    for url_key in ("landing_page_url", "pdf_url"):
        url_match = _ARXIV_URL_RE.search(primary.get(url_key) or "")
        if url_match:
            return f"arxiv:{url_match.group('id')}"
    if doi:
        return f"doi:{doi.casefold()}"
    return f"openalex:{(work.get('id') or '').rsplit('/', 1)[-1]}"


def _filters(person: Researcher, cutoff: dt.date) -> list[str]:
    since = f"from_publication_date:{cutoff.isoformat()}"
    if person.openalex_id:
        return [f"authorships.author.id:{person.openalex_id},{since}"]
    return [
        f"raw_author_name.search:{query_name},{since}"
        for query_name in person.query_names()
        if "," not in query_name  # Komma ist Filter-Trennzeichen
    ]


def fetch(person: Researcher, cutoff: dt.date) -> list[Publication]:
    """Neueste OpenAlex-Werke von ``person`` ab ``cutoff`` (einschließlich)."""
    found: dict[str, Publication] = {}
    mailto = os.environ.get("OPENALEX_MAILTO", "").strip()
    for filter_expression in _filters(person, cutoff):
        _throttle()
        params = {
            "filter": filter_expression,
            "per-page": str(PER_PAGE),
            "sort": "publication_date:desc",
            "select": _SELECT,
        }
        if mailto:
            params["mailto"] = mailto
        payload = http.get(API_URL, params=params).json()
        for work in payload.get("results") or []:
            date_text = work.get("publication_date") or ""
            title = " ".join((work.get("display_name") or "").split())
            if not date_text or not title:
                continue
            published = dt.date.fromisoformat(date_text)
            if published < cutoff:
                continue
            authorships = work.get("authorships") or []
            display_names = [
                (authorship.get("author") or {}).get("display_name") or ""
                for authorship in authorships
            ]
            raw_names = [authorship.get("raw_author_name") or "" for authorship in authorships]
            if not person.openalex_id:
                candidates = [name for name in (*display_names, *raw_names) if name]
                if not any(matches(name, person.search_names()) for name in candidates):
                    continue
            pid = _canonical_id(work)
            if pid in found:
                continue
            primary = work.get("primary_location") or {}
            venue = ((primary.get("source") or {}).get("display_name")) or None
            found[pid] = Publication(
                source="openalex",
                pid=pid,
                title=title,
                url=work.get("doi") or primary.get("landing_page_url") or work.get("id") or "",
                published=published,
                authors=[display or raw for display, raw in zip(display_names, raw_names)],
                venue=venue,
            )
    return list(found.values())
