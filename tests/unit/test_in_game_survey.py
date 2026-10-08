"""Relevés en jeu de l'utilisateur du 2026-10-08 (certitude certain) : format v6 de Talents Forever vérifié en jeu
(témoin importé et réexporté à l'identique), Improved Serpent Sting absent de l'arbre du Chasseur (CLS3),
Intimidation exige Bestial Swiftness (DON5 : arête circulaire écartée), Improved Life Tap et Amplify Curse placés
(CLS1) ; export du Chasseur et du Démoniste débloqué ; cas d'évaluation sans code stocké.

Valeurs attendues lues dans `decode_rules.json` (`observed_absent`, `observed_positions`), dans les données
installées, dans les fixtures (`tests/fixtures/talents_forever/mage_builds.json`, builds fixes sourcés ;
`tests/fixtures/community/hunter_example_build.json`) ou dans les tables de la fixture wago, jamais écrites dans le
test. Addon synthétique dans `tmp_path` ; aucun accès au dossier réel du jeu."""

import copy
import re

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, REPO_ROOT, read_json
from talents_forever_data import load_fixture, write_addon

from forever.engine.talents import check_class_build
from forever.errors import DataSchemaError
from forever.gamedata import build_game_data
from forever.lookup import check_talents
from forever.pipeline.decode import decode_classes
from forever.store import load_version
from forever.talents_forever import crosscheck_report, decode_code, export_build, load_addon

CLASSES = DATA_DIR / LOCAL_VERSION / "classes.json"
CASES = load_fixture("mage_builds.json")["cases"]
HUNTER_EXAMPLE = read_json(FIXTURES / "community" / "hunter_example_build.json")
EVALS = REPO_ROOT / "plugin" / "evals"
SURVEY_DATE = "2026-10-08"


def specs(rules, field):
    return {cls: spec for cls, spec in rules[field].items() if isinstance(spec, dict)}


def talents_of(c):
    return {t["key"]: t for tree in c["trees"] for t in tree["talents"]}


@pytest.fixture(scope="module")
def doc(class_tables, decode_rules):
    return decode_classes(class_tables, decode_rules, LOCAL_VERSION)


@pytest.fixture(scope="module")
def installed():
    return read_json(CLASSES)["classes"]


# --- Décodage : talent absent de l'arbre en jeu (CLS3) ---------------------------------------------------------


def test_observed_absent_node_is_dropped_with_its_source(doc, decode_rules):
    absent = specs(decode_rules, "observed_absent")
    assert "improvedSerpentSting" in absent["Hunter"]  # prémisse : relevé du 2026-10-08
    for cls, spec in absent.items():
        c = doc["classes"][cls]
        dropped = {d["node_id"]: d for d in c["dropped_nodes"]}
        for key, seen in spec.items():
            assert key not in talents_of(c)
            assert seen["certainty"] == "certain" and SURVEY_DATE in seen["source"]
            reason = dropped[seen["node_id"]]["reason"]
            assert "absent de l'arbre en jeu" in reason and seen["source"] in reason


def test_observed_absent_unknown_talent_stops_the_decode(class_tables, decode_rules):
    rules = copy.deepcopy(decode_rules)
    spec = specs(rules, "observed_absent")["Hunter"]
    seen = next(iter(spec.values()))
    spec["noSuchTalent"] = dict(seen, node_id=seen["node_id"] + 1)
    with pytest.raises(DataSchemaError):
        decode_classes(class_tables, rules, LOCAL_VERSION)


def test_observed_absent_with_another_node_stops_the_decode(class_tables, decode_rules):
    rules = copy.deepcopy(decode_rules)
    seen = next(iter(specs(rules, "observed_absent")["Hunter"].values()))
    seen["node_id"] += 1  # le relevé ne désigne plus le nœud décodé sous cette clé
    with pytest.raises(DataSchemaError):
        decode_classes(class_tables, rules, LOCAL_VERSION)


# --- Décodage : arête suffisante circulaire (DON5) ---------------------------------------------------------------


