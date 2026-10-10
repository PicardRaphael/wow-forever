# P06b — demandes de correction de tests verrouillés

Regroupées pour une seule validation (consigne du 2026-10-10). Chaque correction porte sur une prémisse fausse du
test, pas sur le comportement voulu ; le code n'est pas changé pour les contourner.

## Bloc A (commit « P06b: tests (bloc A) », e7fcbc1)

**Acceptées le 2026-10-10, appliquées dans 7b5a264.**

### 1. `tests/unit/test_bridge_loop_p06b.py::test_parts_in_any_order_make_one_message` — emplacement relu
- **Preuve** : le message porte `slot=2` (prochain emplacement que le jeu chargera). Comme en P06a
  (`Bridge._accept` : `self.first_slot = record.slot`), le pont publie la réponse à partir de l'emplacement 2 : le jeu
  ne relira jamais l'emplacement 1. Le test relit l'emplacement 1 après le message complet, qui garde la dernière
  publication « parts » (faite avant que le numéro d'emplacement soit connu) : `'parts' == 'done'` échoue.
- **Diff proposé** :
  ```diff
  -    assert len(agent.calls) == 1 and replies(addons)[-1].status == "done"
  +    assert len(agent.calls) == 1 and replies(addons, 2)[-1].status == "done"
  ```

### 2. `tests/unit/test_bridge_loop_p06b.py::action` (assistant de 7 tests d'actions) — emplacement relu
- **Preuve** : même cause : le message d'action porte `slot=2`, la réponse du pont est écrite à partir de
  l'emplacement 2 ; l'emplacement 1 n'a reçu que la publication des cartes, sans réponse (`IndexError` sur
  `replies(addons)[-1]`).
- **Diff proposé** :
  ```diff
  -    return bridge, addons, replies(addons)[-1], [e for e in events(tmp_path) if e["event"] == "action"]
  +    return bridge, addons, replies(addons, 2)[-1], [e for e in events(tmp_path) if e["event"] == "action"]
  ```

### 3. `tests/unit/test_bridge_loop_p06b.py::test_message_event_keeps_the_whole_context` — clés interdites
- **Preuve** : le test cherche la chaîne `"pixels"` dans tout le journal, mais elle y est comme **valeur** du champ
  `via` (`"via": "pixels"`, écrit par P06a pour tout message lu sur la bande, `test_bridge_loop.py:155`). La règle
  est l'absence de **clé** `pixels`, `image`, `bgra` (`journal._FORBIDDEN`, contrôlée ainsi par
  `test_bridge_loop.py:264`).
- **Diff proposé** :
  ```diff
  -    for line in (tmp_path / "journal").glob("*.jsonl"):
  -        for key in ("pixels", "image", "bgra"):
  -            assert f'"{key}"' not in line.read_text(encoding="utf-8")
  +    for event in events(tmp_path):
  +        assert not {"pixels", "image", "bgra"} & set(event)
  ```

## Bloc C (commit « P06b: tests (bloc C) », fda590b) — en attente d'accord

### 4. `tests/unit/test_profile_schema3.py::test_schema_2_is_read_then_written_as_3` — date du profil d'origine
- **Preuve** : le profil de schéma 2 du test porte des champs datés `AT` = 2026-10-10T12:00:00Z, alors que l'horloge
  des tests (`conftest.NOW`) est le 2026-09-27T12:00:00Z. `set_character(deps, "Jen", level=19)` écrit donc une valeur
  **plus ancienne** que celle du profil, et `merge_field` garde la plus récente (règle du schéma 2, inchangée, testée
  par `test_profile_import.py::test_equal_dates_follow_source_order`) : le niveau reste 18. Le test voulait vérifier
  la réécriture en schéma 3 sans perte, pas l'ordre des dates.
- **Diff proposé** (le profil d'origine daté avant l'horloge des tests) :
  ```diff
  -           "characters": {"Jen": {"class": make_field("Mage", "joueur", AT), "level": make_field(18, "joueur", AT)}}}  # fmt: skip
  +           "characters": {"Jen": {"class": make_field("Mage", "joueur", "2026-09-01T00:00:00Z"),
  +                                  "level": make_field(18, "joueur", "2026-09-01T00:00:00Z")}}}  # fmt: skip
  ```
