# T04d — Quêtes de Forever et modèle d'XP de Forever : plan

> Plan rédigé le 2026-10-13 (`/tranche T04d`), sans code. Exécution : `/tranche T04d` dans une nouvelle session, sur la
> branche `t04d`, un cycle rouge → vert par bloc. **Échéance dure** : ForeverLogger mis à jour et sonde en jeu I prête
> (bloc A) avant la fin de la bêta, le **2026-10-21** ; le bloc A passe donc en premier, le reste se fait hors jeu.

## Demande de l'utilisateur (2026-10-13)
Utile à toutes les classes, avec une sonde en jeu avant le 21 octobre :
1. **Quêtes** : liste des quêtes de Forever par zone et par niveau (nouvelles, retouchées, retirées), prérequis, XP,
   récompenses, à partir des addons installés lus en local (Questie, Naowh Forever : Completo et Dungeon Journal,
   Forever Guide, GearQuest) ; seuls nos agrégats entrent dans le dépôt (décision 133) ; écarts entre sources
   signalés, jamais devinés.
2. **Modèle d'XP** : XP des quêtes selon l'écart de niveau, XP des monstres (donjon à environ +20 %, groupe calculé
   sur le niveau de chaque joueur : règles de la note du 08/10 déjà écrites en `probable`), XP de repos ; chaque règle
   avec sa source et sa certitude.
3. **Leveling** : XP par heure par zone et par tranche de niveaux, quêtes et monstres combinés, pour toutes les
   classes (temps par monstre calculé pour les classes à moteur, estimé et marqué comme tel pour les autres) ; le
   bouton Leveling et `forever_build` s'en servent.
4. **Mesure** : modèle vérifié sur les journaux et ForeverLogger (relevé de l'XP de chaque quête rendue et de chaque
   monstre, ajouté s'il manque) ; sonde en jeu courte pour le Mage et le Chasseur.
5. **Préparer RX1** : données de quêtes utilisables pour des feuilles de route RestedXP (ordre, prérequis, positions
   des PNJ).

## Réponses de l'utilisateur (2026-10-13)
1. **Réseau** : la table `QuestXP` est téléchargée de wago.tools par la voie existante de `forever fetch` et
   `forever update`, et décodée dans T04d. `QuestLine`, `QuestLineXQuest` et `QuestPOIPoint` sont **téléchargées une
   fois, pas décodées** : le résumé de fin de tranche dit seulement combien de leurs lignes concernent des quêtes de
   Forever (chaînes et positions réellement présentes dans le client) ; leur décodage se décidera au plan de RX1.
2. **Stockage** : la liste fusionnée des quêtes vit dans le **cache local** (`<cache>/quests/`), rebâtie à la demande
   depuis les addons installés ; le dépôt ne garde que ce qui vient du client (XP des quêtes par `questcache.wdb` et
   `QuestXP`) et des agrégats (comptes par zone, écarts entre sources). RX1 exportera depuis ce cache.
3. **Classes sans moteur** : temps par monstre mesuré dans mes relevés pour la classe (journaux, ForeverLogger),
   sinon hypothèse déclarée dans `forever/data/` avec sa source, `suppose` et « estimé ». Aucun moteur de classe
   ajouté.
4. **Sonde** : solo, 20 à 30 minutes par personnage ; en plus, avec le Chasseur de niveau 15 : prendre les quêtes de
   Ragefire Chasm avant d'entrer, tuer quelques monstres du donjon, rendre les quêtes, pour mesurer le bonus d'environ
   20 % des monstres de donjon (LVL5, comparé à niveau égal avec des monstres du dehors) et l'XP réelle de ses quêtes ;
   la procédure nomme les quêtes à prendre et les monstres à tuer, dedans et dehors. L'XP en groupe (LVL4) seulement
   si le joueur se trouve en groupe, sinon elle reste ouverte.
5. **Ajout : rentabilité d'un donjon**. Elle vient surtout de ses quêtes, qui rapportent beaucoup mais une seule fois.
   Le modèle distingue le **premier passage avec les quêtes** (XP des monstres avec le bonus, plus l'XP de toutes les
   quêtes du donjon, sur le temps total : prise des quêtes, trajet, donjon, retour pour les rendre) et les **passages
   suivants** (XP des monstres seule). Quêtes de chaque donjon et prérequis : Naowh Forever (Dungeon Journal) et
   Forever Guide, avec l'XP réelle de `QuestXP` quand je les ai vues. Le bouton Leveling dit quand un donjon vaut le
   coup (« fais Ragefire Chasm une fois avec ses quêtes : environ N XP en M minutes ») et quand il vaut mieux
   continuer dehors.

## Constats (relevés le 2026-10-13, lecture seule du dépôt, du client et des addons)

### Code actuel
- **XP d'un monstre** : `forever/engine/monsters.py:105` `mob_xp(gd, level)` = `xp_base + xp_per_level × niveau`
  (`mechanics.json` `leveling.mob_xp`, `{"base":45,"per_level":5}`, `suppose`, registre I6), monstre normal de même
  niveau, sans écart de niveau, sans élite, sans repos. Appelants : `sim/leveling_mc.py:555`,
  `sim/leveling_analytic.py:166,191`, `optimize/leveling.py:112` (`level_weight = xp_to_next / mob_xp`, donc le
  chemin des talents de `forever_build` en contexte leveling dépend de l'XP d'un monstre).
- `leveling.json` `mob_xp` (règles Classic d'écart de niveau, `zero_difference`, repos ×2) : texte écrit à la main,
  **lu par aucun code**.
- **Repos** : `character_scaling.json` `rested[]` (table `Exhaustion` du client : 5 paliers, `xp`, `factor`,
  `outdoor_hours`, `inn_hours`, `threshold`), décodé, lu par aucun moteur (note « non modélisés (D7) »).
- **GameTable `xp`** (décodée pour `Total`) : sa colonne `PerKill` n'est pas décodée.
- `mechanics.json` : `xp.dungeon_kill_bonus` (0,2, `approximate`, `probable`, I10) et `xp.group_level_basis`
  (`individual`, `probable`, I11), écrits à la main (révision 2 de 1.60.1.70291), lus par aucun code.
- **`forever sim leveling` / `forever_sim_leveling`** (`forever/leveling.py:210`) : Mage seulement (rotations
  givre, feu, arcanes ; aucun paramètre de classe). Sortie : `monte_carlo`, `analytic`, `xp_h`, `mob_hp`,
  `provenance`.
- **`forever lookup zones`** (`forever/pipeline/questie.py`, T04c) : base Classic de Questie (`classicQuestDB`,
  `classicNpcDB`, `xpDB-classic`, `dungeons.lua`, `lookupZones.lua`) **sans ses corrections** (`classicQuestFixes.lua`,
  environ 2 010 entrées) ni `QuestieForeverDB` ; `CLASS_IDS = {"mage": 8}` seulement.
- **Bouton Leveling** (`forever/bridge/plans.py:95`) : `forever_lookup(kind="zones")` pour toutes les classes ; Mage
  en plus : prochain talent et `forever_sim_leveling` ; autres classes : build populaire et « XP par heure pas encore
  calculée » (décision 242).
- **Lecteurs d'addons** : Questie, Auctionator, ForeverBestiary, TalentsForeverBook, ForeverLogger ; aucun lecteur
  pour Naowh Forever, Forever Guide, ForeverDungeonJournal (FDJ), GearQuestForever (`forever/addons.py` les liste
  sans lecteur). Agrégats de Questie dans `<cache>/addons/state.json`.
- **Aucune table de quêtes** dans `forever/data/` ni dans `tables.py` ; aucun fichier de quêtes dans
  `DECODED_FILES` / `INHERITED_FILES`.

### ForeverLogger (0.3.0) et relevés existants
- Écoute `CHAT_MSG_COMBAT_XP_GAIN` : entrée `{level, text, time, localtime}` (texte brut, montant non extrait) ;
  `PLAYER_LEVEL_UP` (instantané). **Pas** de `QUEST_TURNED_IN`, `QUEST_ACCEPTED`, `PLAYER_XP_UPDATE`, `UnitXP`,
  `GetXPExhaustion`, niveau du monstre, instance ou groupe.
- Lecteur Python : `forever/pipeline/addon_sv.py` (`XpGain`), **lu par aucun code** hors de son test.
- SavedVariable du client (645 Ko, 12 personnages) : **2 714 gains d'XP déjà relevés** (« <monstre> dies, you gain N
  experience. » ×1 738, la même avec « (+N group bonus) » ×660, « You gain N experience. » ×314, une trentaine en
  français) ; Mage principal : 494 gains, niveaux 15 à 19 ; deux Chasseurs : 678 (1 à 15) et 1 000 (1 à 21). Aucun
  bonus de repos dans les textes (à expliquer : pas de repos, ou forme du texte différente). Sans identifiant de quête
  ni niveau de monstre : utilisables pour la cadence des monstres et, joints aux journaux ou à Questie, pour l'XP par
  monstre.
- Aucun test n'exécute `ForeverLogger.lua` sous lupa (le client simulé `tests/fixtures/bridge/wow_stub.lua` sert à
  ForeverBridge).

