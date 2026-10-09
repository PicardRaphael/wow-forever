# 1.60.1.70291 : tests rendus indépendants de la version installée (2026-10-09)

La nouvelle version 1.60.1.70291 est la première, depuis la décision 192, qui change des valeurs lues par les moteurs
(rangs bas de Frostbolt, Fireball et Arcane Missiles lissés) et qui renomme un talent hors du Mage (Druide :
Predatory Instincts devient Natural Instinct, clé `naturalInstinct`). Le passage de `forever update` ne l'avait pas
vu : son `verify` a tourné sur une préparation sans 70291, l'installation étant refusée par les règles de fusion.
Installée en session (accord de l'utilisateur du 2026-10-09), elle rendait rouges 32 tests et en mettait 87 en
erreur. Aucun test n'a été corrigé valeur par valeur : chaque famille est rattachée à la version d'où viennent ses
valeurs (décision 215).

## Dégâts des rangs écrits en dur
`RANK_VALUES_VERSION = "1.60.1.70245"` (`tests/conftest.py`) : dernière version dont les dégâts des rangs du Mage
sont ceux des fixtures wago de 1.60.1.70009. Fixtures de session `data_at_rank_values_version` (copie du dépôt
ramenée à cette version par `rewind_to`) et `game_data_at_rank_values_version`.

| Test | Correction |
| --- | --- |
| `test_lookup.py::test_frostbolt_rank_2` | données de `RANK_VALUES_VERSION`, version attendue dans la provenance |
| `test_cli.py::test_lookup_text`, `test_lookup_json`, `test_lookup_all_ranks_text` | idem |
| `integration/test_mcp.py::test_lookup_frostbolt_rank_2` | idem |
| `test_engine_leveling.py::test_rank_damage_at_the_character_level`, `test_expected_cast_at_the_character_level` | `game_data_at_rank_values_version` |
| `test_spell_scaling.py::test_frostbolt_rank3_by_level`, `test_reproduces_decoded_ranks_at_capped_max_level` | idem |
| `test_spell_scaling.py::test_decode_reproduces_installed_spell_scaling` | comparé à `spell_scaling.json` de `RANK_VALUES_VERSION` (tables des fixtures) |
| `test_seed_data.py::test_simulate_leveling_passes_rules_to_the_loader` (fixture `client_copy`) | copie ramenée à `RANK_VALUES_VERSION` des deux côtés |
| `test_community_builds.py::test_gaps_are_computed_by_the_engine` (fixture `frozen_game_data`) | copie ramenée à la version de la comparaison |
| `test_decode_spells.py::test_rank_values` | référence de 1.60.1.70009, le build des fixtures (docstring) |
| `test_gamedata.py::test_spell_ranks` | valeurs du seed lues dans ses copies figées (`seed_game_data`), source citée par la docstring |
| `test_client_decisions.py::test_talent_rank_one_spells_are_conventions` | écarts de T03 lus dans `confirmed_changes.json` de 1.60.1.70009 (70291 ajoute 24 écarts « client ») |
| `integration/test_mcp_stdio.py::test_stdio_server` | valeur attendue lue dans `spells.json` installé : le test vérifie le transport stdio, pas la valeur |

## Version fictive plus récente
`tests/fixtures/wago/builds_stale.json` : 1.60.1.70250 (après 70150) devenait plus ancienne que la version
installée ; portée à 1.60.1.99250 (`test_builds.py`, `test_freshness.py`, `test_lookup.py`). Nouveau garde
`test_builds.py::test_stale_fixture_is_newer_than_the_installed_version`.

## Talent renommé par le client hors du Mage
D'abord résolu par `RENAMED_KEYS` dans `tests/talents_forever_data.py` ; remplacé le jour même par la décision 218 :
les clés de talent sont stables d'une version à l'autre pour les 9 classes (même nœud, même sort), et
1.60.1.70291 révision 3 garde `predatoryInstincts` pour Natural Instinct. `RENAMED_KEYS` est retiré.

## Registre
`test_registry.py` : plus aucun total figé (décision 214).
