"""Réponses des outils (CLI `forever sims`, MCP `forever_simulate`) au niveau 60, calculées par wowsims/forever
(décisions 293 et 294) : préréglages du dépôt épinglé, races comparées par paires, poids des statistiques. Chaque
réponse porte la provenance (commit et empreinte du binaire, certitude `suppose`). Aucun calcul de jeu ici."""

from __future__ import annotations

from typing import Any

from forever.config import Deps
from forever.errors import InvalidArgumentError
from forever.pipeline.wowsims_build import pinned, wowsims_dir
from forever.provenance import local_provenance
from forever.sims import wowsims

MAGE_ENGINE_FROZEN = (
    "moteur du Mage gelé à la révision 7 de 1.60.1.70450 (décision 293) : plus aucune mécanique ajoutée, recoupé par "
    "les journaux de combat ; au niveau 60, wowsims/forever répond (forever_simulate)"
)
LEVEL = 60  # wowsims/forever ne simule que le niveau 60 (constante de son code, issue #624)
ACTIONS = ("presets", "races", "weights", "compare")


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
) -> dict[str, Any]:
    """`action` : `presets` (liste, objets équipés de chacun), `races` (races séparées par des virgules, sur
    `preset`), `weights` (statistiques séparées par des virgules, rapportées à `reference`, `race` du joueur exigée),
    `compare` (`cases` : « clé@Race » séparés par des virgules, conditions identiques ; `consumables` : `none` ou
    `own`). Préréglage sans équipement : refusé. La race vient toujours du joueur, jamais du préréglage."""
    if action not in ACTIONS:
        raise InvalidArgumentError(f"Action inconnue : « {action} ».", "choisir " + ", ".join(ACTIONS))
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
        rows, conditions = wowsims.compare_presets(
            deps.cache_dir, pairs, wowsims.reference_encounter(presets), consumables=consumables, **kw
        )
        return {"level": LEVEL, "rows": rows, "conditions": conditions, "provenance": provenance}
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
