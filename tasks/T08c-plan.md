# T08c — Valeurs des correctifs du serveur (`DBCache.bin`) : plan

Demande de l'utilisateur du 2026-10-02 (décision 170), section T08c de `docs/ROADMAP.md`, précisée par la commande
`/tranche T08c` du même jour (7 points). Plan écrit sans code ; exécution dans une nouvelle session, sur la branche
`t08c`, un cycle rouge → vert par bloc.

## Questions décisives et réponses (2026-10-02)

1. **Source des définitions de structure** : **WoWDBDefs**, accord réseau donné : les fichiers `.dbd` des tables
   utiles lus une seule fois sur `raw.githubusercontent.com/wowdev/WoWDBDefs/<commit>/definitions/<Table>.dbd`, le
   commit épinglé par l'API GitHub (`api.github.com/repos/wowdev/WoWDBDefs/commits/master`), par `forever fetch`,
   gardés dans le cache. Chaque disposition est ensuite **validée en local** contre les CSV de 70170 (bloc B). Un
   nouveau relevé (autre commit, autre version) redemande l'accord.
2. **Noms français** : préférence durable de l'utilisateur, **il joue avec le client en anglais (enUS) et converse
   en français**. Le profil porte la langue du client (`game_locale` `enUS`) ; les skills du plugin citent les noms
   de sorts, de talents, d'objets et de zones **tels qu'ils apparaissent dans le client** (anglais), avec le nom
   français entre parenthèses quand il est connu ; le reste de la réponse reste en français (bloc F). Conséquence
   pour T08c : le `DBCache.bin` frFR (29/09, avant la refonte) n'est pas lu ; les nouveaux talents n'ont pas de
   `name_fr`, ce qui est listé dans le rapport sans bloquer.
3. **Contrôle contre Talents Forever** : **rapport ponctuel** (`docs/research/guerrier-T08c-talents-forever.md`), par
   un script hors du paquet qui lit `Data.lua` en local par `forever/pipeline/lua_table.py` ; agrégats seulement ; le
   lecteur durable reste à FA1.

Écart avec la ROADMAP à reporter au bloc G : la ROADMAP prévoit une « origine propre dans `origins.json` » et une
« fixture synthétique » ; la commande demande l'origine **« client »** et des fixtures **extraites du `DBCache.bin`
de l'utilisateur**. La commande fait foi ; la section T08c de la ROADMAP est corrigée en fin de tranche.

## Contexte relevé pendant le plan (lecture locale seulement, aucun réseau)

- `Cache/ADB/enUS/DBCache.bin` : 6 133 744 octets, daté du 2026-10-02 13:29. En-tête `XFTH`, **format 9, build
  70170**, puis 32 octets de contrôle. Puis 129 839 entrées contiguës, sans alignement, chacune : `XFTH`, `int32`
  (70 sur tout le fichier, sens non établi, noté `region_id`), `int32 push_id`, `uint32 unique_id`, `uint32
  table_hash`, `uint32 rec_id`, `uint32 data_size`, `uint8 status` + 3 octets de bourrage, puis `data_size` octets.
- **Hachage des noms de tables** : `SStrHash` de Storm (nom en majuscules, graine 0x7FED7FED) ; vérifié :
  `TraitNode` → `0xE1432D63`, `ItemSparse` → `0x919BE54E`. 34 hachages distincts, 26 reconnus parmi les tables du
  projet ; 8 inconnus (les tables de `Hotfix.log` hors du projet : `SpellCastingRequirements`, `SpellEquippedItems`,
  `SpellPowerDifficulty`, `SpellScript`…).
- **Statuts** : 1 `VALID` (13 908, avec données), 2 `DELETE` (97 796, taille 0), 3 `INVALID` (15 561, **taille 0 :
  aucune valeur portée**, réponse à DON2), 4 `NOTPUBLIC` (2 574 : `TactKey` 2 573, `SpellClassOptions` 73078 ; taille 0).
- **Réponses `DBReply`** : `push_id` −1 et `unique_id` 0xFFFFFFFF (`ItemSparse` 99 153, `Spell` 15147 ×14) ; ce
  sont des réponses « enregistrement absent » à une requête du client (98 861 lignes `DBReply` dans `Hotfix.log`),
  **jamais des suppressions** de lignes des tables.
