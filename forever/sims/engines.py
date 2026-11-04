"""Talents choisis, second moteur et recherche de builds au niveau 60 (MS1, décision 301 ; revient sur la décision 299
au niveau 60 seulement) : orchestration de wowsims/forever (`forever.sims.wowsims`) et de MythicSim
(`forever.sims.mythicsim`), talents convertis par identifiant de sort (`forever.sims.talents`), légalité sur les arbres
du client. Aucun calcul de jeu ici : chaque chiffre vient d'un des deux simulateurs, rendu avec sa source."""

from __future__ import annotations

import dataclasses
from typing import Any

from forever.config import Deps
from forever.errors import ForeverError, InvalidArgumentError
from forever.pipeline import mythicsim_build
from forever.pipeline.wowsims_build import wowsims_dir
from forever.provenance import local_provenance
from forever.sims import mythicsim, wowsims
from forever.sims import talents as tal

LEVEL = 60
CONFIRM_ITERATIONS = 10000  # combats de la confirmation d'un build trouvé (réglage de l'outil, plan MS1)
SHARED_NOTE = (
    "MythicSim : rotation, options et buffs de son fork Go épinglé ; équipement, talents, race et rencontre communs "
    "aux deux moteurs ; écart des deux colonnes sans moyenne ni choix"
)


def class_of(preset: wowsims.Preset) -> str:
    return preset.class_token.removeprefix("Class")


class ClassTalents:
    """Talents d'une classe pour les deux moteurs : arbres du client, ordre de wowsims, ordre de MythicSim (lu à la
    demande : une classe que forever ne convertit pas pour MythicSim n'empêche pas wowsims)."""

    def __init__(self, deps: Deps, class_name: str) -> None:
        from forever.lookup import _class_knowledge

        self.class_name = class_name
        _, self.knowledge, self.gd = _class_knowledge(deps, class_name)
        self.client = tal.client_trees(deps, class_name)
        self.tree_names = [str(tree.get("name")) for tree in self.knowledge.trees]
        self._clone = wowsims_dir(deps.cache_dir) / "forever"
        self._ms_root = mythicsim_build.mythicsim_dir(deps.cache_dir)
        self.wowsims = tal.wowsims_layout(self._clone, class_name, self.client)
        self._mythicsim: tal.EngineLayout | None = None

    @property
    def mythicsim(self) -> tal.EngineLayout:
        if self._mythicsim is None:
            self._mythicsim = tal.mythicsim_layout(self._ms_root / "engine", self._ms_root / "go", self.class_name,
                                                   self.client, wowsims=self._clone)  # fmt: skip
        return self._mythicsim

    def errors(self, keys: dict[str, int]) -> list[str]:
        from forever.engine.talents import check_class_build

        return list(check_class_build(self.knowledge, self.gd.constants.talents, keys, LEVEL))

    def chosen(self, text: str) -> dict[str, int]:
        """`talents` du joueur (« clé=rang,… ») contrôlés au niveau 60 ; illégal : refus qui dit les erreurs."""
        keys = tal.parse_talents(text)
        errors = self.errors(keys)
        if errors:
            raise InvalidArgumentError(
                f"Build illégal au niveau {LEVEL} ({text}) : {' ; '.join(errors)}.",
                "corriger le build (forever_lookup kind=build_check)",
            )
        return keys

    def lead_tree(self, keys: dict[str, int]) -> str:
        """Nom de l'arbre le plus pris."""
        points = [sum(keys.get(str(t["key"]), 0) for t in tree) for tree in self.client]
        return self.tree_names[points.index(max(points))]


def _error(err: ForeverError) -> dict[str, Any]:
    return {"error": {"code": err.code, "message": err.message, "action": err.action}}


def _need_mythicsim(deps: Deps) -> dict[str, Any]:
    pin = mythicsim_build.pinned(deps.cache_dir)
    if pin is None:
        raise mythicsim.MythicsimError("MythicSim n'est pas encore compilé : lancer `uv run forever sims update`.")
    return pin


