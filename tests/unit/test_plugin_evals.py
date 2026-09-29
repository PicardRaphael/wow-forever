"""Suite d'évaluation du plugin (T06, décisions D6 et D10), contrôlée sans modèle : cas, correcteurs, outils cités,
exclusion des résultats, script de rapport sur un résultat synthétique (tests/fixtures/plugin_eval/)."""

import asyncio
import importlib.util
import json
import re

import pytest
import yaml
from conftest import DATA_DIR, FIXTURES, NOW, REGISTRY_PATH, REPO_ROOT, FakeHttp
from mcp import Client

from forever.config import Deps
from forever.hooks import GAME_NUMBER, NUMBERS_MARKER
from forever.mcp_server import build_server

EVALS = REPO_ROOT / "plugin" / "evals"
MCP_PREFIX = "mcp__plugin_forever_forever__"
POSITIVE_COUNTS = {
    "profil": 2,
    "talent": 6,
    "build": 6,
    "respec": 4,
    "zone": 4,
    "generale": 2,
    "personnelle": 2,
    "mecanique": 5,
    "leveling": 3,
    "hors-perimetre": 3,
}
NEGATIVE_CATEGORIES = ("wow-autre", "autre-jeu", "programmation")
POSITIVE_GRADERS = {"skill", "outil", "chiffres", "certitude", "provenance"}


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def front(path):
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
    assert m, path
    return yaml.safe_load(m.group(1)), m.group(2).strip()


def cases():
    return sorted(p for p in EVALS.iterdir() if p.is_dir() and p.name not in ("results", "mocks"))


def graders(case):
    return {p.stem: front(p) for p in (case / "graders").glob("*.md")}


@pytest.fixture(scope="module")
def tool_names(tmp_path_factory):
    deps = Deps(
        data_dir=DATA_DIR,
        registry_path=REGISTRY_PATH,
        cache_dir=tmp_path_factory.mktemp("cache"),
        http_get=FakeHttp.failing(),
        now=lambda: NOW,
    )

    async def go():
        async with Client(build_server(deps)) as client:
            return {t.name for t in (await client.list_tools()).tools}

    return asyncio.run(go())


# --- Suite ---------------------------------------------------------------------------------------------------------


def test_fifty_seven_cases_thirty_seven_positive_twenty_negative():
    polarity = [front(c / "prompt.md")[0]["tags"][0] for c in cases()]
    # T06b : talent-niveau-22 et deux cas à profil vide ; 2026-09-29 : deux questions générales, deux personnelles.
    assert len(polarity) == 57
    assert polarity.count("positif") == 37 and polarity.count("negatif") == 20


def test_empty_profile_cases():
    """T06b (demande du 2026-09-29) : la suite tourne avec un profil rempli (EVAL_FOREVER_PROFILE, fixture
    tests/fixtures/plugin_eval/profile-rempli.json) ; deux cas pointent vers un profil absent et attendent la question."""
    named = [c for c in cases() if front(c / "prompt.md")[0]["tags"] == ["positif", "profil"]]
    assert [c.name for c in named] == ["profil-vide-leveling-18", "profil-vide-zone-18"]
    for c in named:
        meta, _ = front(c / "prompt.md")
        assert set(meta["env"]) == {"EVAL_FOREVER_PROFILE"}
        assert not (REPO_ROOT / meta["env"]["EVAL_FOREVER_PROFILE"]).exists()
        g = graders(c)
        assert g["outil"][0]["tool"] == MCP_PREFIX + "forever_player_profile"
        assert g["demande-la-donnee"][0]["type"] == "llm" and "forever profile set" in g["demande-la-donnee"][1]
    profile = json.loads((FIXTURES / "plugin_eval" / "profile-rempli.json").read_text(encoding="utf-8"))
    assert profile["active"] in profile["characters"]


def test_talent_level_22_case():
    """T06b (D7) : prochain talent depuis un build actuel écrit en toutes lettres ; juge « mesuré et modélisé »."""
    case = EVALS / "talent-niveau-22"
    meta, question = front(case / "prompt.md")
    assert meta["tags"] == ["positif", "talent"]
    assert "22" in question and "Givre" in question
    g = graders(case)
    assert set(g) == POSITIVE_GRADERS | {"mesure-et-modelise"}
    outil = g["outil"][0]
    assert outil["tool"] == MCP_PREFIX + "forever_build"
    assert "current" in outil["input_match"] and re.search(r"level", outil["input_match"])
    assert re.search(outil["input_match"], '{"context": "leveling", "level": 22, "current": {"x": 1}}')
    judge_meta, judge = g["mesure-et-modelise"]
    assert judge_meta["type"] == "llm"
    for words in ("non modélisé", "Monte Carlo", "analytique", "non départagé"):
        assert words in judge, words


RESPEC_AT_ANOTHER_LEVEL = ("respec-feu-vers-givre", "respec-troisieme")


