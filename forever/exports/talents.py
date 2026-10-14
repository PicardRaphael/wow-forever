"""Builds de talents vers Naowh Forever (EX1, bloc B) : points d'un build en nœuds du client (`node_id` de
`classes.json`, TraitNodeID chez Naowh), un par point, dans l'ordre de prise ; ordre de leveling quand il existe,
sinon ordre légal généré par le moteur (`forever/engine/talents.py`) et signalé comme tel."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from forever.config import Deps
from forever.engine.model import ClassKnowledge, GameData
from forever.exports.codec import ExportFormatError

ORDER_NOTE = "ordre généré (légal à chaque prise), pas un ordre de leveling"
IMPORT_STEPS = "en jeu : /nf, Profiles, Import, coller le code (Naowh demande confirmation)"
OrderSource = Literal["leveling", "code", "genere"]


def naowh_points(knowledge: ClassKnowledge, order: Sequence[str]) -> tuple[int, ...]:
    """Nœud du client (`node_id`) de chaque prise de l'ordre, un par point."""
    nodes = {t["key"]: int(t["node_id"]) for tree in knowledge.trees for t in tree["talents"]}
    return tuple(nodes[key] for key in order)


def _dominant_tree(knowledge: ClassKnowledge, talents: Mapping[str, int]) -> str:
    """Arbre le plus chargé (premier dans l'ordre du client à égalité), nommé comme dans nos données."""
    tree_of = {t["key"]: str(tree["name"]) for tree in knowledge.trees for t in tree["talents"]}
    load: Counter[str] = Counter()
    for key, rank in talents.items():
        if rank > 0 and key in tree_of:
            load[tree_of[key]] += rank
    names = [str(tree["name"]) for tree in knowledge.trees]
    return max(names, key=lambda n: (load[n], -names.index(n)))


def _provenance(deps: Deps, notes: Sequence[str]) -> Any:
    from forever.exports.naowh import NAOWH_VERSION
    from forever.provenance import local_provenance

    base = [
        (
            f"format !NFB1! relevé dans Naowh Forever {NAOWH_VERSION} (module Training), réimplémenté sans code "
            "recopié ; jamais importé en jeu (question NFB1) : probable"
        ),
        "nœuds de talents : node_id de classes.json (TraitNodeID du client)",
    ]
    return local_provenance(deps, certainty="probable", assumptions=[*base, *notes])


def naowh_block(
    gd: GameData,
    class_name: str,
    level: int,
    talents: Mapping[str, int],
    order: Sequence[str] | None = None,
    name: str | None = None,
    *,
    order_source: OrderSource = "leveling",
    talented_bonus: int = 0,
) -> dict[str, Any]:
    """Code `!NFB1!` d'un build légal au niveau, sur des données déjà chargées (sans provenance) : ordre donné
    (leveling ou code Talents Forever), contrôlé à chaque prise comme le fait Naowh ; sans ordre, ordre légal généré
    (`status="ordre_genere"`). Build illégal, ordre incohérent ou illégal : `status="bloque"` avec la raison (talent
    nommé), jamais un code deviné. Certitude `probable` tant que l'import en jeu n'est pas vérifié (question NFB1)."""
    from forever.engine.talents import check_class_build, check_order, legal_order
    from forever.exports.naowh import NAOWH_VERSION, build_text, naowh_build
    from forever.profile import normalize_class

    cls = normalize_class(class_name)
    placed = {k: int(v) for k, v in talents.items() if int(v) > 0}
    block: dict[str, Any] = {
        "kind": "naowh_build",
        "status": "ok",
        "reason": None,
        "class": cls,
        "class_id": None,
        "level": level,
        "name": None,
        "spec": None,
        "code": None,
        "points": None,
        "order": None,
        "order_source": None,
        "order_note": None,
        "import": IMPORT_STEPS,
        "addon": {"name": "Naowh Forever", "version": NAOWH_VERSION, "format": "!NFB1!"},
        "certainty": "probable",
    }

    def refuse(reason: str) -> dict[str, Any]:
        block.update(status="bloque", reason=reason)
        return block

    knowledge = gd.classes.get(cls)
    if knowledge is None:
        return refuse(f"classe {cls} absente des données")
    block["class_id"] = knowledge.id
    if not placed:
        return refuse("aucun point placé")
    errors = check_class_build(knowledge, gd.constants.talents, placed, level, talented_bonus)
    if errors:
        return refuse(f"build illégal au niveau {level} : {errors[0]}")
    if order:
        if Counter(order) != Counter(placed):
            return refuse("ordre incohérent : les prises de l'ordre ne font pas les rangs du build")
        steps = check_order(knowledge, gd.constants.talents, order)
        if steps:
            return refuse(f"ordre illégal pour Naowh : {steps[0]}")
        chosen, source, note = list(order), order_source, None
    else:
        try:
            chosen = legal_order(knowledge, gd.constants.talents, placed)
        except ValueError as err:
            return refuse(str(err))
        source, note = "genere", ORDER_NOTE
    spec = _dominant_tree(knowledge, placed)
    label = name or f"{cls} {level} ({spec}, forever)"
    points = naowh_points(knowledge, chosen)
    try:
        code = naowh_build(knowledge.id, label, spec, points)
    except ExportFormatError as err:
        return refuse(str(err))
    block.update(
        status="ok" if source != "genere" else "ordre_genere",
        name=build_text(label),
        spec=build_text(spec),
        code=code,
        points=list(points),
        order=chosen,
        order_source=source,
        order_note=note,
    )
    return block


def naowh_export(
    deps: Deps,
    class_name: str,
    level: int,
    talents: Mapping[str, int],
    order: Sequence[str] | None = None,
    name: str | None = None,
    *,
    order_source: OrderSource = "leveling",
    talented_bonus: int = 0,
) -> dict[str, Any]:
    """`naowh_block` sur les données installées, avec sa provenance (CLI, MCP, pont)."""
    from forever.gamedata import build_game_data
    from forever.store import load_version

    gd = build_game_data(load_version(deps))
    block = naowh_block(
        gd, class_name, level, talents, order, name, order_source=order_source, talented_bonus=talented_bonus
    )
    notes = [f"export bloqué : {block['reason']}"] if block["reason"] else []
    if block["order_note"]:
        notes.append(block["order_note"])
    block["provenance"] = _provenance(deps, notes)
    return block


def compact(block: Mapping[str, Any]) -> dict[str, Any]:
    """Bloc court pour un build populaire ou un contrôle de build : statut, raison, code, source de l'ordre."""
    keys = ("status", "reason", "code", "order_source", "order_note", "import", "certainty")
    return {k: block.get(k) for k in keys}


def render_naowh(block: Mapping[str, Any]) -> list[str]:
    """Lignes « Naowh Forever » d'une sortie texte (`forever build`, `forever export naowh-build`)."""
    if block["status"] == "bloque":
        return [f"Naowh Forever : export bloqué : {block['reason']}"]
    addon = block["addon"]
    head = f"Naowh Forever : {block['code']} ({block['certainty']}, format {addon['format']}, Naowh {addon['version']})"
    lines = [f"{head} · {block['import']}"]
    if block.get("order_note"):
        lines.append(f"  {block['order_note']}")
    return lines
