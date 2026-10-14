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

from forever.errors import DataSchemaError, InvalidArgumentError
from forever.installs import NOT_FOREVER_PRODUCTS, ROLE_BETA, ROLE_OTHER, Install, product_of
from forever.pipeline.builds import version_key
from forever.timefmt import format_utc

JOURNAL_NAME = "client_builds.json"
BUILD_INFO = ".build.info"
SCHEMA_VERSION = 2  # 2 : produits adoptés (LN1) ; le schéma 1 se relit


class ClientBuild(NamedTuple):
    """Une version du client et le moment où elle est apparue sur ce poste."""

    build: str
    installed_at: datetime
    product: str
    # D'où vient la date : `.build.info` pour un relevé automatique, sinon la preuve citée (rapport d'erreur du
    # client, date de publication…) quand l'entrée est écrite à la main pour une version déjà remplacée.
    source: str = ".build.info"


def _journal_path(cache_dir: Path) -> Path:
    return cache_dir / JOURNAL_NAME


def read_build_info(wow_dir: Path) -> ClientBuild | None:
    """Version courante du client, lue dans `.build.info` à la racine de l'installation (le dossier parent de
    `wow_dir`), datée de la dernière écriture du fichier.

    Le produit du dossier est lu dans son `.flavor.info` ; à défaut, la ligne d'un produit public dont le dossier est
    connu, sinon la ligne unique (`forever.installs.product_of`, LN1, décision 271). Il n'est jamais déduit du nom du
    dossier : attribuer la version d'un autre produit installé à côté est exactement l'erreur que ce journal doit
    empêcher.

    Rend `None` si le fichier est absent ou illisible : l'absence d'un relevé n'est pas une erreur, elle rend
    seulement l'attribution incertaine."""
    path = wow_dir.parent / BUILD_INFO
    if not path.is_file():
        return None
    product, version, _source = product_of(wow_dir)
    if product is None or not version:
        return None
    try:
        installed_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    except OSError:
        return None
    return ClientBuild(build=version, installed_at=installed_at, product=product)


def _read_doc(cache_dir: Path) -> dict[str, Any]:
    path = _journal_path(cache_dir)
    if not path.is_file():
        return {}
    try:
        doc: Any = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise TypeError("objet JSON attendu")
    except (OSError, ValueError, TypeError) as err:
        raise DataSchemaError(
            f"Journal des versions du client illisible ({JOURNAL_NAME}) : {err}.",
            f"supprimer {path} : il sera reconstruit au prochain relevé (les versions antérieures seront perdues)",
        ) from err
    return doc


def _write_doc(cache_dir: Path, entries: list[ClientBuild], products: dict[str, dict[str, Any]]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": SCHEMA_VERSION,
        "note": (
            "Versions du client vues sur ce poste, avec la date de la mise à jour (date de .build.info). "
            "En ajout seulement : sert à attribuer une mesure à la version du client qui l'a produite (T08a). "
            "products : produits adoptés comme version finale (forever wow adopt, LN1)."
        ),
        "builds": [
            {"build": e.build, "installed_at": format_utc(e.installed_at), "product": e.product, "source": e.source}
            for e in entries
        ],
        "products": products,
    }
    _journal_path(cache_dir).write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


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
                source=str(e.get("source", ".build.info")),
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
    """Ajoute `build` au journal s'il n'y est pas déjà (même build du même produit), et rend le journal complet.

    En ajout seulement : un build déjà relevé garde sa **première** date d'installation, qui est la plus proche du
    moment de la mise à jour. Les adoptions (`products`) sont gardées."""
    entries = load_builds(cache_dir) if _journal_path(cache_dir).is_file() else []
    if any(e.build == build.build and e.product == build.product for e in entries):
        return entries
    entries = sorted([*entries, build], key=lambda e: e.installed_at)
    _write_doc(cache_dir, entries, adopted_products(cache_dir))
    return entries


