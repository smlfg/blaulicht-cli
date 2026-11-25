"""Config-, Zustands- und Cache-Pfade mit den Rechten aus INTERFACE.md."""

from __future__ import annotations

import json
import os
from pathlib import Path

VERZEICHNIS = "blaulicht-cli"


def _basis(env_name: str, standard: str) -> Path:
    roh = os.environ.get(env_name, "").strip()
    return Path(roh) if roh else Path(standard)


def config_pfad() -> Path:
    return _basis("XDG_CONFIG_HOME", str(Path.home() / ".config")) / VERZEICHNIS / "config.json"


def state_pfad() -> Path:
    return (
        _basis("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))
        / VERZEICHNIS
        / "watch.json"
    )


def cache_pfad() -> Path:
    from .client import cache_verzeichnis

    return cache_verzeichnis()


def _lese(pfad: Path) -> dict:
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return daten if isinstance(daten, dict) else {}


def _schreibe(pfad: Path, daten: dict) -> None:
    eltern = pfad.parent
    eltern.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(eltern, 0o700)
    except OSError:
        pass
    roh = json.dumps(daten, ensure_ascii=False, indent=2) + "\n"
    handle = os.open(pfad, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(handle, 0o600)
    with os.fdopen(handle, "w", encoding="utf-8") as datei:
        datei.write(roh)


def lade_config() -> dict:
    return _lese(config_pfad())


def speichere_config(daten: dict) -> Path:
    pfad = config_pfad()
    _schreibe(pfad, daten)
    return pfad


def lade_state() -> dict:
    return _lese(state_pfad())


def speichere_state(daten: dict) -> Path:
    pfad = state_pfad()
    _schreibe(pfad, daten)
    return pfad
