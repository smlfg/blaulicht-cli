"""Fehlervertrag der Kommandozeile: Exit-Codes, JSON, keine Tracebacks."""

from __future__ import annotations

import json
import socket
import stat

from blaulicht import cli, pfade


def _json(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


def test_help_und_version_exit_null(capsys):
    assert cli.main(["--help"]) == 0
    assert "dienststelle" in capsys.readouterr().out

    assert cli.main(["--version"]) == 0
    assert "blaulicht" in capsys.readouterr().out.lower()


def test_fehlender_ort_ist_usage(fake_server, capsys):
    code = cli.main(["neu", "--json"])

    assert code == 2
    data = _json(capsys)
    assert data["exit"] == 2
    assert data["naechster_schritt"]


def test_ungueltiges_datum_ist_usage(fake_server, capsys):
    code = cli.main(["suche", "Unfall", "--ort", "Heilbronn", "--seit", "2026-13-01", "--json"])

    assert code == 2
    assert _json(capsys)["exit"] == 2


def test_ungueltiger_limit_wert_ist_usage(fake_server, capsys):
    code = cli.main(["neu", "Heilbronn", "--limit", "0", "--json"])

    assert code == 2
    assert _json(capsys)["exit"] == 2


def test_unbekannte_kennung_ist_laufzeitfehler(fake_server, capsys):
    code = cli.main(["zeige", "1/2", "--json"])

    assert code == 1
    data = _json(capsys)
    assert data["exit"] == 1
    assert "nicht gefunden" in data["fehler"]


def test_seit_folgt_folgeseiten_und_reicht_aeltere_treffer(
    fake_server_seit, monkeypatch, capsys
):
    monkeypatch.setenv("BLAULICHT_HEUTE", "2026-11-25")

    code = cli.main(
        [
            "suche",
            "Unfall",
            "--ort",
            "Heilbronn",
            "--seit",
            "2025-01-01",
            "--limit",
            "50",
            "--json",
        ]
    )

    assert code == 0
    data = _json(capsys)
    kennungen = [treffer["kennung"] for treffer in data["treffer"]]
    assert "110971/5961820" in kennungen
    assert fake_server_seit.anfragen == [
        "/blaulicht/r/Heilbronn",
        "/blaulicht/r/Heilbronn/30",
    ]
    assert "startDate=2025-01-01" in fake_server_seit.anfragen_query[0]
    assert "endDate=2026-11-25" in fake_server_seit.anfragen_query[0]


def test_config_ungueltiger_schluessel_ist_usage(umgebung, capsys):
    code = cli.main(["config", "farbe", "rot", "--json"])

    assert code == 2
    data = _json(capsys)
    assert data["exit"] == 2
    assert "ort" in data["fehler"]


def test_config_speichert_ort_mit_0600(umgebung, capsys):
    code = cli.main(["config", "ort", "Heilbronn", "--json"])

    assert code == 0
    data = _json(capsys)
    assert data["ort"] == "Heilbronn"
    assert pfade.lade_config()["ort"] == "Heilbronn"
    assert stat.S_IMODE(pfade.config_pfad().stat().st_mode) == 0o600


def test_netzfehler_ohne_traceback(monkeypatch, capsys):
    port = _freier_port()
    monkeypatch.setenv("BLAULICHT_BASE_URL", f"http://127.0.0.1:{port}")

    code = cli.main(["neu", "Heilbronn", "--json"])

    aus = capsys.readouterr()
    assert code == 3
    assert json.loads(aus.out)["exit"] == 3
    assert "Traceback" not in aus.out
    assert "Traceback" not in aus.err


def _freier_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port
