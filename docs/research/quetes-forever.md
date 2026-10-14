# Quêtes de Forever : agrégats (T04d, bloc D)

> Relevé du 2026-10-13 par `forever quests build` (empreinte `e9ea35ee9b5847d2`), addons installés lus en local.
> Seuls des agrégats entrent dans le dépôt (décision 133) ; la liste fusionnée vit dans le cache
> (`<cache>/quests/`), rebâtie à la demande (`forever quests build|diff|show`, `forever lookup quests`).

Sources (quêtes lues) : client (questcache.wdb et QuestXP) 1.60.1.70338:f262004ced4e (203), Questie (Classic Era, corrections comprises) 11.38.0 (4244), Naowh Forever, Completo 1.1.11 (2917), Naowh Forever, Journeys 1.1.11 (2857), Naowh Forever, Dungeon Journal 1.1.11 (233), Forever Guide 1.33.0 (550), ForeverDungeonJournal 1.6.2 (78), Questie, quêtes apprises en jeu (QuestieForeverDB) (285), GearQuestForever 0.5.4-beta (725).

## Statuts

| Statut | Quêtes |
| --- | --- |
| nouvelle | 556 |
| retouchée | 183 |
| absente des sources Forever | 19 |
| inchangée | 2597 |
| non couverte | 1445 |
| total | 4800 |

« absente des sources Forever » : quête de la base Classic de Questie, dans une zone couverte par Completo, absente
de Completo : candidate au retrait (`suppose`), jamais « retirée » (question LVL9). « non couverte » : quête de la
base Classic hors des zones de Completo (donjons, catégories, villes) : rien ne dit si Forever la garde.

Champs changés des quêtes retouchées (une quête peut en compter plusieurs) : prereq_any 142, min_level 20, level 16, xp 11.

## Par zone (Completo)

| Zone | nouvelle | retouchée | absente des sources Forever | inchangée | non couverte |
| --- | --- | --- | --- | --- | --- |
| Alterac Mountains | 6 | 0 | 0 | 9 | 0 |
| Arathi Highlands | 2 | 3 | 1 | 45 | 0 |
| Ashenvale | 8 | 2 | 0 | 63 | 0 |
| Azshara | 0 | 5 | 0 | 27 | 0 |
| Badlands | 1 | 4 | 0 | 37 | 0 |
| Blasted Lands | 0 | 0 | 0 | 18 | 0 |
| Burning Steppes | 0 | 0 | 0 | 20 | 0 |
| Darkshore | 7 | 3 | 0 | 57 | 0 |
| Darnassus | 4 | 6 | 2 | 23 | 0 |
| Desolace | 5 | 5 | 0 | 53 | 0 |
| Dun Morogh | 21 | 4 | 4 | 38 | 0 |
| Durotar | 19 | 4 | 2 | 41 | 0 |
| Duskwood | 20 | 4 | 0 | 66 | 0 |
| Dustwallow Marsh | 0 | 4 | 0 | 49 | 0 |
| Eastern Plaguelands | 0 | 5 | 1 | 94 | 0 |
| Elwynn Forest | 26 | 4 | 2 | 52 | 0 |
| Felwood | 0 | 1 | 0 | 84 | 0 |
| Feralas | 1 | 4 | 0 | 70 | 0 |
| Hillsbrad Foothills | 9 | 3 | 0 | 60 | 0 |
| Ironforge | 3 | 2 | 1 | 88 | 0 |
| Loch Modan | 5 | 6 | 0 | 34 | 0 |
| Moonglade | 0 | 0 | 0 | 8 | 0 |
| Mulgore | 21 | 3 | 0 | 30 | 0 |
| Orgrimmar | 8 | 3 | 2 | 78 | 0 |
| Redridge Mountains | 4 | 1 | 0 | 32 | 0 |
| Searing Gorge | 0 | 1 | 0 | 30 | 0 |
| Silithus | 0 | 10 | 0 | 108 | 0 |
| Silverpine Forest | 8 | 3 | 0 | 35 | 0 |
| Stonetalon Mountains | 5 | 6 | 0 | 35 | 0 |
| Stormwind City | 16 | 5 | 0 | 74 | 0 |
| Stranglethorn Vale | 3 | 18 | 1 | 97 | 0 |
| Swamp of Sorrows | 2 | 0 | 0 | 33 | 0 |
| Tanaris | 0 | 5 | 1 | 95 | 0 |
| Teldrassil | 15 | 5 | 0 | 48 | 0 |
| The Barrens | 13 | 8 | 0 | 110 | 0 |
| The Hinterlands | 0 | 0 | 0 | 39 | 0 |
| Thousand Needles | 2 | 2 | 0 | 45 | 0 |
| Thunder Bluff | 4 | 4 | 2 | 31 | 0 |
| Tirisfal Glades | 25 | 4 | 0 | 62 | 0 |
| Un'Goro Crater | 0 | 1 | 0 | 42 | 0 |
| Undercity | 3 | 4 | 0 | 37 | 0 |
| Western Plaguelands | 0 | 6 | 0 | 63 | 0 |
| Westfall | 11 | 1 | 0 | 33 | 0 |
| Wetlands | 26 | 9 | 0 | 37 | 0 |
| Winterspring | 0 | 2 | 0 | 58 | 0 |
| Zephras Isle | 108 | 0 | 0 | 0 | 0 |

