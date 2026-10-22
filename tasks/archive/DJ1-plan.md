# DJ1 — Donjons de Forever : plan

> Plan rédigé le 2026-10-13 (`/tranche DJ1`), sans code. Exécution : `/tranche DJ1` dans une nouvelle session, sur la
> branche `dj1`, un cycle rouge → vert par bloc. Échéance : finie avant le **2026-10-21** (fin de la bêta) pour laisser
> RX1 démarrer (décision 251) ; **aucune sonde en jeu exigée** (décision 247) : les relevés du joueur vérifient, ils ne
> bloquent rien. Ordre des blocs = ordre d'utilité : si le temps manque, les blocs A à E suffisent au bouton Leveling
> et à RX1 ; F et G peuvent glisser.

## Demande de l'utilisateur (2026-10-13)
Avant le plan : consigner dans `docs/DECISIONS.md` la règle « étude de l'existant à chaque plan de tranche » (**fait :
décision 264**, committée avec ce plan ; le reste de `tasks/idees-du-chat-2026-10-13-factoruide.md` attend RX1).
Puis DJ1, utile à toutes les classes, sans sonde obligatoire :
1. Étude de l'existant, puis liste des donjons de Forever (nouveaux compris, comme City of Dalaran), niveaux, entrée,
   boss.
