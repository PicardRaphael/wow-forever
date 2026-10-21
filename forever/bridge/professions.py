"""Assistant « Métier » du pont (plan « Sources d'abord », reste de l'étape b ; décisions 272 et 288) : réponse à
l'action `a=profession` de ForeverBridge, sans le modèle. Pour chaque métier envoyé par le jeu (`professions` du
contexte : nom et rang), les recettes de SkillUp Forever qui font encore monter le métier (`lookup_profession` : orange
puis jaune), la fraîcheur de la source et le rappel de `/skillup`, qui calcule en jeu l'itinéraire complet. On lit,
on ne recalcule pas. Un métier que SkillUp ne couvre pas est dit non couvert, sans faire échouer la réponse."""

from __future__ import annotations

from collections.abc import Mapping

from forever.bridge.context import professions_context
from forever.config import Deps
from forever.errors import InvalidArgumentError

TITLE = "## Métiers"


def profession_reply(deps: Deps, context: Mapping[str, str]) -> str:
    """Texte Markdown de la réponse : une section par métier du personnage."""
    from forever.lookup import lookup_profession

    professions = professions_context(context)
    if not professions:
        return f"{TITLE}\nLe jeu n'a envoyé aucun métier : apprends un métier, puis relance « Calculer »."
    lines = [TITLE]
    reminder = None
    for name, rank in professions.items():
        try:
            out = lookup_profession(deps, name, rank=rank)
        except InvalidArgumentError:
            lines.append(f"\n### {name} (rang {rank})\nnon couvert par SkillUp Forever : rien à proposer ici.")
            continue
        if not out["available"]:
            return f"{TITLE}\n{out['reason']} : installe ou active SkillUp Forever, puis relance « Calculer »."
        lines.append(f"\n### {out['profession']} (rang {rank})")
        if not out["recipes"]:
            lines.append("Aucune recette connue ne fait encore monter ce métier à ce rang.")
        for r in out["recipes"]:
            lines.append(f"- {r['name']} ({r['color']})")
        if out["total"] > len(out["recipes"]):
            lines.append(f"- … et {out['total'] - len(out['recipes'])} autre(s)")
        fresh = out["freshness"]
        if fresh["status"] != "à jour":
            lines.append(f"Source {fresh['status']} : {'; '.join(fresh['detail'])}.")
        reminder = out["in_game"]
    if reminder:
        lines.append(f"\n{reminder}.")
    return "\n".join(lines)
