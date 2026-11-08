"""Réponses des outils (CLI `forever sims`, MCP `forever_simulate`) au niveau 60, calculées par wowsims/forever
(décisions 293 et 294) et MythicSim (MS1, décision 301) : préréglages du dépôt épinglé, races comparées par paires,
poids des statistiques, comparaisons avec les talents choisis (un moteur ou les deux), recherche de builds
(`forever.sims.engines`). Chaque réponse porte la provenance (moteur, commit et empreinte du binaire, certitude
`suppose`). Aucun calcul de jeu ici."""

from __future__ import annotations

from typing import Any

from forever.config import Deps
from forever.errors import InvalidArgumentError
from forever.pipeline.wowsims_build import pinned, wowsims_dir
from forever.provenance import local_provenance
from forever.sims import engines, wowsims

MAGE_ENGINE_FROZEN = (
    "moteur du Mage gelé à la révision 7 de 1.60.1.70450 (décision 293) : plus aucune mécanique ajoutée, recoupé par "
    "les journaux de combat ; au niveau 60, wowsims/forever répond (forever_simulate)"
)
LEVEL = 60  # wowsims/forever ne simule que le niveau 60 (constante de son code, issue #624)
ACTIONS = ("presets", "races", "weights", "compare", "builds", "brackets", "race_brackets", "gear", "analysis")
ENGINES = ("wowsims", "mythicsim", "both")


def _stat(name: str) -> str:
    key = name.strip().replace(" ", "")
    return key if key.startswith("Stat") else "Stat" + key


