"""Serveur MCP : outils `forever_status`, `forever_lookup`, `forever_explain_mechanic`, `forever_sim_leveling` et
`forever_build` (même cœur que la CLI).

Une erreur métier est renvoyée comme résultat d'outil (`is_error`, `structured_content` avec l'erreur et la
provenance) : une exception brute ne montrerait au modèle qu'un message générique."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent

from forever import __version__
from forever.build import BuildReport, build_report
from forever.config import Deps
from forever.errors import ForeverError, InvalidArgumentError, UnsupportedKindError
from forever.explain import MechanicExplanation, explain_mechanic
from forever.leveling import LevelingReport, parse_talents, simulate_leveling
from forever.lookup import lookup_spell, lookup_talent, lookup_zones
from forever.profile import ProfileView, read_profile
from forever.provenance import error_payload
from forever.pvp import compact, pvp_report
from forever.status import StatusReport, status_report

INSTRUCTIONS = (
    "Données de World of Warcraft: Forever, versionnées par version du jeu. Chaque résultat porte un bloc "
    "`provenance` (version, empreinte, fraîcheur, certitude, hypothèses) à citer dans la réponse.\n"
    "\n"
    "Règles de réponse, pour toute IA cliente :\n"
    "1. Aucun chiffre de jeu sans appel d'outil. Chaque valeur est recopiée telle quelle d'un résultat de ces "
    "outils : jamais tirée de la mémoire du modèle, jamais calculée (ni somme, ni produit, ni moyenne, ni formule "
    "appliquée à la main). Si le chiffre voulu n'est dans aucun résultat, demander l'outil qui le rend ou dire "
    "qu'il manque.\n"
    "2. Afficher la certitude et la provenance de toute réponse chiffrée : certitude (`certain` lu dans le client "
    "ou observé en jeu, `probable` calculé ou recoupé, `suppose` estimé ou hérité), version du jeu, fraîcheur des "
    "données, et les hypothèses du bloc `provenance`. Une fraîcheur `stale`, `unknown` ou `silent` se signale.\n"
    "3. Dire ce qui n'est pas couvert. Quand aucun outil ne répond à la question, répondre « je ne sais pas », "
    "nommer ce qui manque et ne rien inventer ; une source extérieure citée reste étiquetée comme telle, avec sa "
    "date, et sa certitude ne dépasse jamais `suppose`."
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
        opponent: str | None = None,
        race: str | None = None,
        talents: str | None = None,
        opponent_level: int | None = None,
    ) -> dict[str, Any]:
        """Consulte une entité du jeu. T01 : `kind="spell"` (sorts de dégâts, nom anglais, ex. « frostbolt »).

        `rank` : position du rang à partir de 1 (tous les rangs, paginés, s'il est omis).
        `detail=True` : champs complémentaires (ralentissement, vitesse de projectile…).
        T04c : `kind="zones"` avec `level` (niveau du personnage), `faction` (horde ou alliance, défaut : toutes) et
        `questie` (dossier de l'addon, défaut : dans FOREVER_WOW_DIR) : zones et donjons classés par quêtes utiles
        (base Questie Classic Era lue sur disque, noms anglais, certitude suppose).
        T06 : `kind="talent"` avec `name` (nom anglais ou clé, ex. « Improved Frostbolt » ou « improvedFrostbolt »)
        et `rank` (tous les rangs s'il est omis) : arbre, palier, points exigés dans l'arbre, prérequis, valeurs et
        description de chaque rang, sort appris, source des valeurs.
        PV1 : `kind="pvp"` avec `name` (classe, nom français ou anglais), `level`, et pour un affrontement
        `opponent` (classe adverse), `race`, `talents` (« clé=rang,… » ; défaut : inconnus, sorts de talent
        « si talent »), `opponent_level` : fiche PvP fixe tirée du client (contrôles, défensifs, ruptures,
        interruptions, dissipations, recharges, raciaux, bijoux), listes paginées (`limit`, `offset`, `totals`),
        valeurs avec leur chemin dans les données si `detail=True`, `missing` à citer. Ne lit jamais le profil :
        passer la classe, le niveau, la race et les talents lus par forever_player_profile."""
        try:
            if kind == "zones":
                path = Path(questie) if questie else None
                return dict(lookup_zones(deps, level, faction=faction, questie_dir=path))
            if kind == "talent":
                if not name:
                    raise InvalidArgumentError("Nom du talent manquant.", "donner name (nom anglais ou clé du talent)")
                return dict(lookup_talent(deps, name, rank))
            if kind == "pvp":
                if not name:
                    raise InvalidArgumentError("Classe manquante.", "donner name (classe, nom français ou anglais)")
                report = pvp_report(
                    deps,
                    name,
                    opponent=opponent,
                    level=level,
                    race=race,
                    talents=parse_talents(talents) if talents else None,
                    opponent_level=opponent_level,
                )
                return compact(report, detail=detail, limit=limit, offset=offset)
            if kind != "spell":
                raise UnsupportedKindError(f"type « {kind} »", ["spell", "talent", "zones", "pvp"])
            if not name:
                raise InvalidArgumentError("Nom du sort manquant.", "donner name (nom anglais du sort)")
            return dict(lookup_spell(deps, name, rank, detail=detail, limit=limit, offset=offset))
        except ForeverError as err:
            # Le SDK transmet tel quel un CallToolResult renvoyé par l'outil (vérifié avec mcp 2.2).
            return cast("dict[str, Any]", _error_result(deps, err))

    @server.tool()
    def forever_player_profile(name: str | None = None) -> ProfileView:
        """Profil du joueur (lecture seule, hors du dépôt) : personnage actif, ou `name` ; liste des personnages,
        `stale` (saisi sur une autre version des données), `missing` (race, faction, niveau, talents ou métiers non
        renseignés). À lire avant tout calcul qui dépend du personnage ; les outils de calcul ne le lisent jamais
        d'eux-mêmes. Écriture : `forever profile set` (CLI)."""
        try:
            return read_profile(deps, name)
        except ForeverError as err:
            return cast(ProfileView, _error_result(deps, err))

    @server.tool()
    def forever_explain_mechanic(mechanic_id: str, level: int | None = None) -> MechanicExplanation:
        """Explique une mécanique du registre (identifiant de la forme « A5 », casse ignorée, ou mots de sa
        description en français ou en anglais selon le registre, ex. « Ignite » ; plusieurs entrées : la liste
        « identifiant : description » est rendue en suggestions) : description, statut,
        certitude, formule symbolique, paramètres chiffrés de la version courante, implémentation, sources, tests,
        et `derived` : valeurs par cumul calculées (coût d'Arcane Blast, critique de Winter's Chill, Hot Streak), en
        mana au niveau `level` s'il est donné."""
        try:
            return explain_mechanic(deps, mechanic_id, level)
        except ForeverError as err:
            return cast(MechanicExplanation, _error_result(deps, err))

    @server.tool()
    def forever_sim_leveling(
        level: int,
        race: str | None = None,
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
        low_level_penalty: bool | None = None,
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
        talent ; défaut : maximum) puis `ab_dump` (frostbolt par défaut, fireball, arcane_missiles).
        `low_level_penalty` : pénalité des sorts de bas niveau (None : défaut des données ; False refusé avec seed)."""
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
                low_level_penalty=low_level_penalty,
            )
        except ForeverError as err:
            return cast(LevelingReport, _error_result(deps, err))

    @server.tool()
    def forever_build(
        context: str,
        level: int | None = None,
        race: str | None = None,
        current: dict[str, int] | None = None,
        respecs: int = 0,
        sp: float | None = None,
        crit: float | None = None,
        preset: str = "rapide",
        seed: int = 12345,
        rules: str = "forever",
        sensitivity: bool = True,
        talented_bonus: int = 0,
    ) -> BuildReport:
        """Build du Mage par contexte (leveling, dungeon, raid, pvp-bg, pvp-world) à un niveau : talents et ordre
        d'apprentissage, choix du build (rotation, armure, cumuls d'Arcane Blast et de Hot Streak), raison de chaque
        talent (valeur marginale), alternative la plus proche avec écart apparié et intervalle de confiance, stabilité
        sur plusieurs graines, sensibilité aux sept hypothèses incertaines, respec (coût, gain, niveau conseillé),
        angles morts (borne haute ou non chiffré), certitude, hypothèses et provenance. Donjon et raid : scénarios
        provisoires. Au-delà du plafond de la bêta, le build n'est pas vérifiable en jeu avant la sortie.

        `level` absent : niveau maximal des données (question générale sans niveau, `inputs.level.origin` vaut
        `default`). `current` : build actuel {clé: rang} (conseil de respec ; à un niveau plus bas que `level`, le
        bloc `respec.projected` donne le chemin conseillé depuis ce build jusqu'à `level`) ; `respecs` : réinitialisations déjà faites ;
        `sp`, `crit` : fiche remplacée (puissance des sorts, critique en fraction) ; `preset` : rapide (défaut) ou
        complet ; `rules` : forever, ou seed (leveling seulement, parité) ; `talented_bonus` : points du bonus Legacy
        « Talented » (hypothèse)."""
        try:
            return build_report(
                deps,
                context,
                level,
                race=race,
                current=current,
                respecs=respecs,
                sp=sp,
                crit=crit,
                preset=preset,
                seed=seed,
                rules=rules,
                sensitivity=sensitivity,
                talented_bonus=talented_bonus,
            )
        except ForeverError as err:
            return cast(BuildReport, _error_result(deps, err))

    return server
