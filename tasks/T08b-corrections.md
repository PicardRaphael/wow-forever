# T08b — Demandes de correction des tests verrouillés

Regroupées pour être présentées en une fois avant la fusion (consigne de l'utilisateur du 2026-10-01).

## 1. `tests/unit/test_origins.py::test_leaf_added_in_a_decoded_file_is_covered_by_its_pattern` (bloc H)

- **Prémisse fausse** : le test suppose que `spell_scaling.json` `spells.<sort>` est un objet ; c'est une **liste de
  rangs** (objets `rank`, `spell_id`, `base_level`, `spell_level`, `max_level`, `start_recovery_ms`, `components`…).
- **Preuve** (données) : `forever/data/1.60.1.70124/spell_scaling.json`, `spells.frostbolt` est une liste de 11 objets
  (lu le 2026-10-01) ; le test échoue sur `TypeError: list indices must be integers or slices, not str`, avant le
  contrôle visé.
- **Diff proposé** (ajout du champ dans le premier rang, ce que le test veut montrer : une feuille nouvelle d'un
  fichier décodé reste couverte par son motif `client`) :

```diff
-    doc["spells"][first]["t08b_champ_nouveau"] = 1
+    doc["spells"][first][0]["t08b_champ_nouveau"] = 1
```

## 2. `tests/unit/test_install.py::test_plan_lists_exactly_the_allowed_changes` (T06b, bloc B de T08b)

- **Prémisse changée par D2** (accord du 2026-10-01) : toute installation déplace le plafond de la bêta de
  `mechanics.json` vers `meta.json` `game_state` (règle `game_state` : retrait de `values.build.beta_level_cap`,
  valeur reportée). Ces lignes portent la certitude de la valeur reportée (`probable`), pas `certain`.
- **Preuve** : `forever/data/1.60.1.70124/mechanics.json`, `values["build.beta_level_cap"].certainty` vaut
  `probable` ; le test échoue sur `assert all(c["source"] and c["certainty"] == "certain" for c in plan["changes"])`.
- **Diff proposé** :

```diff
-    assert all(c["source"] and c["certainty"] == "certain" for c in plan["changes"])
+    assert all(c["source"] and c["certainty"] == "certain" for c in plan["changes"] if c["rule"] != "game_state")
+    assert {c["path"] for c in plan["changes"] if c["rule"] == "game_state"} == {"values.build.beta_level_cap"}
```

## 3. `tests/unit/test_install_new_version.py::test_nothing_changed_is_installed_anyway` (T08a, bloc B de T08b)

- **Même cause** (D2) : la nouvelle version reçoit le plafond reporté dans `meta.json` `game_state`, et la clé de
  `mechanics.json` est retirée ; « seule la provenance bouge » ne vaut plus pour cette ligne d'état du jeu.
- **Preuve** : `plan["changes"]` contient la ligne `game_state` `values.build.beta_level_cap` (valeur
  `forever/data/1.60.1.70009/mechanics.json`) ; échec sur l'ensemble des règles permises.
- **Diff proposé** :

```diff
-    assert {c["rule"] for c in plan["changes"]} <= {"added_field", "metadata", "certainty"}
-    assert all(c["path"].endswith(".source") or c["rule"] == "certainty" for c in plan["changes"])
+    assert {c["rule"] for c in plan["changes"]} <= {"added_field", "metadata", "certainty", "game_state"}
+    assert all(c["path"].endswith(".source") or c["rule"] in ("certainty", "game_state") for c in plan["changes"])
```

## 4. `tests/unit/test_spell_scaling.py::test_decode_reproduces_installed_spell_scaling` (T04, blocs B et I de T08b)

- **Pas de correction demandée** : le décodage ajoute `auras.ignite` et `auras.winters_chill` (bloc B) ;
  `spell_scaling.json` installé ne les porte qu'à la révision 4 (bloc I, après accord). Le test redevient vert à
  l'installation de la révision 4 ; s'il ne l'est pas, une demande sera ajoutée ici.

## 5. `tests/unit/test_install.py::test_client_decode_matches_the_installed_data` (T06b, blocs B et C de T08b)

- **Prémisse changée** : `forever diff` compare désormais les valeurs de `spell_scaling.json` (bloc C, demande de
  l'utilisateur, point 3), et le décodage porte deux auras de plus (bloc B : `auras.ignite`, `auras.winters_chill`).
  La version 1.60.1.70009 installée ne recevra jamais ces champs (aucune révision prévue) : le diff liste 11 valeurs
  **ajoutées**, aucune valeur modifiée.
- **Preuve** : `diff_versions(1.60.1.70009, candidate)` rend 11 lignes `scaling` `added` (`auras ignite` : 4 champs,
  `auras winters_chill` : 7 champs) ; aucune ligne `modified` ni `removed`.
- **Diff proposé** (le test garde son sens : le décodage reproduit toutes les valeurs installées ; les champs
  décodés depuis sont des ajouts) :

```diff
-    assert [c for c in d["changes"] if c["kind"] != "file"] == []
+    assert [c for c in d["changes"] if c["kind"] != "file" and not (c["kind"] == "scaling" and c["change"] == "added")] == []
```

## Après l'installation de la révision 4 (bloc I, dans l'arbre de travail, non committée)

La suite complète avec la révision 4 installée et les changements à la main appliqués donne 29 échecs, tous
expliqués ci-dessous. La correction 4 n'est plus nécessaire (le test est vert avec la révision 4).

### D3 (accord du 2026-10-01) : cas du mode seed passés sur `seed_game_data`, aucune valeur attendue changée

Vérifié sur des copies temporaires : les 9 tests passent sur `seed_game_data` avec leurs valeurs actuelles.
`tests/unit/test_engine_character.py` : `test_character_orc_60`, `test_character_gnome_mana`, `test_int_per_crit`,
`test_overrides_replace_estimates` (`game_data` → `seed_game_data`) ; `tests/unit/test_engine_values.py` :
`test_arcane_blast_mana_pct` (fixture `seed_ch` = `character(seed_game_data, …)`, mêmes arguments que `ch`) ;
`tests/unit/test_sim_rules.py::test_seed_rules_keep_the_seed_value` et
`tests/unit/test_sim_leveling.py::test_monte_carlo_reproducible_seed_mode` (rules seed du simulateur sur les données
du seed).

### 6. Numéro de révision : `test_install.py::test_repository_is_revision_two` (l. 225), `test_install.py::test_status_shows_the_revision` (l. 283), `test_provenance.py::test_make_provenance` (l. 121), `test_manifest.py::test_manifest_content`

- Preuve : `forever/data/1.60.1.70124/sources.json` `revision` vaut 4 après l'installation (accord du 2026-10-01).
- Diff : `== 3` → `== 4` aux trois endroits (commentaire « T08b : révision 4 (ratios du personnage) ») ; dans
  `test_manifest.py` : `v["revision"] == 4 and v["revised_at"] == "2026-10-01"`, `len(v["files"]) == 23` et
  `"character_scaling.json"` ajouté au sous-ensemble.

### 7. Fichier décodé nouveau dans les ensembles exacts : `test_data_import.py::test_version_dir_contains_exactly_expected_files`, `test_decode_version.py::test_candidate_is_a_complete_data_dir` et `::test_sources_describe_every_file`, `test_verify_version.py::test_candidate_is_ok_and_lists_inherited_files`, `test_install_new_version.py::test_the_new_version_has_every_file_of_the_previous_one` et `::test_diff_between_the_two_installed_versions_has_no_removed_file`

- Preuve : `forever/data/1.60.1.70124/character_scaling.json` existe (révision 4) ; la candidate de la fixture
  1.60.1.70009 (sans tables des ratios) en hérite, comme des fichiers des classes (`CHARACTER_FILES`).
- Diffs : `"character_scaling.json"` ajouté à l'ensemble attendu de `test_data_import.py` ; dans
  `test_decode_version.py`, `EXPECTED_FILES = {*DECODED_FILES, *INHERITED_FILES, *CHARACTER_FILES, "sources.json"}`
  et `len(names) == 18` ; dans `test_verify_version.py`, `| set(CHARACTER_FILES)` ; dans
  `test_install_new_version.py`, `"character_scaling.json"` ajouté aux fichiers attendus (le test installe la
  candidate de la fixture sur le dépôt ramené à 1.60.1.70009 : `PV1_ADDED | {"character_scaling.json"}`).

### 8. `test_data_import.py::test_seed_files_are_inherited_unchanged_by_the_installed_version`

- Preuve : `meta.json` porte maintenant `game_state` (fait d'installation, D2) ; le reste est identique au seed.
- Diff : `content()` ignore aussi `game_state` (`k not in ("inherited_from", "game_state")`).

### 9. `test_build_data.py::test_build_keys_carry_certainty_and_source` et `::test_missing_build_key_is_schema_error`

- Preuve : `build.beta_level_cap` a quitté `mechanics.json` à la révision 4 (D2) ; il vit dans `meta.json`
  `game_state.beta_level_cap` (certitude `probable`, source et révision).
- Diff : retirer `"build.beta_level_cap": "probable"` de `expected` et ajouter
  `assert read_json(DATA_DIR / LOCAL_VERSION / "meta.json")["game_state"]["beta_level_cap"]["certainty"] == "probable"` ;
  dans le second test, retirer la clé `game_state` de `meta.json` en plus de la clé de `mechanics.json`
  (`edit_json(data_copy, "meta.json", lambda doc: doc.pop("game_state"))`) pour atteindre l'erreur de schéma.

### 10. `test_seed_data.py::test_seed_rules_read_the_frozen_copies` (l. 81)

- Prémisse changée par la demande de l'utilisateur (point 1) : en mode forever, les ratios du personnage viennent
  du client ; `seed.constants == forever.constants` n'est plus vrai (critique par Intelligence, mana de base).
- Diff : `assert seed.scaling == forever.scaling and seed.constants.coefficients == forever.constants.coefficients`
  et `assert seed.constants.character.base_mana_by_level == ()`.

### 11. `test_community_builds.py::test_gaps_are_computed_by_the_engine`

- Prémisse changée : les écarts des 55 builds de la communauté sont calculés en mode forever ; ils bougent avec les
  ratios du client. La fixture `tests/fixtures/community/mage_builds.json` (écrite par
  `scripts/build_community_fixture.py` le 2026-09-29) doit être régénérée par le même script ; aucun code du test ne
  change. Le diff de la fixture sera montré avant le commit.

### 12. `test_install_game_state.py` (bloc B, verrouillé ; erreur de collecte)

- Preuve : la clé `build.beta_level_cap` n'existe plus dans `mechanics.json` (révision 4).
- Diff :

```diff
-CURRENT = read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"][OLD_KEY]["value"]
+CURRENT = read_json(DATA_DIR / LOCAL_VERSION / "meta.json")["game_state"]["beta_level_cap"]["value"]
```

### 13. `test_install_revision_decoded.py::test_plan_lists_changed_values_of_decoded_files` (bloc C, verrouillé)

- Prémisse : le dépôt n'avait pas `character_scaling.json` ; il l'a depuis la révision 4.
- Diff : au début du test, `(data_copy / LOCAL_VERSION / CHARACTER).unlink()` puis `write_manifest(data_copy)`
  (import de `write_manifest` déjà présent).

### 14. `test_origins.py::test_pending_lowering_is_tolerated_and_listed` et `test_origins_inventory.py::test_pending_lowerings_come_first` (bloc H, verrouillés)

- Preuve : la révision 4 a fait les cinq abaissements de 1.60.1.70124 (`pending` vide, test `test_origins_r4.py`) ;
  1.60.1.70009 garde les siens (aucune révision prévue).
- Diff : ces deux tests lisent `PREVIOUS_VERSION` au lieu de `LOCAL_VERSION` (copie des données et inventaire).

Mesure pour la correction 11 (fixture régénérée puis remise en l'état, 2026-10-01) : 41 écarts sur 55 changent ;
builds qui **concordent** avec notre référence : **8 → 2** (C2 devient « source douteuse » ; C7, C9, A1, A3, A30 et
C11 passent à « mécanique non modélisée »), plus grands mouvements : C1 −4,9 % → −10,0 %, C9 +0,7 % → −4,2 %,
A1 +1,1 % → −3,8 %, C2 −0,3 % → −5,1 %, C3 +7,3 % → +2,6 %. La conclusion « 8 concordent » de
`docs/research/builds-T05.md` et `docs/research/community-builds-mage.md` sera réécrite avec la fixture.
