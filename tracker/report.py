"""Markdown-Report für Issue und LATEST.md."""

from __future__ import annotations

import datetime as dt

from .config import Researcher
from .model import Publication

Findings = list[tuple[Researcher, list[Publication]]]


def deduplicate_findings(findings: Findings) -> Findings:
    """List each work once, under its first researcher, without changing inputs.

    Canonical IDs or normalised titles connect records across authors/sources.
    Resolve all connections before selecting representatives: a later record
    can link two earlier records through its ID and title respectively.
    """
    records = [
        (group, publication)
        for group, (_, publications) in enumerate(findings)
        for publication in publications
    ]
    parents = list(range(len(records)))
    keys: dict[tuple[str, str], int] = {}

    def root(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for index, (_, publication) in enumerate(records):
        for kind, value in (("pid", publication.pid), ("title", publication.title_id)):
            if not value:
                continue
            key = (kind, value)
            if key in keys:
                first, other = sorted((root(index), root(keys[key])))
                parents[other] = first
            else:
                keys[key] = index

    unique: list[list[Publication]] = [[] for _ in findings]
    for index, (group, publication) in enumerate(records):
        if root(index) == index:
            unique[group].append(publication)
    return [
        (researcher, publications)
        for (researcher, _), publications in zip(findings, unique)
        if publications
    ]


def _format_publication(publication: Publication) -> str:
    if publication.source == "arxiv":
        source = "arXiv"
        if publication.categories:
            source += f" · {publication.categories[0]}"
    else:
        source = "OpenAlex"
        if publication.venue:
            source += f" · {publication.venue}"
    return (
        f"- **{publication.published.isoformat()}** · "
        f"[{publication.title}]({publication.url}) — {source}"
    )


def render_report(findings: Findings, run_date: dt.date,
                  arxiv_days: int, openalex_days: int) -> tuple[str, str]:
    """Liefert (Issue-Titel, Markdown-Body), mit jeder Arbeit genau einmal."""
    findings = deduplicate_findings(findings)
    total = sum(len(publications) for _, publications in findings)
    title = f"🧠 Neue Publikationen ({total}) – {run_date.isoformat()}"

    lines = [
        f"Automatische Abfrage vom **{run_date.isoformat()}**: "
        f"**{total}** neue Publikation(en), einmalig gelistet unter "
        f"**{len(findings)}** beobachteten Person(en).",
        "",
        f"_Suchfenster nach Veröffentlichungsdatum: arXiv {arxiv_days} Tage, "
        f"OpenAlex {openalex_days} Tage. Bereits gemeldete Einträge werden übersprungen; "
        "reine Namenssuche kann vereinzelt Fehltreffer (Namensgleichheit) enthalten._",
        "",
        "_Gemeinsame Arbeiten erscheinen nur bei der ersten zugeordneten Person "
        "in der alphabetischen Report-Reihenfolge; das bezeichnet keine Erstautorenschaft._",
        "",
    ]
    for researcher, publications in findings:
        category_note = (
            f" _({', '.join(researcher.categories)})_" if researcher.categories else ""
        )
        lines.append(f"### {researcher.name}{category_note}")
        lines.append("")
        lines.extend(_format_publication(publication) for publication in publications)
        lines.append("")
    return title, "\n".join(lines).rstrip() + "\n"


def render_latest(title: str, body: str, generated_at: dt.datetime) -> str:
    stamp = generated_at.strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"# {title}\n\n"
        f"_Letzter Lauf mit Funden: {stamp} – erzeugt von "
        f"[daily-check](.github/workflows/daily-check.yml)._\n\n"
        f"{body}"
    )
