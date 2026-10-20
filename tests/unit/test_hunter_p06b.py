"""Corrections après l'essai en jeu sur un Chasseur réel (décision 242 ; contexte relevé le 2026-10-13 :
`tests/fixtures/bridge/contexts/chasseur15.txt`, Orc de niveau 15 dans The Barrens, talents placés) :

- Familiers : sans capacité nommée, `forever_lookup(kind="pets", zone, level)` rend les bêtes apprivoisables
  maintenant dans la zone puis dans les zones voisines, avec les capacités et les rangs qu'elles enseignent et leurs
  positions (avant : les seules règles, d'où « aucune bête ») ; sans Forever Bestiary, la réponse dit la source qui
  manque et quoi faire, et donne ce que les données du jeu savent (capacités et rangs atteignables, familles) ;
- rangs enseignés : le correctif officiel du 2026-10-01 (rangs trop hauts pour le niveau de la bête) est appliqué
  rang par rang ; un rang au-dessus du niveau de sa bête est marqué, avec le rang corrigé supposé ;
- Leveling pour toutes les classes : zones, quêtes et donjon (indépendants de la classe), build populaire et son
  lien ; pour le Mage, prochain talent calculé et XP par heure ; la consigne dit ce qui n'est pas calculé ;
- jargon : aucune réponse du pont ne cite une commande interne.

Valeurs relues dans les fixtures (`tests/fixtures/bestiary/`, Questie, Talents Forever) et dans `pets.json` ; aucun
chiffre du jeu écrit ici."""

import ast
import asyncio
import json
import shutil
from pathlib import Path

import pytest
from conftest import DATA_DIR, FIXTURES, PRE_70450_VERSION, read_json
from talents_forever_data import write_addon

from forever.bridge.buttons import BUTTONS, visible_buttons
from forever.bridge.context import load_context_data, resolve
from forever.bridge.plans import button_plan, plan_text
from forever.pets import corrected_taught
from forever.pets_lookup import lookup_pets


@pytest.fixture
def make_deps(make_deps_at_pre_70450_version):
    """Données de PRE_70450_VERSION : les arbres de l'addon fabriqué sont ceux de layout.json (conftest)."""
    return make_deps_at_pre_70450_version


PETS = read_json(DATA_DIR / PRE_70450_VERSION / "pets.json")
PET_RULES = read_json(DATA_DIR / PRE_70450_VERSION / "pet_rules.json")
CONTEXTS = FIXTURES / "bridge" / "contexts"
LEVEL = 15


def context(name):
    text = (CONTEXTS / f"{name}.txt").read_text(encoding="utf-8")
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


@pytest.fixture
def wow(tmp_path):
    root = tmp_path / "wow"
    addons = root / "Interface" / "AddOns"
    shutil.copytree(FIXTURES / "bestiary" / "ForeverBestiary", addons / "ForeverBestiary")
    shutil.copytree(FIXTURES / "questie" / "11.38.0", addons / "Questie")
    return root


def bite_levels():
    bite = next(a for a in PETS["abilities"].values() if a["name"]["en"] == "Bite")
    return {r["rank"]: r["level"] for r in bite["ranks"]}


# --- 1. guide de la zone sans capacité nommée ------------------------------------------------------------------


def test_zone_guide_without_a_name_lists_the_tameable_beasts(make_deps, wow):
    out = lookup_pets(make_deps(wow_dir=wow), None, zone="The Barrens", level=LEVEL)
    assert out["kind"] == "pets_guide" and out["target"]["kind"] == "all"
    first = out["zones"][0]
    assert first["requested"] and first["name"]["en"] == "The Barrens"
    beasts = [b for z in out["zones"] for b in z["beasts"]]
    assert beasts, "des bêtes de la fixture sont dans The Barrens à ce niveau"
    assert all(b["tameable_now"] for b in beasts)  # niveau inférieur ou égal au mien
    assert all(b["taught"] or b["family_abilities"] for b in first["beasts"])  # rangs enseignés, sinon de la famille
    assert any(b["coords"] for b in first["beasts"])  # positions


