# Architecture

État réel du dépôt après le changement de cap des décisions 288 à 297. Les sources elles-mêmes (ce qu'elles
fournissent, licence, fraîcheur, relecture) sont décrites dans `docs/DATA_SOURCES.md` ; l'historique des choix dans
`docs/DECISIONS.md`.

## Principe : lire et alimenter ce qui existe
- **Deux questions avant tout chantier** (décision 288) : « qui maintient déjà ça mieux que nous ? » et « que se
  passe-t-il au prochain patch ? ». Ce qui casserait à chaque patch n'est pas construit : on lit le client, les addons
  de l'utilisateur, le simulateur de la communauté et les parcours maintenus, et on les alimente (exports).
- **Données réutilisées** : le client du jeu (tables, correctifs du serveur) est la vérité ; les addons installés
  passent avant toute fonction maison (décision 272) ; seuls des agrégats entrent dans le dépôt (décision 133).
- **Calculs réutilisés** (décision 293) : les calculs viennent des simulateurs maintenus par d'autres, par des
  adaptateurs minces, épinglés et tenus à jour par la veille ; plus aucun code de calcul qui recopie une mécanique ;
  le code redondant est gelé (moteur du Mage) ou retiré.
- **Forever seulement** (décision 294) : aucune donnée ni mécanique de Season of Discovery ou de la Classic. Les
  valeurs encore héritées de la Classic sont recensées et dites dans la provenance (`forever/classic.py`,
  `forever origins classic`).
- **Mise à jour automatique complète** (décision 295) : la veille installe d'elle-même, prévient (carte « Mis à jour »,
  `forever update status`) et se défait en un clic (`forever update undo <id>`).
- **Un cœur, plusieurs portes** : toute la logique vit dans le paquet Python `forever` ; la CLI, le serveur MCP, le pont
  en jeu et le plugin Claude Code l'appellent sans rien recalculer.

## Flux d'ensemble

```
 SOURCES MAINTENUES PAR D'AUTRES                  ADAPTATEURS MINCES                     DONNÉES ET ÉTATS
 ───────────────────────────────                  ──────────────────                     ────────────────
 wago.tools (tables CSV, builds) ───────┐
 WoWDBDefs (dispositions .dbd) ─────────┤
 DBCache.bin du jeu / Raidbots ─────────┼──► forever/pipeline/ (fetch, dbd, dbcache,     ┌► forever/data/<version>/
 Hotfix.log, questcache.wdb ────────────┤     raidbots, decode, install, verify…) ──────┤   (versionné, haché :
 journaux de combat, ForeverLogger ─────┘                                               │    manifest, origins,
                                                                                        │    sources, revisions)
 addons installés (Questie, Naowh, ─────────► forever/pipeline/*_sources.py, companion, ├► <cache>/ (hors dépôt :
 Forever Companion, Talents Forever…)          skillup, bestiary… (lecture sur disque)  │    livres fusionnés,
 RestedXP (parcours gratuits), Polestar ────► forever/rxp_guides.py, forever/polestar.py │    clones, binaires,
 wowsims/forever (Go, compilé tel quel) ────► forever/pipeline/wowsims_build.py ────────┘    fiches de la veille)
                                               forever/sims/ (requête, binaire, résultat)

                    forever/gamedata.py ─► forever/engine/ (moteur du Mage, gelé) ─► forever/sim/, forever/optimize/
                                                       │
     services (build, leveling, gear, route, lookup, pvp, pets, dungeons, quests, sims/report…) + provenance
                                                       │
            ┌──────────────────┬───────────────────────┼─────────────────────┬──────────────────────┐
         CLI `forever`     serveur MCP          pont en jeu (bridge)     plugin Claude Code     exports d'addons
         (forever/cli.py)  (mcp_server.py)      + addon ForeverBridge    (skills, hooks)        (forever/exports/)
```

La veille (`forever update`) relit chaque source maintenue par d'autres, installe ce qui change dans
`forever/data/` par un clone dédié et la CI, puis rejoue les conseils et le dit (section « Veille »).

## Arborescence réelle

