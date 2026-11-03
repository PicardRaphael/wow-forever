"""Bloc 4c (idées du chat du 2026-10-16, point 5 ; décision 282) : les poids du Mage tiennent compte des talents.
À mon niveau, mes vrais talents (contexte du jeu) ; à un autre niveau, le build populaire de Talents Forever le plus
proche (RB1, décision 299 : `tests/unit/test_rb1_build_removed.py`) ; avant le premier point, aucun talent. Le
classement change quand un talent qui modifie la valeur d'une statistique est pris.

Valeurs : addons fabriqués dans `tmp_path`, poids calculés par le moteur sur les données du dépôt ; talents lus dans
le build populaire de l'addon synthétique (aucun talent écrit ici). Aucun chiffre de jeu ici."""

from conftest import DATA_DIR, PRE_70450_VERSION
from talents_forever_data import write_addon
from test_gear_level_reply import wow_dir

from forever.gear import gear_report, leveling_gear, mage_guide_weights, mage_weights

HIGH = 20


def leveling(deps, level, **kwargs):
    return gear_report(deps, "leveling", class_name="Mage", race="Gnome", faction="alliance", level=level, **kwargs)


def test_no_talent_before_the_first_point(tmp_path, make_deps):
    deps = make_deps(wow_dir=wow_dir(tmp_path), offline=True)
    doc = leveling(deps, 1, to_level=3)
    assert {u["source"] for u in doc["talents_used"].values()} == {"aucun"}


def test_a_talent_that_changes_a_stat_value_changes_the_ranking(tmp_path, make_deps_at_pre_70450_version):
    root = wow_dir(tmp_path)
    write_addon(root, DATA_DIR / PRE_70450_VERSION / "classes.json")
    deps = make_deps_at_pre_70450_version(wow_dir=root, offline=True)
    used = leveling(deps, HIGH)["talents_used"][str(HIGH)]
    talents = used["talents"]
    rotation = used["rotation"]
    bare = mage_guide_weights(mage_weights(deps, level=HIGH, race="Gnome", rotation=rotation), spec_key="fire-mage")
    built = mage_guide_weights(
        mage_weights(deps, level=HIGH, race="Gnome", rotation=rotation, talents=talents), spec_key="fire-mage"
    )
    # statistique dont la valeur relative à l'Intelligence change le plus avec les talents du build populaire
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


def test_a_popular_talent_unknown_to_the_frozen_engine_is_left_out_and_named(tmp_path, make_deps, monkeypatch):
    """Vérification de RB1 sur 70707 : un talent du build populaire que le moteur gelé ne connaît pas (renommé par le
    client) n'annule plus tous les talents des poids ; il est écarté et nommé. Clé inventée, aucune valeur de jeu."""
    import forever.gear as gear
    from forever.engine.talents import legal_order
    from forever.gamedata import build_game_data
    from forever.store import load_version

    deps = make_deps(wow_dir=wow_dir(tmp_path), offline=True)
    gd = build_game_data(load_version(deps))
    known = next(iter(gd.talents))
    order = legal_order(gd.classes["Mage"], gd.constants.talents, {known: 1})
    plan = {"rank": 1, "spec": "Frost", "asOf": "2026-10-24", "link": "L", "closest": False, "rotation": "frost",
            "order": [*order, "inventedTalent"]}  # fmt: skip
    monkeypatch.setattr(gear, "popular_plan", lambda deps, current: plan)
    doc = leveling(deps, HIGH)
    used = doc["talents_used"][str(HIGH)]
    assert used["source"] == "populaire" and used["talents"] == {known: 1}
    assert used["build"]["ignored"] == ["inventedTalent"]
    assert any("ignorés dans les poids : inventedTalent" in n for n in doc["weights_notes"])
