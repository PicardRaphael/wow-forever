"""Consultation des familiers du Chasseur (CH0, bloc D) : lit `pets.json`, `pet_rules.json`, Forever Bestiary, sa
sauvegarde et Questie sur disque (jamais par le réseau), appelle les fonctions pures de `forever/pets.py` et ajoute
la provenance (version du jeu, empreinte des données, version et empreinte de l'addon, date de sa base, date de la
carte communautaire, date de ma sauvegarde). La CLI (`forever pets …`) et le MCP (`forever_lookup(kind="pets")`)
appellent ces fonctions."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from forever.config import Deps
from forever.errors import DataSchemaError, InvalidArgumentError, PathNotFoundError
from forever.freshness import freshness_for_version
from forever.gamedata import read_pets
from forever.pets import (
    ability_sheet,
    beast_sheet,
    crosscheck,
    family_sheet,
    resolve_name,
    rules_sheet,
    tame_guide,
)
from forever.pipeline.bestiary import ADDON_NAME, read_bestiary, read_bestiary_saved
from forever.pipeline.questie import TOC_NAME, QuestieDB, npc_level_ranges, read_questie
from forever.provenance import Certainty, Provenance, make_provenance
from forever.store import VersionData, load_version

PET_RULES_FILE = "pet_rules.json"
SAVED_NAME = "ForeverBestiary.lua"


class _Sources:
    """Sources lues une fois par consultation, avec leurs notes de provenance."""

    def __init__(
        self,
        deps: Deps,
        *,
        addon_dir: Path | None = None,
        saved_path: Path | None = None,
        questie_dir: Path | None = None,
    ) -> None:
        self.deps = deps
        self.version: VersionData = load_version(deps)
        pets = read_pets(self.version)
        if pets is None:
            raise DataSchemaError(f"pets.json absent de {self.version.game_version} : familiers non installés (CH0).")
        self.pets: dict[str, Any] = pets
        rules_path = self.version.path / PET_RULES_FILE
        self.rules: dict[str, Any] = self.version.read_json(PET_RULES_FILE) if rules_path.is_file() else {"rules": {}}
        self.notes: list[str] = []
        wow = deps.wow_dir
        addon_dir = addon_dir or (wow / "Interface" / "AddOns" / ADDON_NAME if wow else None)
        self.bestiary: dict[str, Any] | None = None
        if addon_dir is not None and addon_dir.is_dir():
            try:
                self.bestiary = read_bestiary(addon_dir)
            except PathNotFoundError:
                self.bestiary = None
        if self.bestiary is None:
            self.notes.append("Forever Bestiary absent : fiches du client seules, aucune bête ni coordonnée")
        else:
            info = self.bestiary["info"]
            self.notes.append(
                f"source des bêtes : Forever Bestiary {info['version']} (empreinte {info['fingerprint']}, base du "
                f"{info['date']} figée sur le client {info['client_build']}) ; carte communautaire du "
                f"{info['community_date']} ({info['community_players']} joueurs) ; relevés de joueurs, suppose"
            )
        self.saved_path = saved_path or self._find_saved(wow)
        self.saved: dict[str, Any] | None = None
        if self.saved_path is not None and self.saved_path.is_file():
            self.saved = read_bestiary_saved(self.saved_path)
            stamp = datetime.fromtimestamp(self.saved_path.stat().st_mtime, tz=UTC).date().isoformat()
            self.notes.append(f"ma sauvegarde ForeverBestiaryDB du {stamp} (lue sur disque, sans données de tiers)")
        questie_dir = questie_dir or (wow / "Interface" / "AddOns" / "Questie" if wow else None)
        self.questie: QuestieDB | None = None
        if questie_dir is not None and (questie_dir / TOC_NAME).is_file():
            self.questie = read_questie(questie_dir)
            self.notes.append(f"plages de niveau des zones : {self.questie.source}")
        gaps = [str(o) for o in self.pets.get("observations", []) if "Crocilisk" in str(o) or "orpheline" in str(o)]
        self.notes += [f"écart interne au client : {g}" for g in gaps]

    @staticmethod
    def _find_saved(wow: Path | None) -> Path | None:
        if wow is None:
            return None
        found = sorted((wow / "WTF" / "Account").glob(f"*/SavedVariables/{SAVED_NAME}"))
        return found[0] if found else None

    def gaps(self) -> list[dict[str, Any]]:
        if self.bestiary is None:
            return []
        return list(crosscheck(self.pets, self.bestiary, self.questie)["gaps"])

    def provenance(self, certainty: Certainty, extra: list[str] | None = None) -> Provenance:
        fresh = freshness_for_version(self.deps, self.version.game_version, allow_network=False)
        return make_provenance(
            self.deps,
            game_version=self.version.game_version,
            data_sha=self.version.data_sha,
            freshness=fresh["freshness"],
            certainty=certainty,
            assumptions=[*fresh["assumptions"], *self.notes, *(extra or [])],
        )

    def addon_info(self) -> dict[str, Any] | None:
        return dict(self.bestiary["info"]) if self.bestiary is not None else None


def _gap_notes(gaps: list[dict[str, Any]]) -> list[str]:
    return [
        f"écart {g['kind']} {g['subject']}{' ' + str(g['field']) if g['field'] else ''} : "
        + " ; ".join(f"{side} {value}" for side, value in g["values"].items())
        + " (le client fait foi)"
        for g in gaps
    ]


def lookup_pets(
    deps: Deps,
    name: str | None = None,
    *,
    rank: int | None = None,
    zone: str | None = None,
    level: int | None = None,
    detail: bool = False,
    addon_dir: Path | None = None,
    saved_path: Path | None = None,
    questie_dir: Path | None = None,
) -> dict[str, Any]:
    """`name` absent : règles ; famille, capacité ou bête : sa fiche ; avec `zone` et `level` : guide."""
    src = _Sources(deps, addon_dir=addon_dir, saved_path=saved_path, questie_dir=questie_dir)
    if not name:
        return {"kind": "pets_rules", **rules_sheet(src.rules), "provenance": src.provenance("suppose")}
    target = resolve_name(src.pets, src.bestiary, name)
    if zone is not None:
        return _guide(src, target, rank=rank, zone=zone, level=level)
    gaps = src.gaps()
    if target["kind"] == "family":
        sheet = family_sheet(src.pets, target["key"], gaps)
        extra = _gap_notes(sheet["gaps"])
        return {"kind": "pets_family", **sheet, "provenance": src.provenance("probable", extra)}
    if target["kind"] == "ability":
        sheet = ability_sheet(src.pets, target["key"], src.bestiary, rank=rank, detail=detail)
        extra = _gap_notes([g for g in gaps if g["subject"] == target["key"]])
        return {"kind": "pets_ability", **sheet, "provenance": src.provenance("probable", extra)}
    assert src.bestiary is not None  # une bête n'est résolue que dans l'addon
    npc = src.questie.npc(int(target["key"])) if src.questie is not None else None
    sheet = beast_sheet(
        src.bestiary,
        int(target["key"]),
        src.pets,
        questie_levels=[npc.min_level, npc.max_level] if npc is not None else None,
        gaps=gaps,
    )
    return {"kind": "pets_beast", **sheet, "provenance": src.provenance("suppose", _gap_notes(sheet["gaps"]))}


def _guide(src: _Sources, target: dict[str, Any], *, rank: int | None, zone: str, level: int | None) -> dict[str, Any]:
    from forever.engine.leveling import level_band
    from forever.gamedata import build_game_data
    from forever.leveling import check_level, level_cap

    if src.bestiary is None:
        raise InvalidArgumentError(
            "Guide d'apprivoisement impossible : Forever Bestiary absent (aucune bête ni coordonnée).",
            "installer l'addon Forever Bestiary ou définir FOREVER_WOW_DIR ; les fiches du client restent disponibles",
        )
    if level is None:
        raise InvalidArgumentError(
            "Niveau manquant pour le guide d'apprivoisement.",
            "donner le niveau du Chasseur (profil ou question), jamais une valeur par défaut",
        )
    check_level(level, level_cap(src.version))
    band = level_band(build_game_data(src.version), level)
    ranges = npc_level_ranges(src.questie) if src.questie is not None else {}
    kind = target["kind"]
    out = tame_guide(
        src.pets,
        src.rules,
        src.bestiary,
        level=level,
        zone=zone,
        band=band,
        zone_levels=ranges,
        ability=target["key"] if kind == "ability" else None,
        rank=rank if kind == "ability" else None,
        family=target["key"] if kind == "family" else None,
        beast=int(target["key"]) if kind == "beast" else None,
        saved=src.saved,
        gaps=src.gaps(),
    )
    extra = list(out["assumptions"])
    if src.questie is None:
        extra.append("Questie absent : plages de niveau des zones inconnues, zones voisines non proposées")
    extra.append("bande de niveau du joueur : règle de Classic des couleurs de quête (leveling.quest_band, suppose)")
    return {"kind": "pets_guide", **out, "addon": src.addon_info(), "provenance": src.provenance("suppose", extra)}


def pets_crosscheck(deps: Deps, *, addon_dir: Path | None = None, questie_dir: Path | None = None) -> dict[str, Any]:
    """Recoupement client ↔ Forever Bestiary ↔ Questie, avec provenance."""
    src = _Sources(deps, addon_dir=addon_dir, questie_dir=questie_dir)
    if src.bestiary is None:
        raise InvalidArgumentError(
            "Recoupement impossible : Forever Bestiary absent.",
            "installer l'addon Forever Bestiary ou définir FOREVER_WOW_DIR",
        )
    report = crosscheck(src.pets, src.bestiary, src.questie)
    return {"kind": "pets_crosscheck", **report, "provenance": src.provenance("probable")}


def pets_mine(deps: Deps, *, saved_path: Path | None = None) -> dict[str, Any]:
    """Mes observations et mes familiers (`ForeverBestiaryDB`), sans aucune donnée de tiers."""
    src = _Sources(deps, saved_path=saved_path)
    if src.saved is None:
        raise InvalidArgumentError(
            "Sauvegarde de Forever Bestiary introuvable.",
            "donner WTF/Account/<COMPTE>/SavedVariables/ForeverBestiary.lua ou définir FOREVER_WOW_DIR",
        )
    mine = {k: v for k, v in src.saved["observations"].items() if v.get("mine")}
    return {
        "kind": "pets_mine",
        "pets": src.saved["pets"],
        "history": src.saved["history"],
        "observations": mine,
        "observations_total": len(src.saved["observations"]),
        "provenance": src.provenance("certain"),
    }


def _value(value: Any) -> str:
    return "—" if value is None else str(value)


def render_pets(payload: dict[str, Any]) -> list[str]:
    """Lignes de texte d'un résultat de consultation des familiers (la provenance est ajoutée par l'appelant)."""
    kind = payload["kind"]
    lines: list[str] = []
    if kind == "pets_rules":
        lines.append("Système de familiers du Chasseur (règles absentes du client, relevés de joueurs)")
        for r in payload["rules"]:
            unit = f" {r['unit']}" if r.get("unit") else ""
            value = f" [{r['value']}{unit}]" if r.get("value") is not None else ""
            lines.append(f"- {r['text']}{value} ({r['certainty']}, {r['registry']}, {r['date']} ; {r['source']})")
        lines += [f"- Bug signalé : {b['text']} ({b['certainty']}, {b['date']})" for b in payload["reported_bugs"]]
    elif kind == "pets_family":
        b = payload["bonus"]
        lines.append(f"{payload['name']['fr']} ({payload['name']['en']}) · ligne « {payload['skill_line_name']} »")
        lines.append(
            f"Bonus ({payload['certainty'].get('bonus')}) : dégâts {_value(b['damage_pct'])} %, armure "
            f"{_value(b['armor_pct'])} %, PV {_value(b['health_pct'])} %"
        )
        diet = ", ".join(f"{d['fr']} ({d['en']})" for d in payload["diet"] or []) or "inconnu"
        lines.append(f"Régime ({payload['certainty'].get('diet')}) : {diet}")
        for a in payload["abilities"]:
            ranks = " ; ".join(
                f"rang {r['rank']} niv. {r['level']}, coût {_value(r['training_cost'])}, focus {_value(r['focus_cost'])}"
                for r in a["ranks"]
            )
            lines.append(f"- {a['name']['fr']} ({a['name']['en']}) : {ranks}")
        lines.append("Coût en points d'entraînement : probable (colonne sans nom du client)")
        lines += [f"Écart : {g['kind']} {g['field'] or ''} {g['values']}" for g in payload["gaps"]]
    elif kind == "pets_ability":
        lines.append(f"{payload['name']['fr']} ({payload['name']['en']}) · familles : {', '.join(payload['families'])}")
        for r in payload["ranks"]:
            beasts = f", {r['beasts']} bête(s) de l'addon" if "beasts" in r else ""
            lines.append(
                f"- rang {r['rank']} : niveau {r['level']}, coût {_value(r['training_cost'])}, focus "
                f"{_value(r['focus_cost'])}, recharge {_value(r['cooldown_s'])} s{beasts}"
            )
            lines += [
                f"    {t['name']['en']} (PNJ {t['id']}, {t['family']}, niv. {t['level']}, {', '.join(t['zones'])})"
                for t in r.get("teachers", [])
            ]
    elif kind == "pets_beast":
        lines.append(
            f"{payload['name'].get('en')} (PNJ {payload['id']}) · famille {payload['family']['key']} · niveaux "
            f"addon {payload['level']['addon']}, Questie {payload['level']['questie']}"
        )
        lines.append(
            f"Zones : {', '.join(payload['zones']) or '—'} ; confirmation : {payload['confirmation']['meaning']}"
        )
        lines += [
            f"- enseigne {t['ability']} rang {t['rank']}{' (' + t['label'] + ')' if t['label'] else ''}"
            for t in payload["taught"]
        ]
    elif kind == "pets_guide":
        zone = payload["zone"]
        lines.append(
            f"Guide d'apprivoisement : niveau {payload['level']}, zone {zone['name']['fr']} ({zone['name']['en']}), "
            f"rang le plus haut atteignable {_value(payload['highest_rank'])}"
        )
        for z in payload["zones"]:
            tag = "zone demandée" if z["requested"] else f"zone voisine, PNJ niv. {z['levels']}"
            lines.append(f"{z['name']['fr'] or z['name']['en']} ({tag}) : {len(z['beasts'])} bête(s)")
            for b in z["beasts"]:
                when = "apprivoisable" if b["tameable_now"] else f"apprivoisable au niveau {b['tameable_at']}"
                where = "; ".join(f"{c['x']}, {c['y']} ({c['source']}, {c['date']})" for c in b["coords"][:3])
                lines.append(f"- {b['name'].get('en')} (PNJ {b['id']}, niv. {b['level']}) : {when} ; {where or '—'}")
    elif kind == "pets_crosscheck":
        lines.append(f"Recoupement : {len(payload['gaps'])} écart(s)")
        lines += [f"- {g['kind']} {g['subject']} {g['field'] or ''} : {g['values']}" for g in payload["gaps"]]
    elif kind == "pets_mine":
        for character, entry in payload["pets"].items():
            lines += [
                f"{character} : {a['name']} ({a['family']}, niveau {a['level']}, loyauté {a['loyalty']})"
                for a in entry["active"]
            ]
        lines.append(f"Mes observations : {len(payload['observations'])} sur {payload['observations_total']}")
    return lines
