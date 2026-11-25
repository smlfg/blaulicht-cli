"""Parser-Tests gegen die Live-Fixtures aus tests/fixtures/ux."""

from __future__ import annotations

from pathlib import Path

from blaulicht import parse

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ux"


def _liest(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_liste_liefert_nur_blaulicht_meldungen():
    meldungen = parse.parse_liste(
        _liest("heilbronn_liste.html"), basis="https://www.presseportal.de"
    )

    assert len(meldungen) == 4
    assert [m["kennung"] for m in meldungen] == [
        "110971/6397111",
        "110971/6396898",
        "110971/6396715",
        "110971/6396663",
    ]
    assert all("Lidl" not in m["titel"] for m in meldungen)


def test_liste_felder_sind_komplett():
    erste = parse.parse_liste(
        _liest("heilbronn_liste.html"), basis="https://www.presseportal.de"
    )[0]

    assert erste["kennung"] == "110971/6397111"
    assert erste["dienststelle"] == "Polizeipräsidium Heilbronn"
    assert erste["kuerzel"] == "POL-HN"
    assert erste["datum"] == "2026-11-24"
    assert erste["zeit"] == "13:57"
    assert erste["titel"] == "POL-HN: Landkreis Heilbronn: Unfall"
    assert erste["teaser"].startswith("A6/Neckarsulm: Drei Leichtverletzte")
    assert erste["url"] == "https://www.presseportal.de/blaulicht/pm/110971/6397111"


def test_liste_ohne_p_customer_nutzt_uebergebenen_namen():
    meldungen = parse.parse_liste(
        _liest("dienststelle_110971.html"),
        basis="https://www.presseportal.de",
        dienststelle="Polizeipräsidium Heilbronn",
    )

    assert len(meldungen) == 5
    assert all(m["dienststelle"] == "Polizeipräsidium Heilbronn" for m in meldungen)
    assert meldungen[3]["kennung"] == "110971/6396688"


def test_liste_filtert_ohne_ots_teaser():
    html = """
    <article class="news" data-url-ugly="https:@@www.presseportal.de@blaulicht@pm@1@2">
      <div class="news-meta"><div class="date">01.01.2026 &ndash; 10:00</div></div>
      <h3 class="news-headline-clamp"><a href="/blaulicht/pm/1/2">Kein Ortsverweis</a></h3>
      <p>Beliebiger Text ohne Ortskennung.</p>
    </article>
    """
    assert parse.parse_liste(html, basis="https://www.presseportal.de") == []


def test_liste_kuerzel_nur_bei_kuerzel_form():
    html = """
    <article class="news" data-url-ugly="https:@@www.presseportal.de@blaulicht@pm@1@2">
      <div class="news-meta"><div class="date">01.01.2026 &ndash; 10:00</div></div>
      <h3 class="news-headline-clamp"><a href="/blaulicht/pm/1/2">Stadt warnt: nicht klingeln</a></h3>
      <p>Heilbronn (ots) - Beispieltext.</p>
    </article>
    """
    meldung = parse.parse_liste(html, basis="https://www.presseportal.de")[0]
    assert meldung["kuerzel"] == ""
    assert meldung["titel"] == "Stadt warnt: nicht klingeln"


def test_detail_volltext_ohne_kontaktblock():
    detail = parse.parse_detail(_liest("meldung_6397111.html"))

    assert detail["titel"] == "POL-HN: Landkreis Heilbronn: Unfall"
    assert detail["dienststelle"] == "Polizeipräsidium Heilbronn"
    assert detail["datum"] == "2026-11-24"
    assert detail["zeit"] == "13:57"
    assert "A6/Neckarsulm" in detail["volltext"]
    assert "82 Kinder" in detail["volltext"]
    assert "example.invalid" not in detail["volltext"]
    assert "Heilbronn (ots)" not in detail["volltext"]
    assert "Rückfragen" not in detail["volltext"]
    assert "Original-Content" not in detail["volltext"]
    assert detail["volltext"].splitlines()[0].startswith("A6/Neckarsulm")


def test_dienststellenverzeichnis_nutzt_title_attribut():
    eintraege = parse.parse_dienststellen(_liest("dienststellen.html"))

    assert len(eintraege) == 5
    assert {"id": "110971", "name": "Polizeipräsidium Heilbronn"} in eintraege
    assert {"id": "121248", "name": "Hauptzollamt Heilbronn"} in eintraege
    assert all(e["name"] and e["id"].isdigit() for e in eintraege)


def test_naechste_seite_liest_link_rel_next():
    html = (
        '<html><head><link rel="next" '
        'href="/blaulicht/r/Heilbronn/30?startDate=2025-01-01&amp;endDate=2025-01-31">'
        "</head></html>"
    )
    assert (
        parse.naechste_seite(html)
        == "/blaulicht/r/Heilbronn/30?startDate=2025-01-01&endDate=2025-01-31"
    )
    assert parse.naechste_seite("<html><body>keine Folgeseite</body></html>") == ""


def test_bundesland_slug():
    assert parse.bundesland_slug("Baden-Württemberg") == "baden-wuerttemberg"
    assert parse.bundesland_slug("Thüringen") == "thueringen"
    assert parse.bundesland_slug("Berlin") == "berlin"


def test_datum_text():
    assert parse.datum_text("2026-11-24") == "24.11.2026"
    assert parse.datum_text("") == ""


def test_absolut_loest_relative_links():
    basis = "http://127.0.0.1:8000"
    assert parse.absolut("/blaulicht/pm/1/2", basis) == "http://127.0.0.1:8000/blaulicht/pm/1/2"
    assert parse.absolut("https://example.org/x", basis) == "https://example.org/x"
    assert parse.absolut("", basis) == ""
