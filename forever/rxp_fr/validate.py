"""Validateur bloquant d'un fichier français généré (FR1) : un échec n'écrit rien.

Pour chaque guide, face au guide anglais : un guide généré a autant de lignes, la même nature de ligne, les mêmes
commandes avec les mêmes arguments (identifiants, coordonnées ; noms de `.target` / `.mob` seulement traduits, `::id`
intacts), les mêmes filtres `<<` et en-têtes non traduits, aucun `]]` (fin de la chaîne Lua) et autant de codes
couleur ouverts que fermés qu'en anglais ; un guide recopié tel quel de RestedXP n'est pas contrôlé. Chaque `#next` traduit
désigne un guide du fichier ou des autres fichiers français, dès que le `#next` anglais désigne un guide connu."""

from __future__ import annotations

import re
from collections.abc import Iterable

from forever.rxp_fr.source import GUARD, MARKER, UNTRANSLATED_COMMANDS, guide_bodies, header, line_key
from forever.rxp_fr.tokens import TITLE_HEADERS, Line, parse_line

_END = re.compile(r"\]=*\]")


def _ids(prefix: str) -> list[str]:
    return re.findall(r"::\d+", prefix)


def _colour(text: str) -> int:
    return text.count("|c") - text.count("|r")


def _check_line(n: int, en: Line, fr: Line) -> str | None:
    where = f"ligne {n}"
    if en.kind != fr.kind or en.command != fr.command:
        return f"{where} : commande ou nature de ligne changée ({en.render().strip()!r})"
    if en.suffix.strip() != fr.suffix.strip():
        return f"{where} : filtre changé ({en.suffix.strip()!r} -> {fr.suffix.strip()!r})"
    command = (en.command or "").lower()
    if en.kind == "command" and command in UNTRANSLATED_COMMANDS:
        if _ids(en.prefix) != _ids(fr.prefix) or en.prefix.count(",") != fr.prefix.count(","):
            return f"{where} : commande changée (.{command} : identifiants ou nombre de noms)"
    elif en.kind == "header" and command in TITLE_HEADERS:
        if en.prefix.strip() != fr.prefix.strip():
            return f"{where} : en-tête changé"
    elif en.kind == "command" and line_key(en) != line_key(fr) or en.kind != "command" and en.prefix != fr.prefix:
        return f"{where} : commande changée ({en.prefix.strip()!r} -> {fr.prefix.strip()!r})"
    if en.kind in ("blank", "comment", "step", "other") and en.render() != fr.render():
        return f"{where} : ligne non traduisible changée"
    if _END.search(fr.text) and not _END.search(en.text):
        return f"{where} : « ]] » introduit (fin de la chaîne Lua)"
    if _END.search(fr.prefix) and not _END.search(en.prefix):
        return f"{where} : « ]] » introduit (fin de la chaîne Lua)"
    if _colour(fr.text) != _colour(en.text) or _colour(fr.prefix) != _colour(en.prefix):
        return f"{where} : codes couleur déséquilibrés (|c sans |r)"
    return None


def _names(bodies: Iterable[str]) -> set[str]:
    return {name.strip() for body in bodies for name in header(body, "name")}


def _nexts(body: str) -> list[str]:
    r"""Guides désignés par `#next` : « Groupe\Guide » ou « Guide » (le groupe est celui du guide)."""
    return [part.strip() for text in header(body, "next") for part in text.split(";")]


def _groups(bodies: Iterable[str]) -> set[str]:
    return {g.strip() for body in bodies for g in header(body, "group")}


def _known(ref: str, names: set[str], groups: set[str]) -> bool:
    group, _, name = ref.rpartition("\\")
    return name.strip() in names and (not group or group.strip() in groups)


def _norm(body: str) -> str:
    return body.replace("\r", "")


def validate_file(
    english: str,
    french: str,
    *,
    known_names: set[str],
    english_names: set[str] | None = None,
    restedxp: Iterable[str] = (),
    known_groups: Iterable[str] = (),
    english_groups: Iterable[str] = (),
) -> list[str]:
    """Erreurs du fichier français `french` généré depuis `english` (liste vide : valide). `known_names` : noms des
    guides des autres fichiers français ; `english_names` : ceux des autres fichiers anglais ; `restedxp` : guides
    français de RestedXP, recopiés tels quels (ni leur texte ni leurs `#next` ne sont contrôlés)."""
    theirs = {_norm(b) for b in restedxp}
    errors: list[str] = []
    lines = french.split("\n")
    if lines[0].rstrip("\r") != GUARD:
        errors.append("première ligne : garde-fou frFR absent")
    if len(lines) < 2 or not lines[1].startswith(MARKER):
        errors.append("deuxième ligne : marqueur FR1 absent")
    extra = sum(1 for ln in lines if _END.search(ln) and ln.strip() != "]])") - sum(
        1 for ln in english.split("\n") if _END.search(ln) and ln.strip() != "]])"
    )
    if extra > 0:
        errors.append(f"{extra} ligne(s) avec « ]] » introduit (fin de la chaîne Lua)")
    en_guides, fr_guides = guide_bodies(english), guide_bodies(french)
    if len(en_guides) != len(fr_guides):
        errors.append(f"{len(fr_guides)} guide(s) en français pour {len(en_guides)} en anglais")
        return errors
    fr_known = _names(fr_guides) | known_names
    en_known = _names(en_guides) | (english_names or set())
    fr_groups, en_groups = _groups(fr_guides) | set(known_groups), _groups(en_guides) | set(english_groups)
    for k, (en_body, fr_body) in enumerate(zip(en_guides, fr_guides, strict=True), 1):
        name = (header(en_body, "name") or [f"n°{k}"])[0].strip()
        if _norm(fr_body) in theirs:
            continue
        a, b = en_body.split("\n"), fr_body.split("\n")
        if len(a) != len(b):
            errors.append(f"guide {name} : {len(b)} lignes en français pour {len(a)} en anglais (commande perdue)")
            continue
        for n, (x, y) in enumerate(zip(a, b, strict=True), 1):
            problem = _check_line(n, parse_line(x.rstrip("\r")), parse_line(y.rstrip("\r")))
            if problem:
                errors.append(f"guide {name}, {problem}")
        en_next, fr_next = _nexts(en_body), _nexts(fr_body)
        if len(en_next) != len(fr_next):
            errors.append(f"guide {name} : #next change de nombre de guides")
            continue
        for x, y in zip(en_next, fr_next, strict=True):
            if _known(x, en_known, en_groups) and not _known(y, fr_known, fr_groups):
                errors.append(f"guide {name} : #next « {y} » ne désigne aucun guide français (anglais : « {x} »)")
    return errors