def test_circular_sufficient_edge_is_dropped(doc):
    hunter = doc["classes"]["Hunter"]
    t = talents_of(hunter)
    by_node = {x["node_id"]: x for x in t.values()}
    intimidation, wrath = t["intimidation"], t["bestialWrath"]
    assert [by_node[p["node_id"]]["key"] for p in intimidation["prereqs"]] == ["bestialSwiftness"]
    assert intimidation["prereq"]["node_id"] == t["bestialSwiftness"]["node_id"]
    assert [by_node[p["node_id"]]["key"] for p in wrath["prereqs"]] == ["intimidation"]
    edge = {(e["from_node"], e["to_node"]): e for e in hunter["dropped_edges"]}
    reason = edge[(wrath["node_id"], intimidation["node_id"])]["reason"]
    assert "circulaire" in reason


def test_no_talent_keeps_a_sufficient_prerequisite_that_requires_it(doc):
    for cls, c in doc["classes"].items():
        by_node = {x["node_id"]: x for x in talents_of(c).values()}
        for t in by_node.values():
            for p in t["prereqs"]:
                back = [q["node_id"] for q in by_node[p["node_id"]]["prereqs"]]
                assert t["node_id"] not in back, (cls, t["key"])


def _with_edges(class_tables, decode_rules, cls, *pairs):
    """Classe décodée avec des arêtes suffisantes ajoutées (gauche, droite)."""
    tables = {name: list(rows) for name, rows in class_tables.items()}
    model = next(e for e in tables["TraitEdge"] if int(e["Type"]) == 2)
    top = max(int(e["ID"]) for e in tables["TraitEdge"])
    added = [dict(model, ID=top + i + 1, LeftTraitNodeID=a, RightTraitNodeID=b) for i, (a, b) in enumerate(pairs)]
    tables["TraitEdge"] = [*tables["TraitEdge"], *added]
    c = decode_classes(tables, decode_rules, LOCAL_VERSION)["classes"][cls]
    return {x["node_id"]: x for x in talents_of(c).values()}, c


def _chain(doc):
    """(classe, t, source) : t n'a que source pour prérequis, et source a elle-même un seul prérequis (comme Bestial
    Wrath, Intimidation et Bestial Swiftness)."""
    for cls, c in doc["classes"].items():
        by_node = {x["node_id"]: x for x in talents_of(c).values()}
        for t in by_node.values():
            if len(t["prereqs"]) == 1 and len(by_node[t["prereqs"][0]["node_id"]]["prereqs"]) == 1:
                return cls, t, t["prereqs"][0]["node_id"]
    raise AssertionError("aucune chaîne de deux prérequis")


def test_synthetic_back_edge_is_dropped(doc, class_tables, decode_rules):
    cls, t, source = _chain(doc)
    by_node, c = _with_edges(class_tables, decode_rules, cls, (t["node_id"], source))  # retour : circulaire
    assert t["node_id"] not in [p["node_id"] for p in by_node[source]["prereqs"]]
    assert [p["node_id"] for p in by_node[t["node_id"]]["prereqs"]] == [source]
    assert (t["node_id"], source) in {(e["from_node"], e["to_node"]) for e in c["dropped_edges"]}


def test_synthetic_real_alternative_is_kept(doc, class_tables, decode_rules):
    cls, t, source = _chain(doc)
    other = next(
        x
        for x in talents_of(doc["classes"][cls]).values()
        if x["node_id"] not in (t["node_id"], source) and not x["prereqs"] and x["tree"] == t["tree"]
    )
    by_node, c = _with_edges(class_tables, decode_rules, cls, (other["node_id"], t["node_id"]))  # vraie voie
    assert {p["node_id"] for p in by_node[t["node_id"]]["prereqs"]} == {source, other["node_id"]}
    assert [e for e in c["dropped_edges"] if e["to_node"] == t["node_id"]] == []


def test_synthetic_closed_cycle_stops_the_decode(doc, class_tables, decode_rules):
    a, b = [x for x in talents_of(doc["classes"]["Rogue"]).values() if not x["prereqs"]][:2]
    with pytest.raises(DataSchemaError):  # deux talents qui n'ont que l'autre pour prérequis : jamais deviné
        _with_edges(class_tables, decode_rules, "Rogue", (a["node_id"], b["node_id"]), (b["node_id"], a["node_id"]))


# --- Décodage : positions du Démoniste relevées en jeu (CLS1) ----------------------------------------------------


