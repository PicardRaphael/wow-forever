"""Profil joueur minimal hors du dépôt (T06b, bloc D, décision D5) et défauts visibles des outils de calcul.

Le profil vit dans un dossier temporaire (`Deps.profile_path`) ; aucun test ne lit ni n'écrit ~/.forever. Build de
Givre légal au niveau 22 (13 points = 22 − 9, `points_available`) ; Ice Lance au palier 3 illégal au niveau 12
(`check_build`)."""

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import REPO_ROOT, FakeHttp
from mcp import Client

from forever.build import build_report
from forever.cli import main
from forever.errors import InvalidArgumentError
from forever.leveling import simulate_leveling
from forever.mcp_server import build_server
from forever.profile import character_values, load_profile, profile_path, read_profile, remove, set_character, use
from forever.provenance import validate_provenance

FROST_22 = {"improvedFrostbolt": 5, "elementalPrecision": 3, "frostbite": 3, "iceShards": 2}


@pytest.fixture
def deps(make_deps, tmp_path):
    return replace(make_deps(), profile_path=tmp_path / "joueur" / "profile.json")


def three(deps):
    set_character(deps, "Givrelame", cls="Mage", race="Orc", faction="Horde", level=22, talents=FROST_22)
    set_character(deps, "Lumière", cls="Paladin", race="Human", faction="Alliance", level=15, talents={"x": 1})
    set_character(deps, "Ombre", cls="Démoniste", race="Undead", faction="Horde", level=30)


def test_default_path_is_outside_the_repository(tmp_path):
    default = profile_path({})
    assert default.name == "profile.json" and default.parent.name == ".forever"
    assert not default.resolve().is_relative_to(REPO_ROOT.resolve())
    assert profile_path({"FOREVER_PROFILE": str(tmp_path / "p.json")}) == tmp_path / "p.json"
    # T06b : repli de l'évaluation du plugin (claude plugin eval ne transmet que EVAL_*) ; FOREVER_PROFILE prime.
    assert profile_path({"EVAL_FOREVER_PROFILE": str(tmp_path / "e.json")}) == tmp_path / "e.json"
    both = {"FOREVER_PROFILE": str(tmp_path / "p.json"), "EVAL_FOREVER_PROFILE": str(tmp_path / "e.json")}
    assert profile_path(both) == tmp_path / "p.json"


def test_relative_eval_profile_is_resolved_against_the_repository():
    # CH0 : le champ `env` d'un cas d'évaluation donne un chemin relatif au dépôt ; le serveur MCP ne tourne pas
    # forcément depuis la racine du dépôt (claude plugin eval)
    rel = "tests/fixtures/plugin_eval/profile-chasseur.json"
    assert profile_path({"EVAL_FOREVER_PROFILE": rel}) == REPO_ROOT / rel
    assert profile_path({"FOREVER_PROFILE": "relatif.json"}) == Path("relatif.json")  # FOREVER_PROFILE inchangé


def test_profile_under_the_repository_is_refused(make_deps):
    inside = replace(make_deps(), profile_path=REPO_ROOT / "profile.json")
    with pytest.raises(InvalidArgumentError):
        set_character(inside, "Givrelame", cls="Mage", race="Orc", faction="Horde", level=22)
    assert not (REPO_ROOT / "profile.json").exists()


def test_three_characters_and_the_active_one(deps):
    three(deps)
    p = load_profile(deps.profile_path)
    assert p["schema_version"] == 2
    assert list(p["characters"]) == ["Givrelame", "Lumière", "Ombre"]
    assert p["active"] == "Givrelame"  # premier personnage créé
    assert character_values(p["characters"]["Ombre"])["class"] == "Warlock"
    use(deps, "Ombre")
    assert load_profile(deps.profile_path)["active"] == "Ombre"
    with pytest.raises(InvalidArgumentError):
        use(deps, "Inconnu")


def test_partial_update_keeps_the_other_fields(deps):
    three(deps)
    set_character(deps, "Givrelame", level=23)
    c = character_values(load_profile(deps.profile_path)["characters"]["Givrelame"])
    assert (c["level"], c["race"], c["faction"], c["talents"]) == (23, "Orc", "Horde", FROST_22)
    set_character(deps, "Givrelame", professions={"Couture": 150})
    assert character_values(load_profile(deps.profile_path)["characters"]["Givrelame"])["professions"] == {
        "Couture": 150
    }


def test_mage_race_is_checked_with_close_names(deps):
    with pytest.raises(InvalidArgumentError) as info:
        set_character(deps, "Givrelame", cls="Mage", race="Orcc", faction="Horde", level=22)
    assert "Orc" in info.value.message + info.value.action


def test_mage_talents_must_be_legal_at_the_level(deps):
    with pytest.raises(InvalidArgumentError) as info:
        set_character(deps, "Givrelame", cls="Mage", race="Orc", faction="Horde", level=12, talents={"iceLance": 1})
    assert "Ice Lance" in info.value.message
    with pytest.raises(InvalidArgumentError):
        set_character(deps, "Givrelame", cls="Mage", race="Orc", faction="Horde", level=99)
    with pytest.raises(InvalidArgumentError):
        set_character(deps, "Givrelame", cls="Chevalier de la mort", race="Orc", faction="Horde", level=20)


