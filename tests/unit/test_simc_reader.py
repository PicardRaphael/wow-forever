"""Lecteur de l'export SimulationCraft (P06b, bloc D, décisions 225 et 235), sur l'export construit
(`simc/constructed_mage.txt`) et le premier export réel (`simc/mage19_sonde_g.txt`, sonde G, anonymisé) : en-tête,
objets, fiche, notations, compétences, buffs, somme de contrôle ; chaîne `talents=` gardée brute (jamais décodée) ;
écarts avec le profil et le contexte du même message."""

from conftest import FIXTURES
from test_bridge_sonde_g import context

from forever.bridge.items import parse_gear
from forever.simc import parse_simc, simc_checksum, simc_gaps

SIMC = FIXTURES / "simc"
CONSTRUCTED = (SIMC / "constructed_mage.txt").read_text(encoding="utf-8")
REAL = (SIMC / "mage19_sonde_g.txt").read_text(encoding="utf-8")


def resign(body: str) -> str:
    return body + "# Checksum: " + simc_checksum(body)


def test_constructed_export_header_and_items():
    export = parse_simc(CONSTRUCTED)
    assert (export.class_token, export.name, export.level, export.race, export.server) == (
        "mage", "Jen", 19, "orc", "classic_beta_pve_2",
    )  # fmt: skip
    assert export.client_version == "1.60.1.70338" and export.role == "" and export.professions == {}
    assert export.spec == "unknown"
    assert export.checksum_ok is True and export.talents_string.startswith("BAEAA")
    staff = export.items["main_hand"]
    assert (staff.slot, staff.item, staff.enchant, staff.name, staff.ilvl) == (
        16,
        15444,
        1883,
        "Staff of Orgrimmar",
        20,
    )
    assert set(export.items) >= {"shoulder", "chest", "feet", "finger1", "finger2", "back"}


def test_constructed_export_sheet():
    export = parse_simc(CONSTRUCTED)
    assert set(export.sheet["spell_power"]) == {"holy", "fire", "nature", "frost", "shadow", "arcane"}
    assert export.sheet["crit"]["spell"] == 3.25
    assert "hit" not in export.sheet  # « # hit= » vide : aucun champ, aucune erreur
    assert export.ratings["hit_spell"] == (0.0, 0.0)
    assert export.buffs == {1459: 0, 10157: 0}
    assert export.skills[6] == (95, 0, 100)


def test_checksum_states():
    assert parse_simc(CONSTRUCTED.replace("\n", "\r\n")).checksum_ok is True
    assert parse_simc(CONSTRUCTED.replace("level=19", "level=18")).checksum_ok is False
    assert parse_simc(CONSTRUCTED.rsplit("# Checksum:", 1)[0]).checksum_ok is None


def test_gems_bonus_and_unreadable_talents():
    body = CONSTRUCTED.rsplit("# Checksum:", 1)[0]
    body = body.replace("feet=,id=14364", "feet=,id=14364,gem_id=3001/3002,bonus_id=1500/1501")
    body = body.replace("talents=BAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "# Unable to export talents (x)")
    export = parse_simc(resign(body))
    assert export.items["feet"].gems == (3001, 3002) and export.items["feet"].bonus == (1500, 1501)
    assert export.talents_string is None and any("talents" in w for w in export.warnings)


def test_real_export():
    export = parse_simc(REAL)
    assert export.checksum_ok is True and export.level >= 19 and export.class_token == "mage"
    assert export.professions == {"tailoring": 57, "enchanting": 75}
    assert export.items["chest"].enchant == 41 and export.items["back"].enchant == 65
    assert "off_hand" not in export.items  # objet des sacs (lignes commentées)
    assert "ranged" not in export.items
    pieces, _ = parse_gear(context("mage19_sonde_g_simc.txt")["gear"])
    in_context = {p.item.item for p in pieces}
    assert {i.item for i in export.items.values()} <= in_context
    assert export.sheet["spell_power"]["frost"] == 29
    assert export.sheet["regen"]["mana"] == [12.0, 0.0]


def test_gaps_with_the_context_and_the_profile():
    export = parse_simc(REAL)
    pieces, _ = parse_gear(context("mage19_sonde_g_simc.txt")["gear"])
    gaps, warnings = simc_gaps(export, None, pieces)
    assert [g.field for g in gaps] == ["sheet"]
    assert gaps[0].game["spell_power"]["frost"] == 29 and gaps[0].profile is None
    assert any("emplacement 18" in w and "à distance absent de l'export" in w for w in warnings)
    same = {"sheet": gaps[0].game}
    assert simc_gaps(export, same, pieces)[0] == []
    other = [p for p in pieces if p.slot != 5]
    _, warnings = simc_gaps(export, same, other)
    assert any("emplacement 5" in w for w in warnings)
