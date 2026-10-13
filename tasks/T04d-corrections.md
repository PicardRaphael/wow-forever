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
