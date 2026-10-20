# Réputations de WoW Forever : étude de l'existant (CJ1, avant les blocs 6b et 4e)

Relevé le 2026-10-20, lecture seule (décision 264), à la demande de l'utilisateur (idée du chat du 2026-10-15, nuit,
archivée dans `tasks/archive/idees-du-chat-2026-10-15-reputations.md`). Sources : tables du client 1.60.1.70450
(wago.tools, cache de `forever fetch` : `Faction`, `FactionGroup`, `FactionTemplate`, `QuestFactionReward`), addons
installés lus sur le disque (décision 133 : comptes, noms de factions et de sources, jamais leurs tables), note
officielle du 15 octobre (sujet 2360696, message n° 6, révision 2 ; paraphrasée, texte sous CC BY-NC-SA).

## 1. Factions du client 1.60.1.70450

`Faction` compte **253** factions, dont **75** visibles par le joueur (`ReputationIndex` ≥ 0). `FactionGroup` ne porte
que les quatre groupes techniques (Player, Alliance, Horde, Monster) ; le regroupement visible vient de
`ParentFactionID`. Sens des colonnes (`probable`, définitions communautaires de la table) : `ReputationRaceMasksN`
(masque de races sur deux entiers, bit `race - 1`, races 33 et 34 : bits étendus des deux Skyborne) associé à
`ReputationBaseN` (réputation de départ de ces races) ; `ReputationMax` (plafond) ; `ReputationFlags` (affichage,
dont « en guerre » forcé). Une base de -42000 pour un camp : faction fermée à ce camp.

| Groupe | Nombre | Factions (ID) |
| --- | --- | --- |
| En-têtes | 5 | Alliance (469), Horde (67), Alliance Forces (891), Horde Forces (892), Steamwheedle Cartel (169) |
| Villes | 8 | Alliance : Darnassus (69), Gnomeregan Exiles (54), Ironforge (47), Stormwind (72) ; Horde : Darkspear Trolls (530), Orgrimmar (76), Thunder Bluff (81), Undercity (68) |
| Forces JcJ | 8 | Alliance : Silverwing Sentinels (890), Stormpike Guard (730), The League of Arathor (509), **Theramore Expeditionary Force (2799)** ; Horde : Frostwolf Clan (729), The Defilers (510), Warsong Outriders (889), **Darkspear Raiders (2798)** |
| Cartel | 5 | Booty Bay (21), Everlook (577), Gadgetzan (369), Ratchet (470), **Powderfuse (2827)** |
| Neutres et de zone | 34 | voir ci-dessous |
| Métiers | 10 | spécialisations de forge, d'ingénierie et de travail du cuir (plafond 3000) |
| Techniques | 5 | Battleground Neutral (709), PvP Rank Points (2800), Neutral Both But Alliance Can Attack (2801), Legacy Track (2802), DNT Test Reputation (2807) |

Neutres et de zone (34) : Argent Dawn (529), Bloodsail Buccaneers (87), Brood of Nozdormu (910), Caer Darrow (574),
Cenarion Circle (609), Darkmoon Faire (909), Gelkis Clan Centaur (92), Hydraxian Waterlords (749), Magram Clan Centaur
(93), Moro'gai (789), Ravasaur Trainers (630, Horde : base -42000 pour l'Alliance), Ravenholdt (349), Shatterspear
Trolls (629), Shen'dralar (809), Syndicate (70, plafond 0), Thorium Brotherhood (59), Timbermaw Hold (576), Wildhammer
Clan (471, Alliance, plafond 3000), Wintersaber Trainers (589, Alliance : base -42000 pour la Horde), Zandalar Tribe
(270), et les **14 factions propres à Forever** (ID 2586 et plus, absentes de Classic) :

| Faction (ID) | Camp (masques de race) | Zone (Naowh Forever, Dungeon Journal) |
| --- | --- | --- |
| Azeroth Commerce Authority (2586) | Alliance | oui |
| Durotar Supply and Logistics (2587) | Horde | oui |
| Emerald Wardens (2641) | deux camps | — |
| Cenarion Scouts (2719) | deux camps, base 500 | — |
| Kirin Tor (2740) | Alliance (races 1, 3, 4, 7 ; Horde à -42000) ; la note du 15 octobre corrige un bug qui laissait la Horde la monter | Dalaran |
| Barkskin Burrow (2747) | deux camps, base -3400 | — |
| Nightclaw Druids (2758) | les deux Skyborne (races 33, 34) | oui |
| Guardians of Hyjal (2765) | deux camps | Mount Hyjal |
| Windshapers (2778) | Windshaper Skyborne (34), base 3100 | — |
| High Order (2779) | High Order Skyborne (33), base 3100 | — |
| Bolder'ok Clan (2782) | Horde | — |
| Earthen Ring (2787) | Horde (races 2, 5, 6, 8), plafond 12500 | oui |
| The Watchers (2819) | deux camps | oui |
| Brotherhood of the Horse (2826) | Alliance | — |

Paliers (Haï à Exalté) : seuils de Classic, **non lus dans le client** (`suppose`) ; les plafonds 42999, 12500 et
3000 de `ReputationMax` sont, eux, lus.

## 2. Comment on les monte : sources trouvées

