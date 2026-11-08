"""SIM2 (décision 305) : correctifs locaux de wowsims/forever pour calculer au niveau L.

- Les correctifs vivent à part, dans `forever/sims/patches/wowsims/*.patch`, appliqués dans l'ordre de leur nom par
  `git apply` après la remise du clone sur son commit, avant la génération protobuf et la compilation.
- L'épinglage (`pin.json`) porte l'empreinte du jeu de correctifs : même commit et correctifs changés, on recompile.
- Un correctif qui ne s'applique plus garde le binaire épinglé précédent (échec nommé, rien ne casse en silence).
- Le niveau passe au binaire par l'option `--forever-level=L` (lue à l'initialisation du simulateur, avant la
  requête) ; sans correctifs épinglés, un niveau est refusé ; la source du calcul cite l'empreinte des correctifs.

Commandes simulées (`test_wowsims_build.Tools`, `wowsims_fakes.Sim`) : aucun réseau ni compilateur."""

import json

import pytest
from test_wowsims_build import NEXT, Tools
from wowsims_fakes import ENCOUNTER, Sim, clone

from forever.errors import ForeverError
from forever.pipeline.gitops import GitOpsError
from forever.pipeline.wowsims_build import PATCHES_DIR, patchset, pinned, update_wowsims
from forever.sims.wowsims import WowsimsError, read_presets, request_for, run_sim, source_note


def _patches(tmp_path, **files):
    folder = tmp_path / "patches"
    folder.mkdir(exist_ok=True)
    for name, text in files.items():
        (folder / f"{name}.patch").write_bytes(text.encode("utf-8"))
    return folder


def test_patches_are_applied_in_name_order_after_reset_and_before_protoc(tmp_path):
    folder = _patches(tmp_path, **{"0002-b": "deux\n", "0001-a": "un\n"})
    tools = Tools(tmp_path / "cache")
    pin = update_wowsims(tmp_path / "cache", runner=tools, patches_dir=folder)
    applies = [i for i, c in enumerate(tools.calls) if c[:2] == ["git", "apply"]]
    assert [tools.calls[i][-1].rsplit("/", 1)[-1].rsplit("\\", 1)[-1] for i in applies] == [
        "0001-a.patch",
        "0002-b.patch",
    ]
    clone_at = next(i for i, c in enumerate(tools.calls) if c[:2] == ["git", "clone"])
    protoc = next(i for i, c in enumerate(tools.calls) if c[0] == "protoc" and c[1] != "--version")
    assert clone_at < applies[0] and applies[-1] < protoc
    assert pin["patches"] == patchset(folder)
    assert pin["patches"]["files"] == ["0001-a.patch", "0002-b.patch"] and len(pin["patches"]["sha256"]) == 64


def test_same_commit_with_changed_patches_is_rebuilt(tmp_path):
    folder = _patches(tmp_path, **{"0001-a": "un\n"})
    first = update_wowsims(tmp_path, runner=Tools(tmp_path), patches_dir=folder)
    same = update_wowsims(tmp_path, runner=Tools(tmp_path), patches_dir=folder)
    assert same["status"] == "à jour"
    (folder / "0001-a.patch").write_bytes(b"un, corrige\n")
    tools = Tools(tmp_path)
    again = update_wowsims(tmp_path, runner=tools, patches_dir=folder)
    assert again["status"] == "compilé" and any(c[:2] == ["go", "build"] for c in tools.calls)
    assert again["commit"] == first["commit"] and again["patches"]["sha256"] != first["patches"]["sha256"]


def test_a_pin_without_patches_is_rebuilt_once_patches_exist(tmp_path):
    """Binaire épinglé avant SIM2 (aucune clé `patches`) : recompilé avec les correctifs au passage suivant."""
    empty = tmp_path / "vide"
    empty.mkdir()
    update_wowsims(tmp_path, runner=Tools(tmp_path), patches_dir=empty)
    doc = json.loads((tmp_path / "third_party" / "wowsims" / "pin.json").read_text(encoding="utf-8"))
    doc.pop("patches", None)
    (tmp_path / "third_party" / "wowsims" / "pin.json").write_text(json.dumps(doc), encoding="utf-8")
    folder = _patches(tmp_path, **{"0001-a": "un\n"})
    assert update_wowsims(tmp_path, runner=Tools(tmp_path), patches_dir=folder)["status"] == "compilé"


