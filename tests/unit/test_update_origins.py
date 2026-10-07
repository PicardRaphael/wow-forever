"""Installation seule des fiches recopiées du client et correctifs d'une nouvelle version (T08e, décision 207).

Cas réels du 2026-10-07 sur fixtures (`tests/fixtures/update_origins/`, tirées de git) : 70170 r5 portait la refonte
du Guerrier par les correctifs du serveur (poussée 112347) ; 70245 r1, décodée sans le `DBCache.bin` de 70245, l'avait
défaite ; r3 l'a rétablie. Aucune valeur de jeu n'est affirmée hors des fixtures : noms et valeurs relus dans les
sous-arbres extraits."""

import re
from datetime import UTC, datetime, timedelta

import pytest
from conftest import UPDATE_ORIGINS, mount_warrior, read_json

from forever.carry import CarryReport
from forever.config import UPDATE_HOTFIX_WAIT
from forever.engine_inputs import ValueChange, compare_inputs, hotfix_losses
from forever.pipeline.value_diff import CopiedLine, capped_lines, copied_lines, copied_summary, summary_sentence
from forever.update import decide, hotfix_gate

NO_CARRY = CarryReport([], [], [], [])
BERSERKER = "/classes/Warrior/spells/berserkerRage/ranks/0/level"
SEEN_70245 = datetime(2026, 10, 7, 0, 35, 33, tzinfo=UTC)  # journal des versions du client (source `.build.info`)
R1_RUN = datetime(2026, 10, 7, 6, 0, 14, tzinfo=UTC)  # passage qui a décodé r1 (rapport du 2026-10-07)


def warrior(label):
    return read_json(UPDATE_ORIGINS / f"warrior-{label}.json")


def failed(verdict):
    return {k for k, ok in verdict.clauses.items() if not ok}


# --- Porte des correctifs ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("archived", "age", "gate"),
    [
        (True, timedelta(hours=1), "lire"),
        (True, None, "lire"),
        (False, timedelta(hours=1), "attendre"),
        (False, timedelta(hours=23, minutes=59), "attendre"),
        (False, timedelta(hours=24), "sans_correctifs"),
        (False, timedelta(days=3), "sans_correctifs"),
        (False, None, "attendre"),
    ],
)
def test_gate_table(archived, age, gate):
    now = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
    seen = None if age is None else now - age
    assert hotfix_gate(archived, seen, now, timedelta(hours=24)) == gate


def test_the_wait_is_a_day():
    assert timedelta(hours=24) == UPDATE_HOTFIX_WAIT


def test_70245_r1_without_dbcache_waits():
    assert hotfix_gate(False, SEEN_70245, R1_RUN, UPDATE_HOTFIX_WAIT) == "attendre"


# --- Cas réels ---------------------------------------------------------------------------------------------------


def test_70245_r1_after_the_delay_waits_on_lost_hotfixes(tmp_path):
    before = mount_warrior(tmp_path / "avant", "70170-r5", "70170-r5")
    after = mount_warrior(tmp_path / "après", "70245-r1", None)
    losses = hotfix_losses(before, after)
    assert ValueChange("classes.json", BERSERKER, 30, 32, "correctif_serveur", "client") in losses
    assert all(c.origin_before == "correctif_serveur" and c.origin_after != "correctif_serveur" for c in losses)
    assert all(c.pointer.startswith("/classes/Warrior/") for c in losses)
    verdict = decide(True, NO_CARRY, compare_inputs(before, after), "install_version", hotfix_losses=losses)
    assert verdict.action == "attente"
    assert failed(verdict) == {"hotfixes"}  # les fiches PvP ne changent que par des valeurs du client
    assert any("correctifs du serveur non relus" in r for r in verdict.reasons)


def test_70245_r1_with_its_dbcache_installs_alone(tmp_path):
    before = mount_warrior(tmp_path / "avant", "70170-r5", "70170-r5")
    after = mount_warrior(tmp_path / "après", "70245-r3", "70245-r3")
    inputs = compare_inputs(before, after)
    assert inputs["pvp_dr"].identical
    assert hotfix_losses(before, after) == []
    assert decide(True, NO_CARRY, inputs, "install_version").action == "écrire"


