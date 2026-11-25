from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HARNESS = REPO / "tests" / "harness"
if str(HARNESS) not in sys.path:
    sys.path.insert(0, str(HARNESS))

from fake_server import FakeServer
from ux_spec import parse

SPEC = parse(REPO / "docs" / "UX.md")
HEUTE = "2026-11-25"


@pytest.fixture(scope="module", autouse=True)
def spec_is_valid():
    assert not SPEC.errors, f"docs/UX.md ist ungültig: {SPEC.errors}"


@pytest.fixture()
def server():
    with FakeServer(SPEC, REPO) as fake:
        yield fake


@pytest.fixture()
def home():
    base = REPO / "scratch" / "tmp"
    base.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="acceptance-", dir=base))
    for sub in (".config", ".local/state", ".local/share", ".cache"):
        (path / sub).mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _tool_command() -> list[str]:
    candidate = Path(sys.executable).with_name("blaulicht")
    if candidate.is_file():
        return [str(candidate)]
    return [sys.executable, "-m", "blaulicht"]


def _env(base_url: str, home: Path) -> dict[str, str]:
    env = dict(os.environ)
    parts = [str(HARNESS), str(REPO / "src"), str(REPO)]
    if env.get("PYTHONPATH"):
        parts.append(env["PYTHONPATH"])
    env.update(
        {
            "BLAULICHT_BASE_URL": base_url,
            "BLAULICHT_HEUTE": HEUTE,
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_STATE_HOME": str(home / ".local" / "state"),
            "XDG_DATA_HOME": str(home / ".local" / "share"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "TMPDIR": str(REPO / "scratch" / "tmp"),
            "PYTHONPATH": os.pathsep.join(parts),
            "PYTHONUNBUFFERED": "1",
            "TERM": "xterm",
            "LANG": "C.UTF-8",
            "ACCEPTANCE_SANDBOX": "1",
            "ACCEPTANCE_NET_LOG": str(home / "net.log"),
        }
    )
    return env


def _run(args: list[str], base_url: str, home: Path, timeout: int = 60):
    return subprocess.run(
        _tool_command() + args,
        cwd=str(REPO),
        env=_env(base_url, home),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _json(proc: subprocess.CompletedProcess) -> dict:
    assert proc.returncode == 0, (
        f"Exit {proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    text = proc.stdout.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"stdout ist kein JSON-Objekt ({exc}):\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
    assert isinstance(data, dict), f"JSON ist kein Objekt: {data!r}"
    return data


def test_installation_und_neue_meldungen(server, home):
    proc = _run(["neu", "Heilbronn", "--json"], server.base_url, home)
    data = _json(proc)

    assert data["ort"] == "Heilbronn"
    assert data["anzahl"] == 4
    meldungen = data["meldungen"]
    assert [m["kennung"] for m in meldungen] == [
        "110971/6397111",
        "110971/6396898",
        "110971/6396715",
        "110971/6396663",
    ]
    erste = meldungen[0]
    assert erste["kuerzel"] == "POL-HN"
    assert erste["datum"] == "2026-11-24"
    assert erste["zeit"] == "13:57"
    assert erste["titel"] == "POL-HN: Landkreis Heilbronn: Unfall"
    assert "Lidl" not in proc.stdout


def test_help_und_version_ohne_fehler(server, home):
    help_proc = _run(["--help"], server.base_url, home)
    assert help_proc.returncode == 0, help_proc.stderr
    assert "neu" in help_proc.stdout
    assert "dienststelle" in help_proc.stdout

    version_proc = _run(["--version"], server.base_url, home)
    assert version_proc.returncode == 0, version_proc.stderr
    assert "blaulicht" in (version_proc.stdout + version_proc.stderr).lower()


def test_suche_mit_ort_filtert_treffer(server, home):
    proc = _run(
        ["suche", "Unfall", "--ort", "Heilbronn", "--json"],
        server.base_url,
        home,
    )
    data = _json(proc)

    assert data["stichwort"] == "Unfall"
    assert data["ort"] == "Heilbronn"
    assert data["anzahl"] == 2
    kennungen = {m["kennung"] for m in data["treffer"]}
    assert kennungen == {"110971/6397111", "110971/6396715"}
    for meldung in data["treffer"]:
        assert "unfall" in (meldung["titel"] + " " + meldung.get("teaser", "")).lower()


def test_zeige_volltext_ueber_kennung(server, home):
    proc = _run(["zeige", "110971/6397111", "--json"], server.base_url, home)
    data = _json(proc)

    assert data["kennung"] == "110971/6397111"
    assert data["titel"] == "POL-HN: Landkreis Heilbronn: Unfall"
    assert data["dienststelle"] == "Polizeipräsidium Heilbronn"
    assert data["datum"] == "2026-11-24"
    assert data["zeit"] == "13:57"
    assert "A6/Neckarsulm" in data["volltext"]
    assert "82 Kinder" in data["volltext"]
    assert "example.invalid" not in data["volltext"]


def test_watch_merkt_sich_stand(server, home):
    first = _json(_run(["watch", "Heilbronn", "--json"], server.base_url, home))
    assert first["ort"] == "Heilbronn"
    assert first["ausgangsstand"] is True
    assert first["gespeichert"] == 4
    assert first["anzahl"] == 0

    state = home / ".local" / "state" / "blaulicht-cli" / "watch.json"
    assert state.is_file()
    assert stat.S_IMODE(state.stat().st_mode) == 0o600

    second = _json(_run(["watch", "Heilbronn", "--json"], server.base_url, home))
    assert second["ausgangsstand"] is False
    assert second["anzahl"] == 0
    assert second["neu"] == []


def test_dienststelle_per_name(server, home):
    proc = _run(
        ["dienststelle", "Polizeipräsidium Heilbronn", "--json"],
        server.base_url,
        home,
    )
    data = _json(proc)

    assert data["dienststelle"]["name"] == "Polizeipräsidium Heilbronn"
    assert data["dienststelle"]["id"] == "110971"
    assert data["anzahl"] == 5
    kennungen = [m["kennung"] for m in data["meldungen"]]
    assert kennungen[0] == "110971/6397111"
    assert kennungen[3] == "110971/6396688"
