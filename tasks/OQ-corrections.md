# Pistes du 2026-10-01 : demandes de correction de tests (regroupées avant le commit des données)

**Accord de l'utilisateur du 2026-10-02** : révision 6 et C1 à C6, C2 en variante stricte ; découpe de L1 en L1 et
L13, d'où C7 à C9 (comptes du registre).

Cause commune : la révision 6 de 1.60.1.70124 (en attente d'accord, arbre de travail) ramène la marge
d'apprivoisement (`pet_rules.json`, `tame.level_margin`, registre L1) de 2 à **0 niveau**. La source est le texte
officiel des notes de développement de la bêta (<https://us.forums.blizzard.com/en/wow/t/2360696>, 24 septembre 2026,
révisées le 1er octobre, section Hunter > Pets, lu le 2026-10-02). Il remplace le relevé de joueurs de Forever
Bestiary. Une règle du serveur portée par un texte officiel passe de `suppose` à `probable`, jamais `certain` sans
mesure (`docs/DATA_SOURCES.md`, notes officielles). Elle est écrite à la main (origine `manuel`, au plus `probable`
selon `forever/origins.py`). Six tests (C1 à C6) portent l'ancienne prémisse : marge relevée par des joueurs (`addon`,
`suppose`), règle `manuel` bornée à `suppose`, révision 5 des données.

Preuve tirée des données : `forever/data/1.60.1.70124/pet_rules.json` (`tame.level_margin` : 0, `probable`,
`manuel`), `origins.json` (règle `/rules/tame.level_margin`), `sources.json` (`revision` 6, `revised_at`
2026-10-02), `revisions.json` (révision 6, `manual_changes`) ; `uv run tasks.py test-fast` : 6 échecs, tous listés
ici (l'inventaire `docs/research/valeurs-ecrites-a-la-main.md`, document régénéré, est à jour).

## C1 — `tests/unit/test_pet_rules.py::test_tame_margin_stays_suppose_after_reading_the_client` (CH0, bloc C)

Prémisse contredite : la marge vient maintenant d'un texte officiel, plus d'un relevé de joueurs. Le test garde la
lecture du client (aucune borne de niveau dans `SpellTargetRestrictions`) et vérifie la nouvelle source.

```diff
-def test_tame_margin_stays_suppose_after_reading_the_client(doc):
+def test_tame_margin_comes_from_the_official_notes_after_reading_the_client(doc):
     rule = doc["rules"]["tame.level_margin"]
-    assert rule["certainty"] == "suppose" and rule["origin"] == "addon"
+    assert rule["value"] == 0 and rule["certainty"] == "probable" and rule["origin"] == "manuel"
+    assert rule["registry"] == "L13"
+    assert "us.forums.blizzard.com/en/wow/t/2360696" in rule["source"]
     assert "SpellTargetRestrictions" in rule["note"]
```

Le registre suit le nouveau nom : la marge passe dans la nouvelle entrée L13 (découpe de L1, choix de l'utilisateur du
2026-10-02), L1 garde les bêtes apprivoisables.

## C2 — `tests/unit/test_pet_rules.py::test_certainty_never_above_its_origin` (CH0, bloc C)

Choix de l'utilisateur du 2026-10-02 (variante stricte) : une règle `manuel` reste au plus `suppose`, sauf si sa
source cite le forum officiel de Blizzard ; elle peut alors être `probable` (texte officiel sans mesure).

```diff
 MAX_BY_ORIGIN = {"addon": "suppose", "manuel": "suppose", "client": "certain"}
+OFFICIAL_FORUM = "us.forums.blizzard.com"  # note officielle : règle manuel au plus probable (décision 162)
@@ test_certainty_never_above_its_origin
     for key, rule in doc["rules"].items():
         assert rule["origin"] in MAX_BY_ORIGIN, key
-        assert RANK[rule["certainty"]] <= RANK[MAX_BY_ORIGIN[rule["origin"]]], key
+        official = rule["origin"] == "manuel" and OFFICIAL_FORUM in rule["source"]
+        cap = "probable" if official else MAX_BY_ORIGIN[rule["origin"]]
+        assert RANK[rule["certainty"]] <= RANK[cap], key
```

## C3 — `tests/unit/test_install.py::test_repository_is_revision_two` (T08a, comptes)

```diff
-    assert p["data_revision"] == 5  # T08b : révision 4 (ratios du personnage) ; CH0 : 5 (familiers)
+    assert p["data_revision"] == 6  # T08b : r4 (ratios du personnage) ; CH0 : r5 (familiers) ; r6 (marge)
```

## C4 — `tests/unit/test_install.py::test_status_shows_the_revision` (T08a, comptes)

```diff
-    assert rep["data_revision"] == 5  # PV1 : révisions 2 (9 classes, raciaux) et 3 (dissipations) ; T08b : 4 ; CH0 : 5
-    assert render_status(rep)[0].startswith(f"Données locales {LOCAL_VERSION} r5 ·")
+    assert rep["data_revision"] == 6  # PV1 : r2 (9 classes, raciaux), r3 (dissipations) ; T08b : r4 ; CH0 : r5 ; r6
+    assert render_status(rep)[0].startswith(f"Données locales {LOCAL_VERSION} r6 ·")
```

## C5 — `tests/unit/test_manifest.py::test_manifest_content` (comptes)

```diff
-    assert v["revision"] == 5 and v["revised_at"] == "2026-10-01"  # PV1 : r2, r3 ; T08b : r4 ; CH0 : r5 (familiers)
+    assert v["revision"] == 6 and v["revised_at"] == "2026-10-02"  # PV1 : r2, r3 ; T08b : r4 ; CH0 : r5 ; r6 (marge)
```

## C6 — `tests/unit/test_provenance.py::test_make_provenance` (comptes)

```diff
-    assert p["data_revision"] == 5  # T08b : révision 4 (ratios du personnage) ; CH0 : 5 (familiers)
+    assert p["data_revision"] == 6  # T08b : révision 4 (ratios du personnage) ; CH0 : 5 (familiers) ; 6 (marge)
```

## C7 à C9 — `tests/unit/test_registry.py` (comptes du registre)

Choix de l'utilisateur du 2026-10-02 : L1 est découpée. L1 garde les bêtes apprivoisables (Forever Bestiary,
`suppose`) ; la nouvelle entrée L13 porte la marge (`probable`, `teste`). Le registre a une entrée de plus, testée.

