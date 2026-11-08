"""Métiers rentables et hôtel des ventes (AMI7a, `tasks/AMI7a-plan.md` ; décisions 272, 288, 294 et 300).

Tout est lu en local dans mes addons, sans réseau : recettes, réactifs, produits et prix de marchand dans SkillUp
Forever (données tirées par l'addon du client de Forever), prix dans mes relevés d'Auctionator (dernier minimum vu par
objet, daté), sacs, banque et courrier dans les SavedVariables de Forever Companion. SkillUp calcule déjà en jeu le
coût d'une recette avec Auctionator : ici, seulement le classement hors du jeu par profit et la liste des objets à
vendre. Aucun chiffre de jeu écrit ici ; taxe et dépôt de l'hôtel des ventes absents des sources, donc non déduits."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.config import Deps
from forever.errors import ForeverError, InvalidArgumentError
from forever.pipeline.auctionator import ItemPrice, read_price_database
from forever.provenance import local_provenance
from forever.store import current_identity

AUCTIONATOR_FILE = "Auctionator.lua"
COMPANION_FILE = "ForeverCompanion.lua"
COMPANION_VARIABLE = "ForeverCompanionDB"
PLACES = {"bags": "sacs", "bank": "banque", "mail": "courrier"}  # `equip` (porté) jamais proposé à la vente
DEFAULT_LIMIT = 20  # recettes et objets rendus au plus (réglage de l'outil)
CUT_NOTE = (
    "taxe et dépôt de l'hôtel des ventes : absente des données de forever et des sources locales, non déduits "
    "(profit brut)"
)


def _account_svs(deps: Deps) -> list[Path]:
    if deps.wow_dir is None:
        return []
    return sorted((Path(deps.wow_dir) / "WTF" / "Account").glob("*/SavedVariables"))


def _is_beta(realm: str) -> bool:
    from forever.profile_import import BETA_REALM

    return bool(BETA_REALM.search(realm))


def _color(skill: int, thresholds: Sequence[int]) -> str:
    _, yellow, green, grey = thresholds
    return "orange" if skill < yellow else "jaune" if skill < green else "vert" if skill < grey else "gris"


# --- prix d'Auctionator ---------------------------------------------------------------------------------------------


def _prices(deps: Deps, realm: str | None) -> tuple[str | None, dict[int, ItemPrice], list[str], list[str]]:
    """Royaume choisi, prix par objet (le relevé le plus récent de tous les comptes), royaumes de la bêta ignorés
    (décision 300), notes."""
    merged: dict[str, dict[int, ItemPrice]] = {}
    files = [d / AUCTIONATOR_FILE for d in _account_svs(deps) if (d / AUCTIONATOR_FILE).is_file()]
    for path in files:
        for name, items in read_price_database(path).items():
            table = merged.setdefault(name, {})
            for item, price in items.items():
                if item not in table or price.day > table[item].day:
                    table[item] = price
    ignored = sorted(r for r in merged if _is_beta(r))
    realms = sorted(r for r in merged if not _is_beta(r))
    if not files:
        return None, {}, ignored, ["Auctionator : aucune SavedVariable trouvée, aucun prix de l'hôtel des ventes"]
    if realm is not None:
        if realm not in realms:
            raise InvalidArgumentError(
                f"Royaume sans prix d'Auctionator : « {realm} ».", "royaumes : " + (", ".join(realms) or "aucun")
            )
        return realm, merged[realm], ignored, []
    if not realms:
        return None, {}, ignored, ["Auctionator : aucun relevé de prix hors de la bêta"]
    if len(realms) > 1:
        raise InvalidArgumentError(
            "Plusieurs royaumes ont des prix d'Auctionator.", "donner --realm : " + ", ".join(realms)
        )
    return realms[0], merged[realms[0]], ignored, []


def _ah(prices: Mapping[int, ItemPrice], item: int) -> ItemPrice | None:
    price = prices.get(item)
    return price if price is not None and price.min > 0 else None


# --- recettes ---------------------------------------------------------------------------------------------------------


Prices = Mapping[int, ItemPrice]
Names = Mapping[int, str]
Craft = Mapping[str, Any]


def _reagent(item: int, qty: int, prices: Prices, craft: Craft, names: Names) -> dict[str, Any]:
    offers: list[tuple[int, str, str | None]] = []
    vendor = craft["vendor_prices"].get(item)
    if vendor is not None:
        offers.append((vendor, "marchand", None))
    ah = _ah(prices, item)
    if ah is not None:
        offers.append((ah.min, "auctionator", ah.date))
    best: tuple[int | None, str | None, str | None] = min(offers, key=lambda o: o[0]) if offers else (None, None, None)
    return {"item_id": item, "name": names.get(item), "quantity": qty, "unit_price": best[0], "source": best[1],
            "date": best[2]}  # fmt: skip


def _recipe_row(
    spell: int, base: Mapping[str, Any], made: Mapping[str, Any], skill: int, prices: Prices, craft: Craft, names: Names
) -> dict[str, Any]:
    reagents = [_reagent(i, q, prices, craft, names) for i, q in made["reagents"]]
    out_item, out_qty = made["output"]
    ah = _ah(prices, out_item)
    missing = [r["item_id"] for r in reagents if r["unit_price"] is None]
    if ah is None:
        missing.append(out_item)
    unknown = not reagents
    cost = (
        None
        if unknown or any(r["unit_price"] is None for r in reagents)
        else sum(r["unit_price"] * r["quantity"] for r in reagents)
    )
    sale = round(ah.min * out_qty) if ah is not None else None
    return {
        "spell_id": spell,
        "name": base["name"],
        "color": _color(skill, base["thresholds"]),
        "thresholds": list(base["thresholds"]),
        "reagents": reagents,
        "reagents_unknown": unknown,
        "output": {
            "item_id": out_item,
            "name": names.get(out_item),
            "quantity": out_qty,
            "unit_price": ah.min if ah else None,
            "date": ah.date if ah else None,
            "vendor_sell": craft["sell_prices"].get(out_item),
        },
        "cost": cost,
        "sale": sale,
        "profit": sale - cost if sale is not None and cost is not None else None,
        "missing": missing,
    }


def _one_profession(
    name: str, line: int, skill: int, skillup: Mapping[str, Any], craft: Craft, prices: Prices, names: Names, limit: int
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    too_high, without_output, no_data = 0, 0, 0
    for spell, base in skillup["recipes"].items():
        if base["skill_line"] != line:
            continue
        if skill < base["thresholds"][0]:
            too_high += 1
            continue
        made = craft["recipes"].get(spell)
        if made is None:
            no_data += 1
            continue
        if made["output"] is False:
            without_output += 1
            continue
        rows.append(_recipe_row(spell, base, made, skill, prices, craft, names))
    priced = sorted((r for r in rows if r["profit"] is not None), key=lambda r: (-r["profit"], r["name"]))
    other = sorted((r for r in rows if r["profit"] is None), key=lambda r: r["name"])
    ordered = priced + other
    return {"profession": name, "skill": skill, "recipes": ordered[:limit], "total": len(ordered),
            "priced": len(priced), "too_high": too_high, "without_output": without_output,
            "no_data": no_data}  # fmt: skip


def _wanted(deps: Deps, profession: str | None, skill: int | None) -> dict[str, int]:
    """Métiers à calculer (nom tel que donné -> rang) : celui donné, sinon ceux du personnage actif du profil."""
    from forever.profile import read_profile

    character = read_profile(deps)["character"] or {}
    known = {str(k): v for k, v in (character.get("professions") or {}).items() if isinstance(v, int)}
    if profession is not None:
        if skill is None:
            skill = next((v for k, v in known.items() if k.lower() == profession.strip().lower()), None)
        if skill is None:
            raise InvalidArgumentError(
                f"Rang du métier « {profession} » inconnu.", "donner --skill (rang actuel du métier)"
            )
        return {profession.strip(): skill}
    if not known:
        raise InvalidArgumentError(
            "Aucun métier dans le profil.", "donner --profession et --skill, ou forever profile set --profession"
        )
    return known


# --- objets à vendre --------------------------------------------------------------------------------------------------


def _inventories(deps: Deps) -> dict[str, dict[str, Any]] | None:
    from forever.pipeline.lua_table import parse_lua_assignments

    found: dict[str, dict[str, Any]] | None = None
    for d in _account_svs(deps):
        path = d / COMPANION_FILE
        if not path.is_file():
            continue
        try:
            db = parse_lua_assignments(path.read_text(encoding="utf-8")).get(COMPANION_VARIABLE)
        except (ValueError, ForeverError):
            continue
        inventory = ((db or {}).get("global") or {}).get("inventory") if isinstance(db, dict) else None
        if isinstance(inventory, dict):
            found = found or {}
            for realm, chars in inventory.items():
                if isinstance(chars, dict):
                    found.setdefault(str(realm), {}).update(
                        {str(k): v for k, v in chars.items() if isinstance(v, dict)}
                    )
    return found


def _to_sell(
    deps: Deps, realm: str | None, character: str | None, prices: Prices, craft: Craft, names: Names, limit: int
) -> dict[str, Any]:
    inventories = _inventories(deps)
    if inventories is None:
        reason = "Forever Companion : SavedVariables absentes (inventaire des sacs et de la banque inconnu)"
        return {"available": False, "reason": reason, "items": [], "missing": [], "notes": []}
    notes: list[str] = []
    realms = [r for r in inventories if not _is_beta(r)]
    if realm is not None:
        same = [r for r in realms if r == realm or r.endswith(" " + realm)]
        if same:
            realms = same
        else:
            notes.append(f"aucun royaume de Forever Companion ne correspond à « {realm} » : tous les personnages lus")
    counts: dict[int, int] = {}
    where: dict[int, list[dict[str, Any]]] = {}
    for r in realms:
        for name, entry in sorted(inventories[r].items()):
            if character is not None and name.lower() != character.lower():
                continue
            for key, place in PLACES.items():
                table = entry.get(key)
                if not isinstance(table, dict):
                    continue
                for item, count in sorted(table.items()):
                    if not isinstance(item, int) or not isinstance(count, int) or count <= 0:
                        continue
                    counts[item] = counts.get(item, 0) + count
                    where.setdefault(item, []).append({"character": name, "realm": r, "place": place, "count": count})
    items, missing = [], []
    for item, count in counts.items():
        ah = _ah(prices, item)
        if ah is None:
            missing.append(item)
            continue
        items.append({"item_id": item, "name": names.get(item), "count": count, "unit_price": ah.min, "date": ah.date,
                      "total": ah.min * count, "vendor_sell": craft["sell_prices"].get(item),
                      "where": where[item]})  # fmt: skip
    items.sort(key=lambda i: (-i["total"], i["item_id"]))
    notes.append("objets liés au personnage non distingués (Forever Companion ne le dit pas)")
    return {"available": True, "source": "Forever Companion", "items": items[:limit], "total": len(items),
            "missing": sorted(missing), "notes": notes}  # fmt: skip


# --- point d'entrée -------------------------------------------------------------------------------------------------


def _item_names(deps: Deps, craft: Mapping[str, Any]) -> dict[int, str]:
    """Noms anglais du client (`ItemSparse` du cache de `forever fetch`), sinon commentaires de `Vendor.lua`."""
    from forever.dungeons import _item_rows

    names = dict(craft["vendor_names"])
    rows = _item_rows(deps, current_identity(deps.data_dir).game_version)
    names.update({i: str(r["Display_lang"]) for i, r in rows.items() if r.get("Display_lang")})
    return names


def profession_profit(
    deps: Deps,
    *,
    profession: str | None = None,
    skill: int | None = None,
    realm: str | None = None,
    character: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Recettes faisables (seuil orange ≤ rang) classées par profit à l'hôtel des ventes, prix manquants nommés, et
    objets à vendre ; `forever professions profit`, `forever_lookup(kind="profession_profit")`. Certitude `suppose`."""
    from forever.pipeline.skillup import read_crafting, read_skillup
    from forever.sources import _fresh, choose

    addons = Path(deps.wow_dir) / "Interface" / "AddOns" if deps.wow_dir is not None else None
    skillup = read_skillup(addons) if addons is not None else None
    craft = read_crafting(addons) if addons is not None else None
    if skillup is None or craft is None:
        reason = "SkillUp Forever introuvable (lecture locale du dossier du jeu)"
        return {"kind": "profession_profit", "available": False, "reason": reason, "professions": [],
                "provenance": local_provenance(deps, certainty="suppose", assumptions=[reason])}  # fmt: skip
    wanted = _wanted(deps, profession, skill)
    chosen, prices, ignored, notes = _prices(deps, realm)
    names = _item_names(deps, craft)
    lines = {k.lower(): (k, v) for k, v in skillup["professions"].items()}
    results, uncovered = [], []
    for asked, rank in sorted(wanted.items()):
        found = lines.get(asked.lower())
        if found is None:
            if profession is not None:
                raise InvalidArgumentError(
                    f"Métier inconnu de SkillUp Forever : « {asked} ».", "métiers : " + ", ".join(sorted(lines))
                )
            uncovered.append(asked)
            continue
        results.append(_one_profession(found[0], found[1], rank, skillup, craft, prices, names, limit))
    results.sort(key=lambda p: p["profession"])
    version = current_identity(deps.data_dir).game_version
    build = skillup["build"]
    status = "à jour" if build == version else ("en retard" if build else "inconnue")
    detail = [] if status == "à jour" else [f"données de SkillUp tirées du build {build or '?'}, jeu {version}"]
    fresh = _fresh("skillup", "SkillUp Forever", "metiers", ["*"], status, "version", detail)  # type: ignore[arg-type]
    newest = max((p.date for p in prices.values()), default=None)
    notes += [
        f"SkillUp Forever (données du client {build or '?'} du {skillup['date'] or '?'}) : réactifs, produits, seuils",
        (
            f"prix : derniers minimums d'Auctionator du royaume {chosen or '?'} (relevé le plus récent : "
            f"{newest or '?'}), prix d'achat au marchand de SkillUp quand il est moins cher ; montants en cuivre"
        ),
        "produit : quantité moyenne de SkillUp ; recette apprise ou non : inconnu hors du jeu (seuil orange ≤ rang)",
        CUT_NOTE,
    ]
    if ignored:
        notes.append(f"royaumes de la bêta ignorés (décision 300) : {', '.join(ignored)}")
    note = choose([fresh])["note"]
    if note:
        notes.append(note)
    return {
        "kind": "profession_profit",
        "available": True,
        "realm": chosen,
        "ignored_realms": ignored,
        "professions": results,
        "uncovered": uncovered,
        "auction_cut": None,
        "to_sell": _to_sell(deps, chosen, character, prices, craft, names, limit),
        "freshness": fresh,
        "in_game": "SkillUp Forever donne en jeu le coût de chaque recette avec Auctionator : /skillup",
        "provenance": local_provenance(deps, certainty="suppose", assumptions=notes),
    }
