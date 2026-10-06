"""Colonnes du client à plusieurs noms, et arrêt propre de `forever update` sur une colonne renommée (T08d, bloc I).

Relevé du 2026-10-06 : dans les tables de wago de 1.60.1.70235, la colonne `Field_1_60_1_69876_005` de
`PlayerExpectedStat` porte le nom `HPPerStamina` (définitions de la communauté) ; c'est la seule colonne déclarée
absente. Réponse de l'utilisateur du 2026-10-06 : chaque colonne peut avoir une liste de noms, le nouveau d'abord ;
si aucun nom ne correspond, `forever update` s'arrête avec un message clair et une attente d'accord, au lieu d'une
erreur. Les tests renomment des en-têtes de la fixture 70124, jamais une valeur."""

import csv
import io
import json

import pytest
from conftest import DATA_DIR, WAGO_70124
from test_update_chain import DRY, TARGET, montage, step  # noqa: F401  (fixture importée)

from forever.cli import main
from forever.errors import EXIT_PENDING, DataSchemaError, InvalidArgumentError
from forever.pipeline.fetch import table_url
from forever.pipeline.tables import TABLES, ColumnNamesError, column_value, propose_names, read_table
from forever.update import approve, record_pending, run_update

OLD = "Field_1_60_1_69876_005"
NEW = "HPPerStamina"
SOURCE = WAGO_70124 / "enUS" / "PlayerExpectedStat.csv"


def renamed(body: bytes, old: str, new: str) -> bytes:
    """Même CSV, une colonne renommée dans l'en-tête."""
    rows = list(csv.reader(io.StringIO(body.decode("utf-8-sig"))))
    rows[0] = [new if c == old else c for c in rows[0]]
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    return out.getvalue().encode("utf-8")


def header(body: bytes) -> list[str]:
    return next(csv.reader(io.StringIO(body.decode("utf-8-sig"))))


# --- Lecture des tables --------------------------------------------------------------------------------------


def test_player_expected_stat_declares_the_new_name_first():
    names = {c.names for c in TABLES["PlayerExpectedStat"]}
    assert (NEW, OLD) in names


def test_old_and_new_header_read_the_same_values_under_every_name(tmp_path):
    original = read_table(SOURCE, "PlayerExpectedStat")
    path = tmp_path / "PlayerExpectedStat.csv"
    path.write_bytes(renamed(SOURCE.read_bytes(), OLD, NEW))
    after = read_table(path, "PlayerExpectedStat")
    assert len(after) == len(original) > 0
    assert (
        [r[OLD] for r in original] == [r[NEW] for r in original] == [r[OLD] for r in after] == [r[NEW] for r in after]
    )


def test_no_known_name_raises_a_column_names_error(tmp_path):
    path = tmp_path / "PlayerExpectedStat.csv"
    path.write_bytes(renamed(SOURCE.read_bytes(), OLD, "HPPerStaminaV2"))
    with pytest.raises(ColumnNamesError) as caught:
        read_table(path, "PlayerExpectedStat")
    err = caught.value
    assert isinstance(err, DataSchemaError)
    assert err.table == "PlayerExpectedStat"
    assert err.missing == ((NEW, OLD),)
    assert "HPPerStaminaV2" in err.header
    assert NEW in err.message and OLD in err.message


def test_rules_name_a_column_by_one_name_or_a_list():
    row = {NEW: 10.0, OLD: 10.0, "BaseMana": 0.0}
    assert column_value(row, OLD) == 10.0
    assert column_value(row, [NEW, OLD]) == 10.0
    assert column_value({OLD: 7.0}, [NEW, OLD]) == 7.0
    with pytest.raises(DataSchemaError):
        column_value({"BaseMana": 0.0}, [NEW, OLD])


def test_a_name_is_proposed_by_its_place_in_the_installed_header():
    old = header(SOURCE.read_bytes())
    new = header(renamed(SOURCE.read_bytes(), OLD, "HPPerStaminaV2"))
    assert propose_names(old, new, (NEW, OLD)) == "HPPerStaminaV2"
    assert propose_names(old, [*new, "Extra"], (NEW, OLD)) is None  # en-têtes de longueurs différentes
    assert propose_names(old, old, ("Absent",)) is None


def test_installed_rules_list_the_new_name_first():
    rules = json.loads((DATA_DIR / "1.60.1.70170" / "decode_rules.json").read_text(encoding="utf-8"))
    assert rules["character_scaling"]["player_columns"]["hp_per_stamina"] == [NEW, OLD]


# --- forever update ------------------------------------------------------------------------------------------


def serve_renamed(http, new_name):
    url = table_url("PlayerExpectedStat", TARGET, "enUS")
    http.routes[url] = renamed(http.routes[url], OLD, new_name)


def test_the_new_name_alone_is_decoded_without_waiting(montage):  # noqa: F811
    deps, http = montage()
    serve_renamed(http, NEW)
    report = run_update(deps, DRY)
    assert step(report, "nouvelle_version")["status"] != "erreur"
    assert not [p for p in report["pending"] if p["kind"] == "column_names"]


def test_an_unknown_name_waits_instead_of_failing(montage):  # noqa: F811
    deps, http = montage()
    serve_renamed(http, "HPPerStaminaV2")
    report = run_update(deps, DRY)
    found = step(report, "nouvelle_version")
    assert found["status"] == "attente"
    pending = [p for p in report["pending"] if p["kind"] == "column_names"]
    assert len(pending) == 1
    entry = pending[0]
    assert entry["action"] == "attente" and entry["version"] == TARGET
    assert entry["table"] == "PlayerExpectedStat"
    assert [NEW, OLD] in entry["missing"]
    assert any("session" in c for c in entry["commands"])


def test_the_column_wait_exits_with_code_6_and_is_not_approvable(montage, capsys):  # noqa: F811
    deps, http = montage()
    serve_renamed(http, "HPPerStaminaV2")
    assert main(["update", "--dry-run", "--json", "--only", "jeu"], deps) == EXIT_PENDING
    payload = json.loads(capsys.readouterr().out)
    entry = next(p for p in payload["pending"] if p["kind"] == "column_names")
    record_pending(deps.cache_dir, {**entry, "state": "en_attente"})
    with pytest.raises(InvalidArgumentError) as caught:
        approve(deps, entry["id"], spawn=lambda args: None)
    assert "session" in caught.value.message
