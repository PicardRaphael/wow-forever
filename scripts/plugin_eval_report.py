"""Rapport d'un passage de `claude plugin eval` sur plugin/evals/ (T06, décision D10) : seuils de la tranche et chiffres
signalés par le contrôle des chiffres, pour mesurer ses fausses alertes.

    uv run python scripts/plugin_eval_report.py <résultat JSON de claude plugin eval> [--evals plugin/evals]

Lecture locale seulement (résultat JSON et traces gardées par --keep-temp), aucun accès réseau."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from forever.hooks import read_transcript, session_used_forever, unsourced_numbers

# Seuils de réussite de la tranche (paramètres de l'évaluation, décision D10 et précisions de l'utilisateur).
THRESHOLDS: dict[str, float] = {
    "aiguillage": 0.9,
    "outil": 0.9,
    "chiffres": 1.0,
    "certitude": 1.0,
    "provenance": 0.9,
    "je_ne_sais_pas": 1.0,
}
LABELS = {
    "aiguillage": "bonnes décisions d'aiguillage (50 cas)",
    "outil": "outil attendu appelé (cas positifs)",
    "chiffres": "aucun chiffre inventé (cas positifs)",
    "certitude": "certitude affichée (cas positifs)",
    "provenance": "provenance affichée (cas positifs)",
    "je_ne_sais_pas": "« je ne sais pas » hors périmètre",
}
_FRONT = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def load_cases(evals_dir: Path) -> dict[str, dict[str, str]]:
    """Cas de la suite : nom -> polarité (positif, negatif) et catégorie, lus dans les tags de prompt.md."""
    out: dict[str, dict[str, str]] = {}
    for prompt in sorted(evals_dir.glob("*/prompt.md")):
        m = _FRONT.match(prompt.read_text(encoding="utf-8").replace("\r\n", "\n"))
        meta = yaml.safe_load(m.group(1)) if m else {}
        tags = list(meta.get("tags") or [])
        if len(tags) >= 2:
            out[prompt.parent.name] = {"polarity": str(tags[0]), "category": str(tags[1])}
    return out


def _runs(result: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [(c["name"], run) for c in result.get("cases", []) for run in c.get("arms", {}).get("with", [])]


def _passed(run: dict[str, Any], grader: str) -> bool | None:
    for g in run.get("graders", []):
        if g.get("name") == grader:
            return bool(g.get("passed"))
    return None


def metrics(result: dict[str, Any], cases: dict[str, dict[str, str]]) -> dict[str, dict[str, Any]]:
    """Taux de réussite par critère de D10 sur tous les passages du bras « with »."""
    counts = {k: [0, 0] for k in THRESHOLDS}

    def count(key: str, ok: bool | None) -> None:
        counts[key][1] += 1
        counts[key][0] += bool(ok)

    for name, run in _runs(result):
        case = cases.get(name)
        if case is None:
            continue
        if case["polarity"] == "negatif":
            count("aiguillage", _passed(run, "aucun-skill-forever"))
            continue
        count("aiguillage", _passed(run, "skill"))
        for key, grader in (("outil", "outil"), ("chiffres", "chiffres"), ("certitude", "certitude")):
            count(key, _passed(run, grader))
        count("provenance", _passed(run, "provenance"))
        if case["category"] == "hors-perimetre":
            count("je_ne_sais_pas", bool(_passed(run, "je-ne-sais-pas")) and bool(_passed(run, "sans-estimation")))
    return {
        k: {
            "passed": p,
            "total": t,
            "rate": p / t if t else None,
            "threshold": THRESHOLDS[k],
            "ok": t > 0 and p / t >= THRESHOLDS[k],
        }
        for k, (p, t) in counts.items()
    }


def flagged_numbers(result: dict[str, Any], base: Path) -> list[dict[str, Any]]:
    """Chiffres de jeu sans source relevés dans les traces gardées (même règle que le hook Stop) ; chemins relatifs
    résolus depuis `base`."""
    out: list[dict[str, Any]] = []
    for name, run in _runs(result):
        trace = run.get("tracePath")
        if not trace:
            continue
        lines = read_transcript(base / trace)
        if not lines or not session_used_forever(lines):
            continue
        found = unsourced_numbers(lines)
        if found:
            out.append({"case": name, "numbers": found})
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rapport d'un passage de claude plugin eval (seuils de T06).")
    parser.add_argument("result", type=Path, help="résultat JSON de claude plugin eval --json")
    parser.add_argument("--evals", type=Path, default=ROOT / "plugin" / "evals", help="dossier des cas")
    args = parser.parse_args(argv)
    result = json.loads(args.result.read_text(encoding="utf-8"))
    m = metrics(result, load_cases(args.evals))
    print(f"Passage : Claude Code {result.get('claudeVersion', '?')}, coût {result.get('costUsd', '?')} $")
    for key, v in m.items():
        rate = "—" if v["rate"] is None else f"{v['rate']:.0%}"
        verdict = "OK" if v["ok"] else "ÉCHEC"
        print(f"  {verdict:5} {LABELS[key]} : {v['passed']}/{v['total']} ({rate}, seuil {v['threshold']:.0%})")
    flagged = flagged_numbers(result, args.result.parent)
    print(f"Chiffres signalés par le contrôle (à revoir un par un pour les fausses alertes) : {len(flagged)} cas")
    for f in flagged:
        print(f"  {f['case']} : " + ", ".join(f"« {n} »" for n in f["numbers"]))
    return 0 if all(v["ok"] for v in m.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
