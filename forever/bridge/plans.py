"""Appel fixé de chaque bouton de la fenêtre du jeu (sonde en jeu F du 2026-10-09). Relevé de la sonde : pour un même
bouton et un même contexte, la conversation « jeu » appelait les outils de façon différente d'une fois à l'autre
(bouton Talents : un outil au niveau actuel, ailleurs au niveau suivant). Le pont calcule
donc lui-même, depuis le contexte vérifié (`context.resolve`), l'appel exact de chaque bouton et la façon d'en lire le
résultat, et les place dans le message : le modèle n'a plus qu'à appeler et rédiger. Le banc d'essai
(`tests/unit/test_bridge_bench.py`) exécute ces appels sans modèle sur les contextes réels. Aucune valeur de jeu ici :
la tranche de la route est bornée par le niveau maximal des données."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from forever.bridge.buttons import BUTTONS
from forever.bridge.choices import ROUTE_CHOICES, route_options
from forever.bridge.context import ContextData, Defect, Resolved, context_notes, resolve
from forever.bridge.record import Record


@dataclass(frozen=True)
class Call:
    tool: str  # nom de l'outil forever sans préfixe de serveur (forever_lookup, forever_route…)
    args: dict[str, Any]


@dataclass(frozen=True)
class Plan:
    button: str
    calls: tuple[Call, ...]
    read: tuple[str, ...]
    link: str | None = None  # lien publié : « closest » (build populaire le plus proche) ou None


@dataclass(frozen=True)
class Prepared:
    """Ce que le pont ajoute au message d'un joueur : notes du contexte relié, consigne du bouton, défauts à
    journaliser, lien à publier."""

    notes: str | None
    guide: str | None
    defects: list[Defect] = field(default_factory=list)
    link: str | None = None


def _talents_arg(current: Mapping[str, int]) -> str:
    return ",".join(f"{k}={v}" for k, v in sorted(current.items()))


def _objectives_call(r: Resolved) -> Call:
    """Objectifs de leveling de T04d (toutes les classes) : XP par heure par zone et par donjon."""
    args: dict[str, Any] = {"kind": "objectives", "level": r.level, "class_name": r.class_name}
    if r.faction in ("horde", "alliance"):
        args["faction"] = r.faction
    if r.race:
        args["race"] = r.race
    xp = r.xp
    if xp is not None:  # T04f : état du jeu transmis tel quel, jamais deviné
        if xp.rested is not None:
            args["rested"] = xp.rested
        if xp.auras:
            args["auras"] = ",".join(
                f"{a.spell_id}:{a.stacks}:{'' if a.remaining_s is None else round(a.remaining_s)}" for a in xp.auras
            )
        if xp.items:
            args["has_sleeping_bag"] = any(count > 0 for count in xp.items.values())
    return Call("forever_sim_leveling", args)


OBJECTIVES_READ = (
    "Objectifs (résultat de forever_sim_leveling, kind objectives) : rends `advice` tel quel, puis le meilleur "
    "objectif (`best` : nom, XP, minutes, XP par heure) et, s'il y a un donjon, son premier passage avec ses quêtes "
    "et ses passages suivants ; puis `dungeon_advice` tel quel (donjon à faire maintenant ou à viser, avec son "
    "niveau de placement `placement.level` : niveau où son premier passage rapporte la plus grande part de niveau "
    "par heure) et la durée d'un passage (`run.source` : measured relevé, formula estimée) ; dis d'où vient le temps par monstre (`kill_time.source` : engine calculé, measured "
    "mesuré sur tes relevés, estimated estimé) et que les temps de trajet et de quête sont des hypothèses. "
    "Bonus d'XP : les bonus actifs (`bonuses.active` : nom, cumuls, temps restant `remaining_s`), puis `bonus_advice` "
    "tel quel ; si `sleeping_bag_chain` est rendu, sa phrase `sentence` telle quelle (étape suivante, lieu et position) "
    "et ses écarts entre sources (`discrepancies`) en une ligne."
)


def _leveling_plan(r: Resolved, level_cap: int | None) -> Plan:
    """Bouton Leveling, toutes les classes (décisions 242 et 243, T04d) : zones, quêtes et donjon, objectifs de
    leveling (XP par heure par zone et par donjon), le build populaire de la classe et son lien, et la mention de ce
    qui n'est pas calculé (prochain talent ; RB1, décision 299 : le Mage suit le même chemin)."""
    zones: dict[str, Any] = {"kind": "zones", "level": r.level}
    if r.faction in ("horde", "alliance"):
        zones["faction"] = r.faction
    zones["limit"] = 5
    if r.class_name:
        zones["class_name"] = r.class_name  # classe du personnage connecté (plus le Mage par défaut)
    head = (
        "Zones et quêtes : les trois premières zones du résultat de zones, dans l'ordre rendu, avec leur nombre de "
        "quêtes utiles ; prochain donjon : le premier donjon rendu (`dungeons`)."
    )
    popular: dict[str, Any] = {"kind": "tf_popular", "name": r.class_name}
    if r.current:
        popular["current"] = ",".join(f"{k}={v}" for k, v in r.current.items())
    read = (
        head,
        (
            "Build populaire de ta classe : `closest` s'il est rendu (le plus proche de tes talents), sinon le build le "
            "plus joué ; son lien et sa commande `/tf import` tels quels, sa date (`asOf`)."
        ),
        OBJECTIVES_READ,
        (
            "Dis clairement ce qui est calculé et ce qui ne l'est pas encore : zones, quêtes, donjon et XP par heure "
            "viennent des données et de tes relevés ; le build est un choix de joueurs ; le prochain talent n'est pas "
            "calculé."
        ),
    )
    calls = (Call("forever_lookup", zones), Call("forever_lookup", popular), _objectives_call(r))
    return Plan("leveling", calls, read)


