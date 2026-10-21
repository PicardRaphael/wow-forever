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
