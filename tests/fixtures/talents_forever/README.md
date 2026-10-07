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
- `mage_builds.json` : trois builds du Mage (`build_report`, préréglage `rapide`, graine 12345, sans sensibilité) sur
  1.60.1.70245 : points, ordre de prise, code attendu (relevé du plan `tasks/FA1-plan.md`).
- Non recopié : `Core.lua`, `UI.lua`, `Game.lua` (aucune licence, décisions 172 et 196), les textes, icônes,
  descriptions et tables `legacy`, `learn`, `coef`, `racials`, `renames`, `orderV1` à `orderV5` de `Data.lua`.
