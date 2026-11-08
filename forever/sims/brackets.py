"""Dégâts par tranche de niveaux (SIM2, décision 305), calculés par wowsims/forever compilé avec nos correctifs
(niveau réglable, rang appris au niveau) : aucun calcul de jeu ici, seulement la requête de chaque tranche.

Pour chaque tranche (un niveau représentatif, ou un niveau donné), un combat au niveau L :
- talents : le parcours dans l'ordre (étapes « niveau, clé, rang » de `forever_lookup(kind="leveling_plan")`) tronqué
  au niveau L, contrôlé légal au niveau L sur les arbres du client (un build illégal n'est pas simulé : erreur dans
  sa ligne), converti vers la chaîne de wowsims par identifiant de sort ;
- équipement : choix par emplacement (GearQuest, `forever_gear(action="leveling")`) placés dans l'ordre `ItemSlot` de
  wowsims, ou nu ;
- solo : aucun buff, affaiblissement ni consommable ; cible : celle de la rencontre de référence, au niveau L ;
- rotation et options de la spécialisation : celles du préréglage ; un sort pas encore appris est retiré de la
  rotation par le correctif des rangs."""

from __future__ import annotations

import copy
import dataclasses
import json
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.config import Deps
from forever.errors import ForeverError, InvalidArgumentError
from forever.pipeline import gitops
from forever.pipeline.wowsims_build import pinned, wowsims_dir
from forever.provenance import local_provenance
from forever.sims import wowsims
from forever.sims.wowsims import Preset

# Tranches demandées par l'utilisateur (2026-11-08) et niveau représentatif de chacune (réglage de l'outil, décision 305).
BRACKETS: dict[str, int] = {"10-19": 15, "20-29": 25, "30-39": 35, "40-49": 45, "50-59": 55, "60": 60}
# Ordre des emplacements de `EquipmentSpec.items` (enum `ItemSlot` de `proto/common.proto` de wowsims).
SLOT_NAMES: tuple[str, ...] = (
    "Head", "Neck", "Shoulder", "Back", "Chest", "Wrist", "Hands", "Waist", "Legs", "Feet",
    "Finger1", "Finger2", "Trinket1", "Trinket2", "MainHand", "OffHand", "Ranged",
)  # fmt: skip
# Emplacement de GearQuest -> emplacements de wowsims possibles, dans l'ordre de remplissage.
_SLOT_ALIASES: dict[str, tuple[str, ...]] = {
    "Finger": ("Finger1", "Finger2"),
    "Trinket": ("Trinket1", "Trinket2"),
    "SecondaryHand": ("OffHand",),
    "OffHand": ("OffHand",),
}
_SINGLE = re.compile(r"^\d+$")

NOTES = (
    (
        "solo : aucun buff, affaiblissement ni consommable ; cible de la rencontre de référence de wowsims mise au "
        "niveau du personnage (armure et PV de cette cible, durée fixe du combat : pas de temps pour tuer un monstre "
        "normal)"
    ),
    (
        "attributs de base (Force, Agilité, Endurance, Intelligence, Esprit), mana de base et critique par point "
        "d'Intelligence ou d'Agilité : dits ligne par ligne (base_stats) ; sans relevé ForeverLogger au niveau ou en "
        "dessous, attributs du niveau 60 (dégâts surestimés) ; PV de base du niveau 60 (sans effet sur les dégâts)"
    ),
)


def parse_brackets(text: str | None) -> list[tuple[str, int]]:
    """« all » ou rien : les six tranches ; sinon des tranches (« 20-29 ») ou des niveaux (« 22 ») séparés par des
    virgules."""
    if text is None or text.strip().lower() in ("", "all"):
        return list(BRACKETS.items())
    out: list[tuple[str, int]] = []
    for item in (part.strip() for part in text.split(",")):
        if item in BRACKETS:
            out.append((item, BRACKETS[item]))
        elif _SINGLE.match(item) and wowsims.MIN_LEVEL <= int(item) <= wowsims.MAX_LEVEL:
            out.append((item, int(item)))
        else:
            raise InvalidArgumentError(
                f"Tranche illisible : « {item} ».",
                f"donner des tranches ({', '.join(BRACKETS)}) ou des niveaux de 1 à 60, séparés par des virgules",
            )
    return out


def talents_at(steps: Sequence[Mapping[str, Any]], level: int) -> dict[str, int]:
    """Talents pris jusqu'au niveau `level` inclus : rang le plus haut atteint par clé."""
    out: dict[str, int] = {}
    for step in steps:
        if step.get("key") and int(step["level"]) <= level:
            out[str(step["key"])] = max(out.get(str(step["key"]), 0), int(step["rank"]))
    return out


