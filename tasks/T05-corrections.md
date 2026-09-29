# T05 — demandes de correction de tests verrouillés

À présenter à l'utilisateur avant la fusion (règle du skill `/tranche`, décision 70). Aucune n'est appliquée sans son accord.

## 1. Bloc C : `tests/unit/test_rotations_t05.py::test_pyroblast_enters_the_fire_rotation_after_enough_crits`

- **Échec** : `AssertionError: 3` (`assert pyros > 0, n` pour `hs_stacks=3`).
- **Preuve (prémisse contredite, pas le code)** : au niveau 25 contre un monstre du même niveau, un combat dure ~18 s (7 lancers, relevé sur les graines 0 à 5 avec le critique de test à 50 %) ; le troisième critique d'un sort de Hot Streak arrive au mieux au dernier lancer, quand le monstre meurt : Pyroblast à 3 cumuls n'a pas le temps d'être lancé. Nombre de Pyroblast sur 6 graines, `hs_stacks` = 1, 2, 3 : 7, 3, **0** ; sur 30 graines : 33, 20, 4 ; sur 6 graines avec `level_diff=3` (monstre de niveau 28, combats plus longs) : 11, 5, 5. Le journal montre chaque Pyroblast précédé d'au moins `hs_stacks` critiques (partie du test qui passe).
- **Diff proposé** (paramètre de test signalé, comme `HIGH_CRIT`) :

```diff
 def _fire_log(gd, pts, seed, **opts):
     log = []
-    kill_mc(gd, 25, pts, character(gd, 25, "Orc", HIGH_CRIT), "fire", random.Random(seed), log, **opts)
+    # monstre de 3 niveaux de plus (valeur de test) : combats assez longs pour atteindre 3 cumuls
+    kill_mc(gd, 25, pts, character(gd, 25, "Orc", HIGH_CRIT), "fire", random.Random(seed), log, level_diff=3, **opts)
     return log
```

## 2. Bloc F : `tests/unit/test_optimize_leveling.py::test_talented_bonus_adds_legal_points`

- **Échec** : `assert 1 == 4` à la première étape (niveau 10, bonus « Talented » de 3).
- **Preuve (prémisse du test contredite par sa propre structure, pas par le code)** : avec le bonus, `points_available(10, 3)` = 4 points dès le niveau 10 ; l'optimiseur rend une étape par point (`Step.talent` : un seul talent, forme du seed), donc quatre étapes au niveau 10, avec 1, 2, 3 puis 4 points. Le test exige la somme complète **après chaque étape**, ce qu'aucune suite d'étapes d'un point ne peut satisfaire. Le build de fin de chaque niveau, lui, dépense bien tous les points, est légal avec le bonus et illégal sans (vérifié sur une copie du test avec le diff ci-dessous : vert).
- **Diff proposé** :

```diff
-    for s, pts in _points_by_level(bonus):
-        assert sum(pts.values()) == points_available(game_data, s.level, 3)
-        assert check_build(game_data, pts, s.level, 3) == []
-        assert check_build(game_data, pts, s.level) != []  # illégal sans le bonus
+    by_level = {s.level: pts for s, pts in _points_by_level(bonus)}  # build de fin de chaque niveau
+    assert list(by_level) == [10, 11, 12, 13]
+    for level, pts in by_level.items():
+        assert sum(pts.values()) == points_available(game_data, level, 3)
+        assert check_build(game_data, pts, level, 3) == []
+        assert check_build(game_data, pts, level) != []  # illégal sans le bonus
```

## 3. Bloc I1 : `tests/unit/test_blind_spots.py::test_estimates_are_positive_bounds_from_the_data`

