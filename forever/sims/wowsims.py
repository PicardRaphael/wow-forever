"""Adaptateur mince de wowsims/forever au niveau 60 (décisions 293 et 294 ; `tasks/plan-simulateurs.md` §7) : aucun
calcul de jeu ici. Les préréglages sont ceux du dépôt épinglé (`ui/specs/<classe>/<spé>/`), lus sans exécuter de code :
builds complets (`builds/*.build.json`) et builds de `presets.ts` (`makePresetBuild` : équipement, talents, rotation
APL, options de la spé, buffs). La requête de combat (`RaidSimRequest`, protojson) est envoyée au binaire épinglé par
`forever sims update` (empreinte vérifiée), en local, sans réseau ; le résultat (`RaidSimResult`) donne les dégâts par
seconde. Certitude `suppose` (simulateur tiers), provenance : commit et empreinte du binaire."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from forever.errors import ForeverError
from forever.pipeline import gitops
from forever.pipeline.wowsims_build import pinned, wowsims_dir

DEFAULT_ITERATIONS = 2000  # combats par simulation (réglage de l'outil)
DEFAULT_SEED = 12345  # graine fixe : résultats reproductibles, comparaisons appariées
TIMEOUT_S = 600.0
# Dossier de spé de wowsims -> champ `spec` du message Player (noms du proto de wowsims, pas des valeurs de jeu).
SPEC_FIELDS = {
    "druid/balance": "balanceDruid", "druid/feralcat": "feralCatDruid", "druid/feralbear": "feralBearDruid",
    "druid/restoration": "restorationDruid", "hunter/dps": "hunter", "mage/dps": "mage",
    "paladin/holy": "holyPaladin", "paladin/protection": "protectionPaladin",
    "paladin/retribution": "retributionPaladin", "priest/dps": "dpsPriest", "priest/healer": "healerPriest",
    "rogue/dps": "rogue", "shaman/elemental": "elementalShaman", "shaman/enhancement": "enhancementShaman",
    "shaman/restoration": "restorationShaman", "warlock/dps": "warlock", "warrior/dps": "dpsWarrior",
    "warrior/protection": "protectionWarrior",
}  # fmt: skip
_IMPORT = re.compile(r"^import\s+(\w+)\s+from\s+'\./([^']+\.json)';", re.MULTILINE)
_GEAR = re.compile(r"export const (\w+) = PresetUtils\.makePresetGear\(\s*'[^']*',\s*(\w+)")
_APL = re.compile(r"export const (\w+) = PresetUtils\.makePresetAPLRotation\(\s*'([^']*)',\s*(\w+)")
_TALENTS = re.compile(
    r"export const (\w+) = PresetUtils\.makePresetTalents\(\s*'[^']*',\s*SavedTalents\.create\(\{\s*talentsString:"
    r"\s*'([^']*)'"
)
_BUILD = re.compile(r"PresetUtils\.makePresetBuild\(\s*'([^']*)',\s*\{(.*?)\}\s*\)", re.DOTALL)
_CREATE = re.compile(r"export const (\w+) = \w+\.create\(\s*(?=\{)")
_TALENT_HELPER = re.compile(r"export const (\w+) = talents\(\s*'[^']*',\s*'([^']*)'\s*\)")
_TALENT_OBJECT = re.compile(
    r"export const (\w+) = \{\s*name:\s*'[^']*',\s*data:\s*SavedTalents\.create\(\{\s*talentsString:\s*'([^']*)'"
)
_SIMPLE = re.compile(r"(?:export )?const (\w+) = PresetUtils\.makePresetSimpleRotation\(\s*'[^']*',\s*Spec\.\w+,\s*")
_BUILD_HELPER = re.compile(r"\bbuild\(\s*'([^']*)',\s*(\w+),\s*(\w+),\s*(\w+),\s*(\w+),\s*(\d+(?:\.\d+)?)\s*\)")
_LOCAL_OBJECT = re.compile(r"^(?:export )?const (\w+) = (?=\{)", re.MULTILINE)
_ALIAS = re.compile(r"^export const (\w+) = (\w+);", re.MULTILINE)
_OTHER_DEFAULTS = re.compile(r"export const OtherDefaults = (?=\{)")


class WowsimsError(ForeverError):
    """wowsims/forever non compilé, binaire changé depuis l'épinglage, ou combat en échec."""

    def __init__(self, message: str, action: str = "lancer `uv run forever sims update`") -> None:
        super().__init__("wowsims_failed", message, action)


