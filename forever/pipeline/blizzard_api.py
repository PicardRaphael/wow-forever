"""Sonde de l'API Blizzard (T08b, point 10, décision 149) : savoir quand l'API couvre Forever, pour décider d'EC1.

Usage autorisé des API (conditions des API de Blizzard) : jeton par *client credentials* (`POST` sur `TOKEN_URL`,
authentification de base par les clés de l'utilisateur), puis quelques routes de Game Data essayées avec les **espaces
de noms candidats de Forever seulement** (`static-forever-<région>`, `dynamic-forever-<région>`, et leurs variantes
`classicforever`). Un espace de Retail (`static-eu`), de Classic Era (`classic1x`), de Classic (`classic`) ou de TBC
(`classicann`, `tbc`) n'est **jamais** interrogé : sa réponse n'est pas une donnée de Forever.

Clés : variables d'environnement `BLIZZARD_CLIENT_ID` et `BLIZZARD_CLIENT_SECRET`, sinon fichier `.env` (local) ;
secrets du dépôt en CI. Elles ne figurent jamais dans un résultat, un message d'erreur ni un journal. Une requête à la
fois, avec une pause (bien sous les limites de l'API). Aucune donnée n'entre dans le dépôt : la sonde rend des statuts
HTTP et la couverture (Game Data, Profile, hôtel des ventes, PvP)."""

from __future__ import annotations

import base64
import json
import re
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.config import FETCH_TIMEOUT, USER_AGENT, Deps
from forever.errors import FetchFailedError, InvalidArgumentError, OfflineError
from forever.timefmt import format_utc

TOKEN_URL = "https://oauth.battle.net/token"
API_HOST = "https://{region}.api.blizzard.com"
KEY_NAMES = ("BLIZZARD_CLIENT_ID", "BLIZZARD_CLIENT_SECRET")
# Préfixes candidats (noms non publiés à ce jour : à corriger dès que Blizzard les annonce).
CANDIDATES = ("static-forever", "dynamic-forever", "static-classicforever", "dynamic-classicforever")
_NOT_FOREVER = re.compile(r"classic1x|classicann|tbc|^(static|dynamic|profile)-(classic-)?[a-z]{2}$")
PAUSE_S = 0.2  # pause entre deux requêtes (paramètre de l'outil, bien sous les limites de l'API)
# (route, type d'espace, rubrique de couverture) ; `{item}` : premier bijou de pvp_items.json.
ROUTES = (
    ("/data/wow/playable-class/index", "static", "game_data"),
    ("/data/wow/item/{item}", "static", "game_data"),
    ("/data/wow/realm/index", "dynamic", "game_data"),
    ("/data/wow/connected-realm/index", "dynamic", "auction_house"),
    ("/data/wow/pvp-season/index", "dynamic", "pvp"),
)


def candidate_namespaces(region: str) -> list[str]:
    return [f"{prefix}-{region}" for prefix in CANDIDATES]


def is_forever_namespace(namespace: str) -> bool:
    """Vrai seulement pour un espace dont le nom désigne Forever (jamais Retail, Classic Era, Classic ni TBC)."""
    return "forever" in namespace and not _NOT_FOREVER.search(namespace)


def load_keys(environ: Mapping[str, str], env_file: Path | None) -> dict[str, str]:
    """Clés depuis l'environnement, sinon depuis `env_file` (`NOM=valeur`, guillemets ôtés) ; rien n'est affiché."""
    keys = {k: environ[k] for k in KEY_NAMES if environ.get(k)}
    if len(keys) < len(KEY_NAMES) and env_file is not None and env_file.is_file():
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = (x.strip() for x in line.split("=", 1))
            if name in KEY_NAMES and name not in keys:
                keys[name] = value.strip("'\"")
    return keys


