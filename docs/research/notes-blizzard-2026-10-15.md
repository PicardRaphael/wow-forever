# Notes de développement de Blizzard du 15/10/2026 : lecture et recoupement avec le client 1.60.1.70450

Relevé le 2026-10-20, à la demande de l'utilisateur (priorité 2 : comparer avant d'installer quoi que ce soit). Pour
chaque changement de la note : (a) visible dans les tables du client 1.60.1.70450 (vérifié), (b) passé par un
correctif du serveur, ou (c) règle du serveur absente des données lues. Le texte du forum est sous licence
CC BY-NC-SA 3.0 : il est paraphrasé ici, jamais recopié.

## Source
- Sujet officiel « WoW Forever Beta Development Notes – Updated October 15 » (Community Manager), forum de Blizzard :
  <https://us.forums.blizzard.com/en/wow/t/2360696>.
- **Message n° 6** : créé le 2026-10-16T00:15Z, **révision 2** du 2026-10-16T20:50Z :
  <https://us.forums.blizzard.com/en/wow/t/2360696/6> (provenance retenue : « t/2360696/6, révision 2 »).
- Lecture : `uv run forever notes --post 2360696/6`, lancée à la main le 2026-10-20 (décision 148). Les messages
  suivants du sujet ne sont pas servis par le forum (premiers messages seulement) : aucune note d'un build plus récent.