@dataclass(frozen=True)
class Preset:
    """Préréglage d'une spé du dépôt de wowsims : `key` = `<classe>/<spé>/<nom>`."""

    key: str
    class_token: str
    spec_field: str
    talents: str
    rotation: dict[str, Any]
    equipment: dict[str, Any]
    spec_options: dict[str, Any]
    distance: float | None = None  # distance à la cible du préréglage (Chasseur : `build(…, distance)`)
    race: str | None = None
    raid_buffs: dict[str, Any] = field(default_factory=dict)
    party_buffs: dict[str, Any] = field(default_factory=dict)
    individual_buffs: dict[str, Any] = field(default_factory=dict)
    debuffs: dict[str, Any] = field(default_factory=dict)
    consumables: dict[str, Any] = field(default_factory=dict)
    encounter: dict[str, Any] | None = None


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"(?m)^\s*//.*$|(?<=[,{(\s])//[^\n]*", "", text)


def ts_literal(
    text: str, start: int = 0, ids: dict[str, int] | None = None, refs: dict[str, Any] | None = None
) -> tuple[Any, int]:
    """Littéral d'objet de `presets.ts` (clés nues, `'chaînes'`, nombres, booléens, `Enum.Membre` → « Membre »,
    objets et tableaux imbriqués) en valeur Python ; `Consumables.X.id` → identifiant de la table générée du dépôt
    (`ids`) ; `...nom` : objet local déjà lu (`refs`) étalé ; une autre valeur calculée (appel) vaut None."""
    i = start

    def skip() -> None:
        nonlocal i
        while i < len(text) and text[i] in " \t\r\n,":
            i += 1

    def value() -> Any:
        nonlocal i
        skip()
        ch = text[i]
        if ch == "{":
            i += 1
            out: dict[str, Any] = {}
            while True:
                skip()
                if text[i] == "}":
                    i += 1
                    return out
                spread = re.compile(r"\.\.\.(\w+)").match(text, i)
                if spread:  # `...nom` : objet local du même fichier
                    i = spread.end()
                    base = (refs or {}).get(spread.group(1))
                    if isinstance(base, dict):
                        out.update(base)
                    continue
                m = re.compile(r"['\"]?(\w+)['\"]?\s*:").match(text, i)
                if m is None:
                    raise ValueError(f"clé attendue à la position {i}")
                i = m.end()
                v = value()
                if v is not None:
                    out[m.group(1)] = v
        if ch == "[":
            i += 1
            items: list[Any] = []
            while True:
                skip()
                if text[i] == "]":
                    i += 1
                    return items
                items.append(value())
        if ch in "'\"":
            end = text.index(ch, i + 1)
            s = text[i + 1 : end]
            i = end + 1
            return s
        m = re.compile(r"-?\d+(\.\d+)?").match(text, i)
        if m:
            i = m.end()
            return float(m.group()) if m.group(1) else int(m.group())
        m = re.compile(r"[\w.]+(\([^)]*\))?").match(text, i)
        if m is None:
            raise ValueError(f"valeur illisible à la position {i}")
        i = m.end()
        word = m.group()
        if word in ("true", "false"):
            return word == "true"
        parts = word.split(".")
        if not m.group(1) and len(parts) == 3 and parts[0] == "Consumables" and parts[2] == "id" and ids:
            return ids.get(parts[1])
        if m.group(1) or len(parts) != 2:  # appel ou autre valeur calculée : écartée
            return None
        return parts[1]

    return value(), i


