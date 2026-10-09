"""Conversation « jeu » du pont (P06a, bloc C, décision 212) : `claude -p` en `stream-json`, ligne de commande retenue
par la sonde 0.4 du plan. Outils intégrés réduits à `Skill` (skills du plugin), liste d'autorisations fermée (`Skill`
et les six outils forever), `dontAsk`, réglages ignorés (`--restricted` : ni hooks du projet ni plugins de
l'utilisateur), seul serveur MCP `forever` (`--strict-mcp-config`, `--mcp-config`), plugin par `--plugin-dir`, dossier
de travail dédié hors du dépôt. La question passe par l'entrée standard, en octets UTF-8, jamais par la ligne de
commande ; aucun shell : un texte tapé en jeu ne devient jamais une commande. Le seul exécutable lancé est `claude` ;
le seul processus que le pont arrête est le sien (et ses enfants, par un objet de tâche Windows), au-delà du délai."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from forever.errors import EXIT_USAGE, ForeverError

FOREVER_TOOLS: tuple[str, ...] = (
    "mcp__forever__forever_status",
    "mcp__forever__forever_lookup",
    "mcp__forever__forever_player_profile",
    "mcp__forever__forever_explain_mechanic",
    "mcp__forever__forever_sim_leveling",
    "mcp__forever__forever_build",
)
ALLOWED_TOOLS: tuple[str, ...] = ("Skill", *FOREVER_TOOLS)
DEFAULT_TIMEOUT_S = 180.0
# Variables d'une session Claude Code parente, retirées : la conversation « jeu » est une session à part.
_PARENT_SESSION_VARS = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SSE_PORT")
_CERTAINTY_ORDER = ("suppose", "probable", "certain")
_CREATE_NO_WINDOW = 0x08000000

Popen = Callable[..., Any]


class AgentError(ForeverError):
    """`claude` introuvable ou impossible à lancer."""

    exit_code = EXIT_USAGE

    def __init__(self, message: str) -> None:
        super().__init__("bridge_agent", message, "installer Claude Code (commande `claude`) sur ce poste")


@dataclass(frozen=True)
class AgentResult:
    text: str
    session_id: str | None
    denied: list[str] = field(default_factory=list)
    provenances: list[dict[str, Any]] = field(default_factory=list)
    link: str | None = None
    is_error: bool = False
    error: str | None = None
    tools: list[str] = field(default_factory=list)
    timings: dict[str, Any] = field(default_factory=dict, compare=False)  # durées des étapes (s), stream_timings
    cost_usd: float | None = None


def find_claude(which: Callable[[str], str | None] = shutil.which) -> str:
    path = which("claude")
    if not path:
        raise AgentError("commande `claude` introuvable dans le PATH")
    return path


def conversation_dir(cache_dir: Path) -> Path:
    """Dossier de travail de la conversation « jeu » : hors du dépôt (ni `CLAUDE.md`, ni skills de développement)."""
    return cache_dir / "bridge" / "conversation"


def mcp_config(repo_root: Path) -> dict[str, Any]:
    """Configuration MCP de la conversation : le seul serveur `forever` du dépôt, lancé par l'interpréteur du projet
    en module (`python -m forever`) et sans synchroniser l'environnement ; jamais par le lanceur de la commande
    `forever` (dossier Scripts de l'environnement), qu'un serveur en cours verrouillerait contre `uv sync` (chaque
    question posée en jeu lance ce serveur)."""
    return {
        "mcpServers": {
            "forever": {
                "command": "uv",
                "args": ["run", "--no-sync", "--quiet", "--project", str(repo_root), "python", "-m", "forever", "mcp"],
            }
        }
    }


def write_mcp_config(directory: Path, repo_root: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "mcp.json"
    path.write_bytes(json.dumps(mcp_config(repo_root), ensure_ascii=False, indent=2).encode("utf-8"))
    return path


def claude_argv(
    *,
    claude: str,
    plugin_dir: Path,
    mcp_config: Path,
    system_prompt: str,
    session_id: str | None = None,
    model: str | None = None,
) -> list[str]:
    """Liste d'arguments de `claude` (jamais une chaîne) ; la question n'y figure pas."""
    args = [
        claude,
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--tools",
        "Skill",
        "--restricted",
        "--strict-mcp-config",
        "--mcp-config",
        str(mcp_config),
        "--plugin-dir",
        str(plugin_dir),
        "--allowedTools",
        ",".join(ALLOWED_TOOLS),
        "--permission-mode",
        "dontAsk",
        "--permission-prompts",
        "none",
        "--append-system-prompt",
        system_prompt,
    ]
    if session_id:
        args += ["--resume", session_id]
    if model:
        args += ["--model", model]
    return args


def claude_env(environ: Mapping[str, str], repo_root: Path) -> dict[str, str]:
    """Environnement de la conversation : données du dépôt, aucun outil forever en réseau, hook de démarrage muet."""
    env = {k: v for k, v in environ.items() if k not in _PARENT_SESSION_VARS}
    env["FOREVER_HOME"] = str(repo_root)
    env["FOREVER_OFFLINE"] = "1"
    env["FOREVER_BRIDGE"] = "1"
    return env


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(c.get("text", "")) for c in content if isinstance(c, dict) and c.get("type") == "text")
    return ""


def _find_link(value: Any) -> str | None:
    if isinstance(value, dict):
        export = value.get("export")
        if isinstance(export, dict):
            tf = export.get("talents_forever")
            if isinstance(tf, dict) and isinstance(tf.get("link"), str):
                return str(tf["link"])
    return None


def parse_stream(lines: Iterable[str]) -> AgentResult:
    """Résultat d'une conversation lu dans le flux `stream-json` : texte final, session, refus, blocs `provenance`
    des outils forever, lien Talents Forever d'un résultat de `forever_build`."""
    names: dict[str, str] = {}
    provenances: list[dict[str, Any]] = []
    tools: list[str] = []
    link: str | None = None
    last_text = ""
    final: dict[str, Any] | None = None
    session_id: str | None = None
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        session_id = event.get("session_id") or session_id
        kind = event.get("type")
        content = (event.get("message") or {}).get("content") if kind in ("assistant", "user") else None
        if kind == "assistant" and isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    names[str(block.get("id"))] = str(block.get("name"))
                    tools.append(str(block.get("name")))
                elif block.get("type") == "text":
                    last_text = str(block.get("text", ""))
        elif kind == "user" and isinstance(content, list):
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                if not names.get(str(block.get("tool_use_id")), "").startswith("mcp__forever__"):
                    continue
                try:
                    value = json.loads(_content_text(block.get("content")))
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict) and isinstance(value.get("provenance"), dict):
                    provenances.append(value["provenance"])
                link = _find_link(value) or link
        elif kind == "result":
            final = event
    if final is None:
        return AgentResult(
            text=last_text,
            session_id=session_id,
            provenances=provenances,
            link=link,
            is_error=True,
            error="claude s'est arrêté sans résultat",
            tools=tools,
        )
    denied = [str(d.get("tool_name")) for d in final.get("permission_denials") or [] if isinstance(d, dict)]
    cost = final.get("total_cost_usd")
    text = final.get("result") if isinstance(final.get("result"), str) else last_text
    is_error = bool(final.get("is_error"))
    return AgentResult(
        text=str(text or ""),
        session_id=final.get("session_id") or session_id,
        denied=denied,
        provenances=provenances,
        link=link,
        is_error=is_error,
        error=str(text or "erreur de claude") if is_error else None,
        tools=tools,
        cost_usd=float(cost) if isinstance(cost, int | float) else None,
    )


