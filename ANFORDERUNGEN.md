# Anforderungen: blaulicht-cli

## Zweck

`blaulicht` bringt Polizei-, Feuerwehr- und Zoll-Pressemeldungen von
[presseportal.de/blaulicht](https://www.presseportal.de/blaulicht) ins
Terminal. Anwohner, Lokaljournalisten, Studierende und Agenten beantworten
damit die Frage „Was ist heute in meiner Region passiert?“ ohne Browser,
Login oder API-Key. Das Werkzeug liest ausschließlich öffentliche Seiten und
führt keine schreibenden Aktionen aus.

## Nutzer-Aufgaben

1. **Neueste Meldungen eines Ortes lesen** – `blaulicht neu Heilbronn`
   zeigt Datum/Uhrzeit, Dienststellen-Kürzel, Kennung und Titel der
   aktuellen Blaulicht-Meldungen. Fremde Meldungen ohne Blaulicht-Bezug
   (z. B. Unternehmen) werden herausgefiltert.
2. **Nach einem Stichwort suchen** – `blaulicht suche Unfall --ort Heilbronn`
   filtert Titel und Teaser clientseitig; optional nach Bundesland, Datum und
   Trefferzahl. `--volltext` bezieht den Meldungstext mit ein.
3. **Eine Meldung im Volltext lesen** – `blaulicht zeige 110971/6397111`
   lädt die Detailseite. Ein Titelstichwort funktioniert ebenfalls; bei
   mehreren Treffern fragt das Terminal nach einer Nummer, Agenten nutzen
   `--erster`.
4. **Eine Dienststelle per Name öffnen** – `blaulicht dienststelle
   "Polizeipräsidium Heilbronn"` löst den Namen tippfehlertolerant gegen das
   Verzeichnis auf und zeigt die neuesten Meldungen dieser Dienststelle.
5. **Neue Meldungen seit dem letzten Aufruf sehen** – `blaulicht watch
   Heilbronn` merkt sich den Stand lokal (Datei 0600) und zeigt beim nächsten
   Aufruf nur neue Kennungen.

## Nachfrage

Quelle: Demand-Gate-Recherche vom **25.11.2026** (dokumentiert im Tool-Brief)
sowie Live-Erkundung von presseportal.de am selben Tag.

- Suchen auf GitHub, PyPI, glama.ai und mcp.so nach „presseportal“ und
  „blaulicht“ ergaben **kein gepflegtes CLI- oder MCP-Werkzeug** (0 Treffer
  für ein aktuelles, ohne API-Key nutzbares Werkzeug).
- Mehrere Eigenbauten belegen wiederkehrenden Bedarf, sind aber verwaist:
  - `tcmetzger/pypresseportal` (★8, nur offizielle API mit Key, 06/2025)
  - `tcmetzger/blaulicht-tracker` (★1)
  - `redadmiral/presseportal-blaulicht-scraper` (2022)
  - `alexanderbrenning/blaulicht` (Scrape + Geocode)
  - `ChristianSch/crime-stats-nlp` (★2)
  - `Aznbai/parse-first-responder-news`
  - `NikolajWaller/Polizeimeldungen_Berlin`
- **Lücke:** Es gibt kein gepflegtes Werkzeug ohne API-Key, das Orts-,
  Bundesland- und Dienststellensuche, Volltext und einen Watch-Modus
  menschenbedienbar im Terminal anbietet. Genau diese Lücke schließt
  `blaulicht`.

## Datenquelle

- HTML-Seiten von `https://www.presseportal.de/blaulicht` (nur lesende
  GET-Requests):
  - Ortsseite `/blaulicht/r/<Ort>` inklusive Paging `/30`, `/60` und
    Datumsfilter `startDate`/`endDate` (inklusive, `JJJJ-MM-TT`).
  - Detailseite `/blaulicht/pm/<dienststelle>/<meldung>`.
  - Dienststellenverzeichnis `/blaulicht/dienststellen` und
    Dienststellenseite `/blaulicht/nr/<id>`.
  - Bundeslandseite `/blaulicht/l/<bundesland>`.
- Die Suche ist clientseitig: Die Orts-/Bundeslandseite wird geladen und
  Titel/Teaser werden gefiltert. Die serverseitige Route
  `/blaulicht/suche?q=` antwortet mit 404 und wird nicht verwendet.
- Kein Login, keine Cookies, kein API-Key. Der User-Agent nennt das Repo
  (`blaulicht-cli/0.1 (+https://github.com/smlfg/blaulicht-cli)`).

## Grenzen

- **Inoffiziell:** Das Werkzeug ist nicht mit der Presseportal-Betreiberin
  verbunden. Es liest öffentlich abrufbare Seiten und kann bei
  HTML-Änderungen brechen.
- **Nur lesend live getestet:** Die Live-Erkundung am 25.11.2026 bestand
  ausschließlich aus GET-Requests. Es werden keine Formulare abgesendet,
  keine Kommentare, Abos oder Alert-Mails erzeugt und keine Konten
  angelegt.
- **Keine Vollständigkeitsgarantie:** Angezeigt wird, was die Website
  öffentlich ausliefert. Paging und Datumsfilter werden bestmöglich genutzt,
  ein Anspruch auf alle Meldungen besteht nicht.
- **Höflichkeit:** höchstens ein Request pro Sekunde, Antworten fünf Minuten
  im Cache (`~/.cache/blaulicht-cli`, 0700), keine Umgehung von Captchas.
- **Datenschutz:** Es werden keine echten Personendaten in Repo, Fixtures
  oder Logs übernommen; Test-Fixtures nutzen `example.invalid`. Watch-Zustand
  und Config werden mit Rechten 0600 gespeichert.
- **Kein Login:** Es gibt keine Zugangsdaten und keinen `login`-Befehl;
  Exit-Code 4 („Login nötig“) bleibt reserviert und wird nicht verwendet.
- **Bundesland-Slugs** werden aus dem Namen gebildet (klein, Umlaute
  transliteriert, Leerzeichen zu `-`); bei unbekannten Slugs meldet das Tool
  einen verständlichen Fehler mit nächstem Schritt.

## Nicht-Ziele

- Keine schreibenden Aktionen, keine Push-Benachrichtigungen, kein E-Mail-
  Versand, keine Abos.
- Keine Geocodierung, keine Karten, keine Archivdatenbank.
- Keine offizielle Presseportal-API (API-Key) und kein Login.
