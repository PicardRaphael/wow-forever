"""SIM2 bloc 5 : relevés d'attributs de ForeverLogger -> points d'appui des statistiques de base (correctif
0003-base-stats).

- Valeur sans équipement : effectif - bonus - malus (`UnitStat`), pour les cinq attributs ; un relevé incomplet est
  écarté ;
- seulement la classe simulée ; race du client (nom de fichier) -> race du proto de wowsims (Scourge -> RaceUndead) ;
- un seul point par race et niveau (le plus récent) ; toutes les SavedVariables du jeu sont lues.
SavedVariables synthétiques écrites dans `tmp_path`, aucune règle de jeu."""

from forever.pipeline.addon_sv import read_logger_db
from forever.sims.base_stats import anchors_from_logger, logger_anchors

SV = """ForeverLoggerDB = {
 ["schema"] = 1,
 ["characters"] = {
  ["Player-1"] = {
   ["name"] = "Rose", ["class"] = "MAGE", ["race"] = "Human",
   ["snapshots"] = {
    { ["reason"] = "connexion", ["level"] = 22, ["time"] = 100, ["localtime"] = "11/08/2026 10:00:00",
      ["attributes"] = {
       ["strength"] = { ["stat"] = 30, ["effective"] = 41, ["pos"] = 11, ["neg"] = 0 },
       ["agility"] = { ["stat"] = 25, ["effective"] = 25, ["pos"] = 0, ["neg"] = 0 },
       ["stamina"] = { ["stat"] = 33, ["effective"] = 50, ["pos"] = 17, ["neg"] = 0 },
       ["intellect"] = { ["stat"] = 60, ["effective"] = 72, ["pos"] = 12, ["neg"] = -2 },
       ["spirit"] = { ["stat"] = 55, ["effective"] = 55, ["pos"] = 0, ["neg"] = 0 },
      },
    },
    { ["reason"] = "niveau", ["level"] = 23, ["time"] = 200, ["localtime"] = "11/08/2026 11:00:00",
      ["attributes"] = {
       ["strength"] = { ["stat"] = 31, ["effective"] = 31, ["pos"] = 0, ["neg"] = 0 },
      },
      ["gains"] = { ["health"] = 15, ["power"] = 20, ["strength"] = 1 },
    },
   },
  },
  ["Player-2"] = {
   ["name"] = "Mort", ["class"] = "MAGE", ["race"] = "Scourge",
   ["snapshots"] = {
    { ["reason"] = "connexion", ["level"] = 1, ["time"] = 50, ["localtime"] = "11/08/2026 09:00:00",
      ["attributes"] = {
       ["strength"] = { ["stat"] = 19, ["effective"] = 19, ["pos"] = 0, ["neg"] = 0 },
       ["agility"] = { ["stat"] = 18, ["effective"] = 18, ["pos"] = 0, ["neg"] = 0 },
       ["stamina"] = { ["stat"] = 21, ["effective"] = 21, ["pos"] = 0, ["neg"] = 0 },
       ["intellect"] = { ["stat"] = 22, ["effective"] = 22, ["pos"] = 0, ["neg"] = 0 },
       ["spirit"] = { ["stat"] = 27, ["effective"] = 27, ["pos"] = 0, ["neg"] = 0 },
      },
    },
   },
  },
  ["Player-3"] = {
   ["name"] = "Grom", ["class"] = "WARRIOR", ["race"] = "Orc",
   ["snapshots"] = {
    { ["reason"] = "connexion", ["level"] = 10, ["time"] = 60, ["localtime"] = "11/08/2026 09:30:00",
      ["attributes"] = {
       ["strength"] = { ["stat"] = 40, ["effective"] = 40, ["pos"] = 0, ["neg"] = 0 },
       ["agility"] = { ["stat"] = 30, ["effective"] = 30, ["pos"] = 0, ["neg"] = 0 },
       ["stamina"] = { ["stat"] = 35, ["effective"] = 35, ["pos"] = 0, ["neg"] = 0 },
       ["intellect"] = { ["stat"] = 20, ["effective"] = 20, ["pos"] = 0, ["neg"] = 0 },
       ["spirit"] = { ["stat"] = 25, ["effective"] = 25, ["pos"] = 0, ["neg"] = 0 },
      },
    },
   },
  },
 },
}
"""


def _write(folder):
    folder.mkdir(parents=True)
    path = folder / "ForeverLogger.lua"
    path.write_bytes(SV.encode("utf-8"))
    return path


def test_snapshot_attributes_and_gains_are_read(tmp_path):
    db = read_logger_db(_write(tmp_path / "sv"))
    snap = db.characters["Player-1"].snapshots[0]
    assert snap.attributes["intellect"] == {"stat": 60, "effective": 72, "pos": 12, "neg": -2}
    assert db.characters["Player-1"].snapshots[1].gains == {"health": 15, "power": 20, "strength": 1}


def test_naked_values_for_the_simulated_class_only(tmp_path):
    db = read_logger_db(_write(tmp_path / "sv"))
    anchors = anchors_from_logger(db, "ClassMage")
    assert anchors == [
        {"level": 1, "race": "RaceUndead", "strength": 19, "agility": 18, "stamina": 21, "intellect": 22,
         "spirit": 27},
        {"level": 22, "race": "RaceHuman", "strength": 30, "agility": 25, "stamina": 33, "intellect": 62,
         "spirit": 55},
    ]  # fmt: skip
    assert [a["level"] for a in anchors_from_logger(db, "ClassWarrior")] == [10]
    assert anchors_from_logger(db, "ClassDruid") == []


def test_every_saved_variables_file_of_the_game_is_read(make_deps, tmp_path):
    wow = tmp_path / "wow"
    _write(wow / "WTF" / "Account" / "A" / "SavedVariables")
    other = wow / "WTF" / "Account" / "B" / "SavedVariables"
    other.mkdir(parents=True)
    (other / "ForeverLogger.lua").write_bytes(SV.replace("Player-1", "Player-9").replace("= 22,", "= 30,").encode())
    anchors, files = logger_anchors(make_deps(wow_dir=wow), "ClassMage")
    assert sorted({a["level"] for a in anchors}) == [1, 22, 30] and len(files) == 2
    assert logger_anchors(make_deps(), "ClassMage") == ([], [])  # sans dossier du jeu