- **Échec** : `assert (1.009432743248482 is not None and 1.009432743248482 < 1)` (borne d'Évocation).
- **Preuve (prémisse contredite par les données)** : `spells.json.utility.evocation` : `regen_mult` 15, `duration` 8 s ; au niveau 40 (fiche de base, Orc), régénération d'Esprit 19,53 mana/s et réserve 2 321,7 : une Évocation rend 15 × 19,53 × 8 = 2 343 mana, soit 1,009 réserve. Quand la mana borne le combat, l'effet peut donc dépasser 100 % du temps d'incantation ; la borne n'a pas à être inférieure à 1. Les autres assertions du test (Presence of Mind, Combustion, Cold Snap, Wake of Fire) passent.
- **Diff proposé** :

```diff
     evo = estimate_evocation(game_data, 40, {}, "Orc")
-    assert evo is not None and 0 < evo < 1
+    u = game_data.utility
+    assert evo == pytest.approx(u.evocation_regen_mult * ch.spirit_regen * u.evocation_duration_s / ch.mana, rel=1e-12)
+    assert evo > 0
```

## 4. Bloc I1 : `tests/unit/test_registry.py::test_main_strict_on_repository`

- **Échec** : la sortie commence par `Registre : 108 mécaniques`, le test attend `Registre : 104 mécaniques`.
- **Preuve** : le bloc I1 ajoute quatre entrées au registre (B18, B19, C9, I8, décision 88) ; le commit « tests (bloc I1) » a mis à jour `report.total` (108) et la couverture (`37/108`), mais pas la troisième assertion, sur la première ligne de `main` (oubli de ma part, piège déjà noté dans le skill `/tranche`).
- **Diff proposé** :

```diff
-    assert out.startswith("Registre : 104 mécaniques")
+    assert out.startswith("Registre : 108 mécaniques")
```

## 5. Bloc I2 : `tests/unit/test_build_cli.py::test_mcp_returns_the_cli_json` et `::test_mcp_default_preset_is_fast`

- **Échec** : `pytest_socket.SocketBlockedError: A test tried to use socket.socket.`
- **Preuve (défaut du test, pas du code)** : sous Windows, la boucle asyncio du client MCP ouvre une paire de sockets locale ; `pyproject.toml` bloque les sockets (`--disable-socket --allow-unix-socket`) et `tests/integration/test_mcp.py` les autorise pour l'hôte local par `pytestmark = pytest.mark.allow_hosts(["127.0.0.1"])`. Mon test n'a pas repris cette marque. Avec elle (copie du test), les 6 tests du fichier passent, dont les deux cités (même JSON par la CLI et le MCP ; préréglage rapide par défaut).
- **Diff proposé** :

```diff
 import asyncio
 import json
 
+import pytest
 from conftest import FakeHttp
 from mcp import Client
@@
+# La boucle asyncio de Windows ouvre une paire de sockets locale : autorisée, tout autre hôte reste bloqué.
+pytestmark = pytest.mark.allow_hosts(["127.0.0.1"])
 ARGV = ["build", "leveling", "--level", "14", "--preset", "rapide"]
```

## 6. Bloc J : `tests/unit/test_community_builds.py::test_every_build_has_source_date_context_level`

- **Échec attendu** : `dt.date.fromisoformat(None)` et `assert b["author"]` sur 9 builds.
- **Preuve (prémisse contredite par les données de la recherche)** : dans le bloc JSON de `docs/research/community-builds-mage.md`, 9 builds n'ont pas de date (C15, C16, A5, A7, A8, A9, A14, A15, A16) et 6 pas d'auteur (C15, C16, A5, A7, A8, A9, pages de wowtbc.gg sans signature) ; la recherche le signale dans `reliability_flags` de chacun (« date inconnue ou imprécise… », « page non datée, auteur inconnu »). Je n'invente ni date ni auteur.
- **Diff proposé** :

```diff
     for b in doc["builds"]:
-        assert b["source_url"].startswith("https://") and b["author"]
-        dt.date.fromisoformat(b["date"])
+        assert b["source_url"].startswith("https://")
+        flags = " ".join(b["reliability_flags"])
+        if b["author"] is None:  # page sans signature, signalée par la recherche
+            assert "auteur inconnu" in flags, b["id"]
+        if b["date"] is None:  # date inconnue, signalée par la recherche
+            assert "date" in flags and "inconnue" in flags, b["id"]
+        else:
+            dt.date.fromisoformat(b["date"])
         assert b["context"] in CONTEXTS and isinstance(b["level"], int) and 10 <= b["level"] <= 60
```
