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

## 2. Bloc 2 : trois tests de RX1 qui contredisent les décisions 276 et 277 (questions dans le chat, plus de bouton de livraison séparé)
Les assertions ci-dessous décrivent l'ancien comportement que tu as demandé de changer le 2026-10-14 ; le reste de
chaque test est gardé. L'action `a=route_deliver` reste (elle sert au bouton « Valider et livrer » sous l'aperçu),
seul le bouton séparé de la barre disparaît.

### 2.1 `tests/unit/test_bridge_buttons.py::test_buttons_since_p06b` : liste des boutons visibles
```diff
         "route",
-        "route_deliver",
         "exports",
```
(et la docstring : « RX1 : « Feuille de route » ; la livraison se fait par « Valider et livrer » sous l'aperçu, CJ1 »).

### 2.2 `tests/unit/test_bridge_choices.py::test_route_button_visible_when_rx1_done` : bouton de livraison
```diff
-    keys = {b.key for b in BUTTONS if "RX1" in b.requires}
-    assert {"route", "route_deliver"} <= keys
+    keys = {b.key for b in BUTTONS if "RX1" in b.requires}
+    assert "route" in keys and "route_deliver" not in keys  # CJ1 : plus de bouton séparé (décision 276)
```

### 2.3 `tests/unit/test_bridge_choices.py::test_route_button_publishes_the_choices` : plus de cartes de questions
```diff
-    ids = [c.id for c in cards()]
-    assert ids == [f"choice-{c.id}" for c in ROUTE_CHOICES]
+    assert not [c.id for c in cards() if c.id.startswith("choice-")]  # CJ1 : plus de question dans À valider
```
(la question en cours part avec la réponse, sous le message : test nouveau du bloc 2).

- **Statut** : en attente de ton accord ; d'ici là, ces trois tests sont listés dans `tasks/.rouge`.
