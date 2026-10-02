"""Révision 4 de 1.60.1.70124 (T08b, bloc I) : abaissements de certitude faits (plus aucun en attente), plus aucune
valeur `certain` écrite à la main, fichier décodé des ratios couvert, plafond de la bêta dans `meta.json`."""

from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.origins import check_version, inventory

V = DATA_DIR / LOCAL_VERSION


def test_no_pending_lowering_left():
    assert read_json(V / "origins.json")["pending"] == []
    _, pending = inventory(DATA_DIR, LOCAL_VERSION)
    assert pending == []


def test_installed_version_passes_and_covers_the_decoded_file():
    report = check_version(DATA_DIR, LOCAL_VERSION)
    assert report.ok, [f"{i.file} {i.path} {i.kind}" for i in report.issues[:10]]
    rules = read_json(V / "origins.json")["rules"]
    assert any(r["file"] == "character_scaling.json" and r["origin"] == "client" for r in rules)
    assert any(r["file"] == "meta.json" and "/game_state" in r["paths"] for r in rules)


def test_mechanics_values_written_by_hand_are_at_most_probable():
    values = read_json(V / "mechanics.json")["values"]
    origins = read_json(V / "origins.json")["rules"]
    params = {
        p.split("/")[2]
        for r in origins
        if r["origin"] == "parametre" and r["file"] == "mechanics.json"
        for p in r["paths"]
    }
    assert {k for k, v in values.items() if v["certainty"] == "certain"} <= params
    assert "build.beta_level_cap" not in values
    fc = read_json(V / "sources.json")["files"]["leveling.json"]["field_certainty"]
    assert "certain" not in fc.values()


def test_beta_cap_is_an_installation_fact():
    state = read_json(V / "meta.json")["game_state"]["beta_level_cap"]
    # T08b : posé en révision 4 de 1.60.1.70124 ; 1.60.1.70170 (2026-10-02) : observé, installé en révision 1
    assert state["revision"] == 1 and state["source"] and state["certainty"] in ("probable", "certain")
