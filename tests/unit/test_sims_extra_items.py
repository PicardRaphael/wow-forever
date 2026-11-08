"""SIM2 bloc 6 : objets absents de la base de wowsims pris dans la base du fork Go épinglé de MythicSim (simulateur de
la communauté pour Forever, MIT), donnés au binaire par `--forever-items=<fichier>` (correctif 0004-items).

- Seuls les objets que wowsims ne connaît pas sont pris ; un objet connu de wowsims n'est jamais remplacé ;
- sans MythicSim copié, rien n'est ajouté ; sans le correctif épinglé, l'option est refusée ;
- dans le calcul par tranche, un objet pris chez MythicSim est gardé et nommé (`extra_items`), un objet inconnu des
  deux reste écarté et nommé (`unknown_items`).
Bases fabriquées dans `tmp_path`, simulateur fabriqué : aucune valeur de jeu."""

import json
from pathlib import Path

import pytest
from test_sims_base_stats import FileSim
from test_sims_brackets import _setup as brackets_setup
from wowsims_fakes import ENCOUNTER, clone

from forever.pipeline.wowsims_build import PATCHES_DIR
from forever.sims.brackets import extra_items, run_brackets
from forever.sims.wowsims import WowsimsError, read_presets, request_for, run_sim

PATCHES = ["0001-level.patch", "0002-ranks.patch", "0003-base-stats.patch", "0004-items.patch"]


def _db(path: Path, ids):
    path.mkdir(parents=True, exist_ok=True)
    (path / "db.json").write_text(json.dumps({"items": [{"id": i, "name": f"objet {i}"} for i in ids]}), "utf-8")


def _bases(cache, ws_ids, ms_ids):
    ws = cache / "third_party" / "wowsims" / "forever" / "assets" / "database"
    _db(ws, ws_ids)
    (ws / "leftover_db.json").write_text(json.dumps({"items": []}), "utf-8")
    if ms_ids is not None:
        _db(cache / "third_party" / "mythicsim" / "go" / "assets" / "database", ms_ids)
        pin = {"commit": "d" * 40, "go_revision": "e" * 40, "binary": "x.exe", "sha256": "f" * 64}
        (cache / "third_party" / "mythicsim" / "pin.json").write_text(json.dumps(pin), "utf-8")


def _pin(cache, files):
    root = cache / "third_party" / "wowsims"
    doc = json.loads((root / "pin.json").read_text(encoding="utf-8"))
    doc["patches"] = {"sha256": "c" * 64, "files": files}
    (root / "pin.json").write_text(json.dumps(doc), encoding="utf-8")


def test_only_items_unknown_to_wowsims_are_taken_from_mythicsim(tmp_path):
    clone(tmp_path)
    _bases(tmp_path, [1, 2], [2, 3, 4])
    path, ids, note = extra_items(tmp_path)
    assert ids == {3, 4}
    assert [i["id"] for i in json.loads(path.read_text(encoding="utf-8"))["items"]] == [3, 4]
    assert "MythicSim" in note and "e" * 12 in note and "suppose" in note


def test_without_mythicsim_nothing_is_added(tmp_path):
    clone(tmp_path)
    _bases(tmp_path, [1, 2], None)
    assert extra_items(tmp_path) == (None, set(), None)


class ItemsSim(FileSim):
    def __call__(self, args, cwd, timeout=None):
        flag = next((a for a in args if a.startswith("--forever-items=")), None)
        self.items = json.loads(Path(flag.split("=", 1)[1]).read_text(encoding="utf-8")) if flag else None
        return super().__call__(args, cwd, timeout)


def test_items_file_is_passed_only_with_the_patch(tmp_path):
    root = clone(tmp_path)
    _bases(tmp_path, [1], [1, 3])
    path, _, _ = extra_items(tmp_path)
    fire = next(p for p in read_presets(root / "forever") if p.key == "mage/dps/Fire")
    req = request_for(fire, race="RaceHuman", encounter=ENCOUNTER)
    _pin(tmp_path, PATCHES)
    sim = ItemsSim()
    out = run_sim(tmp_path, req, runner=sim, level=25, items=path)
    assert sim.items == {"items": [{"id": 3, "name": "objet 3"}]} and out["source"]["extra_items"] is True
    _pin(tmp_path, PATCHES[:3])
    with pytest.raises(WowsimsError, match="0004-items"):
        run_sim(tmp_path, req, runner=ItemsSim(), level=25, items=path)


def test_brackets_keep_items_known_to_mythicsim_and_name_them(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    _bases(deps.cache_dir, [6614], [6614, 240046])
    _pin(deps.cache_dir, PATCHES)
    sim = ItemsSim()
    picks = [{"slot": "Back", "item": 6614}, {"slot": "Shoulder", "item": 240046}, {"slot": "Head", "item": 99}]
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="60", steps=[],
                       picks_at=lambda _level: picks, iterations=10, runner=sim)  # fmt: skip
    row = out["rows"][0]
    assert row["extra_items"] == [240046] and row["unknown_items"] == [99]
    items = sim.requests[0]["raid"]["parties"][0]["players"][0]["equipment"]["items"]
    assert items[2] == {"id": 240046} and items[3] == {"id": 6614} and items[0] == {}
    assert sim.items == {"items": [{"id": 240046, "name": "objet 240046"}]}
    assert any("MythicSim" in a for a in out["provenance"]["assumptions"])


def test_repository_patch_adds_items_without_replacing_any():
    text = (PATCHES_DIR / "0004-items.patch").read_text(encoding="utf-8")
    assert "--forever-items=" in text and "forever (SIM2)" in text and "sim/core/database_load.go" in text
    assert "if !known[item.Id]" in text  # un objet connu de wowsims n'est jamais remplacé
