# LN1 — Préparation au lancement : plan

Tranche de la ROADMAP (section « LN1 — Préparation au lancement »), fondée sur les décisions 226, 227, 231, 234, 241,
244, 247, 251, 256, 257, 260 et 264. Plan écrit le 2026-10-14 ; exécution à partir du 21 octobre (fin de la bêta) et
**au plus tard le 24 octobre** (décision 251), sur une branche `ln1`. Le code s'écrit et se teste sur fixtures ; ce
qui demande la version finale installée (nom de son produit, numéro d'interface, tests en jeu) se fait le 4 novembre
en suivant `docs/LANCEMENT.md`.

## Demande de l'utilisateur (2026-10-14)

1. Découverte des installations par leur `.build.info` (produit, version, exécutable), bêta et version finale
   distinguées, version finale choisie dès qu'elle existe, choix forçable ; produit de la version finale accepté
   partout où celui de la bêta est exigé, sans deviner son nom ; suffixe des `.toc` ; veille, archivage de
   `DBCache.bin`, `forever update`, tâches planifiées, pont et addons sur la bonne installation, y compris quand la
   bêta et la version finale cohabitent.
2. `forever doctor`, sans réseau, contrôle de toute l'installation avec la correction de chaque problème ; tous les
   cas réels de la remise à zéro du PC du 12 octobre détectés.
3. Sauvegarde et restauration de ce qui n'est pas sur GitHub, restauration par `forever doctor`.
4. Profil : personnages de la bêta archivés, nouveaux personnages créés depuis le jeu ; données de la bêta gardées
   comme point de départ et remesurées par les journaux de la version finale ; tests en jeu restés facultatifs
   (décision 247).
5. `docs/LANCEMENT.md` : pas-à-pas du 4 novembre sur les deux PC, y compris quand le jeu change de dossier.

## Réponses de l'utilisateur (2026-10-14)

1. **Produit de la version finale : adoption confirmée.** Un produit inconnu (ni la bêta, ni un produit public connu
   qui n'est pas Forever) est signalé par `forever doctor` et `forever wow list` ; `forever wow adopt <dossier>`
   l'inscrit une fois comme version finale au journal des versions ; ensuite il est choisi d'office partout. Jamais
   d'adoption automatique (un second produit Forever, de stress test, existe déjà : voir l'étude).
2. **Sauvegardes** : chaque jour au passage de 08:00, jeu fermé ; avant toute restauration ou bascule
   d'installation ; `forever backup` à la main ; **14 gardées**. **Jamais sur le disque système par défaut** (la
   remise à zéro a effacé tout C:) : un autre disque fixe s'il en existe un, dans `WoW Forever\sauvegardes\<date>` ;
   sinon OneDrive s'il est connecté et synchronisé ; sinon Documents, avec un avertissement de `forever doctor`.
   Modifiable par `FOREVER_BACKUP_DIR`.
3. **Claude Code** : journal du pont (« OAuth session expired », `/login`) et `claude auth status` (seuls `loggedIn`
   et `authMethod` gardés ; e-mail et organisation jetés, jamais écrits). Vérifié au bloc D que la commande ne touche
   pas le réseau ; sinon, repli sur le journal seul, sans nouvel accord.
4. **Découverte** : racines fixes et déclarées ; lecture de `.build.info` et `.flavor.info` seulement ; pas de
   `product.db` de Battle.net.

## Étude de l'existant (décision 264 ; web le 2026-10-14, lecture seule, aucun téléchargement)

| Trouvaille | Licence | Fraîcheur | Réutilisable pour LN1 | Verdict |
| --- | --- | --- | --- | --- |
| instawow, `wow_installations.py` (layday/instawow) | GPL-3.0 | actif | lecture de `.build.info` par nom de colonne (BPSV, en-tête `Nom!TYPE:taille`, lignes `#` ignorées), table produit → sous-dossier, plages de versions ; découverte locale sous macOS seulement | **recouper** (parseur réécrit, ~15 lignes ; rien copié) |
| WowUp 2.24.0 (10 oct. 2026, « WoW Forever support »), commits `a2d38e2` et `c2b12a2` | GPL-3.0 | 2026-10 | découverte Windows par `product.db` de l'Agent Battle.net ; bêta de Forever = `ClassicBeta` distinguée par le dossier ; `.toc` lus avec `forever\|camelot` ; **doublons d'installation par chemins non normalisés** | **recouper** (piège des chemins retenu ; `product.db` écarté, réponse 4) |
| CurseBreaker (AcidWeb) | GPL-3.0 | — | sauvegarde complète de `WTF` avant chaque mise à jour | **recouper** (principe) |
| WowUp « Interface Settings Backup » | GPL-3.0 | — | parcours de sauvegarde de `WTF` | **recouper** (parcours) |
| warcraft.wiki.gg `TOC_format` (9 oct. 2026) | CC BY-SA | 2026-10 | ordre de lecture : suffixe du jeu (`_Forever`, `_Camelot`), puis famille (`_Mainline`), puis sans suffixe ; `## Interface` à plusieurs valeurs séparées par des virgules | **réutiliser** la règle (citée) ; à vérifier sur le client final |
| warcraft.wiki.gg `Template:LatestPatchInfo`, BlizzTrack | CC BY-SA / — | 2026-10-14 | codes produits publics (`wow`, `wowt`, `wowxptr`, `wow_beta`, `wow_classic`, `wow_classic_ptr`, `wow_classic_era`, `wow_classic_era_ptr`, `wow_anniversary`, `wow_classic_titan`) ; bêta de Forever `wow_classic_beta` (`_classic_beta_`, `WowB.exe`, interface 16001) ; **second produit Forever `wowf`** (« Forever PTR » / « Stress Test », 1.60.1.70245) | **recouper** : liste des produits connus **qui ne sont pas Forever** (exclusion), citée ; `wowf` n'est écrit nulle part (inconnu tant qu'il n'est pas adopté) |
| Annonce Blizzard de la bêta (news.blizzard.com, article 24304160) | — | 2026-10 | ni dossier ni produit de la version finale | **non annoncé** : rien deviné |
| ForeverSVBridge (CurseForge, MIT, 24 sept.) et fils du forum Blizzard 2356559, 2353992 | MIT / — | 2026-09/10 | joueurs : la bêta écrirait les SavedVariables sans les relire ; aucune reconnaissance officielle | **écarter** (non modélisé) ; signalé en information par `doctor` si un tel addon est présent |
| WoWInterface (fil 45715) | — | ancien | copier ou restaurer `WTF` jeu fermé, sinon le client réécrit à la sortie | **réutiliser** la règle |
| `gh auth status` (cli/cli, `status.go`) | MIT | trunk | interroge GitHub | **écarter** (réseau) |
| `gh auth token` (cli/cli, `token.go`) | MIT | trunk | dit sans réseau qu'un jeton est présent (pas qu'il est valide) | **réutiliser** (sortie jetée, seul le code compte) |
| `claude auth status` (documentation de Claude Code) | — | 2026-10 | JSON `loggedIn`, `authMethod`, code 0/1 | **réutiliser** (réponse 3) ; `.credentials.json` **jamais lu** (format non documenté) |
| `MpCmdRun.exe -CheckExclusion` (SharpExclusionFinder) ; `Get-MpPreference` | — | 2026 | exclusions de Defender | **écarter** : essayé sur ce PC sans droits, `0x80070005` ; `Get-MpPreference` rend « N/A: Must be an administrator » ; la clé du registre est refusée. `doctor` dit « non vérifiable » et renvoie à `docs/LANCEMENT.md` |
| `flutter doctor`, `brew doctor`, `claude doctor` | — | — | une ligne par contrôle, puis la correction ; constat séparé de la correction | **réutiliser** la forme |

