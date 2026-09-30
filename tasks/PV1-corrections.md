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
