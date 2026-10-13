"""T04d, bloc A : vrai Lua de ForeverLogger 0.4.0 exécuté sous lupa.lua51 avec le client simulé
`tests/fixtures/bridge/wow_stub.lua`. Chaque gain d'XP garde montant, cible (niveau, classification, PNJ), état de
l'XP et du repos, instance, groupe et carte ; les quêtes acceptées et rendues sont relevées (ID, `xpReward`) ; une API
en panne ou secrète ne casse rien ; aucune erreur Lua dans les gestionnaires. Valeurs synthétiques (entrées du client
simulé), aucune règle de jeu."""

import pytest
from conftest import FIXTURES, REPO_ROOT

lupa = pytest.importorskip("lupa")
from lupa import lua51

ADDON = REPO_ROOT / "addon" / "ForeverLogger"
STUB = FIXTURES / "bridge" / "wow_stub.lua"
GUID = "Player-0000-00000001"
MOB = "Bristleback Thornweaver"
MOB_GUID = "Creature-0-4170-1-28-3263-0000ABCDEF"


class Logger:
    """Client simulé avec ForeverLogger chargé comme le jeu le fait (fichier, SavedVariables, ADDON_LOADED,
    PLAYER_LOGIN, PLAYER_ENTERING_WORLD)."""

    def __init__(self, *, saved=None, unknown_events=(), failing=(), secret=(), player=None):
        self.lua = lua51.LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(STUB.read_bytes())
        self.stub = self.lua.globals().Stub
        for event in unknown_events:
            self.stub.unknown_events[event] = True
        for name in failing:
            self.stub.failing[name] = True
        for name in secret:
            self.stub.secret[name] = True
        for key, value in (player or {}).items():
            self.stub.player[key] = value
        self.lua.execute((ADDON / "ForeverLogger.lua").read_bytes(), "ForeverLogger", self.lua.table())
        if saved is not None:
            self.lua.globals().ForeverLoggerDB = self.lua.table_from(saved, recursive=True)
        self.fire("ADDON_LOADED", "ForeverLogger")
        self.fire("PLAYER_LOGIN")
        self.fire("PLAYER_ENTERING_WORLD")

    def fire(self, event, *args):
        self.stub.Fire(event, *args)

    def unit(self, unit, **fields):
        self.stub.units[unit] = self.lua.table_from(fields)

    def clear_unit(self, unit):
        self.stub.units[unit] = None

    def db(self):
        return self.lua.globals().ForeverLoggerDB

    def me(self):
        return self.db().characters[GUID]

    def entries(self, name):
        table = self.me()[name]
        return [table[i] for i in range(1, len(table) + 1)] if table is not None else []

    def errors(self):
        errors = self.db().errors
        return {k: (v.count, v.last) for k, v in errors.items()} if errors is not None else {}

    def kill(self, text, *, xp_after, rested_after=None):
        """Message de gain, puis mise à jour de l'XP comme le client l'envoie."""
        self.fire("CHAT_MSG_COMBAT_XP_GAIN", text)
        self.stub.player.xp = xp_after
        self.stub.player.rested = rested_after
        self.fire("PLAYER_XP_UPDATE", "player")
        self.fire("UPDATE_EXHAUSTION")


def to_py(value):
    if lua51.lua_type(value) == "table":
        return {k: to_py(v) for k, v in value.items()}
    return value


def test_kill_of_the_dead_target_keeps_amount_target_rest_instance_and_group():
    game = Logger(player={"xp": 400, "rested": 300, "rest_state": 1, "level": 12})
    game.unit("target", name=MOB, level=11, classification="normal", dead=True, guid=MOB_GUID, creature_type="Humanoid")
    game.kill(f"{MOB} dies, you gain 67 experience. (+33 exp Rested bonus)", xp_after=467, rested_after=267)
    (gain,) = game.entries("xp")
    assert gain.text.startswith(MOB) and gain.level == 12
    assert gain.amount == 67 and gain.kind == "monster" and gain.monster == MOB
    target = to_py(gain.target)
    assert target == {"name": MOB, "level": 11, "classification": "normal", "npc": 3263, "creature_type": "Humanoid",
                      "source": "target"}  # fmt: skip
    assert to_py(gain.state) == {"xp": 400, "max": 1000, "rested": 300, "rest_state": 1}
    assert gain.resting is False
    assert to_py(gain.instance) == {"inside": False, "type": "none"}
    assert to_py(gain.group) == {"size": 0, "raid": False}
    assert gain.map == 1436
    assert isinstance(gain.seq, int | float)
    states = game.entries("xp_states")
    after = [s for s in states if s.seq > gain.seq]
    assert after and after[0].xp == 467 and after[0].rested == 267 and after[0].reason == "xp"
    assert any(s.seq < gain.seq and s.xp == 400 and s.rested == 300 for s in states)  # état de la connexion
    assert game.errors() == {}


