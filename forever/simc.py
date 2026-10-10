"""Export de l'addon SimulationCraft collé dans la fenêtre du chat (P06b, décisions 225 et 235).

Bloc A : somme de contrôle et anonymisation de l'export reçu (gardé dans le journal du pont pour devenir la fixture
réelle). La somme est l'adler32 de tout le texte qui précède la ligne `# Checksum: <hex>`, `\\n` final compris,
après `||` → `|`, en hexadécimal minuscule sans zéros de tête (`core.lua` de l'addon). L'anonymisation ne touche que
les lignes qui portent le nom du personnage et le royaume : en-tête `# <Nom> - … - <région>/<royaume>`,
`<classe>="<Nom>"` et `server=<royaume>` ; la somme est vérifiée sur le texte reçu, puis recalculée sur le texte
anonymisé. Bloc D : lecture complète (`parse_simc`)."""

from __future__ import annotations

import re
import zlib
from dataclasses import dataclass, field
from typing import Any

ANON_NAME = "Personnage"
ANON_REALM = "Royaume"
CHECKSUM_PREFIX = "# Checksum: "


_HEADER = re.compile(r"# (?P<name>.+?) - (?P<middle>.* - )?(?P<region>[^ /]*)/(?P<realm>.+)")
_PLAYER = re.compile(r'(?P<cls>[a-z_]+)="(?P<name>.*)"')


def simc_checksum(text_before: str) -> str:
    """Somme de contrôle de l'export (`text_before` : tout ce qui précède la ligne de la somme)."""
    return format(zlib.adler32(text_before.replace("||", "|").encode("utf-8")), "x")


def _split(text: str) -> tuple[str, str | None]:
    """(texte qui précède la ligne de la somme, somme lue) ; somme None si la ligne manque."""
    text = text.replace("\r\n", "\n")
    at = text.rfind("\n" + CHECKSUM_PREFIX)
    if at < 0:
        return text, None
    value = text[at + 1 + len(CHECKSUM_PREFIX) :].strip()
    return text[: at + 1], value.lower()


def checksum_ok(text: str) -> bool | None:
    """Somme de l'export juste ? None si la ligne `# Checksum:` manque. Fins de ligne CRLF ramenées à LF."""
    body, value = _split(text)
    if value is None:
        return None
    return simc_checksum(body) == value


def anonymize_simc(text: str) -> tuple[str, bool | None]:
    """(texte anonymisé, somme d'origine juste ?) ; la ligne de la somme est réécrite sur le texte anonymisé quand elle
    existait."""
    original = checksum_ok(text)
    body, value = _split(text)
    lines = body.split("\n")
    header_done = player_done = False
    for i, line in enumerate(lines):
        if not header_done and (m := _HEADER.fullmatch(line)):
            lines[i] = f"# {ANON_NAME} - {m['middle'] or ''}{m['region']}/{ANON_REALM}"
            header_done = True
        elif not player_done and (m := _PLAYER.fullmatch(line)):
            lines[i] = f'{m["cls"]}="{ANON_NAME}"'
            player_done = True
        elif line.startswith("server="):
            lines[i] = f"server={ANON_REALM.lower()}"
    anonymized = "\n".join(lines)
    if value is not None:
        anonymized += CHECKSUM_PREFIX + simc_checksum(anonymized)
    return anonymized, original


# Emplacements de l'export → numéros d'emplacement du client (`GetInventoryItemLink`, constantes de l'interface).
SLOTS = {
    "head": 1,
    "neck": 2,
    "shoulder": 3,
    "shirt": 4,
    "chest": 5,
    "waist": 6,
    "legs": 7,
    "feet": 8,
    "wrist": 9,
    "hands": 10,
    "finger1": 11,
    "finger2": 12,
    "trinket1": 13,
    "trinket2": 14,
    "back": 15,
    "main_hand": 16,
    "off_hand": 17,
    "ranged": 18,
    "tabard": 19,
}
RANGED_SLOT = 18
_ITEM_NAME = re.compile(r"# (?P<name>.+) \((?P<ilvl>\d+)\)")
_INFO = re.compile(r"# (?P<key>[a-z_]+)=(?P<value>.*)")
_SHEET_START = "### Additional Character Info"


@dataclass(frozen=True)
class SimcItem:
    slot: int
    item: int
    enchant: int = 0
    gems: tuple[int, ...] = ()
    bonus: tuple[int, ...] = ()
    name: str = ""
    ilvl: int | None = None
    extra: dict[str, str] = field(default_factory=dict)


@dataclass
class SimcExport:
    name: str | None = None
    class_token: str | None = None
    level: int | None = None
    race: str | None = None
    region: str | None = None
    server: str | None = None
    role: str | None = None
    spec: str | None = None
    professions: dict[str, int] = field(default_factory=dict)
    client_version: str | None = None
    talents_string: str | None = None  # chaîne d'import du client, gardée brute (jamais décodée, décision 235)
    items: dict[str, SimcItem] = field(default_factory=dict)
    sheet: dict[str, dict[str, Any]] = field(default_factory=dict)
    ratings: dict[str, tuple[float, float]] = field(default_factory=dict)
    skills: dict[int, tuple[int, ...]] = field(default_factory=dict)
    buffs: dict[int, int] = field(default_factory=dict)
    checksum_ok: bool | None = None
    warnings: list[str] = field(default_factory=list)


def _number(text: str) -> float | int | str:
    try:
        value = float(text)
    except ValueError:
        return text
    return int(value) if value.is_integer() and "." not in text else value


def _ints(text: str) -> tuple[int, ...]:
    return tuple(int(x) for x in text.split("/") if x.strip().lstrip("-").isdigit())


