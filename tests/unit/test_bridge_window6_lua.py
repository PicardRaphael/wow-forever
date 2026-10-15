"""CJ1, bloc 6a (décision 280, maquettes `tasks/CJ1-maquettes.md` acceptées le 2026-10-15) : nouvelle fenêtre de
ForeverBridge sous lupa.lua51. Barre latérale à gauche (Chat, Feuille de route, Talents, Équipement, Exports, Mises à
jour, Aide), un écran à la fois ; 640 × 440 par défaut, redimensionnable dès 520 × 380 ; barre d'actions courte et
menu « Plus ▾ » (boutons du pont gardés sous leur nom) ; rangée de réponses qui passe à la ligne sans chevauchement à
toutes les largeurs ; assistant de feuille de route (type de route, niveaux, donjons, quêtes de classe) qui envoie la
même demande que le chat ; écran Équipement (choix du niveau, « En faire une route ») ; couleur d'accent et police
d'EllesmereUI lues sans rien y écrire ; aide d'accueil une fois ; ancienne fenêtre derrière `/fv classique`.

Personnage du client simulé et cartes synthétiques (aucune règle de jeu)."""

import itertools

import pytest
from test_bridge_addon_lua import Game
from test_bridge_exports_lua import LINKS, answered
from test_bridge_p06b_g_lua import Publisher, card
from test_bridge_reply_lua import fill, reply
from test_bridge_send_lua import MAGE_TALENTS, sent, type_and_enter, with_buttons
from test_bridge_window_lua import history, window

from forever.bridge.codec import decode_band

pytest.importorskip("lupa")

NAV = ("chat", "route", "talents", "gear", "exports", "updates", "help")
NAV_LABELS = ("Chat", "Feuille de route", "Talents", "Équipement", "Exports", "Mises à jour", "Aide")
SCREENS = ("chat", "route", "talents", "gear", "exports")
ACCENT = """
EUI = { writes = {}, calls = {} }
EllesmereUI = {}
function EllesmereUI.ResolveActiveAccent() return 0.1, 0.6, 0.9 end
function EllesmereUI.GetFontPath(key) EUI.calls[#EUI.calls + 1] = "font"; return "Fonts\\\\Fixture.ttf" end
function EllesmereUI.SwitchProfile(name) EUI.calls[#EUI.calls + 1] = "switch" end
function EllesmereUI.RegAccent(entry) EUI.calls[#EUI.calls + 1] = "reg" end
"""


def g(game, name):
    return game.lua.globals()[name]


def click(game, name):
    widget = g(game, name)
    assert widget is not None, name
    widget.scripts.OnClick(widget)


def visible(game, name) -> bool:
    widget = g(game, name)
    return widget is not None and widget.IsVisible(widget)


def text(game, name) -> str:
    widget = g(game, name)
    return str(widget.GetText(widget))


def opened(**kwargs):
    game = with_buttons(Game(**kwargs))
    game.slash("/fv")
    return game


def resize(game, width, height=440):
    frame = window(game)
    frame.SetSize(frame, width, height)
    frame.scripts.OnSizeChanged(frame, width, height)


def boxes(game, names):
    """(gauche, droite, haut) de chaque widget montré, d'après son ancre TOPLEFT et sa largeur."""
    out = []
    for name in names:
        widget = g(game, name)
        if widget is None or not widget.IsShown(widget):
            continue
        point = widget.points[1]
        assert point.point == "TOPLEFT", name
        out.append((point.x, point.x + widget.GetWidth(widget), point.y))
    return out


# --- 1. fenêtre et navigation --------------------------------------------------------------------------------


def test_sidebar_lists_the_seven_entries_in_order():
    game = opened()
    assert visible(game, "ForeverBridgeNav")
    tops = []
    for key, label in zip(NAV, NAV_LABELS, strict=True):
        assert visible(game, "ForeverBridgeNav_" + key), key
        assert text(game, "ForeverBridgeNav_" + key).startswith(label)
        tops.append(g(game, "ForeverBridgeNav_" + key).points[1].y)
    assert tops == sorted(tops, reverse=True)  # de haut en bas


