"""Import automatique minimal du profil (PV1, bloc A ; D1, D2 ; décisions 99, 105, 125).

Fixtures (`tests/fixtures/addon/README.md`) : `ForeverLoggerDB.lua` (Mage « Moi », GUID du joueur « à moi » des
journaux, et Chasseur fictif « Traqueur », valeurs inventées), `Questie_journey.lua` (carnet synthétique),
`Auctionator.lua` (écrit par `scripts/build_auctionator_fixture.py` depuis `auctionator_source.json`, valeurs
inventées) et les journaux anonymisés de `tests/fixtures/combatlog/`. Décalage de l'heure locale : +2 h (instantané
ForeverLogger `time` ↔ `localtime`, `tests/fixtures/questie/README.md`). Journal des versions du client écrit dans
le cache temporaire (état de l'outil, versions et dates choisies pour le test)."""

import json
import shutil
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from conftest import FIXTURES, FakeHttp

from forever.cli import main
from forever.pipeline.auctionator import DAY_EPOCH, ItemPrice, read_price_database
from forever.pipeline.client_builds import ClientBuild, record_build
from forever.pipeline.combatlog import read_log
from forever.pipeline.questie import read_completed_quests
from forever.profile import (
    SOURCE_RANK,
    character_values,
    load_profile,
    make_field,
    merge_field,
    read_profile,
    set_character,
)
from forever.profile_import import apply_import, class_spell_index, plan_import
from forever.provenance import validate_provenance
from forever.store import load_version
from forever.timefmt import format_utc

ADDON = FIXTURES / "addon"
LOGS = FIXTURES / "combatlog"
LOG1 = LOGS / "WoWCombatLog-092726_145346.anon.txt"
OFFSET = timedelta(hours=2)
MOI, TRAQUEUR = "Player-0000-00000000", "Player-0000-0000F00D"
AFTER = datetime(2026, 9, 30, 10, 0, tzinfo=UTC)  # saisie du joueur postérieure aux instantanés des fixtures
BEFORE = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)  # saisie du joueur antérieure


def utc(ts: int) -> str:
    return format_utc(datetime.fromtimestamp(ts, UTC))


def with_builds(deps):
    """Deux versions du client dans le journal du cache : 70009 jusqu'à 14:00 UTC le 2026-09-27, puis 70124."""
    record_build(deps.cache_dir, ClientBuild("1.60.1.70009", datetime(2026, 9, 27, 10, 0, tzinfo=UTC), "wow_beta"))
    record_build(deps.cache_dir, ClientBuild("1.60.1.70124", datetime(2026, 9, 27, 14, 0, tzinfo=UTC), "wow_beta"))
    return deps


@pytest.fixture
def deps(make_deps):
    return with_builds(make_deps(now=AFTER))


@pytest.fixture
def sv(tmp_path):
    d = tmp_path / "SavedVariables"
    d.mkdir()
    shutil.copy(ADDON / "ForeverLoggerDB.lua", d / "ForeverLogger.lua")
    shutil.copy(ADDON / "Questie_journey.lua", d / "Questie.lua")
    shutil.copy(ADDON / "Auctionator.lua", d / "Auctionator.lua")
    return d


@pytest.fixture
def log1_only(tmp_path):
    d = tmp_path / "Logs1"
    d.mkdir()
    shutil.copy(LOG1, d / LOG1.name)
    return d


def run(deps, sv_dir, logs_dir=LOGS, **kw):
    plan = plan_import(deps, sv_dir=sv_dir, logs_dir=logs_dir, utc_offset=OFFSET, **kw)
    apply_import(deps, plan)
    return plan


def char(deps, name):
    return read_profile(deps, name)["character"]


def planned_char(plan, name):
    return character_values(plan["doc"]["characters"][name])


# --- Création et sources -----------------------------------------------------------------------------------


def test_import_creates_two_characters_of_different_classes(deps, sv):
    run(deps, sv)
    moi, traq = char(deps, "Moi"), char(deps, "Traqueur")
    assert (moi["class"], moi["race"], moi["level"]) == ("Mage", "Troll", 15)
    assert moi["talent_nodes"] == {"80213": 2}  # dernier instantané qui porte des talents
    assert (traq["class"], traq["race"], traq["level"]) == ("Hunter", "NightElf", 20)
    assert traq["talent_nodes"] == {"104960": 5, "104976": 5, "104973": 1}
    assert (moi["guid"], moi["realm"], traq["guid"]) == (MOI, "Royaume", TRAQUEUR)
    assert moi["planned"] is False and traq["planned"] is False
    f = moi["fields"]
    assert f["level"]["source"] == "ForeverLogger" and f["level"]["at"] == utc(1790516000)
    assert f["talent_nodes"]["at"] == utc(1790513400)
    assert f["class"]["source"] == "ForeverLogger" and f["class"]["certainty"] == "certain"
    assert traq["fields"]["level"]["at"] == utc(1790520000)


