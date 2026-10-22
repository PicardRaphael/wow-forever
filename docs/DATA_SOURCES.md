# Sources de données

Chaque source : ce qu'elle fournit, sa licence, sa fraîcheur et comment elle est relue (commande, étape de la veille
`forever update`, fréquence). L'architecture qui les lit est décrite dans `docs/ARCHITECTURE.md`. Une licence que le
dépôt n'établit pas (fichier lu, inventaire, décision) est écrite « non déclarée » ou « à vérifier ».

## Règles communes
- **Forever seulement** (décision 294) : une source qui ne couvre pas WoW Forever n'est pas prise ; rien de Season of
  Discovery ni de la Classic, ni données ni mécanismes. Les valeurs encore héritées de la Classic sont recensées et
  dites (`forever origins classic`).
- **Hiérarchie** (décisions 127 et 128) : 1. données du client (tables, correctifs du serveur) : `certain` ;
  2. mes observations (journaux de combat, relevés de ForeverLogger) : `certain` pour ce qu'elles mesurent ;
  3. addons de données, simulateur et parcours de la communauté : `suppose` au mieux, source et version citées ;
  4. guides et sites : faits sourcés, `suppose`. Une source plus haute l'emporte ; un écart est toujours signalé,
  jamais tranché au hasard.
- **Lire ce qui existe** (décisions 272, 288, 293) : une donnée ou un calcul déjà tenu par un addon installé, le
  simulateur de la communauté ou un parcours maintenu est lu tel quel par un adaptateur mince, jamais refait.
- **Dans le dépôt, seulement des agrégats** (décisions 123 et 133) : la lecture locale de tout addon installé est
  libre quelle que soit sa licence ; ce qui entre dans le dépôt (comptes, écarts, valeurs recoupées avec leur source)
  respecte la licence ; les tables, textes et guides des tiers restent sur le disque de l'utilisateur ou dans le cache.
- **Provenance** : chaque valeur lue porte sa source (version, empreinte ou commit, date) dans le bloc `provenance`.
- **Fraîcheur** : le registre des sources (`forever/sources.py`, `forever status`) dit pour chaque source si elle est
  à jour pour la version du jeu installée, par son contenu quand c'est possible, sinon par sa date ou son build ; une
  source en retard donne « calcul en cours de mise à jour », jamais une panne.
- **Réseau** : seulement les accès listés dans `CLAUDE.md`, jamais dans les tests (`tests/fixtures/` seulement).

## Vue d'ensemble

| Source | Fournit | Licence | Fraîcheur | Relecture |
| --- | --- | --- | --- | --- |
| wago.tools | versions publiées du client, tables du client (CSV), GameTables | non déclarée | `forever status` (cache de 6 h) | étapes `jeu` et `nouvelle_version` de chaque passage ; `forever builds`, `forever fetch` à la main ; `build-watch.yml` chaque jour |
| WoWDBDefs | dispositions des tables (`.dbd`) pour décoder les correctifs | introuvable (`LICENSE` absent) : à vérifier | commit épinglé dans `<cache>/dbd/dbd.json` | relu par la veille quand des correctifs l'exigent ; `forever fetch --version V --dbd` |
| `DBCache.bin` du jeu | correctifs du serveur (valeurs) | données du client de l'utilisateur, lecture locale | par build (en-tête du fichier) | étapes `archivage` puis `nouvelle_version` ou `correctifs` ; `forever hotfixes` |
| Raidbots (caches vérifiés) | `DBCache.bin` d'un build quand le jeu n'en a pas | non déclarée | entrée vérifiée la plus récente du build | repli des étapes `nouvelle_version` et `correctifs` ; `forever hotfixes --raidbots`, `forever decode --hotfixes --raidbots` |
| `Hotfix.log` | index des poussées vues par le client (sans valeur) | lecture locale | réécrit à chaque démarrage du client | journal `<cache>/hotfixes.json` ; `forever hotfixes`, `forever watch` |
| `questcache.wdb` | quêtes vues par le client | lecture locale | archivé par build | révision des quêtes vues par la veille ; `forever decode --questcache` |
| Journaux de combat | PV des monstres, coûts, incantations, touchés et ratés, critiques | données de l'utilisateur | par session (version du client attribuée par `client_builds`) | étape `journaux` ; `forever logs`, `forever measures refresh` |
| ForeverLogger (notre addon) | niveau, talents, gains d'XP, relevés hors combat | dépôt | à chaque connexion | profil, mesures, `forever xp check` |
| Addons de données installés | quêtes, donjons, butin, BiS, échelles, builds, familiers, métiers, trajets | variable (table plus bas) | empreinte des fichiers, contenu ou date | étape `addons` ; `forever addons status` |
| RestedXP (parcours gratuits) | parcours de leveling en clair | CC BY-NC-SA 4.0 | version de l'addon installé | lu à chaque appel (`forever route …`) |
| Polestar | guides de leveling au-delà de RestedXP | GPL-3.0 | commit épinglé du clone | étape `guides` (clone existant) ; `forever route polestar` |
| wowsims/forever | calcul au niveau 60 (dégâts, poids, races, classes) | MIT (lien de retour demandé) | commit épinglé et compilé, daté contre le build | étape `simulateurs` (déjà compilé) ; `forever sims update` |
| Factoruide | base de quêtes et méthode de route (recoupement) | code MIT, `data/` GPL-2.0+ (part VMaNGOS) | commit épinglé `f7da6da` | à la main seulement |
| Forum de Blizzard | notes officielles (signal) | CC BY-NC-SA 3.0 (textes jamais recopiés) | une fois par jour au plus | `forever notes`, à la main ; `notes-watch.yml` à la main |
| API Blizzard | (à venir) prix, fiches, PvP | conditions des API de Blizzard | sonde quotidienne | `forever api probe` ; `api-probe.yml` chaque jour |
| Wowhead Forever | contrôle ponctuel d'une valeur | conditions du site : aucune aspiration | à la consultation | sous-agent `forever-web-researcher` seulement ; aucun code du dépôt ne le lit |