def simulate(
    deps: Deps,
    action: str,
    *,
    preset: str | None = None,
    races: str | None = None,
    race: str | None = None,
    stats: str | None = None,
    reference: str | None = None,
    iterations: int | None = None,
    cases: str | None = None,
    consumables: str = "none",
    talents: str | None = None,
    engine: str = "wowsims",
    rotation: str | None = None,
    max_steps: int | None = None,
    popular: bool = True,
    brackets: str | None = None,
    path: str = "auto",
    gear: str = "gearquest",
    spec: str | None = None,
    level: int | None = None,
    equipped: str | None = None,
    candidates: str | None = None,
    conditions: str = "solo",
    targets: int = 1,
) -> dict[str, Any]:
    """`action` : `presets` (liste, objets équipés de chacun), `races` (races séparées par des virgules, sur
    `preset`), `weights` (statistiques séparées par des virgules, rapportées à `reference`, `race` du joueur exigée),
    `compare` (`cases` : « clé@Race » séparés par des virgules, conditions identiques ; `consumables` : `none` ou
    `own` ; `talents` : « clé=rang,… » en nos clés, légaux au niveau 60 ; `engine` : `wowsims`, `mythicsim` ou
    `both`), `builds` (recherche locale sur `preset` pour `race` ; départs : `talents`, talents du préréglage, builds
    populaires de Talents Forever si `popular` ; `rotation` : rotation du fork de MythicSim). Préréglage sans
    équipement : refusé. La race vient toujours du joueur, jamais du préréglage ; sauf `race_brackets` : toutes les
    races jouables de la classe (ou `races`) classées par tranche (`brackets`, `path`, `gear`, `conditions`)."""

    if action not in ACTIONS:
        raise InvalidArgumentError(f"Action inconnue : « {action} ».", "choisir " + ", ".join(ACTIONS))
    if engine not in ENGINES:
        raise InvalidArgumentError(f"Moteur inconnu : « {engine} ».", "choisir " + ", ".join(ENGINES))
    if action == "analysis":  # SIM2 bloc 15 : analyse gardée (forever sims analyse), jamais recalculée ici
        from forever.sims.analysis import dps_presets, read_analysis

        if not preset:
            listed = [{"preset": k, "race": r, "ready": read_analysis(deps, k, r) is not None}
                      for k, r in dps_presets(deps)]  # fmt: skip
            return {"analyses": listed, "provenance": local_provenance(deps, certainty="suppose", assumptions=[])}
        doc = read_analysis(deps, preset, race or dict(dps_presets(deps)).get(preset, ""))
        if doc is None:
            raise InvalidArgumentError(f"Analyse absente pour « {preset} ».",
                                       "lancer `uv run forever sims analyse --preset …` (ou --all)")  # fmt: skip
        if level is not None:
            doc = {**doc, "brackets": [b for b in doc["brackets"] if b["level"] == level] or doc["brackets"]}
        return doc
    if action == "gear":  # SIM2 bloc 8 : optimisation de l'équipement par emplacement au niveau
        from forever.sims.brackets import optimise_from_sources, parse_equipped

        if not preset or level is None:
            raise InvalidArgumentError("Préréglage ou niveau manquant.", "donner preset et level")
        cands = None
        if candidates:
            cands = [{"slot": k, "item": v} for k, v in parse_equipped(candidates).items()]
        return optimise_from_sources(deps, preset=preset, race=race, level=level,
                                     equipped=parse_equipped(equipped or ""), candidates=cands, path=path, spec=spec,
                                     iterations=iterations)  # fmt: skip
    if action == "race_brackets":  # SIM2 §9 : toutes les races jouables de la classe, par tranche
        from forever.sims.races import races_from_sources

        if not preset:
            raise InvalidArgumentError("Préréglage manquant.", "donner preset (voir action=presets)")
        asked = [r for r in (races or "").split(",") if r.strip()] or None
        return races_from_sources(deps, preset=preset, brackets=brackets, races=asked, path=path, gear=gear,
                                  spec=spec, iterations=iterations, conditions=conditions)  # fmt: skip
    if action == "brackets":  # SIM2 : sous le 60, par tranche de niveaux (wowsims corrigé, décision 305)
        from forever.sims.brackets import run_from_sources

        if not preset:
            raise InvalidArgumentError("Préréglage manquant.", "donner preset (voir action=presets)")
        if (stats or "").strip().lower() == "auto":  # toutes les statistiques d'équipement connues du proto épinglé
            known = wowsims.stat_names(wowsims_dir(deps.cache_dir) / "forever")
            wanted = [s for s in wowsims.STAT_TO_GUIDE if s in known]
        else:
            wanted = [_stat(s) for s in (stats or "").split(",") if s.strip()]
        auto = (stats or "").strip().lower() == "auto"
        ref = _stat(reference) if reference else (None if auto else (wanted[0] if wanted else None))
        if wanted and ref is not None and ref not in wanted:
            raise InvalidArgumentError(f"reference « {reference} » absente de stats.",
                                       "donner reference parmi stats (ex. SpellDamage)")  # fmt: skip
        return run_from_sources(deps, preset=preset, race=race, brackets=brackets, path=path, gear=gear, spec=spec,
                                iterations=iterations, stats=wanted or None, reference=ref,
                                conditions=conditions, targets=targets)  # fmt: skip
    pin = pinned(deps.cache_dir)
    if pin is None:
        raise wowsims.WowsimsError("wowsims/forever n'est pas encore compilé : lancer `uv run forever sims update`.")
    presets = wowsims.read_presets(wowsims_dir(deps.cache_dir) / "forever")
    provenance = local_provenance(deps, certainty="suppose", assumptions=[wowsims.source_note(pin)])
    if action == "presets":
        listed = [{"key": p.key, "class": p.class_token, "race": p.race, "items": p.items} for p in presets]
        return {"level": LEVEL, "presets": listed, "provenance": provenance}
    if action == "compare":
        by_key = {p.key: p for p in presets}
        pairs = []
        for item in (cases or "").split(","):
            key, _, race_name = item.strip().partition("@")
            if key not in by_key or not race_name:
                raise InvalidArgumentError(f"Cas illisible : « {item} ».", "donner cases, ex. mage/dps/Fire@Human")
            pairs.append((by_key[key], wowsims.race_enum(race_name)))
        kw: dict[str, Any] = {"iterations": iterations} if iterations else {}
        if engine == "wowsims" and not talents:  # comparaison d'avant MS1, inchangée
            rows, fight_conditions = wowsims.compare_presets(
                deps.cache_dir, pairs, wowsims.reference_encounter(presets), consumables=consumables, **kw
            )
            return {
                "level": LEVEL,
                "engine": engine,
                "rows": rows,
                "conditions": fight_conditions,
                "provenance": provenance,
            }
        return engines.compare(deps, pairs, presets, engine=engine, talents=talents, consumables=consumables,
                               rotation=rotation, ws_note=wowsims.source_note(pin), **kw)  # fmt: skip
    if action == "builds":
        found = next((p for p in presets if p.key == preset), None)
        if found is None:
            raise InvalidArgumentError(f"Préréglage inconnu : « {preset} ».", "voir action=presets")
        if not race:
            raise InvalidArgumentError(
                "Race manquante.", "demander la race au joueur (question ou profil), puis race=…"
            )
        if engine == "both":
            raise InvalidArgumentError("Recherche de builds par un seul moteur.", "choisir engine=wowsims ou mythicsim")
        return engines.search_builds(deps, found, presets, wowsims.race_enum(race), engine=engine, talents=talents,
                                     iterations=iterations or wowsims.DEFAULT_ITERATIONS, max_steps=max_steps or 30,
                                     popular=popular, rotation=rotation, ws_note=wowsims.source_note(pin))  # fmt: skip
    chosen = next((p for p in presets if p.key == preset), None)
    if chosen is None:
        raise InvalidArgumentError(f"Préréglage inconnu : « {preset} ».", "voir action=presets")
    encounter = wowsims.reference_encounter(presets)
    kwargs: dict[str, Any] = {"iterations": iterations} if iterations else {}
    if action == "races":
        names = [wowsims.race_enum(r) for r in (races or "").split(",") if r.strip()]
        if not names:
            raise InvalidArgumentError("Races manquantes.", "donner races, ex. Human,Gnome,High Order Skyborne")
        rows = wowsims.compare_races(deps.cache_dir, chosen, names, encounter, **kwargs)
        return {"level": LEVEL, "preset": chosen.key, "races": rows, "provenance": provenance}
    if not race:  # race du joueur seulement, jamais celle du préréglage (demande du 2026-10-22)
        raise InvalidArgumentError("Race manquante.", "demander la race au joueur (question ou profil), puis race=…")
    wanted = [_stat(s) for s in (stats or "").split(",") if s.strip()]
    if not wanted or not reference:
        raise InvalidArgumentError(
            "Statistiques ou référence manquantes.", "donner stats et reference, ex. SpellDamage"
        )
    out = wowsims.stat_weights(
        deps.cache_dir,
        chosen,
        wanted,
        reference=_stat(reference),
        race=wowsims.race_enum(race),
        encounter=encounter,
        **kwargs,
    )
    return {"level": LEVEL, "preset": chosen.key, **out, "provenance": provenance}