| Façon | Source (lecture locale) | Contenu | Certitude |
| --- | --- | --- | --- |
| Quêtes, montant par faction | Questie 11.38.0 Forever-v27, `Database/Classic/classicQuestDB.lua` (clé `reputationReward`, 26) | 2267 des 4244 quêtes portent une récompense (faction, montant) ; 37 factions, **aucune propre à Forever** | `suppose` (données Classic, non relues pour Forever) |
| Quêtes, corrections | Questie, `Corrections/Automatic/classicQuestReputationFixes.lua` | 4254 quêtes, 2994 couples (faction, montant) ; mêmes factions de Classic, plus 7 factions de métier | `suppose` |
| Quêtes, faction seule | Forever Guide 1.37.0 (déjà lu par `forever/pipeline/quest_sources.py`, `rewards.reputation`) | 265 quêtes du livre, 303 factions récompensées **sans montant** ; dont Kirin Tor (4 quêtes) | `suppose` |
| Quêtes, montant par difficulté | Client, table `QuestFactionReward` | deux lignes d'indices (gains et pertes par difficulté) ; l'indice de chaque quête n'est pas dans les tables | `certain` pour la table, lien aux quêtes absent |
| Objets à rendre (rendus répétables) | Naowh Forever 1.1.37, Dungeon Journal, `Data/Factions/*.lua` | 37 rendus sur 13 factions (gain par rendu, niveau, objets pris, donneur et position, monstres qui lâchent l'objet) | `suppose` (addon communautaire) |
| Récompenses par palier | Naowh Dungeon Journal (31 factions : paliers et objets, 22 avec prix, 17 intendants positionnés ; 10 marquées nouvelles, 3 « pas encore sorties » : Brood of Nozdormu, Hydraxian Waterlords, Zandalar Tribe) ; Naowh BiS et Forever Companion (objets d'origine « Reputation ») | objets, paliers, prix | `suppose` |
| Donjons | Naowh Dungeon Journal (2 factions reliées à leurs donjons : Argent Dawn, Thorium Brotherhood) ; Naowh Utilities, Instance Tracker (réputation gagnée par passage, relevée dans les SavedVariables) | aucun relevé du joueur aujourd'hui (SavedVariables sans réputation) | relevé : `certain` quand il existera |
| Monstres (gain par mise à mort, plafond) | **aucune source locale** : Questie lie un PNJ à son modèle de faction (`FactionTemplate`), sans gain ; le gain par mise à mort et le palier où il cesse sont des règles du serveur | — | manque |
| Objectifs de zone | LegacyForever v0.11.1, `Data/Legacy.lua` (5 zones listent une réputation dans leurs objectifs) ; client : sort « Legacy Reputation Reward » (1324722, question LEG1) | sens non établi | `suppose` |
| Palier actuel | En jeu seulement (`C_Reputation`, lu par Forever Guide) | — | — |

Absents de l'installation (cités par `docs/DATA_SOURCES.md`, ligne « Gains de réputation par source ») : Forever
Journal, Saga (collecteurs), WoW Forever Rep & Skill Tracker (état courant seulement).

## 3. Ce que le dépôt sait déjà
- `forever/pipeline/quest_sources.py` lit les factions récompensées de Forever Guide (`rewards.reputation`, sans montant) ;
  le livre des quêtes les garde, aucun calcul ne les utilise.
- `forever/pipeline/questie.py` ne lit pas `reputationReward` (champs lus : nom, niveaux, races, classes, zone).
- `forever/pipeline/questcache.py` lit le début des enregistrements de `questcache.wdb` (niveau, zone, XP, argent) ; les
  champs de réputation d'un enregistrement ne sont pas lus (piste : récompenses de faction des quêtes vues, à établir).
- Équipement : `forever/gear.py` reconnaît l'origine « Reputation » des objets de Naowh (`NAOWH_CAMP_KINDS`).
- Ni ForeverLogger ni le contexte du pont ne lisent les réputations du personnage ; l'écran « Réputation » de ForeverBridge
  (`Screens.lua`) n'envoie qu'une question au modèle.
- Documents : `docs/DATA_SOURCES.md` (aucune base de gains trouvée au 2026-09-30), `docs/OPEN_QUESTIONS.md` DON9 (tables
  des réputations à inventorier) et LEG1, ROADMAP RP1 (réputations : factions, paliers, gains, récompenses).

## 4. Ce qu'il faudrait pour la route de réputation (bloc 4e)
- **Tables à ajouter** à `decode_rules.json` (version suivante, décision 263) : `Faction` (et `FactionTemplate` pour
  relier un PNJ à sa faction) ; `QuestFactionReward` en recoupement ; un fichier décodé `factions.json` (groupes, camp
  par masques de race, base, plafond).
- **Entrées de la route** : quêtes avec leur gain (Questie, `suppose` ; Forever Guide pour la faction seule ;
  `questcache.wdb` si ses champs de faction se confirment), rendus répétables de Naowh (objets, monstres qui les
  lâchent, donneur), donjons liés ; palier actuel envoyé par le pont (contexte : `C_Reputation`, hors combat, sous
  `pcall`) ; relevé des gains par ForeverLogger (prévu depuis DJ1, jamais fait).
- **Questions ouvertes à poser** :
  1. gain de réputation par monstre tué et palier où il cesse (règle du serveur, aucune source) ;
  2. seuils des paliers à Forever (ceux de Classic supposés) ;
  3. montants des quêtes des 14 factions propres à Forever (aucune source chiffrée ; Forever Guide donne la faction seule) ;
  4. sens de « Legacy Reputation Reward » (1324722) et des réputations des objectifs Legacy ;
  5. disposition des champs de réputation de `questcache.wdb` (indices `QuestFactionReward` ou montants).
