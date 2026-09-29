"""Angles morts lisibles par le code (T05, bloc I1 ; décision 88) : champ `angle_mort` du registre (talents,
contextes, fonction d'estimation), validation, choix des angles morts d'un build, estimations bornées calculées par le
moteur avec les données (talents.json, recharges du client, spells.json)."""

import pytest
from conftest import REGISTRY_PATH, REPO_ROOT

from forever.engine.blind_spots import (
    CONTEXTS,
    ESTIMATORS,
    BlindSpotRule,
    estimate_cooldown_talents,
    estimate_evocation,
    estimate_wake_of_fire_crit,
    select_blind_spots,
)
from forever.engine.casting import cast_time
from forever.engine.character import character
from forever.engine.crit import crit_mult
from forever.engine.spells import best_rank
from forever.engine.talents import talent_value
from forever.registry import blind_spot_rules, load, validate

# Talents non modélisés de la décision 83 (angles morts chiffrés ou non) et Wake of Fire (bonus de critique).
UNMODELED = {
    "presenceOfMind",
    "combustion",
    "coldSnap",
    "impact",
    "improvedScorch",
    "improvedBlizzard",
    "iceBarrier",
    "iceBlock",
    "improvedCounterspell",
    "wandSpecialization",
    "wakeOfFire",
}


@pytest.fixture(scope="module")
def rules():
    return blind_spot_rules(load(REGISTRY_PATH))


def test_every_unmodeled_talent_has_a_blind_spot(rules):
    covered = {t for r in rules for t in r.talents}
    assert covered >= UNMODELED, UNMODELED - covered
    for r in rules:
        assert set(r.contexts) <= set(CONTEXTS) and r.contexts
        assert r.estimate is None or r.estimate in ESTIMATORS


def test_new_registry_entries(rules):
    by_id = {r.id: r for r in rules}
    assert {"B18", "B19", "C9", "I8"} <= set(by_id)
    assert set(by_id["B18"].talents) == {"presenceOfMind", "combustion", "coldSnap"}
    assert by_id["B18"].estimate == "cooldown_talents"
    assert by_id["B10"].estimate == "evocation" and set(by_id["B10"].contexts) == {"dungeon", "raid"}
    assert by_id["F6"].talents == ("wandSpecialization",)


def _write(tmp_path, angle_mort):
    """Copie du registre où l'entrée B10 porte le champ `angle_mort` donné (l'ancien est retiré)."""
    lines = (REPO_ROOT / "docs" / "MECHANICS_REGISTRY.yaml").read_text(encoding="utf-8").splitlines()
    i = lines.index("  - id: B10")
    j = next(k for k in range(i + 1, len(lines)) if lines[k].startswith("  - id: "))
    block, skipping = [], False
    for line in lines[i:j]:
        if line.startswith("    angle_mort:"):
            skipping = True
            continue
        if skipping and line.startswith("      ") and not line.startswith("      - "):
            continue
        skipping = False
        block.append(line)
    while block and not block[-1].strip():
        block.pop()
    block += ["    angle_mort:", *[f"      {k}: {v}" for k, v in angle_mort.items()]]
    path = tmp_path / "registry.yaml"
    path.write_text(chr(10).join([*lines[:i], *block, *lines[j:]]), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("angle_mort", "message"),
    [
        ({"talents": "[notATalent]", "contextes": "[raid]", "estimation": "null"}, "talent inconnu"),
        ({"talents": "[]", "contextes": "[arena]", "estimation": "null"}, "contexte inconnu"),
        ({"talents": "[]", "contextes": "[raid]", "estimation": "guess"}, "estimation inconnue"),
    ],
)
def test_invalid_blind_spot_is_refused(tmp_path, angle_mort, message):
    report = validate(_write(tmp_path, angle_mort), REPO_ROOT, strict=True)
    assert any("B10" in e and message in e for e in report.errors), report.errors


def test_repository_registry_blind_spots_are_valid():
    assert validate(REGISTRY_PATH, REPO_ROOT, strict=True).errors == []


def test_selection_follows_talents_and_context(game_data, rules):
    pts = {"arcaneFocus": 5, "arcaneConcentration": 5, "arcaneBlast": 1, "presenceOfMind": 1}
    raid = {b.id for b in select_blind_spots(game_data, rules, "raid", 40, pts)}
    assert "B18" in raid and "B10" in raid  # talent pris ; règle de contexte sans talent
    assert "F6" not in raid  # baguettes : leveling seulement, talent non pris
    near = {b.id for b in select_blind_spots(game_data, rules, "leveling", 40, {}, near={"wandSpecialization": 2})}
    assert "F6" in near  # talent de l'alternative proche
    assert "B18" not in {b.id for b in select_blind_spots(game_data, rules, "raid", 40, {"arcaneFocus": 5})}


def test_estimates_are_positive_bounds_from_the_data(game_data):
    ch = character(game_data, 40, "Orc")
    pom = estimate_cooldown_talents(game_data, 40, {"presenceOfMind": 1, "improvedFireball": 5}, "Orc")
    longest = max(
        cast_time(game_data, k, best_rank(game_data, k, 40, {}), {"improvedFireball": 5}, ch)
        for k in ("frostbolt", "fireball")
    )
    assert pom == pytest.approx(longest / game_data.talent_cooldowns_s["presenceOfMind"], rel=1e-12)
    comb = estimate_cooldown_talents(game_data, 40, {"combustion": 1}, "Orc")
    charges = talent_value(game_data, {"combustion": 1}, "combustion", 1)
    fireball = cast_time(game_data, "fireball", best_rank(game_data, "fireball", 40, {}), {}, ch)
    expected = charges * (crit_mult(game_data, "fire", {}) - 1) * fireball / game_data.talent_cooldowns_s["combustion"]
    assert comb == pytest.approx(expected, rel=1e-12)
    assert estimate_cooldown_talents(game_data, 40, {"coldSnap": 1}, "Orc") is None
    assert estimate_cooldown_talents(game_data, 40, {}, "Orc") is None
    wof = estimate_wake_of_fire_crit(game_data, 20, {"wakeOfFire": 2}, "Orc")
    assert wof is not None and 0 < wof < 1
    assert estimate_wake_of_fire_crit(game_data, 20, {}, "Orc") is None
    evo = estimate_evocation(game_data, 40, {}, "Orc")
    assert evo is not None and 0 < evo < 1


def test_blind_spot_effects_come_from_the_estimators(game_data, rules):
    pts = {"improvedFireball": 5, "presenceOfMind": 1}
    spots = {b.id: b for b in select_blind_spots(game_data, rules, "dungeon", 40, pts)}
    assert spots["B18"].effect == estimate_cooldown_talents(game_data, 40, pts, "Orc")
    assert spots["B18"].talents == ("presenceOfMind",)
    assert spots["B10"].effect == estimate_evocation(game_data, 40, pts, "Orc")
    unrated = [b for b in spots.values() if b.effect is None]
    assert unrated  # angles morts non chiffrés gardés (effet inconnu, signalé)
    assert all(isinstance(r, BlindSpotRule) for r in blind_spot_rules(load(REGISTRY_PATH)))
