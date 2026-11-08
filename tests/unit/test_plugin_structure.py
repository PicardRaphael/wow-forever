"""Structure du plugin Claude Code (T06, décisions D1, D2, D3, D4, D5) : manifeste, marketplace locale, serveur MCP,
hooks, skills et sous-agents ; aucun chiffre de jeu ni aucune statusLine dans le plugin.

Formes vérifiées sur place au bloc A (annexe de tasks/T06-plan.md) : noms `forever:<skill>` et
`mcp__plugin_forever_forever__<outil>`, hooks en forme `command` (Git Bash), défauts `${VAR:-…}`."""

import asyncio
import json
import re

import pytest
import yaml
from conftest import REPO_ROOT
from mcp import Client

from forever.cli import build_parser
from forever.hooks import GAME_NUMBER, NUMBERS_MARKER
from forever.mcp_server import build_server

PLUGIN = REPO_ROOT / "plugin"
SKILLS = (
    "forever-router",
    "forever-leveling",
    "forever-mage",
    "forever-pvp",
    "forever-builds",
    "forever-familiers",
    "forever-donjons",
    "forever-routes",
    "forever-economie",
)
AGENTS = ("forever-web-researcher", "forever-sim-runner")
MCP_PREFIX = "mcp__plugin_forever_forever__"
# Domaines non couverts à ce stade et tranche qui les couvrira (docs/ROADMAP.md, partie 3, état du 2026-10-22). Les
# tranches caduques depuis les décisions 288 à 297 (T04d faite, T05b, T09, moteurs de classe CH1 à DR1) ne sont plus
# citées : au 60, wowsims/forever calcule toutes les classes ; dessous, SIM2 (simulateur de la communauté) et CM1.
UNCOVERED_TRANCHES = (
    "PV2",
    "LG1",
    "LG2",
    "MT1",
    "RP1",
    "EC1",
    "T07",
    "T10",
    "T11",
    "AN1",
    "AN2",
    "SIM2",
    "CM1",
)
OBSOLETE_TRANCHES = ("T04d", "T05b", "T09", "CH1", "DE1", "PA1", "GU1", "VO1", "PR1", "DR1")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def frontmatter(path):
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    assert m, f"{path} : frontmatter absent"
    return yaml.safe_load(m.group(1)), m.group(2)


def plugin_texts():
    return {p: p.read_text(encoding="utf-8") for p in PLUGIN.rglob("*") if p.is_file() and "results" not in p.parts}


@pytest.fixture(scope="module")
def tool_names(tmp_path_factory):
    from conftest import DATA_DIR, NOW, REGISTRY_PATH, FakeHttp

    from forever.config import Deps

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


def test_marketplace_declares_the_plugin():
    m = read_json(REPO_ROOT / ".claude-plugin" / "marketplace.json")
    assert m["name"] == "wow-forever"
    assert m["owner"]["name"]
    assert m["description"]
    (entry,) = m["plugins"]
    assert entry["name"] == "forever"
    assert entry["source"] == "./plugin"
    assert (REPO_ROOT / entry["source"] / ".claude-plugin" / "plugin.json").is_file()


def test_plugin_manifest():
    p = read_json(PLUGIN / ".claude-plugin" / "plugin.json")
    assert p["name"] == "forever"
    assert p["description"]
    assert p["author"]["name"]
    # T06b (D8) : version semver, relevée à chaque changement de plugin/ (test_plugin_version.py).
    assert "version" in p


def test_mcp_server_runs_forever_mcp_from_the_repo():
    servers = read_json(PLUGIN / ".mcp.json")["mcpServers"]
    assert set(servers) == {"forever"}
    s = servers["forever"]
    assert s["command"] == "uv"
    args = s["args"]
    assert args[:1] == ["run"]
    assert args[-2:] == ["forever", "mcp"]
    project = args[args.index("--project") + 1]
    assert project == "${FOREVER_HOME:-${CLAUDE_PLUGIN_ROOT}/..}"
    assert "env" not in s  # le profil passe par l'environnement hérité (forever/profile.py)


def hook_commands(event):
    hooks = read_json(PLUGIN / "hooks" / "hooks.json")["hooks"]
    return [h for group in hooks[event] for h in group["hooks"]]