def test_70245_r3_installs_alone_with_a_summary(tmp_path):
    before = mount_warrior(tmp_path / "avant", "70245-r1", None)
    after = mount_warrior(tmp_path / "après", "70245-r3", "70245-r3")
    losses = hotfix_losses(before, after)
    assert losses == []
    verdict = decide(True, NO_CARRY, compare_inputs(before, after), "install_revision", hotfix_losses=losses)
    assert verdict.action == "écrire" and verdict.reasons == []

    lines = copied_lines("classes.json", warrior("70245-r1"), warrior("70245-r3"), "/classes/Warrior")
    summary = copied_summary(lines)
    assert summary == {
        "Warrior": {
            "talents_added": 4,
            "talents_removed": 5,
            "talents_modified": 18,
            "spells_added": 0,
            "spells_removed": 0,
            "spells_modified": 4,
            "other": 1,
        }
    }
    added = {line.entity for line in lines if line.after == "ajouté"}
    removed = {line.entity for line in lines if line.after == "retiré"}
    assert added == {
        "talent Fury Furious Precision",
        "talent Fury Gore Drinker",
        "talent Fury Lingering Rage",
        "talent Protection Iron Will",
    }
    assert removed == {
        "talent Fury Boundless Rage",
        "talent Fury Improved Cleave",
        "talent Fury Iron Will",
        "talent Fury Precision",
        "talent Protection Toughness",
    }
    spells = {line.entity for line in lines if line.entity.startswith("sort ")}
    assert spells == {"sort Berserker Rage", "sort Improved Cleave", "sort Iron Will", "sort Toughness"}
    assert CopiedLine("Warrior", "sort Berserker Rage", "rang 1 level", 32, 30) in lines
    assert all(line.cls == "Warrior" for line in lines)
    assert not any(re.search(r"\d", line.entity) for line in lines if line.entity.startswith("talent "))
    sentence = summary_sentence(summary, "pvp_dr")
    assert sentence == "fiches PvP : Warrior, 9 talents ajoutés ou retirés, 18 talents et 4 sorts modifiés"


def test_after_the_delay_without_loss_installs_alone(tmp_path):
    def bump(classes):
        classes["classes"]["Warrior"]["trees"][0]["talents"][0]["max"] += 1

    before = mount_warrior(tmp_path / "avant", "70245-r3", "70245-r3")
    after = mount_warrior(tmp_path / "après", "70245-r3", None, change=bump)
    assert hotfix_losses(before, after) == []
    verdict = decide(True, NO_CARRY, compare_inputs(before, after), "install_version", hotfix_losses=[])
    assert verdict.action == "écrire"


def test_summary_is_capped():
    lines = [CopiedLine("Warrior", f"sort s{i}", "rang 1 level", i, i + 1) for i in range(60)]
    capped = capped_lines(lines)
    assert len(capped["lines"]) == 50 and capped["more"] == 10 and capped["note"] == "et 10 autres"
    assert capped["lines"][0] == ["Warrior", "sort s0", "rang 1 level", 0, 1]
    assert capped_lines(lines[:3]) == {"lines": [list(line) for line in lines[:3]], "more": 0, "note": ""}


def test_list_items_are_aligned_by_key_on_each_side():
    """Un prérequis retiré s'affiche retiré, pas comme un autre prérequis à la même position (relecture de T08e)."""
    before = {"trees": [{"name": "Fury", "talents": [{"key": "a", "prereqs": [{"node_id": 1}, {"node_id": 2}]}]}]}
    after = {"trees": [{"name": "Fury", "talents": [{"key": "a", "prereqs": [{"node_id": 2}]}]}]}
    lines = copied_lines("classes.json", before, after, "/classes/Warrior")
    assert lines == [CopiedLine("Warrior", "talent Fury a", "prereqs 1", {"node_id": 1}, None)]


def test_pointers_are_escaped(tmp_path):
    """Clé contenant « / » : pointeur échappé (RFC 6901), origine résolue."""
    from forever.engine_inputs import _value_changes

    calls = []
    changes = _value_changes(
        "x.json", None, {"a/b": 1}, {"a/b": 2}, lambda f, p: calls.append(p) or ("client", "client")
    )
    assert [c.pointer for c in changes] == calls == ["/a~1b"]