Non trouvé : bibliothèque Python pour `.build.info` ; outil de migration des addons ou de `WTF` de la bêta vers la
version finale ; annonce du produit, du dossier ou du numéro d'interface de la version finale.

## Constats (dépôt, PC de jeu, 2026-10-14)

### Installation réelle (lecture seule)
- `C:\Program Files (x86)\World of Warcraft\.build.info` : en-tête de 15 colonnes, **une ligne**, `Product`
  `wow_classic_beta`, `Version` 1.60.1.70374. Le fichier est à la racine, partagé par tous les produits installés.
- `_classic_beta_\.flavor.info` : `Product Flavor!STRING:0` puis `wow_classic_beta` : **relie un dossier à son produit
  sans déduire du nom du dossier**. Exécutable `WowB.exe`.
- Addons tiers : 8 `_Camelot.toc` et 8 `_Forever.toc` ; les nôtres n'ont pas de suffixe (lus en dernier recours).
- `WTF\Config.wtf` : `SET advancedCombatLogging "1"`. Journaux dans `Logs\WoWCombatLog-*.txt`.
- Disques fixes : C:, D: (« RPKrypto »), E: (« Divers », 26 Go libres), F: (« SAUVEGARDE », 809 Go libres).
  Dossier `OneDrive` présent mais aucun compte dans `HKCU\Software\Microsoft\OneDrive\Accounts`.
- `claude auth status` : JSON (`loggedIn`, `authMethod`, plus e-mail et organisation, à jeter). `gh auth token`
  sort en 0. Interpréteur `python` absent du `PATH` de Git Bash (tout passe par `uv`).

### Code : la bêta écrite en dur
- `forever/config.py:37` `DEFAULT_WOW_DIR` (`_classic_beta_` sous `Program Files (x86)`) ; `:90-94`
  `WOW_DIR_CANDIDATES` ; `:97-103` `default_wow_dir` (`FOREVER_WOW_DIR`, puis premier candidat existant, puis défaut).
- `scripts/install_plugin.ps1:72-87` : candidats `-WowDir`, ancienne `FOREVER_WOW_DIR` (passe avant les candidats),
  deux dossiers `_classic_beta_` ; écrit `FOREVER_WOW_DIR` sans demander.
- `forever/pipeline/client_builds.py:47-79` `read_build_info` : lit `wow_dir.parent/.build.info` ; **produit déduit du
  nom du dossier** (`wow_{nom sans _}`, `:65`), repli sur la ligne unique. Journal `<cache>/client_builds.json`
  (schéma 1, `builds[]` avec `product`), en ajout seulement ; `version_at` et `split_by_version` **ignorent le produit**.
- Appelants : `archive.py:275-317` (archives `<cache>/dbcache/<build>/`, sans produit), `bridge/status.py:139`,
  `watch.py:74,255`, `update.py:634-666` (`_step_game`), `:1381` (correctifs), `:1566` (journaux), `cli.py:2299,3825,
  4127`, `profile_import.py:23`.
- Produit demandé à wago.tools : **aucune constante** ; `product` et `version_prefix` lus dans
  `forever/data/<v>/sources.json` (7 versions, toutes `wow_classic_beta`), recopiés dans `manifest.json` ; lecteurs
  `cli._local_product` (`forever builds`, CI build-watch), `freshness.freshness_for_version`, `update._step_game` ;
  `decode.py:2054,2095` recopie ces clés de la version de base dans la candidate.
  `.github/workflows/build-watch.yml:70` : texte « le produit wow_classic_beta est toujours le bon ».
- Exécutables : `pipeline/live_logs.py:22` `DEFAULT_EXECUTABLES` (six noms publics) et `client_executables`.
- `.toc` : `ForeverLogger.toc` et `ForeverBridge.toc` sans suffixe, `## Interface: 16001` ; emplacements et sondes
  générés par `forever/bridge/install.py` (`INTERFACE = "16001"`, `:54`) ; `scripts/check_addon.py:17` ;
  `forever/addons.py:131` cherche `*_Camelot.toc` d'abord ; `bridge/guide_addon.py:18` recopie l'interface.
- Tâche du pont : `bridge/autostart.py:74` écrit `--wow-dir` dans ses arguments ; la surveillance le garde.
  La tâche de mise à jour (`scripts/install_update_task.ps1`, `update_task.py`) relit l'installation à chaque passage.
