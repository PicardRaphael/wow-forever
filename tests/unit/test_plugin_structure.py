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
SKILLS = ("forever-router", "forever-leveling", "forever-mage")
AGENTS = ("forever-web-researcher", "forever-sim-runner")
MCP_PREFIX = "mcp__plugin_forever_forever__"
# Domaines non couverts à ce stade et tranche qui les couvrira (docs/ROADMAP.md).
UNCOVERED_TRANCHES = (
    "PV1",
    "PV2",
    "DJ1",
    "LG1",
    "MT1",
    "RP1",
    "EC1",
    "T04d",
    "T05b",
    "T07",
    "T09",
    "T10",
    "T11",
    "AN1",
    "AN2",
    # Tranches de classe (remplacent T12, décision 102).
    "PA1",
    "DE1",
    "PR1",
    "CH1",
    "CM1",
    "GU1",
    "VO1",
    "DR1",
)


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


def test_router_maps_skills_and_uncovered_domains():
    _, body = frontmatter(PLUGIN / "skills" / "forever-router" / "SKILL.md")
    assert "forever-leveling" in body and "forever-mage" in body
    assert "format-reponse.md" in body
    assert "forever_status" in body
    for tranche in UNCOVERED_TRANCHES:
        assert re.search(rf"\b{tranche}\b", body), tranche


@pytest.mark.parametrize("name", ["forever-leveling", "forever-mage"])
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
    assert "forever_build" in {t.removeprefix(MCP_PREFIX) for t in tools}


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
