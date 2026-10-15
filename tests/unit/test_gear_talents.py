"""Bloc 4c (idées du chat du 2026-10-16, point 5 ; décision 282) : les poids du Mage tiennent compte des talents.
À mon niveau, mes vrais talents (contexte du jeu) ; à un autre niveau, les talents de mon plan (ordre de prise du
build calculé) ; avant le premier point, aucun talent. La réponse dit le build qui a servi ; le classement change
quand un talent qui modifie la valeur d'une statistique est pris.

Valeurs : addons fabriqués dans `tmp_path`, poids calculés par le moteur sur les données du dépôt ; talents lus dans
le plan calculé (aucun talent écrit ici sauf ceux que le plan rend). Aucun chiffre de jeu ici."""

from test_gear_level_reply import wow_dir

from forever.gear import gear_report, leveling_gear, mage_guide_weights, mage_weights

HIGH = 20


def leveling(deps, level, **kwargs):
    return gear_report(deps, "leveling", class_name="Mage", race="Gnome", faction="alliance", level=level, **kwargs)


def test_future_level_uses_my_talent_plan_and_says_it(tmp_path, make_deps):
    deps = make_deps(wow_dir=wow_dir(tmp_path), offline=True)
    doc = leveling(deps, HIGH)
    used = doc["talents_used"][str(HIGH)]
    assert used["source"] == "plan" and used["talents"]
    assert any("plan de talents" in note for note in doc["weights_notes"])


def test_my_level_uses_my_real_talents(tmp_path, make_deps):
    deps = make_deps(wow_dir=wow_dir(tmp_path), offline=True)
    plan = leveling(deps, HIGH)["talents_used"][str(HIGH)]["talents"]
    mine = dict(list(plan.items())[:1])  # un build réel différent du plan : le premier talent seulement
    doc = leveling(deps, HIGH, talents=mine, talents_level=HIGH)
    used = doc["talents_used"][str(HIGH)]
    assert used == {"source": "actuels", "talents": mine}
    assert any("tes talents actuels" in note for note in doc["weights_notes"])


def test_no_talent_before_the_first_point(tmp_path, make_deps):
    deps = make_deps(wow_dir=wow_dir(tmp_path), offline=True)
    doc = leveling(deps, 1, to_level=3)
    assert {u["source"] for u in doc["talents_used"].values()} == {"aucun"}


def test_a_talent_that_changes_a_stat_value_changes_the_ranking(tmp_path, make_deps):
    deps = make_deps(wow_dir=wow_dir(tmp_path), offline=True)
    used = leveling(deps, HIGH)["talents_used"][str(HIGH)]
    talents = used["talents"]
    rotation = used["rotation"]
    bare = mage_guide_weights(mage_weights(deps, level=HIGH, race="Gnome", rotation=rotation), spec_key="fire-mage")
    built = mage_guide_weights(
        mage_weights(deps, level=HIGH, race="Gnome", rotation=rotation, talents=talents), spec_key="fire-mage"
    )
    # statistique dont la valeur relative à l'Intelligence change le plus avec les talents du plan
    ratio = {
        k: (bare[k] / bare["int"], built[k] / built["int"]) for k in bare if k != "int" and k in built and bare[k] > 0
    }
    stat, (before, after) = max(ratio.items(), key=lambda kv: abs(kv[1][0] - kv[1][1]))
    assert before != after
    amount = 2 / (before + after)  # objet A : `amount` de cette statistique ; objet B : 1 Intelligence
    addons = tmp_path / "flip" / "Interface" / "AddOns"
    (addons / "GearQuestForever_MAGE").mkdir(parents=True)
    (addons / "GearQuestForever_MAGE" / "Data.Mage.generated.lua").write_text(
        "local GQ = GearQuest\nGQ.Data.mageItemFacts = {\n"
        '    [950001]={name="Stat",quality=2,reqLevel=1,sourceType="vendor",instructions="Bought."},\n'
        '    [950002]={name="Int",quality=2,reqLevel=1,sourceType="vendor",instructions="Bought."},\n'
        "}\nGQ.Data.magePicks = {\n"
        f'    {{950001,"Hands",{HIGH},{HIGH},1,"fire","Alliance",1.0}},\n'
        f'    {{950002,"Hands",{HIGH},{HIGH},2,"fire","Alliance",1.0}},\n'
        "}\n",
        encoding="utf-8",
    )
    (addons / "ForeverGuide").mkdir()
    (addons / "ForeverGuide" / "GearData.lua").write_text(
        f"local _, ns = ...\nns.GEAR_DATA = [[\n950001 10 1 {HIGH} 2 0 0 {stat}={amount}\n950002 10 1 {HIGH} 2 0 0 int=1\n]]\n",
        encoding="utf-8",
    )
    first = {
        name: leveling_gear(addons, "MAGE", level=HIGH, weights=w)[0]["item"]
        for name, w in (("bare", bare), ("built", built))
    }
    assert first["bare"] != first["built"]  # le talent pris change le premier choix
