# T04d : demandes de correction de tests verrouillés

## 1. `tests/unit/test_addon_logger_xp.py::to_py` (bloc A) — appliquée le 2026-10-13 avec l'accord de l'utilisateur
- **Constat** : `to_py` teste `lupa.lua_type(value) == "table"` ; `lupa.lua_type` est celui du runtime par défaut de
  lupa 2.8 et rend `None` pour une table créée par `lupa.lua51` (relevé : `lupa.lua_type(t)` → `None`,
  `lua51.lua_type(t)` → `table`). `to_py` rend alors la table Lua telle quelle et les cinq comparaisons à un `dict`
  échouent quel que soit le code de l'addon (cible, instance, état de l'XP du rendu de quête ×2, état de
  l'instantané).
- **Preuve** : une copie du fichier avec la seule ligne corrigée passe en entier (14 tests) sur ForeverLogger 0.4.0.
- **Diff proposé** :
```diff
 def to_py(value):
-    if lupa.lua_type(value) == "table":
+    if lua51.lua_type(value) == "table":
         return {k: to_py(v) for k, v in value.items()}
     return value
```

## 2. `tests/unit/test_quests_merge.py::test_quest_learned_in_game_is_a_player_record` (bloc D) — appliquée le 2026-10-13 avec l'accord de l'utilisateur
- **Constat** : le test suppose que la quête 96607 (The Great Outdoors) n'est connue que par `QuestieForeverDB` ; or
  le client l'a vue : `forever/data/1.60.1.70338/quest_rewards.json` porte `seen_quests["96607"]` (révision 4, cache
  des quêtes du 2026-10-13). La règle de priorité (client > relevé du joueur) donne alors le niveau au client, comme
  voulu ; seul le champ visé par le test est mal choisi. Le nom, que le client ne donne pas, vient bien de
  `QuestieForeverDB`.
- **Preuve** : `uv run python -c "import json;print('96607' in json.load(open('forever/data/1.60.1.70338/quest_rewards.json',encoding='utf-8'))['seen_quests'])"` → `True`.
- **Diff proposé** :
```diff
 def test_quest_learned_in_game_is_a_player_record(book):
     q = book.quests[96607]  # QuestieForeverDB de la fixture
     assert q["status"] == "nouvelle"
-    assert q["fields"]["level"]["source"] == "questie_forever"
-    assert q["fields"]["level"]["certainty"] == "probable"
+    assert q["fields"]["name"]["source"] == "questie_forever"
+    assert q["fields"]["name"]["certainty"] == "probable"
```

## 3. `tests/unit/test_lookup_quests.py::test_lookup_by_status_and_dungeon` (bloc D) — en attente
- **Constat** : la fixture de Questie ne garde que 13 quêtes ; les 203 quêtes vues par le client
  (`quest_rewards.json`, révision 4) absentes de cette fixture sont donc `nouvelle` selon la règle du plan (absente de
  la base Classic, présente dans le client). La consultation est paginée (20 par défaut) et triée par niveau : 92432
  (niveau 33) et 96403 (niveau 15) tombent après la première page. La règle et la pagination sont voulues ; seule la
  page demandée par le test est trop courte.
- **Preuve** : `lookup_quests(deps, status="nouvelle", wow_dir=WOW)["total"]` → plus de 20 (quêtes vues par le client
  hors de la fixture de Questie), page triée par niveau.
- **Diff proposé** :
```diff
-    new = lookup_quests(deps, status="nouvelle", wow_dir=WOW)
+    new = lookup_quests(deps, status="nouvelle", wow_dir=WOW, limit=10_000)
```
