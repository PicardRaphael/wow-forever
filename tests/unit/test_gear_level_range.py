"""Bloc 4c : équipement pour une tranche de niveaux (« par niveau du 10 au 14 ») : une ligne par emplacement, un
segment par palier où l'objet visé change (pas une liste par niveau) ; action `a=gear_level:<de>-<à>` du pont sans le
modèle ; CLI `--to`, outil `to_level` ; tranche à l'envers refusée (« niveau invalide »).

Valeurs : addon GearQuest fabriqué dans `tmp_path` (Prêtre : ordre de GearQuest, sans reclassement), contexte
synthétique. Aucun chiffre de jeu ici."""

import pytest
from test_bridge_choices import setup_bridge

from forever.bridge import gear_level
from forever.gear import gear_report

LOW, HIGH = 10, 14
# objet : (emplacement, niveau bas, niveau haut du choix de GearQuest, rang)
ITEMS = {
    940001: ("Hands", LOW - 2, LOW + 1, 1),
    940002: ("Hands", LOW + 2, HIGH + 1, 1),
    940003: ("Feet", LOW - 2, HIGH + 2, 1),
}


def wow_dir(tmp_path):
    folder = tmp_path / "wow" / "Interface" / "AddOns" / "GearQuestForever_PRIEST"
    folder.mkdir(parents=True)
    facts = "\n".join(
        f'    [{i}]={{name="Fixture {i}",quality=2,reqLevel={low},sourceType="vendor",instructions="Bought here."}},'
        for i, (_, low, _, _) in ITEMS.items()
    )
    picks = "\n".join(
        f'    {{{i},"{slot}",{low},{high},{rank},"holy","Alliance",1.0}},'
        for i, (slot, low, high, rank) in ITEMS.items()
    )
    (folder / "Data.Priest.generated.lua").write_text(
        f"local GQ = GearQuest\nGQ.Data.priestItemFacts = {{\n{facts}\n}}\nGQ.Data.priestPicks = {{\n{picks}\n}}\n",
        encoding="utf-8",
    )
    return tmp_path / "wow"


CONTEXT = {"name": "Go", "class": "PRIEST", "race": "Human", "faction": "Alliance", "level": "1"}


def test_range_gives_one_segment_per_change(tmp_path, make_deps):
    deps = make_deps(wow_dir=wow_dir(tmp_path), offline=True)
    doc = gear_report(deps, "leveling", class_name="Priest", level=LOW, to_level=HIGH, faction="alliance")
    segments = {(s["slot"], s["from"], s["to"], s["item"]) for s in doc["segments"]}
    assert segments == {("Hands", LOW, LOW + 1, 940001), ("Hands", LOW + 2, HIGH, 940002), ("Feet", LOW, HIGH, 940003)}


@pytest.fixture
def send(tmp_path, make_deps):
    deps = make_deps(wow_dir=wow_dir(tmp_path), offline=True)
    (tmp_path / "bridge").mkdir()
    bridge, _addons, _agent, send, _cards = setup_bridge(tmp_path / "bridge")
    bridge.gearer = lambda context, level: gear_level.gear_level_reply(deps, CONTEXT, level)
    return send


def test_range_action_reply(send):
    text = send(flags={f"a=gear_level:{LOW}-{HIGH}"}, text="").text
    hands = next(line for line in text.splitlines() if line.startswith("- Mains :"))
    assert f"niveaux {LOW} à {LOW + 1}" in hands and f"niveaux {LOW + 2} à {HIGH}" in hands
    assert hands.index("940001") < hands.index("940002")
    assert f"Équipement du niveau {LOW} au niveau {HIGH}" in text


def test_reversed_range_is_refused(send):
    assert "niveau invalide" in send(flags={f"a=gear_level:{HIGH}-{LOW}"}, text="").text
