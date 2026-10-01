"""Savoir des familiers du Chasseur (CH0) : recoupement client ↔ Forever Bestiary ↔ Questie, fiches et guide
d'apprivoisement, en fonctions pures (aucun calcul de combat : filtres et tris de données).

Le client fait foi : un écart avec l'addon ou Questie est listé avec ses deux valeurs et leurs sources, jamais
tranché ; les fiches rendent la valeur du client."""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from forever.errors import InvalidArgumentError
from forever.pipeline.pets import family_key
from forever.pipeline.questie import QuestieDB

GAP_KINDS = (
    "family_missing_addon",
    "family_missing_client",
    "family_bonus",
    "family_diet",
    "family_abilities",
    "ability_missing_client",
    "rank_level",
    "beast_family_unknown",
    "beast_level_questie",
    "beast_zone_questie",
)
GAP_TITLES = {
    "family_missing_addon": "Familles du client absentes de l'addon",
    "family_missing_client": "Familles de l'addon absentes du client",
    "family_bonus": "Bonus de famille différents",
    "family_diet": "Régimes différents",
    "family_abilities": "Capacités d'une famille différentes",
    "ability_missing_client": "Capacités de l'addon absentes du client",
    "rank_level": "Niveau requis d'un rang différent",
    "beast_family_unknown": "Bêtes de l'addon d'une famille inconnue du client",
    "beast_level_questie": "Plage de niveau d'un PNJ différente de Questie",
    "beast_zone_questie": "Zone d'un PNJ différente de Questie",
}


def _sources(pets: Mapping[str, Any], bestiary: Mapping[str, Any], questie: QuestieDB | None) -> dict[str, Any]:
    info = bestiary.get("info", {})
    return {
        "client": f"client {pets.get('build')} (pets.json)",
        "addon": (
            f"Forever Bestiary {info.get('version')} (base du {info.get('date')}, client {info.get('client_build')} ; "
            f"carte communautaire du {info.get('community_date')})"
        ),
        "questie": f"Questie {questie.info.version} (base Classic Era)" if questie is not None else None,
    }


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def crosscheck(
    pets: Mapping[str, Any], bestiary: Mapping[str, Any], questie: QuestieDB | None = None
) -> dict[str, Any]:
    """Écarts entre `pets.json` (client), la base de Forever Bestiary et Questie : chaque écart porte son type
    (`GAP_KINDS`), son sujet, ses deux valeurs et leurs sources."""
    src = _sources(pets, bestiary, questie)
    gaps: list[dict[str, Any]] = []

    def gap(kind: str, subject: str, field: str | None, a: tuple[str, Any], b: tuple[str, Any]) -> None:
        gaps.append(
            {
                "kind": kind,
                "subject": subject,
                "field": field,
                "values": {a[0]: a[1], b[0]: b[1]},
                "sources": {a[0]: src[a[0]], b[0]: src[b[0]]},
            }
        )

    aliases = pets.get("aliases", {})
    client_fams: Mapping[str, Any] = pets.get("families", {})
    addon_fams: Mapping[str, Any] = {aliases.get(k, k): v for k, v in bestiary.get("families", {}).items()}
    for key in sorted(set(client_fams) - set(addon_fams)):
        gap("family_missing_addon", key, None, ("client", client_fams[key]["name"]["en"]), ("addon", None))
    for key in sorted(set(addon_fams) - set(client_fams)):
        gap("family_missing_client", key, None, ("client", None), ("addon", addon_fams[key]["name"].get("en")))
    common = sorted(set(client_fams) & set(addon_fams))
    for key in common:
        ours, theirs = client_fams[key], addon_fams[key]
        for field, value in ours.get("bonus", {}).items():
            other = theirs.get("bonus", {}).get(field)
            if _number(value) is not None and _number(other) is not None and _number(value) != _number(other):
                gap("family_bonus", key, field, ("client", value), ("addon", other))
        diet = [d["en"] for d in ours.get("diet") or []]
        if ours.get("diet") is not None and sorted(diet) != sorted(theirs.get("diet", [])):
            gap("family_diet", key, None, ("client", diet), ("addon", list(theirs.get("diet", []))))
        mine = sorted(ours.get("abilities", []))
        listed = sorted(family_key(a) for a in theirs.get("abilities", []))
        if mine != listed:
            gap("family_abilities", key, None, ("client", mine), ("addon", listed))

    client_abilities: Mapping[str, Any] = pets.get("abilities", {})
    for name, ability in sorted(bestiary.get("abilities", {}).items()):
        key = family_key(name)
        client = client_abilities.get(key)
        if client is None:
            gap("ability_missing_client", key, None, ("client", None), ("addon", name))
            continue
        levels = {r["rank"]: r["level"] for r in client.get("ranks", [])}
        for r in ability.get("ranks", []):
            rank, level = r.get("rank"), r.get("level")
            if level is not None and rank in levels and levels[rank] != level:
                gap("rank_level", key, f"rang {rank}", ("client", levels[rank]), ("addon", level))

    beasts = bestiary.get("beasts", [])
    zone_names = questie.zone_names() if questie is not None else {}
    for b in beasts:
        subject = str(b.get("id"))
        family = _family_of(aliases, b.get("family"))
        if family not in client_fams:
            gap("beast_family_unknown", subject, "famille", ("client", None), ("addon", b.get("family")))
        if questie is None or not isinstance(b.get("id"), int):
            continue
        npc = questie.npc(b["id"])
        if npc is None:
            continue
        if [npc.min_level, npc.max_level] != list(b.get("level", [])):
            gap(
                "beast_level_questie",
                subject,
                "niveau",
                ("questie", [npc.min_level, npc.max_level]),
                ("addon", b["level"]),
            )
        zone = zone_names.get(npc.zone_id)
        if zone and b.get("zones") and zone not in b["zones"]:
            gap("beast_zone_questie", subject, "zone", ("questie", zone), ("addon", list(b["zones"])))

    order = {k: i for i, k in enumerate(GAP_KINDS)}
    gaps.sort(key=lambda g: (order[g["kind"]], g["subject"], str(g["field"])))
    return {
        "sources": src,
        "counts": {
            "families_client": len(client_fams),
            "families_addon": len(addon_fams),
            "families_compared": len(common),
            "abilities_addon": len(bestiary.get("abilities", {})),
            "beasts": len(beasts),
            "beasts_in_questie": sum(
                1 for b in beasts if questie is not None and isinstance(b.get("id"), int) and questie.npc(b["id"])
            ),
        },
        "gaps": gaps,
    }