def test_warlock_positions_observed_in_game(doc, decode_rules):
    observed = specs(decode_rules, "observed_positions")["Warlock"]
    assert set(observed) == {"improvedLifeTap", "amplifyCurse"}
    warlock = doc["classes"]["Warlock"]
    t = talents_of(warlock)
    for key, pos in observed.items():
        assert SURVEY_DATE in pos["source"] and pos["certainty"] == "certain"
        assert (t[key]["tier"], t[key]["col"]) == (pos["tier"], pos["col"])
        assert t[key]["tree"] == "Affliction"
    assert warlock["unresolved_nodes"] == []


# --- Données installées ------------------------------------------------------------------------------------------


def test_installed_trees_follow_the_survey(installed, decode_rules):
    for cls, spec in specs(decode_rules, "observed_absent").items():
        for key in spec:
            assert key not in talents_of(installed[cls])
    hunter = talents_of(installed["Hunter"])
    by_node = {x["node_id"]: x for x in hunter.values()}
    assert [by_node[p["node_id"]]["key"] for p in hunter["intimidation"]["prereqs"]] == ["bestialSwiftness"]
    warlock = talents_of(installed["Warlock"])
    for key, pos in specs(decode_rules, "observed_positions")["Warlock"].items():
        assert (warlock[key]["tier"], warlock[key]["col"]) == (pos["tier"], pos["col"])
        assert warlock[key]["position"]["certainty"] == "certain"
    assert installed["Warlock"]["unresolved_nodes"] == []


# --- Légalité (registre G3) --------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def gd(tmp_path_factory):
    from conftest import isolated_deps

    return build_game_data(load_version(isolated_deps(tmp_path_factory.mktemp("gd"))))


def test_intimidation_without_bestial_swiftness_is_illegal(gd):
    hunter = gd.classes["Hunter"]
    t = {x["key"]: x for tree in hunter.trees for x in tree["talents"]}
    wrath, intimidation, swift = t["bestialWrath"], t["intimidation"], t["bestialSwiftness"]
    need = gd.constants.talents.points_per_tier * (wrath["tier"] - 1)
    pts, spent = {}, 0
    for x in t.values():
        if spent >= need:
            break
        ok = x["tree"] == wrath["tree"] and x["tier"] and x["tier"] < wrath["tier"] and not x["prereqs"]
        if ok and x["key"] != swift["key"]:
            pts[x["key"]] = x["max"]
            spent += x["max"]
    assert spent >= need  # prémisse : l'arbre s'ouvre sans Bestial Swiftness
    pts[intimidation["key"]] = intimidation["max"]
    pts[wrath["key"]] = wrath["max"]
    errors = check_class_build(hunter, gd.constants.talents, pts, 60)
    assert any(intimidation["name"] in e and swift["name"] in e and "exige" in e for e in errors)
    pts[swift["key"]] = swift["max"]
    errors = check_class_build(hunter, gd.constants.talents, pts, 60)
    assert not [e for e in errors if "exige" in e]


def test_talents_check_of_intimidation_names_bestial_swiftness(make_deps, gd):
    t = {x["key"]: x for tree in gd.classes["Hunter"].trees for x in tree["talents"]}
    out = check_talents(make_deps(), "Chasseur", {"intimidation": 1}, 60)
    assert out["legal"] is False
    assert any(t["bestialSwiftness"]["name"] in e and " ou " not in e for e in out["errors"] if "exige" in e)


# --- Talents Forever : témoin en jeu, certitude, Chasseur et Démoniste ------------------------------------------


@pytest.fixture
def deps(tmp_path, make_deps):
    root = tmp_path / "wow"
    write_addon(root, CLASSES)
    return make_deps(wow_dir=root)


@pytest.fixture
def addon(deps):
    loaded = load_addon(deps)
    assert loaded is not None
    return loaded


def test_fixed_builds_carry_their_source():
    assert {name for name, c in CASES.items() if c["verified_in_game"]} == {"leveling-20", "leveling-20-current"}
    for c in CASES.values():
        assert c["source"]
        assert sum(c["talents"].values()) == len(c["order"]) or not c["order"]
    for name in ("leveling-20", "leveling-20-current"):
        assert SURVEY_DATE in CASES[name]["source"] and "relevé en jeu" in CASES[name]["source"]
    assert CASES["leveling-20"]["verified_in_game"] == "import_export"


