# FA1 — demandes de correction de tests verrouillés

Regroupées pour une seule présentation avant la fusion (consigne de l'utilisateur du 2026-10-07).

## 1. `tests/unit/test_tf_code.py` : codes de test à deux segments d'arbre au lieu de trois

- **Test** : `test_refusals_in_french[mage/60/111111111111111111111111111111--6-position]` (rouge) ;
  `test_more_than_fifty_eight_positions_are_refused` (vert, mais pour un code mal formé).
- **Preuve** : un code v6 porte toujours trois segments d'arbre avant la génération ; un arbre sans point est un
  segment vide. Codes de la fixture `tests/fixtures/talents_forever/popular.json` et du plan : 
  `mage/60/--0555323331321331251-6` (arbres vide, vide, `0555…`), `mage/20/0500050001---6` (Arcane seul : trois
  tirets avant `6`). `"1" * 30 + "--6"` donne `111…`, vide, puis `6` : deux arbres seulement, refusé à juste titre
  pour sa forme (« forme invalide : 2 segment(s) avant la génération ») avant que le nombre de positions soit lu. De
  même `x/60/1--6` (deux arbres) n'atteint le refus « 58 » que parce que la taille de la disposition est contrôlée
  d'abord.
- **Diff proposé** :

```diff
-        ("mage/60/" + "1" * 30 + "--6", "position"),
+        ("mage/60/" + "1" * 30 + "---6", "position"),
```

```diff
-        decode("x/60/1--6", big)
+        decode("x/60/1---6", big)
```

## 2. `tests/unit/test_plugin_evals.py` : code réel écrit en dur dans un test

- **Test** : `test_talents_forever_cases` (vert ; signalé par la relecture).
- **Preuve** : la ligne `re.search(link["lien"][0]["pattern"], "https://talentsforever.com/mage/20/--0530002001-klps-6")`
  recopie des rangs de talents (chiffres de jeu) qui ne viennent pas d'une fixture citée ; la même valeur est le code
  attendu du cas `leveling-20` de `tests/fixtures/talents_forever/mage_builds.json` (règle `CLAUDE.md` : un test prend
  ses valeurs dans `tests/fixtures/` ou cite sa source).
- **Diff proposé** :

```diff
+from talents_forever_data import load_fixture
@@
-    assert re.search(link["lien"][0]["pattern"], "https://talentsforever.com/mage/20/--0530002001-klps-6")
+    code = load_fixture("mage_builds.json")["cases"]["leveling-20"]["expected_code"]
+    assert re.search(link["lien"][0]["pattern"], "https://talentsforever.com/" + code)
```
