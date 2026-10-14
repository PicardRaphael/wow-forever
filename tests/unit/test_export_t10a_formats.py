"""Formats de T10a préparés côté format (EX1, bloc E) : liste BiS `!NBIS1!` (v=4) et poids de statistiques `NFSW1:`
de Naowh Forever, écrits et relus, bornes du format ; aucune donnée remplie avant T10a (`forever export bis` et
`forever export weights` le disent).

Valeurs : clés et emplacements de `tests/fixtures/exports/naowh_keys.json` (noms de format relevés dans Naowh Forever
1.1.12) ; identifiants d'objets et poids **synthétiques** (aucune valeur du jeu)."""

import json

import pytest
from conftest import FIXTURES
from lua_oracle import lua_unpack, runtime

from forever.cli import main
from forever.exports.codec import ExportFormatError, pack
from forever.exports.naowh import (
    BIS_PREFIX,
    BIS_VERSION,
    WEIGHTS_MAX,
    naowh_bis,
    naowh_weights,
    read_naowh_bis,
    read_naowh_weights,
)
from forever.exports.naowh_keys import BIS_SLOTS, SPEC_KEYS, STAT_KEYS

KEYS = json.loads((FIXTURES / "exports" / "naowh_keys.json").read_text(encoding="utf-8"))
SLOTS = {1: 101, 2: 102, 16: 116, 18: 118}  # identifiants synthétiques
EXTRA = {1: [201, 202], 16: [216]}


def test_format_names_match_the_survey():
    assert list(SPEC_KEYS) == KEYS["spec_keys"] and len(SPEC_KEYS) == 28
    assert list(STAT_KEYS) == KEYS["stat_keys"] and len(STAT_KEYS) == 27
    assert sorted(BIS_SLOTS) == sorted(KEYS["bis_slots"]) and 4 not in BIS_SLOTS and 19 not in BIS_SLOTS
    assert BIS_VERSION == KEYS["bis_version"] and WEIGHTS_MAX == KEYS["weights_max"]


# --- !NBIS1! --------------------------------------------------------------------------------------------------------


def test_bis_round_trip_python_and_lua():
    text = naowh_bis("Liste d'essai", "frost-mage", SLOTS, EXTRA)
    assert text.startswith(BIS_PREFIX)
    back = read_naowh_bis(text)
    assert back.name == "Liste d'essai" and back.spec == "frost-mage"
    assert back.slots == SLOTS and back.extra == {k: tuple(v) for k, v in EXTRA.items()}
    table = lua_unpack(runtime(), text[len(BIS_PREFIX) :].encode())
    assert table["v"] == 4 and table["name"] == "Liste d'essai" and table["spec"] == "frost-mage"
    assert {int(k): v for k, v in table["slots"].items()} == SLOTS
    assert {int(k): v for k, v in table["extra"].items()} == EXTRA


@pytest.mark.parametrize("slot", [4, 19, 0])
def test_bis_refuses_slots_outside_the_list(slot):
    with pytest.raises(ExportFormatError):
        naowh_bis("x", "frost-mage", {slot: 101}, {})
    with pytest.raises(ExportFormatError):
        naowh_bis("x", "frost-mage", {1: 101}, {slot: [101]})


def test_bis_refuses_bad_identifiers_and_spec():
    for bad in (0, -1, 2**31, 1.5):
        with pytest.raises(ExportFormatError):
            naowh_bis("x", "frost-mage", {1: bad}, {})
    with pytest.raises(ExportFormatError):
        naowh_bis("x", "ice-mage", SLOTS, {})


def test_bis_text_is_cut_like_naowh():
    back = read_naowh_bis(naowh_bis("é" * 30 + "|", "frost-mage", SLOTS, {}))
    assert back.name == "é" * 20


def test_bis_read_refuses_other_versions():
    for v in (1, 2, 3, 5):
        with pytest.raises(ExportFormatError):
            read_naowh_bis(pack(BIS_PREFIX, {"v": v, "name": "x", "spec": "frost-mage", "slots": {1: 101}}))


# --- NFSW1: ---------------------------------------------------------------------------------------------------------


def test_weights_round_trip_and_text():
    weights = {"int": 0.5, "spell": 1.0, "scrit": 12.25, "sta": 0.000125, "mp5": 0.0}
    text = naowh_weights("frost-mage", weights)
    assert text.startswith("NFSW1:frost-mage:")
    assert all("e" not in part.split("=", 1)[1] for part in text.split(":", 2)[2].split(","))
    assert all(ch.isalnum() or ch in "=.," for ch in text.split(":", 2)[2])
    key, back = read_naowh_weights(text)
    assert key == "frost-mage" and back == pytest.approx(weights, rel=1e-9)


def test_weights_never_use_exponent_notation():
    text = naowh_weights("frost-mage", {"int": 1e-5, "spell": 123.456789})
    body = text.split(":", 2)[2]
    assert "e" not in body.replace("spell", "") and "-" not in body


@pytest.mark.parametrize(
    "weights", [{"int": 1000}, {"int": 1000.5}, {"int": -1}, {"luck": 1}, {"int": float("nan")}, {"int": float("inf")}]
)
def test_weights_out_of_bounds_are_refused(weights):
    with pytest.raises(ExportFormatError):
        naowh_weights("frost-mage", weights)


def test_weights_unknown_spec_refused():
    with pytest.raises(ExportFormatError):
        naowh_weights("ice-mage", {"int": 1})
    with pytest.raises(ExportFormatError):
        read_naowh_weights("NFSW1:ice-mage:int=1")
    with pytest.raises(ExportFormatError):
        read_naowh_weights("NFSW1:frost-mage:int=1e5")
    with pytest.raises(ExportFormatError):
        read_naowh_weights("NFSW1:frost-mage:luck=1")


# --- CLI ------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("cmd", ["bis", "weights"])
def test_cli_says_filled_by_t10a(make_deps, capsys, cmd):
    assert main(["export", cmd, "--json"], make_deps()) == 2
    data = json.loads(capsys.readouterr().out)
    assert "T10a" in data["error"]["message"]


def test_cli_reads_both_formats(make_deps, capsys):
    deps = make_deps()
    assert main(["export", "read", naowh_bis("x", "frost-mage", SLOTS, EXTRA), "--json"], deps) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["kind"] == "naowh_bis" and {int(k): v for k, v in data["slots"].items()} == SLOTS
    assert main(["export", "read", naowh_weights("frost-mage", {"int": 0.5}), "--json"], deps) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["kind"] == "naowh_weights" and data["spec"] == "frost-mage" and data["weights"] == {"int": 0.5}
