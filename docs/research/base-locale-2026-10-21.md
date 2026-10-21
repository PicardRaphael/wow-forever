# Base de connaissances locale : cache incrémental, SQLite, sorties compactes

> Recherche du 2026-10-21, en lecture seule (web et dépôt). Rien n'est implémenté.
> Légende (celle de `architecture-agent.md`) : **[Certain]** source primaire lue ; **[Probable]** recoupement ou
> inférence forte ; **[Supposé]** jugement d'architecture non vérifié.
> Aucun chiffre de jeu ici : les tailles de cache et les nombres de lignes sont des mesures de l'outil.

## Résumé

Construire une base SQLite **en lecture seule**, reconstruite (jamais migrée) dans le cache local, en **deux étages
d'empreintes** : un étage par source (client installé, chaque addon, chaque SavedVariables) qui produit une sortie
normalisée et son empreinte, puis un étage de fusion dont la clé est faite des **empreintes des sorties**, pas des
entrées. Cela donne l'« early cutoff » des systèmes de build (une source relue qui produit la même chose ne
déclenche pas de nouvelle fusion). Tables par type d'entité (quête, objet, PNJ, sort, zone, donjon), une seule
table de provenance par champ, FTS5 pour les noms, et des outils qui rendent identifiants et résumé d'abord, le
détail à la demande. À éviter : un fichier SQLite partagé et modifié sur place par le pont, le MCP, la CLI et la
mise à jour (Windows, verrous, migrations), et un modèle entité-attribut-valeur généralisé.

## 0. Point de départ dans le dépôt (constaté le 2026-10-21)

- **Données versionnées** : `forever/data/<version>/*.json` (23 Mo pour toutes les versions), lues par
  `store.load_version` après contrôle des empreintes du manifeste. Elles restent la vérité du dépôt ; la base locale
  ne les remplace pas, elle les **lit** comme une source parmi d'autres (`game_version:data_sha` dans la clé).
- **Addons lus à chaque appel, avec un cache par domaine déjà fait** : `forever/quests.py` (`<cache>/quests/`) et
  `forever/dungeons.py` (`<cache>/dungeons/`) bâtissent un « livre » fusionné champ par champ (valeur, source,
  certitude, `others`, `discrepancies`) et l'écrivent en un seul JSON nommé par une empreinte globale.
  `MERGE_FORMAT` et `READ_FORMAT` font déjà partie de la clé. [Certain]
- **Défauts mesurés** [Certain] :
  1. **Pas de ménage** : `<cache>/quests/` pèse 194 Mo (33 fichiers de 6 Mo, un par empreinte vue, jamais
     supprimés), `<cache>/dungeons/` 14 Mo (24 fichiers).
  2. **Deux politiques d'empreinte** : `quests.py` hache `(chemin, taille, mtime_ns)` (un « bit sale » à la Make,
     trompé par une copie qui garde la date ou par un `touch`) ; `dungeons.py` hache tous les octets de tous les
     fichiers à chaque appel (correct, mais relit des Mo pour rien).
  3. **Clé globale unique** : toute écriture d'une SavedVariables (à chaque déconnexion du jeu) change la clé et
     fait tout relire et tout refusionner. Dans le vocabulaire de Mokhov et al. (section 1), c'est une **trace
     constructive profonde** : clé faite des seules entrées terminales, donc **aucun early cutoff**.
  4. **Le coût n'est pas l'analyse JSON** : relire le livre de quêtes en cache prend 0,058 s pour 5 285 quêtes.
     Le gain d'une base est ailleurs : requête précise (une quête, les quêtes d'une zone et d'un niveau), index,
     recherche par nom, et ne plus charger 6 Mo par appel d'outil (pont en jeu compris).
