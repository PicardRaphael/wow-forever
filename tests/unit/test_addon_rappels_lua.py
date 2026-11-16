"""RA1 : addon ForeverRappels sous lupa.lua51 (client simulé `tests/fixtures/bridge/wow_stub.lua`) : rappel d'aura
en combat (aura attendue absente ou aura interdite présente) et hors combat (familier absent ou mort), icône
déplaçable gardée d'une session à l'autre, page dans EllesmereUI (`EllesmereUI.RegisterPlugin`, API publique),
lecture des auras à trois états (présente, absente, inconnue : nil en combat, valeur secrète ou panne) avec repli
sur l'état d'avant le combat et sur les sorts vus lancés. Données synthétiques (identifiants inventés), aucune règle
de jeu."""

import pytest
from conftest import REPO_ROOT

lupa = pytest.importorskip("lupa")
from lupa import lua51

STUB = REPO_ROOT / "tests" / "fixtures" / "bridge" / "wow_stub.lua"
ADDON = REPO_ROOT / "addon" / "ForeverRappels"
HAWK, HAWK2, CHEETAH, PACK, BEAST = 900001, 900002, 900010, 900020, 900030
DATA = f"""
ForeverRappelsData = {{
    game_version = "9.9.9.1", data_sha = "abc123",
    groups = {{
        aspect_faucon = {{ name = "Faucon inventé", spells = {{ {HAWK}, {HAWK2} }} }},
        aspect_guepard = {{ name = "Guépard inventé", spells = {{ {CHEETAH} }} }},
        aspect_meute = {{ name = "Meute inventée", spells = {{ {PACK} }} }},
        aspect_bete = {{ name = "Bête inventée", spells = {{ {BEAST} }} }},
    }},
}}
"""
EUI = """
EUICalls = { registered = {} }
EllesmereUI = {
    RegisterPlugin = function(id, spec)
        if EUICalls.raise then error("panne simulée de RegisterPlugin") end
        table.insert(EUICalls.registered, { id = id, spec = spec })
        return not EUICalls.reject
    end,
    OpenPlugin = function(id) EUICalls.opened = id; return true end,
    IsSearchPrebuild = function() return false end,
}
-- Fabrique de widgets factice : enregistre chaque ligne construite.
FakeW = { rows = {} }
local function row(kind, text, get, set, extra)
    table.insert(FakeW.rows, { kind = kind, text = text, get = get, set = set, extra = extra })
    return {}, 30
end
function FakeW:SectionHeader(parent, text, y) return row("header", text) end
function FakeW:Toggle(parent, text, y, get, set) return row("toggle", text, get, set) end
function FakeW:Slider(parent, text, y, lo, hi, step, get, set) return row("slider", text, get, set, { lo, hi, step }) end
function FakeW:Button(parent, text, y, onClick) return row("button", text, nil, onClick) end
EllesmereUI.Widgets = FakeW
"""


