# Pflicht-QA: blaulicht-cli

- Datum: 2026-11-25
- Version: 0.1.0
- Commit: `19c5fc5` (`docs(ux): UX-Gate-Bericht`)
- Prüfer: separater QA-Durchlauf, Rolle „find -> file“ (keine Code-Fixes)
- Installation: `pipx install git+https://github.com/smlfg/blaulicht-cli` in
  `./scratch/pipx`, Protokoll `scratch/qa/pipx-install.log`
- Aufruf: ausschließlich über `PATH=$PWD/scratch/pipx/bin:$PATH`
- Live-Zugriffe: nur lesende GET-Requests auf presseportal.de; lokale
  Schreibziele nur unter `./scratch/qa/`
- Zusätzlich: `scratch/venv/bin/pytest -q` = 58 passed

## Befunde

| Prüfung | Befehl | Erwartet | Ergebnis | Beleg (gekürzt) |
|---|---|---|---|---|
| Frische pipx-Installation | `pipx install git+https://github.com/smlfg/blaulicht-cli` | `blaulicht` im PATH, Installation erfolgreich | OK | Log: „installed package blaulicht-cli 0.1.0“, App `blaulicht` |
| Version | `blaulicht --version` | Exit 0, Version | OK | `blaulicht 0.1.0`, Exit 0 |
| Hilfe | `blaulicht --help`, `blaulicht <sub> --help` für alle 6 Unterkommandos | Exit 0, verständlich | OK | alle Exit 0; Usage/Options lesbar |
| Schnellstart gegen Fake-Server: `neu` | `blaulicht neu Heilbronn` (PTY, Fake) | Text, 4 Meldungen, Exit 0 | OK | 4 Zeilen mit Datum, POL-HN, Kennung, Titel |
| Schnellstart gegen Fake-Server: `suche` | `blaulicht suche Unfall --ort Heilbronn` (PTY, Fake) | 2 Treffer | OK | „2 Treffer für Unfall in Heilbronn“ |
| Schnellstart gegen Fake-Server: `zeige` | `blaulicht zeige 110971/6397111` (PTY, Fake) | Volltext, Exit 0 | OK | Titel, Dienststelle, Datum, Kennung, Volltext |
| Schnellstart gegen Fake-Server: `watch` | `blaulicht watch Heilbronn` zweimal (PTY, Fake) | 1. Ausgangsstand, 2. keine neuen | OK | „Ausgangsstand gespeichert: 4 …“ / „Keine neuen Meldungen …“ |
| Schnellstart gegen Fake-Server: `dienststelle` | `blaulicht dienststelle "Polizeipräsidium Heilbronn"` (PTY, Fake) | Name → ID 110971, 5 Meldungen | OK | „Polizeipräsidium Heilbronn (Dienststelle 110971)“ |
| Live `neu` | `blaulicht neu Heilbronn --limit 10` | plausible Meldungen für Heilbronn | OK | 10 Meldungen, 23.–25.11.2026, Polizeipräsidium Heilbronn |
| Live `suche`-Filter (Stichwort) | `blaulicht suche Unfall --ort Heilbronn --limit 20 --json` | jeder Treffer enthält „Unfall“ | OK | anzahl 14; Treffer ohne „Unfall“ in Titel/Teaser: keine |
| Live `--seit` (aktuell) | `blaulicht suche Unfall --ort Heilbronn --seit 2026-11-25 --json` | alle Treffer am/ab Tag | OK | anzahl 1; kein Datum < 2026-11-25 |
| Live `--seit` (älter, Vollständigkeit) | `blaulicht suche Unfall --ort Heilbronn --seit 2025-01-01 --limit 100 --json` | auch ältere Treffer seit Datum | **FAIL** | anzahl 14, frühestes Datum 2026-11-11; Website liefert mit `startDate=2025-01-01&endDate=2025-01-31` u. a. `110971/5961820`, das fehlt |
| Live `--bundesland` | `blaulicht suche Unfall --bundesland Baden-Württemberg --limit 5 --json`; zusätzlich Thüringen, Nordrhein-Westfalen | passende Landes-Meldungen | OK | BW/TH/NRW liefern jeweils plausible Dienststellen |
| Live `--volltext` | `blaulicht suche Fahrbahn --ort Heilbronn --limit 5 --json` mit/ohne `--volltext` | ohne: nur Titel/Teaser; mit: auch Detailtreffer | OK | ohne 2 Treffer im Teaser; mit 5 Treffern, die nur im Volltext stehen |
| Live `zeige` per Kennung | `blaulicht zeige 110971/6397786 --json` | Titel, Dienststelle, Datum, Volltext | OK | Kennung, „Polizeipräsidium Heilbronn“, 2026-11-25 12:29, Volltext 3826 Zeichen |
| Live `zeige` per Titelstichwort | `blaulicht zeige Sattelzug --ort Heilbronn --erster --json` | erster Treffer ohne Nachfrage | OK | Kennung `110971/6397786` |
| Live Dienststelle: exakt, Tippfehler, Umlaut | `dienststelle "Polizeipräsidium Heilbronn"`, `"Polizeipraesidium Heilbronn"`, `"Polizeipräsidium Heilbrnn"` | ID 110971 | OK | alle drei lösen auf `name=Polizeipräsidium Heilbronn, id=110971` |
| Live `watch` | erster/zweiter Aufruf, danach `stat` | Ausgangsstand, dann keine neuen; 0700/0600 | OK | `ausgangsstand=true`, dann `false`; State-Datei 600, Ordner 700 |
| `config` und Vorrang | `blaulicht config ort Heilbronn`, `neu` ohne Ort, `BLAULICHT_ORT=… watch` | Config 0600, Ort wird genutzt, Env überschreibt | OK | Config 600; `neu` nutzt Heilbronn; Watch nutzt `BLAULICHT_ORT` |
| Leerer Ort | `blaulicht neu Zzzz-kein-ort-12345` (PTY/live) | Exit 0, Hinweis Ort prüfen | OK | „Keine Meldungen … gefunden. Bitte Ort prüfen.“ |
| Unbekannte Kennung (404) | `blaulicht zeige 110971/9999999 --json` | Exit 1, „nicht gefunden“, nächster Schritt | OK | Exit 1; `naechster_schritt` = `blaulicht neu <Ort> …` |
| Unbekannte/gelöschte Kennung (410) | `blaulicht zeige 110971/1 --json` und `999999999/1 --json` | laut INTERFACE: Exit 1, „Meldung … nicht gefunden“ | **FAIL** | Exit 3; `"/blaulicht/pm/110971/1 liefert HTTP 410"`, nächster Schritt „Pfad prüfen …“ |
| Usage-Fehler | `suche Unfall --seit 2026-13-99`, `neu Heilbronn --limit 0`, `suche '' --ort Heilbronn`, `neu` ohne Ort, `blaulicht quatsch` | Exit 2, nächster Schritt, kein Traceback | OK | alle Exit 2 mit `naechster_schritt`; kein Traceback |
| Netzfehler | `BLAULICHT_BASE_URL=http://127.0.0.1:1 blaulicht neu Heilbronn --json` | Exit 3, Meldung + nächster Schritt, kein Traceback | OK | Exit 3; „Verbindung … fehlgeschlagen“, Hinweis „später erneut versuchen …“ |
| TTY-Auswahl `zeige` | `blaulicht zeige Unfall --ort Heilbronn` (PTY, Fake) | Nummernliste, ungültige Eingabe erneut, dann Detail | OK | „Bitte eine Zahl von 1 bis 2“; danach gewählter Treffer |
| TTY-Auswahl EOF/Strg+C | EOF bzw. `Strg+C` an der Nummernabfrage | sauberer Abbruch, kein Traceback | OK | „Eingabe beendet.“ / Exit 130; kein Traceback |
| JSON-Vertrag | `--json` sowie Pipe-Ausgabe für `neu`, `suche`, `zeige`, `dienststelle`, `watch`, `config`, Fehler | genau ein valides JSON-Objekt | OK | alle mit `json.load` geprüft; Fehlerobjekt enthält `fehler`, `exit`, `naechster_schritt` |
| Text statt JSON im TTY | `script -qc 'blaulicht neu Heilbronn --limit 3'` | lesbarer Text, kein JSON | OK | nummerierte Textliste; kein JSON |
| Fixtures ohne echte Personendaten | Stichprobe `tests/fixtures/ux/*.html` | nur anonymisierte Kontakte | OK | Telefon `000`, E-Mail/URL `example.invalid` |
| User-Agent | lokaler Recorder, `blaulicht neu Heilbronn` | `blaulicht-cli/0.1 (+https://github.com/smlfg/blaulicht-cli)` laut README/INTERFACE | **FAIL** | gesendet: `blaulicht-cli/0.1.0 (+https://github.com/smlfg/blaulicht-cli)` |
| Testsuite | `scratch/venv/bin/pytest -q` | grün | OK | `58 passed in 53.07s` |
| UX-Spec statisch | `python3 tests/harness/ux_check.py . --spec-only` | PASS | OK | UX01/UX06/UX07 PASS, Rest SKIP |

