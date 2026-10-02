# Notes du 1er octobre : demandes de correction de tests (regroupées avant le commit des données)

**Accord de l'utilisateur du 2026-10-02** : révision 3 de 1.60.1.70170 et D1 à D3.

Cause commune : le registre gagne trois mécaniques tirées de la note officielle du 01/10
(<https://us.forums.blizzard.com/en/wow/t/2360696/4>, révision 4 ; `docs/research/notes-blizzard-2026-10-01.md`).
Ce sont trois règles du serveur absentes des données, toutes `absent` et `probable` :
- **B20** : chance de déclenchement réduite des effets de classe et de talents pour un rang de sort très inférieur au
  niveau ;
- **I9** : XP des quêtes de donjon (bonus au-delà de la valeur normale réduit de 50 %) ;
- **K6** : honneur (coûts relevés d'environ 50 %, plafond porté à 25 000).

Le total passe de 126 à 129. La couverture reste à 53 entrées `teste` ou mieux (aucune des trois n'est testée).
Seuls les trois tests qui figent ces comptes échouent. La révision 3 de 1.60.1.70170 (arbre de travail) ne casse
aucun test : `uv run tasks.py test-fast`, 1 910 verts avant la modification du registre.

## D1 — `tests/unit/test_registry.py::test_repository_registry_is_valid_strict`

```diff
-    assert report.total == 126  # T04b : H11 ; T04c : I7 ; T05 : B18, B19, C9, I8 ; PV1 : K1 à K5 ; CH0 : L1 à L12 ; L13
+    assert report.total == 129  # T04b : H11 ; T04c : I7 ; T05 : B18, B19, C9, I8 ; PV1 : K1 à K5 ; CH0 : L1 à L12 ; L13 ; notes du 01/10 : B20, I9, K6
```

## D2 — `tests/unit/test_registry.py::test_repository_coverage`

```diff
-        coverage(REGISTRY_PATH) == "53/126"
+        coverage(REGISTRY_PATH) == "53/129"
```

## D3 — `tests/unit/test_registry.py::test_main_strict_on_repository`

```diff
-    assert out.startswith("Registre : 126 mécaniques")
+    assert out.startswith("Registre : 129 mécaniques")
```
