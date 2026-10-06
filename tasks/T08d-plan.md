# T08d — Mise à jour automatique des données : plan

Demande de l'utilisateur du 2026-10-06 (commande `/tranche T08d`, 6 points). La tranche n'existe pas encore dans
`docs/ROADMAP.md` : sa section, sa ligne de table (après T08c, avant FA1, dépend de T08c) et ses décisions
(numéros 178 et suivants) sont écrites au bloc 0. Objectif : quand le jeu change de version, reçoit des correctifs
du serveur, ou quand un addon de données change, les données du projet suivent **sans session manuelle**, et
l'outil ne s'arrête que si un résultat change pour l'utilisateur. Plan écrit sans code. Exécution dans une nouvelle
session, sur la branche `t08d`, avec un cycle rouge → vert par bloc.

## Questions décisives et réponses (2026-10-06)

1. **Premier cas réel : 1.60.1.70235, et non 70205.** Le client est passé en 70235 le 2026-10-05 à 23:40:36 UTC.
   Le `DBCache.bin` de 70205 a été réécrit en 70235 le 2026-10-06 à 07:42, pendant le plan : il est perdu. 70205
   est sautée, comme 70058, et notée « jamais installée ». **Ajout de l'utilisateur** : la veille locale copie
   automatiquement `DBCache.bin` **et** `Logs/Hotfix.log` dans le cache du projet, rangés par version, dès qu'ils
   changent. Elle le fait à chaque démarrage de session et par la tâche planifiée, même si aucune installation n'est
   lancée (bloc A).
2. **Talents Forever réinstallé par l'utilisateur** (0.37.1, voir le contexte). **Forever Companion** sert aussi de
   second témoin : DON13 est recoupé avec les deux.
3. **Git** : une écriture autorisée par la règle d'automatisme suit ce chemin : commit sur une branche
   `data/<version>-r<N>`, poussée, CI attendue sous Ubuntu et Windows, fusion en avance rapide dans `main`, poussée
   de `main`, puis suppression de la branche locale et distante. Garde-fous :
    - **Avant tout**, récupérer `main` distant. Si la version ou la révision visée y est déjà installée (par l'autre
      PC de l'utilisateur ou par une session), mettre seulement `main` local à jour : rien n'est recalculé ni poussé.
    - **Jamais de poussée forcée.** Si la fusion en avance rapide échoue parce que `main` distant a bougé entre-temps,
      l'outil s'arrête et le signale.
    - Refus si l'arbre de travail est sale ou si la branche courante n'est pas `main`.
4. **Déclenchement** : `forever update --auto` est lancé en arrière-plan, avec un verrou, sans bloquer la session ;
   la tâche planifiée lance la même commande. La ligne de démarrage montre le dernier passage et ce qui attend
   l'accord de l'utilisateur. **Condition de l'utilisateur** : le passage automatique ne touche jamais l'arbre de
   travail de sa session. Il travaille dans un **clone dédié du dépôt**, rangé dans le cache du projet (pas de
   worktree, à cause des verrous de fichiers sous Windows). Branche, commit, CI, fusion et poussée se font depuis ce
   clone. La session récupère ensuite les données par un simple `git pull`, que la ligne de démarrage propose quand
   `main` distant a avancé.

### Points à confirmer à la validation du plan (choix par défaut écrits)

- **Accord réseau permanent** (décision 179) : il couvre ce que demande la commande, c'est-à-dire wago.tools pour
  une version : liste des builds (`forever builds`), tables CSV et GameTables (`forever fetch`). Il couvre aussi
  `forever status` et les opérations git et `gh` du clone dédié (`fetch`, `push`, CI). **Par défaut, il ne couvre
  pas WoWDBDefs** (GitHub, `forever fetch --dbd`) : un nouveau build qui a besoin de dispositions pour appliquer ses
  correctifs crée une attente d'accord de type `network_dbd`. Il suffit d'un mot à la validation pour l'inclure.
- **Commit fait par l'outil** : message `Veille : <version> r<N> installée par forever update (<motif>)`, sans ligne
  d'attribution à Claude (l'auteur est l'outil, sous l'identité git du poste).
- **Seuils de l'outil** (paramètres de `forever/config.py`, pas des chiffres de jeu) :
    - au démarrage, un passage automatique au plus toutes les 6 h (`CACHE_TTL`) ;
    - un verrou est déclaré périmé après 3 h ;
    - l'attente de la CI s'arrête au bout de 60 min ;
    - la tâche planifiée est limitée à 2 h (au lieu de 10 min).

## Contexte relevé pendant le plan (lecture locale seulement, aucun réseau)

- **Client** : `.build.info` donne 1.60.1.70235, mis à jour le 2026-10-05 à 23:40:36 UTC. Le journal
  `client_builds.json` s'arrête à 70170 : **70205 n'a jamais été relevé**, faute de lecture des journaux pendant sa
  vie. Il reste deux traces de 70205 :
    - les **1 196 lignes** de `<cache>/hotfixes.json` marquées `client_build` 1.60.1.70205 (la plus ancienne date la
      mise à jour, comme dans la décision 167) ;
    - deux journaux de combat du 05/10 (`WoWCombatLog-100526_073349.txt` et `…_173059.txt`).
