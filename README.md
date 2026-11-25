# blaulicht-cli

Polizei-, Feuerwehr- und Zoll-Pressemeldungen von
[presseportal.de/blaulicht](https://www.presseportal.de/blaulicht) im
Terminal: neueste Meldungen für einen Ort, Stichwortsuche, Volltext,
Dienststellen per Name und ein Watch-Modus für neue Meldungen. Kein Login,
kein API-Key, nur lesende GET-Requests.

## Schnellstart

```text
pipx install git+https://github.com/smlfg/blaulicht-cli
blaulicht neu Heilbronn
blaulicht suche Unfall --ort Heilbronn
blaulicht zeige 110971/6397111
blaulicht watch Heilbronn
blaulicht dienststelle "Polizeipräsidium Heilbronn"
```

Nach der Installation liegt `blaulicht` im PATH. `neu` zeigt die neuesten
Meldungen, `suche` filtert Titel und Teaser, `zeige` öffnet den Volltext,
`watch` merkt sich den Stand und zeigt beim nächsten Aufruf nur Neues.

## Befehle

| Befehl | Zweck |
|---|---|
| `blaulicht neu [ORT]` | Neueste Blaulicht-Meldungen für einen Ort oder Landkreis |
| `blaulicht suche STICHWORT [--ort ORT] [--bundesland LAND] [--seit DATUM] [--limit N] [--volltext]` | Titel und Teaser clientseitig filtern |
| `blaulicht zeige KENNUNG\|TITELSTICHWORT [--erster]` | Volltext einer Meldung; mehrere Treffer werden im Terminal nummeriert |
| `blaulicht dienststelle NAME [--limit N]` | Dienststelle per Name auflösen und ihre Meldungen zeigen |
| `blaulicht watch [ORT]` | Nur Meldungen, die seit dem letzten Aufruf neu sind |
| `blaulicht config ort ORT` | Standard-Ort dauerhaft speichern (Config mit 0600) |

Die Kennung einer Meldung ist `Dienststelle/Meldung`, zum Beispiel
`110971/6397111`. Sie steht in der Listenausgabe und lässt sich direkt an
`zeige` übergeben. Ein Titelstichwort funktioniert ebenfalls; ist es
mehrdeutig, fragt `zeige` im Terminal nach einer Nummer. Ohne Terminal wird
dann die Trefferliste ausgegeben (Exit 2); Agenten nutzen `--erster`.

## Beispiele

```text
blaulicht neu Heilbronn --limit 5
blaulicht suche Einbruch --ort Heilbronn --seit 2026-11-20
blaulicht suche Unfall --bundesland Baden-Württemberg --volltext
blaulicht zeige Unfall --ort Heilbronn --erster
blaulicht dienststelle "Polizeipräsidium Heilbronn" --json
blaulicht watch Heilbronn --json
```

## Ausgabe und Optionen

- Standardmäßig erscheint lesbarer Text. Mit `--json` oder wenn stdout kein
  Terminal ist, kommt genau ein JSON-Objekt.
- `--limit N` begrenzt die Trefferzahl, `--seit JJJJ-MM-TT` filtert
  clientseitig nach Datum (inklusive).
- `--version` und `--help` funktionieren ohne Netzzugriff und enden mit
  Exit 0.
- Fehler nennen den nächsten sinnvollen Befehl und geben keinen Traceback
  aus, auch nicht bei `Strg+C` oder EOF.
- Die Basis-URL lässt sich für Tests über `BLAULICHT_BASE_URL` überschreiben;
  `BLAULICHT_HEUTE` setzt das Testdatum.

## Exit-Codes

| Code | Bedeutung |
|---|---|
| `0` | Erfolg, auch bei leerer Trefferliste |
| `1` | Laufzeitfehler, z. B. unbekannte Kennung oder Dienststelle |
| `2` | Usage, z. B. ungültiges Datum oder fehlender Ort |
| `3` | Netzwerk oder Quelle nicht erreichbar bzw. unerwartete Antwort |
| `4` | Reserviert für „Login nötig“; das Tool braucht keinen Login |
| `130` | Abbruch per `Strg+C` |

## Konfiguration und Zwischenspeicher

- `blaulicht config ort Heilbronn` speichert den Standard-Ort unter
  `~/.config/blaulicht-cli/config.json` (Rechte 0600). `BLAULICHT_ORT`
  überschreibt die Datei.
- `watch` merkt sich den Stand unter `~/.local/state/blaulicht-cli` (0600).
- Antworten werden höchstens fünf Minuten unter `~/.cache/blaulicht-cli`
  (0700) zwischengespeichert; Requests laufen mit höchstens einem pro Sekunde.
- Der User-Agent nennt das Repo:
  `blaulicht-cli/0.1 (+https://github.com/smlfg/blaulicht-cli)`.

## Inoffiziell

Dieses Werkzeug ist nicht mit der Presseportal-Betreiberin verbunden. Es
liest ausschließlich öffentliche Seiten per GET, sendet keine Formulare ab
und legt keine Konten an. Bei Änderungen am Seitenaufbau kann die Ausgabe
brechen; dann bitte ein Issue mit Beispiel-URL öffnen. Bitte die Seite nicht
mit parallelen Massenabrufen belasten – das Tool begrenzt sich selbst auf
einen Request pro Sekunde und cacht Antworten.

## Entwicklung

```text
python3 -m venv scratch/venv
scratch/venv/bin/pip install -e .
scratch/venv/bin/pytest -q
```

Das UX-Gate liegt unverändert in `tests/harness/`:

```text
python3 tests/harness/ux_check.py . --spec-only
python3 tests/harness/ux_check.py .
python3 tests/harness/ux_session.py .
```

## Lizenz

MIT, Copyright smlfg. Siehe [LICENSE](LICENSE).
