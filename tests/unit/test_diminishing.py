"""Rendements décroissants en PvP (PV1, bloc C ; registre K1, K3) : règles du serveur de Classic, `suppose`.

Valeurs lues dans `forever/data/<version>/pvp_rules.json` (sources citées), jamais écrites dans le test. La catégorie
d'un contrôle est le masque `DiminishType` du client (`classes.json`, certain) ; les durées de base viennent des
rangs du client."""

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.engine.diminishing import Application, effective_durations
from forever.gamedata import dr_rules


@pytest.fixture(scope="module")
def raw():
    return read_json(DATA_DIR / LOCAL_VERSION / "pvp_rules.json")


@pytest.fixture(scope="module")
def rules(raw):
    return dr_rules(raw)


def category_in_data() -> int:
    """Une catégorie de contrôle réellement portée par un sort de classe (Kidney Shot…), lue dans classes.json."""
    doc = read_json(DATA_DIR / LOCAL_VERSION / "classes.json")
    bits = sorted(
        {
            spell["pvp"]["control"]["diminish"]
            for c in doc["classes"].values()
            for spell in c["spells"].values()
            if spell["pvp"].get("control") and spell["pvp"]["control"]["diminish"]
        }
    )
    assert len(bits) >= 2  # prémisse : plusieurs catégories dans les données
    return bits[0]


def other_category() -> int:
    doc = read_json(DATA_DIR / LOCAL_VERSION / "classes.json")
    bits = sorted(
        {
            spell["pvp"]["control"]["diminish"]
            for c in doc["classes"].values()
            for spell in c["spells"].values()
            if spell["pvp"].get("control") and spell["pvp"]["control"]["diminish"]
        }
    )
    return bits[1]


def base(rules) -> float:
    """Durée de base sous le plafond PvP des données (le plafond n'intervient pas)."""
    cap = rules.pvp_cap_s
    return cap / 2 if cap else 4.0


def next_time(rules, time_s: float, duration_s: float) -> float:
    """Instant juste avant la remise à zéro, selon le point de départ de la fenêtre des données."""
    start = time_s + duration_s if rules.window_from == "fin" else time_s
    return start + rules.window_s - 0.01


def test_first_application_has_full_duration(rules):
    cat = category_in_data()
    (r,) = effective_durations(rules, [Application(0.0, cat, base(rules))])
    assert r.duration_s == pytest.approx(base(rules) * rules.steps[0]) and r.step == 1 and not r.immune


def test_successive_applications_follow_the_data_steps(rules):
    cat, d = category_in_data(), base(rules)
    apps, t = [], 0.0
    for _ in rules.steps:
        apps.append(Application(t, cat, d))
        t += 0.5
    got = effective_durations(rules, apps)
    assert [r.duration_s for r in got] == pytest.approx([d * s for s in rules.steps])
    assert [r.step for r in got] == list(range(1, len(rules.steps) + 1))
    assert len(rules.steps) >= 2 and rules.steps[1] < rules.steps[0]  # la règle diminue vraiment


def test_window_resets_after_the_data_window(rules):
    cat, d = category_in_data(), base(rules)
    first = effective_durations(rules, [Application(0.0, cat, d)])[0]
    before = next_time(rules, 0.0, first.duration_s)
    kept = effective_durations(rules, [Application(0.0, cat, d), Application(before, cat, d)])
    assert kept[1].step == 2  # encore dans la fenêtre
    after = before + 0.02
    reset = effective_durations(rules, [Application(0.0, cat, d), Application(after, cat, d)])
    assert reset[1].step == 1 and reset[1].duration_s == pytest.approx(d * rules.steps[0])


def test_categories_are_independent(rules):
    a, b, d = category_in_data(), other_category(), base(rules)
    got = effective_durations(rules, [Application(0.0, a, d), Application(0.5, b, d), Application(1.0, a, d)])
    assert [r.step for r in got] == [1, 1, 2]
    assert got[1].duration_s == pytest.approx(d * rules.steps[0])


def test_immune_after_the_last_step(rules):
    cat, d = category_in_data(), base(rules)
    apps = [Application(0.1 * i, cat, d) for i in range(len(rules.steps) + 1)]
    last = effective_durations(rules, apps)[-1]
    assert last.immune and last.duration_s == 0 and last.step is None


def test_pvp_duration_is_the_base_when_present(rules):
    cat, d = category_in_data(), base(rules)
    (r,) = effective_durations(rules, [Application(0.0, cat, d, pvp_duration_s=d / 2)])
    assert r.duration_s == pytest.approx(d / 2 * rules.steps[0])  # registre K3 : durée PvP du client
    if rules.pvp_cap_s:
        (capped,) = effective_durations(rules, [Application(0.0, cat, rules.pvp_cap_s * 3)])
        assert capped.duration_s == pytest.approx(rules.pvp_cap_s * rules.steps[0])


def test_rules_are_suppose_with_a_source(raw):
    dr = raw["diminishing_returns"]
    for key in ("steps", "window_s", "window_from", "pvp_duration_cap_s"):
        entry = dr[key]
        assert entry["certainty"] == "suppose", key
        assert entry["sources"] and all(s.startswith("https://") for s in entry["sources"]), key
    assert raw["open_question"]  # point de départ de la fenêtre et catégories à mesurer (PV2)


def test_unmapped_mechanic_has_no_category(rules):
    d = base(rules)
    got = effective_durations(rules, [Application(0.1 * i, 0, d) for i in range(len(rules.steps) + 2)])
    assert all(r.step is None and not r.immune and r.duration_s == pytest.approx(d) for r in got)


def test_every_category_of_the_client_is_named_or_flagged(raw):
    doc = read_json(DATA_DIR / LOCAL_VERSION / "classes.json")
    bits = {
        spell["pvp"]["control"]["diminish"]
        for c in doc["classes"].values()
        for spells in (c["spells"], c.get("pet_spells", {}))
        for spell in spells.values()
        if spell["pvp"].get("control") and spell["pvp"]["control"]["diminish"]
    }
    categories = raw["categories"]
    for bit in bits:
        entry = categories[str(bit)]
        assert entry["certainty"] == "suppose" and (entry["name"] or entry["note"])
