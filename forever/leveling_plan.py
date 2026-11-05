"""Plan de talents de leveling niveau par niveau (LV1, décision 303).

Rien n'est calculé ici (décisions 293 et 299) : on rapproche deux sources installées et on les contrôle sur le
client.
- **Build visé** : le build populaire de Talents Forever le plus joué de la spécialisation, légal sur le client (choix
  de joueurs) ; sans lui, les points de Polestar encore valables.
- **Ordre** : celui de Polestar (`Polestar/Talents/Builds.lua`), point par point, tant que le point suivant est dans
  le build visé et légal à ce moment ; sinon un point légal généré par le moteur, marqué `genere`.
- Points de Polestar reliés à nos talents **par le nom** dans la classe (Blizzard réutilise des nœuds) : nom absent du
  client, point écarté et dit ; nœud qui porte aujourd'hui un autre talent, dit.
- Resets : aucun n'est inventé ; aucune source n'en donne.
Certitude `suppose` (choix de joueurs et ordre d'un guide)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from forever.config import Deps
from forever.errors import InvalidArgumentError

RESET_NOTE = (
    "aucun reset prévu : aucune source (Polestar, Talents Forever) n'en donne pour le leveling ; un seul build suivi "
    "du premier point au dernier"
)
CERTAINTY: Literal["suppose"] = "suppose"


def _knowledge_maps(knowledge: Any) -> tuple[dict[str, Any], dict[str, Any], dict[int, Any]]:
    talents = {t["key"]: t for tree in knowledge.trees for t in tree["talents"]}
    by_name = {str(t["name"]).casefold(): t for t in talents.values()}
    by_node = {int(t["node_id"]): t for t in talents.values() if t.get("node_id") is not None}
    return talents, by_name, by_node


def _read_polestar_build(
    build: Mapping[str, Any],
    nodes: Mapping[int, Any],
    by_name: Mapping[str, Any],
    by_node: Mapping[int, Any],
    first_level: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Points de Polestar en nos clés (`key` None si le talent manque au client) et écarts constatés."""
    picks: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    said: set[int] = set()
    for i, (node, rank) in enumerate(build["picks"]):
        level = first_level + i
        entry = nodes.get(node) or {}
        name = str(entry.get("name") or f"nœud {node}")
        ours = by_name.get(name.casefold())
        if ours is None:
            last = issues[-1] if issues else None
            if last and last["name"] == name and last["reason"].startswith("absent"):
                last["picks"].append(i + 1)
                last["levels"].append(level)
            else:
                issues.append(
                    {
                        "pick": i + 1,
                        "level": level,
                        "picks": [i + 1],
                        "levels": [level],
                        "name": name,
                        "reason": "absent du client : point écarté",
                    }
                )
        now = by_node.get(node)
        if now is not None and str(now["name"]).casefold() != name.casefold() and node not in said:
            said.add(node)
            issues.append(
                {
                    "pick": i + 1,
                    "level": level,
                    "picks": [i + 1],
                    "levels": [level],
                    "name": name,
                    "reason": f"nœud réaffecté : le client y met {now['name']} ; point lu par son nom",
                }
            )
        picks.append(
            {"key": ours["key"] if ours else None, "rank": rank, "level": level, "note": build["notes"].get(level)}
        )
    return picks, issues


