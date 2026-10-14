"""Fichiers `.toc` des addons et numéros d'interface admis (LN1, bloc C, décision 271).

Ordre de lecture des `.toc` d'un addon par le client : suffixe du jeu (`_Forever`, `_Camelot`), puis de la famille
(`_Mainline`), puis sans suffixe (warcraft.wiki.gg, `TOC_format`, relu le 2026-10-09). Nos `.toc` restent sans
suffixe (lus en dernier recours par tout client) tant que la version finale n'en exige pas.

`INTERFACES` : seule source des valeurs `## Interface` admises (contrôle de l'addon, `.toc` générés par le pont et
le guide). La valeur de la version finale s'y ajoute le 4 novembre après lecture en jeu
(`/dump select(4, GetBuildInfo())`, `docs/LANCEMENT.md`), jamais devinée."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

INTERFACES: tuple[str, ...] = ("16001",)  # bêta de Forever (interface de l'API du client, build 70009)
TOC_SUFFIXES: tuple[str, ...] = ("_Forever", "_Camelot", "_Mainline", "")


def interface_line(values: Sequence[str] | None = None) -> str:
    """Ligne `## Interface` d'un `.toc` généré : toutes les valeurs admises (ou `values`), séparées par des virgules."""
    return "## Interface: " + ", ".join(INTERFACES if values is None else values)


def interface_values(line: str) -> list[str]:
    """Valeurs d'une ligne `## Interface: a, b`."""
    return [v.strip() for v in line.split(":", 1)[1].split(",") if v.strip()] if ":" in line else []


def interface_errors(values: Sequence[str]) -> list[str]:
    """Valeurs non admises (toutes doivent l'être, au moins une), en texte ; liste vide si la ligne est bonne."""
    if not values:
        return [f"aucune valeur (attendu : {', '.join(INTERFACES)})"]
    return [f"{v} non admise (admises : {', '.join(INTERFACES)})" for v in values if v not in INTERFACES]


def toc_files(folder: Path) -> list[Path]:
    """`.toc` de l'addon dans l'ordre où le client les lit (suffixe du jeu, de la famille, puis sans suffixe)."""
    name = folder.name
    return [folder / f"{name}{suffix}.toc" for suffix in TOC_SUFFIXES if (folder / f"{name}{suffix}.toc").is_file()]