def test_second_import_writes_nothing(deps, sv, capsys):
    run(deps, sv)
    before = deps.profile_path.read_bytes()
    again = plan_import(deps, sv_dir=sv, logs_dir=LOGS, utc_offset=OFFSET)
    assert again["changes"] == [] and again["status"] == "aucun changement"
    argv = ["profile", "import", "--wtf", str(sv), "--logs", str(LOGS), "--utc-offset", "2", "--yes", "--json"]
    capsys.readouterr()
    assert main(argv, deps=deps) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "aucun changement"
    assert deps.profile_path.read_bytes() == before


def test_older_value_never_replaces_newer(make_deps, sv):
    later = with_builds(make_deps(now=AFTER))
    set_character(later, "Moi", cls="Mage", race="Troll", level=30)
    run(later, sv)
    c = char(later, "Moi")
    assert c["level"] == 30 and c["fields"]["level"]["source"] == "joueur"
    assert c["talent_nodes"] == {"80213": 2}  # champ vide : rempli par l'import

    earlier = with_builds(replace(make_deps(now=BEFORE), profile_path=later.profile_path.with_name("autre.json")))
    set_character(earlier, "Moi", cls="Mage", race="Troll", level=10)
    run(earlier, sv)
    c = char(earlier, "Moi")
    assert c["level"] == 15 and c["fields"]["level"]["source"] == "ForeverLogger"


def test_equal_dates_follow_source_order():
    assert sorted(SOURCE_RANK, key=SOURCE_RANK.__getitem__)[:2] == ["joueur", "ForeverLogger"]
    assert SOURCE_RANK["ForeverLogger"] < SOURCE_RANK["Questie"] == SOURCE_RANK["Auctionator"] < SOURCE_RANK["journal"]
    at = "2026-09-27T12:00:00Z"
    player, logger, log = (
        make_field(30, "joueur", at),
        make_field(15, "ForeverLogger", at),
        make_field(16, "journal", at),
    )
    for current, new in ((logger, player), (player, logger)):
        kept, conflict = merge_field(current, new)
        assert kept["value"] == 30 and kept["source"] == "joueur" and conflict is not None
    for current, new in ((log, logger), (logger, log)):
        kept, _ = merge_field(current, new)
        assert kept["value"] == 15
    newer = make_field(16, "journal", "2026-09-27T12:00:01Z")
    kept, conflict = merge_field(player, newer)  # la plus récente l'emporte, même moins directe
    assert kept["value"] == 16 and conflict["other"]["value"] == 30
    same, conflict = merge_field(logger, make_field(15, "journal", "2026-09-28T00:00:00Z"))
    assert same == logger and conflict is None  # même valeur : la source la plus directe est gardée


def test_disagreement_is_reported_not_erased(deps, sv):
    set_character(deps, "Moi", cls="Mage", race="Troll", level=30)
    plan = run(deps, sv)
    expected = [c for c in plan["conflicts"] if c["character"] == "Moi" and c["field"] == "level"]
    assert len(expected) == 1
    assert expected[0]["kept"]["value"] == 30 and expected[0]["other"]["value"] == 15
    assert expected[0]["other"]["source"] == "ForeverLogger"
    kept = [c for c in char(deps, "Moi")["conflicts"] if c["field"] == "level"]
    assert len(kept) == 1
    run(deps, sv)  # second import : l'écart reste, sans doublon
    assert [c for c in char(deps, "Moi")["conflicts"] if c["field"] == "level"] == kept


def test_planned_character_found_in_log_becomes_created(deps, sv):
    set_character(deps, "Moi", cls="Mage", race="Troll", planned=True)
    assert char(deps, "Moi")["planned"] is True
    run(deps, sv)
    c = char(deps, "Moi")
    assert c["planned"] is False and c["level"] == 15


def test_planned_class_conflict_is_reported(deps, sv):
    set_character(deps, "Moi", cls="Guerrier", planned=True)
    plan = run(deps, sv)
    assert any(c["character"] == "Moi" and c["field"] == "class" for c in plan["conflicts"])
    c = char(deps, "Moi")
    assert c["class"] == "Warrior" and c["planned"] is True and c["level"] is None


def test_faction_is_never_imported(deps, sv):
    plan = run(deps, sv)
    assert not any(ch["field"] == "faction" for ch in plan["changes"])
    view = read_profile(deps, "Moi")
    assert view["character"]["faction"] is None and "faction" in view["missing"]