### Client : `questcache.wdb` (lu en local)
- `Cache/WDB/enUS/questcache.wdb` (209 Ko, réécrit le 2026-10-13 ; le cache repart de zéro depuis la remise à zéro du
  PC le 2026-10-12) : signature `WQST`, langue `enUS`, puis un enregistrement par quête **vue** par le client.
  Premier enregistrement lu à la main : quête 479, type 2, niveau 16, niveau requis 10, zone 130, quête suivante
  480, **difficulté d'XP 5, multiplicateur d'XP 1,0**, argent 800 (difficulté 5, multiplicateur 1,0). Disposition
  des champs à établir sur plusieurs enregistrements (puis `probable`, `certain` après recoupement par `xpReward` en
  jeu).
- XP d'une quête vue = `QuestXP[niveau de la quête].Difficulty[difficulté]` × multiplicateur, puis règle d'écart de
  niveau : la table `QuestXP` manque (réponse 1). Rapports d'XP de FDJ sur Questie pour 49 quêtes Classic : 24 à
  environ 1,0, les autres de 0,74 à 7,5 à niveau égal (inventaire des addons) : un réglage par quête, cohérent avec
  ce multiplicateur.

### Addons installés (lecture locale)
| Addon (version) | Quêtes | Apporte | Manque | Marqueur Forever |
| --- | --- | --- | --- | --- |
| Questie 11.38.0 Forever-v27 | 4 244 (Classic Era) ; corrections Classic et SoD ; `QuestieForeverDB` (SavedVariable, environ 434 quêtes apprises en jeu, 91 d'ID ≥ 90000) | niveau, niveau requis, races, classes, donneur et rendeur (ID de PNJ), positions des PNJ (`spawns` par zone AreaTable), prérequis (`preQuestGroup`, `preQuestSingle`), chaîne (`nextQuestInChain`), exclusions, objectifs (monstres et objets), XP Classic (`xpDB-classic`, 3 494) | XP de Forever ; corrections Forever | aucun (nouvelle = absente de la base) |
| Naowh Forever 1.1.11, Completo (`NaowhForever_Discovery/QuestList/Data/Quests.lua`) | 2 917 (385 d'ID ≥ 90000), 47 zones, 456 chaînes | niveau, niveau requis, camp, races, classes, uiMapID, x, y du donneur (nom), `Requires` (au moins un parmi), `Chains` ordonnées ; tiré de Wowhead Forever | XP, rendeur, ID de PNJ | aucun (ID seulement) |
| Naowh Forever, Journeys (`QuestSpots.lua`) | 2 857 | point de rendu et camps d'objectifs (uiMapID, x, y) | noms | — |
| Naowh Forever, Dungeon Journal (build 70338) | 236 sur 35 donjons (33 d'ID ≥ 90000) | donjon, plage de niveau, niveau (un seul champ), camp, partage, donneur (texte et position), étapes, prérequis, `BossQuests`, `BiSQuests` | XP | aucun |
| Forever Guide 1.33.0 (`DungeonData.lua`) | 561 quêtes de donjon (32 `new=true`) | niveau `lv` et requis `rl`, donneur et rendeur (ID de PNJ et position), prérequis `ps`, suite `nx`, récompenses `rw` (argent, au choix, réputation, `fv` = publiée pour Forever) ; 259 PNJ | XP | `new=true`, `fv` |
| ForeverDungeonJournal 1.6.2 | 103 quêtes de donjon (34 d'ID ≥ 90000) | **XP** (`FOREVER_QUEST_XP_FALLBACK` « client-cache values », `FOREVER_QUEST_BASE_XP`, corrections `QuestUpdates.lua`, `correctedBFDXP`), récompenses, niveau et requis | positions (56 seulement) | aucun |
| GearQuestForever 0.5.4-beta | 882 noms de quête, **sans ID** | récompenses par objet (`questName`, `zone`, `reqLevel` de l'objet), positions par objet | ID de quête, XP | `foreverNew` (objets) |
| RXPGuides v4.11.23 | — | **réinstallé** (fichiers du 11/10) alors que `docs/DATA_SOURCES.md` le dit supprimé ; reste **exclu comme source** (CC BY-NC-SA 4.0, guide payant). Format utile à RX1 seulement : `RegisterGuide`, `.goto uiMapID/étage,x,y` ou `Zone,x,y`, `.accept`, `.turnin`, `.complete`, `.xp` | — | `#forever` |

- **Aucune source ne marque une quête « retirée »** : « absente des sources Forever » se déduit (quête de la base
  Classic, de sa zone, absente de Completo, tiré de Wowhead Forever), jamais « retirée » de façon certaine.
- **Écart déjà visible** (exemple de test) : Slaying the Beast (5761) : niveau 9 dans le Dungeon Journal de Naowh,
  `lv=16` et `rl=9` dans Forever Guide (le 9 de Naowh est le niveau requis).
- **Écart interne à FDJ** : An Ancient Grudge (96395) : `liveXPFallback` 1 050 contre « 3,570 XP » dans le texte.
- `SleepingBagData.lua` cité par la ROADMAP s'appelle `NaowhForever_Discovery/Data/SleepingBag.lua` (T04f).
- **Ragefire Chasm** (Horde, 13 à 18 selon Naowh) : Slaying the Beast (5761, Neeru Fireblade, Orgrimmar, boss
  Taragaman), Hidden Enemies (5728, Thrall, Orgrimmar, chaîne de 3 quêtes), Testing an Enemy's Strength (5723,
  Rahauro, Thunder Bluff : 8 Ragefire Troggs et 8 Ragefire Shamans), Searching for the Lost Satchel (5722 → 5724,
  Rahauro), The Power to Destroy... (5725, Varimathras, Undercity).

## Décisions à écrire (étape 0, `docs/DECISIONS.md`)
- **245** : T04d avancée avant LN1, exécutée pendant la bêta pour que la sonde I se joue avant le 21 octobre
  (demande du 2026-10-13) ; LN1 garde sa place en tête de la fenêtre sans jeu, T04d n'y est plus.
- **246** : choix de ce plan (réponses 1 à 5 ci-dessus) : `QuestXP` téléchargée et décodée, trois tables de chaînes
  téléchargées une fois et comptées seulement ; liste fusionnée dans le cache, jamais dans le dépôt ; données
  client des quêtes vues dans le dépôt ; temps par monstre des classes sans moteur mesuré sinon estimé ; sonde I solo
  plus Ragefire Chasm ; donjon au premier passage avec quêtes et aux passages suivants.
- `docs/DATA_SOURCES.md` : RXPGuides présent (v4.11.23), toujours exclu ; nouvelles sources de T04d
  (`questcache.wdb`, `QuestXP`, Naowh Completo et Dungeon Journal, Forever Guide, FDJ, GearQuest) ; nom réel du
  fichier du sac de couchage. `docs/ROADMAP.md` : ordre (décision 245), critères de fin de T04d (ci-dessous).

## Choix de conception
1. **Priorité des sources par champ** (une règle écrite, testée) : client (`questcache.wdb`, `QuestXP`) >
   relevé en jeu (ForeverLogger, `QuestieForeverDB`) > addons Forever (Forever Guide, Naowh, FDJ) > Questie Classic.
   La valeur retenue porte sa source et sa certitude (`certain` client ou relevé, `probable` client à disposition
   déduite, `suppose` addon) ; chaque désaccord entre sources sur un même champ est gardé dans `discrepancies`
   (champ, valeur par source), jamais tranché par moyenne. Un désaccord sur le niveau entre un addon et le client est
   un écart à signaler, pas une erreur.
2. **Statut d'une quête** : `nouvelle` (absente de la base Classic de Questie, présente dans une source Forever ou
   le client), `retouchée` (présente dans les deux, avec un niveau, un niveau requis, des prérequis ou une XP
   différents ; la liste des champs changés est rendue), `absente des sources Forever` (base Classic seulement, zone
   couverte par Completo : candidate au retrait, `suppose`, jamais « retirée »), `inchangée`. Les annonces
   officielles (Elixir of Pain, Stanley, Shadowvale, Bandarion Keep, Gelkis, Magram) servent de cas de contrôle.
3. **Modèle d'XP en fonctions pures** (`forever/engine/xp.py`), chaque règle lue dans `mechanics.json` (`xp.*`)
   avec source, certitude et entrée du registre ; aucun chiffre dans le code :
    - XP de base d'un monstre par niveau : colonne `PerKill` de la GameTable `xp` décodée (client) si elle concorde
      avec la règle actuelle, sinon écart signalé et arrêt pour accord (elle change `level_weight`) ;
    - écart de niveau du monstre (règle Classic : plus haut, plus bas, gris par `zero_difference`, déjà dans
      `leveling.json`, déplacée dans `mechanics.json` avec source) ; élite (facteur Classic, `suppose`) ;
    - donjon (`xp.dungeon_kill_bonus`, I10, assiette LVL5 en question) ; groupe (`xp.group_level_basis`, I11 ; partage
      et bonus de groupe Classic `suppose`, seuil de coupure inconnu : LVL4, pas modélisé, signalé) ;
    - repos : paliers de `Exhaustion` (consommation par monstre, quêtes hors repos, plafond, gain en auberge et
      dehors), D7 ;
    - XP d'une quête : `QuestXP` × multiplicateur de `questcache.wdb` quand la quête a été vue (`probable`, `certain`
      après recoupement par `xpReward`) ; sinon XP Classic de Questie ou de FDJ (`suppose`) ; puis règle d'écart de
      niveau de Classic (`suppose`) et arrondi ; quêtes de donjon : I9 (réduction déjà comprise dans le multiplicateur
      d'une quête vue ; signalée sinon).
   `monsters.mob_xp` délègue au nouveau modèle (même valeur à niveau égal tant que `PerKill` concorde).
4. **Liste fusionnée dans le cache** (`<cache>/quests/<empreinte>.json`, empreinte = versions et empreintes des
   addons lus + version des données) : rebâtie seulement quand une empreinte change ; **jamais dans le dépôt**. Dans le
   dépôt : `quest_rewards.json` (client : table `QuestXP` décodée, et pour chaque quête vue : niveau, niveau requis,
   zone, quête suivante, difficulté et multiplicateur d'XP, argent) et `docs/research/quetes-forever.md` (agrégats :
   comptes par zone et par statut, écarts par paire de sources, comptes des trois tables de chaînes).
5. **`questcache.wdb` suit les mises à jour** : archivé par build avec `DBCache.bin` (étape d'archivage de
   `forever update`) ; une quête nouvellement vue donne une attente `quest_cache` (révision des données, approuvable
   en jeu comme `addon_data`), jamais une écriture silencieuse.
6. **Prêt pour RX1** : chaque quête du cache porte, par champ et avec sa source : camp, races, classes, niveau et
   requis, zone, donneur et rendeur (ID de PNJ ou d'objet, nom, uiMapID, x, y), objectifs (monstres, objets, camps
   d'objectifs de Journeys), prérequis (tous / au moins un), chaîne et position, suite, exclusions, quête d'accroche,
   donjon. Positions ramenées en uiMapID et pourcentage (table AreaTable → uiMapID lue dans Questie). Une fonction
   d'ordre (tri topologique sur les prérequis et chaînes, stable par position puis niveau) rend un ordre valide ; un
   cycle est signalé. L'export au format RestedXP reste à RX1.
7. **Temps par monstre** (ordre de priorité, la source est rendue) : moteur (Mage) ; sinon **mesuré** pour la classe
   et la tranche de niveaux : durée des combats dans les journaux (première attaque du joueur ou de son familier
   jusqu'à `UNIT_DIED`) et cadence de ForeverLogger (intervalle médian entre deux gains d'XP de monstre dans une
   même séance, pauses longues écartées, seuil dans les données) ; sinon **estimé** : la cible de Blizzard de 10 à
   15 s par monstre en solo (déjà citée par `leveling.json` `mob_model`), rendue en fourchette, `suppose`,
   « estimé ». Les relevés sont propres au joueur : gardés dans `<cache>/measures/`, jamais dans `forever/data/`.
8. **Objectifs de leveling** (simulateur, `forever/sim/objectives.py`) : pour un personnage (classe, race, camp,
   niveau, repos), chaque zone et chaque donjon accessibles sur une tranche de niveaux :
    - zone : XP des quêtes disponibles non grises (modèle) + XP des monstres de leurs objectifs + XP du reste du
      temps passé à tuer, sur le temps total (monstres des objectifs × temps par monstre + surcoût par quête,
      hypothèse `leveling.quest_overhead_s`, `suppose`, à mesurer par ForeverLogger : acceptation → rendu) ;
    - donjon, **premier passage avec quêtes** : XP des monstres (bonus de donjon, élite, groupe) + XP de toutes ses
      quêtes accessibles (prérequis compris, ceux qui manquent sont listés), sur le temps total : prise des quêtes,
      trajet (hypothèse `suppose`), donjon (monstres du donjon d'après les positions de Questie × temps par monstre
      en groupe), retour pour les rendre ;
    - donjon, **passages suivants** : XP des monstres seule, sur la durée du donjon ;
    - rendu : classement par XP par heure, en XP et en minutes, avec certitude de chaque terme ; phrase prête pour le
      bouton (« fais Ragefire Chasm une fois avec ses quêtes : environ N XP en M minutes », « continue dehors »)
      construite par l'outil à partir de ses chiffres, jamais par le modèle de langage.
9. **Interfaces publiques** : `forever quests build|diff|show`, `forever lookup quests` (zone, niveau, ID, statut),
   `forever sim objectives` ; MCP : `forever_lookup(kind="quests")` et `forever_sim_leveling(kind="objectives", …)`
   (le défaut `kind="kill"` garde la sortie actuelle) ; aucun nouvel outil MCP. Toutes les sorties portent
   `provenance` (version, empreinte, fraîcheur, certitude, versions et empreintes des addons lus).

## Étapes et blocs (commits `T04d: tests (bloc X)` puis `T04d: bloc X vert`)

### Étape 0 — Préalables
Branche `t04d` depuis `origin/main` (mémoire « la veille pousse sur main ») ; décisions 245 et 246, `DATA_SOURCES`,
`ROADMAP` ; charger le skill `addon-forever` avant le bloc A.

### Bloc A — ForeverLogger 0.4.0 et sonde I (**à finir le premier, objectif : sonde jouable au plus tard le 2026-10-18**)
- ForeverLogger : chaque gain d'XP garde en plus le montant lu (texte anglais et français), le bonus de groupe et de
  repos s'ils figurent, `UnitXP` / `UnitXPMax` et `GetXPExhaustion` avant et après (`PLAYER_XP_UPDATE`), le niveau et
  la classification de la cible quand elle porte le nom du monstre et qu'elle est morte, l'instance (`IsInInstance`),
  la taille et les niveaux du groupe, la carte (`C_Map.GetBestMapForUnit`) ; nouvelle liste `quests` : acceptation
  (`QUEST_ACCEPTED`, ID, heure) et rendu (`QUEST_TURNED_IN` : ID, `xpReward`, `moneyReward`, niveau du personnage,
  repos, heure) ; `UnitQuestTrivialLevelRange` dans l'instantané (LVL2). Chaque API sous `pcall`, valeur secrète
  traitée comme absente, aucune fonction d'action, aucun abonnement au journal de combat. Schéma de la SavedVariable
  inchangé pour les anciennes listes (lecture des anciennes entrées gardée).
- Client simulé : ForeverLogger exécuté sous lupa (extension du bouchon de ForeverBridge : `UnitXP`,
  `GetXPExhaustion`, événements de quête), pour qu'aucune erreur Lua n'arrive en jeu pendant la bêta.
- Lecteur Python (`addon_sv.py`) : `XpGain` enrichi (montant, type monstre / autre, groupe, repos, cible, instance) et
  `QuestTurnIn`, `QuestAccept` ; anciennes entrées lues (montant extrait du texte, champs nouveaux absents).
- `docs/ADDON.md` : **sonde I** (procédure plus bas) ; `addon/README.md` (titre resté à 0.2.0 corrigé).

### Bloc B — Client : `QuestXP`, `PerKill`, `questcache.wdb`
- `QuestXP` ajoutée aux tables de `forever fetch` / `forever update` et décodée dans `quest_rewards.json` (nouveau
  fichier de données : pièges des comptes, `DECODED_FILES`, `sources.json`, `origins.json`) ; colonne `PerKill` de
  la GameTable `xp` décodée dans `character_scaling.json`.
- Lecteur de `questcache.wdb` (`forever/pipeline/questcache.py`) : en-tête, enregistrements, champs numériques du
  début jusqu'aux récompenses (disposition établie sur la fixture et recoupée avec `classicQuestDB` pour niveau,
  requis, zone et suite) ; chaînes de texte ignorées. Quêtes vues fusionnées dans `quest_rewards.json` ; archivage
  par build et attente `quest_cache` dans `forever update`.
- **Une fois, hors tests** : `QuestLine`, `QuestLineXQuest`, `QuestPOIPoint` téléchargées par la même voie dans le
  cache (pas décodées, pas dans le dépôt) ; comptes des lignes qui touchent des quêtes de Forever (ID présentes dans
  le cache des quêtes avec le statut `nouvelle`, et ID ≥ 90000) écrits dans `docs/research/quetes-forever.md`.

### Bloc C — Modèle d'XP (`forever/engine/xp.py`)
Fonctions du choix 3, règles dans `mechanics.json` (`xp.*` : base par niveau ou renvoi à `PerKill`, écart de niveau,
élite, donjon, groupe, repos, écart de niveau des quêtes, arrondi), `mob_xp` qui délègue, registre.

### Bloc D — Quêtes de Forever (lecteurs, fusion, cache)
Lecteurs locaux : Naowh Completo, Journeys (`QuestSpots`), Dungeon Journal ; Forever Guide ; FDJ ; GearQuest (par
nom de quête, rapproché par nom et zone, ambiguïté signalée) ; Questie étendu (corrections de Questie,
`QuestieForeverDB`, positions, prérequis, objectifs, AreaTable → uiMapID, toutes les classes et non plus le Mage
seul). Fusion, statut, écarts, ordre topologique ; `forever quests build|diff|show`, `forever lookup quests`,
`forever_lookup(kind="quests")` ; lecteurs branchés sur `forever addons status` (agrégats dans l'état, reliés à la
liste du cache) ; `docs/research/quetes-forever.md`.

### Bloc E — Temps par monstre des classes sans moteur
Mesure dans les journaux (durée des combats par classe et tranche de niveaux, familier compris) et cadence de
ForeverLogger ; hypothèse de repli dans les données ; `forever measures refresh` en rend l'état (sans rien écrire
dans `forever/data/`).

### Bloc F — Objectifs de leveling, bouton Leveling, `forever_build`
`forever/sim/objectives.py` (choix 8), `forever sim objectives`, `forever_sim_leveling(kind="objectives")` ; le plan du
bouton Leveling (`bridge/plans.py`) l'appelle **pour toutes les classes** (le Mage garde en plus prochain talent et
temps par monstre calculé) ; `forever_build` (contexte leveling) prend l'XP d'un monstre du modèle ; skill
`forever-leveling` et routeur mis à jour (sans chiffre), évaluations du plugin pour le Chasseur et le Mage.

### Bloc G — Mesure et vérification du modèle
`forever xp check` : compare le modèle aux gains relevés (anciens gains joints aux journaux par l'heure ou au niveau
fixe de Questie pour connaître le niveau du monstre ; nouveaux gains par la cible et `xpReward`) ; rend, par règle,
le nombre de cas, l'écart médian et les cas hors tolérance ; aucune écriture. Après la sonde I : relevés de
l'utilisateur en fixtures, règles confirmées passées `certain` ou écarts portés en questions ouvertes ; s'il manque
la sonde à la fin de la tranche, elle reste dans `docs/ADDON.md` et dans la liste des tests en jeu en attente de LN1.

## Sonde en jeu I (à écrire dans `docs/ADDON.md` au bloc A ; avant le 2026-10-21)
0. Jeu fermé : `uv run python scripts/install_addon.py` (ForeverLogger 0.4.0) ; `uv run forever logs scan`.
1. En jeu : `/combatlog` (journal avancé actif), noter le repos affiché (barre d'XP bleue ou non).
2. **Mage, 20 à 30 min, seul, dehors** : 5 monstres de son niveau, 5 de 2 à 3 niveaux en dessous, 3 de 1 à 2 niveaux
   au-dessus, si possible 2 gris ; une partie avec du repos, une partie sans ; rendre au moins 3 quêtes de couleurs
   différentes (jaune, verte, et grise s'il en reste une).
3. **Chasseur, 20 à 30 min, seul** : même chose dehors (The Barrens ou Durotar), dont 5 monstres normaux de chaque
   niveau qui se rencontre aussi dans Ragefire Chasm.
4. **Chasseur, Ragefire Chasm** : avant d'entrer, prendre Slaying the Beast (Neeru Fireblade, Orgrimmar) et la
   première quête de Hidden Enemies (Thrall) ; si le trajet le permet, Testing an Enemy's Strength et Searching for
   the Lost Satchel (Rahauro, Thunder Bluff). Dans le donjon, seul : tuer des Ragefire Troggs et des Ragefire
   Shamans (objectif de Testing an Enemy's Strength), noter leur niveau ; boss seulement en groupe. Sortir, rendre ce
   qui est fini. Liste exacte des quêtes et des monstres recopiée de la liste du cache au bloc A
   (`forever quests show --dungeon "Ragefire Chasm" --faction horde`).
5. En groupe seulement par hasard : quelques monstres tués en groupe, niveaux des membres notés (LVL4).
6. Jeu fermé : `uv run forever xp check` et `uv run forever logs scan` ; relevé : sortie de `forever xp check`, copie
   de `ForeverLogger.lua` (SavedVariables) et du journal de combat, à extraire en fixtures (sans GUID ni nom).
7. « Fait le AAAA-MM-JJ (relevés de l'utilisateur) » : règles confirmées, écarts, questions mises à jour.

## Fichiers
- **Nouveaux** : `forever/engine/xp.py`, `forever/pipeline/questcache.py`, `forever/pipeline/naowh.py`,
  `forever/pipeline/forever_guide.py`, `forever/pipeline/fdj.py`, `forever/pipeline/gearquest.py`,
  `forever/quests.py` (fusion, statut, écarts, ordre, cache), `forever/sim/objectives.py`,
  `forever/measures/kill_time.py` (ou dans `pipeline/measure.py`), `forever/data/1.60.1.70338/quest_rewards.json`,
  `docs/research/quetes-forever.md`, fixtures (ci-dessous), tests (ci-dessous).
- **Modifiés** : `addon/ForeverLogger/ForeverLogger.lua` et `.toc` (0.4.0), `addon/README.md`, `docs/ADDON.md`,
  `forever/pipeline/addon_sv.py`, `forever/pipeline/questie.py`, `forever/pipeline/tables.py`,
  `forever/pipeline/decode.py`, `forever/pipeline/character_scaling.py`, `forever/pipeline/update.py` (archivage,
  attente `quest_cache`), `forever/pipeline/fetch.py` ou équivalent (liste des tables), `forever/engine/monsters.py`,
  `forever/optimize/leveling.py`, `forever/leveling.py`, `forever/lookup.py`, `forever/cli.py`,
  `forever/mcp_server.py`, `forever/addons.py`, `forever/bridge/plans.py`, `forever/bridge/buttons.py`,
  `forever/data/1.60.1.70338/{mechanics,character_scaling,sources,origins,leveling}.json`,
  `plugin/skills/forever-leveling/`, `plugin/skills/forever-router/`, `plugin/evals/`,
  `docs/MECHANICS_REGISTRY.yaml`, `docs/OPEN_QUESTIONS.md`, `docs/DATA_SOURCES.md`, `docs/DECISIONS.md`,
  `docs/ROADMAP.md`, `docs/USAGE.md`, `docs/ARCHITECTURE.md` (outils).

## Interfaces (signatures indicatives, forme définitive au bloc)
```
# forever/engine/xp.py  (registre : I6, I9, I10, I11, I12, I13, D7)
# mob_kill_xp(gd, player_level, mob_level, *, elite=False, dungeon=False, party: Party | None = None,
#             rested_pool: float = 0) -> XpResult(xp, rested_used, terms: list[Term(rule, factor, certainty, source)])
# quest_xp(gd, player_level, quest: QuestXpInput(level, difficulty, multiplier, source)) -> XpResult
# rested_gain(gd, level, hours, *, inn: bool) -> float ; gray_level(gd, level) -> int (repris de leveling)

# forever/pipeline/questcache.py
# read_questcache(path) -> QuestCache(build, locale, records: dict[int, QuestRecord])
# QuestRecord(id, type, level, min_level, sort_id, next_quest, xp_difficulty, xp_multiplier, money, …)

# forever/quests.py
# build_quests(deps, *, addons_dir, wtf_dir, cache_dir) -> QuestBook(quests: dict[int, Quest], sources, provenance)
# Quest(id, name, faction, races, classes, level, min_level, zone, giver, turn_in, objectives, prereq_all, prereq_any,
#       chain, next, exclusive, dungeon, rewards, xp, status, changed_fields, discrepancies, field_sources)
# order_quests(book, ids) -> OrderResult(order, cycles, missing_prereqs)

# forever/sim/objectives.py
# objectives(deps, *, class_name, race, faction, level, levels=…, rested=…, party=1, dungeon_party=5)
#   -> ObjectivesReport(zones: [Objective], dungeons: [DungeonObjective(first_pass, repeat)], kill_time_source,
#                       advice: str, provenance)
```
CLI (texte français, `--json`, provenance, aucun réseau sauf `fetch` / `update`) : `forever quests build`,
`forever quests diff [--sources a,b]`, `forever quests show (--id N | --zone Z | --dungeon D) [--faction]`,
`forever lookup quests --level N [--zone] [--status nouvelle|retouchée|absente]`,
`forever sim objectives --level N --class C [--race] [--faction] [--rested XP] [--party N]`, `forever xp check`.

## Tests attendus (valeurs tirées des fixtures ou des données)
- **Fixtures** (extraits minimaux, extraits par `scripts/extract_quest_fixtures.py`, sans données personnelles) :
  `tests/fixtures/client/questcache_sample.wdb` (en-tête et une dizaine d'enregistrements dont 479 et des quêtes de
  Ragefire Chasm si vues) ; `tests/fixtures/addons/quests/` : extraits de Questie (7, 783, 5761, 5723 et leurs PNJ),
  Completo (92432, 7, une chaîne), Journeys (7), Dungeon Journal (Ragefire Chasm, The Hall of Thanes), Forever Guide
  (5761, 5723, 96403 et leurs PNJ), FDJ (96395), GearQuest (deux objets de récompense dont un nom ambigu) ;
  `tests/fixtures/addon/ForeverLoggerDB_xp.lua` (anciennes et nouvelles entrées, anglais et français, groupe, repos,
  quête rendue) ; `tests/fixtures/client/QuestXP.csv` (quelques lignes) ; journal de combat synthétique d'un
  Chasseur (familier) pour la durée des combats.
- `test_addon_logger_xp.py` (bloc A, lupa) : un gain d'XP de monstre déclenché par le bouchon garde montant, cible
  (niveau, classification), repos avant / après, instance ; `QUEST_TURNED_IN` garde ID et `xpReward` ; une API qui
  lève une erreur ne casse rien (`pcall`) ; `test_addon_rules.py` vert et version 0.4.0.
- `test_addon_sv_xp.py` : « X dies, you gain 23 experience. » → 23, monstre ; « (+N group bonus) » → bonus de
  groupe séparé ; « You gain N experience. » → autre ; forme française lue ; entrée de quête lue.
- `test_questcache.py` : 479 → niveau 16, requis 10, zone 130, suite 480, difficulté 5, multiplicateur 1,0, argent
  800 ; niveau, requis, zone et suite égaux à ceux de `classicQuestDB` pour chaque quête Classic de la fixture ;
  signature autre que `WQST` → erreur de schéma.
- `test_quest_rewards_decode.py` : `QuestXP` décodée = lignes de la fixture ; XP d'une quête vue = cellule de la
  table × multiplicateur (cellule et multiplicateur lus dans les fixtures) ; `PerKill` décodé égal à la règle de base
  actuelle à chaque niveau (sinon le test rouge arrête l'exécution pour accord, voir Risques).
- `test_engine_xp.py` : chaque règle lue dans `mechanics.json` (aucun chiffre dans le test) : monstre gris → 0 ;
  plus haut et plus bas suivent les lignes de `zero_difference` ; donjon multiplie par `1 + xp.dungeon_kill_bonus` ;
  repos : gain doublé tant que le réservoir suffit, puis partiel, réservoir consommé ; quête : pas de repos ; écart
  de niveau de quête au-delà du seuil réduit l'XP selon la règle des données ; chaque `Term` porte sa certitude.
- `test_quests_merge.py` : 92432 → `nouvelle`, donneur Emissary Jacques en uiMapID 1424 (48,3 ; 60,1), source
  Completo ; 5761 → écart `level` signalé (Dungeon Journal de Naowh 9, Forever Guide 16), niveau retenu 16 (règle
  de priorité), requis 9 ; 7 → prérequis 783 dans Questie et dans Completo (accord, aucun écart) ; 96395 → écart
  interne de FDJ signalé ; 96403 → `new` de Forever Guide, donneur et rendeur Thom Filch ; une quête de la base
  Classic absente de Completo dans une zone couverte → `absente des sources Forever`, certitude `suppose` ; une quête
  vue dans la fixture `questcache` → XP `probable` de source client, l'emporte sur Questie.
- `test_quests_order.py` : l'ordre rendu respecte prérequis et chaînes de la fixture ; un cycle fabriqué est signalé.
- `test_quests_cache.py` : deuxième appel sans changement → cache relu (pas de relecture des addons) ; empreinte d'un
  addon changée → reconstruction ; rien n'est écrit sous le dépôt (`tmp_path`).
- `test_kill_time.py` : durée des combats du journal synthétique (familier compris) ; cadence des gains de la
  fixture ForeverLogger, pauses écartées ; sans relevé → hypothèse des données en fourchette, `suppose`, `estimated`.
- `test_sim_objectives.py` : Chasseur 15 Horde sur les fixtures : Ragefire Chasm a un premier passage (quêtes
  comprises, prérequis manquants listés) et des passages suivants, le premier rapporte plus d'XP au total ; XP par
  heure = XP / temps de chaque objectif ; Mage : temps par monstre de source `engine`, Chasseur : `measured` ou
  `estimated` ; la phrase du conseil reprend les chiffres de l'objectif.
- `test_bridge_leveling_all_classes.py` : le plan du bouton Leveling d'un Chasseur et d'un Mage appelle
  `forever_sim_leveling(kind="objectives")` ; la consigne ne dit plus « XP par heure pas encore calculée ».
- `test_xp_check.py` : écart du modèle sur la fixture ForeverLogger (cas joints, cas sans niveau de monstre écartés
  et comptés).
- Comptes à mettre à jour dès le commit « tests » : `test_data_import.py`, `test_manifest.py`,
  `test_decode_version.py` (nouveau fichier `quest_rewards.json`), `test_registry.py` (entrées ajoutées et statuts
  changés : `total`, `coverage`, sortie de `main`, nombre de `teste`), `test_addon_rules.py` (version).

## Registre (`docs/MECHANICS_REGISTRY.yaml`)
- I6 (XP d'un monstre, temps par monstre) : source client pour la base, règles d'écart de niveau, tests.
- I9 (XP des quêtes de donjon) : multiplicateur du client, `teste`.
- I10 (donjon), I11 (groupe), D7 (repos) : `absent` → modélisés et testés, certitude inchangée (`probable`) jusqu'à
  la sonde.
- Nouvelles : **I12** XP d'une quête selon l'écart de niveau ; **I13** XP des monstres élites ; **I14** rentabilité
  d'un donjon (premier passage avec quêtes, passages suivants) ; **I15** temps par monstre des classes sans moteur
  (mesuré ou estimé). Comptes de `test_registry.py` écrits en phase rouge.

## Questions ouvertes à ajouter ou modifier (`docs/OPEN_QUESTIONS.md`)
- LVL1 (mise à jour : XP des quêtes vues par le client), LVL4, LVL5 (sonde I).
- **LVL6** : disposition des champs de `questcache.wdb` sur Forever (recoupée par `xpReward`).
- **LVL7** : règle d'écart de niveau des quêtes sur Forever (Classic ?).
- **LVL8** : facteur des élites sur Forever.
- **LVL9** : quêtes « absentes des sources Forever » vraiment retirées ? (contrôle en jeu ou par le client).
- **LVL10** : aucun bonus de repos dans 2 714 gains relevés : pas de repos, ou texte du repos différent sur Forever ?

## Hors périmètre
- Export vers RestedXP et feuilles de route (RX1) ; décodage de `QuestLine`, `QuestLineXQuest`, `QuestPOIPoint`
  (comptés seulement).
- Bonus d'XP cumulés : sac de couchage, nourriture, Legacy, camps (T04f) ; le repos de base est ici.
- Moteur générique des autres classes (étude `docs/research/moteur-generique.md`) ; temps de déplacement réel
  (Journeys, ShortestPathForever : RX1).
- Donjons au-delà de leurs quêtes et de l'XP de leurs monstres (boss, butin : DJ1) ; XP au niveau maximal.
- Toute lecture de RXPGuides comme source.

## Risques
- **`PerKill` différent de la règle actuelle** : change `level_weight`, donc peut-être le chemin des talents de
  leveling et les fichiers de `tests/golden/` : s'arrêter et demander avant tout changement de golden.
- **Disposition de `questcache.wdb`** déduite d'enregistrements : la fixer sur plusieurs quêtes connues (niveau,
  requis, zone, suite comparés à Questie) ; sans recoupement par `xpReward`, la certitude reste `probable`.
- **Calendrier** : la sonde dépend du bloc A ; si le bloc A glisse après le 2026-10-18, la sonde se réduit au
  Chasseur dans Ragefire Chasm (la mesure la plus rare).
- **Bêta et cache vides** : la remise à zéro du PC a vidé `questcache.wdb` le 2026-10-12 ; seules les quêtes vues
  depuis comptent ; les autres restent `suppose`.
- **Noms de GearQuest** : rapprochement par nom et zone ambigu ; un nom ambigu n'est jamais rattaché.
- **Temps des objectifs** (surcoût par quête, trajet, monstres d'un donjon) : hypothèses `suppose` ; le classement
  des objectifs peut en dépendre plus que de l'XP : la sortie le dit.
- **Taille** : sept blocs ; si le contexte se remplit, s'arrêter après un bloc vert committé (A d'abord).
- **Réseau** : seule `QuestXP` (et le téléchargement unique des trois tables de chaînes) passe par la voie existante ;
  aucun test réseau.

## Critères de fin (T04d)
- ForeverLogger 0.4.0 relève XP de chaque monstre (montant, cible, repos, instance, groupe) et de chaque quête
  rendue (`xpReward`) ; exécuté sans erreur sous lupa ; `test_addon_rules.py` vert ; sonde I écrite, et jouée si le
  joueur l'a pu avant le 21 octobre.
- `QuestXP` et `PerKill` décodés, `questcache.wdb` lu ; XP d'une quête vue venue du client ; comptes des trois
  tables de chaînes dans `docs/research/quetes-forever.md`.
- Modèle d'XP en fonctions pures, chaque règle avec source et certitude dans `mechanics.json` et le registre.
- Liste fusionnée des quêtes dans le cache, statut et écarts entre sources, champs prêts pour RX1 et ordre valide ;
  rien de la liste dans le dépôt.
- `forever sim objectives` et le bouton Leveling rendent XP par heure par zone et donjon (premier passage et
  passages suivants) pour le Mage (temps calculé) et le Chasseur (mesuré ou estimé, marqué) ; `forever_build` sur le
  nouveau modèle sans changement de golden non approuvé.
- `forever xp check` rend l'écart du modèle sur les gains relevés.
- Registre, questions ouvertes, `DATA_SOURCES`, `DECISIONS`, `ROADMAP` à jour ; `uv run tasks.py verify` vert ; CI
  verte sous Ubuntu et Windows.
