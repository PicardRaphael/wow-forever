"""Talents envoyés par le jeu reliés aux clés de forever (P06a, sonde en jeu E du 2026-10-09). L'addon envoie
`nœud:rang` (identifiants de nœud de `C_Traits`, rangs achetés) ; `classes.json` relie chaque nœud à un talent
(tables TraitNode et TraitNodeEntry du client, même build que les données). Le pont ajoute la traduction au message,
pour que la conversation passe ces clés à `current` de `forever_build` sans rien deviner."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from forever.bridge.items import GearPiece, parse_gear
from forever.config import Deps
from forever.engine.xp import ActiveAura

# Jeton de classe du jeu (`UnitClassBase`) → nom de la classe dans `classes.json`.
CLASS_NAMES = {
    "WARRIOR": "Warrior",
    "PALADIN": "Paladin",
    "HUNTER": "Hunter",
    "ROGUE": "Rogue",
    "PRIEST": "Priest",
    "SHAMAN": "Shaman",
    "MAGE": "Mage",
    "WARLOCK": "Warlock",
    "DRUID": "Druid",
}


@dataclass(frozen=True)
class KnownTalent:
    key: str
    name: str
    rank: int
    max: int


@dataclass(frozen=True)
class TalentReading:
    known: list[KnownTalent] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)


TalentTable = Mapping[str, Mapping[int, tuple[str, str, int]]]


def talent_table(deps: Deps) -> dict[str, dict[int, tuple[str, str, int]]]:
    """Jeton de classe → nœud → (clé, nom anglais du client, rang maximal), d'après `classes.json`."""
    from forever.store import load_version

    data = load_version(deps)
    classes = data.read_json("classes.json")["classes"]
    out: dict[str, dict[int, tuple[str, str, int]]] = {}
    for token, name in CLASS_NAMES.items():
        trees = (classes.get(name) or {}).get("trees") or []
        out[token] = {
            int(t["node_id"]): (str(t["key"]), str(t["name"]), int(t["max"]))
            for tree in trees
            for t in tree["talents"]
            if t.get("node_id") is not None
        }
    return out


def describe_talents(table: TalentTable, class_token: str, text: str) -> TalentReading:
    """Talents `nœud:rang` du jeu, dans l'ordre reçu ; ce qui ne se relie à aucun talent reste dans `unknown`."""
    nodes = table.get(class_token, {})
    reading = TalentReading()
    for part in (p.strip() for p in str(text or "").split(",")):
        if not part:
            continue
        node, sep, rank = part.partition(":")
        if sep and node.isdigit() and rank.isdigit() and int(node) in nodes:
            key, name, top = nodes[int(node)]
            reading.known.append(KnownTalent(key, name, int(rank), top))
        else:
            reading.unknown.append(part)
    return reading


def talents_line(reading: TalentReading) -> str:
    """« clé:rang (Nom rang/max), … » ; les nœuds non reconnus sont nommés à part."""
    parts = [f"{t.key}:{t.rank} ({t.name} {t.rank}/{t.max})" for t in reading.known]
    text = ", ".join(parts) or "aucun talent reconnu"
    if reading.unknown:
        text += f" ; nœuds non reconnus : {', '.join(reading.unknown)}"
    return text


# --- Contexte vérifié (sonde en jeu F du 2026-10-09) ---------------------------------------------------------------

# Note lue par la conversation « jeu » : en mots de joueur, sans nom de tranche (sonde en jeu H du 2026-10-10).
EQUIPMENT_NOTE = "noms du client ; objets pas encore reliés aux données de forever, comparaison d'objets à venir"


@dataclass(frozen=True)
class ContextData:
    """Données dont le pont a besoin pour relier le contexte du jeu : talents par nœud, niveau maximal des données,
    races par nom de fichier du client (`UnitRace`) et par nom."""

    talents: TalentTable
    level_cap: int | None
    races: Mapping[str, tuple[str, ...]]
    factions: Mapping[str, str] = field(default_factory=dict)  # race → faction (minuscules)


