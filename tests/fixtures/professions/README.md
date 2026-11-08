# Métiers rentables (fixtures d'AMI7a)

Valeurs inventées (pas des relevés), au format des fichiers lus en local :

- `AddOns/SkillUpForever/Data/` : extraits au format de SkillUp Forever (`Thresholds.lua`, `Recipes.lua` avec
  `ns.RecipeData`, `ns.ItemSellPrices` et `ns.ProfessionSkillLines`, `Vendor.lua` avec `ns.VendorPrices`). Recettes
  920001 à 920008 (Tailoring, ligne 197) et 930001 (Cooking, ligne 185) ; objets 1001 à 1009, ceux de
  `../addon/auctionator_source.json` pour 1001 à 1004 (royaume « Royaume »).
- `SavedVariables/ForeverCompanion.lua` : `ForeverCompanionDB.global.inventory` au format de Forever Companion
  (royaume, personnage, `bags`, `bank`, `mail`, `equip`) ; un personnage d'un royaume de la bêta à ignorer.
