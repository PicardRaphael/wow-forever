"""Registre des sources et fraîcheur (plan `tasks/plan-sources.md`, étape a ; décisions 288 et 291).

Chaque source (notre moteur du Mage, Talents Forever, Forever Companion, Forever Guide…) dit si elle est à jour pour
la version du jeu installée, en lisant son **contenu** quand c'est possible (talents dont le texte du client ne
correspond plus à aucune règle de lecture du moteur ; export de Talents Forever bloqué par la table de recoupement),
sinon sa **date ou son build** contre la date de publication du build (fraîcheur dite « par la version »). Le choix
d'une source prend la première à jour dans l'ordre du domaine ; une source écartée l'est avec sa raison et la
réponse dit « calcul en cours de mise à jour » ; sans source à jour, la meilleure, « antérieure au patch » ; jamais
une panne.

Documents, règles et dates fabriqués ici ; aucun chiffre de jeu."""

from forever.sources import choose, dated_freshness, engine_freshness, tf_freshness

RULES = {
    "talent_models": {
        "missileBarrage": [
            {"contains": "Arcane Missile hits", "model": "missile_hits"},
            {"contains": "Frost Blast, and Frostfire Bolt", "model": "listed_spells"},
        ],
        "note": "texte",
    }
}


def talents(desc, model=None):
    t = {"key": "missileBarrage", "name": "Missile Barrage", "source": {"client_desc": desc}}
    if model:
        t["model"] = model
    return {"trees": [{"name": "Arcane", "talents": [t]}]}


def test_engine_is_late_when_a_tracked_talent_matches_no_rule():
    """Missile Barrage de ce matin sans sa règle `listed_spells` : le moteur aurait gardé l'ancien sens en silence."""
    late = engine_freshness(talents("Gives your Arcane Blast spell a chance, and your new spells", None), RULES)
    assert late["status"] == "en retard" and late["basis"] == "contenu"
    assert late["detail"] == ["Missile Barrage : texte du client sans règle de lecture connue"]
    ok = engine_freshness(talents("and your Frost Blast, and Frostfire Bolt spells", "listed_spells"), RULES)
    assert ok["status"] == "à jour" and ok["detail"] == []
    assert ok["classes"] == ["Mage"] and ok["source"] == "moteur"


def test_talents_forever_follows_its_export_state_per_class():
    states = {
        "Mage": {"status": "bloque", "talents": ["piercingIce"]},
        "Priest": {"status": "possible", "talents": []},
        "Rogue": {"status": "format_non_pris_en_charge", "talents": []},
    }
    out = {f["classes"][0]: f for f in tf_freshness(states, "0.38.9")}
    assert out["Mage"]["status"] == "en retard" and out["Mage"]["detail"] == ["sans correspondance : piercingIce"]
    assert out["Rogue"]["status"] == "en retard" and "génération" in out["Rogue"]["detail"][0]
    assert out["Priest"]["status"] == "à jour" and out["Priest"]["basis"] == "contenu"
    assert "0.38.9" in out["Mage"]["label"]


def test_dated_sources_compare_their_date_to_the_build_release():
    after = dated_freshness("companion", "Forever Companion", "builds", ["*"], "2026-10-20", "2026-10-16T22:29:05Z")
    assert after["status"] == "à jour" and after["basis"] == "version"
    before = dated_freshness("naowh", "Naowh Forever", "bis", ["*"], "2026-10-11", "2026-10-16T22:29:05Z")
    assert before["status"] == "en retard" and "antérieures au build" in before["detail"][0]
    unknown = dated_freshness("x", "X", "bis", ["*"], None, "2026-10-16T22:29:05Z")
    assert unknown["status"] == "inconnue"


def test_choose_takes_the_first_fresh_source_and_says_why_others_were_set_aside():
    engine = engine_freshness(talents("new text", None), RULES)
    tf = tf_freshness({"Mage": {"status": "possible", "talents": []}}, "0.38.9")[0]
    pick = choose([engine, tf])
    assert pick["chosen"]["source"] == tf["source"]
    assert pick["set_aside"] == [engine]
    assert pick["note"].startswith("calcul en cours de mise à jour : moteur du Mage en retard")
    assert "Talents Forever" in pick["note"]


def test_choose_without_fresh_source_keeps_the_best_and_says_so():
    late = engine_freshness(talents("new text", None), RULES)
    pick = choose([late])
    assert pick["chosen"] is late and pick["set_aside"] == []
    assert "antérieure au patch" in pick["note"]
    assert choose([])["chosen"] is None


def test_status_lists_the_sources(make_deps):
    """`forever status` et l'outil MCP `forever_status` : fraîcheur de chaque source (sans dossier du jeu : le
    moteur du Mage seul)."""
    from forever.cli import render_status
    from forever.status import status_report

    rep = status_report(make_deps(), allow_network=False)
    assert [s["source"] for s in rep["sources"]] == ["moteur"] and rep["sources"][0]["status"] == "à jour"
    assert any(line.startswith("Sources : moteur du Mage à jour") for line in render_status(rep))


def test_build_says_when_the_engine_is_late(data_copy, make_deps):
    """Un texte du client que le moteur ne sait plus lire (règle de Missile Barrage retirée) : la réponse de
    `forever_build` le dit dans sa provenance, en certitude `suppose`, au lieu de garder l'ancien sens en silence."""
    import json

    from conftest import LOCAL_VERSION

    from forever.build import build_report
    from forever.manifest import write_manifest

    path = data_copy / LOCAL_VERSION / "decode_rules.json"
    rules = json.loads(path.read_text(encoding="utf-8"))
    rules["talent_models"]["missileBarrage"] = [{"contains": "texte qui n'existe pas", "model": "listed_spells"}]
    path.write_text(json.dumps(rules, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tpath = data_copy / LOCAL_VERSION / "talents.json"
    talents = json.loads(tpath.read_text(encoding="utf-8"))
    for tree in talents["trees"]:
        for t in tree["talents"]:
            if t["key"] == "missileBarrage":
                t.pop("model", None)
    tpath.write_text(json.dumps(talents, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_manifest(data_copy)
    rep = build_report(make_deps(data_dir=data_copy), "leveling", 12, preset="rapide", sensitivity=False)
    notes = " ".join(rep["provenance"]["assumptions"])
    assert "moteur du Mage" in notes and "Missile Barrage" in notes
    assert rep["provenance"]["certainty"] == "suppose"


def test_report_reads_companion_by_content_and_skillup_by_build(tmp_path, make_deps):
    """Relevé des sources avec les addons : Forever Companion jugé classe par classe sur son contenu (talents de ses
    arbres inconnus de nos données), SkillUp Forever sur le build de ses données. Addons fabriqués."""
    from test_companion_guides import write_companion
    from test_skillup import write_skillup

    from forever.sources import sources_report

    root, _spec = write_companion(tmp_path)
    write_skillup(root)
    rep = {s["source"]: s for s in sources_report(make_deps(wow_dir=root))}
    assert rep["companion:Priest"]["status"] == "en retard" and rep["companion:Priest"]["basis"] == "contenu"
    assert "Talent retiré" in rep["companion:Priest"]["detail"][0]
    assert rep["skillup"]["status"] == "à jour" and rep["skillup"]["basis"] == "version"