CONSUMABLES_TS = ("ui", "features", "settings", "model", "consumables_auto_gen.ts")
_CONSUMABLE = re.compile(r"^export const (\w+) = \{\s*id:\s*(\d+)\s*\}", re.MULTILINE)


def consumable_ids(clone: Path) -> dict[str, int]:
    """Table générée des consommables du dépôt (`consumables_auto_gen.ts` : nom → identifiant d'objet)."""
    path = clone.joinpath(*CONSUMABLES_TS)
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    return {name: int(i) for name, i in _CONSUMABLE.findall(text)}


def _literal_or_empty(
    text: str, start: int, ids: dict[str, int] | None = None, refs: dict[str, Any] | None = None
) -> Any:
    """Littéral de `presets.ts`, ou {} s'il porte une syntaxe que ce lecteur ne lit pas (le préréglage reste utilisable
    sans ces options ou ces buffs)."""
    try:
        return ts_literal(text, start, ids, refs)[0]
    except (ValueError, IndexError):
        return {}


def _json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _from_presets_ts(spec_dir: Path, rel: str, ids: dict[str, int] | None = None) -> list[Preset]:
    path = spec_dir / "presets.ts"
    if not path.is_file() or rel not in SPEC_FIELDS:
        return []
    text = _strip_comments(path.read_text(encoding="utf-8"))
    files = {name: spec_dir / file for name, file in _IMPORT.findall(text)}
    gear = {var: files.get(src) for var, src in _GEAR.findall(text)}
    apls = _APL.findall(text)
    apl = {var: files.get(src) for var, _, src in apls}
    apl_by_label = {label: files.get(src) for _, label, src in apls}
    talents = {
        **dict(_TALENTS.findall(text)),
        **dict(_TALENT_HELPER.findall(text)),
        **dict(_TALENT_OBJECT.findall(text)),
    }
    local: dict[str, Any] = {}  # objets locaux (`const nom = {…}`), dans l'ordre du fichier, pour les `...nom`
    for m in _LOCAL_OBJECT.finditer(text):
        local[m.group(1)] = _literal_or_empty(text, m.end(), ids, local)
    created = {m.group(1): _literal_or_empty(text, m.end(), ids, local) for m in _CREATE.finditer(text)}
    for var, alias in _ALIAS.findall(text):  # `export const DefaultOptions = NoPetOptions;`
        if alias in created:
            created[var] = created[alias]
    # rotations « simples » (`makePresetSimpleRotation`) : converties en APL par l'interface web seulement, le moteur
    # ne les joue pas ; un build qui en porte une prend l'APL du dépôt de même nom, sinon l'APL par défaut de la spé
    simple = {m.group(1) for m in _SIMPLE.finditer(text)}
    other = _OTHER_DEFAULTS.search(text)
    defaults = _literal_or_empty(text, other.end()) if other else {}
    race = defaults.get("race") if isinstance(defaults, dict) else None  # race par défaut de la spé (OtherDefaults)

    def preset(
        key: str,
        g: Path | None,
        t: str | None,
        r: Path | dict[str, Any] | None,
        options: Any = None,
        distance: float | None = None,
    ) -> Preset | None:
        if g is None or t is None or r is None or not g.is_file() or (isinstance(r, Path) and not r.is_file()):
            return None
        return Preset(
            key=key,
            class_token="Class" + rel.split("/")[0].capitalize(),
            spec_field=SPEC_FIELDS[rel],
            talents=t,
            rotation=_json(r) if isinstance(r, Path) else r,
            equipment=_json(g),
            spec_options={"options": (options if isinstance(options, dict) else created.get("DefaultOptions")) or {}},
            distance=distance,
            raid_buffs=created.get("DefaultRaidBuffs") or {},
            party_buffs=created.get("DefaultPartyBuffs") or {},
            individual_buffs=created.get("DefaultIndividualBuffs") or {},
            debuffs=created.get("DefaultDebuffs") or {},
            consumables=created.get("DefaultConsumables") or {},
            race=race if isinstance(race, str) else None,
        )

    out = []
    for name, body in _BUILD.findall(text):
        fields = dict(re.findall(r"(\w+):\s*(\w+)", body))
        group = re.search(r"group:\s*'([^']*)'", body)
        label = f"{group.group(1)} {name}" if group else name
        rot = fields.get("rotation", "")
        r: Path | dict[str, Any] | None = apl.get(rot)
        if r is None:  # rotation simple ou absente : APL du dépôt du même groupe ou nom, sinon APL par défaut
            r = apl_by_label.get(group.group(1) if group else name) or apl_by_label.get(name)
            if r is None and rot in simple and apls:
                r = files.get(apls[0][2])
        made = preset(f"{rel}/{label}", gear.get(fields.get("gear", "")), talents.get(fields.get("talents", "")), r)
        if made is not None:
            out.append(made)
    for name, g, t, r_var, o_var, distance in _BUILD_HELPER.findall(text):  # Chasseur : build(nom, …, distance)
        made = preset(f"{rel}/{name}", gear.get(g), talents.get(t), apl.get(r_var),
                      created.get(o_var), float(distance))  # fmt: skip
        if made is not None:
            out.append(made)
    if not out and gear and talents and apls:  # aucun build : équipement, talents et rotation par défaut de la spé
        made = preset(
            f"{rel}/défaut",
            next(iter(gear.values())),
            next(iter(talents.values())),
            apls[0][2] and files.get(apls[0][2]),
        )
        if made is not None:
            out.append(made)
    return out


