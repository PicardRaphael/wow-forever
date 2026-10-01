"""Lecteur local de Forever Bestiary et de sa sauvegarde (CH0, bloc B) : version, empreinte, dates, familles,
capacités, bêtes, carte communautaire, marques traduites ; anonymisation à la lecture.

Fixtures synthétiques : `tests/fixtures/bestiary/` (bêtes et noms inventés, structure de l'addon 0.5.0). Les
valeurs attendues sont relues dans les fichiers de la fixture par le lecteur Lua du projet, jamais écrites ici."""

import json
import re

import pytest
from conftest import FIXTURES

from forever.addons import fingerprint_folder
from forever.errors import PathNotFoundError
from forever.pipeline.bestiary import read_bestiary, read_bestiary_saved
from forever.pipeline.lua_table import parse_lua_assignments, parse_lua_value

ADDON = FIXTURES / "bestiary" / "ForeverBestiary"
SAVED = FIXTURES / "bestiary" / "ForeverBestiary.lua"


def lua_field(path, field):
    """Littéral affecté à `field` (ex. `ns.Data`) dans un fichier de la fixture, relu par `parse_lua_value` sur le
    morceau compris entre cette affectation et la suivante (indépendant du lecteur testé)."""
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^(ns\.[A-Za-z.]+)\s*=", text, flags=re.MULTILINE)
    found = {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}
    return parse_lua_value(found[field])


DATA = lua_field(ADDON / "Data" / "Data.lua", "ns.Data")
BEASTS = lua_field(ADDON / "Data" / "Data.lua", "ns.Data.beasts")
COMMUNITY = lua_field(ADDON / "Data" / "Community.lua", "ns.Data.community")
SV = parse_lua_assignments(SAVED.read_text(encoding="utf-8"))["ForeverBestiaryDB"]


@pytest.fixture(scope="module")
def db():
    return read_bestiary(ADDON)


@pytest.fixture(scope="module")
def saved():
    return read_bestiary_saved(SAVED)


def third_party_strings():
    """Chaînes de tiers de la fixture : noms des pairs, auteurs du flux, empreintes de joueurs, GUID, clés self*,
    clés de likes et de votes (sauvegarde et carte communautaire)."""
    out = set(SV["peers"]) | {f["who"] for f in SV["feed"]} | set(SV["petGuids"])
    out |= set(SV["selfIds"]) | set(SV["selfLooseDone"])
    out |= {k for forms in SV["selfForms"].values() for k in forms}
    out |= {k for likes in SV["likes"].values() for k in likes}
    out |= {k for votes in SV["votes"].values() for k in votes}
    out |= {r for o in SV["obs"].values() for r in o["rp"]}
    out |= {r for o in COMMUNITY["obs"].values() for r in o["rp"]}
    out |= {k for votes in COMMUNITY["votes"].values() for k in votes}
    return out


# --- Base de l'addon -------------------------------------------------------------------------------


def test_info_version_fingerprint_dates(db):
    info = db["info"]
    assert info["version"] == "0.5.0"
    assert info["fingerprint"] == fingerprint_folder(ADDON) and re.fullmatch(r"[0-9a-f]{12}", info["fingerprint"])
    assert info["date"] == DATA["date"] and info["client_build"] == DATA["clientBuild"]
    assert info["community_date"] == COMMUNITY["date"] and info["community_players"] == COMMUNITY["players"]


def test_families_with_bonus_diet_and_abilities(db):
    assert list(db["families"]) == DATA["familyOrder"]
    wolf, raw = db["families"]["wolf"], DATA["families"]["wolf"]
    assert wolf["name"] == {"en": raw["en"], "es": raw["es"]}
    assert wolf["bonus"] == {"damage_pct": raw["dmg"], "armor_pct": raw["armor"], "health_pct": raw["hp"]}
    assert wolf["diet"] == raw["diet"]
    assert wolf["abilities"] == [a["n"] for a in raw["abil"]]
    assert wolf["fastest"] == {
        "speed_s": raw["fastest"]["s"],
        "beast": raw["fastest"]["n"],
        "level": raw["fastest"]["l"],
    }
    renamed = next(k for k, f in DATA["families"].items() if "renamed" in f)
    assert db["families"][renamed]["renamed_from"] == DATA["families"][renamed]["renamed"]


def test_abilities_with_ranks_and_taught_counts(db):
    bite, raw = db["abilities"]["Bite"], DATA["abilities"]["Bite"]
    assert bite["kind"] == raw["kind"] and bite["focus"] == raw["focus"] and bite["cooldown_s"] == raw["cd"]
    assert bite["families"] == raw["fams"]
    assert [(r["rank"], r["level"], r["text_en"]) for r in bite["ranks"]] == [
        (r["r"], r["l"], r["en"]) for r in raw["ranks"]
    ]
    assert bite["taught"] == {str(k): v for k, v in raw["taught"].items()}
    slower = db["abilities"]["Slower Attack"]["ranks"][0]
    assert slower["level"] is None and slower["speed_s"] == DATA["abilities"]["Slower Attack"]["ranks"][0]["spd"]