- **Recoupement avec `Hotfix.log`** (129 217 lignes, réécrit au démarrage du 02/10 08:00:10) : pour chacune des 23
  tables `Trait*`, `Spell*`, `Curve*` présentes des deux côtés, les comptes `VALID`, `DELETE`, `INVALID`,
  `NOTPUBLIC` sont **identiques** (par exemple `TraitNode` 14 `VALID` + 3 `DELETE`, `SpellName` 20 + 1). Poussées :
  112323 (un nœud de l'arbre 1188, hors classe), 112340 (`GlobalStrings`), **112347** (refonte du Guerrier) et 112349.
- **Ordre des octets ≠ ordre des colonnes des CSV de wago.tools** pour les tables à identifiant non intégré
  (`SpellEffect` 136 octets, `SpellMisc` 119, `SpellLevels` 17 : identifiant absent des données, relation `SpellID`
  ailleurs) ; ordre identique pour `Trait*` et `CurvePoint` (identifiant intégré). D'où les types exacts de WoWDBDefs.
- **Valeurs lues provisoirement** (dispositions déduites à la main pour `Trait*`, à confirmer par WoWDBDefs au bloc B
  avant tout verrouillage de test) :
    - `TraitNode` (arbre 1117, Guerrier) : 105928 `PosX` 6220 → 5620 ; 105953 `PosX` 6820 → 5020 ; 105962 `PosX`
      10880 → 10280 et `PosY` 4530 → 5130 ; supprimés 105929, 105936, 105973 ; **nouveaux 113569** (`PosX` 6220,
      `PosY` 5130) et **113570** (`PosX` 10280, `PosY` 2130) ; 110298 (arbre 1188) `Flags` 10 → 8.
    - `TraitNodeEntry` nouveaux : 141191 (définition 145863, `MaxRanks` 2), 141192 (définition 145864, `MaxRanks` 5).
    - `TraitNodeXTraitNodeEntry` nouveaux : 139873 (nœud 113569 → entrée 141191, `_Index` 100), 139874 (113570 →
      141192) ; supprimés 128126, 128133, 128170.
    - `TraitEdge` : supprimées 124811 (105931 → 105928), 132568, 136314 ; nouvelles 136735 (105931 → 113569, `Type`
      2) et 136736 (105927 → 105928, `Type` 2).
    - `TraitDefinition` : 135484 `SpellID` 1310236 → 1323963 ; 142603 `SpellID` 12962 → 1323964 ; nouvelles 145863
      (`SpellID` 1323967) et 145864 (`SpellID` 12962) ; 145860 supprimée.
    - `TraitDefinitionEffectPoints` : 25094 `CurveID` 112760 → 111755 ; **25099 `VALID` mais identique au CSV** ;
      nouvelles 25180 à 25186 (courbes 125259 à 125265) ; supprimées 23597, 24568, 24569, 25167, 25179 (25179 absente
      du CSV).
    - `CurvePoint` 334737 : courbe 111755, `Pos` (1.0, 20.0), ordre 0 ; 30 `VALID`, 5 `DELETE`. `Curve` : 7 `VALID`,
      pas de CSV dans le cache (table listée par T08b, non décodée par le pipeline).
    - `SpellName` (20 `VALID`) : Whirlwind, Intimidating Shout, Booming Voice, Unbridled Wrath, Piercing Howl, Enrage,
      Blood Craze, Dual Wield Specialization, Enraged Regeneration, Echoes of Gladiator Stance, Raging Blows, Furious
      Precision, Lingering Rage ×3, Gore Drinker ×3, Serpentbloom Snake.
- Géométrie : les nouvelles positions tombent sur la grille de `decode_rules.json` (`talent_geometry` : origines 1020,
  5020, 9080, pas de 600, `row_base` 2130) : 113569 → rangée 6 de l'arbre du milieu, 113570 → rangée 1 du troisième.
- `Cache/ADB/frFR/DBCache.bin` : daté du 29/09 (avant la refonte) ; non lu (réponse 2).
- `WTF/Config.wtf` : `SET textLocale "enUS"` (source locale de `game_locale`, bloc F).
- Talents Forever 0.35.0 (`tasks/inventaire-addons.md`) : `Data.lua` du build 70170 généré le 2026-10-01 ; son
  `CHANGELOG.md` dit que la refonte du Guerrier n'est pas dans les fichiers du build : **l'écart sur les nœuds de la
  refonte est attendu par construction**.
- Note officielle du 01/10 révisée le 02/10 (`docs/research/notes-blizzard-2026-10-01.md`, lignes Guerrier) : Fureur
  (nouveaux talents Lingering Rage, Furious Precision, Gore Drinker ; Improved Cleave et Boundless Rage retirés ;
  Flurry exige Death Wish au lieu d'Enrage ; Improved Berserker Rage en rangée 5), Protection (Iron Will,
  Anticipation, Improved Bloodrage, Improved Revenge, Improved Disarm, Improved Shield Bash déplacés ; Toughness
  retiré).
- Dernier rejeu des builds de T05 : `70170-r2` ; la révision 3 n'a pas été rejouée.

## Choix d'architecture (sans question)

- **Lecture** : `forever/pipeline/dbcache.py`, fonctions pures sur des octets ; le chemin du fichier vient de
  `FOREVER_WOW_DIR` (`Cache/ADB/<locale>/DBCache.bin`, locale `enUS` par défaut, option `--dbcache`). Jamais de
  réseau ; dans les tests, seulement la fixture.
- **Règles d'application des entrées** (format, pas règle de jeu ; chacune testée) :
    - `VALID` : la ligne du correctif remplace la ligne de même identifiant, ou **s'ajoute** si l'identifiant est
      absent des tables du build ;
    - `DELETE` d'une poussée réelle (`push_id` ≥ 0) : la ligne est retirée ; absente des tables : ignorée et listée ;
    - `INVALID` et `NOTPUBLIC` : jamais appliqués, valeur du build gardée, listés à part ; `TactKey` (clés de
      chiffrement) est **ignorée sans être lue ni affichée**, ni dans une sortie ni dans une fixture ;
    - réponses `DBReply` (`push_id` −1) : jamais appliquées, comptées à part ;
    - plusieurs entrées pour une même table et un même enregistrement : la **poussée la plus haute** gagne, à
      poussée égale la dernière dans l'ordre du fichier (aucun cas réel aujourd'hui : cas synthétique signalé dans la
      fixture) ;
    - hachage inconnu, ou table sans disposition validée : listé (hachage, comptes), jamais décodé ni appliqué.
