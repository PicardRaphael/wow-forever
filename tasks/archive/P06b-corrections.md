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

## Bloc C (commit « P06b: tests (bloc C) », fda590b)

**Acceptée le 2026-10-10 (profil d'origine daté du 1er septembre).**

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

## Retours de la sonde H (commit « P06b: tests des retours de la sonde H … », 9da81ca) — acceptées le 2026-10-11, appliquées

### 5. `tests/unit/test_sonde_h.py` (`quiet_steps` et `test_a_pass_over_its_limit_stops_and_leaves_an_error`) — `Step` sans `data`
- **Preuve** : `forever.update.Step` est un `NamedTuple` à quatre champs, `name`, `status`, `detail`, `data`
  (`forever/update.py`, classe `Step`) ; l'assistant du test construit `Step(step, "rien", "simulé")` et
  `Step("clone", "fait", "débloqué")` sans `data` : `TypeError` dans le fil du passage, qui ne va jamais jusqu'à
  l'étape bloquée (`stuck.wait(5)` faux) ni jusqu'à l'erreur simulée. Le code passe sur la copie corrigée (les 2 tests, vérifié le 2026-10-10).
- **Diff proposé** :
  ```diff
  -        monkeypatch.setattr(update, fn, overrides.get(step) or (lambda *a, step=step: update.Step(step, "rien", "simulé")))
  -    monkeypatch.setattr(update, "_step_game", overrides.get("jeu") or (lambda run: (update.Step("jeu", "rien", "simulé"), None)))
  +        monkeypatch.setattr(update, fn, overrides.get(step) or (lambda *a, step=step: update.Step(step, "rien", "simulé", {})))
  +    monkeypatch.setattr(update, "_step_game", overrides.get("jeu") or (lambda run: (update.Step("jeu", "rien", "simulé", {}), None)))
  …
  -        return update.Step("clone", "fait", "débloqué")
  +        return update.Step("clone", "fait", "débloqué", {})
  ```

### 6. `tests/unit/test_plugin_evals.py::test_report_loads_the_real_suite` — compte des cas
- **Preuve** : le cas `plugin/evals/pont-question-de-suite-faute` (demandé par l'utilisateur, point 10 de la sonde H)
  porte la suite à 75 cas dont 52 positifs ; le commit « tests » a mis à jour le compte de
  `test_fifty_eight_cases_thirty_eight_positive_twenty_negative` mais pas celui-ci, resté à 74 et 51.
- **Diff proposé** :
  ```diff
  -    assert len(loaded) == 74  # sonde F : un cas par bouton du pont
  -    assert sum(1 for v in loaded.values() if v["polarity"] == "positif") == 51
  +    assert len(loaded) == 75  # sonde F : un cas par bouton du pont ; sonde H : question de suite à faute de frappe
  +    assert sum(1 for v in loaded.values() if v["polarity"] == "positif") == 52
  ```
- **Accord du 2026-10-11** : n° 5 appliquée telle quelle ; n° 6 élargie à la demande de l'utilisateur (décision 239) :
  plus aucun total figé dans `tests/unit/test_plugin_evals.py` (cas complets et valides, catégories connues, comptes du
  rapport calculés sur la suite elle-même) ; un nouveau cas d'évaluation ne casse plus aucun test verrouillé.
