# T06b — demandes de correction de tests verrouillés

Présentées ensemble avant la fusion (règle du skill `/tranche`). Chaque correction attend l'accord de l'utilisateur.

## 1. `tests/unit/test_install.py::test_change_outside_the_rules_is_refused` (bloc B)

- **Prémisse fausse** : le test suppose que le rang 1 d'Improved Frostbolt vaut `[1]` avant la modification de la
  candidate ; les données disent `[0.1]` (réduction d'incantation de 0,1 s).
- **Preuve** : `forever/data/1.60.1.70009/_seed_talents.json` (et `talents.json` en r1), talent `improvedFrostbolt`,
  `ranks` = `[[0.1], [0.2], [0.3], [0.4], [0.5]]`. Sortie du test :
  `('improvedFrostbolt.ranks[1]', [0.1], [9]) != ('improvedFrostbolt.ranks[1]', [1], [9])`.
- **Code** : conforme (l'écart est bien refusé, rien n'est écrit) ; seule la valeur attendue `before` est fausse.
- **Diff proposé** :

```diff
-    assert [(c["path"], c["before"], c["after"]) for c in plan["refused"]] == [("improvedFrostbolt.ranks[1]", [1], [9])]
+    assert [(c["path"], c["before"], c["after"]) for c in plan["refused"]] == [
+        ("improvedFrostbolt.ranks[1]", [0.1], [9])
+    ]
```

## 2. `tests/unit/test_data_import.py::test_version_dir_contains_exactly_expected_files` (bloc B)

- **Prémisse fausse** : l'ensemble exact se construit sur `SEED_FILES` ; en retirant `talents.json` et `spells.json`
  de `SEED_FILES` (ils ne sont plus des copies du seed depuis la révision 2), le commit « tests (bloc B) » les a aussi
  retirés, sans le vouloir, de l'ensemble des fichiers attendus du dossier.
- **Preuve** : `forever/data/1.60.1.70009/` contient `talents.json` et `spells.json` (lus par le mode forever,
  `forever/gamedata.py`) ; sortie du test : « Extra items in the left set: 'talents.json', 'spells.json' ».
- **Diff proposé** :

```diff
     assert names == set(SEED_FILES) | {
+        "talents.json",  # T06b : valeurs du client (révision 2), plus des copies du seed
+        "spells.json",
         "overrides.json",
```
