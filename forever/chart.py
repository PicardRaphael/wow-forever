"""Graphique de leveling (PNG) : par niveau, temps par monstre (Monte Carlo total et combat, analytique total) et
XP par heure ; le marqueur de chaque niveau indique la certitude des PV du monstre. Un niveau où le build est
illégal (ou le sort principal non appris) est omis et cité.

Rendu déterministe : moteur Agg sans état global (pas de pyplot), taille et résolution fixes, métadonnées PNG sans
version du logiciel. Aucun calcul de jeu ici : les simulateurs de `forever/sim/` fournissent les valeurs."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypedDict

from forever.engine.model import GameData, Points
from forever.engine.monsters import mob_hp
from forever.engine.talents import check_build
from forever.sim.leveling_analytic import kill_analytic
from forever.sim.leveling_mc import mc, options_with_defaults

# Mise en page (paramètres d'affichage, pas des chiffres de jeu).
FIGSIZE_IN = (9.0, 5.0)
DPI = 100
MARKERS = {"certain": "o", "probable": "s", "suppose": "x"}


class ChartResult(TypedDict):
    path: str
    levels: list[dict[str, Any]]
    omitted: list[dict[str, Any]]


def _points(
    gd: GameData,
    levels: Iterable[int],
    pts: Points,
    race: str,
    rotation: str,
    n: int,
    seed: int,
    options: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    o = options_with_defaults(gd, rotation, options)
    points: list[dict[str, Any]] = []
    omitted: list[dict[str, Any]] = []
    for level in levels:
        errors = check_build(gd, pts, level)
        if errors:
            omitted.append({"level": level, "reason": "build illégal : " + " ; ".join(errors)})
            continue
        try:
            hp = mob_hp(gd, level + o["level_diff"], o["mob_source"])
            m = mc(gd, level, pts, race, rotation, n, seed, **options)
            a = kill_analytic(gd, level, pts, race, rotation, **options)
        except ValueError as exc:
            omitted.append({"level": level, "reason": str(exc)})
            continue
        points.append(
            {
                "level": level,
                "mc_total": m["total"],
                "mc_combat": m["combat"],
                "analytic_total": a["total"],
                "xp_h": m["xp_h"],
                "mob_hp": hp.value,
                "mob_hp_certainty": hp.certainty,
            }
        )
    return points, omitted


def _draw(points: list[dict[str, Any]], rotation: str, out: Path) -> None:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    fig = Figure(figsize=FIGSIZE_IN, dpi=DPI)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot()
    xp = ax.twinx()
    x = [p["level"] for p in points]
    ax.plot(x, [p["mc_total"] for p in points], color="tab:blue", label="Monte Carlo : total (s)")
    ax.plot(x, [p["mc_combat"] for p in points], color="tab:cyan", label="Monte Carlo : combat (s)")
    ax.plot(
        x, [p["analytic_total"] for p in points], color="tab:orange", linestyle="--", label="analytique : total (s)"
    )
    xp.plot(x, [p["xp_h"] for p in points], color="tab:green", label="XP par heure")
    for certainty, marker in MARKERS.items():
        sel = [p for p in points if p["mob_hp_certainty"] == certainty]
        if sel:
            ax.scatter(
                [p["level"] for p in sel],
                [p["mc_total"] for p in sel],
                marker=marker,
                color="tab:blue",
                label=f"PV du monstre : {certainty}",
            )
    ax.set_xlabel("niveau du personnage")
    ax.set_ylabel("temps par monstre (s)")
    xp.set_ylabel("XP par heure")
    ax.set_title(f"Leveling du Mage ({rotation})")
    handles = ax.get_legend_handles_labels()
    extra = xp.get_legend_handles_labels()
    ax.legend(handles[0] + extra[0], handles[1] + extra[1], loc="upper left", fontsize="small")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, format="png", metadata={"Software": None})


def leveling_chart(
    gd: GameData,
    levels: Iterable[int],
    pts: Points,
    *,
    race: str = "Orc",
    rotation: str = "frost",
    n: int = 300,
    seed: int = 12345,
    options: dict[str, Any] | None = None,
    out: Path,
) -> ChartResult:
    """Simule chaque niveau (Monte Carlo à graine fixe, analytique) et écrit le PNG `out`."""
    points, omitted = _points(gd, levels, pts, race, rotation, n, seed, dict(options or {}))
    out.parent.mkdir(parents=True, exist_ok=True)
    _draw(points, rotation, out)
    return {"path": str(out), "levels": points, "omitted": omitted}