- **`DBCache.bin`** :
    - à 07:41, le fichier de 9,7 Mo du 05/10 18:07 était celui de 70205 (la veille le signalait « d'un autre build ») ;
    - à 07:42:33, le client l'a remplacé par un fichier de build 70235 : 2 986 362 octets, 29 283 entrées, sha256
      `c38deba0acac…`, poussées réelles jusqu'à 112426 ;
    - ce fichier a été copié dans `<cache>/dbcache/70235/DBCache.bin` (convention de la décision 176), mais **le
      client tournait encore** : la copie sera remplacée par l'archivage du bloc A quand le fichier changera ;
    - la copie de 70170 (`<cache>/dbcache/70170/`) est intacte.
- `forever watch` a été lancé une fois pendant le plan. Son état (`<cache>/watch/state.json`) a donc déjà consommé
  l'évènement « client 70235 » : la ligne de démarrage ne le montrera plus.
- **wago.tools** : le dernier relevé de `status.json` date du 2026-10-02 (dernier build : 70170). On ne sait pas
  encore si 70205 et 70235 y sont publiées : aucun réseau en session de plan, c'est un risque listé plus bas.
- **Révisions faites à la main** (sans commande, champ `manual_changes`) : 70124 r6 (marge d'apprivoisement) et
  70170 r3 (note officielle : `coefficient.low_level_default`, `pet_rules.json` `official_fixes`). Les valeurs
  `manuel` sont déclarées dans `origins.json` (`forever origins inventory`). Les mesures des journaux (70170 r2,
  origine `journal`) sont elles aussi des valeurs qui ne viennent pas du décodage.
- **Preuve d'entrées identiques** : elle n'existe qu'à la main, dans `docs/research/data-1.60.1.70170-r4.md`
  (relevé instrumenté de `VersionData.read_json`, puis empreintes fichier par fichier, et de `classes.Mage` en
  forme canonique). Le moteur du Mage lit `character_scaling.json`, `decode_rules.json`, `leveling.json`,
  `mechanics.json`, `meta.json`, `monsters.json`, `races.json`, `respec.json`, `spell_scaling.json`, `spells.json`,
  `talents.json` et `classes.Mage.spells`.
- **Talents Forever 0.37.1**, réinstallé à 07:49 : `Data.lua` du build **1.60.1.70170**, généré le **2026-10-04**,
  **`codeVersion` "6"** (FA1 prévoit le format v5 : à signaler à FA1). Il n'était pas suivi par
  `forever addons status` (FA1 devait l'y ajouter, décision 172).
- **Forever Companion 1.0.0** (nouveau) :
    - `.toc` : interface 16001, SavedVariable `ForeverCompanionDB`, aucune licence (ni fichier ni `X-License`) ;
    - données générées par « Forever Companion Studio » (`Data/Meta.lua` : `dataVersion` 79, `updated` 2026-10-05) :
      `Bis.lua`, `Rotations.lua`, `Consumes.lua`, `Talents.lua`, `Loot.lua`, `Professions.lua`, `Dictionary.lua` ;
    - les talents y sont décrits par sort, rangée, colonne et rangs, **sans identifiant de nœud** : pour DON13, il ne
      peut témoigner que du sort, de la position et des rangs ;
    - il porte la refonte du Guerrier : Lingering Rage, Furious Precision, Gore Drinker, et Iron Will déplacé.
- **Addons du poste, comparés à la liste de l'utilisateur et à `tasks/inventaire-addons.md`** (versions du `.toc` ;
  `forever addons status` lancé sans `--save`, l'état du 2026-10-01 est gardé) :

| Addon (dossier) | Version | Liste de l'utilisateur | Suivi aujourd'hui | Classement proposé | Depuis le 2026-10-01 |
| --- | --- | --- | --- | --- | --- |
| AtlasLootClassic (+ modules) | `.toc` `Forever 1.60.1` | 1.1.9 (CurseForge) | oui | données | changé (2 fichiers) |
| Auctionator | 340 | 340 | oui | données (mes prix) | changé (339 → 340) |
| ForeverDungeonJournal | 1.5.2 | 1.5.2 | oui | données | changé (1.3.3 → 1.5.2) |
| ForeverBestiary | 0.5.0 | 0.5.0 | oui | données | inchangé |
| ForeverGuide | 1.25.3 | 1.25.3 | oui | données | changé (1.17.0 → 1.25.3) |
| GearQuestForever (+ 9 modules) | 0.3.5-beta | 0.3.5-beta | oui | données (recoupement) | changé (0.2.20 → 0.3.5) |
| LegacyForever | v0.6.12 | 0.6.12 | oui | données | changé (v0.6.7 → v0.6.12) |
| Questie | 11.38.0 Forever-v27 | v27 | oui | données | inchangé |
| ZoneLevelForever | 1.5 | 1.5 | oui | données | changé (1.4 → 1.5) |
| ForeverLogger | 0.3.0 | — (le nôtre) | oui | relevés | changé (0.2.0 → 0.3.0) |
| **TalentsForeverBook** | 0.37.1 | Talents Forever | **non** | données (à suivre, avancé de FA1) | — |
| **ForeverCompanion** | 1.0.0 | nouveau | **non** | données : **inventaire proposé en premier** | — |
| **NaowhForever** (+ 12 modules : BiS, DungeonJournal, Training, Professions…) | 0.5.22-beta | 0.5.22-beta | non | données probables : inventaire proposé en second | — |
| AtlasBIStooltips | 1.0.1 | absent de la liste | non | données probables (BiS) : inventaire proposé | — |
| RXPGuides | v4.11.15 | absent de la liste | non | guides : inventaire proposé (basse priorité) | — |
| EllesmereUI (+ 20 modules) | 9.3.8 | 9.3.8 | non | **interface seule**, noté sans lecture | — |
| Leatrix_Maps | 1.60.13 | 1.60.13 | non | **interface seule**, noté sans lecture | — |
| ForeverMapFix | 0.2.0 | 0.2.0 | non | **interface seule**, noté sans lecture | — |
| RaphCompletionist | 0.2.1 | absent de la liste | non | à classer par l'utilisateur (son addon ?) | — |
| ForeverCompletionist | — (pas de `.toc`) | absent de la liste | non | **pas un addon** (dossier de travail : `tests/`, `source_importers/`) | — |

  Sauvegardes présentes sans leur addon (désinstallé) : `AllTheThings`, `QuestMaster`, `XLoot`,
  `CraftingOrderClassic` ; elles ne sont pas lues.

## Choix d'architecture (sans question)

- **Où vit le code** :
    - `forever/update.py` : orchestrateur. Il enchaîne des fonctions existantes, sans aucun calcul de combat.
    - `forever/pipeline/gitops.py` : git et `gh`, par un exécuteur injectable. C'est du réseau, donc il est dans
      `pipeline/`, comme `fetch.py`.
    - `forever/archive.py` : archivage des fichiers du client, local seulement.
    - `forever/engine_inputs.py` : empreinte des entrées des moteurs.
    - `forever/carry.py` : report des changements faits à la main.
  Les tests ne touchent jamais le réseau : `http_get` est simulé, et git tourne sur un dépôt nu local comme
  `origin`. `gh` est toujours simulé.
- **Une étape = un enregistrement** `Step(name, status, detail, data)`. Statuts :
    - `fait` ;
    - `rien` (rien à faire) ;
    - `attente` (accord requis, une entrée en attente créée) ;
    - `arrêt` (garde-fou : arbre sale, poussée refusée, verrou pris) ;
    - `erreur` (exception de forever, avec son code).

  Le rapport (`UpdateReport`) porte les étapes, le verdict de la règle, les écritures faites, les attentes et la
  provenance. Sorties : texte en français, ou JSON avec `--json` (schéma versionné, `schema_version` 1).
- **Ordre de la chaîne** (`forever update`) :
    0. Verrou `<cache>/update/lock` (PID, heure, commande). Un verrou vivant fait sortir avec « déjà en cours » ; un
       verrou périmé est repris et signalé.
    1. **Archivage** des fichiers du client (bloc A), toujours, même hors ligne.
    2. **Clone dédié** `<cache>/update/repo` :
        - créé au premier passage par `git clone <url d'origin du dépôt>` ;
        - puis `git fetch origin`, contrôle de l'arbre (propre, sur `main`) et `git merge --ff-only origin/main` ;
        - environnement par `uv sync --frozen --offline` : en cas d'échec, arrêt avec la commande à lancer à la main
          (le réseau de PyPI n'est pas dans l'accord) ;
        - toutes les commandes `forever` qui écrivent tournent **dans le clone** (`uv run --project <clone>`), avec le
          même cache (`FOREVER_CACHE_DIR`) et le même dossier du client.
    3. **Jeu** :
        - build du client (`.build.info`), versions installées du clone (`version_dirs`), builds publiés
          (`forever builds`, réseau) ;
        - **cible = build du client** s'il est publié sur wago (règle de T08a : les données suivent le client joué) ;
        - un build de wago plus récent que le client est seulement signalé (c'est la PR de `build-watch.yml` qui le
          suit) ;
        - un build du client absent de wago donne une étape `rien` (« en attente de wago »).
    4. **Distant déjà à jour** : si `origin/main` porte déjà la version (ou la révision) visée, le clone est seulement
       avancé, et le rapport dit « installée ailleurs : `git pull` dans la session ».
    5. **Nouvelle version** :
        - `fetch` (tables et GameTables, réseau accordé) ;
        - `decode --hotfixes`, si `<cache>/dbcache/<build>/DBCache.bin` existe et porte des entrées applicables ;
        - `verify` de la candidate, **bloquant** ici (à la différence de la CI) ;
        - `diff`, `report` ;
        - **report des changements faits à la main** (bloc C) ;
        - **preuve d'entrées** (bloc B) ;
        - règle, puis écriture ou attente.
    6. **Correctifs du serveur** (version installée = build du client) : correctifs applicables non appliqués
       (`watch._dbcache_event`, déplacé dans une fonction réutilisable) → `decode --hotfixes` → même suite → révision
       suivante.
    7. **Journaux** : sessions nouvelles de la version installée seulement (règle de T08a). `forever logs measure`,
       puis `forever measures refresh` **en simulation** (rien écrit). Une mesure qui change une valeur lue par un
       moteur crée une attente ; les sessions d'une autre version sont listées « en attente ».
    8. **Addons de données** (bloc D) : `addons status` puis relecture par les lecteurs existants. Le relevé du cache
       est enregistré (`--save`, hors dépôt). Un changement qui touche un agrégat du dépôt (`depends`) crée une
       attente. Un addon présent non inventorié donne une proposition d'inventaire. Les addons d'interface sont notés
       sans lecture.
    9. **Fin** : preuve d'entrées par moteur pour chaque écriture faite, ou rejeu ciblé (bloc B) dans le rapport.
       Rapport écrit dans `<cache>/update/last.json` (et `report-<horodatage>.json`). Un historique des passages
       garde les 30 derniers.
- **Règle d'automatisme** (`decide(...)`, pure, testée par table). Une écriture se fait seulement si les trois
  conditions sont vraies :
    - (a) `verify` est vert : `verify` de la candidate, puis `uv run tasks.py verify` dans le clone après
      l'installation et avant le commit ;
    - (b) aucun changement fait à la main n'est perdu (bloc C : ni `perdu` ni `remplacé`) ;
    - (c) les entrées de chaque moteur calculé sont identiques (bloc B).

  Sinon, attente d'accord, avec le rapport et le rejeu ciblé (les recommandations qui changeraient). Un `verify`
  rouge n'est **jamais approuvable** : il demande une session. Un changement à la main `perdu` (disparu sans
  explication) n'est pas approuvable non plus. Un changement `remplacé` (le client donne désormais une autre valeur)
  est approuvable : la valeur du client l'emporte, et l'entrée `manuel` est retirée avec sa raison dans la révision.
- **Approbation différée** :
    - `<cache>/update/pending/<id>.json` porte :
        - l'identifiant (`<version>-r<N>-<sha12 de la candidate>`) et le type (`install_version`,
          `install_revision`, `measures`, `addon_data`, `network_dbd`) ;
        - les clauses non tenues, les chemins du rapport et de la candidate, et l'empreinte de la candidate ;
        - la base : `origin/main`, version et révision installées, build du client ;
        - les commandes qui seront lancées, et l'état (`en_attente`, `approuvée`, `rejetée`, `périmée`, `faite`).
    - Commandes :
        - `forever update status [--json]` liste les attentes ;
        - `forever update approve <id> [--wait] [--json]` contrôle que la base n'a pas bougé (sinon `périmée`, et le
          prochain passage recalcule), marque l'entrée `approuvée` et lance un passage détaché (`--wait` : dans le
          processus courant). Le passage consomme les entrées approuvées et n'applique que ce qui y est écrit ;
        - `forever update reject <id> [--reason TEXTE]`.
    - Le pont en jeu de P06 n'a besoin que de `status --json` et `approve <id> --json` : réponse immédiate, travail en
      arrière-plan.
    - Nouveau code de sortie `EXIT_PENDING = 6` : passage fini avec au moins une attente. `0` : rien ou fait. Les
      erreurs gardent les codes existants (`5` réseau…).
