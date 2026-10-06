# T08d — Demandes de correction de tests verrouillés

Demandes regroupées, à présenter avant la fusion (consigne de l'utilisateur du 2026-10-06).

## 1. `tests/unit/test_update_chain.py::test_cli_json_exit_codes` (bloc E) — accordée le 2026-10-06, appliquée

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

## 2. `tests/unit/test_monsters.py::test_installed_table_is_read_by_game_data` (révision 5 de 70170) — révisée

Première version accordée le 2026-10-06 (`certain`, deux PNJ concordants), devenue fausse avant d'être appliquée :
la règle des PNJ nommés de quête (décision 189) écarte de la courbe Sarilus Foulborne et Muglash, les deux seuls PNJ
mesurés au niveau 25.

**Preuve.** `forever/data/1.60.1.70170/monsters.json` (r5 corrigée) : `hp_by_level["25"]` vient de Questie corrigé,
certitude `suppose` ; `questie_correction.range` = [1, 24] (le niveau 25 est hors de la plage mesurée, d'où
`suppose`, règle de T04b citée dans le test lui-même) ; Sarilus Foulborne (3986) et Muglash (12717) dans
`curve_excluded`, raison « PNJ nommé de quête ».

**Diff proposé** (une assertion et son commentaire) :

```diff
-    assert monsters.hp_by_level[25].certainty == "probable"  # un seul PNJ nommé
+    assert monsters.hp_by_level[25].certainty == "suppose"  # PNJ nommés écartés : hors de la plage mesurée (r5)
```

## 3. `tests/unit/test_update_publish.py` (4 tests, garde-fou de la décision 184)

**Constat.** `test_same_tables_are_installed_through_the_clone`, `test_a_red_windows_job_merges_nothing_and_keeps_the_branch`,
`test_a_red_verify_in_the_clone_leaves_it_clean` et `test_a_version_installed_by_the_other_pc_only_advances_the_clone`
passent en `--auto` (`GAME = UpdateOptions(auto=True, …)`) et attendent une écriture. Le garde-fou demandé le
2026-10-06 retient désormais la première écriture de `--auto` en attente : le verdict devient `attente`.

**Preuve.** `forever/update.py`, `first_write_guard` (vrai sans `first_write_approved_at` dans
`<cache>/update/state.json`) ; échec observé : `['attente'] == ['écrire']` (`test_update_publish.py:109`).

**Diff proposé** (fixture `origin` seulement, aucune assertion changée : ces tests portent sur le chemin git) :

```diff
     config.write_text(json.dumps({"repo_url": str(bare)}), encoding="utf-8")
+    # garde-fou de la première écriture levé (décision 184) : ces tests portent sur le chemin git
+    (config.parent / "state.json").write_text(json.dumps({"first_write_approved_at": "2026-10-06T00:00:00Z"}), encoding="utf-8")
     return montage, bare
```

## 4. `tests/unit/test_monsters_correction.py` (méthode Theil-Sen pondéré, décision 190)

**Constat.** `test_least_squares_line_on_ratios_above_one` fige la pente, l'ordonnée et le genou des moindres carrés ;
`test_excluded_npc_is_listed_with_its_ratio` affirme que garder Sarilus Foulborne (un seul PNJ, niveau 25, rapport
1,62) relève la pente. Avec Theil-Sen pondéré (décision de l'utilisateur du 2026-10-06), ce point isolé ne bouge plus
la pente : c'est la robustesse demandée.

**Preuve.** Mêmes fixtures (`REAL_LOG`, `WoWCombatLog-092726_150346.anon.txt.gz`, Questie 11.38.0), valeurs par
`repr()` : pente 0.0246379983222087, ordonnée 0.8050680234890781, genou 7.911843079200558 ; avec Sarilus :
0.0246379983222087 (identique). Niveau 16 inchangé (427, probable).

**Diff proposé** (constantes, une assertion, docstring ; noms des tests inchangés) :

```diff
-sur les médianes supérieures à 1 ; rapport d'un niveau non mesuré = max(1, droite). Certitude `probable` entre le
+sur les médianes supérieures à 1 (Theil-Sen pondéré depuis la décision 190) ; rapport d'un niveau non mesuré = max(1, droite). Certitude `probable` entre le
-SLOPE, INTERCEPT, KNEE = 0.02479762330307588, 0.8029465816401004, 7.946463899040569
+SLOPE, INTERCEPT, KNEE = 0.0246379983222087, 0.8050680234890781, 7.911843079200558
-    assert kept is not None and kept["fit"]["slope"] > SLOPE and kept["excluded"] == []
+    assert kept is not None and kept["fit"]["slope"] == pytest.approx(SLOPE, rel=1e-12) and kept["excluded"] == []
```
