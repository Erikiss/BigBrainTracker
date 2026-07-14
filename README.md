# BigBrainTracker 🧠

[![Täglicher Publikations-Check](https://github.com/Erikiss/BigBrainTracker/actions/workflows/daily-check.yml/badge.svg)](https://github.com/Erikiss/BigBrainTracker/actions/workflows/daily-check.yml)
[![CI](https://github.com/Erikiss/BigBrainTracker/actions/workflows/ci.yml/badge.svg)](https://github.com/Erikiss/BigBrainTracker/actions/workflows/ci.yml)

Fragt **einmal täglich** ab, ob eine der beobachteten Personen aus der
BigBrains-Liste ([`researchers.yaml`](researchers.yaml), zurzeit 103 aktive
Einträge) etwas Neues publiziert hat – und meldet Funde als **GitHub-Issue**.

## Wie es funktioniert

1. Eine GitHub Action ([`daily-check.yml`](.github/workflows/daily-check.yml))
   läuft täglich um **05:30 UTC** (07:30 MESZ / 06:30 MEZ).
2. Für jede aktive Person werden zwei Quellen abgefragt:
   - **arXiv** (Autorensuche, Suchfenster 14 Tage) – deckt Preprints ab, wo
     fast alle Personen der Liste publizieren.
   - **OpenAlex** (Suchfenster 45 Tage, wegen Indexierungsverzug) – deckt
     zusätzlich Journal- und Konferenzveröffentlichungen ab.
3. Bereits gemeldete Publikationen stehen in [`data/seen.json`](data/seen.json) und
   werden übersprungen; Duplikate derselben Arbeit über beide Quellen hinweg
   werden zusammengeführt (arXiv-ID/DOI + Titelabgleich).
4. Gibt es Neues, passiert dreierlei:
   - ein **Issue** mit dem Label `publikationen` wird erstellt (Titel z. B.
     „🧠 Neue Publikationen (7) – 2026-07-15“),
   - [`LATEST.md`](LATEST.md) wird mit demselben Report aktualisiert,
   - der neue Stand wird nach `data/seen.json` committet.

**Benachrichtigungen:** Oben rechts im Repo **Watch → Custom → Issues**
aktivieren, dann kommt bei jedem Fund eine E-Mail bzw. Push-Benachrichtigung
(GitHub-App). Wer keine Issues möchte, kann stattdessen nur `LATEST.md`
bzw. die Commits verfolgen.

> **Wichtig:** Der Zeitplan (`schedule`) läuft nur auf dem Default-Branch
> (`main`). Nach dem Merge dieses Branches ist der Tracker aktiv. Der
> allererste Lauf meldet als Startbestand alles aus dem Suchfenster
> (ca. die letzten zwei Wochen), danach nur noch wirklich Neues.
> GitHub deaktiviert geplante Workflows nach 60 Tagen ohne Repo-Aktivität –
> die täglichen State-Commits verhindern das nebenbei.

## Manuell starten

Unter **Actions → Täglicher Publikations-Check → Run workflow** lässt sich der
Check jederzeit von Hand anstoßen (optional mit größerem Suchfenster).

## Personen pflegen

Einträge in [`researchers.yaml`](researchers.yaml) ergänzen oder anpassen –
mehr braucht es nicht. Minimalform ist nur der Name:

```yaml
researchers:
  - name: Ada Lovelace                # einfachster Fall
  - name: Quoc Le
    aliases: [Quoc V. Le]             # weitere Schreibweisen (Suche + Abgleich)
    categories: [foundation-models]   # nur fürs Gruppieren im Report
  - name: Satinder Singh
    sources: [arxiv]                  # sehr häufiger Name: nur arXiv abfragen …
    arxiv_categories: ["cs.", "stat."]  # … und nur ML-nahe Kategorien akzeptieren
  - name: Beispiel Person
    openalex_id: A5012345678          # exakte Zuordnung statt Namenssuche
  - name: Pausierte Person
    enabled: false
```

Die OpenAlex-Autoren-ID (`openalex_id`) findet man über
`https://api.openalex.org/authors?search=Vorname+Nachname` – sie ist der
zuverlässigste Weg, Personen mit häufigen Namen sauber zu treffen.

## Genauigkeit & Grenzen

- **Namensabgleich:** Diakritika werden normalisiert (Łukasz ≙ Lukasz),
  mittlere Namen/Initialen ignoriert („Quoc V. Le“ ≙ „Quoc Le“), abgekürzte
  Vornamen („J. Wei“) bewusst **nicht** akzeptiert. Trotzdem kann reine
  Namenssuche bei Allerweltsnamen Fehltreffer liefern → `openalex_id`,
  `arxiv_categories` oder `sources` nutzen (bei David Silver, Satinder Singh
  und Tom Brown bereits voreingestellt).
- **Deaktivierte Einträge:** „Anthropic (Interpretability Team)“ ist eine
  Organisation (Mitglieder wie Chris Olah und Samuel Marks sind einzeln
  gelistet); David Marr (†1980), David MacKay (†2016) und Ian Hacking (†2023)
  sind historisch. Alle stehen mit `enabled: false` in der Liste.
- **Hinweise zur Liste:** „Timothy Michael Bennett“ ist vermutlich Michael
  Timothy Bennett (ANU, AGI-Theorie) – als Alias hinterlegt. Zu „Ian Gertz“
  ist keine eindeutige Person auffindbar – ggf. Schreibweise korrigieren oder
  `openalex_id` ergänzen.
- **Latenz:** arXiv listet neue Einreichungen meist binnen 1–2 Werktagen,
  OpenAlex indexiert Journals teils mit Wochen Verzug (daher das größere
  Suchfenster dort).

## Lokal ausführen

```bash
pip install -r requirements.txt
python -m tracker --dry-run --only "Yann LeCun, Karl Friston"  # Probelauf, schreibt nichts
python -m tracker --check-config                               # nur YAML validieren
python -m unittest discover -s tests                           # Tests
```

Ein voller Lauf (`python -m tracker`) dauert wegen der arXiv-Rate-Limits
(1 Anfrage / 3 s) etwa 6–8 Minuten und schreibt `report.md`,
`report_title.txt` (beide git-ignoriert), `LATEST.md` und `data/seen.json`.

### Konfiguration

| Variable                 | Standard | Bedeutung                                   |
| ------------------------ | -------- | ------------------------------------------- |
| `LOOKBACK_DAYS`          | `14`     | Suchfenster arXiv in Tagen                  |
| `OPENALEX_LOOKBACK_DAYS` | `45`     | Suchfenster OpenAlex in Tagen               |
| `OPENALEX_MAILTO`        | –        | E-Mail für den schnelleren „polite pool“ von OpenAlex; im Repo als Secret `OPENALEX_MAILTO` hinterlegbar (optional) |

## Projektstruktur

```
researchers.yaml            # die beobachtete Personenliste (hier pflegen!)
tracker/                    # Python-Paket
  __main__.py               #   Ablaufsteuerung (python -m tracker)
  arxiv.py, openalex.py     #   Quellen-Clients
  names.py                  #   Namensnormalisierung & -abgleich
  config.py, state.py       #   YAML-Konfiguration, seen.json-Zustand
  report.py                 #   Markdown-Report (Issue + LATEST.md)
data/seen.json              # bereits gemeldete Publikationen (vom Bot gepflegt)
LATEST.md                   # letzter Report mit Funden
.github/workflows/
  daily-check.yml           # täglicher Check (Cron + manuell)
  ci.yml                    # Tests & Konfig-Validierung bei jedem Push
```