@dataclass(frozen=True)
class Defect:
    kind: str  # talent, classe, race, objet
    value: str
    reason: str


@dataclass(frozen=True)
class Resolved:
    """Contexte relié à nos données ; ce qui ne se relie pas est dans `defects`, jamais ailleurs."""

    class_token: str
    class_name: str | None
    level: int | None
    race: str | None
    faction: str | None
    zone: str | None
    reading: TalentReading
    current: dict[str, int]
    target_class: str | None
    target_level: int | None
    target_races: tuple[str, ...]
    gear: list[tuple[str, int, str]]
    defects: list[Defect]
    pieces: list[GearPiece] = field(default_factory=list)  # pièces complètes (enchantement, suffixe ; P06b)
    xp: XpContext | None = None  # T04f : repos, auras d'XP, objets surveillés (ForeverBridge 0.2.0)
    professions: dict[str, int] | None = None  # RX1 : métiers et rang (ForeverBridge 0.3.0)


def load_context_data(deps: Deps) -> ContextData:
    """Tables du contexte lues dans la version installée (ForeverError si les données sont illisibles)."""
    from forever.store import load_version

    data = load_version(deps)
    races: dict[str, list[str]] = {}
    factions: dict[str, str] = {}
    for name, race in (data.read_json("races.json").get("races") or {}).items():
        for label in {str(name), str(race.get("client_file") or name)}:
            races.setdefault(label.lower(), []).append(str(name))
        if race.get("faction"):
            factions[str(name)] = str(race["faction"]).lower()
    cap = data.read_json("spell_scaling.json").get("level_cap")
    return ContextData(
        talents=talent_table(deps),
        level_cap=int(cap) if isinstance(cap, int) else None,
        races={k: tuple(sorted(set(v))) for k, v in races.items()},
        factions=factions,
    )


def _int(text: str | None) -> int | None:
    return int(text) if text and text.isdigit() else None


def _races(data: ContextData, text: str | None, defects: list[Defect]) -> tuple[str, ...]:
    if not text:
        return ()
    found = data.races.get(text.lower())
    if not found:
        defects.append(Defect("race", text, "race absente de races.json (nom ni fichier du client)"))
        return ()
    return found


def _gear(text: str | None, defects: list[Defect]) -> list[GearPiece]:
    """Équipement `emplacement=chaîne=nom` séparé par `;` (P06b, `items.parse_gear`), ancienne forme
    `emplacement:id[:nom]` de P06a encore lue."""
    pieces, bad = parse_gear(str(text or ""))
    for part in bad:
        reason = "objet mal formé : « emplacement=chaîne=nom » ou « emplacement:identifiant:nom » attendu"
        defects.append(Defect("objet", part, reason))
    return pieces


def resolve(data: ContextData, context: Mapping[str, str]) -> Resolved:
    """Contexte du jeu relié à nos données : classe, niveau, race, talents en clés de forever, cible, équipement ; chaque
    élément non relié devient un défaut."""
    defects: list[Defect] = []
    token = str(context.get("class") or "")
    class_name = CLASS_NAMES.get(token)
    if token and class_name is None:
        defects.append(Defect("classe", token, "jeton de classe inconnu (UnitClassBase)"))
    reading = describe_talents(data.talents, token, context.get("talents", "")) if class_name else TalentReading()
    for part in reading.unknown:
        defects.append(Defect("talent", part, f"nœud absent de classes.json ({class_name})"))
    own = _races(data, context.get("race"), defects)
    target_token = context.get("target") or ""
    target_class = CLASS_NAMES.get(target_token)
    if target_token and target_class is None:
        defects.append(Defect("classe", target_token, "jeton de classe de la cible inconnu (UnitClassBase)"))
    target_races = _races(data, context.get("target_race"), defects)
    pieces = _gear(context.get("gear"), defects)
    faction = (context.get("faction") or "").lower() or None
    race = own[0] if len(own) == 1 else None
    if len(own) > 1 and faction:  # même fichier du client pour deux races : la faction tranche
        same = [r for r in own if data.factions.get(r) == faction]
        race = same[0] if len(same) == 1 else None
    return Resolved(
        class_token=token,
        class_name=class_name,
        level=_int(context.get("level")),
        race=race,
        faction=faction,
        zone=context.get("zone") or None,
        reading=reading,
        current={t.key: t.rank for t in reading.known if t.rank > 0},
        target_class=target_class,
        target_level=_int(context.get("target_level")),
        target_races=target_races,
        gear=[(str(p.slot), p.item.item, p.name) for p in pieces],
        defects=defects,
        pieces=pieces,
        xp=xp_context(context),
        professions=professions_context(context),
    )