def _item_id(deps: Deps) -> int | None:
    from forever.manifest import version_dirs

    versions = version_dirs(deps.data_dir)
    if not versions:
        return None
    try:
        doc = json.loads((deps.data_dir / versions[-1] / "pvp_items.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    trinkets = doc.get("trinkets") or []
    return int(trinkets[0]["item_id"]) if trinkets else None


def _token(keys: Mapping[str, str], http_post: Callable[..., bytes]) -> str:
    raw = f"{keys['BLIZZARD_CLIENT_ID']}:{keys['BLIZZARD_CLIENT_SECRET']}".encode()
    headers = {
        "User-Agent": USER_AGENT,
        "Authorization": "Basic " + base64.b64encode(raw).decode("ascii"),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    try:
        body = http_post(TOKEN_URL, headers, b"grant_type=client_credentials", FETCH_TIMEOUT)
        token = json.loads(body.decode("utf-8")).get("access_token")
    except (OSError, ValueError, AttributeError) as exc:
        # le message d'origine peut citer l'adresse ou l'en-tête : il n'est jamais repris (clés)
        raise FetchFailedError(f"Jeton de l'API Blizzard refusé ou illisible ({type(exc).__name__}).") from None
    if not isinstance(token, str) or not token:
        raise FetchFailedError("Jeton de l'API Blizzard absent de la réponse.")
    return token


def probe(
    deps: Deps,
    keys: Mapping[str, str],
    *,
    regions: Sequence[str] = ("eu", "us"),
    http_post: Callable[..., bytes] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    """Essaie chaque route avec chaque espace candidat de Forever ; rend les statuts et la couverture."""
    missing = [k for k in KEY_NAMES if not keys.get(k)]
    if missing:
        raise InvalidArgumentError(
            f"Clés de l'API Blizzard absentes : {', '.join(missing)}.",
            "les mettre dans .env (local) ou dans les secrets du dépôt (CI), jamais dans le code",
        )
    if deps.offline:
        raise OfflineError("la sonde de l'API Blizzard")
    if http_post is None:
        from forever.pipeline.http_client import urllib_post

        http_post = urllib_post
    pause = sleep or time.sleep
    token = _token(keys, http_post)
    item = _item_id(deps)
    results: list[dict[str, Any]] = []
    for region in regions:
        for namespace in candidate_namespaces(region):
            if not is_forever_namespace(namespace):
                continue  # garde-fou : jamais un espace d'une autre version du jeu
            kind = namespace.split("-", 1)[0]
            for route, route_kind, section in ROUTES:
                if route_kind != kind or ("{item}" in route and item is None):
                    continue
                path = route.format(item=item)
                url = f"{API_HOST.format(region=region)}{path}?namespace={namespace}&locale=en_US"
                headers = {"User-Agent": USER_AGENT, "Authorization": f"Bearer {token}"}
                try:
                    deps.http_get(url, headers, FETCH_TIMEOUT)
                    status = "répond"
                except OSError as exc:
                    status = f"ne répond pas ({str(exc).replace(token, '…')[:60]})"
                results.append(
                    {"region": region, "namespace": namespace, "route": path, "section": section, "status": status}
                )
                pause(PAUSE_S)
    responding = sorted({r["namespace"] for r in results if r["status"] == "répond"})
    coverage: dict[str, Any] = {
        section: any(r["status"] == "répond" for r in results if r["section"] == section)
        for section in ("game_data", "auction_house", "pvp")
    }
    coverage["profile"] = "non sondé : une fiche de personnage demande un royaume et un nom (EC1)"
    return {
        "checked_at": format_utc(deps.now()),
        "regions": list(regions),
        "results": results,
        "responding": responding,
        "coverage": coverage,
        "issue_needed": bool(responding),
    }


def probe_issue_body(result: Mapping[str, Any]) -> str:
    """Corps de l'issue « L'API Blizzard couvre Forever » (aucune clé, aucun jeton)."""
    cov = result["coverage"]

    def yes(value: Any) -> str:
        return "oui" if value is True else "non" if value is False else str(value)

    lines = [
        "La sonde quotidienne de l'API Blizzard (décision 149) a obtenu une réponse d'un espace de noms de Forever.",
        "",
        f"- espaces qui répondent : {', '.join(result['responding']) or 'aucun'}",
        f"- Game Data : {yes(cov['game_data'])}",
        f"- Profile : {yes(cov['profile'])}",
        f"- hôtel des ventes (royaumes connectés) : {yes(cov['auction_house'])}",
        f"- PvP (saisons) : {yes(cov['pvp'])}",
        "",
        "| Région | Espace | Route | Statut |",
        "| --- | --- | --- | --- |",
        *[f"| {r['region']} | {r['namespace']} | {r['route']} | {r['status']} |" for r in result["results"]],
        "",
        (
            f"Sondé le {result['checked_at']}. À décider : démarrage d'EC1 (API Blizzard : hôtel des ventes, "
            "personnages, PvP, décision 126) ; aucune donnée n'entre dans le dépôt avant le plan d'EC1."
        ),
    ]
    return "\n".join(lines) + "\n"
