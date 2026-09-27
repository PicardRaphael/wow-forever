"""Serveur MCP : outils `forever_status`, `forever_lookup`, `forever_explain_mechanic` et `forever_sim_leveling` (même
cœur que la CLI).

Une erreur métier est renvoyée comme résultat d'outil (`is_error`, `structured_content` avec l'erreur et la
provenance) : une exception brute ne montrerait au modèle qu'un message générique."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent

from forever import __version__
from forever.config import Deps
from forever.errors import ForeverError, InvalidArgumentError, UnsupportedKindError
from forever.explain import MechanicExplanation, explain_mechanic
from forever.leveling import LevelingReport, simulate_leveling
from forever.lookup import lookup_spell, lookup_zones
from forever.provenance import error_payload
from forever.status import StatusReport, status_report

INSTRUCTIONS = (
    "Données de World of Warcraft: Forever, versionnées par version du jeu. Chaque résultat porte un bloc "
    "`provenance` (version, empreinte, fraîcheur, certitude, hypothèses) à citer dans la réponse."
)


def _error_result(deps: Deps, err: ForeverError) -> CallToolResult:
    payload = error_payload(deps, err)
    text = f"Erreur ({err.code}) : {err.message} À faire : {err.action}."
    if err.suggestions:
        text += f" Suggestions : {', '.join(err.suggestions)}."
    return CallToolResult(
        is_error=True,
        structured_content=json.loads(json.dumps(payload)),
        content=[TextContent(type="text", text=text)],
    )


def build_server(deps: Deps) -> MCPServer:
    server = MCPServer("forever", version=__version__, instructions=INSTRUCTIONS)

    @server.tool()
    def forever_status(offline: bool = False) -> StatusReport:
        """Fraîcheur des données (dernière version publiée du jeu), intégrité des empreintes, couverture du registre.

        `offline=True` : aucun appel réseau, dernier état connu seulement."""
        return status_report(deps, allow_network=not offline)

    @server.tool()
    def forever_lookup(
        kind: str,
        name: str = "",
        rank: int | None = None,
        detail: bool = False,
        limit: int = 20,
        offset: int = 0,
        level: int | None = None,
        faction: str | None = None,
        questie: str | None = None,
    ) -> dict[str, Any]:
        """Consulte une entité du jeu. T01 : `kind="spell"` (sorts de dégâts, nom anglais, ex. « frostbolt »).

        `rank` : position du rang à partir de 1 (tous les rangs, paginés, s'il est omis).
        `detail=True` : champs complémentaires (ralentissement, vitesse de projectile…).
        T04c : `kind="zones"` avec `level` (niveau du personnage), `faction` (horde ou alliance, défaut : toutes) et
        `questie` (dossier de l'addon, défaut : dans FOREVER_WOW_DIR) : zones et donjons classés par quêtes utiles
        (base Questie Classic Era lue sur disque, noms anglais, certitude suppose)."""
        try:
            if kind == "zones":
                path = Path(questie) if questie else None
                return dict(lookup_zones(deps, level, faction=faction, questie_dir=path))
            if kind != "spell":
                raise UnsupportedKindError(f"type « {kind} »", ["spell", "zones"])
            if not name:
                raise InvalidArgumentError("Nom du sort manquant.", "donner name (nom anglais du sort)")
            return dict(lookup_spell(deps, name, rank, detail=detail, limit=limit, offset=offset))
        except ForeverError as err:
            # Le SDK transmet tel quel un CallToolResult renvoyé par l'outil (vérifié avec mcp 2.2).
            return cast("dict[str, Any]", _error_result(deps, err))

    @server.tool()
    def forever_explain_mechanic(mechanic_id: str) -> MechanicExplanation:
        """Explique une mécanique du registre (identifiant de la forme « A5 », casse ignorée) : description, statut,
        certitude, formule symbolique, paramètres chiffrés de la version courante, implémentation, sources, tests."""
        try:
            return explain_mechanic(deps, mechanic_id)
        except ForeverError as err:
            return cast(MechanicExplanation, _error_result(deps, err))

    @server.tool()
    def forever_sim_leveling(
        level: int,
        race: str = "Orc",
        rotation: str = "frost",
        talents: dict[str, int] | None = None,
        n: int = 1500,
        seed: int = 12345,
        mob_source: str = "measured",
        spell_level: str = "character",
        level_diff: int | None = None,
        nova: bool = False,
        rules: str = "forever",
        armor: str = "auto",
        ab_stacks: int | None = None,
        ab_dump: str | None = None,
    ) -> LevelingReport:
        """Leveling du Mage : temps par monstre (combat, repos, total), mana, dégâts subis et XP par heure, par Monte
        Carlo (moyenne de `n` combats, graine fixe) et par le modèle analytique, avec les PV du monstre (valeur,
        source, certitude) et la provenance.

        `rotation` : frost, fire ou arcane. `talents` : clé de talent -> rang (ex. {"improvedFrostbolt": 3}), build vérifié.
        `mob_source` : measured (PV mesurés, puis Questie corrigé) ou seed (modèle du seed).
        `spell_level` : character (dégâts au niveau du personnage) ou rank (dégâts du rang, parité avec le seed).
        `rules` : forever (corrections de Forever, défaut) ou seed (comportement du seed, parité).
        `armor` : auto (armure selon le niveau d'apprentissage lu dans le client), frost ou mage (paramètre de build ;
        Mage Armor sous son niveau d'apprentissage est refusée).
        Rotation arcane (niveau 20 et talent arcaneBlast) : `ab_stacks` cumuls d'Arcane Blast (0 au maximum du
        talent ; défaut : maximum) puis `ab_dump` (frostbolt par défaut, fireball, arcane_missiles)."""
        try:
            return simulate_leveling(
                deps,
                level,
                race=race,
                rotation=rotation,
                talents=talents,
                n=n,
                seed=seed,
                mob_source=mob_source,
                spell_level=spell_level,
                level_diff=level_diff,
                nova=nova,
                rules=rules,
                armor=armor,
                ab_stacks=ab_stacks,
                ab_dump=ab_dump,
            )
        except ForeverError as err:
            return cast(LevelingReport, _error_result(deps, err))

    return server