```diff
@@ test_repository_registry_is_valid_strict
-    assert report.total == 125  # T04b : H11 ; T04c : I7 ; T05 : B18, B19, C9, I8 ; PV1 : K1 à K5 ; CH0 : L1 à L12
+    assert report.total == 126  # T04b : H11 ; T04c : I7 ; T05 : B18, B19, C9, I8 ; PV1 : K1 à K5 ; CH0 : L1 à L12 ; L13
@@ test_repository_coverage
-        coverage(REGISTRY_PATH) == "52/125"
-    )  # T04b : H11 ; T04c : I7 ajoutée et testée, B15 testée ; T05 : B14, H3, H5, I5 ; PV1 : K1, K2, K3 ; CH0 : L1 à L12 sauf L5
+        coverage(REGISTRY_PATH) == "53/126"
+    )  # T04b : H11 ; T04c : I7 ajoutée et testée, B15 testée ; T05 : B14, H3, H5, I5 ; PV1 : K1, K2, K3 ; CH0 : L1 à L12 sauf L5 ; L13
@@ test_main_strict_on_repository
-    assert out.startswith("Registre : 125 mécaniques")
+    assert out.startswith("Registre : 126 mécaniques")
     assert (
-        "teste 51" in out and "valide-journal 1" in out
-    )  # B1 validée par les journaux (T04b) ; T04c : I7, B15 ; T05 : B14, H3, H5, I5 ; PV1 : K1, K2, K3
+        "teste 52" in out and "valide-journal 1" in out
+    )  # B1 validée par les journaux (T04b) ; T04c : I7, B15 ; T05 : B14, H3, H5, I5 ; PV1 : K1, K2, K3 ; L13
```
