"""Fehlerklassen mit den Exit-Codes aus INTERFACE.md."""

from __future__ import annotations


class BlaulichtFehler(Exception):
    """Grundklasse: Meldung plus nächster Schritt für den Menschen."""

    exit_code = 1

    def __init__(self, meldung: str, naechster_schritt: str = "", exit_code: int | None = None):
        super().__init__(meldung)
        self.meldung = meldung
        self.naechster_schritt = naechster_schritt
        if exit_code is not None:
            self.exit_code = exit_code


class UsageFehler(BlaulichtFehler):
    """Ungültige Argumente, fehlender Ort, Mehrdeutigkeit ohne TTY, ungültiges Datum."""

    exit_code = 2


class LaufzeitFehler(BlaulichtFehler):
    """Unbekannte Kennung/Dienststelle, Config-Schreibfehler, unerwartete Antwort."""

    exit_code = 1


class NetzFehler(BlaulichtFehler):
    """Verbindungsfehler, Timeout, HTTP-Status >= 400, unlesbares HTML."""

    exit_code = 3


class HttpFehler(NetzFehler):
    """Antwort mit HTTP-Status >= 400; der Status erlaubt gezielte Zuordnungen."""

    def __init__(self, meldung: str, naechster_schritt: str, status: int):
        super().__init__(meldung, naechster_schritt)
        self.status = int(status)


class MehrdeutigFehler(UsageFehler):
    """Mehrere Treffer ohne TTY: Liste ausgeben, Exit 2."""

    def __init__(self, meldung: str, treffer: list, naechster_schritt: str = ""):
        super().__init__(meldung, naechster_schritt)
        self.treffer = treffer
