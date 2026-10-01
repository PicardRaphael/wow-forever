# T08b — Tout ce qui doit suivre les mises à jour : plan

Tranche longue, sur la version du jeu installée la plus récente (**1.60.1.70124**, révision 3 à ce jour). Demande de
l'utilisateur du 2026-10-01, en neuf points, d'après l'audit `docs/research/audit-mises-a-jour.md` ; section T08b de
`docs/ROADMAP.md` ; décisions 13, 19, 89, 98, 123, 124, 127, 134, 135, 146, 147.

But : qu'une mise à jour du jeu, un correctif du serveur, une note officielle ou une nouvelle version d'un addon de
données ne passe plus inaperçue, et qu'aucune valeur qui dépend de la version ne reste écrite à la main sans le dire.
Aucune valeur de jeu n'apparaît dans ce plan : les clés sont nommées, les tests lisent leurs valeurs attendues dans
`forever/data/` ou `tests/fixtures/`.

## Questions décisives (réponse attendue avant l'exécution)

- **D1 — Veille des notes officielles : ce que disent `robots.txt` et les conditions, et ce qu'on en fait.** Relevé
  du 2026-10-01 :
  - `https://us.forums.blizzard.com/robots.txt` (`User-agent: *`) : les sujets et catégories en JSON
    (`/en/wow/t/<id>.json`, `/en/wow/c/<slug>/<id>.json`) **ne sont pas interdits** ; sont interdits les flux
    `.rss` des sujets et des catégories (`/en/wow/t/*/*.rss`, `/en/wow/c/*.rss`), `/en/wow/search`, `/en/wow/g`
    (traqueur des messages bleus compris), `/en/wow/my`, `/en/wow/session`, `/en/wow/user-api-key`, toute adresse
    portant `api_key`. **Aucun `Crawl-delay`.**
  - Conditions du forum (`/en/wow/tos`) : **gabarit Discourse jamais rempli** (les noms de l'exploitant sont restés
    `company_short_name`, `company_domain`) ; aucune clause sur l'accès automatisé ; les contributions des
    utilisateurs sont sous licence **CC BY-NC-SA 3.0** (attribution, pas d'usage commercial, partage identique).
  - Contrat de licence de Blizzard (EULA, mis à jour le 2024-03-21), § 1.C.vi : interdit tout procédé non autorisé
    qui « intercepts, collects, reads, or "mines" information generated or stored by the **Platform** » ; la
    définition de la Platform (application Battle.net, service, jeux, applications mobiles) **n'inclut pas** les
    sites ni les forums.
  - **Conditions des API de Blizzard** (Blizzard Developer API Terms of Use, 2019-10-01), § 2.16 : « Except as
    permitted through authorized use of the Blizzard Developer APIs, You will not perform any data-mining, scraping,
    crawling, or use any processes that sends automated queries to Blizzard or any Blizzard game, service, **or
    website** ». Elles lient quiconque a ouvert un compte développeur et obtenu une clé d'API, ce que **EC1 fera**.
    Aujourd'hui, rien de ce que tu as accepté n'interdit la lecture ; après EC1, une lecture quotidienne automatisée
    du forum entrerait en conflit direct avec ce paragraphe.
  - Options : (a) lecture **quotidienne** automatique en CI, deux catégories, une requête par catégorie puis une par
    sujet nouveau ou révisé, identifiant de client explicite, `robots.txt` relu à chaque passage (arrêt si l'adresse
    devient interdite), décision réexaminée au plan d'EC1 avant d'accepter les conditions des API ; (b) même code,
    mais **lancé à la main seulement** (`forever notes` et `workflow_dispatch`, pas de `schedule`) ; (c) reporter.
  - **Proposition : (a)**, avec le conflit d'EC1 écrit dans `docs/DECISIONS.md` pour qu'il soit retrouvé au moment
    d'accepter les conditions des API ; si tu préfères la prudence, (b) ne change que le déclencheur du workflow.
- **D2 — Valeurs qui dépendent de la version : d'où elles viennent.** Deux faits d'abord :
  - **Deux plafonds distincts**, pas un : `decode_rules.levels.level_cap` est le **niveau maximal du jeu** (borne des
    rangs de sort quand `SpellLevels.MaxLevel` vaut 0, et bornes de niveau des outils) ; `mechanics.build.beta_level_cap`
    est le **plafond temporaire de la bêta** (décision 89). Ta demande les confond (« 20 dans mechanics.json et
    decode_rules.json ») : seul le second vaut le plafond de bêta.
  - **Aucune table du client lue pendant le plan ne porte le plafond de bêta** (`Cfg_GameRules`, `GameParameter`,
    `ContentTuning`, `NumTalentsAtLevel`, `LevelExperience` qui va bien au-delà du niveau maximal, `PlayerExpectedStat`
    idem). Je ne devine pas une table.
  - **Proposition** :
    - plafond de bêta = **fait d'installation** : `forever install` (nouvelle version ou révision) le reçoit par
      `--beta-level-cap <niveau> --beta-level-cap-source <adresse de la note | observation>` et l'écrit dans
      `revisions.json` (révision courante) et dans un nouveau bloc `game_state` de `meta.json` avec sa source, sa date
      et sa certitude (`probable` pour une note officielle, `certain` pour une observation en jeu : niveau atteint où
      l'XP cesse, relevé par ForeverLogger) ; sans option, la valeur précédente est **reportée avec la mention
      « reportée de la révision N »** et la sortie de `forever install` le dit ; `GameData` lit ce bloc à la place
      de `mechanics.build.beta_level_cap`, qui disparaît de `mechanics.json` ; la veille des notes (bloc F) signale
      toute note qui parle de « level cap » ;
    - **valeur à installer maintenant** : la note du 2026-10-01 annonce un plafond relevé avec le build suivant
      sans donner le niveau dans le relevé de l'audit ; je garde la valeur actuelle tant que le nouveau build n'est
      pas installé et que les notes détaillées ne sont pas parues, sauf si tu me donnes la valeur et sa source ;
    - niveau maximal du jeu : aucune table ne le porte non plus ; il reste dans `decode_rules.json`, origine
      « écrite à la main », raison « niveau maximal annoncé de Forever », certitude `probable` (au lieu de `certain`
      aujourd'hui, par le fichier) ;
    - **copies du seed lues par le moteur en mode forever** alors que le client les porte déjà (`classes.json`) :
      champs `utility` de `spells.json` (niveaux, recharges, portées, coûts d'Evocation, Counterspell, Ice Barrier…)
      et `mana_pct_base` (Arcane Blast, Blink). **Proposition** : en mode forever, le moteur lit les valeurs décodées
      de `classes.json` quand elles existent (la valeur du client l'emporte, hiérarchie des sources), le mode seed
      garde les copies ; Ice Barrier rang 1 change donc de niveau d'apprentissage en mode forever (question ouverte
      ajoutée ce jour) ; l'effet sur les builds est montré au rejeu (bloc I).
- **D3 — Tests des tranches passées qui épinglent des estimations en mode forever, et certitudes abaissées.**
  `forever/engine/character.py` n'a pas de paramètre `rules` et `mechanics.json` est le même dans les deux modes :
  les tests ci-dessous épinglent, sous la fixture `game_data` (mode forever), des valeurs calculées par `fm.py` du
  seed. Dès que le moteur lira les ratios décodés en mode forever, ils échoueront.
  - Fichiers concernés (liste exacte arrêtée en phase rouge du bloc A, présentée avec les demandes de correction) :
    `tests/unit/test_engine_character.py`, `tests/unit/test_engine_arcane_blast.py`, les cas `game_data` de
    `tests/unit/test_engine_values.py` et `tests/unit/test_engine_mechanics.py` qui passent par l'Intelligence par
    point de critique, la mana de base, l'XP par niveau ou l'armure des monstres, et `tests/unit/test_build_data.py`
    (plafond de bêta épinglé, D2).
  - **Proposition** : ces cas passent sur la fixture `seed_game_data` **sans changer une seule valeur attendue**
    (ce sont des valeurs du seed) ; de nouveaux tests du mode forever lisent leurs valeurs dans les fixtures
    décodées ; `tests/parity/test_fm_parity.py` ne bouge pas. Accord demandé ici pour ne pas bloquer en phase verte.
  - **Certitudes abaissées** (point 2) : `leveling.combat_rules.crit_mult_spell` et `dot_can_crit` ne sont dans
    aucune table (règle du serveur) : `probable` au mieux, et seulement si les journaux les recoupent (rapports de
    critique et tics critiques, `forever logs measure`), sinon `suppose` (règle Classic) ; `mechanics.leveling.ignite`
    (aura, durée, période) et `mechanics.crit.winters_chill_per_stack` **sont décodables** (lignes de l'aura dans
    `SpellEffect`, `SpellMisc`, `SpellDuration`, déjà en cache) : `certain` par décodage ; `mechanics.talents.first_level`
    décodable par `NumTalentsAtLevel`, `points_per_tier` par `TraitCond` si la colonne de points dépensés existe,
    sinon `probable`. Les paramètres de l'outil marqués `certain` (`build.confidence`, `build.stability_seeds`,
    `build.presets`, `build.contexts`, `build.concord_threshold`) ne sont pas des valeurs de jeu : origine
    « paramètre de l'outil » (D4), certitude sans objet.
- **D4 — Forme de l'origine de chaque valeur (point 8).** **Proposition** :
  - un fichier par version, `forever/data/<version>/origins.json`, hérité d'une version à l'autre et complété par
    le décodage, plutôt qu'un champ dans chaque fichier (les copies du seed et `spells.json` gardent leur schéma,
    les empreintes de parité ne bougent pas) ;
  - chaque règle porte `file`, `paths` (chemins JSON), `origin`, `source`, `certainty`, et `reason` obligatoire
    pour une valeur écrite à la main ; six origines : les quatre que tu demandes, **client** (décodé d'une table,
    table et colonne nommées), **journal** (mesuré dans mes journaux ou relevé en jeu par ForeverLogger ou par
    toi), **addon** (addon de données, nom et version), **manuel** (écrite à la main, raison et source), plus deux
    pour ne rien mélanger : **copie_figee** (copies du seed `_seed_*.json`, `_source_gunba_mage_tree.json`, lues
    seulement en mode seed, règle au niveau du fichier) et **parametre** (réglage de l'outil, pas une valeur de
    jeu : graines, seuils, préréglages) ;
  - motifs (`*`) permis seulement pour client, journal, addon et copie_figee ; une valeur **manuel** est nommée
    par son chemin exact, regroupée avec d'autres sous une même raison si besoin : une clé nouvelle n'est donc jamais
    couverte en silence ;
  - contrôle : toute feuille (nombre, booléen, chaîne de valeur) de tout fichier de données doit être couverte par
    une règle ; une feuille **manuel** sans raison, ou à certitude `certain` sans preuve d'observation, échoue ; la
    certitude d'une entrée de `mechanics.json` ne dépasse pas celle de sa règle d'origine.
- **D5 — Liste des accès réseau du bloc A** (accord demandé **à chaque accès**, au moment de l'exécution ; rien
  d'autre ; une table absente n'entraîne aucun appel de remplacement) :
  1. `forever fetch --version 1.60.1.70124` des tables DB2 nouvelles, par l'adresse actuelle : `PlayerExpectedStat`,
     `LevelExperience`, `Exhaustion`, `ExpectedStat`, `GlobalCurve`, `NumTalentsAtLevel`, et `TraitCond` (point
     `points_per_tier`) ; les tables déjà en cache ne sont pas retéléchargées.
  2. La liste des fichiers GameTables de wago.tools (`https://wago.tools/files?search=gametables`), **une** requête,
     pour lire les identifiants de fichier. Les pages gardées par l'audit dans le dossier temporaire ne servent pas :
     leur extraction rend des identifiants incohérents.
  3. Chaque GameTable par `https://wago.tools/api/casc/<identifiant>?version=1.60.1.70124`, une requête par
     fichier : `xp` (colonne de l'XP par monstre), `hppersta`, `basemp` (recoupements), puis `armormitigationbylvl`
     et `npctotalhp` (questions ouvertes sur l'armure et les PV des monstres).
  4. Si D1 = (a) ou (b) : une lecture des catégories suivies (349, 347) pour vérifier la forme réelle du JSON
     avant d'écrire les fixtures ; les fixtures sont **synthétiques** (structure réelle, texte inventé) pour ne
     recopier aucun contenu sous licence CC BY-NC-SA.
  Aucun CSV du dossier temporaire de l'audit ne devient une fixture : les fixtures sont extraites du cache rempli par
  `forever fetch`, qui garde l'empreinte et la date de chaque table.

## Contexte relevé pendant le plan (lecture locale seulement, plus le relevé de D1)

| Fait | Où |
| --- | --- |
| `spell_scaling.json` n'est jamais installé par une **révision** : `forever install` sans `--new-version` n'écrit que talents, sorts, changements confirmés, sources, révisions et fichiers des classes | `forever/pipeline/install.py:617-622` |
| « Fichier remplacé » vient de l'installation (empreinte, fichiers des classes seulement), pas de `forever diff`, qui ne compare que la présence des fichiers, les talents et les rangs des sorts | `install.py:41-52, 282-333`, `diff.py:90-125` |
| `decode_rules.json` est **hérité** (recopié) à chaque nouvelle version : le plafond qu'il porte doit être édité avant de décoder | `decode.py:29-39` (`INHERITED_FILES`) |
| `character()` n'a pas de paramètre `rules` ; en mode seed, seuls `spells.json`, `talents.json` et les raciaux changent de source | `forever/engine/character.py:10-67`, `forever/gamedata.py:917-961` |
| `mechanics.json` : 52 entrées (39 `suppose`, 5 `probable`, 8 `certain`, dont 5 paramètres de l'outil) ; provenance par entrée. `leveling.json` : provenance par section, sauf 5 clés de `combat_rules` dans `sources.json` ; environ 270 feuilles numériques à eux deux | `mechanics.json`, `leveling.json`, `sources.json` |
| Les champs non-rang de `spells.json` (`utility`, `slow`, `range`, `mana_pct_base`…) sont des copies du seed sans certitude propre, alors que `classes.json` porte des valeurs décodées pour plusieurs d'entre eux | audit, section 1.4 ; `gamedata.py:460-485` |
| `Logs/Hotfix.log` (9,2 Mo, environ 114 000 lignes) est **réécrit à chaque démarrage du client** (une seule ligne `---- Startup ----`) ; forme d'une ligne : date, heure, identifiant de poussée, `Table <nom> RecID <n> VALIDATION_RESULT_{VALID,INVALID,DELETE}`, plus des lignes `DBReply` et `TactKey` | `C:\Program Files\World of Warcraft\_classic_beta_\Logs\Hotfix.log` |
| Ce matin, les correctifs touchent des tables que le projet décode : `CurvePoint`, `Curve` (rangs des talents), `SpellMisc`, `SpellName`, `CreatureDifficulty`, `ItemSparse` et `Item` (bijoux PvP) | même fichier |
| `DBCache.bin` est présent dans `Cache/ADB/enUS/` (valeurs des correctifs, décodage en T08) | dossier du client |
| La ligne de démarrage de session (`forever hook session-start`, plugin) est hors ligne, budget de 10 s | `plugin/hooks/hooks.json`, `forever/hooks.py`, `forever/status.py:32-67` |
| `forever addons status` n'existe pas ; lecteurs existants : Questie (`questie.py`), Auctionator (`auctionator.py`), ForeverLogger (`addon_sv.py`) | code |
| Le test de frontière réseau contrôle les **modules** hors de `forever/pipeline/` ; la liste des commandes réseau n'existe qu'en prose (`CLAUDE.md`) | `tests/unit/test_network_boundary.py` |
| `verify` = lint, typage, tests, registre, chiffres du plugin ; une étape s'ajoute dans `verify()`, `COMMANDS` et la docstring | `tasks.py:3-11, 64-93` |
| Passages de rejeu en cache : `PV1`, `T08a` (`~/.cache/forever/builds/`) ; `scripts/replay_builds.py run|table|compare` ; la règle reste celle par défaut (forever) | `scripts/replay_builds.py` |
| `tests/golden/` n'existe pas | — |
| Le mode auto n'écrit pas dans `.github/workflows/` : workflow en patch (précédent `tasks/T08a-build-watch.patch`) | Pièges du skill |

## Choix d'architecture (sans question)

- **Un fichier décodé de plus**, `character_scaling.json` (nom définitif au bloc A) : par classe et par niveau, mana
  de base, critique des sorts par Intelligence, critique par Agilité, PV par Endurance (colonne dont le sens est
  probable) ; XP pour passer chaque niveau ; paramètres du repos (`Exhaustion`) ; constante d'armure par niveau ;
  courbes de régénération de PV par l'Esprit (`GlobalCurve` types 27 et 28 et leurs `CurvePoint`) ; recoupements
  par les GameTables, écart signalé, jamais tranché en silence. Il entre dans `DECODED_FILES`, `sources.json` et les
  comptes des tests de données dès le commit « tests ».
- **Le moteur choisit par le mode** : `CharacterModel` reçoit ses ratios de `GameData`, qui les prend dans le fichier
  décodé en mode forever et dans `mechanics.character` en mode seed ; même règle pour `xp_to_next` (`leveling.json`
  en seed) et la constante d'armure. Ce que le client ne porte pas (critique de base, mana par Intelligence,
  statistiques de base par race, régénération de mana par l'Esprit, PV de base) reste dans `mechanics.json` pour
  les deux modes, inchangé.
- **Décodé mais pas encore utilisé**, et dit tel quel : la régénération de PV par l'Esprit (la formule qui combine
  les deux courbes reste au serveur ; `rest_hp_regen_fraction` est gardée), les PV par Endurance (sans PV de base,
  le lien seul ne remplace pas `mechanics.character.hp`), l'XP de repos (modèle de leveling inchangé, T04d), la
  table de PV des créatures (question ouverte). Ils sont consultables (`forever lookup`) avec leur certitude.
- **L'installation d'une révision installe tous les fichiers décodés**, `spell_scaling.json` et le nouveau fichier
  compris, avec la liste des valeurs changées dans le rapport et dans `revisions.json` ; sans blocage (comme les
  fichiers des classes) : le diff des valeurs (bloc C) rend l'écart visible dans la PR de veille.
- **Toutes les données nouvelles entrent par une seule révision 4 de 1.60.1.70124**, installée au bloc I, après
  accord et après le rejeu : les blocs A et B livrent le code et les tests sur fixtures ; sans le fichier décodé, le
  mode forever garde son comportement actuel (hypothèse affichée : « ratios estimés »).
- **Correctifs du serveur** : `Hotfix.log` étant réécrit à chaque démarrage, un journal en ajout seul
  `<cache>/hotfixes.json` (comme `client_builds.json`) garde chaque ligne vue (poussée, table, enregistrement,
  résultat, première et dernière date vues, build du client à ce moment) ; lecture limitée aux lignes `VALID` et
  `DELETE` des tables que le projet décode ou lit (liste tirée de `decode_rules.json`, jamais écrite à part), plages
  d'enregistrements regroupées ; « depuis la dernière installation » = vues après la date de la révision installée.
  Le sens de `VALIDATION_RESULT_INVALID` n'est pas établi : compté à part, question ouverte.
- **Entités touchées par un correctif** : les enregistrements sont reliés aux entités du projet par les CSV du
  cache (`CurvePoint` → courbe → talent ; `SpellMisc`, `SpellName` → sort ; `Item*` → bijou PvP) ; `forever lookup`
  ajoute à la provenance d'une entité touchée l'hypothèse « corrigée par le serveur le <date>, valeur du correctif
  non lue (T08) ». Aucune certitude n'est abaissée automatiquement (décision 19 reste en T08).
- **`forever addons status`** : pour chaque addon de données installé (Questie, AtlasLoot, ForeverDungeonJournal,
  GearQuestForever, Auctionator, et ForeverLogger pour sa version), version du `.toc`, empreinte de chaque fichier
  de données (court-circuit par taille et date avant de hacher), relevé précédent dans `<cache>/addons/state.json`,
  statut `nouveau`, `inchangé` ou `changé`. « Relit et liste ce qui a changé » n'est **concret que pour les addons
  qui ont un lecteur** : Questie (PV et niveaux des PNJ de `monsters.json`, niveaux des zones, nombre de quêtes et
  XP des quêtes, en différence avec le relevé précédent, agrégats gardés dans le cache) ; Auctionator et
  ForeverLogger (format relu sans erreur, nombre d'entrées) ; AtlasLoot, ForeverDungeonJournal, GearQuestForever :
  fichiers ajoutés, retirés ou modifiés, avec « lecteur en DJ1 ». Les agrégats du dépôt qui en dépendent sont nommés
  (`monsters.json` `questie_correction`) et l'action proposée est `forever measures refresh` ; rien n'est réécrit.
- **Veille locale** : `forever watch` (hors ligne) assemble les détecteurs : build du client (`.build.info`,
  `client_builds.json`), `forever addons status`, nouveaux correctifs (`hotfixes.json`), nouveaux journaux de combat
  et nouvelles sauvegardes (ForeverLogger, Questie, Auctionator) depuis le dernier passage ; il rend un résumé et les
  **actions proposées** (commande exacte, réseau ou non) sans rien lancer. La ligne de démarrage de session y ajoute
  une ligne compacte quand quelque chose a changé ; la tâche planifiée Windows est un script PowerShell que **tu**
  lances (`scripts/install_watch_task.ps1`, `-WhatIf` et `-Remove`), qui exécute `forever watch --report` chaque jour
  et écrit le résumé dans le cache ; la session suivante l'affiche.
- **Notes officielles** : `forever/pipeline/notes.py` (accès par `Deps.http_get`, comme `builds`), commande
  `forever notes [--since <date>] [--json]`. L'état (sujet, `updated_at`, `version` du premier message) vit dans le
  **corps des issues** (marqueur caché), pour que la CI n'ait besoin d'aucun stockage ; en local, dans le cache.
  Entités nommées : noms anglais des sorts et talents de `spells.json`, `talents.json` et `classes.json`, noms des
  classes, et un dictionnaire de mots-clés reliés aux entrées du registre (« Ignite » → A18, « diminishing returns »
  → K1, « level cap » → plafond de bêta, « experience » → I6…), sans aucun chiffre. Le sujet « Known Issues » est
  repéré : ses éléments sont listés comme bugs reconnus, à ne jamais modéliser.

## Blocs et étapes

Un cycle rouge → vert par bloc (commit « T08b: tests (bloc X) », puis « T08b: bloc X vert ») ; `tasks/.rouge` et
`tasks/.tests-verrouilles` réécrits à chaque bloc. Ordre choisi par dépendance, pas dans l'ordre de ta liste :
l'origine des valeurs d'abord (elle nomme ce que le bloc B doit décoder ou abaisser, et chaque bloc suivant y déclare
ses valeurs), le rejeu à la fin (point d'arrêt avant le commit des données). Si le contexte se remplit, arrêt après
un bloc vert committé.

### Bloc H — Origine de chaque valeur et contrôle de `verify` (point 8)

1. `origins.json` dans `forever/data/1.60.1.70124/` (et `1.60.1.70009/`, pour que le contrôle couvre les deux
   versions installées), au format de D4 ; `INHERITED_FILES` (recopié et complété à chaque nouvelle version),
   `sources.json`, manifeste.
2. `forever/origins.py` : parcours des feuilles de chaque fichier de données, règle la plus précise, erreurs typées
   (feuille non couverte, `manuel` sans raison, `manuel` à `certain` sans preuve, certitude d'entrée supérieure à
   celle de la règle, motif sur une valeur `manuel`).
3. `scripts/check_origins.py` et étape `origins` de `uv run tasks.py verify` (docstring, `COMMANDS`, CI inchangée :
   elle lance déjà `verify`).
4. `forever origins inventory [--json]` produit l'**inventaire complet des valeurs écrites à la main** (fichier,
   chemin, certitude, raison, source, entrée du registre) ; rendu committé dans
   `docs/research/valeurs-ecrites-a-la-main.md`, régénéré en fin de tranche (après les blocs A et B, qui en retirent).
5. Certitudes ramenées à la règle du projet (point 2, pour ce qui n'est ni décodé ni observé) : les écarts sont
   écrits dans la révision 4 (bloc I), pas avant.

### Bloc A — Ratios du personnage décodés du client (point 1)

1. Accès réseau 1 à 3 de D5, chacun après accord. Identifiants des GameTables dans `decode_rules.json`
   (`gametables : {nom : identifiant de fichier}`), adresse `api/casc` dans `forever/pipeline/fetch.py`
   (`forever fetch --gametables`), réponse vide = « absente du build », notée et jamais remplacée par une autre.
2. Fixtures : extraits des tables du cache dans `tests/fixtures/wago/1.60.1.70124/` (lignes du Mage, d'une classe
   sans mana et de deux autres classes ; niveaux de début, de milieu et de fin), GameTables réduites aux mêmes
   niveaux.
3. `decode` produit le fichier décodé (choix d'architecture) ; `verify` de la candidate contrôle sa forme (9 classes
   jouables, niveaux 1 au niveau maximal sans trou, mana nulle pour les classes sans mana) ; recoupement DB2 contre
   GameTables par valeur, écarts dans le rapport.
4. `GameData` et `CharacterModel` séparés par le mode (choix d'architecture) ; `xp_to_next` et la constante
   d'armure aussi.
5. Registre : A5 et B9 (terme décodé `certain`, le reste inchangé), G2 (lien Endurance → PV décodé, base toujours
   estimée), I6 (XP par niveau décodée), D7 (repos décodé, non modélisé), constante d'armure (`probable` : table lue
   par le serveur inconnue) ; questions ouvertes closes ou mises à jour (`int_per_crit`).

### Bloc B — Plus de valeur dépendante de la version écrite à la main (point 2)

1. Plafond de bêta comme fait d'installation (D2) : options de `forever install`, bloc `game_state` de `meta.json`,
   lecture par `GameData`, report signalé, retrait de `mechanics.build.beta_level_cap`.
2. Ignite (aura, durée, période) et Winter's Chill par cumul décodés des lignes de leur aura (`SpellEffect`,
   `SpellMisc`, `SpellDuration`) ; `talents.first_level` par `NumTalentsAtLevel` ; `points_per_tier` par `TraitCond`
   si possible. Chaque valeur décodée quitte `mechanics.json` pour le fichier décodé qui convient, ou y reste avec
   l'origine `client` si son schéma l'impose ; le mode seed garde ses copies.
3. Selon D2 : en mode forever, champs `utility` et `mana_pct_base` lus dans `classes.json` quand il les porte.
4. `crit_mult_spell`, `dot_can_crit` : mesure dans les journaux existants (rapports de critique, tics critiques) ;
   certitude fixée selon D3, preuve au registre si la mesure suffit (`tolerance.n_min`).
5. Registre : A18, A5 (multiplicateur), C1 ou l'entrée du plafond (I5), G3 (règles des points de talent).

### Bloc C — `forever diff` compare les valeurs de `spell_scaling.json` (point 3)

1. `compare_data` : par sort, rang et composant (`base_points`, `points_per_level`, `variance`,
   `bonus_coefficient`, `period_ms`, `ticks`, `max_level`), plus `level_cap`, `utility`, `auras`,
   `talent_cooldowns` ; même mécanique pour le fichier décodé du bloc A.
2. Rapport (`forever report`) et rapport d'installation : une ligne par valeur changée, plus de « fichier
   remplacé » pour ces fichiers.
3. Installation en révision de tous les fichiers décodés (choix d'architecture).

### Bloc E — Correctifs du serveur listés depuis `Hotfix.log` (point 5)

1. `forever/pipeline/hotfixes.py` : lecture sur disque (dossier `FOREVER_WOW_DIR`), journal `hotfixes.json` en ajout
   seul, filtre des tables, regroupement, relation aux entités (choix d'architecture).
2. `forever hotfixes [--since-install] [--json]` : tables et lignes corrigées, nouvelles depuis la dernière
   installation, entités touchées ; provenance.
3. Hypothèse « corrigée par le serveur » dans la provenance de `forever lookup` pour une entité touchée.
4. Fixture : extrait court du vrai journal (lignes des tables suivies et quelques autres, dates conservées), aucune
   valeur de jeu dedans ; question ouverte sur `VALIDATION_RESULT_INVALID`.

### Bloc D — `forever addons status` (point 4)

1. `forever/addons.py` : liste des addons et de leurs fichiers de données (motifs de chemins, jamais de valeur),
   relevé précédent dans le cache, statuts, différences des agrégats pour Questie.
2. `forever addons status [--json] [--save]` : sans `--save`, compare sans rien écrire ; avec, enregistre le relevé.
3. Fixtures : deux dossiers d'addons factices par addon (`.toc` et fichiers de données), dont un changé à chaîne de
   version identique (cas d'AtlasLoot, décision 124).
4. `docs/DATA_SOURCES.md` (suivi des versions) et `tasks/inventaire-addons.md` (empreintes de référence remplacées par
   le relevé de la commande).

### Bloc G — Veille locale sur le poste (point 7)

1. `forever/watch.py` et `forever watch [--report] [--json]` (choix d'architecture) ; état du dernier passage dans le
   cache ; budget de temps borné et mesuré en test (fichiers volumineux simulés, court-circuit par taille et date).
2. `forever hook session-start` : une ligne de plus quand quelque chose a changé (« client 1.60.1.x installé ; 2
   addons changés ; correctifs nouveaux ; 3 journaux à mesurer : `forever watch` pour le détail »), rien sinon ; jamais
   d'échec du hook.
3. `scripts/install_watch_task.ps1` (tâche planifiée Windows, lancée par toi) ; procédure dans `docs/USAGE.md`.
4. `docs/research/lecture-directe-client.md` : le secours sans wago.tools (lecture des archives CASC du client,
   identifiants de fichier, clés TACT, `DBCache.bin`), documenté pour plus tard, sans code.

### Bloc F — Veille des notes officielles (point 6, selon D1)

1. `forever/pipeline/notes.py` et `forever notes` (choix d'architecture) ; `robots.txt` relu à chaque passage, arrêt
   si une adresse suivie devient interdite ; une fois par jour au plus (horodatage du dernier passage).
2. Fixtures synthétiques dans `tests/fixtures/forum/` : catégorie, sujet nouveau, sujet révisé (`version` qui monte,
   `updated_at` plus récent), message non officiel ignoré, sujet « Known Issues », entités reconnues.
3. Workflow : nouvelle tâche de `build-watch.yml` (ou workflow `notes-watch.yml`) qui lance `forever notes --json`
   et ouvre ou met à jour une issue `veille-notes` par note nouvelle ou modifiée ; livré en patch
   `tasks/T08b-notes-watch.patch`, avec la commande `git apply` à lancer.
4. `CLAUDE.md` (liste des commandes réseau : `forever notes`), `docs/ARCHITECTURE.md`, `docs/DATA_SOURCES.md`
   (rang de la source : signal qui ne change jamais une valeur ; une règle du serveur sans autre source peut passer
   de `suppose` à `probable` par un texte officiel, la mesure seule donnant `certain`) ; décision écrite avec le
   conflit d'EC1 (D1).

### Bloc I — Révision 4, rejeu des builds de T05 et point d'arrêt (point 9)

1. `forever decode` de 1.60.1.70124, puis `forever install --dry-run` : liste des valeurs changées (fichier décodé
   nouveau, origines, certitudes abaissées, plafond reporté, valeurs de `mechanics.json` déplacées) ; accord, puis
   installation en révision 4 **dans l'arbre de travail, sans commit**.
2. `scripts/replay_builds.py run T08b`, puis `compare PV1 T08b` : chaque recommandation changée (contexte, niveau,
   points, métrique, alternative).
3. **Raison de chaque changement, par ablation** : rejouer les cas changés en remettant un à un chaque ratio décodé
   à son estimation (Intelligence par point de critique, mana de base, XP par niveau, constante d'armure, valeurs
   lues dans `classes.json`) ; la raison d'un changement est le ratio dont le retrait l'annule (ou la combinaison,
   si aucun seul ne suffit). Option de rejeu prévue pour cela (`--ratios seed:<nom>`), sans toucher aux données.
4. **Arrêt** : je te montre la table des recommandations changées avec leur raison, avant le commit de la révision 4.
   Après ton accord : commit des données, section « Rejeu T08b » de `docs/research/builds-T05.md`, rapport de
   données `docs/research/data-1.60.1.70124-r4.md`.

## Fichiers

| Fichier | Bloc | Nature |
| --- | --- | --- |
| `forever/origins.py`, `scripts/check_origins.py`, `tasks.py` | H | nouveau, nouveau, étape `origins` |
| `forever/data/<version>/origins.json` (deux versions) | H | nouveau fichier de données |
| `docs/research/valeurs-ecrites-a-la-main.md` | H, fin | inventaire généré |
| `forever/pipeline/fetch.py`, `decode.py`, `verify.py`, `install.py` | A, B, C | GameTables, nouveau fichier décodé, révision de tous les fichiers décodés |
| `forever/gamedata.py`, `forever/engine/model.py`, `forever/engine/character.py`, `forever/engine/monsters.py`, `forever/optimize/leveling.py` | A, B | ratios selon le mode, plafond de bêta |
| `forever/pipeline/diff.py`, `report.py` | C | valeurs de `spell_scaling.json` et du fichier décodé |
| `forever/pipeline/hotfixes.py` | E | nouveau |
| `forever/addons.py` | D | nouveau |
| `forever/watch.py`, `forever/hooks.py` | G | nouveau, ligne de démarrage |
| `forever/pipeline/notes.py` | F | nouveau (réseau) |
| `forever/cli.py`, `forever/mcp_server.py` (`forever_status` : résumé de la veille locale, sans réseau de plus) | A à G | commandes `origins`, `hotfixes`, `addons status`, `watch`, `notes`, options d'installation |
| `scripts/replay_builds.py` | I | option d'ablation |
| `scripts/install_watch_task.ps1` | G | nouveau |
| `tasks/T08b-notes-watch.patch` | F | patch du workflow |
| `docs/MECHANICS_REGISTRY.yaml`, `docs/OPEN_QUESTIONS.md`, `docs/DECISIONS.md`, `docs/DATA_SOURCES.md`, `docs/ARCHITECTURE.md`, `docs/USAGE.md`, `docs/ROADMAP.md`, `CLAUDE.md` | tous | registre, questions, décisions, sources, commandes |
| `docs/research/lecture-directe-client.md`, `docs/research/data-1.60.1.70124-r4.md`, `docs/research/builds-T05.md` | G, I | secours documenté, rapport de données, rejeu |
| `tests/fixtures/wago/1.60.1.70124/`, `tests/fixtures/hotfix/`, `tests/fixtures/addons/`, `tests/fixtures/forum/` | A à F | extraits et fixtures synthétiques |

## Tests attendus

Valeurs attendues lues dans les fixtures (ligne et colonne nommées dans le test) ou dans `forever/data/`, jamais
écrites dans le test.

| Bloc | Test | Attendu |
| --- | --- | --- |
| H | `test_origins.py` | les fichiers installés des deux versions passent ; une feuille ajoutée sans règle échoue (copie des données, manifeste régénéré) ; `manuel` sans raison échoue ; `manuel` à `certain` sans preuve échoue ; motif sur `manuel` refusé ; entrée de `mechanics.json` plus certaine que sa règle échoue ; `copie_figee` au niveau du fichier accepté |
| H | `test_origins_inventory.py` | l'inventaire liste chaque valeur `manuel` une fois, avec raison et certitude ; sortie déterministe ; aucune `certain` |
| H | `test_tasks_verify.py` (ou extension existante) | `verify` compte l'étape `origins` |
| A | `test_decode_character.py` | sur les fixtures : mana de base, critique par Intelligence et par Agilité, PV par Endurance égaux aux lignes de `PlayerExpectedStat` ; XP par niveau égale à `LevelExperience` ; repos égal à `Exhaustion` ; constante d'armure égale à `ExpectedStat` ; courbes 27 et 28 égales à leurs `CurvePoint` ; mana nulle pour une classe sans mana ; écart DB2 / GameTable signalé sur une fixture modifiée |
| A | `test_fetch_gametables.py` | adresse `api/casc` construite depuis `decode_rules.json` ; réponse vide = absente, aucun autre appel ; refus hors ligne ; aucun réseau dans le test |
| A | `test_engine_character_rules.py` | même personnage : en mode forever, critique et mana issues du fichier décodé (fixture) ; en mode seed, valeurs de `fm.py` inchangées ; sans fichier décodé, mode forever = estimations, hypothèse affichée |
| A | comptes des fichiers (`test_data_import.py`, `test_manifest.py`, `test_decode_version.py`) | nouveau fichier décodé et `origins.json` comptés |
| A, B | `test_registry.py` | `total`, `coverage`, sortie de `main`, nombre de `teste` aux valeurs du bloc (écrites en phase rouge) |
| B | `test_install_game_state.py` | `--beta-level-cap` écrit le plafond et sa source ; sans option, report signalé ; `GameData` lit le bloc ; l'ancienne clé de `mechanics.json` est refusée |
| B | `test_decode_mechanics.py` | Ignite (aura, durée, période), Winter's Chill par cumul, premier niveau à points de talent égaux aux lignes des fixtures |
| B | `test_utility_source.py` (selon D2) | en mode forever, la valeur de `classes.json` ; en mode seed, la copie du seed |
| C | `test_diff_scaling.py` | un coefficient, des points par niveau, une période et une recharge de talent modifiés dans une copie : quatre lignes de diff nommant sort, rang, composant, avant et après ; aucun changement sur deux copies identiques |
| C | `test_install_revision_decoded.py` | une révision installe `spell_scaling.json` et le fichier décodé et liste leurs valeurs changées |
| E | `test_hotfixes.py` | sur la fixture : tables suivies seulement, `VALID` et `DELETE`, `INVALID` compté à part ; journal en ajout seul (second passage sans nouvelle ligne n'écrit rien) ; « depuis l'installation » selon la date de la révision ; entités reliées par les CSV de fixture ; hypothèse ajoutée à `forever lookup` pour une entité touchée |
| D | `test_addons_status.py` | `nouveau` au premier relevé ; `inchangé` au second ; `changé` quand un fichier de données change à chaîne de version identique ; différences des agrégats de Questie listées ; sans `--save`, rien écrit ; aucun réseau |
| G | `test_watch.py` | build du client changé, addon changé, correctif nouveau, journal nouveau : chacun détecté et assorti d'une action proposée, rien lancé ; second passage sans changement : sortie vide ; ligne de démarrage limitée à une ligne et sans exception sur un dossier absent |
| F | `test_notes.py` | sujet nouveau et sujet révisé détectés, message non officiel ignoré, « Known Issues » repéré, entités reconnues par les noms des données et le dictionnaire ; une adresse interdite par un `robots.txt` de fixture arrête la lecture ; corps d'issue déterministe avec marqueur d'état |
| F | `test_network_boundary.py` | inchangé (le code réseau reste dans `pipeline/`) |
| I | `test_replay_builds_ablation.py` | l'option d'ablation remplace un seul ratio et refuse un nom inconnu |

## Hors périmètre

- Décodage de `DBCache.bin` (valeurs des correctifs) et baisse automatique de certitude sur un correctif ou un diff
  `stale` (T08).
- Modèle d'XP de Forever, XP de repos dans la simulation du leveling, XP selon l'écart de niveau (T04d).
- Lecteurs d'AtlasLoot et de ForeverDungeonJournal pour leurs consultations (DJ1) : ici, version et empreintes.
- Lecture directe des fichiers du client sans wago.tools : documentée seulement.
- PV des monstres tirés d'une table du client, armure des monstres (H2) : questions ouvertes, rien de modélisé.
- Autres sources officielles (actualités de worldofwarcraft.blizzard.com, forums européens) : à ajouter au
  lancement, sur accord.

## Risques

- **Les ratios décodés changent les builds de leveling** (critique tirée de l'Intelligence bien plus forte en début
  de partie selon l'audit, mana de base plus faible) : le rejeu peut changer plusieurs recommandations ; l'ablation
  en donne la raison ; arrêt avant le commit des données.
- **Colonne sans nom de `PlayerExpectedStat`** lue comme PV par Endurance : `probable`, non utilisée par le moteur.
- **Hotfix.log volumineux** : lecture incrémentale et filtrée, budget mesuré ; un format qui change rend une erreur
  lisible, jamais un échec du hook.
- **Ligne de démarrage trop lente** sous `uv run` Windows : court-circuit par taille et date, résultat mis en cache,
  `forever watch` complet seulement à la demande ou par la tâche planifiée.
- **Inventaire des valeurs à la main** : plusieurs centaines de feuilles ; regroupées par raison pour rester lisibles,
  mais chaque chemin nommé.
- **Conditions de Blizzard** (D1) : à réexaminer au plan d'EC1.
- **Tests verrouillés faux** : demandes regroupées dans `tasks/T08b-corrections.md`, présentées avant la fusion.

## Angles morts attendus (à chiffrer en fin de tranche)

- Critique de base, mana par Intelligence, statistiques de base par race, régénération de mana par l'Esprit : restent
  estimés (absents du client).
- Valeurs des correctifs du serveur (`DBCache.bin`) : seulement la liste des lignes touchées.
- Table de PV et d'armure réellement lue par le serveur : inconnue.

## Critères de fin

- Les ratios du client sont lus en mode forever (mana de base, critique par Intelligence, XP par niveau, constante
  d'armure), le mode seed et `tests/parity/` inchangés ; recoupement par les GameTables documenté.
- Plus aucune valeur dépendante de la version écrite à la main sans origine : plafond de bêta par l'installation,
  valeurs `certain` à la main décodées ou abaissées ; `forever origins inventory` sans aucune `certain` manuelle.
- `forever diff` liste les valeurs changées de `spell_scaling.json` et du fichier décodé.
- `forever addons status`, `forever hotfixes`, `forever watch` testés sur fixtures, sans réseau ; ligne de démarrage
  enrichie ; script de tâche planifiée livré.
- `forever notes` testé sur fixtures ; workflow en patch avec sa commande.
- Révision 4 de 1.60.1.70124 installée après accord ; rejeu des builds de T05 documenté avec la raison de chaque
  recommandation changée.
- Registre, questions ouvertes, décisions, `CLAUDE.md` et documentation à jour ; `uv run tasks.py verify` vert ; CI
  verte sous Ubuntu et Windows ; fusion en avance rapide dans `main`.

## Validation

Plan à valider par l'utilisateur (D1 à D5) avant l'exécution, dans une nouvelle session, sur la branche `t08b`.