def _from_builds(spec_dir: Path, rel: str) -> list[Preset]:
    out = []
    for path in sorted((spec_dir / "builds").glob("*.build.json")):
        doc = _json(path)
        player = doc.get("player") or {}
        spec_field = next((f for f in SPEC_FIELDS.values() if f in player), None)
        if spec_field is None or not player.get("rotation"):
            continue
        out.append(
            Preset(
                key=f"{rel}/{path.name.removesuffix('.build.json')}",
                class_token=str(player.get("class")),
                spec_field=spec_field,
                talents=str(player.get("talentsString") or ""),
                rotation=dict(player["rotation"]),
                equipment=dict(player.get("equipment") or {}),
                spec_options=dict(player.get(spec_field) or {}),
                race=player.get("race"),
                raid_buffs=dict(doc.get("raidBuffs") or {}),
                party_buffs=dict(doc.get("partyBuffs") or {}),
                individual_buffs=dict(player.get("buffs") or {}),
                debuffs=dict(doc.get("debuffs") or {}),
                consumables=dict(player.get("consumables") or {}),
                encounter=doc.get("encounter"),
            )
        )
    return out


def read_presets(clone: Path) -> list[Preset]:
    """Préréglages de toutes les spés du clone épinglé, dans l'ordre des dossiers."""
    specs = clone / "ui" / "specs"
    ids = consumable_ids(clone)
    out: list[Preset] = []
    for spec_dir in sorted(p for p in specs.glob("*/*") if p.is_dir()):
        rel = spec_dir.relative_to(specs).as_posix()
        out += _from_builds(spec_dir, rel) + _from_presets_ts(spec_dir, rel, ids)
    return out


def race_enum(name: str) -> str:
    """Nom de race du proto de wowsims (`RaceHighOrderSkyborne`) depuis un nom du client (« High Order Skyborne »)."""
    words = name.strip().removeprefix("Race").replace("-", " ").split()
    return "Race" + "".join(w[:1].upper() + w[1:] for w in words)


def source_note(pin: dict[str, Any]) -> str:
    """Hypothèse de provenance d'un résultat de wowsims : commit et empreinte du binaire épinglé."""
    return (f"calcul de wowsims/forever, commit {pin['commit'][:12]} du {pin.get('committed_at')}, binaire compilé "
            f"tel quel (empreinte {pin['sha256'][:12]}), niveau 60 seulement ; simulateur tiers, certitude suppose")  # fmt: skip


