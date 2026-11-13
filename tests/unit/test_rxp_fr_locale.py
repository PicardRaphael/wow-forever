"""FR1 : depuis RestedXP v4.11.36, `RXPGuides.lua` met en commentaire `["frFR"] = true` de `addon.enabledLocale` ;
en client frFR, les guides anglais se chargent alors en plus des guides français (doublons dans le menu). Sur accord
de l'utilisateur (2026-11-13), `forever rxp traduire` et la veille réactivent cette seule ligne, après une
sauvegarde ; `--annuler` remet le fichier de RestedXP.

Valeurs : fichier Lua minimal écrit pour le test (structure de la table seulement, aucun texte de RestedXP)."""

import shutil
from pathlib import Path

from forever.cli import main
from forever.rxp_fr.install import enable_french
from forever.rxp_fr.run import translate_addons
from forever.update import UpdateOptions, run_update

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "rxp_fr"
LUA = """local addon = {}
addon.enabledLocale = {
    ["enUS"] = false,
    -- ["deDE"] = true,
    -- ["frFR"] = true,
    -- ["zhTW"] = true
}
-- ["frFR"] = true hors de la table : jamais touché
"""
ONLY = UpdateOptions(only=frozenset({"addons"}), network=False)


def _addons(tmp_path: Path, text: str = LUA) -> Path:
    addons = tmp_path / "wow" / "Interface" / "AddOns"
    shutil.copytree(FIX / "AddOns", addons)
    (addons / "RXPGuides" / "RXPGuides.lua").write_bytes(text.encode("utf-8"))
    shutil.copytree(FIX / "wago", tmp_path / "cache" / "wago" / "1.0.0.1")
    return addons


def _lua(addons: Path) -> str:
    return (addons / "RXPGuides" / "RXPGuides.lua").read_bytes().decode("utf-8")


def test_only_the_french_line_of_the_table_is_enabled(tmp_path):
    addons = _addons(tmp_path)
    assert enable_french(addons, tmp_path / "cache") == "réactivé"
    text = _lua(addons)
    assert '    ["frFR"] = true,\n' in text
    assert '    -- ["deDE"] = true,' in text and '    -- ["zhTW"] = true' in text
    assert '-- ["frFR"] = true hors de la table' in text
    assert len(text) == len(LUA) - 3
    saved = list((tmp_path / "cache" / "backups" / "rxp_fr" / "restedxp").glob("RXPGuides.lua.*"))
    assert len(saved) == 1 and saved[0].read_bytes() == LUA.encode("utf-8")
    assert enable_french(addons, tmp_path / "cache") == "déjà actif"
    assert _lua(addons) == text


def test_without_the_table_nothing_is_written(tmp_path):
    addons = _addons(tmp_path, "local addon = {}\n")
    assert enable_french(addons, tmp_path / "cache") == "absent"
    assert _lua(addons) == "local addon = {}\n"
    assert enable_french(tmp_path / "vide", tmp_path / "cache") == "absent"


def test_simulation_leaves_the_file_and_a_write_enables_french(make_deps, tmp_path):
    addons = _addons(tmp_path)
    deps = make_deps(wow_dir=tmp_path / "wow")
    doc = translate_addons(deps, simulate=True)
    assert doc["french"] == "à réactiver" and _lua(addons) == LUA
    doc = translate_addons(deps)
    assert doc["french"] == "réactivé" and '    ["frFR"] = true,' in _lua(addons)


def test_cancel_puts_back_the_restedxp_file(make_deps, tmp_path):
    addons = _addons(tmp_path)
    deps = make_deps(wow_dir=tmp_path / "wow")
    assert main(["rxp", "traduire", "--json"], deps) == 0
    assert main(["rxp", "traduire", "--annuler", "--json"], deps) == 0
    assert _lua(addons) == LUA


def test_the_pass_enables_french_again_after_a_restedxp_update(make_deps, tmp_path):
    addons = _addons(tmp_path)
    deps = make_deps(wow_dir=tmp_path / "wow")
    run_update(deps, ONLY)
    assert '    ["frFR"] = true,' in _lua(addons)
    (addons / "RXPGuides" / "RXPGuides.lua").write_bytes(LUA.encode("utf-8"))  # RestedXP mis à jour
    report = run_update(deps, ONLY)
    (step,) = [s for s in report["steps"] if s["name"] == "addons"]
    assert "français réactivé" in step["detail"]
    assert '    ["frFR"] = true,' in _lua(addons)
