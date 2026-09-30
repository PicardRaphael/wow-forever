"""Fiches PvP par classe et par affrontement (PV1, bloc D) : service de lecture, aucun calcul de combat.

Lit le savoir décodé du client (`classes.json`, `races.json`, `pvp_items.json`) et les règles du serveur
(`pvp_rules.json`, noms des catégories de rendements décroissants, `suppose`). Chaque valeur porte son chemin dans les
données (`from` : `fichier:chemin`), sa certitude et la provenance ; une valeur absente vaut `null` et donne une ligne
dans `missing`, jamais une valeur inventée. Les fiches ne lisent jamais le profil joueur (décision 99) : classe,
niveau, race et talents sont passés en arguments. Limite (décision 130, `docs/research/addon-forever.md`) : aucun suivi
en direct des recharges adverses n'est possible dans un addon sur Forever ; seules des fiches fixes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from forever.config import Deps
from forever.profile import normalize_class
from forever.provenance import local_provenance
from forever.store import VersionData, load_version

CLASSES_FILE = "classes.json"
RACES_FILE = "races.json"
ITEMS_FILE = "pvp_items.json"
RULES_FILE = "pvp_rules.json"
SECTIONS = {
    "control": "controls",
    "defensive": "defensives",
    "cc_break": "cc_breaks",
    "interrupt": "interrupts",
    "dispel": "dispels",
    "mobility": "mobility",
    "burst": "bursts",
}
RANK_FIELDS = ("cooldown_s", "duration_s", "pvp_duration_s", "cast_s")
# Interprétations des champs du client par la table des règles (classement, masque de rupture, verrouillage).
INTERPRETED_FIELDS = ("types", "breaks_on_damage", "lockout_s", "how", "targets")
SNARE_TYPES = ("ralentissement",)  # libellé de pvp_classification.control_auras : pas un contrôle diminué
LIMIT = (
    "Aucun suivi en direct des recharges adverses : le journal de combat est refusé aux addons sur Forever et les "
    "valeurs de combat y sont secrètes (docs/research/addon-forever.md) ; ces fiches sont fixes, à consulter hors "
    "combat ou affichées en jeu par l'addon (FA1p)."
)


def _value(value: Any, path: str, certainty: str) -> dict[str, Any]:
    return {"value": value, "from": path, "certainty": certainty}


def _rank_index(spell: Mapping[str, Any], level: int | None) -> int | None:
    """Indice du rang le plus haut connu au niveau (tous les rangs sans niveau) ; None si aucun."""
    ranks = spell["ranks"]
    usable = [i for i, r in enumerate(ranks) if level is None or r["level"] is None or r["level"] <= level]
    if not usable:
        return None
    numbered = [i for i in usable if ranks[i]["rank"] is not None]
    return (numbered or usable)[-1]


def _entry(
    cls: str,
    pool: str,
    key: str,
    spell: Mapping[str, Any],
    index: int,
    kind: str,
    talents: Mapping[str, int] | None,
    categories: Mapping[str, Any],
    missing: list[str],
) -> dict[str, Any]:
    base = f"{CLASSES_FILE}:classes.{cls}.{pool}.{key}"
    rank_path = f"{base}.ranks[{index}]"
    rank = spell["ranks"][index]
    detail = spell["pvp"][kind]
    entry: dict[str, Any] = {
        "key": key,
        "name": spell["name"],
        "name_fr": spell["name_fr"],
        "kind": kind,
        "spell_id": _value(rank["spell_id"], f"{rank_path}.spell_id", "certain"),
        "talent": None,
        "conditional": None,
    }
    talent = spell.get("talent")
    if talent is not None:
        entry["talent"] = talent["key"]
        if talents is None:
            entry["conditional"] = "si talent"
    for field in RANK_FIELDS:
        entry[field] = _value(rank[field], f"{rank_path}.{field}", "certain")
    entry["range_yd"] = _value(
        rank["range_yd"]["max"] if rank["range_yd"] else None,
        f"{rank_path}.range_yd.max" if rank["range_yd"] else f"{rank_path}.range_yd",
        "certain",
    )
    entry["dispel_type"] = _value(rank["dispel_type"], f"{rank_path}.dispel_type", "certain")
    kind_path = f"{base}.pvp.{kind}"
    via = detail.get("via")
    for field, value in detail.items():
        if field == "via":
            entry["via"] = value
            continue
        if via is None and field in RANK_FIELDS:
            continue  # valeur du rang connu au niveau, déjà lue (le détail porte celle du rang le plus haut)
        if via is None and field == "lockout_s":
            entry[field] = _value(rank["duration_s"], f"{rank_path}.duration_s", "probable")
            continue
        certainty = "probable" if field in INTERPRETED_FIELDS else "certain"
        entry[field] = _value(value, f"{kind_path}.{field}", certainty)
    if kind == "control":
        bit = detail.get("diminish") or 0
        category = categories.get(str(bit)) if bit else None
        # Sans catégorie (ou catégorie absente de pvp_rules.json) : null, sans chemin, et une ligne dans `missing`.
        entry["diminish_name"] = (
            _value(category.get("name"), f"{RULES_FILE}:categories.{bit}.name", "suppose") if category else None
        )
        if bit and category is None:
            missing.append(f"{spell['name']} : catégorie {bit} absente de pvp_rules.json")
        if not bit and set(detail.get("types") or []) - set(SNARE_TYPES):
            missing.append(f"{spell['name']} : aucune catégorie de rendement décroissant dans le client")
    if entry["range_yd"]["value"] is None:
        missing.append(f"{spell['name']} : portée absente")
    return entry


def _sections(
    data_cls: Mapping[str, Any],
    cls: str,
    level: int | None,
    talents: Mapping[str, int] | None,
    categories: Mapping[str, Any],
    missing: list[str],
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {name: [] for name in SECTIONS.values()}
    for pool in ("spells", "pet_spells"):
        for key, spell in (data_cls.get(pool) or {}).items():
            if not spell["pvp"]["kinds"]:
                continue
            talent = spell.get("talent")
            if talent is not None and talents is not None and not talents.get(talent["key"]):
                continue  # talent non pris : sort indisponible
            index = _rank_index(spell, level)
            if index is None:
                continue
            for kind in spell["pvp"]["kinds"]:
                item = _entry(cls, pool, key, spell, index, kind, talents, categories, missing)
                item["pet"] = pool == "pet_spells"
                out[SECTIONS[kind]].append(item)
    return out


def _racials(data: VersionData, cls: str) -> list[dict[str, Any]]:
    races = data.read_json(RACES_FILE)["races"]
    out = []
    for race, entry in races.items():
        if cls not in entry["classes"]:
            continue
        for i, racial in enumerate(entry["racials"]):
            if racial["passive"] or (racial["classes"] is not None and cls not in racial["classes"]):
                continue
            path = f"{RACES_FILE}:races.{race}.racials[{i}]"
            out.append(
                {
                    "race": race,
                    "name": racial["name"],
                    "name_fr": racial["name_fr"],
                    "cooldown_s": _value(racial["cooldown_s"], f"{path}.cooldown_s", "certain"),
                    "duration_s": _value(racial["duration_s"], f"{path}.duration_s", "certain"),
                }
            )
    return out


def _trinkets(data: VersionData, cls: str) -> list[dict[str, Any]]:
    out = []
    for i, t in enumerate(data.read_json(ITEMS_FILE)["trinkets"]):
        if t["classes"] is not None and cls not in t["classes"]:
            continue
        path = f"{ITEMS_FILE}:trinkets[{i}]"
        out.append(
            {
                "name": t["name"],
                "item_id": t["item_id"],
                "cooldown_s": _value(t["cooldown_s"], f"{path}.cooldown_s", "certain"),
                "breaks": [b["mechanic_name"] for b in t["breaks"]],
            }
        )
    return out


def _class(data: VersionData, name: str) -> tuple[str, dict[str, Any]]:
    cls = normalize_class(name)
    classes = data.read_json(CLASSES_FILE)["classes"]
    return cls, classes[cls]


def class_sheet(
    data: VersionData, cls: str, level: int | None = None, talents: Mapping[str, int] | None = None
) -> dict[str, Any]:
    """Fiche PvP d'une classe : contrôles (catégorie, durées, portée, recharge, ruptures), défensifs et immunités,
    ruptures de contrôle, interruptions (verrouillage), dissipations, mobilité, recharges offensives, raciaux
    possibles, bijoux PvP ; `missing` : ce qui manque ; `unresolved` : sorts non classés."""
    name, raw = _class(data, cls)
    categories = data.read_json(RULES_FILE).get("categories", {}) if (data.path / RULES_FILE).is_file() else {}
    missing: list[str] = []
    if talents is None:
        missing.append("talents inconnus : sorts de talent marqués « si talent »")
    if level is None:
        missing.append("niveau inconnu : rang le plus haut de chaque sort")
    sheet: dict[str, Any] = {"class": name, "level": level, "talents_known": talents is not None}
    sheet |= _sections(raw, name, level, talents, categories, missing)
    sheet["racials"] = _racials(data, name)
    sheet["trinkets"] = _trinkets(data, name)
    sheet["unresolved"] = [u["name"] for u in raw.get("unresolved_spells", [])]
    if sheet["unresolved"]:
        missing.append(f"{len(sheet['unresolved'])} sort(s) marqué(s) non classé(s) : {', '.join(sheet['unresolved'])}")
    missing.append("condition d'emploi (posture, forme, camouflage) non décodée")
    sheet["missing"] = list(dict.fromkeys(missing))
    sheet["limits"] = [LIMIT]
    return sheet


def matchup(
    data: VersionData,
    mine: Mapping[str, Any],
    opponent: Mapping[str, Any],
) -> dict[str, Any]:
    """Fiche d'affrontement. `mine` : `{class, level, race, talents}` (passés en arguments, jamais lus dans le
    profil) ; `opponent` : `{class, level}`, talents adverses inconnus (sorts de talent « si talent »). Rend les
    menaces adverses (recharges offensives, contrôles, défensifs), mes réponses (ruptures de contrôle, bijou,
    raciaux de ma race, interruptions contre ses sorts à incantation, dissipations contre ses auras), ses réponses à
    mes contrôles, les fenêtres à surveiller (ses recharges longues) et `missing`."""
    me = class_sheet(data, mine["class"], mine.get("level"), mine.get("talents"))
    them = class_sheet(data, opponent["class"], opponent.get("level"), None)
    _, their_raw = _class(data, opponent["class"])
    rules = data.read_json(RULES_FILE) if (data.path / RULES_FILE).is_file() else {}
    long_cd = ((rules.get("sheets") or {}).get("long_cooldown_s") or {}).get("value")
    missing = [*me["missing"], *(f"adversaire : {m}" for m in them["missing"])]
    race = mine.get("race")
    races = data.read_json(RACES_FILE)["races"]
    race_name = next((n for n, r in races.items() if race in (n, r["client_file"], r["name_fr"])), None)
    racials = [r for r in me["racials"] if race_name is not None and r["race"] == race_name]
    if race is None:
        missing.append("race inconnue : raciaux non retenus")
    elif race_name is None:
        missing.append(f"race « {race} » absente de races.json : raciaux non retenus")
    casts = []
    for key, spell in (their_raw.get("spells") or {}).items():
        index = _rank_index(spell, opponent.get("level"))
        if index is None:
            continue
        rank = spell["ranks"][index]
        if rank["cast_s"]:
            path = f"{CLASSES_FILE}:classes.{them['class']}.spells.{key}.ranks[{index}].cast_s"
            casts.append({"key": key, "name": spell["name"], "cast_s": _value(rank["cast_s"], path, "certain")})

    def dispel_types(sheet: Mapping[str, Any], direction: str) -> set[int]:
        return {t for d in sheet["dispels"] if direction in d["targets"]["value"] for t in d["types"]["value"]}

    my_dispel_types = dispel_types(me, "ennemi")  # mes dissipations offensives : ses buffs
    their_dispel_types = dispel_types(them, "allié")  # ses dissipations amies : mes contrôles sur lui ou ses alliés

    def dispellable(items: Sequence[dict[str, Any]], types: set[int]) -> list[dict[str, Any]]:
        return [i for i in items if i["dispel_type"]["value"] in types]

    windows = []
    if long_cd is None:
        missing.append("seuil des recharges longues absent de pvp_rules.json")
    else:
        for section in ("bursts", "defensives", "cc_breaks"):
            for item in them[section]:
                cd = item["cooldown_s"]["value"]
                if cd is not None and cd >= long_cd:
                    windows.append({"name": item["name"], "kind": item["kind"], "cooldown_s": item["cooldown_s"]})
    return {
        "mine": {"class": me["class"], "level": mine.get("level"), "race": race, "talents_known": me["talents_known"]},
        "opponent": {"class": them["class"], "level": opponent.get("level")},
        "threats": {"bursts": them["bursts"], "controls": them["controls"], "defensives": them["defensives"]},
        "answers": {
            "cc_breaks": me["cc_breaks"],
            "trinkets": me["trinkets"],
            "racials": racials,
            "interrupts": me["interrupts"],
            "interruptible_casts": casts if me["interrupts"] else [],
            "dispellable_auras": dispellable([*them["bursts"], *them["defensives"]], my_dispel_types),
        },
        "their_answers": {
            "cc_breaks": them["cc_breaks"],
            "dispels_against_my_controls": dispellable(me["controls"], their_dispel_types),
        },
        "windows": sorted(windows, key=lambda w: -w["cooldown_s"]["value"]),
        "missing": list(dict.fromkeys(missing)),
        "limits": [LIMIT],
    }


def pvp_report(
    deps: Deps,
    cls: str,
    *,
    opponent: str | None = None,
    level: int | None = None,
    race: str | None = None,
    talents: Mapping[str, int] | None = None,
    opponent_level: int | None = None,
) -> dict[str, Any]:
    """Fiche de classe (sans `opponent`) ou d'affrontement, avec la provenance ; ne lit jamais le profil."""
    data = load_version(deps)
    if opponent is None:
        report = class_sheet(data, cls, level, talents)
    else:
        mine = {"class": cls, "level": level, "race": race, "talents": talents}
        report = matchup(data, mine, {"class": opponent, "level": opponent_level if opponent_level else level})
    notes = [
        (
            "valeurs du client certaines (classes.json, races.json, pvp_items.json) ; classement PvP probable ; noms "
            "des catégories de rendements décroissants et règles du serveur supposés (pvp_rules.json)"
        ),
        "fiche fixe : aucun suivi en direct des recharges (voir limits)",
    ]
    report["provenance"] = local_provenance(deps, certainty="suppose", assumptions=notes)
    return report


