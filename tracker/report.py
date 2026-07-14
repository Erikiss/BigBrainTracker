"""Markdown-Report für Issue und LATEST.md."""

from __future__ import annotations

import datetime as dt

from .config import Researcher
from .model import Publication

Findings = list[tuple[Researcher, list[Publication]]]


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
    """Liefert (Issue-Titel, Markdown-Body)."""
    total = sum(len(publications) for _, publications in findings)
    title = f"🧠 Neue Publikationen ({total}) – {run_date.isoformat()}"

    lines = [
        f"Automatische Abfrage vom **{run_date.isoformat()}**: "
        f"**{total}** neue Publikation(en) von **{len(findings)}** beobachteten Person(en).",
        "",
        f"_Suchfenster nach Veröffentlichungsdatum: arXiv {arxiv_days} Tage, "
        f"OpenAlex {openalex_days} Tage. Bereits gemeldete Einträge werden übersprungen; "
        "reine Namenssuche kann vereinzelt Fehltreffer (Namensgleichheit) enthalten._",
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