def equipment_from_picks(picks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Choix par emplacement -> `EquipmentSpec` de wowsims (17 emplacements, vides s'il n'y a rien)."""
    items: list[dict[str, Any]] = [{} for _ in SLOT_NAMES]
    for pick in picks:
        slot = str(pick.get("slot"))
        targets = _SLOT_ALIASES.get(slot, (slot,) if slot in SLOT_NAMES else ())
        if not targets:
            raise InvalidArgumentError(f"Emplacement inconnu de wowsims : « {slot} ».", "vérifier les choix d'objets")
        free = next((t for t in targets if not items[SLOT_NAMES.index(t)]), None)
        if free is not None:
            items[SLOT_NAMES.index(free)] = {"id": int(pick["item"])}
    return {"items": items}


DATABASE = ("assets", "database")  # base d'objets de wowsims (db.json et leftover_db.json, chargées par son binaire)


def known_items(clone: Path) -> set[int] | None:
    """Objets de la base de wowsims (les deux fichiers que son binaire charge) ; None si le clone n'en a pas."""
    folder = clone.joinpath(*DATABASE)
    files = [folder / name for name in ("db.json", "leftover_db.json") if (folder / name).is_file()]
    if not files:
        return None
    key = tuple((str(f), f.stat().st_mtime_ns) for f in files)
    if key not in _KNOWN:
        _KNOWN.clear()
        _KNOWN[key] = {int(i["id"]) for f in files for i in json.loads(f.read_text(encoding="utf-8"))["items"]}
    return _KNOWN[key]


_KNOWN: dict[tuple[tuple[str, int], ...], set[int]] = {}


def solo_preset(preset: Preset, *, talents: str, equipment: dict[str, Any]) -> Preset:
    """Préréglage joué seul : talents et équipement donnés, sans buff, affaiblissement ni consommable."""
    return dataclasses.replace(preset, talents=talents, equipment=equipment, raid_buffs={}, party_buffs={},
                               individual_buffs={}, debuffs={}, consumables={})  # fmt: skip


def encounter_at(encounter: dict[str, Any] | None, level: int, *, crush: bool = False) -> dict[str, Any]:
    """Copie de la rencontre dont chaque cible est au niveau `level` (coups écrasants seulement si `crush`)."""
    out = copy.deepcopy(encounter) if encounter else {"targets": [{}]}
    for target in out.get("targets") or []:
        target["level"] = level
        target["canCrush"] = crush
    return out


CONDITIONS = ("solo", "group", "raid")  # leveling seul (défaut), groupe de donjon, raid
CONDITION_NOTES = {
    "solo": "conditions solo : aucun buff, affaiblissement ni consommable ; cible du niveau du personnage",
    "group": ("conditions groupe : buffs et affaiblissements du préréglage de wowsims (rangs au niveau), aucun "
              "consommable ; cible du niveau du personnage"),
    "raid": ("conditions raid : buffs, affaiblissements et consommables du préréglage de wowsims (consommables du "
             "préréglage, même sous leur niveau requis) ; boss au-dessus du personnage, écart de la rencontre de "
             "référence de wowsims, coups écrasants permis"),
}  # fmt: skip


def conditioned(preset: Preset, conditions: str, *, talents: str, equipment: dict[str, Any]) -> Preset:
    """Préréglage aux conditions voulues (voir CONDITIONS) avec les talents et l'équipement donnés."""
    if conditions == "solo":
        return solo_preset(preset, talents=talents, equipment=equipment)
    if conditions == "group":
        return dataclasses.replace(preset, talents=talents, equipment=equipment, consumables={})
    return dataclasses.replace(preset, talents=talents, equipment=equipment)


def target_level(encounter: dict[str, Any] | None, level: int, conditions: str) -> int:
    """Niveau de la cible : celui du personnage, ou en raid celui du boss de la rencontre de référence de wowsims
    rapporté au personnage (même écart au niveau maximal, jamais au-dessus du boss de référence)."""
    if conditions != "raid":
        return level
    ref = max((int(t.get("level") or 0) for t in (encounter or {}).get("targets") or []), default=level)
    return min(level + max(0, ref - wowsims.MAX_LEVEL), ref)


def _legality(deps: Deps, class_name: str) -> tuple[Any, Callable[[dict[str, int], int], list[str]]]:
    from forever.engine.talents import check_class_build
    from forever.sims.engines import ClassTalents

    conv = ClassTalents(deps, class_name)

    def errors(keys: dict[str, int], level: int) -> list[str]:
        return list(check_class_build(conv.knowledge, conv.gd.constants.talents, keys, level))

    return conv, errors


def run_brackets(
    deps: Deps,
    *,
    preset: str,
    race: str | None,
    brackets: str | None,
    steps: Sequence[Mapping[str, Any]],
    picks_at: Callable[[int], Sequence[Mapping[str, Any]]] | None,
    iterations: int | None = None,
    runner: gitops.Runner | None = None,
    anchors: Sequence[Mapping[str, Any]] | None = None,
    stats: Sequence[str] | None = None,
    reference: str | None = None,
    conditions: str = "solo",
) -> dict[str, Any]:
    """Un combat par tranche (voir le module) ; une ligne par tranche : niveau, talents, équipement, dégâts par
    seconde et écart type, source (commit, correctifs, niveau), ou l'erreur de la tranche."""
    from forever.sims.engines import class_of

    wanted = parse_brackets(brackets)
    if conditions not in CONDITIONS:
        raise InvalidArgumentError(f"conditions inconnues : « {conditions} ».", "choisir " + ", ".join(CONDITIONS))
    if not race:
        raise InvalidArgumentError("Race manquante.", "demander la race au joueur (question ou profil), puis race=…")
    pin = pinned(deps.cache_dir)
    if pin is None:
        raise wowsims.WowsimsError("wowsims/forever n'est pas encore compilé : lancer `uv run forever sims update`.")
    presets = wowsims.read_presets(wowsims_dir(deps.cache_dir) / "forever")
    chosen = next((p for p in presets if p.key == preset), None)
    if chosen is None:
        raise InvalidArgumentError(f"Préréglage inconnu : « {preset} ».", "voir forever_simulate(action='presets')")
    from forever.sims import base_stats as bs

    conv, errors = _legality(deps, class_of(chosen))
    with_patch = bs.PATCH in ((pin.get("patches") or {}).get("files") or [])
    items_path, items_ids, items_note = (
        extra_items(deps.cache_dir)
        if ITEMS_PATCH in ((pin.get("patches") or {}).get("files") or [])
        else (None, set(), None)
    )
    encounter = wowsims.reference_encounter(presets)
    race_token = wowsims.race_enum(race)
    rows: list[dict[str, Any]] = []
    for label, level in wanted:
        keys = talents_at(steps, level)
        row: dict[str, Any] = {"bracket": label, "level": level, "talents": keys}
        problems = errors(keys, level)
        if problems:
            err = InvalidArgumentError(f"Talents illégaux au niveau {level} : {' ; '.join(problems)}.",
                                       "corriger le parcours de talents")  # fmt: skip
            rows.append({**row, "error": {"code": err.code, "message": err.message, "action": err.action}})
            continue
        try:
            picks = list(picks_at(level)) if picks_at else []
            known = known_items(wowsims_dir(deps.cache_dir) / "forever")
            if known is not None and items_ids:
                known = known | items_ids
                taken = sorted({int(p["item"]) for p in picks if int(p["item"]) in items_ids})
                if taken:
                    row["extra_items"] = taken
            unknown = sorted({int(p["item"]) for p in picks if known is not None and int(p["item"]) not in known})
            if unknown:  # objet absent de la base de wowsims : écarté et nommé, jamais remplacé (dégâts sous-estimés)
                row["unknown_items"] = unknown
                picks = [p for p in picks if int(p["item"]) not in unknown]
            case = conditioned(chosen, conditions, talents=conv.wowsims.encode(keys),
                               equipment=equipment_from_picks(picks))  # fmt: skip
            fight = encounter_at(encounter, target_level(encounter, level, conditions), crush=conditions == "raid")
            request = wowsims.request_for(case, race=race_token, encounter=fight,
                                          iterations=iterations or wowsims.DEFAULT_ITERATIONS)  # fmt: skip
            if with_patch:
                doc = bs.base_stats_doc(chosen.class_token, bs.client_scaling(deps, class_of(chosen), level),
                                        anchors or [])  # fmt: skip
                row["base_stats"] = "mana de base et critique par point du client au niveau ; " + bs.anchor_note(
                    anchors or [], level
                )
            else:
                doc = None
                row["base_stats"] = (f"statistiques de base du niveau 60 : binaire sans le correctif {bs.PATCH} "
                                     "(lancer `forever sims update`)")  # fmt: skip
            out = wowsims.run_sim(deps.cache_dir, request, runner=runner, level=level, base_stats=doc,
                                  items=items_path)  # fmt: skip
            if stats:
                try:
                    w = wowsims.stat_weights(
                        deps.cache_dir, case, list(stats), reference=reference or stats[0], race=race_token,
                        encounter=fight, iterations=iterations or wowsims.DEFAULT_ITERATIONS,
                        runner=runner, level=level, base_stats=doc, items=items_path,
                    )  # fmt: skip
                    row["weights"] = {k: w[k] for k in ("per_point", "normalised", "reference", "delta", "base_dps")}
                except ForeverError as err:
                    row["weights_error"] = {"code": err.code, "message": err.message, "action": err.action}
        except ForeverError as err:
            rows.append({**row, "error": {"code": err.code, "message": err.message, "action": err.action}})
            continue
        rows.append({**row, "talents_string": case.talents, "equipment": [p["item"] for p in picks] if picks else "nu",
                     **out})  # fmt: skip
    notes = [wowsims.source_note(pin), CONDITION_NOTES[conditions], *NOTES[1:], *([items_note] if items_note else [])]
    if stats:
        notes.append(f"poids des statistiques par tranche : tirages appariés (même graine, +{wowsims.STAT_DELTA:g} "
                     "points par statistique) dans les conditions de la tranche ; gain de dégâts par seconde par point")  # fmt: skip
    if any(r.get("unknown_items") for r in rows):
        notes.append("objets choisis absents de la base de wowsims (unknown_items) : emplacement laissé vide, dégâts "
                     "sous-estimés")  # fmt: skip
    return {"preset": chosen.key, "race": race_token, "conditions": conditions, "rows": rows,
            "provenance": local_provenance(deps, certainty="suppose", assumptions=notes)}  # fmt: skip


# parcours de talents : plan de leveling (Polestar et Talents Forever), build populaire de Talents Forever de l'arbre du
# préréglage dans un ordre légal généré, ou aucun talent ; « auto » : le plan, sinon le build populaire
PATHS = ("auto", "plan", "popular", "none")
GEARS = ("gearquest", "none")  # équipement : choix de GearQuest au niveau L, ou nu


def _plan_steps(deps: Deps, class_name: str, preset: Preset, spec: str | None) -> tuple[list[dict[str, Any]], str]:
    """Étapes du plan de leveling de la spécialisation : `spec` (nom anglais), sinon celle dont l'arbre est le plus
    pris par les talents du préréglage."""
    from forever.leveling_plan import leveling_plan
    from forever.sims.engines import ClassTalents

    plan = leveling_plan(deps, class_name, spec)
    specs = plan.get("specs") or []
    if spec is None and len(specs) > 1:
        conv = ClassTalents(deps, class_name)
        tree = conv.lead_tree(conv.wowsims.decode(preset.talents))
        specs = [s for s in specs if s.get("tree") == tree] or specs
    if not specs:
        raise InvalidArgumentError(f"Aucun plan de leveling pour {class_name}.", "donner spec=<nom anglais>")
    chosen = specs[0]
    return list(chosen.get("steps") or []), str(chosen.get("spec") or chosen.get("key"))


def _popular_steps(deps: Deps, class_name: str, preset: Preset) -> tuple[list[dict[str, Any]], str]:
    """Build populaire de Talents Forever le plus joué, légal, de l'arbre le plus pris par le préréglage, dans un
    ordre de prise légal généré (`legal_order` : pas un ordre optimisé) ; un point par niveau dès le premier."""
    from forever.engine.talents import legal_order
    from forever.sims.engines import ClassTalents
    from forever.talents_forever import load_addon, popular_builds

    addon = load_addon(deps)
    if addon is None or not addon.popular:
        raise InvalidArgumentError("Builds populaires de Talents Forever introuvables.",
                                   "installer l'addon Talents Forever, ou path=none")  # fmt: skip
    conv = ClassTalents(deps, class_name)
    tree = conv.lead_tree(conv.wowsims.decode(preset.talents))
    top = (popular_builds(addon, deps, class_name)["classes"].get(class_name) or {}).get("top") or []
    chosen = next((b for b in top if b.get("legality") == "légal" and b.get("tree") == tree), None)
    if chosen is None:
        raise InvalidArgumentError(f"Aucun build populaire légal de l'arbre {tree} pour {class_name}.",
                                   "donner path=plan ou path=none")  # fmt: skip
    rules = conv.gd.constants.talents
    order = legal_order(conv.knowledge, rules, dict(chosen["talents"]))
    steps, ranks = [], {}  # type: ignore[var-annotated]
    for i, key in enumerate(order):
        ranks[key] = ranks.get(key, 0) + 1
        steps.append({"level": rules.first_level + i, "key": key, "rank": ranks[key]})
    return steps, f"build populaire n° {chosen.get('rank')} {tree} de Talents Forever ({chosen.get('link')})"


def run_from_sources(
    deps: Deps,
    *,
    preset: str,
    race: str | None,
    brackets: str | None,
    path: str = "auto",
    gear: str = "gearquest",
    spec: str | None = None,
    gear_spec: str | None = None,
    iterations: int | None = None,
    stats: Sequence[str] | None = None,
    reference: str | None = None,
    conditions: str = "solo",
) -> dict[str, Any]:
    """`run_brackets` avec les sources installées : parcours `path` (plan de leveling ou aucun) et équipement `gear`
    (choix de GearQuest au niveau de chaque tranche, ou nu)."""
    from forever.sims.engines import class_of

    if path not in PATHS:
        raise InvalidArgumentError(f"Parcours inconnu : « {path} ».", "choisir " + ", ".join(PATHS))
    if gear not in GEARS:
        raise InvalidArgumentError(f"Équipement inconnu : « {gear} ».", "choisir " + ", ".join(GEARS))
    presets = wowsims.read_presets(wowsims_dir(deps.cache_dir) / "forever")
    chosen = next((p for p in presets if p.key == preset), None)
    if chosen is None:
        raise InvalidArgumentError(f"Préréglage inconnu : « {preset} ».", "voir forever_simulate(action='presets')")
    class_name = class_of(chosen)
    steps: list[dict[str, Any]] = []
    notes: list[str] = []
    if path in ("auto", "plan"):
        try:
            steps, plan_spec = _plan_steps(deps, class_name, chosen, spec)
            notes.append(
                f"talents : plan de leveling {plan_spec} (forever_lookup kind=leveling_plan) tronqué au niveau"
            )
        except InvalidArgumentError as err:
            if path == "plan":
                raise
            notes.append(f"plan de leveling indisponible ({err.message}) : build populaire à la place")
            path = "popular"
    if path == "popular":
        steps, label = _popular_steps(deps, class_name, chosen)
        notes.append(f"talents : {label}, ordre de prise légal généré (pas un ordre optimisé), tronqué au niveau")
    elif path == "none":
        notes.append("talents : aucun")
    picks_at: Callable[[int], Sequence[Mapping[str, Any]]] | None = None
    if gear == "gearquest":
        from forever.gear import gear_report
        from forever.sims.engines import ClassTalents

        if gear_spec is None:
            conv = ClassTalents(deps, class_name)
            gear_spec = gearquest_spec(chosen.key, conv.lead_tree(conv.wowsims.decode(chosen.talents)))

        def picks_at(level: int) -> Sequence[Mapping[str, Any]]:
            doc = gear_report(deps, "leveling", class_name=class_name, level=level, race=race or "Orc",
                              spec=gear_spec)  # fmt: skip
            return list(doc.get("picks") or [])

        notes.append(f"équipement : choix de GearQuest ({gear_spec}) au niveau de chaque tranche "
                     "(forever_gear action=leveling)")  # fmt: skip
    else:
        notes.append("équipement : aucun (nu)")
    from forever.sims.base_stats import logger_anchors

    anchors, files = logger_anchors(deps, chosen.class_token)
    notes.append(f"relevés d'attributs de ForeverLogger : {len(anchors)} point(s) de la classe dans {len(files)} "
                 "fichier(s) de SavedVariables (connexion et montée de niveau, ForeverLogger 0.8.0)")  # fmt: skip
    out = run_brackets(deps, preset=preset, race=race, brackets=brackets, steps=steps, picks_at=picks_at,
                       iterations=iterations, anchors=anchors, stats=stats, reference=reference,
                       conditions=conditions)  # fmt: skip
    out["provenance"]["assumptions"] = [*out["provenance"]["assumptions"], *notes]
    return out


ITEMS_PATCH = "0004-items.patch"
EXTRA_ITEMS = "extra_items.json"  # fichier des objets ajoutés, dans le dossier de wowsims du cache


def extra_items(cache_dir: Path) -> tuple[Path | None, set[int], str | None]:
    """Objets absents de la base de wowsims pris dans la base du fork Go épinglé de MythicSim (simulateur de la
    communauté pour Forever, MIT) : (fichier pour `--forever-items=`, identifiants, note de provenance) ; rien sans
    MythicSim copié. Un objet connu de wowsims n'est jamais pris (le correctif ne remplace rien non plus)."""
    from forever.pipeline import mythicsim_build

    source = mythicsim_build.mythicsim_dir(cache_dir) / "go" / DATABASE[0] / DATABASE[1] / "db.json"
    if not source.is_file():
        return None, set(), None
    known = known_items(wowsims_dir(cache_dir) / "forever") or set()
    items = [i for i in json.loads(source.read_text(encoding="utf-8"))["items"] if int(i["id"]) not in known]
    path = wowsims_dir(cache_dir) / EXTRA_ITEMS
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"items": items}), encoding="utf-8")
    revision = str((mythicsim_build.pinned(cache_dir) or {}).get("go_revision") or "?")
    note = (
        f"{len(items)} objets absents de la base de wowsims pris dans celle du fork Go de MythicSim (révision "
        f"{revision[:12]}) : valeurs de cette révision, objet changé depuis par Blizzard non suivi (suppose)"
    )
    return path, {int(i["id"]) for i in items}, note