def test_zone_guide_through_the_mcp_tool(make_deps, wow):
    from mcp import Client

    from forever.mcp_server import build_server

    async def go():
        async with Client(build_server(make_deps(wow_dir=wow))) as client:
            result = await client.call_tool("forever_lookup", {"kind": "pets", "zone": "The Barrens", "level": LEVEL})
            return json.loads(result.content[0].text)

    out = asyncio.run(go())
    assert out["kind"] == "pets_guide" and out["zones"][0]["beasts"]


def test_missing_bestiary_is_said_plainly_with_what_to_do(make_deps, tmp_path):
    deps = make_deps(wow_dir=tmp_path / "jeu sans addon")
    for out in (
        lookup_pets(deps, None, zone="The Barrens", level=LEVEL),
        lookup_pets(deps, "Bite", zone="The Barrens", level=LEVEL),
    ):
        assert out["kind"] == "pets_guide"
        missing = out["missing"]
        assert missing["source"] == "Forever Bestiary" and "Interface" in missing["where"]
        assert "installer" in missing["action"].lower()
        known = out["client_only"]
        bite = next(a for a in known["abilities"] if a["name"]["en"] == "Bite")
        reachable = max(r for r, lv in bite_levels().items() if lv <= LEVEL)
        assert bite["highest_rank"] == reachable and bite["families"]


# --- 2. rangs corrigés par le correctif officiel -----------------------------------------------------------------


def test_a_rank_above_the_beast_level_is_marked_with_the_expected_rank():
    levels = bite_levels()
    high = max(levels)
    beast_top = levels[high] - 1  # bête d'un niveau sous celui du rang qu'elle dit enseigner
    fix = PET_RULES["official_fixes"][0]
    out = corrected_taught({"ability": "Bite", "rank": high}, [beast_top - 1, beast_top], PETS, fix)
    expected = max(r for r, lv in levels.items() if lv <= beast_top)
    assert out["above_beast_level"] is True and out["expected_rank"] == expected
    assert out["rank_level"] == levels[high] and out["certainty"] == "suppose"
    assert out["fix"]["date"] == fix["date"] and out["fix"]["source"] == fix["source"]
    ok = corrected_taught({"ability": "Bite", "rank": expected}, [beast_top - 1, beast_top], PETS, fix)
    assert ok["above_beast_level"] is False and ok.get("expected_rank") is None


def test_guide_marks_the_fixture_beast_that_teaches_a_rank_too_high(make_deps, wow):
    out = lookup_pets(make_deps(wow_dir=wow), None, zone="The Barrens", level=LEVEL)
    marked = [t for z in out["zones"] for b in z["beasts"] for t in b["taught"] if t.get("above_beast_level")]
    assert marked and all(t["expected_rank"] is None or t["expected_rank"] < t["rank"] for t in marked)
    notes = " ".join(out["provenance"]["assumptions"])
    assert "rang(s) enseigné(s) au-dessus du niveau de leur bête" in notes
    assert "mes données datent d'avant" not in notes


# --- 3. Leveling pour toutes les classes -------------------------------------------------------------------------


def test_leveling_button_is_shown_for_every_class():
    button = next(b for b in visible_buttons() if b.key == "leveling")
    assert button.classes is None and button.computed_for == ("MAGE",)


@pytest.fixture(scope="module")
def hunter_bench(tmp_path_factory, data_at_pre_70450_version):
    from conftest import NOW, REGISTRY_PATH, FakeHttp

    from forever.config import Deps

    root = tmp_path_factory.mktemp("banc-chasseur")
    wow = root / "wow"
    write_addon(wow, DATA_DIR / PRE_70450_VERSION / "classes.json")
    addons = wow / "Interface" / "AddOns"
    shutil.copytree(FIXTURES / "questie" / "11.38.0", addons / "Questie")
    shutil.copytree(FIXTURES / "bestiary" / "ForeverBestiary", addons / "ForeverBestiary")
    deps = Deps(
        data_dir=data_at_pre_70450_version, registry_path=REGISTRY_PATH, cache_dir=root / "cache", http_get=FakeHttp.failing(),
        now=lambda: NOW, wow_dir=wow, profile_path=root / "profil" / "profile.json",
    )  # fmt: skip
    return deps, load_context_data(deps)


