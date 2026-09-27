# T03 — Inventaire des tables du client 1.60.1.70009

Collecte du 2026-09-27 (`forever fetch`, 38 tables enUS + `SpellName` et `TraitDefinition` en frFR). `TraitTreeLoadout` et `TraitTreeLoadoutEntry` : HTTP 400 sur ce build (inutiles). Locale : `&locale=frFR` fonctionne (116 → « Eclair de givre »). `TraitDefinition` frFR : même taille qu'en enUS, `OverrideName_lang` vide pour le Mage ; les noms français viennent de `SpellName` seul.

## Talents
- Arbre : `SkillLineXTraitTree` associe la ligne 237 (Arcane) au TraitTree 1112 ; 54 nœuds (18 Arcane, 17 Fire, 19 Frost), un seul `TraitNodeEntry` et un seul sort par nœud, `Type` et `Flags` à 0.
- Géométrie : onglets PosX 1020 / 5020 / 9080, PosY 2130 + 600 × (palier − 1), colonnes tous les 600. Aucune position hors grille sur ce build (pas de zéro en trop), aucun sort partagé par deux nœuds (Wake of Fire 11078, Flame Throwing 11100 ; l'arbre wowsims leur donnait les mêmes sorts).
- Prérequis : 6 `TraitEdge` (gauche = prérequis, droite = dépendant), identiques à `talents.json`.
- Nom : `TraitDefinition.OverrideName_lang` sinon `SpellName` ; clé = nom anglais en camelCase (apostrophes retirées) : les 54 clés et l'ordre de `talents.json` sont reproduits.
- Valeurs par rang : `TraitDefinitionEffectPoints` (OperationType 0 partout) → `CurvePoint` (Pos_0 = rang, Pos_1 = points de l'effet) ; les effets sans courbe gardent `EffectBasePointsF`.
- Infobulle : `Spell.Description_lang` du sort du nœud. Motifs rencontrés : `$s1`, `$m1`, `$d`, `$u`, `$n`, `$o2`, `$<id>s1`, `$<id>d`, `$<id>u`, `$/1000;S1`, `$/10;12536s1`, `${$m1/1000}`, `${$s1/-1000}`, `${$m1/2}`, `${$m2/10}.1`, `$lspell:spells;`. Aucun `$<var>` ni `$?s…` dans les infobulles de talent (présents dans celles des sorts : `$<frostdamage>`, variables de `SpellDescriptionVariables`).
- Évaluation : `$s`/`$m` seuls affichent la valeur absolue ; `$s` d'un effet à `Variance` > 0 donne deux valeurs (min, max) ; dans `${…}` les valeurs sont signées ; arrondi au demi supérieur ; `$d` en min si ≥ 60 000 ms, sinon en s ; `$u` = `SpellAuraOptions.CumulativeAura`, `$n` = `ProcCharges`.
- Les rangs de wowsims sont les variables que son texte a templatées : plusieurs constantes y sont écrites en clair (Ignite « 4 sec », Impact « 2 sec »…), d'où des écarts de forme.

## Sorts
- Rangs : `SkillLineAbility` des lignes 6, 8, 237, `AcquireMethod` 0 ou 2 (Fire Blast a 7 doublons à 3, niveau de base 0, recharge 15 s), numéro de rang dans `Spell.NameSubtext_lang` (« Rank N »). 15 sorts, 99 rangs.
- Niveau appris : `SpellLevels.BaseLevel`. Valeurs évaluées au niveau min(MaxLevel, 60) : points = base + RealPointsPerLevel × (niveau − BaseLevel) ; min / max = points × (1 ∓ Variance / 2), arrondis au demi supérieur (Frostbolt r1, r2, r11, Pyroblast r2 vérifiés).
- Dégâts directs : effets `Effect` 2. DoT (sort non canalisé) : aura 3, points par tick × durée / période. Canalisés (`Attributes_1 & 0x44`) : aura 23 → sort déclenché × ticks (Arcane Missiles) ; aura 226 → sort cité par l'infobulle × ticks (Blizzard 1279976, Flamestrike 1279983 pour son DoT) ; incantation = durée.
- Mana : `SpellPower.ManaCost` (type 0) si > 0, sinon null (Arcane Blast : `PowerCostPct` 15). Recharge : max(`RecoveryTime`, `CategoryRecoveryTime`).

## Résultat du prototype (cache et fixtures identiques)
- Talents : 54 reproduits (clé, nom, arbre, palier, colonne, max, prérequis, ordre) ; 5 oracles FC-70009 exacts ; 29 lignes de rang différentes (voir le rapport d'arrêt).
- Sorts : 95 rangs sur 99 identiques ; écarts sur les rangs 1 issus d'un talent (Pyroblast, Ice Lance, Arcane Blast, Blast Wave : référence lue au niveau de base) et le niveau de Blast Wave r1 (30 contre 36) ; mana relevé là où la référence a null : Pyroblast r1 125, Ice Lance r1 45, Blast Wave r1 215.
- `spellIds` : le client n'a qu'un sort par nœud ; wowsims donne des identifiants par rang, souvent TBC/Wrath (Arcane Blast 30451 contre 400574, Arcane Geometry 11100 contre 11247…). Comparés à part, jamais un écart.