## Écarts entre sources

Par champ : level 224, faction 43, prereq_any 38, xp 31, min_level 21, next 2.

| Paire de sources | Quêtes en désaccord |
| --- | --- |
| forever_guide / naowh_dj | 202 |
| naowh_dj / questie | 198 |
| completo / questie | 109 |
| fdj / naowh_dj | 22 |
| fdj / fdj_text | 21 |
| fdj / questie | 11 |
| completo / forever_guide | 9 |
| completo / naowh_dj | 7 |
| fdj_text / questie | 7 |
| naowh_dj / questie_forever | 6 |
| client / completo | 4 |
| client / questie | 3 |
| questie / questie_forever | 2 |
| fdj / forever_guide | 1 |
| client / naowh_dj | 1 |
| client / fdj | 1 |
| client / questie_forever | 1 |
| completo / questie_forever | 1 |

Un écart n'est jamais tranché par moyenne : la valeur retenue suit la priorité client > relevé du joueur > addons
de Forever > Questie Classic, et toutes les valeurs restent dans `discrepancies`. Exemple connu : le Dungeon
Journal de Naowh donne un seul niveau, qui est le niveau requis (Slaying the Beast, 5761 : 9 contre 16 dans Forever
Guide et Questie).

## Tables des chaînes du client (téléchargées une fois, non décodées)

- `QuestLine` : 3 ligne(s) ; `QuestLineXQuest` : 22 ligne(s), 22 d'ID ≥ 90000, 11 présentes dans la liste fusionnée dont 11 au statut `nouvelle` ; 3 chaîne(s) touchent une quête de Forever.
- `QuestPOIPoint` : 99 point(s), sans colonne de quête (seulement `QuestPOIBlobID`) : leur rattachement
  exige `QuestPOIBlob`, à décider au plan de RX1.

## Recoupement avec Factoruide (RX1, bloc A, 2026-10-14)

> `forever quests build --rebuild` puis `forever quests diff --factoruide` (empreinte de la liste `170ca2799c91a5ec`,
> base de Factoruide `f7da6da`, empreinte `109110f37776b7b3`, import du 2026-10-13). Lecture locale du cache
> (décision 266) ; seuls ces agrégats entrent dans le dépôt.

| Statut chez Factoruide | Connues des deux | De Factoruide seul |
| --- | --- | --- |
| available | 4439 | 332 |
| incomplete | 82 | 67 |
| removed | 363 | 213 |

Liste fusionnée : 5224 quêtes (nouvelle 648, retouchée 196, absente des sources Forever 19, inchangée 2645, non
couverte 1384, **vue seulement chez Factoruide 332**) ; 8 quêtes connues de nous seuls.

**Lecteurs incomplets corrigés** (avant : 387 quêtes `available` de Factoruide absentes de notre liste ; 89 citées par
un fichier local ; **51 récupérées**, d'où 332) :
- `read_questie_forever` jetait les entrées de `QuestieForeverDB` sans titre ni niveau (quête rendue vue en jeu) et ne
  lisait pas les quêtes faites (`QuestieConfig.char[…].complete`, sans nom de personnage gardé) : livres, « Camping
  101 », quêtes de classe faites ;
- Naowh Discovery `Data/Books.lua` (livres de la bibliothèque et objectifs « Friend of the Library ») jamais lu ;
- Forever Guide `ChainData.lua` (chaîne du sac de couchage, départ propre à chaque camp) jamais lu ;
- Dungeon Journal de Naowh `Data/QuestChains.lua` (chaînes « Call of Fire », « The Moonsilver Blade », « Old
  Fire-Eye » : noms, niveaux minimaux, ordre, donneur du début) jamais lu ;
- ForeverDungeonJournal `Data/QuestChains.lua` et `Data/QuestMaps.lua` (prérequis requis, détails, donneurs) jamais
  lus.

**38 citations écartées, avec leur preuve** : coïncidences numériques (identifiants d'objets, de PNJ ou de sorts dans
`ItemCatalog*`, `LootDB`, `*NpcDB`, `*ObjectDB`, `EnchantSpells*`, `Transports.lua`, `Data.lua` de ForeverMapFix) ;
fichiers d'un autre mode de jeu exclus par construction (Questie `SeasonOfDiscovery.lua` : 16 quêtes de la Saison de
la Découverte ; `QuestieQuestBlacklist.lua` et corrections de Classic pour les quêtes de classe retirées en Classic
5640, 5678, 7669, 7670, 8259 et 65593 à 65610) ; AlexAtlasLoot `QuestDB.lua` (écarté, décision 265) ;
SavedVariables d'AllTheThings (addon désinstallé, fichier du 2026-09-24) et de RaphCompletionist (92479).

**Les 332 restantes** sont « vue seulement chez Factoruide » (`suppose`, jamais placées dans une route, LVL17) :
Factoruide les tient de Wowhead Forever et d'AllTheThings. AllTheThings a une saveur `forever` (interface 16001,
licence MIT, base Forever mise à jour chaque jour) : une fois installé, un lecteur local pourra les confirmer.
