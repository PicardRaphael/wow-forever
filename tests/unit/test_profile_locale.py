"""Langue du client au profil et noms cités par les skills (T08c, bloc F, préférence durable de l'utilisateur) :
`game_locale` lu dans `WTF/Config.wtf` (source `client`) ou donné par le joueur (`profile set --game-locale`,
prioritaire), rendu par `forever profile show` et l'outil MCP ; règle « noms du client » dans chaque skill du plugin.

Fixture : `tests/fixtures/wow/WTF/Config.wtf` (voir son README)."""

import json

from conftest import FIXTURES, REPO_ROOT, read_json

from forever.cli import main
from forever.profile import read_profile

WOW = FIXTURES / "wow"
SKILLS = REPO_ROOT / "plugin" / "skills"
RULE = "Noms du client"


def show(deps, capsys):
    code = main(["profile", "show", "--json"], deps)
    out, _ = capsys.readouterr()
    assert code == 0, out
    return json.loads(out)


def test_locale_read_from_the_client_config(make_deps):
    view = read_profile(make_deps(wow_dir=WOW))
    assert view["game_locale"] == {"value": "enUS", "source": "client"}


def test_no_client_and_no_setting_means_unknown(make_deps, tmp_path):
    assert read_profile(make_deps(wow_dir=tmp_path / "absent"))["game_locale"] is None


def test_player_setting_wins_over_the_client(make_deps, capsys):
    deps = make_deps(wow_dir=WOW)
    code = main(["profile", "set", "--game-locale", "frFR", "--json"], deps)
    capsys.readouterr()
    assert code == 0
    data = show(deps, capsys)
    assert data["game_locale"]["value"] == "frFR" and data["game_locale"]["source"] == "joueur"
    assert data["provenance"]["game_version"]


def test_invalid_locale_is_refused(make_deps, capsys):
    deps = make_deps(wow_dir=WOW)
    code = main(["profile", "set", "--game-locale", "english"], deps)
    capsys.readouterr()
    assert code == 2
    assert not deps.profile_path.exists()


def test_locale_with_a_character(make_deps, capsys):
    deps = make_deps(wow_dir=WOW)
    code = main(["profile", "set", "Givrelame", "--class", "Mage", "--game-locale", "enUS"], deps)
    capsys.readouterr()
    assert code == 0
    data = show(deps, capsys)
    assert data["character"]["name"] == "Givrelame" and data["game_locale"]["source"] == "joueur"


def test_show_text_names_the_locale(make_deps, capsys):
    code = main(["profile", "show"], make_deps(wow_dir=WOW))
    out, _ = capsys.readouterr()
    assert code == 0 and "Langue du client : enUS" in out


def test_mcp_tool_returns_the_locale(make_deps):
    import asyncio

    from mcp import Client

    from forever.mcp_server import build_server

    deps = make_deps(wow_dir=WOW)

    async def go():
        async with Client(build_server(deps)) as client:
            return await client.call_tool("forever_player_profile", {})

    r = asyncio.run(go())
    assert not r.is_error
    assert r.structured_content["game_locale"] == {"value": "enUS", "source": "client"}


def test_every_skill_names_spells_as_in_the_client():
    skills = sorted(p for p in SKILLS.iterdir() if (p / "SKILL.md").is_file())
    assert len(skills) == 6
    for skill in skills:
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        assert RULE in text, skill.name
        assert "game_locale" in text, skill.name


def test_plugin_version_is_at_least_0_7_0():
    """Noms du client dans les skills depuis 0.7.0 (T08c) ; la version exacte est épinglée par test_plugin_version.py."""
    version = read_json(REPO_ROOT / "plugin" / ".claude-plugin" / "plugin.json")["version"]
    assert tuple(int(n) for n in version.split(".")) >= (0, 7, 0)