def test_default_size_and_resize_bounds():
    game = opened()
    frame = window(game)
    assert (frame.GetWidth(frame), frame.GetHeight(frame)) == (640, 440)
    assert (frame.minWidth, frame.minHeight) == (520, 380)


def test_one_screen_at_a_time_and_chat_first():
    game = opened()
    assert visible(game, "ForeverBridgeHistory") and visible(game, "ForeverBridgeInput")
    for key in SCREENS:
        click(game, "ForeverBridgeNav_" + key)
        for other in SCREENS:
            assert visible(game, "ForeverBridgeScreen_" + other) == (other == key), (key, other)
    click(game, "ForeverBridgeNav_chat")
    assert visible(game, "ForeverBridgeHistory")


def test_more_menu_holds_the_other_actions_without_overlap():
    game = opened()
    assert visible(game, "ForeverBridgeMoreButton") and not visible(game, "ForeverBridgeMore")
    click(game, "ForeverBridgeMoreButton")
    assert visible(game, "ForeverBridgeMore")
    names = ["ForeverBridgeNewButton", "ForeverBridgePasteButton", "ForeverBridgeButton_leveling",
             "ForeverBridgeButton_pvp", "ForeverBridgeButton_update"]  # fmt: skip
    for name in names:
        assert visible(game, name), name
    tops = sorted((-y for _, _, y in boxes(game, names)))
    assert all(b - a >= 22 for a, b in itertools.pairwise(tops))  # une ligne par action
    click(game, "ForeverBridgeNewButton")
    assert not visible(game, "ForeverBridgeMore")  # le menu se referme après une action


def test_bar_buttons_keep_their_names_and_behaviour():
    game = opened()
    click(game, "ForeverBridgeButton_talents")
    _, record = sent(game)
    assert record.text == MAGE_TALENTS and record.flags == frozenset({"b=talents"})


@pytest.mark.parametrize("width", [520, 560, 600, 640, 760, 900, 1200, 1920])
def test_answer_row_wraps_without_overlap_at_every_width(width):
    game = opened()
    labels = ["Trois niveaux de plus", "Cinq niveaux de plus", "Dix niveaux de plus", "Valider et livrer"]
    choices = {
        "prompt": "Combien ?",
        "buttons": [{"label": t, "action": f"choice:x.{i}"} for i, t in enumerate(labels)],
    }
    fill(game, [reply(game, "done", text="Aperçu", provenance="p", choices=choices)])
    type_and_enter(game, "Prépare ma feuille de route")
    game.stub.Advance(4)
    resize(game, width)
    shown = boxes(game, [f"ForeverBridgeAnswer{i}" for i in range(1, 5)])
    assert len(shown) == 4
    limit = g(game, "ForeverBridgeAnswers").GetWidth(g(game, "ForeverBridgeAnswers"))
    assert limit > 0 and all(right <= limit for _, right, _ in shown)
    for i, (left, right, top) in enumerate(shown):
        for other_left, other_right, other_top in shown[i + 1 :]:
            assert top != other_top or right <= other_left or other_right <= left


# --- 2. assistant de feuille de route ------------------------------------------------------------------------


def test_route_assistant_sends_a_leveling_route_with_its_choices():
    game = opened()
    click(game, "ForeverBridgeNav_route")
    assert "Jen" in text(game, "ForeverBridgeRouteWho")
    start = int(text(game, "ForeverBridgeRouteFromValue"))
    assert start == 19  # niveau du personnage simulé
    end = int(text(game, "ForeverBridgeRouteToValue"))
    click(game, "ForeverBridgeRouteToUp")
    assert int(text(game, "ForeverBridgeRouteToValue")) == end + 1
    click(game, "ForeverBridgeRouteClass")  # quêtes de classe : non
    click(game, "ForeverBridgeRouteCompute")
    _, record = sent(game)
    assert record.flags == frozenset({"b=route", f"lv={start}-{end + 1}", "cq=no"})
    assert f"{start}" in record.text and f"{end + 1}" in record.text
    assert visible(game, "ForeverBridgeHistory")  # l'aperçu arrive dans le chat


