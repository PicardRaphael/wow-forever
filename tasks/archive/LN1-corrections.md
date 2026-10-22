# LN1 — demandes de correction des tests verrouillés

## 1. `tests/unit/test_choice_everywhere.py::test_a_candidate_decoded_from_the_final_carries_its_product` : chemin de la candidate (prémisse fausse)
- **Constat** : `forever decode` écrit la candidate dans `<cache>/candidates/<version>/<version>/` (racine de la
  candidate, puis dossier de la version, comme `forever/data/<version>/`) ; le test lit
  `<cache>/candidates/<version>/sources.json`, qui n'existe pas. Relu après le décodage du test : le fichier
  `candidates/1.60.1.70374/1.60.1.70374/sources.json` porte bien `product` `wow_fictif_finale` et `version_prefix`
  `1.60.`.
- **Diff proposé** (assertion inchangée) :
  ```diff
  -    sources = json.loads((deps.cache_dir / "candidates" / LOCAL_VERSION / "sources.json").read_text(encoding="utf-8"))
  +    candidate = deps.cache_dir / "candidates" / LOCAL_VERSION / LOCAL_VERSION
  +    sources = json.loads((candidate / "sources.json").read_text(encoding="utf-8"))
  ```
