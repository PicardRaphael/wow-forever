"""Règle d'automatisme de `forever update` (T08d, bloc E, décision 180, amendée par 198 et 207), testée par table.

Une écriture se fait seulement si (a) `verify` est vert, (b) aucune valeur faite à la main n'est perdue ni remplacée,
(c) les entrées de chaque moteur qui calcule sont identiques, et celles d'un moteur qui recopie ne changent que par des
valeurs d'origine `client` ou `correctif_serveur` (avant et après), (d) aucune valeur d'un correctif du serveur n'est
perdue. `verify` rouge, installation refusée par les règles de fusion ou valeur `perdu` : `bloqué` (jamais
approuvable). Aucune règle de jeu ici : des valeurs de forme seulement."""

import pytest

from forever.carry import CarryReport, ManualValue
from forever.engine_inputs import ABSENT, ENGINES, EngineDeclarationError, InputsDiff, ValueChange
from forever.update import decide

VALUE = ManualValue("pet_rules.json", "/official_fixes", ["x"], "manuel", 3, "note officielle")
CLAUSES = {"verify", "install", "manual", "inputs", "hotfixes"}
WARRIOR = "/classes/Warrior/spells/x/ranks/0/level"
DR = "/diminishing_returns/steps/value/1"


def carry(kept=1, reapplied=0, superseded=0, lost=0):
    return CarryReport(
        [VALUE] * kept,
        [VALUE] * reapplied,
        [(VALUE, ["y"])] * superseded,
        [VALUE] * lost,
    )


def inputs(*different):
    """Entrées changées sans le détail des feuilles (appel sans origines)."""
    item = {"file": "spell_scaling.json", "pointer": None, "status": "différent", "before": "a", "after": "b"}
    return {name: InputsDiff(name, name not in different, [item] if name in different else []) for name in ENGINES}


def change(origin_before, origin_after, file="classes.json", pointer=WARRIOR, before=1, after=2):
    return ValueChange(file, pointer, before, after, origin_before, origin_after)


def copied(*changes, engine="pvp_dr", others=()):
    """Entrées où `engine` change par les feuilles données ; `others` : moteurs changés sans détail."""
    out = inputs(*others)
    item = {
        "file": changes[0].file,
        "pointer": "/classes/Warrior" if changes[0].file == "classes.json" else None,
        "status": "différent",
        "before": "a",
        "after": "b",
        "leaves": len(changes),
        "changes": list(changes),
        "origins": {},
    }
    out[engine] = InputsDiff(engine, False, [item])
    return out


def loss():
    return change("correctif_serveur", "client", before=30, after=32)


@pytest.mark.parametrize(
    ("verify_ok", "install_ok", "report", "diffs", "losses", "action", "failed"),
    [
        (True, True, carry(), inputs(), (), "écrire", set()),
        (True, True, carry(reapplied=1), inputs(), (), "écrire", set()),
        (True, True, carry(), inputs("mage_build"), (), "attente", {"inputs"}),
        (True, True, carry(superseded=1), inputs(), (), "attente", {"manual"}),
        (True, True, carry(superseded=1), inputs("pvp_dr"), (), "attente", {"manual", "inputs"}),
        (True, True, carry(lost=1), inputs(), (), "bloqué", {"manual"}),
        (False, True, carry(), inputs(), (), "bloqué", {"verify"}),
        (False, True, carry(superseded=1), inputs("mage_build"), (), "bloqué", {"verify", "manual", "inputs"}),
        (True, False, carry(), inputs(), (), "bloqué", {"install"}),
        # T08e : moteur qui recopie, jugé par l'origine des feuilles changées
        (True, True, carry(), copied(change("client", "client")), (), "écrire", set()),
        (True, True, carry(), copied(change("correctif_serveur", "correctif_serveur")), (), "écrire", set()),
        (True, True, carry(), copied(change("client", "correctif_serveur")), (), "écrire", set()),
        (True, True, carry(), copied(change("client", None, before=ABSENT)), (), "attente", {"inputs"}),
        (True, True, carry(), copied(change("manuel", "client")), (), "attente", {"inputs"}),
        (True, True, carry(), inputs("pvp_dr"), (), "attente", {"inputs"}),  # sans le détail des feuilles
        (True, True, carry(), copied(change("client", "client"), engine="mage_build"), (), "attente", {"inputs"}),
        # T08e : perte d'un correctif du serveur
        (True, True, carry(), inputs(), (loss(),), "attente", {"hotfixes"}),
        (True, True, carry(), copied(change("client", "client")), (loss(),), "attente", {"hotfixes"}),
        (False, True, carry(), inputs(), (loss(),), "bloqué", {"verify", "hotfixes"}),
    ],
)
def test_rule_table(verify_ok, install_ok, report, diffs, losses, action, failed):
    verdict = decide(verify_ok, report, diffs, "install_version", install_ok=install_ok, hotfix_losses=losses)
    assert verdict.action == action
    assert set(verdict.clauses) == CLAUSES
    assert {k for k, ok in verdict.clauses.items() if not ok} == failed
    assert (verdict.reasons == []) == (action == "écrire")


@pytest.mark.parametrize("origin", ["manuel", "journal", "addon", "parametre", "copie_figee", None])
def test_a_copying_engine_waits_on_any_other_origin(origin):
    for pair in ((origin, origin), ("client", origin), (origin, "correctif_serveur")):
        verdict = decide(True, carry(), copied(change(*pair)), "install_version")
        assert verdict.action == "attente", pair
        assert {k for k, ok in verdict.clauses.items() if not ok} == {"inputs"}


def test_a_manual_input_is_named_with_its_pointer():
    diffs = copied(change("client", "client"), change("manuel", "manuel", file="pvp_rules.json", pointer=DR))
    verdict = decide(True, carry(), diffs, "install_version")
    text = " ".join(verdict.reasons)
    assert verdict.action == "attente"
    assert "pvp_dr" in text and "pvp_rules.json" in text and DR in text and "manuel" in text


def test_a_computing_engine_is_named_and_a_copying_one_is_not():
    verdict = decide(True, carry(), copied(change("client", "client"), others=("mage_build",)), "install_version")
    text = " ".join(verdict.reasons)
    assert verdict.action == "attente"
    assert "moteurs aux entrées changées : mage_build" in text and "pvp_dr" not in text


def test_a_lost_hotfix_is_named():
    verdict = decide(True, carry(), inputs(), "install_version", hotfix_losses=[loss(), loss()])
    text = " ".join(verdict.reasons)
    assert "correctifs du serveur non relus" in text and "2 valeur" in text
    assert "classes.json" in text and WARRIOR in text


def test_an_undeclared_engine_is_refused():
    diffs = {**inputs(), "inconnu": InputsDiff("inconnu", False, [])}
    with pytest.raises(EngineDeclarationError, match="inconnu"):
        decide(True, carry(), diffs, "install_version")


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
