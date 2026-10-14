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
    raise NotImplementedError


def interface_values(line: str) -> list[str]:
    raise NotImplementedError


def interface_errors(values: Sequence[str]) -> list[str]:
    raise NotImplementedError


def toc_files(folder: Path) -> list[Path]:
    raise NotImplementedError
