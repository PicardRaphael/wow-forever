# FA1, relevés en jeu du 2026-10-08 : demandes de correction de tests verrouillés

Regroupées pour une seule présentation (consigne de l'utilisateur du 2026-10-08). Diff complet, vérifié (les tests
corrigés passent, test lent du MCP compris) : `tasks/FA1-releves-corrections.patch`. Branche `fa1-releves` ; tests
nouveaux : `tests/unit/test_in_game_survey.py` (commit `5905a8e` après rebase, verts après l'implémentation et la révision 6 de
1.60.1.70245). Chaque test ci-dessous est devenu faux parce que le relevé en jeu contredit sa prémisse, jamais
parce que l'implémentation s'en écarte.

## Format v6 certain (point 1)

### C1. `tests/unit/test_talents_forever_export.py::test_provenance_and_certainty` (ligne 82)

- **Preuve** : le témoin `mage/20/--0530002001-klps-6` a été importé en jeu et réexporté à l'identique, ordre compris
  (relevé de l'utilisateur, `tests/fixtures/talents_forever/mage_builds.json`, cas `leveling-20`) ; la procédure de
  `docs/ADDON.md` (section 7, étape 6) dit : « Tout concorde : la certitude de l'export passe de `probable` à
  `certain` (champ `verified_in_game`) ».
- **Diff proposé** :

```diff
-    assert block["certainty"] == "probable"
+    assert block["certainty"] == "certain"
     prov = block["provenance"]
     assert prov["format"] == "v6"
+    assert prov["verified_in_game"] is True
```

### C2. `tests/unit/test_talents_forever_export.py::test_mcp_build_carries_the_export` (ligne 178, `slow`)

- **Preuve** : la même (C1).
- **Diff proposé** :

```diff
-    assert block["status"] == "ok" and block["certainty"] == "probable"
+    assert block["status"] == "ok" and block["certainty"] == "certain"
```

## Chasseur et Démoniste débloqués (points 3 à 5)

### C3. `tests/unit/test_talents_forever_export.py::test_hunter_export_is_blocked_with_the_missing_talent` (ligne 135)

- **Preuve** : Improved Serpent Sting est absent de l'arbre en jeu (relevé du 2026-10-08) ; la révision 6 l'écarte
  (`observed_absent`) ; plus aucun talent du Chasseur sans correspondance.
- **Diff proposé** :

```diff
-def test_hunter_export_is_blocked_with_the_missing_talent(addon):
+def test_hunter_export_is_no_longer_blocked(addon):
     block = export_build(addon, "Hunter", 20, {}, None)
-    assert block["status"] == "bloque" and "improvedSerpentSting" in block["reason"]
+    assert block["status"] == "ok" and block["reason"] is None
```

### C4. `tests/unit/test_talents_forever_layout.py` : cinq tests

- **Preuve** : `layout.json` régénéré depuis l'addon installé (0.37.1, inchangé) après la révision 6 : Chasseur 50 sur
  50, Démoniste 52 sur 52, prérequis d'Intimidation identique au nôtre ; recoupement `renumbered 4, unmatched 0,
  prereq 0, tree_names 2` ; le rendu ne cite plus `improvedSerpentSting`, `improvedLifeTap`, `amplifyCurse` ni
  `intimidation`.
- **Diff proposé** :

```diff
-def test_hunter_blocked_by_a_talent_missing_from_talents_forever(addon):
+def test_hunter_all_matched_after_the_in_game_survey(addon):
     hunter = addon.layouts["Hunter"]
-    assert matched(hunter) == 50 and not hunter.exportable
-    assert [(u["key"], u["reason"]) for u in hunter.unmatched] == [("improvedSerpentSting", "seulement_forever")]
-    reason = hunter.blocked
-    assert "Improved Serpent Sting" in reason and "improvedSerpentSting" in reason
-    assert "absent de Talents Forever" in reason and "0.37.1" in reason
-    assert "à chaque mise à jour de l'addon" in reason
+    assert matched(hunter) == 50 and hunter.exportable and hunter.unmatched == ()
+    assert hunter.prereq_gaps == ()


-def test_warlock_blocked_by_unknown_rows(addon):
+def test_warlock_all_matched_after_the_in_game_survey(addon):
     warlock = addon.layouts["Warlock"]
-    assert matched(warlock) == 50 and not warlock.exportable
-    assert sorted((u["key"], u["reason"]) for u in warlock.unmatched) == [
-        ("amplifyCurse", "position_inconnue"),
-        ("improvedLifeTap", "position_inconnue"),
-    ]
-    assert "Improved Life Tap" in warlock.blocked and "Amplify Curse" in warlock.blocked
-    assert "CLS1" in warlock.blocked
+    assert matched(warlock) == 52 and warlock.exportable and warlock.unmatched == ()
@@ test_trees_matched_by_index_tree_names_are_cosmetic
-    assert {"Paladin", "Rogue", "Druid", "Priest", "Shaman", "Mage", "Warrior"} == {
+    assert {"Paladin", "Rogue", "Druid", "Priest", "Shaman", "Mage", "Warrior", "Hunter", "Warlock"} == {
         n for n, lay in addon.layouts.items() if lay.exportable
     }
@@ test_crosscheck_of_the_installed_version
-    assert report["totals"] == {"renumbered": 4, "unmatched": 3, "prereq": 1, "tree_names": 2}
+    assert report["totals"] == {"renumbered": 4, "unmatched": 0, "prereq": 0, "tree_names": 2}
@@
-    assert hunter["matched"] == 50 and hunter["export"] == "bloque"
-    assert [g["key"] for g in hunter["prereq"]] == ["intimidation"]
+    assert hunter["matched"] == 50 and hunter["export"] == "possible"
+    assert hunter["prereq"] == []
@@ test_crosscheck_render_is_deterministic
     for words in (
         "0.37.1",
         LOCAL_VERSION,
         "lingeringRage",
-        "improvedSerpentSting",
-        "improvedLifeTap",
-        "amplifyCurse",
-        "intimidation",
         "Shadow Magic",
         "Elemental Combat",
     ):
@@ test_cli_crosscheck
-    assert data["totals"]["unmatched"] == 3
+    assert data["totals"]["unmatched"] == 0
     assert data["provenance"]["game_version"] == LOCAL_VERSION
-    assert "improvedSerpentSting" in out.read_text(encoding="utf-8")
+    assert "lingeringRage" in out.read_text(encoding="utf-8")
```

### C5. `tests/unit/test_addons_status.py::test_talents_forever_change_rechecks_the_export_without_pending_entry` (ligne 131)

- **Preuve** : la même (C4).
- **Diff proposé** :

```diff
-    assert recheck["export"]["Hunter"] == {"status": "bloque", "talents": ["improvedSerpentSting"]}
-    assert recheck["export"]["Warlock"] == {"status": "bloque", "talents": ["amplifyCurse", "improvedLifeTap"]}
-    assert recheck["unmatched"] == 3 and recheck["renumbered"] == 4
+    assert recheck["export"]["Hunter"] == {"status": "possible", "talents": []}
+    assert recheck["export"]["Warlock"] == {"status": "possible", "talents": []}
+    assert recheck["unmatched"] == 0 and recheck["renumbered"] == 4
```

### C6. `tests/unit/test_talents_forever_popular.py::test_legality_on_the_client` (ligne 74)

- **Preuve** : le 4e build populaire du Démoniste n'était « non vérifiable » que par la rangée inconnue d'Amplify
  Curse (CLS1) ; placée par le relevé, il est vérifié **légal** : 45 builds légaux sur 45.
- **Diff proposé** :

```diff
-    assert sum(1 for b in builds if b["legality"] == "légal") == 44
+    assert sum(1 for b in builds if b["legality"] == "légal") == 45
     odd = [(name, b["rank"]) for name, c in popular["classes"].items() for b in c["top"] if b["legality"] != "légal"]
-    assert odd == [("Warlock", 4)]
-    warlock = popular["classes"]["Warlock"]["top"][3]
-    assert warlock["legality"] == "non vérifiable" and warlock["unverifiable"] == ["amplifyCurse"]
+    assert odd == []
```

## Décodage (CLS1, CLS3)

### C7. `tests/unit/test_class_build_legality.py::test_unresolved_tier_uses_community_tier_else_is_undecidable`

- **Preuve** : sa prémisse (des talents du Démoniste sans palier, placés par les seuls paliers communautaires) est
  fausse depuis le relevé : plus aucun talent installé n'a de palier inconnu. Le comportement du moteur
  (`tier_community`, puis « non décidable ») reste à tester, sur une copie où un palier est retiré.
- **Diff proposé** :

```diff
 def test_unresolved_tier_uses_community_tier_else_is_undecidable(gd):
-    warlock = gd.classes["Warlock"]
-    placed = [t for t in talents(gd, "Warlock").values() if t["tier"] is None]
-    assert placed and all(t.get("tier_community") for t in placed)  # prémisse : paliers communautaires
-    t = placed[0]
+    from dataclasses import replace
+
+    # Plus aucun palier inconnu depuis le relevé du 2026-10-08 (CLS1) : palier retiré sur une copie, palier
+    # communautaire égal au palier relevé.
+    trees = copy.deepcopy(gd.classes["Warlock"].trees)
+    t = next(x for tree in trees for x in tree["talents"] if x["key"] == "amplifyCurse")
+    t["tier_community"] = {"tier": t["tier"], "sources": ["copie de test"], "certainty": "probable"}
+    t["tier"] = None
+    warlock = replace(gd.classes["Warlock"], trees=trees)
     pts = (
         filler(gd, "Warlock", t["tree"], t["tier_community"]["tier"], {t["key"]})
         if t["tier_community"]["tier"] > 1
         else {}
     )
     pts[t["key"]] = 1
     assert not [e for e in check_class_build(warlock, gd.constants.talents, pts, 60) if "non décidable" in e]
     blind = copy.deepcopy(warlock.trees)
     for tree in blind:
         for x in tree["talents"]:
             x.pop("tier_community", None)
-    from dataclasses import replace
-
     errors = check_class_build(replace(warlock, trees=blind), gd.constants.talents, pts, 60)
```

### C8. `tests/unit/test_decode_classes.py::test_extra_zero_node_is_placed` (ligne 134)

- **Preuve** : le seul talent gardé à une position au zéro en trop était Improved Serpent Sting (ordonnée 39300),
  absent de l'arbre en jeu ; les deux autres nœuds ×10 (Lightning Reflexes du Chasseur, Holy Specialization du
  Prêtre) sont des doublons périmés. Le choix de l'utilisateur (absence relevée) garde la règle `extra_zero_divisor`
  sans cas vivant ; son mécanisme reste testé sur une position modifiée
  (`tests/unit/test_decode_talents.py::test_extra_zero_in_position_is_corrected`).
- **Diff proposé** :

```diff
-    assert corrected >= 1  # prémisse : la fixture porte un nœud au zéro en trop
+    # Aucun talent gardé au zéro en trop : le seul cas, Improved Serpent Sting, est absent de l'arbre en jeu
+    # (relevé du 2026-10-08, observed_absent) ; mécanisme testé dans test_decode_talents.py.
+    assert corrected == 0
```

### C9. `tests/unit/test_decode_classes.py::test_off_grid_nodes_are_listed_unresolved` (ligne 148)

- **Preuve** : les nœuds hors grille du Démoniste sont placés par le relevé (`observed_positions`, comme le Paladin) ;
  plus aucune classe n'a de nœud non résolu.
- **Diff proposé** :

```diff
-    assert "Warlock" in with_unresolved  # paliers du Démoniste : sources communautaires seulement
+    assert with_unresolved == set()  # Paladin et Démoniste placés par les relevés en jeu (observed_positions)
```

### C10. `tests/unit/test_decode_classes.py::test_stale_duplicate_nodes_are_dropped_for_the_newer_node` (ligne 178)

- **Preuve** : `dropped_nodes` porte désormais aussi les talents absents de l'arbre en jeu (`kept_node` nul, raison
  « absent de l'arbre en jeu : <source> »), testés par
  `test_in_game_survey.py::test_observed_absent_node_is_dropped_with_its_source`.
- **Diff proposé** :

```diff
         for d in c["dropped_nodes"]:
+            if d["kept_node"] is None:
+                continue  # absence relevée en jeu (observed_absent), pas un doublon
             assert d["kept_node"] in kept and d["kept_node"] > d["node_id"]  # le nœud le plus récent l'emporte
```

## Effets de bord

### C12. `tests/unit/test_plugin_version.py::test_plugin_json_has_a_semver_version` (ligne 37)

- **Preuve** : le point 2 ajoute le correcteur `plugin/evals/build-lien-talents-forever/graders/code-outil.md` (le
  lien comparé au code rendu par `forever_build` dans la même exécution) ; `plugin/` change, donc
  `test_fingerprint_is_up_to_date` exige de relever la version (`plugin.json` passé en 0.8.1, empreinte recalculée
  par `scripts/plugin_fingerprint.py`), que ce test épingle à 0.8.0.
- **Diff proposé** :

```diff
-    # calculé, builds populaires), FA1.
-    assert version == "0.8.0"
+    # calculé, builds populaires), FA1 ; 0.8.1 : cas d'évaluation comparé au code rendu par l'outil (relevés du
+    # 2026-10-08, décision 210).
+    assert version == "0.8.1"
```

### C13. `tests/unit/test_decode_class_spells.py::test_community_positions_are_separate_and_probable` (ligne 237)

- **Preuve** : les paliers communautaires d'Improved Life Tap et d'Amplify Curse sont gardés dans `decode_rules.json`
  (sources du recoupement, concordantes avec le relevé) mais ne s'appliquent qu'à un palier inconnu ; le relevé en
  jeu les place, donc ni `tier_community` ni `unresolved`.
- **Diff proposé** :

```diff
     positions = decode_rules["community_positions"]
+    observed = decode_rules["observed_positions"]
     for cls, c in doc["classes"].items():
         talents = {t["key"]: t for tree in c["trees"] for t in tree["talents"]}
-        wanted = {k: v for k, v in positions.get(cls, {}).items() if isinstance(v, dict)}
+        seen = observed.get(cls, {})  # palier relevé en jeu : le palier communautaire ne sert plus
+        wanted = {k: v for k, v in positions.get(cls, {}).items() if isinstance(v, dict) and k not in seen}
```

## Test nouveau corrigé avant l'implémentation

### C11. `tests/unit/test_in_game_survey.py::test_synthetic_back_edge_is_dropped` (et son voisin)

- **Preuve** : la version du commit `5905a8e` ajoutait le retour d'une arête dont la source était un talent de
  rangée 1 sans prérequis : la source n'avait alors plus que la cible pour prérequis, ce qui fait un **cycle fermé**,
  que le décodage refuse à juste titre (comme `test_synthetic_closed_cycle_stops_the_decode`). Le cas de DON5 est
  une chaîne : Bestial Wrath n'a qu'Intimidation, qui a aussi Bestial Swiftness.
- **Correction appliquée** (déjà dans le dépôt, à valider) : la paire est cherchée dans toutes les classes, avec une
  source qui a elle-même un seul prérequis (`_chain`) ; la vraie voie (`test_synthetic_real_alternative_is_kept`) se
  vérifie sur la même chaîne.
