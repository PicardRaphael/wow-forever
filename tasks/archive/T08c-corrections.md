# T08c — Demandes de correction de tests verrouillés

Regroupées pour être présentées en une fois avant la fusion (commande `/tranche T08c` du 2026-10-05).

## Bloc A

### 1. `tests/unit/test_dbcache.py::test_summary_counts_by_table_and_status` : `max_push`

- Prémisse fausse : le test attend `max_push == 112349`, mais la fixture (README, comptes `pushes`) contient une
  entrée de la poussée **112350** (`QuestV2CliTask` 17, `INVALID`, table hors du projet), choisie exprès par le script
  d'extraction (`ONE_OF`). La poussée la plus haute du fichier est donc 112350 ; le plan disait « `max_push` 112347
  (ou la plus haute de la fixture) ».
- Preuve : `tests/fixtures/hotfix/README.md`, bloc JSON, `"pushes": {…, "112349": 8, "112350": 1, …}`.
- Diff proposé :

```diff
-    assert s["max_push"] == 112349
+    assert s["max_push"] == 112350
```

### 2. `test_crosscheck_matches_the_journal_of_the_same_build` et `test_cli_hotfixes_reads_dbcache` : entrées synthétiques

- Prémisse fausse : les deux tests attendent `only_cache == []`, mais la fixture porte les deux entrées
  **synthétiques** `SpellLevels` 999901 (poussées 100002 `DELETE` et 100001 `VALID`, README), qui ne sont par
  construction dans aucun journal : le recoupement les liste à juste titre dans `only_cache`. Même cause pour le
  troisième cas (journal d'un autre build : 194 entrées seulement dans le cache, pas 192).
- Preuve : `tests/fixtures/hotfix/README.md`, `"synthetic"` ; sortie du recoupement : `only_cache` =
  `[{push 100001, SpellLevels, 999901, VALID}, {push 100002, SpellLevels, 999901, DELETE}]`.
- Diff proposé :

```diff
 def test_crosscheck_matches_the_journal_of_the_same_build(cache, names):
     journal = read_json(JOURNAL)["entries"]
     tracked = tracked_tables(RULES)
     check = crosscheck(cache.entries, names, journal, cache.build, tracked)
-    assert check.only_log == [] and check.only_cache == []
+    synthetic = [("SpellLevels", 999901, "100001"), ("SpellLevels", 999901, "100002")]
+    assert check.only_log == []
+    assert [(e["table"], e["rec_id"], e["push"]) for e in check.only_cache] == synthetic
     assert check.matched == COUNTS["journal_lines"] == 192
     removed = next(e for e in journal if e["table"] == "TraitNode" and e["rec_id"] == 105928)
     fewer = [e for e in journal if e is not removed]
     check = crosscheck(cache.entries, names, fewer, cache.build, tracked)
-    assert [(e["table"], e["rec_id"]) for e in check.only_cache] == [("TraitNode", 105928)]
+    assert [(e["table"], e["rec_id"]) for e in check.only_cache if e["rec_id"] != 999901] == [("TraitNode", 105928)]
     other_build = [{**e, "client_build": "1.60.1.70124"} for e in journal]
     check = crosscheck(cache.entries, names, other_build, cache.build, tracked)
-    assert check.matched == 0 and len(check.only_cache) == 192
+    assert check.matched == 0 and len(check.only_cache) == 192 + len(COUNTS["synthetic"])
```

```diff
     assert block["crosscheck"]["matched"] == 192
-    assert block["crosscheck"]["only_log"] == [] and block["crosscheck"]["only_cache"] == []
+    assert block["crosscheck"]["only_log"] == []
+    assert {e["rec_id"] for e in block["crosscheck"]["only_cache"]} == {999901}
```

## Bloc B

### 3. `tests/unit/test_dbd.py::test_wrong_identifier_is_refused` : altération sans effet

- Test faux par construction (pas par les données) : il échange les champs 0 et 1 de la disposition de `TraitNode`
  **puis leur rend leurs noms et leurs annotations** ; le champ lu en premier s'appelle donc encore `ID` et porte
  `$id$` : la disposition altérée est identique à la vraie, l'identifiant décodé égale `rec_id`, rien n'est refusé.
- Preuve : sortie du test, `LayoutCheck(table='TraitNode', ok=True, … 14 entrée(s) décodée(s), 12 comparée(s), 79 %
  des valeurs égales au build)`.
- Diff proposé (échanger les champs sans les renommer : `TraitTreeID` est lu à la place de l'identifiant) :

```diff
     lay = layouts["TraitNode"]
     fields = list(lay.fields)
-    fields[0], fields[1] = (
-        fields[1]._replace(name="ID", is_id=True),
-        fields[0]._replace(name="TraitTreeID", is_id=False),
-    )
+    fields[0], fields[1] = fields[1], fields[0]  # identifiant lu à la place de TraitTreeID
```

  Vérifié sur une copie hors verrou : 18 tests sur 18 passent avec ce diff.

## Bloc C

### 4. `tests/unit/test_hotfix_overlay.py::test_touched_entities_carry_their_hotfix` : témoin intact mal choisi

- Prémisse contredite par les données : le test prend Booming Voice (nœud 105938) comme talent intact, or la poussée
  112347 le touche réellement : son sort 12321 change (`Spell` 12321, `SpellEffect` 1360666) et un nouveau point
  d'effet (`TraitDefinitionEffectPoints` 25182, courbe 125261, `CurvePoint` 364800, 364801, 364891 à 364893) lui est
  ajouté.
- Preuve : champ `hotfix` de Booming Voice dans la candidate : `rows` = `CurvePoint 364800 … 364893`, `Spell 12321`,
  `SpellEffect 1360666`, `TraitDefinitionEffectPoints 25182`.
- Diff proposé (Improved Heroic Strike, nœud 105958, Armes : aucune entrée ne l'atteint) :

```diff
-    untouched = talents[105938]
+    untouched = talents[105958]  # Improved Heroic Strike (Armes) : aucune entrée de correctif ne l'atteint
     assert HOTFIX_KEY not in untouched
```

### 5. `tests/unit/test_hotfix_overlay.py::test_origins_of_the_candidate` : contrôle complet impossible sur une candidate

- Prémisse fausse (plan : « `forever origins check` vert sur la candidate ») : une candidate n'a pas les fichiers
  propres à l'installation (`_seed_spells.json`, `_seed_talents.json`, `_source_gunba_mage_tree.json`,
  `confirmed_changes.json`, `revisions.json`) et ses `spells.json` décodés des extraits portent des clés que la
  version installée ne couvre pas : 134 écarts, **les mêmes avec et sans correctifs**. Le contrôle complet est fait
  après l'installation (`test_install_carries_origins_and_sources`, vert).
- Preuve : `check_version` sur les deux candidates : mêmes comptes (`non_couverte spells.json` 129, `fichier_absent`
  ×5), aucun sur `classes.json`.
- Diff proposé :

```diff
-    assert check_version(with_fix.parent, LOCAL_VERSION).issues == []
+    issues = {(i.kind, i.file, i.path) for i in check_version(with_fix.parent, LOCAL_VERSION).issues}
+    baseline = {(i.kind, i.file, i.path) for i in check_version(decoded[1].parent, LOCAL_VERSION).issues}
+    assert issues == baseline  # une candidate n'a pas les fichiers propres à l'installation ; les correctifs n'ajoutent rien
+    assert not any(f == "classes.json" for _, f, _ in issues)
```

  Vérifié sur une copie hors verrou : 19 tests sur 19 passent avec les diffs 4 et 5.