- **Provenance des révisions automatiques** : `revisions.json` porte `command` (`forever update --auto`), `automated:
  true`, le verdict de la règle (trois clauses avec leur preuve : empreintes des entrées par moteur, comptes du
  report à la main) et l'identifiant de l'approbation s'il y en a une. Le rapport
  `docs/research/data-<version>-r<N>.md` est généré (`render_install_report`, plus les sections « Report à la main »
  et « Entrées des moteurs ») et committé avec les données.

## Blocs et étapes

**Première action de la session d'exécution**, avant tout test sur les données réelles, tout
`forever measures refresh` et tout `forever update` : inscrire 70205 dans `client_builds.json`, avec la date de sa
première ligne de `hotfixes.json` (source citée). Le journal saute aujourd'hui de 70170 (02/10) à 70235 (05/10,
23:40 UTC) : `version_at` attribuerait donc à **70170** les deux journaux du 05/10, qui viennent de 70205, et une
mesure les écrirait dans les données de 70170. Jusque-là, `forever measures refresh` ne doit pas être lancé.

Ordre : 0, A, B, C, D, E, F, G, H. A, B, C et D sont indépendants ; E en dépend, F dépend de E, G de E et F, et H de
tout. Chaque bloc testé suit le cycle : tests rouges committés (« T08d: tests (bloc X) »), `tasks/.rouge` et
`tasks/.tests-verrouilles` réécrits, puis vert (« T08d: bloc X vert »), et ces fichiers supprimés.

### Bloc 0 — Feuille de route et décisions (sans test)

1. `docs/ROADMAP.md` :
    - ligne de table T08d après T08c (« Mise à jour automatique des données : `forever update`, archivage des
      fichiers du client, règle d'automatisme, approbation différée, clone dédié », dépend de T08c) ;
    - section T08d (Fait, Sources, Hors périmètre, Critères de fin, renvoi à ce plan) ;
    - section T08 : ce qui en est avancé (versions des addons de données, relecture et note de changement, chaîne
      automatique).
2. `docs/DECISIONS.md` :
    - 178 : tranche T08d et place dans l'ordre ;
    - 179 : accord réseau permanent pour wago.tools, l'état du jeu et git du clone dédié (portée exacte, WoWDBDefs
      exclu par défaut) ;
    - 180 : règle d'automatisme et approbation différée ;
    - 181 : clone dédié, chemin git, garde-fous des deux PC, jamais de poussée forcée ;
    - 182 : archivage de `DBCache.bin` et `Hotfix.log` par build ;
    - 183 : 70205 sautée, avec la date de sa mise à jour tirée de `hotfixes.json`.

### Bloc A — Archivage des fichiers du client par version (réponse 1)

