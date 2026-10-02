"""Rejeu des builds de fin de T05 (T06b, décision D9) : cinq contextes × trois niveaux, préréglage complet.

    uv run python scripts/replay_builds.py run <étiquette> [--only contexte-niveau …] [--ratios seed:<nom>,…]
    uv run python scripts/replay_builds.py table <étiquette>
    uv run python scripts/replay_builds.py compare <avant> <après>

`run` écrit un JSON par cas dans `<cache>/builds/<étiquette>/` (rapport complet de `build_report`, durée du calcul)
et le tableau `table.md` ; `compare` liste les recommandations changées entre deux passages (talents, ordre, choix,
alternative, verdicts de sensibilité et de stabilité). Tout calcul passe par `forever.build.build_report`."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from forever.build import build_report
from forever.config import default_deps
from forever.errors import InvalidArgumentError
from forever.gamedata import ABLATABLE, ablated

CONTEXTS = ("leveling", "dungeon", "raid", "pvp-bg", "pvp-world")
LEVELS = (20, 40, 60)
# Leveling joué aussi au plafond de la bêta (30, observé en jeu le 2026-10-01, installation de 1.60.1.70170).
LEVELING_LEVELS = (20, 30, 40, 60)
SEED = 12345
RACE = "Orc"
PRESET = "complet"


def _dir(label: str) -> Path:
    return default_deps().cache_dir / "builds" / label


def _num(x: float | None) -> str:
    return "—" if x is None else f"{x:.2f}".replace(".", ",")


def _advantage(rep: dict[str, Any]) -> tuple[float, float, float] | None:
    """Écart orienté vers le build (positif : le build fait mieux) et son intervalle."""
    gap = rep["alternative"]["gap"]
    if gap is None:
        return None
    sign = 1 if rep["metric"]["higher_is_better"] else -1
    low, high = sorted((sign * gap["low"], sign * gap["high"]))
    return sign * gap["mean"], low, high


def _split(rep: dict[str, Any]) -> str:
    return "/".join(str(sum(t.values())) for t in rep["talents_by_tree"].values())


def _row(case: dict[str, Any]) -> str:
    rep = case["report"]
    adv = _advantage(rep)
    alt = rep["alternative"]
    gap = "—" if adv is None else f"{_num(adv[0])} [{_num(adv[1])} ; {_num(adv[2])}]"
    if adv is not None and not alt["gap"]["significant"]:
        gap += " (égalité)"
    stab = rep["stability"]
    winners = stab["winners"]
    stable = f"stable ({winners[0]})" if stab["stable"] and winners else "instable"
    if not stab["stable"]:
        stable += f" ({winners.count('build')}/{len(winners)} build)"
    flips = [r["assumption"] for r in rep["sensitivity"] if not r["holds"]]
    retained = f"{alt['better']} ({alt['decided_by']})" if alt["better"] else "—"
    cells = [
        rep["context"],
        str(rep["level"]),
        _split(rep),
        _num(rep["metric"]["monte_carlo"]),
        _num(rep["metric"]["analytic"]),
        gap,
        retained,
        stable,
        ", ".join(flips) or "tient",
        f"{case['duration_s']:.0f} s",
    ]
    return "| " + " | ".join(cells) + " |"


HEADER = (
    "| Contexte | Niveau | Arcanes/Feu/Givre | Monte Carlo | Analytique | Avantage sur l'alternative | Retenu "
    "| Stabilité | Sensibilité | Calcul |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
)


def _builds_root() -> Path:
    """Dossier qui contient les passages (`Path / ""` ne descend pas : on passe par un nom quelconque)."""
    return _dir("x").parent


def _available() -> list[str]:
    """Passages présents dans le cache, par ordre alphabétique."""
    root = _builds_root()
    if not root.is_dir():
        return []
    return sorted(d.name for d in root.iterdir() if d.is_dir() and any(d.glob("*.json")))


def _require(*labels: str) -> None:
    """Refuse une étiquette absente ou vide.

    Sans ce contrôle, `compare` lisait un dictionnaire vide et concluait « aucune recommandation changée » : une
    comparaison contre rien passait pour une comparaison réussie (constat du 2026-09-30, T08a)."""
    missing = [label for label in labels if not any(_dir(label).glob("*.json"))]
    if not missing:
        return
    found = _available()
    known = ", ".join(found) if found else "aucun"
    raise SystemExit(
        f"Passage introuvable dans le cache : {', '.join(missing)}.\n"
        f"Cherché dans {_builds_root()} ; passages disponibles : {known}.\n"
        f"Produire le passage manquant avec : uv run python scripts/replay_builds.py run {missing[0]}"
    )


def _load(label: str) -> dict[str, dict[str, Any]]:
    out = {}
    for path in sorted(_dir(label).glob("*.json")):
        out[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return out


def _cases() -> list[tuple[str, int]]:
    return [(c, lv) for c in CONTEXTS for lv in (LEVELING_LEVELS if c == "leveling" else LEVELS)]


def table(label: str) -> str:
    _require(label)
    cases = _load(label)
    rows = [_row(cases[f"{c}-{lv}"]) for c, lv in _cases() if f"{c}-{lv}" in cases]
    first = next(iter(cases.values()), None)
    prov = first["report"]["provenance"] if first else {}
    head = (
        f"Passage `{label}` : graine {SEED}, race {RACE}, préréglage {PRESET}, données {prov.get('game_version')} "
        f"(empreinte {prov.get('data_sha')}, révision {prov.get('data_revision', 1)})."
    )
    return "\n".join([head, "", HEADER, *rows]) + "\n"


def parse_ratios(value: str) -> set[str]:
    """« seed:<nom>[,<nom>] » -> valeurs du client remises à leur estimation (ablation, T08b, bloc I)."""
    kind, _, names = value.partition(":")
    chosen = {n.strip() for n in names.split(",") if n.strip()}
    if kind != "seed" or not chosen:
        raise InvalidArgumentError(f"--ratios mal formé : {value!r}.", "écrire --ratios seed:<nom>[,<nom>]")
    unknown = sorted(chosen - set(ABLATABLE))
    if unknown:
        raise InvalidArgumentError(f"Valeur inconnue : {', '.join(unknown)}.", f"choisir parmi {', '.join(ABLATABLE)}")
    return chosen


def run(label: str, only: list[str] | None, ratios: set[str] | None = None) -> None:
    out = _dir(label)
    out.mkdir(parents=True, exist_ok=True)
    deps = default_deps()
    for context, level in _cases():
        name = f"{context}-{level}"
        if only and name not in only:
            continue
        start = time.perf_counter()
        with ablated(ratios or set()):
            rep = build_report(deps, context, level, race=RACE, preset=PRESET, seed=SEED)
        case = {"report": rep, "duration_s": time.perf_counter() - start, "ablated": sorted(ratios or ())}
        (out / f"{name}.json").write_bytes((json.dumps(case, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
        print(f"{name} : {case['duration_s']:.0f} s", flush=True)
    (out / "table.md").write_bytes(table(label).encode("utf-8"))
    print(f"Écrit : {out}")


def _order(rep: dict[str, Any]) -> list[str]:
    return [f"{s['level']}:{s['talent']}" for s in rep["order"]]


def compare(before: str, after: str) -> str:
    _require(before, after)
    a, b = _load(before), _load(after)
    lines = [f"Changements de `{before}` à `{after}` :", ""]
    for context, level in _cases():
        name = f"{context}-{level}"
        if name not in a or name not in b:
            continue
        ra, rb = a[name]["report"], b[name]["report"]
        changes = []
        if ra["talents"] != rb["talents"]:
            keys = sorted(set(ra["talents"]) | set(rb["talents"]))
            diff = [
                f"{k} {ra['talents'].get(k, 0)}→{rb['talents'].get(k, 0)}"
                for k in keys
                if ra["talents"].get(k, 0) != rb["talents"].get(k, 0)
            ]
            changes.append("talents : " + ", ".join(diff))
        if _order(ra) != _order(rb):
            changes.append("ordre des talents changé")
        if ra["choices"] != rb["choices"]:
            changes.append(f"choix : {ra['choices']} → {rb['choices']}")
        aa, ab = ra["alternative"], rb["alternative"]
        if aa["talents"] != ab["talents"]:
            changes.append(f"alternative : {aa['diff']} → {ab['diff']}")
        if (aa["better"], aa["decided_by"]) != (ab["better"], ab["decided_by"]):
            changes.append(f"retenu : {aa['better']} ({aa['decided_by']}) → {ab['better']} ({ab['decided_by']})")
        if ra["stability"]["stable"] != rb["stability"]["stable"]:
            changes.append(f"stabilité : {ra['stability']['winners']} → {rb['stability']['winners']}")
        fa = {r["assumption"] for r in ra["sensitivity"] if not r["holds"]}
        fb = {r["assumption"] for r in rb["sensitivity"] if not r["holds"]}
        if fa != fb:
            changes.append(f"sensibilité : {sorted(fa) or 'tient'} → {sorted(fb) or 'tient'}")
        if changes:
            lines.append(f"- **{context} {level}** : " + " ; ".join(changes))
    if len(lines) == 2:
        lines.append("- aucune recommandation changée")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Rejeu des builds de T05")
    sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("label")
    r.add_argument("--only", nargs="*")
    r.add_argument("--ratios", help="ablation : seed:<nom>[,<nom>] (valeurs du client remises à leur estimation)")
    t = sub.add_parser("table")
    t.add_argument("label")
    c = sub.add_parser("compare")
    c.add_argument("before")
    c.add_argument("after")
    args = parser.parse_args(argv)
    if args.cmd == "run":
        run(args.label, args.only, parse_ratios(args.ratios) if args.ratios else None)
    elif args.cmd == "table":
        sys.stdout.write(table(args.label))
    else:
        sys.stdout.write(compare(args.before, args.after))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
