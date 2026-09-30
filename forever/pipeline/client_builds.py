"""Journal des versions du client installées sur ce poste (T08a, décision 135).

`.build.info` ne porte que la version **courante** du client, et il est réécrit à chaque mise à jour, tout comme
l'exécutable : l'instant d'un changement de version est perdu s'il n'est pas relevé. Ce journal, en ajout seulement,
garde pour chaque build vu sa date d'installation.

Il sert à attribuer une mesure à la version du client qui l'a produite : l'entête d'un journal de combat
(`COMBAT_LOG_VERSION … BUILD_VERSION 1.60.1`) est tronquée, sans numéro de build, et ne distingue pas deux versions.
L'attribution se fait donc par l'instant, et **par session** : un `WoWCombatLog-*.txt` peut chevaucher une mise à
jour.

C'est un état de l'outil, pas une donnée du jeu : il vit dans le cache, jamais dans `forever/data/`. Lecture sur
disque seulement, jamais par le réseau."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NamedTuple

from forever.errors import DataSchemaError
from forever.timefmt import format_utc

JOURNAL_NAME = "client_builds.json"
BUILD_INFO = ".build.info"
SCHEMA_VERSION = 1


class ClientBuild(NamedTuple):
    """Une version du client et le moment où elle est apparue sur ce poste."""

    build: str
    installed_at: datetime
    product: str


def _journal_path(cache_dir: Path) -> Path:
    return cache_dir / JOURNAL_NAME


def read_build_info(wow_dir: Path) -> ClientBuild | None:
    """Version courante du client, lue dans `.build.info` à la racine de l'installation (le dossier parent de
    `_classic_beta_`), datée de la dernière écriture du fichier.

    Rend `None` si le fichier est absent ou illisible : l'absence d'un relevé n'est pas une erreur, elle rend
    seulement l'attribution incertaine."""
    path = wow_dir.parent / BUILD_INFO
    if not path.is_file():
        return None
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        columns = [field.split("!", 1)[0] for field in lines[0].split("|")]
        version_at_column = columns.index("Version")
        product_at_column = columns.index("Product")
        rows = [line.split("|") for line in lines[1:]]
        # Le fichier liste un produit par ligne (wow, wow_classic_beta…) : on garde celui du dossier lu quand il
        # s'y trouve, sinon la première ligne.
        wanted = wow_dir.name.strip("_")
        chosen = next((r for r in rows if wanted in r[product_at_column]), rows[0])
        build = chosen[version_at_column].strip()
        if not build:
            return None
    except (OSError, IndexError, ValueError, UnicodeDecodeError):
        return None
    installed_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return ClientBuild(build=build, installed_at=installed_at, product=chosen[product_at_column].strip())


def load_builds(cache_dir: Path) -> list[ClientBuild]:
    """Journal relu, trié par date d'installation croissante (liste vide s'il n'existe pas encore)."""
    path = _journal_path(cache_dir)
    if not path.is_file():
        return []
    try:
        doc: Any = json.loads(path.read_text(encoding="utf-8"))
        entries = [
            ClientBuild(
                build=str(e["build"]),
                installed_at=datetime.fromisoformat(str(e["installed_at"])),
                product=str(e.get("product", "")),
            )
            for e in doc["builds"]
        ]
    except (OSError, ValueError, KeyError, TypeError) as err:
        raise DataSchemaError(
            f"Journal des versions du client illisible ({JOURNAL_NAME}) : {err}.",
            f"supprimer {path} : il sera reconstruit au prochain relevé (les versions antérieures seront perdues)",
        ) from err
    return sorted(entries, key=lambda e: e.installed_at)


def record_build(cache_dir: Path, build: ClientBuild) -> list[ClientBuild]:
    """Ajoute `build` au journal s'il n'y est pas déjà, et rend le journal complet.

    En ajout seulement : un build déjà relevé garde sa **première** date d'installation, qui est la plus proche du
    moment de la mise à jour."""
    entries = load_builds(cache_dir) if _journal_path(cache_dir).is_file() else []
    if any(e.build == build.build for e in entries):
        return entries
    entries = sorted([*entries, build], key=lambda e: e.installed_at)
    cache_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": SCHEMA_VERSION,
        "note": (
            "Versions du client vues sur ce poste, avec la date de la mise à jour (date de .build.info). "
            "En ajout seulement : sert à attribuer une mesure à la version du client qui l'a produite (T08a)."
        ),
        "builds": [
            {"build": e.build, "installed_at": format_utc(e.installed_at), "product": e.product} for e in entries
        ],
    }
    _journal_path(cache_dir).write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    return entries


def version_at(
    builds: list[ClientBuild] | tuple[ClientBuild, ...],
    when: datetime,
    *,
    utc_offset: timedelta | None = None,
) -> str | None:
    """Version du client en vigueur à `when`, ou `None` si elle est antérieure au premier relevé.

    `when` sans fuseau est lu en heure locale : les journaux de combat datent leurs événements ainsi. `utc_offset`
    donne le décalage de cette heure locale (défaut : celui du système)."""
    moment = when
    if moment.tzinfo is None:
        offset = utc_offset if utc_offset is not None else datetime.now().astimezone().utcoffset() or timedelta()
        moment = moment.replace(tzinfo=UTC) - offset
    found = [e for e in sorted(builds, key=lambda e: e.installed_at) if e.installed_at <= moment]
    return found[-1].build if found else None


class HeldBack(NamedTuple):
    """Journal écarté d'une mesure parce qu'il vient d'une autre version du client."""

    name: str
    client_version: str | None
    reason: str


def split_by_version(
    logs: Iterable[tuple[str, datetime | None]],
    builds: list[ClientBuild] | tuple[ClientBuild, ...],
    installed: str,
    *,
    utc_offset: timedelta | None = None,
) -> tuple[list[str], list[HeldBack], list[str]]:
    """Sépare les journaux à mesurer, ceux à retenir et ceux dont la version est inconnue, d'après la version du
    client en vigueur à leur début.

    Un journal antérieur au premier relevé (ou sans aucun relevé) n'est **pas** écarté : on ne sait pas, et écarter
    serait aussi faux qu'attribuer. Il est rendu dans la troisième liste, pour que l'appelant dise l'incertitude."""
    keep: list[str] = []
    held: list[HeldBack] = []
    unknown: list[str] = []
    for name, start in logs:
        seen = version_at(builds, start, utc_offset=utc_offset) if start is not None else None
        if seen is None:
            keep.append(name)
            unknown.append(name)
            continue
        if seen == installed:
            keep.append(name)
            continue
        held.append(
            HeldBack(
                name=name,
                client_version=seen,
                reason=(
                    f"écrit sous le client {seen}, la version installée est {installed} : "
                    f"mesure en attente de l'installation de {seen}"
                ),
            )
        )
    return keep, held, unknown