## Client du jeu (vérité)

### wago.tools : versions et tables
- **Fournit** : la liste des versions publiées du client (`https://wago.tools/api/builds`, produit `wow_classic_beta`,
  préfixe `1.60.` ; liste non triée : tri par `created_at` ; produit de la version finale à revérifier, d'où l'alerte
  `silent`) et les tables du client en CSV (`https://wago.tools/db2/<Table>/csv?build=<version>`, `&locale=frFR` pour
  une autre locale), plus les GameTables (`api/casc`, `forever fetch --gametables`).
- **Licence** : non déclarée (données du client republiées par wago.tools ; aucune condition relevée dans le dépôt).
- **Lecteurs** : `forever/pipeline/builds.py`, `fetch.py` (cache `<cache>/wago/<version>/<locale>/<Table>.csv`, index
  `fetch.json` : adresse, empreinte, taille, date ; une réponse sans en-tête CSV est refusée), `tables.py` (colonnes
  déclarées par table, plusieurs noms admis par colonne), puis les décodeurs (`decode.py`, `character_scaling.py`,
  `dungeons_client.py`, `pets.py`, `quest_rewards.py`, `travel_client.py`, `xp_bonuses.py`). Tables lues, colonnes et
  constantes de lecture : `forever/data/<version>/decode_rules.json` (`tables`, `class_tables`, `character_tables`,
  `pet_tables`, `travel`…), jamais dans le code.
- **Couverture** : talents (`Trait*`, `CurvePoint`, `SkillLineXTraitTree`), sorts (`Spell*`, `SkillLineAbility`), neuf
  classes, races et combinaisons, objets, donjons (`Map`, `LFGDungeons`, `ContentTuning`, `DungeonEncounter`,
  `AreaTable`), familiers, trajets (`TaxiNodes`, `TaxiPath*`, `UiMapAssignment`), XP (`QuestXP`, `LevelExperience`,
  GameTable `xp`), bonus d'XP. **Absent du client** : PV des monstres, quêtes non vues, positions des PNJ, taux de
  butin, listes d'entraîneurs.
- **Fraîcheur** : `forever status` compare la version installée à la dernière publiée (cache de 6 h, `fresh`, `stale`,
  `unknown`, `silent`).
- **Relecture** : chaque passage de la veille (étape `jeu`, puis `nouvelle_version` si une version plus récente paraît :
  téléchargement, trois essais par table avec délai doublé, décision 230 ; les tables d'une autre locale sont
  facultatives et ajoutées en révision au passage suivant) ; à la main `forever builds`, `forever fetch --version V
  [--tables …] [--locale frFR] [--refresh]` ; en CI `build-watch.yml` chaque jour (rapport en pull request, n'installe
  rien).