def test_a_patch_that_no_longer_applies_keeps_the_previous_binary(tmp_path):
    folder = _patches(tmp_path, **{"0001-a": "un\n"})
    first = update_wowsims(tmp_path, runner=Tools(tmp_path), patches_dir=folder)
    with pytest.raises(GitOpsError, match="0001-a.patch"):
        update_wowsims(tmp_path, runner=Tools(tmp_path, commit=NEXT, fail=["git", "apply"]), patches_dir=folder)
    assert pinned(tmp_path) == first
    assert (tmp_path / "third_party" / "wowsims" / first["binary"]).is_file()


def test_repository_patches_name_their_reason():
    """Correctifs du dépôt : le niveau réglable, les rangs appris, puis les statistiques de base (bloc 4), chacun marqué « forever (SIM2) » dans le code
    qu'il ajoute ; mention de licence de wowsims gardée par le fichier d'origine (correctifs, pas de copie)."""
    names = sorted(p.name for p in PATCHES_DIR.glob("*.patch"))
    assert names == ["0001-level.patch", "0002-ranks.patch", "0003-base-stats.patch", "0004-items.patch"]
    level = (PATCHES_DIR / "0001-level.patch").read_text(encoding="utf-8")
    ranks = (PATCHES_DIR / "0002-ranks.patch").read_text(encoding="utf-8")
    assert "sim/core/constants.go" in level and "--forever-level=" in level and "forever (SIM2)" in level
    assert "sim/core/spelldata/ladder.go" in ranks and "forever (SIM2)" in ranks
    assert patchset(PATCHES_DIR)["files"] == names


class FlagSim(Sim):
    """wowsimcli simulé qui garde les arguments de chaque lancement."""

    def __init__(self):
        super().__init__()
        self.args = []

    def __call__(self, args, cwd, timeout=None):
        self.args.append(list(args))
        return super().__call__(args, cwd, timeout)


def _patched_pin(tmp_path, sha="c" * 64):
    root = clone(tmp_path)
    doc = json.loads((root / "pin.json").read_text(encoding="utf-8"))
    doc["patches"] = {"sha256": sha, "files": ["0001-level.patch", "0002-ranks.patch"]}
    (root / "pin.json").write_text(json.dumps(doc), encoding="utf-8")
    return root


def test_level_is_passed_to_the_patched_binary_and_named_in_the_source(tmp_path):
    root = _patched_pin(tmp_path)
    preset = next(p for p in read_presets(root / "forever") if p.key == "mage/dps/Fire")
    sim = FlagSim()
    out = run_sim(tmp_path, request_for(preset, race="RaceHuman", encounter=ENCOUNTER), runner=sim, level=25)
    assert "--forever-level=25" in sim.args[-1]
    assert out["source"]["patches"] == "c" * 64 and out["source"]["level"] == 25
    run_sim(tmp_path, request_for(preset, race="RaceHuman", encounter=ENCOUNTER), runner=sim)
    assert not any(a.startswith("--forever-level") for a in sim.args[-1])  # sans niveau : 60, comme avant


def test_level_without_patched_binary_or_out_of_range_is_refused(tmp_path):
    root = clone(tmp_path)  # épinglé avant SIM2 : aucun correctif
    preset = next(p for p in read_presets(root / "forever") if p.key == "mage/dps/Fire")
    req = request_for(preset, race="RaceHuman", encounter=ENCOUNTER)
    with pytest.raises(WowsimsError, match="correctifs"):
        run_sim(tmp_path, req, runner=FlagSim(), level=25)
    _patched_pin(tmp_path)
    for bad in (0, 61):
        with pytest.raises(ForeverError, match="niveau"):
            run_sim(tmp_path, req, runner=FlagSim(), level=bad)


def test_source_note_names_the_patches():
    pin = {"commit": "a" * 40, "committed_at": "2026-11-08", "sha256": "b" * 64,
           "patches": {"sha256": "c" * 64, "files": ["0001-level.patch"]}}  # fmt: skip
    note = source_note(pin)
    assert "correctifs forever" in note and "c" * 12 in note and "tel quel" not in note
    assert "tel quel" in source_note({k: v for k, v in pin.items() if k != "patches"})
