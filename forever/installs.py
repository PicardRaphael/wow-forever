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

import json
import os
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
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

SOURCE_FLAVOR = ".flavor.info"
SOURCE_KNOWN_FOLDER = ".build.info (dossier d'un produit public connu)"
SOURCE_SINGLE_LINE = ".build.info (ligne unique)"
SOURCE_UNREADABLE = "illisible (ni .flavor.info, ni ligne unique dans .build.info)"

_DRIVE_FIXED = 3  # GetDriveTypeW : disque fixe


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
        return {
            "root": str(self.root),
            "folder": str(self.folder),
            "product": self.product,
            "version": self.version,
            "executable": self.executable,
            "product_source": self.product_source,
            "role": self.role,
        }


@dataclass(frozen=True)
class Choice:
    """Installation lue par forever et la raison du choix (en français)."""

    folder: Path | None
    reason: str
    install: Install | None = None

    def as_dict(self) -> dict[str, Any]:
        found = self.install
        return {
            "folder": str(self.folder) if self.folder is not None else None,
            "role": found.role if found is not None else None,
            "product": found.product if found is not None else None,
            "version": found.version if found is not None else None,
            "reason": self.reason,
        }


def parse_build_info(text: str) -> list[dict[str, str]]:
    """Lignes d'un fichier BPSV (`.build.info`, `.flavor.info`), par nom de colonne : en-tête `Nom!TYPE:taille`,
    lignes commençant par `#` ignorées."""
    lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not lines:
        return []
    columns = [field.split("!", 1)[0].strip() for field in lines[0].split("|")]
    rows = []
    for line in lines[1:]:
        values = line.split("|")
        if len(values) != len(columns):
            continue
        rows.append({name: value.strip() for name, value in zip(columns, values, strict=True)})
    return rows


def _read_rows(path: Path) -> list[dict[str, str]]:
    try:
        return parse_build_info(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return []


def read_flavor(folder: Path) -> str | None:
    """Produit lu dans `<dossier>/.flavor.info` (None s'il est absent ou illisible)."""
    for row in _read_rows(folder / FLAVOR_INFO):
        product = row.get("Product Flavor", "")
        if product:
            return product
    return None


def product_of(folder: Path) -> tuple[str | None, str | None, str]:
    """(produit, version, source du produit) d'un dossier d'installation ; produit None s'il est illisible."""
    rows = [r for r in _read_rows(folder.parent / BUILD_INFO) if r.get("Product")]
    flavor = read_flavor(folder)
    if flavor is not None:
        row = next((r for r in rows if r["Product"] == flavor), None)
        return flavor, (row.get("Version") or None) if row else None, SOURCE_FLAVOR
    known = [r for r in rows if NOT_FOREVER_PRODUCTS.get(r["Product"]) == folder.name]
    if len(known) == 1:
        return known[0]["Product"], known[0].get("Version") or None, SOURCE_KNOWN_FOLDER
    if len(rows) == 1:
        return rows[0]["Product"], rows[0].get("Version") or None, SOURCE_SINGLE_LINE
    return None, None, SOURCE_UNREADABLE


def fixed_drives() -> list[Path]:
    """Disques fixes de ce poste (Windows) ; liste vide ailleurs."""
    if sys.platform != "win32":
        return []
    import ctypes

    kernel32 = ctypes.windll.kernel32
    found = []
    for drive in os.listdrives():
        if kernel32.GetDriveTypeW(drive) == _DRIVE_FIXED:
            found.append(Path(drive))
    return found


def no_drives() -> list[Path]:
    """Aucun disque : défaut des dépendances construites à la main (tests)."""
    return []


def _key(path: Path) -> str:
    """Clé de comparaison d'un chemin : sans casse sous Windows, sans barre finale, absolue."""
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))


def same_folder(a: Path, b: Path) -> bool:
    """Même dossier, sans tenir compte de la casse (Windows) ni d'une barre finale."""
    return _key(a) == _key(b)


def roots(environ: Mapping[str, str], drives: Iterable[Path]) -> list[Path]:
    """Racines à examiner, sans doublon : parents de `FOREVER_WOW_DIR` et `FOREVER_WOW_FORCE`, `FOREVER_WOW_ROOTS`
    (séparées par `;`), puis les racines usuelles de chaque disque fixe."""
    found: list[Path] = []
    for name in ("FOREVER_WOW_DIR", "FOREVER_WOW_FORCE"):
        value = environ.get(name, "").strip()
        if value:
            found.append(Path(os.path.normpath(value)).parent)
    found += [Path(os.path.normpath(p.strip())) for p in environ.get("FOREVER_WOW_ROOTS", "").split(";") if p.strip()]
    for drive in drives:
        found += [drive / suffix for suffix in ROOT_SUFFIXES]
    unique: list[Path] = []
    seen: set[str] = set()
    for root in found:
        if _key(root) not in seen:
            seen.add(_key(root))
            unique.append(root)
    return unique