@pytest.mark.parametrize(("event", "sub"), [("SessionStart", "session-start"), ("Stop", "check-numbers")])
def test_hooks_call_the_cli_subcommands_quietly(event, sub):
    (h,) = hook_commands(event)
    assert h["type"] == "command"
    assert "args" not in h  # forme exec : ${VAR:-…} n'y est pas développé (bloc A)
    cmd = h["command"]
    assert f"forever hook {sub}" in cmd
    assert "${FOREVER_HOME:-${CLAUDE_PLUGIN_ROOT}/..}" in cmd
    assert "pyproject.toml" in cmd  # garde : aucun message d'erreur hors du dépôt ni sans FOREVER_HOME
    assert "--no-sync" in cmd  # pas de synchronisation (réseau) dans un hook
    assert cmd.rstrip().endswith("exit 0")
    assert 0 < h["timeout"] <= 10
    assert build_parser().parse_args(["hook", sub]).hook_name == sub


def test_only_two_hooks():
    hooks = read_json(PLUGIN / "hooks" / "hooks.json")["hooks"]
    assert set(hooks) == {"SessionStart", "Stop"}


@pytest.mark.parametrize("name", SKILLS)
def test_skill_frontmatter_and_size(name):
    path = PLUGIN / "skills" / name / "SKILL.md"
    meta, _ = frontmatter(path)
    assert meta["name"] == name
    assert 100 <= len(meta["description"]) <= 1024
    assert len(path.read_text(encoding="utf-8").splitlines()) < 200


def test_skill_descriptions_carry_trigger_words():
    desc = {n: frontmatter(PLUGIN / "skills" / n / "SKILL.md")[0]["description"].lower() for n in SKILLS}
    assert "forever" in desc["forever-router"]
    for word in ("retail", "classic", "programmation"):
        assert word in desc["forever-router"]  # ce qui ne doit pas déclencher
    for word in ("niveau", "xp", "respec", "zone", "donjon"):
        assert word in desc["forever-leveling"]
    for word in ("mage", "talent", "build", "givre", "feu", "arcanes"):
        assert word in desc["forever-mage"]
    for word in ("pvp", "contrôle", "affrontement", "recharge", "rendements décroissants"):
        assert word in desc["forever-pvp"]
    for word in ("build", "classe", "légal", "communauté", "talents"):
        assert word in desc["forever-builds"]
    for word in (
        "familier",
        "chasseur",
        "apprivois",
        "capacité",
        "rang",
        "entraînement",
        "beast training",
        "loyauté",
        "régime",
        "famille",
        "retail",
    ):
        assert word in desc["forever-familiers"], word
    for word in ("donjon", "boss", "butin", "taux", "quête", "prérequis", "retail"):  # DJ1
        assert word in desc["forever-donjons"], word
    for word in ("feuille de route", "restedxp", "quête", "niveau", "donjon", "retail"):  # RX1
        assert word in desc["forever-routes"], word
    for word in ("hôtel des ventes", "prix", "métier", "recette", "réputation", "champ", "pnj", "vendeur", "objet"):
        assert word in desc["forever-economie"], word  # AMI7b
    assert "retail" in desc["forever-economie"]


def test_router_maps_skills_and_uncovered_domains():
    _, body = frontmatter(PLUGIN / "skills" / "forever-router" / "SKILL.md")
    assert "forever-leveling" in body and "forever-mage" in body
    assert "forever-pvp" in body and "forever-builds" in body
    assert 'kind="pvp"' in body and 'kind="build_check"' in body
    assert 'kind="pets"' in body and "forever-familiers" in body
    assert 'kind="dungeons"' in body and 'kind="dungeon_item"' in body and "forever-donjons" in body  # DJ1
    assert "forever_route" in body and "forever-routes" in body  # RX1
    assert "format-reponse.md" in body
    assert "forever_status" in body
    for tranche in UNCOVERED_TRANCHES:
        assert re.search(rf"\b{tranche}\b", body), tranche
    for tranche in OBSOLETE_TRANCHES:  # caduques ou faites : plus jamais annoncées au joueur
        assert not re.search(rf"\b{tranche}\b", body), tranche


