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

- **Statut** : acceptée par l'utilisateur le 2026-10-15, appliquée ; `tasks/.rouge` vidé.

## 3. Bloc 5 : treize tests d'EX1 qui supposent EllesmereUI allumé par défaut (décision 274 : éteint par défaut)
Ces tests vérifient le lien de profil EllesmereUI et la bascule par rôle ; depuis la décision 274, ils n'existent
qu'après `/fb eui on` (contexte `eui=on`). Correction proposée : rallumer EllesmereUI dans la préparation de ces tests,
**aucune assertion touchée**.

### 3.1 `tests/unit/test_bridge_exports_more.py`, `tests/unit/test_ellesmere_base_choice.py`, `tests/unit/test_rx1c_review.py` (contexte commun)
Dans chacun des trois fichiers, après la construction de `CONTEXT` :
```diff
 CONTEXT = dict(
     line.split("=", 1)
     for line in (FIXTURES / "bridge" / "contexts" / "mage19.txt").read_text(encoding="utf-8").split("\n")
     if "=" in line
 )
+CONTEXT["eui"] = "on"  # CJ1 (décision 274) : EllesmereUI rallumé par le joueur (/fb eui on)
```
Tests concernés : `test_macros_and_ellesmere_links_follow_the_current_build`, `test_without_base_profile_the_reply_says_so`,
`test_without_role_the_reply_says_so`, les quatre `test_exports_button_*` de `test_ellesmere_base_choice.py`,
`test_later_command_is_not_overwritten_by_an_old_game_choice`.

### 3.2 `tests/unit/test_bridge_role_lua.py` (bascule par rôle)
```diff
 def game_with_ellesmere(**kwargs):
     game = Game(prelude=ELLESMERE, **kwargs)
     game.stub.Fire("PLAYER_ENTERING_WORLD", True, False)
     game.slash("/fv")
+    game.slash("/fb eui on")  # CJ1 (décision 274) : bascule seulement après /fb eui on
     return game
```
```diff
-    game = Game(prelude=ELLESMERE, saved={"roles": {"Jen - Forever": "dps"}})
+    game = Game(prelude=ELLESMERE, saved={"roles": {"Jen - Forever": "dps"}, "eui": True})
```
Tests concernés : `test_switch_out_of_combat_with_the_profile_name`, `test_switch_waits_for_the_end_of_combat`,
`test_missing_profile_is_never_switched_to`, `test_ellesmere_automatic_switch_wins_and_is_reported_once`,
`test_saved_role_switches_after_login_with_a_delay`.

- **Statut** : acceptée par l'utilisateur le 2026-10-15, appliquée ; `tasks/.rouge` vidé.
