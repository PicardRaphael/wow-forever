"""Appel fixé de chaque bouton de la fenêtre du jeu (sonde en jeu F du 2026-10-09). Relevé de la sonde : pour un même
bouton et un même contexte, la conversation « jeu » appelait les outils de façon différente d'une fois à l'autre
(bouton Talents : `forever_build` au niveau actuel, sans prochain point ; ailleurs au niveau suivant). Le pont calcule
donc lui-même, depuis le contexte vérifié (`context.resolve`), l'appel exact de chaque bouton et la façon d'en lire le
résultat, et les place dans le message : le modèle n'a plus qu'à appeler et rédiger. Le banc d'essai
(`tests/unit/test_bridge_bench.py`) exécute ces appels sans modèle sur les contextes réels. Aucune valeur de jeu ici :
le niveau suivant est le niveau du contexte plus un, borné par le niveau maximal des données."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from forever.bridge.buttons import BUTTONS
from forever.bridge.context import ContextData, Defect, Resolved, context_notes, resolve
from forever.bridge.record import Record


@dataclass(frozen=True)
class Call:
    tool: str  # nom de l'outil forever sans préfixe de serveur (forever_build, forever_lookup…)
    args: dict[str, Any]


@dataclass(frozen=True)
class Plan:
    button: str
    calls: tuple[Call, ...]
    read: tuple[str, ...]
    link: str | None = None  # lien publié : « projected » (chemin du joueur) ou None (lien du build)


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


def _next_point(r: Resolved, level_cap: int | None) -> tuple[Call, tuple[str, ...]] | None:
    """`forever_build` au niveau du prochain point depuis le build actuel, et la lecture de son résultat."""
    if r.level is None:
        return None
    at_cap = level_cap is not None and r.level >= level_cap
    level = r.level if at_cap else r.level + 1
    args: dict[str, Any] = {"context": "leveling", "level": level}
    if r.race:
        args["race"] = r.race
    if r.current:
        args["current"] = dict(sorted(r.current.items()))
    args["sensitivity"] = False
    read: tuple[str, ...]
    if at_cap:
        read = (
            (
                f"Niveau maximal des données ({level}) : aucun point de plus à placer ; donne le conseil de respec "
                "(`respec.verdict`) et le lien du build (`export.talents_forever`)."
            ),
        )
        return Call("forever_build", args), read
    read = (
        (
            "Prochain point, en premier : le talent du premier pas de `respec.projected.steps` et son niveau (un pas à un "
            f"niveau inférieur ou égal à {r.level} est un point à placer dès maintenant)."
        ),
        (
            "Égalité : si `next_step.decided_by` vaut `non_departage` ou `modelise`, dis que le choix est à égalité "
            "statistique (non départagé par le calcul) et nomme `next_step.runner_up` et les autres candidats dont "
            "l'écart (`next_step.candidates[].gap.significant`) n'est pas significatif."
        ),
        "Lien Talents Forever : celui de `respec.projected.export` (build actuel plus ce point), tel quel.",
        (
            "Build, en complément, après le prochain point : si `respec.versus_optimal.same` est vrai, dis que ton build "
            "actuel est la recommandation (départage final au Monte Carlo) et que tu le gardes ; si `respec.versus_optimal.tie` est vrai, dis que ton build actuel et le build optimal "
            "(`choices.leveling.rotation`) sont à égalité statistique et que tu gardes ton build (aucun gain mesurable) ; "
            "si `stability.stable` est faux, ajoute que le build optimal lui-même est instable (il change avec la "
            "graine). Si `respec.versus_optimal.current_better` est vrai, dis que ton build actuel est meilleur que le build "
            "retenu par l'optimiseur (écart mesuré, `respec.versus_optimal`) et que tu le gardes. Sinon, donne l'écart "
            "(`respec.versus_optimal`) et le conseil de respec (`respec.verdict`)."
        ),
    )
    return Call("forever_build", args), read


def button_plan(key: str, r: Resolved, level_cap: int | None) -> Plan | None:
    """Appels et lecture du bouton `key` pour ce contexte ; None si le contexte ne suffit pas (niveau inconnu, pas de
    cible joueur pour PvP, classe que le bouton ne sert pas)."""
    if r.class_name is None or r.level is None:
        return None
    if key == "talents":
        if r.class_token == "MAGE":
            point = _next_point(r, level_cap)
            if point is None:
                return None
            call, read = point
            return Plan(key, (call,), read, link="projected")
        calls = [Call("forever_lookup", {"kind": "tf_popular", "name": r.class_name})]
        if r.current:
            calls.append(
                Call(
                    "forever_lookup",
                    {"kind": "build_check", "name": r.class_name, "level": r.level, "talents": _talents_arg(r.current)},
                )
            )
        read = (
            (
                "Donne le build populaire de la même spécialisation que les talents actuels (arbre où ils sont placés), "
                "avec son lien et sa commande `/tf import` tels quels, sa date (`asOf`) et sa certitude."
            ),
        )
        return Plan(key, tuple(calls), read)
    if key == "leveling" and r.class_token == "MAGE":
        zones: dict[str, Any] = {"kind": "zones", "level": r.level}
        if r.faction in ("horde", "alliance"):
            zones["faction"] = r.faction
        zones["limit"] = 5
        point = _next_point(r, level_cap)
        calls = [Call("forever_lookup", zones)] + ([point[0]] if point else [])
        read = (
            (
                "Objectif : les trois premières zones ou donjons du résultat de zones, dans l'ordre rendu ; puis le "
                "prochain point de talent, lu comme pour le bouton Talents (`respec.projected.steps`) ; si "
                "`respec.versus_optimal.same` ou `respec.versus_optimal.tie` est vrai, tu gardes ton build (égalité statistique avec le build optimal, "
                "instable si `stability.stable` est faux)."
            ),
        )
        return Plan(key, tuple(calls), read)
    if key == "pets" and r.class_token == "HUNTER" and r.zone:
        call = Call("forever_lookup", {"kind": "pets", "zone": r.zone, "level": r.level})
        read = (
            (
                "Donne le rang le plus haut atteignable et la bête qui l'enseigne la plus proche (zone, coordonnées et "
                "date tels que rendus)."
            ),
        )
        return Plan(key, (call,), read)
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
                f"Fiche de {r.target_class} face à ton personnage : menaces (`threats`), tes réponses (`answers`), leurs "
                "réponses (`their_answers`), fenêtres (`windows`) ; cite ce qui manque (`missing`)."
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
    plan = button_plan(key, resolved, data.level_cap) if key else None
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
    plan = button_plan(key, resolve(data, record.context), data.level_cap)
    return message_text(record, talents=prepared.notes, guide=prepared.guide), plan
