"""Valeurs héritées de la Classic recensées et marquées (décision 294 ; plan des simulateurs §6) : toute règle d'origine
(`origins.json`) ou entrée de `mechanics.json` dont la source cite la Classic (règle de Classic, vMangos, émulateur de
Classic) est listée par `forever origins classic` ; une réponse qui s'appuie sur l'un de ces fichiers le dit dans sa
provenance (nombre et premières clés) ; leur remplacement par des valeurs de Forever vient après la sortie, avec les
mesures de l'utilisateur. Règles fabriquées ici ; les tests sur la version installée ne lisent aucune valeur de jeu."""

import json

from forever.classic import classic_note, classic_values


def write(tmp_path):
    vdir = tmp_path / "data" / "1.0"
    vdir.mkdir(parents=True)
    rules = [
        {"file": "mechanics.json", "paths": ["/values/xp.elite_factor"], "origin": "manuel", "certainty": "suppose",
         "source": "règle de Classic (vMangos, émulateur de Classic 1.12)", "reason": "règle du serveur"},
        {"file": "mechanics.json", "paths": ["/values/build.confidence"], "origin": "parametre", "certainty": None,
         "source": "réglage de l'outil", "reason": "seuil"},
        {"file": "pvp_rules.json", "paths": ["/categories"], "origin": "manuel", "certainty": "suppose",
         "source": "règles de Classic (vmangos)", "reason": "absentes du client"},
    ]  # fmt: skip
    (vdir / "origins.json").write_text(json.dumps({"rules": rules}), encoding="utf-8")
    mech = {"values": {"xp.group": {"value": 1, "certainty": "suppose", "source": "règle de Classic : groupe"},
                       "build.confidence": {"value": 0.9, "source": "réglage de l'outil"}}}  # fmt: skip
    (vdir / "mechanics.json").write_text(json.dumps(mech), encoding="utf-8")
    return vdir


def test_classic_values_are_listed_from_origins_and_mechanics(tmp_path):
    rows = classic_values(write(tmp_path))
    keys = {(r["file"], r["path"]) for r in rows}
    assert keys == {
        ("mechanics.json", "/values/xp.elite_factor"),
        ("mechanics.json", "/values/xp.group"),
        ("pvp_rules.json", "/categories"),
    }
    assert all(r["source"] for r in rows)


def test_note_names_the_classic_values_of_the_files_used(tmp_path):
    vdir = write(tmp_path)
    note = classic_note(vdir, {"mechanics.json"})
    assert note is not None and "2 valeur(s)" in note and "xp.elite_factor" in note and "après la sortie" in note
    assert "categories" not in note
    assert classic_note(vdir, {"spells.json"}) is None


def test_installed_build_and_leveling_answers_say_it(make_deps):
    from forever.leveling import simulate_leveling

    out = simulate_leveling(make_deps(), 20, n=5)
    assert any("héritées de la Classic" in a for a in out["provenance"]["assumptions"])


def test_note_can_be_limited_to_the_keys_an_answer_uses(tmp_path):
    vdir = write(tmp_path)
    note = classic_note(vdir, {"mechanics.json"}, {"xp.group"})
    assert note is not None and "1 valeur(s)" in note and "xp.group" in note and "elite_factor" not in note