def parse_equipped(text: str) -> dict[str, int]:
    """« Emplacement:objet,… » (emplacements de wowsims : Head, Finger1, MainHand…) -> dictionnaire."""
    out: dict[str, int] = {}
    for item in (part.strip() for part in text.split(",") if part.strip()):
        slot, sep, value = item.partition(":")
        if not sep or not value.strip().isdigit():
            raise InvalidArgumentError(f"Objet porté illisible : « {item} ».",
                                       "donner equipped en Emplacement:objet séparés par des virgules")  # fmt: skip
        out[slot.strip()] = int(value)
    return out


def optimise_gear(
    deps: Deps,
    *,
    preset: str,
    race: str | None,
    level: int,
    equipped: Mapping[str, int],
    candidates: Sequence[Mapping[str, Any]],
    steps: Sequence[Mapping[str, Any]],
    iterations: int | None = None,
    runner: gitops.Runner | None = None,
    anchors: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Chaque candidat essayé à sa place sur l'équipement porté, au niveau `level`, conditions des tranches, même
    graine ; gain, seuil de bruit et verdict (règle de MS1) ; triés par gain. Voir le module."""
    from forever.sims import base_stats as bs
    from forever.sims.builds import decide
    from forever.sims.engines import class_of

    if not race:
        raise InvalidArgumentError("Race manquante.", "demander la race au joueur (question ou profil), puis race=…")
    unknown_slots = sorted(k for k in equipped if k not in SLOT_NAMES)
    if unknown_slots:
        raise InvalidArgumentError(f"Emplacement inconnu de wowsims : {', '.join(unknown_slots)}.",
                                   "emplacements : " + ", ".join(SLOT_NAMES))  # fmt: skip
    pin = pinned(deps.cache_dir)
    if pin is None:
        raise wowsims.WowsimsError("wowsims/forever n'est pas encore compilé : lancer `uv run forever sims update`.")
    presets = wowsims.read_presets(wowsims_dir(deps.cache_dir) / "forever")
    chosen = next((p for p in presets if p.key == preset), None)
    if chosen is None:
        raise InvalidArgumentError(f"Préréglage inconnu : « {preset} ».", "voir forever_simulate(action='presets')")
    conv, errors = _legality(deps, class_of(chosen))
    keys = talents_at(steps, level)
    problems = errors(keys, level)
    if problems:
        raise InvalidArgumentError(f"Talents illégaux au niveau {level} : {' ; '.join(problems)}.",
                                   "corriger le parcours de talents")  # fmt: skip
    files = (pin.get("patches") or {}).get("files") or []
    doc = (bs.base_stats_doc(chosen.class_token, bs.client_scaling(deps, class_of(chosen), level), anchors or [])
           if bs.PATCH in files else None)  # fmt: skip
    items_path, items_ids, items_note = extra_items(deps.cache_dir) if ITEMS_PATCH in files else (None, set(), None)
    known = known_items(wowsims_dir(deps.cache_dir) / "forever")
    known = None if known is None else known | items_ids
    encounter = encounter_at(wowsims.reference_encounter(presets), level)
    race_token = wowsims.race_enum(race)
    code = conv.wowsims.encode(keys)
    n = iterations or wowsims.DEFAULT_ITERATIONS

    def run(gear: Mapping[str, int]) -> dict[str, Any]:
        items: list[dict[str, Any]] = [{} for _ in SLOT_NAMES]
        for slot, item in gear.items():
            items[SLOT_NAMES.index(slot)] = {"id": int(item)}
        case = solo_preset(chosen, talents=code, equipment={"items": items})
        request = wowsims.request_for(case, race=race_token, encounter=encounter, iterations=n)
        return wowsims.run_sim(deps.cache_dir, request, runner=runner, level=level, base_stats=doc, items=items_path)

    base_gear = {k: v for k, v in equipped.items() if known is None or v in known}
    base = run(base_gear)
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    worn = set(equipped.values())
    for cand in candidates:
        item, slot = int(cand["item"]), str(cand.get("slot"))
        targets = _SLOT_ALIASES.get(slot, (slot,) if slot in SLOT_NAMES else ())
        if item in worn:
            continue
        if not targets or (known is not None and item not in known):
            skipped.append({"slot": slot, "item": item,
                            "reason": "emplacement inconnu" if not targets else "objet absent de wowsims et de MythicSim"})  # fmt: skip
            continue
        best: dict[str, Any] | None = None
        for target in targets:
            trial = run({**base_gear, target: item})
            if best is None or trial["dps"] > best["dps"]:
                best = {**trial, "slot": target}
        assert best is not None
        rows.append({"item": item, "slot": best["slot"], "replaces": equipped.get(best["slot"]),
                     "dps": best["dps"], **decide(base, best)})  # fmt: skip
    rows.sort(key=lambda r: -float(r["gain"]))
    notes = [wowsims.source_note(pin), *NOTES, *([items_note] if items_note else []),
             ("optimisation : chaque candidat à sa place sur l'équipement porté, même graine ; « non départagé » : "
              "gain sous deux erreurs types de la différence (règle de MS1)")]  # fmt: skip
    return {"preset": chosen.key, "race": race_token, "level": level, "base": {"dps": base["dps"],
            "stdev": base["stdev"], "equipped": dict(equipped)}, "candidates": rows, "skipped": skipped,
            "provenance": local_provenance(deps, certainty="suppose", assumptions=notes)}  # fmt: skip


def optimise_from_sources(
    deps: Deps,
    *,
    preset: str,
    race: str | None,
    level: int,
    equipped: Mapping[str, int],
    candidates: Sequence[Mapping[str, Any]] | None = None,
    path: str = "auto",
    spec: str | None = None,
    gear_spec: str | None = None,
    iterations: int | None = None,
) -> dict[str, Any]:
    """`optimise_gear` avec les sources installées : parcours de talents (`path`, comme les tranches), candidats
    donnés ou choix de GearQuest au niveau, relevés d'attributs de ForeverLogger."""
    from forever.sims.base_stats import logger_anchors
    from forever.sims.engines import class_of

    if path not in PATHS:
        raise InvalidArgumentError(f"Parcours inconnu : « {path} ».", "choisir " + ", ".join(PATHS))
    presets = wowsims.read_presets(wowsims_dir(deps.cache_dir) / "forever")
    chosen = next((p for p in presets if p.key == preset), None)
    if chosen is None:
        raise InvalidArgumentError(f"Préréglage inconnu : « {preset} ».", "voir forever_simulate(action='presets')")
    class_name = class_of(chosen)
    notes: list[str] = []
    steps: list[dict[str, Any]] = []
    if path in ("auto", "plan"):
        try:
            steps, label = _plan_steps(deps, class_name, chosen, spec)
            notes.append(f"talents : plan de leveling {label} tronqué au niveau")
        except InvalidArgumentError as err:
            if path == "plan":
                raise
            notes.append(f"plan de leveling indisponible ({err.message}) : build populaire à la place")
            path = "popular"
    if path == "popular":
        steps, label = _popular_steps(deps, class_name, chosen)
        notes.append(f"talents : {label}, ordre de prise légal généré, tronqué au niveau")
    if candidates is None:
        if gear_spec is None:
            from forever.sims.engines import ClassTalents

            conv = ClassTalents(deps, class_name)
            gear_spec = gearquest_spec(chosen.key, conv.lead_tree(conv.wowsims.decode(chosen.talents)))
        candidates, set_aside, names = pool_from_sources(deps, class_name, gear_spec, level, race or "Orc")
        notes.append(f"candidats : {len(candidates)} objets de {', '.join(names)}, filtrés au niveau {level} par la "
                     f"base des simulateurs ({len(set_aside)} écartés)")  # fmt: skip
    anchors, _files = logger_anchors(deps, chosen.class_token)
    out = optimise_gear(deps, preset=preset, race=race, level=level, equipped=equipped, candidates=candidates,
                        steps=steps, iterations=iterations, anchors=anchors)  # fmt: skip
    out["provenance"]["assumptions"] = [*out["provenance"]["assumptions"], *notes]
    return out


# dossier de spé de wowsims -> spécialisation de GearQuest, quand le dossier la nomme
_GQ_FOLDERS = {"retribution": "retribution", "balance": "balance", "elemental": "elemental",
               "enhancement": "enhancement", "feralcat": "feral", "feralbear": "bear"}  # fmt: skip
_GQ_TREES = {"feral_combat": "feral"}  # arbre du client -> spécialisation de GearQuest, quand ils diffèrent


def gearquest_spec(preset_key: str, lead_tree: str) -> str:
    """Spécialisation de GearQuest Forever (`<spé>-<classe>`, forme de `forever_gear`) d'un préréglage : son dossier
    de spé s'il la nomme, sinon l'arbre le plus pris par ses talents."""
    class_folder, spec_folder = preset_key.split("/")[:2]
    tree = lead_tree.strip().lower().replace(" ", "_")
    name = _GQ_FOLDERS.get(spec_folder) or _GQ_TREES.get(tree, tree)
    return f"{name}-{class_folder}"


def candidate_pool(
    db: Mapping[int, Mapping[str, Any]], sources: Sequence[tuple[str, Sequence[int]]], *, level: int, class_id: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Réserve de candidats : objets de toutes les `sources` (nom, objets), emplacement déduit du type de la base,
    filtrés par niveau requis et classe permise ; (candidats avec leurs sources, objets écartés avec la raison)."""
    found: dict[int, list[str]] = {}
    for name, items in sources:
        for item in items:
            found.setdefault(int(item), [])
            if name not in found[int(item)]:
                found[int(item)].append(name)
    pool: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for item, names in found.items():
        row = db.get(item)
        slot = _slot_of(row) if row else None
        reason = None
        if row is None:
            reason = "absent des bases de wowsims et de MythicSim"
        elif int(row.get("reqLvl") or 0) > level:
            reason = f"niveau requis {int(row['reqLvl'])}"
        elif row.get("classAllowlist") and class_id not in row["classAllowlist"]:
            reason = "réservé à d'autres classes"
        elif slot is None:
            reason = "emplacement inconnu"
        if reason:
            skipped.append({"item": item, "reason": reason, "sources": names})
        else:
            pool.append({"item": item, "slot": slot, "sources": names})
    return pool, skipped


# type d'objet de wowsims (`ItemType` de proto/common.proto) -> emplacement des choix (bague et bijou : deux places)
_ITEM_TYPE_SLOTS = {1: "Head", 2: "Neck", 3: "Shoulder", 4: "Back", 5: "Chest", 6: "Wrist", 7: "Hands", 8: "Waist",
                    9: "Legs", 10: "Feet", 11: "Finger", 12: "Trinket", 14: "Ranged"}  # fmt: skip
_WEAPON, _OFF_HAND = 13, 3  # ItemTypeWeapon, HandTypeOffHand


def _slot_of(row: Mapping[str, Any]) -> str | None:
    kind = int(row.get("type") or 0)
    if kind == _WEAPON:
        return "OffHand" if int(row.get("handType") or 0) == _OFF_HAND else "MainHand"
    return _ITEM_TYPE_SLOTS.get(kind)


# classe du client -> identifiant de classe (`classAllowlist` des bases d'objets)
CLASS_IDS = {"Warrior": 1, "Paladin": 2, "Hunter": 3, "Rogue": 4, "Priest": 5, "Shaman": 7, "Mage": 8, "Warlock": 9,
             "Druid": 11}  # fmt: skip


def item_database(cache_dir: Path) -> dict[int, dict[str, Any]]:
    """Base d'objets des simulateurs : wowsims (db.json, leftover_db.json) puis les objets en plus du fork Go de
    MythicSim, sans jamais remplacer un objet de wowsims."""
    from forever.pipeline import mythicsim_build

    out: dict[int, dict[str, Any]] = {}
    ws = wowsims_dir(cache_dir) / "forever" / DATABASE[0] / DATABASE[1]
    ms = mythicsim_build.mythicsim_dir(cache_dir) / "go" / DATABASE[0] / DATABASE[1]
    for path in (ws / "db.json", ws / "leftover_db.json", ms / "db.json"):
        if path.is_file():
            for row in json.loads(path.read_text(encoding="utf-8")).get("items") or []:
                out.setdefault(int(row["id"]), row)
    return out


def pool_from_sources(
    deps: Deps, class_name: str, gear_spec: str, level: int, race: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Réserve de candidats depuis les addons installés : choix de GearQuest au niveau, listes BiS de Naowh Forever
    et de Forever Companion de la classe ; (candidats, écartés, sources lues)."""
    from forever.gear import _addons_dir, gear_report
    from forever.pipeline.gear_sources import read_companion_bis, read_naowh_bis

    addons = _addons_dir(deps)
    sources: list[tuple[str, list[int]]] = []
    picks = gear_report(deps, "leveling", class_name=class_name, level=level, race=race, spec=gear_spec)["picks"]
    sources.append(("GearQuest", [int(p["item"]) for p in picks]))
    token = class_name.upper()
    naowh, _ = read_naowh_bis(addons)
    for key, bis in naowh.items():
        if bis.class_token.upper() == token:
            sources.append((f"Naowh {key}", [i for ids in bis.slots.values() for i in ids]))
    for (cls, spec), slots in read_companion_bis(addons).items():
        if cls.upper() == token:
            sources.append((f"Forever Companion {spec}", [i for ids in slots.values() for i in ids]))
    pool, skipped = candidate_pool(item_database(deps.cache_dir), sources, level=level,
                                   class_id=CLASS_IDS.get(class_name, 0))  # fmt: skip
    return pool, skipped, [name for name, _ in sources]
