"""Gemeinsame Fixture: lokaler Fake-Server und saubere XDG-Umgebung."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "ux"

ROUTES = {
    "/blaulicht/r/Heilbronn": "heilbronn_liste.html",
    "/blaulicht/pm/110971/6397111": "meldung_6397111.html",
    "/blaulicht/dienststellen": "dienststellen.html",
    "/blaulicht/nr/110971": "dienststelle_110971.html",
}
STATUS_ROUTES = {"/blaulicht/pm/110971/1": 410}

SEIT_ROUTES = {
    "/blaulicht/r/Heilbronn": "heilbronn_seit_liste.html",
    "/blaulicht/r/Heilbronn/30": "heilbronn_seit_liste2.html",
}


class LokalerServer:
    """Fake-Server auf 127.0.0.1 mit den UX-Fixtures als Antworten."""

    def __init__(self, routes: dict[str, str] | None = None):
        self.routes = dict(routes or ROUTES)
        self.anfragen: list[str] = []
        self.anfragen_query: list[str] = []
        self.basis = ""
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> "LokalerServer":
        anfragen = self.anfragen
        anfragen_query = self.anfragen_query
        routes = self.routes

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # noqa: D401 - leise
                return

            def do_GET(self):  # noqa: N802 - Name von http.server
                teile = urlsplit(self.path)
                pfad = teile.path
                anfragen.append(pfad)
                anfragen_query.append(teile.query)
                datei = routes.get(pfad)
                if datei is None and pfad in STATUS_ROUTES:
                    koerper = b"gone"
                    self.send_response(STATUS_ROUTES[pfad])
                elif datei is None:
                    koerper = b"not found"
                    self.send_response(404)
                else:
                    koerper = (FIXTURES / datei).read_bytes()
                    self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(koerper)))
                self.end_headers()
                self.wfile.write(koerper)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.basis = f"http://127.0.0.1:{self._server.server_address[1]}"
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)


@pytest.fixture(autouse=True)
def umgebung(monkeypatch, tmp_path):
    """Pfade und Env-Werte nur innerhalb des Repos; kein Zugriff auf Echt-HOME."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / ".local" / "state"))
    for name in ("BLAULICHT_BASE_URL", "BLAULICHT_ORT", "BLAULICHT_HEUTE"):
        monkeypatch.delenv(name, raising=False)
    yield tmp_path


def _starte_server(monkeypatch, routes: dict[str, str] | None = None):
    server = LokalerServer(routes).start()
    monkeypatch.setenv("BLAULICHT_BASE_URL", server.basis)
    return server


@pytest.fixture()
def fake_server(monkeypatch):
    server = _starte_server(monkeypatch)
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture()
def fake_server_seit(monkeypatch):
    server = _starte_server(monkeypatch, SEIT_ROUTES)
    try:
        yield server
    finally:
        server.stop()
