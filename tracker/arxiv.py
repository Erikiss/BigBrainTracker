"""arXiv als Quelle (Atom-API, https://info.arxiv.org/help/api/)."""

from __future__ import annotations

import datetime as dt
import re
import time
import xml.etree.ElementTree as ET

from . import http
from .config import Researcher
from .model import Publication
from .names import matches

API_URL = "https://export.arxiv.org/api/query"
MIN_INTERVAL_SECONDS = 3.0   # arXiv bittet um max. 1 Anfrage alle 3 Sekunden
MAX_RESULTS = 50

_ATOM = "{http://www.w3.org/2005/Atom}"
_ID_RE = re.compile(r"arxiv\.org/abs/(?P<id>.+?)(?:v\d+)?$")

_last_request = 0.0


def _throttle() -> None:
    global _last_request
    wait = _last_request + MIN_INTERVAL_SECONDS - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


def _matches_categories(person: Researcher, categories: list[str]) -> bool:
    if not person.arxiv_categories:
        return True
    return any(
        category.startswith(prefix)
        for category in categories
        for prefix in person.arxiv_categories
    )


def fetch(person: Researcher, cutoff: dt.date) -> list[Publication]:
    """Neueste arXiv-Einreichungen von ``person`` ab ``cutoff`` (einschließlich)."""
    found: dict[str, Publication] = {}
    for query_name in person.query_names():
        _throttle()
        response = http.get(API_URL, params={
            "search_query": f'au:"{query_name}"',
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "start": "0",
            "max_results": str(MAX_RESULTS),
        })
        root = ET.fromstring(response.content)
        for entry in root.iter(f"{_ATOM}entry"):
            id_match = _ID_RE.search((entry.findtext(f"{_ATOM}id") or "").strip())
            published_text = (entry.findtext(f"{_ATOM}published") or "").strip()
            if not id_match or not published_text:
                continue
            published = dt.datetime.fromisoformat(published_text.replace("Z", "+00:00")).date()
            if published < cutoff:
                # Sortierung folgt dem Datum der letzten Version; ältere
                # Erstveröffentlichungen können dazwischen liegen -> weiter prüfen.
                continue
            authors = [
                author.findtext(f"{_ATOM}name") or ""
                for author in entry.findall(f"{_ATOM}author")
            ]
            if not any(matches(author, person.search_names()) for author in authors):
                continue
            categories = [
                category.get("term") or ""
                for category in entry.findall(f"{_ATOM}category")
            ]
            categories = [category for category in categories if category]
            if not _matches_categories(person, categories):
                continue
            arxiv_id = id_match.group("id")
            pid = f"arxiv:{arxiv_id}"
            if pid in found:
                continue
            title = " ".join((entry.findtext(f"{_ATOM}title") or "").split())
            if not title:
                continue
            found[pid] = Publication(
                source="arxiv",
                pid=pid,
                title=title,
                url=f"https://arxiv.org/abs/{arxiv_id}",
                published=published,
                authors=authors,
                categories=categories,
            )
    return list(found.values())
