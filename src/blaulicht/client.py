"""Lesender Zugriff auf presseportal.de/blaulicht.

Nur GET, höchstens ein Request pro Sekunde, Antworten fünf Minuten im Cache.
Die Basis-URL kommt aus BLAULICHT_BASE_URL (Fake-Server in Tests).
"""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from urllib.parse import urlencode

import requests

from . import __version__
from .fehler import HttpFehler, NetzFehler, UsageFehler

STANDARD_BASIS = "https://www.presseportal.de"
USER_AGENT = f"blaulicht-cli/{__version__} (+https://github.com/smlfg/blaulicht-cli)"
CACHE_TTL_SEKUNDEN = 300
MINDESTABSTAND_SEKUNDEN = 1.0
TIMEOUT_SEKUNDEN = 15.0


def basis_url() -> str:
    """Basis-URL aus der Umgebung, sonst die Standard-URL."""
    roh = os.environ.get("BLAULICHT_BASE_URL", "").strip() or STANDARD_BASIS
    if not roh.startswith(("http://", "https://")):
        raise UsageFehler(
            f"BLAULICHT_BASE_URL ist keine gültige URL: {roh!r}",
            "eine vollständige URL setzen, z. B. BLAULICHT_BASE_URL=https://www.presseportal.de",
        )
    return roh.rstrip("/")


def cache_verzeichnis() -> Path:
    """Verzeichnis für den Antwortcache (0700)."""
    basis = os.environ.get("XDG_CACHE_HOME", "").strip() or os.path.join(
        str(Path.home()), ".cache"
    )
    return Path(basis) / "blaulicht-cli"


class Client:
    """Kleiner HTTP-Client mit Cache, Zeitlimit und Höflichkeitsabstand."""

    def __init__(
        self,
        basis: str | None = None,
        cache: Path | None = None,
        timeout: float = TIMEOUT_SEKUNDEN,
    ):
        self.basis = (basis if basis is not None else basis_url()).rstrip("/")
        self.cache = Path(cache) if cache is not None else cache_verzeichnis()
        self.timeout = float(timeout)
        self.letzte_url = ""
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": USER_AGENT, "Accept-Language": "de,de-DE;q=0.9"}
        )

    def get(self, pfad: str, params: dict | None = None) -> str:
        """GET auf Basis-URL + Pfad; liefert den HTML-Text."""
        url = self.basis + pfad
        schluessel = url + ("?" + urlencode(params) if params else "")

        gecacht = self._lese_cache(schluessel)
        if gecacht is not None:
            self.letzte_url = url
            return gecacht

        self._warte()
        self._merke_anfrage()
        try:
            antwort = self.session.get(url, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            raise NetzFehler(
                f"Verbindung zu {self.basis} fehlgeschlagen: {exc}",
                "später erneut versuchen oder BLAULICHT_BASE_URL prüfen",
            ) from None

        if antwort.status_code >= 400:
            raise HttpFehler(
                f"{pfad} liefert HTTP {antwort.status_code}",
                "Pfad prüfen oder blaulicht --help ansehen",
                antwort.status_code,
            )

        if "charset" not in antwort.headers.get("Content-Type", "").lower():
            antwort.encoding = "utf-8"
        self.letzte_url = antwort.url or url
        text = antwort.text
        self._schreibe_cache(schluessel, text)
        return text

    # ------------------------------------------------------------------ Cache

    def _cache_datei(self, schluessel: str) -> Path:
        digest = hashlib.sha256(schluessel.encode("utf-8")).hexdigest()
        return self.cache / f"{digest}.html"

    def _lese_cache(self, schluessel: str) -> str | None:
        datei = self._cache_datei(schluessel)
        try:
            alter = time.time() - datei.stat().st_mtime
            if alter > CACHE_TTL_SEKUNDEN:
                return None
            return datei.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    def _schreibe_cache(self, schluessel: str, text: str) -> None:
        datei = self._cache_datei(schluessel)
        try:
            self._verzeichnis_sichern(self.cache)
            datei.write_text(text, encoding="utf-8")
            os.chmod(datei, 0o600)
        except OSError:
            pass

    # ------------------------------------------------------------- Höflichkeit

    def _warte(self) -> None:
        try:
            roh = (self.cache / ".letzte_anfrage").read_text(encoding="utf-8")
            letzte = float(roh)
        except (OSError, ValueError):
            return
        rest = MINDESTABSTAND_SEKUNDEN - (time.time() - letzte)
        if 0 < rest < MINDESTABSTAND_SEKUNDEN + 5:
            time.sleep(rest)

    def _merke_anfrage(self) -> None:
        try:
            self._verzeichnis_sichern(self.cache)
            marke = self.cache / ".letzte_anfrage"
            marke.write_text(str(time.time()), encoding="utf-8")
            os.chmod(marke, 0o600)
        except OSError:
            pass

    @staticmethod
    def _verzeichnis_sichern(pfad: Path) -> None:
        pfad.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(pfad, 0o700)
        except OSError:
            pass
