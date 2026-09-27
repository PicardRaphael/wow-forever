# T04c — demandes de correction de tests verrouillés (regroupées avant la fusion)

## 1. `tests/unit/test_measures_refresh.py::test_accepted_refresh_writes_monsters_manifest_and_snapshot`

- **Prémisse contredite** : le test (bloc E) fige l'ensemble des fichiers écrits par `forever measures refresh` à
  `{"monsters.json", "manifest.json", "last.json"}`. Or la relecture (point 3) a montré que l'entrée `monsters.json` de
  `forever/data/1.60.1.70009/sources.json` cite en dur les journaux et `--fit-exclude 3986` : après un rafraîchissement
  écrit, cette source devient fausse (règle `.claude/rules/data.md` : chaque fichier porte ses sources).
- **Correction faite dans le code** (commit « corrections de relecture ») : `apply_refresh` réécrit le seul champ
  `source` de cette entrée (journaux utilisés, Questie, date, PNJ écartés), sans réécrire le reste du fichier ; testé par
  `tests/unit/test_review_t04c.py::test_written_refresh_updates_the_monsters_source` (vert).
- **Diff proposé** (seul changement) :

```diff
-    assert written == {"monsters.json", "manifest.json", "last.json"}
+    assert written == {"monsters.json", "sources.json", "manifest.json", "last.json"}
```