class Game:
    """Client simulé avec ForeverRappels chargé comme le jeu le fait (données, fichier, SavedVariables, ADDON_LOADED,
    PLAYER_LOGIN, PLAYER_ENTERING_WORLD)."""

    def __init__(
        self,
        *,
        klass="HUNTER",
        saved=None,
        eui=False,
        reject=False,
        raise_=False,
        data=DATA,
        pet=True,
        auras=(),
        hidden_in_combat=False,
    ):
        self.lua = lua51.LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(STUB.read_bytes())
        self.stub = self.lua.globals().Stub
        self.stub.player["class"] = klass
        self.stub.aura_hidden_in_combat = hidden_in_combat
        if eui:
            self.lua.execute(EUI.encode("utf-8"))
            self.lua.globals().EUICalls.reject = reject
            self.lua.globals().EUICalls["raise"] = raise_
        if pet:
            self.set_pet(dead=False)
        self.set_auras(*auras)
        if data is None:
            data = (ADDON / "RappelsData.lua").read_text(encoding="utf-8")
        self.lua.execute(data.encode("utf-8"))
        self.lua.execute((ADDON / "ForeverRappels.lua").read_bytes(), "ForeverRappels", self.lua.table())
        if saved is not None:
            self.lua.globals().ForeverRappelsDB = self.lua.table_from(saved, recursive=True)
        self.fire("ADDON_LOADED", "ForeverRappels")
        self.fire("PLAYER_LOGIN")
        self.fire("PLAYER_ENTERING_WORLD")

    def fire(self, event, *args):
        self.stub.Fire(event, *args)

    def set_pet(self, *, dead=False):
        self.stub.units["pet"] = self.lua.table_from({"name": "FamilierInvente", "dead": dead})

    def no_pet(self):
        self.stub.units["pet"] = None
        self.fire("UNIT_PET", "player")

    def set_auras(self, *ids):
        self.stub.player.auras = self.lua.table_from([{"spellId": i} for i in ids], recursive=True)

    def auras(self, *ids):
        self.set_auras(*ids)
        self.fire("UNIT_AURA", "player")

    def enter_combat(self):
        self.fire("PLAYER_REGEN_DISABLED")
        self.stub.combat = True

    def leave_combat(self):
        self.stub.combat = False
        self.fire("PLAYER_REGEN_ENABLED")

    def cast(self, spell_id):
        self.fire("UNIT_SPELLCAST_SUCCEEDED", "player", "Cast-Invente", spell_id)

    def icon(self):
        return self.lua.globals().ForeverRappelsIcon

    def shown(self):
        icon = self.icon()
        return icon is not None and bool(icon.shown)

    def texture(self):
        return self.lua.globals().ForeverRappelsIconTexture.texture

    def db(self):
        return self.lua.globals().ForeverRappelsDB

    def printed(self):
        p = self.stub.printed
        return [p[i] for i in range(1, len(p) + 1)]

    def kits(self):
        return len(self.stub.kits)


# --- En combat -------------------------------------------------------------------------------------------------


def test_no_reminder_out_of_combat_when_the_pet_is_there():
    game = Game()
    assert not game.shown()


def test_combat_without_the_expected_aspect_shows_its_icon_and_plays_a_sound_once():
    game = Game()
    game.enter_combat()
    game.fire("UNIT_AURA", "player")
    assert game.shown()
    assert game.texture() == f"icon-{HAWK}"
    assert game.kits() == 1


def test_expected_aspect_put_on_in_combat_hides_the_icon():
    game = Game()
    game.enter_combat()
    game.auras(HAWK2)
    assert not game.shown()


def test_forbidden_aspect_in_combat_shows_the_icon_even_with_the_expected_one_missing_only():
    game = Game(auras=(CHEETAH,))
    game.enter_combat()
    assert game.shown()
    game.auras(HAWK)
    assert not game.shown()


def test_forbidden_aspect_alone_shows_the_icon():
    game = Game(auras=(HAWK, PACK))
    game.enter_combat()
    assert game.shown()


def test_leaving_combat_hides_the_combat_reminder():
    game = Game()
    game.enter_combat()
    assert game.shown()
    game.leave_combat()
    assert not game.shown()


# --- Hors combat -----------------------------------------------------------------------------------------------


def test_missing_pet_out_of_combat_shows_a_reminder():
    game = Game()
    game.no_pet()
    assert game.shown()
    game.set_pet()
    game.fire("UNIT_PET", "player")
    assert not game.shown()


def test_dead_pet_out_of_combat_shows_a_reminder():
    game = Game()
    game.set_pet(dead=True)
    game.fire("UNIT_PET", "player")
    assert game.shown()


def test_pet_rule_can_be_turned_off():
    game = Game(saved={"regles": {"hors_combat_familier": False}})
    game.no_pet()
    assert not game.shown()


def test_cheetah_out_of_combat_rule_is_off_by_default_and_can_be_turned_on():
    assert not Game().shown()
    game = Game(saved={"regles": {"hors_combat_guepard": True}})
    assert game.shown()
    assert game.texture() == f"icon-{CHEETAH}"
    game.auras(PACK)
    assert not game.shown()


