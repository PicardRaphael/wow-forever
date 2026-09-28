"""Exemples chiffrés de la vidéo BVSgeHp3sWU (Toleduck, 2026-09-27) refaits par le moteur, mode forever (T04e).

Valeurs : tests/fixtures/community/BVSgeHp3sWU.json (certitude communautaire, sens `suppose` : source unique, outil
non publié), relevées dans docs/research/videos/BVSgeHp3sWU.md (sections 1 et 3). Tolérance ±0,5 (affichage au
dixième du tableur). Trois exemples sont exclus (écart d'arrondi des bornes, question ouverte E7) : un test vérifie que
leur écart s'explique par l'arrondi seul."""

import json

import pytest
from conftest import FIXTURES

from forever.engine import arcane_power_buffs, character, expected_cast, merge_buffs
from forever.engine.buffs import arcane_blast_bonus

DOC = json.loads((FIXTURES / "community" / "BVSgeHp3sWU.json").read_text(encoding="utf-8"))
TOL = DOC["tolerance"]
INCLUDED = [e for e in DOC["examples"] if "exclu" not in e]
EXCLUDED = [e for e in DOC["examples"] if "exclu" in e]


def engine(gd, e, rules="forever"):
    """(coup normal, coup critique, estimation) du moteur pour l'exemple `e` : dégâts au niveau du personnage, coup
    normal = coup direct moyen sans l'espérance de critique ; un missile d'Arcane Missiles = sort / missiles."""
    pts = e["talents"]
    ch = character(gd, e["level"], "Orc", {"sp": e["sp"]})
    buffs = merge_buffs(
        arcane_blast_bonus(gd, pts, e.get("arcane_blast_stacks", 0), for_spell=e["spell"]),
        arcane_power_buffs(gd, pts) if e.get("arcane_power") else None,
    )
    est = expected_cast(
        gd,
        e["spell"],
        e["level"],
        pts,
        ch,
        frozen=e.get("frozen", False),
        buffs=buffs,
        spell_level="character",
        rules=rules,
    )
    assert est is not None and est["rank"].position == e["rank"], e["id"]
    normal = est["direct_per_hit"] / (1 + est["crit"] * (est["crit_mult"] - 1))
    if e.get("per") == "missile":
        (channel,) = [c for c in gd.scaling[e["spell"]][e["rank"] - 1].components if c.kind == "channel"]
        normal /= channel.ticks
    return normal, normal * est["crit_mult"], est


def test_fixture_is_marked_as_community_source():
    assert DOC["certainty"] == "communautaire"
    assert DOC["source"]["url"] == "https://www.youtube.com/watch?v=BVSgeHp3sWU"
    assert len(INCLUDED) == 14 and {e["id"] for e in EXCLUDED} == {"V18-explosion", "V19", "V8-tableur"}
    assert all(e["exclu"] == "E7" and "sheet_bounds" in e for e in EXCLUDED)


@pytest.mark.parametrize("e", INCLUDED, ids=[e["id"] for e in INCLUDED])
def test_video_example(game_data, e):
    normal, crit, _ = engine(game_data, e)
    assert abs(normal - e["normal"]) <= TOL, (e["id"], normal)
    if "crit" in e:
        assert abs(crit - e["crit"]) <= TOL, (e["id"], crit)


@pytest.mark.parametrize("e", EXCLUDED, ids=[e["id"] for e in EXCLUDED])
def test_video_rounding_gap(game_data, e):
    """Écart hors tolérance, expliqué par l'arrondi seul : avec les bornes tronquées du tableur (`sheet_bounds`) à la
    place des bornes du moteur (demi supérieur, G7), la même formule redonne la valeur de la vidéo à ±0,5."""
    normal, _, est = engine(game_data, e)
    gap = normal - e["normal"]
    assert abs(gap) > TOL
    assert gap == pytest.approx(e["engine_gap"], abs=0.05)
    r = est["rank"]
    frozen = game_data.spells[e["spell"]].frozen_mult if e.get("frozen") else None
    shift = ((r.damage_min + r.damage_max) / 2 - sum(e["sheet_bounds"]) / 2) * est["dmg_mult"] * (frozen or 1.0)
    assert abs(normal - shift - e["normal"]) <= TOL, (e["id"], normal - shift)


@pytest.mark.parametrize("key", ["V13", "V18-missiles", "V11b-2000"])
def test_seed_rules_miss_the_video(game_data, key):
    """Le test mesure bien T04e : en mode seed (formule, Improved Cone of Cold ignoré, bonus additionnés), ces
    exemples sortent de la tolérance."""
    (e,) = [x for x in INCLUDED if x["id"] == key]
    normal, _, _ = engine(game_data, e, rules="seed")
    assert abs(normal - e["normal"]) > TOL, (key, normal)
