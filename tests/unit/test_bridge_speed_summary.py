"""Résumé de la mesure des accélérations (P06b, bloc G) : un échec de qualité déjà présent dans la variante A pour la
même question du même passage est un défaut de la ligne actuelle, rapporté à part ; seuls les échecs propres à une
variante l'empêchent d'être gardée. Durées synthétiques."""

from forever.bridge.speed import Measure, own_failures, report_markdown, summary


def m(variant, question, seconds, failures=(), rnd=1):
    return Measure(variant, rnd, question, seconds, failures=list(failures), text=f"{variant} {question}")


def test_failures_shared_with_a_do_not_count():
    measures = [
        m("A", "pvp", 10.0, ["réponse trop longue"]),
        m("A", "talents", 20.0),
        m("C", "pvp", 5.0, ["réponse trop longue"]),
        m("C", "talents", 9.0),
        m("B", "pvp", 9.5, ["réponse trop longue", "lien changé"]),
        m("B", "talents", 19.0),
    ]
    own = own_failures(measures)
    assert [own[id(x)] for x in measures] == [[], [], [], [], ["lien changé"], []]
    s = summary(measures)
    assert s["C"]["failures"] == 0 and s["C"]["shared_failures"] == 1 and s["C"]["keep"] is True
    assert s["B"]["failures"] == 1 and s["B"]["keep"] is False
    assert s["A"]["keep"] is False
    text = report_markdown(measures, {"date": "2026-10-10T12:00:00Z", "model": "sonnet", "rounds": 1})
    assert "| C (session gardée ouverte) | 7.0 | 7.0 | 0 | 1 |" in text
