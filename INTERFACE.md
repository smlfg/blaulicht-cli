# Schnittstelle: blaulicht

Vertrag für das Kommando `blaulicht`. Maßgeblich für Implementierung und
Akzeptanztests. Abweichungen sind Fehler.

## Aufruf

```text
blaulicht [--version] [--help]
blaulicht neu [ORT] [--limit N] [--json]
blaulicht suche STICHWORT [--ort ORT | --bundesland LAND] [--seit JJJJ-MM-TT] [--limit N] [--volltext] [--json]
blaulicht zeige KENNUNG|TITELSTICHWORT [--ort ORT] [--limit N] [--erster] [--json]
blaulicht dienststelle NAME [--limit N] [--json]
blaulicht watch [ORT] [--limit N] [--json]
blaulicht config [ort [ORT]] [--json]
```

Alle Argumente mit Namen sind positional und für Menschen abtippbar. IDs sind
nie Pflicht; sie sind nur eine alternative Kennung aus der Listenausgabe.
`--json` ist global und darf vor oder nach dem Unterkommando stehen.

## Unterkommandos

### `neu [ORT]`

Neueste Blaulicht-Meldungen für einen Ort oder Landkreis.

- `ORT` (optional): Ortsname, z. B. `Heilbronn`. Fehlt er, gilt
  `BLAULICHT_ORT`, sonst `config.ort`. Ist nichts gesetzt: Exit 2 mit Hinweis
  auf `blaulicht config ort <ORT>`.
- `--limit N` (Default `10`): höchstens N Meldungen.
- Filtert Einträge ohne Blaulicht-Bezug (kein `@blaulicht@` in der
  Meldungs-URL bzw. kein `ots`-Teaser) heraus.
- Textausgabe:

  ```text
  Neueste Blaulicht-Meldungen aus Heilbronn:
  1) 24.11.2026 13:57 · POL-HN · 110971/6397111
     POL-HN: Landkreis Heilbronn: Unfall
  ```

- Leerer Ort: Exit 0, Text `Keine Meldungen für <ORT> gefunden. Bitte Ort
  prüfen.`

### `suche STICHWORT`

Stichwortsuche über Titel und Teaser, optional eingeschränkt.

- `STICHWORT` (Pflicht): case-insensitive Teilstring.
- `--ort ORT`: lädt die Ortsseite. Ohne `--ort`/`--bundesland` gilt
  `BLAULICHT_ORT`, dann `config.ort`; sonst Exit 2.
- `--bundesland LAND`: lädt `/blaulicht/l/<slug>`; Slug = klein,
  Umlaute transliteriert (`ä→ae`, `ö→oe`, `ü→ue`, `ß→ss`), Leerzeichen zu
  `-`.
- `--seit JJJJ-MM-TT`: nur Meldungen ab diesem Tag (inklusive). Ungültiges
  Datum: Exit 2.
- `--limit N` (Default `10`): höchstens N Treffer.
- `--volltext`: lädt zusätzlich die Detailseite je Kandidat und sucht auch
  im Volltext (mehr Requests, langsamer).
- Textausgabe:

  ```text
  2 Treffer für Unfall in Heilbronn:
  1) 24.11.2026 13:57 · POL-HN · 110971/6397111
     POL-HN: Landkreis Heilbronn: Unfall
  ```

- Keine Treffer: Exit 0, Text `Keine Treffer für <STICHWORT> in <Ort>.`

### `zeige KENNUNG|TITELSTICHWORT`

Volltext einer Meldung.

- Enthält das Argument `/` und beide Teile sind Ziffern (`<dienststelle>/
  <meldung>`, z. B. `110971/6397111`): Detailseite direkt laden.
- Sonst als Titelstichwort behandeln: Liste des Ortes laden (`--ort`,
  `BLAULICHT_ORT`, `config.ort`) und Titel durchsuchen.
- Genau ein Treffer: Detailseite laden.
- Mehrere Treffer:
  - im TTY: nummerierte Auswahl auf stderr, Eingabe einer Nummer;
    ungültige Eingabe erneut fragen; `Strg+C`/EOF ohne Traceback → Exit 2.
  - ohne TTY: Trefferliste auf stdout, Exit 2.
  - `--erster`: ersten Treffer ohne Nachfrage nehmen.
