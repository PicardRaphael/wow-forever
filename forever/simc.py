"""Export de l'addon SimulationCraft collé dans la fenêtre du chat (P06b, décisions 225 et 235).

Bloc A : somme de contrôle et anonymisation de l'export reçu (gardé dans le journal du pont pour devenir la fixture
réelle). La somme est l'adler32 de tout le texte qui précède la ligne `# Checksum: <hex>`, `\\n` final compris,
après `||` → `|`, en hexadécimal minuscule sans zéros de tête (`core.lua` de l'addon). L'anonymisation ne touche que
les lignes qui portent le nom du personnage et le royaume : en-tête `# <Nom> - … - <région>/<royaume>`,
`<classe>="<Nom>"` et `server=<royaume>` ; la somme est vérifiée sur le texte reçu, puis recalculée sur le texte
anonymisé. Bloc D : lecture complète (`parse_simc`)."""

from __future__ import annotations

ANON_NAME = "Personnage"
ANON_REALM = "Royaume"
CHECKSUM_PREFIX = "# Checksum: "


def simc_checksum(text_before: str) -> str:
    """Somme de contrôle de l'export (`text_before` : tout ce qui précède la ligne de la somme)."""
    raise NotImplementedError


def checksum_ok(text: str) -> bool | None:
    """Somme de l'export juste ? None si la ligne `# Checksum:` manque. Fins de ligne CRLF ramenées à LF."""
    raise NotImplementedError


def anonymize_simc(text: str) -> tuple[str, bool | None]:
    """(texte anonymisé, somme d'origine juste ?) ; la ligne de la somme est réécrite sur le texte anonymisé quand elle
    existait."""
    raise NotImplementedError
