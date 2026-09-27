# Sources et mise à jour

## Client Forever (vérité)
- Liste des builds : https://wago.tools/api/builds (produit `wow_classic_beta`, versions `1.60.x`, liste non triée : trier par `created_at`). Premier build bêta : 1.60.1.69893.
- Tables : `https://wago.tools/db2/<Table>/csv?build=<build>`. Talents : TraitTree, TraitNode, TraitNodeEntry, TraitNodeXTraitNodeEntry, TraitDefinition, TraitDefinitionEffectPoints, TraitEdge, CurvePoint, SpellName, Spell, SpellEffect. Ignorer Talent et TalentTab (reliquats Classic).
- Géométrie des arbres : un TraitTree par classe, les 3 onglets côte à côte (PosX 1020 / 5020 / 9080), rangées à PosY 2130 + 600 par rangée, colonnes espacées de 600 ; quelques positions ont un zéro en trop ; si deux nœuds partagent un sort, le plus récent est le bon.
- Sorts : SpellEffect (points de base, RealPointsPerLevel, variance 7,5-12 %), SpellLevels, SpellCastTimes, SpellPower (coût).
- Le client ne contient pas : PV des monstres, textes et objectifs de quêtes, positions des PNJ, taux de butin, listes d'entraîneurs.

## Données dérivées (vérifiées contre le client)
- Arbres complets au format wowsims : https://raw.githubusercontent.com/gunba/wow-forever-sim/master/ui/core/talents/trees/mage.json (MIT)
- Rangs confirmés : https://raw.githubusercontent.com/ElliotWood/Forever/master/assets/confirmed_talents.json (MIT)
- Pages lisibles : ForeverChanges (talents, sorts, raciaux, build indiqué), WoW Forever Talents (sorts par rang), Wowhead Forever.

## Simulateurs de référence (raid 60)
- ElliotWood/Forever : fork de wowsims/classic converti à Forever (MIT, garder le lien vers wowsims/classic). `SimOptions.ruleset` choisit les règles ; `RulesetClassic` est la valeur par défaut sur le fil : toujours passer la règle Forever.
- gunba/wow-forever-sim : matrice de 23 builds et 147 combinaisons race/build, requêtes et résultats bruts réutilisables comme modèles.
- sage3648/mythicsim-forever-engine : fork utilisé par MythicSim (classement public).
- wowsims/forever : dépôt officiel (tables de sorts générées depuis le client ; fork officiel annoncé après la bêta).
- Lancer : cloner, `make wowsimclassic` ou le binaire CLI du dépôt, puis passer une requête JSON (partir d'une requête brute de gunba). Vérifier la syntaxe exacte dans le README du dépôt cloné.

## Procédure à chaque nouveau build
1. `python scripts/update_data.py check`
2. `python scripts/update_data.py pull` (talents reconstruits, le reste hérité et marqué)
3. Revérifier `spells.json` contre ForeverChanges / WoW Forever Talents ou les tables SpellEffect ; mettre à jour `data/overrides.json` si une valeur lue dans le client diffère des arbres open source.
4. `python tests/run_all.py` ; ajuster les tests de valeurs si le client a changé.
