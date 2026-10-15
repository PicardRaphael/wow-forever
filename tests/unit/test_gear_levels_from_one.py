"""Bug de l'écran Équipement (2026-10-15) : « Mon équipement du niveau 1 au niveau 15 » répondait « Équipement non
calculé : InvalidArgumentError: Poids du Mage impossibles au niveau 1 : frostbolt n'est pas appris au niveau 1 ».

1. Aux niveaux où la rotation de la spécialisation n'est pas encore apprise, les poids se calculent avec un sort
   réellement appris à ce niveau (Fireball pour le Mage au niveau 1) ; à défaut, ces niveaux gardent l'ordre de
   GearQuest ; la réponse le dit en une phrase.
2. Un échec sur une partie de la tranche ne fait jamais tomber la réponse : les autres niveaux s'affichent, le manque
   est dit en mots de joueur ; jamais de nom d'exception ni de message technique dans le chat, pour aucun bouton.
3. Chaque classe et chaque spécialisation calculée, sur une tranche partant du niveau 1.

Valeurs : addons fabriqués (`test_gear_level_reply.wow_dir`), poids du Mage calculés par le moteur sur les données du
dépôt, contexte synthétique. Aucun chiffre de jeu ici."""

import json

import pytest
from test_bridge_choices import setup_bridge
from test_bridge_loop import FakeAgent
from test_gear_level_reply import wow_dir

from forever import gear
from forever.bridge.agent import AgentResult
from forever.bridge.gear_level import gear_level_reply
from forever.gear import gear_report

LOW, HIGH = 1, 15
CLASSES = ("WARRIOR", "PALADIN", "HUNTER", "ROGUE", "PRIEST", "SHAMAN", "MAGE", "WARLOCK", "DRUID")
MAGE_SPECS = ("frost-mage", "fire-mage", "arcane-mage")  # spécialisations dont le moteur calcule les poids
TECHNICAL = ("Error", "Exception", "Traceback", "boom", "__", "frostbolt", "arcane_blast")


def context(cls):
    return {"name": "Go", "class": cls, "race": "Gnome", "faction": "Alliance", "level": "1"}


@pytest.mark.parametrize("spec", MAGE_SPECS)
def test_mage_specs_from_level_one_use_a_learned_spell(tmp_path, make_deps, spec):
    deps = make_deps(wow_dir=wow_dir(tmp_path), offline=True)
    doc = gear_report(deps, "leveling", class_name="Mage", race="Gnome", level=LOW, to_level=HIGH, spec=spec,
                      faction="alliance")  # fmt: skip
    rotations = doc["rotations"]
    assert set(rotations) == {str(lv) for lv in range(LOW, HIGH + 1)}
    assert all(r is None or r in ("fire", "frost", "arcane") for r in rotations.values())
    assert rotations[str(LOW)] == "fire"  # seul sort de dégâts appris au niveau 1 parmi les rotations
    if spec == "fire-mage":
        # décision 282 : la réponse dit aussi le build des poids ; aucune phrase « pas encore appris » pour Feu
        assert set(rotations.values()) == {"fire"} and not any("pas encore appris" in n for n in doc["weights_notes"])
    else:
        assert doc["weights_notes"] and any("pas encore appris" in n for n in doc["weights_notes"])


@pytest.mark.parametrize("cls", CLASSES)
def test_every_class_from_level_one(tmp_path, make_deps, cls):
    deps = make_deps(wow_dir=wow_dir(tmp_path, token=cls), offline=True)
    text, _links = gear_level_reply(deps, context(cls), (LOW, HIGH))
    assert f"## Équipement du niveau {LOW} au niveau {HIGH}" in text
    assert not any(word in text for word in TECHNICAL)
    if cls == "MAGE":
        assert "pas encore appris" in text  # Frostbolt avant son niveau : la réponse le dit
    else:
        assert "ordre de GearQuest" in text


def test_a_failing_level_never_drops_the_whole_range(tmp_path, make_deps, monkeypatch):
    deps = make_deps(wow_dir=wow_dir(tmp_path), offline=True)
    real = gear.mage_weights

    def flaky(deps_, *, level, **kwargs):
        if level == 9:
            raise RuntimeError("boom")
        return real(deps_, level=level, **kwargs)

    monkeypatch.setattr(gear, "mage_weights", flaky)
    text, _ = gear_level_reply(deps, context("MAGE"), (8, 12))
    assert "Fixture 930002" in text  # les autres niveaux restent
    assert "niveau 9" in text and not any(word in text for word in TECHNICAL)


def no_technical(text):
    return not any(word in text for word in TECHNICAL)


def test_no_technical_message_reaches_the_chat(tmp_path):
    def broken(*_args, **_kwargs):
        raise RuntimeError("boom Traceback")

    failing = AgentResult(text="", session_id=None, is_error=True, error="RuntimeError: boom")
    bridge, _addons, _agent, send, _cards = setup_bridge(tmp_path, agent=FakeAgent(results=[failing]))
    bridge.gearer = bridge.gear_router = broken
    bridge.exporter = broken
    routes = tmp_path / "routes"
    routes.mkdir()
    (routes / "bad.json").write_text("{tronqué", encoding="utf-8")
    bridge.routes_dir = routes
    texts = [
        send(flags={"a=gear_level:10"}, text="").text,
        send(flags={"a=gear_level:1-15"}, text="").text,
        send(flags={"a=gear_route:10"}, text="").text,
        send(flags={"a=exports"}, text="").text,
        send(flags={"a=route_deliver"}, text="").text,
        send(text="Une question").text,
    ]
    for text in texts:
        assert text and no_technical(text), text
    journal = "\n".join(p.read_text(encoding="utf-8") for p in (tmp_path / "journal").glob("*.jsonl"))
    assert "boom" in journal  # le détail technique reste dans le journal du pont
    assert json.loads(journal.splitlines()[0])  # journal lisible
