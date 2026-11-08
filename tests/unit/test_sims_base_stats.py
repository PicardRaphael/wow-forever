"""SIM2 bloc 4 : statistiques de base au niveau du personnage dans wowsims corrigé (correctif 0003-base-stats).

- Mana de base et critique par point d'Intelligence ou d'Agilité : tables du client au niveau L
  (`forever/data/<version>/character_scaling.json`, PlayerExpectedStat), passées en pour cent comme wowsims les compte.
- Attributs sans équipement : relevés en jeu (ForeverLogger), passés tels quels ; wowsims interpole entre eux et ses
  tables du niveau 60. Sans relevé au niveau ou en dessous, les attributs du 60 restent, et la provenance le dit.
- Le fichier est donné au binaire par `--forever-base-stats=<fichier>`, seulement si l'épinglage porte le correctif ;
  sinon le calcul garde les valeurs du 60 et le dit.
- `forever sims update` nettoie les fichiers laissés par les correctifs du passage précédent avant de les réappliquer.

Valeurs attendues lues dans les données du dépôt (source citée) ; simulateur fabriqué."""

import json
from pathlib import Path

import pytest
from conftest import DATA_DIR
from test_sims_brackets import FROST_STEPS
from test_sims_brackets import _setup as brackets_setup
from test_wowsims_build import Tools
from wowsims_fakes import ENCOUNTER, Sim, clone

from forever.pipeline.wowsims_build import update_wowsims
from forever.sims.base_stats import anchor_note, base_stats_doc, client_scaling
from forever.sims.brackets import run_brackets
from forever.sims.wowsims import WowsimsError, read_presets, request_for, run_sim

ALL_PATCHES = ["0001-level.patch", "0002-ranks.patch", "0003-base-stats.patch"]
ANCHOR = {"level": 22, "race": "RaceHuman", "strength": 1, "agility": 2, "stamina": 3, "intellect": 4, "spirit": 5}


def _scaling(class_name):
    """Ligne de la classe dans character_scaling.json de la version courante des données (source du test)."""
    version = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))["game_version"]
    doc = json.loads((DATA_DIR / version / "character_scaling.json").read_text(encoding="utf-8"))
    return doc["classes"][class_name]


def test_client_values_at_the_level_in_wowsims_units(make_deps):
    row = _scaling("Mage")
    out = client_scaling(make_deps(), "Mage", 25)
    assert out["mana"] == row["base_mana"][24]
    assert out["crit_per_int"] == pytest.approx(row["spell_crit_per_intellect"][24] * 100, rel=1e-12)
    assert out["crit_per_agi"] == pytest.approx(row["crit_per_agility"][24] * 100, rel=1e-12)
    doc = base_stats_doc("ClassMage", out, [ANCHOR])
    assert doc == {"class": "ClassMage", **out, "anchors": [ANCHOR]}


def test_anchor_note_says_measured_or_level_60():
    assert "niveau 60" in anchor_note([], 25) and "ForeverLogger" in anchor_note([], 25)
    assert "niveau 60" in anchor_note([{**ANCHOR, "level": 30}], 25)  # relevé au-dessus du niveau seulement
    note = anchor_note([ANCHOR], 25)
    assert "interpolés" in note and "22" in note and "suppose" in note


class FileSim(Sim):
    """wowsimcli simulé : lit le fichier des statistiques de base pendant le lancement."""

    def __init__(self):
        super().__init__()
        self.base_stats = []
        self.args = []

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        self.args.append(args)
        flag = next((a for a in args if a.startswith("--forever-base-stats=")), None)
        self.base_stats.append(json.loads(Path(flag.split("=", 1)[1]).read_text(encoding="utf-8")) if flag else None)
        return super().__call__(args, cwd, timeout)


def _pin(root, files):
    doc = json.loads((root / "pin.json").read_text(encoding="utf-8"))
    doc["patches"] = {"sha256": "c" * 64, "files": files}
    (root / "pin.json").write_text(json.dumps(doc), encoding="utf-8")


def test_base_stats_file_is_passed_then_removed(tmp_path):
    root = clone(tmp_path)
    _pin(root, ALL_PATCHES)
    fire = next(p for p in read_presets(root / "forever") if p.key == "mage/dps/Fire")
    doc = {"class": "ClassMage", "mana": 1.0, "crit_per_int": 2.0, "crit_per_agi": 3.0, "anchors": []}
    sim = FileSim()
    out = run_sim(tmp_path, request_for(fire, race="RaceHuman", encounter=ENCOUNTER), runner=sim, level=25,
                  base_stats=doc)  # fmt: skip
    assert sim.base_stats == [doc] and out["source"]["base_stats"] is True
    path = next(a for a in sim.args[0] if a.startswith("--forever-base-stats=")).split("=", 1)[1]
    assert not Path(path).exists()  # fichier de passage retiré
    _pin(root, ALL_PATCHES[:2])
    with pytest.raises(WowsimsError, match="0003-base-stats"):
        run_sim(tmp_path, request_for(fire, race="RaceHuman", encounter=ENCOUNTER), runner=FileSim(), level=25,
                base_stats=doc)  # fmt: skip


def test_update_cleans_files_left_by_previous_patches(tmp_path):
    update_wowsims(tmp_path, runner=Tools(tmp_path))
    tools = Tools(tmp_path)
    update_wowsims(tmp_path, runner=tools)
    git = [c[:2] for c in tools.calls if c[0] == "git"]
    reset = git.index(["git", "reset"])
    assert git[reset + 1] == ["git", "clean"]
    clean = next(c for c in tools.calls if c[:2] == ["git", "clean"])
    assert "-fd" in clean or ("-f" in clean and "-d" in clean)
    assert "-x" not in clean and "-fdx" not in clean  # fichiers ignorés gardés (code protobuf généré)


def test_brackets_pass_client_values_and_anchors_when_the_patch_is_pinned(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    _pin(deps.cache_dir / "third_party" / "wowsims", ALL_PATCHES)
    sim = FileSim()
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="10-19,20-29", steps=FROST_STEPS,
                       picks_at=None, iterations=10, runner=sim, anchors=[ANCHOR])  # fmt: skip
    row = _scaling("Mage")
    assert [d["mana"] for d in sim.base_stats] == [row["base_mana"][14], row["base_mana"][24]]
    assert all(d["class"] == "ClassMage" and d["anchors"] == [ANCHOR] for d in sim.base_stats)
    assert "niveau 60" in out["rows"][0]["base_stats"] and "interpolés" in out["rows"][1]["base_stats"]


def test_brackets_without_the_patch_keep_level_60_values_and_say_so(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)  # épinglage sans 0003-base-stats
    sim = FileSim()
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="20-29", steps=FROST_STEPS,
                       picks_at=None, iterations=10, runner=sim, anchors=[ANCHOR])  # fmt: skip
    assert sim.base_stats == [None]
    assert "0003-base-stats" in out["rows"][0]["base_stats"]


def test_repository_patches_include_base_stats():
    from forever.pipeline.wowsims_build import PATCHES_DIR

    text = (PATCHES_DIR / "0003-base-stats.patch").read_text(encoding="utf-8")
    assert "--forever-base-stats=" in text and "forever (SIM2)" in text and "sim/core/base_stats.go" in text
