"""Conversation « jeu » du pont (P06a, bloc C, décision 212) : `claude -p` en `stream-json`, ligne de commande retenue
par la sonde 0.4 du plan. Outils intégrés réduits à `Skill` (skills du plugin), liste d'autorisations fermée (`Skill`
et les six outils forever), `dontAsk`, réglages ignorés (`--restricted` : ni hooks du projet ni plugins de
l'utilisateur), seul serveur MCP `forever` (`--strict-mcp-config`, `--mcp-config`), plugin par `--plugin-dir`, dossier
de travail dédié hors du dépôt. La question passe par l'entrée standard, en octets UTF-8, jamais par la ligne de
commande ; aucun shell : un texte tapé en jeu ne devient jamais une commande. Le seul exécutable lancé est `claude` ;
le seul processus que le pont arrête est le sien (et ses enfants, par un objet de tâche Windows), au-delà du délai."""

from __future__ import annotations

import json
import queue
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
    "mcp__forever__forever_route",  # RX1 : feuille de route
)
ALLOWED_TOOLS: tuple[str, ...] = ("Skill", *FOREVER_TOOLS)
# Conversations du pont sans les hooks du plugin (démarrage, contrôle de fin) : le pont publie lui-même l'état des
# données et la provenance (BR8, décision 237 ; mesure du 2026-10-10 : médiane 8,37 s avec, 6,02 s sans).
NO_HOOKS_SETTINGS = json.dumps({"disableAllHooks": True})
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
    # « build » (export), « projected » (chemin du joueur), « closest » (build populaire le plus proche, P06b)
    links: dict[str, str] = field(default_factory=dict)
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list, compare=False)  # outil et arguments (P06b)
    events: list[dict[str, Any]] = field(
        default_factory=list, compare=False, repr=False
    )  # flux lu (contrôle des chiffres)
    # EX1 : liens typés `{kind, label, text}` rangés comme `links` (« build », « closest », « check », « export »)
    exports: dict[str, list[dict[str, str]]] = field(default_factory=dict)


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
    input_stream: bool = False,
) -> list[str]:
    """Liste d'arguments de `claude` (jamais une chaîne) ; la question n'y figure pas. `input_stream` (variante C,
    P06b) : messages lus en JSON sur l'entrée, un processus gardé ouvert entre deux messages."""
    args = [
        claude,
        "-p",
        *(["--input-format", "stream-json"] if input_stream else []),
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
        "--settings",
        NO_HOOKS_SETTINGS,
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


def _projected_link(value: Any) -> str | None:
    """Lien Talents Forever du chemin conseillé depuis le build actuel (`respec.projected.export`)."""
    respec = value.get("respec") if isinstance(value, dict) else None
    projected = respec.get("projected") if isinstance(respec, dict) else None
    export = projected.get("export") if isinstance(projected, dict) else None
    if isinstance(export, dict) and export.get("status") == "ok" and isinstance(export.get("link"), str):
        return str(export["link"])
    return None


def parse_stream(lines: Iterable[str]) -> AgentResult:
    """Résultat d'une conversation lu dans le flux `stream-json` : texte final, session, refus, blocs `provenance`
    des outils forever, lien Talents Forever d'un résultat de `forever_build`."""
    names: dict[str, str] = {}
    provenances: list[dict[str, Any]] = []
    tools: list[str] = []
    calls: list[tuple[str, dict[str, Any]]] = []
    events: list[dict[str, Any]] = []
    link: str | None = None
    links: dict[str, str] = {}
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
        events.append(event)
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
                    args = block.get("input")
                    calls.append((str(block.get("name")), dict(args) if isinstance(args, dict) else {}))
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
                if _find_link(value):
                    links["build"] = str(_find_link(value))
                if _projected_link(value):
                    links["projected"] = str(_projected_link(value))
                closest = value.get("closest") if isinstance(value, dict) else None
                if isinstance(closest, dict) and closest.get("link"):
                    links["closest"] = str(closest["link"])  # build populaire le plus proche (P06b)
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
            links=links,
            calls=calls,
            events=events,
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
        links=links,
        calls=calls,
        events=events,
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


def _spawn(popen: Popen, argv: list[str], cwd: Path, env: Mapping[str, str]) -> Any:
    """Seul lancement de `claude` du module : liste d'arguments, jamais de shell, entrée et sorties en tubes."""
    flags = _CREATE_NO_WINDOW if sys.platform == "win32" else 0
    return popen(
        argv,
        cwd=cwd,
        env=dict(env),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=flags,
    )


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
    started = time.monotonic()
    proc = _spawn(popen, argv, cwd, env)
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


def default_system_prompt() -> str:
    from forever.bridge.prompt import SYSTEM_PROMPT

    return SYSTEM_PROMPT


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


ADDONS_TOOLS: tuple[str, ...] = ("Read", "Glob", "Grep", "Edit", "Write")


def addons_argv(
    *,
    claude: str,
    folder: Path,
    mcp_config: Path,
    system_prompt: str,
    session_id: str | None = None,
    model: str | None = None,
) -> list[str]:
    """Ligne de `claude` de la conversation « addons » (P06b, bloc F, décision 235) : outils de fichiers seulement
    (aucun shell, aucun outil web, aucun serveur MCP : configuration vide), limités au dossier de travail (`folder`, le
    dossier de l'addon) par des règles relatives et `--restricted` ; sonde 0.2 du 2026-10-10 : une écriture, une
    lecture, un Grep et un Glob hors du dossier sont refusés."""
    del folder  # le dossier est le dossier de travail du processus (cwd), les règles lui sont relatives
    args = [
        claude,
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--tools",
        ",".join(ADDONS_TOOLS),
        "--restricted",
        "--strict-mcp-config",
        "--mcp-config",
        str(mcp_config),
        "--allowedTools",
        ",".join(ADDONS_RULES),
        "--permission-mode",
        "dontAsk",
        "--permission-prompts",
        "none",
        "--settings",
        NO_HOOKS_SETTINGS,
        "--append-system-prompt",
        system_prompt,
    ]
    if session_id:
        args += ["--resume", session_id]
    if model:
        args += ["--model", model]
    return args


ADDONS_RULES: tuple[str, ...] = ("Read(./**)", "Edit(./**)", "Write(./**)", "Glob(./**)", "Grep(./**)")


def write_empty_mcp_config(directory: Path) -> Path:
    """Configuration MCP vide de la conversation « addons » (`--strict-mcp-config`)."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "mcp-vide.json"
    path.write_bytes(b'{"mcpServers": {}}\n')
    return path


IDLE_S = 15 * 60.0  # session gardée ouverte arrêtée après ce silence


class PersistentSession:
    """Session `claude` gardée ouverte (variante C de P06b, bloc G, sonde 0.3) : un processus lancé avec
    `--input-format stream-json` ; chaque message est écrit en JSON sur son entrée et lu jusqu'à son événement
    `result`. Relancé pour une nouvelle conversation, après `idle_s` secondes sans message, quand il s'est arrêté ou
    après un délai dépassé (arrêté avec ses enfants) ; relancé avec `--resume` quand la session est connue.
    `argv(resume)` rend la ligne de commande."""

    def __init__(
        self,
        argv: Callable[[str | None], list[str]],
        *,
        cwd: Path | str,
        env: Mapping[str, str],
        popen: Popen = subprocess.Popen,
        clock: Callable[[], float] = time.monotonic,
        idle_s: float = IDLE_S,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        self.argv = argv
        self.cwd = Path(cwd)
        self.env = env
        self.popen = popen
        self.clock = clock
        self.idle_s = idle_s
        self.timeout_s = timeout_s
        self.proc: Any = None
        self.job: _Job | None = None
        self.lines: queue.Queue[tuple[float, str] | None] = queue.Queue()
        self.session_id: str | None = None
        self.last: float | None = None
        self.cost_total = 0.0

    def _start(self, resume: str | None) -> None:
        self.proc = _spawn(self.popen, self.argv(resume), self.cwd, self.env)
        self.job = _Job(self.proc)
        self.lines = queue.Queue()
        self.cost_total = 0.0
        lines, out = self.lines, self.proc.stdout

        def read() -> None:
            for raw in out:
                text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
                lines.put((time.monotonic(), text))
            lines.put(None)

        threading.Thread(target=read, daemon=True).start()

    def _stop(self) -> None:
        proc, self.proc = self.proc, None
        if proc is None:
            return
        try:
            proc.stdin.close()
        except OSError:
            pass
        try:
            proc.kill()
            proc.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass
        if self.job is not None:
            self.job.close()
            self.job = None

    def close(self) -> None:
        self._stop()

    def ask(self, prompt: str, *, new: bool = False) -> AgentResult:
        now = self.clock()
        if new:
            self._stop()
            self.session_id = None
        elif self.proc is not None and (
            self.proc.poll() is not None or (self.last is not None and now - self.last > self.idle_s)
        ):
            self._stop()
        if self.proc is None:
            self._start(None if new else self.session_id)
        message = {"type": "user", "message": {"role": "user", "content": prompt}}
        sent = time.monotonic()
        try:
            self.proc.stdin.write((json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8"))
            self.proc.stdin.flush()
        except OSError as exc:
            self._stop()
            return AgentResult(text="", session_id=None, is_error=True, error=f"session arrêtée : {exc}")
        timed: list[tuple[float, str]] = []
        deadline = sent + self.timeout_s
        while True:
            try:
                item = self.lines.get(timeout=max(0.0, deadline - time.monotonic()))
            except queue.Empty:
                self._stop()
                return AgentResult(text="", session_id=None, is_error=True,
                                   error=f"délai dépassé ({self.timeout_s:g} s)")  # fmt: skip
            if item is None:
                self._stop()
                break
            timed.append(item)
            try:
                if json.loads(item[1]).get("type") == "result":
                    break
            except (ValueError, AttributeError):
                continue
        result = replace(parse_stream([text for _, text in timed]), timings=stream_timings(timed, sent))
        if result.cost_usd is not None:  # coût cumulé sur le processus : celui du seul tour
            turn = round(result.cost_usd - self.cost_total, 7)
            self.cost_total = result.cost_usd
            result = replace(result, cost_usd=turn)
        self.session_id = result.session_id or self.session_id
        self.last = self.clock()
        return result
