"""CJ1, décision 279 (registre I18) : acceptation automatique d'une feuille de route face au parcours gratuit de
RestedXP de la même race et de la même classe. Acceptée : même enchaînement de zones et au plus trois différences,
chacune expliquée (quête de classe, donjon avec ses quêtes, gain mesuré) ; sinon refusée, l'écart expliqué.

Valeurs : quêtes et zones fabriquées ici ; guides fabriqués (`tests/fixtures/rxp_guides`, syntaxe seulement, quêtes
de `tests/fixtures/route/route.json`). Aucun chiffre de jeu ici."""

import json
import shutil
from dataclasses import dataclass

from conftest import FIXTURES

from forever.cli import main
from forever.provenance import validate_provenance
from forever.route_check import MAX_DIFFERENCES, accept_route, zone_sequence

ADDONS = FIXTURES / "rxp_guides"


@dataclass(frozen=True)
class Q:  # quête fabriquée : seuls les champs lus par le contrôle
    id: int
    zone: int | None = 1
    class_quest: bool = False
    dungeon: str | None = None


QUESTS = {
    1: Q(1),
    2: Q(2),
    3: Q(3),
    4: Q(4),
    5: Q(5, zone=2),
    6: Q(6, class_quest=True),
    7: Q(7, dungeon="D"),
    8: Q(8, dungeon="D"),
    9: Q(9),
    10: Q(10),
}
NAMES = {1: "Vale", 2: "Hills"}


def _turnins(ids):
    return [(i, QUESTS[i].zone if i in QUESTS else None) for i in ids]


def test_zone_sequence_merges_consecutive_zones():
    assert zone_sequence(["A", "A", None, "B", "B", "A"]) == ["A", "B", "A"]


def test_same_route_is_accepted():
    res = accept_route(_turnins([1, 2, 3, 5]), _turnins([1, 2, 3, 5]), QUESTS, NAMES)
    assert res["accepted"] and res["differences"] == [] and res["zones_ours"] == ["Vale", "Hills"]


def test_explained_differences_within_the_limit_are_accepted():
    ours = _turnins([1, 2, 6, 7, 8, 3, 5])  # quête de classe + un donjon (deux quêtes, une seule différence)
    res = accept_route(ours, _turnins([1, 2, 3, 5]), QUESTS, NAMES)
    assert res["accepted"], res["explanation"]
    groups = {d["group"] for d in res["differences"]}
    assert len(groups) == 2 and all(d["explained"] for d in res["differences"])
    assert {d["reason"] for d in res["differences"]} == {"quête de classe", "donjon avec ses quêtes"}


def test_measured_gain_explains_a_quest_of_ours():
    gains = {9: 120.0}  # secondes gagnées par la quête 9, mesurées par la simulation
    res = accept_route(_turnins([1, 2, 9, 3, 5]), _turnins([1, 2, 3, 5]), QUESTS, NAMES, gains=gains)
    assert res["accepted"]
    assert res["differences"][0]["reason"].startswith("gain mesuré")


def test_unexplained_differences_refuse_the_route_with_the_gap():
    ours = _turnins([1, 9, 10, 3, 5])
    ref = _turnins([1, 2, 4, 3, 5, 99])  # 99 : quête absente de nos données
    res = accept_route(ours, ref, QUESTS, NAMES, dropped={99: "sans donneur positionné"})
    assert not res["accepted"]
    reasons = {d["quest"]: d["reason"] for d in res["differences"]}
    assert "sans donneur positionné" in reasons[99] and not any(d["explained"] for d in res["differences"])
    assert "différence" in res["explanation"]
    assert len(res["differences"]) > MAX_DIFFERENCES


def test_different_zone_sequence_refuses_the_route():
    res = accept_route(_turnins([1, 5, 2]), _turnins([1, 2, 5]), QUESTS, NAMES)
    assert not res["accepted"] and "zones" in res["explanation"]


def test_recette_cli(tmp_path, monkeypatch, capsys):
    root = tmp_path / "wow"
    shutil.copytree(FIXTURES / "addons" / "dungeons", root)
    shutil.copytree(ADDONS / "RXPGuides", root / "Interface" / "AddOns" / "RXPGuides")
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FOREVER_WOW_DIR", str(root))
    monkeypatch.setenv("FOREVER_OFFLINE", "1")
    argv = ["route", "recette", "--race", "Orc", "--class", "Mage", "--to", "5"]
    assert main([*argv, "--json"]) == 0
    raw = capsys.readouterr().out
    doc = json.loads(raw)
    assert validate_provenance(doc["provenance"]) == []
    row = doc["rows"][0]
    assert (row["race"], row["class"]) == ("Orc", "Mage")
    assert {"accepted", "zones_ours", "zones_reference", "differences", "explanation", "hours_ours"} <= set(row)
    assert "Secret" not in raw and "objective one" not in raw  # aucun texte de guide recopié
    assert main(argv) == 0
    assert "Orc" in capsys.readouterr().out