- `--limit N` (Default `10`): Suchfenster für das Titelstichwort.
- Textausgabe:

  ```text
  POL-HN: Landkreis Heilbronn: Unfall
  Polizeipräsidium Heilbronn · 24.11.2026 13:57 · 110971/6397111
  A6/Neckarsulm: Drei Leichtverletzte bei Unfall zwischen zwei Reisebussen
  Bei einem Auffahrunfall zwischen zwei Reisebussen und einem Pkw wurden ...
  ```

  Die Ortszeile (`Heilbronn (ots)`), Kontaktblock und Herkunftshinweis
  entfallen im Volltext.
- Unbekannte Kennung: Exit 1, Text `Meldung <KENNUNG> nicht gefunden. Als
  Nächstes: blaulicht neu <Ort> oder blaulicht suche <Stichwort>`.

### `dienststelle NAME`

Dienststelle per Name auflösen und ihre neuesten Meldungen zeigen.

- `NAME` (Pflicht): vollständiger oder ungefährer Name, z. B.
  `"Polizeipräsidium Heilbronn"`. Auflösung gegen
  `/blaulicht/dienststellen` (vollständiger Name im `title`-Attribut),
  tippfehlertolerant.
- Exakter Treffer gewinnt; sonst bester Ähnlichkeitswert ab `0.6`.
  Mehrere ähnlich gute Treffer: im TTY nummerierte Auswahl, ohne TTY Liste +
  Exit 2.
- Kein Treffer: Exit 1 mit Hinweis auf `blaulicht dienststelle <Name>` bzw.
  `blaulicht neu <Ort>`.
- `--limit N` (Default `10`).
- Textausgabe:

  ```text
  Polizeipräsidium Heilbronn (Dienststelle 110971)
  Neueste Meldungen:
  1) 24.11.2026 13:57 · POL-HN · 110971/6397111
     POL-HN: Landkreis Heilbronn: Unfall
  ```

### `watch [ORT]`

Nur Meldungen, die seit dem letzten Aufruf neu sind.

- `ORT` optional wie bei `neu`.
- Zustandsdatei: `$XDG_STATE_HOME/blaulicht-cli/watch.json` (Fallback
  `~/.local/state/blaulicht-cli/watch.json`), Verzeichnis 0700, Datei 0600.
  Schlüssel je Ort, Wert = Liste zuletzt gesehener Kennungen.
- Erster Aufruf: aktuellen Stand speichern, Text
  `Ausgangsstand gespeichert: <N> Meldungen für <Ort>.` plus Hinweis, dass
  der nächste Aufruf nur Neues zeigt. Exit 0.
- Folgende Aufrufe: Differenz der Kennungen ausgeben. Keine neuen: Text
  `Keine neuen Meldungen seit dem letzten Aufruf.` Exit 0.
- `--limit N` (Default `10`) begrenzt die angezeigten neuen Meldungen; der
  gespeicherte Stand enthält weiterhin alle gesehenen Kennungen.

### `config [ort [ORT]]`

- `blaulicht config` zeigt die Pfade und den gespeicherten Standard-Ort.
- `blaulicht config ort Heilbronn` speichert `{"ort": "Heilbronn"}` in
  `$XDG_CONFIG_HOME/blaulicht-cli/config.json` (Fallback
  `~/.config/blaulicht-cli/config.json`), Verzeichnis 0700, Datei 0600.
- Ungültiger Schlüssel: Exit 2 mit Liste der erlaubten Schlüssel (`ort`).

## Ausgabeformat

- **Text** (Default, wenn stdout ein TTY ist): lesbare, nummerierte Listen
  wie oben. Hinweise und Fehler auf stderr.
- **JSON**: bei `--json` oder wenn stdout kein TTY ist (Pipe/Agent). Genau
  ein JSON-Objekt auf stdout, keine weiteren Zeilen; Hinweise auf stderr.
  Fehlerobjekt: `{"fehler": "...", "exit": <code>, "naechster_schritt":
  "..."}`.

