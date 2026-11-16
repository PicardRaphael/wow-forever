"""RA1 : données de l'addon ForeverRappels (`RappelsData.lua`) générées depuis `classes.json`, jamais écrites à la
main dans `addon/`. Fixture synthétique (identifiants inventés), aucune règle de jeu ; le Lua produit est relu par le
vrai Lua 5.1 (lupa)."""

import pytest
from forever.rappels import GROUPS, build_groups, render_lua

lupa = pytest.importorskip("lupa")
from lupa import lua51


def spell(name, name_fr, ids):
    return {"name": name, "name_fr": name_fr, "ranks": [{"spell_id": i, "rank": n} for n, i in enumerate(ids, 1)]}


CLASSES = {
    "classes": {
        "Hunter": {
            "spells": {
                "aspectOfTheHawk": spell("Aspect of the Hawk", "Faucon inventé", [900003, 900001, 900002]),
                "aspectOfTheCheetah": spell("Aspect of the Cheetah", "Guépard inventé", [900010]),
                "aspectOfThePack": spell("Aspect of the Pack", None, [900020]),
                "aspectOfTheBeast": spell("Aspect of the Beast", "Bête inventée", [900030, 900031]),
            }
        }
    }
}


def load(text):
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(text.encode("utf-8"))
    return lua.globals().ForeverRappelsData


def test_groups_hold_every_rank_and_the_french_name():
    groups = build_groups(CLASSES)
    assert groups["aspect_faucon"] == {"name": "Faucon inventé", "spells": [900003, 900001, 900002]}
    assert groups["aspect_guepard"]["spells"] == [900010]
    assert groups["aspect_bete"]["spells"] == [900030, 900031]


def test_missing_french_name_falls_back_to_the_english_name():
    assert build_groups(CLASSES)["aspect_meute"]["name"] == "Aspect of the Pack"


def test_group_absent_from_the_data_is_left_out():
    classes = {
        "classes": {
            "Hunter": {"spells": {"aspectOfTheHawk": CLASSES["classes"]["Hunter"]["spells"]["aspectOfTheHawk"]}}
        }
    }
    assert set(build_groups(classes)) == {"aspect_faucon"}


def test_every_group_points_to_a_class_and_a_spell_key():
    assert {"aspect_faucon", "aspect_guepard", "aspect_meute", "aspect_bete"} <= set(GROUPS)
    for cls, key in GROUPS.values():
        assert cls and key


def test_rendered_lua_is_read_back_with_version_and_fingerprint():
    text = render_lua(build_groups(CLASSES), game_version="9.9.9.1", data_sha="abc123")
    data = load(text)
    assert data.game_version == "9.9.9.1" and data.data_sha == "abc123"
    hawk = data.groups.aspect_faucon
    assert hawk.name == "Faucon inventé"
    assert [hawk.spells[i] for i in range(1, len(hawk.spells) + 1)] == [900003, 900001, 900002]


def test_rendered_lua_escapes_quotes_and_backslashes():
    groups = {"aspect_faucon": {"name": 'A "b" \\ c', "spells": [900001]}}
    data = load(render_lua(groups, game_version="v", data_sha="s"))
    assert data.groups.aspect_faucon.name == 'A "b" \\ c'


def test_repository_placeholder_has_no_spell_ids():
    from conftest import REPO_ROOT

    text = (REPO_ROOT / "addon" / "ForeverRappels" / "RappelsData.lua").read_text(encoding="utf-8")
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("--"))
    assert not any(ch.isdigit() for ch in code)
    data = load(text)
    assert len(list(data.groups.keys())) == 0