## Version concernée : 1.60.1.70450
Le build 70450 porte les changements de la note : la refonte du Mage et les raciaux sont dans ses tables, absents de
celles de 70374 (le build intermédiaire 70425, nommé par Talents Forever 0.38.9, n'a jamais été installé ici).
- **Correctifs du serveur** : aucun `DBCache.bin` du build 70450 (la bêta s'est terminée avant une connexion). La
  candidate est décodée **sans correctifs**. Mesure : **0 valeur** d'origine `correctif_serveur` de 70374 perdue (les
  valeurs que les correctifs avaient apportées sont déjà dans les tables de 70450) ; seuls manquent les correctifs
  propres à 70450, inconnus : la classe (b) n'est vérifiable pour rien, et l'installation le notera dans sa
  provenance (porte `sans_correctifs` de la décision 207, délai écoulé).
- **Lecture du client** : la lecture de 70450 échoue aujourd'hui sur Winter's Chill (`rank_variables` et
  `target_auras` de `decode_rules.json`) ; avec ces deux règles retirées, elle passe. Une installation simulée refuse
  ensuite **54 écarts**, tous propres au moteur du Mage (section suivante).

## Synthèse
- Vient du client (a) : presque tout, refonte du Mage comprise ; règles du serveur (c) : immobilité des baguettes et
  d'Auto Shot, comportements de Heating Up, vitesse minimale de Plainsrunning, corrections de bugs.
- Touche nos calculs : **le moteur du Mage** (trois talents qui changent de sens, deux sorts nouveaux, deux talents
  déplacés ou remplacés, valeurs d'Ice Lance, de Critical Mass et d'Arcane Blast) et **les raciaux du Mage** (Ruthless
  de l'Humain n'est plus lu ; Savage de l'Orc et Wind Blessed des Skyborne ne l'ont jamais été ; Eureka! du Gnome hors
  modèle). Les fiches PvP et les familiers changent d'office (valeurs recopiées du client).
- Recommandations du Mage : **non rejouables honnêtement** avant de modéliser la refonte (fin de la section Mage).
- Talents Forever 0.38.9 écrit des codes de génération 7 (arbres du build 70425) ; notre lecteur et notre export ne
  connaissent que la génération 6 (que l'addon relit encore par sa table `orderV6`) : à reprendre avec la version 70450,
  sans quoi un build qui prend un talent nouveau ne s'exporte pas.

## Mage : changements et effet sur le moteur
Comparaison : `talents.json`, `spells.json` et `classes.json` installés (1.60.1.70374 r8) contre la candidate
1.60.1.70450 décodée sans correctifs du serveur ; descriptions de `Spell.csv` des deux builds. Une simulation
d'installation (`forever install --new-version` sur une copie des données hors du dépôt) **refuse 54 écarts**, tous du Mage : hors
`confirmed_changes.json`, les règles de fusion n'acceptent aucune valeur changée des fichiers propres au moteur du Mage.

| Changement (paraphrase) | Classe | Preuve (1.60.1.70374 → 1.60.1.70450) | Moteur et registre |
| --- | --- | --- | --- |
| Winter's Chill repensé : ne donne plus de critique ; chaque cumul augmente les dégâts du prochain Cone of Cold sur la cible | (a) | Description de 11180 réécrite (« Cone of Cold » au lieu d'Ice Lance et Frostbolt) ; infobulle du rang 1 [20, 2, 15, 1] → [20, 40, 5] (chance, gain par cumul, cumuls) ; l'aura 308 (critique) du sort 12579 disparaît : **la lecture de 70450 échoue** sur `rank_variables` et `target_auras` | **Entrée calculée et sens changé** : `engine/crit.py`, `sim/encounter.py` lisent la chance et les cumuls comme du critique ; D4 |
| La note donne deux textes pour Winter's Chill (dégâts de Cone of Cold +40 % par cumul, ou +5 % et 7 % de la puissance des sorts, 5 cumuls) | (a) tranche | Les tables de 70450 portent 40 par cumul et 5 cumuls : le premier texte est celui du client ; le second reste non vérifié | D4 |
| Arcane Blast repensé : incantation 1,5 s (au lieu de 2,5) ; chaque lancer donne une part de l'Intelligence en puissance des sorts (au lieu de +dégâts des autres sorts) ; dure 15 s depuis la première application ; dégâts et coefficients baissés d'environ 40 % | (a) | `spells.json` : rangs 1 à 5 min/max baissés (57-66 → 33-39 … 364-424 → 218-254), `cast_s` 2,5 → 1,5 ; talent [50, 58, 10, 175, 4, 8] → [30, 34, 15, 175, 4, 15] ; description de 400573 et 400574 réécrites | **Entrée calculée et sens changé** : `engine/buffs.py` (bonus de dégâts des autres sorts), `engine/derived.py`, `engine/mana.py` (escalade du coût, inchangée : 175 %, 4 cumuls) ; B15, B11 |
| Missile Barrage : passe en première ligne, 2 points ; les impacts d'Arcane Missiles peuvent aussi le déclencher ; Arcane Wrath aussi | (a) | Palier 4 → 1, `max` 1 → 2, rangs [40, 20, 50, 100, 0,5] → [20, 5, 10, 50, 100, 0,5] et [40, 10, 20, 50, 100, 0,5] | **Entrée calculée** : `engine/buffs.py` (procs) ; B14, B15 ; arbre Arcane changé pour tous les builds |
| Arcane Wrath : nouveau talent en or à 16 points (Arcane, palier 4), 3,5 s d'incantation, 6 s de recharge, puissance des sorts en plus égale à une part du mana maximum | (a) | Talent `arcaneWrath` ajouté (rang [108, 132, 5]) ; sort 1280471 ; `classes.json` du Mage : sort ajouté | **Absent du moteur** : nouveau sort de rotation à modéliser |
| Frost Blast : nouveau sort appris au niveau 24, 1,5 s, ralentit, profite des talents de Frostbolt | (a) | `classes.json` du Mage : sort ajouté (1326053, niveau 24, `cast_s` 1,5, durée 9 s) ; absent de `spells.json` (liste fermée des sorts du moteur) | **Absent du moteur** : à ajouter aux sorts du moteur et aux rotations de leveling (rôle du Frostbolt de rang 1) |
| Ice Lance : bonus contre une cible gelée à +200 % (au lieu de +300 %) | (a) | Talent `iceLance` [26, 30, 300] → [26, 30, 200] | **Entrée calculée** (`frozen_mult` de `spells.json`, `engine/cast.py`, `engine/damage.py`) : simple valeur, sans changement de modèle |
| Wake of Fire redevient Improved Fire Blast : recharge de Fire Blast réduite, portée augmentée de 8/15 m ; plus de bonus à la mise à mort | (a) | Talent `wakeOfFire` retiré, `improvedFireBlast` ajouté (rangs [1, 8], [2, 15]) | **Entrée calculée** : `engine/casting.py` lit la réduction de recharge de `wakeOfFire` (B13) ; le bonus à la mise à mort était hors modèle (B19) |
| Critical Mass : jusqu'à 5 points, 10 % de critique au total | (a) | `max` 3 → 5, rangs 4 et 5 ajoutés [8], [10] | **Entrée calculée** (`engine/crit.py`) : valeur, sans changement de modèle ; arbre Feu changé |
| Fire Power repensé : 3 points ; +1/2/3 % de dégâts de Feu par effet de Feu du Mage sur la cible (Ignite, Improved Scorch, Fireball, Pyroblast, Impact), jusqu'à +12 % ; les sorts de deux écoles n'en donnent pas | (a) et (c) | `max` 5 → 3, rangs [2]…[10] → [1, 4], [2, 8], [3, 12] ; la liste des effets qui comptent est une règle du serveur (note) | **Sens changé** : `engine/damage.py` applique un bonus plat ; il faudra compter les effets de Feu présents sur la cible |
| Heating Up : plus consommé si Presence of Mind était actif sur le Pyroblast ; Fire Blast donne toujours une charge de plus (2 sur un critique) | (c) | Talent renommé `hotStreak` → `heatingUp` par le client, valeurs inchangées [20, 25, 3] | **Règle du serveur** à écrire (source : la note) ; `engine/buffs.py`, simulateurs ; A19, B15 |
| Missile Barrage ne réduit plus le coût et la durée d'un second Arcane Missiles | (c) | Aucune ligne changée | Correctif d'un bug reconnu : rien à modéliser (le moteur ne le permettait pas) |
| Frost Channeling réduit bien la menace ; Frostbite et Fingers of Frost se déclenchent depuis Ice Armor et Frost Armor | (c) | Correctifs de bugs reconnus | Menace hors modèle ; Frostbite des armures hors modèle (angle mort à noter) |

**Ce qui bloque l'installation** : la lecture de 70450 échoue sur Winter's Chill (`rank_variables` et `target_auras`
de `decode_rules.json`). Une règle de lecture changée doit encore lire les extraits des versions précédentes
(tests) : elle doit dépendre de la forme de l'infobulle ou du build. La révision 9 de 1.60.1.70374 installera ces
règles avant la nouvelle version (décision 263).

**Recommandations du Mage** : elles **ne peuvent pas être rejouées honnêtement** avec le moteur actuel. Trois talents
changent de sens (Winter's Chill, Arcane Blast, Fire Power) : le moteur lirait les nouvelles valeurs avec l'ancien
sens (par exemple 40 lu comme un critique par cumul). De plus, deux sorts nouveaux (Frost Blast, Arcane Wrath) et
deux talents qui changent (Missile Barrage, Improved Fire Blast) sont absents du modèle. L'aperçu de rejeu de
`forever update` le refuse aussi : un talent ajouté ou retiré rend l'aperçu impossible. Le rejeu demande d'abord de
modéliser la refonte (nouvelle tranche du Mage).

## Raciaux

| Changement (paraphrase) | Classe | Preuve | Effet sur nos calculs |
| --- | --- | --- | --- |
| Tauren, Endurance : bonus de critique en dégâts et soins (au lieu du toucher) | (a) | races.json, sort 20550 : effets aura 54 et 55 (1) → aura 163 et 50 (2) | Tauren non Mage : aucun moteur ; fiche PvP recopiée |
| Tauren, Plainsrunning : +3 % de vitesse montée | (a) | sort 1259918 : effet 3 ajouté, aura 130, 3 | aucun moteur |
| Tauren, Plainsrunning : vitesse minimale à tenir | (c) | aucune trace dans les tables lues | aucun |
| Tauren, Cultivation : recharge 15 min | (a) | SpellCooldowns, sort 1312643 : CategoryRecoveryTime 3600000 → 900000 ms | aucun |
| Tauren, War Stomp : recharge 90 s | (a) | races.json, sort 20549 : cooldown_s 120 → 90 | fiche PvP recopiée (pvp_dr) |
| Nain, Mace Specialization remplacée par Earth Fury | (a) | sort 1259719 : aura 290 (1) → aura 163 et 50 (2), nom changé | Nain non Mage : aucun moteur |
| Nain, Find Treasure : objets de coffre en plus | (c) | aucune trace | aucun |
| Skyborne, Wind Blessed : hâte 3 % | (a) | sort 1259710 : auras 342 et 65, 1 → 3 | **le moteur du Mage ne lit pas cette hâte** (pas de règle dans `racial_values`) : Mage Skyborne sous-estimé, écart passé de 1 à 3 points de hâte |
| Skyborne, Skysight et Read Leyline incantables en mouvement | (a) | SpellInterrupts, sorts 1259686 et 1259705 : InterruptFlags 15 → 14 | aucun |
| Skyborne, Read Leyline : durée minimale 30 s | non retrouvé | le sort déclenché 1270842 n'a pas été comparé ; (b) ou (c) | aucun |
| Skyborne, Walk on Air : recharge 90 s | (a) | races.json, sort 1259416 : cooldown_s 120 → 90 | fiche PvP recopiée |
| Plus de convergences et lignes telluriques | (c) | apparitions du serveur | aucun |
| Humain, Sword Specialization remplacée par Ruthless : 2 % de critique | (a) pour le nom ; effet déjà présent | sort 20597 : aura 290, 2 **inchangée depuis 70374**, seul le nom change ; la restriction d'arme éventuelle (SpellEquippedItems) n'est pas dans les tables lues | **touche le moteur du Mage** : `racial_values.sword_crit` est lu par le nom « Sword Specialization » ; en 70450 il ne correspond plus, `mage_values.sword_crit` disparaît (races.json). Le moteur n'ajoutait ces 2 % qu'avec une épée (`character.py`, `over["sword"]`) ; Ruthless s'applique à toute arme selon la note : Mage humain sous-estimé de 2 points de critique tant que la règle n'est pas réécrite |
| Orc, Axe Specialization remplacée par Savage : 1 % de critique | (a) pour le nom ; effet déjà présent | sort 20574 : aura 290, 1 inchangée, nom changé | **le moteur du Mage l'ignore** (aucune règle) : Mage orc sous-estimé de 1 point de critique |
| Orc, Blood Fury : recharge 3 min | (a) | sort 20572 : cooldown_s 120 → 180 | fiche PvP recopiée |
| Orc, Shatter Curse : dissipe malédictions et fléaux, dégâts magiques subis −5 % | (a) | sort 1299026 : aura 87 −15 → −5 ; effet aura 41 (immunité) → effet 38 (dissipation) | fiche PvP recopiée |
| Mort-vivant, Touch of the Grave / Touch of the Dead : chance 20 et 30 %, recharge interne 25 s | (a) | SpellAuraOptions, sorts 1260189 et 1260201 : ProcChance 5 → 20 et 10 → 30, ProcCategoryRecovery 1000 → 25000 ms | non modélisé (aucun moteur) |
| Touch of the Dead : plus d'effet des bonus d'ombre ni de pénalité de rang | (a) probable | SpellMisc, sort 1260198 : six champs d'attributs passent de 0 à une valeur ; sens des bits non vérifié | aucun |
| Mort-vivant, Will of the Forsaken interdit sous Scatter Shot | (a) probable | SpellMisc, sort 7744 : attributs 3, 5, 8, 13 changés ; sens non vérifié | fiche PvP recopiée |
| Gnome, Eureka! : effet de 8 s sans charges | (a) | races.json, sorts 1259812 à 1259823 : duration_s 15 → 8 ; SpellAuraOptions du sort 1259817 : ProcCharges 3 → ligne absente | **non modélisé par le moteur du Mage** (aucune trace d'Eureka) : angle mort inchangé |
| Gnome, Eureka! : aussi pour Power Word: Shield ; pas en camouflage | (c) | non retrouvé dans les tables lues | aucun |
| Elfe de la nuit, Quickness : cumul avec les autres vitesses | (a) | sort 20582 : aura 31 → 129 | aucun |
| Troll, Regeneration : 20 % | (a) | sort 20555 : auras 88 et 116, 10 → 20 | non lu par le moteur du Mage (repos des simulations : `leveling.rest_hp_regen_fraction`, pas de racial) |

## Buffs de raid

| Changement | Classe | Preuve | Effet |
| --- | --- | --- | --- |
| Moonkin Aura : critique des sorts seulement, à tout le raid | (a) | SpellEffect, sort 24907 : Effect 35 → 65 (aura de zone de groupe → de raid), aura 290 → 57 | aucun moteur ne lit les buffs extérieurs |
| Leader of the Pack : critique de mêlée et à distance seulement, à tout le raid | (a) | sort 24932 : Effect 35 → 65, aura 290 → 52 | aucun |
| Trueshot Aura à tout le raid | (a) | sorts 19506, 20905, 20906, 1299346, 1299348 : Effect 35 → 65 | aucun |
| Totems Grace of Air, Strength of Earth, Windfury, Flametongue à tout le raid | (a) | sorts 8836, 10626, 25360, 8076…, 8515…, 8230… : Effect 35 → 65 | aucun |
| Grace of Air plus exclusif avec Windfury et Flametongue | (a) probable | SpellMisc 8836, 10626, 25360 : Attributes_11 1024 → 0 | aucun |
| Windfury et Flametongue Totem seulement sur les joueurs | (a) probable | SpellMisc 8515, 8230… : Attributes_3 0 → 256 | aucun |
| Battle Shout à tout le raid | (a) | sorts 5242, 6192, 6673, 11549, 11550, 11551, 25289 : ImplicitTarget_0 20 → 56 | aucun |

## Baguettes et Auto Shot

| Changement | Classe | Preuve | Effet |
| --- | --- | --- | --- |
| Baguettes : 0,5 s immobile avant de tirer | (c) | Shoot (5019) : Attributes_4 16777216 → 0 ; Shoot (1316579) : Attributes_6 0 → 2097152 ; le même bit 2097152 apparaît sur Mine! (familier) : lien avec l'immobilité non établi | aucun moteur ne modélise la baguette (aucune trace dans `forever/`) |
| Auto Shot : même règle | (c) | aucun changement d'Auto Shot dans les tables lues | aucun |
| Réglage auto-attaque / Auto Shot | (c) | interface | aucun |

## Chaman

| Changement | Classe | Preuve | Effet |
| --- | --- | --- | --- |
| Totems de raid, Grace of Air non exclusif | (a) | voir Buffs de raid | aucun |
| Chain Lightning : coût réduit d'environ 35 % | (a) | classes.json chainLightning r1 225 → 145, r2 305 → 200, r3 390 → 250… | fiches recopiées |
| Fire Nova : coefficient 0,143, base et coût réduits | (a) | SpellEffect 408423-408428 : EffectBonusCoefficient 0,214 → 0,143, base 50 → 33, 102 → 55… ; coût r1 95 → 65… | fiches recopiées |
| Elemental Mastery, talent de 31 points | (a) | classes.json : talent elementalMastery ajouté (palier 7, prérequis Lava Burst) ; sort 16166 | **builds Élémentaire à revoir** |
| Lava Burst en ligne 5, rang 4 ajouté, sans prérequis | (a) | lavaBurst palier 7 → 5, prérequis retiré ; rangs aux niveaux 40, 50, 60 → 30, 40, 50, 60 | builds à revoir |
| Elemental Fury ← Lightning Overload ← Elemental Alacrity ; Alacrity ligne 2 ; Warding ligne 3 | (a) | prérequis et paliers changés dans classes.json | builds à revoir |
| Call of Thunder retiré | (a) | talent callOfThunder absent | **un build qui le prend devient illégal** |
| Earthbound en ligne 4 | (a) | earthbound palier 5 → 4 | builds à revoir |
| Elemental Reach : recharge de Totemic Projection −10/20 s | (a) | sort 28999 : effet 2 ajouté (aura 107, −20000) | aucun |
| Call of Flame : Flame Shock prolongé de 3/6/9 s | (a) | sort 16038 : effet 2 ajouté (aura 107, 9000) | aucun |
| Colonnes réarrangées ; Improved Fire Nova devient Trial By Fire | (a) | elementalFocus, elementalDevastation, callOfFlame, lightningOverload, elementalWarding : colonnes changées ; improvedFireNova retiré, trialByFire ajouté | **clé de talent changée** : un build qui portait improvedFireNova devient illisible |
| Clearcasting non consommé par Lightning Overload ; Elemental Focus et Fire Nova | (c) | non retrouvé | aucun |
| Stormstrike : 8 % du mana de base | (a) | stormstrike coût 125 → 8 % | fiches recopiées |
| Stormstrike non consommé si le sort ne touche pas ; pas par d'autres | (c) | — | aucun |
| Mana Tide Totem : rang au niveau 38 | (a) | manaTideTotem : 3 → 4 rangs (niveaux 25, 48, 58 → 1, 38, 48, 58 ; le premier niveau lu, 1, est celui d'un sort de talent) | fiches |
| Restorative Totems ; Tidal Focus et Totemic Focus échangés | (a) en partie | tidalFocus palier 2 → 1, totemicFocus 1 → 2 ; Restorative Totems non retrouvé | builds Restauration à revoir |
| Water Shield sur tout critique de sort | (a) | SpellAuraOptions 408510 : ProcTypeMask_0 156328 → 221864 | aucun |
| Totemic Recall au prix voulu ; Grounding Totem ; visuels | (c) | prix d'entraîneur absent des tables lues | aucun |

## Autres classes

| Classe | Changement | Classe | Preuve |
| --- | --- | --- | --- |
| Druide | Moonkin Aura, Leader of the Pack de raid | (a) | voir Buffs de raid |
| Druide | Shred rang 1 au niveau 20 | (a) | classes.json shred r1 22 → 20 ; sort 5221 base 24 → 22 ; sort 3252 aura 22 → 674 |
| Druide | Furor : énergie gardée hors de la forme de félin | (a) description changée | classes.json furor desc |
| Druide | Predatory Instincts remplacé par Natural Instinct | (a), **absent de la note** | talent predatoryInstincts retiré, naturalInstinct ajouté (même place) |
| Druide | Rejuvenation, Omen of Clarity, Faerie Fire, Insect Swarm | (c) | corrections du serveur, non retrouvées |
| Chasseur | Trueshot Aura de raid ; Resourcefulness | (a) | Effect 35 → 65 ; 440529 ProcTypeMask_0 328020 → 272 |
| Chasseur | Multi-Shot sans temps d'incantation | (a), **absent de la note** | classes.json multiShot r1 cast_s 0,5 → 0 |
| Chasseur | Strider Kick désarmé | (a) probable | SpellMisc 1317257 Attributes_3 1024 → 0 |
| Chasseur, familiers | Dismember : −25 % de soins, 6 s, recharge 15 s ; Sonic Blast : −30 %, 20 s, recharge 60 s ; Mine! : 3 s, recharge 90 s | (a) | Dismember 1264758… : base −50 → −25, DurationIndex 1 → 32, recharge 6000 → 15000 ms ; Sonic Blast 1264478… : −60 → −30, DurationIndex 9 → 18, 30000 → 60000 ms ; Mine! 1265054… : DurationIndex 35 → 27, 60000 → 90000 ms ; pets.json changera à l'installation |
| Chasseur | Auto Shot immobile ; pièges de feu et AP ; un piège de feu et un de glace ; Summon Hawk | (c) | non retrouvés |
| Paladin | Salvation et Mass Salvation, Revoke | (a) | sorts blessingOfSalvation et greaterBlessingOfSalvation retirés ; salvation (26), massSalvation (60), revoke (26) ajoutés |
| Paladin | Seal of Fury rang 3 au niveau 26 | (a) | sealOfFury r3 25 → 26 |
| Paladin | Consecration : coefficient 0,042 par impulsion | (a) | SpellEffect 1280345-1280353 : 0,095 → 0,042 |
| Paladin | Righteous Fury : menace 90 % | (a) | sort 25780 : 60 → 90 |
| Paladin | Shield Specialization : 4 % de mana | (a) | sort 1310925 : 6 → 4 |
| Paladin | Reckoning : charges cumulées | (a) | sort 20177 : aura 42 → 4, sort déclenché retiré ; description changée |
| Paladin | Champion of the Light : 10/20/30 % de l'Intelligence | (a) | courbe 110350 : 20, 40, 60 → 10, 20, 30 |
| Paladin | Seal of Righteousness, Judgement of Righteousness/Fury, Infusion of Light, Sanctified Judgement | (c) ou (b) | non retrouvés dans les effets comparés |
| Prêtre | Devouring Plague : recharge 24 s | (a) | 60 → 24 s (6 rangs) |
| Prêtre | Shadow Word: Death : recharge 18 s | (a) | 15 → 18 s ; la note dit « était 12 s », nos données de 70374 disent 15 s (écart de la note) |
| Prêtre | Vampiric Embrace : recharge 30 s | (a) | 60 → 30 s |
| Prêtre | Mental Strength ligne 2, Intelligence 2/4/6/8/10 % | (a) | palier 4 → 2 ; courbe 83132 : 3…15 → 2…10 |
| Prêtre | Improved Power Word: Shield ligne 3 ; Improved Mind Blast ligne 2 | (a) | paliers 2 → 3 et 3 → 2 |
| Prêtre | Improved Fade et Shadow Affinity retirés, Dark Inspiration ajouté | (a) | talents improvedFade et shadowAffinity retirés, darkInspiration ajouté (palier 4, 5 rangs) ; la note nomme le second « Shadow Infinity » |
| Prêtre | Improved Mind Flay ; Devouring Contagion à 2 cibles ; Power in Light ; Silent Resolve ; Divine Aegis ; Shadow Weaving | (a) | descriptions changées ; 1225139 effets réduits à un ; 1309950 effet 2 ajouté |
| Prêtre | Improved Mana Burn colonne 4 → 2 | (a), **absent de la note** | classes.json |
| Voleur | Poisons, Sap, Cold Blood, énergie au changement de spécialisation | (c) | aucun changement dans classes.json |
| Démoniste | Malediction remplacé par Grim Reach (portée +10/20 %) | (a) | malediction (5 rangs) retiré, grimReach (2 rangs) ajouté |
| Démoniste | Shadow Mastery : 2/4/6/8/10 % | (a) | courbes 83215 et 88067 : 1…5 → 2…10 |
| Démoniste | Destructive Reach : portée | (a) | sort 17917 : masques de sorts changés |
| Démoniste | Soul Link sur le familier | (a) probable | soulLink r1 niveau 40 → 0 |
| Démoniste | Portal of Summoning : recharge 1 h, coût 100 % | (a), **absent de la note** | 120 → 3600 s, 12 → 100 % |
| Guerrier | Battle Shout de raid | (a) | ImplicitTarget 20 → 56 |
| Guerrier | Lingering Rage ne coupe plus la régénération | (a) | sort 1323965 : aura 94 → 110 (−100) ; Bloodthrill : description changée |
| Guerrier | Slam, Overpower, Sword Specialization, Improved Berserker Rage | (c) | non retrouvés |

## Ce qui touche nos calculs

- **Moteur du Mage** (`mage_build`, `mage_leveling` ; `races.json` en est une entrée, `forever/engine_inputs.py`) :
  - Humain : `mage_values.sword_crit` disparaît en 70450 (la règle `racial_values.sword_crit` de `decode_rules.json`
    cherche le nom « Sword Specialization ») ; Ruthless (2 %, toute arme selon la note) n'est compté nulle part.
  - Orc (Savage, 1 %) et Skyborne (Wind Blessed, 3 % de hâte) : jamais comptés.
  - Gnome (Eureka!, 8 s) : non modélisé, angle mort inchangé.
  - Ces changements font de `races.json` une entrée modifiée : la veille mettra l'installation en attente.
- **PvP** (`pvp_dr`, recopie de classes.json et races.json) : fiches changées d'office à l'installation (origine
  `client`), sans calcul.
- **Familiers** (pets.json) : Dismember, Sonic Blast, Mine! changent à l'installation.
- **Buffs de raid, baguettes, Auto Shot** : rien dans nos moteurs ; aucun effet.
- **Builds des autres classes** : clés de talent retirées ou renommées (callOfThunder, improvedFireNova →
  trialByFire, improvedFade, shadowAffinity, malediction → grimReach, predatoryInstincts → naturalInstinct) et
  prérequis déplacés (Élémentaire, Ombre) : tout build enregistré qui les porte devient illégal ou illisible.

## Builds des autres classes

- Vérification par `popular_builds` (Talents Forever installé : **0.38.9**), 45 builds populaires sur 9 classes,
  données 70374 contre une copie dont `classes.json` vient de 70450 (vérification faite hors du dépôt) : **les 45 sont
  « illisible » des deux côtés** : l'addon écrit désormais des codes de **génération 7**, notre lecteur ne lit que la
  génération 6 (`forever/talents_forever.py`). Aucune comparaison de légalité n'est donc possible par ce chemin ;
  c'est un écart indépendant de 70450 (l'export vers Talents Forever est sans doute bloqué aussi).
- Faute de builds lisibles, l'effet est déduit des arbres : un build Élémentaire qui prend Call of Thunder ou Improved
  Fire Nova devient illégal ou illisible ; un build Ombre qui prend Improved Fade ou Shadow Affinity aussi ; un build
  Affliction avec Malediction (5 rangs) aussi ; un build Feral avec Predatory Instincts aussi. Les déplacements
  (Lava Burst ligne 7 → 5, Earthbound 5 → 4, Mental Strength 4 → 2…) changent l'ordre légal de prise.
