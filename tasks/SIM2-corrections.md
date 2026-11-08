# SIM2 : demandes de correction de tests verrouillés

## 1. `tests/unit/test_sims_optimise_gear.py::test_each_candidate_is_tried_in_its_slot_and_ranked` (bloc 8)
- **Preuve** : le parcours de test `FROST_STEPS` (`tests/unit/test_sims_brackets.py`) donne au niveau 25
  `{"improvedFrostbolt": 5, "iceShards": 5}` (assertion de `test_talents_follow_the_path_up_to_the_level`), soit la
  chaîne de wowsims `--0505` ; `--0501` est celle du niveau 15. Le test attend `--0501` au niveau 25 : erreur de
  rédaction du test, pas du code.
- **Diff proposé** (une ligne) :
  ```diff
  -    assert first["talentsString"] == "--0501" and "buffs" not in first
  +    assert first["talentsString"] == "--0505" and "buffs" not in first
  ```
