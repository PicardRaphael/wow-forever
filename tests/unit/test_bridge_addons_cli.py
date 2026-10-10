"""`forever bridge addons config | status | restore | log` (P06b, bloc F, décision 235) : réglage du dossier de la
conversation « addons » (refus d'un addon de la communauté), sauvegardes listées, restauration sans suppression,
historique git local lu par `git log` (faux git)."""

import json

from test_bridge_addons import addon

from forever.bridge.addons import AddonsConfig, load_config, snapshot
from forever.cli import main


def test_config_status_and_restore(tmp_path, make_deps, capsys):
    deps = make_deps(wow_dir=tmp_path)
    folder = addon(tmp_path)
    community = tmp_path / "Interface" / "AddOns" / "Questie"
    community.mkdir()
    assert main(["bridge", "addons", "config", "--source", str(community)], deps) != 0
    assert load_config(deps.cache_dir) is None
    capsys.readouterr()
    assert main(["bridge", "addons", "config", "--source", str(folder), "--json"], deps) == 0
    assert json.loads(capsys.readouterr()[0])["source"] == str(folder)
    assert load_config(deps.cache_dir) == AddonsConfig(folder)
    snapshot(AddonsConfig(folder), deps.cache_dir, "20261010T120000Z")
    (folder / "Core.lua").write_text("-- cassé\n", encoding="utf-8")
    assert main(["bridge", "addons", "status"], deps) == 0
    out = capsys.readouterr()[0]
    assert "RaphCompletionist" in out and "20261010T120000Z" in out
    assert main(["bridge", "addons", "restore", "--json"], deps) == 0
    payload = json.loads(capsys.readouterr()[0])
    assert payload["stamp"] == "20261010T120000Z" and "Core.lua" in payload["restored"]
    assert (folder / "Core.lua").read_text(encoding="utf-8") == "-- coeur\n"


def test_without_configuration(make_deps, capsys):
    deps = make_deps()
    assert main(["bridge", "addons", "status"], deps) == 0
    assert "non configurée" in capsys.readouterr()[0]
    assert main(["bridge", "addons", "restore"], deps) != 0
