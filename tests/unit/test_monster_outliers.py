"""PNJ hors norme écartés de la courbe des PV (décision 223, demande de l'utilisateur du 2026-10-09).

Quand un niveau compte au moins `min_npcs` PNJ de la courbe et que la référence est concordante (au moins une part
`concordance` des autres PNJ à moins du seuil de leur médiane), un PNJ dont les PV s'écartent de plus du seuil de la
médiane des autres est mesuré un par un mais écarté de la courbe, raison « hors norme » écrite. Valeurs synthétiques,
à la forme des cas relevés (ours au-dessus, Sunscale Lashtail en dessous, bestioles du niveau 1) ; les paramètres de la
règle sont lus dans `mechanics.json` installé."""

from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.pipeline.monsters import OutlierRule, build_monsters, curve_outliers, outlier_rule

RULE = OutlierRule(threshold=0.15, min_npcs=3, concordance=(2, 3))


def obs(npc_id, level, max_hp, name="PNJ"):
    return {"npc_id": npc_id, "name": name, "level": level, "max_hp": max_hp, "guids": 1, "ui_map_id": 1, "log": "x"}


def test_a_npc_far_from_a_concordant_level_is_out():
    level = {11: [(1, 239), (2, 239), (3, 239), (4, 239), (1186, 287), (3254, 191)]}
    out = curve_outliers(level, RULE)
    assert set(out) == {1186, 3254}
    assert all("hors norme" in reason and "décision 223" in reason for reason in out.values())


def test_a_small_gap_stays_in():
    assert curve_outliers({5: [(1, 102), (2, 102), (3, 112)]}, RULE) == {}  # écart sous le seuil


def test_a_level_with_too_few_npcs_is_not_judged():
    assert curve_outliers({6: [(1, 120), (1128, 144)]}, RULE) == {}


def test_a_non_concordant_reference_is_not_judged():
    # niveau 5 relevé : l'ours seul est écarté ; Crag Boar n'est pas jugé (autres : 102 et l'ours à 122)
    assert set(curve_outliers({5: [(1199, 102), (1125, 102), (1128, 122)]}, RULE)) == {1128}
    # niveau 1 relevé : les bestioles s'écartent d'une référence concordante, les monstres ne sont pas jugés
    assert set(curve_outliers({1: [(707, 42), (705, 42), (721, 1), (5951, 8)]}, RULE)) == {721, 5951}


def test_build_monsters_moves_the_outliers_out_of_the_curve_at_every_level():
    observations = [obs(n, 11, 239) for n in (1, 2, 3, 4)] + [obs(n, 12, 272) for n in (5, 6, 7)]
    observations += [obs(1186, 11, 287, "Elder Black Bear"), obs(1186, 12, 326, "Elder Black Bear")]
    table = build_monsters(observations, None, LOCAL_VERSION, outlier=RULE)
    assert [e["npc_id"] for e in table["curve_excluded"]] == [1186]
    assert table["npcs"]["1186"]["levels"]["11"]["max_hp"] == 287  # toujours mesuré un par un
    assert table["hp_by_level"]["11"]["value"] == 239 and table["hp_by_level"]["11"]["certainty"] == "certain"
    assert table["hp_by_level"]["12"]["value"] == 272


def test_the_rule_is_read_in_the_installed_data():
    values = read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]
    rule = outlier_rule(values)
    assert rule is not None and 0 < rule.threshold < 1 and rule.min_npcs >= 3
    assert 0 < rule.concordance[0] <= rule.concordance[1]
    assert values["monsters.curve_outlier"]["registry"] == "H11"