2. Quêtes de chaque donjon : prérequis, donneur, XP réelle (`QuestXP` et `questcache.wdb`, T04d), depuis Naowh Forever
   (Dungeon Journal, « à faire d'abord »), Forever Guide, ForeverDungeonJournal, FojjiCore DungeonJournal ; écarts
   signalés, jamais devinés.
3. Butin de chaque boss avec ses taux quand une source les donne (AtlasLoot, Naowh BiS, ForeverDungeonJournal, Naowh),
   marqué pour ma classe et mon niveau ; seuls nos agrégats dans le dépôt (décision 133).
4. Rentabilité : XP par heure du premier passage avec quêtes et des passages suivants (modèle de T04d, bonus de
   T04f), quand un donjon vaut le coup face aux quêtes du dehors ; bouton Leveling et chat, toutes les classes.
5. Préparer RX1 : chaque donjon et ses quêtes placés dans une route au niveau où ils rapportent le plus.

## Réponses de l'utilisateur (2026-10-13)
1. **Réseau, étude de l'existant** : accord en lecture seule (recherche web, pages ; ni téléchargement ni clonage).
   Faite le 2026-10-13, résultat plus bas.
2. **Tables du client** : téléchargées de wago.tools par la voie existante de `forever fetch` et `forever update`,
   épinglées à la version, et décodées : `Map`, `LFGDungeons`, `JournalInstance`, `JournalEncounter`,
   `JournalEncounterItem`, `DungeonEncounter`, `AreaTable`.
3. **Durée et monstres d'un passage** : mes relevés d'abord (journaux, ForeverLogger), en complément les relevés que
   Naowh tient déjà (`InstanceTracker`, `journalRun`, `journalKills`), lus en local ; à défaut, les comptes de
   monstres des addons tels quels, mais leurs durées de speedrun sont des **bornes basses** (groupes très rapides),
   ajustées et marquées `suppose` ; sinon une hypothèse par donjon : **formule de Factoruide** (MIT, citée),
   `suppose`.
4. **ForeverLogger** : passages (entrée et sortie d'instance) et butin ramassé avec son boss ; marchands vers EC1,
   réputation vers RP1 (amende la ligne DJ1 de la ROADMAP et la décision 127 pour ces deux relevés).
5. **Taux de butin** : Naowh d'abord (`suppose`, origine déclarée : Wowhead Forever et wowsrc) ; FojjiCore en
   recoupement, écart signalé ; taux Classic (Forever Guide, AtlasLoot, Forever Companion) seulement pour un boss
   inchangé, étiquetés « Classic » ; mes relevés priment toujours (`certain`).

## Étude de l'existant (décision 264 ; web le 2026-10-13, lecture seule)

Aucune source ne publie à la fois des donjons de Forever complets, sous licence libre, avec des **taux de butin
mesurés sur Forever** ou une **durée de passage mesurée**. Réutilisable : des formats et un algorithme ; les données
viennent du client et des addons installés.

| Trouvaille | Licence | Fraîcheur | Réutilisable pour DJ1 | Verdict |
| --- | --- | --- | --- | --- |
| Notes de développement de la bêta (forum Blizzard, t/2360696) | officiel | 2026-10-08 | donjons ouverts, Excavation Site 26-31, RFD 25+, Uldaman 30+, Dalaran ouvert aux tests (08/10), quêtes de donjon −50 % du bonus (I9), monstres de donjon +20 % (I10), bug de l'XP en groupe (corrigé, non modélisé) | source (`probable`) |
| Factoruide (`crates/fg-route/src/model/dungeons.rs`, `params.rs`, `overrides/dungeons.toml`) | MIT (code), GPL-2.0+ (données) | 2026-10-13 | **formule par défaut d'un passage** : minutes = borne(40 + niveau des monstres, 50, 120), monstres = 60 + 2 × niveau ; niveau des monstres = médiane des niveaux des quêtes ; plage déduite des quêtes ; quêtes ramassées d'avance (`dungeon_pickup_ahead` 8) ; butin pondéré par sa probabilité ; format TOML d'un donjon (aire, entrée, niveaux, minutes, monstres) | **réutiliser l'algorithme** (cité, `suppose`) ; données non lues |
| ForeverDungeonRoutes (Checkov23) | MIT (cartes exclues) | 2026-10-13 | entrées et salles générées des tables du client | recouper (idée : entrées par le client) |
| DungeonLens (denisanzora) | MIT | 1 commit | entrées par wago.tools ; dit qu'aucune source ne mesure les taux de Forever | recouper |
| AtlasLootForeverImenso | aucune | 2026-09-19 | format de collecte `ALF1` (taux = lâchés ÷ fouillés) | recouper (format) |
| ForeverDungeonJournal (lemillermicrosoft, homonyme) | MIT | alpha | paquets de données avec source, version, licence | recouper (format) |
| adventure-guide-forever (cjber) | GPL-3.0+ | inconnue | chaînes de quêtes, prérequis d'entrée | recouper |
| foreverchanges.pro, wowf.io, wclbox, wowtbc.gg, wowforeverguides, Warcraft Tavern | aucune licence ouverte | sept.-oct. 2026 | XP des quêtes (totaux divergents : Hall of Thanes 13 300 contre 10 750 XP pour l'Alliance), listes de boss et d'objets | contrôle ponctuel seulement (décision 128) |
| Wowhead Forever | propriétaire | inconnue | taux de la bêta peut-être (rendu JavaScript, non vérifié) | contrôle à la main |
| VMaNGOS, cMaNGOS classic-db | GPL-2.0, GPL-3.0 | Classic 1.12 | butin et positions Classic | écarté pour DJ1 (étude dédiée au plan de RX1) |
| Dungeon Codex, Lootified, forever-loot | GPL-2, GPL-3, aucune | oct. 2026 | taux Classic ou d'origine inconnue | écarter pour les taux |
| Dungeon Quest, Forever Dungeon Quests, Forever Dungeon Scout, WoW Forever Builds, Forever Instances (HandyNotes) | ARR, MIT, ARR, MIT, ARR | sept.-oct. 2026 | prérequis, donneurs, entrées | non installés : candidats seulement si un manque persiste (décision 131) |
| wowlevelling, wow-xp-calc | aucune | — | XP par heure supposée | écarter |

Non trouvé : taux de Forever mesurés et vérifiés ; durée de passage ou XP par heure mesurée sur Forever ; fil Reddit
utile ; XP de base officielle des quêtes de donjon.

## Constats (lecture seule du dépôt, du client et des addons, 2026-10-13)

### Addons installés (lus en local)
| Addon | Version | Licence | Donjons | Boss | Quêtes | Butin, taux | Particularités |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Naowh Forever, Dungeon Journal | 1.1.11, données 1.60.1.70338 (10 oct.) | tous droits réservés | 35 (13 nouveaux, dont 3 fermés sans instance), instanceID, plage, entrée `{uiMapID, x, y}` | par aile, npcID, rencontre ; `BossInfo` (nouveaux boss au niveau −1, inconnu) | 236 (`J.QuestData`), `QuestPrereqs` 139, `QuestMinLevel` 321, `NextPrereq()` (« à faire d'abord »), donneur et position, lieu de rendu | `chance` entière, origine déclarée (pas de taux sous 10 victoires) | SavedVariables : `journalRun` (1 passage RFC ≈ 2 360 s), `journalKills` (4 rencontres RFC, durées), `journalLoot` (5 objets) ; noms de joueurs dans `rolls`/`team` à ne jamais lire |
| Naowh Forever, InstanceTracker | 1.1.11 | idem | — | — | — | — | passage `{instance, mapID, entered, left, level, loot, xp, deaths, group}` ; **désactivé** (`enabled=false`) : à activer par l'utilisateur |
| Naowh Forever, BiS | 1.1.11 | idem | `sources` : 707 objets → « Boss · Donjon » | — | — | — | 28 spécialisations, un classement sans niveau (wowsrc) : T10a |
| FojjiCore DungeonJournal (+ Speedrun, BiS) | 3.3.5 | tous droits réservés, réutilisation interdite | 29 (jusqu'à Dalaran), plage | npcID, niveau `lv`, `odds` décimaux (origine non déclarée) | `QuestBook` 262, chaînes 239, `Access` (clés et chaînes d'accès, par exemple Dalaran Sewer Key) | taux divergents de Naowh | Speedrun : aucun temps de référence ; jamais lancé sur ce poste |
| ForeverDungeonJournal (Exehn) | 1.6.2 | aucune ; « ne donne pas de taux » | 14 (jusqu'à SM Library) | `BOSS_LEVELS` | 81, `liveXPFallback`, XP du texte, `QUEST_PREREQ_CHAINS` (obligatoires) | sans taux | **bogue du dépôt** : `read_fdj` ne lit que 3 des 14 donjons (premier littéral `FDJ.DB = ` seulement) |
| Forever Guide | 1.33.0 | aucune (module LFG MIT) | 35, plage, entrée (nouveaux sans entrée sauf Hall of Thanes) | `BOSS_INFO` (Classic ; nouveaux absents) | 550 (`ns.DQ`, sans XP) + 15 dans `DalaranData.lua` **non lues** par le dépôt | `p` Classic (ForeverChanges) ; nouveaux donjons sans taux | `TRASH_NPC` : 403 monstres non boss par donjon (Classic) ; SavedVariables : `bossloot` RFC |
| AtlasLoot Classic Forever | `Forever 1.60.1` | GPL-2 | `LevelRange {entrée, min, max}` ; Ruins {10,13,18} (copie probable de Hall of Thanes) | npcID (Classic seulement) | — | `droprate.lua` Classic (295 PNJ, aucun de Forever) | `forever.lua` mort (aucun `.toc`) |
| Forever Companion | 1.0.0 | aucune | 37, plages divergentes (WC 15-25, RFK 30-40…) | noms | 4 à 8 par nouveau donjon | `d` Classic ; nouveaux sans taux | |
| ZoneInfoForever (ex-Zone Level: Forever) | 1.9 | aucune | plages par zone, AreaTable ID des nouveaux (Dalaran 16560, Hall of Thanes 16919, Ruins 16611, Excavation 16732) | — | — | — | plages classiques de Classic, pas de Forever ; `docs/DATA_SOURCES.md` le dit encore « Zone Level: Forever installé » |
| AlexAtlasLoot | 1.7.0 | tous droits réservés, **copie interdite même partielle dans toute base** | nouveaux donjons vides | niveaux des boss = ceux de FDJ | 291 | aucun | écarté (licence explicite) |
| Questie | Forever-v27 | GPL-3 | `dungeons.lua` : entrées Classic, **aucun donjon de Forever** | — | — | — | |

Écarts déjà visibles : plage d'Excavation Site 24-29 (Naowh, ZoneInfo, Companion, AtlasLoot), 26-31 (Fojji, Forever
Guide, note officielle), 26-33 (FDJ) ; Hall of Thanes 13-20 (FDJ) contre 13-18 ; Ruins 15-22 (FDJ) ; boss
d'Excavation : 4 avec Highland Horror (Naowh, Speedrun, Forever Guide) contre 3 ; Dalaran : 9 boss chez Naowh (Mana
Wraith) contre 8 ; entrées de Dalaran, d'Excavation et de Ruins différentes d'un addon à l'autre (jusqu'à deux cartes
pour Ruins : 1458 et 1420) ; niveaux des nouveaux boss : FDJ, Fojji et AlexAtlasLoot identiques (copie, pas
recoupement), Naowh inconnu.

### Client
- Cache wago de 1.60.1.70338 : **aucune** table d'instance (`Map`, `LFGDungeons`, `JournalInstance`,
  `JournalEncounter`, `JournalEncounterItem`, `DungeonEncounter`, `AreaTable` absentes) ; `UiMap` sans carte de donjon.
  Présentes et utiles : `Item`, `ItemSparse` (niveau requis, classes permises, emplacement), `QuestXP`, `questcache.wdb`
  (quêtes vues), GameTable `xp` (`PerKill`).
- On ne sait pas encore si les nouveaux donjons et leur journal sont dans ces tables (DON9) : inventaire au bloc A.

### Code actuel
- `forever/sim/objectives.py` (T04d, I14) : regroupe les quêtes par le **texte** du champ `dungeon` (noms différents
  selon la source : « Hall of Thanes » / « The Hall of Thanes ») ; niveau des monstres = médiane des quêtes ; tous
  élites ; constantes globales `leveling.objectives` (`dungeon_kills` 40, `dungeon_travel_s` 600,
  `dungeon_group_speedup` 2,5, `dungeon_party` 5) ; aucun donjon sans quête ; aucune plage de niveau.
- `forever/pipeline/quest_sources.py` : `read_naowh_dj` ignore `levels`, `map`, `shareable`, `QuestChains.lua`,
  `QuestTurnIns` ; `read_forever_guide` ignore `DalaranData.lua` ; `read_fdj` bogue ci-dessus.
- `forever/addons.py` : AtlasLoot « lecteur en DJ1 », FojjiCore, ZoneInfoForever, ForeverCompanion « lecteur à
  venir ».
- ForeverLogger 0.5.0 : chaque gain d'XP porte `instance {inside, type, name, id}` et l'heure : un passage peut déjà
  être reconstruit des gains (début, fin, monstres tués) ; ni entrée ni sortie explicites, ni butin.
- Registre : I9, I10, I14 (`teste`), D8 (butin, `absent`), H1 (niveau des boss +3, `suppose`), H3 (scénarios de
  donjon, « affinés en DJ1 »).

## Décisions à écrire (étape 0, `docs/DECISIONS.md`)
- **265 — Choix du plan de DJ1** : réponses 2 à 5 ci-dessus ; la liste fusionnée des donjons vit dans le cache local
  (`<cache>/dungeons/`), rebâtie à la demande depuis les addons ; le dépôt garde ce qui vient du client
  (`dungeons.json` par version) et des agrégats (comptes, écarts) ; AlexAtlasLoot écarté (copie interdite), FojjiCore
  lu en local en recoupement seulement (décision 133) ; formule de Factoruide écrite dans `mechanics.json` avec sa
  source (MIT, chemin et date) ; marchands vers EC1 et réputation vers RP1.

## Choix de conception
1. **Clé d'un donjon = instanceID** (`Map.ID`, aussi dans Naowh `map` et Fojji `instance`) ; table de noms (alias des
   sources, « The », « Scarlet Monastery - Graveyard » / « : Graveyard ») pour rattacher ce qui n'a qu'un nom ; un nom
   non rattaché est signalé, jamais deviné. Les ailes de Scarlet Monastery sont des donjons distincts (rencontres et
   plages propres), avec l'instance commune.
