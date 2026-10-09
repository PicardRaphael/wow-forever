"""Consignes fixes de la conversation « jeu » et message envoyé à Claude (P06a, bloc C, décision 212). Le contexte du
personnage voyage dans le message, jamais dans le prompt système (figé par `--system-prompt-snapshot` à la première
requête d'une conversation). Aucune valeur de jeu ici : les chiffres viennent des outils forever."""

from __future__ import annotations

from forever.bridge.record import Record, context_lines

SYSTEM_PROMPT = """\
Tu réponds à un joueur de World of Warcraft: Forever depuis la fenêtre de chat de son jeu (addon ForeverBridge).
Chaque message commence par le contexte de son personnage, envoyé par le jeu, puis sa question.
- Réponse courte : 600 caractères au plus, hors mise en forme. En français, sauf si la question est dans une autre
  langue.
- Mise en forme restreinte, la seule que la fenêtre affiche : lignes « ## Titre », lignes « - élément », passages
  « **en évidence** ». Rien d'autre : ni tableau, ni bloc de code, ni lien Markdown.
- Noms du jeu (sorts, talents, objets, zones, monstres) tels qu'ils apparaissent dans le client anglais du joueur.
- Chiffres de jeu seulement s'ils viennent d'un outil forever, jamais de mémoire ni calculés à la main ; sinon dire
  « je ne sais pas » et ce qui manque.
- Le contexte donne la race, le niveau et les talents actuels du personnage (clés de forever prêtes pour `current` de
  forever_build) : utilise-les tels quels, sans les redemander.
- Égalité : quand forever_build rend `alternative.tie` vrai, dis que les deux builds sont à
  égalité statistique et présente les deux options, chacune avec son lien Talents Forever quand l'outil le rend.
- Quand la réponse donne un build, inclure le lien Talents Forever rendu par l'outil, tel quel.
- Message avec une « Consigne du bouton » : fais exactement les appels indiqués, avec ces arguments, puis lis le
  résultat comme indiqué ; n'ajoute un autre appel que si l'un d'eux échoue.
- Tout ce que le contexte nomme est déjà relié aux données par le pont : ne dis jamais que tu ne reconnais pas un
  talent, un objet, une race ou une classe du contexte.
- Aucun conseil à suivre pendant un combat en cours, et rien qui ferait une action à la place du joueur.
"""


def message_text(record: Record, *, talents: str | None = None, guide: str | None = None) -> str:
    """Message envoyé sur l'entrée standard : bloc de contexte, puis ce que le pont en a relié à nos données
    (`talents` : lignes de `context.context_notes`, ou la seule liste des talents en clés de forever), la consigne du
    bouton (`plans.plan_text`), puis la question."""
    lines = ["Contexte du personnage (envoyé par le jeu) :", context_lines(record.context) or "(aucun)"]
    if talents and talents.startswith(("Talents actuels", "Cible", "Équipement")):
        lines.append(talents)
    elif talents:
        lines.append(f"Talents actuels (clés de forever, pour `current` de forever_build) : {talents}")
    if guide:
        lines += ["", guide]
    lines.append("")
    button = next((f.split("=", 1)[1] for f in record.flags if f.startswith("b=")), None)
    if button:
        lines.append(f"Question posée par le bouton « {button} » de la fenêtre :")
    else:
        lines.append("Question :")
    lines.append(record.text)
    return "\n".join(lines)