def run_calls(deps, plan):
    from mcp import Client

    from forever.mcp_server import build_server

    async def go():
        async with Client(build_server(deps)) as client:
            out = []
            for call in plan.calls:
                result = await client.call_tool(call.tool, call.args)
                out.append(json.loads(result.content[0].text))
            return out

    return asyncio.run(go())


def test_real_hunter_context_is_recognized(hunter_bench):
    _, data = hunter_bench
    r = resolve(data, context("chasseur15"))
    assert r.class_token == "HUNTER" and r.level == LEVEL and r.zone == "The Barrens" and r.current
    assert not [d for d in r.defects if d.kind in ("classe", "race", "talent")]


def test_hunter_leveling_gives_zones_dungeon_and_popular_build(hunter_bench):
    deps, data = hunter_bench
    plan = button_plan("leveling", resolve(data, context("chasseur15")), data.level_cap)
    assert plan is not None
    # T04d, bloc F : objectifs de leveling (XP par heure par zone et donjon) pour toutes les classes
    assert [c.tool for c in plan.calls] == ["forever_lookup", "forever_lookup", "forever_sim_leveling"]
    assert [c.args["kind"] for c in plan.calls] == ["zones", "tf_popular", "objectives"]
    text = plan_text(plan)
    assert "pas encore calculé" in text and "donjon" in text
    zones, popular, _objectives = run_calls(deps, plan)
    assert zones["zones"] and zones["provenance"]
    assert popular.get("closest") or popular.get("builds")


def test_mage_leveling_adds_the_computed_talent_and_xp_per_hour(hunter_bench):
    _, data = hunter_bench
    plan = button_plan("leveling", resolve(data, context("mage19")), data.level_cap)
    tools = [c.tool for c in plan.calls]
    assert tools == ["forever_lookup", "forever_build", "forever_sim_leveling"]
    assert "XP par heure" in plan_text(plan)


def test_hunter_pets_and_talents_buttons_on_the_real_context(hunter_bench):
    deps, data = hunter_bench
    r = resolve(data, context("chasseur15"))
    pets = button_plan("pets", r, data.level_cap)
    (out,) = run_calls(deps, pets)
    assert out["kind"] == "pets_guide" and out["target"]["kind"] == "all" and out["zones"][0]["beasts"]
    assert "positions" in plan_text(pets) and "missing" in plan_text(pets)
    talents = button_plan("talents", r, data.level_cap)
    results = run_calls(deps, talents)
    assert results[0].get("closest")


# --- 4. jargon -----------------------------------------------------------------------------------------------------


def test_no_bridge_reply_text_names_an_internal_command():
    """Chaînes du code du pont (hors docstrings) : aucune ne cite une commande interne de mise à jour."""
    bridge = Path(__file__).resolve().parents[2] / "forever" / "bridge"
    found = []
    for path in sorted(bridge.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = {
            id(n.body[0].value)
            for n in ast.walk(tree)
            if isinstance(n, ast.Module | ast.FunctionDef | ast.ClassDef | ast.AsyncFunctionDef)
            and n.body
            and isinstance(n.body[0], ast.Expr)
            and isinstance(n.body[0].value, ast.Constant)
        }
        for node in ast.walk(tree):
            text = node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else ""
            if id(node) not in docstrings and ("(forever update" in text or "update --auto)" in text):
                found.append(f"{path.name}:{node.lineno}")
    assert found == []


def test_every_button_question_is_in_player_words():
    from forever.bridge.jargon import internal_jargon

    for b in BUTTONS:
        for text in [b.question, *b.questions.values()]:
            assert internal_jargon(text) == [], (b.key, text)
