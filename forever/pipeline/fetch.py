"""Téléchargement des tables du client publiées par wago.tools (CSV), avec cache et empreintes.

Seul appelant réseau avec `builds` : tout passe par le client injecté `Deps.http_get`. Le cache vit hors de
`forever/data/` : `<cache>/wago/<version>/<locale>/<Table>.csv`, indexé par `<cache>/wago/<version>/fetch.json`."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TypedDict

from forever.config import FETCH_TIMEOUT, USER_AGENT, Deps
from forever.errors import FetchFailedError, InvalidArgumentError, OfflineError
from forever.manifest import VERSION_DIR_RE
from forever.timefmt import format_utc

DB2_URL = "https://wago.tools/db2/{table}/csv?build={version}"
DEFAULT_LOCALE = "enUS"
INDEX_NAME = "fetch.json"
INDEX_SCHEMA_VERSION = 1
TABLE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
LOCALE_RE = re.compile(r"^[a-z]{2}[A-Z]{2}$")
_HEADER_FIELD_RE = re.compile(r'^"?[A-Za-z_][A-Za-z0-9_\[\]]*"?$')


class TableFetch(TypedDict):
    table: str
    locale: str
    url: str
    sha256: str
    bytes: int
    fetched_at: str
    from_cache: bool


def table_url(table: str, version: str, locale: str | None) -> str:
    """URL CSV d'une table ; la locale par défaut du service (enUS) n'ajoute aucun paramètre."""
    url = DB2_URL.format(table=table, version=version)
    if locale is not None and locale != DEFAULT_LOCALE:
        url += f"&locale={locale}"
    return url


def wago_dir(cache_dir: Path, version: str) -> Path:
    return cache_dir / "wago" / version


def table_path(cache_dir: Path, version: str, locale: str, table: str) -> Path:
    return wago_dir(cache_dir, version) / locale / f"{table}.csv"


def index_path(cache_dir: Path, version: str) -> Path:
    return wago_dir(cache_dir, version) / INDEX_NAME


def _check_arguments(version: str, tables: Sequence[str], locales: Sequence[str]) -> None:
    if not VERSION_DIR_RE.fullmatch(version):
        raise InvalidArgumentError(
            f"Version mal formée : « {version} ».", "donner une version complète, par exemple 1.60.1.70009"
        )
    bad_tables = [t for t in tables if not TABLE_RE.fullmatch(t)]
    if bad_tables or not tables:
        shown = ", ".join(repr(t) for t in bad_tables) or "aucune"
        raise InvalidArgumentError(
            f"Nom de table invalide : {shown}.", "donner des noms de tables wago (ex. SpellName)"
        )
    bad_locales = [loc for loc in locales if not LOCALE_RE.fullmatch(loc)]
    if bad_locales or not locales:
        shown = ", ".join(repr(loc) for loc in bad_locales) or "aucune"
        raise InvalidArgumentError(f"Locale invalide : {shown}.", "donner une locale de la forme enUS ou frFR")


def looks_like_csv(body: bytes) -> bool:
    """Première ligne en UTF-8 faite de noms de colonnes (refuse une page HTML ou un JSON d'erreur)."""
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError:
        return False
    header = text.split("\n", 1)[0].rstrip("\r")
    fields = header.split(",")
    return bool(header) and all(_HEADER_FIELD_RE.fullmatch(f) for f in fields)


def _read_index(path: Path, version: str) -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict) or data.get("version") != version or not isinstance(data.get("tables"), dict):
        return {}
    return {k: v for k, v in data["tables"].items() if isinstance(v, dict)}


def _write_index(path: Path, version: str, tables: dict[str, dict[str, Any]]) -> None:
    data = {"schema_version": INDEX_SCHEMA_VERSION, "version": version, "tables": dict(sorted(tables.items()))}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def _cached(path: Path, entry: dict[str, Any] | None) -> bytes | None:
    if entry is None or not path.is_file():
        return None
    body = path.read_bytes()
    return body if hashlib.sha256(body).hexdigest() == entry.get("sha256") else None


def fetch_tables(
    deps: Deps,
    version: str,
    tables: Sequence[str],
    *,
    locales: Sequence[str] = (DEFAULT_LOCALE,),
    refresh: bool = False,
) -> list[TableFetch]:
    """Télécharge chaque table pour chaque locale (dans l'ordre donné) ; un fichier du cache conforme à son
    empreinte n'est pas retéléchargé, sauf `refresh`. Les tables réussies sont écrites même si d'autres
    échouent ; les échecs sont signalés ensemble à la fin (FetchFailedError)."""
    _check_arguments(version, tables, locales)
    if deps.offline:
        raise OfflineError("le téléchargement des tables")
    ipath = index_path(deps.cache_dir, version)
    index = _read_index(ipath, version)
    results: list[TableFetch] = []
    failures: list[str] = []
    headers = {"User-Agent": USER_AGENT, "Accept": "text/csv"}
    for locale in locales:
        for table in tables:
            key = f"{locale}/{table}"
            path = table_path(deps.cache_dir, version, locale, table)
            url = table_url(table, version, locale)
            body = None if refresh else _cached(path, index.get(key))
            if body is not None:
                entry = index[key]
                results.append({**entry, "from_cache": True})  # type: ignore[typeddict-item]
                continue
            try:
                body = deps.http_get(url, headers, FETCH_TIMEOUT)
            except OSError as exc:
                failures.append(f"{key} ({exc})")
                continue
            if not looks_like_csv(body):
                failures.append(f"{key} (réponse qui n'est pas un CSV)")
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            entry = {
                "table": table,
                "locale": locale,
                "url": url,
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
                "fetched_at": format_utc(deps.now()),
            }
            index[key] = entry
            _write_index(ipath, version, index)
            results.append({**entry, "from_cache": False})  # type: ignore[typeddict-item]
    if failures:
        raise FetchFailedError(f"Téléchargement impossible pour {version} : {' ; '.join(failures)}.")
    return results
