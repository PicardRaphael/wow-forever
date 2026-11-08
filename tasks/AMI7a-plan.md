# AMI7a — Métiers rentables et hôtel des ventes

Première partie d'AMI7 (`docs/ROADMAP.md`, section AMI) : pour un métier et un rang (ou les métiers du profil), les
recettes faisables classées par profit à l'hôtel des ventes, et les objets de mes sacs et de ma banque à vendre. Tout
est lu en local dans mes addons (décision 272) ; aucun accès réseau, aucun chiffre de jeu dans le dépôt.

## Décision 288

- **Qui maintient déjà ça mieux que nous ?** SkillUp Forever : il calcule en jeu le coût d'une recette avec les prix
  d'Auctionator (`Integrations/Prices.lua`, par l'API de l'addon), sinon ses prix de marchand ; Auctionator relève les
  prix. Nous ne faisons que le classement hors du jeu par profit (vente du produit moins coût des réactifs) et la liste
  des objets à vendre, à partir de leurs fichiers ; on ne refait ni leur interface ni leurs données.
- **Que se passe-t-il au prochain patch ?** Rien à reprendre chez nous : réactifs, produits et prix de marchand sont
  régénérés par SkillUp depuis le client du build nommé dans l'en-tête (`Data/Recipes.lua`, `Data/Vendor.lua`), relus
  tels quels ; la fraîcheur se juge par ce build contre la version installée (comme `kind="profession"`). Les prix
  sont ceux de mes relevés d'Auctionator, datés. Rien dans `forever/data/`, aucun test de valeurs de jeu.

## Sources locales (lecture seule)

1. SkillUp Forever, `Data/Recipes.lua` : `ns.RecipeData` (métier, réactifs `{itemID, quantity}`, produit
   `{itemID, quantity}` en rendement moyen, `false` sans objet produit) et `ns.ItemSellPrices` (prix de vente au
   marchand) ; `Data/Thresholds.lua` (seuils orange, jaune, vert, gris ; nom de la recette) ; `Data/Vendor.lua`
   `ns.VendorPrices` (prix d'achat au marchand des composants, nom en commentaire). Données tirées par l'addon du
   client de Forever (wago.tools, `wow_classic_beta`) ; les fichiers tirés de CMaNGOS/Classic (`Trainer.lua`,
   `Sources.lua`) ne sont pas lus (décision 294).
2. Auctionator, `WTF/Account/*/SavedVariables/Auctionator.lua` : dernier minimum vu par objet et son jour
   (`forever/pipeline/auctionator.py`). Royaumes de la bêta ignorés (décision 300). Un seul royaume restant : pris ;
   plusieurs : `--realm` exigé.
3. Forever Companion, `WTF/Account/*/SavedVariables/ForeverCompanion.lua` : `global.inventory[royaume][perso]` avec
   `bags`, `bank`, `mail` (objet -> nombre) ; `equip` ignoré. Nouveau : jusqu'ici seul le dossier de l'addon était lu ;
   même règle que pour Auctionator (mes propres SavedVariables). Ses noms de royaume diffèrent de ceux d'Auctionator
   (« CAMWOW EU4 Realm 2 PvP » contre « PvP ») : personnages du royaume égal ou finissant par le nom du royaume des
   prix ; sinon tous, avec une note.
4. Noms d'objets : `ItemSparse` du cache de `forever fetch` si présent, sinon commentaire de `Vendor.lua`, sinon rien.

## Règles du calcul

- Faisable : seuil orange (rang requis) ≤ rang ; couleur donnée (orange, jaune, vert, gris). Recette apprise ou non :
  inconnu hors du jeu (dit).
- Coût d'un réactif : le moins cher entre prix de marchand (SkillUp) et dernier minimum d'Auctionator, source nommée.
- Vente : dernier minimum d'Auctionator du produit × quantité moyenne produite ; prix au marchand donné à côté.
- Profit = vente − coût, en pièces de cuivre (aucune conversion écrite ici). Taxe et dépôt de l'hôtel des ventes :
  absents des données et des sources locales, donc non déduits (profit brut, dit).
- Prix manquant (réactif ou produit) ou réactifs absents de SkillUp : profit inconnu, objets nommés ; ces recettes
  viennent après les recettes chiffrées. Recettes sans objet produit (enchantements) écartées et comptées.
- Certitude `suppose` (addons), dates des prix rendues.

## Livrables

- `forever/pipeline/skillup.py` : `read_crafting` (réactifs, produits, prix de marchand).
- `forever/professions.py` : `profession_profit` (payload avec provenance).
- CLI `forever professions profit [--profession NOM] [--skill N] [--realm R] [--character P] [--limit N] [--json]` ;
  MCP `forever_lookup(kind="profession_profit", name, level, realm, character, limit)`.
- Tests d'abord (`tests/unit/test_profession_profit.py`), fixtures `tests/fixtures/professions/` (inventées, LF) et
  `tests/fixtures/addon/Auctionator.lua` existant.

## Essai en jeu (décision 273)

1. En jeu, ouvrir l'hôtel des ventes avec Auctionator (scan), ouvrir les sacs et la banque, puis `/reload`.
2. `uv run forever professions profit --json` : métiers du profil, royaume des prix, recettes classées, objets à
   vendre ; comparer deux ou trois coûts avec le coût affiché par `/skillup`.
