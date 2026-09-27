"""Contrôle statique des règles de l'addon (CLAUDE.md, section « Addon » ; docs/ADDON.md), sans exécuter de Lua.

    uv run python scripts/check_addon.py [dossier…]      (défaut : chaque dossier de addon/)

Règles : SavedVariable initialisée dans le gestionnaire d'ADDON_LOADED, jamais d'alias ni d'usage au niveau du
fichier ; chaque RegisterEvent sous pcall ; aucune fonction d'action ; aucun abonnement au journal de combat ;
`.toc` sans lignes fusionnées, `## Interface: 16001`, fichiers listés présents. Commentaires et chaînes ignorés
(sauf les noms d'événement, qui s'écrivent dans des chaînes). Chaque erreur nomme le fichier et la ligne."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INTERFACE = "16001"  # interface de l'API du client Forever (Mainline 12.1.5, build 70009)
SAVED_VARIABLE = "ForeverLoggerDB"
FORBIDDEN = frozenset(
    {"CastSpell", "CastSpellByName", "CastSpellByID", "UseAction", "SendChatMessage", "RunMacro", "RunMacroText"}
)
COMBAT_LOG = frozenset({"COMBAT_LOG_EVENT", "COMBAT_LOG_EVENT_UNFILTERED"})
OPENERS = frozenset({"function", "if", "do", "repeat"})
CLOSERS = frozenset({"end", "until"})
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_LONG_OPEN = re.compile(r"\[(=*)\[")


def _mask(text: str) -> tuple[str, list[tuple[int, str]]]:
    """(code où commentaires et chaînes sont remplacés par des espaces, sauts de ligne gardés ; chaînes littérales
    avec leur position)."""
    out: list[str] = []
    strings: list[tuple[int, str]] = []
    i, n = 0, len(text)

    def blank(chunk: str) -> str:
        return "".join("\n" if c == "\n" else " " for c in chunk)

    while i < n:
        c = text[i]
        if text.startswith("--", i):
            long = _LONG_OPEN.match(text, i + 2)
            if long:
                end = text.find("]" + long[1] + "]", long.end())
                end = n if end < 0 else end + len(long[1]) + 2
            else:
                end = text.find("\n", i)
                end = n if end < 0 else end
            out.append(blank(text[i:end]))
            i = end
        elif c in ("'", '"'):
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            strings.append((i, text[i + 1 : j]))
            out.append(blank(text[i : j + 1]))
            i = j + 1
        elif c == "[" and (long := _LONG_OPEN.match(text, i)):
            end = text.find("]" + long[1] + "]", long.end())
            end = n if end < 0 else end + len(long[1]) + 2
            strings.append((i, text[long.end() : end]))
            out.append(blank(text[i:end]))
            i = end
        else:
            out.append(c)
            i += 1
    return "".join(out), strings


def _line(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def check_lua(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    code, strings = _mask(text)
    lines = code.splitlines()
    name = path.name
    errors: list[str] = []
    stack: list[str] = []
    uses_db = False
    for m in _WORD.finditer(code):
        word, line = m[0], _line(code, m.start())
        in_function = "function" in stack
        if word in OPENERS:
            stack.append(word)
        elif word in CLOSERS and stack:
            stack.pop()
        elif word == SAVED_VARIABLE:
            uses_db = True
            if not in_function:
                statement = lines[line - 1]
                if re.match(r"\s*local\b", statement):
                    errors.append(
                        f"{name}:{line} : alias local de {SAVED_VARIABLE} au niveau du fichier (table perdue)"
                    )
                elif re.match(rf"\s*{SAVED_VARIABLE}\s*=", statement):
                    errors.append(
                        f"{name}:{line} : {SAVED_VARIABLE} initialisée hors d'une fonction : l'initialiser dans le "
                        "gestionnaire d'ADDON_LOADED"
                    )
                else:
                    errors.append(f"{name}:{line} : {SAVED_VARIABLE} utilisée hors d'une fonction")
        elif word in ("RegisterEvent", "RegisterUnitEvent"):
            before = code[code.rfind("\n", 0, m.start()) + 1 : m.start()]
            if not re.search(r"pcall\s*\(\s*[\w.:]*$", before):
                errors.append(f"{name}:{line} : {word} sans pcall (un événement inconnu du client lève une erreur)")
        elif word in FORBIDDEN or word.startswith("CastSpell"):
            errors.append(f"{name}:{line} : fonction interdite {word} (aucune action de jeu)")
        if word in COMBAT_LOG:
            errors.append(f"{name}:{line} : abonnement au journal de combat interdit ({word})")
    for pos, value in strings:
        if value in COMBAT_LOG:
            errors.append(f"{name}:{_line(text, pos)} : abonnement au journal de combat interdit ({value})")
    if uses_db and not any(value == "ADDON_LOADED" for _, value in strings) and "ADDON_LOADED" not in code:
        errors.append(f"{name}:1 : {SAVED_VARIABLE} sans initialisation dans ADDON_LOADED")
    return errors


def check_toc(path: Path) -> list[str]:
    name = path.name
    errors: list[str] = []
    interface_seen = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if "##" in line and not line.startswith("##"):
            errors.append(f"{name}:{number} : lignes fusionnées (« ## » au milieu d'une ligne)")
            continue
        if line.startswith("## Interface:"):
            interface_seen = True
            values = [v.strip() for v in line.split(":", 1)[1].split(",")]
            if INTERFACE not in values:
                errors.append(f"{name}:{number} : ## Interface: {INTERFACE} attendu (lu : {', '.join(values)})")
        elif line.strip() and not line.startswith("#") and not (path.parent / line.strip()).is_file():
            errors.append(f"{name}:{number} : fichier listé introuvable « {line.strip()} »")
    if not interface_seen:
        errors.append(f"{name}:1 : ## Interface: {INTERFACE} absent")
    return errors


def check_addon(directory: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(directory.iterdir()):
        if path.suffix == ".lua":
            errors += check_lua(path)
        elif path.suffix == ".toc":
            errors += check_toc(path)
    return errors


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    dirs = [Path(a) for a in args] or sorted(p for p in (ROOT / "addon").iterdir() if p.is_dir())
    errors = [e for d in dirs for e in check_addon(d)]
    for e in errors:
        print(f"  ERREUR : {e}")
    print(f"Règles de l'addon : {len(dirs)} dossier(s), {len(errors)} erreur(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