def _item(slot: str, value: str, comment: str | None) -> SimcItem | None:
    fields = dict(part.partition("=")[::2] for part in value.split(",") if "=" in part)
    if not fields.get("id", "").isdigit():
        return None
    name, ilvl = "", None
    if comment and (m := _ITEM_NAME.fullmatch(comment)):
        name, ilvl = m["name"], int(m["ilvl"])
    known = {"id", "enchant_id", "gem_id", "bonus_id"}
    return SimcItem(
        slot=SLOTS[slot],
        item=int(fields["id"]),
        enchant=int(fields["enchant_id"]) if fields.get("enchant_id", "").isdigit() else 0,
        gems=_ints(fields.get("gem_id", "")),
        bonus=_ints(fields.get("bonus_id", "")),
        name=name,
        ilvl=ilvl,
        extra={k: v for k, v in fields.items() if k not in known},
    )


def _info(export: SimcExport, key: str, value: str) -> None:
    """Ligne `# clé=a:v/b:v` de la fiche ; une ligne vide (API absente) n'ajoute rien."""
    if not value.strip():
        return
    entries = [e.split(":") for e in value.split("/") if e]
    if key == "skills":
        export.skills = {int(e[0]): tuple(int(x) for x in e[1:] if x.lstrip("-").isdigit()) for e in entries
                         if e[0].isdigit()}  # fmt: skip
    elif key == "buffs":
        export.buffs = {int(e[0]): int(e[1]) if len(e) > 1 and e[1].isdigit() else 0 for e in entries if e[0].isdigit()}
    elif key == "combat_ratings":
        export.ratings = {e[0]: (float(e[1]), float(e[2])) for e in entries if len(e) >= 3}
    else:
        values: dict[str, Any] = {}
        for e in entries:
            numbers = [_number(x) for x in e[1:]]
            values[e[0]] = numbers[0] if len(numbers) == 1 else numbers
        export.sheet[key] = values


def parse_simc(text: str) -> SimcExport:
    """Export lu (bloc D) : en-tête, objets, fiche, notations, compétences, buffs, somme de contrôle. Les objets des
    sacs (lignes commentées) et la chaîne `talents=` commentée sont ignorés ; un talent illisible est un avertissement."""
    export = SimcExport(checksum_ok=checksum_ok(text))
    body, _ = _split(text)
    in_sheet = False
    comment: str | None = None
    for line in body.split("\n"):
        line = line.rstrip()
        if line == _SHEET_START:
            in_sheet = True
            continue
        if line.startswith("#"):
            if export.name is None and (m := _HEADER.fullmatch(line)):
                export.name, export.region = m["name"], m["region"]
            elif line.startswith("# WoW "):
                export.client_version = line[len("# WoW ") :].split(",", 1)[0].strip()
            elif line.startswith("# Unable to export talents"):
                export.warnings.append("talents illisibles dans l'export : les talents du jeu font foi")
            elif in_sheet and (m := _INFO.fullmatch(line)):
                _info(export, m["key"], m["value"])
            comment = line
            continue
        key, sep, value = line.partition("=")
        if not sep:
            comment = None
            continue
        if export.class_token is None and value.startswith('"') and value.endswith('"'):
            export.class_token, export.name = key, value[1:-1]
        elif key == "level" and value.isdigit():
            export.level = int(value)
        elif key in ("race", "region", "server", "role", "spec"):
            setattr(export, key, value)
        elif key == "professions":
            export.professions = {
                n: int(v) for n, _, v in (p.partition("=") for p in value.split("/")) if n and v.isdigit()
            }
        elif key == "talents":
            export.talents_string = value or None
        elif key in SLOTS:
            item = _item(key, value, comment)
            if item is not None:
                export.items[key] = item
        comment = None
    return export


def simc_gaps(export: SimcExport, profile: Any, context_gear: Any) -> tuple[list[Any], list[str]]:
    """(écarts avec le profil, avertissements). L'export apporte la fiche (`sheet`, source `simulationcraft`) ; les
    objets sont recoupés avec l'équipement du contexte du même message, qui fait foi (suffixe aléatoire, emplacement
    à distance absent de l'export) : un recoupement qui ne tient pas est un avertissement, jamais un écart."""
    from forever.bridge.profile_gap import Gap

    gaps = []
    sheet = {k: v for k, v in export.sheet.items()}
    if sheet:
        sheet["ratings"] = {k: list(v) for k, v in export.ratings.items()}
        known = (profile or {}).get("sheet") if profile is not None else None
        comparable = {k: v for k, v in (known or {}).items() if k != "read_at"}
        if comparable != sheet:
            gaps.append(Gap("sheet", known, sheet))
    warnings = list(export.warnings)
    by_slot = {p.slot: p for p in context_gear or []}
    exported = {i.slot: i for i in export.items.values()}
    if RANGED_SLOT in by_slot and RANGED_SLOT not in exported:
        warnings.append(
            f"emplacement {RANGED_SLOT} à distance absent de l'export : pris du contexte du jeu "
            f"({by_slot[RANGED_SLOT].name or by_slot[RANGED_SLOT].item.item})"
        )
    for slot, item in sorted(exported.items()):
        piece = by_slot.get(slot)
        if piece is None:
            warnings.append(f"emplacement {slot} : {item.name or item.item} dans l'export, absent du contexte du jeu")
        elif (piece.item.item, piece.item.enchant) != (item.item, item.enchant):
            warnings.append(
                f"emplacement {slot} : l'export ({item.item}, enchantement {item.enchant}) et le jeu "
                f"({piece.item.item}, enchantement {piece.item.enchant}) diffèrent : le jeu fait foi"
            )
    return gaps, warnings
