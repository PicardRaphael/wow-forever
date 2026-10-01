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