def test_respec_at_another_level_asks_for_the_current_build():
    """Demande du 2026-09-29 : une respec posée à un autre niveau que celui du profil (profil de test au niveau 23) ne se
    conseille pas sans le build actuel ; la bonne réponse le demande (outil attendu : le profil, pas encore le build)."""
    for name in RESPEC_AT_ANOTHER_LEVEL:
        meta, question = front(EVALS / name / "prompt.md")
        assert meta["tags"] == ["positif", "respec"]
        g = graders(EVALS / name)
        assert g["outil"][0]["tool"] == MCP_PREFIX + "forever_player_profile", name
        judge_meta, judge = g["demande-le-build"]
        assert judge_meta["type"] == "llm"
        for words in ("build actuel", "respec", "forever profile set"):
            assert words in judge, (name, words)
    for name in ("respec-build-precis", "respec-leveling-vers-donjon"):
        assert graders(EVALS / name)["outil"][0]["tool"] == MCP_PREFIX + "forever_build", name


def test_general_and_personal_cases():
    """Demande du 2026-09-29 (règle « question personnelle ou générale » de format-reponse.md) : une question générale
    ne lit pas le profil et annonce son hypothèse neutre ; une question personnelle part du personnage actif ; une
    question générale sur une classe pas encore calculée le dit sans rien demander."""
    by_tag = {}
    for c in cases():
        tags = front(c / "prompt.md")[0]["tags"]
        if tags[0] == "positif" and tags[1] in ("generale", "personnelle"):
            by_tag.setdefault(tags[1], []).append(c.name)
    assert by_tag == {
        "generale": ["generale-classe-non-calculee", "generale-mage-raid"],
        "personnelle": ["personnelle-mage-donjon", "personnelle-mage-temps"],
    }
    for name in by_tag["generale"]:
        g = graders(EVALS / name)
        no_profile = g["sans-profil"][0]
        assert no_profile["type"] == "tool_used" and no_profile["tool"] == MCP_PREFIX + "forever_player_profile"
        assert no_profile["min"] == 0 and no_profile["max"] == 0
        assert g["hypothese-neutre"][0]["type"] == "llm"
    raid = graders(EVALS / "generale-mage-raid")
    assert raid["outil"][0]["tool"] == MCP_PREFIX + "forever_build"
    assert re.search(raid["outil"][0]["input_match"], '{"context": "raid", "level": 60}')
    for words in ("hypothèse", "race", "profil"):
        assert words in raid["hypothese-neutre"][1], words
    uncomputed = graders(EVALS / "generale-classe-non-calculee")
    assert uncomputed["outil"][0]["tool"] == MCP_PREFIX + "forever_status"
    assert re.search(uncomputed["non-calcule"][0]["pattern"], "pas encore calculé par le moteur", re.IGNORECASE)
    for words in ("PA1", "PV1", "supposé", "communauté", "source"):
        assert words in uncomputed["hypothese-neutre"][1], words
    for name in by_tag["personnelle"]:
        g = graders(EVALS / name)
        assert g["profil"][0] == {"type": "tool_used", "tool": MCP_PREFIX + "forever_player_profile"}
        assert g["profil-actif"][0]["type"] == "llm" and "profil actif" in g["profil-actif"][1]
        assert re.search(g["outil"][0]["input_match"], '{"level": 23, "race": "Orc"}'), name
    assert graders(EVALS / "personnelle-mage-donjon")["outil"][0]["tool"] == MCP_PREFIX + "forever_build"
    assert graders(EVALS / "personnelle-mage-temps")["outil"][0]["tool"] == MCP_PREFIX + "forever_sim_leveling"


def test_case_names_are_the_directories():
    for c in cases():
        meta, question = front(c / "prompt.md")
        assert "name" not in meta or meta["name"] == c.name
        assert question


def test_positive_categories():
    counts = {}
    for c in cases():
        tags = front(c / "prompt.md")[0]["tags"]
        if tags[0] == "positif":
            counts[tags[1]] = counts.get(tags[1], 0) + 1
    assert counts == POSITIVE_COUNTS


def test_negative_categories():
    counts = dict.fromkeys(NEGATIVE_CATEGORIES, 0)
    for c in cases():
        tags = front(c / "prompt.md")[0]["tags"]
        if tags[0] == "negatif":
            counts[tags[1]] += 1
    assert sum(counts.values()) == 20
    assert all(n >= 4 for n in counts.values()), counts


def test_positive_cases_have_their_expectations(tool_names):
    for c in cases():
        meta, _ = front(c / "prompt.md")
        if meta["tags"][0] != "positif":
            continue
        g = graders(c)
        assert POSITIVE_GRADERS <= set(g), c.name
        skill = g["skill"][0]
        assert skill["type"] == "tool_used" and skill["tool"] == "Skill" and "forever:" in skill["input_match"]
        outil = g["outil"][0]
        assert outil["type"] == "tool_used" and outil["tool"].startswith(MCP_PREFIX)
        assert outil["tool"].removeprefix(MCP_PREFIX) in tool_names, c.name
        chiffres = g["chiffres"][0]
        assert chiffres == {
            "type": "regex",
            "target": "trace",
            "match": "not_contains",
            "pattern": re.escape(NUMBERS_MARKER).replace("\\:", ":"),
        }
        assert re.search(chiffres["pattern"], NUMBERS_MARKER)
        certitude = g["certitude"][0]
        assert certitude["type"] == "regex" and "Certitude" in certitude["pattern"]
        for word in ("Certitude : certain", "Certitude : probable", "Certitude : supposé"):
            assert re.search(certitude["pattern"], word, re.IGNORECASE)
        assert g["provenance"][0]["type"] == "regex"