def test_route_levels_stay_ordered():
    game = opened()
    click(game, "ForeverBridgeNav_route")
    for _ in range(60):
        click(game, "ForeverBridgeRouteToDown")
    assert int(text(game, "ForeverBridgeRouteToValue")) == int(text(game, "ForeverBridgeRouteFromValue")) + 1
    for _ in range(60):
        click(game, "ForeverBridgeRouteFromDown")
    assert int(text(game, "ForeverBridgeRouteFromValue")) == 1


def test_route_assistant_other_types_send_a_plain_question():
    game = opened()
    click(game, "ForeverBridgeNav_route")
    click(game, "ForeverBridgeRouteType_reputation")
    click(game, "ForeverBridgeRouteCompute")
    assert decode_band(game.screen_image()) is None  # faction manquante : rien n'est envoyé
    assert any("faction" in line for line in history(game))
    click(game, "ForeverBridgeNav_route")
    box = g(game, "ForeverBridgeRouteTarget")
    box.SetText(box, "Darkspear Raiders")
    click(game, "ForeverBridgeRouteCompute")
    _, record = sent(game)
    assert "réputation" in record.text and "Darkspear Raiders" in record.text and record.flags == frozenset()
    click(game, "ForeverBridgeNav_route")
    click(game, "ForeverBridgeRouteType_gear")
    click(game, "ForeverBridgeRouteCompute")
    _, record = sent(game)
    assert "route d'équipement" in record.text and record.flags == frozenset()


# --- 3. écrans Talents, Équipement, Exports, Mises à jour ------------------------------------------------------


def test_talents_screen_asks_the_same_question_as_the_button():
    game = opened()
    click(game, "ForeverBridgeNav_talents")
    click(game, "ForeverBridgeTalentsNext")
    _, record = sent(game)
    assert record.text == MAGE_TALENTS and record.flags == frozenset({"b=talents"})


def test_gear_screen_level_choice_and_make_a_route():
    game = opened()
    click(game, "ForeverBridgeNav_gear")
    assert int(text(game, "ForeverBridgeGearLevelValue")) == 19
    click(game, "ForeverBridgeGearLevelDown")
    click(game, "ForeverBridgeGearList")
    _, record = sent(game)
    # essai CJ-6 : action traitée par le pont sans le modèle (une seule sortie de l'outil, au niveau choisi)
    assert record.flags == frozenset({"a=gear_level:18"}) and record.text == ""
    assert any("niveau 18" in line for line in history(game))
    click(game, "ForeverBridgeNav_gear")
    click(game, "ForeverBridgeGearRoute")
    _, record = sent(game)
    # bloc 4c : action traitée par le pont sans le modèle (route des objets obtenables au niveau choisi)
    assert record.flags == frozenset({"a=gear_route:18"}) and record.text == ""


def test_exports_screen_lists_the_session_links_with_a_copy_button():
    game = Game()
    answered(game, links=LINKS)
    click(game, "ForeverBridgeNav_exports")
    assert "Talents Forever" in text(game, "ForeverBridgeExport1Label")
    click(game, "ForeverBridgeExport2Copy")
    box = g(game, "ForeverBridgeCopyBox")
    assert box.IsVisible(box) and str(box.GetText(box)) == LINKS[1]["text"]


def test_updates_entry_counts_the_same_cards_and_opens_the_panel():
    game = opened()
    Publisher(game)([card("a", "s1"), card("b", "s2")])
    assert text(game, "ForeverBridgeNav_updates") == "Mises à jour (2)"
    assert "(2)" in text(game, "ForeverBridgeCardsButton")
    click(game, "ForeverBridgeNav_updates")
    assert visible(game, "ForeverBridgePanel")


# --- 4. thème, accueil, ancienne fenêtre, règles ---------------------------------------------------------------


