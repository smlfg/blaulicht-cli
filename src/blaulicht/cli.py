"""Kommandozeile für blaulicht: Argumente, Ausgabe, Exit-Codes."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlsplit

from . import __version__, pfade, parse
from .client import Client
from .fehler import (
    BlaulichtFehler,
    HttpFehler,
    LaufzeitFehler,
    MehrdeutigFehler,
    NetzFehler,
    UsageFehler,
)

DATUM_MUSTER = re.compile(r"^\d{4}-\d{2}-\d{2}$")
KENNUNG_ARG = re.compile(r"^(\d+)/(\d+)$")
MAX_SEITEN = 60


# ---------------------------------------------------------------------- Ausgabe


def _ist_tty(stream) -> bool:
    try:
        return bool(stream.isatty())
    except (AttributeError, OSError, ValueError):
        return False


class Ausgabe:
    """Text für Menschen, JSON für Agenten – genau ein Objekt auf stdout."""

    def __init__(self, json_gefordert: bool = False):
        self.json = bool(json_gefordert) or not _ist_tty(sys.stdout)

    def zeige(self, objekt: dict, text: str) -> None:
        if self.json:
            print(json.dumps(objekt, ensure_ascii=False))
        else:
            print(text)

    def hinweis(self, text: str) -> None:
        print(text, file=sys.stderr)


class BefehlsParser(argparse.ArgumentParser):
    """Usage-Fehler werden als BlaulichtFehler gemeldet, nie als Traceback."""

    def error(self, message: str):
        raise UsageFehler(message, "blaulicht --help zeigt alle Befehle und Optionen")


def _fehler_ausgeben(fehler: BlaulichtFehler, json_modus: bool) -> int:
    if json_modus:
        objekt = {
            "fehler": fehler.meldung,
            "exit": fehler.exit_code,
            "naechster_schritt": fehler.naechster_schritt,
        }
        if isinstance(fehler, MehrdeutigFehler):
            objekt["treffer"] = fehler.treffer
        print(json.dumps(objekt, ensure_ascii=False))
    else:
        if isinstance(fehler, MehrdeutigFehler) and fehler.treffer:
            print(_liste_text(fehler.treffer))
        print(f"Fehler: {fehler.meldung}", file=sys.stderr)
        if fehler.naechster_schritt:
            print(f"Als Nächstes: {fehler.naechster_schritt}", file=sys.stderr)
    return fehler.exit_code


# -------------------------------------------------------------------- Helfer


def _limit(wert: int) -> int:
    if wert < 1:
        raise UsageFehler(
            f"--limit muss mindestens 1 sein (erhalten: {wert}).",
            "--limit 10 verwenden",
        )
    return wert


def _ort_holen(vorgabe: str | None) -> str:
    ort = (vorgabe or "").strip()
    if not ort:
        ort = os.environ.get("BLAULICHT_ORT", "").strip()
    if not ort:
        ort = str(pfade.lade_config().get("ort") or "").strip()
    if not ort:
        raise UsageFehler(
            "Kein Ort angegeben.",
            "blaulicht config ort <ORT> ausführen oder BLAULICHT_ORT setzen",
        )
    return ort


def _datum_pruefen(wert: str) -> str:
    roh = (wert or "").strip()
    if not DATUM_MUSTER.match(roh):
        raise UsageFehler(
            f"Ungültiges Datum: {wert!r} (Format JJJJ-MM-TT).",
            "ein Datum wie 2026-11-24 angeben",
        )
    try:
        dt.date.fromisoformat(roh)
    except ValueError:
        raise UsageFehler(
            f"Ungültiges Datum: {wert!r} (Format JJJJ-MM-TT).",
            "ein Datum wie 2026-11-24 angeben",
        ) from None
    return roh


def _heute() -> str:
    roh = os.environ.get("BLAULICHT_HEUTE", "").strip()
    if DATUM_MUSTER.match(roh):
        return roh
    return dt.date.today().isoformat()


def _pruefe_seite(html: str, pfad: str) -> None:
    klein = (html or "").lower()
    if "<html" not in klein and "<article" not in klein and "<!doctype" not in klein:
        raise NetzFehler(
            f"Antwort auf {pfad} ist kein Blaulicht-Seiten-HTML.",
            "später erneut versuchen oder die Adresse prüfen",
        )


def _lade_liste_html(client: Client, pfad: str) -> str:
    html = client.get(pfad)
    _pruefe_seite(html, pfad)
    return html


def _lade_liste(client: Client, pfad: str, dienststelle: str | None = None) -> list[dict]:
    html = client.get(pfad)
    _pruefe_seite(html, pfad)
    return parse.parse_liste(html, basis=client.basis, dienststelle=dienststelle)


def _detail_laden(client: Client, dienststelle: str, meldung: str) -> dict:
    """Detailseite laden und als Meldungsobjekt mit Kennung und URL liefern."""
    pfad = f"/blaulicht/pm/{dienststelle}/{meldung}"
    html = client.get(pfad)
    _pruefe_seite(html, pfad)
    roh = parse.parse_detail(html)
    return {
        "kennung": f"{dienststelle}/{meldung}",
        "titel": roh["titel"],
        "dienststelle": roh["dienststelle"],
        "datum": roh["datum"],
        "zeit": roh["zeit"],
        "volltext": roh["volltext"],
        "url": client.basis + pfad,
    }


def _liste_text(meldungen: list[dict]) -> str:
    zeilen: list[str] = []
    for nummer, meldung in enumerate(meldungen, 1):
        teile = [f"{parse.datum_text(meldung['datum'])} {meldung['zeit']}".strip()]
        if meldung.get("kuerzel"):
            teile.append(meldung["kuerzel"])
        teile.append(meldung["kennung"])
        zeilen.append(f"{nummer}) {' · '.join(teile)}")
        zeilen.append(f"   {meldung['titel']}")
    return "\n".join(zeilen)


def _namen_normieren(text: str) -> str:
    return " ".join((text or "").split()).casefold()


# ------------------------------------------------------------------- Unterkommando


def cmd_neu(args, out: Ausgabe) -> int:
    """Neueste Blaulicht-Meldungen eines Ortes."""
    ort = _ort_holen(args.ort)
    limit = _limit(args.limit)
    client = Client()
    meldungen = _lade_liste(client, parse.ort_pfad(ort))[:limit]
    objekt = {"ort": ort, "anzahl": len(meldungen), "meldungen": meldungen}
    if not meldungen:
        out.zeige(objekt, f"Keine Meldungen für {ort} gefunden. Bitte Ort prüfen.")
        return 0
    text = f"Neueste Blaulicht-Meldungen aus {ort}:\n{_liste_text(meldungen)}"
    out.zeige(objekt, text)
    return 0


def _seit_ok(meldung: dict, seit: str | None) -> bool:
    return not seit or bool(meldung.get("datum")) and meldung["datum"] >= seit


def _seit_filter(meldungen: list[dict], seit: str | None) -> list[dict]:
    return [m for m in meldungen if _seit_ok(m, seit)]


def _enthaelt_stichwort(meldung: dict, stichwort: str) -> bool:
    text = f"{meldung.get('titel', '')} {meldung.get('teaser', '')}"
    return stichwort.casefold() in text.casefold()


def _suche_ziel(args) -> tuple[str, str]:
    """Liefert (Seitenpfad, Anzeigename) für Ort bzw. Bundesland."""
    if args.bundesland:
        land = args.bundesland.strip()
        if not land:
            raise UsageFehler(
                "Leeres Bundesland angegeben.",
                "ein Bundesland wie Baden-Württemberg angeben",
            )
        return f"/blaulicht/l/{parse.bundesland_slug(land)}", land
    ort = _ort_holen(args.ort)
    return parse.ort_pfad(ort), ort


def _listen_seiten(client: Client, pfad: str, params: dict | None = None):
    """HTML der Listenseite und ihrer Folgeseiten (max. MAX_SEITEN)."""
    naechster_pfad = pfad
    naechste_params = params
    for _ in range(MAX_SEITEN):
        html = client.get(naechster_pfad, params=naechste_params)
        _pruefe_seite(html, naechster_pfad)
        yield html
        link = parse.naechste_seite(html)
        if not link:
            return
        ziel = urlsplit(link)
        if not ziel.path.startswith("/"):
            return
        naechster_pfad = ziel.path
        naechste_params = dict(parse_qsl(ziel.query)) or None


def cmd_suche(args, out: Ausgabe) -> int:
    """Stichwortsuche über Titel und Teaser, optional im Volltext."""
    stichwort = (args.stichwort or "").strip()
    if not stichwort:
        raise UsageFehler(
            "Kein Stichwort angegeben.",
            "blaulicht suche <STICHWORT> [--ort ORT] ausführen",
        )
    limit = _limit(args.limit)
    seit = _datum_pruefen(args.seit) if args.seit else None

    pfad, ziel = _suche_ziel(args)
    client = Client()
    if seit:
        seiten = _listen_seiten(
            client, pfad, {"startDate": seit, "endDate": _heute()}
        )
    else:
        seiten = iter([_lade_liste_html(client, pfad)])

    treffer: list[dict] = []
    gesehen: set[str] = set()
    for html in seiten:
        for meldung in parse.parse_liste(html, basis=client.basis):
            if meldung["kennung"] in gesehen:
                continue
            gesehen.add(meldung["kennung"])
            if not _seit_ok(meldung, seit):
                continue
            passt = _enthaelt_stichwort(meldung, stichwort)
            if not passt and args.volltext:
                teile = meldung["kennung"].split("/")
                if len(teile) == 2:
                    detail = _detail_laden(client, teile[0], teile[1])
                    passt = stichwort.casefold() in detail["volltext"].casefold()
            if passt:
                treffer.append(meldung)
            if len(treffer) >= limit:
                break
        if len(treffer) >= limit:
            break

    objekt = {
        "stichwort": stichwort,
        "ort": ziel,
        "anzahl": len(treffer),
        "treffer": treffer,
    }
    if not treffer:
        out.zeige(objekt, f"Keine Treffer für {stichwort} in {ziel}.")
        return 0
    text = f"{len(treffer)} Treffer für {stichwort} in {ziel}:\n{_liste_text(treffer)}"
    out.zeige(objekt, text)
    return 0


def _kennung_zerlegen(text: str) -> tuple[str, str] | None:
    treffer = KENNUNG_ARG.match((text or "").strip())
    if treffer is None:
        return None
    return treffer.group(1), treffer.group(2)


def _waehle(treffer: list[dict], was: str) -> dict:
    """Nummerierte Auswahl im TTY; ohne TTY Liste und Exit 2."""
    if not _ist_tty(sys.stdin):
        raise MehrdeutigFehler(
            f"{len(treffer)} Treffer für {was}.",
            treffer,
            "Suchbegriff präzisieren oder --erster verwenden",
        )
    for nummer, meldung in enumerate(treffer, 1):
        print(f"{nummer}) {meldung['titel']}", file=sys.stderr)
    while True:
        print("Nummer wählen: ", end="", file=sys.stderr, flush=True)
        zeile = sys.stdin.readline()
        if zeile == "":
            raise EOFError
        zeile = zeile.strip()
        if zeile.isdigit() and 1 <= int(zeile) <= len(treffer):
            return treffer[int(zeile) - 1]
        print(f"Bitte eine Zahl von 1 bis {len(treffer)} eingeben.", file=sys.stderr)


def _detail_text(detail: dict) -> str:
    zeilen = [detail["titel"]]
    kopf = [detail.get("dienststelle") or "", ""]
    kopf[1] = (
        f"{parse.datum_text(detail.get('datum', ''))} {detail.get('zeit', '')}".strip()
        + f" · {detail['kennung']}"
    )
    zeilen.append(" · ".join(teil for teil in kopf if teil))
    if detail.get("volltext"):
        zeilen.append(detail["volltext"])
    return "\n".join(zeilen)


def cmd_zeige(args, out: Ausgabe) -> int:
    """Volltext einer Meldung über Kennung oder Titelstichwort."""
    argument = (args.argument or "").strip()
    if not argument:
        raise UsageFehler(
            "Keine Kennung und kein Titelstichwort angegeben.",
            "blaulicht zeige <KENNUNG|TITELSTICHWORT> ausführen",
        )
    client = Client()
    kennung = _kennung_zerlegen(argument)
    if kennung is not None:
        detail = _direkt_detail(client, *kennung)
    else:
        limit = _limit(args.limit)
        ort = _ort_holen(args.ort)
        meldungen = _lade_liste(client, parse.ort_pfad(ort))[:limit]
        stichwort = argument.casefold()
        treffer = [m for m in meldungen if stichwort in m["titel"].casefold()]
        if not treffer:
            raise LaufzeitFehler(
                f"Meldung {argument} nicht gefunden.",
                f"blaulicht neu {ort} oder blaulicht suche {argument} ausführen",
            )
        if len(treffer) > 1 and not args.erster:
            meldung = _waehle(treffer, argument)
        else:
            meldung = treffer[0]
        teile = meldung["kennung"].split("/")
        detail = _detail_laden(client, teile[0], teile[1])

    out.zeige(detail, _detail_text(detail))
    return 0


def _direkt_detail(client: Client, dienststelle: str, meldung: str) -> dict:
    try:
        return _detail_laden(client, dienststelle, meldung)
    except HttpFehler as fehler:
        if fehler.status == 404:
            raise LaufzeitFehler(
                f"Meldung {dienststelle}/{meldung} nicht gefunden.",
                f"blaulicht neu <Ort> oder blaulicht suche <Stichwort> ausführen",
            ) from None
        raise


def _dienststelle_aufloesen(name: str, eintraege: list[dict]) -> list[dict]:
    ziel = _namen_normieren(name)
    exakt = [e for e in eintraege if _namen_normieren(e["name"]) == ziel]
    if exakt:
        return exakt[:1]
    bewertet: list[tuple[float, dict]] = []
    for eintrag in eintraege:
        quote = SequenceMatcher(None, ziel, _namen_normieren(eintrag["name"])).ratio()
        if quote >= 0.6:
            bewertet.append((quote, eintrag))
    if not bewertet:
        return []
    bewertet.sort(key=lambda paar: paar[0], reverse=True)
    beste = bewertet[0][0]
    return [eintrag for quote, eintrag in bewertet if quote >= beste - 0.05]


def _waehle_dienststelle(treffer: list[dict], name: str) -> dict:
    if not _ist_tty(sys.stdin):
        raise MehrdeutigFehler(
            f"{len(treffer)} Dienststellen passen zu {name}.",
            treffer,
            "den Namen genauer angeben",
        )
    for nummer, eintrag in enumerate(treffer, 1):
        print(f"{nummer}) {eintrag['name']}", file=sys.stderr)
    while True:
        print("Nummer wählen: ", end="", file=sys.stderr, flush=True)
        zeile = sys.stdin.readline()
        if zeile == "":
            raise EOFError
        zeile = zeile.strip()
        if zeile.isdigit() and 1 <= int(zeile) <= len(treffer):
            return treffer[int(zeile) - 1]
        print(f"Bitte eine Zahl von 1 bis {len(treffer)} eingeben.", file=sys.stderr)


def cmd_dienststelle(args, out: Ausgabe) -> int:
    """Dienststelle per Name auflösen und ihre neuesten Meldungen zeigen."""
    name = (args.name or "").strip()
    if not name:
        raise UsageFehler(
            "Kein Dienststellenname angegeben.",
            'blaulicht dienststelle "Polizeipräsidium Heilbronn" ausführen',
        )
    limit = _limit(args.limit)
    client = Client()
    verzeichnis = _lade_liste_html(client, "/blaulicht/dienststellen")
    eintraege = parse.parse_dienststellen(verzeichnis)
    if not eintraege:
        raise NetzFehler(
            "Das Dienststellenverzeichnis konnte nicht gelesen werden.",
            "später erneut versuchen oder blaulicht neu <Ort> ausführen",
        )
    treffer = _dienststelle_aufloesen(name, eintraege)
    if not treffer:
        raise LaufzeitFehler(
            f"Dienststelle {name} nicht gefunden.",
            f"blaulicht dienststelle <Name> oder blaulicht neu <Ort> ausführen",
        )
    gewaehlt = treffer[0] if len(treffer) == 1 else _waehle_dienststelle(treffer, name)

    meldungen = _lade_liste(
        client, f"/blaulicht/nr/{gewaehlt['id']}", dienststelle=gewaehlt["name"]
    )[:limit]
    objekt = {
        "dienststelle": {"name": gewaehlt["name"], "id": gewaehlt["id"]},
        "anzahl": len(meldungen),
        "meldungen": meldungen,
    }
    text = f"{gewaehlt['name']} (Dienststelle {gewaehlt['id']})\nNeueste Meldungen:"
    if meldungen:
        text += "\n" + _liste_text(meldungen)
    else:
        text += "\nKeine Meldungen gefunden."
    out.zeige(objekt, text)
    return 0


def _state_speichern(zustand: dict) -> None:
    try:
        pfade.speichere_state(zustand)
    except OSError as exc:
        raise LaufzeitFehler(
            f"Watch-Stand konnte nicht gespeichert werden: {exc}",
            "Schreibrechte für das State-Verzeichnis prüfen",
        ) from None


def cmd_watch(args, out: Ausgabe) -> int:
    """Nur Meldungen, die seit dem letzten Aufruf neu sind."""
    ort = _ort_holen(args.ort)
    limit = _limit(args.limit)
    client = Client()
    meldungen = _lade_liste(client, parse.ort_pfad(ort))
    kennungen = [m["kennung"] for m in meldungen]

    zustand = pfade.lade_state()
    alt = zustand.get(ort)
    if not isinstance(alt, list):
        zustand[ort] = kennungen
        _state_speichern(zustand)
        objekt = {
            "ort": ort,
            "ausgangsstand": True,
            "anzahl": 0,
            "gespeichert": len(kennungen),
            "neu": [],
        }
        text = (
            f"Ausgangsstand gespeichert: {len(kennungen)} Meldungen für {ort}.\n"
            "Beim nächsten Aufruf werden nur neue Meldungen angezeigt."
        )
        out.zeige(objekt, text)
        return 0

    bekannt = set(alt)
    neue = [m for m in meldungen if m["kennung"] not in bekannt]
    zustand[ort] = list(dict.fromkeys([*alt, *kennungen]))
    _state_speichern(zustand)

    anzeige = neue[:limit]
    objekt = {
        "ort": ort,
        "ausgangsstand": False,
        "anzahl": len(anzeige),
        "gespeichert": len(zustand[ort]),
        "neu": anzeige,
    }
    if not anzeige:
        out.zeige(objekt, "Keine neuen Meldungen seit dem letzten Aufruf.")
        return 0
    text = (
        f"{len(anzeige)} neue Meldungen für {ort} seit dem letzten Aufruf:\n"
        f"{_liste_text(anzeige)}"
    )
    out.zeige(objekt, text)
    return 0


def _config_objekt(daten: dict) -> dict:
    return {
        "config_pfad": str(pfade.config_pfad()),
        "state_pfad": str(pfade.state_pfad()),
        "cache_pfad": str(pfade.cache_pfad()),
        "ort": str(daten.get("ort") or ""),
    }


def cmd_config(args, out: Ausgabe) -> int:
    """Standard-Ort speichern oder Pfade und Einstellungen anzeigen."""
    schluessel = args.schluessel
    wert = args.wert
    daten = pfade.lade_config()
    hinweis = ""

    if schluessel is not None:
        if schluessel != "ort":
            raise UsageFehler(
                f"Unbekannter Schlüssel: {schluessel}. Erlaubt ist nur: ort.",
                "blaulicht config ort <ORT> ausführen",
            )
        if wert is not None:
            ort = wert.strip()
            if not ort:
                raise UsageFehler(
                    "Der Ort darf nicht leer sein.",
                    "blaulicht config ort <ORT> ausführen",
                )
            daten["ort"] = ort
            try:
                pfade.speichere_config(daten)
            except OSError as exc:
                raise LaufzeitFehler(
                    f"Config konnte nicht gespeichert werden: {exc}",
                    "Schreibrechte für das Config-Verzeichnis prüfen",
                ) from None
            hinweis = f"Standard-Ort gespeichert: {ort}."

    objekt = _config_objekt(daten)
    ort_anzeige = objekt["ort"] or "(nicht gesetzt)"
    text = (
        f"{hinweis + chr(10) if hinweis else ''}"
        f"Config: {objekt['config_pfad']}\n"
        f"State:  {objekt['state_pfad']}\n"
        f"Cache:  {objekt['cache_pfad']}\n"
        f"Ort:    {ort_anzeige}"
    )
    out.zeige(objekt, text)
    return 0


# --------------------------------------------------------------------- Parser


def _json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Ausgabe als ein JSON-Objekt auf stdout",
    )


def _bau_parser() -> argparse.ArgumentParser:
    parser = BefehlsParser(
        prog="blaulicht",
        description="Blaulicht-Pressemeldungen von presseportal.de im Terminal.",
        epilog="Beispiel: blaulicht neu Heilbronn",
    )
    parser.add_argument(
        "--version", action="version", version=f"blaulicht {__version__}"
    )
    parser.add_argument(
        "--json", action="store_true", help="Ausgabe als ein JSON-Objekt auf stdout"
    )
    unter = parser.add_subparsers(dest="befehl")

    neu = unter.add_parser(
        "neu", help="Neueste Blaulicht-Meldungen eines Ortes oder Landkreises"
    )
    neu.add_argument("ort", nargs="?", help="Ort, z. B. Heilbronn")
    neu.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="höchstens N Meldungen (Standard 10)",
    )
    _json_flag(neu)
    neu.set_defaults(funktion=cmd_neu)

    suche = unter.add_parser(
        "suche", help="Stichwortsuche in Titel, Teaser und optional Volltext"
    )
    suche.add_argument("stichwort", metavar="STICHWORT", help="Suchbegriff")
    ziel = suche.add_mutually_exclusive_group()
    ziel.add_argument("--ort", help="Ort oder Landkreis, z. B. Heilbronn")
    ziel.add_argument("--bundesland", metavar="LAND", help="z. B. Baden-Württemberg")
    suche.add_argument(
        "--seit", metavar="JJJJ-MM-TT", help="nur Meldungen ab diesem Tag"
    )
    suche.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="höchstens N Treffer (Standard 10)",
    )
    suche.add_argument(
        "--volltext", action="store_true", help="auch im Volltext der Meldungen suchen"
    )
    _json_flag(suche)
    suche.set_defaults(funktion=cmd_suche)

    zeige = unter.add_parser(
        "zeige", help="Volltext einer Meldung über Kennung oder Titelstichwort"
    )
    zeige.add_argument(
        "argument",
        metavar="KENNUNG|TITELSTICHWORT",
        help="z. B. 110971/6397111 oder Unfall",
    )
    zeige.add_argument("--ort", help="Ort für die Titelsuche, z. B. Heilbronn")
    zeige.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="Suchfenster für das Titelstichwort (Standard 10)",
    )
    zeige.add_argument(
        "--erster", action="store_true", help="bei mehreren Treffern den ersten nehmen"
    )
    _json_flag(zeige)
    zeige.set_defaults(funktion=cmd_zeige)

    dienststelle = unter.add_parser(
        "dienststelle", help="Dienststelle per Name auflösen und Meldungen zeigen"
    )
    dienststelle.add_argument(
        "name", metavar="NAME", help='z. B. "Polizeipräsidium Heilbronn"'
    )
    dienststelle.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="höchstens N Meldungen (Standard 10)",
    )
    _json_flag(dienststelle)
    dienststelle.set_defaults(funktion=cmd_dienststelle)

    watch = unter.add_parser(
        "watch", help="Nur Meldungen, die seit dem letzten Aufruf neu sind"
    )
    watch.add_argument("ort", nargs="?", help="Ort, z. B. Heilbronn")
    watch.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="höchstens N neue Meldungen (Standard 10)",
    )
    _json_flag(watch)
    watch.set_defaults(funktion=cmd_watch)

    config = unter.add_parser(
        "config", help="Standard-Ort speichern oder Pfade und Einstellungen anzeigen"
    )
    config.add_argument(
        "schluessel", nargs="?", help="Einstellung, derzeit nur: ort"
    )
    config.add_argument("wert", nargs="?", help="neuer Wert, z. B. Heilbronn")
    _json_flag(config)
    config.set_defaults(funktion=cmd_config)

    return parser


def main(argv: list[str] | None = None) -> int:
    roh = list(sys.argv[1:] if argv is None else argv)
    json_gefordert = "--json" in roh
    json_auto = not _ist_tty(sys.stdout)
    parser = _bau_parser()

    try:
        args = parser.parse_args(roh)
    except SystemExit as raus:
        return 0 if raus.code in (None, 0) else int(raus.code)
    except BlaulichtFehler as fehler:
        return _fehler_ausgeben(fehler, json_gefordert or json_auto)

    funktion = getattr(args, "funktion", None)
    if funktion is None:
        parser.print_help()
        return 0

    out = Ausgabe(json_gefordert or json_auto)
    try:
        return int(funktion(args, out) or 0)
    except BlaulichtFehler as fehler:
        return _fehler_ausgeben(fehler, out.json)
    except KeyboardInterrupt:
        print("Abgebrochen.", file=sys.stderr)
        return 130
    except EOFError:
        print("Eingabe beendet.", file=sys.stderr)
        return 2
    except BrokenPipeError:
        return 0
    except Exception as exc:  # noqa: BLE001 - Tracebacks sind nicht erlaubt
        return _fehler_ausgeben(
            BlaulichtFehler(
                f"{type(exc).__name__}: {exc}",
                "blaulicht --help prüfen und den Befehl erneut ausführen",
                exit_code=1,
            ),
            out.json,
        )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
