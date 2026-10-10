"""`forever update` face au réseau (décision 230, point 3), hors ligne, sur le montage de `test_update_chain` :

- une table qui porte des valeurs de calcul (enUS, GameTables) et reste en échec après ses trois essais crée une
  attente « réseau » qui se lève seule au passage suivant ;
- les tables de noms français (frFR) sont facultatives : la version s'installe sans elles, les noms manquants sont
  notés dans `sources.json` (`missing_names`), et un passage suivant les ajoute en révision, écrite seule : les noms
  affichés (`name_fr`) ne sont pas une entrée des moteurs."""

import json
import shutil
from pathlib import Path

import pytest
from conftest import WAGO_70124
from test_update_chain import DRY, TARGET, montage, step  # noqa: F401 : fixture partagée

from forever.engine_inputs import DISPLAY_KEYS, compare_inputs
from forever.errors import InvalidArgumentError
from forever.pipeline.decode import decode_version
from forever.pipeline.fetch import table_url
from forever.pipeline.install import apply_install
from forever.store import read_sources
from forever.update import SELF_CLEARING_KINDS, approve, list_pending, run_update

TIMEOUT = TimeoutError("The read operation timed out")
PET_FOOD_FR = "frFR/ItemPetFood"
REPO = Path(__file__).resolve().parents[2]


def break_route(http, table, locale):
    http.routes[table_url(table, TARGET, locale)] = TIMEOUT


def pending(deps, kind):
    return [e for e in list_pending(deps.cache_dir) if e.get("kind") == kind]


def test_a_failed_calculation_table_waits_for_the_network(montage):  # noqa: F811
    deps, http = montage()
    break_route(http, "SpellName", "enUS")
    report = run_update(deps, DRY._replace(dry_run=False))
    found = step(report, "nouvelle_version")
    assert found["status"] == "attente", found
    assert "enUS/SpellName" in found["detail"]
    waits = pending(deps, "network")
    assert [w["id"] for w in waits] == [f"network-{TARGET}"]
    assert waits[0]["state"] == "en_attente" and waits[0]["version"] == TARGET
    calls = [c for c in http.calls if c[0] == table_url("SpellName", TARGET, "enUS")]
    assert len(calls) == 3  # trois essais avant l'attente


def test_the_network_wait_is_not_approvable(montage):  # noqa: F811
    deps, http = montage()
    break_route(http, "SpellName", "enUS")
    run_update(deps, DRY._replace(dry_run=False))
    assert "network" in SELF_CLEARING_KINDS
    with pytest.raises(InvalidArgumentError, match="se lève seule"):
        approve(deps, f"network-{TARGET}")


def test_the_network_wait_clears_itself_at_the_next_pass(montage):  # noqa: F811
    deps, http = montage()
    broken = table_url("SpellName", TARGET, "enUS")
    good = http.routes[broken]
    http.routes[broken] = TIMEOUT
    run_update(deps, DRY._replace(dry_run=False))
    http.routes[broken] = good
    report = run_update(deps, DRY._replace(dry_run=False))
    assert step(report, "nouvelle_version")["status"] != "attente"
    (wait,) = pending(deps, "network")
    assert wait["state"] == "faite"


def test_missing_french_names_never_block_a_new_version(montage):  # noqa: F811
    deps, http = montage()
    break_route(http, "ItemPetFood", "frFR")
    report = run_update(deps, DRY)
    found = step(report, "nouvelle_version")
    assert found["status"] == "fait", found
    assert PET_FOOD_FR in found["data"]["missing_names"]
    (verdict,) = report["verdicts"]
    assert verdict["action"] == "écrire"
    assert not pending(deps, "network")


