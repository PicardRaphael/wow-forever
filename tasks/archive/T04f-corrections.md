# T04f — demandes de correction des tests verrouillés

## 1. `tests/unit/test_verify_version.py` : ordre des imports (lint seulement)
- **Constat** : `ruff check` (I001) : l'import `forever.pipeline.xp_bonuses` ajouté au commit « tests (bloc A) » est
  placé avant `forever.pipeline.verify` ; l'ordre alphabétique le veut après.
- **Diff proposé** (aucune assertion touchée) :
  ```diff
   from forever.pipeline.quest_rewards import QUEST_FILES
  -from forever.pipeline.xp_bonuses import XP_BONUS_FILES
   from forever.pipeline.verify import verify_version
  +from forever.pipeline.xp_bonuses import XP_BONUS_FILES
  ```

## 2. `tests/unit/test_install_rules.py` : forme du changement `rules` (prémisse fausse)
- **Constat** : l'installation ne connaît de l'ancien `decode_rules.json` que son empreinte (manifeste) : les clés
  changées ne peuvent pas être listées ; le changement est donc rendu sur tout le fichier (`path` `*`, empreintes avant
  et après), comme `added_file` et `replaced_file`. Et le `decode_rules.json` installé garde sa marque
  `inherited_from` (déjà présente dans le dépôt : `forever/data/1.60.1.70124/decode_rules.json` la porte), le fichier
  du dépôt n'étant pas réécrit.
- **Diff proposé** :
  ```diff
  -    assert [c["path"] for c in rules_changes(plan)] == [NEW_KEY] and not plan["refused"]
  +    assert [c["path"] for c in rules_changes(plan)] == ["*"] and not plan["refused"]
  @@
  -    assert [c["path"] for c in rules_changes(revision)] == [NEW_KEY]
  +    assert [c["path"] for c in rules_changes(revision)] == ["*"]
  @@
  -    assert installed[NEW_KEY] == {"note": "règle de lecture de test"} and "inherited_from" not in installed
  +    assert installed[NEW_KEY] == {"note": "règle de lecture de test"}
  ```

## 3. `tests/unit/test_addon_bridge_auras.py` : `Message.Context()` rend deux valeurs (erreur du test)
- **Constat** : `ForeverBridge_Message.Context()` rend `ctx, pieces` (contexte et pièces d'équipement, utilisés par
  `Message.Build`) ; sous `lupa` (`unpack_returned_tuples=True`), l'appel rend un tuple Python, et `ctx[k]` lève
  `TypeError: tuple indices must be integers or slices, not str`. Avec `[0]`, les trois tests passent (vérifié sur une
  copie hors du dépôt).
- **Diff proposé** :
  ```diff
   def context(g):
  -    ctx = g.lua.globals().ForeverBridge_Message.Context()
  +    ctx = g.lua.globals().ForeverBridge_Message.Context()[0]
  ```
