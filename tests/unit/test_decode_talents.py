"""Critère 2 : les 54 talents du Mage reproduits depuis les tables du client (fixtures wago 1.60.1.70009).

Référence : forever/data/1.60.1.70009/talents.json. Les écarts de rangs entre le client et la référence sont
comparés à forever/data/1.60.1.70009/confirmed_changes.json dans les deux sens : chaque changement confirmé existe,
et rien d'autre ne diffère. Les valeurs propres au client (identifiants, noms français) viennent des fixtures."""

import copy

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, change_key, client_vs_reference, format_changes, read_json

from forever.pipeline.decode import decode_talents, talent_key

REFERENCE = [t for tree in read_json(DATA_DIR / LOCAL_VERSION / "talents.json")["trees"] for t in tree["talents"]]
REF = {t["key"]: t for t in REFERENCE}
STRUCTURE = ("key", "name", "tree", "tier", "col", "max", "prereq")


@pytest.fixture(scope="module")
def decoded(client_tables, decode_rules):
    return decode_talents(client_tables, decode_rules, LOCAL_VERSION)


@pytest.fixture(scope="module")
def talents(decoded):
    return {t["key"]: t for tree in decoded["trees"] for t in tree["talents"]}


def flat(doc):
    return [t for tree in doc["trees"] for t in tree["talents"]]


def test_counts_per_tree(decoded):
    counts = {tree["name"]: len(tree["talents"]) for tree in decoded["trees"]}
    assert counts == {"Arcane": 18, "Fire": 17, "Frost": 19}
    assert sum(counts.values()) == 54


def test_same_order_as_reference(decoded):
    assert [t["key"] for t in flat(decoded)] == [t["key"] for t in REFERENCE]


@pytest.mark.parametrize("key", list(REF))
def test_structure_matches_reference(talents, key):
    decoded = {f: talents[key][f] for f in STRUCTURE}
    assert decoded == {f: REF[key][f] for f in STRUCTURE}


@pytest.mark.parametrize(
    ("key", "ranks"),
    [  # oracles FC-70009 de talents.json (rangs relus sur le build 70009)
        ("iceLance", [[26, 30, 300]]),
        ("pyroblast", [[95, 125, 44, 12]]),
        ("arcaneBlast", [[50, 58, 10, 175, 4, 8]]),
        ("blastWave", [[148, 178, 50, 6]]),
        ("iceBarrier", [[431, 1]]),
    ],
)
def test_fc_70009_oracles(talents, key, ranks):
    assert REF[key]["ranks"] == ranks and REF[key]["certainty"] == "FC-70009"
    assert talents[key]["ranks"] == ranks


@pytest.mark.parametrize(
    ("key", "ranks"),
    [  # talents.json : valeurs d'infobulle simples, identiques dans le client
        ("improvedFrostbolt", [[0.1], [0.2], [0.3], [0.4], [0.5]]),
        ("wandSpecialization", [[13], [25]]),
        ("arcaneSubtlety", [[8, 15], [15, 30]]),
        ("wakeOfFire", [[1, 30, 25], [2, 30, 50]]),
        ("missileBarrage", [[40, 20, 50, 100, 0.5]]),
        ("improvedCounterspell", [[2], [4]]),
        ("coldSnap", [[]]),
    ],
)
def test_tooltip_patterns(talents, key, ranks):
    assert REF[key]["ranks"] == ranks
    assert talents[key]["ranks"] == ranks


def test_prerequisites(talents):
    links = {k: t["prereq"] for k, t in talents.items() if t["prereq"]}
    at = {(t["tree"], t["tier"], t["col"]): k for k, t in talents.items()}
    named = {k: at[(talents[k]["tree"], p["tier"], p["col"])] for k, p in links.items()}
    assert named == {
        "arcaneMeditation": "arcaneConcentration",
        "arcanePower": "presenceOfMind",
        "hotStreak": "pyroblast",
        "combustion": "criticalMass",
        "fingersOfFrost": "iceLance",
        "iceBarrier": "coldSnap",
    }


def test_french_names(talents):
    assert all(t["name_fr"] for t in talents.values())
    assert talents["iceLance"]["name_fr"] == "Javelot de glace"  # fixture frFR/SpellName.csv


def test_client_spell_ids_and_certainty(talents):
    assert talents["iceLance"]["spellIds"] == [1312002]  # fixture TraitDefinition : un sort par nœud
    assert all(len(t["spellIds"]) == 1 for t in talents.values())
    assert {t["certainty"] for t in talents.values()} == {f"FC-{LOCAL_VERSION}"}
    assert all(isinstance(t["desc"], str) for t in talents.values())


