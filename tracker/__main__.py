"""Einstiegspunkt: python -m tracker

Fragt arXiv und OpenAlex für alle aktiven Personen aus researchers.yaml ab,
vergleicht mit dem gespeicherten Zustand (data/seen.json) und schreibt bei
neuen Publikationen report.md / report_title.txt / LATEST.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

from . import arxiv, openalex
from .config import Researcher, load_config
from .model import Publication
from .report import render_latest, render_report
from .state import State

_SOURCE_MODULES = {"arxiv": arxiv, "openalex": openalex}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, ""))
    except ValueError:
        return default


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tracker",
        description="Täglicher Publikations-Check für die BigBrains-Liste.",
    )
    parser.add_argument("--config", default="researchers.yaml")
    parser.add_argument("--state", default="data/seen.json")
    parser.add_argument("--report", default="report.md")
    parser.add_argument("--title-file", default="report_title.txt")
    parser.add_argument("--latest", default="LATEST.md")
    parser.add_argument("--lookback-days", type=int,
                        default=_env_int("LOOKBACK_DAYS", 14),
                        help="Suchfenster arXiv in Tagen (Standard: 14 bzw. $LOOKBACK_DAYS)")
    parser.add_argument("--openalex-lookback-days", type=int,
                        default=_env_int("OPENALEX_LOOKBACK_DAYS", 45),
                        help="Suchfenster OpenAlex in Tagen (Standard: 45, wegen Indexierungsverzug)")
    parser.add_argument("--only", default="",
                        help="Kommagetrennte Namensliste – nur diese Personen abfragen (für Tests)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Nichts schreiben, Report auf stdout ausgeben")
    parser.add_argument("--check-config", action="store_true",
                        help="Nur die Konfiguration validieren und beenden")
    return parser.parse_args(argv)


def _collect(person: Researcher, cutoffs: dict[str, dt.date]) -> tuple[list[Publication], int, int]:
    publications: list[Publication] = []
    fetches_ok = 0
    fetches_failed = 0
    for source_name, module in _SOURCE_MODULES.items():
        if source_name not in person.sources:
            continue
        try:
            publications.extend(module.fetch(person, cutoffs[source_name]))
            fetches_ok += 1
        except Exception as exc:  # noqa: BLE001 – eine Quelle/Person darf den Lauf nicht stoppen
            fetches_failed += 1
            print(f"WARNUNG {person.name} [{source_name}]: {exc}", file=sys.stderr, flush=True)
    return publications, fetches_ok, fetches_failed


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    researchers = load_config(args.config)
    enabled = [researcher for researcher in researchers if researcher.enabled]

    if args.check_config:
        print(f"Konfiguration OK: {len(researchers)} Einträge, {len(enabled)} aktiv.")
        return 0

    if args.only:
        wanted = {name.strip().casefold() for name in args.only.split(",") if name.strip()}
        enabled = [researcher for researcher in enabled if researcher.name.casefold() in wanted]

    today = dt.date.today()
    cutoffs = {
        "arxiv": today - dt.timedelta(days=args.lookback_days),
        "openalex": today - dt.timedelta(days=args.openalex_lookback_days),
    }
    state = State.load(args.state)

    findings: list[tuple[Researcher, list[Publication]]] = []
    fetches_ok = 0
    fetches_failed = 0
    for index, person in enumerate(enabled, start=1):
        collected, ok, failed = _collect(person, cutoffs)
        fetches_ok += ok
        fetches_failed += failed

        new_publications: list[Publication] = []
        titles_this_run: set[str] = set()
        for publication in sorted(collected, key=lambda p: (p.published, p.pid), reverse=True):
            if state.is_seen(person.name, publication):
                continue
            if publication.title_id and publication.title_id in titles_this_run:
                continue  # gleiche Arbeit aus zweiter Quelle
            titles_this_run.add(publication.title_id)
            new_publications.append(publication)

        if new_publications:
            findings.append((person, new_publications))
            if not args.dry_run:
                for publication in new_publications:
                    state.mark_seen(person.name, publication, today)
        print(f"[{index}/{len(enabled)}] {person.name}: {len(new_publications)} neu", flush=True)

    findings.sort(key=lambda item: item[0].name.casefold())
    total = sum(len(publications) for _, publications in findings)

    if not args.dry_run:
        state.prune(today)
        state.save()

    if findings:
        title, body = render_report(findings, today,
                                    args.lookback_days, args.openalex_lookback_days)
        if args.dry_run:
            print(f"\n--- REPORT (dry-run) ---\n# {title}\n\n{body}")
        else:
            Path(args.report).write_text(body, encoding="utf-8")
            Path(args.title_file).write_text(title + "\n", encoding="utf-8")
            Path(args.latest).write_text(
                render_latest(title, body, dt.datetime.now(dt.timezone.utc)),
                encoding="utf-8",
            )

    print(
        f"Fertig: {total} neue Publikation(en) bei {len(findings)} Person(en); "
        f"Quellen-Abrufe ok={fetches_ok}, fehlgeschlagen={fetches_failed}.",
        flush=True,
    )
    if fetches_failed and fetches_failed >= fetches_ok:
        print("Zu viele fehlgeschlagene Abrufe – Lauf wird als Fehler markiert.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