### WoWDBDefs : dispositions des tables
- **Fournit** : les définitions `.dbd` (<https://github.com/wowdev/WoWDBDefs>) qui décrivent l'ordre des octets des
  enregistrements, nécessaires pour décoder les correctifs de `DBCache.bin` (`forever/pipeline/dbd.py`). Seul le bloc
  qui nomme le build sert ; chaque disposition est validée contre le CSV du build avant application.
- **Licence** : introuvable (`LICENSE` absent du dépôt amont au relevé de T08c) : à vérifier. Aucun texte de `.dbd`
  dans le dépôt ; les fixtures ne portent que des dispositions dérivées.
- **Fraîcheur et relecture** : commit épinglé dans `<cache>/dbd/dbd.json` (API GitHub, lecture seule, décision 179) ;
  relu par la veille quand un correctif du serveur demande une disposition absente (sinon attente `network_dbd` qui
  se lève seule) ; à la main `forever fetch --version V --dbd [--dbd-commit …]`.

### Correctifs du serveur : `DBCache.bin` du jeu et caches vérifiés de Raidbots
- **`DBCache.bin` du jeu** (`Cache/ADB/<locale>/DBCache.bin`, `forever/pipeline/dbcache.py`) : valeurs des correctifs
  poussés par le serveur. Le client le réécrit à sa sortie et ne garde que son build : `forever/archive.py` le copie
  par build dans `<cache>/dbcache/<build>/` (étape `archivage` de chaque passage, et passage lancé par le pont à la
  fermeture du jeu ou à l'écriture du fichier). Seules les poussées réelles sont appliquées (`VALID` remplace ou
  ajoute, `DELETE` retire ; la plus haute poussée l'emporte), par `forever/pipeline/hotfix_overlay.py`, avant tout
  décodeur. Origine `correctif_serveur` dans `origins.json`, certitude jusqu'à `certain`.
- **Raidbots** (décision 290, `forever/pipeline/raidbots.py`) : quand le jeu n'a pas d'archive du build (utilisateur
  qui ne peut pas se connecter), le `DBCache.bin` vérifié le plus récent du build est lu dans la liste publique
  `https://www.raidbots.com/api/dbcache/verified` (celle qu'utilise wowsims/forever), téléchargé en lecture seule et
  épinglé dans `<cache>/dbcache/<build>/raidbots/` (adresse, date de création, empreinte, date du téléchargement).
  **Licence** : non déclarée. Certitude au plus `probable` (copie tierce) ; le cache du jeu de l'utilisateur prime
  dès qu'il existe. Un talent ou un sort retiré par un correctif ainsi lu est « probablement retiré » et exclu des
  recommandations (`forever/server_removed.py`).
- **Relecture** : étapes `nouvelle_version` et `correctifs` de chaque passage (révision suivante écrite d'elle-même,
  décision 295) ; une nouvelle version attend le `DBCache.bin` de son build (`hotfixes_unread`, levée seule), puis
  s'installe sans correctifs après `UPDATE_HOTFIX_WAIT` si aucune valeur `correctif_serveur` n'est perdue. À la main :
  `forever hotfixes [--dbcache F | --raidbots] [--values]`, `forever decode --version V --hotfixes [--raidbots]`.
- **`Hotfix.log`** (`Logs/Hotfix.log`, `forever/pipeline/hotfixes.py`) : index des poussées appliquées au démarrage,
  sans valeur, réécrit à chaque démarrage ; chaque ligne est gardée dans `<cache>/hotfixes.json`, qui date les
  poussées. Relu par `forever watch` et par la veille.

### Cache des quêtes du client
`Cache/WDB/<locale>/questcache.wdb` (`forever/pipeline/questcache.py`, disposition `probable`) : quêtes **vues** par le
client (niveau, requis, zone, suite, difficulté, multiplicateur d'XP, argent), archivé par build ; la veille ajoute les
quêtes nouvellement vues à `quest_rewards.json` en révision. `creaturecache.wdb` (sans PV) n'est pas lu ;
`QuestCache.log` ne contient aucune donnée.

## Mes observations

### Journaux de combat
- **Fournit** : `Logs/WoWCombatLog-*.txt` (et `.txt.gz`), format 22 avec le bloc avancé : PV max des PNJ, coûts,
  durées d'incantation, intervalles, critiques, touchés et ratés par écart de niveau, durée des combats
  (`forever/pipeline/combatlog.py`, `measure.py`, `levels.py`, `monsters.py`). Source de premier rang pour les PV des
  monstres (`certain`). L'en-tête ne donne pas le build : la version vient du journal des versions du client vues sur
  le poste (`forever/pipeline/client_builds.py`).
- **Licence** : données de l'utilisateur ; aucune donnée de tiers écrite en clair (anonymisation à la lecture).
- **Relecture** : étape `journaux` de chaque passage, sur les journaux de la version installée seulement ; un journal
  en cours d'écriture (jeu ouvert, modifié récemment) est remis au passage suivant (`live_logs.py`, décision 205) ; la
  mesure s'écrit d'elle-même en révision (décision 295). À la main : `forever logs scan | measure`,
  `forever measures refresh`, `forever monsters build`.

### ForeverLogger (notre addon)
`ForeverLoggerDB` (`WTF/Account/<COMPTE>/SavedVariables/ForeverLogger.lua`, `forever/pipeline/addon_sv.py`) :
instantanés du personnage (niveau, talents), gains d'XP, passages et butin de donjon, relevés hors combat (marchands,
réputation), sans abonnement au journal de combat ni fonction d'action (`docs/ADDON.md`). Une observation réelle
l'emporte sur une donnée d'addon et passe la certitude à `certain` ; un écart est signalé. Lu par le profil
(`forever profile import`), les mesures, `forever xp check` et `forever measures kill-time`.

### Autres sauvegardes du joueur (lecture locale)
- **Carnet de Questie** (`Questie.lua`, `journey`) : gains de niveau horodatés, repli pour le niveau du lanceur
  (`levels.py`) ; `QuestieForeverDB` : quêtes de Forever apprises en jeu (relevé du joueur, `quest_sources.py`).
- **Auctionator** (`AUCTIONATOR_PRICE_DATABASE`, `forever/pipeline/auctionator.py`, décodeur CBOR maison
  `cbor.py`) : mes relevés de prix ; le code de l'addon (« All Rights Reserved ») n'est jamais lu.
- **Export SimulationCraft** collé dans la fenêtre du pont (`forever/simc.py`) : fiche du personnage lue au client,
  source `simulationcraft`, jamais lue sur disque.
- **Profil multi-sources** (décision 125) : chaque champ garde sa source et sa date ; la plus récente l'emporte, à date
  égale la plus directe ; ce que le joueur dit l'emporte pour la réponse en cours (décision 122).

## Addons de données installés
Dossier du client : `FOREVER_WOW_DIR` ou installation choisie (`forever wow list | adopt`), lu en lecture seule.

**Suivi** : `forever/addons.py` (`DATA_ADDONS`) relève pour chaque addon la version du `.toc` et l'**empreinte de ses
fichiers de données** (la version seule ne suffit pas : AtlasLoot change de contenu à version égale, décision 124) ;
statut `nouveau`, `inchangé`, `changé` ou `absent` contre `<cache>/addons/state.json`. **Relecture** : étape `addons`
de chaque passage de la veille (`forever addons status --save`) ; Questie changé relance la mesure des journaux,
écrite d'elle-même ; un autre addon changé laisse un rappel de relecture en session (n'attend aucun accord, ne bloque
rien) ; les livres fusionnés du cache (quêtes, donjons) se rebâtissent quand un fichier lu change. `forever watch`
le signale hors ligne. **Fraîcheur par le contenu** (registre des sources) : Talents Forever et Forever Companion
(talents sans correspondance avec nos données), sinon par date ou build (poids de Naowh, SkillUp Forever).

Versions du relevé du 2026-10-21 (`docs/research/sources-addons-2026-10-21.md` ; détail des formats et relevés
antérieurs : `tasks/inventaire-addons.md`) :

| Addon | Version | Fournit | Licence | Lecteur et usage |
| --- | --- | --- | --- | --- |
| Questie | 11.38.0 Forever-v27 | quêtes, PNJ (PV, niveaux), XP des quêtes : base **Classic Era sans correction Forever** | à vérifier (aucun fichier de licence installé ; CurseForge 334372) | `questie.py`, `quest_sources.py`, `travel_sources.py` (maîtres de classe) ; `suppose` ; agrégat par niveau seulement (`monsters.json`) |
| Naowh Forever (13 dossiers) | 1.1.38 | quêtes (Completo, Journeys), journal des donjons, butin, BiS par spé, poids par défaut, trajets et transports, niveaux d'apprentissage, chaîne du sac de couchage | tous droits réservés (`LICENSE.md`) | `quest_sources.py`, `dungeon_sources.py`, `gear_sources.py`, `travel_sources.py`, `sleeping_bag.py` ; recoupement, `suppose` ; **cible d'export** |
| Forever Companion | 1.0.0 (`dataVersion` 91) | arbres et builds des neuf classes, rotations en prose, BiS, échelles de statistiques, butin des donjons | aucune | `companion.py`, `gear_sources.py`, `dungeon_sources.py` ; **cible d'export** (Pawn v1) |
| Talents Forever (`TalentsForeverBook`) | 0.38.9 (`codeVersion` 7) | arbres des neuf classes, codes de build, builds populaires datés | aucune | `forever/talents_forever.py`, `pipeline/talents_forever.py` ; codec réimplémenté (`tf_code.py`) ; le client fait foi |
| Forever Guide | 1.37.0 | quêtes et chaînes de donjon, butin, `GearData` | aucune pour le projet (briques reprises : LFG en MIT, Ace3 en BSD, cartes Atlas en GPL-2.0+) | `quest_sources.py`, `gear_sources.py` ; recoupement |
| GearQuest Forever (+ modules de classe) | 1.0.0 | choix d'équipement de leveling par plage de niveaux, récompenses par nom de quête | aucune | `gear_sources.py`, `quest_sources.py` ; recoupement seulement |
| ForeverDungeonJournal | 1.6.5 | donjons, boss, butin, quêtes de donjon et leur XP | aucune ; données de sites tiers (`SOURCES.txt`) | `quest_sources.py`, `dungeon_sources.py` |
| AtlasLoot Classic Forever (+ modules) | Forever 1.60.1 (contenu suivi par empreinte) | butin par boss, taux Classic | GPL-2 | `dungeon_sources.py` ; taux Classic dits comme tels |
| AtlasBIStooltips | 1.0.1 | listes BiS par spécialisation | aucune | suivi seulement (lecteur prévu en T10a) |
| Forever Bestiary | 0.7.0 | familles, capacités et rangs, bêtes apprivoisables, carte communautaire datée ; `ForeverBestiaryDB` (mes observations) | aucune | `bestiary.py`, anonymisation par liste blanche ; le client fait foi (`forever pets crosscheck`) ; `pet_rules.json` relu en session |
| SkillUp Forever | 0.18.6 | seuils des recettes, métiers (données du build nommé) | GPL-3.0-or-later | `skillup.py` ; assistant « Métier » du pont ; `/skillup` calcule en jeu |
| Shortest Path Forever | 1.21.5 | trajets, transports, portails (générés du client) | GPL-3.0-or-later | suivi ; lecteur à venir |
| Legacy Forever | 0.11.3 | défis et points Legacy (générés du client) | GPL-3.0-or-later | suivi ; lecteur à venir (LG1) |
| Zone Info: Forever | 1.9.1 | plages de niveau des zones et donjons (plages classiques) | aucune | `dungeon_sources.py` |
| FojjiCore et modules | absent au 2026-10-21 | rangs de sorts, journal des donjons, sac de couchage | cœur « tous droits réservés », modules sans licence | relu s'il revient ; recoupement seulement |
| Auctionator | 341 | mes prix (SavedVariables) | All Rights Reserved | `auctionator.py`, code jamais lu |

- **Exclus** (connus, jamais lus comme source, `EXCLUDED_ADDONS`) : RXPGuides comme base de données (ses parcours
  gratuits sont lus à part, plus bas), Tamed (tables de Forever vides), AlexAtlasLoot (licence qui interdit la copie
  de ses tables, décision 229).
- **Interface seule** : SimulationCraft (Unlicense, export collé seulement), EllesmereUI (cible d'export sur demande,
  décision 274), addons sans données utiles (`docs/research/sources-addons-2026-10-21.md`).
- **Nos addons** (`OWN_ADDONS`, jamais sources communautaires) : ForeverLogger, ForeverBridge et sa réserve
  d'emplacements, RaphCompletionist (addon de l'utilisateur). `ForeverCompletionist` n'est pas un addon (`NOT_ADDONS`).
- **Seulement des addons à jour pour Forever** (version Forever explicite, données postérieures à la version jouée) ;
  un addon périmé est signalé par le registre des sources et cesse d'être pris en premier.

## Parcours de leveling maintenus

### RestedXP : parcours gratuits en clair
- **Fournit** : les guides gratuits de `RXPGuides/Guides/Forever/*.lua` (et `dungeon/` sur demande) de l'addon
  installé (4.11.26 au 2026-10-21), lus par `forever/rxp_guides.py` : mesure de nos routes, référence de
  l'optimiseur et base adaptée là où ils font mieux (décisions 268 et 277), acceptation automatique d'une feuille de
  route qui leur ressemble (`forever/route_check.py`, décision 279). Syntaxe des guides relevée dans son code
  (`forever/rxp.py`) ; livraison de nos routes par son API publique (`RXPGuides.ImportGuide`, décision 253).
- **Licence** : CC BY-NC-SA 4.0 (`LICENSE` de l'addon) : usage personnel et non commercial, attribution ; leur texte
  n'entre jamais dans le dépôt. Les guides payants et les bases de l'addon ne sont jamais lus.
- **Fraîcheur et relecture** : relus à chaque appel (`forever route plan | compare | rxp-compare | rxp-coverage`) ;
  version suivie comme addon installé.

### Polestar : au-delà de RestedXP
- **Fournit** : les fichiers `.guide` de la catégorie Leveling, squelette des routes au-delà des parcours gratuits de
  RestedXP (décision 289), lus par `forever/polestar.py` dans un clone en cache `<cache>/third_party/polestar`
  (`https://github.com/fitzforge/polestar.git`, `forever/pipeline/polestar_fetch.py`). L'addon n'est jamais installé
  ni exécuté ; ses règles de jeu restent `suppose`, sa règle sur les donjons n'est pas reprise.
- **Licence** : GPL-3.0 ; utilisation et modification privées, attribution (commit épinglé) dans chaque route livrée,
  rien redistribué ni copié dans le dépôt.
- **Fraîcheur et relecture** : commit du clone dans la provenance ; créé une fois par `forever route polestar`, puis
  remis sur le dernier commit à l'étape `guides` de chaque passage (git limité à `STEP_GIT_TIMEOUT_S` ; injoignable :
  copie gardée, nouvel essai au passage suivant).

### Factoruide : recoupement
`brouznouf/factoruide` (code MIT ; base `data/forever.sqlite.zst` sous GPL-2.0+ pour la part VMaNGOS, données de
Questie sans licence et de Wowhead Forever), cloné hors du dépôt à `FACTORUIDE_COMMIT` (`f7da6da`), base décompressée
dans le cache (`forever/pipeline/factoruide.py`). Sert à mesurer les écarts de notre livre des quêtes
(`forever quests diff --factoruide`, statut « vue seulement chez Factoruide », `suppose`) ; algorithmes de route portés
et cités (`forever/optimize/route.py`). Relu à la main seulement ; jamais téléchargé par la veille.

## Simulateur de la communauté

### wowsims/forever (référence au niveau 60)
- **Fournit** : dégâts par seconde de fin de partie, poids des statistiques par tirages appariés, comparaison des races
  et des classes, préréglages par spécialisation (`ui/specs/<classe>/<spé>/`), neuf classes, **niveau 60 seulement**
  (constante de son code). Adaptateur `forever/sims/wowsims.py` (requête `RaidSimRequest` en protojson, binaire lancé
  en local sans réseau, résultat lu), réponses `forever/sims/report.py` (`forever sims presets | races`,
  `forever_simulate`), poids de `forever gear` au niveau 60.
- **Licence** : MIT, lien de retour demandé (`docs/research/simulateurs-2026-10-21.md`). Code utilisé tel quel, sans
  modification (décision 294).
- **Fraîcheur** : le projet ne publie pas de binaire : compilé chez nous (`forever/pipeline/wowsims_build.py`, clone
  superficiel `<cache>/third_party/wowsims/forever`, protobuf, `go build` de `cmd/wowsimcli`), épinglé dans `pin.json`
  (commit, date, empreinte, versions de Go et de protoc) ; le registre des sources date le commit contre la
  publication du build installé. Certitude `suppose`.
- **Relecture** : première compilation par `forever sims update` ; puis étape `simulateurs` de chaque passage :
  recompilation au nouveau commit (git `GIT_TIMEOUT_S`, compilation `TIMEOUT_S`), cas de référence rejoués, écarts
  notés dans `veille.json` ; échec : binaire précédent gardé.

### Simulateurs relus à la main seulement
Sims Forever (site sans licence déclarée ; addon exportateur MIT), DPS Forever (aucune licence, code fermé), ForeverDB
(code fermé, API de données avec clé et crédit obligatoire), MythicSim (MIT, fork de wowsims, en retard d'une version) :
pas d'API utilisable ou `robots.txt` qui interdit leurs `/api/` ; références de recoupement relues à la main
(`docs/research/simulateurs-2026-10-21.md`). Le dépôt `ElliotWood/Forever` n'existe plus (décision 291) : les
reprises de formules prévues par les décisions 233 et 234 sont remplacées par la décision 293 (aucun nouveau code de
calcul).

## Notre calcul gelé
Le moteur du Mage (`forever/engine/`) est gelé à la révision 7 de 1.60.1.70450 (décisions 293 et 294) : seul calcul
sous le niveau 60, recoupé par les journaux de combat, dit comme tel dans chaque réponse. Ses entrées viennent du
client ; les constantes absentes du client vivent dans `mechanics.json` avec leur origine et leur certitude ; celles
qui viennent de la Classic sont recensées (`forever/classic.py`) et remplacées après la sortie par les mesures de
l'utilisateur.

## Signaux officiels

### Notes du forum de Blizzard (décision 148)
Catégories de la bêta et de la discussion générale de Forever (Discourse), lues par `forever notes`
(`forever/pipeline/notes.py`) **à la main seulement** (ou proposé par `forever watch` quand le build du client change ;
workflow `notes-watch` en `workflow_dispatch`), une fois par jour au plus, `robots.txt` relu à chaque passage. Textes
sous CC BY-NC-SA 3.0, jamais recopiés : la sortie nomme l'adresse, les dates et les entités reconnues. Rang : **signal**,
jamais une valeur ; une règle sans autre source peut passer de `suppose` à `probable` par un texte officiel, seule la
mesure donne `certain`. Le sujet « Known Issues » liste des bugs reconnus : jamais modélisés.

### API Blizzard (décisions 126 et 149)
`forever api probe` (`forever/pipeline/blizzard_api.py`, workflow `api-probe` quotidien, clés dans les secrets du
dépôt ou `.env`) sonde les seuls espaces de noms candidats de Forever ; aucun espace de Retail ni de Classic. Une issue
`api-blizzard` s'ouvre dès qu'un espace répond, pour décider du démarrage d'EC1 (prix, fiches, PvP). Conditions des API
de Blizzard ; tout nouvel accès réseau attend l'accord de l'utilisateur.

### Wowhead Forever : contrôle, jamais vérité (décision 128)
Consultation ponctuelle par le sous-agent `forever-web-researcher` (adresse et date citées), pour contrôler une valeur
décodée. Divergence avec le client : **alerte**, pas un arbitrage (vérifier d'abord les correctifs du serveur, puis mes
journaux ; sinon question dans `docs/OPEN_QUESTIONS.md`). **Aucune aspiration** : aucun code du dépôt ne lit Wowhead.

## Addons pilotés : exports de forever-core (décision 196)
Un export se fait vers un addon qui a un point d'import ; sinon notre addon affiche la donnée. Le code des addons
n'est jamais modifié ni recopié : formats réimplémentés d'après leur description (`forever/exports/`, `tf_code.py`).

| Donnée calculée | Addon cible | Point d'import | Tranche |
| --- | --- | --- | --- |
| Build de talents | Talents Forever | code et lien | FA1 |
| Build de talents | Naowh Forever | chaîne `!NFB1!` | EX1 |
| Liste BiS par personnage et par contexte | Naowh Forever | chaîne `!NBIS1!` | CJ1 bloc 4, T10 |
| Poids des statistiques | Naowh Forever | ligne `NFSW1:` | CJ1 bloc 4, T10 |
| Poids des statistiques | Forever Companion | échelle texte Pawn v1 (« Import scale… ») | CJ1 bloc 4 |
| Feuille de route | RestedXP | `RXPGuides.ImportGuide`, groupe « Forever Routes » ; repli jeu fermé | RX1, CJ1 |
| Macros par classe | Naowh Forever | chaîne `!NFM1!` | EX1 |
| Profil d'interface par personnage et par rôle | EllesmereUI | chaîne `!EUI_`, **sur demande seulement** (décision 274) | EX1, CJ1 bloc 5 |
| Conversation, boutons, cartes | ForeverBridge (notre addon) | pont de P06a et P06b | P06a, P06b |

## Données manquantes et addons candidats (décision 131)
Quand une donnée manque pour répondre (angle mort, valeur supposée, domaine non couvert, taux de Classic au lieu de
Forever), l'agent cherche un addon de Forever qui l'embarque ou la collecte et **propose de l'installer** (donnée
apportée, effet sur la réponse, lien, version, date, licence, compatibilité Forever, stabilité). **Il ne télécharge ni
n'installe rien** ; une fois l'addon installé, il l'inventorie en lecture seule (`forever addons status`,
`tasks/inventaire-addons.md`) et l'ajoute ici.

