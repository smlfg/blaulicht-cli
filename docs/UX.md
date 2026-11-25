# UX-Spec: blaulicht

`blaulicht` zeigt Polizei-, Feuerwehr- und Zoll-Pressemeldungen von
presseportal.de/blaulicht im Terminal. Der Dienst ist öffentlich und
schreibfrei: Es gibt keine Anmeldung, keine Cookies und keine Aktion, die
etwas verbindlich auslöst. Alle Befehle sind so abtippbar, wie ein Mensch sie
im Terminal eingibt.

## Meta

```ux-meta
{"tool": "blaulicht",
 "install": "pipx install git+https://github.com/smlfg/blaulicht-cli",
 "base_url_env": "BLAULICHT_BASE_URL",
 "env": {"BLAULICHT_HEUTE": "2026-11-25"}}
```

- `BLAULICHT_BASE_URL` ersetzt `https://www.presseportal.de` und wird von der
  Harness auf den Fake-Server gesetzt.
- `BLAULICHT_HEUTE` setzt nur für Tests das heutige Datum (`JJJJ-MM-TT`), damit
  `--seit` und `watch` deterministisch bleiben. Im Alltag wird es nicht
  gebraucht.
- Es gibt kein `credential_env`: keine Zugangsdaten, kein `login`, kein
  `whoami`/`logout`.

## Sitzungen

### Installation und erste Meldungen

Die Installation per `pipx` legt den Befehl `blaulicht` im PATH ab. Danach
zeigt `neu` die neuesten Meldungen eines Ortes. Jede Zeile nennt Datum und
Uhrzeit, das Dienststellen-Kürzel aus dem Titel, die kombinierte Kennung
`<Dienststelle>/<Meldung>` und darunter den Titel. Fremde Meldungen ohne
Blaulicht-Bezug (z. B. Unternehmen) werden herausgefiltert.

```ux-session
$ pipx install git+https://github.com/smlfg/blaulicht-cli
$ blaulicht neu Heilbronn
< Neueste Blaulicht-Meldungen aus Heilbronn:
< 1) 24.11.2026 13:57 · POL-HN · 110971/6397111
<    POL-HN: Landkreis Heilbronn: Unfall
< 2) 24.11.2026 11:23 · POL-HN · 110971/6396898
<    POL-HN: Neckar-Odenwald-Kreis: Einbruch und Hinweis auf verdächtiges Ansprechen eines Kindes
< 3) 24.11.2026 09:44 · POL-HN · 110971/6396715
<    POL-HN: Stadt- und Landkreis Heilbronn: Einbrüche, Unfall nach verbotenem Kraftfahrzeugrennen
< 4) 24.11.2026 09:04 · POL-HN · 110971/6396663
<    POL-HN: Dunkle Jahreszeit - Hochsaison für ungebetene Gäste! So machen Sie Einbrechern das Leben schwer
! exit 0
```

### Stichwortsuche mit Ort

Das Stichwort ist positional, der Ort ist eine optionale Angabe. Die Suche
lädt die Ortsseite und filtert Titel und Teaser clientseitig; dadurch
funktioniert sie auch ohne die serverseitige Suchroute. Ausgegeben werden nur
Treffer, die das Stichwort wirklich enthalten.

```ux-session
$ blaulicht suche Unfall --ort Heilbronn
< 2 Treffer für Unfall in Heilbronn:
< 1) 24.11.2026 13:57 · POL-HN · 110971/6397111
<    POL-HN: Landkreis Heilbronn: Unfall
< 2) 24.11.2026 09:44 · POL-HN · 110971/6396715
<    POL-HN: Stadt- und Landkreis Heilbronn: Einbrüche, Unfall nach verbotenem Kraftfahrzeugrennen
! exit 0
```

### Meldung im Volltext

`zeige` nimmt die Kennung aus der Liste (`110971/6397111`) oder ein
Titelstichwort. Bei einer Kennung wird die Detailseite direkt geladen. Bei
mehreren Treffern zu einem Stichwort folgt im Terminal eine nummerierte
Auswahl; ohne Terminal wird nur die Liste ausgegeben (Exit 2), mit `--erster`
wird der erste Treffer genommen.

```ux-session
$ blaulicht zeige 110971/6397111
< POL-HN: Landkreis Heilbronn: Unfall
< Polizeipräsidium Heilbronn · 24.11.2026 13:57 · 110971/6397111
< A6/Neckarsulm: Drei Leichtverletzte bei Unfall zwischen zwei Reisebussen
< Bei einem Auffahrunfall zwischen zwei Reisebussen und einem Pkw wurden am Dienstagmorgen
! exit 0
```

### Neue Meldungen seit dem letzten Aufruf