2. **Fusion champ par champ**, comme `forever/quests.py` : chaque champ porte valeur, source, certitude et écarts.
   Ordre : relevé du joueur (`certain`) > client (`certain` pour ce qu'il dit : niveaux de `LFGDungeons`, rencontres de
   `DungeonEncounter`, objets du journal) > note officielle (`probable`) > Naowh > Fojji > FDJ > Forever Guide >
   Companion > AtlasLoot > ZoneInfo (`suppose`). Un champ où deux sources diffèrent liste les deux valeurs.
3. **Niveaux** : accès (minimum d'entrée) et recommandé (plage) séparés. Niveau des boss : relevé dans un journal de
   combat (bloc avancé, H1) > client > addons ; une valeur copiée (FDJ = Fojji = Alex) compte pour une seule source.
4. **Quêtes de donjon** : rattachées par instanceID au livre de quêtes de T04d (`forever/quests.py`), qui garde l'XP
   (client si vue, sinon addon `suppose`). « À faire d'abord » : prérequis obligatoires (Naowh `QuestPrereqs`, FDJ
   `QUEST_PREREQ_CHAINS`, Fojji `QuestBook.req`) et clés d'accès (Fojji `Access`), ordonnés par `order_quests` ;
   niveau minimum de prise (`QuestMinLevel`) distinct du niveau de la quête.