def test_router_describes_what_is_covered_today():
    """Leveling couvert pour toutes les classes, sources par classe, moteur du Mage gelé sous le 60, wowsims au 60."""
    _, body = frontmatter(PLUGIN / "skills" / "forever-router" / "SKILL.md")
    lowered = body.lower()
    assert "gelé" in lowered and "wowsims/forever" in body and "forever_simulate" in body
    assert "toutes les classes" in lowered and "forever companion" in lowered and "talents forever" in lowered
    assert "leveling" in lowered


@pytest.mark.parametrize(
    "name",
    [
        "forever-leveling",
        "forever-mage",
        "forever-pvp",
        "forever-builds",
        "forever-familiers",
        "forever-donjons",
        "forever-routes",
        "forever-economie",
    ],
)
def test_domain_skills_use_the_response_format(name):
    _, body = frontmatter(PLUGIN / "skills" / name / "SKILL.md")
    assert "format-reponse.md" in body


def test_response_format():
    text = (PLUGIN / "skills" / "forever-router" / "format-reponse.md").read_text(encoding="utf-8")
    for heading in ("Certitude", "Hypothèses", "Angles morts", "Provenance"):
        assert heading in text
    assert "je ne sais pas" in text.lower()
    assert "français" in text and "courte" in text  # D3
    # pied de réponse fixe, cherché par les correcteurs de l'évaluation ; révision des données (T06b)
    assert re.search(r"Certitude : .* · Version .* · Fraîcheur", text)
    assert "r<provenance.data_revision>" in text


def test_player_data_rule():
    """T06b (D6) : donnée personnelle lue dans le profil, demandée avant le calcul sinon, jamais un défaut muet."""
    text = (PLUGIN / "skills" / "forever-router" / "format-reponse.md").read_text(encoding="utf-8")
    assert "## Données du joueur" in text
    section = text.split("## Données du joueur", 1)[1].split("\n## ", 1)[0]
    assert "forever_player_profile" in section
    assert "forever profile set" in section
    assert "avant" in section and "inputs" in section and "Profil :" in section
    for name in SKILLS:
        _, body = frontmatter(PLUGIN / "skills" / name / "SKILL.md")
        assert "forever_player_profile" in body or name == "forever-mage", name
    _, leveling = frontmatter(PLUGIN / "skills" / "forever-leveling" / "SKILL.md")
    assert "garde le défaut de l'outil" not in leveling
    assert "next_step" in leveling


def test_simulate_race_is_asked_never_taken_from_a_preset():
    """Demande du 2026-10-22 : la race passée à forever_simulate vient de la question ou du profil, jamais de la race
    par défaut d'un préréglage ; sinon elle est demandée avant l'appel. Préréglage sans équipement : jamais cité."""
    text = (PLUGIN / "skills" / "forever-router" / "format-reponse.md").read_text(encoding="utf-8")
    section = text.split("## Données du joueur", 1)[1].split("\n## ", 1)[0]
    assert "forever_simulate" in section and "préréglage" in section and "demande" in section
    _, router = frontmatter(PLUGIN / "skills" / "forever-router" / "SKILL.md")
    assert "items" in router and "sans équipement" in router


def test_measured_comparison_rule():
    """T06b (D6, D7) : Monte Carlo contre Monte Carlo avec intervalle ; « non départagé » quand il contient zéro."""
    text = (PLUGIN / "skills" / "forever-router" / "format-reponse.md").read_text(encoding="utf-8")
    assert "## Comparer deux options" in text
    section = text.split("## Comparer deux options", 1)[1].split("\n## ", 1)[0]
    assert "non départagé par le calcul" in section
    assert "analytique" in section and "Monte Carlo" in section and "intervalle" in section
    assert "non modélisé" in section


@pytest.mark.parametrize("name", AGENTS)
def test_agent_frontmatter(name):
    meta, body = frontmatter(PLUGIN / "agents" / f"{name}.md")
    assert meta["name"] == name
    assert meta["description"]
    assert body.strip()