def version_at(
    builds: list[ClientBuild] | tuple[ClientBuild, ...],
    when: datetime,
    *,
    utc_offset: timedelta | None = None,
    product: str | None = None,
) -> str | None:
    """Version du client en vigueur à `when`, ou `None` si elle est antérieure au premier relevé.

    `when` sans fuseau est lu en heure locale : les journaux de combat datent leurs événements ainsi. `utc_offset`
    donne le décalage de cette heure locale (défaut : celui du système). `product` : seules les versions de ce produit
    comptent (LN1 : la bêta et la version finale peuvent cohabiter) ; None : toutes, comme avant LN1."""
    moment = when
    if moment.tzinfo is None:
        offset = utc_offset if utc_offset is not None else datetime.now().astimezone().utcoffset() or timedelta()
        moment = moment.replace(tzinfo=UTC) - offset
    ordered = sorted(builds, key=lambda e: e.installed_at)
    found = [e for e in ordered if e.installed_at <= moment and (product is None or e.product == product)]
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
    product: str | None = None,
    data_product: str | None = None,
) -> tuple[list[str], list[HeldBack], list[str]]:
    """Sépare les journaux à mesurer, ceux à retenir et ceux dont la version est inconnue, d'après la version du
    client en vigueur à leur début.

    Un journal antérieur au premier relevé (ou sans aucun relevé) n'est **pas** écarté : on ne sait pas, et écarter
    serait aussi faux qu'attribuer. Il est rendu dans la troisième liste, pour que l'appelant dise l'incertitude.

    LN1 : `product` est le produit de l'installation dont les journaux sont tirés (dossier `Logs`), `data_product`
    celui des données `installed` (`sources.json`). Un journal d'un autre produit (la bêta face aux données de la
    version finale, ou l'inverse) est toujours retenu, sauf accord explicite (`accept_earlier`)."""
    keep: list[str] = []
    held: list[HeldBack] = []
    unknown: list[str] = []
    other_product = product is not None and data_product is not None and product != data_product
    for name, start in logs:
        seen = version_at(builds, start, utc_offset=utc_offset, product=product) if start is not None else None
        if other_product:
            held.append(
                HeldBack(
                    name=name,
                    client_version=seen,
                    reason=(
                        f"écrit sous le produit {product} ({seen or 'version inconnue'}), les données {installed} "
                        f"sont celles du produit {data_product} : jamais mesuré dans ces données sans accord "
                        "(--accept-version)"
                    ),
                )
            )
            continue
        if seen is None:
            keep.append(name)
            unknown.append(name)
            continue
        if seen == installed:
            keep.append(name)
            continue
        if version_key(seen) > version_key(installed):
            why = f"mesure en attente de l'installation de {seen}"
        else:
            why = f"mesure d'une version antérieure, jamais écrite dans les données de {installed}"
        held.append(
            HeldBack(
                name=name,
                client_version=seen,
                reason=f"écrit sous le client {seen}, la version courante est {installed} : {why}",
            )
        )
    return keep, held, unknown


def current_builds(cache_dir: Path, wow_dir: Path | None) -> list[ClientBuild]:
    """Journal des versions du client, complété du relevé courant quand le dossier du client est lisible (T08a).

    Rien n'est écrit si `.build.info` est absent : l'attribution reste alors inconnue, jamais devinée."""
    if wow_dir is not None:
        found = read_build_info(wow_dir)
        if found is not None:
            return record_build(cache_dir, found)
    return load_builds(cache_dir)


class Accepted(NamedTuple):
    """Journal d'une version antérieure mesuré dans la version installée, sur accord explicite et tracé."""

    name: str
    client_version: str
    reason: str