def _merge(
    knowledge: Any, rules: Any, target: Mapping[str, int], picks: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Ordre de Polestar gardé tant qu'il colle au build visé et reste légal. Point de tête illégal : le premier point
    de Polestar encore attendu et légal (avancé, source `polestar`), sinon un point légal du build visé hors de
    Polestar, arbre le plus chargé du build d'abord (source `genere`). Build visé plus court que Polestar : complété
    par les points suivants de Polestar encore légaux (source `polestar`)."""
    from forever.engine.talents import next_step_error

    talents = {t["key"]: t for tree in knowledge.trees for t in tree["talents"]}
    position = {t["key"]: (i, j) for i, tree in enumerate(knowledge.trees) for j, t in enumerate(tree["talents"])}
    load = Counter({str(talents[k]["tree"]): 0 for k in talents})
    for k, v in target.items():
        if k in talents:
            load[str(talents[k]["tree"])] += v
    remaining = Counter({k: v for k, v in target.items() if v > 0})
    main = max(load, key=lambda name: load[name]) if load else None  # arbre le plus chargé du build visé
    queue = [p for p in picks if p["key"]]
    order: list[str] = []
    steps: list[dict[str, Any]] = []
    stops: list[str] = []

    def legal(key: str) -> bool:
        return next_step_error(knowledge, rules, order, key) is None

    def take(key: str, source: str, note: str | None) -> None:
        order.append(key)
        steps.append(
            {"key": key, "name": talents[key]["name"], "rank": order.count(key), "source": source, "note": note}
        )

    while sum(remaining.values()) > 0:
        queue = [p for p in queue if remaining.get(p["key"], 0) > 0]
        pending = {p["key"] for p in queue}
        legal_queue = [p for p in queue if legal(p["key"])]
        generated = sorted(
            (k for k in remaining if remaining[k] > 0 and k not in pending and legal(k)),
            key=lambda k: (-load[str(talents[k]["tree"])], talents[k].get("tier") or 0, position[k]),
        )
        in_main = [p for p in legal_queue if str(talents[p["key"]]["tree"]) == main]
        if queue and legal_queue and legal_queue[0] is queue[0]:  # ordre de Polestar tel quel
            wanted, note = queue[0], queue[0]["note"]
        elif in_main:  # point de Polestar avancé, dans l'arbre principal (sa note de niveau ne vaut plus)
            wanted, note = in_main[0], None
        elif generated and str(talents[generated[0]]["tree"]) == main:
            wanted, note = None, None
        else:
            wanted, note = (legal_queue[0] if legal_queue else None), None
        if wanted is not None:
            queue.remove(wanted)
            key, source = wanted["key"], "polestar"
        else:
            if not generated:
                generated = [k for k in remaining if remaining[k] > 0 and legal(k)]
            if not generated:
                stops.append(f"ordre interrompu après {len(order)} points : aucun point légal du build visé")
                break
            key, source = generated[0], "genere"
        remaining[key] -= 1
        take(key, source, note)
    target_size = sum(v for v in target.values() if v > 0)
    if len(order) == target_size and len(picks) > len(order):
        added = 0
        for p in picks:
            if len(order) >= len(picks):
                break
            key = p["key"]
            if key and order.count(key) < p["rank"] and legal(key):
                take(key, "polestar", p["note"])
                added += 1
        if added:
            stops.append(f"build visé de {target_size} points : complété par {added} point(s) suivants de Polestar")
    return steps, stops


def _tranches(steps: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Niveaux consécutifs du même talent : « niveaux A–B : talent, rangs r1→r2 »."""
    out: list[dict[str, Any]] = []
    for s in steps:
        last = out[-1] if out else None
        if last and last["key"] == s["key"] and last["source"] == s["source"]:
            last["to"] = s["level"]
            last["ranks"][1] = s["rank"]
            continue
        out.append(
            {
                "from": s["level"],
                "to": s["level"],
                "key": s["key"],
                "name": s["name"],
                "ranks": [s["rank"], s["rank"]],
                "source": s["source"],
                "note": s.get("note"),
            }
        )
    return out


def _tree_of(talents: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    load = Counter(str(talents[k]["tree"]) for k in keys if k in talents)
    return load.most_common(1)[0][0] if load else None


def _target(popular: Mapping[str, Any] | None, tree: str | None) -> dict[str, Any] | None:
    if not popular or tree is None:
        return None
    for b in popular.get("top") or []:
        if b.get("tree") == tree and b.get("legality") == "légal":
            return dict(b)
    return None


def _respec(vd: Any) -> dict[str, Any] | None:
    try:
        raw = vd.read_json("respec.json")
    except (OSError, ValueError):
        return None
    keep = ("build", "beta_observed", "dual_spec", "legacy_reset")
    return {k: raw.get(k) for k in keep if k in raw} | {"certainty": "suppose"}


def _matches(spec: str, names: Sequence[str | None]) -> bool:
    want = spec.casefold()
    return any(n and (n.casefold() == want or n.casefold().startswith(want)) for n in names)


def leveling_plan(deps: Deps, class_name: str, spec: str | None = None, level: int | None = None) -> dict[str, Any]:
    """Plan par spécialisation : build visé, points dans l'ordre (niveau, talent, rang, source), tranches, écarts de
    Polestar, point suivant au niveau `level`, code Naowh `!NFB1!` dans cet ordre, resets (aucun inventé)."""
    from forever.exports.talents import compact, naowh_block
    from forever.gamedata import build_game_data
    from forever.polestar_talents import ADDON_FOLDER, read_polestar_talents
    from forever.profile import normalize_class
    from forever.provenance import local_provenance
    from forever.store import load_version
    from forever.talents_forever import load_addon, popular_builds

    cls = normalize_class(class_name)
    folder = deps.wow_dir / "Interface" / "AddOns" / ADDON_FOLDER if deps.wow_dir else None
    polestar = read_polestar_talents(folder) if folder else None
    if not polestar or cls not in polestar["classes"]:
        where = folder or "FOREVER_WOW_DIR non réglé"
        raise InvalidArgumentError(
            f"Builds de talents de Polestar introuvables pour {cls} ({where}).",
            "installer l'addon Polestar ou régler FOREVER_WOW_DIR",
        )
    vd = load_version(deps)
    gd = build_game_data(vd)
    knowledge = gd.classes[cls]
    rules = gd.constants.talents
    talents, by_name, by_node = _knowledge_maps(knowledge)
    addon = load_addon(deps)
    popular = None
    tf_note = "Talents Forever absent : build visé = points de Polestar encore valables"
    if addon is not None and addon.popular:
        popular = popular_builds(addon, deps, cls)["classes"].get(cls)
        tf_note = (
            f"build visé : build populaire de Talents Forever {addon.version} le plus joué de la spécialisation "
            f"(relevé du {(popular or {}).get('asOf') or '?'}), choix de joueurs"
        )
    pclass = polestar["classes"][cls]
    specs_out: list[dict[str, Any]] = []
    for build in pclass["builds"]:
        picks, issues = _read_polestar_build(build, pclass["nodes"], by_name, by_node, rules.first_level)
        keys = [p["key"] for p in picks if p["key"]]
        tree = _tree_of(talents, keys)
        idx = build.get("spec")
        pname = pclass["specs"][idx - 1] if isinstance(idx, int) and 0 < idx <= len(pclass["specs"]) else None
        if spec and not _matches(spec, [pname, tree, build["key"]]):
            continue
        tf = _target(popular, tree)
        if tf is not None:
            target = dict(tf["talents"])
            target_out = {
                "source": "talents_forever",
                "rank": tf["rank"],
                "spec": tf["spec"],
                "link": tf["link"],
                "import": tf["import"],
                "talents": target,
            }
        else:
            target = dict(Counter(keys))
            target_out = {
                "source": "polestar",
                "rank": None,
                "spec": pname,
                "link": build.get("link"),
                "import": None,
                "talents": target,
            }
        steps, stops = _merge(knowledge, rules, target, picks)
        for i, s in enumerate(steps):
            s["level"] = rules.first_level + i
        polestar_note = {(p["key"], p["rank"]): p["note"] for p in picks if p["key"] and p["note"]}
        for s in steps:
            if s["source"] == "polestar" and s["note"] is None:
                s["note"] = polestar_note.get((s["key"], s["rank"]))
        last_level = steps[-1]["level"] if steps else rules.first_level
        order = [s["key"] for s in steps]
        naowh = (
            compact(
                naowh_block(
                    gd,
                    cls,
                    last_level,
                    Counter(order),
                    order,
                    f"{cls} {pname or tree} leveling (forever)",
                    order_source="leveling",
                )
            )
            if order
            else None
        )
        nxt = next((s for s in steps if level is not None and s["level"] == level + 1), None)
        specs_out.append(
            {
                "key": build["key"],
                "spec": pname,
                "tree": tree,
                "split": build.get("split"),
                "target": target_out,
                "polestar": {"issues": issues, "usable_picks": len(keys), "picks": len(picks)},
                "steps": steps,
                "tranches": _tranches(steps),
                "generated": sum(1 for s in steps if s["source"] == "genere"),
                "stops": stops,
                "next": nxt,
                "naowh": naowh,
                "resets": {"planned": [], "note": RESET_NOTE, "data": _respec(vd)},
            }
        )
    if spec and not specs_out:
        raise InvalidArgumentError(
            f"Spécialisation « {spec} » absente des builds de Polestar pour {cls}.",
            "donner une spécialisation de la classe (nom anglais)",
        )
    notes = [
        (
            f"ordre : Polestar {polestar['version'] or '?'} (Talents/Builds.lua), écrit sur le client "
            f"{polestar['written_on'] or '?'}, contrôlé point par point sur le client installé {vd.game_version}"
        ),
        tf_note,
        "points absents du build visé ou illégaux remplacés par un point légal généré (source « genere »)",
        "aucun calcul de rendement sous le 60 (décision 299) ; resets : aucun inventé",
    ]
    notes += [
        f"{s['spec'] or s['key']} : {i['name']} ({i['reason']})" for s in specs_out for i in s["polestar"]["issues"]
    ]
    return {
        "kind": "leveling_plan",
        "class": cls,
        "summary": pclass.get("summary"),
        "polestar": {
            "version": polestar["version"],
            "written_on": polestar["written_on"],
            "client": vd.game_version,
            "source": pclass.get("source"),
        },
        "specs": specs_out,
        "certainty": CERTAINTY,
        "provenance": local_provenance(deps, certainty=CERTAINTY, assumptions=notes),
    }


def render_plan(plan: Mapping[str, Any]) -> list[str]:
    """Lignes d'une sortie texte (`forever talents plan`)."""
    p = plan["polestar"]
    lines = [
        f"Plan de talents de leveling : {plan['class']} (certitude {plan['certainty']})",
        f"Ordre : Polestar {p['version']} écrit sur {p['written_on']}, contrôlé sur {p['client']}",
    ]
    for s in plan["specs"]:
        t = s["target"]
        head = f"\n{s['spec'] or s['key']} ({s['tree']}) · build visé : "
        head += f"Talents Forever n° {t['rank']} {t['link']}" if t["source"] == "talents_forever" else "Polestar"
        lines.append(head)
        for tr in s["tranches"]:
            span = f"niveau {tr['from']}" if tr["from"] == tr["to"] else f"niveaux {tr['from']}–{tr['to']}"
            ranks = f"{tr['ranks'][0]}" if tr["ranks"][0] == tr["ranks"][1] else f"{tr['ranks'][0]}→{tr['ranks'][1]}"
            tag = " (généré)" if tr["source"] == "genere" else ""
            note = f" · {tr['note']}" if tr.get("note") else ""
            lines.append(f"  {span} : {tr['name']} {ranks}{tag}{note}")
        for i in s["polestar"]["issues"]:
            lv = i["levels"]
            at = f"niveau {lv[0]}" if len(lv) == 1 else f"niveaux {lv[0]}–{lv[-1]}"
            lines.append(f"  ! Polestar ({at}) : {i['name']} : {i['reason']}")
        lines += [f"  ! {x}" for x in s["stops"]]
        if s["next"]:
            lines.append(f"  Au prochain niveau ({s['next']['level']}) : {s['next']['name']} rang {s['next']['rank']}")
        n = s["naowh"]
        if n and n.get("code"):
            lines.append(f"  Naowh Forever : {n['code']} · {n['import']} ; puis Follow")
        elif n:
            lines.append(f"  Naowh Forever : export bloqué : {n['reason']}")
        lines.append(f"  Resets : {s['resets']['note']}")
    return lines
