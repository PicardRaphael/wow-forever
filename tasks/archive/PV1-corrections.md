# PV1 — demandes de correction de tests verrouillés

Présentées ensemble avant la fusion (règle du skill `/tranche`). Chaque correction attend l'accord de l'utilisateur.

## 1. `tests/unit/test_profile_import.py::test_client_build_attached_per_snapshot_and_session` (bloc A)

- **Prémisse fausse** : la seconde moitié du test veut lire la version du client d'une classe « venue du journal
  seul », mais elle planifie l'import sur le **même profil** que la première moitié, où `run(deps, sv)` vient
  d'écrire Moi avec la classe de ForeverLogger. Même valeur (Mage) : la règle de fusion garde la source la plus
  directe, ForeverLogger (verrouillé par `test_equal_dates_follow_source_order`, dernière assertion :
  `same == logger`). Le champ lu est donc celui de ForeverLogger (client 1.60.1.70009, instantané de 13:33:20 UTC),
  pas celui du journal. L'assertion sur le premier journal passait par coïncidence (même version).
- **Preuve** : sortie du test : `assert '1.60.1.70009' == '1.60.1.70124'` sur `both` ; `both["fields"]["class"]`
  a pour source `ForeverLogger`. Les deux tests verrouillés ne peuvent pas passer ensemble sur un profil non vide.
- **Code** : conforme aux deux règles (version par session vérifiée sur un profil vide : le test corrigé passe,
  essayé sur une copie).
- **Diff proposé** (planifier la partie « journal seul » sur un profil vide) :

```diff
-    first = planned_char(plan_import(deps, sv_dir=None, logs_dir=log1_only, utc_offset=OFFSET), "Moi")
+    fresh = replace(deps, profile_path=deps.profile_path.with_name("journal-seul.json"))  # profil vide
+    first = planned_char(plan_import(fresh, sv_dir=None, logs_dir=log1_only, utc_offset=OFFSET), "Moi")
     assert first["fields"]["class"]["client_build"] == "1.60.1.70009"  # 14:55:24 locale, 12:55:24 UTC
-    both = planned_char(plan_import(deps, sv_dir=None, logs_dir=LOGS, utc_offset=OFFSET), "Moi")
+    both = planned_char(plan_import(fresh, sv_dir=None, logs_dir=LOGS, utc_offset=OFFSET), "Moi")
```

## 2. `tests/unit/test_decode_classes.py::test_mage_part_matches_talents_json` (bloc B1)

- **Prémisse fausse** : le test compare la description et le sort décodés du client aux champs `desc` et
  `spellIds` de `talents.json`, qui sont ceux **du dépôt** (gabarit `{0}`, identifiants du seed) ; les valeurs du
  client sont rangées dans `source.client_desc` et `source.client_spell_ids` de chaque talent
  (`forever/pipeline/install.py`, champs du client ajoutés à l'installation ; `sources.json` : « desc : gabarit du
  dépôt ({i}) ; gabarit brut et identifiants de sort du client dans source »).
- **Preuve** : `forever/data/1.60.1.70124/talents.json`, talent `wandSpecialization` : `desc` =
  « Increases your damage with Wands by {0}%. », `source.client_desc` = « … by $s1%. » ; sortie du test :
  `'Increases your damage with Wands by $s1%.' != 'Increases your damage with Wands by {0}%.'`. Sept talents ont un
  `spellIds[0]` du dépôt différent du sort du client (arcaneGeometry, arcaneBlast, missileBarrage, flameThrowing,
  hotStreak, iceLance, fingersOfFrost).
- **Code** : conforme (le test corrigé passe, essayé sur une copie).
- **Diff proposé** :

```diff
-                r["desc"],
+                r["source"]["client_desc"],
             )
-            assert g["spell_id"] == r["spellIds"][0]
+            assert g["spell_id"] == r["source"]["client_spell_ids"][0]
```

## 3. `tests/unit/test_decode_class_spells.py::test_mage_part_matches_spells_json` (bloc B3)

- **Prémisse fausse** : le test lit `name` et `spell_ids` au premier niveau de chaque sort de `spells.json` ; le
  fichier installé ne les porte pas : le nom anglais est dans `decode_rules.json` (`spells.<clé>`) et les
  identifiants des rangs dans `source.rank_spell_ids`.
- **Preuve** : `forever/data/1.60.1.70124/spells.json`, sort `frostbolt` : clés `school, range, slow, slow_dur,
  binary, projectile_speed, ranks, source` ; `source.rank_spell_ids` = identifiants des 11 rangs. Sortie du test :
  `KeyError: 'name'`.