def test_decode_without_french_tables_notes_the_missing_names(tmp_path, montage):  # noqa: F811
    deps, _ = montage()
    csv = deps.cache_dir / "wago" / TARGET
    shutil.copytree(WAGO_70124, csv)
    (csv / "frFR" / "ItemPetFood.csv").unlink()
    (csv / "frFR" / "SpellName.csv").unlink()
    candidate = decode_version(deps, TARGET)
    sources = read_sources(candidate.root, TARGET)
    assert sources is not None
    assert sorted(sources["missing_names"]) == ["frFR/ItemPetFood", "frFR/SpellName"]
    spells = json.loads((candidate.root / TARGET / "spells.json").read_text(encoding="utf-8"))
    assert all(not s.get("name_fr") for s in spells["spells"].values())


def test_decode_still_needs_the_calculation_tables(montage):  # noqa: F811
    from forever.errors import ForeverError

    deps, _ = montage()
    csv = deps.cache_dir / "wago" / TARGET
    shutil.copytree(WAGO_70124, csv)
    (csv / "enUS" / "SpellName.csv").unlink()
    with pytest.raises(ForeverError, match="SpellName"):
        decode_version(deps, TARGET)


def test_a_later_pass_adds_the_french_names_as_a_revision_written_alone(montage):  # noqa: F811
    deps, _ = montage()
    csv = deps.cache_dir / "wago" / TARGET
    shutil.copytree(WAGO_70124, csv)
    (csv / "frFR" / "SpellName.csv").unlink()
    apply_install(deps, str(decode_version(deps, TARGET).root), motif="sans noms", new_version=True)
    shutil.rmtree(csv)
    shutil.rmtree(deps.cache_dir / "candidates")
    assert read_sources(deps.data_dir, TARGET)["missing_names"] == ["frFR/SpellName"]
    report = run_update(deps, DRY)
    found = step(report, "correctifs")
    assert found["status"] == "fait", found
    (verdict,) = report["verdicts"]
    assert verdict["kind"] == "install_revision" and verdict["revision"] == 2
    assert verdict["action"] == "écrire"
    assert all(e["identical"] for e in verdict["inputs"].values())


def test_a_pass_without_the_french_names_again_changes_nothing(montage):  # noqa: F811
    deps, http = montage()
    csv = deps.cache_dir / "wago" / TARGET
    shutil.copytree(WAGO_70124, csv)
    (csv / "frFR" / "SpellName.csv").unlink()
    apply_install(deps, str(decode_version(deps, TARGET).root), motif="sans noms", new_version=True)
    shutil.rmtree(csv)
    shutil.rmtree(deps.cache_dir / "candidates")
    break_route(http, "SpellName", "frFR")
    report = run_update(deps, DRY)
    found = step(report, "correctifs")
    assert found["status"] == "rien" and "frFR/SpellName" in found["detail"]
    assert report["verdicts"] == [] and not pending(deps, "network")


def test_french_names_are_not_an_engine_input(tmp_path):
    assert "name_fr" in DISPLAY_KEYS
    before, after = tmp_path / "a", tmp_path / "b"
    for folder, name in ((before, ""), (after, "Éclair de givre")):
        folder.mkdir()
        doc = {"spells": {"frostbolt": {"name": "Frostbolt", "name_fr": name, "ranks": []}}}
        (folder / "spells.json").write_text(json.dumps(doc), encoding="utf-8")
    assert compare_inputs(before, after)["mage_build"].identical


def test_no_engine_reads_the_french_names():
    """Garde : aucun module de calcul ne lit `name_fr` (seuls lookup et pvp s'en servent, pour l'affichage et la
    recherche d'une race par son nom) ; sans quoi l'écarter des entrées des moteurs serait faux."""
    roots = ["forever/engine", "forever/optimize", "forever/sim"]
    files = [p for r in roots for p in (REPO / r).rglob("*.py")]
    files += [REPO / "forever" / "build.py", REPO / "forever" / "leveling.py"]
    readers = [p.relative_to(REPO).as_posix() for p in files if "name_fr" in p.read_text(encoding="utf-8")]
    assert readers == []