def _mythicsim_rows(
    deps: Deps,
    cases: list[tuple[wowsims.Preset, str, str, list[str]]],
    encounter: dict[str, Any] | None,
    *,
    consumables: str,
    rotation: str | None,
    iterations: int,
    keep_errors: bool,
) -> list[dict[str, Any]]:
    """Un combat par cas par MythicSim (même graine ; buffs du fork réunis entre les cas, comme chez wowsims) ; un refus
    est rendu dans sa ligne (`keep_errors`) ou levé."""
    built: list[tuple[wowsims.Preset, str, wowsims.Preset | ForeverError]] = []
    for preset, race, code, trees in cases:
        try:
            made: wowsims.Preset | ForeverError = mythicsim.preset_for(
                deps.cache_dir, preset, talents=code, tree_names=trees, rotation=rotation
            )
        except ForeverError as err:
            if not keep_errors:
                raise
            made = err
        built.append((preset, race, made))
    ok = [m for _, _, m in built if isinstance(m, wowsims.Preset)]
    common = {
        "raid_buffs": wowsims._union([m.raid_buffs for m in ok]),
        "party_buffs": wowsims._union([m.party_buffs for m in ok]),
        "individual_buffs": wowsims._union([m.individual_buffs for m in ok]),
        "debuffs": wowsims._union([m.debuffs for m in ok]),
    }
    rows = []
    for preset, race, m in built:
        row: dict[str, Any] = {"preset": preset.key, "race": race}
        if not isinstance(m, wowsims.Preset):
            rows.append({**row, **_error(m)})
            continue
        same = dataclasses.replace(
            m,
            consumables=m.consumables if consumables == "own" else {},
            raid_buffs=common["raid_buffs"],
            party_buffs=common["party_buffs"],
            individual_buffs=common["individual_buffs"],
            debuffs=common["debuffs"],
        )
        try:
            out = mythicsim.run_sim(deps.cache_dir, mythicsim.request_for(same, race=race, encounter=encounter,
                                                                         iterations=iterations))  # fmt: skip
        except ForeverError as err:
            if not keep_errors:
                raise
            rows.append({**row, **_error(err)})
            continue
        rows.append({**row, "talents_string": m.talents, **out})
    return rows


