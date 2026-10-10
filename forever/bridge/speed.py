"""Mesure des accélérations de la conversation « jeu » (P06b, bloc G, décision 235). Variantes : A (ligne actuelle),
B (réflexion coupée : `MAX_THINKING_TOKENS=0`), C (session `claude` gardée ouverte, `agent.PersistentSession`), D (B et
C). Critères de qualité automatiques, écrits avant la mesure (`quality_failures`) : appels d'outils de la consigne du
bouton (outil et arguments), lien identique à celui de la variante A, provenance quand un outil a été appelé, réponse
de 600 caractères au plus après mise en forme, aucun chiffre de jeu hors des résultats d'outil (contrôle du hook
`check-numbers`), aucune erreur. Règle de décision (`keep`) : médiane plus basse d'au moins 2 s ou 15 % que celle de A,
sans aucun échec de qualité. Banc : `forever bridge bench` (`run_bench`), rapport `tasks/P06b-vitesse.md`."""

from __future__ import annotations

import json
import re
import statistics
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

MAX_REPLY_CHARS = 600
MIN_GAIN_S = 2.0
MIN_GAIN_RATIO = 0.15
_MARKUP = re.compile(r"\*\*|^## |^- ", re.MULTILINE)


@dataclass(frozen=True)
class Variant:
    name: str
    thinking_off: bool
    persistent: bool
    label: str = ""


VARIANTS: dict[str, Variant] = {
    "A": Variant("A", False, False, "ligne actuelle"),
    "B": Variant("B", True, False, "réflexion coupée (MAX_THINKING_TOKENS=0)"),
    "C": Variant("C", False, True, "session gardée ouverte"),
    "D": Variant("D", True, True, "réflexion coupée et session gardée ouverte"),
}


def variant_env(env: Mapping[str, str], variant: Variant) -> dict[str, str]:
    """Environnement de `claude` pour la variante : `MAX_THINKING_TOKENS=0` pour B et D, jamais pour A et C."""
    out = {k: v for k, v in env.items() if k != "MAX_THINKING_TOKENS"}
    if variant.thinking_off:
        out["MAX_THINKING_TOKENS"] = "0"
    return out


def _plain_length(text: str) -> int:
    from forever.bridge.format import normalize_reply

    return len(_MARKUP.sub("", normalize_reply(text)))


def quality_failures(
    result: Any, plan: Any, baseline_link: str | None, *, earlier: Sequence[Mapping[str, Any]] = ()
) -> list[str]:
    """Échecs de qualité d'une réponse (liste vide : réponse acceptable). `earlier` : événements des tours précédents
    de la même conversation, dont les résultats d'outils sourcent aussi un chiffre (décision 237)."""
    failures: list[str] = []
    if getattr(result, "is_error", False):
        return ["erreur"]
    calls = [(str(n).removeprefix("mcp__forever__"), dict(a)) for n, a in getattr(result, "calls", []) or []]
    forever_calls = [c for c in calls if not c[0].startswith("Skill")]
    if plan is not None:
        wanted = [(c.tool, dict(c.args)) for c in plan.calls]
        if any(c not in wanted for c in forever_calls) or any(w not in forever_calls for w in wanted):
            failures.append("appel hors consigne")
        link = (getattr(result, "links", {}) or {}).get(plan.link) if plan.link else getattr(result, "link", None)
    else:
        link = getattr(result, "link", None)
    if link != baseline_link:
        failures.append("lien changé")
    if forever_calls and not getattr(result, "provenances", None):
        failures.append("provenance absente")
    if _plain_length(getattr(result, "text", "") or "") > MAX_REPLY_CHARS:
        failures.append("réponse trop longue")
    if unsourced(result, earlier):
        failures.append("chiffre hors des résultats d'outil")
    from forever.bridge.jargon import internal_jargon

    if internal_jargon(getattr(result, "text", "") or ""):
        failures.append("jargon interne")
    return failures


def unsourced(result: Any, earlier: Sequence[Mapping[str, Any]] = ()) -> list[str]:
    """Chiffres de jeu de la réponse absents des résultats des outils de la conversation, ce tour et les précédents
    (même règle que le hook `check-numbers` du plugin)."""
    from forever.hooks import unsourced_numbers

    events = [*earlier, *(getattr(result, "events", None) or [])]
    return unsourced_numbers(events, getattr(result, "text", "") or "")


