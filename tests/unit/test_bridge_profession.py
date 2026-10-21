"""Assistant « Métier » du pont (plan « Sources d'abord », reste de l'étape b ; décisions 272 et 288) : le type de
route Métier de ForeverBridge envoie l'action `a=profession` (sans identifiant) ; le pont répond sans le modèle, pour
chaque métier envoyé par le jeu (`professions` du contexte, nom et rang), avec les recettes de SkillUp Forever qui font
encore monter le métier (orange puis jaune), la fraîcheur de la source et le rappel de `/skillup` ; un métier que
SkillUp ne couvre pas (Pêche, Secourisme, nom d'un client traduit) est dit non couvert, sans faire échouer la réponse.

Addon SkillUp fabriqué (`test_skillup.write_skillup`) ; recettes et noms inventés."""

from test_bridge_choices import setup_bridge
from test_skillup import write_skillup

from forever.bridge.actions import parse_action


def test_profession_is_an_action_without_identifier():
    assert parse_action("a=profession") == ("profession", None)
    assert parse_action("a=profession:Alchemy") is None


def test_reply_lists_recipes_per_profession(tmp_path, make_deps):
    from forever.bridge.professions import profession_reply

    deps = make_deps(wow_dir=write_skillup(tmp_path))
    text = profession_reply(deps, {"professions": "Métier Test:35:75,Fishing:20:75"})
    assert "Métier Test" in text and "rang 35" in text
    assert text.index("Recette Deux") < text.index("Recette Un")  # orange d'abord, puis jaune
    assert "Recette Grise" not in text and "/skillup" in text
    assert "Fishing" in text and "non couvert" in text  # métier absent de SkillUp : dit, sans échec


def test_reply_without_professions_or_addon(tmp_path, make_deps):
    from forever.bridge.professions import profession_reply

    deps = make_deps(wow_dir=write_skillup(tmp_path))
    assert "aucun métier" in profession_reply(deps, {})
    empty = make_deps(wow_dir=tmp_path / "vide")
    assert "SkillUp Forever" in profession_reply(empty, {"professions": "Alchemy:1:75"})


def test_action_is_answered_without_the_model(tmp_path):
    (tmp_path / "bridge").mkdir()
    bridge, _addons, agent, send, _cards = setup_bridge(tmp_path / "bridge")
    seen = []

    def router(context):
        seen.append(dict(context))
        return "## Métiers\n- réponse fabriquée"

    bridge.profession_router = router
    before = len(agent.calls)
    reply = send(flags={"a=profession"}, text="")
    assert len(agent.calls) == before and seen and "réponse fabriquée" in reply.text