def compare(
    deps: Deps,
    pairs: list[tuple[wowsims.Preset, str]],
    presets: list[wowsims.Preset],
    *,
    engine: str,
    talents: str | None,
    consumables: str,
    rotation: str | None,
    ws_note: str,
    iterations: int = wowsims.DEFAULT_ITERATIONS,
) -> dict[str, Any]:
    """`action="compare"` avec des talents choisis ou un autre moteur : talents du préréglage ou `talents` (légaux au
    niveau 60), convertis pour chaque moteur ; `both` rend les deux colonnes et leur écart, un refus d'un moteur
    n'efface pas l'autre colonne."""
    encounter = wowsims.reference_encounter(presets)
    convs: dict[str, ClassTalents] = {}
    ws_cases: list[tuple[wowsims.Preset, str]] = []
    ms_cases: list[tuple[wowsims.Preset, str, str, list[str]]] = []
    labels: list[dict[str, Any]] = []
    ms_missing: dict[tuple[str, str], ForeverError] = {}
    for preset, race in pairs:
        cls = class_of(preset)
        conv = convs.get(cls) or convs.setdefault(cls, ClassTalents(deps, cls))
        # talents du préréglage gardés tels quels pour wowsims : seul MythicSim a besoin de nos clés (un carré sans
        # correspondance, ex. Call of Thunder, n'efface que sa colonne)
        keys: dict[str, int] | ForeverError
        try:
            keys = conv.chosen(talents) if talents else conv.wowsims.decode(preset.talents)
        except tal.TalentConversionError as err:
            if engine == "mythicsim":
                raise
            keys = err
        ws_code = conv.wowsims.encode(keys) if talents and isinstance(keys, dict) else preset.talents
        ws_cases.append((dataclasses.replace(preset, talents=ws_code), race))
        labels.append({"source": "talents" if talents else "préréglage", "code": ws_code,
                       "keys": keys if isinstance(keys, dict) else None})  # fmt: skip
        if engine != "wowsims":
            try:
                if isinstance(keys, ForeverError):
                    raise keys
                ms_cases.append((preset, race, conv.mythicsim.encode(keys), conv.tree_names))
            except ForeverError as err:
                if engine == "mythicsim":
                    raise
                ms_missing[(preset.key, race)] = err
    notes = [ws_note]
    out: dict[str, Any] = {"level": LEVEL, "engine": engine}
    if engine == "wowsims":
        rows, conditions = wowsims.compare_presets(deps.cache_dir, ws_cases, encounter, consumables=consumables,
                                                   iterations=iterations)  # fmt: skip
        by_case = {(c[0].key, c[1]): lab for c, lab in zip(ws_cases, labels, strict=True)}
        out.update(rows=[{**r, "talents": by_case[(r["preset"], r["race"])]} for r in rows], conditions=conditions)
    elif engine == "mythicsim":
        notes = [mythicsim.source_note(_need_mythicsim(deps))]
        rows = _mythicsim_rows(deps, ms_cases, encounter, consumables=consumables, rotation=rotation,
                               iterations=iterations, keep_errors=False)  # fmt: skip
        rows.sort(key=lambda r: -r["dps"])
        best = rows[0]["dps"] if rows else 0.0
        by_case = {(p.key, r): lab for (p, r), lab in zip(pairs, labels, strict=True)}
        out["rows"] = [{**r, "gap_to_best": r["dps"] - best, "talents": by_case[(r["preset"], r["race"])]}
                       for r in rows]  # fmt: skip
    else:
        notes += [mythicsim.source_note(_need_mythicsim(deps)), SHARED_NOTE]
        ws_rows: dict[tuple[str, str], dict[str, Any]]
        try:
            got, conditions = wowsims.compare_presets(deps.cache_dir, ws_cases, encounter, consumables=consumables,
                                                      iterations=iterations)  # fmt: skip
            ws_rows = {(r["preset"], r["race"]): r for r in got}
            out["conditions"] = conditions
        except ForeverError as err:
            ws_rows = {(p.key, r): _error(err) for p, r in ws_cases}
        ms_rows = {(r["preset"], r["race"]): r
                   for r in _mythicsim_rows(deps, ms_cases, encounter, consumables=consumables, rotation=rotation,
                                            iterations=iterations, keep_errors=True)}  # fmt: skip
        rows = []
        for (preset, race), lab in zip(pairs, labels, strict=True):
            w = ws_rows.get((preset.key, race), {})
            m = ms_rows.get((preset.key, race)) or _error(ms_missing[(preset.key, race)])
            gap = m["dps"] - w["dps"] if "dps" in m and "dps" in w else None
            rows.append({"preset": preset.key, "race": race, "talents": lab, "wowsims": w, "mythicsim": m,
                         "gap": gap})  # fmt: skip
        out["rows"] = rows
    out["provenance"] = local_provenance(deps, certainty="suppose", assumptions=notes)
    return out


def _popular_starts(deps: Deps, class_name: str, tree: str) -> list[tuple[str, dict[str, int]]]:
    """Builds populaires de Talents Forever de la classe, légaux au niveau 60 et du même arbre principal."""
    from forever.talents_forever import load_addon, popular_builds

    addon = load_addon(deps)
    if addon is None or not addon.popular:
        return []
    try:
        doc = popular_builds(addon, deps, class_name)
    except ForeverError:
        return []
    out = []
    for entry in (doc["classes"].get(class_name) or {}).get("top") or []:
        if entry.get("legality") == "légal" and entry.get("level") == LEVEL and entry.get("tree") == tree:
            out.append((f"Talents Forever n° {entry.get('rank')}", dict(entry["talents"])))
    return out


