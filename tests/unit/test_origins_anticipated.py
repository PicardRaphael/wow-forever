"""1.60.1.70450, bloc A : une règle d'origine écrite par une tranche pour des valeurs d'une version à venir (sorts
nouveaux Frost Blast et Arcane Wrath, absents de la version courante) est portée par la version courante, comme les
règles de lecture (décisions 263 et 284), et reportée dans la nouvelle version. Marquée `anticipe`, elle n'est pas
« sans effet » là où ses valeurs n'existent pas encore ; sans ce drapeau, elle l'est toujours.

Copie des données (fixture `data_copy`) ; aucun chiffre de jeu."""

import json

from conftest import LOCAL_VERSION

from forever.origins import ORIGINS_NAME, check_version

RULE = {
    "file": "spells.json",
    "paths": ["/spells/fixture_new_spell/*"],
    "origin": "client",
    "source": "règle de test",
    "certainty": "certain",
}


def write_rule(data, rule):
    path = data / LOCAL_VERSION / ORIGINS_NAME
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["rules"].append(rule)
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def issues(data):
    return {i.kind for i in check_version(data, LOCAL_VERSION).issues}


def test_rule_without_values_is_refused(data_copy):
    write_rule(data_copy, RULE)
    assert "regle_sans_effet" in issues(data_copy)


def test_anticipated_rule_waits_for_its_values(data_copy):
    write_rule(data_copy, {**RULE, "anticipe": "1.60.1.70450 : sorts nouveaux de la refonte du Mage"})
    assert "regle_sans_effet" not in issues(data_copy)
