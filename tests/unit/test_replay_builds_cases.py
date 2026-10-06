"""Rejeu des builds : cas joués (installation de 1.60.1.70170, 2026-10-02).

Le plafond de la bêta passe à 30 (observé en jeu par l'utilisateur le 2026-10-01) : le rejeu ajoute le leveling au
niveau 30, en plus des trois niveaux de T05 pour chaque contexte. Aucun calcul de build ici."""

import importlib.util

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "replay_builds.py"


def replay_module():
    spec = importlib.util.spec_from_file_location("replay_builds", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_leveling_is_replayed_at_the_beta_cap_too():
    cases = replay_module()._cases()
    assert ("leveling", 30) in cases
    assert [lv for c, lv in cases if c == "leveling"] == [20, 30, 40, 60]


def test_other_contexts_keep_the_three_levels_of_t05():
    cases = replay_module()._cases()
    for context in ("dungeon", "raid", "pvp-bg", "pvp-world"):
        assert [lv for c, lv in cases if c == context] == [20, 40, 60]


# --- T08d, bloc E : rejeu par fonction, appelé par `forever update` -------------------------------------------


def test_run_cases_writes_in_the_given_cache_and_returns_the_cases(tmp_path, monkeypatch):
    """`run_cases` rejoue les cas choisis sur un dossier de données et un cache donnés ; le calcul est simulé (aucun
    Monte Carlo) : seul le chemin des fichiers et des arguments est contrôlé."""
    mod = replay_module()
    seen = []

    def fake_build_report(deps, context, level, **kwargs):
        seen.append((deps.data_dir, context, level, kwargs["seed"]))
        return {"provenance": {"game_version": "x"}, "context": context, "level": level}

    monkeypatch.setattr(mod, "build_report", fake_build_report)
    data = tmp_path / "data"
    out = mod.run_cases("update-x-avant", ["leveling-20", "raid-40"], data_dir=data, cache_dir=tmp_path / "cache")
    assert sorted(out) == ["leveling-20", "raid-40"]
    assert out["raid-40"]["report"]["level"] == 40
    assert seen == [(data, "leveling", 20, mod.SEED), (data, "raid", 40, mod.SEED)]
    folder = tmp_path / "cache" / "builds" / "update-x-avant"
    assert sorted(p.name for p in folder.glob("*.json")) == ["leveling-20.json", "raid-40.json"]
