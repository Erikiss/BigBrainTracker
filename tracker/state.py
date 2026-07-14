"""Persistenter Zustand: welche Publikationen wurden bereits gemeldet."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from .model import Publication

KEEP_DAYS = 400


def _entry_date(value: str, fallback: dt.date) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return fallback


class State:
    """Map aus "Person|Publikations-Schlüssel" -> Datum der ersten Sichtung."""

    def __init__(self, path: str | Path, entries: dict[str, str] | None = None):
        self.path = Path(path)
        self.entries: dict[str, str] = dict(entries or {})

    @classmethod
    def load(cls, path: str | Path) -> "State":
        file_path = Path(path)
        if not file_path.exists():
            return cls(file_path)
        data = json.loads(file_path.read_text(encoding="utf-8"))
        entries = data.get("entries")
        if not isinstance(entries, dict):
            entries = {}
        return cls(file_path, entries)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "entries": dict(sorted(self.entries.items()))}
        self.path.write_text(
            json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _keys(person_name: str, publication: Publication) -> tuple[str, ...]:
        keys = [f"{person_name}|{publication.pid}"]
        if publication.title_id:
            keys.append(f"{person_name}|title:{publication.title_id}")
        return tuple(keys)

    def is_seen(self, person_name: str, publication: Publication) -> bool:
        return any(key in self.entries for key in self._keys(person_name, publication))

    def mark_seen(self, person_name: str, publication: Publication, day: dt.date) -> None:
        for key in self._keys(person_name, publication):
            self.entries.setdefault(key, day.isoformat())

    def prune(self, today: dt.date, keep_days: int = KEEP_DAYS) -> None:
        cutoff = today - dt.timedelta(days=keep_days)
        self.entries = {
            key: value
            for key, value in self.entries.items()
            if _entry_date(value, today) >= cutoff
        }