def keep(baseline: Sequence[float], candidate: Sequence[float], failures: int) -> bool:
    """Variante gardée : médiane plus basse que celle de A d'au moins 2 s ou 15 %, sans aucun échec de qualité."""
    if failures or not baseline or not candidate:
        return False
    base, cand = statistics.median(baseline), statistics.median(candidate)
    gain = base - cand
    return gain >= MIN_GAIN_S or (base > 0 and gain / base >= MIN_GAIN_RATIO - 1e-9)


# --- Banc --------------------------------------------------------------------------------------------------------


@dataclass
class Measure:
    variant: str
    round: int
    question: str
    seconds: float
    timings: dict[str, Any] = field(default_factory=dict)
    cost_usd: float | None = None
    text: str = ""
    link: str | None = None
    failures: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)


Ask = Callable[[str, bool], Any]  # (message, nouvelle conversation) → AgentResult


def run_bench(
    questions: Sequence[tuple[str, str, Any]],
    runners: Mapping[str, Callable[[], Ask]],
    *,
    rounds: int = 2,
    clock: Callable[[], float] = time.monotonic,
    progress: Callable[[str], None] | None = None,
) -> list[Measure]:
    """Chaque variante, `rounds` passages, chaque question (clé, message, consigne) : une conversation par passage,
    comme un joueur qui pose ses questions à la suite (A et B la reprennent par `--resume`, C et D gardent leur
    processus). Le lien de référence de chaque question est celui de la variante A du même passage."""
    out: list[Measure] = []
    baseline: dict[tuple[int, str], str | None] = {}
    for rnd in range(1, rounds + 1):
        for name, factory in runners.items():
            ask = factory()
            history: list[Mapping[str, Any]] = []  # événements des tours précédents de la conversation du passage
            try:
                for index, (key, message, plan) in enumerate(questions):
                    started = clock()
                    result = ask(message, index == 0)
                    seconds = round(clock() - started, 2)
                    link = (result.links or {}).get(plan.link) if plan is not None and plan.link else result.link
                    if name == "A":
                        baseline[(rnd, key)] = link
                    failures = quality_failures(result, plan, baseline.get((rnd, key), link), earlier=history)
                    history += list(getattr(result, "events", None) or [])
                    out.append(Measure(name, rnd, key, seconds, dict(result.timings or {}), result.cost_usd,
                                       result.text, link, failures, list(result.tools)))  # fmt: skip
                    if progress:
                        progress(
                            f"{name} passage {rnd} {key} : {seconds} s{' · ' + ', '.join(failures) if failures else ''}"
                        )
            finally:
                close = getattr(ask, "close", None)
                if callable(close):
                    close()
    return out


BENCH_QUESTIONS: tuple[tuple[str, str, str, str | None], ...] = (
    # (clé, contexte réel de tests/fixtures/bridge/contexts, question, bouton)
    ("talents", "mage19", "Quel est mon prochain talent, avec le lien Talents Forever ?", "talents"),
    ("suite-faute", "mage19", "Pour toi le projet step c'est quoi ?", None),  # sonde H : suite à faute de frappe
    ("leveling", "mage19", "Quel est mon prochain objectif de leveling ?", "leveling"),
    ("pvp", "mage19_cible_chaman21_tauren", "Fiche de la classe de ma cible", "pvp"),
    ("libre-talents", "mage19", "Quelles est les talent opti pour mage givre level 20", None),  # journal, 2026-10-09
    ("libre-rotation", "mage19", "c'est quoi la rotation pour toi", None),  # journal, 2026-10-09
    ("libre-liens", "mage19_sonde_g_liens", "[Sharp Canine][Mystic's Slippers]", None),  # sonde G, 2026-10-10
)


def bench_messages(data: Any, contexts_dir: Any) -> list[tuple[str, str, Any]]:
    """Les six messages du banc, construits comme le pont les construit (contexte relié, consigne du bouton)."""
    from forever.bridge.context import resolve
    from forever.bridge.plans import button_plan, prepare_record
    from forever.bridge.prompt import message_text
    from forever.bridge.record import Record

    out = []
    for key, name, question, button in BENCH_QUESTIONS:
        text = (contexts_dir / f"{name}.txt").read_text(encoding="utf-8")
        context = dict(line.split("=", 1) for line in text.split("\n") if "=" in line)
        record = Record("banc", 0, frozenset({f"b={button}"} if button else ()), context, question)
        prepared = prepare_record(data, record)
        plan = button_plan(button, resolve(data, context), data.level_cap) if button else None
        out.append((key, message_text(record, talents=prepared.notes, guide=prepared.guide), plan))
    return out


