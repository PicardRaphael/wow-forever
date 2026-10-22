"""Sort retiré par une nouvelle version du client (décision 297, 2026-10-22) : il ne bloque plus l'installation. Il est
appliqué comme Piercing Ice : gardé dans `spells.json`, marqué « retiré par la version … », exclu de toutes les
recommandations (builds, PvP, exports) et signalé dans la carte « Mis à jour ». Un sort d'une classe que
`classes.json` ne porte plus est noté de même (`confirmed_changes.json`, carte).

Données du dépôt copiées dans `tmp_path`, sorts et versions des écarts fabriqués ; aucun chiffre du jeu écrit ici."""

import json
import shutil

from conftest import LOCAL_VERSION

from forever.engine.pvp import control
from forever.engine.spells import best_rank
from forever.gamedata import build_game_data
from forever.lookup import lookup_spell
from forever.manifest import write_manifest
from forever.pipeline.install import apply_install, plan_install
from forever.pipeline.observations import resolve
from forever.store import load_version

OLD, NEW = "1.60.1.10000", "1.60.1.10001"
SPELL = "frostbolt"  # sort au cœur du profil d'un Mage Givre


def refused(file, path, before, after):
    return {"file": file, "path": path, "before": before, "after": after, "source": "client", "certainty": "certain",
            "rule": "refused"}  # fmt: skip


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, doc):
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")


def retire(data, key=SPELL, by=NEW):
    """Données où `key` est marqué retiré par `by` (comme l'écrit l'installation)."""
    path = data / LOCAL_VERSION / "spells.json"
    doc = read(path)
    doc["spells"][key]["retired"] = {"by": by, "decision": "décision 297 (test)"}
    write(path, doc)
    write_manifest(data)


def test_a_spell_removed_by_a_newer_version_no_longer_blocks(tmp_path):
    cand = tmp_path / "cand" / NEW
    cand.mkdir(parents=True)
    write(cand / "talents.json", {"trees": []})
    write(cand / "spells.json", {"rank_format": [], "spells": {}})
    out = resolve([refused("spells.json", "fakeSpell", {"ranks": []}, None)], version_from=OLD, version_to=NEW,
                  candidate_vdir=cand, names={"fakeSpell": "Fake Spell"})  # fmt: skip
    assert out.unresolved == [] and out.kept == []
    assert [(e["kind"], e["key"], e["change"]) for e in out.accepted] == [("spell", "fakeSpell", "removed")]
    assert out.notes == [f"sort Fake Spell retiré par la version {NEW} ; ton observation datait de {OLD}"]


def test_the_merge_keeps_the_removed_spell_marked_retired(make_deps, data_copy, tmp_path):
    """Candidate sans un sort, écart tranché (entrée confirmée) : la fusion ne refuse plus, le sort reste dans
    `spells.json` marqué « retiré par la version »."""
    confirmed = data_copy / LOCAL_VERSION / "confirmed_changes.json"
    doc = read(confirmed)
    doc["changes"].append({"kind": "spell", "key": SPELL, "change": "removed", "field": None, "old": SPELL,
                           "new": None, "nature": "client", "decision": "décision 296 (test)"})  # fmt: skip
    write(confirmed, doc)
    write_manifest(data_copy)
    cand = tmp_path / "candidate"
    shutil.copytree(data_copy / LOCAL_VERSION, cand / LOCAL_VERSION)
    spells = read(cand / LOCAL_VERSION / "spells.json")
    del spells["spells"][SPELL]
    write(cand / LOCAL_VERSION / "spells.json", spells)
    write_manifest(cand)
    deps = make_deps(data_dir=data_copy)
    assert plan_install(deps, str(cand))["refused"] == []
    apply_install(deps, str(cand), motif="test", date="2026-10-22")
    after = read(data_copy / LOCAL_VERSION / "spells.json")["spells"][SPELL]
    assert after["retired"]["by"] == LOCAL_VERSION and after["ranks"]


def test_the_final_version_removes_a_spell_my_profile_uses(make_deps, data_copy):
    """Profil d'un Mage Givre : la version finale retire Frostbolt. Plus aucun rang appris (builds et rotations), le
    contrôle PvP ne le compte plus, la fiche le dit retiré par la version."""
    deps = make_deps(data_dir=data_copy)
    gd = build_game_data(load_version(deps))
    level = max(r.level for r in gd.spells[SPELL].ranks)
    before = control(gd, {}, level)
    assert best_rank(gd, SPELL, level, {}) is not None
    retire(data_copy)
    gd = build_game_data(load_version(deps))
    assert gd.spells[SPELL].retired_by == NEW
    assert best_rank(gd, SPELL, level, {}) is None
    assert control(gd, {}, level) < before
    found = lookup_spell(deps, "Frostbolt")
    assert any(f"retiré par la version {NEW}" in a for a in found["provenance"]["assumptions"])


def test_a_class_spell_gone_from_classes_json_is_recorded_and_said(tmp_path):
    from forever.update import _record_retired_class_spells

    base, stage = tmp_path / "base" / OLD, tmp_path / "stage"
    base.mkdir(parents=True)
    (stage / NEW).mkdir(parents=True)
    spell = {"name": "Fake Strike", "ranks": []}
    write(base / "classes.json", {"classes": {"Warrior": {"spells": {"fakeStrike": spell, "kept": spell}}}})
    write(stage / NEW / "classes.json", {"classes": {"Warrior": {"spells": {"kept": spell}}}})
    write(stage / NEW / "confirmed_changes.json", {"changes": []})
    write(stage / "manifest.json", {})
    notes = _record_retired_class_spells(stage, base, NEW)
    assert notes == [f"sort Fake Strike (Warrior) retiré par la version {NEW}"]
    (entry,) = read(stage / NEW / "confirmed_changes.json")["changes"]
    assert (entry["kind"], entry["key"], entry["class"], entry["change"]) == ("class_spell", "fakeStrike", "Warrior",
                                                                             "removed")  # fmt: skip
