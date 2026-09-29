"""Fixture de comparaison avec les builds de la communauté (T05, bloc J) : lit le bloc JSON de
docs/research/community-builds-mage.md, calcule nos builds de référence (optimiseur, préréglage rapide) pour chaque
couple contexte-niveau, l'écart de chaque build (analytique et Monte Carlo apparié) et son explication, puis écrit
tests/fixtures/community/mage_builds.json (LF) et le tableau « Comparaison avec nos builds » du document de recherche.

Hors ligne, déterministe (graine fixe). Aucune valeur communautaire n'entre dans forever/data/.

Usage : uv run python scripts/build_community_fixture.py"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from forever.config import default_deps
from forever.engine.blind_spots import BlindSpotRule
from forever.engine.talents import check_build
from forever.gamedata import load_game_data
from forever.optimize.decide import paired_gap
from forever.optimize.endgame import context_analytic, context_mc, optimize_context
from forever.optimize.leveling import best_choice, optimize_leveling
from forever.registry import blind_spot_rules, load
from forever.sim.community import SOURCE_CONTEXTS, community_gap
from forever.sim.leveling_mc import mc_stats

RESEARCH = ROOT / "docs" / "research" / "community-builds-mage.md"
FIXTURE = ROOT / "tests" / "fixtures" / "community" / "mage_builds.json"
SECTION = "## Comparaison avec nos builds (T05, bloc J)"
PRESET = "rapide"
MC_N = 100  # combats par Monte Carlo de la comparaison (paramètre de méthode)
SEED = 12345
SIMULATORS = ("wowsims", "elliotwood", "gunba", "mythicsim", "simulat")  # préréglages de simulateur


def research_builds() -> list[dict[str, Any]]:
    text = RESEARCH.read_text(encoding="utf-8")
    m = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
    assert m, "bloc JSON absent du document de recherche"
    return list(json.loads(m.group(1)))


def reference(gd: Any, context: str, level: int) -> dict[str, int]:
    p = gd.build.presets[PRESET]
    ctx = SOURCE_CONTEXTS[context]
    if ctx == "leveling":
        path = optimize_leveling(
            gd,
            "Orc",
            gd.constants.talents.first_level,
            level,
            beam=p.beam,
            depth=p.depth,
            shortlist=p.shortlist,
            mc_n=p.mc_n,
        )
        return dict(path.points)
    cands = optimize_context(gd, ctx, level, "Orc", shortlist=p.shortlist, mc_n=p.mc_n, depth=p.depth)
    return dict(cands[0].points)


def mc_gap(gd: Any, context: str, level: int, theirs: dict[str, int], ours: dict[str, int]) -> dict[str, Any] | None:
    ctx = SOURCE_CONTEXTS[context]
    if ctx.startswith("pvp"):
        return None
    if ctx == "leveling":

        def stats(pts: dict[str, int]) -> Any:
            _, c = best_choice(gd, level, pts, "Orc", full=True)
            return mc_stats(gd, level, pts, "Orc", c.rotation, MC_N, SEED, **c.options())
    else:

        def stats(pts: dict[str, int]) -> Any:
            _, choices = context_analytic(gd, ctx, level, pts, "Orc")
            return context_mc(gd, ctx, level, pts, choices, "Orc", MC_N, SEED)

    a, b = stats(theirs), stats(ours)
    g = paired_gap(a, b, gd.build.confidence)
    sign = -1 if ctx == "leveling" else 1  # orienté : positif, leur build fait mieux
    return {"mc_rel": sign * g.mean / b.mean, "mc_significant": g.significant}


def explain(gd: Any, b: dict[str, Any], ours: dict[str, int], rules: list[BlindSpotRule], thr: float) -> dict[str, Any]:
    if not b["legal"]:
        return {
            "kind": "source_douteuse",
            "registry": None,
            "motif": f"build illégal : {b.get('legal_notes') or 'règle niveau − 9'}",
        }
    rel = b["gap"]["analytic_rel"]
    if abs(rel) <= thr:
        motif = f"écart {rel:+.1%} à l'analytique, sous le seuil de concordance".replace(".", ",")
        return {"kind": "concorde", "registry": None, "motif": motif}
    if rel > thr:
        ctx = SOURCE_CONTEXTS[b["context"]]
        mc, sig = b["gap"].get("mc_rel"), b["gap"].get("mc_significant")
        if mc is not None and sig and mc < 0:
            motif = (
                f"l'analytique donne {rel:+.1%} mais le Monte Carlo {mc:+.1%} : notre build fait mieux au Monte Carlo "
                "(approximation de l'analytique)"
            ).replace(".", ",")
            return {"kind": "mecanique_non_modelisee", "registry": "H5" if ctx != "leveling" else "I6", "motif": motif}
        if ctx == "leveling":
            motif = (
                f"leur build fait mieux de {rel:+.1%} au seul niveau {b['level']} ; le nôtre suit le meilleur chemin de "
                f"10 à {b['level']} (heures cumulées, préréglage {PRESET}) : une respec peut valoir la peine "
                "(forever build leveling --current)"
            ).replace(".", ",")
        else:
            motif = (
                f"leur build fait mieux de {rel:+.1%} à l'analytique : optimum local de notre recherche (départs "
                "multiples, un point déplacé à la fois)"
            ).replace(".", ",")
        return {"kind": "mecanique_non_modelisee", "registry": "I5", "motif": motif}
    return _worse(gd, b, ours, rules)


def _worse(gd: Any, b: dict[str, Any], ours: dict[str, int], rules: list[BlindSpotRule]) -> dict[str, Any]:
    extra = {k: v - ours.get(k, 0) for k, v in b["points"].items() if v > ours.get(k, 0)}
    best: tuple[int, BlindSpotRule] | None = None
    ctx = SOURCE_CONTEXTS[b["context"]]
    for r in rules:
        if ctx not in r.contexts or not r.talents:
            continue
        n = sum(extra.get(k, 0) for k in r.talents)
        if n and (best is None or n > best[0]):
            best = (n, r)
    if best is not None:
        n, r = best
        names = ", ".join(k for k in r.talents if extra.get(k))
        return {
            "kind": "mecanique_non_modelisee",
            "registry": r.id,
            "motif": f"{n} point(s) sur des talents dont l'effet n'est pas modélisé ({names}) : {r.description}",
        }
    src = (b["source_url"] + " " + (b.get("author") or "")).lower()
    if ctx in ("dungeon", "raid") and any(s in src for s in SIMULATORS):
        return {
            "kind": "mecanique_non_modelisee",
            "registry": "F1",
            "motif": "préréglage de simulateur calculé avec un équipement de raid ; notre build suit la fiche de base par niveau",
        }
    if b["level"] > gd.build.beta_level_cap:
        return {
            "kind": "source_douteuse",
            "registry": None,
            "motif": f"théorie au-delà du plafond de la bêta (niveau {gd.build.beta_level_cap}), sans mesure en jeu",
        }
    flags = b.get("reliability_flags") or []
    return {
        "kind": "source_douteuse",
        "registry": None,
        "motif": "choix non chiffré par la source" + (f" ({flags[0]})" if flags else ""),
    }


def main() -> int:
    deps = default_deps()
    gd = load_game_data(deps)
    rules = blind_spot_rules(load(deps.registry_path))
    thr = gd.build.concord_threshold
    builds = research_builds()
    pairs = sorted({(b["context"], b["level"]) for b in builds})
    refs = {pair: reference(gd, *pair) for pair in pairs}
    out = []
    for b in builds:
        pts = b["points"]
        legal = all(k in gd.talents for k in pts) and check_build(gd, pts, b["level"]) == []
        assert legal == b["legal"], (b["id"], legal, b["legal"])
        row = dict(b)
        if legal:
            ours = refs[(b["context"], b["level"])]
            row["gap"] = {"analytic_rel": community_gap(gd, b["context"], b["level"], pts, ours)}
            mc = mc_gap(gd, b["context"], b["level"], pts, ours)
            row["gap"].update(mc or {"mc_rel": None, "mc_significant": None})
        else:
            row["gap"] = None
        row["explanation"] = explain(gd, row, refs.get((b["context"], b["level"]), {}), rules, thr)
        out.append(row)
    doc = {
        "source": "docs/research/community-builds-mage.md (bloc JSON, recherche du 2026-09-28)",
        "generated_by": "scripts/build_community_fixture.py",
        "game_version": gd.game_version,
        "concord_threshold": thr,
        "preset": PRESET,
        "mc_n": MC_N,
        "seed": SEED,
        "references": [{"context": c, "level": lv, "points": refs[(c, lv)], "preset": PRESET} for c, lv in pairs],
        "builds": out,
    }
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    write_section(gd, doc)
    print(f"{len(out)} builds, {len(pairs)} références")
    return 0


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x:+.1%}".replace(".", ",")


def write_section(gd: Any, doc: dict[str, Any]) -> None:
    lines = [
        SECTION,
        "",
        (
            f"Calculée le 2026-09-29 par `scripts/build_community_fixture.py` (fixture `tests/fixtures/community/mage_builds.json`) : "
            f"pour chaque build, écart relatif de sa métrique avec notre build de référence du même contexte et du même niveau "
            f"(optimiseur, préréglage {doc['preset']}, fiche de base, race Orc), à l'analytique et au Monte Carlo apparié "
            f"(n = {doc['mc_n']}, graine {doc['seed']}) ; positif : le build de la communauté fait mieux dans notre modèle. "
            f"Seuil de concordance : {doc['concord_threshold']:.0%} (`build.concord_threshold`). Contexte `pvp` des sources : profil "
            "des champs de bataille. Aucune source n'est prise pour vérité ; aucune valeur communautaire n'entre dans `forever/data/`."
        ),
        "",
        "Nos builds de référence :",
        "",
    ]
    for r in doc["references"]:
        pts = ", ".join(f"{k} {v}" for k, v in r["points"].items())
        lines.append(f"- {r['context']} niveau {r['level']} : {pts}")
    lines += [
        "",
        "| Id | Source | Date | Contexte | Niveau | Écart analytique | Écart Monte Carlo | Explication |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for b in doc["builds"]:
        g = b["gap"] or {}
        mc = _pct(g.get("mc_rel")) + (" (s.)" if g.get("mc_significant") else "") if g else "—"
        e = b["explanation"]
        kind = {
            "concorde": "concorde",
            "mecanique_non_modelisee": f"mécanique non modélisée ({e['registry']})",
            "source_douteuse": "source douteuse",
        }[e["kind"]]
        lines.append(
            f"| {b['id']} | [{b['author']}]({b['source_url']}) | {b['date']} | {b['context']} | {b['level']} | "
            f"{_pct(g.get('analytic_rel')) if g else '—'} | {mc} | {kind} : {e['motif'].replace('|', '/')} |"
        )
    text = RESEARCH.read_text(encoding="utf-8")
    if SECTION in text:
        text = text[: text.index(SECTION)].rstrip("\n") + "\n"
    RESEARCH.write_bytes((text.rstrip("\n") + "\n\n" + "\n".join(lines) + "\n").encode("utf-8"))


if __name__ == "__main__":
    sys.exit(main())
