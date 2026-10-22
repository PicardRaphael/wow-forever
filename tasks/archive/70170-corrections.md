# 1.60.1.70170 : demandes de correction de tests (regroupées avant le commit)

Le diff exact est dans l'arbre de travail (`git diff -- tests`). Ce fichier donne la cause et la portée de chaque
correction. Aucun test n'est affaibli : chacun garde son assertion et suit soit la version installée, soit la
version de ses extraits.

## Causes communes
1. **Version installée** : 1.60.1.70170 remplace 1.60.1.70124 comme version la plus récente (révision 1, collecte du
   2026-10-02, plafond de la bêta 30 observé et `certain`).
2. **Extraits de tables** : les fixtures `tests/fixtures/wago/1.60.1.70124` (9 classes, ratios, familiers) et
   `1.60.1.70009` (Mage, T03) restent des extraits de **leur** client. Avant, ils coïncidaient avec la version
   installée, ce qui n'est plus vrai : 70170 renomme Hot Streak et passe Combustion à 3 charges. Les tests qui
   installent la candidate de ces extraits en révision travaillent sur une copie du dépôt ramenée à la version des
   extraits ; ceux qui comparent le décodage des extraits à une référence lisent la référence de cette version.
3. **Version fictive « plus récente »** : 1.60.1.70150, qui servait de version publiée plus récente que la version
   installée, est désormais plus ancienne. Elle passe à 1.60.1.70250.

## C1 — `tests/conftest.py` (cause 1 et 2)
- `LOCAL_VERSION` : `1.60.1.70124` → `1.60.1.70170`.
- Nouvelle constante `CLASS_FIXTURE_VERSION = "1.60.1.70124"`. `WAGO_70124` pointe vers elle au lieu de
  `LOCAL_VERSION`, sinon le dossier des extraits serait cherché sous `1.60.1.70170`.
- Nouvelle fonction `rewind_to(data, version)` (retire les versions plus récentes et réécrit le manifeste). Nouvelle
  fixture `data_at_class_fixture_version` (copie de `forever/data` ramenée à `CLASS_FIXTURE_VERSION`).
- `client_vs_reference` lit `confirmed_changes.json` de `PREVIOUS_VERSION` (version des extraits de T03) au lieu de
  `LOCAL_VERSION`, qui porte maintenant aussi les trois écarts de 70170.

## C2 — tests qui installent la candidate des extraits 70124 en révision (cause 2)
- `test_install_game_state.py`, `test_install_pets.py`, `test_install_revision_decoded.py` : `LOCAL_VERSION`
  importé comme alias de `CLASS_FIXTURE_VERSION`, et fixture de module `data_copy` = `data_at_class_fixture_version`.
- `test_install_r2.py` : candidate décodée à `CLASS_FIXTURE_VERSION` ; `rewind_classes` ramène la copie à cette
  version avant de retirer les fichiers des classes ; `test_inherited_class_files_are_never_installed` ramène la copie
  à 70009 par `rewind_to` (avant : suppression du seul dossier `LOCAL_VERSION`) ; contrôles des données installées
  inchangés (`LOCAL_VERSION`).
- `test_review_t08b.py` : `test_observed_cap_is_certain_and_origins_stay_valid` et
  `test_carried_cap_keeps_its_original_date_and_revision` sur `data_at_class_fixture_version`.

## C3 — références des extraits (cause 2)
- `test_decode_talents.py` : `REFERENCE`, `test_confirmed_changes_are_well_formed` et l'oracle des certitudes lisent
  `PREVIOUS_VERSION` (70009, la version que décrivent la docstring du module et ses extraits).
- `test_decode_classes.py::test_mage_part_matches_talents_json` : référence `talents.json` de `CLASS_FIXTURE_VERSION`.

## C4 — valeurs de la version installée (cause 1)
- `test_install.py` (deux tests), `test_provenance.py::test_make_provenance` : révision 6 → 1.
- `test_manifest.py::test_manifest_content` : `collected_at` 2026-09-30 → 2026-10-02, révision 1.
- `test_origins.py::test_installed_versions_pass` : trois versions installées.
- `test_origins_r4.py::test_beta_cap_is_an_installation_fact` : plafond posé en révision 1 (avant : 4).
- `test_build_data.py` : plafond 20 → 30, certitude `probable` → `certain` (observation).
- `test_build_report.py::test_beta_level_cap` : le donjon de niveau 25 n'est plus au-delà du plafond ; le test
  calcule un rapport rapide à « plafond + 5 ».

## C5 — version fictive plus récente (cause 3)
- `tests/fixtures/wago/builds_stale.json`, `test_builds.py`, `test_freshness.py`, `test_lookup.py`,
  `test_manifest.py::test_game_version_is_highest_version_dir` : 1.60.1.70150 → 1.60.1.70250 (et l'ensemble des
  versions attendues compte 70124).

## Tests ajoutés (écrits avant le code, échec constaté)
- `tests/unit/test_install_confirmed_talents.py` : renommage et `tooltip_values` confirmés, ancien nom gardé,
  renommage appliqué à l'arbre du Mage de `classes.json`, refus sans entrée confirmée.
- `tests/unit/test_replay_builds_cases.py` : leveling rejoué au niveau 30.
- `tests/unit/test_lookup_talent.py::test_former_name_of_a_renamed_talent_still_resolves` (ajout dans un module
  existant, aucun test existant modifié).
