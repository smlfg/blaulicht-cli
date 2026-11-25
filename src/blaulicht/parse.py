"""HTML-Auswertung für Listen-, Detail- und Dienststellen-Seiten."""

from __future__ import annotations

import re
from urllib.parse import quote

from bs4 import BeautifulSoup

DATUM_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})\s*[–\-]\s*(\d{2}:\d{2})")
ISO_DATUM_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})[ T](\d{2}:\d{2})")
KENNUNG_RE = re.compile(r"/(?:blaulicht/)?pm/(\d+)/(\d+)")
KUERZEL_RE = re.compile(r"^[A-ZÄÖÜ0-9]+(?:-[A-Z0-9]+)*$")
SLUG_ZEICHEN = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}

AUSGESCHLOSSEN = {
    "date",
    "customer",
    "contact-headline",
    "contact-text",
    "originator",
}


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html or "", "html.parser")


def absolut(link: str, basis: str) -> str:
    """Relative Links gegen die Basis-URL auflösen."""
    link = (link or "").strip()
    if not link:
        return ""
    if link.startswith("http://") or link.startswith("https://"):
        return link
    if link.startswith("//"):
        return "https:" + link
    return basis.rstrip("/") + link


def _datum_aus_text(text: str) -> tuple[str, str]:
    treffer = DATUM_RE.search(text or "")
    if not treffer:
        return "", ""
    tag, monat, jahr, uhrzeit = treffer.groups()
    return f"{jahr}-{monat}-{tag}", uhrzeit


def _teaser(artikel) -> tuple[str, bool]:
    """Liefert (Teaser ohne Ortsverweis, enthält „(ots)“)."""
    h3 = artikel.select_one("h3")
    absatz = h3.find_next_sibling("p") if h3 is not None else None
    if absatz is None and h3 is not None:
        absatz = h3.find_next("p")
    if absatz is None:
        return "", False
    roh = absatz.get_text(" ", strip=True)
    hat_ots = "(ots)" in roh
    text = roh
    kursiv = absatz.find("i")
    if kursiv is not None:
        prefix = kursiv.get_text(" ", strip=True) + " - "
        if text.startswith(prefix):
            text = text[len(prefix) :]
        else:
            text = re.sub(r"^\S.*?\(ots\)\s*[-–]\s*", "", text, count=1)
    return text.strip(), hat_ots


def parse_liste(html: str, basis: str = "", dienststelle: str | None = None) -> list[dict]:
    """Meldungen einer Orts-, Landkreis- oder Dienststellen-Seite.

    Einträge ohne Blaulicht-Bezug (fremde Newsrooms) und ohne ots-Teaser
    fallen heraus.
    """
    soup = _soup(html)
    meldungen: list[dict] = []
    for artikel in soup.select("article.news"):
        link = artikel.select_one("h3 a[href]")
        if link is None:
            continue
        href = (link.get("href") or "").strip()
        roh_url = (artikel.get("data-url-ugly") or "").replace("@", "/")
        if "/blaulicht/pm/" not in href and "/blaulicht/pm/" not in roh_url:
            continue
        teaser, hat_ots = _teaser(artikel)
        if not hat_ots:
            continue
        treffer = KENNUNG_RE.search(href) or KENNUNG_RE.search(roh_url)
        if treffer is None:
            continue

        titel = (link.get("title") or "").strip() or link.get_text(" ", strip=True)
        datum, zeit = "", ""
        datumsfeld = artikel.select_one(".news-meta .date")
        if datumsfeld is not None:
            datum, zeit = _datum_aus_text(datumsfeld.get_text(" ", strip=True))

        kundenfeld = artikel.select_one("p.customer a")
        name = (kundenfeld.get_text(" ", strip=True) if kundenfeld is not None else "") or (
            dienststelle or ""
        )
        kopf = titel.split(":", 1)[0].strip() if ":" in titel else ""
        kuerzel = kopf if KUERZEL_RE.match(kopf) else ""

        meldungen.append(
            {
                "kennung": f"{treffer.group(1)}/{treffer.group(2)}",
                "dienststelle": name,
                "kuerzel": kuerzel,
                "datum": datum,
                "zeit": zeit,
                "titel": titel,
                "teaser": teaser,
                "url": absolut(href, basis),
            }
        )
    return meldungen


