# DJ1 — demandes de correction de tests verrouillés

## 1. `tests/unit/test_cli_dungeon.py::test_dungeon_item_where` (bloc F)

**Prémisse contredite par la fixture.** Le test attend que le taux retenu de l'objet 14149 vienne de Naowh Forever
(`naowh_dj`, version 1.1.11). Or `build_dungeons` lit aussi les SavedVariables de la fixture
(`tests/fixtures/addons/dungeons/WTF/Account/COMPTE/SavedVariables/NaowhForever.lua`) : `journalLoot` contient
l'objet 14149 lâché par Taragaman the Hungerer et `journalKills[2733].n = 1`. Un butin relevé l'emporte toujours
(décision 265, réponse 5 : « mes relevés priment toujours (`certain`) » ; testé par
`tests/unit/test_dungeons.py::test_observed_loot_wins`). Sortie réelle : `source = "relevé"`, `version = None`.

La fixture ne peut pas changer : `tests/unit/test_dungeon_sources.py::test_naowh_runs_skip_player_names` (verrouillé)
fige ce butin relevé.

**Diff proposé** (le test garde son intention : boss, source et version de la source retenue) :

```diff
 def test_dungeon_item_where(capsys, tmp_path, monkeypatch):
     code, out = run(capsys, ["dungeon", "item", "14149", "--json"], tmp_path, monkeypatch)
     assert code == 0
     doc = json.loads(out)
     (hit,) = doc["hits"]
-    assert hit["boss"] == "Taragaman the Hungerer" and hit["source"] == "naowh_dj" and hit["version"] == "1.1.11"
+    assert hit["boss"] == "Taragaman the Hungerer" and hit["source"] == "relevé" and hit["certainty"] == "certain"
+    code, out = run(capsys, ["dungeon", "item", "14148", "--json"], tmp_path, monkeypatch)
+    (hit,) = json.loads(out)["hits"]
+    assert hit["source"] == "fojji" and hit["version"] == "3.3.5"  # sans relevé : source et version de l'addon
     assert validate_provenance(doc["provenance"]) == []
```