# Plan « Sources d'abord », étape b : guide de Forever Companion, toutes les classes (RB1 : le Mage aussi).
GUIDE_READ = (
    "Guide de Forever Companion (`class_guide`), pour la spécialisation du build retenu ci-dessus : son build `pick` "
    "(nom ; légal à son niveau ou non) et les builds écartés avec leur raison (`set_aside`), puis la rotation telle "
    "quelle (`rotation.single`, puis `rotation.aoe`), en disant qu'elle vient de Forever Companion, qu'elle est écrite "
    "pour le niveau 30 et qu'aucun ordre de prise n'est calculé ; si `freshness.status` n'est pas « à "
    "jour », dis « calcul en cours de mise à jour » avec sa raison. Forever Companion absent : ne dis rien de plus."
)


NAOWH_POPULAR = (
    "Code Naowh du build (`naowh`) tel quel, à coller dans Naowh Forever, Training, Builds, Import ; dis que son ordre "
    "de prise est généré (palier, prérequis), pas un ordre de leveling optimisé."
)


def button_plan(
    key: str,
    r: Resolved,
    level_cap: int | None,
    *,
    first_talent_level: int | None = None,
    options: Mapping[str, Any] | None = None,
) -> Plan | None:
    """Appels et lecture du bouton `key` pour ce contexte ; None si le contexte ne suffit pas (niveau inconnu, pas de
    cible joueur pour PvP, classe que le bouton ne sert pas)."""
    if r.class_name is None or r.level is None:
        return None
    if key == "talents":
        guide = Call("forever_lookup", {"kind": "class_guide", "name": r.class_name, "level": r.level})
        if not r.current:
            calls = [Call("forever_lookup", {"kind": "tf_popular", "name": r.class_name}), guide]
            read = (
                (
                    "aucun talent placé : build le plus joué de la classe (rang 1) ; donne son lien et sa commande "
                    "`/tf import` tels quels, sa date (`asOf`) et sa certitude ; c'est le plan complet à suivre dès le "
                    "premier point."
                ),
                NAOWH_POPULAR,
                GUIDE_READ,
            )
            return Plan(key, tuple(calls), read)
        current = ",".join(f"{k}={v}" for k, v in r.current.items())
        calls = [
            Call("forever_lookup", {"kind": "tf_popular", "name": r.class_name, "current": current}),
            Call("forever_lookup", {"kind": "build_check", "name": r.class_name, "level": r.level, "talents": current}),
            guide,
        ]
        read = (
            (
                "Donne `closest` tel quel (spécialisation, lien, commande `/tf import`, points absents "
                "`missing_points`, écarts `differences`), avec sa date (`asOf`) et sa certitude ; n'en choisis pas un "
                "autre."
            ),
            GUIDE_READ,
        )
        return Plan(key, tuple(calls), read, link="closest")
    if key == "leveling":
        return _leveling_plan(r, level_cap)
    if key == "pets" and r.class_token == "HUNTER" and r.zone:
        call = Call("forever_lookup", {"kind": "pets", "zone": r.zone, "level": r.level})
        read = (
            (
                "Bêtes apprivoisables maintenant (niveau inférieur ou égal au tien), la zone actuelle d'abord puis les "
                "zones voisines dans l'ordre rendu : pour chacune, son nom, sa famille, son niveau, les capacités et les "
                "rangs qu'elle enseigne et ses positions (coordonnées et date, telles que rendues ; `positions_known` "
                "faux : dis que sa position n'est pas connue) ; rangs enseignés inconnus : les capacités de sa famille "
                "(`family_abilities`) ; cinq bêtes au plus, celles qui enseignent les rangs les plus hauts d'abord. "
                "Familles, capacités, rangs et niveaux requis viennent des données du client du jeu installé, qui priment "
                "sur l'addon."
            ),
            (
                "Rang marqué au-dessus du niveau de sa bête (`above_beast_level`) : donne le rang corrigé supposé "
                "(`expected_rank`) en disant qu'un correctif de Blizzard l'a abaissé, à vérifier en jeu avec Beast Lore ; "
                "ne parle d'aucun correctif pour les autres rangs."
            ),
            (
                "Si le résultat porte `missing` : dis en clair la source qui manque, où elle est attendue et quoi faire "
                "(`missing.action`), puis donne ce que les données du jeu savent (`client_only` : rang le plus haut "
                "atteignable de chaque capacité et familles qui l'apprennent). Jamais « je n'ai pas de réponse » quand "
                "des bêtes ou des données sont rendues."
            ),
        )
        return Plan(key, (call,), read)
    if key == "route" and r.faction:
        # RX1 : route calculée aussitôt avec les réponses par défaut des questions (choices.ROUTE_CHOICES), ajustée
        # ensuite à chaque « Réponse : … » du joueur
        span = int(ROUTE_CHOICES[0].default or ROUTE_CHOICES[0].options[0].key)
        opts = options or {}
        start, end = opts.get("lv") or (r.level, r.level + span)  # CJ1, bloc 6a : niveaux de l'assistant
        end = min(end, level_cap) if level_cap else end
        if end <= start:
            return None
        route_args: dict[str, Any] = {
            "action": "plan",
            "class_name": r.class_name,
            "faction": r.faction.lower(),
            "start_level": start,
            "end_level": end,
        }
        if "dj" in opts:
            route_args["dungeons"] = opts["dj"]
        if "cq" in opts:
            route_args["class_quests"] = opts["cq"]
        if r.race:  # CJ1 : masques de race et zone de départ de la race
            route_args["race"] = r.race
        if r.name:  # CJ1 : quêtes déjà faites par ce personnage (profil)
            route_args["character"] = r.name
        if start == r.level and r.map is not None and r.x is not None and r.y is not None:  # CJ1 : position réelle
            route_args.update(start_map=r.map, start_x=r.x, start_y=r.y)
        read = (
            (
                "Résumé de la route (réponse compacte de forever_route) : heures, XP par heure, zones dans l'ordre "
                "(`zones`), donjons et leur niveau, quêtes de classe (`class_quests`), récompenses notables, base "
                "utilisée (`basis`), certitude ; puis les cinq premiers arrêts (`first_stops` : `text`, zone et "
                "position) ; une ligne pour les avertissements (`warnings`) s'il y en a. Jamais `detail=True` ici : "
                "la route complète reste sur le disque pour la livraison."
            ),
            (
                "La question suivante (nombre de niveaux) et le bouton « Valider et livrer » apparaissent sous ta "
                "réponse, posés par le pont : ne les répète pas et ne parle pas de « À valider ». Donjons avec leurs "
                "quêtes et quêtes de classe sont inclus par défaut. À chaque « Réponse : … », rappelle forever_route "
                "avec l'option changée et redonne l'aperçu (il remplace le précédent) ; dis la base de la route "
                "(`basis.verdict`) en une ligne."
            ),
        )
        return Plan(key, (Call("forever_route", route_args),), read)
    if key == "pvp" and r.target_class:
        args: dict[str, Any] = {"kind": "pvp", "name": r.class_name, "level": r.level}
        if r.race:
            args["race"] = r.race
        if r.current:
            args["talents"] = _talents_arg(r.current)
        args["opponent"] = r.target_class
        if r.target_level is not None:
            args["opponent_level"] = r.target_level
        read = (
            (
                f"{r.target_class} face à ton personnage (bloc 6b, décision 281), en 1200 caractères au plus, mise en "
                "forme comprise, sans titre. Commence par « Comment jouer contre lui » : trois à cinq consignes "
                "concrètes, dans l'ordre du combat (ouverture, ses menaces, tes réponses, la fenêtre à saisir), avec "
                "tes sorts, tirées seulement de ses menaces (`threats`), de tes réponses (`answers`), de ses réponses "
                "(`their_answers`) et des fenêtres (`windows`) : aucune règle inventée. Puis le détail, en mots de "
                "joueur : chaque sort nommé avec ce qu'il fait en quelques mots ; « rendement décroissant » expliqué "
                "en une phrase la première fois. Une seule ligne pour ce qui manque (`missing`), s'il manque quelque "
                "chose ; la certitude de la fiche en fin de réponse. Noms des sorts : ni rang, ni durée, ni recharge."
            ),
        )
        return Plan(key, (Call("forever_lookup", args),), read)
    return None