def test_out_of_scope_cases_expect_i_do_not_know():
    for c in cases():
        meta, _ = front(c / "prompt.md")
        if meta["tags"][:2] != ["positif", "hors-perimetre"]:
            continue
        g = graders(c)
        assert g["je-ne-sais-pas"][0]["type"] == "regex"
        assert re.search(g["je-ne-sais-pas"][0]["pattern"], "Je ne sais pas", re.IGNORECASE)
        assert any(meta_g["type"] == "llm" and body for meta_g, body in g.values())


def test_negative_cases_forbid_forever_skills():
    for c in cases():
        meta, _ = front(c / "prompt.md")
        if meta["tags"][0] != "negatif":
            continue
        (g,) = graders(c).values()
        m = g[0]
        assert m["type"] == "tool_used" and m["tool"] == "Skill"
        assert "forever:" in m["input_match"]
        assert m["min"] == 0 and m["max"] == 0 and m["arm"] == "both"


def test_prompts_have_no_game_number():
    for c in cases():
        _, question = front(c / "prompt.md")
        assert not GAME_NUMBER.search(question), c.name


def test_results_are_neither_versioned_nor_checked():
    assert "plugin/evals/results/" in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    check = load_module("check_game_numbers")
    assert REPO_ROOT / "plugin" / "evals" / "results" in check.EXCLUDED


# --- Script de rapport ---------------------------------------------------------------------------------------------

AGGREGATE = FIXTURES / "plugin_eval" / "aggregate.json"
SYNTHETIC_CASES = {
    "talent-a": {"polarity": "positif", "category": "talent"},
    "talent-b": {"polarity": "positif", "category": "talent"},
    "hors-x": {"polarity": "positif", "category": "hors-perimetre"},
    "neg-a": {"polarity": "negatif", "category": "programmation"},
    "neg-b": {"polarity": "negatif", "category": "autre-jeu"},
}


def test_report_thresholds_of_d10():
    report = load_module("plugin_eval_report")
    assert report.THRESHOLDS == {
        "aiguillage": 0.9,
        "outil": 0.9,
        "chiffres": 1.0,
        "certitude": 1.0,
        "provenance": 0.9,
        "je_ne_sais_pas": 1.0,
    }


def test_report_loads_the_real_suite():
    report = load_module("plugin_eval_report")
    loaded = report.load_cases(EVALS)
    assert len(loaded) == 57
    assert sum(1 for v in loaded.values() if v["polarity"] == "positif") == 37
    assert not any(ch.isdigit() for label in report.LABELS.values() for ch in label)  # compte tiré de la suite
    assert loaded["talent-improved-frostbolt"] == {"polarity": "positif", "category": "talent"}


def test_report_metrics():
    report = load_module("plugin_eval_report")
    m = report.metrics(json.loads(AGGREGATE.read_text(encoding="utf-8")), SYNTHETIC_CASES)
    assert {k: (v["passed"], v["total"]) for k, v in m.items()} == {
        "aiguillage": (4, 5),
        "outil": (2, 3),
        "chiffres": (2, 3),
        "certitude": (3, 3),
        "provenance": (2, 3),
        "je_ne_sais_pas": (1, 1),
    }
    assert {k: v["ok"] for k, v in m.items()} == {
        "aiguillage": False,
        "outil": False,
        "chiffres": False,
        "certitude": True,
        "provenance": False,
        "je_ne_sais_pas": True,
    }


def test_report_flagged_numbers():
    report = load_module("plugin_eval_report")
    flagged = report.flagged_numbers(json.loads(AGGREGATE.read_text(encoding="utf-8")), AGGREGATE.parent)
    assert flagged == [{"case": "talent-b", "numbers": ["18 à 20 points de dégâts", "5 secondes"]}]


def test_report_main_exit_code(tmp_path, capsys):
    report = load_module("plugin_eval_report")
    evals = tmp_path / "evals"
    for name, v in SYNTHETIC_CASES.items():
        (evals / name).mkdir(parents=True)
        (evals / name / "prompt.md").write_text(
            f"---\ntags: [{v['polarity']}, {v['category']}]\n---\n\nQuestion ?\n", encoding="utf-8"
        )
    assert report.main([str(AGGREGATE), "--evals", str(evals)]) == 1
    out = capsys.readouterr().out
    assert "aiguillage" in out and "ÉCHEC" in out
    assert "18 à 20 points de dégâts" in out
