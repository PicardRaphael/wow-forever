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


def parse_simc(text: str) -> Any:
    """Export lu (bloc D) : en-tête, objets, fiche, notations, compétences, buffs, somme de contrôle."""
    raise NotImplementedError


def simc_gaps(export: Any, profile: Any, context_gear: Any) -> tuple[list[Any], list[str]]:
    """(écarts avec le profil, avertissements) : fiche lue par l'export ; objets recoupés avec le contexte."""
    raise NotImplementedError