**Recherche du 2026-09-30** (sources communautaires : CurseForge, GitHub, <https://foreverchanges.pro/addons>).
Limites : compatibilité lue sur l'étiquette « 1.60.1 » de CurseForge sauf mention ; stabilité non vérifiée ; un
collecteur ne vaut que si ses SavedVariables sont relues d'une session à l'autre et s'il ne dépend ni du journal de
combat ni d'une valeur secrète ; licence sans effet sur la lecture locale (décision 133). Les addons conseillés alors
(Forever Guide, Legacy Forever, Zone Level: Forever, mise à jour d'AtlasLoot) sont installés depuis.

| Donnée manquante | Où elle manque | Candidat |
|---|---|---|
| PV des monstres de Forever hors des zones mesurées | H11, `hp_by_level` | **Aucun addon qui embarque des PV de Forever (2026-09-30).** Collecteur : MobInfo2 (MIT ; lectures de PV annoncées secrètes par son auteur). Source retenue : mes journaux |
| XP des monstres de Forever | T04d | **Aucune base trouvée (2026-09-30).** Collecteur : MobInfo2 (méthode non vérifiée) ; MyXPBar Forever (All Rights Reserved) : estimation, pas de base par monstre |
| Taux de butin de Forever | DJ1, T10 | **Aucune table Forever (2026-09-30)** ; Forever Guide reprend les taux Classic. Collecteurs : KillDex (All Rights Reserved, rien en donjon), MobInfo2. AtlasLoot : taux Classic, `suppose` |
| Butin des donjons et raids Forever | DJ1 | ForeverDungeonJournal, AtlasLoot, Naowh Forever, Forever Companion (installés, incomplets). Candidats : Atlas Forever (GPLv2), Forever Atlas (GPLv2) |
| Niveaux des boss et plages des donjons | DJ1, H1 | client (`dungeons.json`), addons installés (contradictoires). Candidats : Forever Map Levels (All Rights Reserved). Mesure : mes journaux |
| Quêtes propres à Forever et leur XP | T04d | Installés : `QuestieForeverDB`, Naowh Forever, Forever Guide, ForeverDungeonJournal, GearQuestForever ; `questcache.wdb` du client. Candidats : xeR's Forever Level Journal (MIT), Dungeon Quest, Dungeon Quests Forever (All Rights Reserved) ; AllTheThings (MIT, base Forever propre) non installé au 2026-10-14 |
| Couleurs de quête de Forever | I7 | **Aucun addon qui embarque les plages de Forever (2026-09-30).** Relevé possible par ForeverLogger |
| Prix de l'hôtel des ventes | EC1, T10, MT1 | Auctionator (mes relevés) ; AHledger (All Rights Reserved) ; API Blizzard après le lancement |
| Objets et prix des marchands | T10, MT1 | Auctionator (prix marchands), relevé ForeverLogger ; Recipe Registry (MIT) |
| Gains de réputation par source | RP1 | **Aucune base trouvée (2026-09-30).** Collecteurs : Forever Journal (MIT), Saga (MIT) ; relevé ForeverLogger |
| Récompenses de réputation par palier | RP1, T10 | **Aucun trouvé (2026-09-30).** Relevé chez les intendants |
| Entraîneurs, sources de recettes | MT1 | SkillUp Forever (installé ; frais d'entraîneur et sources de recettes tirés de CMaNGOS Classic), Recipe Registry (MIT), TrainForever (MIT) |
| Chance de gain d'un point de métier | MT1 | **Aucune règle Forever trouvée (2026-09-30).** Mesure en jeu |
| Catalogue Legacy | LG1, G5 | Legacy Forever (installé, tiré du client). Arbres de bonus : **aucun addon trouvé (2026-09-30)** |
| Progression Legacy du compte | LG2 | Legacy Forever (`LegacyForeverDB`, contenu non vérifié) |
| Honneur, rang et classements PvP | PV2, LG2 | **Aucun suivi Forever trouvé (2026-09-30).** API Blizzard après le lancement |
| Rendements décroissants de Forever | PV2 | **Aucun trouvé (2026-09-30)** ; un suivi en direct lirait le journal de combat, refusé aux addons. Mesure : mes journaux |
| Buffs de campement | D5, T11 | Campfire Tooltips (GPLv3), CampingInfo (MIT) |
| Buffs mondiaux, buffs de Legacy, conditions de zone des flacons | D3, D5, E1 | **Aucun trouvé (2026-09-30)** |
| Armure et résistances des monstres | H2 | **Aucun trouvé (2026-09-30)** |
| Statistiques des objets de Forever | T10, F1 | tables du client ; GearQuestForever en recoupement |
| Familiers du Chasseur : bêtes par rang, héritage des statistiques, gain des points d'entraînement | CH0, CH1 | Forever Bestiary (installé) ; héritage et vitesse : mesure dans mes journaux (protocole de CH0) |

Écartés : addons sans version Forever (Exalted, RepMatic, GrindPlus, HonorSpy, Rank Marshal, What's Crafting?,
WhatItDrops…), ForeverQuest (base Classic, licence incohérente), ForeverWisp (quêtes Classic-DB), AtlasLootClassic
Continued (donjons Forever en attente).