def _cell(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) or "—"
    return str(value).replace("|", "\\|")


def render_crosscheck_markdown(report: Mapping[str, Any]) -> str:
    """Rapport Markdown déterministe du recoupement (`docs/research/familiers-recoupement.md`)."""
    src, counts = report["sources"], report["counts"]
    lines = [
        "# Familiers du Chasseur : recoupement client ↔ Forever Bestiary ↔ Questie",
        "",
        "Rapport généré par `forever pets crosscheck --markdown` : ne pas éditer à la main. Le client fait foi ;",
        "chaque écart est listé avec ses deux valeurs et leurs sources, jamais tranché.",
        "",
        f"- Client : {src['client']}",
        f"- Addon : {src['addon']}",
        f"- Questie : {src['questie'] or 'non lu'}",
        (
            f"- Familles : {counts['families_client']} dans le client, {counts['families_addon']} dans l'addon, "
            f"{counts['families_compared']} comparées ; capacités de l'addon : {counts['abilities_addon']} ; "
            f"bêtes de l'addon : {counts['beasts']} (dont {counts['beasts_in_questie']} dans Questie)"
        ),
        f"- Écarts : {len(report['gaps'])}",
        "",
    ]
    for kind in GAP_KINDS:
        rows = [g for g in report["gaps"] if g["kind"] == kind]
        if not rows:
            continue
        lines += [f"## {GAP_TITLES[kind]} ({len(rows)})", ""]
        sides = list(rows[0]["values"])
        lines += [
            f"| Sujet | Champ | {sides[0]} | {sides[1]} |",
            "| --- | --- | --- | --- |",
        ]
        lines += [
            f"| {_cell(g['subject'])} | {_cell(g['field'])} | {_cell(g['values'][sides[0]])} | "
            f"{_cell(g['values'][sides[1]])} |"
            for g in rows
        ]
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