- **Précédent dans l'écosystème** : la base de Factoruide déjà en cache (`<cache>/third_party/factoruide-db/
  forever.sqlite`, 91 Mo, ouverte en lecture seule) a 52 tables : une couche brute `client_*` (tables du client)
  et une couche fusionnée **par type d'entité** `m_quest`, `m_npc`, `m_item`, `m_spawn`, `m_quest_reward`…, plus
  `import_run(source, imported_at, detail)` et `app_meta(key, value)` ; `user_version` laissé à 0, journal
  `delete`, 18 index. C'est le schéma « table par type, brut puis fusionné » appliqué à Forever. [Certain]
- **SQLite disponible** : le venv `uv` local (Python 3.13.16, Windows) embarque SQLite 3.53.1 avec FTS5 (dont le
  tokenizer `trigram`), les fonctions JSON (JSONB compris) et les tables `STRICT`. [Certain] La CI (Ubuntu et
  Windows via `setup-uv`) utilise d'autres interpréteurs : uv 0.7.21 a dû **restaurer** FTS5 sur macOS et Linux dans
  ses Python, donc la présence dépend du build de l'interpréteur. [Probable]

## 1. Cache incrémental et reconstruction dirigée par les empreintes

### 1.1 Le cadre : « Build systems à la carte »

Mokhov, Mitchell et Peyton Jones (ICFP 2018, version longue JFP 2020) décomposent un système de build en un
**ordonnanceur** et un **reconstructeur**. [Certain]

- **Minimalité** : « executes tasks at most once per build, and only if they transitively depend on inputs that
  changed ».
- **Early cutoff** : si une tâche reconstruite produit le même résultat, ses dépendants ne sont pas reconstruits
  (exemple du commentaire ajouté à `main.c` : `main.o` identique, l'édition de liens n'est pas relancée).
- **Reconstructeurs** :
  - *bit sale* (Make, Ninja, Excel) : Make se sert des dates de modification ; il exige des dates qui n'avancent
    que dans le temps, « which can be violated by backup software », et ne peut pas faire d'early cutoff ;
  - *traces vérifiantes* (Shake, Buck, CloudBuild) : on garde les empreintes des dépendances utilisées la dernière
    fois et on ne refait que si l'une a changé ; petites, elles constituent « the build system's memory » ;
  - *traces constructives* (Bazel) : la trace garde aussi le **résultat**, ce qui permet un cache partagé ;
  - *traces constructives profondes* (Nix) : la clé ne regarde que les entrées terminales ; avantages : décision
    immédiate ; inconvénients : tâches obligatoirement déterministes et « No early cutoff ».
- **Auto-suivi** (section 8.8) : une tâche doit aussi être refaite quand **sa règle** change. Shake passe deux
  versions, celle du script et celle de la règle : « If either version changes, then it is as though the key has
  changed […] to avoid using stale build products from previous versions of the build script ».
- **Surveillance contre relevé** (8.9) : relever la date ou l'empreinte de chaque fichier, ou s'abonner aux
  changements (Bazel, Buck), au prix de complications (tâches rendues obsolètes en cours de route).

**Pour nous** [Probable] : le cache actuel est une trace constructive profonde. Passer à des **traces
constructives à deux étages** (par source, puis fusion) rend l'early cutoff ; la constante de format de chaque
lecteur et de la fusion joue le rôle de la « version de la règle » de Shake.

### 1.2 Les outils concrets

| Outil | Ce qu'il met dans la clé | Leçon pour nous |
| --- | --- | --- |
| **Make** | dates de modification seules | rapide mais faux après une copie ou un retour en arrière de la date ; à éviter seul [Certain] |
| **Ninja** | dates, plus la **ligne de commande** de chaque sortie (`.ninja_log`) : « an existing output was built with a different command line » entraîne une reconstruction ; `restat` relit les dates des sorties après la commande et élague les dépendants d'une sortie inchangée | `restat` est un early cutoff par date ; la ligne de commande dans la trace = version du lecteur dans la clé [Certain] |
| **ccache** | identité du compilateur (`compiler_check` : `mtime` par défaut, ou `content`), options, source ; en **mode direct**, un *manifeste* garde les fichiers inclus et leur empreinte ; `sloppiness=file_stat_matches` accepte la date à la place du contenu, au risque de rater un changement à date égale ; nettoyage par `max_size` (5 Gio) en ordre « approximate LRU » | le manifeste « chemin → (taille, date, empreinte) » permet de ne rehacher qu'un fichier dont la date a bougé ; il faut une limite et une éviction [Certain] |
| **Bazel** | cache d'actions (empreinte d'une action → métadonnées du résultat) et stockage adressé par contenu ; seules les variables d'environnement listées par `--action_env` entrent dans la clé ; un outil hors de l'espace de travail n'y entre pas : « two users with different compilers installed will wrongly share cache hits » ; une entrée modifiée pendant le build peut empoisonner le cache | tout ce qui influence le résultat doit être dans la clé (version du jeu, de l'addon, du lecteur) ; relire l'empreinte après lecture pour détecter un fichier modifié pendant la lecture [Certain] |
| **Nix** | sortie adressée par ses entrées (changer une URL change le chemin de **tous** les dépendants) ou, en mode expérimental `ca-derivations`, par son contenu, qui « only depends on that store object itself » | l'adressage par contenu de la sortie est ce qui permet l'arrêt de la propagation [Certain pour la doc, Probable pour l'inférence] |
| **Salsa** (rust-analyzer) | révision globale ; une requête refaite qui rend la même valeur est « backdatée » (early cutoff) ; **durabilité** : chaque entrée a un niveau, un compteur par niveau, une requête qui ne dépend que d'entrées durables n'est pas revérifiée quand une entrée volatile change (rust-analyzer : environ 300 ms économisées par frappe en marquant la bibliothèque standard durable) | classer nos entrées par durabilité : données du client (changent au patch), fichiers d'addons (à leur mise à jour), SavedVariables (à chaque déconnexion) [Certain] |

### 1.3 Conséquences pour la clé [Probable]

- **Étage source** : clé = `(nom du lecteur, READ_FORMAT du lecteur, version déclarée de l'addon (.toc),
  empreinte sha256 des fichiers lus)` ; sortie normalisée + **empreinte de la sortie**.
- **Étage fusion** : clé = `(SCHEMA_VERSION, MERGE_FORMAT, game_version:data_sha, empreintes des sorties des
  sources triées)`. Une SavedVariables réécrite sans changement de ce qu'on en lit donne la même sortie, donc la
  même clé de fusion : pas de refusion.
- **Ne pas mettre `forever.__version__`** dans la clé : tout serait invalidé à chaque publication. Une constante par
  lecteur et par fusion, relevée quand leur code change de sens, suffit (c'est déjà la pratique de `MERGE_FORMAT`).
  Un test peut imposer de relever la constante quand la sortie d'une fixture change.
- **Empreinte des fichiers** : manifeste « chemin → (taille, mtime_ns, sha256) » dans le cache ; on ne rehache que
  si taille ou date ont bougé (mode direct de ccache) ; on rehache aussi si la date est « trop récente » (fichier
  peut-être en cours d'écriture par le jeu à la déconnexion), comme ccache désactive le cache pour un fichier dont
  la date suit son lancement.

## 2. Bases locales pour données de jeu et outils d'agents

### 2.1 SQLite : ce qui sert ici

- **Format de fichier d'application** : SQLite se présente comme un format de document (un fichier, écritures
  atomiques, lisible sans notre code, compatible depuis 2004, « Data lives longer than code »), souvent plus rapide
  qu'un tas de fichiers. [Certain]
- **`PRAGMA user_version`** : entier libre de l'en-tête, « SQLite makes no use of the user-version itself » ;
  **`application_id`** : identifiant 32 bits du type de fichier. [Certain]
- **Tables `STRICT`** (3.37.0, 2021-11-27) : type déclaré obligatoire, `INT`, `INTEGER`, `REAL`, `TEXT`, `BLOB`,
  `ANY` ; une valeur non convertible sans perte lève une erreur. [Certain]
- **JSON** intégré par défaut depuis 3.38.0 (2022-02-22) ; **JSONB** stocké en BLOB depuis 3.45.0 (2024-01-15),
  « should not use JSONB outside of SQLite » ; `json_each` et `json_tree` pour parcourir. [Certain] Les index sur
  expression ou colonnes générées permettent d'indexer un champ JSON. [Probable]
- **FTS5** : table virtuelle ; mode *external content* (`content='quest', content_rowid='id'`) qui n'indexe que le
  texte d'une table existante (cohérence à la charge de l'application, ou `INSERT … VALUES('rebuild')`) ; tokenizer
  `unicode61 remove_diacritics 2`, `trigram` (sous-chaînes, et `LIKE '%…%'` indexé ; moins de 3 caractères ne
  trouvent rien), `porter` (anglais seulement) ; classement `bm25` ; `snippet` et `highlight`. [Certain]
- **WAL** : lecteurs et écrivain ne se bloquent pas, mais : même machine seulement, fichiers `-wal` et `-shm`
  quasi persistants (« not ideal as an application file format »), WAL qui grossit sans fin si des lecteurs
  restent toujours ouverts (*checkpoint starvation*), et un bogue de corruption rare corrigé en 3.51.3. [Certain]
- **Ouverture en lecture seule** : `file:…?mode=ro` garde le verrouillage normal ; `immutable=1` saute verrous et
  détection de changement et ne convient qu'à un fichier qui ne change **jamais** (sinon résultats faux ou
  `SQLITE_CORRUPT`). [Certain]
- **Python 3.13 `sqlite3`** : `autocommit=False` est le réglage recommandé (le défaut reste l'ancien
  comportement) ; `with con:` valide ou annule mais « neither implicitly opens a new transaction nor closes the
  connection » ; `executescript` valide d'abord une transaction en cours ; adaptateurs de dates par défaut
  dépréciés depuis 3.12. [Certain]
- **`PRAGMA optimize`** à lancer après création d'index et avant fermeture d'une connexion courte ; `foreign_keys`
  désactivé par défaut, à fixer explicitement. [Certain]
- **`ALTER TABLE`** limité (ajout de colonne avec restrictions, suppression de colonne sous conditions) ; tout
  autre changement passe par la procédure en 12 étapes (nouvelle table, copie, suppression, renommage).
  `ALTER COLUMN … SET/DROP NOT NULL` n'existe que depuis 3.53.0 (2026-04-09) : ne pas s'en servir. [Certain]

### 2.2 DuckDB et Datasette

- **DuckDB** : base en colonnes, excellente pour l'analytique ; un seul processus en lecture-écriture ou plusieurs
  en lecture seule ; l'écriture multi-processus passe par un protocole distant encore en bêta (v1.5.2) ou par
  DuckLake avec un catalogue PostgreSQL. [Certain] Pour nous : dépendance ajoutée, format moins pérenne,
  requêtes ponctuelles par identifiant plutôt qu'analytiques, et plusieurs processus (MCP, CLI, pont, mise à jour) :
  **écarté**. [Probable]
- **Datasette** (Simon Willison) : outil d'exploration et de publication d'une base SQLite ; **sqlite-utils 4.0**
  (2026-07-07) ajoute des migrations en fonctions Python décorées, sans retour arrière « by design ». [Certain]
  Intérêt : ouvrir notre base à la main pour la déboguer (`uvx datasette <fichier>` hors du dépôt) ; pas une
  dépendance du paquet. [Supposé]

### 2.3 Entité-attribut-valeur contre tables par type

- **EAV** (une ligne par entité, attribut, valeur) : facile à étendre, mais types perdus (une colonne par type de
  valeur ou des conversions), requêtes pénibles et contraintes impossibles ; des retours d'expérience (Magento,
  Postgres) préfèrent une colonne JSON pour les attributs volatils. [Probable : sources secondaires]
- **Tables par type** : colonnes typées et indexées pour les champs interrogés (niveau, zone, faction, prérequis),
  plus une colonne JSON pour la « traîne » de champs rares. C'est le choix de Factoruide (`m_quest`, `m_npc`…).
- **Notre cas** : les champs interrogés sont connus et peu nombreux par type ; la provenance, elle, est par champ
  et de forme uniforme. D'où : **tables par type** pour les valeurs retenues, **une seule table de forme EAV
  réservée à la provenance** (§ 5).

### 2.4 Provenance par champ : W3C PROV simplifié

PROV-DM (recommandation W3C du 2013-04-30) : *Entity* (« a physical, digital, conceptual, or other kind of thing
with some fixed aspects »), *Activity*, *Agent*, relations `wasGeneratedBy`, `used`, `wasDerivedFrom`,
`wasAttributedTo`, et *Bundle* (ensemble nommé de descriptions de provenance, lui-même une entité). [Certain]

Réduction pour nous [Supposé] : **entité** = la valeur d'un champ d'une entité de jeu ; **agent** = la source
(client à telle version et empreinte, addon X version Y, journal, relevé du joueur) ; **activité** = un passage de
reconstruction (clé de fusion) ; `wasDerivedFrom` = la ligne de `field_provenance` qui relie la valeur retenue à
chaque valeur source ; **bundle** = la base elle-même, identifiée par sa clé. Pas besoin de RDF : quatre colonnes
(`source`, `source_version`, `certainty`, `value_json`) suffisent, ce que `quests.py` fait déjà en JSON.

### 2.5 Ce que font les projets WoW

- **Questie** : une base Lua par type (quêtes, PNJ, objets, objets du monde), indexée par identifiant, champs
  **positionnels** nommés par des tables de clés (`QuestieDB.questKeys`…), fichiers **générés** depuis plusieurs
  sources, puis une couche **Corrections** séparée par type et par extension (une extension plus récente
  surcharge), et une « compilation » en jeu après correction. [Certain] Base historique tirée de MaNGOS ; scripts
  de validation par extension (`cli/validate-<extension>.lua`). [Probable : source secondaire]
- **AtlasLoot Classic Forever** : tables imbriquées instance → boss → `npcID` → objets, taux Classic dans
  `droprate.lua` (selon `docs/DATA_SOURCES.md` du dépôt ; non revérifié sur le site).
- **WoWDBDefs** : définitions des colonnes des tables du client par plage de build (`BUILD`, `LAYOUT`,
  annotations `$id$`, `$relation$`, clés étrangères `type<Table::Colonne>`), lisibles par machine. [Certain]
  wago.tools sert ces tables en CSV par build (`https://wago.tools/db2/<Table>/csv?build=X`, voie de `forever
  fetch`, `docs/ARCHITECTURE.md`).
- **Factoruide** : base SQLite distribuée (brut client + fusionné par type, § 0), sous GPL-2.0+ pour sa part
  VMaNGOS (docstring de `forever/pipeline/factoruide.py`). [Certain, lu localement]
- **Bases « monde » des émulateurs (VMaNGOS, CMaNGOS)** : une table par type (`quest_template`,
  `creature_template`, `item_template`…), identifiant du jeu comme clé, sous GPL ; elles sont à l'origine de la base
  historique de Questie, de la part VMaNGOS de Factoruide, et LibQuestDB lit `quest_template` d'une base CMaNGOS
  convertie en SQLite. [Probable : source secondaire pour LibQuestDB] Conséquence : ce qui dérive de ces bases (ou de
  Factoruide) reste dans le cache local ; rien n'en passe dans le dépôt ni dans `tests/fixtures/` (décision 133).
- **Wowhead** : pas d'export public de base trouvé ; contrôle seulement (décision 128). [Probable]

Leçon commune [Probable] : **identifiant du jeu comme clé**, une table par type, une couche « brut » et une couche
« corrigé ou fusionné », la base **régénérée** depuis ses sources plutôt qu'éditée.

## 3. Sorties d'outils compactes pour agents

- **Anthropic, « Writing effective tools for agents »** (2025-09-11) [Certain] : rendre seulement l'information à
  fort signal ; préférer des noms compréhensibles aux identifiants opaques, en gardant l'identifiant technique
  quand il sert à enchaîner un appel ; un paramètre `response_format` (`concise` ou `detailed`) : 72 contre 206
  jetons dans leur exemple ; pagination, filtrage, sélection de plage et troncature avec des valeurs par défaut
  raisonnables, et un message qui oriente quand on tronque ; regrouper des opérations dans un outil
  (`search_logs` plutôt que `read_logs`) ; erreurs actionnables.
- **Anthropic, « Effective context engineering »** (2025-09-29) [Certain] : le contexte est une ressource finie à
  rendement décroissant ; récupération « juste à temps » à partir d'**identifiants légers** ; divulgation
  progressive.
- **Anthropic, « Code execution with MCP »** (2025-11-04) et **« Advanced tool use »** (2025-11-24) [Certain] : les
  résultats intermédiaires qui traversent le modèle coûtent cher (un flux passe d'environ 150 000 à 2 000 jetons
  quand le filtrage se fait hors du modèle) ; recherche d'outils différée ; exemples d'usage (`input_examples`, 1 à
  5 par outil).
- **Claude Code** (documentation MCP, consultée le 2026-10-21) [Certain] : avertissement au-delà de 10 000 jetons
  (seuil fixe), plafond par défaut de 25 000 jetons (`MAX_MCP_OUTPUT_TOKENS`), au-delà de 50 000 caractères le
  résultat est écrit dans un fichier et remplacé par son chemin ; `_meta["anthropic/maxResultSizeChars"]` relève le
  seuil d'un outil (jusqu'à 500 000 caractères) ; une erreur longue est coupée au milieu.
- **Spécification MCP 2025-11-25** [Certain] : `structuredContent` (avec `outputSchema` facultatif ; un outil qui en
  rend « SHOULD also return the serialized JSON in a TextContent block ») ; liens `resource_link` ; erreurs d'outil
  `isError: true` avec un retour actionnable ; pagination par **curseur opaque** (`nextCursor`) pour les listes du
  protocole (`tools/list`, `resources/list`…), pas pour le contenu d'un résultat d'outil.
- **OpenAI, guide du function calling** (consulté le 2026-10-21) [Certain] : moins de 20 fonctions au départ d'un
  tour, énumérations et objets structurés pour empêcher les états invalides, ne pas faire remplir par le modèle ce
  que le code connaît, fusionner les fonctions toujours appelées à la suite.

**Pour nous** [Probable] : `forever_lookup` suit déjà la bonne forme (un outil, un `kind`, `detail=false` par
défaut, `limit`, `offset`, `total`). La base permet d'aller plus loin sans nouvel outil :
- réponse par défaut = liste de lignes courtes `{id, name, level, zone, status}` + `total` + `next_offset` +
  provenance **résumée une fois** (versions et empreintes des sources, certitude minimale), et non une provenance par
  champ ;
- `detail=true` ou `ids=[…]` pour la fiche complète (valeurs, source et certitude par champ, `discrepancies`) ;
- garder chaque réponse sous l'avertissement de 10 000 jetons plutôt que relever `maxResultSizeChars` ;
- recherche par nom approchée (FTS5) avec, en cas d'échec, des suggestions d'identifiants plutôt qu'une liste.

## 4. Schéma versionné, migrations et reconstruction déterministe

- **Une base de cache ne se migre pas, elle se reconstruit** [Probable]. La version du schéma entre dans la clé ; au
  chargement, `PRAGMA user_version` (et `application_id`) différents de ceux du code = fichier ignoré et rebâti.
  Ainsi, aucune migration à écrire ni à tester, et l'invariant « la base se reconstruit depuis les sources » est
  exercé à chaque changement.
- **Si un jour une base locale doit garder un état non reconstructible** (annotations du joueur, par exemple) :
  migrations numérotées en SQL pur, appliquées dans une transaction et suivies par `user_version` (chaque fichier
  `NNNN_nom.sql` lève la version de 1), avec la procédure en 12 étapes de SQLite pour ce que `ALTER TABLE` ne sait
  pas faire ; c'est ce que font sqlite-migrate et sqlite-utils 4.0, sans retour arrière. [Certain pour les outils,
  Supposé pour l'application]
- **Alembic** : son « batch mode » recopie la table pour contourner les limites d'`ALTER` de SQLite et repose sur la
  réflexion de SQLAlchemy [Certain] : dépendance lourde, **écarté** (décision 16 : pas de dépendance ajoutée sans
  accord).
- **Déterminisme** : un build reproductible donne des copies « bit-by-bit identical » à partir des mêmes sources,
  environnement et instructions (reproducible-builds.org) [Certain]. Pour une base SQLite, l'identité octet par
  octet n'est pas un bon critère (pages, liste libre, version de SQLite) ; comparer un **contenu logique** :
  lignes de chaque table triées par clé, sérialisées en JSON à clés triées, hachées. [Probable] Règles : insertion
  dans un ordre fixe, JSON avec `sort_keys`, aucun horodatage hors d'une table `meta` exclue de la comparaison.
- **Tests (dans `tmp_path`, sans réseau, sources de `tests/fixtures/`)** [Supposé] :
  1. construire deux fois la même base : contenus logiques égaux ;
  2. toucher un fichier source sans le changer (date seule) : aucun étage refait ;
  3. modifier une partie d'une SavedVariables que le lecteur ignore : étage source refait, **fusion non refaite**
     (early cutoff), compteur d'exécutions injecté ;
  4. changer une source : seuls son étage et la fusion sont refaits ;
  5. relever `READ_FORMAT` d'un lecteur : son étage est refait ;
  6. base d'un autre `user_version` : ignorée et rebâtie ;
  7. ménage : garder les N plus récentes, ignorer un fichier encore ouvert ;
  8. SQLite de l'interpréteur : `sqlite_version_info >= (3, 38)` et FTS5 présent (sinon message clair, pas de
     repli silencieux).
  Fermer explicitement chaque connexion (`contextlib.closing`) : sous Windows, un fichier encore ouvert empêche le
  nettoyage de `tmp_path` et le remplacement d'un fichier.

## 5. Architecture recommandée pour notre cas

### 5.1 Les pistes proposées, une par une

| Piste de l'utilisateur | Verdict | Raison | Sources |
| --- | --- | --- | --- |
| Données normalisées par identifiant du jeu, source et certitude par champ | **Retenir** | Même forme que `quests.py` et `dungeons.py` ; identifiant du client comme clé (Questie, Factoruide) ; nom à côté de l'identifiant pour l'agent | Questie, Factoruide, Anthropic 2025-09-11 |
| Clé de cache faite des empreintes des entrées (version de l'addon, empreinte des fichiers, version du jeu, version du lecteur) | **Adapter** | Bonne liste, mais à **deux étages** et avec l'empreinte des **sorties** dans la clé de fusion, sinon pas d'early cutoff ; pas de version du paquet dans la clé | Mokhov et al. 2020, Shake, Ninja, Salsa |
| Reconstruire seulement ce qui a changé | **Retenir** | Par source (étage 1) ; la fusion reste globale mais ne tourne que si une sortie a changé | ccache, Salsa |
| Au passage de la mise à jour et au démarrage du pont | **Retenir, plus un repli** | Ajouter la construction paresseuse au premier appel (CLI seule, MCP sans pont), comme aujourd'hui ; un verrou par clé évite deux constructions simultanées | — |
| SQLite indexé pour les grosses tables, JSON pour les petites données lisibles | **Retenir** | SQLite pour quêtes, objets, PNJ, sorts, zones, donjons ; JSON pour les sorties d'étage 1 (lisibles, comparables) et l'état (`manifest` des fichiers) ; `forever/data/` reste en JSON versionné | SQLite appfileformat |
| Schéma versionné avec migrations | **Adapter** | Version du schéma dans la clé et `user_version` ; reconstruction au lieu de migration (cache) | SQLite pragma, sqlite-utils 4.0 |
| Sorties compactes, résumé et identifiants d'abord | **Retenir** | Prolonger `detail=false` / `limit` / `offset` existants ; provenance résumée une fois par réponse | Anthropic, MCP, OpenAI |
| La base vit dans le cache, se reconstruit, rien dans le dépôt | **Retenir** | Décision 133 (agrégats seulement dans le dépôt) ; précédent `<cache>/dungeons/` | DECISIONS 133 |

### 5.2 Forme proposée [Supposé, à valider au plan]

```
<cache>/kb/
├── files.json                    # manifeste : chemin -> (taille, mtime_ns, sha256)
├── stages/<lecteur>-<clé>.json   # sortie normalisée d'une source + empreinte de sortie
├── kb-<clé de fusion>.sqlite     # base fusionnée, jamais modifiée après construction
├── current.json                  # clé de la dernière base complète (pointeur)
└── build.lock                    # un constructeur à la fois
```

- **Étage 1, par source** : client installé (`forever/data/<version>`, `quest_rewards.json`…), chaque addon
  (Questie, Forever Guide, Naowh, Forever Companion, GearQuest, SkillUp, Forever Bestiary, Talents Forever…), chaque
  SavedVariables, la base Factoruide ; RestedXP reste une cible de livraison, pas une source (décision 253). Un
  lecteur qui échoue (nouveau format d'addon) rend « source illisible » avec une note, comme « Questie absent »
  aujourd'hui : la base se construit sans elle, jamais d'échec global.
- **Étage 2, fusion** : règles de priorité actuelles (`PRIORITY` de `quests.py`, `ORDER` de `dungeons.py`)
  appliquées une fois, écrites dans `kb-<clé>.sqlite.tmp`, puis `os.replace` vers le nom final (personne ne l'a
  encore ouvert, donc pas de blocage Windows). `os.replace` écrase sans prévenir : tester d'abord l'existence du nom
  final (sous le verrou) et ne renommer que s'il est absent ; s'il existe déjà (autre constructeur), supprimer le
  `.tmp`.
- **Lecture** : `file:kb-<clé>.sqlite?mode=ro` (ou `immutable=1`, valable puisque le fichier ne change jamais) ;
  journal `delete`, **pas de WAL** (inutile en lecture seule, laisse des fichiers annexes). Pendant la
  construction : une seule transaction, index créés après le remplissage, `PRAGMA optimize` à la fin.
- **Ménage** : garder les N dernières bases et les étages qu'elles référencent ; supprimer le reste ; un
  `PermissionError` (fichier encore ouvert par le pont sous Windows) est ignoré et retenté au passage suivant. Le
  même ménage manque aujourd'hui à `<cache>/quests/` et `<cache>/dungeons/`.
- **Schéma (esquisse)** :
  - `meta(key, value)` : clé de fusion, version du schéma, versions des lecteurs, date (exclue des comparaisons) ;
  - `source(id, name, addon_version, files_sha, read_format, status, note)` ;
  - une table `STRICT` par type : `quest(id INTEGER PRIMARY KEY, name TEXT, level INT, min_level INT, zone INT,
    faction TEXT, status TEXT, extra TEXT /* JSON */)`, de même `npc`, `item`, `spell`, `zone`, `dungeon`, avec les
    relations en tables (`quest_prereq`, `quest_giver`, `item_source`, `dungeon_boss`, `boss_loot`) ;
  - `field_provenance(entity_type, entity_id, field, source, certainty, value_json, chosen)` et une vue
    `discrepancy` (champs dont les sources divergent) ;
  - `name_fts` (FTS5 `trigram`, contenu externe) sur les noms anglais, et le français quand une source le donne.
- **Outils** : pas de nouvel outil ; `forever_lookup` et les services existants lisent la base au lieu de
  reconstruire leur livre, avec la forme de sortie du § 3. La CLI gagne `forever kb status | build | gc`.
- **Coût estimé** : quelques dizaines de milliers de lignes par type, de quelques Mo à quelques dizaines de Mo par
  base ; Factoruide, avec couche brute du client et images de cartes, fait 91 Mo. [Supposé]

### 5.3 Décision 288 : les deux questions

- *Qui maintient déjà ça mieux que nous ?* Les addons et le client maintiennent les données ; la base ne les refait
  pas, elle les **indexe** et les fusionne pour des requêtes précises. Nous ne maintenons que des lecteurs et des
  règles de fusion, déjà écrits.
- *Que se passe-t-il au prochain patch ?* La clé change, la base se reconstruit seule ; un lecteur cassé dégrade
  sa source en « illisible », le reste est servi. Aucune valeur de la base n'est fixée par un test : les tests
  portent sur les fixtures et sur le mécanisme.

### 5.4 Ce qu'il faut éviter

- Un fichier SQLite **unique modifié sur place** et partagé par le MCP, la CLI, le pont et `forever update` :
  verrous et remplacement impossibles sous Windows tant qu'un processus l'a ouvert, WAL et ses fichiers annexes,
  migrations à écrire. [Probable]
- Une **clé globale** faite des seules entrées (cas actuel) : pas d'early cutoff, tout est refait à chaque
  déconnexion du jeu.
- La **date seule** comme empreinte (Make, `quests.py`) et le **hachage complet** à chaque appel (`dungeons.py`).
- Un cache **sans limite** (194 Mo de livres de quêtes périmés aujourd'hui).
- Un **EAV généralisé** pour les valeurs ; un ORM, Alembic ou DuckDB (dépendances, décision 16).
- `immutable=1` sur un fichier qui peut changer ; comparer les **octets** d'un `.sqlite` dans un test.
- Recopier la base ou des tables d'addons dans `forever/data/` ou `tests/fixtures/` (décision 133) : fixtures
  synthétiques ou agrégats seulement.
- Lire un test dans le vrai cache ou le dossier du jeu (tests en parallèle, `tmp_path` seulement).
- Rendre la base entière dans une réponse d'outil ou relever `maxResultSizeChars` pour y arriver.

## Recommandation

1. Faire de la base une **couche de lecture** reconstruite dans `<cache>/kb/`, jamais dans le dépôt, à deux étages
   d'empreintes : sorties par source (JSON) puis fusion (SQLite), la clé de fusion faite des **empreintes des
   sorties** (early cutoff), des constantes `READ_FORMAT` / `MERGE_FORMAT` et de la version du schéma.
2. Empreintes des fichiers par manifeste « taille, date, sha256 », rehachage seulement si taille ou date bougent.
3. SQLite de la bibliothèque standard : tables `STRICT` par type d'entité, une table de provenance par champ, FTS5
   sur les noms ; fichier écrit sous un nom temporaire puis renommé, lu en lecture seule, jamais migré ; ménage aux
   N dernières bases.
4. Construction à la fin de `forever update`, au démarrage du pont (en tâche de fond), et au premier appel si la
   base manque ; verrou par constructeur.
5. Sorties : identifiants, noms et résumé par défaut, provenance résumée une fois, détail par `detail` ou `ids`,
   pagination existante ; rester sous 10 000 jetons par réponse.
6. Commencer par un pilote : porter `quests` et `dungeons` (qui ont déjà fusion et provenance par champ) sur la
   base, mesurer, puis étendre aux objets, PNJ, sorts et zones.

**À trancher par l'utilisateur** : (a) une base commune à tous les domaines ou une base par domaine (je recommande
une seule, avec un étage par source) ; (b) la construction au démarrage du pont, qui ajoute du travail à ce moment ;
(c) le nombre de bases gardées (N) ; (d) la recherche plein texte limitée aux noms ou étendue aux objectifs de
quête.

## Sources

Dépôt (lu le 2026-10-21) : `docs/ARCHITECTURE.md`, `docs/research/architecture-agent.md`,
`docs/research/lecture-directe-client.md`, `docs/DECISIONS.md` (décisions 16, 123, 133, 253, 272, 288),
`docs/DATA_SOURCES.md`, `forever/store.py`, `forever/mcp_server.py`, `forever/quests.py`, `forever/dungeons.py`,
`forever/pipeline/factoruide.py` ; mesures du cache local (`~/.cache/forever/`) et lecture seule de la base
Factoruide le 2026-10-21.

Build et cache incrémental :
- Mokhov, Mitchell, Peyton Jones, *Build systems à la carte: Theory and practice*, Journal of Functional
  Programming 30, e11, publié le 2020-04-21, DOI 10.1017/S0956796820000088 (version ICFP 2018 :
  https://www.microsoft.com/en-us/research/publication/build-systems-la-carte/) ;
  PDF : https://ndmitchell.com/downloads/paper-build_systems_a_la_carte_theory_and_practice-21_apr_2020.pdf
- Salsa, algorithme (consulté le 2026-10-21) : https://salsa-rs.github.io/salsa/reference/algorithm.html
- rust-analyzer, *Durable Incrementality*, 2023-07-24 :
  https://rust-analyzer.github.io/blog/2023/07/24/durable-incrementality.html
- ccache, manuel (consulté le 2026-10-21) : https://ccache.dev/manual/latest.html
- Bazel, *Remote caching* (consulté le 2026-10-21) : https://bazel.build/remote/caching
- Ninja, manuel (consulté le 2026-10-21) : https://ninja-build.org/manual.html
- Nix 2.28, *Content-addressing derivation outputs* (consulté le 2026-10-21) :
  https://nix.dev/manual/nix/2.28/store/derivation/outputs/content-address
- Reproducible Builds, définition (consultée le 2026-10-21) : https://reproducible-builds.org/docs/definition/

SQLite, Python et bases locales :
- SQLite, PRAGMA (consulté le 2026-10-21) : https://www.sqlite.org/pragma.html
- SQLite, WAL : https://www.sqlite.org/wal.html ; URI (`mode=ro`, `immutable`) : https://www.sqlite.org/uri.html
- SQLite, FTS5 : https://www.sqlite.org/fts5.html ; JSON : https://www.sqlite.org/json1.html
- SQLite, tables STRICT : https://www.sqlite.org/stricttables.html ; ALTER TABLE :
  https://www.sqlite.org/lang_altertable.html ; format d'application : https://www.sqlite.org/appfileformat.html
  (toutes consultées le 2026-10-21)
- Python 3.13, module `sqlite3` (consulté le 2026-10-21) : https://docs.python.org/3.13/library/sqlite3.html
- uv 0.7.21, notes de version (restauration de FTS5 sur macOS et Linux) :
  https://newreleases.io/project/pypi/uv/release/0.7.21
- DuckDB, concurrence (consulté le 2026-10-21) : https://duckdb.org/docs/current/connect/concurrency.html
- Alembic, *batch migrations* (consulté le 2026-10-21) : https://alembic.sqlalchemy.org/en/latest/batch.html
- Simon Willison, sqlite-utils 4.0, 2026-07-07 : https://simonwillison.net/2026/Jul/7/sqlite-utils-4/
- EAV, sources secondaires (consultées le 2026-10-21) :
  https://leapcell.io/blog/the-enticing-trap-of-entity-attribute-value-schemas ,
  https://www.educative.io/courses/the-art-of-postgresql/entity-attribute-values
- W3C PROV-DM, recommandation du 2013-04-30 : https://www.w3.org/TR/prov-dm/ ; vue d'ensemble :
  https://www.w3.org/TR/prov-overview/

Projets WoW :
- Questie, wiki *Corrections* (consulté le 2026-10-21) : https://github.com/Questie/Questie/wiki/Corrections
- WoWDBDefs (consulté le 2026-10-21) : https://github.com/wowdev/WoWDBDefs
- Questie, origine MaNGOS et scripts de validation (sources secondaires) :
  https://elijahketchersid.com/forums/thread-8958.html , https://wowinterface.com/downloads/info24994-Questie.html

Outils pour agents :
- Anthropic, *Writing effective tools for agents*, 2025-09-11 :
  https://www.anthropic.com/engineering/writing-tools-for-agents
- Anthropic, *Effective context engineering for AI agents*, 2025-09-29 :
  https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Anthropic, *Code execution with MCP*, 2025-11-04 : https://www.anthropic.com/engineering/code-execution-with-mcp
- Anthropic, *Introducing advanced tool use*, 2025-11-24 : https://www.anthropic.com/engineering/advanced-tool-use
- Claude Code, MCP (limites de sortie, consulté le 2026-10-21) : https://code.claude.com/docs/en/mcp
- Spécification MCP 2025-11-25, outils : https://modelcontextprotocol.io/specification/2025-11-25/server/tools ;
  pagination : https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/pagination
- OpenAI, *Function calling* (consulté le 2026-10-21) :
  https://developers.openai.com/api/docs/guides/function-calling
