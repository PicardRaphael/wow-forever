"""Installations du client sur ce poste et choix de celle que forever lit (LN1, décision 271).

Une **racine** est un dossier « World of Warcraft » (fixe ou déclarée, jamais un balayage du disque) ; une
**installation** est un sous-dossier `_…_` de la racine qui contient un exécutable `Wow*.exe`. Son produit est lu
dans `<dossier>/.flavor.info` ; à défaut, dans la ligne de `<racine>/.build.info` dont le produit public connu a ce
dossier, sinon dans la ligne unique du fichier. Il n'est **jamais déduit du nom du dossier** : le produit de la
version finale n'est pas annoncé, et un second produit Forever (stress test) existe déjà.

Rôles : `beta` (produit des données installées, `sources.json`), `final` (produit adopté par `forever wow adopt`,
inscrit au journal des versions), `other` (produit public connu qui n'est pas Forever), sinon `unknown`.

Lecture sur disque seulement, jamais par le réseau ; `product.db` de Battle.net n'est jamais lu."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BUILD_INFO = ".build.info"
FLAVOR_INFO = ".flavor.info"

ROLE_BETA = "beta"
ROLE_FINAL = "final"
ROLE_OTHER = "other"
ROLE_UNKNOWN = "unknown"

# Racines usuelles cherchées sur chaque disque fixe, dans cet ordre.
ROOT_SUFFIXES: tuple[Path, ...] = (
    Path("Program Files (x86)") / "World of Warcraft",
    Path("Program Files") / "World of Warcraft",
    Path("World of Warcraft"),
    Path("Games") / "World of Warcraft",
)

# Produits publics connus qui ne sont pas Forever, avec leur dossier quand il est connu (None sinon). Sources :
# warcraft.wiki.gg `Template:LatestPatchInfo` et BlizzTrack, relevés le 2026-10-14 (étude de `tasks/LN1-plan.md`).
# Le produit de la bêta de Forever n'y est pas (il vient de `sources.json`) ; celui de la version finale non plus
# (il est adopté, jamais écrit).
NOT_FOREVER_PRODUCTS: Mapping[str, str | None] = {
    "wow": "_retail_",
    "wowt": "_ptr_",
    "wowxptr": "_xptr_",
    "wow_beta": "_beta_",
    "wow_classic": "_classic_",
    "wow_classic_ptr": "_classic_ptr_",
    "wow_classic_era": "_classic_era_",
    "wow_classic_era_ptr": "_classic_era_ptr_",
    "wow_anniversary": None,
    "wow_classic_titan": None,
}


@dataclass(frozen=True)
class Install:
    """Une installation du client : dossier, produit (None : illisible), version, exécutable et rôle."""

    root: Path
    folder: Path
    product: str | None
    version: str | None
    executable: str | None
    product_source: str
    role: str = ROLE_UNKNOWN

    def as_dict(self) -> dict[str, Any]:
        raise NotImplementedError


@dataclass(frozen=True)
class Choice:
    """Installation lue par forever et la raison du choix (en français)."""

    folder: Path | None
    reason: str
    install: Install | None = None


def parse_build_info(text: str) -> list[dict[str, str]]:
    """Lignes d'un fichier BPSV (`.build.info`, `.flavor.info`), par nom de colonne."""
    raise NotImplementedError


def read_flavor(folder: Path) -> str | None:
    """Produit lu dans `<dossier>/.flavor.info` (None s'il est absent ou illisible)."""
    raise NotImplementedError


def fixed_drives() -> list[Path]:
    """Disques fixes de ce poste (Windows) ; liste vide ailleurs."""
    raise NotImplementedError


def no_drives() -> list[Path]:
    """Aucun disque : défaut des dépendances construites à la main (tests)."""
    return []


def roots(environ: Mapping[str, str], drives: Iterable[Path]) -> list[Path]:
    """Racines à examiner, sans doublon (chemins comparés sans casse ni barre finale)."""
    raise NotImplementedError


def discover(candidates: Iterable[Path]) -> list[Install]:
    """Installations trouvées sous les racines (rôle encore inconnu)."""
    raise NotImplementedError


def beta_product(data_dir: Path) -> str | None:
    """Produit de la version de données installée (`sources.json`), celui de la bêta aujourd'hui."""
    raise NotImplementedError


def assign_roles(
    installs: Sequence[Install], *, beta: str | None, adopted: Mapping[str, Mapping[str, Any]]
) -> list[Install]:
    """Rôle de chaque installation."""
    raise NotImplementedError


def choose(installs: Sequence[Install], *, option: Path | None = None, environ: Mapping[str, str]) -> Choice:
    """Installation lue : `--wow-dir`, puis `FOREVER_WOW_FORCE`, puis la version finale adoptée la plus récente, puis
    la bêta, puis `FOREVER_WOW_DIR` s'il existe."""
    raise NotImplementedError


def survey(
    environ: Mapping[str, str],
    *,
    drives: Callable[[], Sequence[Path]],
    cache_dir: Path,
    data_dir: Path,
    option: Path | None = None,
) -> tuple[Choice, list[Install]]:
    """Découverte, rôles et choix en un appel."""
    raise NotImplementedError


def same_folder(a: Path, b: Path) -> bool:
    """Même dossier, sans tenir compte de la casse ni d'une barre finale."""
    raise NotImplementedError