- **Code** : conforme (le test corrigé passe, essayé sur une copie : rangs, niveaux, temps d'incantation, mana et
  recharges des 15 sorts suivis identiques).
- **Diff proposé** :

```diff
-        (spell,) = [s for s in mage.values() if s["name"] == ref["name"]]
+        (spell,) = [s for s in mage.values() if s["name"] == decode_rules["spells"][key]]
         ranked = [r for r in spell["ranks"] if r["rank"] is not None]
-        assert [r["spell_id"] for r in ranked] == ref["spell_ids"], key
+        assert [r["spell_id"] for r in ranked] == ref["source"]["rank_spell_ids"], key
```

## 4. `tests/unit/test_decode_classes.py::test_off_grid_nodes_are_listed_unresolved` (bloc B1)

- **Prémisse devenue fausse** : le test exige que tout nœud hors grille garde une colonne ou un palier `null` et
  figure dans `unresolved_nodes`, et que le Paladin en ait au moins un. Ton relevé en jeu du 2026-09-30 place
  Improved Seal of Fury (palier 3, colonne 1) et Swift Judgement (palier 4, colonne 1), certitude certain ; tu as
  demandé de les retirer des nœuds non résolus.
- **Preuve** : `decode_rules.json`, `observed_positions.Paladin` ; paliers décodés du client (ordonnées 3330 et 3930)
  identiques à ceux du relevé, colonne 1 libre dans ces deux rangées de Protection (colonnes 2 à 4 occupées). Le
  nouveau test `tests/unit/test_observed_positions.py` couvre le placement, le prérequis et l'arrêt en cas de
  désaccord avec le client. Restent non résolus : les deux nœuds du Démoniste (palier seulement communautaire).
- **Diff proposé** (le test ignore les nœuds placés par un relevé en jeu ; la prémisse « Paladin » devient « au
  moins une classe », le Démoniste) :

```diff
     nodes = {int(r["ID"]): r for r in csv_rows("TraitNode")}
+    observed = decode_rules.get("observed_positions", {})
     with_unresolved = set()
     for cls, c in doc["classes"].items():
         expected = {}
         for t in talents_of(c):
+            if t["key"] in observed.get(cls, {}):
+                continue  # placé par un relevé en jeu (test_observed_positions.py)
             x, y = int(nodes[t["node_id"]]["PosX"]), int(nodes[t["node_id"]]["PosY"])
@@
-    assert "Paladin" in with_unresolved  # plan de PV1 : écart relevé sur l'arbre du Paladin
+    assert "Warlock" in with_unresolved  # paliers du Démoniste : sources communautaires seulement
```

## 5. `tests/unit/test_decode_races.py::test_mage_racial_values_equal_the_community_record` (bloc B2)

- **Prémisse devenue fausse** : le test lit le relevé communautaire dans `forever/data/1.60.1.70124/racials.json`,
  retiré à la révision 2 (D5, ton accord) ; le relevé y vit désormais dans la copie figée `_seed_racials.json`,
  de contenu identique (`tests/unit/test_install_r2.py::test_seed_racials_is_a_frozen_copy_of_the_community_record`).
- **Preuve** : sortie du test : `FileNotFoundError: …\1.60.1.70124\racials.json`. Le test corrigé passe (essayé sur
  une copie) : les grandeurs du Mage décodées du client restent égales au relevé.
- **Diff proposé** :

```diff
-    record = read_json(DATA_DIR / LOCAL_VERSION / "racials.json")["races"]
+    record = read_json(DATA_DIR / LOCAL_VERSION / "_seed_racials.json")["races"]  # copie figée du relevé (D5)
```

## 6. `tests/unit/test_plugin_evals.py::test_report_loads_the_real_suite` (bloc F)

- **Prémisse devenue fausse** : compte oublié dans le commit « tests » du bloc F. Le test fige encore 58 cas dont
  38 positifs ; la suite en compte 62 dont 41 positifs (plan de PV1, bloc F.5 : trois cas PvP et un voisin),
  comptes déjà verrouillés dans `test_fifty_eight_cases_thirty_eight_positive_twenty_negative`.
- **Preuve** : sortie du test : `assert 62 == 58` (`scripts/plugin_eval_report.py`, `load_cases(plugin/evals)`).
- **Diff proposé** :

```diff
-    assert len(loaded) == 58
-    assert sum(1 for v in loaded.values() if v["polarity"] == "positif") == 38
+    assert len(loaded) == 62  # PV1 : trois cas PvP et un voisin
+    assert sum(1 for v in loaded.values() if v["polarity"] == "positif") == 41
```
