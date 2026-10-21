# Mage contre Chaman au niveau 60, dans des conditions identiques (2026-10-21)

Calcul de wowsims/forever, commit 10b0e65f2494, compilé tel quel (décisions 293 et 294),
`forever_simulate(action="compare")`. Certitude `suppose` (simulateur tiers), niveau 60 seulement.

## Conditions, les mêmes pour tous
- **Rencontre** : cible de raid du dépôt (« Raid Target », niveau 63), 180 s ± 5 s, une seule cible.
- **Graine et volume** : même graine, 10 000 combats par cas.
- **Buffs** : réunion de ceux des préréglages comparés, donnés à tous.
  - Raid : Arcane Brilliance, Battle Shout, Flametongue Totem, Gift of the Wild, Grace of Air Totem, Leader of the
    Pack, Moonkin Aura, Prayer of Fortitude, Prayer of Spirit.
  - Groupe : Mana Spring Totem, Mana Tide Totem.
  - Individuels : Greater Blessing of Kings, Might, Salvation et Wisdom ; Innervate.
- **Affaiblissements** : Curse of Elements, Curse of Recklessness, Expose Armor, Faerie Fire, Gift of Arthas, Hunter's
  Mark, Judgement of Wisdom, Sunder Armor.
- **Consommables**, deux variantes :
  - « aucun » : personne n'en a, conditions strictement identiques ;
  - « propres » : chacun ceux de son préréglage, car un flacon de lanceur de sorts ne sert à rien à un Chaman
    Amélioration.
- **Ce qui reste propre à chacun** : l'équipement et les talents du préréglage de chaque spécialisation. Il n'existe
  pas d'équipement commun à un lanceur de sorts et à une classe de mêlée.

## Résultats (dégâts par seconde, intervalle à 95 %, écart au meilleur)

| Spécialisation (préréglage) | Race | Sans consommables | Consommables propres |
| --- | --- | --- | --- |
| Mage Feu (`Fire`) | Humain | 641,1 ±0,7 | **823,5** ±1,0 |
| Mage Feu | High Order Skyborne | 639,4 ±0,7 (−1,8) | 822,0 ±1,0 (−1,5) |
| Mage Feu | Gnome | 636,7 ±0,7 (−4,4) | 817,6 ±1,0 (−5,9) |
| Mage Givre-feu (`FFB`) | High Order Skyborne | 589,9 ±0,8 (−51,3) | 808,4 ±1,2 (−15,1) |
| Mage Givre-feu | Humain | 586,0 ±0,8 (−55,1) | 813,0 ±1,1 (−10,5) |
| Mage Givre-feu | Gnome | 577,9 ±0,8 (−63,2) | 803,0 ±1,1 (−20,5) |
| Mage Arcanes et Feu (`Arcane Fire`) | Humain | 591,4 ±0,7 (−49,7) | 761,6 ±0,9 (−61,9) |
| Mage Arcanes et Feu | Gnome | 590,8 ±0,7 (−50,3) | 760,1 ±0,9 (−63,4) |
| Mage Arcanes et Feu | High Order Skyborne | 584,6 ±0,7 (−56,5) | 750,8 ±0,9 (−72,7) |
| Mage Arcanes et Givre (`Arcane Frost`) | Humain | 553,8 ±0,6 (−87,3) | 702,2 ±0,7 (−121,3) |
| Mage Arcanes et Givre | Gnome | 553,6 ±0,6 (−87,5) | 701,5 ±0,7 (−122,0) |
| Mage Arcanes et Givre | High Order Skyborne | 552,8 ±0,6 (−88,3) | 700,5 ±0,7 (−123,0) |
| Chaman Amélioration (`testing`) | Nain | 564,6 ±0,8 (−76,6) | 665,4 ±0,8 (−158,0) |
| Chaman Élémentaire (`testing`) | Nain | 420,5 ±0,4 (−220,6) | 595,3 ±0,5 (−228,2) |

Le dépôt de wowsims n'a pas de préréglage de Givre pur pour le Mage : la spécialisation Givre n'y est représentée que
par le Givre-feu (`FFB`, talents Feu et Givre). Le Nain est la seule race de l'Alliance qui peut être Chaman (client).

## Ce que le simulateur ne chiffre pas
- **Soin du Chaman Restauration** : aucun préréglage de soigneur n'a de rotation dans le dépôt : « non calculé ».
- **Utilité en groupe** : les totems du Chaman sont ici donnés à tous ; leur valeur pour le groupe, Chain Heal,
  Purge et Earth Shock, ainsi que l'invocation d'eau, Polymorph et Arcane Intellect du Mage, ne sont pas chiffrés.
- **PvP**, **leveling** sous le 60, survie et repos : hors de wowsims.
- **Plusieurs cibles** : une seule cible ici.

## Conclusion
Au niveau 60, en dégâts mono-cible, le Mage Feu est devant les deux spécialisations de dégâts du Chaman, dans les deux
variantes. La race du Mage pèse peu : moins de 6 dégâts par seconde entre Humain, High Order Skyborne et Gnome en Feu.
Ce calcul ne départage ni le soin, ni l'utilité, ni le PvP, ni le leveling.