def test_client_build_attached_per_snapshot_and_session(deps, sv, log1_only):
    run(deps, sv)
    assert char(deps, "Moi")["fields"]["level"]["client_build"] == "1.60.1.70009"  # 13:33:20 UTC
    assert char(deps, "Traqueur")["fields"]["level"]["client_build"] == "1.60.1.70124"  # 14:40 UTC
    # Classe venue du journal seul : version de la session (dernier événement vu).
    first = planned_char(plan_import(deps, sv_dir=None, logs_dir=log1_only, utc_offset=OFFSET), "Moi")
    assert first["fields"]["class"]["client_build"] == "1.60.1.70009"  # 14:55:24 locale, 12:55:24 UTC
    both = planned_char(plan_import(deps, sv_dir=None, logs_dir=LOGS, utc_offset=OFFSET), "Moi")
    assert both["fields"]["class"]["client_build"] == "1.60.1.70124"  # 16:48:23 locale, 14:48:23 UTC


def test_unknown_build_is_null_not_installed_version(make_deps, sv):
    bare = make_deps(now=AFTER)  # aucun journal des versions du client
    plan = run(bare, sv)
    installed = load_version(bare).game_version
    for name in ("Moi", "Traqueur"):
        for meta in char(bare, name)["fields"].values():
            assert meta["client_build"] != installed
            if meta["source"] == "ForeverLogger":
                assert meta["client_build"] is None
    assert any("version du client inconnue" in n for n in plan["notes"])


def test_class_from_logger_else_from_class_spells_probable(deps, sv):
    known = planned_char(plan_import(deps, sv_dir=sv, logs_dir=LOGS, utc_offset=OFFSET), "Moi")
    assert known["fields"]["class"]["source"] == "ForeverLogger" and known["fields"]["class"]["certainty"] == "certain"
    alone = planned_char(plan_import(deps, sv_dir=None, logs_dir=LOGS, utc_offset=OFFSET), "Moi")
    assert alone["class"] == "Mage"
    assert alone["fields"]["class"]["source"] == "journal" and alone["fields"]["class"]["certainty"] == "probable"
    assert alone["level"] is None  # le champ `level` du journal n'est pas lu pour un joueur


def test_mixed_class_spells_leave_class_unknown(deps, log1_only):
    _, events = read_log(LOG1)
    cast = sorted(
        {e.spell[0] for e in events if e.name == "SPELL_CAST_SUCCESS" and e.source and e.source.guid == MOI and e.spell}
    )
    index = class_spell_index(load_version(deps))
    mage = [s for s in cast if index.get(s) == "Mage"]
    assert len(mage) >= 2  # prémisse : au moins deux sorts de Mage distincts lancés
    mixed = {**index, mage[0]: "Warrior"}
    plan = plan_import(deps, sv_dir=None, logs_dir=log1_only, utc_offset=OFFSET, class_spells=mixed)
    assert "Moi" not in plan["doc"]["characters"]
    assert any(s["name"] == "Moi" and s["guid"] == MOI for s in plan["skipped"])


# --- Questie et Auctionator ----------------------------------------------------------------------------------


def test_questie_completed_quests_per_character(deps, sv):
    assert read_completed_quests(sv / "Questie.lua", MOI) == [(835, 1790410000), (834, 1790420836)]
    run(deps, sv)
    moi, traq = char(deps, "Moi"), char(deps, "Traqueur")
    assert moi["quests_completed"] == {"835": utc(1790410000), "834": utc(1790420836)}  # 830 acceptée, 836 abandonnée
    assert traq["quests_completed"] == {"900": utc(1790519000)}
    assert moi["fields"]["quests_completed"]["source"] == "Questie"
    assert moi["fields"]["quests_completed"]["at"] == utc(1790420836)
    assert "Autre" not in read_profile(deps)["characters"]  # GUID ni dans ForeverLogger ni dans les journaux


def test_auctionator_prices_per_realm(deps, sv):
    prices = read_price_database(sv / "Auctionator.lua")
    assert set(prices) == {"Royaume", "AutreRoyaume"}  # RoyaumePvE : aucune entrée d'objet

    def day(n):
        return (DAY_EPOCH + timedelta(days=n)).isoformat()

    royaume = prices["Royaume"]
    assert royaume[1001] == ItemPrice(120, 2463, day(2463), 20)  # dernier jour vu, minimum courant `m`
    assert royaume[1002] == ItemPrice(10, 2463, day(2463), 13)  # saut de ligne et retour chariot échappés
    assert royaume[1003] == ItemPrice(45000, 2463, day(2463), None)  # quantité absente
    assert royaume[1004] == ItemPrice(34, 2463, day(2463), 92)  # guillemet et barre oblique inverse échappés
    assert royaume[1005] == ItemPrice(0, 2463, day(2463), 0)  # octet nul échappé
    assert prices["AutreRoyaume"][1001] == ItemPrice(99, 2460, day(2460), 4)
    run(deps, sv)
    doc = load_profile(deps.profile_path)
    stored = doc["realms"]["Royaume"]["prices"]
    assert stored["source"] == "Auctionator" and stored["certainty"] == "probable"
    assert stored["value"]["1001"] == {"min": 120, "day": 2463, "date": day(2463), "quantity": 20}
    assert doc["realms"]["AutreRoyaume"]["prices"]["value"]["1001"]["min"] == 99
    assert "prices" not in char(deps, "Moi")  # par royaume, jamais par personnage