### JSON-Schemata

```json
{"ort": "Heilbronn", "anzahl": 4,
 "meldungen": [{"kennung": "110971/6397111",
                "dienststelle": "Polizeipräsidium Heilbronn",
                "kuerzel": "POL-HN",
                "datum": "2026-11-24", "zeit": "13:57",
                "titel": "POL-HN: Landkreis Heilbronn: Unfall",
                "teaser": "A6/Neckarsulm: ...",
                "url": "https://www.presseportal.de/blaulicht/pm/110971/6397111"}]}
```

```json
{"stichwort": "Unfall", "ort": "Heilbronn", "anzahl": 2,
 "treffer": [ /* Meldungsobjekte wie oben */ ]}
```

```json
{"kennung": "110971/6397111",
 "titel": "POL-HN: Landkreis Heilbronn: Unfall",
 "dienststelle": "Polizeipräsidium Heilbronn",
 "datum": "2026-11-24", "zeit": "13:57",
 "volltext": "A6/Neckarsulm: ...",
 "url": "https://www.presseportal.de/blaulicht/pm/110971/6397111"}
```

```json
{"dienststelle": {"name": "Polizeipräsidium Heilbronn", "id": "110971"},
 "anzahl": 5, "meldungen": [ /* Meldungsobjekte wie oben */ ]}
```

```json
{"ort": "Heilbronn", "ausgangsstand": true, "anzahl": 0,
 "gespeichert": 4, "neu": [ /* Meldungsobjekte wie oben */ ]}
```

```json
{"config_pfad": "/home/<user>/.config/blaulicht-cli/config.json",
 "state_pfad": "/home/<user>/.local/state/blaulicht-cli/watch.json",
 "cache_pfad": "/home/<user>/.cache/blaulicht-cli", "ort": "Heilbronn"}
```

Bei Mehrdeutigkeit ohne TTY liefert `zeige`/`dienststelle` ein Objekt
`{"fehler": "...", "exit": 2, "treffer": [...]}`.

## Exit-Codes

| Code | Bedeutung |
|---|---|
| `0` | Erfolg, auch bei leerer Trefferliste |
| `1` | Laufzeitfehler: unbekannte Kennung/Dienststelle, Config-Schreibfehler, unerwartete Antwort |
| `2` | Usage: ungültige Argumente, fehlender Ort, Mehrdeutigkeit ohne TTY, ungültiges Datum |
| `3` | Netzwerk/Quelle: Verbindungsfehler, Timeout, HTTP-Status ≥ 400, unlesbares HTML |
| `4` | Reserviert für „Login nötig“; wird nicht verwendet (kein Login) |
| `130` | Abbruch per `Strg+C`, ohne Traceback |

## Umgebungsvariablen

| Variable | Bedeutung |
|---|---|
| `BLAULICHT_BASE_URL` | Basis-URL, Default `https://www.presseportal.de` (für Fake-Server/Tests) |
| `BLAULICHT_ORT` | Standard-Ort; überschreibt `config.ort` |
| `BLAULICHT_HEUTE` | Nur Test: heutiges Datum als `JJJJ-MM-TT`; im Alltag ungenutzt |
| `XDG_CONFIG_HOME` | Basis für Config, Default `~/.config` |
| `XDG_STATE_HOME` | Basis für Watch-Zustand, Default `~/.local/state` |
| `XDG_CACHE_HOME` | Basis für Cache, Default `~/.cache` |

## Pfade und Zwischenspeicher

- Config: `$XDG_CONFIG_HOME/blaulicht-cli/config.json` (Datei 0600, Ordner
  0700).
- State: `$XDG_STATE_HOME/blaulicht-cli/watch.json` (Datei 0600, Ordner
  0700).
- Cache: `$XDG_CACHE_HOME/blaulicht-cli` (Ordner 0700), Einträge höchstens
  fünf Minuten gültig.
- Höflichkeit: höchstens ein Request pro Sekunde; nur GET.
- User-Agent: `blaulicht-cli/0.1 (+https://github.com/smlfg/blaulicht-cli)`.