```
forever/
├── data/<version>/            # une version du jeu par dossier, révisions numérotées (revisions.json)
├── data/manifest.json         # version courante, empreintes sha256 de chaque fichier
├── pipeline/                  # seul endroit qui touche Internet ; lecteurs du client et des addons
├── sims/                      # adaptateurs des simulateurs maintenus par d'autres (wowsims/forever)
├── exports/                   # chaînes d'import des addons (Naowh, EllesmereUI, Pawn, Talents Forever)
├── engine/                    # moteur du Mage en fonctions pures (gelé, décision 293) et règles neutres
├── sim/ , optimize/           # orchestration du moteur (leveling, rencontres, objectifs) et recherche de builds
├── bridge/                    # pont du chat en jeu (P06a, P06b)
├── update.py, update_installed.py, update_task.py, spawn.py, archive.py, carry.py, engine_inputs.py, replay.py
│                              # veille automatique
├── sources.py, origins.py, classic.py, registry.py, provenance.py, freshness.py, status.py, store.py,
│   manifest.py, gamedata.py   # registre des sources, origines, provenance, intégrité
├── build.py, leveling.py, gear.py, gear_route.py, route.py, route_check.py, rxp.py, rxp_guides.py, rxp_clean.py,
│   polestar.py, compare.py, travel.py, quests.py, dungeons.py, pets.py, pets_lookup.py, pvp.py, lookup.py,
│   xp_bonuses.py, xp_check.py, kill_time.py, talents_forever.py, tf_code.py, server_removed.py, simc.py
│                              # services communs à la CLI, au MCP et au pont
├── profile.py, profile_import.py, backup.py, installs.py, doctor.py, doctor_probes.py, addons.py, toc.py, watch.py
├── hooks.py                   # hooks du plugin
├── cli.py, mcp_server.py      # portes d'entrée
addon/ForeverLogger, addon/ForeverBridge   # nos addons (règles : docs/ADDON.md)
plugin/                        # plugin Claude Code mince (skills, agents, hooks, .mcp.json)
seed/forever-mage, seed/grimoire-engine    # code de référence en lecture seule (parité : tests/parity/)
tests/{unit,integration,parity,e2e,fixtures}/
.github/workflows/{ci.yml,build-watch.yml,notes-watch.yml,api-probe.yml}
```

## Adaptateurs minces
Un adaptateur lit une source telle qu'elle est publiée, sans recopier sa logique, rend une forme commune et porte la
provenance de la source (version, empreinte ou commit, date). Rien de ce qu'il lit n'entre dans le dépôt hors
agrégats.

- **Client du jeu** (`forever/pipeline/`) : `builds.py` (versions publiées, wago.tools), `fetch.py` (tables CSV,
  GameTables, `.dbd` de WoWDBDefs à commit épinglé), `tables.py` (lecture typée des CSV), `dbd.py` (dispositions),
  `dbcache.py` et `hotfix_overlay.py` (correctifs du serveur de `DBCache.bin`), `raidbots.py` (cache vérifié de
  Raidbots quand le jeu n'a pas d'archive du build, décision 290), `hotfixes.py` (`Hotfix.log`), `questcache.py`
  (`questcache.wdb`), puis les décodeurs : `decode.py`, `character_scaling.py`, `dungeons_client.py`, `pets.py`,
  `quest_rewards.py`, `travel_client.py`, `xp_bonuses.py`, `tooltip.py`. Toutes les constantes de lecture vivent dans
  `forever/data/<version>/decode_rules.json`.
- **Installation et contrôle** : `install.py` (révision suivante, règles de fusion), `observations.py` (écarts tranchés
  par la version, décisions 296 et 297), `verify.py`, `diff.py`, `value_diff.py`, `report.py`, `sources.py`
  (désignation d'une version ou d'une candidate), `gitops.py` (seul module qui lance git et `gh`),
  `http_client.py` (seul `urlopen` du paquet, contrôlé par `tests/unit/test_network_boundary.py`).
- **Journaux et sauvegardes du joueur** : `combatlog.py`, `measure.py`, `levels.py`, `live_logs.py`, `monsters.py`,
  `refresh.py`, `addon_sv.py` (ForeverLogger), `auctionator.py` et `cbor.py`, `lua_table.py` (tables Lua sans
  exécuter de Lua), `client_builds.py` (versions du client vues sur le poste).
