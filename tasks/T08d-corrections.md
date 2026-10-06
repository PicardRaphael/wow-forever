# T08d — Demandes de correction de tests verrouillés

Demandes regroupées, à présenter avant la fusion (consigne de l'utilisateur du 2026-10-06).

## 1. `tests/unit/test_update_chain.py::test_cli_json_exit_codes` (bloc E)

**Constat.** La seconde moitié du test rappelle le montage (`montage(change=…)`) dans le **même cache** que la
première. Le premier passage a déjà relevé les CSV de `1.60.1.79999` (`<cache>/wago/1.60.1.79999/` et son
`fetch.json`). Au second passage, `fetch_tables` trouve chaque fichier conforme à son empreinte et ne le
retélécharge pas (`forever/pipeline/fetch.py`, `_cached`, puis la boucle de `fetch_tables` : « un fichier du cache
conforme à son empreinte n'est pas retéléchargé, sauf `refresh` »). Le coefficient changé servi par `FakeHttp`
n'arrive donc jamais : le passage rend `0` au lieu de `6`.

Le comportement du cache est voulu (les tables d'un build publié ne changent pas, T02) : c'est la prémisse du test
qui est fausse, pas le code.

**Preuve.** La même séquence, avec `<cache>/wago/1.60.1.79999/` retiré entre les deux appels, passe (sonde du
2026-10-06, `1 passed`). Les autres tests du coefficient changé (`test_a_mage_value_changed_…`,
`test_cli_text_names_the_verdict`) utilisent un cache neuf et passent.

**Diff proposé** (une ligne ajoutée, aucune assertion changée) :

```diff
     assert payload["provenance"]["certainty"] in ("certain", "probable", "suppose")
 
+    shutil.rmtree(deps.cache_dir / "wago" / TARGET)  # tables relevées au premier passage : jamais retéléchargées
     deps, _ = montage(change=("SpellEffect", "116", "EffectBonusCoefficient"))
     assert main(["update", "--dry-run", "--json", "--only", "jeu"], deps) == EXIT_PENDING
```