@pytest.mark.parametrize("name", ["leveling-20", "leveling-20-current"])
def test_in_game_witnesses_encode_and_read_back(addon, deps, name):
    case = CASES[name]
    block = export_build(addon, "Mage", case["level"], case["talents"], case["order"])
    assert block["status"] == "ok" and block["code"] == case["expected_code"]
    back = decode_code(addon, deps, "https://talentsforever.com/" + case["expected_code"] + "?a")
    assert back["talents"] == case["talents"] and back["order"] == case["order"]
    assert back["legal"] is True


def test_v6_format_is_certain_after_the_in_game_test(addon, deps):
    case = CASES["leveling-20"]
    block = export_build(addon, "Mage", case["level"], case["talents"], case["order"])
    assert block["certainty"] == "certain"
    prov = block["provenance"]
    assert prov["verified_in_game"] is True
    assert SURVEY_DATE in prov["verified_in_game_source"] and "v6" in prov["verified_in_game_source"]
    back = decode_code(addon, deps, case["expected_code"])
    assert back["certainty"] == "certain" and back["provenance"]["certainty"] == "certain"


def test_other_generation_is_never_certain(tmp_path, make_deps):
    root = tmp_path / "wow"
    write_addon(root, CLASSES, mutate=lambda doc: doc.update(codeVersion="7"))
    loaded = load_addon(make_deps(wow_dir=root))
    case = CASES["leveling-20"]
    block = export_build(loaded, "Mage", case["level"], case["talents"], case["order"])
    assert block["code"] is None and block["certainty"] is None
    assert block["provenance"]["verified_in_game"] is False


def test_hunter_and_warlock_are_exportable(addon):
    report = crosscheck_report(addon)
    for name in ("Hunter", "Warlock"):
        assert addon.layouts[name].exportable, name
        assert report["classes"][name]["export"] == "possible"
        assert addon.layouts[name].unmatched == ()
    assert report["totals"]["unmatched"] == 0 and report["totals"]["prereq"] == 0


def test_hunter_build_exports_and_reads_back(addon, deps):
    block = export_build(addon, "Hunter", HUNTER_EXAMPLE["level"], HUNTER_EXAMPLE["talents"], None)
    assert block["status"] == "ok" and block["code"].startswith(f"hunter/{HUNTER_EXAMPLE['level']}/")
    back = decode_code(addon, deps, block["code"])
    assert back["class"] == "Hunter" and back["talents"] == HUNTER_EXAMPLE["talents"]
    assert back["legal"] is True


def test_warlock_build_with_the_observed_talents_exports(addon, deps, installed):
    t = talents_of(installed["Warlock"])
    pts = {"improvedLifeTap": t["improvedLifeTap"]["max"]}
    block = export_build(addon, "Warlock", 20, pts, None)
    assert block["status"] == "ok"
    back = decode_code(addon, deps, block["code"])
    assert back["talents"] == pts and back["legal"] is True
    both = {**pts, "amplifyCurse": t["amplifyCurse"]["max"]}
    assert export_build(addon, "Warlock", 60, both, None)["status"] == "ok"


# --- Fixtures et cas d'évaluation sans code stocké d'un build calculé -------------------------------------------

CODE = re.compile(r"\b[a-z]+/\d{1,2}/[0-9a-z]*-[0-9a-z-]*-\d\b")


def test_extraction_script_never_writes_computed_builds():
    script = (REPO_ROOT / "scripts" / "extract_talents_forever_fixture.py").read_text(encoding="utf-8")
    assert "build_report" not in script and "MAGE_CASES" not in script
    assert not CODE.search(script)


def test_eval_cases_never_store_a_code():
    for path in EVALS.rglob("*.md"):
        assert not CODE.search(path.read_text(encoding="utf-8")), path


def test_link_case_compares_to_the_code_of_the_tool():
    grader = (EVALS / "build-lien-talents-forever" / "graders" / "code-outil.md").read_text(encoding="utf-8")
    assert grader.startswith("---\ntype: llm\n---")
    for words in ("forever_build", "export.talents_forever", "code", "/tf import", "même exécution"):
        assert words in grader, words