1. `forever/archive.py`, appelé par `forever watch`, par le hook de démarrage et par `forever update` :
    - `DBCache.bin` (`Cache/ADB/<locale>/`, `enUS` par défaut) :
        - lu en entier puis contrôlé par `dbcache.parse_dbcache` : un fichier illisible ou tronqué (copie pendant
          une écriture) n'est **pas** archivé, et il est réessayé au passage suivant ;
        - la version vient de **l'en-tête** (`build`), sous la forme `<cache>/dbcache/<build>/DBCache.bin` ;
        - à la première copie d'un contenu différent pour le même build, l'ancien est gardé en
          `DBCache-<sha12>.bin`. Rien n'est jamais effacé ;
        - un index `<cache>/dbcache/<build>/index.json` liste chaque copie : sha256, taille, date du fichier, date de
          copie, nombre d'entrées, poussée maximale.
    - `Logs/Hotfix.log` : il est réécrit à chaque démarrage du client, puis **grossit pendant la session** (les
      poussées et les réponses `DBReply` arrivent en jeu). On garde donc une copie par session du client, et non une
      par contenu :
        - la session se reconnaît au début du fichier (empreinte des premières lignes, gardée dans l'index) ;
        - un contenu dont la copie archivée est un **préfixe** remplace cette copie, au lieu de s'y ajouter ;
        - seule une réécriture (nouveau démarrage du client, début différent) crée un nouveau fichier ;
        - nommé `<cache>/dbcache/<build>/Hotfix-<date du début de session, UTC compacte>.log` ;
        - le build est celui du client à la date du fichier (`client_builds.version_at`), sinon celui de
          `.build.info` au moment de la copie, avec la source notée dans l'index ;
        - un contenu déjà archivé (même sha256) n'est pas recopié.
    - Le contrôle se fait d'abord par taille et date, et le fichier n'est relu que s'il a changé. L'état est gardé
      dans `<cache>/watch/state.json`.
    - `client_builds.record_build` est appelé à chaque passage : le build vu est inscrit au journal même sans
      journal de combat (l'absence de 70205 venait de là).
    - Les écritures se font en octets (`write_bytes`), avec un fichier temporaire puis un renommage.
2. `forever watch` montre « archivé : DBCache.bin 70235 (nouvelle copie) » quand une copie est faite. Aucune ligne de
   démarrage pour une copie (bruit) : seulement en cas d'échec répété (3 passages illisibles).
3. Inscription rétroactive de 70205 dans `client_builds.json` : faite **en première action de la session**, avant
   les blocs (voir « Blocs et étapes »), avec la date de sa première ligne de `hotfixes.json` (source citée, comme
   70009 l'a été par `Errors/`). Le bloc A n'ajoute que la fonction qui l'inscrit avec sa source.

### Bloc B — Preuve d'entrées identiques par moteur, et rejeu ciblé (point 1, fin)

1. `forever/engine_inputs.py` :
    - `ENGINES` : registre des moteurs calculés. Aujourd'hui :
        - `mage_build` (`forever.build.build_report`) ;
        - `mage_leveling` (`forever sim leveling`) ;
        - `pvp_dr` (`forever/engine/diminishing.py` par les fiches PvP).

      Pour chacun : les fichiers et, pour un fichier partagé, les **pointeurs JSON** lus (`classes.json` :
      `/classes/Mage` pour le Mage, `/classes/*/spells/*/dr` pour les rendements décroissants : la forme exacte est
      fixée par le relevé de l'étape 2). Les cas qui l'exercent sont ceux de `scripts/replay_builds.py` (contexte et
      niveau).
    - `capture_reads(fn)` : relevé instrumenté de `VersionData.read_json` (et des lectures de `classes.json` par
      pointeur). C'est la méthode du rapport de la révision 4, devenue du code.
    - `canonical_sha(doc, pointers, metadata)` : JSON trié sans les clés de métadonnées (`value_diff.META` et les
      `metadata_keys` d'`origins.json` : `source`, `read_at`, `carried_from`, `carried_to`, `hotfix`…).
    - `compare_inputs(before_dir, after_dir) -> dict[engine, InputsDiff]` : pour chaque moteur, la liste des fichiers
      ou pointeurs `identique` ou `différent`, avec les deux empreintes et le nombre de feuilles changées.
2. Garde de complétude (test) : pour chaque moteur, les lectures relevées pendant un cas réel de fixture sont
   **incluses** dans sa déclaration. Un moteur qui se met à lire un nouveau fichier fait échouer le test : la preuve
   ne peut pas devenir fausse en silence.
3. Rejeu ciblé :
    - `scripts/replay_builds.py` expose `run_cases(label, only, data_dir, cache_dir)` et `compare(a, b)` comme
      fonctions, la CLI du script restant inchangée ;
    - `forever update` rejoue seulement les cas des moteurs dont une entrée change, sur la version installée puis sur
      la candidate, dans `<cache>/builds/update-<id>-avant|après/` ;
    - les recommandations qui changent entrent dans le rapport et l'attente.

### Bloc C — Report des changements faits à la main (point 1)

1. `forever/carry.py` :
    - `manual_values(version_dir)` : toutes les feuilles d'origine `manuel` et `journal` (`origins.json`), plus les
      chemins des `manual_changes` de `revisions.json`, plus `meta.json` `game_state`. Pour chacune : chemin, valeur,
      origine, révision et raison.
    - `carry_check(old_dir, new_dir) -> CarryReport`. Pour chaque valeur :
        - `gardé` : même valeur au même chemin ;
        - `réappliqué` : absente d'un fichier **hérité** de la nouvelle version, et réécrite par
          `carry_apply` ;
        - `remplacé` : le fichier est désormais décodé et le client donne une autre valeur ;
        - `perdu` : absente sans explication.
    - `carry_apply(old_dir, new_dir, report)` : réécrit les `réappliqué`, en octets, puis appelle
      `write_manifest`.
2. Appelé par la chaîne avant la règle, aussi bien sur une **nouvelle version** que sur une **révision** (contrôle
   après l'installation dans le clone). `forever install` n'est pas modifié : le report se fait autour de lui.
3. Section « Report à la main » du rapport : comptes par statut, et une ligne par valeur `remplacé` ou `perdu`.

### Bloc D — Addons : suivi par empreinte, relecture, inventaire proposé (point 1, addons ; point 5)

1. `DATA_ADDONS` reçoit trois nouvelles entrées :
    - `TalentsForeverBook` (lecteur : `scripts/compare_talents_forever.py`, devenu la fonction
      `forever/pipeline/talents_forever.py` `read_trees`, agrégats seulement ; `depends` : recoupement des arbres) ;
    - `ForeverCompanion` (lecteur « inventaire T08d, lecteur à venir ») ;
    - `NaowhForever` (motif `NaowhForever_*`, lecteur à venir).

   La version de **contenu** est lue en plus de celle du `.toc` quand l'addon la porte : `Data.lua` de Talents
   Forever (`build`, `generated`, `codeVersion`) et `Data/Meta.lua` de Forever Companion (`dataVersion`, `updated`).
   La lecture passe par `lua_table`, jamais par du Lua exécuté.
2. `UI_ADDONS` (`EllesmereUI*`, `Leatrix_Maps`, `ForeverMapFix`) : notés « interface seule » avec leur version,
   **aucun fichier lu** hors du `.toc`. `NOT_ADDONS` : un dossier sans `.toc` (`ForeverCompletionist`) est noté
   « pas un addon ».
3. **Addon présent mais jamais inventorié** : tout dossier avec un `.toc` qui n'est ni suivi, ni d'interface, ni un
   module d'un addon suivi (motifs). Statut `non_inventorié`, avec la proposition
   `forever addons inventory <dossier>`.
4. `forever addons inventory <dossier> [--json]`, en lecture seule. Il rend :
    - les métadonnées du `.toc` (titre, version, auteur, `X-*`, SavedVariables, interface) ;
    - la présence d'une licence (fichier ou `X-License`) ;
    - les fichiers de données (nombre, tailles, sha256 et empreinte), les en-têtes de génération (premières lignes de
      commentaire) et les clés de premier niveau des tables globales.

   Il ne rend **aucune valeur** et n'écrit rien. L'agent s'en sert pour rédiger une section de
   `tasks/inventaire-addons.md`, après l'accord de l'utilisateur.
5. Relecture à un changement : chaque addon qui a un lecteur est relu.
    - Questie : agrégats, comme aujourd'hui.
    - Forever Bestiary : `forever pets crosscheck` en simulation.
    - Talents Forever : recoupement de ses arbres avec `classes.json` installé (comptes et écarts).

   Résultat : la liste des changements (fichiers, version de contenu, agrégats). Un `depends` touché crée une attente
   `addon_data`.
6. Hors tests (fin du bloc) :
    - section « Relevé du 2026-10-06 (T08d) » de `tasks/inventaire-addons.md` : le tableau du contexte complété par
      `forever addons status`, puis l'**inventaire de Forever Companion** par `forever addons inventory` (agrégats
      seulement, aucune licence : décision 172 étendue) ;
    - NaowhForever, AtlasBIStooltips et RXPGuides sont **proposés**, sans être inventoriés sans accord ;
    - `docs/DATA_SOURCES.md` (Talents Forever : `codeVersion` 6 et suivi par empreinte ; Forever Companion : nouvelle
      ligne).

### Bloc E — Chaîne `forever update`, règle d'automatisme et approbation différée (points 1, 2 et 3)

1. `forever/update.py` : `run_update(deps, options) -> UpdateReport` enchaîne les étapes 0 à 9 décrites plus haut,
   chacune dans une fonction séparée et testée seule. En mode `--dry-run`, tout est calculé, rien n'est écrit dans le
   clone, les attentes sont rendues sans être enregistrées, et seul l'archivage s'exécute.
2. `decide(verify_ok, carry, inputs, kind) -> Verdict` : fonction pure. Elle rend `écrire`, `attente` (avec les
   clauses non tenues) ou `bloqué` (`verify` rouge, ou un changement à la main `perdu`).
3. Attentes : `pending.py` (dans `update.py` si c'est court) crée, liste, approuve, rejette et rend périmées les
   entrées. Une base changée rend l'entrée périmée.
4. CLI :
    - `forever update [--auto] [--dry-run] [--json] [--no-network] [--only jeu,correctifs,journaux,addons]` ;
    - `forever update status|approve|reject` ;
    - sans `--auto`, la sortie est la même, mais aucun processus détaché n'est lancé.
5. Correctifs du serveur en révision suivante : la logique de `watch._dbcache_event` est déplacée dans
   `forever/pipeline/hotfixes.py` (`pending_hotfixes(cache, sources, rules)`), appelée par la veille et par la
   chaîne. Les correctifs viennent de l'**archive** (`<cache>/dbcache/<build>/DBCache.bin`), jamais du fichier vivant.
6. MCP : `forever_status` reçoit un bloc `update` (dernier passage, attentes) en lecture seule. Aucun outil MCP
   n'écrit ni n'approuve : l'approbation reste dans la CLI.

### Bloc F — Git dans le clone dédié (réponses 3 et 4)

1. `forever/pipeline/gitops.py` : `Runner` injectable (`subprocess.run`, sans shell, liste d'arguments). Fonctions :
    - `ensure_clone(repo_url, path)` ;
    - `sync_main(clone) -> SyncResult` (`fetch`, contrôle de l'arbre et de la branche, `merge --ff-only`) ;
    - `remote_has(clone, version, revision)`, qui lit `revisions.json` de `origin/main` par `git show`, sans
      checkout ;
    - `commit_branch(clone, branch, paths, message)` ;
    - `push(clone, branch)` ;
    - `wait_ci(clone, sha, timeout)` : `gh run list --branch … --json …` pour trouver l'exécution de `ci.yml` du sha
      poussé, puis `gh run watch <id> --exit-status`, puis `gh run view <id> --json jobs`. Il exige les jobs Ubuntu
      **et** Windows en `success` ;
    - `merge_ff_and_push(clone, branch)` ;
    - `delete_branch(clone, branch)`.

   **Aucune commande ne contient `--force`, `-f` ni `+refs`** (test sur toutes les commandes émises).
2. Rejet de la poussée de `main` (non avance rapide) : étape `arrêt`, « main distant a bougé : relancer
   `forever update` ». La branche reste poussée et le rapport la nomme.
3. CI rouge ou délai dépassé : étape `arrêt`. La branche est gardée, rien n'est fusionné, et le rapport donne le lien
   de l'exécution.
4. Chemin du clone : `<cache>/update/repo`. L'URL vient de `git remote get-url origin` du dépôt de la session, lue une
   fois et gardée dans `<cache>/update/config.json`. Le clone ne partage aucun fichier avec la session.
5. `last.json` garde `origin_main` (sha) après chaque `fetch`. La ligne de démarrage le compare au `HEAD` de la
   session (`git merge-base --is-ancestor`, local, sans réseau) pour proposer `git pull --ff-only`.

### Bloc G — Déclenchement : démarrage de session, tâche planifiée, documentation réseau (point 3)

1. `forever/hooks.py`, au `SessionStart` :
    - (1) archivage (bloc A), qui est rapide et local ;
    - (2) si aucun verrou n'est vivant et que le dernier passage a plus de 6 h, lancement **détaché** de
      `uv run forever update --auto --json` **depuis l'installation de la session** : au premier passage, le clone
      n'existe pas encore. C'est l'orchestrateur qui crée le clone, puis y lance `install`, `verify`, le commit et
      git ; il n'écrit jamais dans l'arbre de la session. Sous Windows : `DETACHED_PROCESS |
      CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`, sortie dans `<cache>/update/run-<horodatage>.log`. Le lancement
      passe par un `spawn` injectable, et ne lève jamais d'exception ;
    - (3) la ligne affiche, sans réseau :
        - le dernier passage (« mise à jour : 1.60.1.70235 r1 installée il y a 2 h », ou « en cours ») ;
        - le nombre d'attentes, avec `forever update status` ;
        - « main distant a avancé : `git pull` » quand c'est le cas.

      Elle ne dépasse jamais une ligne.
2. `scripts/install_update_task.ps1`, sur le modèle de `install_watch_task.ps1` (`-WhatIf`, `-Remove`, `-At`) :
   `forever update --auto --json` chaque jour, limite d'exécution de 2 h. Le script retire l'ancienne tâche
   « veille locale » s'il la trouve (avec `-WhatIf`, il le montre seulement). **Lancé par l'utilisateur, jamais par
   l'agent.**
3. Réseau :
    - `CLAUDE.md` : liste des commandes qui touchent Internet (+ `forever update`, avec la portée de la décision 179) ;
    - `docs/ARCHITECTURE.md` ;
    - `docs/USAGE.md` (`update`, `update status|approve|reject`, `addons inventory`, tâche planifiée) ;
    - `tests/unit/test_network_boundary.py` : `subprocess` avec `git`/`gh` seulement dans `pipeline/gitops.py` ;
    - un patch pour `.claude/settings.json`, s'il faut autoriser le hook à lancer un processus (le mode auto n'y écrit
      pas : `tasks/T08d-settings.patch`).
4. `build-watch.yml` n'est pas modifié : la CI continue d'ouvrir sa PR `data/<version>`. Le rapport de
   `forever update` signale une PR de veille ouverte pour la version installée, sans la fermer.

### Bloc H — Cas réel 1.60.1.70235, DON13 et point d'arrêt (point 6)

Hors tests, sur le poste :
1. Archivage réel : `DBCache.bin` 70235 recopié après la fermeture du client, `Hotfix.log` archivés ; contrôle que 70205
   est inscrite (première action de la session) et que les journaux du 05/10 lui sont attribués.
2. `forever update --dry-run --json` depuis la session, puis `forever update` (avec le clone). Pour 70235 :
    - `fetch` (accord permanent) ;
    - `decode --hotfixes` avec l'archive 70235 : il faut des dispositions pour 70235, donc une attente `network_dbd`
      si l'accord ne couvre pas WoWDBDefs ;
    - `verify`, `diff` avec 70170 r4, report des 70170 r3 et r2, puis preuve d'entrées.

   Attendu probable : **attente**, car une nouvelle version change au moins les métadonnées. Si un `talents.json` ou
   un `spells.json` du Mage change, le rejeu ciblé est montré.
3. **DON13** : les identifiants de nœud des nouveaux talents du Guerrier (Lingering Rage, Furious Precision, Gore
   Drinker, Iron Will) sont comparés entre :
    - (a) le `DBCache.bin` de 70170 (`<cache>/dbcache/70170/`, nœuds de la révision 4) ;
    - (b) les tables de wago de 70235 ;
    - (c) le `DBCache.bin` de 70235 (archive) ;
    - (d) Talents Forever 0.37.1 (`Data.lua`, 70170 du 04/10) ;
    - (e) Forever Companion (sort, rangée, colonne et rangs seulement, pas de nœud).

   Le client du build joué fait foi : (b) recouvert par (c). Rapport `docs/research/guerrier-T08d-noeuds.md`
   (agrégats seulement). DON13 passe dans `docs/RESOLVED_QUESTIONS.md`, avec la règle à retenir pour FA1 : quels
   nœuds exporter, et le `codeVersion` 6 de Talents Forever. Contrôle facultatif en jeu (proposé, jamais exigé) :
   apprendre un des talents, puis exporter le code par `/tf`.
4. **Point d'arrêt** : avant toute approbation, montrer à l'utilisateur :
    - le rapport de `forever update` (étapes, verdict, clauses) ;
    - le `diff` 70170 r4 → 70235 ;
    - le report à la main ;
    - les entrées des moteurs, et le rejeu ciblé s'il y en a un ;
    - DON13 ;
    - les addons changés, avec leurs listes de changements.

   Après son accord seulement : `forever update approve <id>`. Le chemin git complet est alors exercé pour la
   première fois (branche, CI, fusion, poussée), puis `git pull` dans la session.
5. Documentation finale :
    - `docs/ROADMAP.md` (T08d réalisée, écarts) ;
    - `docs/OPEN_QUESTIONS.md` (questions plus bas, DON13 retirée) ;
    - `docs/research/data-1.60.1.70235-install.md` (généré) ;
    - `docs/research/builds-T05.md` (section « Rejeu T08d », seulement s'il y a eu un rejeu).

### Blocs I et J — Reprise du 2026-10-06 (réponses de l'utilisateur aux points bloquants)

Constats de la session précédente : la simulation sur 70235 s'arrêtait en erreur (`data_schema`) parce que la
colonne `Field_1_60_1_69876_005` de `PlayerExpectedStat` s'appelle `HPPerStamina` dans les tables de wago de 70235
(seule colonne déclarée absente, relevé de tous les en-têtes) ; deux journaux du 02/10 attendaient une mesure.

**Bloc I — Noms de colonne multiples, arrêt propre (réponse 2).**
1. `forever/pipeline/tables.py` : une colonne déclarée peut avoir plusieurs noms (`Nouveau|Ancien:type`, le nouveau
   d'abord). `read_table` prend le premier nom présent dans l'en-tête et range la valeur sous **chacun** des noms de
   la colonne (les lecteurs qui citent l'un ou l'autre nom lisent la même valeur).
2. Les règles (`decode_rules.json`) acceptent pour une colonne un nom ou une liste de noms (`player_columns`,
   `pets.training_cost_column`) ; `column_value(row, names)` rend la valeur du premier nom présent.
3. Aucun nom trouvé : `ColumnNamesError` (sous-classe de `DataSchemaError`, avec la table, les noms essayés et
   l'en-tête). `forever update` l'attrape à l'étape `nouvelle_version` (et `correctifs`) : étape `attente`, entrée
   d'attente `column_names` (table, noms essayés, nom proposé par la position dans le CSV de la version installée,
   commandes à faire en session), code 6. `approve` la refuse avec le message « à traiter en session » : rien ne
   s'écrit sans édition du schéma.
4. Révision de `forever/data/1.60.1.70170/decode_rules.json` (accord du 2026-10-06) : `hp_per_stamina` =
   `["HPPerStamina", "Field_1_60_1_69876_005"]`. Le nom vient des définitions de la communauté (WoWDBDefs) : il
   conforte le sens « PV par point d'Endurance », qui reste `probable` jusqu'à une mesure en jeu (notes mises à jour).

Tests (`tests/unit/test_column_names.py`) : en-tête ancien ou nouveau lu pareil ; aucun nom → `ColumnNamesError`
qui nomme les noms essayés ; liste de noms dans les règles ; proposition par position ; règles de 70170 et schéma
alignés ; chaîne : attente `column_names` au lieu d'une erreur, code 6, `approve` refusé.

**Bloc J — Mesures de 70170, révision suivante (réponse 3).**
Vérification faite : l'empreinte du journal de la révision 2 (`WoWCombatLog-100226_080035.txt`) est celle des
21 372 premières lignes (5 936 426 octets) du fichier actuel (28 335 lignes) : c'est le même journal, qui a grossi
après la mesure de 13:11. `WoWCombatLog-100226_162842.txt` est une autre session du même jour, sous 70170.
1. `build_monsters` écarte automatiquement de la courbe tout PNJ mesuré que Questie classe hors du rang normal
   (`rank` de Questie, référence `creature_template` de cmangos citée par `npcDB.lua` : 1 élite, 2 élite rare,
   3 boss, 4 rare), avec la raison écrite dans `curve_excluded` ; une raison donnée par l'utilisateur n'est jamais
   remplacée. Un PNJ inconnu de Questie reste dans la courbe.
2. La mesure est simulée (`forever measures refresh --dry-run`) et montrée ; rien n'est écrit sans accord.

Tests (`tests/unit/test_monsters_rank_exclusion.py`, Questie de fixture : 5945 rang 1, 1531 rang 4).

## Fichiers

- **Nouveaux** :
    - code : `forever/update.py`, `forever/archive.py`, `forever/engine_inputs.py`, `forever/carry.py`,
      `forever/pipeline/gitops.py`, `forever/pipeline/talents_forever.py`, `scripts/install_update_task.ps1` ;
    - tests : `tests/unit/test_archive.py`, `tests/unit/test_engine_inputs.py`, `tests/unit/test_carry.py`,
      `tests/unit/test_update_rule.py`, `tests/unit/test_update_chain.py`, `tests/unit/test_update_pending.py`,
      `tests/unit/test_gitops.py`, `tests/unit/test_addons_inventory.py` ;
    - fixtures : `tests/fixtures/addons/` (addons **synthétiques** : `.toc` et `.lua` écrits pour le test, sans
      contenu tiers), `tests/fixtures/addons/README.md` ;
    - documentation et patch : `docs/research/guerrier-T08d-noeuds.md`, `tasks/T08d-settings.patch` si besoin.
- **Modifiés** :
    - code : `forever/addons.py`, `forever/watch.py`, `forever/hooks.py`, `forever/cli.py`, `forever/errors.py`
      (`EXIT_PENDING`), `forever/config.py` (seuils, chemins), `forever/mcp_server.py` et `forever/status.py` (bloc
      `update` en lecture), `forever/pipeline/hotfixes.py` (`pending_hotfixes`), `forever/pipeline/client_builds.py`
      (inscription rétroactive avec une source), `scripts/replay_builds.py` (fonctions), `scripts/compare_talents_forever.py`
      (appelle `talents_forever.py`) ;
    - tests : `tests/unit/test_watch.py`, `tests/unit/test_addons_status.py`, `tests/unit/test_hooks.py`,
      `tests/unit/test_network_boundary.py`, `tests/unit/test_replay_builds_*.py` si leurs points d'entrée changent ;
    - documentation : `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/USAGE.md`, `docs/DECISIONS.md`, `docs/ROADMAP.md`,
      `docs/DATA_SOURCES.md`, `docs/OPEN_QUESTIONS.md`, `docs/RESOLVED_QUESTIONS.md`, `tasks/inventaire-addons.md`.
- **Données** : rien dans les blocs 0 à G. Au bloc H, après accord, et **par le clone et le chemin git** :
  `forever/data/1.60.1.70235/`.

## Interfaces

```python
# forever/archive.py
class ArchivedCopy(NamedTuple):
    kind: str            # "dbcache" | "hotfix_log"
    build: str           # "70235" (en-tête de DBCache.bin) ou build du client à la date du fichier
    path: Path; sha256: str; size: int; file_mtime: str; copied_at: str; new: bool
def archive_client_files(deps: Deps, *, locale: str = "enUS") -> list[ArchivedCopy]   # ne lève jamais : erreurs dans le résultat
def archived_dbcache(cache_dir: Path, build: str) -> Path | None                       # copie la plus récente du build

# forever/engine_inputs.py
class EngineSpec(NamedTuple):
    name: str; files: tuple[str, ...]; pointers: Mapping[str, tuple[str, ...]]; cases: tuple[str, ...]
ENGINES: Mapping[str, EngineSpec]
def capture_reads(fn: Callable[[], Any]) -> set[tuple[str, str | None]]    # (fichier, pointeur ou None)
def canonical_sha(doc: Any, pointers: Sequence[str] | None, metadata: frozenset[str]) -> str
class InputsDiff(NamedTuple):
    engine: str; identical: bool; items: list[dict[str, Any]]              # fichier/pointeur, avant, après, feuilles
def compare_inputs(before: Path, after: Path) -> dict[str, InputsDiff]

# forever/carry.py
class ManualValue(NamedTuple):
    file: str; pointer: str; value: Any; origin: str; revision: int | None; reason: str
class CarryReport(NamedTuple):
    kept: list[ManualValue]; reapplied: list[ManualValue]; superseded: list[tuple[ManualValue, Any]]; lost: list[ManualValue]
def manual_values(version_dir: Path) -> list[ManualValue]
def carry_check(old_dir: Path, new_dir: Path) -> CarryReport
def carry_apply(old_dir: Path, new_dir: Path, report: CarryReport) -> list[Path]

# forever/update.py
class Step(NamedTuple):
    name: str; status: str; detail: str; data: Mapping[str, Any]          # fait | rien | attente | arrêt | erreur
class Verdict(NamedTuple):
    action: str; clauses: Mapping[str, bool]; reasons: list[str]          # écrire | attente | bloqué
def decide(verify_ok: bool, carry: CarryReport, inputs: Mapping[str, InputsDiff], kind: str) -> Verdict
class UpdateOptions(NamedTuple):
    auto: bool = False; dry_run: bool = False; network: bool = True; only: frozenset[str] = frozenset()
class UpdateReport(TypedDict):
    schema_version: int; started_at: str; finished_at: str; steps: list[dict[str, Any]]; verdicts: list[dict[str, Any]]
    written: list[dict[str, Any]]; pending: list[str]; origin_main: str | None; provenance: dict[str, Any]
def run_update(deps: Deps, options: UpdateOptions, *, runner: Runner | None = None) -> UpdateReport
def list_pending(cache_dir: Path) -> list[dict[str, Any]]
def approve(deps: Deps, pending_id: str, *, wait: bool = False, runner: Runner | None = None) -> dict[str, Any]
def reject(cache_dir: Path, pending_id: str, reason: str | None) -> dict[str, Any]

# forever/pipeline/gitops.py
class Runner(Protocol):
    def __call__(self, args: Sequence[str], cwd: Path, timeout: float | None = None) -> CompletedProcess[str]: ...
class SyncResult(NamedTuple):
    ok: bool; reason: str | None; origin_main: str; advanced: bool
def ensure_clone(runner: Runner, url: str, path: Path) -> None
def sync_main(runner: Runner, clone: Path) -> SyncResult
def remote_has(runner: Runner, clone: Path, version: str, revision: int | None) -> bool
def commit_branch(runner: Runner, clone: Path, branch: str, paths: Sequence[str], message: str) -> str   # sha
def push(runner: Runner, clone: Path, branch: str) -> None
def wait_ci(runner: Runner, clone: Path, branch: str, sha: str, timeout_s: float) -> CiResult           # jobs, lien
def merge_ff_and_push(runner: Runner, clone: Path, branch: str) -> MergeResult                          # ok | main_moved
def delete_branch(runner: Runner, clone: Path, branch: str) -> None

# forever/addons.py (ajouts)
UI_ADDONS: tuple[str, ...]                 # motifs : EllesmereUI*, Leatrix_Maps, ForeverMapFix
def content_version(name: str, folder: Path) -> dict[str, Any] | None   # Talents Forever, Forever Companion
def untracked_addons(addons_dir: Path) -> list[dict[str, Any]]           # non_inventorié | interface | pas_un_addon
def inventory(folder: Path) -> dict[str, Any]                            # métadonnées et empreintes, aucune valeur
```

CLI :
- `forever update [--auto] [--dry-run] [--json] [--no-network] [--only …]` ;
- `forever update status [--json]` ;
- `forever update approve <id> [--wait] [--json]` ;
- `forever update reject <id> [--reason …]` ;
- `forever addons inventory <dossier> [--json]` ;
- `forever addons status` montre `non_inventorié`, `interface` et la version de contenu.

MCP : bloc `update` en lecture dans `forever_status`, et aucun nouvel outil.

## Tests attendus

Les valeurs viennent des fixtures ; aucune règle de jeu n'est en jeu.

Bloc A (`test_archive.py`, `test_watch.py`), sur un dossier du client en `tmp_path` qui reçoit la fixture
`tests/fixtures/hotfix/DBCache.bin` (build 70170) et l'extrait `Hotfix.log` :
- Premier passage : `<cache>/dbcache/70170/DBCache.bin` créé, de mêmes octets que la fixture ; `index.json` avec
  sha256, taille, nombre d'entrées (celui du README de la fixture) et `new: true`. `Hotfix-<date>-<sha12>.log` créé.
- Second passage sans changement : aucune lecture complète (compteur de lecture simulé) et aucune copie.
- Même build, octets différents (une entrée retirée par le test) : l'ancienne copie est gardée en
  `DBCache-<sha12>.bin`, la nouvelle devient `DBCache.bin`, et l'index compte deux copies.
- Fichier tronqué : rien n'est archivé, l'erreur est dans le résultat, aucune exception. Le passage suivant, avec le
  fichier entier, archive.
- `Hotfix.log` qui grossit (mêmes premières lignes, plus des lignes ajoutées par le test) : une seule archive, mise à
  jour avec le contenu le plus long. `Hotfix.log` réécrit (début différent) : deux fichiers archivés. Le même contenu
  recopié ne change rien.
- `.build.info` d'un build absent du journal : `client_builds.json` le contient après le passage.
- Aucune écriture hors de `<cache>` (le dossier du client est intact : empreinte avant et après).

Bloc B (`test_engine_inputs.py`), sur une copie des données (`data_copy`) :
- `compare_inputs(copie, copie)` : tous les moteurs `identical`.
- `meta.json` `carried_from` changé : identique (métadonnée). `talents.json` `source.read_at` changé : identique.
- Une valeur de `spell_scaling.json` changée : `mage_build` et `mage_leveling` `différent`, une feuille ; `pvp_dr`
  identique.
- `classes.json` : une valeur du Guerrier changée laisse les moteurs du Mage identiques ; une valeur de
  `classes.Mage.spells` changée les rend différents.
- `pvp_rules.json` changé : seul `pvp_dr` est différent.
- Complétude : `capture_reads` autour d'un cas de fixture de chaque moteur (`build_report` leveling 20, fiche PvP d'un
  affrontement) donne un ensemble **inclus** dans la déclaration du moteur.
- Rejeu ciblé : sur une différence de `mage_build` seul, les cas choisis sont ceux de `mage_build`, et aucun de
  `pvp_dr`. Le calcul est simulé par une fonction de rejeu injectée, sans Monte Carlo.

Bloc C (`test_carry.py`) : version de fixture A, avec une règle `manuel` sur `pet_rules.json` `/official_fixes` et
une valeur `journal` dans `monsters.json`, puis une version B construite par le test :
- B identique : tout `gardé`.
- `official_fixes` absent de B (fichier hérité) : `réappliqué`, puis `carry_apply` le réécrit (octets égaux à A),
  `write_manifest` est appelé et `verify` est vert.
- `monsters.json` décodé dans B (marqué décodé dans `sources.json`) avec une autre valeur : `remplacé`, avant et
  après donnés.
- Valeur absente d'un fichier décodé sans valeur du client : `perdu`.
- Les chemins des `manual_changes` de `revisions.json` sont inclus même sans règle d'origine (cas de 70124 r6 et
  70170 r3 reproduit dans la fixture).

Bloc D (`test_addons_status.py`, `test_addons_inventory.py`), sur des addons synthétiques de `tests/fixtures/addons/`
(`TalentsForeverBook` avec un `Data.lua` minimal : `build`, `generated`, `codeVersion` ; `ForeverCompanion` avec
`Data/Meta.lua` : `dataVersion`, `updated` ; un faux `EllesmereUI` ; un dossier sans `.toc` ; un addon inconnu
`SomeDataAddon`) :
- `TalentsForeverBook` et `ForeverCompanion` sont suivis. La version de contenu est rendue (valeurs de la fixture).
  Changer `dataVersion` donne `changé`, avec le fichier modifié et la version de contenu avant et après.
- `EllesmereUI` : `interface`, version du `.toc` ; un contrôle prouve que ses `.lua` ne sont jamais ouverts (`open`
  simulé).
- Dossier sans `.toc` : `pas_un_addon`. `SomeDataAddon` : `non_inventorié`, avec l'action
  `forever addons inventory SomeDataAddon`.
- `inventory` : métadonnées du `.toc`, `license: null`, nombre de fichiers, empreinte égale à `fingerprint_folder`,
  en-tête de génération. **Aucune valeur de table** dans la sortie (la sortie ne contient aucune chaîne de valeur de
  la fixture).
- Changement d'un addon dont `depends` est non vide : attente `addon_data` proposée. Sans `depends` : seulement une
  liste.

Bloc E (`test_update_rule.py`, `test_update_chain.py`, `test_update_pending.py`) :
- `decide`, par table de cas :
    - tout vert : `écrire` ;
    - une entrée de moteur différente : `attente` (clause `inputs`) ;
    - un `remplacé` : `attente` (clause `manual`) ;
    - un `perdu` : `bloqué` ;
    - `verify` rouge : `bloqué`, quelles que soient les autres clauses.
- Chaîne en `--dry-run`, sur le montage de `test_build_watch_chain.py` (version fictive `1.60.1.79999` publiée par
  `FakeHttp`, CSV de 70009 en cache, `.build.info` de fixture à 79999) :
    - étapes dans l'ordre (archivage, clone, jeu, nouvelle version, journaux, addons, fin) ;
    - candidate décodée, `verify` vert, report à la main sans `perdu`. La preuve d'entrées est **identique** si les
      tables sont les mêmes (métadonnées seulement), et le verdict est `écrire` ;
    - `forever/data/` intact (dry-run).
- Même montage, avec une valeur de `spells.json` du Mage changée dans les CSV de la version fictive : verdict
  `attente`, entrée en attente rendue, avec le rejeu ciblé (simulé).
- Build du client absent de wago : étape `rien` (« en attente de wago »), sans fetch.
- Build de wago plus récent que le client : signalé, cible = build du client.
- Correctifs : version installée = build de l'archive, avec la fixture `DBCache.bin` dont des poussées ne sont pas
  dans `sources.json` : étape `correctifs` avec le nombre de correctifs. Tables sans disposition validée : attente
  `network_dbd`.
- Journaux : session d'une autre version listée « en attente », jamais mesurée. Session de la version installée :
  mesure simulée, attente `measures` si une valeur lue par un moteur change.
- Attentes :
    - `status` liste l'entrée ;
    - `approve` avec une base inchangée la marque `approuvée` et lance un passage (`spawn` simulé) ;
    - `approve` avec une base changée (sha de `origin/main` différent, ou candidate réécrite) la marque `périmée` ;
    - `reject` garde la raison ;
    - une entrée `bloqué` n'est pas approuvable (refus, code 2).
- Code de sortie 6 avec une attente, 0 sinon. `--json` valide le schéma (clés de `UpdateReport`) et le bloc
  `provenance`.
- Verrou : un verrou vivant fait sortir avec l'étape `arrêt` « déjà en cours » ; un verrou périmé (date simulée) est
  repris.

Bloc F (`test_gitops.py`). Git réel dans `tmp_path` (dépôt nu `origin.git`, clone dédié, second clone qui joue
« l'autre PC »), `gh` simulé :
- `ensure_clone` puis `sync_main` : le clone est sur `main`, à `origin/main`.
- Clone sale (un fichier modifié) : `ok: False`, raison « arbre de travail modifié », aucune commande d'écriture.
  Clone sur une autre branche : même refus.
- `remote_has` : l'autre PC pousse une révision dans `revisions.json` → vrai, et la chaîne avance seulement le clone,
  sans commit ni poussée (journal des commandes du `Runner` enveloppé).
- Chemin complet avec une CI simulée verte, Ubuntu et Windows : branche `data/<v>-r<N>` créée, commit, poussée, CI
  attendue, `main` avancé en avance rapide sur `origin`, branche supprimée en local et à distance.
- CI avec le job Windows en échec : `arrêt`, rien fusionné, branche gardée.
- L'autre PC pousse sur `main` entre la CI et la fusion : poussée refusée, étape `arrêt` « main distant a bougé »,
  `origin/main` inchangé par notre clone.
- **Sur tous les tests** : aucune commande émise ne contient `--force`, `-f`, `--force-with-lease` ni de refspec en
  `+`.

Bloc G (`test_hooks.py`, `test_network_boundary.py`) :
- Session ouverte dans le dépôt :
    - l'archivage est appelé ;
    - `spawn` est appelé une fois quand aucun verrou n'est vivant et que le dernier passage date de plus de 6 h ;
    - pas de `spawn` avec un verrou vivant, ni avec un passage récent ;
    - une exception de `spawn` ne casse pas la ligne.
- Ligne de démarrage :
    - « 1 attente : `forever update status` » avec une attente ;
    - « main distant a avancé : `git pull` » quand `last.json` porte un `origin_main` dont le `HEAD` de la session est
      un ancêtre strict (dépôt git de `tmp_path`) ;
    - rien de tout cela sans état ;
    - une seule ligne, sans retour à la ligne.
- `test_network_boundary.py` : `subprocess` avec `git` ou `gh` seulement dans `forever/pipeline/gitops.py` ;
  `forever/update.py` n'importe aucun module réseau.

Registre (`test_registry.py`) : **aucune mécanique ajoutée ni changée de statut**. La couverture reste **54/129** ;
le total, 129, et la sortie de `main` restent inchangés (affirmé, aucun compte à modifier). Si DON13 change la preuve
de G3, seules la source et la note changent, sans changer de statut.

## Hors périmètre

- Lecture des notes officielles : toujours à la main (décision 148, conditions de Blizzard). La chaîne ne fait que
  proposer `forever notes` à un nouveau build.
- `build-watch.yml`, `notes-watch.yml` et `api-probe.yml` ne sont pas modifiés. Aucune PR de veille n'est fermée par
  l'outil.
- Pont en jeu de P06 : seule son interface (`--json`, `status` et `approve`) est prévue, sans aucun code d'addon.
- Lecteurs du contenu de Forever Companion (BiS, rotations, guides, butin, métiers), de NaowhForever, d'AtlasBIStooltips
  et de RXPGuides : inventaire proposé seulement (les lecteurs viendront avec FA1, DJ1 ou les tranches de classe) ;
  aucun addon installé ni mis à jour par l'agent.
- Note d'impact par personnage, baisse automatique de certitude d'un diff `stale`, `forever_diff_versions` (T08).
- Correctifs obtenus par le réseau ; `DBCache.bin` d'une autre locale.
- Récupération des correctifs de 70205 : impossible, le fichier est perdu.
- Outil MCP qui écrit ou approuve.

## Risques

- **wago n'a pas encore 70235** (ni 70205) : la chaîne attend (« en attente de wago »), et le bloc H attend avec
  elle. Le reste de la tranche n'en dépend pas.
- **WoWDBDefs sans bloc pour 70235** : les correctifs de 70235 ne peuvent pas être appliqués. Règle : ne jamais
  installer une version sans les correctifs applicables de son archive (sinon la refonte du Guerrier pourrait reculer
  si les tables de 70235 ne la portent pas). C'est une attente, avec la source suivante proposée (décision 175),
  jamais un bloc voisin.
- **Arbres du Guerrier de 70235 différents de la révision 4** (`observed_positions`, `community_positions`,
  `tree_checks` réveillés) : le `verify` de la candidate est rouge, donc `bloqué`. Le traitement se fait en session,
  avec l'accord de l'utilisateur.
- **Copie de `DBCache.bin` pendant son écriture** : la lecture complète et l'analyse se font avant l'archivage, avec
  un nouvel essai au passage suivant (bloc A). On ne sait pas quand le client écrit le fichier : réécriture constatée
  une minute après la connexion (DON14).
- **Clone dédié sous Windows** :
    - chemins longs (`core.longpaths`) ;
    - `uv sync --offline` qui échoue (cache de uv vidé) : arrêt avec la commande à lancer ;
    - identifiants git et `gh` absents dans la tâche planifiée (session non interactive) : arrêt « authentification »,
      sans jamais demander de saisie.
- **Deux passages concurrents** (session et tâche, ou les deux PC) : le verrou local, `fetch` puis
  `remote_has` puis `--ff-only`, et jamais de poussée forcée. Le pire cas est un passage perdu, rejoué au suivant.
- **Durée** (fetch, decode, `verify` complet, CI) : la tâche est limitée à 2 h, et chaque étape est horodatée dans le
  rapport.
- **Faux « identique »** si un moteur lit une entrée non déclarée : la garde de complétude du bloc B l'empêche pour
  les cas testés. Un chemin de code non exercé par les cas reste un angle mort, listé plus bas.
- **Bruit à chaque démarrage** : l'archivage est court-circuité par la taille et la date, et la ligne ne parle que
  d'attentes, d'un `pull` à faire ou d'un échec répété.

## Angles morts attendus (à chiffrer en fin de tranche)

- **70205 jamais installée** : ses correctifs du serveur sont perdus. Les deux journaux du 05/10 restent « en
  attente » pour toujours : leurs PV de monstres ne servent pas. L'effet sur `monsters.json` est faible (deux
  sessions sur treize), et va dans le sens d'une courbe de PV moins mesurée.
- **Moteurs sans cas de rejeu** (fiches PvP hors rendements décroissants, familiers) : ce sont des consultations sans
  calcul, hors de la règle (c) ; un changement y passe sans arrêt. Effet : un changement de données affiché sans
  accord.
- **Addons sans lecteur** (Forever Companion, NaowhForever…) : un changement est vu par empreinte, mais son contenu
  n'est pas relu ; il n'a aucun effet sur les résultats tant qu'aucun lecteur ne l'utilise.
- **Format des codes de Talents Forever passé en v6** : FA1 prévoit le v5 ; c'est à reprendre au plan de FA1.

## Questions ouvertes à ajouter

- DON14 — Quand le client écrit-il `DBCache.bin` ? À la connexion, à la fermeture, à la réception d'une poussée ? Le
  fichier a été remplacé une minute après le lancement de 70235. Test : dates de `DBCache.bin` et de
  `DBCache.bin<pid>.tmp` relevées par l'archivage sur plusieurs sessions. Priorité : moyenne (archivage).
- DON13 : retirée si elle est tranchée au bloc H (déplacée dans `docs/RESOLVED_QUESTIONS.md`).

## Critères de fin

- L'archivage garde chaque `DBCache.bin` et chaque `Hotfix.log` distincts, par build, sans jamais écrire dans le
  dossier du client, et seulement s'ils sont lisibles ; le build vu est inscrit au journal ; testé sur fixtures.
- La preuve d'entrées par moteur sépare les valeurs des métadonnées, la garde de complétude est verte, et le rejeu
  ciblé ne rejoue que les moteurs touchés.
- Le report à la main classe chaque valeur `manuel` et `journal` (`gardé`, `réappliqué`, `remplacé`, `perdu`) et
  réapplique ce qui doit l'être.
- `forever addons status` suit Talents Forever et Forever Companion (version de contenu comprise), signale les addons
  non inventoriés et n'ouvre aucun fichier des addons d'interface ; `forever addons inventory` ne rend aucune valeur.
- `forever update` enchaîne jeu, correctifs, journaux et addons. La règle d'automatisme est testée par table.
  L'approbation différée (`status`, `approve`, `reject`, périmée) et `--json` (code 6) sont testés.
- Le chemin git du clone dédié est testé sur un dépôt local : distant déjà à jour, CI rouge, `main` qui bouge, aucune
  poussée forcée.
- Le hook lance le passage détaché sans bloquer, et la ligne montre les attentes et le `git pull` ; le script de tâche
  planifiée est livré ; `CLAUDE.md`, `ARCHITECTURE.md`, `USAGE.md`, `DECISIONS.md` et la frontière réseau sont à
  jour.
- Cas réel : 70235 traitée par `forever update` jusqu'au point d'arrêt, DON13 tranché avec cinq témoins, puis
  installation **après accord** par le chemin git complet. Inventaire des addons du 2026-10-06 et de Forever
  Companion écrit.
- Registre inchangé (54/129) ; `uv run tasks.py verify` vert ; CI verte sous Ubuntu et Windows avant la fusion de
  `t08d`.

## Validation

Plan à valider par l'utilisateur avant l'exécution (nouvelle session, `/tranche T08d`). À confirmer en même temps :
la portée de l'accord réseau (WoWDBDefs exclu par défaut), le message de commit de l'outil et les seuils.