def test_kill_in_a_dungeon_in_a_group_keeps_instance_and_member_levels():
    game = Logger(player={"xp": 100, "level": 15})
    game.stub.instance = game.lua.table_from({"inside": True, "type": "party", "name": "Ragefire Chasm", "id": 389})
    game.stub.group = game.lua.table_from({"size": 3, "raid": False})
    game.unit("party1", name="Ami", level=14)
    game.unit("party2", name="Autre", level=17)
    game.unit("target", name="Ragefire Trogg", level=13, classification="normal", dead=True,
              guid="Creature-0-4170-389-28-11318-0000ABCDEF")  # fmt: skip
    game.kill("Ragefire Trogg dies, you gain 40 experience. (+4 group bonus)", xp_after=140)
    (gain,) = game.entries("xp")
    assert to_py(gain.instance) == {"inside": True, "type": "party", "name": "Ragefire Chasm", "id": 389}
    group = to_py(gain.group)
    assert group["size"] == 3 and group["raid"] is False
    assert sorted(group["levels"].values()) == [14, 17]
    assert gain.target.level == 13 and gain.target.npc == 11318


def test_kill_without_target_uses_a_dead_nameplate_then_recent_then_seen_levels():
    game = Logger(player={"xp": 0})
    game.unit("nameplate3", name=MOB, level=10, classification="normal", dead=True, guid=MOB_GUID)
    game.kill(f"{MOB} dies, you gain 50 experience.", xp_after=50)
    game.clear_unit("nameplate3")
    # Plaque retirée alors que l'unité était morte : rapprochée par le nom juste après.
    game.unit("nameplate4", name="Dire Mottled Boar", level=6, classification="normal", dead=True,
              guid="Creature-0-4170-1-28-3099-0000ABCDEF")  # fmt: skip
    game.fire("NAME_PLATE_UNIT_REMOVED", "nameplate4")
    game.clear_unit("nameplate4")
    game.kill("Dire Mottled Boar dies, you gain 20 experience.", xp_after=70)
    # Deux unités du même nom vues vivantes à des niveaux différents, aucune morte visible : niveaux vus rendus.
    game.unit("nameplate1", name="Durotar Tiger", level=7, classification="normal", dead=False)
    game.fire("NAME_PLATE_UNIT_ADDED", "nameplate1")
    game.unit("nameplate1", name="Durotar Tiger", level=8, classification="normal", dead=False)
    game.fire("NAME_PLATE_UNIT_ADDED", "nameplate1")
    game.clear_unit("nameplate1")
    game.kill("Durotar Tiger dies, you gain 30 experience.", xp_after=100)
    first, second, third = game.entries("xp")
    assert first.target.source == "nameplate" and first.target.level == 10
    assert second.target.source == "recent" and second.target.level == 6 and second.target.npc == 3099
    assert third.target is None
    assert sorted(to_py(third.seen_levels).values()) == [7, 8]
    assert game.errors() == {}


def test_living_or_other_target_is_not_taken_for_the_killed_monster():
    game = Logger()
    game.unit("target", name=MOB, level=11, classification="normal", dead=False, guid=MOB_GUID)
    game.kill(f"{MOB} dies, you gain 67 experience.", xp_after=67)
    game.unit("target", name="Autre monstre", level=11, classification="normal", dead=True, guid=MOB_GUID)
    game.kill(f"{MOB} dies, you gain 67 experience.", xp_after=134)
    assert [g.target for g in game.entries("xp")] == [None, None]
    assert [g.amount for g in game.entries("xp")] == [67, 67]


def test_other_and_french_gains_are_kept_with_their_amount():
    game = Logger()
    game.kill("You gain 450 experience.", xp_after=450)
    game.kill("Sanglier marbré meurt, vous gagnez 23 points d'expérience.", xp_after=473)
    game.kill("Vous gagnez 120 points d'expérience.", xp_after=593)
    gains = game.entries("xp")
    assert [(g.amount, g.kind, g.monster) for g in gains] == [
        (450, "other", None),
        (23, "monster", "Sanglier marbré"),
        (120, "other", None),
    ]


@pytest.mark.parametrize("args", [(5761,), (3, 5761)], ids=["mainline", "classic"])
def test_quest_accepted_and_turned_in_keep_id_level_and_xp_reward(args):
    game = Logger(player={"xp": 900, "level": 15, "rested": 120, "rest_state": 1})
    game.stub.quests[5761] = game.lua.table_from({"title": "Slaying the Beast", "level": 16, "index": 3})
    game.fire("QUEST_ACCEPTED", *args)
    game.fire("QUEST_TURNED_IN", 5761, 1450, 2500)
    accepted, turned = game.entries("quests")
    assert (accepted.event, accepted.quest_id, accepted.title, accepted.quest_level) == (
        "accepted",
        5761,
        "Slaying the Beast",
        16,
    )
    assert (turned.event, turned.quest_id, turned.xp_reward, turned.money_reward) == ("turned_in", 5761, 1450, 2500)
    assert turned.level == 15 and turned.quest_level == 16
    assert to_py(turned.state) == {"xp": 900, "max": 1000, "rested": 120, "rest_state": 1}
    assert turned.map == 1436 and turned.seq > accepted.seq
    assert game.errors() == {}