# --- Lecture des auras incertaine (bloc 0) -----------------------------------------------------------------------


def test_nil_in_combat_is_not_read_as_missing_when_the_aspect_was_there_before():
    game = Game(auras=(HAWK,), hidden_in_combat=True)
    game.enter_combat()
    game.fire("UNIT_AURA", "player")
    assert not game.shown()


def test_hidden_auras_fall_back_on_the_state_before_combat_then_on_the_cast_seen():
    game = Game(auras=(CHEETAH,), hidden_in_combat=True)
    game.enter_combat()
    assert game.shown()
    game.fire("UNIT_AURA", "player")
    assert game.shown()
    game.cast(HAWK2)
    assert not game.shown()
    game.cast(CHEETAH)
    assert game.shown()


def test_secret_aura_values_are_unknown_not_present():
    game = Game(auras=(CHEETAH,))
    game.stub.secret["C_UnitAuras.GetPlayerAuraBySpellID"] = True
    game.enter_combat()
    game.fire("UNIT_AURA", "player")
    assert game.shown()
    game.cast(HAWK)
    assert not game.shown()


def test_failing_aura_api_raises_no_error():
    game = Game()
    game.stub.failing["C_UnitAuras.GetPlayerAuraBySpellID"] = True
    game.enter_combat()
    game.fire("UNIT_AURA", "player")
    game.cast(HAWK)
    assert not game.shown()


def test_secret_cast_spell_is_ignored():
    game = Game(auras=(CHEETAH,), hidden_in_combat=True)
    game.enter_combat()
    game.fire("UNIT_SPELLCAST_SUCCEEDED", "player", "Cast-Invente", game.stub.SECRET)
    assert game.shown()


# --- Autres classes, données absentes ----------------------------------------------------------------------------


def test_other_class_never_gets_a_reminder():
    game = Game(klass="MAGE", pet=False)
    game.enter_combat()
    game.fire("UNIT_AURA", "player")
    assert not game.shown()


def test_secret_class_gets_no_reminder_and_no_error():
    game = Game(pet=False)
    game.stub.secret["UnitClassBase"] = True
    game.fire("PLAYER_ENTERING_WORLD")
    game.enter_combat()
    assert not game.shown()


def test_placeholder_data_gives_no_reminder_and_says_so():
    game = Game(data=None)
    game.enter_combat()
    assert not game.shown()
    game.stub.Slash("/rappels")
    assert any("données" in str(line) for line in game.printed())


# --- Icône déplaçable, verrou, rien de cliquable ------------------------------------------------------------------


def test_icon_is_locked_click_through_and_not_a_secure_button():
    game = Game()
    icon = game.icon()
    assert icon.template is None
    assert not icon.mouse
    assert list(game.stub.forbidden.values()) == []


def test_unlock_shows_the_icon_to_place_it_and_the_position_is_kept():
    game = Game()
    game.stub.Slash("/rappels deverrou")
    icon = game.icon()
    assert icon.shown and icon.mouse and icon.movable
    icon.scripts.OnDragStart(icon)
    icon.points = game.lua.table_from([{"point": "CENTER", "relPoint": "CENTER", "x": 120, "y": -40}], recursive=True)
    icon.scripts.OnDragStop(icon)
    game.stub.Slash("/rappels verrou")
    assert not game.icon().mouse
    pos = game.db().pos
    assert (pos.point, pos.x, pos.y) == ("CENTER", 120, -40)

    again = Game(saved={"pos": {"point": "CENTER", "relPoint": "CENTER", "x": 120, "y": -40}})
    point, _rel, _relp, x, y = again.icon().GetPoint(again.icon())
    assert (point, x, y) == ("CENTER", 120, -40)


def test_test_command_shows_the_icon_then_it_follows_the_rules_again():
    game = Game()
    game.stub.Slash("/rappels test")
    assert game.shown()
    game.stub.Slash("/rappels test")
    assert not game.shown()