def test_talent_key():
    assert talent_key("Winter's Chill") == "wintersChill"
    assert talent_key("Improved Cone of Cold") == "improvedConeOfCold"
    assert talent_key("Master of Elements") == "masterOfElements"


# --- Règles de decode_rules.json -----------------------------------------------------------------


def node_of(tables, spell_id):
    """Nœud de l'arbre dont la définition porte le sort (fixtures TraitNode / TraitNodeEntry / TraitDefinition)."""
    definition = next(d["ID"] for d in tables["TraitDefinition"] if d["SpellID"] == spell_id)
    entry = next(e["ID"] for e in tables["TraitNodeEntry"] if e["TraitDefinitionID"] == definition)
    node = next(x["TraitNodeID"] for x in tables["TraitNodeXTraitNodeEntry"] if x["TraitNodeEntryID"] == entry)
    return next(n for n in tables["TraitNode"] if n["ID"] == node)


def test_decoy_node_of_other_tree_is_ignored(client_tables, decoded):
    trees = {n["TraitTreeID"] for n in client_tables["TraitNode"]}
    assert len(trees) == 2  # la fixture garde un nœud leurre d'un autre arbre
    assert len(flat(decoded)) == 54


def test_shifted_geometry_changes_tiers(client_tables, decode_rules):
    rules = copy.deepcopy(decode_rules)
    rules["talent_geometry"]["row_base"] -= rules["talent_geometry"]["row_step"]
    shifted = {t["key"]: t for t in flat(decode_talents(client_tables, rules, LOCAL_VERSION))}
    assert all(shifted[k]["tier"] == REF[k]["tier"] + 1 for k in REF)


def test_extra_zero_in_position_is_corrected(client_tables, decode_rules):
    tables = {name: [dict(r) for r in rows] for name, rows in client_tables.items()}
    wand = node_of(tables, 6057)  # Wand Specialization (fixture TraitDefinition)
    target = next(n for n in tables["TraitNode"] if n["ID"] == wand["ID"])
    target["PosY"] = target["PosY"] * decode_rules["talent_geometry"]["extra_zero_divisor"]
    talents = {t["key"]: t for t in flat(decode_talents(tables, decode_rules, LOCAL_VERSION))}
    assert (talents["wandSpecialization"]["tier"], talents["wandSpecialization"]["col"]) == (1, 1)


def test_shared_spell_keeps_latest_node(client_tables, decode_rules):
    tables = {name: [dict(r) for r in rows] for name, rows in client_tables.items()}
    wake = node_of(tables, 11078)  # Wake of Fire (fixture TraitDefinition)
    link = next(x for x in tables["TraitNodeXTraitNodeEntry"] if x["TraitNodeID"] == wake["ID"])
    newer = dict(wake, ID=max(n["ID"] for n in tables["TraitNode"]) + 1)
    newer["PosY"] += 7 * decode_rules["talent_geometry"]["row_step"]  # palier 8, libre
    tables["TraitNode"].append(newer)
    tables["TraitNodeXTraitNodeEntry"].append(dict(link, ID=link["ID"] + 100000, TraitNodeID=newer["ID"]))
    talents = flat(decode_talents(tables, decode_rules, LOCAL_VERSION))
    wakes = [t for t in talents if t["key"] == "wakeOfFire"]
    assert len(talents) == 54 and len(wakes) == 1 and wakes[0]["tier"] == 8


# --- Écarts client ↔ référence -------------------------------------------------------------------


def test_confirmed_changes_are_well_formed():
    doc = read_json(DATA_DIR / LOCAL_VERSION / "confirmed_changes.json")
    assert doc["version"] == LOCAL_VERSION
    for c in doc["changes"]:
        assert {"kind", "key", "change", "field", "old", "new", "reference_certainty", "decision"} <= set(c)
        assert c["kind"] in ("talent", "spell")


def test_every_confirmed_talent_change_exists(candidate):
    gaps, _, confirmed = client_vs_reference(candidate, "talent")
    observed = {change_key(c) for c in gaps}
    missing = [c for c in confirmed if change_key(c) not in observed]
    assert not missing, "changements confirmés absents du décodage :\n" + format_changes(missing)


def test_no_other_talent_difference(candidate):
    gaps, _, confirmed = client_vs_reference(candidate, "talent")
    known = {change_key(c) for c in confirmed}
    unexpected = [c for c in gaps if change_key(c) not in known]
    assert not unexpected, f"{len(unexpected)} écart(s) client ↔ talents.json :\n" + format_changes(unexpected)