def test_posting_history_is_never_read(deps, sv, capsys):
    sentinel = json.loads((ADDON / "auctionator_source.json").read_text(encoding="utf-8"))["posting_history_sentinel"]
    argv = ["profile", "import", "--wtf", str(sv), "--logs", str(LOGS), "--utc-offset", "2", "--dry-run", "--json"]
    capsys.readouterr()
    assert main(argv, deps=deps) == 0
    assert sentinel not in capsys.readouterr().out
    # Historique rendu illisible : la base de prix se lit toujours, l'historique n'est jamais analysé.
    path = sv / "Auctionator.lua"
    raw = path.read_bytes()
    cut = raw.index(b"AUCTIONATOR_POSTING_HISTORY")
    path.write_bytes(raw[:cut] + b"AUCTIONATOR_POSTING_HISTORY = @@@ " + sentinel.encode() + b" {{{\r\n")
    assert read_price_database(path)["Royaume"][1001].min == 120
    assert main(argv, deps=deps) == 0
    assert sentinel not in capsys.readouterr().out


# --- CLI, accord, provenance ---------------------------------------------------------------------------------


def test_changes_listed_before_writing_and_consent_required(deps, sv, capsys):
    argv = ["profile", "import", "--wtf", str(sv), "--logs", str(LOGS), "--utc-offset", "2"]
    capsys.readouterr()
    assert main(argv, deps=deps) == 0  # aucun moyen de demander l'accord : refus
    out = capsys.readouterr().out
    assert "refus" in out and "Traqueur" in out and "level" in out
    assert not deps.profile_path.exists()
    seen: list[str] = []

    def confirm(prompt: str) -> bool:
        seen.append(capsys.readouterr().out)
        return True

    agreeing = replace(deps, confirm=confirm)
    assert main(argv, deps=agreeing) == 0
    assert len(seen) == 1 and "Traqueur" in seen[0] and "level" in seen[0]  # changements listés avant l'accord
    assert char(agreeing, "Traqueur")["level"] == 20


def test_profile_import_cli_dry_run(deps, sv, capsys):
    argv = ["profile", "import", "--wtf", str(sv), "--logs", str(LOGS), "--utc-offset", "2", "--dry-run"]
    capsys.readouterr()
    assert main([*argv, "--json"], deps=deps) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "simulation" and payload["changes"]
    for change in payload["changes"]:
        assert {"character", "field", "old", "new", "source", "at", "client_build"} <= set(change)
    assert validate_provenance(payload["provenance"]) == []
    assert not deps.profile_path.exists()
    assert main(argv, deps=deps) == 0
    text = capsys.readouterr().out
    assert "simulation" in text and "Moi" in text


def test_absent_sources_are_reported_not_errors(deps, tmp_path, capsys):
    empty = tmp_path / "vide"
    empty.mkdir()
    plan = plan_import(deps, sv_dir=empty, logs_dir=empty, utc_offset=OFFSET)
    assert plan["changes"] == [] and plan["status"] == "aucun changement"
    assert all(v is None for v in plan["sources"].values())
    assert plan["notes"]


def test_import_never_touches_the_network(make_deps, sv):
    offline = with_builds(replace(make_deps(now=AFTER), http_get=FakeHttp.failing()))
    run(offline, sv)
    assert offline.http_get.calls == []


def test_schema_1_profile_is_migrated_on_read(make_deps, tmp_path):
    path = tmp_path / "profil" / "profile.json"
    path.parent.mkdir()
    shutil.copy(FIXTURES / "plugin_eval" / "profile-rempli.json", path)
    before = path.read_bytes()
    old = json.loads(before)["characters"]["Givrelame"]
    deps = replace(make_deps(), profile_path=path)
    c = read_profile(deps)["character"]
    for key in ("class", "race", "faction", "level", "talents", "professions"):
        assert c[key] == old[key]
    assert c["fields"]["level"] == {
        "source": "joueur",
        "at": old["updated_at"],
        "client_build": None,
        "certainty": "certain",
    }
    assert c["conflicts"] == []
    assert load_profile(path)["schema_version"] == 2
    assert path.read_bytes() == before  # migré à la lecture seulement
    set_character(deps, "Givrelame", level=24)  # une commande qui écrit réécrit en schéma 2
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 2
    assert read_profile(deps)["character"]["race"] == "Orc"