def test_web_researcher_tools_and_labels():
    meta, body = frontmatter(PLUGIN / "agents" / "forever-web-researcher.md")
    assert {t.strip() for t in meta["tools"].split(",")} == {"WebSearch", "WebFetch"}
    for label in ("officielle", "communautaire", "simulateur"):
        assert label in body
    assert "forever/data" in body  # rien n'y entre


def test_sim_runner_tools_are_forever_tools(tool_names):
    meta, _ = frontmatter(PLUGIN / "agents" / "forever-sim-runner.md")
    tools = {t.strip() for t in meta["tools"].split(",")}
    assert tools and all(t.startswith(MCP_PREFIX) for t in tools)
    assert {t.removeprefix(MCP_PREFIX) for t in tools} <= tool_names
    assert "forever_sim_leveling" in {t.removeprefix(MCP_PREFIX) for t in tools}  # RB1 : plus de forever_build


def test_tools_cited_by_the_plugin_exist(tool_names):
    cited = set()
    for path, text in plugin_texts().items():
        if path.suffix == ".md" and "evals" not in path.parts:
            cited |= set(re.findall(r"\bforever_[a-z_]+\b", text))
    assert cited
    assert cited <= tool_names


def test_no_game_number_marker_or_statusline_in_the_plugin():
    for path, text in plugin_texts().items():
        assert not GAME_NUMBER.search(text), f"chiffre de jeu dans {path}"
        assert NUMBERS_MARKER not in text, path
        assert "statusLine" not in text and "statusline" not in text.lower(), path
    assert not (PLUGIN / "settings.json").exists()


# --- PV1, blocs F et G ----------------------------------------------------------------------------------------------


def router_section(title):
    _, body = frontmatter(PLUGIN / "skills" / "forever-router" / "SKILL.md")
    assert title in body, title
    return body.split(title, 1)[1].split("\n## ", 1)[0].split("\n### ", 1)[0]


def test_router_uncovered_table_drops_pv1_rows():
    table = router_section("## 3. Domaines non couverts")
    assert "PvP : classes adverses" not in table and "Profil rempli automatiquement" not in table
    assert "PV1" not in table  # tout ce que PV1 couvre est sorti de la table
    assert "PV2" in table


def test_router_missing_data_and_not_built_instructions():
    missing = router_section("### Donnée manquante")
    for word in ("addon", "forever-web-researcher", "CurseForge", "Wago", "foreverchanges.pro"):
        assert word in missing, word
    assert "installe" in missing and "jamais" in missing  # rien téléchargé ni installé par l'agent
    built = router_section("### Pas encore construit")
    for word in ("objets", "réputations", "champs de bataille", "source", "tranche"):
        assert word in built, word
    other = router_section("### Classe pas encore calculée")
    assert 'kind="build_check"' in other and "légalité" in other


def test_router_proposes_the_profile_import():
    _, body = frontmatter(PLUGIN / "skills" / "forever-router" / "SKILL.md")
    assert "forever profile import" in body


def test_pvp_skill_states_no_live_cooldown_tracking():
    _, body = frontmatter(PLUGIN / "skills" / "forever-pvp" / "SKILL.md")
    lowered = body.lower()
    assert "aucun suivi en direct" in lowered and "journal de combat" in lowered
    assert "missing" in body and 'kind="pvp"' in body and "forever_player_profile" in body
    addon = (REPO_ROOT / "docs" / "ADDON.md").read_text(encoding="utf-8").lower()
    assert "aucun suivi en direct des recharges adverses" in addon


def test_builds_skill_checks_community_builds():
    _, body = frontmatter(PLUGIN / "skills" / "forever-builds" / "SKILL.md")
    for word in ('kind="tf_popular"', "forever-web-researcher", 'kind="build_check"', "légal"):
        assert word in body, word
    assert "forever_build" not in body  # RB1 (décision 299) : le Mage suit le chemin des autres classes


