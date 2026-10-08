# Talents Forever (fixture de FA1)

- Origine : addon Talents Forever installé (`<FOREVER_WOW_DIR>/Interface/AddOns/TalentsForeverBook`), `## Version:
  0.37.1`, `Data.lua` d'en-tête `build = "1.60.1.70170"`, `generated = "2026-10-04"`, `codeVersion = "6"` ; builds
  populaires `asOf` 2026-10-04 ; relevé le 2026-10-07 face aux données installées 1.60.1.70245.
- Extraction : `uv run python scripts/extract_talents_forever_fixture.py` (lecture locale par
  `forever/pipeline/lua_table.py`, aucun Lua exécuté) ; ne pas éditer à la main. Le script vérifie, avant d'écrire,
  que le `Data.lua` synthétique de `tests/talents_forever_data.py` rend exactement les champs lus de l'addon.
- `popular.json` : agrégats du bloc `popular` (décision 172) : par classe `builds`, `window`, `asOf`, `full`, `spec`,
  et pour chaque build `rank`, `lead`, `pts`, `code`. Les compteurs `score`, `shared`, `saved`, `opened`,
  `variants`, `seated` ne sont pas gardés.
- `layout.json` : par classe, arbres dans l'ordre de l'addon et, par position de liste, notre clé (`classes.json` de
  1.60.1.70245) ; seuls les écarts de l'addon sont écrits : `node` (nœud numéroté autrement, DON13), `req`
  (prérequis différent du nôtre, DON5), `tf` (position sans correspondance : nom, sort, rangée, colonne, rangs, nœud,
  avec sa raison) ; `forever_only` : nos talents absents de l'addon.
- `mage_builds.json` : builds fixes du Mage pour les tests du format v6 (points, ordre de prise, code attendu, source,
  `verified_in_game`), écrits à la main et jamais recalculés : `leveling-20`, témoin relevé en jeu le 2026-10-08
  (importé dans Talents Forever 0.37.1 et réexporté à l'identique) ; `leveling-20-current`, importé en jeu le même jour
  (préréglage complet) ; `leveling-30` et `dungeon-20`, points et ordre du plan `tasks/FA1-plan.md` figés. Un build
  calculé par l'outil se compare au code que l'outil rend au moment du test, jamais à un code stocké.
- Non recopié : `Core.lua`, `UI.lua`, `Game.lua` (aucune licence, décisions 172 et 196), les textes, icônes,
  descriptions et tables `legacy`, `learn`, `coef`, `racials`, `renames`, `orderV1` à `orderV5` de `Data.lua`.
- `class_witnesses.json` : codes de test du Chasseur (`hunter-40`, par Improved Stings et Intimidation) et du
  Démoniste (`warlock-30`, par Improved Life Tap et Amplify Curse), builds légaux construits le 2026-10-08 sur
  1.60.1.70245 r6 et encodés par `export_build` ; écrits à la main ; importés en jeu le 2026-10-08, affichés comme prévu (`verified_in_game` :
  `import`).
