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
```

## Befehle

| Befehl | Zweck |
|---|---|
| `blaulicht neu [ORT]` | Neueste Blaulicht-Meldungen für einen Ort oder Landkreis |
| `blaulicht suche STICHWORT [--ort ORT] [--bundesland LAND] [--seit DATUM] [--limit N]` | Titel und Teaser clientseitig filtern |
| `blaulicht zeige KENNUNG\|TITELSTICHWORT` | Volltext einer Meldung; mehrere Treffer werden im Terminal nummeriert |
| `blaulicht dienststelle NAME` | Dienststelle per Name auflösen und ihre Meldungen zeigen |
| `blaulicht watch [ORT]` | Nur Meldungen, die seit dem letzten Aufruf neu sind |
| `blaulicht config ort ORT` | Standard-Ort dauerhaft speichern (Config mit 0600) |

Die Kennung einer Meldung ist `Dienststelle/Meldung`, zum Beispiel
`110971/6397111`. Sie steht in der Listenausgabe und lässt sich direkt an
`zeige` übergeben. Ein Titelstichwort funktioniert ebenfalls; ist es
mehrdeutig, fragt `zeige` im Terminal nach einer Nummer. Ohne Terminal wird
dann die Trefferliste ausgegeben (Exit 2); Agenten nutzen `--erster`.

## Ausgabe und Optionen

- Standardmäßig erscheint lesbarer Text. Mit `--json` oder wenn stdout kein
  Terminal ist, kommt genau ein JSON-Objekt.
- `--limit N` begrenzt die Trefferzahl, `--seit JJJJ-MM-TT` filtert
  clientseitig nach Datum.
- `--version` und `--help` funktionieren ohne Netzzugriff und enden mit Exit 0.
- Fehler nennen den nächsten sinnvollen Befehl und geben keinen Traceback aus.
- Die Basis-URL lässt sich für Tests über `BLAULICHT_BASE_URL` überschreiben;
  `BLAULICHT_HEUTE` setzt das Testdatum.

## Konfiguration und Zwischenspeicher

- `blaulicht config ort Heilbronn` speichert den Standard-Ort unter
  `~/.config/blaulicht-cli/config.json` (Rechte 0600). `BLAULICHT_ORT`
  überschreibt die Datei.
- `watch` merkt sich den Stand unter `~/.local/state/blaulicht-cli` (0600).
- Antworten werden höchstens fünf Minuten unter `~/.cache/blaulicht-cli`
  (0700) zwischengespeichert; Requests laufen mit höchstens einem pro Sekunde.
- Der User-Agent nennt das Repo:
  `blaulicht-cli/0.1 (+https://github.com/smlfg/blaulicht-cli)`.

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

MIT, Copyright smlfg.
