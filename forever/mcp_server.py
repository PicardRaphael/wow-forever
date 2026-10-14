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
from forever.build import build_report
from forever.config import Deps
from forever.errors import ForeverError, InvalidArgumentError, UnsupportedKindError
from forever.explain import MechanicExplanation, explain_mechanic
from forever.leveling import parse_talents, simulate_leveling
from forever.lookup import check_talents, lookup_class_talent, lookup_spell, lookup_talent, lookup_zones
from forever.pets_lookup import lookup_pets
from forever.profile import ProfileView, normalize_class, read_profile
from forever.provenance import error_payload
from forever.pvp import compact, pvp_report
from forever.status import status_report
from forever.talents_forever import BuildWithExport, attach_export

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
    def forever_status(offline: bool = False) -> dict[str, Any]:
        """Fraîcheur des données (dernière version publiée du jeu), intégrité des empreintes, couverture du registre,
        et bloc `update` en lecture seule (dernier passage de `forever update`, attentes d'accord ; l'approbation se
        fait dans la CLI, jamais par un outil MCP).

        `offline=True` : aucun appel réseau, dernier état connu seulement."""
        from forever.update import update_summary

        return {**status_report(deps, allow_network=not offline), "update": update_summary(deps.cache_dir, deps.now())}

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
        class_name: str | None = None,
        zone: str | None = None,
        current: str | None = None,
        status: str | None = None,
        quest_id: int | None = None,
        dungeon: str | None = None,
        access: str | None = None,
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
        passer la classe, le niveau, la race et les talents lus par forever_player_profile.
        PV1 : `kind="talent"` avec `class_name` (9 classes, défaut Mage) ; `kind="build_check"` avec `name` (classe),
        `level` et `talents` (« clé=rang,… ») : légal ou liste des erreurs, description des talents du client.
        CH0 : `kind="pets"` (familiers du Chasseur) : sans `name`, règles du système (entraînement, loyauté,
        apprivoisement, héritage…, chacune avec source et certitude) ; `name` = famille, capacité ou bête (nom
        français ou anglais) : sa fiche (`rank`, `detail` pour les bêtes qui enseignent chaque rang) ; avec `zone`
        (nom français ou anglais) et `level` (niveau du Chasseur, jamais deviné) : guide d'apprivoisement (bêtes de la
        zone puis des zones voisines du même continent à son niveau, coordonnées datées, rang le plus haut
        atteignable). Forever Bestiary lu sur disque ; sans lui, fiches du client seules.
        FA1 : `kind="tf_popular"` avec `name` (classe, nom français ou anglais ; vide : les 9 classes) : builds
        populaires de Talents Forever (addon lu sur disque) : part de chaque spécialisation, date `asOf`, fenêtre,
        lien et commande `/tf import` de chaque build, légalité sur le client ; certitude `suppose` (choix de
        joueurs). P06b : avec `current` (talents actuels, « clé=rang,… »), `closest` : le build populaire le plus
        proche, calculé par l'outil (même spécialisation, points absents, écarts) ; à donner tel quel, sans en choisir
        un autre ; `null` si aucun point n'est placé.
        T04d : `kind="quests"` : quêtes de Forever fusionnées (Questie, Naowh Forever, Forever Guide,
        ForeverDungeonJournal, GearQuest et quêtes vues par le client, lus en local) ; filtres `level` (quêtes
        accessibles et non grises), `faction`, `zone`, `status` (nouvelle, retouchée, absente des sources Forever,
        inchangée, non couverte), `dungeon`, `quest_id` ; chaque champ porte sa source et sa certitude, chaque
        désaccord entre sources est dans `discrepancies` ; paginé (`limit`, `offset`, `total`).
        T04f : `kind="xp_bonuses"` (toutes les classes), `access` facultatif (item, legacy, food, camp, none) : chaque
        bonus d'XP du client avec ses effets, sa durée, son cumul, son accès, sa source et sa certitude ; `applied`
        faux pour un bonus sans source joueur (jamais appliqué) ; sac de couchage, nourritures nutritives, camp, règle
        de cumul.
        DJ1 : `kind="dungeons"` (filtres `level`, `faction`) : donjons du livre fusionné (client, note officielle,
        addons et relevés du joueur lus en local), plage retenue et sa source, niveau de contenu du client, nouveau ou
        fermé, nombre d'écarts ; `kind="dungeon"` avec `name` (nom anglais, identifiant d'instance ou clé
        `189:graveyard`), `class_name` et `level` facultatifs : fiche (plages et écarts entre sources, entrée, boss
        et leur niveau, butin avec taux en fraction et sa source, `null` = inconnu, `classic` = taux de Classic,
        objets utilisables, quêtes avec XP et sa source, prérequis « à faire d'abord », passages relevés) ;
        `kind="dungeon_item"` avec `name` (identifiant de l'objet) : donjon, boss, taux, source et version."""
        try:
            if kind in ("dungeons", "dungeon", "dungeon_item"):
                from forever.dungeons import dungeon_payload, dungeons_payload, item_payload

                if kind == "dungeons":
                    return dungeons_payload(deps, level=level, faction=faction)
                if not name:
                    raise InvalidArgumentError("Nom manquant.", "donner name (donjon, ou identifiant de l'objet)")
                if kind == "dungeon":
                    return dungeon_payload(deps, name, class_name=class_name, level=level)
                return item_payload(deps, name)
            if kind == "xp_bonuses":
                from forever.xp_bonuses import lookup_xp_bonuses

                return lookup_xp_bonuses(deps, access=access)
            if kind == "quests":
                from forever.quests import lookup_quests

                return lookup_quests(
                    deps,
                    level=level,
                    zone=zone,
                    status=status,
                    faction=faction,
                    quest_id=quest_id,
                    dungeon=dungeon,
                    limit=limit,
                    offset=offset,
                )
            if kind == "zones":
                path = Path(questie) if questie else None
                return dict(lookup_zones(deps, level, faction=faction, questie_dir=path))
            if kind == "talent":
                if not name:
                    raise InvalidArgumentError("Nom du talent manquant.", "donner name (nom anglais ou clé du talent)")
                if class_name and normalize_class(class_name) != "Mage":
                    return lookup_class_talent(deps, class_name, name)
                return dict(lookup_talent(deps, name, rank))
            if kind == "build_check":
                if not name or level is None:
                    raise InvalidArgumentError("Classe ou niveau manquant.", "donner name (classe), level et talents")
                return check_talents(deps, name, parse_talents(talents) if talents else {}, level)
            if kind == "tf_popular":
                from forever.talents_forever import popular_builds, require_addon

                placed = parse_talents(current) if current else None
                return popular_builds(require_addon(deps), deps, name or None, current=placed)
            if kind == "pets":
                return lookup_pets(deps, name or None, rank=rank, zone=zone, level=level, detail=detail)
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
                raise UnsupportedKindError(
                    f"type « {kind} »",
                    [
                        "spell",
                        "talent",
                        "zones",
                        "pvp",
                        "build_check",
                        "pets",
                        "tf_popular",
                        "quests",
                        "xp_bonuses",
                        "dungeons",
                        "dungeon",
                        "dungeon_item",
                    ],
                )
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
        kind: str = "kill",
        class_name: str | None = None,
        faction: str | None = None,
        rested: float = 0.0,
        party: int = 1,
        limit: int = 5,
        bonus: list[str] | None = None,
        hours: float | None = None,
        sleeping_bag: int | None = None,
        food: bool = False,
        legacy_rested_rank: int | None = None,
        auras: str | None = None,
        has_sleeping_bag: bool | None = None,
    ) -> dict[str, Any]:
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
        `low_level_penalty` : pénalité des sorts de bas niveau (None : défaut des données ; False refusé avec seed).
        T04d : `kind="objectives"` (toutes les classes, `class_name` en anglais, `faction`, `level`, `race`,
        `rested`, `party`) : XP par heure par zone et par donjon (premier passage avec ses quêtes, passages
        suivants), temps par monstre et sa source (`engine` pour le Mage, `measured` ou `estimated` sinon), `advice`
        : phrase de conseil construite par l'outil à partir de ses chiffres, à rendre telle quelle.
        T04f : bonus d'XP. `kind="kill"` : `bonus` (sleeping_bag, food), `rested` (réservoir), `hours` (séance) :
        `xp_h` multiplié par le facteur de la séance, `bonuses` les liste ; sans bonus, sortie inchangée.
        `kind="objectives"` : `rested`, `sleeping_bag` (cumuls, 0 : le maximum), `food`, `legacy_rested_rank`,
        `hours` : chaque objectif rend `xp_h`, `xp_h_rested`, `xp_h_sleeping_bag`, `xp_h_all` ; `bonuses.advice`
        (bonus à prendre, rangés par gain) et `bonus_advice` (phrase de l'outil, à rendre telle quelle) ; `auras`
        (« sort:cumuls:secondes restantes,… », contexte du jeu) et `has_sleeping_bag` : bonus actifs du moment ;
        `sleeping_bag_chain` (sans sac, au niveau de la chaîne) : étapes, étape suivante et `sentence` à rendre telle
        quelle."""
        if kind == "objectives":
            from forever.bridge.context import xp_context
            from forever.sim.objectives import objectives

            try:
                return objectives(
                    deps,
                    class_name=class_name or "mage",
                    level=level,
                    faction=faction,
                    race=race,
                    rested=rested,
                    party=party,
                    limit=limit,
                    sleeping_bag=sleeping_bag,
                    food=food,
                    legacy_rested_rank=legacy_rested_rank,
                    hours=hours,
                    auras=xp_context({"xp_auras": auras or ""}).auras,
                    has_sleeping_bag=has_sleeping_bag,
                )
            except ForeverError as err:
                return cast(dict[str, Any], _error_result(deps, err))
        try:
            report = simulate_leveling(
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
                bonus=bonus or (),
                rested=rested,
                hours=hours,
            )
        except ForeverError as err:
            return cast(dict[str, Any], _error_result(deps, err))
        return dict(report)

    @server.tool()
    def forever_route(
        action: str = "plan",
        class_name: str | None = None,
        faction: str | None = None,
        start_level: int | None = None,
        end_level: int | None = None,
        dungeons: str = "auto",
        class_quests: bool = True,
        exclude: list[int] | None = None,
        include: list[int] | None = None,
        seed: int | None = None,
        plan_id: str | None = None,
    ) -> dict[str, Any]:
        """Feuille de route de leveling (RX1) : `action="plan"` calcule une route (`class_name`, `faction` horde ou
        alliance, `start_level`, `end_level`, `dungeons` auto, none ou noms séparés par des virgules, `class_quests`,
        quêtes `exclude` ou `include`, `seed`) et rend le plan, son aperçu (`preview` : niveaux, heures, XP par heure,
        donjons placés, récompenses, bonus rappelés, certitude) et sa provenance ; `action="show"` relit un plan
        (`plan_id`) ; `action="guide"` rend son guide RestedXP (texte). Ajuster : relancer `plan` avec les options
        changées (« enlève Wailing Caverns » : `dungeons` sans lui, ou `exclude`)."""
        from forever.route import RouteRequest, guide_name, load_plan, plan_route, route_preview
        from forever.rxp import encode_guide

        if action == "plan":
            if not class_name or not faction or start_level is None or end_level is None:
                raise InvalidArgumentError(
                    "Feuille de route : classe, camp, niveau de départ et niveau d'arrivée requis.",
                    "donner class_name, faction, start_level et end_level",
                )
            chosen: str | tuple[str, ...] = dungeons
            if dungeons not in ("auto", "none"):
                chosen = tuple(d.strip() for d in dungeons.split(",") if d.strip())
            plan = plan_route(
                deps,
                RouteRequest(
                    class_name=class_name,
                    faction=faction,
                    start_level=start_level,
                    end_level=end_level,
                    dungeons=chosen,
                    class_quests=class_quests,
                    exclude=tuple(exclude or ()),
                    include=tuple(include or ()),
                    seed=seed,
                ),
            )
        elif action in ("show", "guide") and plan_id:
            plan = load_plan(deps, plan_id)
        else:
            raise InvalidArgumentError(f"Action inconnue ou plan manquant : {action}.", "plan, show ou guide (plan_id)")
        if action == "guide":
            name = guide_name(plan)
            return {"id": plan["id"], "name": name, "text": encode_guide(plan, name=name, group="Forever Routes"),
                    "provenance": plan["provenance"]}  # fmt: skip
        return {**plan, "preview": route_preview(plan)}

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
    ) -> BuildWithExport:
        """Build du Mage par contexte (leveling, dungeon, raid, pvp-bg, pvp-world) à un niveau : talents et ordre
        d'apprentissage, choix du build (rotation, armure, cumuls d'Arcane Blast et de Hot Streak), raison de chaque
        talent (valeur marginale), alternative la plus proche avec écart apparié et intervalle de confiance
        (`alternative.tie` vrai : égalité statistique, présenter les deux options ; `alternative.export` : son lien
        Talents Forever, sans ordre), stabilité
        sur plusieurs graines, sensibilité aux sept hypothèses incertaines, respec (coût, gain, niveau conseillé),
        angles morts (borne haute ou non chiffré), certitude, hypothèses et provenance. Donjon et raid : scénarios
        provisoires. Au-delà du plafond de la bêta, le build n'est pas vérifiable en jeu avant la sortie.

        `level` absent : niveau maximal des données (question générale sans niveau, `inputs.level.origin` vaut
        `default`). `current` : build actuel {clé: rang} (conseil de respec ; à un niveau plus bas que `level`, le
        bloc `respec.projected` donne le chemin conseillé depuis ce build jusqu'à `level`) ; `respecs` : réinitialisations déjà faites ;
        `sp`, `crit` : fiche remplacée (puissance des sorts, critique en fraction) ; `preset` : rapide (défaut, le même que la CLI) ou
        complet ; `rules` : forever, ou seed (leveling seulement, parité) ; `talented_bonus` : points du bonus Legacy
        « Talented » (hypothèse).

        FA1 : bloc `export.talents_forever` : code et lien Talents Forever du build (ordre compris en leveling), commande
        `/tf import <code>` à relayer telle quelle, build populaire le plus proche ; statut `absent`, `bloque`,
        `format_non_pris_en_charge` ou `ordre_incoherent` avec sa raison, jamais un code deviné."""
        try:
            report = build_report(
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
            return attach_export(deps, report, talented_bonus)
        except ForeverError as err:
            return cast(BuildWithExport, _error_result(deps, err))

    return server