def search_builds(
    deps: Deps,
    preset: wowsims.Preset,
    presets: list[wowsims.Preset],
    race: str,
    *,
    engine: str,
    talents: str | None,
    iterations: int,
    max_steps: int,
    popular: bool,
    rotation: str | None,
    ws_note: str,
) -> dict[str, Any]:
    """`action="builds"` : recherche locale (échange d'un point) depuis chaque départ, mesures appariées par le moteur
    choisi, confirmation sur `CONFIRM_ITERATIONS` combats et verdict (`forever.sims.builds`)."""
    from forever.sims import builds

    wowsims.require_gear(preset)
    conv = ClassTalents(deps, class_of(preset))
    layout = conv.wowsims if engine == "wowsims" else conv.mythicsim
    encounter = wowsims.reference_encounter(presets)
    notes = [ws_note] if engine == "wowsims" else [mythicsim.source_note(_need_mythicsim(deps))]

    def run(keys: dict[str, int], n: int) -> dict[str, Any]:
        code = layout.encode(keys)
        if engine == "wowsims":
            req = wowsims.request_for(dataclasses.replace(preset, talents=code), race=race, encounter=encounter,
                                      iterations=n)  # fmt: skip
            return {"code": code, **wowsims.run_sim(deps.cache_dir, req)}
        ms = mythicsim.preset_for(deps.cache_dir, preset, talents=code, tree_names=conv.tree_names, rotation=rotation)
        return {"code": code, **mythicsim.run_sim(deps.cache_dir, mythicsim.request_for(
            ms, race=race, encounter=encounter, iterations=n))}  # fmt: skip

    starts: list[tuple[str, dict[str, int]]] = []
    if talents:
        starts.append(("talents", conv.chosen(talents)))
    try:
        starts.append(("préréglage", conv.wowsims.decode(preset.talents)))
    except ForeverError as err:
        notes.append(f"talents du préréglage non convertis : {err.message}")
    if popular and starts:
        starts += _popular_starts(deps, conv.class_name, conv.lead_tree(starts[-1][1]))
    candidates = [s.key for tree in layout.trees for s in tree if s.key]
    seen: set[tuple[tuple[str, int], ...]] = set()
    results: list[dict[str, Any]] = []
    for origin, keys in starts:
        tag = tuple(sorted((k, v) for k, v in keys.items() if v))
        if tag in seen:
            continue
        seen.add(tag)
        errors = conv.errors(keys)
        if errors:
            results.append({"origin": origin, "legality": "illégal", "errors": errors})
            continue

        def evaluate(t: Any) -> tuple[float, float]:
            r = run(dict(t), iterations)
            return float(r["dps"]), float(r["stdev"])

        found = builds.climb(keys, evaluate, lambda t: not conv.errors(dict(t)), candidates, max_steps=max_steps)
        final_keys = {k: v for k, v in found["talents"].items() if v}
        start, final = run(keys, CONFIRM_ITERATIONS), run(final_keys, CONFIRM_ITERATIONS)
        results.append({
            "origin": origin,
            "start": {"code": start["code"], "talents": keys, "dps": start["dps"], "stdev": start["stdev"]},
            "final": {"code": final["code"], "talents": final_keys, "dps": final["dps"], "stdev": final["stdev"]},
            "steps": found["steps"], "stopped": found["stopped"], "source": final["source"],
            **builds.decide(start, final),
        })  # fmt: skip
    results.sort(key=lambda r: -float((r.get("final") or {}).get("dps", float("-inf"))))
    notes += [
        (
            f"recherche locale : échange d'un point à la fois, {iterations} combats par mesure, même graine ; "
            f"confirmation sur {CONFIRM_ITERATIONS} combats ; « non départagé » : gain sous deux fois l'écart type de "
            "la différence des moyennes"
        ),
        "rotation et équipement du préréglage gardés : un talent que la rotation n'utilise pas ne peut rien rapporter",
    ]
    return {"level": LEVEL, "engine": engine, "preset": preset.key, "race": race, "results": results,
            "provenance": local_provenance(deps, certainty="suppose", assumptions=notes)}  # fmt: skip
