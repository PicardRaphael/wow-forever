"""AMI1 : profil rempli tout seul depuis ForeverLogger, sur chaque PC, sans saisie (demande du 2026-11-08) :
personnage `Nom-Royaume` (dossier du personnage dans `WTF/Account/<compte>/<royaume>/`), classe, race, faction lue
dans `races.json`, dernier niveau relevé, talents des nœuds du client traduits en clés (clés du moteur du Mage pour
le Mage). SavedVariables fabriquées dans `tmp_path` ; données du dépôt pour les classes et les races."""

from forever.profile_sync import sync_from_logger

SV = """ForeverLoggerDB = {
 ["characters"] = {
  ["Player-1"] = {
   ["name"] = "Louis", ["class"] = "SHAMAN", ["race"] = "Dwarf",
   ["snapshots"] = {
    { ["reason"] = "connexion", ["level"] = 11, ["time"] = 100, ["localtime"] = "11/08/2026 10:00:00",
      ["talents"] = { [104729] = 1 } },
    { ["reason"] = "niveau", ["level"] = 12, ["time"] = 200, ["localtime"] = "11/08/2026 11:00:00",
      ["talents"] = { [104729] = 2 } },
   },
  },
 },
}
"""


def _wow(tmp_path):
    wow = tmp_path / "wow"
    account = wow / "WTF" / "Account" / "COMPTE"
    (account / "SavedVariables").mkdir(parents=True)
    (account / "SavedVariables" / "ForeverLogger.lua").write_bytes(SV.encode("utf-8"))
    (account / "Krypto" / "Louis").mkdir(parents=True)
    return wow


def test_characters_are_set_from_the_latest_snapshot(make_deps, tmp_path):
    deps = make_deps(wow_dir=_wow(tmp_path))
    calls = []
    done = sync_from_logger(deps, set_char=lambda d, name, **kw: calls.append((name, kw)))
    assert [name for name, _ in calls] == ["Louis-Krypto"]
    kw = calls[0][1]
    assert kw["cls"] == "Shaman" and kw["race"] == "Dwarf" and kw["faction"] == "Alliance" and kw["level"] == 12
    assert kw["talents"] == {"tidalFocus": 2}
    assert done == [{"name": "Louis-Krypto", "class": "Shaman", "level": 12}]


def test_nothing_without_the_game_folder(make_deps):
    assert sync_from_logger(make_deps(), set_char=lambda *a, **k: None) == []