def parse_detail(html: str) -> dict:
    """Titel, Dienststelle, Datum und Volltext einer Meldungsseite."""
    soup = _soup(html)
    karte = soup.select_one("article .card") or soup.select_one(".card") or soup

    titelfeld = karte.select_one("h1")
    titel = titelfeld.get_text(" ", strip=True) if titelfeld is not None else ""

    dienststelle = ""
    kundenfeld = karte.select_one("a.story-customer") or karte.select_one("p.customer a")
    if kundenfeld is not None:
        dienststelle = kundenfeld.get_text(" ", strip=True)

    datum, zeit = "", ""
    zeitfeld = karte.select_one("p.date time")
    if zeitfeld is not None and zeitfeld.get("datetime"):
        treffer = ISO_DATUM_RE.search(zeitfeld["datetime"])
        if treffer:
            jahr, monat, tag, uhrzeit = treffer.groups()
            datum, zeit = f"{jahr}-{monat}-{tag}", uhrzeit
    if not datum:
        datumsfeld = karte.select_one("p.date")
        if datumsfeld is not None:
            datum, zeit = _datum_aus_text(datumsfeld.get_text(" ", strip=True))

    abschnitte: list[str] = []
    for absatz in karte.find_all("p"):
        klassen = set(absatz.get("class") or [])
        if klassen & AUSGESCHLOSSEN:
            continue
        text = absatz.get_text(" ", strip=True)
        if not text:
            continue
        if absatz.find("i") is not None and "(ots)" in text:
            continue
        if absatz.find(class_="story-city") is not None:
            continue
        abschnitte.append(text)

    return {
        "titel": titel,
        "dienststelle": dienststelle,
        "datum": datum,
        "zeit": zeit,
        "volltext": "\n".join(abschnitte),
    }


def parse_dienststellen(html: str) -> list[dict]:
    """Verzeichnis aller Newsrooms: Name steht im title-Attribut."""
    soup = _soup(html)
    ergebnis: list[dict] = []
    gesehen: set[str] = set()
    for link in soup.select('a[href*="/blaulicht/nr/"]'):
        href = link.get("href") or ""
        treffer = re.search(r"/blaulicht/nr/(\d+)", href)
        if treffer is None:
            continue
        kennung = treffer.group(1)
        if kennung in gesehen:
            continue
        titel = (link.get("title") or "").strip()
        vorzeichen = "weiter zum newsroom von "
        if titel.lower().startswith(vorzeichen):
            name = titel[len(vorzeichen) :].strip()
        else:
            name = link.get_text(" ", strip=True)
        if not name:
            continue
        gesehen.add(kennung)
        ergebnis.append({"id": kennung, "name": name})
    return ergebnis


def naechste_seite(html: str) -> str:
    """Link auf die Folgeseite einer Liste (leer, wenn es keine gibt)."""
    soup = _soup(html)
    link = soup.select_one('link[rel="next"][href]')
    if link is not None:
        return (link.get("href") or "").strip()
    marke = soup.select_one(".pagination-next[data-url]")
    if marke is not None:
        roh = (marke.get("data-url") or "").strip()
        if roh.startswith("@"):
            roh = roh[1:].replace("@", "/")
        return roh
    return ""


def bundesland_slug(land: str) -> str:
    """„Baden-Württemberg“ -> „baden-wuerttemberg“."""
    text = (land or "").strip().lower()
    for alt, neu in SLUG_ZEICHEN.items():
        text = text.replace(alt, neu)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def ort_pfad(ort: str) -> str:
    return "/blaulicht/r/" + quote(ort.strip())


def datum_text(iso: str) -> str:
    """2026-11-24 -> 24.11.2026 (leere Eingabe bleibt leer)."""
    if not iso or len(iso) != 10:
        return iso
    jahr, monat, tag = iso.split("-")
    return f"{tag}.{monat}.{jahr}"
