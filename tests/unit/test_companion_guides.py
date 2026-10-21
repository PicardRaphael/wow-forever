"""Forever Companion lu pour les neuf classes (plan « Sources d'abord », étape b ; décisions 272 et 288) : ses arbres de
talents (identifiant de sort, rangs, ligne, colonne), ses builds par spécialisation (« Level 30 (Beta) »,
« Leveling 1-60 », « Standard Build » ; points par arbre et par position, sans ordre de prise) et ses rotations en prose
(« Single Target — Level 30 », AoE). Chaque build est ramené à nos clés de talent par l'identifiant de sort (le nom à
défaut) ; une position que nos données ne connaissent pas (talent retiré, arbre plus ancien) écarte le build avec sa
raison et met la source « en retard » pour la classe. `forever_lookup(kind="class_guide")` rend, par spécialisation, le
build adapté au niveau, sa légalité, la rotation et la fraîcheur des sources ; certitude `suppose` (addon).

Addon fabriqué dans `tmp_path` depuis nos arbres de la version installée (`classes.json`) ; noms de builds et textes
inventés ; aucun chiffre de jeu."""

import json

import pytest
from conftest import DATA_DIR, LOCAL_VERSION
from forever.pipeline.companion import read_companion, talents_of_build

CLASSES = json.loads((DATA_DIR / LOCAL_VERSION / "classes.json").read_text(encoding="utf-8"))["classes"]
UNKNOWN_ID = 999999999  # identifiant fabriqué, absent du client


def _lua_tree(cls):
    trees = []
    for i, tree in enumerate(CLASSES[cls]["trees"], start=1):
        rows = [
            f'{{name="{t["name"]}",icon=0,id={t["spell_id"]},ranks={t["max"]},row={t["tier"]},col={t["col"]}}}'
            for t in tree["talents"]
        ]
        if i == 1:
            rows.append(f'{{name="Talent retiré",icon=0,id={UNKNOWN_ID},ranks=3,row=1,col=4}}')
        trees.append(f'  [{i}]={{bg="x",treeName="{tree["name"]}",talents={{\n    ' + ",\n    ".join(rows) + "\n  }},")
    return "{\n" + "\n".join(trees) + "\n}"


def write_companion(root, cls="Priest"):
    first = CLASSES[cls]["trees"][0]["talents"]
    retired = len(first)  # position (base 0) du talent fabriqué
    data = root / "Interface" / "AddOns" / "ForeverCompanion" / "Data"
    data.mkdir(parents=True)
    token = CLASSES[cls]["file"].lower()
    spec = CLASSES[cls]["trees"][0]["name"]
    (data / "Meta.lua").write_text('ForeverCompanionData = ForeverCompanionData or {}\nForeverCompanionData.meta = '
                                   '{dataVersion=1, updated="2026-10-20"}\n', encoding="utf-8")  # fmt: skip
    builds = (
        f'ForeverCompanionData.talentBuilds["{token}"] = {{\n'
        f'  ["{spec}"] = {{\n'
        f'    {{name="Level 30 (Beta)",lv=30,tabs={{[1]={{[0]=1}}}}}},\n'
        f'    {{name="Leveling 1-60",tabs={{[1]={{[0]=1,[1]=1}}}}}},\n'
        f'    {{name="Ancien",tabs={{[1]={{[0]=1,[{retired}]=2}}}}}},\n'
        "  },\n}\n"
    )
    (data / "Talents.lua").write_text(
        "ForeverCompanionData = ForeverCompanionData or {}\nForeverCompanionData.talentTrees = {}\n"
        "ForeverCompanionData.talentBuilds = {}\n"
        f'ForeverCompanionData.talentTrees["{token}"] = {_lua_tree(cls)}\n' + builds,
        encoding="utf-8",
    )
    (data / "Rotations.lua").write_text(
        "ForeverCompanionData = ForeverCompanionData or {}\nlocal R = {}\nForeverCompanionData.rotations = R\n"
        f'R["{cls}"] = {{\n  ["{spec}"] = {{\n    single = {{\n'
        '      {{t="text",v="Lance "},{t="skill",v="Sort A",id=1},{t="text",v=" puis "},{t="skill",v="Sort B",id=2}},\n'
        '    },\n    aoe = {\n    },\n    intro = {{t="text",v="Texte d\'introduction."}},\n  },\n}\n',
        encoding="utf-8",
    )
    return root, spec


def test_builds_are_mapped_to_our_keys_by_spell_id(tmp_path):
    root, spec = write_companion(tmp_path)
    guide = read_companion(root / "Interface" / "AddOns", CLASSES)
    priest = guide["classes"]["Priest"]
    first = CLASSES["Priest"]["trees"][0]["talents"]
    builds = {b["name"]: b for b in priest["specs"][spec]["builds"]}
    assert builds["Level 30 (Beta)"]["talents"] == {first[0]["key"]: 1} and builds["Level 30 (Beta)"]["level"] == 30
    assert builds["Leveling 1-60"]["talents"] == {first[0]["key"]: 1, first[1]["key"]: 1}
    assert builds["Ancien"]["unmatched"] == ["Talent retiré"]
    assert priest["unmatched"] == ["Talent retiré"]  # source en retard pour la classe (contenu)
    assert priest["specs"][spec]["rotation"]["single"] == ["Lance Sort A puis Sort B"]
    assert priest["specs"][spec]["rotation"]["intro"] == "Texte d'introduction."
    assert guide["meta"]["updated"] == "2026-10-20"


def test_talents_of_build_never_guess_an_unknown_position(tmp_path):
    trees = [[{"name": "A", "id": 1}, {"name": "B", "id": 2}]]
    ours = {1: "a"}
    talents, unmatched = talents_of_build({1: {0: 1, 1: 3, 5: 1}}, trees, ours, {})
    assert talents == {"a": 1} and unmatched == ["B", "position 1.5"]


def test_class_guide_picks_the_build_for_the_level(tmp_path, make_deps):
    from forever.lookup import lookup_class_guide

    root, spec = write_companion(tmp_path)
    deps = make_deps(wow_dir=root)
    low = lookup_class_guide(deps, "Prêtre", level=20)
    s = low["specs"][spec]
    assert s["pick"]["name"] == "Level 30 (Beta)" and s["pick"]["legal_at_level"] in (True, False)
    assert "Ancien" in [a["name"] for a in s["set_aside"]]
    assert s["rotation"]["single"] and low["provenance"]["certainty"] == "suppose"
    assert any("Forever Companion" in a for a in low["provenance"]["assumptions"])
    high = lookup_class_guide(deps, "Priest", level=45)
    assert high["specs"][spec]["pick"]["name"] == "Leveling 1-60"


def test_class_guide_without_companion_says_so(make_deps, tmp_path):
    from forever.errors import ForeverError
    from forever.lookup import lookup_class_guide

    with pytest.raises(ForeverError) as err:
        lookup_class_guide(make_deps(wow_dir=tmp_path / "vide"), "Priest", level=20)
    assert "Forever Companion" in err.value.message
