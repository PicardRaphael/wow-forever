"""Traducteur des phrases libres (FR1), injecté.

Aucune traduction automatique ni réseau (question Q1) : en usage normal il n'y a pas de traducteur, une phrase
inconnue de la mémoire et des phrases types reste en anglais et figure au rapport (`forever rxp traduire
--manquants`). Les phrases se traduisent depuis la VO anglaise dans une session Claude, à la demande de
l'utilisateur, puis s'importent (`--importer`, origine `traduit`). Les tests injectent un traducteur factice."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Protocol

from forever.rxp_fr.memory import Memory, normalize


class Translator(Protocol):
    def translate(self, items: Sequence[str]) -> Mapping[str, str]: ...


Resolved = tuple[str | None, str]  # (gabarit français ou None, origine : restedxp, manuel, traduit, motif, anglais)


def resolve(
    items: Iterable[str],
    memory: Memory,
    translator: Translator | None,
    *,
    date: str,
    patterns: Callable[[str], str | None] | None = None,
) -> dict[str, Resolved]:
    """Gabarit français de chaque gabarit anglais : mémoire, puis phrases types, puis traducteur (une fois par
    phrase nouvelle, rangée `traduit`) ; sinon (None, « anglais »)."""
    out: dict[str, Resolved] = {}
    pending: list[str] = []
    for item in dict.fromkeys(items):
        entry = memory.get(item)
        if entry is not None:
            out[item] = (entry.fr, entry.origin)
            continue
        found = patterns(item) if patterns is not None else None
        if found is not None:
            out[item] = (found, "motif")
            continue
        pending.append(item)
    answers = translator.translate(pending) if translator is not None and pending else {}
    for item in pending:
        fr = answers.get(item)
        if fr is not None and memory.put(item, fr, "traduit", date=date):
            out[item] = (memory.entries[normalize(item)].fr, "traduit")
        else:
            out[item] = (None, "anglais")
    return out