_LISTS = (
    "controls",
    "defensives",
    "cc_breaks",
    "interrupts",
    "dispels",
    "mobility",
    "bursts",
    "racials",
    "trinkets",
    "interruptible_casts",
    "dispellable_auras",
    "dispels_against_my_controls",
    "windows",
)


def _plain(node: Any) -> Any:
    """Valeur tracée réduite à sa valeur (forme compacte)."""
    if isinstance(node, dict):
        if set(node) == {"value", "from", "certainty"}:
            return node["value"]
        return {k: _plain(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_plain(v) for v in node]
    return node


def compact(report: Mapping[str, Any], *, detail: bool = False, limit: int = 20, offset: int = 0) -> dict[str, Any]:
    """Forme compacte et paginée d'un rapport (outil MCP) : listes coupées à `limit` depuis `offset`, totaux par
    liste dans `totals` ; `detail=False` : valeurs sans leur chemin."""
    totals: dict[str, int] = {}

    def cut(node: Any, path: str = "") -> Any:
        name = path.rsplit(".", 1)[-1]
        if isinstance(node, dict):
            if set(node) == {"value", "from", "certainty"}:
                return node if detail else node["value"]
            return {k: cut(v, f"{path}.{k}" if path else k) for k, v in node.items()}
        if isinstance(node, list) and name in _LISTS:
            totals[path] = len(node)  # chemin complet : answers.cc_breaks et their_answers.cc_breaks distincts
            return [cut(v) for v in node[offset : offset + limit]]
        if isinstance(node, list):
            return [cut(v) for v in node]
        return node

    out = {k: (v if k == "provenance" else cut(v, k)) for k, v in report.items()}
    out["totals"] = totals
    more = [n for n in totals.values() if offset + limit < n]
    out["next_offset"] = offset + limit if more else None
    return out
