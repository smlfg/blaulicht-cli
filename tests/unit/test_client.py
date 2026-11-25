"""Client-Tests: Basis-URL, Cache, Höflichkeit, Fehlerklassen – ohne Fremdnetz."""

from __future__ import annotations

import socket
import time

import pytest

from blaulicht import client
from blaulicht.fehler import HttpFehler, NetzFehler, UsageFehler


def test_basis_url_aus_umgebung(monkeypatch):
    monkeypatch.setenv("BLAULICHT_BASE_URL", "http://127.0.0.1:9999/")
    assert client.basis_url() == "http://127.0.0.1:9999"


def test_basis_url_default():
    assert client.basis_url() == "https://www.presseportal.de"


def test_basis_url_ungueltig(monkeypatch):
    monkeypatch.setenv("BLAULICHT_BASE_URL", "presseportal.de")
    with pytest.raises(UsageFehler) as fehler:
        client.basis_url()
    assert fehler.value.exit_code == 2
    assert fehler.value.naechster_schritt


def test_user_agent_nennt_repo(fake_server):
    instanz = client.Client()
    text = instanz.get("/blaulicht/r/Heilbronn")

    assert "Offizielle News aus Heilbronn" in text
    assert fake_server.anfragen == ["/blaulicht/r/Heilbronn"]
    assert instanz.session.headers["User-Agent"].startswith("blaulicht-cli/")
    assert "github.com/smlfg/blaulicht-cli" in instanz.session.headers["User-Agent"]


def test_cache_spart_zweiten_request(fake_server, umgebung):
    instanz = client.Client()

    erste = instanz.get("/blaulicht/r/Heilbronn")
    zweite = instanz.get("/blaulicht/r/Heilbronn")

    assert erste == zweite
    assert fake_server.anfragen == ["/blaulicht/r/Heilbronn"]
    cache = umgebung / "cache" / "blaulicht-cli"
    assert cache.is_dir()
    dateien = [d for d in cache.iterdir() if d.suffix == ".html"]
    assert len(dateien) == 1
    assert dateien[0].stat().st_mode & 0o777 == 0o600
    assert cache.stat().st_mode & 0o777 == 0o700


def test_hoeflichkeit_wartet_eine_sekunde(fake_server):
    instanz = client.Client()

    instanz.get("/blaulicht/r/Heilbronn")
    start = time.monotonic()
    instanz.get("/blaulicht/dienststellen")
    dauer = time.monotonic() - start

    assert dauer >= 0.9, f"zweite Anfrage nach nur {dauer:.2f}s"


def test_http_404_wird_zu_netzfehler(fake_server):
    instanz = client.Client()

    with pytest.raises(HttpFehler) as fehler:
        instanz.get("/blaulicht/l/gibtsnicht")

    assert fehler.value.status == 404
    assert fehler.value.exit_code == 3


def test_verbindungsfehler_ohne_traceback():
    basis = client.basis_url()
    port = _freier_port()
    instanz = client.Client(basis=f"http://127.0.0.1:{port}")

    with pytest.raises(NetzFehler) as fehler:
        instanz.get("/blaulicht/r/Heilbronn")

    assert fehler.value.exit_code == 3
    assert fehler.value.naechster_schritt
    assert basis.endswith("presseportal.de")


def _freier_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port
