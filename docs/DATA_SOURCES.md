# Sources de données

## Client Forever (vérité)
- Versions : `https://wago.tools/api/builds` (produit `wow_classic_beta`, versions `1.60.x` ; liste non triée : trier par `created_at`). Produit de lancement : inconnu, prévoir l'alerte `silent`.
- Tables : `https://wago.tools/db2/<Table>/csv?build=<version>`.
    - Talents : TraitTree, TraitNode, TraitNodeEntry, TraitNodeXTraitNodeEntry, TraitDefinition, TraitDefinitionEffectPoints, TraitEdge, CurvePoint. Ignorer Talent et TalentTab (reliquats Classic).
    - Géométrie des arbres : onglets à PosX 1020 / 5020 / 9080, rangées à PosY 2130 + 600 par rangée, colonnes espacées de 600 ; quelques positions ont un zéro en trop ; si deux nœuds partagent un sort, le plus récent est le bon.
    - Sorts : Spell, SpellName, SpellEffect (points de base, RealPointsPerLevel, variance), SpellLevels, SpellCastTimes, SpellPower.
    - Objets : Item*, formules RandPropPoints, ItemDamage*, ItemArmor*.
- Hotfixes : `DBCache.bin` du client, à faire correspondre à la version, la région et la langue.
- Absent du client : PV des monstres, quêtes, positions des PNJ, taux de butin, stocks, listes d'entraîneurs.

## Voie autonome (si wago est indisponible)
- `db2tool` (wowsims) : lecture du client installé, superposition des hotfixes ; mode hors ligne sur fichiers extraits.
- wow.tools.local (TACTSharp, DBCD, WoWDBDefs) ; définitions de tables : WoWDBDefs.

## Données dérivées et simulateurs (MIT, garder le lien vers wowsims/classic)
- Arbres de talents au format wowsims : `gunba/wow-forever-sim` (`ui/core/talents/trees/mage.json`), rangs confirmés : `ElliotWood/Forever` (`assets/confirmed_talents.json`).
- Simulateur de référence : fork `ElliotWood/Forever` ; `SimOptions.ruleset` vaut `RulesetClassic` par défaut : toujours passer la règle Forever. Le dépôt amont `wowsims/forever` a été injoignable (404) : **épingler les commits et copier les arbres utilisés**.
- Base d'objets de référence : `alcaras/forever-ref` (calcul des stats par formules du client).
- Recoupements lisibles : ForeverChanges, WoW Forever Talents, Wowhead Forever.

## Journaux de combat
- Format `WoWCombatLog.txt` version 22 (journalisation avancée) : parseur maison. Warcraft Logs n'a pas de support Forever documenté à ce jour.
