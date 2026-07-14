"""Shared data model."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from .names import title_key


@dataclass
class Publication:
    source: str                 # "arxiv" | "openalex"
    pid: str                    # canonical id: "arxiv:2507.01234" | "doi:10..." | "openalex:W..."
    title: str
    url: str
    published: dt.date
    authors: list[str] = field(default_factory=list)
    venue: str | None = None
    categories: list[str] = field(default_factory=list)

    @property
    def title_id(self) -> str:
        return title_key(self.title)
