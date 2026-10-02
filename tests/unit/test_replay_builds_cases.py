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
