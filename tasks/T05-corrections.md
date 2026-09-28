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
