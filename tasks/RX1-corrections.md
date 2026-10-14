# RX1 — demandes de correction des tests verrouillés

## 1. `tests/unit/test_engine_route.py::test_missed_dungeon_window_is_infeasible` (bloc C) : farm final et donjon manqué
- **Constat** : ce test veut qu'une route sans arrêt, de 3 à 5, soit **impossible** parce que le farm final dépasse
  la fenêtre du donjon de la fixture (3-3). Or quatre autres tests verrouillés du même commit attendent une route
  **possible** dans la même situation (farm final de 1 ou 2 jusqu'à 5, au-delà de la fenêtre 3-3, sans passage du
  donjon) : `test_prerequisite_and_chain_checked`, `test_exclusive_checked`, `test_log_size_checked`,
  `test_turnin_needs_objective_or_dungeon` (`run(...)` avec `end_level=5` par défaut et `finish=True`). Les deux
  attentes ne peuvent pas tenir ensemble.
- **Règle retenue dans le code** (la plus cohérente avec ces quatre tests) : un donjon dont la fenêtre est
  dépassée **par les arrêts** rend la route impossible ; dépassée **par le farm final**, il est signalé
  (avertissement « donjon … manqué ») et l'optimiseur refuse une telle route (coût infini, `_acceptable`). Le
  passage au placement reste donc une contrainte dure de toute route rendue par `forever route plan`.
- **Diff proposé** (une seule assertion, le reste du test inchangé) :
  ```diff
  -    assert not run(game_data, world, [], start=at3, end_level=5).feasible  # niveau 4 atteint sans le donjon
  +    assert any("manqué" in w for w in run(game_data, world, [], start=at3, end_level=5).warnings)  # par le farm
  ```