def accept_earlier(
    held: list[HeldBack], version: str, reason: str, installed: str
) -> tuple[list[Accepted], list[HeldBack]]:
    """Journaux retenus écrits sous `version` acceptés dans la mesure de `installed` (`forever measures refresh
    --accept-version --accept-reason`, 2026-10-09) : seulement une version antérieure à la version installée, avec sa
    raison ; ValueError sinon. Rend (acceptés, toujours retenus)."""
    if not reason.strip():
        raise ValueError("raison obligatoire (--accept-reason) pour mesurer les journaux d'une version antérieure")
    if version_key(version) >= version_key(installed):
        raise ValueError(f"{version} n'est pas antérieure à la version installée {installed}")
    accepted = [Accepted(h.name, version, reason) for h in held if h.client_version == version]
    return accepted, [h for h in held if h.client_version != version]


# --- Produits adoptés (LN1, décision 271) --------------------------------------------------------------------------


def adopted_products(cache_dir: Path) -> dict[str, dict[str, Any]]:
    """Produits adoptés comme version finale (`products` du journal, schéma 2) ; vide pour un journal de schéma 1."""
    products = _read_doc(cache_dir).get("products") or {}
    if not isinstance(products, dict):
        return {}
    return {str(k): dict(v) for k, v in products.items() if isinstance(v, dict)}


def adopt_product(cache_dir: Path, install: Install, now: datetime) -> dict[str, Any]:
    """Inscrit le produit de `install` comme version finale ; refuse la bêta, un produit public connu ou un produit
    illisible (InvalidArgumentError). Jamais d'adoption automatique : seul `forever wow adopt` appelle cette fonction."""
    if install.product is None:
        raise InvalidArgumentError(
            f"Produit illisible pour {install.folder} (ni .flavor.info, ni ligne unique dans .build.info).",
            "forcer ce dossier par FOREVER_WOW_FORCE plutôt que de l'adopter",
        )
    if install.role == ROLE_BETA:
        raise InvalidArgumentError(
            f"{install.product} est le produit de la bêta (celui des données installées) : rien à adopter.",
            "adopter le dossier de la version finale, signalé « unknown » par forever wow list",
        )
    if install.role == ROLE_OTHER or install.product in NOT_FOREVER_PRODUCTS:
        raise InvalidArgumentError(
            f"{install.product} est un produit public connu qui n'est pas Forever : adoption refusée.",
            "adopter le dossier de la version finale, signalé « unknown » par forever wow list",
        )
    products = adopted_products(cache_dir)
    entry = {"role": "final", "adopted_at": format_utc(now), "folder": str(install.folder)}
    products[install.product] = entry
    _write_doc(cache_dir, load_builds(cache_dir), products)
    return {"product": install.product, **entry}


def forget_product(cache_dir: Path, product: str) -> bool:
    """Retire une adoption ; False si le produit n'était pas adopté."""
    products = adopted_products(cache_dir)
    if product not in products:
        return False
    del products[product]
    _write_doc(cache_dir, load_builds(cache_dir), products)
    return True


def version_prefix(version: str) -> str:
    """Préfixe des versions publiées d'un produit (`1.60.`), tiré d'une version lue."""
    return ".".join(version.split(".")[:2]) + "."


def final_client(cache_dir: Path, wow_dir: Path | None) -> ClientBuild | None:
    """Version du client de `wow_dir` si son produit est adopté comme version finale ; None sinon (LN1)."""
    if wow_dir is None or not wow_dir.is_dir():
        return None
    client = read_build_info(wow_dir)
    if client is None or client.product not in adopted_products(cache_dir):
        return None
    return client


def wago_product(cache_dir: Path, wow_dir: Path | None, sources: dict[str, Any] | None) -> tuple[str, str] | None:
    """(produit, préfixe) demandés à wago.tools : ceux de la version finale adoptée quand c'est l'installation lue,
    sinon ceux de `sources.json` ; None s'ils sont inconnus."""
    client = final_client(cache_dir, wow_dir)
    if client is not None:
        return client.product, version_prefix(client.build)
    product, prefix = (sources or {}).get("product"), (sources or {}).get("version_prefix")
    if isinstance(product, str) and isinstance(prefix, str):
        return product, prefix
    return None
