"""Loading and validating researchers.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .names import fold

VALID_SOURCES = ("arxiv", "openalex")

_ALLOWED_KEYS = {
    "name", "aliases", "categories", "sources",
    "arxiv_categories", "openalex_id", "enabled",
}


class ConfigError(ValueError):
    """Invalid researchers.yaml."""


@dataclass
class Researcher:
    name: str
    aliases: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    sources: tuple[str, ...] = VALID_SOURCES
    arxiv_categories: tuple[str, ...] = ()
    openalex_id: str | None = None
    enabled: bool = True

    def search_names(self) -> tuple[str, ...]:
        """Names accepted when checking a result's author list."""
        return (self.name, *self.aliases)

    def query_names(self) -> tuple[str, ...]:
        """Names used as literal search queries (adds ASCII-folded variants)."""
        queries: list[str] = []
        for name in self.search_names():
            for variant in (name, fold(name)):
                if variant and variant not in queries:
                    queries.append(variant)
        return tuple(queries)


def _str_tuple(raw: object, entry_name: str, key: str) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list) or not all(isinstance(item, str) and item.strip() for item in raw):
        raise ConfigError(f"'{entry_name}': '{key}' muss eine Liste nicht-leerer Strings sein.")
    return tuple(item.strip() for item in raw)


def load_config(path: str | Path) -> list[Researcher]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("researchers"), list):
        raise ConfigError("Erwartet ein Mapping mit der Liste 'researchers'.")

    researchers: list[Researcher] = []
    seen_names: set[str] = set()
    for index, raw in enumerate(data["researchers"]):
        if isinstance(raw, str):
            raw = {"name": raw}
        if not isinstance(raw, dict):
            raise ConfigError(f"Eintrag {index + 1}: erwartet einen Namen oder ein Mapping.")
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ConfigError(f"Eintrag {index + 1}: 'name' fehlt oder ist leer.")
        name = name.strip()

        unknown = set(raw) - _ALLOWED_KEYS
        if unknown:
            raise ConfigError(f"'{name}': unbekannte Schlüssel {sorted(unknown)}.")

        key = name.casefold()
        if key in seen_names:
            raise ConfigError(f"'{name}' ist mehrfach eingetragen.")
        seen_names.add(key)

        sources = tuple(s.lower() for s in _str_tuple(raw.get("sources"), name, "sources")) or VALID_SOURCES
        invalid = set(sources) - set(VALID_SOURCES)
        if invalid:
            raise ConfigError(f"'{name}': unbekannte Quellen {sorted(invalid)} (erlaubt: {list(VALID_SOURCES)}).")

        openalex_id = raw.get("openalex_id")
        if openalex_id is not None and (not isinstance(openalex_id, str) or not openalex_id.strip()):
            raise ConfigError(f"'{name}': 'openalex_id' muss ein nicht-leerer String sein.")

        researchers.append(Researcher(
            name=name,
            aliases=_str_tuple(raw.get("aliases"), name, "aliases"),
            categories=_str_tuple(raw.get("categories"), name, "categories"),
            sources=sources,
            arxiv_categories=_str_tuple(raw.get("arxiv_categories"), name, "arxiv_categories"),
            openalex_id=openalex_id.strip() if isinstance(openalex_id, str) else None,
            enabled=bool(raw.get("enabled", True)),
        ))
    return researchers
