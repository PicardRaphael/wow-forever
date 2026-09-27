# Mécaniques modélisées (build 1.60.1.70009)

Statuts : FC client Forever · FS simulateur Forever open source · PC règle Classic supposée inchangée · EST estimation.
Toutes sont implémentées dans `scripts/fm.py` ou `scripts/sim_leveling.py` et vérifiées par `tests/run_all.py`.

## Toucher
- Raté des sorts selon l'écart de niveau : 4 % (même niveau), 5 % (+1), 6 % (+2), 17 % (+3), 28 % (+4). Plancher 1 % (plafond de toucher 99 %). PC
- Elemental Precision : +1 %/rang Givre et Feu (5 rangs). FC. Arcane Focus : +1 %/rang Arcanes. FC. Toucher d'équipement : additif. FC (stat unifiée Forever)
- Contre un monstre de ton niveau, seuls 3 points de toucher servent ; contre un boss +3, 16.
- Sorts « binaires » (avec effet non-dégât : Éclair de givre, Nova, Cône) : pas de résistance partielle. PC

## Critique
- Critique de base du Mage : 0,2 % + Int / IntParCrit(niveau). IntParCrit(60) = 59,5 (Mage) ; Forever : 54-60 pour les lanceurs. FC (Warcraft Tavern) / PC. Entre 1 et 60 : interpolation linéaire depuis 6. EST → remplacé par la fiche perso.
- Épée (Humain) +2 % ; critique d'équipement additif ; notation de critique → % : inconnue (à lire dans le moteur wowsims Forever). FC / inconnu
- Talents : Arcane Instability +1 %/rang (tout), Critical Mass +2 %/rang (Feu), Arcane Impact +2 %/rang (Arcanes), Incineration +2 %/rang (Trait de feu, Javelot de glace, Déflagration, Brûlure), Shatter +17 %/rang contre cible gelée (Forever), Winter's Chill +2 % par cumul (Éclair et Javelot uniquement en Forever ; 20 %/rang de chance, cumuls = rang). FC
- Multiplicateur : 150 % ; Ice Shards +20 %/rang du bonus (200 % à 5/5) ; Arcane Mind +20 %/rang du bonus Arcanes. FC
- Les DoT critiquent (règle Forever) : chaque tick de la Boule de feu, de Pyroblast, etc. FS/FC
- Ignite : 8 %/rang du coup critique en DoT sur 4 s. FC. Master of Elements : les crits Feu et Givre rendent 10 %/rang du coût de base. FC
- Critiques des monstres sur toi : 5 %, ×2. PC

## Dégâts
- Dégâts de base : fourchette du rang (le client tire une variance de 7,5 à 12 % autour du centre). FC
- Coefficient : incantation/3,5 (bornée 1,5..3,5) ; ×0,95 si ralentissement ; canalisé : durée/3,5 ; zone : valeurs Classic ; Javelot de glace 0,143 (EST) ; Éclair de givre de givre-feu 0,814. PC/EST
- Pénalité des sorts appris avant 20 : ×(1 - 0,0375 × (20 - niveau du sort)). PC
- Piercing Ice +2 %/rang Givre, Fire Power +2 %/rang Feu, Arcane Instability +1 %/rang tout, Arcane Power +30 % (15 s). FC
- Javelot de glace ×4 contre cible gelée (+300 %). FC
- Résistance de niveau (cibles plus hautes) : moyenne ≈ 0,75 × 8 × écart / (5 × niveau). PC — le moteur de raid utilise 3,75 % contre +3 (à harmoniser)

## Temps
- Temps de recharge global 1,5 s (plancher des incantations). PC
- Improved Frostbolt -0,1 s/rang ; Improved Fireball -0,1 s/rang (Boule de feu et Givre-feu). FC. L'Éclair rang 2 (1,8 s) est plafonné à 1,5 s dès 3 points : les points 4 et 5 ne servent qu'à partir du rang 3 (niveau 14).
- Hâte : 10 points de notation pour 1 % (constantes client via wowsims/forever). FS
- Recul d'incantation : +0,5 s par coup reçu pendant une incantation, sans limite (Classic). PC — à confirmer. Burning Soul : 23 %/rang de chance de ne pas perdre de temps (sorts de Feu). FC. Ice Barrier : aucun recul tant que le bouclier tient. FC
- Projectiles : le Mage enchaîne pendant le vol ; impact différé. Vitesses EST (Éclair 28 m/s, Boule 24 m/s).

## Contrôle et gel
- Éclair de givre : ralentit 40 % (durée selon le rang, 5 à 9 s) ; Permafrost +11 %/rang de durée et +3 %/rang de ralentissement. FC
- Frostbite : 5 %/rang de chance de geler 5 s sur un effet de Chill (non cassé par les dégâts : EST). FC (chance)
- Nova de givre : gel 8 s, cassé par les dégâts (probabilité : paramètre, 100 % par défaut = prudent). PC/EST. Improved Frost Nova -2 s/rang de recharge. FC
- Fingers of Frost : 15 % de chance par effet de Chill ; le prochain sort (2 au rang 2) agit comme sur cible gelée. FC

## Mana et repos
- Mana = base + Int (20 premiers points ×1, puis ×15) ; base Mage 1213 au niveau 60. PC. Gnome +5 %. FC
- Régénération d'Esprit : (13 + Esprit/4) par 2 s hors règle des 5 s. PC. Pendant l'incantation : Arcane Meditation 17 %/rang (Forever), Armure de mage 50 % (Forever). FC
- Frost Channeling -5 %/rang (Givre) ; Arcane Concentration 2 %/rang de Clearcasting ; Arcane Blast 15 % du mana de base (+175 % par cumul) ; Transfert 35 % du mana de base. FC
- Eau et nourriture invoquées : valeurs Classic par rang. PC/EST. On mange et boit en même temps : repos = max(temps pour le mana, temps pour la vie).

## Monstres (EST, le client ne les contient pas)
- PV par niveau : ancres Classic (198 au niveau 10, 484 au 20, 938 au 30, 1550 au 40, 2300 au 50, 3400 au 60), calibrées sur la cible Blizzard de 10 à 15 s par monstre en solo.
- Coup : 0,8 × niveau + 0,02 × niveau² avant armure, toutes les 2 s (+25 % d'intervalle sous Armure de givre), 10 % d'évitement, crit 5 % ×2. Course 7 m/s. Armure : A / (A + 400 + 85 × niveau).
- XP : 45 + 5 × niveau (même niveau), modificateurs d'écart Classic. PC

## Non modélisé (dire si la question en dépend)
- Fuite des humanoïdes à bas PV, groupes de plusieurs monstres (le leveling en zone du Mage), résistances des joueurs en PvP, bijoux et effets d'équipement Forever (environnements, types de créatures), Legacy (bonus de leveling), buffs de groupe.