def test_theme_reads_ellesmere_accent_and_font_without_writing():
    game = opened(prelude=ACCENT)
    selected = g(game, "ForeverBridgeNavSelected")
    assert list(selected.color.values())[:3] == pytest.approx([0.1, 0.6, 0.9])
    calls = list(game.lua.eval("EUI.calls").values())
    assert "switch" not in calls and "reg" not in calls  # rien d'écrit chez EllesmereUI
    assert g(game, "ForeverBridgeNav_chatLabel").fontPath == "Fonts\\Fixture.ttf"
    plain = opened()
    assert list(g(plain, "ForeverBridgeNavSelected").color.values())[:3] != pytest.approx([0.1, 0.6, 0.9])


def test_welcome_is_shown_once():
    game = opened()
    assert visible(game, "ForeverBridgeWelcome")
    click(game, "ForeverBridgeWelcomeOk")
    assert not visible(game, "ForeverBridgeWelcome") and game.lua.globals().ForeverBridgeDB.welcomed
    game.slash("/fv")
    game.slash("/fv")
    assert not visible(game, "ForeverBridgeWelcome")
    click(game, "ForeverBridgeNav_help")
    assert visible(game, "ForeverBridgeWelcome")


def test_classic_window_behind_fv_classique():
    game = opened()
    game.slash("/fv classique")
    assert game.lua.globals().ForeverBridgeDB.classic
    assert any("/reload" in line for line in history(game))
    saved = {"schema": 1, "session": "abcd1234", "next_id": 1, "classic": True}
    old = opened(saved=saved)
    frame = window(old)
    assert (frame.GetWidth(frame), frame.GetHeight(frame)) == (520, 360)
    assert g(old, "ForeverBridgeNav") is None and g(old, "ForeverBridgeMoreButton") is None
    assert visible(old, "ForeverBridgeButton_talents") and visible(old, "ForeverBridgeNewButton")
    old.slash("/fv classique")
    assert not old.lua.globals().ForeverBridgeDB.classic


def test_no_forbidden_call_through_every_screen():
    game = opened(prelude=ACCENT)
    for key in NAV:
        click(game, "ForeverBridgeNav_" + key)
    click(game, "ForeverBridgeMoreButton")
    resize(game, 520, 380)
    assert len(game.stub.forbidden) == 0


def test_answer_row_waits_for_the_chat_screen():
    game = opened()
    click(game, "ForeverBridgeNav_gear")
    choices = {"prompt": "", "buttons": [{"label": "Valider et livrer", "action": "route_deliver"}]}
    fill(game, [reply(game, "done", text="Aperçu", provenance="p", choices=choices)])
    type_and_enter(game, "Prépare ma feuille de route")
    click(game, "ForeverBridgeNav_gear")
    game.stub.Advance(4)
    assert not visible(game, "ForeverBridgeAnswers")  # jamais par-dessus un autre écran
    click(game, "ForeverBridgeNav_chat")
    assert visible(game, "ForeverBridgeAnswers")


def test_updates_entry_without_cards_says_so():
    game = opened()
    assert text(game, "ForeverBridgeNav_updates") == "Mises à jour"
    click(game, "ForeverBridgeNav_updates")
    assert any("aucune mise à jour" in line.lower() for line in history(game))


def test_gear_screen_level_range():
    # bloc 4c : « jusqu'au niveau » ; une tranche part en a=gear_level:<de>-<à>, un seul niveau en a=gear_level:<N>
    game = opened()
    click(game, "ForeverBridgeNav_gear")
    assert int(text(game, "ForeverBridgeGearToValue")) == 19
    click(game, "ForeverBridgeGearToUp")
    click(game, "ForeverBridgeGearToUp")
    click(game, "ForeverBridgeGearList")
    _, record = sent(game)
    assert record.flags == frozenset({"a=gear_level:19-21"})
    click(game, "ForeverBridgeNav_gear")
    for _ in range(5):
        click(game, "ForeverBridgeGearToDown")
    assert int(text(game, "ForeverBridgeGearToValue")) == 19  # jamais sous le niveau de départ
    click(game, "ForeverBridgeGearLevelUp")
    assert int(text(game, "ForeverBridgeGearToValue")) == 20  # le haut de la tranche suit le départ