def plan_text(plan: Plan) -> str:
    """Consigne du bouton ajoutée au message : appels exacts, puis lecture."""
    lines = [f"Consigne du bouton « {plan.button} » : appelle exactement, dans cet ordre :"]
    lines += [f"- {c.tool} {json.dumps(c.args, ensure_ascii=False)}" for c in plan.calls]
    lines.append("Puis :")
    lines += [f"- {r}" for r in plan.read]
    return "\n".join(lines)


def button_key(record: Record) -> str | None:
    return next((f.split("=", 1)[1] for f in record.flags if f.startswith("b=")), None)


def prepare_record(data: ContextData, record: Record) -> Prepared:
    """Contexte du message relié à nos données, consigne du bouton s'il y en a un."""
    resolved = resolve(data, record.context)
    key = button_key(record)
    plan = (
        button_plan(
            key,
            resolved,
            data.level_cap,
            first_talent_level=data.talent_first_level,
            options=route_options(record.flags),
        )
        if key
        else None
    )
    return Prepared(
        notes=context_notes(resolved) or None,
        guide=plan_text(plan) if plan else None,
        defects=list(resolved.defects),
        link=plan.link if plan else None,
    )


def button_message(data: ContextData, key: str, context: Mapping[str, str]) -> tuple[str, Plan | None]:
    """Message exact que le pont envoie pour le bouton `key` dans ce contexte (cas d'évaluation), et son appel."""
    from forever.bridge.prompt import message_text

    button = next(b for b in BUTTONS if b.key == key)
    record = Record("eval", 1, frozenset({f"b={key}"}), dict(context), button.question_for(context.get("class", "")))
    prepared = prepare_record(data, record)
    plan = button_plan(key, resolve(data, record.context), data.level_cap, first_talent_level=data.talent_first_level)
    return message_text(record, talents=prepared.notes, guide=prepared.guide), plan