def test_login_snapshot_and_state_keep_trivial_range_and_rest():
    game = Logger(player={"xp": 250, "rested": 80, "resting": True, "rest_state": 1})
    (snap,) = game.entries("snapshots")
    assert snap.trivial_range == 5
    assert to_py(snap.state) == {"xp": 250, "max": 1000, "rested": 80, "rest_state": 1} and snap.resting is True
    (state,) = game.entries("xp_states")
    assert state.reason == "connexion" and state.xp == 250 and state.rested == 80 and state.resting is True
    game.stub.player.resting = False
    game.fire("PLAYER_UPDATE_RESTING")
    assert game.entries("xp_states")[-1].reason == "repos" and game.entries("xp_states")[-1].resting is False


def test_failing_and_secret_apis_leave_fields_absent_without_errors():
    game = Logger(
        failing=("UnitXP", "GetXPExhaustion", "IsInInstance", "GetNumGroupMembers", "C_QuestLog.GetTitleForQuestID"),
        secret=("UnitLevel", "UnitClassification"),
    )
    game.unit("target", name=MOB, level=11, classification="normal", dead=True, guid=MOB_GUID)
    game.kill(f"{MOB} dies, you gain 67 experience.", xp_after=67)
    game.fire("QUEST_TURNED_IN", 5761, 1450, 2500)
    (gain,) = game.entries("xp")
    assert gain.amount == 67
    assert gain.target.name == MOB and gain.target.level is None and gain.target.classification is None
    assert gain.state.xp is None and gain.state.rested is None and gain.state.max == 1000
    (turned,) = game.entries("quests")
    assert turned.quest_id == 5761 and turned.xp_reward == 1450 and turned.title is None
    assert game.errors() == {}


def test_unknown_events_do_not_stop_the_others():
    game = Logger(unknown_events=("QUEST_TURNED_IN", "NAME_PLATE_UNIT_ADDED", "UPDATE_EXHAUSTION"))
    game.kill("You gain 10 experience.", xp_after=10)
    assert [g.amount for g in game.entries("xp")] == [10]
    assert game.errors() == {}


def test_missing_apis_and_handler_errors_are_counted_not_raised():
    game = Logger()
    game.lua.globals().UnitName = game.lua.eval("function() error('panne') end")
    game.lua.globals().GetServerTime = None
    game.lua.globals().C_Map = None
    game.unit("target", name="x", level=1, dead=True)
    game.kill("x dies, you gain 1 experience.", xp_after=1)
    assert game.entries("xp")[0].amount == 1 and game.entries("xp")[0].target is None
    assert game.errors() == {}
    # SavedVariable abîmée : le gestionnaire échoue, l'erreur est comptée dans ForeverLoggerDB.errors, rien ne remonte.
    game.me().xp = "pas une table"
    game.fire("CHAT_MSG_COMBAT_XP_GAIN", "You gain 2 experience.")
    count, last = game.errors()["CHAT_MSG_COMBAT_XP_GAIN"]
    assert count == 1 and isinstance(last, str) and last


def test_old_saved_entries_are_kept_and_schema_is_current():
    saved = {
        "schema": 1,
        "characters": {GUID: {"snapshots": {}, "xp": {1: {"level": 14, "text": "Boar dies, you gain 23 experience."}}}},
    }
    game = Logger(saved=saved)
    assert game.db().schema == 4  # T04f : schéma 3 (auras, Legacy) ; DJ1 : schéma 4 (passages, butin)
    gains = game.entries("xp")
    assert gains[0].text == "Boar dies, you gain 23 experience."


def test_slash_command_prints_the_last_gain_and_quest():
    game = Logger(player={"xp": 0, "rested": 40, "rest_state": 1})
    game.unit("target", name=MOB, level=11, classification="normal", dead=True, guid=MOB_GUID)
    game.kill(f"{MOB} dies, you gain 67 experience.", xp_after=67, rested_after=7)
    game.fire("QUEST_TURNED_IN", 5761, 1450, 2500)
    assert game.stub.Slash("/flog")
    text = "\n".join(game.stub.printed.values())
    assert "ForeverLogger" in text
    assert "67" in text and "11" in text and "5761" in text and "1450" in text
    assert game.errors() == {}


def test_no_forbidden_call_and_no_combat_log_subscription():
    game = Logger()
    game.kill("You gain 1 experience.", xp_after=1)
    game.fire("QUEST_TURNED_IN", 1, 1, 1)
    assert list(game.stub.forbidden.values()) == []
    registered = set(game.stub.registered.keys())
    assert not any(e.startswith("COMBAT_LOG_EVENT") for e in registered)
    for event in ("QUEST_ACCEPTED", "QUEST_TURNED_IN", "PLAYER_XP_UPDATE", "UPDATE_EXHAUSTION", "PLAYER_UPDATE_RESTING",
                  "NAME_PLATE_UNIT_ADDED", "NAME_PLATE_UNIT_REMOVED", "PLAYER_TARGET_CHANGED", "CHAT_MSG_COMBAT_XP_GAIN"):  # fmt: skip
        assert event in registered, event