# --- Fiches et guide (bloc D) ------------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    """Nom comparable : minuscules, sans accents, mots séparés par une espace."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()
    return " ".join(re.findall(r"[a-z0-9]+", plain))


def _suggest(name: str, labels: Sequence[str], n: int = 5) -> list[str]:
    by_norm: dict[str, str] = {}
    for label in labels:
        by_norm.setdefault(normalize_text(label), label)
    close = difflib.get_close_matches(normalize_text(name), list(by_norm), n=n, cutoff=0.5)
    return [by_norm[c] for c in close]


def resolve_zone(pets: Mapping[str, Any], name: str) -> dict[str, Any]:
    """Zone du client (`maps` de pets.json) par son nom français ou anglais ; InvalidArgumentError qui liste des
    candidats si aucune ne correspond."""
    wanted = normalize_text(name)
    maps: Mapping[str, Any] = pets.get("maps", {})
    found = [
        (key, m)
        for key, m in maps.items()
        if wanted in (normalize_text(m["name"].get("en") or ""), normalize_text(m["name"].get("fr") or ""))
    ]
    if not found:
        labels = [m["name"][loc] for m in maps.values() for loc in ("fr", "en") if m["name"].get(loc)]
        raise InvalidArgumentError(
            f"Zone inconnue : « {name} ».",
            "donner le nom français ou anglais d'une zone du client",
            suggestions=_suggest(name, labels),
        )
    english = {m["name"]["en"] for _, m in found}
    if len(english) > 1:
        raise InvalidArgumentError(
            f"Zone ambiguë : « {name} ».",
            "préciser le nom anglais de la zone",
            suggestions=sorted(english),
        )
    # même nom porté par plusieurs cartes du client : celle qui a un parent, sinon la plus petite
    key, entry = min(found, key=lambda km: (km[1]["parent"] == 0, int(km[0])))
    out = {"map_id": key, "name": dict(entry["name"]), "continent": entry["continent"], "parent": entry["parent"]}
    if len(found) > 1:
        out["note"] = f"{len(found)} cartes du client portent ce nom ({', '.join(k for k, _ in found)}) : {key} retenue"
    return out


def _candidates(pets: Mapping[str, Any], bestiary: Mapping[str, Any] | None) -> list[tuple[str, Any, list[str]]]:
    """(kind, clé, noms) de chaque entité nommable."""
    out: list[tuple[str, Any, list[str]]] = []
    aliases: Mapping[str, str] = pets.get("aliases", {})
    for key, fam in pets.get("families", {}).items():
        names = [key, fam["name"].get("en") or "", fam["name"].get("fr") or ""]
        names += [alias for alias, target in aliases.items() if target == key]
        out.append(("family", key, names))
    for key, ability in pets.get("abilities", {}).items():
        out.append(("ability", key, [key, ability["name"].get("en") or "", ability["name"].get("fr") or ""]))
    if bestiary is not None:
        community = bestiary.get("community", {}).get("beasts", {})
        for b in bestiary.get("beasts", []):
            names = [b["name"].get("en") or "", b["name"].get("es") or ""]
            names += list(community.get(str(b["id"]), {}).get("names", {}).values())
            out.append(("beast", b["id"], names))
        known = {b["id"] for b in bestiary.get("beasts", [])}
        for npc, obs in community.items():
            if int(npc) not in known:
                out.append(("beast", int(npc), list(obs.get("names", {}).values())))
    return out


