"""Repli de livraison d'un guide RestedXP, jeu fermé (RX1, bloc D, décision 266).

Un seul dossier `Interface/AddOns/ForeverRoute/` : `ForeverRoute.toc` (dépend de RXPGuides ; ligne `## Interface`
reprise du `.toc` de ForeverBridge installé, jamais devinée) et `Guide.lua` (`RXPGuides.RegisterGuide([==[…]==])`,
niveau de crochets absent du texte). Écrit seulement jeu fermé, ancien dossier sauvegardé hors des addons, réécrit en
entier ; aucun autre chemin."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from forever.errors import InvalidArgumentError

ADDON_NAME = "ForeverRoute"
BRIDGE_TOC = Path("ForeverBridge") / "ForeverBridge.toc"
INTERFACE = "## Interface:"


def bridge_interface(addons: Path) -> str:
    """Valeur `## Interface` du `.toc` de ForeverBridge installé ; InvalidArgumentError s'il manque."""
    toc = addons / BRIDGE_TOC
    if toc.is_file():
        for line in toc.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith(INTERFACE):
                return line[len(INTERFACE) :].strip()
    raise InvalidArgumentError(
        f"ForeverBridge absent ou sans ligne Interface ({toc}).", "installer ForeverBridge (forever bridge install)"
    )


def bracket_level(text: str) -> int:
    """Plus petit nombre de `=` d'une chaîne longue Lua dont la fermeture n'apparaît pas dans `text`."""
    level = 0
    while "]" + "=" * level + "]" in text:
        level += 1
    return level


def guide_lua(text: str) -> str:
    """Contenu de `Guide.lua` : enregistrement du guide auprès de RestedXP (chaîne longue), sous `pcall`."""
    eq = "=" * bracket_level(text)
    # le premier saut de ligne d'une chaîne longue est ignoré par Lua : on en met un de plus
    return (
        "-- ForeverRoute : feuille de route de forever-core (forever route deliver --addon), à importer par RestedXP.\n"
        "local guide = [" + eq + "[\n" + text + "]" + eq + "]\n"
        'local register = type(RXPGuides) == "table" and RXPGuides.RegisterGuide\n'
        'if type(register) == "function" then\n'
        "\tpcall(register, guide)\n"
        "end\n"
    )


def _toc(interface: str) -> str:
    return (
        f"{INTERFACE} {interface}\n"
        "## Title: ForeverRoute\n"
        "## Notes: Feuille de route de forever-core, livrée à RestedXP (forever route deliver --addon).\n"
        "## Author: forever-core\n"
        "## Dependencies: RXPGuides\n"
        "\n"
        "Guide.lua\n"
    )


def write_guide_addon(
    addons: Path,
    text: str,
    *,
    game_running: Callable[[], bool | None],
    backup_dir: Path,
    now: datetime,
) -> Path:
    """Écrit `ForeverRoute/` (jeu fermé seulement) ; rend le dossier écrit. InvalidArgumentError si le jeu tourne ou
    si son état est inconnu."""
    if game_running() is not False:
        raise InvalidArgumentError(
            "Le jeu est lancé (ou son état est inconnu) : ForeverRoute n'est écrit que jeu fermé.",
            "fermer le jeu puis relancer, ou livrer en jeu par ForeverBridge",
        )
    interface = bridge_interface(addons)
    folder = addons / ADDON_NAME
    if folder.exists():
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(folder), str(backup_dir / f"{ADDON_NAME}-{now.strftime('%Y%m%dT%H%M%S')}"))
    folder.mkdir(parents=True)
    (folder / "ForeverRoute.toc").write_bytes(_toc(interface).encode("utf-8"))
    (folder / "Guide.lua").write_bytes(guide_lua(text).encode("utf-8"))
    return folder
