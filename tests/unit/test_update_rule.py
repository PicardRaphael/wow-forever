"""Règle d'automatisme de `forever update` (T08d, bloc E, décision 180), testée par table.

Une écriture se fait seulement si (a) `verify` est vert, (b) aucune valeur faite à la main n'est perdue ni remplacée,
(c) les entrées de chaque moteur calculé sont identiques. `verify` rouge, installation refusée par les règles de
fusion ou valeur `perdu` : `bloqué` (jamais approuvable). Aucune règle de jeu ici : des valeurs de forme seulement."""

import pytest

from forever.carry import CarryReport, ManualValue
from forever.engine_inputs import ENGINES, InputsDiff
from forever.update import decide

VALUE = ManualValue("pet_rules.json", "/official_fixes", ["x"], "manuel", 3, "note officielle")


def carry(kept=1, reapplied=0, superseded=0, lost=0):
    return CarryReport(
        [VALUE] * kept,
        [VALUE] * reapplied,
        [(VALUE, ["y"])] * superseded,
        [VALUE] * lost,
    )


def inputs(*different):
    item = {"file": "spell_scaling.json", "pointer": None, "status": "différent", "before": "a", "after": "b"}
    return {name: InputsDiff(name, name not in different, [item] if name in different else []) for name in ENGINES}


@pytest.mark.parametrize(
    ("verify_ok", "install_ok", "report", "diffs", "action", "failed"),
    [
        (True, True, carry(), inputs(), "écrire", set()),
        (True, True, carry(reapplied=1), inputs(), "écrire", set()),
        (True, True, carry(), inputs("mage_build"), "attente", {"inputs"}),
        (True, True, carry(superseded=1), inputs(), "attente", {"manual"}),
        (True, True, carry(superseded=1), inputs("pvp_dr"), "attente", {"manual", "inputs"}),
        (True, True, carry(lost=1), inputs(), "bloqué", {"manual"}),
        (False, True, carry(), inputs(), "bloqué", {"verify"}),
        (False, True, carry(superseded=1), inputs("mage_build"), "bloqué", {"verify", "manual", "inputs"}),
        (True, False, carry(), inputs(), "bloqué", {"install"}),
    ],
)
def test_rule_table(verify_ok, install_ok, report, diffs, action, failed):
    verdict = decide(verify_ok, report, diffs, "install_version", install_ok=install_ok)
    assert verdict.action == action
    assert set(verdict.clauses) == {"verify", "install", "manual", "inputs"}
    assert {k for k, ok in verdict.clauses.items() if not ok} == failed
    assert (verdict.reasons == []) == (action == "écrire")


def test_reasons_name_the_engines_and_the_values():
    verdict = decide(True, carry(superseded=1), inputs("mage_build", "mage_leveling"), "install_revision")
    text = " ".join(verdict.reasons)
    assert "mage_build" in text and "mage_leveling" in text and "pvp_dr" not in text
    assert "pet_rules.json" in text and "/official_fixes" in text


def test_lost_value_is_never_approvable_even_when_everything_else_holds():
    verdict = decide(True, carry(lost=1), inputs(), "install_version")
    assert verdict.action == "bloqué"
    assert any("perdu" in r for r in verdict.reasons)


def test_red_verify_wins_over_every_other_clause():
    verdict = decide(False, carry(), inputs(), "install_revision")
    assert verdict.action == "bloqué" and any("verify" in r for r in verdict.reasons)