def resolve_name(pets: Mapping[str, Any], bestiary: Mapping[str, Any] | None, name: str) -> dict[str, Any]:
    """Famille, capacité ou bête par son nom (français, anglais, clé, alias ; casse et accents ignorés) :
    `{"kind": "family" | "ability" | "beast", "key": …}` ; InvalidArgumentError qui liste les candidats si le nom
    est ambigu ou inconnu."""
    wanted = normalize_text(name)
    if wanted.isdigit() and bestiary is not None:
        ids = {b["id"] for b in bestiary.get("beasts", [])} | {
            int(k) for k in bestiary.get("community", {}).get("beasts", {})
        }
        if int(wanted) in ids:
            return {"kind": "beast", "key": int(wanted)}
    candidates = _candidates(pets, bestiary)
    found: dict[tuple[str, Any], str] = {}
    for kind, key, names in candidates:
        for label in names:
            if label and normalize_text(label) == wanted:
                found.setdefault((kind, key), label)
    if len(found) == 1:
        kind, key = next(iter(found))
        return {"kind": kind, "key": key}
    if found:
        raise InvalidArgumentError(
            f"Nom ambigu : « {name} ».",
            "préciser la famille, la capacité ou la bête (identifiant de PNJ pour une bête)",
            suggestions=[f"{label} ({kind} {key})" for (kind, key), label in sorted(found.items(), key=str)],
        )
    labels = [label for _, _, names in candidates for label in names if label]
    raise InvalidArgumentError(
        f"Nom inconnu : « {name} ».",
        "donner une famille, une capacité ou une bête (nom français ou anglais)",
        suggestions=_suggest(name, labels),
    )


def rules_sheet(rules: Mapping[str, Any]) -> dict[str, Any]:
    """Règles du système de familiers (`pet_rules.json`), une par entrée, avec source, date, certitude, registre."""
    return {
        "rules": [{"key": key, **rule} for key, rule in rules.get("rules", {}).items()],
        "reported_bugs": list(rules.get("reported_bugs", [])),
        "source": rules.get("source"),
    }


def _rank_row(rank: Mapping[str, Any], training_cost: Any) -> dict[str, Any]:
    return {
        "rank": rank["rank"],
        "spell_id": rank["spell_id"],
        "level": rank["level"],
        "training_cost": training_cost,
        "focus_cost": rank.get("focus_cost"),
        "cooldown_s": rank.get("cooldown_s"),
        "description": rank.get("description"),
        "tooltip_values": rank.get("tooltip_values"),
    }


def _gaps_about(gaps: Sequence[Mapping[str, Any]] | None, subjects: set[str]) -> list[dict[str, Any]]:
    return [dict(g) for g in gaps or [] if str(g.get("subject")) in subjects]


