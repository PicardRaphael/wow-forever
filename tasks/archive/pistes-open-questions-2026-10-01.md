# Pistes pour OPEN_QUESTIONS (2026-10-01)

Origine : réponses de ChatGPT à docs/OPEN_QUESTIONS.md, relues et triées par claude.ai.
Règle : ChatGPT n'est jamais une source. Chaque piste doit être vérifiée sur une source primaire
(client décodé, notes officielles de Blizzard, mesure en jeu, documentation d'API) avant de changer
une question, une valeur ou une certitude. On cite la source primaire, jamais ChatGPT.

## A. Notes officielles de Blizzard (vérifier avec forever notes, lancé à la main, puis appliquer)

- Tame Beast ne fonctionne plus sur une bête de niveau supérieur à celui du Chasseur (notes de
  développement du 24 septembre). Déjà recoupé par claude.ai sur plusieurs reprises du message
  officiel. Conséquence : la marge d'apprivoisement de CH0 vaut 0 niveau, pas +2 ; corriger
  pet_rules.json, tameable_now, le guide et la question ouverte.
- Même note : bonus de puissance d'attaque de Furious Howl réduit de 40 % ; Sonic Blast désormais
  disponible pour les chauves-souris. Vérifier que pets.json (client 70124) le reflète.
- Hot Streak passé de 15 à 20 s (24 septembre) : concorde avec T06b (20 s lus dans le client).
- Ignite : suppression du double comptage des modificateurs de dégâts en pourcentage. Concorde avec
  le choix de T05. Ne tranche pas le roulement des tics (A18 reste ouvert).
- Arcane Missiles : changement de ligne de vue annoncé, à vérifier.
- Plafond de niveau relevé à 30 avec un nouveau build annoncé le 1er octobre : à installer quand
  il est publié (paramètre de forever install, avec la note comme source).
- Legacy : 65 défis, déblocage vers le niveau 25, rangs PvP 3/7/10/13/14, réputations de champs de
  bataille, Field of Honor, système de perks. Pour LG1 et PV2, à vérifier sur la source officielle.
- Règles de royaume : Normal, PvP, RP, puis Hardcore ; champs de bataille mixtes hors Hardcore.
  Nouveau champ de bataille Darkspear Islands, 15 contre 15, contrôle de points et captures de
  drapeau. Pour PV2, à vérifier.
- Date de lancement et ouverture éventuelle de l'API (EC1) : à vérifier sur la source officielle.

## B. Valeurs dites « du client » par des sites tiers (ForeverDB, ForeverDiff, WoW Forever Talents…)

À vérifier sur notre propre décodage de 1.60.1.70124, jamais importées depuis ces sites.

- Pyroblast rang 1 : 125 mana, niveau 20. Ice Lance rang 1 : 45 mana, niveau 20. Blast Wave rang 1 :
  215 mana, niveau 30.
- Arcane Blast : 15 % de la mana de base, +175 % de coût par cumul, 4 cumuls, 8 s. Additif ou composé :
  à mesurer.
- Impact 3/7/10 % ; Improved Scorch 33/67/100 % ; Improved Blizzard 15/25/40 %, 1,5 s.
- Winter's Chill : +2 % de critique par cumul, pour Frostbolt et Ice Lance seulement.
- Frostfire Bolt : Feu et Givre, utilise la plus basse des deux résistances, compte comme les deux
  écoles (texte du sort).
- Blink : libère des étourdissements et des immobilisations (texte du sort).
- Ice Barrier rang 1 : niveau 40 (classes.json) contre 20 (spells.json) : le client l'emporte.
- Improved Seal of Fury : 60 mana, +15 % par niveau de l'attaquant au-dessus du Paladin, plafond +45 %.
- Ice Lance : aucun coefficient de puissance des sorts dans le client (E4 reste à mesurer).

## C. Raisonnement à rejeter

- Pénalité des sorts de bas niveau (E2). ChatGPT conclut « pas de pénalité » parce que le client
  donne 0,407 à Frostbolt rang 1, contre 0,163 en Classic. C'est faux : 0,163 est la valeur de
  Classic après la pénalité appliquée par le serveur ; le coefficient brut de Classic est lui aussi
  d'environ 0,407. Le client ne dit donc rien de la pénalité serveur : E2 reste ouvert.
  Le test proposé est bon : Frostbolt rang 1 avec deux valeurs de puissance des sorts éloignées ;
  la pente des dégâts dit si une réduction est réappliquée.

## D. API exposées sur Forever 1.60.1 (d'après warcraft.wiki.gg, à confirmer en jeu par /dump)

- C_ClassTalents.GetActiveConfigID et C_Traits.GetNodeInfo.
- GetSpellBonusDamage et GetSpellCritChance (valeurs secrètes possibles dans certains contextes).
- UnitQuestTrivialLevelRange("player") : remplacerait l'émulation de GetQuestGreenRange (I7).
- UnitClass et UnitClassFromGUID : classe d'une cible en champ de bataille.
- UnitHealthMax : marqué SecretWhenUnitHealthMaxRestricted pour les PNJ.
- Addons : Auctionator prend en charge Forever depuis ses versions 337 à 339 ; MobInfo2 a une
  version Forever 1.60.1 (relevé de PV absolus non prouvé).
- SavedVariables : bogue corrigé depuis 70009 selon des joueurs, à confirmer avec ForeverLogger.
- TACT de la bêta : wow_classic_beta (journaux de plantage) ; produit de lancement inconnu.

## E. Réorganisation proposée

Sortir de OPEN_QUESTIONS les choix du modèle, qui ne sont pas des inconnues du jeu : poids PvP (I5),
or par heure du respec, 6 minutes de trajet, départage de l'optimiseur, modeled_talents, découpe I8,
contrôle des chiffres, hook Stop, longueur des réponses (D3), stratégie des _seed_*.json.
Les ranger dans docs/modeling-decisions.md, pour ne plus mélanger « Blizzard fait X » et
« notre moteur choisit X ».

## F. Tests en jeu les plus rentables (à mettre en tête du protocole de ADDON.md)

1. E2, pénalité des sorts de bas niveau : Frostbolt rang 1 avec deux puissances des sorts éloignées.
2. E4, coefficient d'Ice Lance.
3. A18, Ignite : roulement et compteur des tics (deux critiques rapprochés, aura 412538).
4. B7, Mage Armor + Arcane Meditation : régénération pendant la règle des 5 s, nu / l'un / l'autre / les deux.
5. Critique des sorts ×1,5 et DoT qui critiquent : 100 critiques de Frostbolt ou plus.
Pour les ratios encore estimés : GetSpellCritChance avec l'Intelligence connue (critique de base),
UnitPowerMax avec deux valeurs d'Intelligence (mana par Intelligence), UnitHealthMax avec deux
valeurs d'Endurance (PV par Endurance).

## G. Restent ouverts (aucune preuve Forever) : garder, avec le test proposé

Regroupement des événements par le serveur ; recul de 0,5 s ; table de ratés A3 (écarts 0 à +3) ;
boss au niveau du joueur +3 ; progression d'un rang avec le niveau du joueur ; interactions de
Frostfire Bolt (Ice Shards, Fire Vulnerability) ; Arcane Blast (coût à n cumuls, Clearcasting,
Arcane Power) ; Arcane Power au début ou à la fin de l'incantation ; recul d'Arcane Missiles ;
arrondi ou troncature (E7) ; coefficient de Blizzard ; boss gelables ; PV des PNJ (ne pas extrapoler
Questie) ; armure des monstres ; régénération par l'Esprit ; rendements décroissants PvP ; recharge
partagée entre Will of the Forsaken et le bijou PvP ; rendement décroissant sur une application
pendant l'immunité ; coûts d'entraînement à 0 ; Core Hound apprivoisable ; bogue Skyborne (signalé
par des joueurs, non reconnu par Blizzard).
