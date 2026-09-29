# T05 — demandes de correction de tests verrouillés

À présenter à l'utilisateur avant la fusion (règle du skill `/tranche`, décision 70). Aucune n'est appliquée sans son accord.

## 1. Bloc C : `tests/unit/test_rotations_t05.py::test_pyroblast_enters_the_fire_rotation_after_enough_crits`

- **Échec** : `AssertionError: 3` (`assert pyros > 0, n` pour `hs_stacks=3`).
- **Preuve (prémisse contredite, pas le code)** : au niveau 25 contre un monstre du même niveau, un combat dure ~18 s (7 lancers, relevé sur les graines 0 à 5 avec le critique de test à 50 %) ; le troisième critique d'un sort de Hot Streak arrive au mieux au dernier lancer, quand le monstre meurt : Pyroblast à 3 cumuls n'a pas le temps d'être lancé. Nombre de Pyroblast sur 6 graines, `hs_stacks` = 1, 2, 3 : 7, 3, **0** ; sur 30 graines : 33, 20, 4 ; sur 6 graines avec `level_diff=3` (monstre de niveau 28, combats plus longs) : 11, 5, 5. Le journal montre chaque Pyroblast précédé d'au moins `hs_stacks` critiques (partie du test qui passe).
- **Diff proposé** (paramètre de test signalé, comme `HIGH_CRIT`) :

```diff
 def _fire_log(gd, pts, seed, **opts):
     log = []
-    kill_mc(gd, 25, pts, character(gd, 25, "Orc", HIGH_CRIT), "fire", random.Random(seed), log, **opts)
+    # monstre de 3 niveaux de plus (valeur de test) : combats assez longs pour atteindre 3 cumuls
+    kill_mc(gd, 25, pts, character(gd, 25, "Orc", HIGH_CRIT), "fire", random.Random(seed), log, level_diff=3, **opts)
     return log
```

## 2. Bloc F : `tests/unit/test_optimize_leveling.py::test_talented_bonus_adds_legal_points`

- **Échec** : `assert 1 == 4` à la première étape (niveau 10, bonus « Talented » de 3).
- **Preuve (prémisse du test contredite par sa propre structure, pas par le code)** : avec le bonus, `points_available(10, 3)` = 4 points dès le niveau 10 ; l'optimiseur rend une étape par point (`Step.talent` : un seul talent, forme du seed), donc quatre étapes au niveau 10, avec 1, 2, 3 puis 4 points. Le test exige la somme complète **après chaque étape**, ce qu'aucune suite d'étapes d'un point ne peut satisfaire. Le build de fin de chaque niveau, lui, dépense bien tous les points, est légal avec le bonus et illégal sans (vérifié sur une copie du test avec le diff ci-dessous : vert).
- **Diff proposé** :

```diff
-    for s, pts in _points_by_level(bonus):
-        assert sum(pts.values()) == points_available(game_data, s.level, 3)
-        assert check_build(game_data, pts, s.level, 3) == []
-        assert check_build(game_data, pts, s.level) != []  # illégal sans le bonus
+    by_level = {s.level: pts for s, pts in _points_by_level(bonus)}  # build de fin de chaque niveau
+    assert list(by_level) == [10, 11, 12, 13]
+    for level, pts in by_level.items():
+        assert sum(pts.values()) == points_available(game_data, level, 3)
+        assert check_build(game_data, pts, level, 3) == []
+        assert check_build(game_data, pts, level) != []  # illégal sans le bonus
```
