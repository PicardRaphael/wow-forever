# Inventaire des addons de données installés

Relevé du 2026-09-28, en lecture seule, sans réseau, sur le client Forever 1.60.1.70009 (`FOREVER_WOW_DIR` par défaut, `Interface/AddOns` et `WTF/Account/*/SavedVariables`). **Rien n'est ingéré** : aucun fichier de `forever/data/`, de `tests/fixtures/` ni du code n'a changé. Les comptes viennent de scripts jetables (hors dépôt) qui réutilisent `forever/pipeline/lua_table.py` et `forever/pipeline/questie.py`. Noms de compte, de royaume et de personnages anonymisés. Seuls les comptes, les clés et quelques identifiants sont repris ici, pas les tables.

Rappels utiles à la lecture :
- Le client charge l'interface `16001` et cherche `<Addon>_Camelot.toc` avant le `.toc` sans suffixe (`docs/ADDON.md`, section 3).
- `WOW_PROJECT_ID` vaut `WOW_PROJECT_MAINLINE`.
- Cache wago local : tables de sorts et de talents seulement. Aucune table d'objets, d'instances ni de quêtes n'a été téléchargée : les recoupements « client » se limitent à ces tables et aux caches du client sur disque.

## Relevé du 2026-09-30 (après installation de nouveaux addons)

Deuxième relevé du jour, en lecture seule, sans réseau, **sous le client 1.60.1.70124** (le relevé précédent du
2026-09-30 a été fait sous 70009). **Rien n'est ingéré** : aucun fichier de `forever/data/`, de `tests/fixtures/`
ni du code n'a changé. Aucun contenu n'a été recompté : les comptes des sections plus bas restent ceux du
2026-09-28 et doivent être relus par `forever addons status` (DJ1, décision 124).

Les **quatre addons conseillés par la décision 133 sont installés** (AtlasLoot mis à jour, Forever Guide,
Legacy Forever, Zone Level: Forever). D'autres addons, jamais conseillés par l'agent, sont **présents sans avoir
été inventoriés** jusqu'ici : leurs fichiers datent pour la plupart d'avant le relevé du 2026-09-28, ils n'étaient
donc pas nouveaux, seulement hors de l'inventaire.

### Empreintes de référence (pour `forever addons status`)

La version du `.toc` ne suffit pas (décision 124). Empreinte = SHA-256 de la liste triée des SHA-256 des fichiers
`.lua` et `.json` de l'addon, hors `.bak`, 12 premiers caractères. **C'est la ligne de base : aucun relevé
antérieur n'existe**, un premier passage de `forever addons status` ne pourra donc que constater « inchangé » ou
« changé » à partir d'ici.

| Addon | Version `.toc` | Fichiers | Taille | Empreinte | Dernier fichier |
| --- | --- | --- | --- | --- | --- |
| AtlasLootClassic | `Forever 1.60.1` | 82 | 3 Mo | `82c0718e9d98` | 2026-09-30 |
| AtlasLootClassic_Data | — | 3 | 1 Mo | `7f22ad2849eb` | 2026-09-30 |
| ForeverDungeonJournal | **1.3.2** | 25 | 6 Mo | `886ffc832e76` | 2026-09-30 |
| GearQuestForever | **0.2.20-beta** | 23 | 24 Mo | `faa3d66f772a` | 2026-09-30 |
| ForeverGuide | **1.16.2** | 24 | 17 Mo | `078fad14acc9` | 2026-09-30 |
| LegacyForever | **v0.6.5** | 13 | 1 Mo | `c4828de32092` | 2026-09-30 |
| ZoneLevelForever | **1.4** | 1 | 1 Mo | `a7e922c83b89` | 2026-09-30 |
| Questie | 11.38.0 Forever-v27 | 522 | 233 Mo | `6d58cf035130` | 2026-09-21 |
| QuestMaster | **2.4.0** | 120 | 78 Mo | `dea273f11e7f` | 2026-09-22 |
| Auctionator | 339 | 344 | 5 Mo | `2730bf985375` | 2026-09-28 |
| CraftingOrderClassic | **1.40.0** | 215 | 13 Mo | `0455f0f3167c` | 2026-09-30 |
| RXPGuides | **v4.11.11** | 402 | 43 Mo | `9a62e39fe16b` | 2026-09-28 |
| ForeverMapFix | **0.2.0** | 2 | 84 Mo | `c58bbcce05af` | 2026-09-21 |
| AtlasBIStooltips | **1.0.1** | 32 | 1 Mo | `cb98d658c574` | 2026-09-30 |
| RaphCompletionist | **0.2.1** | 5 | 1 Mo | `27159f4bdb32` | 2026-09-21 |

### Écarts avec le relevé du matin (non résolus)

| Addon | Relevé du matin | Relevé du soir | Commentaire |
| --- | --- | --- | --- |
| ForeverDungeonJournal | 1.3.1 | **1.3.2** | Deux versions publiées dans la même journée. Contenu non recompté. |
| GearQuestForever | 0.2.19-beta | **0.2.20-beta** | **Changement de structure** : l'addon est maintenant éclaté en 9 modules par classe (`GearQuestForever_DRUID`, `_HUNTER`, `_MAGE`, `_PALADIN`, `_PRIEST`, `_ROGUE`, `_SHAMAN`, `_WARLOCK`, `_WARRIOR`). La description d'un dossier unique des sections plus bas est périmée, comme pour FDJ en 1.3.1. |
| AtlasLoot Classic Forever | « 1.1.3 » (CurseForge), `.toc` `Forever 1.60.1` | « 1.1.4 » attendue (décision 133), `.toc` **toujours** `Forever 1.60.1` | Les fichiers datent du 2026-09-30 : l'addon **a bien été mis à jour**, mais la chaîne de version ne le dit toujours pas. Seule l'empreinte `82c0718e9d98` le prouvera au prochain relevé. Confirme la décision 124. |
| QuestMaster | 2.5.0 (`_Camelot.toc`, `X-Date: 2026-09-26`) | **2.4.0** dans les 6 `.toc`, dernier fichier du **2026-09-22** | **Écart non expliqué** : version en recul et fichiers plus anciens que le relevé du matin. Soit une erreur de lecture le matin, soit un retour à une version antérieure. À trancher par toi ; sans effet sur le projet (Quest Master est écarté, copie exacte de Questie). |