def test_beasts_with_levels_zones_coords_and_marks(db):
    beasts = {b["id"]: b for b in db["beasts"]}
    assert set(beasts) == {b["id"] for b in BEASTS}
    raw = next(b for b in BEASTS if "c" in b and len(b["t"]) > 1)
    b = beasts[raw["id"]]
    assert b["name"]["en"] == raw["en"] and b["family"] == raw["f"]
    assert b["level"] == [raw["l1"], raw["l2"]] and b["speed_s"] == raw["s"] and b["rank"] == raw["r"]
    assert b["zones"] == [z["z"] for z in raw["z"]]
    assert b["coords"] == {zone: [list(p) for p in pts] for zone, pts in raw["c"].items()}
    marks = {t["ability"]: t for t in b["taught"]}
    for ability, rank, code in raw["t"]:
        assert marks[ability]["rank"] == rank and marks[ability]["mark"] == code
    beta = next(t for t in b["taught"] if t["mark"] == "p")
    assert beta["label"] == "beta" and beta["certainty"] in ("probable", "suppose") and beta["meaning"]


def test_mark_b_is_shown_as_question_and_confirmation_codes_translated(db):
    beasts = {b["id"]: b for b in db["beasts"]}
    b_mark = next(t for b in db["beasts"] for t in b["taught"] if t["mark"] == "b")
    assert b_mark["label"] == "?" and b_mark["certainty"] == "suppose"
    for raw in BEASTS:
        conf = beasts[raw["id"]]["confirmation"]
        assert conf["code"] == raw["cf"] and conf["meaning"]
    meanings = {beasts[r["id"]]["confirmation"]["meaning"] for r in BEASTS}
    assert len(meanings) == len({r["cf"] for r in BEASTS})  # un sens par code


def test_community_map_dated_with_counts_only(db):
    community = db["community"]
    assert community["date"] == COMMUNITY["date"] and community["players"] == COMMUNITY["players"]
    for npc, raw in COMMUNITY["obs"].items():
        entry = community["beasts"][str(npc)]
        assert entry["reporters"] == len(raw["rp"])
        assert entry["level"] == [raw["l1"], raw["l2"]] and entry["names"] == raw["n"]
        for map_id, points in raw["p"].items():
            got = entry["positions"][str(map_id)]
            assert [(p["x"], p["y"], p["t"], p["n"]) for p in got] == [tuple(p[:4]) for p in points]
    assert "votes" not in community


def test_missing_addon_is_a_readable_error(tmp_path):
    with pytest.raises(PathNotFoundError):
        read_bestiary(tmp_path / "ForeverBestiary")


# --- Sauvegarde --------------------------------------------------------------------------------------


def test_saved_observations_and_my_pets(saved):
    assert saved["schema"] == SV["schema"]
    npc, raw = next(iter(SV["obs"].items()))
    obs = saved["observations"][str(npc)]
    assert obs["reporters"] == raw["nrp"] and obs["mine"] is True and obs["names"] == raw["n"]
    point = obs["positions"]["1413"][0]
    assert point["me"] is True and (point["x"], point["y"]) == tuple(raw["p"][1413][0][:2])
    character = next(iter(SV["pets"]))
    assert saved["pets"][character]["active"][0]["family"] == SV["pets"][character]["active"][0]["fam"]
    assert saved["history"][str(next(iter(SV["history"])))]["character"] == character
    assert [f["id"] for f in saved["feed"]] == [f["id"] for f in SV["feed"]]


def test_no_third_party_string_survives_the_reading(db, saved):
    rendered = json.dumps({"db": db, "saved": saved}, ensure_ascii=False)
    leaks = sorted(s for s in third_party_strings() if s in rendered)
    assert leaks == []
    assert "peers" not in saved and "petGuids" not in saved and "likes" not in saved and "votes" not in saved
    assert all("who" not in f for f in saved["feed"])
    assert all("rp" not in o for o in saved["observations"].values())


def test_unknown_saved_field_is_dropped(tmp_path):
    # liste blanche : un champ ajouté par une version future de l'addon n'est jamais rendu
    text = SAVED.read_text(encoding="utf-8").replace('["schema"] = 2,', '["schema"] = 2,\n["nouveau"] = "NomFutur",', 1)
    path = tmp_path / "ForeverBestiary.lua"
    path.write_bytes(text.encode("utf-8"))
    assert "NomFutur" not in json.dumps(read_bestiary_saved(path), ensure_ascii=False)


def test_missing_saved_file_is_a_readable_error(tmp_path):
    with pytest.raises(PathNotFoundError):
        read_bestiary_saved(tmp_path / "ForeverBestiary.lua")