def reference_encounter(presets: Sequence[Preset]) -> dict[str, Any] | None:
    """Combat de référence du dépôt : celui du premier build complet (cible de raid de wowsims)."""
    return next((p.encounter for p in presets if p.encounter), None)


def request_for(
    preset: Preset,
    *,
    race: str | None = None,
    encounter: dict[str, Any] | None = None,
    iterations: int = DEFAULT_ITERATIONS,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """`RaidSimRequest` d'un seul joueur sur le préréglage, race au choix, combat donné (sinon celui du préréglage)."""
    player: dict[str, Any] = {
        "name": preset.key,
        "race": race or preset.race,
        "class": preset.class_token,
        "equipment": preset.equipment,
        "talentsString": preset.talents,
        preset.spec_field: preset.spec_options,
        "rotation": preset.rotation,
    }
    if preset.distance is not None:
        player["distanceFromTarget"] = preset.distance
    if preset.individual_buffs:
        player["buffs"] = preset.individual_buffs
    if preset.consumables:
        player["consumables"] = preset.consumables
    raid: dict[str, Any] = {"parties": [{"players": [player], "buffs": preset.party_buffs}]}
    if preset.raid_buffs:
        raid["buffs"] = preset.raid_buffs
    if preset.debuffs:
        raid["debuffs"] = preset.debuffs
    return {
        "raid": raid,
        "encounter": encounter or preset.encounter or {},
        "simOptions": {"iterations": iterations, "randomSeed": seed},
        "type": "SimTypeIndividual",
    }


def _binary(cache_dir: Path) -> tuple[Path, dict[str, Any]]:
    pin = pinned(cache_dir)
    if pin is None:
        raise WowsimsError("wowsims/forever n'est pas encore compilé : lancer `uv run forever sims update`.")
    binary = wowsims_dir(cache_dir) / str(pin["binary"])
    if not binary.is_file():
        raise WowsimsError(f"binaire épinglé introuvable : {binary}.")
    if hashlib.sha256(binary.read_bytes()).hexdigest() != pin["sha256"]:
        raise WowsimsError(f"empreinte du binaire différente de l'épinglage ({binary.name}) : il a changé.")
    return binary, pin


def run_sim(cache_dir: Path, request: dict[str, Any], *, runner: gitops.Runner | None = None) -> dict[str, Any]:
    """Un combat simulé par le binaire épinglé : dégâts par seconde (moyenne, écart type), combats faits, source."""
    binary, pin = _binary(cache_dir)
    runs = wowsims_dir(cache_dir) / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    name = uuid.uuid4().hex[:12]
    infile, outfile = runs / f"{name}.in.json", runs / f"{name}.out.json"
    infile.write_text(json.dumps(request), encoding="utf-8")
    try:
        gitops._run(
            runner or gitops.subprocess_runner,
            [str(binary), "sim", "--infile", str(infile), "--outfile", str(outfile)],
            runs,
            timeout=TIMEOUT_S,
        )
        result = _json(outfile)
    except (gitops.GitOpsError, OSError, ValueError) as exc:
        raise WowsimsError(
            f"combat simulé en échec : {exc}", "vérifier la requête ; relancer `forever sims update`"
        ) from exc
    finally:
        infile.unlink(missing_ok=True)
        outfile.unlink(missing_ok=True)
    if result.get("error"):
        raise WowsimsError(f"wowsims : {result['error']}", "vérifier la requête (préréglage, race, combat)")
    dps = result["raidMetrics"]["parties"][0]["players"][0]["dps"]
    return {
        "dps": float(dps.get("avg", 0.0)),
        "stdev": float(dps.get("stdev", 0.0)),
        "iterations": int(result.get("iterationsDone", 0)),
        "source": {
            "simulator": "wowsims/forever",
            "commit": pin["commit"],
            "committed_at": pin.get("committed_at"),
            "sha256": pin["sha256"],
            "certainty": "suppose",
        },
    }


def compare_races(
    cache_dir: Path,
    preset: Preset,
    races: Sequence[str],
    encounter: dict[str, Any] | None = None,
    *,
    iterations: int = DEFAULT_ITERATIONS,
    seed: int = DEFAULT_SEED,
    runner: gitops.Runner | None = None,
) -> list[dict[str, Any]]:
    """Races comparées par paires (même préréglage, même combat, même graine), de la meilleure à la moins bonne,
    écart à la meilleure en dégâts par seconde."""
    rows = []
    for race in races:
        out = run_sim(
            cache_dir,
            request_for(preset, race=race, encounter=encounter, iterations=iterations, seed=seed),
            runner=runner,
        )
        rows.append({"race": race, **out})
    rows.sort(key=lambda r: -r["dps"])
    best = rows[0]["dps"] if rows else 0.0
    return [{**r, "gap_to_best": r["dps"] - best} for r in rows]


STAT_DELTA = 50.0  # points ajoutés à une statistique pour mesurer son poids (réglage de l'outil)
_STAT_ENUM = re.compile(r"enum Stat \{(.*?)\}", re.DOTALL)


def stat_names(clone: Path) -> list[str]:
    """Statistiques du proto épinglé (`enum Stat` de `proto/common.proto`), dans l'ordre de leur numéro."""
    m = _STAT_ENUM.search((clone / "proto" / "common.proto").read_text(encoding="utf-8"))
    if m is None:
        raise WowsimsError("proto de wowsims : énumération Stat introuvable.")
    pairs = re.findall(r"^\s*(Stat\w+)\s*=\s*(\d+);", m.group(1), re.MULTILINE)
    return [name for name, _ in sorted(pairs, key=lambda p: int(p[1]))]


def stat_weights(
    cache_dir: Path,
    preset: Preset,
    stats: Sequence[str],
    *,
    reference: str,
    race: str | None = None,
    encounter: dict[str, Any] | None = None,
    delta: float = STAT_DELTA,
    iterations: int = DEFAULT_ITERATIONS,
    seed: int = DEFAULT_SEED,
    runner: gitops.Runner | None = None,
) -> dict[str, Any]:
    """Poids des statistiques par tirages appariés : un combat sans bonus, puis un par statistique avec `delta` points
    de plus (même préréglage, même graine) ; gain de dégâts par seconde par point, et rapporté à `reference`."""
    names = stat_names(wowsims_dir(cache_dir) / "forever")
    unknown = [s for s in [*stats, reference] if s not in names]
    if unknown:
        raise WowsimsError(
            f"statistiques inconnues du proto épinglé : {', '.join(unknown)}.", "voir proto/common.proto"
        )
    base_req = request_for(preset, race=race, encounter=encounter, iterations=iterations, seed=seed)
    base = run_sim(cache_dir, base_req, runner=runner)
    per_point: dict[str, float] = {}
    for stat in dict.fromkeys([*stats, reference]):
        req = request_for(preset, race=race, encounter=encounter, iterations=iterations, seed=seed)
        bonus = [0.0] * len(names)
        bonus[names.index(stat)] = delta
        req["raid"]["parties"][0]["players"][0]["bonusStats"] = {"stats": bonus}
        per_point[stat] = (run_sim(cache_dir, req, runner=runner)["dps"] - base["dps"]) / delta
    ref = per_point[reference]
    normalised = {s: (per_point[s] / ref if ref else 0.0) for s in stats}
    return {"base_dps": base["dps"], "per_point": {s: per_point[s] for s in stats}, "normalised": normalised,
            "reference": reference, "delta": delta, "source": base["source"]}  # fmt: skip


GAP_THRESHOLD = 0.01  # écart relatif noté entre deux commits pour un même cas (réglage de l'outil)
VEILLE_NAME = "veille.json"


def replay_reference(
    cache_dir: Path,
    race_for: dict[str, str],
    *,
    iterations: int = DEFAULT_ITERATIONS,
    seed: int = DEFAULT_SEED,
    runner: gitops.Runner | None = None,
) -> dict[str, Any]:
    """Cas de référence de la veille : chaque préréglage du clone épinglé, sur le combat de référence, même graine ;
    race du préréglage, sinon `race_for[classe]` (race jouable lue dans les données de Forever). Écarts au passage
    précédent au-delà de `GAP_THRESHOLD`, écrits dans `veille.json` avec les deux commits."""
    root = wowsims_dir(cache_dir)
    pin = pinned(cache_dir) or {}
    presets = read_presets(root / "forever")
    encounter = reference_encounter(presets)
    path = root / VEILLE_NAME
    previous = _json(path) if path.is_file() else {}
    cases: dict[str, float] = {}
    skipped: list[str] = []
    for p in presets:
        race = p.race or race_for.get(p.class_token.removeprefix("Class"))
        if race is None:
            skipped.append(p.key)
            continue
        try:
            out = run_sim(cache_dir, request_for(p, race=race, encounter=encounter, iterations=iterations, seed=seed),
                          runner=runner)  # fmt: skip
        except WowsimsError:
            skipped.append(p.key)
            continue
        cases[p.key] = out["dps"]
    old = previous.get("cases") or {}
    gaps = [
        {"case": k, "before": old[k], "after": v, "relative": (v - old[k]) / old[k]}
        for k, v in sorted(cases.items())
        if k in old and old[k] and abs(v - old[k]) / old[k] > GAP_THRESHOLD
    ]
    report = {"commit": pin.get("commit"), "previous_commit": previous.get("commit"), "cases": cases, "gaps": gaps,
              "skipped": skipped, "threshold": GAP_THRESHOLD, "seed": seed}  # fmt: skip
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return report


def _union(dicts: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Réunion de buffs (un buff donné par un préréglage l'est pour tous ; valeur numérique : la plus grande)."""
    out: dict[str, Any] = {}
    for d in dicts:
        for k, v in d.items():
            if isinstance(v, bool) or not isinstance(v, int | float):
                out[k] = out.get(k) or v
            else:
                out[k] = max(out.get(k, 0), v)
    return out


def compare_presets(
    cache_dir: Path,
    cases: Sequence[tuple[Preset, str]],
    encounter: dict[str, Any] | None,
    *,
    consumables: str = "none",
    iterations: int = DEFAULT_ITERATIONS,
    seed: int = DEFAULT_SEED,
    runner: gitops.Runner | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Préréglages (et races) comparés dans des conditions identiques : mêmes buffs de raid, de groupe et individuels,
    mêmes affaiblissements (réunion de ceux des préréglages), même rencontre et durée, même graine ; `consumables` :
    `none` (aucun, strictement identique) ou `own` (ceux de chaque préréglage). Rend les lignes, de la meilleure à la
    moins bonne, et les conditions appliquées."""
    import dataclasses

    if consumables not in ("none", "own"):
        raise WowsimsError(f"consommables « {consumables} » : none ou own attendu.", "choisir none ou own")
    common = {
        "raid_buffs": _union([p.raid_buffs for p, _ in cases]),
        "party_buffs": _union([p.party_buffs for p, _ in cases]),
        "individual_buffs": _union([p.individual_buffs for p, _ in cases]),
        "debuffs": _union([p.debuffs for p, _ in cases]),
    }
    rows = []
    for preset, race in cases:
        same = dataclasses.replace(
            preset,
            raid_buffs=common["raid_buffs"],
            party_buffs=common["party_buffs"],
            individual_buffs=common["individual_buffs"],
            debuffs=common["debuffs"],
            consumables=preset.consumables if consumables == "own" else {},
        )
        out = run_sim(cache_dir, request_for(same, race=race, encounter=encounter, iterations=iterations, seed=seed),
                      runner=runner)  # fmt: skip
        rows.append({"preset": preset.key, "race": race, **out})
    rows.sort(key=lambda r: -r["dps"])
    best = rows[0]["dps"] if rows else 0.0
    conditions = {**common, "consumables": consumables, "encounter": encounter, "seed": seed, "iterations": iterations}
    return [{**r, "gap_to_best": r["dps"] - best} for r in rows], conditions