## Zählung

- OK: 29
- FAIL: 3
- Gesamt: 32

## Offene FAILs

1. **`--seit` erreicht ältere Meldungen nicht.** Die Suche lädt nur die erste
   Listenseite und filtert clientseitig. Ältere, auf der Website über
   `startDate`/`endDate` erreichbare Meldungen fehlen stillschweigend.
   Repro: `blaulicht suche Unfall --ort Heilbronn --seit 2025-01-01 --limit 100 --json`
   liefert 14 Treffer ab 2026-11-11; `110971/5961820` (31.01.2025) fehlt.
2. **HTTP 410 wird nicht als „unbekannte Kennung“ behandelt.**
   `blaulicht zeige 110971/1 --json` endet mit Exit 3 und „Pfad prüfen“,
   obwohl INTERFACE für unbekannte Kennungen Exit 1 und
   „Meldung … nicht gefunden“ mit sinnvollem nächsten Schritt verlangt.
3. **User-Agent weicht von der Doku ab.** Gesendet wird
   `blaulicht-cli/0.1.0`, README/INTERFACE nennen `blaulicht-cli/0.1`.

## Nicht als FAIL gewertet (Hinweise)

- `dienststelle "Feuerwehr Quatschhausen"` liefert wegen der dokumentierten
  0.6-Ähnlichkeitsschwelle 14 entfernte Treffer statt „nicht gefunden“.
  Das entspricht INTERFACE, ist aber ein Bedienbarkeitsrisiko.
- `watch` nutzt den 5-Minuten-Cache; unmittelbar nach einer Meldung kann ein
  zweiter Aufruf sie noch nicht als neu sehen. Der Cache ist dokumentiert.
- `BLAULICHT_HEUTE` ist in `INTERFACE.md` als Testvariable genannt, wird im
  Code aber von keinem Befehl ausgewertet (derzeit ohne Auswirkung).
