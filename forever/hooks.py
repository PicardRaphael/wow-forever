"""Hooks du plugin Claude Code (T06, décision D4) : ligne de fraîcheur au démarrage, contrôle des chiffres de jeu en
fin de réponse.

Le plugin reste mince : `plugin/hooks/hooks.json` appelle `forever hook session-start` et `forever hook check-numbers`.
Les deux n'agissent que là où le plugin sert (dans le dépôt pour la ligne de fraîcheur ; pour le contrôle des
chiffres, dans une session où un skill de jeu du plugin a produit la réponse, jamais dans une session de travail sur
une tranche, PV1), ne lèvent jamais d'exception et n'appellent pas le réseau."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from forever.config import REPO_ROOT, Deps

if TYPE_CHECKING:
    from forever.pipeline.gitops import Runner

Spawn = Callable[[Sequence[str]], None]

_NUM = r"\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?"
_UNITS = (
    r"%|s|sec|secondes?|min|minutes?|h|heures?|mana|dégâts|degats|damage|points?|pv|hp|dps|xp/h|xp|pm|m|mètres?"
    r"|metres?|yd|yards?"
)
_JOIN = r"\s?(?:à|a|-|–|/|et|ou)\s?"
GAME_NUMBER = re.compile(
    rf"(?<![\w.,])(?:{_NUM})(?:{_JOIN}(?:{_NUM}))*\s?(?:points?\s+)?(?:de\s+|d')?(?:{_UNITS})(?![\w/])",
    re.IGNORECASE,
)
"""Chiffre de jeu dans un texte : nombre (ou suite « 20 à 22 ») suivi d'une unité de jeu, « points de » et « de »
permis entre les deux (« 25 de mana », « 18 à 20 points de dégâts »). Même motif pour `scripts/check_game_numbers.py`."""

NUMBERS_MARKER = "[forever:chiffres]"
"""Préfixe du message du contrôle des chiffres (cherché par les correcteurs de l'évaluation)."""

_NUMBER = re.compile(_NUM)
_ANY_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_FOREVER_TOOL = re.compile(r"^mcp__.+__forever_\w+$")
_FOREVER_SKILL = re.compile(r"^(?:forever:)?forever-[\w-]+$")
_SOURCE_AGENT = re.compile(r"^(?:forever:)?forever-sim-runner$")
_RESEARCH_AGENT = re.compile(r"^(?:forever:)?forever-web-researcher$")
_ADDRESS = re.compile(r"https?://", re.IGNORECASE)
_FOREVER_AGENT = re.compile(r"^(?:forever:)?forever-[\w-]+$")
# Session de travail sur le dépôt (skills du projet, commandes) : le contrôle des chiffres ne s'y applique jamais.
_WORK_SKILL = re.compile(r"^(?:[\w-]+:)?(?:tranche|verifier)$")
_WORK_COMMAND = re.compile(r"<command-name>/?(?:tranche|verifier)</command-name>")
_GAME_COMMAND = re.compile(r"<command-name>/?(?:forever:)?forever-[\w-]+</command-name>")
_EPS = 1e-9
# Entier affiché avec des zéros finals (20, 12 300) : lu comme un arrondi à la dizaine, à la centaine…, écart borné à
# cette fraction de la valeur (paramètre de l'outil). « 20 » accepte ainsi une valeur d'outil entre 19 et 21.
_ROUNDING_REL = 0.05


@dataclass(frozen=True)
class GameNumber:
    text: str
    values: tuple[float, ...]
    decimals: tuple[int, ...]
    unit: str


def _parse(raw: str) -> tuple[float, int]:
    compact = re.sub(r"[ \u00a0\u202f]", "", raw).replace(",", ".")
    decimals = len(compact.split(".", 1)[1]) if "." in compact else 0
    return float(compact), decimals


def game_numbers(text: str) -> list[GameNumber]:
    """Chiffres de jeu d'un texte, dans l'ordre."""
    found = []
    for m in GAME_NUMBER.finditer(text):
        phrase = m.group(0)
        numbers = list(_NUMBER.finditer(phrase))
        parsed = [_parse(n.group(0)) for n in numbers]
        unit = phrase[numbers[-1].end() :].strip().lower()
        unit = re.sub(r"^(?:points?\s+)?(?:de\s+|d')?", "", unit) or unit
        found.append(GameNumber(phrase, tuple(v for v, _ in parsed), tuple(d for _, d in parsed), unit))
    return found


def _blocks(line: Mapping[str, Any]) -> list[Any]:
    message = line.get("message")
    if not isinstance(message, Mapping):
        return []
    content = message.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return list(content) if isinstance(content, list) else []


def _tool_uses(lines: Iterable[Mapping[str, Any]]) -> Iterator[Mapping[str, Any]]:
    for line in lines:
        if line.get("type") == "assistant":
            for b in _blocks(line):
                if isinstance(b, Mapping) and b.get("type") == "tool_use":
                    yield b


def _is_forever_use(use: Mapping[str, Any]) -> bool:
    name = str(use.get("name", ""))
    inp = use.get("input") if isinstance(use.get("input"), Mapping) else {}
    assert isinstance(inp, Mapping)
    if _FOREVER_TOOL.match(name):
        return True
    if name == "Skill":
        return bool(_FOREVER_SKILL.match(str(inp.get("skill", ""))))
    if name in ("Agent", "Task"):
        return bool(_FOREVER_AGENT.match(str(inp.get("subagent_type", ""))))
    return False


def _is_source_use(use: Mapping[str, Any]) -> bool:
    name = str(use.get("name", ""))
    inp = use.get("input") if isinstance(use.get("input"), Mapping) else {}
    assert isinstance(inp, Mapping)
    if _FOREVER_TOOL.match(name):
        return True
    return name in ("Agent", "Task") and bool(_SOURCE_AGENT.match(str(inp.get("subagent_type", ""))))


def _is_research_use(use: Mapping[str, Any]) -> bool:
    inp = use.get("input") if isinstance(use.get("input"), Mapping) else {}
    assert isinstance(inp, Mapping)
    return str(use.get("name", "")) in ("Agent", "Task") and bool(
        _RESEARCH_AGENT.match(str(inp.get("subagent_type", "")))
    )


def _texts(obj: Any) -> Iterator[str]:
    """Textes d'un résultat d'outil (chaîne, blocs `text`, listes)."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, list):
        for v in obj:
            yield from _texts(v.get("text") if isinstance(v, Mapping) and v.get("type") == "text" else v)


def _sourced_lines(obj: Any) -> Iterator[str]:
    """Lignes du rapport de `forever-web-researcher` qui portent l'adresse de leur source : seuls leurs chiffres sont
    des sources (affirmation d'une source nommée, à citer comme telle, jamais comme un fait du projet)."""
    for text in _texts(obj):
        for line in text.splitlines():
            if _ADDRESS.search(line):
                yield line


def session_used_forever(lines: Iterable[Mapping[str, Any]]) -> bool:
    """Vrai si le transcript contient un appel d'outil MCP `forever_*`, d'un skill `forever-*` ou d'un sous-agent
    `forever-*`."""
    return any(_is_forever_use(u) for u in _tool_uses(lines))


def _is_game_skill(use: Mapping[str, Any]) -> bool:
    inp = use.get("input") if isinstance(use.get("input"), Mapping) else {}
    assert isinstance(inp, Mapping)
    return str(use.get("name", "")) == "Skill" and bool(_FOREVER_SKILL.match(str(inp.get("skill", ""))))


def _is_work_marker(line: Mapping[str, Any], use: Mapping[str, Any] | None = None) -> bool:
    if use is not None:
        inp = use.get("input") if isinstance(use.get("input"), Mapping) else {}
        assert isinstance(inp, Mapping)
        return str(use.get("name", "")) == "Skill" and bool(_WORK_SKILL.match(str(inp.get("skill", ""))))
    if line.get("type") != "user":
        return False
    return any(_WORK_COMMAND.search(text) for text in _texts(_user_content(line)))


def _user_content(line: Mapping[str, Any]) -> Any:
    message = line.get("message")
    return message.get("content") if isinstance(message, Mapping) else None


def session_is_game_answer(lines: Iterable[Mapping[str, Any]]) -> bool:
    """Vrai si un skill de jeu du plugin (`forever-*` : routeur, leveling, Mage, PvP, builds…) a servi dans la session
    et qu'aucune marque de travail sur le dépôt n'y figure (commande ou skill `tranche`, `verifier`) : seules ces
    réponses passent le contrôle des chiffres (PV1, demande de l'utilisateur du 2026-09-30). Un outil ou un
    sous-agent forever seul ne suffit pas."""
    all_lines = list(lines)
    if any(_is_work_marker(line) for line in all_lines):
        return False
    uses = list(_tool_uses(all_lines))
    if any(_is_work_marker({}, u) for u in uses):
        return False
    commands = any(
        _GAME_COMMAND.search(text)
        for line in all_lines
        if line.get("type") == "user"
        for text in _texts(_user_content(line))
    )
    return commands or any(_is_game_skill(u) for u in uses)


def _values(obj: Any) -> Iterator[float]:
    """Nombres d'un résultat d'outil : valeurs numériques et nombres écrits dans les textes ; le bloc `provenance`
    (version, empreinte, date, couverture) n'est pas une source de chiffres de jeu."""
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, int | float):
        yield float(obj)
    elif isinstance(obj, str):
        stripped = obj.strip()
        if stripped[:1] in ("{", "["):
            try:
                yield from _values(json.loads(stripped))
                return
            except ValueError:
                pass
        for m in _ANY_NUMBER.finditer(obj):
            yield _parse(m.group(0))[0]
        # nombres écrits avec une espace des milliers (« 11 153 », rapport d'un sous-agent), lus aussi en entier
        for m in _NUMBER.finditer(obj):
            if any(c in m.group(0) for c in "   "):
                yield _parse(m.group(0))[0]
    elif isinstance(obj, Mapping):
        for k, v in obj.items():
            if k != "provenance":
                yield from _values(v)
    elif isinstance(obj, list):
        for v in obj:
            if isinstance(v, Mapping) and v.get("type") == "text":
                yield from _values(v.get("text"))
            else:
                yield from _values(v)


def _sources(lines: list[Mapping[str, Any]]) -> list[float]:
    uses = list(_tool_uses(lines))
    source_ids = {str(u.get("id")) for u in uses if _is_source_use(u)}
    research_ids = {str(u.get("id")) for u in uses if _is_research_use(u)}
    values: list[float] = []
    for line in lines:
        if line.get("type") != "user":
            continue
        for b in _blocks(line):
            if not isinstance(b, Mapping):
                continue
            if b.get("type") == "tool_result":
                if str(b.get("tool_use_id")) in source_ids:
                    values.extend(_values(b.get("content")))
                elif str(b.get("tool_use_id")) in research_ids:
                    for sourced in _sourced_lines(b.get("content")):
                        values.extend(_values(sourced))
            elif b.get("type") == "text" and not line.get("isMeta"):
                # question de l'utilisateur (le corps d'un skill chargé est marqué isMeta et ne compte pas)
                values.extend(_parse(m.group(0))[0] for m in _NUMBER.finditer(str(b.get("text", ""))))
    return values


def _last_assistant_text(lines: list[Mapping[str, Any]]) -> str:
    for line in reversed(lines):
        if line.get("type") == "assistant":
            texts = [
                str(b.get("text", "")) for b in _blocks(line) if isinstance(b, Mapping) and b.get("type") == "text"
            ]
            if texts:
                return "\n".join(texts)
    return ""


def _matches(x: float, decimals: int, unit: str, v: float) -> bool:
    if decimals > 0:
        tol = 0.5 * 10**-decimals
    else:
        digits = str(int(x))
        zeros = len(digits) - len(digits.rstrip("0")) if x >= 10 else 0
        tol = min(0.5 * 10**zeros, _ROUNDING_REL * x) if zeros else 0.5
    candidates = [abs(v)]  # un écart négatif de l'outil se cite en valeur absolue, le signe dit en mots
    if unit == "%":
        candidates.append(abs(v) * 100)
    elif unit.startswith("min"):
        candidates.append(abs(v) / 60)
    elif unit in ("h", "heure", "heures"):
        candidates.append(abs(v) / 3600)
    return any(abs(x - c) <= tol + _EPS for c in candidates)


def unsourced_numbers(lines: Iterable[Mapping[str, Any]], last_message: str | None = None) -> list[str]:
    """Chiffres de jeu de la dernière réponse absents des résultats des outils `forever_*` (et du sous-agent de
    simulation), des lignes sourcées (avec une adresse) du rapport du sous-agent de recherche et de la question de
    l'utilisateur. Égalité à l'arrondi affiché près ; fraction acceptée pour un
    pourcentage, secondes pour des minutes ou des heures ; virgule et point équivalents."""
    all_lines = list(lines)
    text = last_message if last_message is not None else _last_assistant_text(all_lines)
    sources = _sources(all_lines)
    out: list[str] = []
    for g in game_numbers(text):
        ok = all(any(_matches(x, d, g.unit, v) for v in sources) for x, d in zip(g.values, g.decimals, strict=True))
        if not ok and g.text not in out:
            out.append(g.text)
    return out


def read_transcript(path: Path) -> list[dict[str, Any]]:
    """Lignes JSON d'un transcript (lignes illisibles ignorées ; fichier absent : liste vide)."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out = []
    for line in raw.splitlines():
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def check_numbers_output(hook_input: Mapping[str, Any]) -> dict[str, Any] | None:
    """Sortie du hook Stop : message à l'utilisateur, sans blocage ; None si rien à signaler ou hors de forever."""
    try:
        path = hook_input.get("transcript_path")
        if not path:
            return None
        lines = read_transcript(Path(str(path)))
        if not session_is_game_answer(lines):
            return None
        last = hook_input.get("last_assistant_message")
        found = unsourced_numbers(lines, str(last) if last is not None else None)
    except Exception:  # noqa: BLE001 : un hook ne doit jamais gêner la session
        return None
    if not found:
        return None
    listed = ", ".join(f"« {t} »" for t in found)
    return {
        "systemMessage": (
            f"{NUMBERS_MARKER} Chiffres de jeu sans source dans les outils forever de la session : {listed}. "
            "Ne pas s'y fier sans vérification (demander la valeur à forever_lookup, forever_build ou "
            "forever_sim_leveling)."
        )
    }


_FRESHNESS_FR = {"fresh": "à jour", "stale": "en retard", "silent": "incertaine", "unknown": "inconnue"}


def session_line(deps: Deps, environ: Mapping[str, str]) -> str:
    """Ligne de fraîcheur, cache seulement (aucun réseau) ; ne lève jamais d'exception."""
    from forever.status import status_report
    from forever.timefmt import format_age

    todo = "lancer `uv run forever status`"
    try:
        rep = status_report(deps, allow_network=False)
    except Exception as exc:  # noqa: BLE001 : un hook ne doit jamais gêner la session
        line = f"WoW Forever · état illisible ({type(exc).__name__}) : {todo}"
    else:
        f = rep["freshness"]
        parts = [f"WoW Forever · données {rep['local_version']}"]
        if not rep["integrity"]["ok"]:
            parts.append(f"données altérées, consultations refusées : {todo}")
        state = _FRESHNESS_FR.get(f["freshness"], f["freshness"])
        if f["age_hours"] is None:
            parts.append(f"fraîcheur {state} (jamais vérifiée : {todo})")
        else:
            checked = f"vérifiée il y a {format_age(f['age_hours'])}"
            if f["freshness"] == "fresh":
                parts.append(f"fraîcheur {state} ({checked})")
            else:
                latest = (
                    f" : {f['latest_version']} publiée" if f["freshness"] == "stale" and f["latest_version"] else ""
                )
                parts.append(f"fraîcheur {state}{latest} ({checked} ; {todo})")
        parts.append(f"registre {rep['registry_coverage']}")
        line = " · ".join(parts)
    try:
        from forever.watch import watch_line

        extra = watch_line(deps)  # T08b, bloc G : changement relevé par la veille locale, une seule ligne
    except Exception:  # noqa: BLE001 : un hook ne doit jamais gêner la session
        extra = None
    if extra:
        line += f" · {extra}"
    if not environ.get("FOREVER_HOME"):
        line += " · FOREVER_HOME absent : lancer scripts/install_plugin.ps1 (le plugin en a besoin hors du dépôt)"
    return line.replace("\n", " ")


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def update_kickoff(deps: Deps, environ: Mapping[str, str], spawn: Spawn | None) -> None:
    """Démarrage de session (T08d, bloc G) : archivage des fichiers du client, puis passage `forever update --auto`
    détaché si aucun verrou n'est vivant et que le dernier passage a plus de 6 h. Jamais sans dossier du client ni
    avec FOREVER_OFFLINE ; ne lève jamais."""
    try:
        if environ.get("FOREVER_BRIDGE", "") not in ("", "0"):
            return  # conversation « jeu » du pont (P06a) : ni archivage ni passage, à chaque message repris
        wow = deps.wow_dir
        if wow is None or not wow.is_dir():
            return
        from forever import archive

        archive.archive_client_files(deps)
        if environ.get("FOREVER_OFFLINE", "") not in ("", "0") or spawn is None:
            return
        from forever.spawn import update_command
        from forever.update import due

        if due(deps.cache_dir, deps.now()):
            spawn(update_command())
    except Exception:  # noqa: BLE001 : un hook ne doit jamais gêner la session
        return


def update_line(deps: Deps, repo_root: Path, runner: Runner | None = None) -> str | None:
    """Partie « mise à jour » de la ligne de démarrage, sans réseau : passage en cours, attentes, `git pull` à
    faire quand `main` distant (relevé par le clone dédié) a avancé ; None s'il n'y a rien. Ne lève jamais."""
    try:
        from forever.pipeline import gitops
        from forever.update import SELF_CLEARING_KINDS, update_summary, written_text

        summary = update_summary(deps.cache_dir, deps.now())
        parts: list[str] = []
        if summary["running"]:
            parts.append("mise à jour en cours")
        last = summary["last"] or {}
        written = last.get("written") or []
        if written:
            parts.append(f"mise à jour : {written_text(written[-1])}")
        unread = [p for p in summary["pending"] if p.get("kind") in SELF_CLEARING_KINDS]
        parts += [f"{p.get('version')} : correctifs du serveur à lire (lancer le jeu sur ce build)" for p in unread]
        blocked = sum(1 for p in summary["pending"] if p.get("action") == "bloqué")
        n = len(summary["pending"]) - blocked - len(unread)
        if blocked:
            plural = "s" if blocked > 1 else ""
            parts.append(f"{blocked} écriture{plural} bloquée{plural}, session nécessaire : `forever update status`")
        if n:
            parts.append(f"{n} attente{'s' if n > 1 else ''} : `forever update status`")
        origin = last.get("origin_main")
        if origin and gitops.remote_ahead(runner or gitops.subprocess_runner, repo_root, str(origin)):
            parts.append("main distant a avancé : `git pull`")
        return " · ".join(parts).replace("\n", " ") if parts else None
    except Exception:  # noqa: BLE001 : un hook ne doit jamais gêner la session
        return None


def session_start_output(
    hook_input: Mapping[str, Any],
    deps: Deps,
    environ: Mapping[str, str],
    repo_root: Path = REPO_ROOT,
    *,
    spawn: Spawn | None = None,
    runner: Runner | None = None,
) -> dict[str, Any] | None:
    """Sortie du hook SessionStart : la ligne (visible et ajoutée au contexte) si la session s'ouvre dans le dépôt ;
    None ailleurs."""
    cwd = hook_input.get("cwd")
    if not cwd or not _inside(Path(str(cwd)), repo_root):
        return None
    update_kickoff(deps, environ, spawn)
    line = session_line(deps, environ)
    extra = update_line(deps, repo_root, runner)
    if extra:
        line = f"{line} · {extra}".replace("\n", " ")
    return {
        "systemMessage": line,
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": line},
    }