### Les quatre addons de la décision 133

| Addon | Version | Licence installée | Contenu utile | Format | Propre à Forever | Usage possible par domaine |
| --- | --- | --- | --- | --- | --- | --- |
| **AtlasLoot Classic Forever** (mise à jour) | `.toc` `Forever 1.60.1`, fichiers du 2026-09-30 | GPL-2 (`LICENSE`) | Butin par boss. Contenu non recompté depuis le 2026-09-28 (45 instances, 311 boss, 2 381 ID d'objets) | Lua, inchangé | À revérifier : les instances Forever étaient vides au 2026-09-28 | DJ1 (recoupement), T10 (liste d'ID) |
| **Forever Guide** | 1.16.2 | **aucune** (`LICENSE` absent ; « All Rights Reserved » d'après sa page CurseForge, `docs/DATA_SOURCES.md`) | 35 donjons (quêtes, chaînes de prérequis, butin des boss et des monstres normaux), environ 2 500 recettes des 12 métiers, recherche d'objets (14 831 ID distincts dans `ItemSearchData.lua`), livres de bibliothèque avec points d'apparition | Lua généré (`gen.py`, `build_search.py`) ; `Data.lua` (livres), `Dungeons.lua`, `DungeonLoot.lua`, `DungeonData.lua`, `DungeonTrash.lua`, `ItemSearchData.lua`, `ItemCatalogData.lua`, `Catalog.lua` ; interface traduite en 8 langues, **dont `DataFrFR.lua`** | Oui (donjons et quêtes Forever) | DJ1 (butin et quêtes de donjon), MT1 (recettes), T04d (XP des quêtes), T10 (objets) |
| **Legacy Forever** | v0.6.5 | **GPL-3.0-or-later** (`LICENSE` présent, `X-License` dans le `.toc`) | Catalogue Legacy : `rewards` (défis porteurs de récompense), `feeds`, `zones`, `completion` ; 266 entrées indexées dans `Data/Legacy.lua` (3 886 lignes) | Lua généré par `tools/gen_legacy.py` | Oui, entièrement | **LG1** (catalogue des défis et points), **LG2** (progression du compte via `LegacyForeverDB`) |
| **Zone Level: Forever** | 1.4 | **aucune** | 50 zones avec `minLevel`, `maxLevel`, `minFish`, donjons de la zone avec leur plage de niveau, moyen de transport, faction | Un seul `.lua` (916 lignes), table indexée par `uiMapID` | Oui (plages de niveau et donjons de Forever, dont The Hall of Thanes 13-18) | **forever-leveling** (« quelle zone à mon niveau », qui repose aujourd'hui sur les niveaux Classic de Questie), DJ1 (plages de niveau des donjons), H1 |

#### Point d'attention sur Forever Guide

Ses fichiers datent du 2026-09-30, mais **ses données sont figées à une version antérieure du jeu** : l'entête de
`Data.lua` cite « ForeverChanges (бета Forever, сборка **1.60.1.69913**, 22.09.2026) », et `ItemSearchData.lua`
et `DungeonLoot.lua` sont générés depuis la base Classic de cmangos et les taux de butin Classic de Wowhead.

Le critère « à jour pour Forever » de la décision 133 porte sur la **version des données**, pas sur la date du
fichier : Forever Guide **échoue** à ce critère pour tout ce qui vient du client (69913, trois versions de retard),
et n'apporte rien pour les taux de butin (Classic, `suppose`, comme AtlasLoot). Il reste utile pour ce qui n'a pas
d'autre source : quêtes et butin **de donjon** de Forever, recettes des métiers.

#### Point d'attention sur Legacy Forever

À l'inverse, ses données sont **générées des tables du client** : `-- Generated by tools/gen_legacy.py from
WoW: Forever build 1.60.1.70009. Source snapshot: 2026-09-25; https://wago.tools/db2/ (pinned CSV exports).`

C'est la **même source que forever-core** (wago.tools), à la même version (70009) : ses valeurs sont directement
comparables aux nôtres, et son `tools/gen_legacy.py` donne la liste des tables du client à lire pour le Legacy —
un raccourci pour l'inventaire de LG1. Licence GPL-3 : agrégats seulement dans le dépôt, comme partout.

### Les autres addons présents, non inventoriés jusqu'ici

| Addon | Version | Licence | Nature | Donnée exploitable ? |
| --- | --- | --- | --- | --- |
| **EllesmereUI** (20 modules) | — | `license.txt`, licence propre à l'auteur | Suite d'interface (barres, cadres, chat, compteurs de dégâts, minuteur mythique) | Non : présentation, aucune donnée de jeu |
| **RXPGuides** (RestedXP) | v4.11.11 | **CC BY-NC-SA 4.0** | Guides de leveling pas à pas | Itinéraires de leveling. **Clause NC** : la licence interdit l'usage commercial ; un agrégat dans le dépôt demande ton accord explicite avant tout usage |
| **CraftingOrderClassic** | 1.40.0 | **aucune** | Commandes de craft et de récolte | Recettes et composants (recoupe Forever Guide) ; MT1 |
| **ForeverMapFix** | 0.2.0 | **MIT** | 84 Mo de tuiles de carte ; auteur « OpenAI / based on Alexey Sofronov and Rhyster » | Non : images. Les 2 `.lua` sont du code |
| **AtlasBIStooltips** | 1.0.1 | **aucune** | Lignes « BiS » dans l'infobulle, 23 spécialisations | Listes BiS de la communauté ; recoupement lointain pour T10. Déjà écarté de l'inventaire du 2026-09-28 |
| **RaphCompletionist** | 0.2.1 | **aucune** | **Ton addon** (`## Author: Raph + ChatGPT`) ; ponts vers Questie et les métiers | À toi de dire s'il collecte quelque chose d'utile |
| **ForeverCompletionist** | — | — | **Ce n'est pas un addon** : aucun `.toc`, contient `baseline.json`, `inventory.json`, `tests/`, `source_importers/`, `LOCAL_INVENTORY.md`. Dossier de projet déposé dans `Interface/AddOns` | Le client ne le charge pas. À vérifier par toi : rien fait dessus |
| `AllTheThings.lua` (SavedVariables) | — | — | Sauvegarde **sans dossier d'addon** : reste d'une désinstallation | Non |

### Ce que ce relevé ne dit pas

- Aucun contenu n'a été recompté pour les addons déjà inventoriés : les chiffres des sections suivantes datent du
  2026-09-28 et sont **périmés** pour AtlasLoot, FDJ et GearQuestForever, qui ont tous changé depuis.
- Le chargement effectif en jeu n'a pas été vérifié. Aucun `_Camelot.toc` pour AtlasLoot, ForeverGuide,
  LegacyForever, ZoneLevelForever, GearQuestForever ni ForeverDungeonJournal : ils portent `## Interface: 16001`
  seul, ce qui suffit d'après `docs/ADDON.md` puisque 16001 est l'interface du client.
- Les recoupements avec le client et avec Questie n'ont pas été refaits.

## Versions relevées le 2026-09-30

Nouveau relevé des `.toc`, en lecture seule, sans réseau. **Seules les versions sont mises à jour** : le contenu (comptes, recoupements) n'a pas été recompté et reste celui du 2026-09-28 ci-dessous ; c'est ce que `forever addons status` devra signaler et relire (DJ1, décision 124).

| Addon | Relevé du 2026-09-28 | Relevé du 2026-09-30 | Fichiers datés du | Commentaire |
|---|---|---|---|---|
| ForeverDungeonJournal | 1.2.0 | **1.3.1** (`## Version`), `## Interface: 16001` | 2026-09-29 | Structure changée : le `.lua` unique est éclaté en 7 fichiers de `Data/` (`Dungeons`, `Bosses`, `QuestMaps`, `QuestChains`, `QuestRewards`, `DungeonEntrances`, `DungeonRoutes`), plus `Localization/Content_frFR.lua` et d'autres langues ; `README.txt` dit toujours v1.0.7 ; **toujours aucune licence**. La description « un seul `.lua` » de la section plus bas est périmée. |
| AtlasLoot Classic Forever | « 1.1.2 » (énoncé), `Forever 1.60.1` | **1.1.3**, nom de la version publiée sur CurseForge (nom du fichier téléchargé par le gestionnaire d'addons, précision de l'utilisateur), non lisible dans les fichiers : les `.toc` disent toujours `## Version: Forever 1.60.1`, aucune occurrence de « 1.1.3 » dans les modules | 2026-09-29 | Toujours aucun `_Camelot.toc` (`.toc` 11508 et `_Forever.toc` 11601). La chaîne de version ne suffit donc pas à détecter un changement : il faut l'empreinte des fichiers de données. |
| GearQuestForever | 0.2.16-beta | **0.2.19-beta** (`.toc`, `Core.lua:12`), `## Interface: 16001` | 2026-09-29 | Toujours aucune licence ni journal des changements. |
| Auctionator | 339 | 339 | — | Inchangé. |
| Questie | 11.38.0 Forever-v27 | 11.38.0 Forever-v27 | — | Inchangé. |
| Quest Master | 2.5.0 | 2.5.0 | — | Inchangé. |
| ForeverLogger | 0.2.0 | 0.2.0 | — | Addon du dépôt. |

## Écarts avec l'énoncé

| Addon | Énoncé | Relevé | Commentaire |
|---|---|---|---|
| AtlasLoot Classic Forever | 1.1.2 | `## Version: Forever 1.60.1` dans 15 `.toc` sur 16 | « 1.1.2 » n'apparaît nulle part : ni dans les `.toc`, ni dans `Init.lua` ou `Constants.lua`, ni dans un journal des changements. C'est probablement le numéro affiché sur CurseForge (projet 1422985). `AtlasLootClassic_DungeonsAndRaids.toc` porte encore `BCC 2.5.4`. |
| ForeverDungeonJournal | 1.2.0 | 1.2.0 (`.toc`) | `README.txt` dit v1.0.7 et les commentaires du code montent jusqu'à v1.0.26. |
| GearQuestForever | 0.2.16-beta | 0.2.16-beta (`.toc`, `Core.lua:12`) | `tasks/T04-plan.md` notait 0.2.14-beta. Pas de journal des changements : on ne sait pas ce qui a changé entre les deux. |
| Auctionator | 339 | 339 | Journal des changements 339 du 2026-09-21, avec trois correctifs « Forever ». |
| Quest Master | à relever | **2.5.0** (`QuestMaster_Camelot.toc`, `X-Date: 2026-09-26`) | `_Camelot.toc` et `_Forever.toc` sont identiques. |

## Synthèse

| Addon | Version | Licence installée | Contenu utile | Format | Propre à Forever | Verdict |
|---|---|---|---|---|---|---|
| AtlasLoot Classic Forever | Forever 1.60.1 | GPL-2 (`AtlasLootClassic/LICENSE`) ; bibliothèques BSD, LGPL, domaine public | 45 instances, 311 boss avec `npcID`, 2 381 ID d'objets, taux de butin Classic (`droprate.lua` : 295 PNJ, 2 135 couples) | Lua : `data["<Instance>"] = {MapID, InstanceID, LevelRange, items = {boss → {case, itemID}}}` ; les stats viennent du client (`C_Item.GetItemInfo`) | 12 instances (9 donjons, 3 raids) ; butin présent pour 2 seulement ; aucun `npcID` ni niveau pour les boss Forever | Recoupement pour DJ1 (donjons hérités), liste d'ID pour T10 |
| ForeverDungeonJournal | 1.2.0 | **aucune** ; données recopiées de sites tiers (`SOURCES.txt`) | 7 donjons, 52 boss (50 `npcID`), 153 objets de butin, 50 quêtes dont 16 propres à Forever, XP « de base » et « réglée » | Un seul `.lua` (7 427 lignes) : `DB`, `BOSS_LEVELS`, `FOREVER_QUEST_XP_FALLBACK`, `FOREVER_QUEST_BASE_XP`, chaînes de prérequis | Hall of Thanes et Ruins of Lordaeron ; boss d'ID ≥ 250000 ; quêtes 92xxx à 98xxx | Index d'ID et piste XP pour T04d, DJ1 ; jamais copié |
| GearQuestForever | 0.2.16-beta | **aucune** ; données tirées de Wowhead (Forever, Classic, TBC) | 7 626 objets (2 590 d'ID ≥ 200000), 6 256 infobulles Wowhead Forever, 471 576 recommandations par classe et niveau | Tables Lua générées (`_generated/`) : fiches, choix par emplacement, audit d'infobulles en texte brut | Infobulles Forever ; 69 noms de quêtes absents de Questie | Jeu de validation pour T10 ; liste cible pour T04d ; jamais copié |
| Auctionator | 339 | **All Rights Reserved** ; `AGENTS.md` interdit aux agents d'IA de s'en servir comme référence | Base de prix : 1 royaume de bêta, 343 objets, **1 seul jour** (2026-09-27) ; cache de prix marchands (105 objets) | SavedVariable `AUCTIONATOR_PRICE_DATABASE`, une chaîne CBOR par royaume, `{m, h, l, a}` par objet | 12 ID ≥ 200000 absents de Questie | Repli possible pour EC1, sous réserve de ta décision sur la licence |
| Quest Master | 2.5.0 | En-têtes « MIT », mais aucun fichier LICENSE (le README y renvoie) ; ces données sont celles de Questie | Base Classic : 4 244 quêtes, 10 119 PNJ, 6 645 objets de monde, 14 889 objets ; aucune XP | Même schéma que Questie, clés renommées | Rien dans la base ; 11 quêtes apprises en jeu (SavedVariable) | **Inutile pour vérifier Questie** (copie exacte) |

## AtlasLoot Classic Forever

### Chargement
- Chaque module a un `.toc` sans suffixe (Interface 11508) et un `_Forever.toc` (11601), mais **aucun `_Camelot.toc`**. D'après `docs/ADDON.md`, le client retombe donc sur le `.toc` 11508, en addon périmé (`probable`).
- Aucune SavedVariable `AtlasLootClassicDB` et absent des `AddOns.txt` des personnages : l'addon n'a jamais été chargé sur ce client (`certain`).
- Deux défauts probables au chargement, à vérifier en jeu (`/dump WOW_PROJECT_ID`, liste des addons) :
    - `Init.lua:16` attend une version de la forme `v<n>.<n>.<n>` et « Forever 1.60.1 » ne correspond pas. `Init.lua:35` reçoit alors `nil`, ce qui donne une erreur Lua probable.
    - Sous `MAINLINE`, `GetForVersion(classic, bcc)` renvoie la valeur **TBC**. L'addon afficherait donc les niveaux TBC des instances et des boss.

### Contenu
- Structure : instance → boss (`npcID`, `Level`, `DisplayIDs`) → entrées `{case, itemID}`. Pas d'emplacement, de classe ni de statistique : tout vient du client au survol.
- Comptes : 45 instances, soit 25 donjons Classic, 8 raids Classic, 9 donjons Forever et 3 raids Forever.
- Instances Forever :
    - Hall of Thanes et Ruins of Lordaeron ont du butin : 12 et 18 objets, ID 27xxxx.
    - Les 10 autres (dont Excavation Site, Drowned City, Barrow Deeps, Mount Hyjal, une nouvelle Onyxia) n'ont que « Loot will be updated asap! ».
    - `LevelRange` de Ruins of Lordaeron est identique à celui de Hall of Thanes : copier-coller probable.
- Dans les donjons Classic, un seul objet Forever (285292, Deadmines) : le reste est le butin de Classic Era, non mis à jour.
- Autres modules :
    - Crafting : sorts de fabrication et composants dans `Data/Profession.lua`, qui mêle Classic, TBC et Wrath.
    - Factions, PvP, Collections : données Classic, rien de propre à Forever.
- AtlasBIStooltips (1.0.1, sans licence) : lignes « BiS » dans l'infobulle pour 23 spécialisations, sans ID d'objet installé. Hors inventaire.

### Recoupements
- **ForeverDungeonJournal** : les 7 donjons de FDJ sont tous dans AtlasLoot.
    - Boss : `npcID` identiques sur tous les boss hérités. FDJ a 3 boss de plus (Oggleflint, Bazzalan, Lorgus Jett), AtlasLoot 2 de plus (Apothecary Hummel et Sever, à Shadowfang Keep).
    - Butin commun : 123 objets. Hall of Thanes et Ruins of Lordaeron concordent. Pour Lordaeron Captain, AtlasLoot est vide (`[NOT FOUND]`) alors que FDJ donne les ID Classic du Deathsworn Captain : donnée douteuse des deux côtés.
    - Niveaux des 38 boss hérités : 3 écarts d'un niveau avec la valeur Classic, 23 avec la valeur TBC.
- **Questie** :
    - Objets : 2 309 ID sur 2 381 sont dans son itemDB, mais **aucun des 31 objets Forever**.
    - PNJ : 334 `npcID` sur 337 sont dans son npcDB.
    - `npcDrops` de Questie contre boss d'AtlasLoot : 1 353 couples concordent, 251 citent un autre PNJ, 1 006 sans donnée.
    - Pour le contenu Forever, aucun recoupement n'est possible.
- **Client** :
    - 1 274 des 1 308 ID de Crafting existent dans `SpellName.csv` (recoupement par ID ; quelques entrées sont des objets).
    - Pour le reste, il faudrait `Item`, `ItemSparse`, `ItemSet`, `JournalInstance`, `JournalEncounter`, `JournalEncounterItem`, `Map` et `MapDifficulty`.
    - Les taux de butin et les `npcID` de créature restent des données serveur, absentes du client.

## ForeverDungeonJournal

### Provenance
- Aucune licence ni bibliothèque embarquée.
- `README.txt` dit que le Lua a été testé dans une API simulée, sans le client Forever.
- `SOURCES.txt` cite une douzaine de sites : foreverchanges.pro (source principale de l'XP « observée »), Wowhead Forever, wowforevertalents, wowf.io, 60.tools, etc.
- Les portraits viennent de captures d'écran du jeu.
- Conclusion : les tables ne se redistribuent pas. Une valeur reprise est au mieux `suppose`, avec l'URL citée.

### Contenu

| Donjon | Plage affichée | Quêtes | Boss | Butin |
|---|---|---|---|---|
| Hall of Thanes (Forever) | 13-20 | 5 | 4 | 13 |
| Ragefire Chasm | 13-18 | 6 | 4 | 12 |
| Ruins of Lordaeron (Forever) | 15-22 | 10 | 7 | 20 |
| The Deadmines | 17-26 | 7 | 9 | 30 |
| Wailing Caverns | 15-24 | 7 | 9 | 29 |
| Shadowfang Keep | 20-30 | 4 | 11 | 28 |
| Blackfathom Deeps | 22+ | 11 | 8 | 21 |

- Aucun raid. `level` est une chaîne d'affichage, qui ne sépare pas le niveau d'accès du niveau recommandé.
- Butin : `{itemID, nom, "emplacement, type", qualité}`, **sans taux** (FDJ le dit lui-même).
- `BOSS_LEVELS` couvre les 52 boss. Le commentaire du code (`.lua:1372`) dit que les valeurs des donjons hérités sont **reprises de Classic Era** ; seul Hall of Thanes est donné comme observé.
- Quêtes : 50 fiches (`id, name, level, requires, faction, pickup, objective, turnin, rewardItems…`).
    - 16 sont propres à Forever (92401 à 98423 ; les 96xxx, 96393 à 96403, sont celles de Hall of Thanes).
    - En tout, 27 ID ≥ 90000 et 9 chaînes de prérequis.
- XP : deux tables, `FOREVER_QUEST_BASE_XP` (48) et `FOREVER_QUEST_XP_FALLBACK` (71).
    - En jeu, si `GetQuestLogRewardXP` renvoie la base, l'addon lui substitue la valeur réglée. **L'API du client afficherait donc l'XP sans le multiplicateur de Forever.**
    - Deux incohérences internes : 6565 et 6562.
- SavedVariable `ForeverDungeonJournalDB` : état de l'interface seulement.
- Code : pas de `pcall` autour de `RegisterEvent`, alias de SavedVariable au niveau du fichier. C'est le contraire de `docs/ADDON.md`, à ne pas reproduire.

### Recoupements
- `monsters.json` : aucun boss de FDJ n'y figure (les 21 PNJ mesurés sont en plein air).
- Questie 11.38.0 :
    - 41 boss sur 52 sont dans le npcDB : 40 noms et 40 niveaux concordent. `BOSS_LEVELS` est donc bien une copie de Classic.
    - Les 11 boss des deux donjons Forever sont absents (Questie n'a aucun PNJ d'ID ≥ 200000). Ces deux donjons sont aussi absents de `dungeons.lua`.
    - Les 16 quêtes Forever sont absentes de questDB et de xpDB (ID max de Questie : 9665).
    - Sur les 34 quêtes Classic, 33 ont une XP de base : elle concorde pour 28 et diffère pour 5 (5723, 962, 1200, 6561, 6564).
- Quest Master : aucune quête Forever.
- AtlasLoot : voir plus haut. Trois sources, trois plages de niveau pour les donjons Forever, sans vérité locale.
- **Caches du client** : `Cache/WDB/enUS/questcache.wdb` (en-tête `WQST`, build 70009, 184 enregistrements dont 50 d'ID ≥ 90000) contient 12 des quêtes de FDJ.
    - Lecture **supposée** du format binaire (non documenté) : niveau, niveau minimal, QuestSort, QuestInfo (81 = donjon), RewardXPDifficulty, et un flottant **RewardXPMultiplier**.
    - Ce flottant vaut 1,0 pour 171 enregistrements sur 184, et 2,9 à 3,2 pour les quêtes de donjon. C'est exactement le rapport « réglée / base » de FDJ pour les 10 quêtes où il en donne un.
    - `creaturecache.wdb` (`WMOB`, 815 entrées) ne contient que 2 boss de FDJ, tous deux de Ragefire.

## GearQuestForever

### Provenance
- Aucune licence, pas de bibliothèque. Tous droits réservés par défaut ; la page CurseForge 1698950 est à vérifier.
- Sources déclarées dans les fichiers :
    - infobulles « Wowhead Forever » (`Data.ForeverAudit.generated.lua:4-6`) ;
    - Wowhead Classic et TBC, extraits le 2026-09-14 ;
    - une base de serveur émulé (`quest_template`) ;
    - AtlasLoot ;
    - textes Blizzard recopiés (`lore`, objectifs).
- La redistribution pose problème quelle que soit la licence du code. Même règle que Questie : lecture locale pour recouper, jamais de copie.

### Contenu
- Rôle en jeu (`/gq`) : il propose des améliorations d'équipement du niveau 1 à 60 par emplacement, classe, spécialisation et faction, avec des flèches sur le butin, les récompenses et les marchands.
    - Classement par poids de stats **TBC**.
    - Pas de journal de combat, `pcall` autour de `RegisterEvent`.
- Tables : `<classe>ItemFacts` (7 626 objets : nom, qualité, ilvl, niveau requis, type de source, PNJ, zone, nom de quête), `<classe>Picks` (471 576 lignes), `Notable`, `foreverAudit` (6 256 lignes : 4 698 infobulles, 1 558 « http 404 »), 367 fiches faites à la main, `StatWeights` et une seule recette.
- Types de source : butin du monde 3 034, récompense de quête 1 546, marchand 1 369, métier 1 088, butin de boss 548.
- **Aucune table de quêtes, de PNJ ni de zones** : seulement des chaînes (840 noms de quêtes, 589 PNJ, 141 zones).
- SavedVariables (compte et personnage) : chasses suivies, objets obtenus et fabriqués, réglages. Ce sont des données personnelles.

### Recoupements
- Questie : 5 011 objets en commun. 2 615 ne sont que dans GQF, dont 2 590 d'ID ≥ 200000.
    - Sur les objets communs, nom, ilvl et niveau requis des fiches sont presque toujours identiques à Questie : **ce sont les valeurs de Classic**.
    - Seules les infobulles de l'audit reflètent Forever : 99 écarts d'ilvl avec Questie, le plus souvent +1 ou +2.
    - Les 1 558 objets « 404 » sont presque tous dans Questie. Ce sont des candidats « retirés de Forever ou non indexés », à vérifier.
- Quêtes : 771 des 840 noms existent dans Questie. **69 n'existent ni dans Questie ni dans Quest Master** ; ils donnent 140 objets en récompense, dont 58 sur Zephras Isle, une zone inconnue de Questie. Pas d'ID, de niveau ni d'XP.
- Client :
    - Le seul ID de sort, 36074, est absent de `SpellName.csv` (recette TBC).
    - En rapprochant les textes d'effets des `Description_lang` de `Spell.csv`, 54 des 177 textes de procs trouvent un sort. C'est indicatif : il n'y a aucun lien fiable par ID.
    - Tables utiles : `Item`, `ItemSparse`, `ItemEffect`, `ItemXItemEffect`, `ItemRandomProperties`, `ItemRandomSuffix` (GQF donne la convention du signe de `suffixId`), `RandPropPoints`, `ItemSet`.

## Auctionator

### Licence
`LICENSE` : « All Rights Reserved ». `AGENTS.md` interdit explicitement aux agents d'IA d'utiliser l'addon « as basis of reference ». Le code de l'addon **n'a pas été lu** : le format ci-dessous est déduit de tes seules SavedVariables, d'où la certitude `probable`.

Bibliothèques : LibCBOR (MIT), LibStub (domaine public), LibBattlePetTooltipLine (MIT).

### Chargement
- Un seul `.toc`, qui déclare 16001. `Source_Forever/Constants.lua` n'est chargé que pour le type de jeu `camelot`.
- On ne sait pas quelle branche de l'hôtel des ventes Forever active, l'ancienne ou la moderne (`suppose`). Indice : la SavedVariable de l'hôtel des ventes moderne de Blizzard (`Blizzard_AuctionHouseUI.lua`) existe.

### Format de la base de prix
Réponse à la question ouverte « format et fonctionnement sur Forever » :
- Racine : `AUCTIONATOR_PRICE_DATABASE = {__dbversion = 8, ["<royaume>"] = <chaîne CBOR>}`, une entrée par royaume, sans suffixe de faction.
- Décodage : `lua_table.parse_lua_assignments`, puis un décodeur CBOR minimal, sans dépendance. Il est exact (11 789 octets lus sur 11 789).
- Par objet, la clé est l'ID en chaîne ; aucune variante `g:ID:…` n'a été observée. Chaque entrée a exactement quatre champs :
    - `m` : prix minimum courant, en cuivre par unité ;
    - `h[jour]` : plus haut du minimum dans la journée ;
    - `l[jour]` : plus bas, stocké seulement s'il diffère de `h` (10 cas) ;
    - `a[jour]` : quantité disponible.
- Le jour est un nombre de jours depuis le 2020-01-01 (`probable`). Trois indices concordent : l'époque calculée, les heures Unix de `AUCTIONATOR_POSTING_HISTORY` et la date de modification du fichier.
- Volume : **1 royaume de bêta, 343 objets, 1 seul jour** (2026-09-27), aucun historique. Ni scan complet ni scan automatique configuré ; six entrées ont un `a` vide, dont cinq correspondent à tes propres mises en vente.
- Rétention configurée : 21 jours.
- Autres SavedVariables :
    - `AUCTIONATOR_VENDOR_PRICE_CACHE` : 105 prix marchands, en cuivre, fractionnaires pour les piles ;
    - `AUCTIONATOR_POSTING_HISTORY` : tes ventes, données personnelles ;
    - `SELLING_GROUPS` ; listes d'achats et recherches vides.

### Recoupements
- Questie : 331 des 343 objets y sont. Les 12 absents ont tous un ID ≥ 200000 (247789 à 286745). Côté cache marchand, 6 objets sur 105 sont absents.
- Client : `ItemSparse.SellPrice` et `BuyPrice` donnent le prix marchand ; il faudrait aussi `Item` et `ItemClass` pour les catégories, et `SpellReagents` pour les composants.

## Quest Master contre Questie

### Lignée : une copie exacte de Questie
- Les quatre bases Classic chargées sur Forever (`Database/Classic/{QuestData, CreatureData, GameObjectData, ItemSourceData}.lua`) sont **identiques octet pour octet** au corps des bases compilées de Questie 11.38.0 Forever-v27. Seule la ligne d'ouverture change (`QMData.questData` au lieu de `QuestieDB.questData`). Pour les quêtes, les deux corps ont la même empreinte md5.
- Le schéma est identique aux mêmes positions, avec des clés renommées : `qMinLvl` pour `requiredLevel`, par exemple. Les champs 27 à 30 portent même de faux noms, et `DatabaseLoader.lua:333-358` recrée des alias vers les noms de Questie.
- `Database/CoreData/` (non chargé) contient des fichiers Questie laissés tels quels (« AUTO GENERATED FILE! », `QuestieLoader:ImportModule`).
- L'en-tête « MIT, compiled from in-game data extraction » est un gabarit collé sur des données de Questie : il ne peut pas couvrir leur licence.

### Comparaison par ID (Classic)

| Base | Quest Master | Questie | Communs | Écarts |
|---|---|---|---|---|
| Quêtes | 4 244 | 4 244 | 4 244 | 0 sur tous les champs : niveau, niveau requis, races, classes, zone, donneur, rendeur, objectifs, prérequis, réputation |
| PNJ | 10 119 | 10 119 | 10 119 | 0 : PV, niveaux, rang, positions, zone |
| Objets de monde | 6 645 | 6 645 | 6 645 | 0 |
| Objets | 14 889 | 14 889 | 14 889 | 0 |
| XP | aucune | par ID de quête (`xpDB-classic.lua`) | — | comparaison impossible |

- Sur les 32 couples PNJ-niveau de `monsters.json`, Quest Master donne la même valeur que Questie : même sous-estimation des PV à partir du niveau 10.
- Aucune quête Forever dans ses bases, quelle que soit la version (Classic, TBC, Wrath, MoP), ni aucune des 16 quêtes Forever de FDJ.
- **Conclusion : leur concordance ne prouve rien. Quest Master ne peut pas vérifier Questie.** En jeu, il est même moins juste que Questie : il ne charge pas les corrections de Questie.

### Ce que l'inventaire a révélé au passage
- **Corrections de Questie ignorées par le dépôt.** `Questie_Camelot.toc` charge `Database/Corrections/classicQuestFixes.lua` (environ 2 010 entrées) et `classicNPCFixes.lua` (environ 1 015), mais `forever/pipeline/questie.py` lit la base compilée **sans ces corrections**.
    - Pour les 21 PNJ de `monsters.json`, seuls 12319 et 12320 sont corrigés, et seulement pour `spawns` et `zoneID` : l'écart de PV mesuré ne vient pas de là.
    - En revanche, `forever lookup zones` peut manquer des corrections de niveau, de races ou de zone.
- **`QuestieForeverDB`** (SavedVariable de `Modules/ForeverQuestData.lua`, déjà désignée par `ROADMAP.md` pour T04d) : 139 quêtes apprises en jeu, dont 38 absentes de la base (37 d'ID ≥ 90000). Champs : titre, niveau, objectifs, points d'intérêt, sources, quête journalière ou non, rendue ou non. Pas d'XP. Les 11 quêtes découvertes par Quest Master (module `Discovery`) en font toutes partie.
- **XP versée par le serveur** : `QuestMasterSavedDB.char.*.questHistory[].xp` est l'argument `xpReward` de `QUEST_TURNED_IN`, donc l'XP réellement reçue. Il n'y a qu'un seul point (quête 805, +2,2 % sur `xpDB-classic`, niveau du personnage inconnu) : aucune conclusion possible, mais c'est la bonne méthode de mesure.
- Rapports d'XP de FDJ sur Questie, pour 49 quêtes Classic : 24 sont à environ 1,0, une à 0,74 et les 24 autres de 2,9 à 7,5, **à niveau égal**. Ce n'est ni un facteur global ni une courbe par niveau : c'est un réglage par quête, cohérent avec le multiplicateur lu dans `questcache.wdb`.

## Usage proposé par domaine

| Domaine | AtlasLoot | ForeverDungeonJournal | GearQuestForever | Auctionator | Quest Master |
|---|---|---|---|---|---|
| **DJ1** donjons | Donjons hérités : boss → `npcID` → objets, en recoupement `suppose`. Toujours prendre la valeur Classic de `GetForVersion` (1ᵉʳ argument). Taux Classic de `droprate.lua` en `suppose`, sans source. Liste des 12 instances Forever. | Meilleur index du contenu Forever : `npcID` des boss (25xxxx, 26xxxx), ID du butin, quêtes de donjon. Tout est `suppose` avec URL ; les niveaux des boss hérités sont une copie de Classic. | 548 objets « boss_drop » avec PNJ et zone, à recouper. | — | Rien. |
| **T04d** quêtes Forever et XP | Rien. | 16 quêtes Forever (niveau, prérequis, faction), valeurs d'XP en recoupement. Piste du modèle : XP = `QuestXP(niveau, difficulté)` × multiplicateur par quête. | Liste cible de 69 noms de quêtes (Zephras Isle surtout), sans ID. | ID ≥ 200000 à identifier (objets Forever). | Rien comme source. Méthode de mesure à reprendre : `xpReward` de `QUEST_TURNED_IN`, avec le niveau du personnage. |
| **T10** équipement | Liste d'ID à résoudre par `Item`, `ItemSparse` et `ItemSet` ; aucune stat. | Lien objet → source seulement. | Jeu de validation : infobulles Forever contre la base tirée d'`ItemSparse`. Liste des 2 590 ID ≥ 200000. Convention des suffixes aléatoires. Ne pas reprendre les poids TBC. | Indication de valeur marchande seulement. | Rien (`iRewardedFrom` = `questRewards` de Questie). |
| **FA1** addon | Aucune donnée (et la GPL-2 s'étendrait à tout code repris) ; modèle d'affichage via `C_Item`. | Modèle d'interface ; montre que l'XP du client doit être corrigée. Défauts à ne pas reproduire. | Retour d'expérience sur le client Forever : chaînes d'infobulle secrètes, événements supprimés, SavedVariables injectées tard, erreur « script ran too long » vers 467k lignes, découpage fiches / lignes. | — | `Compat.lua:323` : sur Forever, `QUEST_ACCEPTED` et `QUEST_WATCH_UPDATE` passent un ID de quête (à recouper). |
| **EC1** économie | Peu utile : prix marchands et composants de `Profession.lua` (à recouper avec `SpellEffect`). | Rien. | Rien (prix seulement dans le texte des infobulles). | Repli local avant le lancement, lecteur sur disque en `probable`. Limites : 1 jour, 1 royaume de bêta, minimum et non médiane, données personnelles mêlées. **Préalable : ta décision sur la licence.** | Rien. |

## Bloqué sur moi
1. *Tranché par l'utilisateur le 2026-09-30 (décision 123) : lecture locale de ses propres SavedVariables, décodage maison, code de l'addon jamais lu ni repris.* **Auctionator et sa licence** : « All Rights Reserved », plus un `AGENTS.md` adressé aux agents d'IA. Un lecteur maison du format de tes propres SavedVariables (CBOR standard) relève de l'interopérabilité, mais c'est à toi de décider si EC1 peut s'y appuyer. Sinon, l'API Blizzard reste la seule source.
2. **Tables du client à télécharger** (réseau, `forever fetch`, accord nécessaire). Noms et colonnes non vérifiés sur 70009 :
    - T10 : `Item`, `ItemSparse`, `ItemEffect`, `ItemXItemEffect`, `ItemSet`, `ItemRandomProperties`, `ItemRandomSuffix`, `RandPropPoints` ;
    - DJ1 : `JournalInstance`, `JournalEncounter`, `JournalEncounterItem`, `JournalEncounterCreature`, `LFGDungeons`, `Map`, `MapDifficulty` ;
    - T04d : `QuestV2`, `QuestXP`, `QuestInfo`, `QuestSort`, `QuestLine`, `QuestLineXQuest`, `QuestPOIBlob`, `QuestPOIPoint`, `ContentTuning`.
3. **Licences amont** (CurseForge, réseau) : AtlasLoot 1422985 (GPL-2 installée), GearQuestForever 1698950, ForeverDungeonJournal (aucune piste), Questie 334372 (déjà ouvert).
4. **Vérifications en jeu** :
    - AtlasLoot : quel `.toc` est chargé, erreur de `Init.lua:35`, affichage des niveaux TBC ?
    - Auctionator : quelle branche d'hôtel des ventes est active ?
    - Relever quelques XP de quêtes rendues avec le niveau du personnage.
5. Origine du « 1.1.2 » d'AtlasLoot (page CurseForge ?).

## Modifications proposées (non faites : l'énoncé limite l'écriture à ce fichier)
- `docs/DATA_SOURCES.md`, section « Addons installés » :
    - AtlasLoot : GPL-2, recoupement DJ1, valeur Classic de `GetForVersion`, jamais copié.
    - Quest Master : copie de Questie, exclu comme vérification.
    - Auctionator : format de la base de prix, licence restrictive.
    - GearQuestForever : version 0.2.16-beta, données Wowhead.
    - Caches du client : `questcache.wdb` porterait RewardXPDifficulty et un multiplicateur d'XP (`suppose`).
- `docs/OPEN_QUESTIONS.md` :
    - format `WQST` de `questcache.wdb` (champ multiplicateur) ;
    - XP de Forever par quête et non globale ;
    - `questie.py` sans la couche de corrections : l'ajouter ou le signaler dans la provenance ;
    - époque et sens des champs d'Auctionator sur plusieurs jours de relevés ;
    - branche d'hôtel des ventes sur Forever ;
    - chargement d'AtlasLoot sans `_Camelot.toc` ;
    - plages de niveau des donjons Forever contradictoires (FDJ, AtlasLoot) : `LFGDungeons` pour trancher.
- `docs/ROADMAP.md` :
    - T04d : ajouter aux sources `questcache.wdb`, les tables de quêtes du client, `QuestieForeverDB` et la mesure de `xpReward`.
    - DJ1 : ajouter AtlasLoot aux recoupements ; retirer l'idée que `BOSS_LEVELS` de FDJ recoupe H1 pour les donjons hérités (c'est une copie de Classic).

## Relevé du 2026-10-01 par `forever addons status --save` (T08b, bloc D)

Les empreintes de référence ci-dessus sont **remplacées** par le relevé de la commande, gardé dans
`<cache>/addons/state.json` (empreinte de chaque fichier `.lua` et `.json`, version du `.toc`, agrégats de Questie).
Empreinte de la commande : SHA-256 de la liste triée des SHA-256 des fichiers de données de l'addon **et de ses
modules** (`AtlasLootClassic_*`, `GearQuestForever_*`), 12 caractères : elle diffère donc de la colonne ci-dessus
pour les addons à modules. Versions relevées (premier relevé, statut `nouveau`) : Questie 11.38.0 Forever-v27,
AtlasLootClassic `Forever 1.60.1`, ForeverDungeonJournal **1.3.3**, GearQuestForever 0.2.20-beta, ForeverGuide
**1.17.0**, LegacyForever **v0.6.7**, ZoneLevelForever 1.4, Auctionator 339, ForeverLogger 0.2.0 (en gras : nouvelle
version depuis le relevé du 2026-09-30). Les passages suivants rendent `inchangé` ou `changé`.