def family_sheet(pets: Mapping[str, Any], key: str, gaps: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Fiche d'une famille : noms, bonus, régime, capacités et rangs (niveau, coût propre à la famille, focus,
    recharge), certitude par champ, écarts du recoupement."""
    fam = pets["families"][key]
    abilities = []
    for ability_key in fam["abilities"]:
        ability = pets["abilities"][ability_key]
        costs = fam.get("training_costs", {}).get(ability_key, [])
        ranks = [
            _rank_row(r, costs[i] if i < len(costs) else r.get("training_cost")) for i, r in enumerate(ability["ranks"])
        ]
        abilities.append({"key": ability_key, "name": ability["name"], "kind": ability["kind"], "ranks": ranks})
    certainty = dict(fam.get("certainty", {}))
    certainty.update({"level": "certain", "training_cost": fam.get("certainty", {}).get("training_costs", "probable")})
    return {
        "key": key,
        "family_id": fam["family_id"],
        "name": fam["name"],
        "skill_line_name": fam.get("skill_line_name"),
        "bonus": fam["bonus"],
        "diet": fam["diet"],
        "abilities": abilities,
        "certainty": certainty,
        "gaps": _gaps_about(gaps, {key}),
    }


def _teaches(beast: Mapping[str, Any], ability_name: str, rank: int | None) -> bool:
    return any(
        normalize_text(str(t.get("ability") or "")) == normalize_text(ability_name)
        and (rank is None or t.get("rank") == rank)
        for t in beast.get("taught", [])
    )


def _beast_brief(beast: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": beast["id"],
        "name": beast["name"],
        "family": beast.get("family"),
        "level": beast.get("level"),
        "zones": beast.get("zones", []),
    }


def ability_sheet(
    pets: Mapping[str, Any],
    key: str,
    bestiary: Mapping[str, Any] | None = None,
    rank: int | None = None,
    detail: bool = False,
) -> dict[str, Any]:
    """Fiche d'une capacité : rangs, familles, nombre de bêtes de l'addon qui enseignent chaque rang (liste avec
    `detail`)."""
    ability = pets["abilities"][key]
    english = ability["name"]["en"]
    ranks = []
    for r in ability["ranks"]:
        if rank is not None and r["rank"] != rank:
            continue
        row = _rank_row(r, r.get("training_cost"))
        row["teach_spell_id"] = r.get("teach_spell_id")
        if bestiary is not None:
            teachers = [b for b in bestiary.get("beasts", []) if _teaches(b, english, r["rank"])]
            row["beasts"] = len(teachers)
            if detail:
                row["teachers"] = [_beast_brief(b) for b in teachers]
        ranks.append(row)
    if rank is not None and not ranks:
        raise InvalidArgumentError(
            f"Rang {rank} inconnu pour {english}.",
            f"choisir un rang parmi {', '.join(str(r['rank']) for r in ability['ranks'])}",
        )
    return {
        "key": key,
        "name": ability["name"],
        "ability_kind": ability["kind"],
        "families": ability["families"],
        "training_costs_by_family": {
            fam: pets["families"][fam].get("training_costs", {}).get(key) for fam in ability["families"]
        },
        "ranks": ranks,
        "certainty": dict(ability.get("certainty", {})),
    }


def beast_sheet(
    bestiary: Mapping[str, Any],
    beast_id: int,
    pets: Mapping[str, Any],
    questie_levels: list[int] | None = None,
    gaps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Fiche d'une bête : famille, niveaux (addon et Questie), zones, coordonnées, rangs enseignés et leur marque,
    vitesse, observations de la carte communautaire."""
    beast = next((b for b in bestiary.get("beasts", []) if b["id"] == beast_id), None)
    community = bestiary.get("community", {}).get("beasts", {}).get(str(beast_id))
    if beast is None and community is None:
        raise InvalidArgumentError(f"Bête inconnue : {beast_id}.", "donner un PNJ de Forever Bestiary")
    family = (beast or {}).get("family") or (community or {}).get("family")
    key = pets.get("aliases", {}).get(family, family)
    fam = pets.get("families", {}).get(key)
    info = bestiary.get("info", {})
    return {
        "id": beast_id,
        "name": (beast or {}).get("name") or {"en": (community or {}).get("names", {}).get("enUS")},
        "names_by_locale": (community or {}).get("names", {}),
        "family": {"key": key, "name": fam["name"] if fam else None, "in_client": fam is not None},
        "level": {"addon": (beast or community or {}).get("level"), "questie": questie_levels},
        "rank": (beast or {}).get("rank"),
        "speed_s": (beast or {}).get("speed_s") if beast else (community or {}).get("speed_s"),
        "zones": (beast or {}).get("zones", []),
        "coords": (beast or {}).get("coords", {}),
        "taught": (beast or {}).get("taught", []),
        "confirmation": (beast or {}).get("confirmation")
        or {"code": "community", "meaning": "découverte de la carte communautaire, absente de la base de l'addon"},
        "community": community,
        "sources": {"addon": f"Forever Bestiary {info.get('version')} (base du {info.get('date')})"},
        "gaps": _gaps_about(gaps, {str(beast_id)}),
    }


def _family_of(aliases: Mapping[str, str], family: Any) -> str | None:
    """Clé de famille du client d'une famille de l'addon (alias résolu)."""
    return aliases.get(family, family) if isinstance(family, str) else None


def _unix_date(ts: Any) -> str | None:
    if not isinstance(ts, int | float) or isinstance(ts, bool):
        return None
    return datetime.fromtimestamp(ts, tz=UTC).date().isoformat()


def _overlaps(levels: Sequence[int] | None, band: tuple[int, int]) -> bool:
    return bool(levels) and levels is not None and levels[0] <= band[1] and levels[1] >= band[0]


