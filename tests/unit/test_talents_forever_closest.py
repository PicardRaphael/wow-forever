"""Build populaire le plus proche des talents actuels (P06b, bloc E, décision 235) : calculé par l'outil
(`closest_popular`), jamais choisi par le modèle. `forever_lookup(kind="tf_popular", current=…)` et
`forever talents tf popular --current` rendent `closest` ; la consigne du bouton Talents hors Mage le demande et le
pont publie son lien. Addon Talents Forever synthétique (`talents_forever_data`) ; talents relevés dans les données au
moment du test, jamais écrits de mémoire."""

import asyncio
import json

from mcp import Client
from test_bridge_bench import bench, context  # noqa: F401  (fixture importée)

from forever.bridge.agent import parse_stream
from forever.bridge.context import resolve
from forever.bridge.plans import button_plan
from forever.mcp_server import build_server
from forever.talents_forever import closest_popular, load_addon, popular_builds


def lookup(deps, **args):
    async def go():
        async with Client(build_server(deps)) as client:
            result = await client.call_tool("forever_lookup", {"kind": "tf_popular", **args})
            return json.loads(result.content[0].text)

    return asyncio.run(go())


def hunter_points(deps):
    """Deux talents du deuxième build populaire du Chasseur, un point de moins sur le premier."""
    top = popular_builds(load_addon(deps), deps, "Hunter")["classes"]["Hunter"]["top"]
    talents = dict(sorted(top[1]["talents"].items())[:2])
    first = next(iter(talents))
    talents[first] = max(1, talents[first] - 1)
    return talents


def test_lookup_returns_the_closest_build_of_the_tool(bench):  # noqa: F811
    deps, _ = bench
    current = hunter_points(deps)
    result = lookup(deps, name="Hunter", current=",".join(f"{k}={v}" for k, v in current.items()))
    addon = load_addon(deps)
    expected = closest_popular(addon, popular_builds(addon, deps, "Hunter"), "Hunter", current)
    assert expected is not None and result["closest"] == expected
    assert result["closest"]["link"].startswith("https://talentsforever.com/")


def test_without_current_there_is_no_closest(bench):  # noqa: F811
    deps, _ = bench
    assert "closest" not in lookup(deps, name="Hunter")


def test_no_point_placed_gives_none(bench):  # noqa: F811
    deps, _ = bench
    result = lookup(deps, name="Hunter", current="")
    assert "closest" not in result
    key = next(iter(hunter_points(deps)))
    result = lookup(deps, name="Hunter", current=f"{key}=0")
    assert result["closest"] is None


def test_cli_current_gives_the_same_block(bench, capsys):  # noqa: F811
    from forever.cli import main

    deps, _ = bench
    current = hunter_points(deps)
    arg = ",".join(f"{k}={v}" for k, v in current.items())
    assert main(["talents", "tf", "popular", "--class", "Hunter", "--current", arg, "--json"], deps) == 0
    payload = json.loads(capsys.readouterr()[0])
    assert payload["closest"] == lookup(deps, name="Hunter", current=arg)["closest"]
    assert main(["talents", "tf", "popular", "--class", "Hunter", "--current", arg], deps) == 0
    assert "Build populaire le plus proche" in capsys.readouterr()[0]


def hunter_context(data):
    nodes = data.talents["HUNTER"]
    first = sorted(nodes)[:2]
    return {**context("chasseur19_construit"), "talents": ",".join(f"{n}:1" for n in first)}


def test_talents_button_of_another_class_asks_closest(bench):  # noqa: F811
    _, data = bench
    resolved = resolve(data, hunter_context(data))
    assert resolved.current
    plan = button_plan("talents", resolved, data.level_cap)
    tf = plan.calls[0]
    assert tf.tool == "forever_lookup" and tf.args["kind"] == "tf_popular" and tf.args["name"] == "Hunter"
    assert tf.args["current"] == ",".join(f"{k}={v}" for k, v in resolved.current.items())
    assert plan.link == "closest"
    text = " ".join(plan.read)
    assert "closest" in text and "n'en choisis pas un autre" in text


def test_talents_button_without_points_gives_the_most_played_build(bench):  # noqa: F811
    _, data = bench
    resolved = resolve(data, context("chasseur19_construit"))
    plan = button_plan("talents", resolved, data.level_cap)
    assert "current" not in plan.calls[0].args and plan.link is None
    assert "aucun talent placé : build le plus joué de la classe (rang 1)" in " ".join(plan.read)


def test_mage_talents_plan_is_unchanged(bench):  # noqa: F811
    _, data = bench
    plan = button_plan("talents", resolve(data, context("mage19")), data.level_cap)
    assert plan.link == "projected" and plan.calls[0].tool == "forever_build"


def test_agent_keeps_the_closest_link():
    link = "https://talentsforever.com/hunter/19/abc"
    events = [
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1",
                                                       "name": "mcp__forever__forever_lookup"}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": json.dumps(
            {"kind": "tf_popular", "closest": {"link": link}, "provenance": {"certainty": "suppose"}})}]}},
        {"type": "result", "result": "Build", "session_id": "s"},
    ]  # fmt: skip
    result = parse_stream(json.dumps(e) for e in events)
    assert result.links["closest"] == link
