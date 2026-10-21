"""Correctifs du serveur lus dans la liste publique des caches vérifiés de Raidbots (décision 290).

Quand l'utilisateur ne peut pas se connecter (fin de la bêta, sortie), le `DBCache.bin` vérifié le plus récent d'un
build est téléchargé en lecture seule depuis la liste que tient Raidbots (celle qu'utilise `wowsims/forever`), puis
épinglé dans le cache (`<cache>/dbcache/<build>/raidbots/`) avec sa source : adresse, date de création, empreinte,
date du téléchargement. `forever decode --hotfixes --dbcache raidbots` l'applique comme le cache du client ; la
provenance nomme Raidbots et la certitude des valeurs corrigées est au plus `probable` (copie tierce du cache du jeu) ;
le `DBCache.bin` du jeu de l'utilisateur, quand il existe, prime.

Aucune valeur de jeu ici : seulement la lecture de la liste et le téléchargement."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from forever.config import FETCH_TIMEOUT, USER_AGENT, Deps
from forever.errors import FetchFailedError, InvalidArgumentError, OfflineError
from forever.timefmt import format_utc

VERIFIED_URL = "https://www.raidbots.com/api/dbcache/verified"
SOURCE = "raidbots"
DOWNLOAD_TIMEOUT = 120.0  # secondes : un DBCache.bin pèse quelques Mo
FOLDER = "raidbots"


def raidbots_version(product: str) -> str:
    """Champ `version` de la liste de Raidbots pour un produit du CDN de Blizzard : le produit sans son préfixe
    `wow_` (`wow_classic_beta` -> `classic_beta`), `retail` pour `wow` (correspondance relevée le 2026-10-21 sur
    la bêta ; à revérifier pour le produit de la version finale)."""
    return "retail" if product == "wow" else product.removeprefix("wow_")


def latest_verified(listing: Mapping[str, Any], product: str, build: int) -> dict[str, Any]:
    """Entrée vérifiée la plus récente (date de création) du build et du produit ; InvalidArgumentError sinon."""
    wanted = raidbots_version(product)
    found = [
        e
        for e in listing.get("data") or []
        if isinstance(e, Mapping)
        and e.get("verified") is True
        and e.get("version") == wanted
        and e.get("build") == build
        and isinstance(e.get("url"), str)
    ]
    if not found:
        raise InvalidArgumentError(
            f"Aucun cache vérifié chez Raidbots pour le build {build} ({wanted}).",
            "réessayer plus tard (la liste suit les correctifs du serveur) ou se connecter au jeu",
        )
    return dict(max(found, key=lambda e: str(dict(e).get("created") or "")))


def _folder(cache_dir: Path, build: int) -> Path:
    return cache_dir / "dbcache" / str(build) / FOLDER


def _get(deps: Deps, url: str, accept: str, timeout: float) -> bytes:
    if deps.offline:
        raise OfflineError("la lecture des caches vérifiés de Raidbots")
    try:
        return deps.http_get(url, {"User-Agent": USER_AGENT, "Accept": accept}, timeout)
    except OSError as exc:
        raise FetchFailedError(f"Raidbots injoignable ({url}) : {exc}") from exc


def fetch_dbcache(deps: Deps, build: int, product: str) -> Path:
    """Télécharge (lecture seule) le `DBCache.bin` vérifié le plus récent de `build` et l'épingle avec sa source ;
    un fichier déjà épinglé pour la même adresse n'est pas retéléchargé. Rend son chemin."""
    try:
        listing = json.loads(_get(deps, VERIFIED_URL, "application/json", FETCH_TIMEOUT))
    except json.JSONDecodeError as exc:
        raise FetchFailedError(f"Liste de Raidbots illisible : {exc}") from exc
    chosen = latest_verified(listing, product, build)
    url = str(chosen["url"])
    folder = _folder(deps.cache_dir, build)
    path = folder / Path(unquote(url)).name
    if path.is_file() and (third_party_of(path) or {}).get("url") == url:
        return path
    body = _get(deps, url, "application/octet-stream", DOWNLOAD_TIMEOUT)
    folder.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_bytes(body)
    tmp.replace(path)
    meta = {
        "source": SOURCE,
        "list": VERIFIED_URL,
        "url": url,
        "version": chosen.get("version"),
        "build": build,
        "created": chosen.get("created"),
        "entries": chosen.get("entries"),
        "push_ids": chosen.get("pushIds"),
        "sha256": hashlib.sha256(body).hexdigest(),
        "fetched_at": format_utc(deps.now()),
    }
    _meta_path(path).write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def _meta_path(path: Path) -> Path:
    return path.with_name(path.name + ".json")


def third_party_of(path: Path) -> dict[str, Any] | None:
    """Source épinglée d'un `DBCache.bin` venu de Raidbots (fichier voisin), None pour le cache du client."""
    meta = _meta_path(path)
    if not meta.is_file():
        return None
    doc = json.loads(meta.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) and doc.get("source") == SOURCE else None


def cached_dbcache(cache_dir: Path, build: int) -> Path | None:
    """Dernier `DBCache.bin` de Raidbots épinglé pour `build` (date de création la plus récente), sans réseau."""
    folder = _folder(cache_dir, build)
    if not folder.is_dir():
        return None
    pinned = [(str((third_party_of(p) or {}).get("created") or ""), p) for p in folder.glob("*.bin")]
    pinned = [(c, p) for c, p in pinned if c]
    return max(pinned)[1] if pinned else None