def test_icon_draws_no_colour_pixels():
    game = Game()
    game.enter_combat()
    assert list(game.stub.ShownTextures(game.icon()).values()) == []


# --- Page dans EllesmereUI ---------------------------------------------------------------------------------------


def registered(game):
    calls = game.lua.globals().EUICalls.registered
    return [calls[i] for i in range(1, len(calls) + 1)]


def test_plugin_is_registered_in_ellesmereui_with_rule_toggles():
    game = Game(eui=True)
    (call,) = registered(game)
    assert call.id == "ForeverRappels"
    spec = call.spec
    assert spec.label == "Rappels"
    module = spec.modules[1]
    assert module.key and module.title and module.pages[1]
    height = module.buildPage(module.pages[1], game.lua.table(), 0)
    assert height > 0
    rows = game.lua.globals().FakeW.rows
    toggles = [rows[i] for i in range(1, len(rows) + 1) if rows[i].kind == "toggle"]
    assert len(toggles) >= 3


def test_plugin_toggle_changes_the_rule():
    game = Game(eui=True)
    module = registered(game)[0].spec.modules[1]
    module.buildPage(module.pages[1], game.lua.table(), 0)
    rows = game.lua.globals().FakeW.rows
    pet = next(rows[i] for i in range(1, len(rows) + 1) if rows[i].kind == "toggle" and "amilier" in rows[i].text)
    assert pet.get() is True
    pet.set(False)
    assert game.db().regles.hors_combat_familier is False
    game.no_pet()
    assert not game.shown()


def test_plugin_rejected_or_failing_keeps_the_slash_command_and_raises_nothing():
    for kwargs in ({"reject": True}, {"raise_": True}):
        game = Game(eui=True, **kwargs)
        assert any("EllesmereUI" in str(line) for line in game.printed())
        game.stub.Slash("/rappels deverrou")
        assert game.icon().mouse


def test_without_ellesmereui_the_slash_command_still_works():
    game = Game()
    assert game.stub.Slash("/rappels")
    assert game.printed()


def test_slash_without_argument_opens_the_ellesmereui_page():
    game = Game(eui=True)
    game.stub.Slash("/rappels")
    assert game.lua.globals().EUICalls.opened == "ForeverRappels"


# --- Règles du dépôt ---------------------------------------------------------------------------------------------


def test_addon_passes_the_repository_rules():
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_addon", REPO_ROOT / "scripts" / "check_addon.py")
    assert spec and spec.loader
    check_addon = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check_addon)
    assert check_addon.check_addon(ADDON) == []
    toc = (ADDON / "ForeverRappels.toc").read_text(encoding="utf-8").splitlines()
    assert "## SavedVariables: ForeverRappelsDB" in toc
    assert "## OptionalDeps: EllesmereUI" in toc
    assert toc.index("RappelsData.lua") < toc.index("ForeverRappels.lua")


def test_saved_variable_rule_follows_the_toc_of_each_addon(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_addon", REPO_ROOT / "scripts" / "check_addon.py")
    assert spec and spec.loader
    check_addon = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check_addon)
    folder = tmp_path / "AutreAddon"
    folder.mkdir()
    (folder / "AutreAddon.toc").write_text("## Interface: 16001\n## SavedVariables: AutreDB\nAutre.lua\n", "utf-8")
    (folder / "Autre.lua").write_text("local db = AutreDB\n", encoding="utf-8")
    errors = check_addon.check_addon(folder)
    assert any("alias local de AutreDB" in e for e in errors)


# --- Après la revue : entrée en combat sur un client qui masque déjà les auras, son du familier -----------------


def test_auras_hidden_while_combat_starts_raise_no_false_alarm():
    game = Game(auras=(HAWK,), hidden_in_combat=True)
    game.stub.combat = True
    game.fire("PLAYER_REGEN_DISABLED")
    assert not game.shown()


def test_out_of_combat_reminder_plays_no_sound():
    game = Game()
    game.no_pet()
    assert game.shown()
    assert game.kits() == 0
