# CJ1 — demandes de correction des tests verrouillés

## 1. `tests/unit/test_route_cj1_bridge.py::test_mcp_forever_route_accepts_race_position_and_character` : nom d'attribut du SDK
- **Constat** : l'objet `Tool` du SDK `mcp` installé expose le schéma d'entrée sous `input_schema` ; le test lit
  `inputSchema` (nom du protocole JSON) et lève `AttributeError` avant toute assertion. Relu avec `input_schema` : le
  test passe (outil, nouveaux paramètres `race`, `start_map`, `start_x`, `start_y`, `character`, plan sans erreur,
  `request.race` rendu).
- **Diff proposé** (assertions inchangées) :
  ```diff
  -    props = tool.inputSchema["properties"]
  +    props = tool.input_schema["properties"]
  ```
- **Statut** : acceptée par l'utilisateur le 2026-10-14, appliquée.