def context_notes(resolved: Resolved) -> str:
    """Lignes ajoutées au message, après le contexte brut : talents en clés de forever, cible et équipement reliés ;
    jamais un élément non relié (journalisé comme défaut par le pont)."""
    lines = []
    if resolved.reading.known:
        lines.append(
            "Talents actuels (clés de forever, pour `current` de forever_build) : "
            + talents_line(TalentReading(known=resolved.reading.known))
        )
    if resolved.target_class:
        level = resolved.target_level if resolved.target_level is not None else "inconnu (caché)"
        races = " ou ".join(resolved.target_races) or "inconnue"
        lines.append(f"Cible (joueur) : {resolved.target_class}, niveau {level}, race {races}")
    if resolved.pieces:
        names = ", ".join(_piece_text(p) for p in resolved.pieces)
        lines.append(f"Équipement ({EQUIPMENT_NOTE}) : {names}")
    return "\n".join(lines)


def _piece_text(piece: GearPiece) -> str:
    """« Nom (enchantement 1883, suffixe aléatoire -12) » : identifiants lus dans le lien, sans interprétation."""
    item = piece.item
    extras = [f"enchantement {item.enchant}"] if item.enchant else []
    if item.gems:
        extras.append("gemmes " + "/".join(str(g) for g in item.gems))
    if item.suffix:
        extras.append(f"suffixe aléatoire {item.suffix}")
    name = piece.name or f"objet {item.item}"
    return f"{name} ({', '.join(extras)})" if extras else name


@dataclass(frozen=True)
class XpContext:
    """T04f : état des bonus d'XP envoyé par ForeverBridge 0.2.0 (repos, zone de repos, auras d'XP actives, objets
    surveillés portés)."""

    rested: float | None = None
    resting: bool | None = None
    auras: tuple[ActiveAura, ...] = ()
    items: Mapping[int, int] = field(default_factory=dict)


def _float(text: str | None) -> float | None:
    try:
        return float(text) if text not in (None, "") else None
    except ValueError:
        return None


def xp_context(context: Mapping[str, str]) -> XpContext:
    """État des bonus d'XP lu dans le contexte du jeu ; une valeur illisible est ignorée, jamais devinée."""
    auras = []
    for item in (context.get("xp_auras") or "").split(","):
        spell, _, rest = item.partition(":")
        stacks, _, remaining = rest.partition(":")
        if spell.isdigit() and stacks.isdigit():
            auras.append(ActiveAura(int(spell), int(stacks), _float(remaining)))
    items = {}
    for item in (context.get("xp_items") or "").split(","):
        key, _, count = item.partition(":")
        if key.isdigit() and count.isdigit():
            items[int(key)] = int(count)
    resting = {"1": True, "0": False}.get(context.get("resting") or "")
    return XpContext(rested=_float(context.get("rested")), resting=resting, auras=tuple(auras), items=items)


def professions_context(context: Mapping[str, str]) -> dict[str, int] | None:
    """RX1 : métiers envoyés par ForeverBridge 0.3.0 (`Nom:rang:rang maximal`, séparés par des virgules) → nom → rang ;
    None si le jeu ne les a pas envoyés ; une entrée illisible est ignorée."""
    raw = context.get("professions")
    if not raw:
        return None
    out: dict[str, int] = {}
    for entry in raw.split(","):
        parts = entry.rsplit(":", 2)
        if len(parts) == 3 and parts[0].strip() and parts[1].isdigit():
            out[parts[0].strip()] = int(parts[1])
    return out
