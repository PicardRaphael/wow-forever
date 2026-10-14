"""Profil joueur au schéma 3 (P06b, bloc C, décision 235) : équipement complet (`gear`) et fiche du personnage
(`sheet`), sources `jeu` (contexte du pont) et `simulationcraft` (export collé), écriture par `apply_game_fields`
seulement (le pont, au clic du joueur), lecture du schéma 2 et réécriture en 3 sans rien perdre. Valeurs
synthétiques (aucune règle de jeu)."""

import json
from dataclasses import replace

from forever.cli import main
from forever.profile import (
    SCHEMA_VERSION,
    SOURCE_RANK,
    apply_game_fields,
    load_profile,
    make_field,
    merge_field,
    read_profile,
    set_character,
)

AT = "2026-10-10T12:00:00Z"
GEAR = {"16": {"item": 15444, "enchant": 1883, "gems": [], "suffix": 0, "unique": 0, "name": "Staff of Orgrimmar"}}
SHEET = {"spell_power": {"frost": 29, "fire": 29}, "crit": {"spell": 4.18}, "read_at": AT}


def test_schema_and_source_order():
    assert SCHEMA_VERSION == 4  # schéma 4 depuis LN1 (personnages archivés, décision 271)
    order = sorted(SOURCE_RANK, key=SOURCE_RANK.__getitem__)
    assert order[:4] == ["joueur", "jeu", "simulationcraft", "ForeverLogger"]
    kept, conflict = merge_field(make_field(18, "simulationcraft", AT), make_field(19, "jeu", AT))
    assert kept["value"] == 19 and conflict is not None
    kept, _ = merge_field(make_field(19, "jeu", AT), make_field(20, "joueur", AT))
    assert kept["value"] == 20


def test_schema_2_is_read_then_written_as_3(tmp_path, make_deps):
    path = tmp_path / "profile.json"
    doc = {"schema_version": 2, "active": "Jen", "realms": {},
           "characters": {"Jen": {"class": make_field("Mage", "joueur", "2026-09-01T00:00:00Z"),
                                  "level": make_field(18, "joueur", "2026-09-01T00:00:00Z")}}}  # fmt: skip
    path.write_text(json.dumps(doc), encoding="utf-8")
    before = path.read_bytes()
    loaded = load_profile(path)
    assert loaded["characters"]["Jen"]["level"]["value"] == 18 and path.read_bytes() == before
    deps = replace(make_deps(), profile_path=path)
    set_character(deps, "Jen", level=19)
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["schema_version"] == 4  # schéma courant (4 depuis LN1)
    c = read_profile(deps)["character"]
    assert (c["class"], c["level"], c["gear"], c["sheet"]) == ("Mage", 19, {}, {})


def test_apply_game_fields_creates_and_updates(tmp_path):
    path = tmp_path / "profile.json"
    fields = {"class": "Mage", "race": "Orc", "faction": "Horde", "level": 19, "talents": {"a": 5}, "gear": GEAR}
    doc = apply_game_fields(path, "Jen", "Royaume", fields, source="jeu", at=AT, client_build="1.60.1.70338")
    raw = doc["characters"]["Jen"]
    assert raw["realm"] == "Royaume" and doc["active"] == "Jen"
    assert raw["level"] == {"value": 19, "source": "jeu", "at": AT, "client_build": "1.60.1.70338",
                            "certainty": "certain"}  # fmt: skip
    assert raw["gear"]["value"] == GEAR and raw["talents"]["value"] == {"a": 5}
    assert load_profile(path)["schema_version"] == 4  # schéma courant (4 depuis LN1)
    doc = apply_game_fields(path, "Jen", "Royaume", {"sheet": SHEET}, source="simulationcraft", at=AT,
                            client_build="1.60.1.70338")  # fmt: skip
    sheet = doc["characters"]["Jen"]["sheet"]
    assert sheet["value"] == SHEET and sheet["source"] == "simulationcraft" and sheet["certainty"] == "certain"
    assert sheet["note"] == "lue avec les buffs actifs"
    assert doc["characters"]["Jen"]["level"]["value"] == 19


def test_profile_show_lists_gear_and_sheet(tmp_path, make_deps, capsys):
    path = tmp_path / "profile.json"
    apply_game_fields(path, "Jen", "Royaume", {"class": "Mage", "race": "Orc", "level": 19, "gear": GEAR},
                      source="jeu", at=AT, client_build="1.60.1.70338")  # fmt: skip
    apply_game_fields(path, "Jen", "Royaume", {"sheet": SHEET}, source="simulationcraft", at=AT, client_build=None)
    deps = replace(make_deps(), profile_path=path)
    assert main(["profile", "show", "Jen"], deps) == 0
    out = capsys.readouterr()[0]
    assert "Équipement (1 pièce, jeu) : 16 Staff of Orgrimmar (objet 15444, enchantement 1883)" in out
    assert "Fiche (simulationcraft, lue avec les buffs actifs" in out and "spell_power" in out