def test_other_classes_are_kept_unvalidated(deps):
    three(deps)
    chars = {n: character_values(c) for n, c in load_profile(deps.profile_path)["characters"].items()}
    assert chars["Lumière"]["validated"] is False and chars["Lumière"]["talents"] == {"x": 1}
    assert chars["Givrelame"]["validated"] is True


def test_faction_is_never_deduced(deps):
    set_character(deps, "Givrelame", cls="Mage", race="Orc", level=22)
    view = read_profile(deps)
    assert view["character"]["faction"] is None
    assert "faction" in view["missing"]


def test_remove_needs_consent(deps, capsys):
    three(deps)
    assert main(["profile", "remove", "Ombre"], deps=deps) == 0  # sans accord : refus, rien d'écrit
    assert "Ombre" in load_profile(deps.profile_path)["characters"]
    assert main(["profile", "remove", "Ombre", "--yes"], deps=deps) == 0
    assert "Ombre" not in load_profile(deps.profile_path)["characters"]
    remove(deps, "Lumière")
    assert list(load_profile(deps.profile_path)["characters"]) == ["Givrelame"]


def test_absent_profile_reads_as_empty(deps):
    view = read_profile(deps)
    assert view["active"] is None and view["character"] is None and view["characters"] == []
    assert validate_provenance(view["provenance"]) == []


def test_read_profile_marks_stale_and_missing(deps):
    three(deps)
    path = deps.profile_path
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["characters"]["Givrelame"]["game_version"] = "1.60.1.69893"
    path.write_bytes(json.dumps(doc).encode("utf-8"))
    view = read_profile(deps)
    assert view["active"] == "Givrelame" and view["stale"] is True
    assert read_profile(deps, "Ombre")["missing"] == ["talents", "professions"]
    assert read_profile(deps, "Ombre")["stale"] is False
    assert view["characters"] == ["Givrelame", "Lumière", "Ombre"]


def test_cli_and_mcp_give_the_same_json(deps, capsys):
    three(deps)
    capsys.readouterr()
    assert main(["profile", "show", "--json"], deps=deps) == 0
    cli = json.loads(capsys.readouterr().out)

    async def call():
        async with Client(build_server(deps)) as client:
            return await client.call_tool("forever_player_profile", {})

    r = asyncio.run(call())
    assert not r.is_error
    mcp = r.structured_content
    for payload in (cli, mcp):
        payload["provenance"].pop("generated_at")
    assert cli == mcp
    assert cli["character"]["name"] == "Givrelame"


def test_cli_set_list_use_show(deps, capsys):
    argv = ["profile", "set", "Givrelame", "--class", "Mage", "--race", "Orc", "--faction", "Horde", "--level", "22"]
    assert (
        main([*argv, "--talents", "improvedFrostbolt=5,elementalPrecision=3,frostbite=3,iceShards=2"], deps=deps) == 0
    )
    assert (
        main(
            ["profile", "set", "Givrelame", "--profession", "Couture=150", "--profession", "Enchantement=90"], deps=deps
        )
        == 0
    )
    c = character_values(load_profile(deps.profile_path)["characters"]["Givrelame"])
    assert c["talents"] == FROST_22 and c["professions"] == {"Couture": 150, "Enchantement": 90}
    capsys.readouterr()
    assert main(["profile", "list"], deps=deps) == 0
    assert "Givrelame" in capsys.readouterr().out
    assert main(["profile", "show"], deps=deps) == 0
    out = capsys.readouterr().out
    assert "Givrelame" in out and "Mage" in out and "niveau 22" in out
    assert deps.profile_path.read_bytes().count(b"\r\n") == 0


def test_no_network(deps):
    failing = replace(deps, http_get=FakeHttp.failing())
    three(failing)
    read_profile(failing)
    assert failing.http_get.calls == []


# --- Défauts visibles des outils de calcul ------------------------------------------------------------------


def test_build_report_shows_the_default_race(deps):
    rep = build_report(deps, "leveling", 11, preset="rapide", sensitivity=False)
    assert rep["inputs"]["race"] == {"value": "Orc", "origin": "default"}
    assert rep["race"] == "Orc"
    assert any("race" in a and "défaut" in a for a in rep["assumptions"])
    given = build_report(deps, "leveling", 11, race="Troll", preset="rapide", sensitivity=False)
    assert given["inputs"]["race"] == {"value": "Troll", "origin": "argument"}
    assert not any("race" in a and "défaut" in a for a in given["assumptions"])
    assert given["inputs"]["level"] == {"value": 11, "origin": "argument"}


def test_sim_leveling_shows_the_default_race(deps):
    rep = simulate_leveling(deps, 12, n=20)
    assert rep["inputs"]["race"] == {"value": "Orc", "origin": "default"}
    assert rep["inputs"]["talents"] == {"value": {}, "origin": "default"}
    assert any("race" in a and "défaut" in a for a in rep["provenance"]["assumptions"])
    given = simulate_leveling(deps, 12, race="Gnome", talents={"improvedFrostbolt": 2}, n=20)
    assert given["inputs"]["race"]["origin"] == "argument" and given["inputs"]["talents"]["origin"] == "argument"


def test_calculation_tools_never_read_the_profile(deps):
    set_character(deps, "Givrelame", cls="Mage", race="Troll", faction="Horde", level=22, talents=FROST_22)
    rep = simulate_leveling(deps, 12, n=20)
    assert rep["race"] == "Orc" and rep["talents"] == {}