- **Dispositions** : `forever/pipeline/dbd.py` lit le format `.dbd` (colonnes typées, blocs `BUILD`/`LAYOUT`,
  `$id$`, `$noninline$`, `$relation$`, tailles `<8>`…`<64>`, `u` non signé, tableaux `[N]`, `locstring`) et choisit
  le bloc qui couvre `1.60.1.70170`. Les noms produits sont ceux des CSV de wago.tools (`Name_lang`, `Pos_0`), pour
  que la ligne décodée soit une `Row` comme les autres. **Pas de bloc pour ce build** : la table est listée « sans
  disposition » ; aucune disposition voisine n'est prise sans validation.
- **Validation d'une disposition** (bloc B), table par table, avant toute application : (1) noms des colonnes
  identiques à l'en-tête du CSV de 70170 ; (2) taille de chaque entrée `VALID` égale à la taille de la disposition
  (tables sans chaîne) ou chaînes lues exactement jusqu'au bout ; (3) identifiant intégré égal à `rec_id` ; (4)
  pour les entrées dont l'identifiant existe dans le CSV, au moins 90 % des valeurs égales à la ligne du CSV (une
  disposition fausse donne du bruit partout), **ou** (4') pour une table sans ligne comparable, références résolues
  vers les autres tables corrigées ou du build (`TraitNodeEntry.TraitDefinitionID` → `TraitDefinition`…). Échec :
  table listée « disposition non validée », rien appliqué. Le seuil est un paramètre de l'outil, pas un chiffre de jeu.
- **Superposition en mode forever** : à la lecture des tables (`load_tables`, `load_class_tables`, `load_pet_tables`,
  `load_character_tables` de `decode.py`), avant tout décodeur : chaque décodeur reçoit des lignes déjà corrigées ;
  rien n'est recalculé ailleurs. Commande : `forever decode 1.60.1.70170 --hotfixes [--dbcache <chemin>]` écrit une
  candidate ; l'installation passe par `forever install <candidate>` (révision suivante, accord, rapport), comme
  toute révision. **Garde de build** : le build de l'en-tête de `DBCache.bin` doit égaler celui de la version, sinon
  refus (une valeur de correctif vaut pour le build du client qui l'a reçue, T08a).
- **Mode seed intouché** : les fichiers `_seed_*` et tout ce que le mode seed lit sont hérités tels quels ; un test
  compare leurs octets avant et après la superposition, et les résultats du mode seed restent ceux des tests de
  parité.
- **Provenance** : origine **« client »** dans `origins.json` (inchangé : les motifs existants couvrent les fichiers
  décodés) ; la provenance du correctif est portée (a) par **chaque entité touchée** (talent, sort, capacité de
  familier, bijou), champ `hotfix` : `pushes`, `rows` (« TraitNode 105928 »…), `first_logged_at` (première ligne de
  la poussée dans le journal `hotfixes.json` de T08b, heure locale du client) ; (b) par **`sources.json`**, bloc
  `hotfixes` : `DBCache.bin` (locale, format, build, taille, sha256, date de lecture), WoWDBDefs (dépôt, commit,
  sha256 de chaque `.dbd`), poussées appliquées, `max_push`, comptes par table et par statut, listés. **Aucun nouveau
  fichier dans `forever/data/<version>/`** (pas de changement de comptes de fichiers). `hotfix` entre dans les
  métadonnées de `value_diff.META` et de `origins.py` (comme `source`).
- **Date** : `DBCache.bin` ne porte aucune date. La date affichée est **« vu par le client le … »** (première ligne
  de la poussée dans `Hotfix.log`, gardée par `hotfixes.json`), jamais une date de publication. Poussée absente du
  journal : « date inconnue », la date du fichier `DBCache.bin` en regard.
- **Certitude** : une valeur appliquée garde la certitude du client (`FC-1.60.1.70170`, `certain`) quand sa table a
  passé la validation (4) ou (4') et la garde de build ; sinon elle n'est pas appliquée.
- **Rejeu** : `scripts/replay_builds.py run 70170-r3` sur les données actuelles d'abord (la révision 3 n'a jamais été
  rejouée), puis `run T08c` sur la candidate, `compare 70170-r3 T08c` : chaque écart vient des seuls correctifs.

## Blocs et étapes

Ordre : A, B, C, D, E, F, G. F est indépendant (reprise possible si un autre bloc attend une correction). Chaque
bloc : tests rouges committés (« T08c: tests (bloc X) »), `tasks/.rouge` et `tasks/.tests-verrouilles` réécrits,
puis vert (« T08c: bloc X vert »), fichiers supprimés.

### Bloc A — Lecture de `DBCache.bin` et recoupement avec `Hotfix.log` (point 1)

1. Fixture `tests/fixtures/hotfix/DBCache.bin` **extraite du fichier de l'utilisateur** par
   `scripts/extract_dbcache_fixture.py` (lecture locale, écriture par `write_bytes`, en-tête recopié, entrées
   choisies, plus deux entrées synthétiques signalées : même enregistrement à deux poussées positives) : toutes les
   entrées `Trait*`, `CurvePoint` et `Curve` des poussées 112323 et 112347 ; les entrées `Spell*` des sorts du
   Guerrier de la poussée 112347 ; une entrée de la poussée 112349 ; une `DBReply` absente (`Spell` 15147, deux
   copies) ; l'`INVALID` `SpellPower` 315008 ; le `NOTPUBLIC` `SpellClassOptions` 73078 ; une entrée de hachage
   inconnu ; **aucune entrée `TactKey`**. `README.md` de la fixture complété (origine, date, sélection, synthétiques).
   Extrait de `Hotfix.log` complété par les lignes des mêmes poussées.
2. `dbcache.py` : `table_hash`, `parse_dbcache`, `read_dbcache`, `effective`, `crosscheck`.
3. `forever hotfixes` lit aussi `DBCache.bin` : par table, comptes par statut (`DBReply` à part), recoupement avec
   le journal (lignes sans entrée, entrées sans ligne), hachages inconnus ; la note « valeurs non lues » disparaît.

### Bloc B — Définitions de WoWDBDefs et validation des dispositions (point 2)

1. `forever fetch 1.60.1.70170 --dbd` (réseau, `forever/pipeline/fetch.py`, `Deps.http_get`) : commit épinglé,
   `.dbd` des tables de `decode_rules.json` (`tables`, `class_tables`, `character_tables`, `pet_tables`,
   `hotfix_related_tables`) et de `TraitNodeGroupXTraitNode`, rangés dans `<cache>/dbd/<commit>/`, index `dbd.json`
   (commit, sha256 par fichier, date, licence relevée dans le dépôt). **Point d'accès réseau unique, déjà accordé**.
2. **Licence** : si celle de WoWDBDefs permet la copie, `tests/fixtures/dbd/` reçoit les `.dbd` réduits au bloc du
   build 70170 avec attribution ; sinon seulement des dispositions dérivées (JSON écrit par le script), sans texte du
   dépôt.
3. `dbd.py` : `parse_dbd`, `layout_for`, `decode_record`, `validate_layout`.
4. **Confirmation des valeurs attendues** : décoder les entrées de la fixture avec les dispositions de WoWDBDefs et
   comparer aux valeurs provisoires du contexte ; tout écart corrige les valeurs attendues **avant** verrouillage
   (et se signale à l'utilisateur dans le résumé du bloc).
5. Contrôle de la prémisse « CSV de wago.tools = fichiers du build sans correctif » : compter les entrées `VALID`
   identiques au CSV (25099 en est une) ; si la part est forte, s'arrêter et en parler (« avant » serait déjà corrigé).

### Bloc C — Superposition en mode forever et décodage de la candidate (point 3)

1. `forever/pipeline/hotfix_overlay.py` : `apply_hotfixes`, appelé par les fonctions de chargement des tables de
   `decode.py` quand `decode_version(..., hotfixes=...)` le demande.
2. Champ `hotfix` sur chaque entité touchée (`classes.json`, `talents.json`, `spells.json`, `spell_scaling.json`,
   `pets.json`, `pvp_items.json`) ; bloc `hotfixes` de `sources.json` de la candidate.
3. Fixture `tests/fixtures/wago/1.60.1.70170/enUS/` (nouvelle) : CSV réduits à l'arbre du Guerrier (arbre 1117, ses
   nœuds, entrées, définitions, arêtes, points de courbe, sorts cités) et aux lignes touchées par la fixture
   `DBCache.bin`, par `scripts/extract_class_fixtures.py` étendu (`--version`, `--classes`), écriture `newline="\n"`.
4. `forever decode 1.60.1.70170 --hotfixes` ; garde de build ; refus si une table a une disposition non validée et
   des entrées `VALID` qui toucheraient une entité (message : table, comptes, commande de diagnostic).

### Bloc D — Valeurs corrigées dans `forever diff` et `forever hotfixes` (point 4)

1. `forever diff <a> <b>` compare les **valeurs** de `classes.json`, `talents.json`, `spells.json`, `pets.json` et
   `pvp_items.json` (T08b ne le faisait que pour `spell_scaling.json` et `character_scaling.json`) : ligne par
   valeur (`Warrior Fury <talent> tier`, `… prereqs`, ajout et retrait de talent), suivie de l'attribution du
   correctif quand l'entité porte `hotfix` (« correctif 112347, vu par le client le 2026-10-02 08:00 »).
2. `forever hotfixes --values` : pour chaque enregistrement appliqué, table, identifiant, statut, poussée, date vue,
   **champ : valeur du build → valeur du correctif** (lignes du CSV et de `DBCache.bin`), entité touchée ; à part :
   `INVALID`, `NOTPUBLIC`, `DBReply`, hachages inconnus, dispositions non validées. JSON avec provenance.
3. `entity_assumptions` (consultation) : « corrigé par le serveur, valeur appliquée (révision N) » quand la poussée
   est dans `sources.json`, sinon « corrigé par le serveur le …, valeur non appliquée : `forever hotfixes --values` ».

### Bloc E — Veille locale des nouveaux correctifs (point 7)

1. `forever/watch.py` : détecteur `dbcache` (empreinte taille + date dans l'état de veille ; analyse seulement si elle
   change) ; compare les entrées `VALID`/`DELETE` des tables suivies à `sources.json` `hotfixes` de la révision
   installée (poussée, table, enregistrement, `unique_id`) ; « N correctifs du serveur non appliqués depuis la
   révision R du <date> (tables …) » ; actions proposées sans rien lancer : `forever hotfixes --values`, `forever
   decode <version> --hotfixes`, `forever diff`, `forever install` (accord). Build de `DBCache.bin` différent de la
   version installée : « correctifs d'un autre build, non applicables ».
2. Ligne de démarrage de session (`forever/hooks.py`) : une ligne compacte quand ce compte est non nul.

### Bloc F — Langue du client et noms cités dans les skills (réponse 2)

1. Profil joueur (hors du dépôt) : champ `game_locale` au niveau du joueur, sourcé : `client` (lu dans
   `WTF/Config.wtf`, `textLocale`, lecture locale) ou `joueur` (`forever profile set --game-locale enUS`, qui
   l'emporte) ; `forever profile show` et l'outil MCP `forever_player_profile` le rendent.
2. Skills du plugin (`forever-router` d'abord, puis `forever-mage`, `forever-builds`, `forever-pvp`,
   `forever-familiers`, `forever-leveling`) : règle « noms du client » : nom tel qu'il apparaît dans le client du
   joueur (`game_locale` ; anglais pour `enUS`), nom français entre parenthèses quand l'outil le rend, réponse en
   français. Cas d'évaluation du plugin mis à jour si l'un attend un nom français seul ; version du plugin 0.7.0.
3. Mémoire de l'assistant déjà écrite (`client-locale-enus`).

### Bloc G — Application réelle, contrôle du Guerrier, rejeu et point d'arrêt (points 5 et 6)

Hors tests, sur les fichiers du poste :
1. `forever fetch 1.60.1.70170 --dbd` (accord donné), `forever hotfixes --values`, puis `forever decode 1.60.1.70170
   --hotfixes` sur le `DBCache.bin` réel.
2. **Contrôle du Guerrier** : dans la candidate, `classes.json` Warrior contient les nouveaux talents de la
   refonte, positions résolues (aucun nœud Guerrier dans `unresolved_nodes`) ; comparaison à la note officielle
   (talents ajoutés, retirés, déplacés, prérequis de Flurry, rangée d'Improved Berserker Rage) ; tout écart avec la
   note listé, jamais forcé.
3. **Rapport Talents Forever** : `scripts/compare_talents_forever.py` (lecture locale, agrégats) ; nœud, sort,
   rangée, colonne et rangs de l'arbre du Guerrier de la candidate face à `Data.lua` (70170) ; écart attendu : les
   nœuds de la refonte ; **tout autre écart signalé** ; rapport `docs/research/guerrier-T08c-talents-forever.md`. Les
   arbres des huit autres classes y sont comparés aussi quand c'est le même script (aucun correctif ne les touche :
   ils doivent concorder ; sinon écart listé pour FA1).
4. **Rejeu des builds de T05** : `run 70170-r3`, puis `run T08c` sur la candidate, `compare 70170-r3 T08c` ;
   résultat écrit dans `docs/research/builds-T05.md` (section « Rejeu T08c ») ; attendu : aucun changement du Mage
   (les correctifs touchent le Guerrier et quelques sorts), **montré explicitement** même s'il est vide.
5. **Point d'arrêt** : montrer à l'utilisateur, avant tout commit de données, la sortie de `forever diff` (valeurs
   corrigées), le contrôle du Guerrier, le rapport Talents Forever et chaque recommandation de T05 qui change avec sa
   raison. Après accord seulement : `forever install <candidate>` en **révision 4 de 1.60.1.70170** (motif : valeurs
   des correctifs du serveur du 2026-10-02, poussées appliquées), rapport `docs/research/data-1.60.1.70170-r4.md`.
6. Documentation : `docs/DATA_SOURCES.md` (`DBCache.bin` lu, WoWDBDefs, règles d'application, `db2tool` non
   utilisé), `docs/DECISIONS.md` (décision de l'origine « client », de la source des dispositions, de la langue du
   client), `docs/ROADMAP.md` (T08c réalisée, écarts de la section corrigés, note pour FA1 : arbres corrigés
   disponibles), `docs/USAGE.md` (`fetch --dbd`, `decode --hotfixes`, `hotfixes --values`, `profile set
   --game-locale`), `docs/OPEN_QUESTIONS.md` (DON1 résolue pour les tables décodées, DON2 répondue en partie, DON3
   mise à jour par les comptes d'`Item`, questions nouvelles ci-dessous).

## Fichiers

- Nouveaux : `forever/pipeline/dbcache.py`, `forever/pipeline/dbd.py`, `forever/pipeline/hotfix_overlay.py`,
  `scripts/extract_dbcache_fixture.py`, `scripts/compare_talents_forever.py`, `tests/fixtures/hotfix/DBCache.bin`,
  `tests/fixtures/dbd/` (`.dbd` réduits ou dispositions dérivées), `tests/fixtures/wago/1.60.1.70170/` (README et
  CSV réduits), `tests/fixtures/wow/WTF/Config.wtf` (une ligne `textLocale`), `tests/unit/test_dbcache.py`,
  `tests/unit/test_dbd.py`, `tests/unit/test_hotfix_overlay.py`, `tests/unit/test_hotfix_values.py`,
  `docs/research/guerrier-T08c-talents-forever.md`, `docs/research/data-1.60.1.70170-r4.md`.
- Modifiés : `forever/pipeline/decode.py` (paramètre `hotfixes`), `forever/pipeline/fetch.py` (`--dbd`),
  `forever/pipeline/hotfixes.py`, `forever/pipeline/value_diff.py`, `forever/pipeline/diff.py`,
  `forever/origins.py` (métadonnée `hotfix`), `forever/watch.py`, `forever/hooks.py`, `forever/profile.py`,
  `forever/cli.py`, `forever/mcp_server.py` (profil), `scripts/extract_class_fixtures.py`,
  `tests/fixtures/hotfix/Hotfix.log` et `README.md`, `tests/unit/test_hotfixes.py`, `tests/unit/test_watch.py`,
  `tests/unit/test_profile.py`, `tests/unit/test_diff.py`, `tests/unit/test_registry.py` (comptes),
  `plugin/skills/*/SKILL.md`, `plugin/.claude-plugin/plugin.json`, `docs/MECHANICS_REGISTRY.yaml`, documentation
  du bloc G.
- Données (bloc G, après accord seulement) : `forever/data/1.60.1.70170/` révision 4 (`classes.json` et les fichiers
  décodés touchés, `sources.json`, `revisions.json`, `manifest.json`).

## Interfaces

```python
# forever/pipeline/dbcache.py
DBCACHE_PATH = ("Cache", "ADB", "{locale}", "DBCache.bin")
class Status(IntEnum): VALID = 1; DELETE = 2; INVALID = 3; NOTPUBLIC = 4
class Entry(NamedTuple):
    region_id: int; push_id: int; unique_id: int; table_hash: int; rec_id: int; status: int; data: bytes; offset: int
class DBCache(NamedTuple):
    format: int; build: int; entries: list[Entry]; sha256: str; size: int
def table_hash(name: str) -> int                      # SStrHash, insensible à la casse
def parse_dbcache(raw: bytes) -> DBCache              # DataSchemaError : signature, format != 9, désalignement
def read_dbcache(path: Path) -> DBCache
def table_names(names: Iterable[str]) -> dict[int, str]
def effective(entries: Sequence[Entry], names: Mapping[int, str]) -> Resolved
    # Resolved : applicable[(table, rec_id)] -> Entry ; listed : invalid, notpublic, dbreply, unknown_hash
def crosscheck(entries, names, log_lines: Sequence[HotfixLine]) -> CrossCheck  # matched, only_log, only_cache

# forever/pipeline/dbd.py
class Field(NamedTuple):
    name: str; kind: str; size: int | None; signed: bool; array: int | None; inline: bool; is_id: bool; relation: bool
class Layout(NamedTuple):
    table: str; build_range: str; fields: tuple[Field, ...]
class LayoutCheck(NamedTuple):
    table: str; ok: bool; reason: str; compared: int; equal_ratio: float | None; references_ok: bool | None
def parse_dbd(text: str) -> Definition
def layout_for(definition: Definition, build: str) -> Layout | None
def decode_record(layout: Layout, data: bytes, rec_id: int) -> dict[str, Value]   # noms des CSV de wago.tools
def validate_layout(layout, entries, csv_header, csv_rows, related_ids) -> LayoutCheck

# forever/pipeline/hotfix_overlay.py
class Applied(NamedTuple):
    table: str; rec_id: int; status: str; push_id: int; seen_at: str | None; before: Row | None; after: Row | None
class Overlay(NamedTuple):
    tables: dict[str, list[Row]]; applied: list[Applied]; listed: dict[str, Any]; checks: list[LayoutCheck]
def apply_hotfixes(tables: Mapping[str, Sequence[Row]], cache: DBCache, layouts: Mapping[str, Layout],
                   journal: Sequence[Mapping[str, Any]], build: str) -> Overlay   # HotfixBuildMismatch si build ≠
```

CLI : `forever fetch <version> --dbd` ; `forever decode <version> --hotfixes [--dbcache PATH]` ; `forever hotfixes
[--values] [--dbcache PATH]` ; `forever diff a b` (valeurs des fichiers des classes) ; `forever profile set
--game-locale <xxYY>`. MCP : `forever_player_profile` rend `game_locale` ; aucun nouvel outil.

## Tests attendus (valeurs à confirmer au bloc B, étape 4, avant verrouillage)

Bloc A (`test_dbcache.py`, `test_hotfixes.py`) :
- `table_hash("TraitNode") == 0xE1432D63`, `table_hash("traitnode")` identique, `table_hash("ItemSparse") ==
  0x919BE54E`.
- Fixture : format 9, build 70170 ; nombre d'entrées égal à celui écrit par le script d'extraction (README) ; un
  octet de signature altéré → `DataSchemaError` ; un fichier tronqué → `DataSchemaError` (pas de lecture partielle
  silencieuse).
- Statuts : `TraitNode` 105928 `VALID`, 105929 `DELETE` (taille 0) ; `SpellPower` 315008 `INVALID` ;
  `SpellClassOptions` 73078 `NOTPUBLIC` ; `Spell` 15147 (deux copies, poussée −1) dans `dbreply`, **jamais** dans
  `applicable`.
- Deux entrées synthétiques du même enregistrement : la poussée la plus haute gagne.
- Hachage inconnu : listé avec son hachage et son compte, absent de `applicable`.
- `crosscheck` sur la fixture : comptes identiques par table et par statut avec l'extrait de `Hotfix.log` ; une
  ligne retirée de l'extrait apparaît dans `only_cache`.
- `forever hotfixes --json` : bloc `dbcache` présent, aucune mention « valeurs non lues », provenance complète ;
  aucune sortie ne contient « TactKey ».

Bloc B (`test_dbd.py`, `test_fetch.py`) :
- `parse_dbd` sur la fixture : colonnes, blocs, `$id$`, `$noninline$`, `$relation$`, tailles, tableaux.
- `layout_for(<TraitNode>, "1.60.1.70170")` non nul ; `layout_for(<…>, "9.9.9.1")` → `None`.
- `decode_record` : `TraitNode` 105928 → `PosX` 5620, `PosY` 5130, `TraitTreeID` 1117 ; `TraitDefinition` 135484 →
  `SpellID` 1323963 ; `TraitNodeEntry` 141191 → `TraitDefinitionID` 145863, `MaxRanks` 2 ; `TraitEdge` 136735 →
  105931 → 113569, `Type` 2 ; `CurvePoint` 334737 → `CurveID` 111755, `Pos_0` 1.0, `Pos_1` 20.0 ; `SpellName` 1680
  → `Name_lang` « Whirlwind » ; une table à identifiant non intégré (`SpellLevels` ou `SpellMisc`) décodée avec son
  `ID` = `rec_id` et sa relation `SpellID` correcte.
- `validate_layout` : vraie disposition → `ok` ; disposition altérée (deux champs inversés, une taille changée) →
  `ok` faux avec la raison ; table sans ligne comparable (`TraitNodeEntry`) validée par les références (4').
- `forever fetch --dbd` : par `Deps.http_get` simulé (aucun réseau) : commit épinglé, sha256 écrits dans `dbd.json`,
  second appel sans téléchargement ; réponse qui n'est pas un `.dbd` → refus.

Bloc C (`test_hotfix_overlay.py`) :
- Après superposition sur la fixture : `TraitNode` 105928 `PosX` 5620 ; 105929, 105936, 105973 absents ; 113569 et
  113570 ajoutés ; `TraitEdge` 124811 absente, 136735 présente ; `TraitDefinitionEffectPoints` 25094 `CurveID`
  111755 ; `TraitDefinitionEffectPoints` 25179 (`DELETE` d'une ligne absente) listée, aucune erreur.
- `INVALID`, `NOTPUBLIC`, `DBReply` : valeurs du build gardées.
- Garde de build : `DBCache.bin` de build 70124 appliqué à 1.60.1.70170 → `HotfixBuildMismatch`.
- `decode_version` sur la fixture avec correctifs : `classes.json` Warrior contient les talents nommés Lingering
  Rage, Furious Precision et Gore Drinker (noms venus de `SpellName` du correctif), le nœud 113569 en rangée 6 avec 2
  rangs, aucun nœud Guerrier dans `unresolved_nodes` ; chaque talent touché porte `hotfix.pushes == [112347]` et
  `first_logged_at` « 2026-10-02T08:00:23… » (extrait de `Hotfix.log`) ; `sources.json` `hotfixes` : build 70170,
  sha256 de la fixture, `max_push` 112347 (ou la plus haute de la fixture), commit de WoWDBDefs.
- Sans `--hotfixes` : candidate identique à celle d'aujourd'hui (non-régression).
- Mode seed : octets des fichiers `_seed_*` identiques avant et après ; tests de parité inchangés.
- `forever origins check` vert sur la candidate (champ `hotfix` en métadonnée).

Bloc D (`test_hotfix_values.py`, `test_diff.py`) :
- `forever diff <sans correctif> <avec correctif>` (fixture) : ligne de valeur pour la rangée ou la colonne d'un
  talent déplacé, ligne d'ajout pour le talent du nœud 113569, ligne de retrait pour le talent du nœud 105929, chacune
  avec « correctif 112347 ».
- `forever hotfixes --values --json` : `TraitNode` 105928 `PosX` 6220 → 5620 ; `TraitDefinition` 135484 `SpellID`
  1310236 → 1323963 ; `TraitDefinitionEffectPoints` 25099 marquée « identique au build ».
- `entity_assumptions` : « valeur appliquée » quand la poussée est dans `sources.json`, « non appliquée » sinon.

Bloc E (`test_watch.py`) :
- État de veille sans `DBCache.bin` connu + fixture → élément `hotfixes_dbcache` avec le nombre de correctifs non
  appliqués et les actions ; second passage sans changement de fichier → aucune analyse (empreinte), aucun élément ;
  `sources.json` qui contient toutes les poussées → zéro ; `DBCache.bin` d'un autre build → « non applicables ».
- Ligne de démarrage : compacte, présente seulement quand le compte est non nul.

Bloc F (`test_profile.py`, `test_plugin_structure.py`, `test_mcp.py`) :
- `game_locale` lu dans la fixture `Config.wtf` (source `client`) ; `profile set --game-locale enUS` → source
  `joueur`, prioritaire ; valeur invalide (`english`) refusée ; `forever_player_profile` le rend.
- Chaque `SKILL.md` du plugin contient la règle « noms du client » ; aucun chiffre de jeu ajouté
  (`check_game_numbers`) ; version du plugin 0.7.0.

Registre (`test_registry.py`, comptes écrits dès le commit « tests » du bloc C) : J1 `modelise` → `teste` (sources
`DBCache.bin`, WoWDBDefs ; tests des blocs A à D) : couverture **54/129**, total 129 inchangé, sortie de `main` à
jour ; G3 : source et note (arbres corrigés par le serveur appliqués en mode forever), sans changement de statut.

## Hors périmètre

- Correctifs obtenus par le réseau (wago.tools en propose) : seul le `DBCache.bin` du poste fait foi.
- Tables que le pipeline ne décode pas : `TraitNodeGroupXTraitNode` (décodée et listée si sa disposition est
  validée, non appliquée : le pipeline ne la lit pas), `Curve` (pas de CSV ; `CurvePoint` suffit au décodage),
  `GlobalStrings`, hachages inconnus, `TactKey` (jamais lue) ; objets au-delà des bijoux PvP (T10, DON3).
- `DBCache.bin` frFR et noms français des nouveaux talents (réponse 2).
- Lecteur durable de Talents Forever, format des codes v5 et légalité de ses builds populaires (FA1).
- Note d'impact par personnage, baisse automatique de certitude, `forever_diff_versions` (T08).
- Moteur du Guerrier (GU1) : seuls les arbres et les sorts décodés changent.

## Risques

- **WoWDBDefs sans bloc pour 1.60.1.70170** (build de Forever peut-être absent du dépôt) : la table est listée sans
  disposition, rien n'est appliqué ; si c'est le cas des tables `Trait*`, s'arrêter et proposer à l'utilisateur la
  source suivante (DB2 bruts par wago.tools) plutôt que d'emprunter un bloc voisin.
- **CSV de wago.tools déjà corrigés** en partie (25099 identique) : « avant » serait faux ; contrôle au bloc B,
  étape 5.
- **Tables à identifiant non intégré** (`Spell*`) : ordre des octets propre au build ; la validation (4) sur les
  lignes existantes l'attrape.
- **Arbres du Guerrier au-delà de la grille** ou positions observées (`observed_positions`, `community_positions`)
  devenues fausses après la refonte : nœuds dans `unresolved_nodes` ou contradictions de `tree_checks` ; listés au
  contrôle du Guerrier, corrigés seulement avec accord.
- **Comptes de la fixture** liés au script d'extraction : les tests lisent les comptes attendus dans le README de la
  fixture, écrit par le script, pas en dur dans deux endroits.
- `Hotfix.log` réécrit à chaque démarrage : sans `hotfixes.json`, la date vue est inconnue (affichée telle quelle).
- Fichier de 6 Mo à chaque démarrage de session : court-circuit par empreinte (taille, date) avant analyse.
- Licence de WoWDBDefs inconnue à ce jour : vérifiée au bloc B avant de committer un `.dbd`.

## Angles morts attendus (à chiffrer en fin de tranche)

- Effet des sorts nouveaux ou corrigés du Guerrier (dégâts, rage) : non calculé avant GU1 ; seuls arbres et fiches.
- `INVALID` : valeur du build gardée (DON2 répondue en partie : aucune valeur portée, sens de l'invalidation non
  établi).
- Correctifs des tables non décodées (`SpellScript`, `SpellCastingRequirements`, `SpellEquippedItems`…) : listés
  par `Hotfix.log`, sans effet sur nos données ; effet sur les sorts touchés non chiffré.
- `name_fr` des nouveaux talents absent (affichage seulement).

## Questions ouvertes à ajouter

- DON8 — Que veut dire le premier champ des entrées de `DBCache.bin` (70 sur tout le fichier : région ?) ?
  Priorité basse.
- DON9 — Une réponse `DBReply` « absent » peut-elle viser un enregistrement présent dans les fichiers du build ?
  Test : `Spell` 15147 et les `ItemSparse` concernés recoupés avec les CSV. Priorité basse.

## Critères de fin

- La fixture `DBCache.bin` (extraite du fichier de l'utilisateur, sans `TactKey`) est décodée sans réseau : statuts,
  poussées, tables, recoupement avec `Hotfix.log`.
- Les dispositions de WoWDBDefs pour 1.60.1.70170 sont validées contre les CSV pour chaque table appliquée ; une
  disposition fausse est refusée (test).
- En mode forever, une valeur corrigée remplace celle des tables (et une ligne nouvelle s'ajoute, une ligne
  supprimée disparaît) avec sa provenance (`hotfix` sur l'entité, bloc `hotfixes` de `sources.json`, origine
  « client ») ; le mode seed est inchangé ; garde de build testée.
- `forever diff` et `forever hotfixes --values` montrent chaque valeur corrigée, avant et après.
- Contrôle du Guerrier et rapport Talents Forever écrits ; rejeu de T05 montré ; révision 4 installée **après
  accord** seulement.
- `forever watch` et la ligne de démarrage signalent les correctifs non appliqués.
- `game_locale` au profil, règle « noms du client » dans les skills, plugin 0.7.0.
- Registre (J1, G3), `docs/DATA_SOURCES.md`, `docs/OPEN_QUESTIONS.md`, `docs/USAGE.md`, `docs/DECISIONS.md`,
  `docs/ROADMAP.md` à jour ; `uv run tasks.py verify` vert ; CI verte sous Ubuntu et Windows avant la fusion.

## Validation

Plan à valider par l'utilisateur avant l'exécution (nouvelle session, `/tranche T08c`).