5. **Butin** : objets par boss (client `JournalEncounterItem` d'abord, sinon addons) ; taux selon la réponse 5 ;
   « pour moi » calculé depuis `ItemSparse` (classes permises, niveau requis) et la maîtrise d'armure et d'armes de la
   classe (règle Classic `suppose` si le client ne la donne pas) ; `usable`, `level_ok`, `upgrade` non calculé
   (T10a). Taux absent : `null`, rendu « inconnu ».
6. **Passage d'un donjon** (registre I16, nouveau) : durée et monstres par ordre — passages relevés (ForeverLogger,
   Naowh `journalRun`/InstanceTracker ; médiane si plusieurs, nombre de passages rendu) > comptes de monstres d'un
   addon (Forever Guide `TRASH_NPC` + boss) > formule de Factoruide (`mechanics.json` `dungeon.run_defaults`, valeurs
   de Factoruide recopiées avec leur source). Temps par monstre de T04d **non** utilisé pour un passage en groupe
   (incohérent avec la mesure). Trajet aller : distance de la zone de quêtes à l'entrée, sinon
   `leveling.objectives.dungeon_travel_s` ; le gain de vitesse du groupe ne s'applique plus qu'au repli par temps par
   monstre.
7. **Rentabilité** (I14 étendue) : premier passage = XP des monstres (élites, bonus de donjon, groupe, bonus de T04f)
   + XP de toutes les quêtes prenables du donjon (prérequis manquants listés, et leur coût en temps s'ils sont dehors)
   sur prise des quêtes + trajet + passage + retour ; passages suivants = monstres seuls ; comparaison avec la
   meilleure zone du même niveau (déjà dans `objectives`) ; phrase de conseil construite à partir des chiffres.
8. **Niveau de placement** (I17, nouveau, pour RX1) : pour chaque donjon, XP du premier passage calculée à chaque
   niveau de sa plage où ses quêtes ne sont pas grises ; le niveau retenu maximise l'XP du premier passage **divisée
   par l'XP du niveau** (part de niveau gagnée par heure), à égalité le plus bas ; on rend aussi la fenêtre où le
   premier passage bat la meilleure zone. Fonction pure dans `forever/engine/`.
9. **Aucun chiffre de jeu dans le code** : constantes dans `mechanics.json` ; tests sur fixtures.

## Étapes et blocs (commits `DJ1: tests (bloc X)` puis `DJ1: bloc X vert`)

### Étape 0 — Préalables
Décision 265 ; `docs/DATA_SOURCES.md` à jour (versions relevées, ZoneInfoForever, Naowh DJ et Fojji comme sources de
donjon, AlexAtlasLoot écarté, durées de speedrun = bornes basses) ; ligne DJ1 et section DJ1 de la ROADMAP (marchands
→ EC1, réputation → RP1, accord de l'utilisateur) ; branche `dj1`.

### Bloc A — Client : tables d'instances et `dungeons.json`
`forever/pipeline/tables.py` (colonnes des 7 tables), `forever fetch`/`forever update` (liste des tables), faux wago des
tests de mise à jour (`wago_routes`, mémoire « clone de mise à jour ») ; `forever/pipeline/dungeons_client.py` décode
`dungeons.json` : instances à 5 (`Map.InstanceType`), plages `LFGDungeons` (min, max, cible), rencontres
`DungeonEncounter` (ordre, npc via `JournalEncounter` si présent), objets du journal par rencontre ; nouveau fichier
dans `DECODED_FILES`, `sources.json`, `origins.json`, règles dans `decode_rules.json` (décision 263), comptes de
`test_data_import.py`, `test_manifest.py`, `test_decode_version.py`. Inventaire réel en début de bloc : ce que les
tables disent des nouveaux donjons est écrit dans le résumé du bloc (DON9). Installation par `forever install`
(révision 6 de 1.60.1.70338).

### Bloc B — Lecteurs des addons (`forever/pipeline/dungeon_sources.py`)
Naowh DJ (donjons, ailes, boss, `chance`, entrées, `BossInfo`, `QuestPrereqs`, `QuestMinLevel`, `QuestTurnIns`),
SavedVariables de Naowh (`journalRun`, `journalKills`, `journalLoot`, `instanceTracker.runs` ; champs de noms de
joueurs jamais lus), Fojji DJ (`Dungeons`, `odds`, `Access`, `QuestBook`), FDJ (les 14 donjons, `BOSS_LEVELS`,
`DungeonEntrances`, `QUEST_PREREQ_CHAINS`), Forever Guide (`DUNGEONS`, `LOOT`, `TRASH_NPC`, `DalaranData.lua`),
AtlasLoot (`LevelRange`, objets, `droprate` Classic), Forever Companion, ZoneInfoForever. Correction de `read_fdj`
(tous les `DB["…"] =`) et de `read_forever_guide` (`DalaranData.lua`) dans `quest_sources.py`. Branchement dans
`forever addons status` (`DATA_ADDONS` : lecteur, agrégats dépendants, action).

### Bloc C — Fusion : livre des donjons (`forever/dungeons.py`)
`build_dungeons` (cache `<cache>/dungeons/`, empreinte des fichiers lus et des données), fusion champ par champ,
alias de noms, rattachement des quêtes de T04d par instanceID, « à faire d'abord », butin et taux, niveau des boss
relevé dans les journaux (H12) ; agrégats du dépôt : `docs/research/donjons-forever.md` (comptes par donjon et par
source, écarts).

### Bloc D — ForeverLogger 0.6.0 (passages et butin)
Schéma 4 : `runs` (entrée et sortie d'instance par `PLAYER_ENTERING_WORLD`/`ZONE_CHANGED_NEW_AREA` et
`GetInstanceInfo` sous `pcall` : instance, difficulté, niveau, taille du groupe, heures), `ENCOUNTER_END` (rencontre,
succès, heure), `loot` (`LOOT_OPENED` : objets, `GetLootSourceInfo` sous `pcall`, GUID de la source → PNJ). Aucun
abonnement au journal de combat, aucune fonction d'action ; `check_addon.py` et `test_addon_rules.py` verts ; client
simulé (lupa) ; lecture dans `forever/pipeline/addon_sv.py` ; `docs/ADDON.md` (relevé facultatif, décision 247) ;
conseil à l'utilisateur d'activer InstanceTracker de Naowh.

### Bloc E — Passage et rentabilité (`forever/engine/dungeon.py`, `forever/sim/objectives.py`)
`run_model` (relevé > comptes d'addon > formule), `first_pass`/`repeat` avec bonus de T04f, `placement_level` (I17),
`objectives` refondu sur le livre des donjons (donjons sans quête rendus en passages répétés seulement) ; bouton
Leveling (`forever/bridge/plans.py`, `OBJECTIVES_READ`) : « fais X une fois avec ses quêtes au niveau N » ou
« continue dehors ».

### Bloc F — Consultation : CLI, MCP, skill
`forever dungeon list [--level N] [--faction]`, `forever dungeon info <donjon> [--class --level]`,
`forever dungeon item <objet>` ; `forever_lookup(kind="dungeons" | "dungeon" | "dungeon_item")` ; profil actif pour
« ma classe et mon niveau » (sinon arguments) ; skill `plugin/skills/forever-donjons/SKILL.md` (décision 115) et routeur
(questions « où trouver tel objet », « quel donjon à mon niveau », « quêtes à prendre avant X »).

### Bloc G — Préparation de RX1
`forever/route.py` : `dungeon_steps(book, dungeon, *, faction, level)` → `RouteStep` (prérequis à faire d'abord,
quêtes à prendre avec donneur et position, entrée, rendus) ; `dungeon_placements(deps, *, class_name, faction,
levels)` → liste `(donjon, niveau de placement, fenêtre, étapes, XP, minutes)` ; aucune livraison (RX1).

## Fichiers
- Nouveaux : `forever/pipeline/dungeons_client.py`, `forever/pipeline/dungeon_sources.py`, `forever/dungeons.py`,
  `forever/engine/dungeon.py`, `forever/data/1.60.1.70338/dungeons.json` (révision installée),
  `plugin/skills/forever-donjons/SKILL.md`, `docs/research/donjons-forever.md`, fixtures `tests/fixtures/addons/`
  (Naowh DJ et ses SavedVariables, Fojji, FDJ multi-littéraux, Forever Guide avec `DalaranData.lua`, AtlasLoot,
  Companion, ZoneInfo : extraits réduits et anonymisés), `tests/fixtures/wago/` (7 tables réduites),
  `tests/fixtures/addon/` (SavedVariables de ForeverLogger schéma 4).
- Modifiés : `forever/pipeline/tables.py`, `fetch.py`, `decode.py`, `quest_sources.py`, `addon_sv.py`,
  `forever/addons.py`, `forever/sim/objectives.py`, `forever/route.py`, `forever/cli.py`, `forever/mcp_server.py`,
  `forever/lookup.py`, `forever/bridge/plans.py`, `addon/ForeverLogger/*`, `forever/data/1.60.1.70338/mechanics.json`
  (`dungeon.run_defaults`, `dungeon.placement`), `decode_rules.json`, `origins.json`, `sources.json`,
  `docs/MECHANICS_REGISTRY.yaml`, `docs/OPEN_QUESTIONS.md`, `docs/DATA_SOURCES.md`, `docs/ADDON.md`,
  `docs/ARCHITECTURE.md`, `docs/USAGE.md` (s'il existe la section CLI), `docs/ROADMAP.md`, `docs/DECISIONS.md`,
  `plugin/skills/forever-router/SKILL.md`, `plugin/skills/forever-leveling/SKILL.md`.

## Interfaces (signatures indicatives, forme définitive au bloc)
```
# forever/pipeline/dungeons_client.py
decode_dungeons(tables, version) -> dict   # {"instances": {id: {name, map, levels{min,max,target}, encounters[{id, name,
                                           #   order, npc}], items{encounter_id: [item_id]}}}, "source", "certainty"}
# forever/pipeline/dungeon_sources.py
SourceDungeons(info: SourceInfo, dungeons: dict[str, Facts])   # clé : instanceID en texte, sinon "name:<nom>"
read_naowh_journal(addons_dir), read_naowh_runs(wtf_dir), read_fojji(addons_dir), read_fdj_dungeons(addons_dir),
read_guide_dungeons(addons_dir), read_atlasloot(addons_dir), read_companion(addons_dir), read_zoneinfo(addons_dir)
# forever/dungeons.py
build_dungeons(deps, *, wow_dir=None, rebuild=False) -> DungeonBook(dungeons: dict[int, Dungeon], aliases, sources,
                                                                    notes, provenance)
Dungeon(id, name, new, closed, levels, entrance, bosses[Boss(npc, name, level, order, loot[Loot(item, rate,
        rate_source, classic)])], quests[int], first_steps[int], access, field_sources, discrepancies)
lookup_dungeons(deps, *, level=None, faction=None) ; dungeon_info(deps, name_or_id, *, class_name=None, level=None)
where_item(deps, item_id_or_name) -> list[{dungeon, boss, rate, source, version}]
# forever/engine/dungeon.py  (registre I14, I16, I17)
run_model(gd, dungeon_id, mob_level, measured: Sequence[Run]) -> RunModel(minutes, kills, source, certainty, samples)
first_pass(gd, *, level, run, quests_xp, kill_xp, travel_s, quest_overhead_s) -> Objective
placement_level(gd, levels: range, first_pass_xp: Callable[[int], float]) -> Placement(level, window, xp_share_h)
# forever/route.py
dungeon_steps(book, dungeon, *, faction, level) -> list[RouteStep] ; dungeon_placements(deps, *, class_name, faction,
                                                                                           levels) -> list[Placement]
```

## Tests attendus (valeurs lues dans les fixtures ou les données ; aucun chiffre de jeu écrit dans un test)
Bloc A (`tests/unit/test_dungeons_client.py`) :
- `test_five_man_instances_are_kept` : fixture `Map` à 3 lignes (un donjon à 5, un raid, un champ de bataille) → une
  seule instance ;
- `test_lfg_levels_are_read` : min, max et cible de la ligne `LFGDungeons` de la fixture ;
- `test_encounters_are_ordered` : ordre des rencontres de `DungeonEncounter` de la fixture ;
- `test_journal_items_by_encounter` ; `test_missing_tables_give_a_note` (candidate sans les tables : note, pas
  d'erreur) ; comptes mis à jour de `test_data_import.py`, `test_manifest.py`, `test_decode_version.py` ;
  `test_fetch_lists_instance_tables`.
Bloc B (`tests/unit/test_dungeon_sources.py`) :
- `test_fdj_reads_every_dungeon` : fixture FDJ à 3 littéraux (`FDJ.DB = {…}`, `DB["X"] = {…}`, `FDJ.DB["Y"] = {…}`) →
  3 donjons (rouge aujourd'hui : 1) ; même correction côté quêtes (`test_quest_sources.py::test_fdj_quests_of_every_dungeon`) ;
- `test_guide_reads_dalaran_data` ; `test_naowh_prereqs_and_min_level` ; `test_naowh_rates_are_percent` ;
- `test_naowh_runs_skip_player_names` (la fixture contient des noms dans `rolls`/`team` : absents de la sortie) ;
- `test_fojji_access_keys` ; `test_atlasloot_rates_marked_classic` ; `test_alexatlasloot_is_not_read` ;
- `test_addons_status_lists_dungeon_readers` (AtlasLoot, FDJ, Naowh, Fojji, Companion, ZoneInfo : lecteur nommé).
Bloc C (`tests/unit/test_dungeons.py`) :
- `test_aliases_join_on_instance` (« Hall of Thanes » et « The Hall of Thanes » → une seule entrée) ;
- `test_level_discrepancy_is_listed` (plages 24-29 et 26-31 dans deux fixtures : les deux rendues, source de chacune) ;
- `test_copied_boss_levels_count_once` ; `test_logged_boss_level_wins` (journal de combat de fixture : niveau
  relevé, `certain`) ;
- `test_rate_order` (Naowh retenu, Fojji en écart, Classic seulement pour un boss inchangé, étiqueté) ;
- `test_unknown_rate_is_null` ; `test_quests_attached_with_xp_source` (XP du client pour une quête vue de la fixture
  `questcache`, addon sinon) ; `test_first_steps_are_ordered` (chaîne de prérequis de la fixture dans l'ordre) ;
- `test_usable_for_class_and_level` (objet de fixture `ItemSparse` réservé à une classe, niveau requis).
Bloc D (`tests/unit/test_logger_runs.py`, `tests/unit/test_addon_rules.py`) :
- `test_run_entry_and_exit_recorded` (lupa : entrée puis sortie simulées → un passage avec instance et durée) ;
- `test_loot_records_source_npc` ; `test_encounter_end_recorded` ; `test_api_errors_are_counted` ;
- `test_runs_are_read_from_saved_variables` (fixture schéma 4) ; règles de l'addon vertes.
Bloc E (`tests/unit/test_engine_dungeon.py`, `tests/unit/test_sim_objectives.py`) :
- `test_measured_run_wins` (deux passages relevés de fixture → médiane, `certain`, `samples` 2) ;
- `test_addon_kill_count_used_when_no_run` ;
- `test_factoruide_formula_bounds` (niveaux de monstres choisis pour toucher la borne basse, le milieu et la borne
  haute ; attendus calculés avec les valeurs de `mechanics.json` `dungeon.run_defaults`) ;
- `test_first_pass_beats_repeat` ; `test_dungeon_without_quests_has_repeat_only` ;
- `test_placement_maximises_level_share` (fonction d'XP de test croissante puis grise : niveau attendu calculé par la
  règle sur les données) ; `test_placement_tie_takes_lowest` ;
- `test_objectives_group_by_instance` (rouge aujourd'hui : regroupement par texte) ;
- `test_leveling_button_names_placement`.
Bloc F (`tests/unit/test_cli_dungeon.py`, `tests/unit/test_mcp_dungeons.py`) :
- `test_dungeon_list_by_level` ; `test_dungeon_info_has_provenance_and_addon_versions` ;
  `test_dungeon_item_where` ; `test_unknown_rate_shown_as_unknown` ; `test_lookup_dungeons_kind` (import de `mcp`
  dans le module, piège T06b) ; `test_router_mentions_dungeons` (structure du plugin).
Bloc G (`tests/unit/test_route_dungeons.py`) :
- `test_steps_start_with_prerequisites` ; `test_steps_have_giver_positions` ;
  `test_placements_cover_each_open_dungeon` (donjons fermés exclus).
Le registre n'a plus de total figé (décision 214) : rien à compter à la main.

## Registre (`docs/MECHANICS_REGISTRY.yaml`)
- **I14** (rentabilité) : sources et tests étendus (passage par donjon, regroupement par instance).
- **I16** (nouvelle, optimisation) : durée et monstres d'un passage de donjon (relevé, addon, formule de Factoruide),
  `suppose` tant qu'aucun passage n'est relevé.
- **I17** (nouvelle, optimisation) : niveau de placement d'un donjon dans une route, `suppose`.
- **H12** (nouvelle, rencontre) : niveau des boss de donjon de Forever (journal > client > addons), certitude par
  boss.
- **D8** (butin) : note mise à jour (butin relevé par ForeverLogger 0.6.0), statut inchangé (aucun effet de calcul).
- **H3** : note « scénarios de donjon » inchangés dans DJ1 (affinés par les tranches de classe), angle mort dit.

## Questions ouvertes (`docs/OPEN_QUESTIONS.md`)
- **DON9** : mise à jour (tables d'instances inventoriées au bloc A).
- **DON17** — Taux de butin de Forever : Naowh et Fojji divergent sur les nouveaux boss ; lequel est juste ? Test :
  butin relevé par ForeverLogger 0.6.0 sur assez de passages (taux = lâchés ÷ victoires). Priorité : basse.
- **DON18** — Plages, boss et entrées des nouveaux donjons divergents entre addons (Excavation Site, Ruins of
  Lordaeron, Dalaran, Highland Horror, Mana Wraith) : le client les tranche-t-il ? Test : tables du bloc A, sinon
  passage en jeu. Priorité : moyenne.
- **LVL15** — Durée réelle d'un passage de donjon à Forever (groupe ordinaire), et écart à la formule de Factoruide ?
  Test : passages relevés par ForeverLogger 0.6.0 ou InstanceTracker de Naowh. Priorité : moyenne. Registre I16.
- **LVL16** — L'XP d'une quête de donjon lue dans le client (`questcache.wdb`) inclut-elle le bonus de donjon réduit
  de moitié ? Test : `xpReward` d'une quête de donjon rendue, comparé par `forever xp check`. Priorité : moyenne.
  Registre I9.

## Hors périmètre
Stratégies de boss recopiées ; valeur d'un objet pour un personnage et « est-ce une amélioration » (T10a) ; listes BiS
(T10a) ; raids (T09 à T11) ; marchands (EC1) et réputation (RP1) dans ForeverLogger ; livraison d'une route dans
RestedXP et recherche de route (RX1) ; VMaNGOS et Factoruide comme moteur ou source de données (étude au plan de
RX1) ; relecture automatique à chaque version d'un addon (T08) ; scénarios de combat de donjon des builds (tranches de
classe).

## Risques
- **Tables du client sans les nouveaux donjons** ou journal vide (plausible sur la bêta) : le livre reste juste avec
  les addons (`suppose`), la note le dit ; aucun blocage.
- **Licences** : Naowh et Fojji « tous droits réservés » : lecture locale seulement, cache local, agrégats seuls dans le
  dépôt (décision 133) ; AlexAtlasLoot écarté.
- **Correction de `read_fdj`** : plus de quêtes dans le livre de T04d → objectifs de T04d changés ; tests de T04d
  verrouillés à vérifier avant (demande de correction si une valeur bouge, `tasks/DJ1-corrections.md`).
- **Formule de Factoruide** non sourcée par son auteur : `suppose` explicite ; le classement donjon contre zone peut
  en dépendre plus que de l'XP (la sortie le dit, comme T04d).
- **Données de la bêta** : tout est à relire sur le client de la sortie (LN1).
- **Temps** : 8 jours avant la fin de la bêta ; F et G peuvent glisser après E sans gêner RX1 au-delà de
  `dungeon_placements` (déplaçable en tête de G si besoin).

## Critères de fin (DJ1)
- `forever dungeon list --level N` et `forever dungeon info` sur les fixtures rendent niveaux, entrée, boss, quêtes
  (prérequis, donneur, XP et sa source) et butin avec provenance (versions des addons comprises) ; un taux absent est
  « inconnu » ; les écarts entre sources sont listés.
- `forever dungeon item <objet>` rend boss, donjon, taux, source et version.
- Le niveau d'un boss relevé dans une fixture de journal l'emporte et passe `certain` ; un passage ou un butin relevé
  par ForeverLogger 0.6.0 l'emporte sur l'addon, `certain`, écart signalé.
- `forever addons status` nomme un lecteur pour AtlasLoot, FDJ, Naowh, Fojji, Companion et ZoneInfo.
- Objectifs et bouton Leveling : premier passage et passages suivants par donjon (clé instance), niveau de placement,
  comparaison avec la meilleure zone, pour toutes les classes.
- `dungeon_placements` rend pour chaque donjon ouvert son niveau de placement et ses étapes (RX1).
- `test_addon_rules.py` vert ; registre et questions ouvertes à jour ; `uv run tasks.py verify` vert ; CI verte sous
  Ubuntu et Windows ; `uv run tasks.py e2e` vert (tables ajoutées à `forever update`).