def stream_timings(timed: Sequence[tuple[float, str]], started: float) -> dict[str, Any]:
    """Durées d'une conversation d'après l'heure d'arrivée de chaque événement du flux, depuis le lancement de
    `claude` : `init_s` (claude et serveur MCP prêts), chaque appel d'outil (`tools`, de la demande au résultat),
    `tools_s` (leur somme), `first_text_s`, `result_s` (réponse complète) ; le reste est le temps du modèle."""
    out: dict[str, Any] = {"init_s": None, "first_text_s": None, "result_s": None, "tools": [], "tools_s": 0.0}
    asked: dict[str, tuple[str, float]] = {}
    for when, raw in timed:
        try:
            event = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(event, dict):
            continue
        at = round(when - started, 3)
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init" and out["init_s"] is None:
            out["init_s"] = at
        content = (event.get("message") or {}).get("content") if kind in ("assistant", "user") else None
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                asked[str(block.get("id"))] = (str(block.get("name")), at)
            elif block.get("type") == "tool_result" and str(block.get("tool_use_id")) in asked:
                name, start = asked.pop(str(block.get("tool_use_id")))
                out["tools"].append({"tool": name, "start_s": start, "seconds": round(at - start, 3)})
            elif block.get("type") == "text" and out["first_text_s"] is None:
                out["first_text_s"] = at
        if kind == "result":
            out["result_s"] = at
    out["tools_s"] = round(sum(x["seconds"] for x in out["tools"]), 3)
    return out


def provenance_line(provenances: Sequence[Mapping[str, Any]]) -> str:
    """Ligne normalisée ajoutée à la réponse : versions des données et certitudes, la plus faible d'abord."""
    if not provenances:
        return "Aucun outil forever appelé : réponse sans chiffre de jeu."
    versions = list(dict.fromkeys(str(p.get("game_version")) for p in provenances if p.get("game_version")))
    seen = {str(p.get("certainty")) for p in provenances if p.get("certainty")}
    order = [c for c in _CERTAINTY_ORDER if c in seen] + sorted(seen - set(_CERTAINTY_ORDER))
    return f"Données {', '.join(versions) or 'inconnues'} · {', '.join(order) or 'certitude inconnue'}"