- Tests qui figent la bêta : `tests/conftest.py:76` `PRODUCT`, `test_manifest.py:91`, `test_install_script.py:17-82`,
  `test_client_builds.py:64-72` (fait de `wow_classic` un produit étranger au dossier bêta), `test_bridge_autostart.py:26`,
  fixtures wago `builds_*.json` ; dossiers `_classic_beta_` construits dans une quinzaine de tests (inchangés : un
  dossier de fixture n'est pas une règle).

### Code : réutilisable pour `doctor`, la sauvegarde et le profil
- `bridge/autostart.py` : `schtasks()` (seul point d'appel, simulé par la classe `Schtasks` des tests), `query()`,
  `parse_task()`, **`status()`** (problèmes « interpréteur introuvable », « dépôt introuvable »), `supervisor_pid()`.
  **Aucune lecture Python de la tâche « WoW Forever - mise à jour »** (nom seulement dans le `.ps1` et `cli.py:2923`).
- `spawn.py` : `probe_environment` (import de `forever.cli`), `read_environment`, `environment_line`,
  `current_interpreter`, `pid_alive`. `bridge/lock.py` : `lock_holder`, `pid_reused`.
- Journal du pont `<cache>/bridge/journal/<date>.jsonl` (`Journal.recent`, `.tail`) : les erreurs de `claude` y sont
  en `error` (`where="conversation"`, 300 derniers caractères de stderr). **Aucune détection d'OAuth** aujourd'hui.
- `update._gh_missing` (`gh --version`, décision 244) ; `gitops.subprocess_runner`, `_AUTH_HINTS`.
- Journal de combat : `combatlog._header` exige `ADVANCED_LOG_ENABLED 1` (lève `UnsupportedLogError`) ;
  `combatlog.log_files`. ForeverLogger active le journal à chaque connexion mais **n'écrit aucun indicateur**.
- `addons.addons_status` (16 addons de données, empreintes, `own_addons`), `bridge/install.addon_outdated`
  (comparaison octet par octet ; `## Version` ignorée ; emplacements et sondes hors comparaison).
- `provenance.local_provenance`, `_emit`, table `handlers` de `cli.main`, tests par `main([...], deps)` + `capsys`,
  `make_deps`. **`tests/unit/test_network_boundary.py:62-104` : `subprocess` permis dans 8 modules seulement.**
- Sauvegardes existantes : `bridge/addons.snapshot` (seule copie datée), `install_addon` et `guide_addon` (déplacent).
- Profil : `~/.forever/profile.json` (schéma 3), **personnages indexés par nom seul** ; `profile_import._merge_character`
  **saute** un homonyme vu sur un autre royaume ; aucune notion d'archivage ni de produit ; `game_version` d'un
  personnage = version des données. Import : `forever profile import` (ForeverLogger, Questie, Auctionator,
  journaux), `_default_sv` ne prend que le premier compte.
- Mesures : aucune version par valeur ; `monsters.json` porte `game_version`, `inherited_from` (dernier saut),
  sources `journal <fichier>`. `forever measures refresh` (`split_by_version`, `--accept-version`, `--into`).
- Variables `FOREVER_*` lues : `FOREVER_CACHE_DIR` (non documentée dans `docs/USAGE.md`), `FOREVER_WOW_DIR`,
  `FOREVER_OFFLINE`, `FOREVER_PROFILE`, `FOREVER_HOME` ; internes `FOREVER_BRIDGE`, `FOREVER_PYVENV_LAUNCHER`,
  `FOREVER_E2E`. `docs/USAGE.md:189` omet `autostart_env_error` et `autostart_skip`.
- Vérifications en jeu en attente : `docs/OPEN_QUESTIONS.md` (MON7, DON4, LOG6, BR2, BR4, BR5, BR9, RXP1, RXP2,
  PRO1, NFB1, BR6, BR7, LEG1, LEG2, PET1), `docs/ADDON.md:31` (suffixe « Camelot » au lancement), `:503-512`
  (sondes `/dump`, produit du lancement), procédure 21 (sonde I, facultative) ; SIM1 et T10a annoncent des procédures
  « au lancement » qui **n'existent pas encore** dans `docs/ADDON.md`.

## Décisions à écrire (étape 0, `docs/DECISIONS.md`)

- **267 — Choix du plan de LN1** : réponses 1 à 4 ci-dessus ; règle de choix de l'installation et du forçage ;
  emplacement des sauvegardes (règle des disques) ; `claude auth status` réduit à deux champs ;
  `.credentials.json` jamais lu ; exclusions de Defender « non vérifiables » sans droits ; archives des versions
  non bêta rangées par produit ; profil à personnages archivés (schéma 4) ; liste des produits publics connus qui ne
  sont pas Forever (sources citées, aucune supposition du produit final).

## Conception

### Installations (`forever/installs.py`, nouveau, sans `subprocess`)
- **Racines** (réponse 4), dans cet ordre, chemins normalisés (`os.path.normcase` + `resolve`, sans barre finale)
  pour ne jamais compter deux fois la même installation (piège de WowUp) : parent de `FOREVER_WOW_DIR` et de
  `FOREVER_WOW_FORCE` ; `FOREVER_WOW_ROOTS` (liste séparée par `;`) ; pour chaque disque fixe (injecté, liste réelle
  par `os.listdrives()` + type de lecteur via `ctypes.windll.kernel32.GetDriveTypeW`, rien sous Linux),
  `<d>:\Program Files (x86)\World of Warcraft`, `<d>:\Program Files\World of Warcraft`, `<d>:\World of Warcraft`,
  `<d>:\Games\World of Warcraft`. Aucun balayage du disque.
- **Une installation** = un sous-dossier `_*_` d'une racine qui contient un `Wow*.exe` (hors `*_loader*`, hors
  `BlizzardError.exe`) : `Install(root, folder, product, version, executable, flavor_source)`. Produit lu dans
  `<dossier>\.flavor.info` ; à défaut, la ligne du `.build.info` dont le produit a ce dossier dans la liste des
  produits connus, sinon la ligne unique ; sinon `product=None` (« produit illisible »). **Jamais déduit du nom du
  dossier.** Version = colonne `Version` de la ligne du produit (lecture par nom de colonne, jamais par position).
- **Rôle** : `beta` si le produit est celui des données installées (`sources.json`, aujourd'hui `wow_classic_beta`,
  observé et non deviné) ; `final` si le produit est adopté (journal) ; `other` si le produit est dans
  `NOT_FOREVER_PRODUCTS` (produits publics de l'étude, avec leur source en commentaire) ; sinon `unknown`.
- **Choix** (`choose(installs, *, forced, option) -> Choice(install, reason)`) : `--wow-dir` de la commande ;
  sinon `FOREVER_WOW_FORCE` (dossier) ; sinon la `final` la plus récente (version) ; sinon la `beta` ; sinon
  `FOREVER_WOW_DIR` s'il existe ; sinon aucune (raison « aucune installation trouvée »). Raison en français
  (« version finale adoptée », « forcée par FOREVER_WOW_FORCE », « bêta : aucune version finale adoptée »…).
- **Adoption** : `forever wow adopt <dossier>` (jeu fermé non exigé, confirmation `--yes`) inscrit dans
  `client_builds.json` (schéma 2, lecture du schéma 1 conservée) `products: {<produit>: {role: "final", adopted_at,
  folder}}` ; refuse un produit `other` ou `beta`, ou un produit illisible. `forever wow forget <produit>` le retire.
- **`config.default_wow_dir`** devient `installs.chosen(environ).folder` avec le repli actuel si rien n'est trouvé ;
  `DEFAULT_WOW_DIR` et `WOW_DIR_CANDIDATES` disparaissent au profit des racines.
- **CLI** : `forever wow list [--json]` (installations, rôle, produit, version, exécutable, choix et raison) ;
  `forever wow adopt|forget` ; `forever status` ajoute l'installation choisie et la raison.

### Bonne installation partout
- `read_build_info(wow_dir)` lit le produit par `installs` (`.flavor.info`) ; le test qui faisait de `wow_classic`
  un produit étranger est réécrit sur la règle `.flavor.info`.
- **Journal des versions** : `version_at` et `split_by_version` prennent le produit ; un journal de combat pris sous
  la bêta n'est jamais compté comme mesure de la version finale (et l'inverse), sauf `--accept-version` (décision
  221) qui dit alors « mesuré sous la bêta ». Le produit d'un journal vient de l'installation dont il est tiré (dossier
  `Logs` de cette installation), recoupé par l'en-tête du journal (`BUILD_VERSION`).
- **Archives** : celles de la bêta restent à `<cache>/dbcache/<build>/` (les empreintes de `sources.json` y renvoient,
  mémoire « révision et DBCache archivé ») ; tout autre produit va à `<cache>/dbcache/<produit>/<build>/`. Fonction
  unique `archive.archive_dir(cache, product, build)` ; aucune archive d'une installation écrite dans le dossier de
  l'autre, même à build égal.
- **`forever update` et `forever builds`** : le produit demandé à wago.tools est celui de l'installation choisie
  quand elle est `final` ; sinon celui de `sources.json`. `decode` écrit dans la candidate le produit de
  l'installation dont vient le build (au lieu de recopier celui de la base) ; `version_prefix` suit la version lue.
  `build-watch.yml` : texte rendu neutre (patch hors dépôt, mode auto, piège du skill).
- **Veille et tâches** : la veille du démarrage et la tâche de 08:00 relisent le choix à chaque passage (déjà le cas
  pour la tâche). **Tâche du pont** : la surveillance ne fixe plus le dossier ; `--wow-dir` devient facultatif
  (présent = forcé, gardé pour les tâches existantes) ; sans lui, la surveillance résout le choix à chaque lancement
  du pont et, quand il change, arrête le pont **jeu fermé** et le relance sur le nouveau (événement
  `autostart_wow_changed`). `forever bridge autostart install` n'écrit plus `--wow-dir` sauf `--wow-dir` explicite.
  `doctor` signale une tâche ancienne (avec `--wow-dir` différent du choix) et donne la commande pour la recréer.
- **Addons** : `scripts/install_addon.py` et `forever bridge install` visent l'installation choisie (ou `--wow-dir`) ;
  la réserve et les sondes suivent. `scripts/install_plugin.ps1` lance `uv run forever wow list --json`, montre le
  choix et sa raison, et **demande avant de changer** `FOREVER_WOW_DIR` quand il diffère de l'ancienne valeur.
- **Suffixe des `.toc`** : nos `.toc` restent sans suffixe (lus par tout client en dernier recours) ; aucun fichier
  suffixé ajouté tant que la version finale n'a pas montré qu'elle en exige un (`docs/LANCEMENT.md`) ;
  `addons._toc` lit dans l'ordre `_Forever`, `_Camelot`, `_Mainline`, sans suffixe (règle du wiki, citée).
  **Numéro d'interface** : `## Interface` accepte plusieurs valeurs ; les valeurs admises viennent d'une seule
  constante partagée par `check_addon.py`, `bridge/install.py` et `guide_addon.py` ; la valeur de la version finale
  est **ajoutée le 4 novembre** après lecture en jeu (`/dump select(4, GetBuildInfo())`, étape de
  `docs/LANCEMENT.md`), jamais devinée. ForeverLogger 0.7.0 note `GetBuildInfo()` (version, build, interface) dans
  son instantané, pour que `doctor` compare l'interface vue en jeu à celle des `.toc` (« addons périmés »).

### `forever doctor` (`forever/doctor.py`, contrôles purs ; sondes injectées)
- Chaque contrôle rend `Check(id, status ∈ {ok, warn, fail, unknown, info}, constat, correction)` ; la correction est
  une commande ou un geste précis. Sortie texte `[ok]`/`[!]`/`[x]`/`[?]` + correction en retrait ; `--json` avec
  `checks[]`, `summary` et `provenance` (`local_provenance`, certitude `certain` pour ce qui est lu, `suppose` pour
  `unknown`). **Code 0** si aucun `fail` ; **code 7** (nouveau `EXIT_DOCTOR` dans `forever/errors.py`) sinon.
  Aucune correction appliquée par défaut ; `--fix` applique seulement les corrections sûres et locales (recréer
  une tâche, réinstaller un addon jeu fermé, restaurer sur confirmation).
- **Sondes** (`forever/doctor_probes.py`, **ajouté à la liste de `test_network_boundary.py`**, avec la même règle :
  pas de réseau) : `gh --version`, `gh auth token` (sortie jetée), `claude auth status` (deux champs gardés),
  `uv --version`, requêtes `schtasks` par `autostart.schtasks`, `spawn.probe_environment`, empreinte de `uv.lock`
  face à `.venv` (`.venv/pyvenv.cfg` et le fichier d'état d'uv `.venv/.lock`… forme exacte relevée au bloc D ; **sans
  lancer `uv sync`**, qui peut télécharger).
- **Contrôles** (identifiants stables, une ligne de `docs/USAGE.md` chacun) :
  1. `repo` : dépôt, `.venv`, `uv.lock` ; `env.python` : l'interpréteur de `spawn.current_interpreter` importe
     `forever.cli` (cas du 2026-10-13, décision 241) ; `env.state` : aucun `<cache>/bridge/environment.json` ni
     `<cache>/update/environment.json` ; `env.uv` : `.venv` suit `uv.lock`. Correction : `uv sync` à la racine du
     dépôt, puis relancer les deux tâches.
  2. `wow.installs` : au moins une installation ; `wow.choice` : choix et raison ; `wow.unknown` : produit inconnu
     signalé (« `forever wow adopt <dossier>` si c'est la version finale ») ; `wow.env` : `FOREVER_WOW_DIR` égal au
     choix (sinon `scripts/install_plugin.ps1`) ; `wow.paths` : `Interface\AddOns`, `Logs`, `WTF\Account\*\SavedVariables`
     existent (chemin avec espaces et parenthèses compris, cas `Program Files (x86)`).
  3. `addons.logger`, `addons.bridge` : présents dans l'installation choisie, identiques au dépôt
     (`addon_outdated`, étendu à ForeverLogger), réserve complète (200 emplacements, 2 sondes), interface des `.toc`
     dans les valeurs admises et égale à celle vue par ForeverLogger. Correction : `uv run python
     scripts/install_addon.py` / `uv run forever bridge install`, jeu fermé.
  4. `combatlog` : journal de moins de 7 jours dans `Logs` et son en-tête avec `ADVANCED_LOG_ENABLED 1` ;
     `advancedCombatLogging "1"` dans `WTF\Config.wtf`. Correction : activer ForeverLogger, puis se connecter.
  5. `addons.data` : addons de données de `forever addons status` présents (absents listés, information).
  6. `env.vars` : `FOREVER_WOW_DIR`, `FOREVER_HOME` (égal au dépôt), `FOREVER_CACHE_DIR`, `FOREVER_PROFILE`,
     `FOREVER_WOW_FORCE`, `FOREVER_WOW_ROOTS`, `FOREVER_BACKUP_DIR` : valeur, dossier existant.
  7. `gh` : `gh --version` (absent : `winget install --id GitHub.cli`), `gh auth token` (aucun jeton : `gh auth
     login`) ; la validité du jeton n'est pas contrôlée (réseau), c'est dit.
  8. `claude` : présent dans le `PATH` (`agent.find_claude`), `claude auth status` → `loggedIn` ; journal du pont
     des 7 derniers jours : erreur contenant `OAuth`, `session expired`, `/login` ou `401` plus récente que le dernier
     `reply` réussi → `fail` « connexion de Claude Code expirée » ; correction : lancer `claude` puis `/login`.
  9. `tasks.bridge`, `tasks.update` : présentes (`schtasks /Query /XML`), interpréteur et dépôt existants
     (`autostart.status`), dépôt égal à celui-ci, `--wow-dir` absent ou égal au choix ; tâche de mise à jour lue de
     la même façon (nouvelle `update_task.query`). Corrections : `uv run forever bridge autostart install`,
     `powershell -File scripts\install_update_task.ps1`.
  10. `bridge.running` : surveillance vivante (`supervisor_pid`), pont vivant (`lock_holder`), pas de fin anormale ;
      `bridge.journal` : boucle `autostart_bridge_down` ou `autostart_env_error` récente.
  11. `profile` : profil présent et lisible ; sinon « restaurer (`forever backup restore`) ou importer (`forever
      profile import`) ».
  12. `backup` : dernière sauvegarde de moins de 2 jours ; emplacement **hors du disque système** (sinon `warn`,
      réponse 2) ; restauration proposée quand le profil ou les SavedVariables manquent et qu'une sauvegarde existe.
  13. `antivirus` : `unknown` « exclusions de Defender non vérifiables sans droits d'administrateur » → section de
      `docs/LANCEMENT.md`.
  14. `info.sv_bridge` : addon tiers de contournement des SavedVariables présent (information seulement).
- Sous Linux (CI) : contrôles Windows (`tasks.*`, `antivirus`, disques) rendus `unknown` « non applicable ».

### Sauvegarde et restauration (`forever/backup.py`, `forever backup`)
- **Contenu** (ce qui n'est pas sur GitHub) : profil ; `WTF\Account\*\SavedVariables\*.lua` et
  `WTF\Account\*\*\*\SavedVariables\*.lua` de l'installation choisie (et de la bêta tant qu'elle existe), plus
  `WTF\Config.wtf` ; `<cache>/bridge/config.json`, `<cache>/bridge/addons/config.json` et le dossier de la
  conversation « addons » (son dépôt git local compris) ; `<cache>/update/pending/`, `state.json`, `config.json` ;
  `<cache>/client_builds.json` ; `<cache>/measures/last.json`. Jamais les jetons ni `.credentials.json`.
- **Forme** : un dossier daté `<racine>/WoW Forever/sauvegardes/<AAAA-MM-JJTHHMMSS>/` avec `manifest.json`
  (fichier → chemin d'origine, empreinte, taille, produit et dossier de l'installation, machine) ; copie simple
  (lisible à la main), écrite dans un dossier `.partiel` renommé à la fin. 14 gardées (les plus anciennes retirées).
- **Racine** (réponse 2) : `FOREVER_BACKUP_DIR` ; sinon le premier disque fixe hors système, dans l'ordre des
  lettres, avec au moins 1 Go libre ; sinon OneDrive connecté (compte dans
  `HKCU\Software\Microsoft\OneDrive\Accounts\*` avec un `UserFolder` existant) ; sinon Documents + avertissement.
  Sur ce PC, la règle donne **D:** ; F: « SAUVEGARDE » serait plus parlant : voir « Point à confirmer ».
- **Fréquence** : `forever update --auto` (tâche de 08:00 et passages du pont) fait la sauvegarde du jour si aucune
  n'a moins de 24 h et si le jeu est fermé (sinon reportée au passage suivant) ; avant toute restauration et toute
  bascule (`wow adopt`, changement du choix vu par la surveillance) ; `forever backup` à la main.
- **Restauration** : `forever backup restore [<date>] [--only profile|wtf|bridge|update]` : jeu fermé exigé,
  liste de ce qui sera écrasé, confirmation (`--yes`), **sauvegarde de l'état courant avant tout écrasement**,
  écriture atomique par fichier ; SavedVariables restaurées dans l'installation choisie (un compte absent est créé ;
  un personnage d'une autre installation n'est pas copié ailleurs). `forever doctor` propose la commande quand le
  profil ou les SavedVariables manquent. `forever backup list` montre les sauvegardes.

### Profil au lancement (`forever/profile.py`, `forever/profile_import.py`)
- **Schéma 4** (lecture des schémas 1 à 3 conservée) : clé d'un personnage `<nom>-<royaume>` ; nouveaux champs
  `product` (produit de l'installation où il a été vu) et `archived` (`{at, product, game_version}`) ; liste
  `archived_characters` séparée de `characters`. Migration à la première écriture, profil d'origine sauvegardé.
- `forever profile archive --product <produit>` (et proposé par `forever wow adopt`) : déplace les personnages de ce
  produit dans `archived_characters`, gardés et marqués, plus jamais proposés comme actifs ; `forever profile list
  --archived`.
- **Import** : un personnage vu dans les SavedVariables ou les journaux d'une installation reçoit son produit ; un
  homonyme d'un personnage archivé est importé à côté (plus de saut, cas de `_merge_character`) ; `_default_sv`
  lit tous les comptes de l'installation choisie. Les champs `client_build` restent.
- **Données** : la version finale part des données de la bêta par `forever install --new-version` (T08a,
  inchangé) ; `monsters.json` et les mesures héritées gardent `inherited_from` ; `forever measures refresh` sur la
  version finale ne prend que les journaux de la version finale (règle du produit ci-dessus), et chaque PNJ remesuré
  remplace la valeur héritée ; un rapport `forever measures inherited` liste les valeurs encore issues de la bêta.
- Tests en jeu en attente : liste tirée de `docs/OPEN_QUESTIONS.md` et `docs/ADDON.md` dans `docs/LANCEMENT.md`,
  toutes facultatives (décision 247, 260).

### `docs/LANCEMENT.md`
- Une section **par PC** (PC de jeu `RAPHAEL-GAMING`, et le second PC, nom à confirmer), chacune dans l'ordre :
  sauvegarde (`forever backup`) ; installation de la version finale par Battle.net ; `forever wow list` (ce qu'il
  faut voir : une ligne `unknown` avec le produit de la version finale) ; `forever wow adopt <dossier>` ;
  `scripts/install_plugin.ps1` (accepter le nouveau `FOREVER_WOW_DIR`) ; addons (`install_addon.py`, `forever bridge
  install`) ; relevé de l'interface en jeu, ajout à la constante, nouveau commit ; tâches (`forever bridge autostart
  install`, `install_update_task.ps1`) et pont relancé (mémoire « relancer le pont ») ; `forever doctor` à zéro
  problème ; première connexion (journal avancé, ForeverLogger) ; `forever update` (nouvelle version des données,
  `forever install --new-version`) ; `forever profile archive` et `forever profile import` ; `forever measures
  refresh` ; tests en jeu restés en attente.
- Pour chaque étape : commande, sortie attendue, que faire sinon. Cas **« le jeu change de dossier »** (nouveau
  disque, `Program Files` ↔ `Program Files (x86)`, dossier choisi dans Battle.net) : `forever wow list`, racine
  ajoutée à `FOREVER_WOW_ROOTS` au besoin, puis la suite. Section **antivirus** (exclusions à poser à la main, en
  administrateur). Section **remise à zéro du PC** (ordre : `uv`, dépôt, `uv sync`, `gh` et `gh auth login`,
  `claude` et `/login`, `install_plugin.ps1`, tâches, `forever backup restore`, `forever doctor`).
- Règle pour la suite (ROADMAP) : chaque tranche qui laisse un test en jeu en attente l'ajoute à ce fichier.

## Étapes et blocs (commits `LN1: tests (bloc X)` puis `LN1: bloc X vert`)

### Étape 0 — Préalables
Branche `ln1` depuis `origin/main` (mémoire « la veille pousse sur main ») ; décision 267 ; `docs/OPEN_QUESTIONS.md` :
DON4 reformulée (produit lu et adopté, plus deviné), LN-questions ci-dessous.

### Bloc A — Découverte et choix (`forever/installs.py`, `config.py`, `client_builds.py`, `forever wow`)
### Bloc B — Bonne installation partout (journal par produit, archives, `update`/`builds`/`decode`, surveillance du pont, addons, `install_plugin.ps1`)
### Bloc C — `.toc` et interface (constante partagée, ordre des suffixes, ForeverLogger 0.7.0, `check_addon.py`, `docs/ADDON.md`)
### Bloc D — `forever doctor` (contrôles 1 à 14, sondes, code 7, contrat de sortie)
### Bloc E — Sauvegarde et restauration (`forever backup`, passage quotidien, restauration guidée par `doctor`)
### Bloc F — Profil (schéma 4, archivage, import par produit, mesures héritées)
### Bloc G — Documentation (`docs/LANCEMENT.md`, `docs/USAGE.md`, `README.md`, `addon/README.md`, ROADMAP, skill `verifier` si besoin)

Ordre d'utilité si le temps manque : A, B, D, E, G, F, C (C ne sert vraiment que le 4 novembre).

## Fichiers

- Nouveaux : `forever/installs.py`, `forever/doctor.py`, `forever/doctor_probes.py`, `forever/backup.py`,
  `docs/LANCEMENT.md` ; tests `tests/unit/test_installs.py`, `test_wow_cli.py`, `test_choice_everywhere.py`,
  `test_toc_interface.py`, `test_doctor.py`, `test_doctor_cases.py`, `test_backup.py`, `test_profile_archive.py`,
  `test_no_final_product_name.py` ; fixtures `tests/fixtures/installs/` (racines `.build.info`, `.flavor.info`,
  exécutables vides).
- Modifiés : `forever/config.py`, `forever/pipeline/client_builds.py`, `forever/archive.py`, `forever/watch.py`,
  `forever/update.py`, `forever/update_task.py`, `forever/pipeline/decode.py`, `forever/cli.py`, `forever/status.py`,
  `forever/errors.py`, `forever/bridge/autostart.py`, `forever/bridge/install.py`, `forever/bridge/guide_addon.py`,
  `forever/bridge/status.py`, `forever/addons.py`, `forever/profile.py`, `forever/profile_import.py`,
  `forever/pipeline/refresh.py`, `scripts/install_addon.py`, `scripts/install_plugin.ps1`, `scripts/check_addon.py`,
  `addon/ForeverLogger/*`, tests existants cités aux constats (dans le commit « tests » de leur bloc),
  `docs/USAGE.md`, `docs/ADDON.md`, `docs/ROADMAP.md`, `docs/OPEN_QUESTIONS.md`, `docs/DECISIONS.md`, `README.md`.
  `.github/workflows/build-watch.yml` : patch hors dépôt donné à l'utilisateur.

## Interfaces (signatures indicatives, forme définitive au bloc)

```text
# forever/installs.py
parse_build_info(text) -> list[dict[str, str]]            # par nom de colonne
read_flavor(folder) -> str | None
discover(roots, *, environ, drives) -> list[Install]       # Install(root, folder, product, version, executable, role)
roles(installs, *, beta_product, adopted) -> list[Install]
choose(installs, *, option, environ) -> Choice             # Choice(install | None, reason)
chosen(environ=os.environ, ...) -> Choice
adopt(cache_dir, install, now) / forget(cache_dir, product)
# forever/pipeline/client_builds.py
read_build_info(wow_dir) -> ClientBuild | None            # produit par .flavor.info
version_at(cache_dir, when, *, product) ; split_by_version(..., product)
# forever/archive.py
archive_dir(cache_dir, product, build) -> Path
# forever/doctor.py
Check(id, status, finding, fix) ; run_checks(deps, probes) -> list[Check] ; exit_code(checks) -> int
# forever/backup.py
backup_root(environ, drives, onedrive, documents) -> (Path, warning | None)
make_backup(deps, now, *, reason) -> Path ; prune(root, keep=14) ; list_backups(root)
restore(deps, stamp, *, only, game_running, confirm) -> RestoreReport
# forever/profile.py
archive_characters(profile, product, now) -> list[str]
```

## Tests attendus (valeurs tirées des fixtures ; aucun chiffre de jeu, aucun nom de produit final)

Produits de fixture **manifestement fictifs** : `wow_fictif_finale`, `wow_fictif_inconnu` ; produits réels seulement
`wow_classic_beta` (lu dans `sources.json`) et un produit public de la liste d'exclusion (`wow`). Versions de fixture
`1.60.1.70374` (bêta, celle des données) et `9.99.9.99999` (fictive).

### Bloc A (`test_installs.py`, `test_wow_cli.py`)
- `parse_build_info` : en-tête à 15 colonnes (copie de l'en-tête réel, sans clés) et à 4 colonnes, colonnes
  permutées → même `Product`/`Version` ; ligne `#` ignorée.
- Quatre fixtures de racines : **bêta seule** → choix bêta, raison « bêta : aucune version finale adoptée » ;
  **bêta + finale adoptée** → choix finale ; **finale seule adoptée** → choix finale ; **bêta + produit inconnu non
  adopté** → choix bêta, `unknown` listé ; produit `wow` → rôle `other`, jamais choisi.
- Dossier sans `.flavor.info` : produit par la ligne unique ; deux lignes sans `.flavor.info` → produit illisible,
  jamais déduit du nom du dossier.
- `FOREVER_WOW_FORCE` vers la bêta alors qu'une finale est adoptée → bêta, raison « forcée » ; `--wow-dir` l'emporte
  sur tout. Même installation vue par deux racines (casse, barre finale) → une seule.
- Chemin `C:\Program Files (x86)\World of Warcraft\_classic_beta_` simulé (dossier `Program Files (x86)` dans
  `tmp_path`) → trouvé, chemin intact dans la sortie JSON.
- `adopt` d'un produit `other` ou `beta` → refus (code 2) ; `adopt` puis relecture du journal schéma 1 + 2.
- `forever wow list --json` : `installs[]`, `choice`, `reason`, `provenance` valide (`test_contract.py`, cas ajouté).

### Bloc B (`test_choice_everywhere.py`, tests existants adaptés)
- Deux installations en fixtures (bêta 1.60.1.70374, finale fictive 9.99.9.99999 adoptée) : la veille, l'archivage,
  `forever update` (`_step_game`), `forever builds` (produit demandé = `wow_fictif_finale`), `status` du pont et
  `profile import` lisent la finale ; le `DBCache.bin` de la bêta n'est jamais copié dans
  `dbcache/wow_fictif_finale/` et inversement ; à build égal (même numéro dans les deux), deux archives distinctes.
- `split_by_version` : journal de la bêta face aux données de la finale → retenu (« bêta ») ; accepté avec
  `--accept-version` et raison.
- `decode` d'une candidate tirée de la finale → `sources.json` porte `wow_fictif_finale`.
- Surveillance : choix changé jeu fermé → pont arrêté puis relancé sur le nouveau dossier, événement
  `autostart_wow_changed` ; jeu ouvert → rien avant fermeture. Tâche avec `--wow-dir` → dossier forcé gardé.
- `install_addon.py` et `forever bridge install` sans `--wow-dir` → installation choisie.
- `install_plugin.ps1 -Print` (Windows seulement, `skipif`) : propose le choix, ne change pas `FOREVER_WOW_DIR` sans
  accord.

### Bloc C (`test_toc_interface.py`, `test_addon_rules.py`)
- Ordre de lecture `_Forever`, `_Camelot`, `_Mainline`, sans suffixe sur une fixture à quatre `.toc`.
- `## Interface: 16001, 99999` accepté par `check_addon.py` si les deux sont dans la constante, refusé sinon.
- ForeverLogger : le client simulé (lupa) rend `GetBuildInfo` → l'instantané porte l'interface ; `doctor` compare.

### Bloc D (`test_doctor.py`, `test_doctor_cases.py`)
- Installation de fixture complète et saine (sondes simulées) → tous `ok`, code 0, aucune sonde réseau appelée
  (`FakeHttp.failing()` jamais touché, `pytest-socket`).
- **Cas réels** (un test chacun, constat et correction exacts) : Python de base sans paquets (`probe_environment`
  rend `ModuleNotFoundError: No module named 'yaml'`) → `env.python` `fail`, correction `uv sync` ; fichier
  `<cache>/bridge/environment.json` présent → `env.state` `fail` ; jeu sous `Program Files (x86)` et
  `FOREVER_WOW_DIR` vers l'ancien dossier → `wow.env` `fail` ; tâche du pont absente → `tasks.bridge` `fail` ; tâche
  avec `--wow-dir` vers l'ancien dossier → `fail` « à recréer » ; `gh --version` en `OSError` → `gh` `fail` (winget) ;
  `gh auth token` code 1 → `fail` (`gh auth login`) ; journal du pont avec `error` « OAuth session expired » après le
  dernier `reply` → `claude` `fail` (`claude` puis `/login`) ; `claude auth status` `loggedIn: false` → `fail` ;
  ForeverLogger absent → `fail` ; fichier de ForeverBridge différent du dépôt → `fail` ; réserve à 199 emplacements →
  `fail` ; profil absent avec une sauvegarde → `fail` avec `forever backup restore` ; antivirus → `unknown` ;
  sauvegardes sur le disque système → `warn` ; aucun journal de combat récent → `warn`.
- Sortie de `claude auth status` de fixture avec `email` et `orgName` → absents du JSON de `doctor`.
- Code 7 dès un `fail` ; `--json` valide (`validate_provenance`).
- `test_network_boundary.py` : `doctor_probes.py` ajouté à la liste ; `doctor.py` sans `subprocess`.

### Bloc E (`test_backup.py`)
- `backup_root` : `FOREVER_BACKUP_DIR` d'abord ; disques `C:` (système) et `D:` → `D:\WoW Forever\sauvegardes` ;
  seul `C:` + OneDrive connecté → OneDrive ; seul `C:` sans OneDrive → Documents + avertissement.
- Sauvegarde dans `tmp_path` : profil, deux SavedVariables, réglages du pont, attente → manifeste aux empreintes
  exactes ; 15e sauvegarde → la plus ancienne retirée (14 gardées) ; aucun `.credentials.json` copié.
- Restauration : jeu lancé → refus ; sans `--yes` → rien écrit ; avec `--yes` → l'état courant sauvegardé d'abord
  (une sauvegarde de plus, raison « avant restauration »), puis fichiers rendus identiques à ceux sauvegardés.
- Passage `update --auto` : jeu fermé et dernière sauvegarde de plus de 24 h → une sauvegarde ; jeu ouvert → aucune.

### Bloc F (`test_profile_archive.py`, `test_profile_import.py`)
- Profil schéma 3 de fixture → migré en 4, original sauvegardé ; `archive --product wow_classic_beta` → personnages
  de la bêta dans `archived_characters`, `use` refusé sur eux ; import d'un homonyme vu sous `wow_fictif_finale` →
  nouveau personnage actif possible, l'archivé intact.
- `forever measures inherited` sur une copie des données : PNJ hérités listés ; après `refresh` de la finale sur un
  journal de fixture, ce PNJ sort de la liste.

### Garde (`test_no_final_product_name.py`)
- Aucun nom de produit Forever autre que celui de `sources.json` dans `forever/`, `scripts/`, `addon/`, `plugin/`,
  `tests/` (hors ce test) : les produits non bêta du code sont la liste d'exclusion publique ; motifs interdits
  `wowf`, `_forever_`, `wow_classic_forever`, `wow_forever`.

## Registre (`docs/MECHANICS_REGISTRY.yaml`)
Aucune mécanique de jeu ajoutée ni modifiée (installation, outils et profil). Au bloc F, vérifier si l'entrée des
PV des monstres doit mentionner la règle « mesures de la bêta héritées, remplacées par les journaux de la version
finale » ; sinon rien.

## Questions ouvertes (`docs/OPEN_QUESTIONS.md`)
- **DON4** reformulée : produit de la version finale lu dans `.build.info`/`.flavor.info` et adopté le 4 novembre.
- **LN-1** : la version finale lit-elle encore les `.toc` sans suffixe et quel numéro d'interface rend-elle ?
  (relevé le 4 novembre, `docs/LANCEMENT.md`).
- **LN-2** : la version finale s'installe-t-elle à côté de la bêta (même racine) ou la remplace-t-elle ?
- **LN-3** : `claude auth status` détecte-t-il une session expirée sans réseau ? (relevé au bloc D, sinon journal
  seul).

## Hors périmètre
Contenu des données de la version finale (T08a, `forever update`) ; installation du jeu (Battle.net) ; écriture dans
la configuration du client ; lecture de `product.db` (réponse 4) ; exclusions de Defender posées par forever ;
vérification en ligne des jetons (`gh auth status`) ; contournements du bug supposé des SavedVariables de la bêta.

## Risques
- **Le produit final ne vient pas en `.flavor.info`** ou partage le dossier de la bêta : repli sur la ligne unique,
  sinon « produit illisible » et forçage par `FOREVER_WOW_FORCE` ; dit dans `docs/LANCEMENT.md`.
- **Même build dans les deux produits** : archives séparées par produit (bloc B), test dédié.
- **Changement de choix en pleine partie** : la surveillance attend la fermeture du jeu.
- **CI sous Ubuntu** : disques, tâches et Defender injectés ; tests Windows sous `skipif`.
- **Schéma 4 du profil** : migration sauvegardée d'abord ; MCP `forever_player_profile` et pont relus au bloc F.
- **Plan long pour une fenêtre courte** : ordre d'utilité ci-dessus ; un cycle rouge → vert par bloc, arrêt après
  un bloc vert si le contexte se remplit.
- `uv` et l'état de `.venv` : la forme exacte du contrôle « `.venv` suit `uv.lock` » sans lancer `uv sync` est à
  relever au bloc D ; à défaut, `warn` « non vérifiable sans `uv sync` » plutôt qu'un accès réseau.

## Point à confirmer à la validation du plan
Règle des disques pour les sauvegardes : appliquée telle quelle, elle choisit **D:** (« RPKrypto ») sur ce PC. Proposé :
préférer d'abord un disque fixe hors système dont le nom contient « sauvegarde » ou « backup » (ici **F:**), puis la
règle des lettres. À trancher en validant ; par défaut, la proposition.

## Critères de fin (LN1)
Sur fixtures de plusieurs installations (bêta seule, bêta et finale, finale seule, produit inconnu), la découverte
choisit la bonne, le forçage l'emporte, un produit inconnu est signalé sans être deviné ; aucun nom de produit final
dans le code ni les tests (test de garde) ; veille, archivage, mise à jour, tâches et pont pointent vers
l'installation choisie (tests sur deux installations) ; `forever doctor` rend chaque problème avec sa correction
(cas réels des décisions 241 et 257 compris), code 0 quand tout va bien, sans réseau ; sauvegarde puis restauration
d'un profil, de SavedVariables et des réglages du pont dans `tmp_path`, état courant gardé avant l'écrasement ;
personnages de la bêta archivés et import des nouveaux sur fixtures ; `docs/LANCEMENT.md` relu, une section par
PC ; `uv run tasks.py verify` vert ; CI verte sous Ubuntu et Windows.