- **Addons de l'utilisateur** (lecture sur disque) : `questie.py`, `quest_sources.py`, `dungeon_sources.py`,
  `gear_sources.py`, `companion.py`, `skillup.py`, `bestiary.py`, `talents_forever.py`, `sleeping_bag.py`,
  `travel_sources.py` ; recoupement : `factoruide.py`. Suivi des versions et empreintes : `forever/addons.py`
  (`DATA_ADDONS`, `EXCLUDED_ADDONS`, `OWN_ADDONS`, `NOT_ADDONS`).
- **Parcours de leveling** : `forever/rxp_guides.py` (parcours gratuits de RestedXP lus dans l'addon installé),
  `forever/polestar.py` et `forever/pipeline/polestar_fetch.py` (guides de Polestar dans un clone en cache,
  décision 289).
- **Simulateur** : `forever/pipeline/wowsims_build.py` (clone de wowsims/forever, génération protobuf, compilation de
  `wowsimcli`, épinglage `pin.json` : commit, date, empreinte, versions de Go et de protoc) et `forever/sims/`
  (`wowsims.py` : préréglages du dépôt épinglé, `RaidSimRequest` en protojson, lancement du binaire en local, lecture
  du résultat, cas de référence ; `report.py` : réponses de `forever sims` et `forever_simulate`).
- **Signaux officiels** : `notes.py` (forum de Blizzard, à la main), `blizzard_api.py` (sonde de l'API).
- **Exports** (`forever/exports/`) : `codec.py`, `naowh.py`, `naowh_keys.py`, `macros.py`, `talents.py`,
  `ellesmere.py`, `pawn.py`, `read.py` ; code de build de Talents Forever : `forever/tf_code.py`. Formats
  réimplémentés d'après leur description, jamais recopiés ; le joueur colle lui-même chaque chaîne.

## Données versionnées, origines et provenance
- **Un dossier par version** (`forever/data/<version>/`), révisé en place par numéro (`revisions.json`) ; une révision
  n'est jamais écrite à la main : `forever install` (ou la veille) installe une candidate décodée hors du dépôt.
- **Manifeste** (`forever/data/manifest.json`) : version courante, empreinte sha256 de chaque fichier, `data_sha`
  (préfixe de l'empreinte globale) ; déterministe, régénéré par `forever manifest --update` ou par l'installation
  (décision 263 : les règles d'une tranche écrites dans `decode_rules.json` avant le décodage sont admises par
  `forever install`). Tout outil qui lit les données refuse une empreinte qui ne correspond pas (`data_integrity`,
  code 3). `.gitattributes` fixe les octets pour que les empreintes soient les mêmes sous Windows et Linux.
- **`sources.json`** : pour chaque fichier, sa source, sa certitude (`certain`, `probable`, `suppose`), les
  certitudes et notes par champ, le bloc `hotfixes` des correctifs lus.
- **`origins.json`** (`forever/origins.py`, étape `origins` de `verify`) : chaque valeur des données a une origine
  déclarée par pointeur JSON parmi sept : `client`, `correctif_serveur`, `journal`, `addon`, `manuel`, `copie_figee`,
  `parametre` ; plafond de certitude par origine ; une valeur `manuel` exige une raison. Inventaire des valeurs écrites
  à la main : `forever origins inventory` (`docs/research/valeurs-ecrites-a-la-main.md`) ; valeurs héritées de la
  Classic : `forever origins classic`.
- **`confirmed_changes.json`** : écarts entre le décodage et la version installée, tranchés (par l'utilisateur, ou par
  la veille selon la règle de version des décisions 296 et 297, ou retraits par correctif du serveur, décision 290 :
  `forever/server_removed.py`).
- **Registre des mécaniques** (`docs/MECHANICS_REGISTRY.yaml`, `forever/registry.py`, `scripts/check_registry.py
  --strict`) : statut, certitude, sources, tests, preuves de journaux ; chaque fonction du moteur cite ses
  identifiants. `forever explain-mechanic` et `forever_explain_mechanic` en rendent une entrée avec les paramètres de
  la version.
- **Registre des sources** (`forever/sources.py`, plan « Sources d'abord », décision 291) : pour chaque domaine, chaque
  source dit si elle est à jour pour la version installée, par son **contenu** quand c'est possible (moteur du Mage :
  talent dont le texte du client n'a plus de règle de lecture ; Talents Forever et Forever Companion : talents sans
  correspondance) sinon par sa **date ou son build** (poids de Naowh, SkillUp Forever, commit épinglé de wowsims).
  `choose` prend la première source à jour et dit « calcul en cours de mise à jour » pour celles qu'il écarte ; sans
  source à jour, la meilleure, « antérieure au patch », jamais une panne. Lu par `forever status`, `build.py` et
  `lookup.py`.
- **Bloc `provenance`** (`forever/provenance.py`), dans chaque résultat d'outil (CLI, MCP, pont) :

  ```json
  {"provenance": {"game_version": "<version>", "data_sha": "<12 hex>", "generated_at": "<horodatage UTC>",
                  "freshness": "fresh|stale|unknown|silent", "certainty": "certain|probable|suppose",
                  "assumptions": ["…"], "registry_coverage": "<testées>/<total>"}}
  ```

  Les hypothèses portent les mentions obligatoires : moteur du Mage gelé, valeurs héritées de la Classic, source en
  retard, correctif lu chez Raidbots, commit et empreinte du binaire de wowsims, version et empreinte d'un addon lu.

## Moteur du Mage gelé et simulateur de la communauté
- **`forever/engine/`** : fonctions pures qui reçoivent `GameData` (`forever/gamedata.py`, seul module qui lit le JSON
  brut du moteur, après contrôle d'intégrité). Aucun chiffre de jeu dans le code. Le moteur du Mage est **gelé à la
  révision 7 de 1.60.1.70450** (décisions 293 et 294) : plus aucune mécanique ajoutée, recoupé par les journaux de
  combat ; chaque réponse qui l'utilise le dit (`MAGE_ENGINE_FROZEN` de `forever/sims/report.py`, repris par
  `build.py`, `leveling.py`, `gear.py`). Il reste le seul calcul sous le niveau 60 (leveling, builds par contexte,
  respec, profil PvP analytique).
- **Règles neutres** qui ne recopient aucune mécanique de classe et restent hors du gel : modèle d'XP (`xp.py`),
  trajets et routes (`travel.py`, `route.py`), passages de donjon et butin (`dungeon.py`, `loot.py`), rendements
  décroissants des fiches PvP (`diminishing.py`), poids par différences finies (`weights.py`).
- **Orchestration** : `forever/sim/` (Monte Carlo et analytique du leveling, scénarios de rencontre, objectifs par
  zone et donjon, écart avec un build de la communauté) et `forever/optimize/` (recherche des talents, décision
  appariée, respec, recherche de route portée de Factoruide). Ni formule ni chiffre ici.
- **wowsims/forever au niveau 60** (`forever/sims/`, `forever sims update | presets | races`, outil MCP
  `forever_simulate` : préréglages, races par paires, poids par tirages appariés, comparaison de classes) : binaire
  compilé chez nous depuis un commit épinglé, sans aucune modification, lancé en sous-processus local sans réseau,
  certitude `suppose`. `forever gear` prend ses poids au niveau 60 ; sous le 60, rien n'est demandé à wowsims.
- **Valeurs attendues des tests** : la suite lit une copie des données ramenée à `VALUES_VERSION`
  (`tests/conftest.py`, `pinned_data_dir`) ; seule `tests/unit/test_installed_invariants.py` lit la version réellement
  installée, et seulement pour des invariants.

## Veille entièrement automatique (`forever update`)
`forever/update.py` orchestre des fonctions existantes, sans calcul de combat ni module réseau propre (le réseau passe
par `forever/pipeline/` et un exécuteur injecté).

**Déclencheurs** (un seul passage à la fois, verrou `<cache>/update/`) :
- hook `SessionStart` du plugin (`forever/hooks.py`, `update.due`) : passage détaché si le dernier a plus de 6 h ;
- tâche planifiée « WoW Forever - mise à jour » chaque jour (`scripts/install_update_task.ps1`,
  `forever/update_task.py`, `pythonw.exe` sans fenêtre) ;
- le pont, quand le jeu se ferme ou écrit son `DBCache.bin` (`forever/bridge/updater.py`, `update.launch_pass`, hors
  de la règle des 6 h) ;
- à la main : `forever update [--auto] [--dry-run] [--no-network] [--only …]`.

**Étapes d'un passage** (`run_update`, chacune avec un délai maximal `STEP_LIMITS_S` : au-delà, le passage s'arrête
proprement et le dit) :

```
verrou → archivage → clone → jeu → nouvelle_version → correctifs → journaux → addons → guides → simulateurs → fin
```

| Étape | Ce qu'elle fait |
| --- | --- |
| `archivage` | copie `DBCache.bin`, `Hotfix.log` et `questcache.wdb` du client par build dans `<cache>/dbcache/<build>/` (`forever/archive.py`), avant que le client ne les réécrive |
| `clone` | clone dédié `<cache>/update/repo` remis sur `origin/main` ; l'arbre de travail de la session n'est jamais touché ; reprise d'une branche `data/…` restée en route |
| `jeu` | dernière version publiée du client (wago.tools) |
| `nouvelle_version` | téléchargement (trois essais par table, décision 230), décodage avec les correctifs du serveur, installation dans une copie de préparation, report des valeurs faites à la main (`forever/carry.py`), preuve d'entrées par moteur (`forever/engine_inputs.py`), écarts tranchés par la version (décisions 296 et 297), écriture |
| `correctifs` | nouveaux correctifs du serveur de la version installée (archive du jeu, sinon Raidbots) : révision suivante |
| `journaux` | mesure des journaux de combat de la version installée (journal en cours d'écriture remis au passage suivant) : révision suivante |
| `addons` | empreintes des addons suivis ; Questie changé relance la mesure des journaux, écrite d'elle-même ; un autre addon changé laisse un rappel de relecture en session, sans rien bloquer |
| `guides` | clone de Polestar remis sur son dernier commit, s'il existe |
| `simulateurs` | wowsims/forever recompilé au nouveau commit, s'il a déjà été compilé ; cas de référence rejoués, écarts notés dans `veille.json` |

**Écriture** (`_publish`, `forever/pipeline/gitops.py`) : branche `data/<version>-r<N>`, `tasks.py verify --data
--engines=<moteurs touchés>` dans le clone (la suite complète si autre chose que des données change), poussée, CI
attendue sous Ubuntu et Windows, puis `main` avancé en avance rapide sur `origin` (refusé si `main` a bougé), jamais
de poussée forcée. Le rapport de l'installation part dans `docs/research/data-<version>-r<N>.md`.

**Après l'installation** : fiche `<cache>/update/installed/<id>.json` (`forever/update_installed.py` : version,
révision, commit, ce qui a changé en mots de joueur, état) ; rejeu ciblé des builds du Mage **après** l'installation
(`forever/replay.py`, cas en cache par version, empreinte des données et empreinte du code, répartis sur les cœurs) qui
ne décide plus rien mais écrit les conseils changés sur la fiche ; carte « Mis à jour » du pont et ligne de
`forever update status`. **Annuler** : `forever update undo <id>` revient à la révision précédente par le même chemin
(`git revert` dans le clone, `verify --data`, branche `data/undo-<id>`, CI, avance rapide), même jeu fermé ; une
fiche annulée empêche la réinstallation du même contenu.

**Ce qui ne s'installe pas, et est dit** (attente visible par `forever update status`) : intégrité cassée (`verify`
rouge, écart de fusion que les décisions 296 et 297 ne tranchent pas, règles modifiées après le décodage, CI rouge),
source injoignable ou illisible (attente `network` levée seule au passage suivant), colonne renommée par le client
(`column_names`, session), dispositions WoWDBDefs absentes, valeur écrite à la main perdue, valeur de correctif du
serveur non relue. Une nouvelle version attend le `DBCache.bin` de son build (`hotfixes_unread`, levée seule), puis
s'installe sans correctifs après un délai si aucune valeur `correctif_serveur` n'est perdue.

**Délais réseau** (réglages de l'outil) : requête HTTP de `status` et `builds` (`HTTP_TIMEOUT`), table CSV
(`FETCH_TIMEOUT`, doublé à chaque essai), téléchargement de Raidbots (`raidbots.DOWNLOAD_TIMEOUT`), commande git de
Polestar (`STEP_GIT_TIMEOUT_S`), git et compilation de wowsims (`wowsims_build.GIT_TIMEOUT_S`, `TIMEOUT_S`), attente
de la CI (`UPDATE_CI_TIMEOUT`), attente du `DBCache.bin` (`UPDATE_HOTFIX_WAIT`). Un accès injoignable est noté sans
bloquer les étapes suivantes ; la copie précédente (clone, binaire) reste lue.

**Veilles hors du poste** (GitHub Actions) : `build-watch.yml` (chaque jour : nouvelle version publiée, décodage et
rapport en pull request, n'installe rien), `notes-watch.yml` (à la main), `api-probe.yml` (sonde quotidienne de l'API
Blizzard). `forever watch` est la veille locale hors ligne (build du client, addons, correctifs, journaux) : elle
signale, ne lance rien.

## Rapports de valeurs à la place des tests rouges (décision 288)
Une nouvelle version ne rend aucun test rouge : les tests de valeurs restent attachés à `VALUES_VERSION`. Elle produit
un **rapport des valeurs qui changent**, à valider : section « Valeurs changées » du rapport d'installation
(`docs/research/data-<version>-r<N>.md`, une ligne par valeur : classe, entité, champ, avant, après, par
`forever/pipeline/value_diff.py` et `diff.py`), conseils rejoués sur la fiche « Mis à jour », écarts de wowsims dans
`veille.json`. Monter `VALUES_VERSION` est un acte délibéré, fait après ce rapport, avec les attentes revues en une
fois. Une source en retard (registre des sources) donne « calcul en cours de mise à jour » dans la réponse, pas une
erreur.

## Fraîcheur et réseau
- `forever status` et `forever_status` (`forever/freshness.py`, `forever/status.py`) : version locale contre dernière
  version publiée (cache `<cache>/status.json`, relu au-delà de 6 h), intégrité, couverture du registre, registre des
  sources. Statuts : `fresh`, `stale` (plus récente publiée), `unknown` (aucune observation), `silent` (aucune
  nouvelle version depuis longtemps : possible changement de produit). `FOREVER_OFFLINE=1` ou `--offline` interdit
  tout appel.
- Accès réseau permis (liste fermée de `CLAUDE.md`, contrôlée par `tests/unit/test_network_boundary.py`) : wago.tools,
  WoWDBDefs, git et `gh` du clone dédié (décision 179), caches vérifiés de Raidbots (décision 290), clone de Polestar
  (décision 289), clone de wowsims/forever et modules Go (décisions 293 et 294), forum de Blizzard à la main
  (décision 148), API Blizzard (décision 149). Jamais dans les tests.

## Pont en jeu (`forever/bridge/`, addon `addon/ForeverBridge`)
Relie la fenêtre de l'addon ForeverBridge à une conversation Claude Code ; forever lui-même n'ouvre aucune connexion.
- **Jeu → pont** : l'addon dessine le message (contexte du personnage, question) en bande de pixels
  (`Message.lua`) ; `capture.py` la lit dans la seule zone client de la fenêtre du jeu au premier plan (`codec.py`,
  `record.py`, `fragments.py` pour les messages longs). Secours : boîte d'envoi des SavedVariables, lue au `/reload`.
- **Conversation** (`agent.py`, `prompt.py`, `plans.py`, `context.py`) : `claude -p` en `stream-json`, outils réduits
  aux skills et aux outils forever, seul serveur MCP `forever` ; contexte relié à nos données ; appel fixé par bouton.
- **Pont → jeu** (`slots.py`, `loop.py`, `status.py`, `cards.py`) : réserve d'emplacements `ForeverBridge_S001`…
  chargés à la demande ; cartes « À valider », « Mis à jour » (avec « Annuler ») et questions à choix (`choices.py`).
- **Actions sans le modèle** (`actions.py`, liste fermée) : commandes fixées de `forever update`, profil
  (`profile_gap.py`), exports (`exports.py`), métiers par SkillUp Forever (`professions.py`), équipement
  (`gear_level.py`), livraison des routes dans RestedXP (`guide_addon.py` en repli jeu fermé), conversation
  « addons » limitée au dossier de l'addon de l'utilisateur (`addons.py`).
- **Exploitation** : `forever bridge install | start | run | stop | status | ask | selftest | autostart | …` ; journal
  sans pixel (`journal.py`), verrou (`lock.py`), addon tenu à jour jeu fermé (`keeper.py`), démarrage à l'ouverture de
  session (`autostart.py`), passage de la veille à la fermeture du jeu (`updater.py`). Le pont ne recharge jamais seul
  son code : il se relance après une fusion.

## CLI, serveur MCP et plugin
- **CLI** (`forever/cli.py`) : sortie en français, `--json` pour une sortie structurée, dernière ligne : provenance ;
  codes de sortie stables (2 usage, 3 intégrité, 4 introuvable, 5 réseau). Groupes : consultation (`status`, `lookup`,
  `explain-mechanic`, `talents`, `pvp`, `pets`, `dungeon`, `quests`, `xp`), calcul (`build`, `sim`, `chart`, `gear`,
  `route`, `sims`), données (`builds`, `fetch`, `decode`, `install`, `diff`, `verify`, `report`, `manifest`,
  `hotfixes`, `origins`, `measures`, `monsters`, `logs`, `questie`, `addons`), veille (`update`, `watch`, `notes`,
  `api`), poste (`profile`, `bridge`, `export`, `doctor`, `backup`, `wow`), `mcp`, `hook`.
- **Serveur MCP** (`forever/mcp_server.py`, même cœur que la CLI ; une erreur métier revient comme résultat d'outil
  avec sa provenance) :

  | Outil | Rôle |
  | --- | --- |
  | `forever_status` | fraîcheur, intégrité, registre des sources, résumé de la veille |
  | `forever_lookup` | consultations par domaine (`kind` : sorts, talents des neuf classes, zones, quêtes, donjons, PvP, familiers, bonus d'XP, builds de Talents Forever, relecture d'un export…) |
  | `forever_player_profile` | profil du joueur, en lecture seule |
  | `forever_explain_mechanic` | entrée du registre et paramètres de la version |
  | `forever_sim_leveling` | temps par monstre et XP par heure (moteur du Mage gelé), objectifs par zone et donjon |
  | `forever_build` | build du Mage par contexte, avec lien Talents Forever |
  | `forever_simulate` | wowsims/forever au niveau 60, toutes classes |
  | `forever_gear` | poids et lignes d'import (moteur du Mage gelé, wowsims/forever au niveau 60), listes BiS et équipement de leveling lus dans les addons |
  | `forever_route` | feuille de route de leveling (quêtes fusionnées, parcours de RestedXP et de Polestar), aperçu et guide RestedXP |

- **Plugin Claude Code** (`plugin/`, installé par `scripts/install_plugin.ps1`, mode d'emploi `docs/USAGE.md`) :
  **mince**, aucun calcul ni chiffre de jeu (`scripts/check_game_numbers.py`). Skills `forever-router`,
  `forever-leveling`, `forever-mage`, `forever-builds`, `forever-pvp`, `forever-familiers`, `forever-donjons`,
  `forever-routes` ; sous-agents `forever-web-researcher` et `forever-sim-runner` ; hooks `SessionStart` (ligne de
  fraîcheur et lancement de la veille) et `Stop` (chiffres de jeu absents des résultats d'outils), logique dans
  `forever/hooks.py`. Version gardée par `plugin/.claude-plugin/fingerprint.json` ; évaluation sans modèle en CI
  (`tests/unit/test_plugin_evals.py`).

## Profil, mémoire et poste
- Profil joueur hors du dépôt (`forever/profile.py`, `FOREVER_PROFILE` ou `~/.forever/profile.json`), importé de
  ForeverLogger, des journaux, de Questie et d'Auctionator (`forever/profile_import.py`) ; chaque champ garde sa
  source et sa date. Les outils de calcul ne le lisent jamais d'eux-mêmes : l'agent le lit et passe les valeurs.
- Installations du client (`forever/installs.py`, `forever wow list | adopt | forget`), contrôle du poste sans réseau
  (`forever doctor`), sauvegarde de ce qui n'est pas sur GitHub (`forever backup`).

## Vérification
`uv run tasks.py quick` pendant le travail, `uv run tasks.py verify` avant chaque poussée (lint, typage, suite
complète, registre, chiffres, origines, intégrité), `uv run tasks.py e2e` pour le bout en bout de `forever update`
(CI simulée du clone comprise) ; la CI sous Ubuntu et Windows juge. Le clone de la veille lance `verify --data` sur
les seuls moteurs aux entrées changées (décision 206).
