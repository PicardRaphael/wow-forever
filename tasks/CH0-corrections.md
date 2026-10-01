# CH0 — demandes de correction de tests (regroupées avant la fusion)

Cause commune : la révision 5 (accord du 2026-10-01) a installé `pets.json` et `pet_rules.json` dans
`forever/data/1.60.1.70124/`. Une candidate décodée **sans** les tables des familiers (fixture 1.60.1.70009) doit
alors **hériter** `pets.json` de la version de base, comme les fichiers des 9 classes (`CLASS_FILES`) : sinon une
nouvelle version installée par `forever install --new-version` perdrait le savoir des familiers (c'est ce que
signale `test_install_new_version.py`). Le décodeur fait désormais cela (`forever/pipeline/decode.py`, `optional`
contient `pets.json`, note « hérité de … » ou « absent » si la base ne l'a pas). Cinq tests portent l'ancienne
prémisse (« jamais hérité », comptes d'avant la révision 5).

Preuve tirée des données : `forever/data/1.60.1.70124/pets.json` et `pet_rules.json` présents (manifeste, révision 5) ;
`uv run pytest tests/unit/test_install_new_version.py` sans la correction du décodeur : la nouvelle version n'a pas
`pets.json` (fichier présent dans la version précédente).

## C1 — `tests/unit/test_decode_pets.py::test_candidate_without_pet_tables_notes_the_absence` (verrouillé, bloc A)

Prémisse contredite : la base a maintenant `pets.json`, la candidate sans tables l'hérite.

```diff
-def test_candidate_without_pet_tables_notes_the_absence(tmp_path):
+def test_candidate_without_pet_tables_inherits_pets_json(tmp_path):
     deps = isolated_deps(tmp_path)
     cand = decode_version(deps, PREVIOUS_VERSION, csv_dir=WAGO_70009, out=tmp_path / "cand")
-    assert not (cand.root / PREVIOUS_VERSION / PETS_FILE).exists()
-    assert any(o.startswith(f"{PETS_FILE} absent") for o in cand.observations)
+    assert read_json(cand.root / PREVIOUS_VERSION / PETS_FILE)["inherited_from"] == LOCAL_VERSION
+    assert any(o.startswith(f"{PETS_FILE} hérité de {LOCAL_VERSION}") for o in cand.observations)
```

(Et la référence du registre, si elle y figure, suit le nouveau nom.)

## C2 — `tests/unit/test_decode_version.py` (verrouillé, bloc C : comptes)

`pets.json` hérité par la candidate de la fixture 1.60.1.70009 : un fichier de plus.

```diff
+from forever.pipeline.pets import PETS_FILES
-EXPECTED_FILES = {*DECODED_FILES, *INHERITED_FILES, *CHARACTER_FILES, "sources.json"}
+EXPECTED_FILES = {*DECODED_FILES, *INHERITED_FILES, *CHARACTER_FILES, *PETS_FILES, "sources.json"}
@@ test_candidate_is_a_complete_data_dir
-        names == EXPECTED_FILES and len(names) == 19
-    )  # PV1, bloc C : pvp_rules.json hérité ; T08b : origins.json, character_scaling.json ; CH0 : pet_rules.json
+        names == EXPECTED_FILES and len(names) == 20
+    )  # PV1, bloc C : pvp_rules.json hérité ; T08b : origins.json, character_scaling.json ; CH0 : pet_rules.json, pets.json
```

## C3 — `tests/unit/test_install_new_version.py` (T08a, comptes de fichiers)

La version précédente installée (1.60.1.70124) porte deux fichiers de plus, hérités par la candidate.

```diff
 PV1_ADDED |= {"character_scaling.json"}  # T08b, révision 4 : hérité par la candidate de la fixture 1.60.1.70009
+PV1_ADDED |= {"pets.json", "pet_rules.json"}  # CH0, révision 5 : hérités par la candidate de la fixture 1.60.1.70009
```

## C4 — `tests/unit/test_review_t08b.py::test_carried_cap_keeps_its_original_date_and_revision` (T08b)

Prémisse contredite : le test suppose que le plafond de la bêta a été posé à la révision courante
(`carried_to == revision du plafond + 1`). Depuis la révision 5, le plafond garde sa révision d'origine (4) et
une nouvelle installation l'emporte à la révision 6 : `carried_to` vaut la révision courante des données + 1.

```diff
     before = read_json(DATA_DIR / LOCAL_VERSION / "meta.json")["game_state"]["beta_level_cap"]
+    current = read_json(DATA_DIR / LOCAL_VERSION / "sources.json")["revision"]
     apply_install(deps, str(cand.root), motif="test")
     state = read_json(data_copy / LOCAL_VERSION / "meta.json")["game_state"]["beta_level_cap"]
     assert (state["date"], state["revision"]) == (before["date"], before["revision"])
-    assert state["carried_to"] == before["revision"] + 1
+    assert state["carried_to"] == current + 1
```

## C5 — `tests/unit/test_verify_version.py::test_candidate_is_ok_and_lists_inherited_files` (T08b)

Même cause : la candidate de la fixture 1.60.1.70009 hérite `pets.json`, que `forever verify` liste parmi les
fichiers hérités (comme les fichiers des 9 classes et `character_scaling.json`).

```diff
+from forever.pipeline.pets import PETS_FILES
@@ test_candidate_is_ok_and_lists_inherited_files
-    assert set(r["inherited"]) == set(INHERITED_FILES) | set(CLASS_FILES) | set(CHARACTER_FILES)  # PV1, T08b
+    assert set(r["inherited"]) == set(INHERITED_FILES) | set(CLASS_FILES) | set(CHARACTER_FILES) | set(PETS_FILES)  # PV1, T08b, CH0
```

## Hors demande

- `docs/research/valeurs-ecrites-a-la-main.md` régénéré par `forever origins inventory` (rapport généré, pas un
  test) : les valeurs écrites à la main de `pet_rules.json` y entrent.