`watch` merkt sich die zuletzt gesehenen Kennungen unter
`~/.local/state/blaulicht-cli` (Datei mit Rechten 0600). Beim ersten Aufruf
wird der Ausgangsstand gespeichert, danach erscheinen nur neue Meldungen.

```ux-session
$ blaulicht watch Heilbronn
< Ausgangsstand gespeichert: 4 Meldungen für Heilbronn.
< Beim nächsten Aufruf werden nur neue Meldungen angezeigt.
$ blaulicht watch Heilbronn
< Keine neuen Meldungen seit dem letzten Aufruf.
! exit 0
```

### Dienststelle per Name

`dienststelle` löst einen Namen tippfehlertolerant gegen das Verzeichnis
`/blaulicht/dienststellen` auf und zeigt die neuesten Meldungen dieser
Dienststelle. Der vollständige Name steht dort im `title`-Attribut der
Newsroom-Links; Linktext und Gattung allein sind nicht eindeutig.

```ux-session
$ blaulicht dienststelle "Polizeipräsidium Heilbronn"
< Polizeipräsidium Heilbronn (Dienststelle 110971)
< Neueste Meldungen:
< 1) 24.11.2026 13:57 · POL-HN · 110971/6397111
<    POL-HN: Landkreis Heilbronn: Unfall
< 2) 24.11.2026 11:23 · POL-HN · 110971/6396898
<    POL-HN: Neckar-Odenwald-Kreis: Einbruch und Hinweis auf verdächtiges Ansprechen eines Kindes
< 3) 24.11.2026 09:44 · POL-HN · 110971/6396715
<    POL-HN: Stadt- und Landkreis Heilbronn: Einbrüche, Unfall nach verbotenem Kraftfahrzeugrennen
< 4) 24.11.2026 09:28 · POL-HN · 110971/6396688
<    POL-HN: Hohenlohekreis: Unfall
< 5) 24.11.2026 09:04 · POL-HN · 110971/6396663
<    POL-HN: Dunkle Jahreszeit - Hochsaison für ungebetene Gäste! So machen Sie Einbrechern das Leben schwer
! exit 0
```

## Lesende Routen

Alle Requests der Sitzungen laufen über `BLAULICHT_BASE_URL`. `path` wird ohne
Querystring verglichen; `--seit` darf zusätzlich `startDate`/`endDate`
anhängen, ohne die Route zu ändern. Die Antworten sind aus echten
Live-Antworten gekürzt und anonymisiert (Kontaktdaten auf `example.invalid`).

```ux-routes
[{"method":"GET","path":"/blaulicht/r/Heilbronn","response":"tests/fixtures/ux/heilbronn_liste.html","status":200,"content_type":"text/html; charset=utf-8"},
 {"method":"GET","path":"/blaulicht/pm/110971/6397111","response":"tests/fixtures/ux/meldung_6397111.html","status":200,"content_type":"text/html; charset=utf-8"},
 {"method":"GET","path":"/blaulicht/dienststellen","response":"tests/fixtures/ux/dienststellen.html","status":200,"content_type":"text/html; charset=utf-8"},
 {"method":"GET","path":"/blaulicht/nr/110971","response":"tests/fixtures/ux/dienststelle_110971.html","status":200,"content_type":"text/html; charset=utf-8"}]
```

## Keine schreibende Aktion

Der Dienst ist rein lesend. Deshalb gibt es bewusst keinen Block
`ux-formsteps` und keine `credential_env`; UX09 entfällt als SKIP. Es werden
weder Formulare abgesendet noch Kommentare, Abos oder Alert-Mails erzeugt.
Die einzigen Requests sind die GET-Routen oben.

## Ausgabe und Fehler

- Im Terminal erscheint lesbarer Text; mit `--json` oder bei einem Pipe-Ausgang
  steht genau ein JSON-Objekt auf stdout, Hinweise gehen auf stderr.
- Ein unbekannter Ort liefert eine leere Liste mit dem Hinweis, den Ort zu
  prüfen (die Website antwortet dort mit 200 und ohne Treffer).
- Eine unbekannte Kennung nennt als nächsten Schritt
  `blaulicht neu <Ort>` oder `blaulicht suche <Stichwort>`.
- Netzwerkfehler nennen den nächsten Schritt und geben keinen Traceback aus.
- `--version` und `--help` enden mit Exit 0.
- Die Basis-URL ist über `BLAULICHT_BASE_URL` überschreibbar; der Standard
  bleibt `https://www.presseportal.de`.
- Der User-Agent nennt das Repo
  (`blaulicht-cli/0.1 (+https://github.com/smlfg/blaulicht-cli)`), Requests
  werden auf höchstens einen pro Sekunde begrenzt und Antworten fünf Minuten
  unter `~/.cache/blaulicht-cli` (0700) zwischengespeichert.
