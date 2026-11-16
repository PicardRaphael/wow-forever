"""RA1 : données de l'addon ForeverRappels (`RappelsData.lua`), générées depuis `classes.json` de la version installée.

Le dépôt ne garde dans `addon/ForeverRappels/RappelsData.lua` qu'un fichier vide, sans identifiant de sort : les
identifiants (tous les rangs) et les noms viennent des données du client, écrits dans la copie installée par
`scripts/install_addon.py --addon ForeverRappels`. Une nouvelle version des données se reporte en réinstallant."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from forever.store import VersionData

# Groupe de sorts lu par l'addon -> (classe, clé du sort dans `classes.json`).
GROUPS: Mapping[str, tuple[str, str]] = {
    "aspect_faucon": ("Hunter", "aspectOfTheHawk"),
    "aspect_guepard": ("Hunter", "aspectOfTheCheetah"),
    "aspect_meute": ("Hunter", "aspectOfThePack"),
    "aspect_bete": ("Hunter", "aspectOfTheBeast"),
}


def build_groups(classes: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Groupes de sorts : nom français (anglais à défaut) et identifiants de tous les rangs, dans l'ordre des données.
    Un sort absent des données laisse son groupe de côté."""
    out: dict[str, dict[str, Any]] = {}
    for group, (cls, key) in GROUPS.items():
        spell = classes.get("classes", {}).get(cls, {}).get("spells", {}).get(key)
        if not spell:
            continue
        ids = [int(r["spell_id"]) for r in spell.get("ranks", []) if r.get("spell_id")]
        if ids:
            out[group] = {"name": spell.get("name_fr") or spell["name"], "spells": ids}
    return out


def _lua_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def render_lua(groups: Mapping[str, Mapping[str, Any]], *, game_version: str, data_sha: str) -> str:
    """Texte de `RappelsData.lua`, version et empreinte des données en tête."""
    lines = [
        "-- Généré par forever (RA1) depuis classes.json : ne pas modifier à la main.",
        "ForeverRappelsData = {",
        f"    game_version = {_lua_string(game_version)},",
        f"    data_sha = {_lua_string(data_sha)},",
        "    groups = {",
    ]
    for group in sorted(groups):
        g = groups[group]
        spells = ", ".join(str(int(i)) for i in g["spells"])
        lines.append(f"        {group} = {{ name = {_lua_string(str(g['name']))}, spells = {{ {spells} }} }},")
    lines += ["    },", "}", ""]
    return "\n".join(lines)


def data_lua(version: VersionData) -> str:
    """`RappelsData.lua` de la version de données installée."""
    return render_lua(
        build_groups(version.read_json("classes.json")), game_version=version.game_version, data_sha=version.data_sha
    )