def own_failures(measures: Sequence[Measure]) -> dict[int, list[str]]:
    """Échecs propres à chaque mesure : ceux que la variante A n'a pas sur la même question du même passage. Un échec
    déjà présent dans A est un défaut de la ligne actuelle, rapporté à part, pas une régression de la variante."""
    base = {(m.round, m.question): set(m.failures) for m in measures if m.variant == "A"}
    return {
        id(m): ([] if m.variant == "A" else [f for f in m.failures if f not in base.get((m.round, m.question), set())])
        for m in measures
    }


def summary(measures: Sequence[Measure]) -> dict[str, Any]:
    """Par variante : médiane, moyenne, échecs propres (et échecs déjà présents dans A), coût, et décision `keep`."""
    own = own_failures(measures)
    by: dict[str, list[Measure]] = {}
    for m in measures:
        by.setdefault(m.variant, []).append(m)
    base = [m.seconds for m in by.get("A", [])]
    out: dict[str, Any] = {}
    for name, items in by.items():
        seconds = [m.seconds for m in items]
        failures = sum(len(own[id(m)]) for m in items)
        out[name] = {
            "median_s": round(statistics.median(seconds), 2),
            "mean_s": round(statistics.mean(seconds), 2),
            "failures": failures,
            "shared_failures": sum(len(m.failures) for m in items) - failures,
            "cost_usd": round(sum(m.cost_usd or 0 for m in items), 4),
            "keep": name != "A" and keep(base, seconds, failures),
        }
    return out


def report_markdown(measures: Sequence[Measure], meta: Mapping[str, Any]) -> str:
    """Rapport côte à côte : décision par variante, durées par question, réponses de chaque variante."""
    s = summary(measures)
    lines = [
        "# P06b — mesure des accélérations de la conversation « jeu »",
        "",
        (
            f"Mesuré le {meta.get('date')} ({meta.get('model')}, {meta.get('rounds')} passages, "
            f"{len({m.question for m in measures})} questions). Règle : médiane plus basse que A d'au moins 2 s ou "
            "15 %, sans échec de qualité (`forever/bridge/speed.py`)."
        ),
        "",
        "| Variante | Médiane (s) | Moyenne (s) | Échecs propres | Échecs aussi dans A | Coût ($) | Gardée |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name in sorted(s):
        v = s[name]
        label = VARIANTS[name].label if name in VARIANTS else name
        kept = "référence" if name == "A" else ("oui" if v["keep"] else "non")
        lines.append(
            f"| {name} ({label}) | {v['median_s']} | {v['mean_s']} | {v['failures']} | {v['shared_failures']} | {v['cost_usd']} | {kept} |"
        )
    lines += ["", "## Durées par question (s)", "", "| Question | " + " | ".join(sorted(s)) + " |",
              "| --- |" + " --- |" * len(s)]  # fmt: skip
    for key in dict.fromkeys(m.question for m in measures):
        cells = []
        for name in sorted(s):
            vals = [
                f"{m.seconds}" + ("*" if m.failures else "")
                for m in measures
                if m.question == key and m.variant == name
            ]
            cells.append(" / ".join(vals))
        lines.append(f"| {key} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "\\* : réponse avec un échec de qualité (détail plus bas).",
        "",
        "## Réponses côte à côte (passage 1)",
        "",
    ]
    for key in dict.fromkeys(m.question for m in measures):
        lines.append(f"### {key}")
        for m in measures:
            if m.question == key and m.round == 1:
                lines.append(f"- **{m.variant}** ({m.seconds} s{'; ' + ', '.join(m.failures) if m.failures else ''}) :")
                lines += [f"  > {line}" for line in (m.text or "(vide)").splitlines() if line.strip()]
        lines.append("")
    lines += ["## Mesures brutes", "", "```json",
              json.dumps([m.__dict__ for m in measures], ensure_ascii=False, indent=1), "```", ""]  # fmt: skip
    return "\n".join(lines)