def _executable(folder: Path) -> str | None:
    try:
        names = sorted(p.name for p in folder.iterdir() if p.is_file())
    except OSError:
        return None
    for name in names:
        low = name.lower()
        if low.startswith("wow") and low.endswith(".exe") and "_loader" not in low:
            return name
    return None


def discover(candidates: Iterable[Path]) -> list[Install]:
    """Installations trouvées sous les racines (rôle encore inconnu), chacune une seule fois."""
    found: list[Install] = []
    seen: set[str] = set()
    for root in candidates:
        try:
            folders = sorted(p for p in root.iterdir() if p.is_dir())
        except OSError:
            continue
        for folder in folders:
            name = folder.name
            if len(name) < 3 or not (name.startswith("_") and name.endswith("_")) or _key(folder) in seen:
                continue
            exe = _executable(folder)
            if exe is None:
                continue
            seen.add(_key(folder))
            product, version, source = product_of(folder)
            found.append(Install(root, folder, product, version, exe, source))
    return found


def beta_product(data_dir: Path) -> str | None:
    """Produit de la version de données installée (`sources.json`), celui de la bêta aujourd'hui."""
    try:
        version = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))["game_version"]
        product = json.loads((data_dir / str(version) / "sources.json").read_text(encoding="utf-8"))["product"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return product if isinstance(product, str) else None


def assign_roles(
    installs: Sequence[Install], *, beta: str | None, adopted: Mapping[str, Mapping[str, Any]]
) -> list[Install]:
    """Rôle de chaque installation : produit adopté, produit des données, produit public connu, sinon inconnu."""

    def role(i: Install) -> str:
        if i.product is None:
            return ROLE_UNKNOWN
        if i.product in adopted:
            return ROLE_FINAL
        if i.product == beta:
            return ROLE_BETA
        if i.product in NOT_FOREVER_PRODUCTS:
            return ROLE_OTHER
        return ROLE_UNKNOWN

    return [replace(i, role=role(i)) for i in installs]


def _version_key(version: str | None) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in (version or "").split("."))
    except ValueError:
        return ()


def _matching(installs: Sequence[Install], folder: Path) -> Install | None:
    return next((i for i in installs if same_folder(i.folder, folder)), None)


def choose(installs: Sequence[Install], *, option: Path | None = None, environ: Mapping[str, str]) -> Choice:
    """Installation lue : `--wow-dir`, puis `FOREVER_WOW_FORCE`, puis la version finale adoptée la plus récente, puis
    la bêta, puis `FOREVER_WOW_DIR` s'il existe."""
    if option is not None:
        return Choice(option, "dossier donné par --wow-dir", _matching(installs, option))
    forced = environ.get("FOREVER_WOW_FORCE", "").strip()
    if forced:
        return Choice(Path(forced), "forcée par FOREVER_WOW_FORCE", _matching(installs, Path(forced)))
    finals = sorted((i for i in installs if i.role == ROLE_FINAL), key=lambda i: _version_key(i.version))
    if finals:
        return Choice(finals[-1].folder, "version finale adoptée", finals[-1])
    beta = next((i for i in installs if i.role == ROLE_BETA), None)
    if beta is not None:
        return Choice(beta.folder, "bêta : aucune version finale adoptée", beta)
    configured = environ.get("FOREVER_WOW_DIR", "").strip()
    if configured and Path(configured).is_dir():
        folder = Path(configured)
        return Choice(folder, "FOREVER_WOW_DIR (aucune installation reconnue)", _matching(installs, folder))
    return Choice(None, "aucune installation trouvée")


def survey(
    environ: Mapping[str, str],
    *,
    drives: Callable[[], Sequence[Path]],
    cache_dir: Path,
    data_dir: Path,
    option: Path | None = None,
) -> tuple[Choice, list[Install]]:
    """Découverte, rôles et choix en un appel."""
    from forever.errors import ForeverError
    from forever.pipeline.client_builds import adopted_products

    found = discover([*roots(environ, drives()), *([option.parent] if option is not None else [])])
    try:
        adopted = adopted_products(cache_dir)
    except ForeverError:
        adopted = {}  # journal des versions illisible : aucune adoption lue (forever doctor le signale), rien n'échoue
    found = assign_roles(found, beta=beta_product(data_dir), adopted=adopted)
    return choose(found, option=option, environ=environ), found
