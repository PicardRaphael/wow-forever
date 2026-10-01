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