def tame_guide(
    pets: Mapping[str, Any],
    rules: Mapping[str, Any],
    bestiary: Mapping[str, Any],
    *,
    level: int | None,
    zone: str,
    band: tuple[int, int],
    zone_levels: Mapping[str, list[int]],
    ability: str | None = None,
    rank: int | None = None,
    family: str | None = None,
    beast: int | None = None,
    saved: Mapping[str, Any] | None = None,
    gaps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Guide d'apprivoisement : bêtes qui enseignent le rang (ou de la famille, ou la bête) dans la zone demandée,
    puis dans les zones du même continent dont la plage de niveau des PNJ normaux (`zone_levels`, Questie) recoupe
    la bande de niveau du joueur (`band`) ; apprivoisable maintenant selon `tame.level_margin`, sinon le niveau où
    elle le devient ; rang le plus haut atteignable au niveau donné ; certitude par champ."""
    if level is None:
        raise InvalidArgumentError(
            "Niveau manquant pour le guide d'apprivoisement.",
            "donner le niveau du Chasseur (profil ou question), jamais une valeur par défaut",
        )
    if sum(x is not None for x in (ability, family, beast)) != 1:
        raise InvalidArgumentError("Cible du guide manquante.", "donner une capacité, une famille ou une bête")
    margin_rule = rules["rules"]["tame.level_margin"]
    margin = int(margin_rule["value"])
    requested = resolve_zone(pets, zone)
    maps: Mapping[str, Any] = pets.get("maps", {})
    map_by_name = {m["name"]["en"]: (k, m) for k, m in sorted(maps.items(), key=lambda km: int(km[0]))}
    aliases: Mapping[str, str] = pets.get("aliases", {})
    info = bestiary.get("info", {})
    community = bestiary.get("community", {}).get("beasts", {})
    saved_obs = (saved or {}).get("observations", {})
    assumptions: list[str] = []
    if requested.get("note"):
        assumptions.append(requested["note"])

    target: dict[str, Any]
    highest: int | None = None
    english = ""
    if ability is not None:
        resolved = resolve_name(pets, bestiary, ability)
        if resolved["kind"] != "ability":
            raise InvalidArgumentError(f"« {ability} » n'est pas une capacité.", "donner une capacité de familier")
        client = pets["abilities"][resolved["key"]]
        levels = {r["rank"]: r["level"] for r in client["ranks"]}
        reachable = [r for r, lv in levels.items() if lv <= level]
        highest = max(reachable) if reachable else None
        wanted_rank = rank if rank is not None else highest
        if wanted_rank is not None and wanted_rank not in levels:
            raise InvalidArgumentError(
                f"Rang {wanted_rank} inconnu pour {client['name']['en']}.",
                f"choisir un rang parmi {', '.join(str(r) for r in sorted(levels))}",
            )
        target = {
            "kind": "ability",
            "key": resolved["key"],
            "name": client["name"],
            "rank": wanted_rank,
            "rank_level": levels.get(wanted_rank) if wanted_rank is not None else None,
            "reachable": wanted_rank is not None and levels[wanted_rank] <= level,
            "applies_to": rules["rules"].get("training.rank_level_applies_to", {}).get("value"),
        }
        english = client["name"]["en"]

        def matches(b: Mapping[str, Any]) -> bool:
            return _teaches(b, english, wanted_rank)

    elif family is not None:
        resolved = resolve_name(pets, bestiary, family)
        if resolved["kind"] != "family":
            raise InvalidArgumentError(f"« {family} » n'est pas une famille.", "donner une famille de familier")
        fam_key = str(resolved["key"])
        target = {"kind": "family", "key": fam_key, "name": pets["families"][fam_key]["name"]}

        def matches(b: Mapping[str, Any]) -> bool:
            return _family_of(aliases, b.get("family")) == fam_key

    else:
        target = {"kind": "beast", "key": beast}

        def matches(b: Mapping[str, Any]) -> bool:
            return b.get("id") == beast

    # bêtes candidates : base de l'addon, puis découvertes de la carte absentes de la base
    pool: list[dict[str, Any]] = [dict(b) for b in bestiary.get("beasts", [])]
    known = {b["id"] for b in pool}
    for npc, obs in community.items():
        if int(npc) in known:
            continue
        zones = sorted({maps[m]["name"]["en"] for m in obs.get("positions", {}) if m in maps})
        pool.append(
            {
                "id": int(npc),
                "name": {"en": obs.get("names", {}).get("enUS"), "es": obs.get("names", {}).get("esES")},
                "family": obs.get("family"),
                "level": obs.get("level"),
                "rank": obs.get("classification"),
                "speed_s": obs.get("speed_s"),
                "zones": zones,
                "coords": {},
                "taught": [],
                "confirmation": {"code": "community", "meaning": "découverte de la carte communautaire"},
            }
        )
    selected = [b for b in pool if matches(b)]

    def entry_for(b: Mapping[str, Any], zone_en: str, map_id: str | None) -> dict[str, Any]:
        low = (b.get("level") or [None])[0]
        now = isinstance(low, int) and low <= level + margin
        obs = community.get(str(b["id"]), {})
        coords: list[dict[str, Any]] = [
            {"source": "addon", "zone": zone_en, "map_id": map_id, "x": p[0], "y": p[1], "date": info.get("date")}
            for p in b.get("coords", {}).get(zone_en, [])
        ]
        for p in obs.get("positions", {}).get(map_id or "", []):
            coords.append(
                {
                    "source": "community",
                    "zone": zone_en,
                    "map_id": map_id,
                    "x": p["x"],
                    "y": p["y"],
                    "date": info.get("community_date"),
                    "seen": _unix_date(p.get("t")),
                }
            )
        for p in saved_obs.get(str(b["id"]), {}).get("positions", {}).get(map_id or "", []):
            coords.append(
                {
                    "source": "mine",
                    "zone": zone_en,
                    "map_id": map_id,
                    "x": p["x"],
                    "y": p["y"],
                    "date": _unix_date(p.get("t")),
                }
            )
        names_fr = obs.get("names", {}).get("frFR") or saved_obs.get(str(b["id"]), {}).get("names", {}).get("frFR")
        taught = [
            t for t in b.get("taught", []) if target["kind"] != "ability" or _teaches({"taught": [t]}, english, None)
        ]
        return {
            "id": b["id"],
            "name": {**b.get("name", {}), "fr": names_fr},
            "family": _family_of(aliases, b.get("family")),
            "level": b.get("level"),
            "tameable_now": now,
            "tameable_at": None if now or not isinstance(low, int) else low - margin,
            "taught": taught,
            "confirmation": b.get("confirmation"),
            "speed_s": b.get("speed_s"),
            "coords": coords,
            "reporters": obs.get("reporters"),
            "gaps": _gaps_about(gaps, {str(b["id"])}),
        }

    def zone_entry(zone_en: str, is_requested: bool) -> dict[str, Any]:
        map_id, m = map_by_name.get(zone_en, (None, None))
        beasts = [entry_for(b, zone_en, map_id) for b in selected if zone_en in b.get("zones", [])]
        beasts.sort(key=lambda e: (not e["tameable_now"], (e["level"] or [0])[0] or 0, e["id"]))
        return {
            "name": {"en": zone_en, "fr": m["name"]["fr"] if m else None},
            "map_id": map_id,
            "requested": is_requested,
            "levels": zone_levels.get(zone_en),
            "beasts": beasts,
        }

    zones = [zone_entry(requested["name"]["en"], True)]
    continent = requested.get("continent")
    if continent is None:
        assumptions.append("zone sans continent dans le client : zones voisines prises sur toutes les cartes")
    neighbours = sorted(
        {
            z
            for b in selected
            for z in b.get("zones", [])
            if z != requested["name"]["en"]
            and z in map_by_name
            and (continent is None or map_by_name[z][1]["continent"] == continent)
            and _overlaps(zone_levels.get(z), band)
        }
    )
    zones += [zone_entry(z, False) for z in neighbours]
    return {
        "level": level,
        "band": list(band),
        "zone": requested,
        "target": target,
        "highest_rank": highest,
        "margin": {"value": margin, "certainty": margin_rule["certainty"], "source": margin_rule["source"]},
        "zones": zones,
        "certainty": {
            "beasts": "suppose",
            "levels": "suppose",
            "coords": "suppose",
            "tameable_now": margin_rule["certainty"],
            "rank_level": "certain",
            "zone_levels": "suppose",
        },
        "assumptions": assumptions,
    }


# --- Relevé du familier (bloc F) ------------------------------------------------------------------------------


def measure_pets(pets: Mapping[str, Any], rules: Mapping[str, Any], db: Any) -> dict[str, Any]:
    """Relevés de ForeverLogger comparés au client : coût et niveau requis observés dans la fenêtre Beast Training,
    régime observé, PV du familier par point d'Endurance du Chasseur par paire d'instantanés (même familier, même
    niveau), vitesse d'attaque par famille ; chaque mesure avec `n`. Rien n'est écrit dans les données."""
    raise NotImplementedError
