"""SIM2 bloc 5 : ForeverLogger 0.8.0 relève les attributs du personnage à la connexion et à chaque niveau (vrai Lua sous
lupa.lua51, client simulé `tests/fixtures/bridge/wow_stub.lua`).

- `attributes` : pour la Force, l'Agilité, l'Endurance, l'Intelligence et l'Esprit, les quatre retours de `UnitStat`
  (valeur, effectif, bonus, malus) ;
- `gains` : gains de la montée de niveau transmis par `PLAYER_LEVEL_UP` (PV, ressource, cinq attributs) ;
- une API en panne ou secrète laisse le champ absent, sans erreur.
Valeurs synthétiques (entrées du client simulé), aucune règle de jeu."""

import pytest
from test_addon_logger_xp import Logger, to_py

pytest.importorskip("lupa")

STATS = {1: [30, 41, 11, 0], 2: [25, 25, 0, 0], 3: [33, 50, 17, 0], 4: [60, 72, 12, 0], 5: [55, 55, 0, 0]}
NAMED = {
    "strength": {"stat": 30, "effective": 41, "pos": 11, "neg": 0},
    "agility": {"stat": 25, "effective": 25, "pos": 0, "neg": 0},
    "stamina": {"stat": 33, "effective": 50, "pos": 17, "neg": 0},
    "intellect": {"stat": 60, "effective": 72, "pos": 12, "neg": 0},
    "spirit": {"stat": 55, "effective": 55, "pos": 0, "neg": 0},
}


def test_login_snapshot_keeps_the_five_attributes():
    game = Logger(player={"stats": STATS})
    (snap,) = game.entries("snapshots")
    assert to_py(snap.attributes) == NAMED
    assert game.errors() == {}


def test_level_up_keeps_attributes_and_gains():
    game = Logger(player={"stats": STATS})
    game.fire("PLAYER_LEVEL_UP", 20, 15, 22, 1, 0, 1, 0, 2, 3, 2)
    snap = game.entries("snapshots")[-1]
    assert snap.reason == "niveau" and snap.level == 20
    assert to_py(snap.gains) == {"health": 15, "power": 22, "strength": 1, "agility": 0, "stamina": 2,
                                 "intellect": 3, "spirit": 2}  # fmt: skip
    assert to_py(snap.attributes) == NAMED


@pytest.mark.parametrize("mode", ["failing", "secret"])
def test_failing_or_secret_unitstat_leaves_attributes_absent(mode):
    game = Logger(player={"stats": STATS}, **{mode: ("UnitStat",)})
    (snap,) = game.entries("snapshots")
    assert snap.attributes is None
    assert game.errors() == {}


def test_toc_version_is_0_8_0():
    from conftest import REPO_ROOT

    toc = (REPO_ROOT / "addon" / "ForeverLogger" / "ForeverLogger.toc").read_text(encoding="utf-8")
    assert "## Version: 0.8.0" in toc