class _Job:
    """Objet de tâche Windows qui arrête le processus et ses enfants à sa fermeture ; sans effet ailleurs."""

    def __init__(self, proc: Any) -> None:
        self.handle = None
        handle = getattr(proc, "_handle", None)
        if sys.platform != "win32" or handle is None:
            return
        try:
            import ctypes
            from ctypes import wintypes

            class IoCounters(ctypes.Structure):
                _fields_ = [(n, ctypes.c_ulonglong) for n in ("r", "w", "o", "rb", "wb", "ob")]

            class Basic(ctypes.Structure):
                _fields_ = [
                    ("PerProcessUserTimeLimit", ctypes.c_longlong),
                    ("PerJobUserTimeLimit", ctypes.c_longlong),
                    ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD),
                ]

            class Extended(ctypes.Structure):
                _fields_ = [
                    ("Basic", Basic),
                    ("Io", IoCounters),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t),
                ]

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateJobObjectW.restype = wintypes.HANDLE
            job = kernel32.CreateJobObjectW(None, None)
            if not job:
                return
            info = Extended()
            info.Basic.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            kernel32.SetInformationJobObject(wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info))
            if kernel32.AssignProcessToJobObject(wintypes.HANDLE(job), wintypes.HANDLE(int(handle))):
                self.handle = job
                self._close = kernel32.CloseHandle
            else:
                kernel32.CloseHandle(wintypes.HANDLE(job))
        except (OSError, AttributeError, ValueError):
            self.handle = None

    def close(self) -> None:
        if self.handle is not None:
            from ctypes import wintypes

            self._close(wintypes.HANDLE(self.handle))
            self.handle = None


def run_claude(
    argv: list[str],
    prompt: str,
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout_s: float = DEFAULT_TIMEOUT_S,
    popen: Popen = subprocess.Popen,
) -> AgentResult:
    """Lance `claude` (liste d'arguments, sans shell), lui passe la question sur l'entrée standard et lit son flux ;
    au-delà de `timeout_s`, arrête le processus et ses enfants et rend une erreur."""
    flags = _CREATE_NO_WINDOW if sys.platform == "win32" else 0
    started = time.monotonic()
    proc = popen(
        argv,
        cwd=cwd,
        env=dict(env),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=flags,
    )
    job = _Job(proc)
    out: list[str] = []
    arrivals: list[float] = []
    err: list[bytes] = []

    def read_out() -> None:
        for line in proc.stdout:
            arrivals.append(time.monotonic())
            out.append(line.decode("utf-8", errors="replace"))

    def read_err() -> None:
        if proc.stderr is not None:
            err.append(proc.stderr.read())

    reader = threading.Thread(target=read_out, daemon=True)
    errors = threading.Thread(target=read_err, daemon=True)
    reader.start()
    errors.start()
    try:
        proc.stdin.write(prompt.encode("utf-8"))
        proc.stdin.close()
    except OSError:
        pass
    reader.join(timeout_s)
    if reader.is_alive():
        proc.kill()
        job.close()
        reader.join(5)
        return AgentResult(text="", session_id=None, is_error=True, error=f"délai dépassé ({timeout_s:g} s)")
    errors.join(5)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    job.close()
    result = replace(parse_stream(out), timings=stream_timings(list(zip(arrivals, out, strict=False)), started))
    if result.is_error and not result.text and err and err[0]:
        tail = err[0].decode("utf-8", errors="replace").strip()[-300:]
        return replace(result, error=f"{result.error} : {tail}")
    return result


def ask(
    prompt: str,
    *,
    session_id: str | None,
    claude: str,
    plugin_dir: Path,
    mcp_path: Path,
    cwd: Path,
    env: Mapping[str, str],
    system_prompt: str | None = None,
    model: str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    popen: Popen = subprocess.Popen,
) -> AgentResult:
    """Un message de la conversation « jeu », repris de `session_id` ; une reprise refusée (session perdue) est
    relancée une fois en nouvelle session."""
    if system_prompt is None:
        from forever.bridge.prompt import SYSTEM_PROMPT

        system_prompt = SYSTEM_PROMPT

    def once(session: str | None) -> AgentResult:
        args = claude_argv(
            claude=claude,
            plugin_dir=plugin_dir,
            mcp_config=mcp_path,
            system_prompt=system_prompt,
            session_id=session,
            model=model,
        )
        return run_claude(args, prompt, cwd=cwd, env=env, timeout_s=timeout_s, popen=popen)

    result = once(session_id)
    if session_id and result.is_error and not result.tools and "délai" not in (result.error or ""):
        result = once(None)
    return result