def test_ch0_is_covered_and_the_pet_choice_waits_for_sim2():
    """CH0 : le savoir des familiers est couvert (aucune ligne « non couvert » ne cite CH0) ; le choix du familier
    chiffré par contexte attend un simulateur sous le 60 (SIM2)."""
    _, body = frontmatter(PLUGIN / "skills" / "forever-router" / "SKILL.md")
    uncovered = body.split("## 3. Domaines non couverts", 1)[1].split("\n## 4.", 1)[0]
    assert not re.search(r"\bCH0\b", uncovered)
    hunter = [line for line in uncovered.splitlines() if "Chasseur" in line]
    assert hunter and any("familier" in line and "SIM2" in line for line in hunter)


def test_familiers_skill_states_its_limits():
    _, body = frontmatter(PLUGIN / "skills" / "forever-familiers" / "SKILL.md")
    assert 'kind="pets"' in body and "forever_player_profile" in body
    for words in ("zone", "niveau", "SIM2", "Forever Bestiary", "relevés de joueurs"):
        assert words in body, words


# --- AMI7b : sources tierces (Everloot) -----------------------------------------------------------------------------

EVERLOOT_TOOLS = (
    "market_value",
    "auction_history",
    "profession_path",
    "recipe_thresholds",
    "item_page",
    "npc_page",
    "vendor_page",
    "search_knowledge",
)


def test_router_routes_third_party_domains_to_everloot():
    """Hôtel des ventes, métiers, réputations, champs de bataille, PNJ, vendeurs, objets : outils forever d'abord,
    Everloot ensuite (tiers, daté, certitude au mieux `suppose`, ligne « More: » recopiée), « je ne sais pas » sinon."""
    _, body = frontmatter(PLUGIN / "skills" / "forever-router" / "SKILL.md")
    assert "forever-economie" in body and "Everloot" in body
    for tool in ("market_value", "profession_path", "search_knowledge", "vendor_page", "npc_page"):
        assert f"mcp__everloot__{tool}" in body, tool
    third = router_section("## 2c. Sources tierces")
    for word in ("forever_", "d'abord", "tiers", "suppose", "More:", "je ne sais pas", "ToolSearch"):
        assert word in third, word
    for tranche in ("EC1", "MT1", "RP1", "PV2"):  # tranche du projet toujours citée
        assert re.search(rf"\b{tranche}\b", third), tranche


def test_uncovered_table_drops_domains_now_answered_by_everloot():
    table = router_section("## 3. Domaines non couverts")
    for row in ("| Réputations |", "| Hôtel des ventes", "| Métiers (au-delà"):
        assert row not in table, row
    assert "Everloot" in table  # dit tiers sous la table


def test_router_description_no_longer_lists_everloot_domains_as_uncovered():
    meta, _ = frontmatter(PLUGIN / "skills" / "forever-router" / "SKILL.md")
    desc = meta["description"].lower()
    assert "everloot" in desc and "hôtel des ventes" in desc
    uncovered = desc.split("ne couvre pas encore", 1)[1]
    for word in ("hôtel des ventes", "réputations", "métiers"):
        assert word not in uncovered.split(")", 1)[0], word


def test_economie_skill_labels_everloot_and_forbids_other_versions():
    _, body = frontmatter(PLUGIN / "skills" / "forever-economie" / "SKILL.md")
    for tool in EVERLOOT_TOOLS:
        assert f"mcp__everloot__{tool}" in body, tool
    for word in ("tiers", "suppose", "More:", "je ne sais pas", 'version="forever"', "forever_lookup", "ToolSearch"):
        assert word in body, word
    assert 'kind="battlegrounds"' not in body  # aucune lecture des champs de bataille dans le dépôt (PVP5)


def test_response_format_has_the_third_party_rule():
    text = (PLUGIN / "skills" / "forever-router" / "format-reponse.md").read_text(encoding="utf-8")
    assert "## Sources tierces (Everloot)" in text
    section = text.split("## Sources tierces (Everloot)", 1)[1].split("\n## ", 1)[0]
    for word in ("Source : Everloot", "suppose", "More:", "date"):
        assert word in section, word


def test_battlegrounds_gap_is_an_open_question():
    text = (REPO_ROOT / "docs" / "OPEN_QUESTIONS.md").read_text(encoding="utf-8")
    pvp5 = text.split("**PVP5", 1)[1].split("\n- **", 1)[0]
    assert "2026-11-08" in pvp5 and "Everloot" in pvp5
