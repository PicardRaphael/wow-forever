# T08a — Installer une nouvelle version du jeu, et veille automatique : plan

Tranche courte, à placer **avant PV1**. Demande de l'utilisateur du 2026-09-30, après la publication de
1.60.1.70124 et son analyse (`docs/research/data-1.60.1.70124.md`).

Elle prend à T08 le strict nécessaire : installer une **nouvelle version** (T06b n'installe qu'une **révision** de
la version courante) et la **veille planifiée**. Le reste de T08 (versions des addons par `forever addons status`,
`forever_diff_versions`, baisse ciblée de certitude, durcissement du pipeline) **reste en T08**.

## Questions décisives (réponse attendue avant l'exécution)

- **D1** — Installer 1.60.1.70124 alors qu'elle ne change **aucune** des 22 tables décodées ? Deux lectures
  défendables : installer pour que la fraîcheur repasse à `fresh` et que la provenance cite la version jouée (le
  client est déjà en 70124, mes journaux du 30/09 aussi) ; ou ne pas installer, puisque aucune valeur ne change, et
  garder 70009 jusqu'à une version qui bouge. **Proposition : installer**, parce que la fraîcheur `stale` fausse la
  certitude rendue par tous les outils et parce que l'attribution des mesures (bloc C) a besoin que la version
  installée soit celle du client.
- **D2** — `forever install --new-version` (une option de plus sur la commande existante) ou une commande séparée
  `forever promote` ? **Proposition : `forever install --new-version`**, parce que les règles de fusion et le
  rapport sont les mêmes ; seul l'emplacement d'écriture change.
- **D3** — La veille ouvre-t-elle une PR **par version** (branche `data/<version>`, réouverte tant que la version
  n'est pas installée) ou une PR unique mise à jour ? **Proposition : une PR par version**, pour garder la trace de
  chaque publication même si plusieurs paraissent avant que tu n'installes (70058 puis 70124 en deux jours).
- **D4** — La veille doit-elle échouer bruyamment quand `forever verify` de la candidate est rouge, ou ouvrir la PR
  en signalant l'échec dans le rapport ? **Proposition : ouvrir la PR quand même**, avec l'échec en tête du
  rapport : une version qui casse le décodeur est précisément celle qu'il faut voir.

## Contexte

| Fait | Où |
| --- | --- |
| 1.60.1.70124 publiée le 2026-09-30T01:57:04Z ; 1.60.1.70058 le 2026-09-29T16:41:04Z | `forever builds` |
| Les 22 tables téléchargées sont identiques entre 70009 et 70124 ; 0 talent, 0 sort changés | `docs/research/data-1.60.1.70124.md` |
| Le client de ce PC est **déjà en 70124** depuis le 2026-09-30 07:46:25 (+0200) | `.build.info`, `WowB.exe` |
| 2 journaux sur 8 (11 260 événements) ont été écrits sous 70124 | même rapport |
| `forever install` n'écrit **que** dans `forever/data/<version courante>/` | `forever/pipeline/install.py`, docstring |
| `forever decode` n'écrit pas `_seed_*.json`, `_source_gunba_mage_tree.json`, `confirmed_changes.json`, `revisions.json` | `forever diff` : 5 « fichiers retirés » |
| `forever measures refresh` écrit dans `data_dir / new["game_version"]` sans jamais noter le build du client mesuré | `forever/pipeline/refresh.py` |
| `forever logs scan` rend `build: "1.60.1"` : l'entête du journal est tronquée, inutilisable pour attribuer | `docs/research/data-1.60.1.70124.md` |
| `tests/golden/` **n'existe pas encore** : aucune zone protégée à toucher dans cette tranche | `find tests -iname '*golden*'` |
| 81 références à `FC-70009` ou `1.60.1.70009` dans le registre | `docs/MECHANICS_REGISTRY.yaml` |
| Les occurrences de `1.60.1.70009` dans le code sont des exemples d'aide (`--version`), pas des valeurs | `forever/cli.py`, `decode.py`, `fetch.py` |
| Le mode auto ne peut pas écrire dans `.github/workflows` ; précédent : un patch dans `tasks/` | `tasks/plugin-eval.patch` |

### Ce que la certitude `FC-70009` devient

Une certitude `FC-<build>` nomme **le build où la valeur a été lue**, pas la version installée. Les 22 tables étant
identiques, les 81 références `FC-70009` du registre **restent vraies** après l'installation de 70124 : rien à
renommer. La tranche doit seulement s'assurer que rien dans le code ne suppose que `FC-<build>` égale la version
courante.

## Blocs et étapes

### Bloc A — Installer une nouvelle version (`forever install --new-version`)

Tests d'abord, sur fixtures, puis implémentation.

1. `forever install --new-version <candidate>` crée `forever/data/<nouvelle version>/` :
   - fichiers décodés écrits par `forever decode` : `talents.json`, `spells.json`, `spell_scaling.json`,
     `decode_rules.json`, `meta.json` ;
   - **copies figées reportées** de la version précédente : `_seed_spells.json`, `_seed_talents.json`,
     `_source_gunba_mage_tree.json` (le mode `rules=seed` doit continuer de rendre les mêmes valeurs) ;
   - **fichiers non décodés reportés** : `leveling.json`, `mechanics.json`, `monsters.json`, `racials.json`,
     `respec.json`, `overrides.json`, chacun avec, dans `sources.json`, la mention `hérité de <version précédente>`
     et sa date ; `forever verify` continue de les signaler « à revérifier » ;
   - `confirmed_changes.json` reporté, `version` mis à la nouvelle, chaque entrée gardant son
     `applied_in_revision` d'origine et recevant `carried_from: <version précédente>` ; une entrée dont l'écart a
     disparu du nouveau décodage est listée dans le rapport, jamais supprimée en silence ;
   - `revisions.json` neuf : révision **1**, motif, commande, empreinte de la candidate, rapport ;
   - `sources.json` reporté, chaque source gardant sa date d'origine.
2. `forever manifest --update` : `game_version` mis à la nouvelle version, empreintes de tous les fichiers,
   l'entrée de l'ancienne version **gardée** (`forever/data/manifest.json` indexe déjà par version).
3. La fraîcheur repasse à `fresh` : `forever status` ne signale plus de retard.
4. Accord demandé avant toute écriture (`--dry-run`, `--yes`), comme `forever install` aujourd'hui.
5. Rapport Markdown écrit hors des données (`--report`), même forme que `docs/research/data-1.60.1.70009-r2.md`.
6. **Arrêt obligatoire** : si `tests/golden/` existe au moment de l'exécution et qu'une installation le modifie,
   s'arrêter et demander l'accord (`CLAUDE.md`, zones protégées). Aujourd'hui ce dossier n'existe pas.

### Bloc B — Installer 1.60.1.70124 (si D1 = oui)

1. `forever fetch`, `forever decode`, `forever verify` : déjà faits le 2026-09-30, candidate en cache
   (données `66be48468707`).
2. `forever install --new-version <candidate> --report docs/research/data-1.60.1.70124-install.md`.
3. Contrôles attendus, tous **sans changement de valeur** puisque les tables sont identiques :
   - `forever diff 1.60.1.70009 1.60.1.70124` : 0 talent, 0 sort, 0 fichier retiré (les 5 « retirés » du rapport
     d'analyse disparaissent, c'est le critère qui prouve que le bloc A fait son travail) ;
   - parité du seed (`tests/parity/`) verte **sans qu'aucune valeur attendue ne change** ;
   - builds de T05 rejoués (`scripts/replay_builds.py`) : identiques au rejeu de T06b
     (`docs/research/builds-T05.md`, section « Rejeu T06b ») ;
   - `forever status` : fraîcheur `fresh`, registre 37/108 inchangé.
4. Fixtures et documents qui nomment la version courante mis à jour (les fixtures `tests/fixtures/` gardent leur
   version d'origine : ce sont des relevés datés, pas la version courante).

### Bloc C — Une mesure n'est jamais attribuée à la mauvaise version

C'est la règle que tu as posée : « ne jamais attribuer à 70009 une mesure faite sous 70124 ». Elle n'a aucun
garde-fou aujourd'hui.

1. **Journal des versions du client**, `<cache>/client_builds.json` (état de l'outil, hors `forever/data/`),
   en ajout seulement : `{build, installed_at, source}` où `build` vient de `.build.info` (champ `Version`) et
   `installed_at` de la date de modification de `.build.info`. Écrit à chaque `forever logs scan`, `logs measure`
   et `measures refresh`. **Raison** : `.build.info` et `WowB.exe` sont écrasés à la mise à jour suivante ; sans ce
   journal, l'instant de la mise à jour est perdu pour toujours.
   Première entrée à écrire à la main dans cette tranche, depuis le relevé du 2026-09-30 :
   `1.60.1.70124`, installée le `2026-09-30T07:46:26+02:00` ; et `1.60.1.70009`, bornée par le rapport d'erreur du
   2026-09-25 13:45 et la publication de 70058 le 2026-09-29 18:41 (local).
2. **Attribution par session**, jamais par fichier : un `WoWCombatLog-*.txt` peut chevaucher une mise à jour.
   Chaque session découpée par `forever logs scan` reçoit la version du client en vigueur à son instant de début,
   lue dans `client_builds.json`. L'entête du journal (`BUILD_VERSION 1.60.1`) reste affichée mais n'est jamais
   utilisée pour attribuer : elle est tronquée.
3. **`forever measures refresh` ne mesure que ce qui correspond** : les sessions dont la version vaut la version
   installée. Les autres sont listées dans la sortie comme « en attente de l'installation de `<version>` », avec
   leur nombre d'événements ; elles ne sont jamais écrites.
4. **Report d'une mesure d'une version à l'autre** : `monsters.json` reporté par le bloc A garde dans
   `sources.json` la mention `mesuré sous <version d'origine>`. Une valeur mesurée sous 70009 et reportée dans
   70124 ne devient pas « mesurée sous 70124 ».
5. **Même règle pour le profil** : les instantanés de ForeverLogger portent une date ; l'import de profil de PV1
   doit leur attacher la version du client de la même façon (un personnage a des instantanés sous 70124 depuis le
   2026-09-30 09:06). Cette tranche **fixe la règle et l'expose** (`client_builds.json`, fonction de résolution
   date → version, dans `forever/pipeline/`) ; PV1 la consomme sans avoir à la réinventer.

### Bloc D — Veille automatique (patch `tasks/T08a-build-watch.patch`)

Le mode auto ne pouvant pas écrire dans `.github/workflows`, le workflow est livré en patch, **à appliquer par
toi** (`git apply tasks/T08a-build-watch.patch`).

`.github/workflows/build-watch.yml`, quotidien (`schedule: cron` + `workflow_dispatch`) :

1. `uv run forever builds --json` : dernière version publiée contre `game_version` de `forever/data/manifest.json`.
2. Égales : le travail s'arrête, aucune PR.
3. Plus récente : `forever fetch`, `forever decode`, `forever verify` (échec **non bloquant**, repris dans le
   rapport, D4), `forever diff`, `forever report`.
4. **Le rapport est committé**, sinon il n'y a rien à mettre dans la PR : la candidate vit dans le cache, hors du
   dépôt, donc `fetch`/`decode`/`diff` ne changent **aucun fichier suivi** et `create-pull-request` ne ferait rien.
   Le workflow écrit `docs/research/data-<version>-candidate.md` (sortie de `forever report`) et
   `tasks/veille/<version>.json` (résumé : version, date de publication, compte des changements, résultat de
   `verify`, empreintes des tables changées).
5. PR sur la branche `data/<version>`, titre `data: <version installée> → <version publiée>`, corps = le rapport.
   Branche fixe : un deuxième passage le lendemain met la PR à jour au lieu d'en ouvrir une seconde.
6. **Rien n'est installé** : ni `forever install`, ni écriture dans `forever/data/`. L'installation reste ta
   décision (tu l'as demandé explicitement). Un contrôle du workflow le vérifie : `git diff --exit-code -- forever/data`.
7. Alerte `silent` : si `forever builds` ne voit aucune version nouvelle depuis plus de 14 jours
   (`SILENT_AFTER` existe déjà dans `forever/config.py`), le travail ouvre ou met à jour une *issue*, sans PR.
8. Réseau : `forever builds` et `forever fetch` uniquement, déjà dans la liste réseau de `CLAUDE.md`. Aucun nouvel
   accès, donc aucun arrêt pour accord à ce titre.
9. Les addons **ne sont pas couverts** par la veille de CI : ils vivent sur ton poste, pas sur le serveur
   (décision 124). `forever addons status` reste en DJ1, son automatisation en T08.

### Bloc E — Routeur du plugin : proposer l'analyse quand la fraîcheur est en retard

Dans `plugin/skills/forever-router/SKILL.md`, à la suite de la consigne existante sur `forever_status`
(lignes 20 à 22), ajouter, **sans aucun chiffre de jeu** :

> - Fraîcheur `stale` au premier appel de `forever_status` : le dire en une ligne (version des données, version
>   publiée) et **proposer** de lancer l'analyse de la nouvelle version — téléchargement des tables, décodage en
>   version candidate, vérification, comparaison et rapport. Ne rien lancer sans accord : l'accès réseau et
>   l'installation se demandent. Tant que l'accord n'est pas donné, répondre normalement avec les données
>   installées, en gardant la mention du retard dans la provenance.

Version du plugin portée à 0.4.3, empreinte régénérée (`scripts/plugin_fingerprint.py`), `plugin.json` et
`validate --strict` verts. Un cas d'évaluation ajouté : question ordinaire, données `stale`, la réponse propose
l'analyse **et** répond quand même.

## Fichiers

| Fichier | Changement |
| --- | --- |
| `forever/pipeline/install.py` | `--new-version` : nouveau dossier, report des copies figées et des fichiers non décodés, `revisions.json` neuf |
| `forever/pipeline/refresh.py` | filtre par version du client, mention `mesuré sous <version>` dans `sources.json` |
| `forever/pipeline/combatlog.py` (ou `measure.py`) | version du client par session |
| `forever/pipeline/` (nouveau) | `client_builds.json` : lecture de `.build.info`, journal en ajout, résolution date → version |
| `forever/cli.py` | option `--new-version` ; version du client dans les sorties de `logs scan` et `measures refresh` |
| `forever/data/1.60.1.70124/` | créé par le bloc B |
| `forever/data/manifest.json` | `game_version` à 1.60.1.70124 |
| `plugin/skills/forever-router/SKILL.md`, `plugin/.claude-plugin/plugin.json` | bloc E, version 0.4.3 |
| `tasks/T08a-build-watch.patch` | workflow, à appliquer à la main |
| `docs/ROADMAP.md`, `docs/DECISIONS.md`, `docs/ARCHITECTURE.md` | tranche T08a, décisions 134 et 135, `client_builds.json` dans le cache |
| `docs/research/data-1.60.1.70124-install.md` | rapport d'installation (bloc B) |

## Tests attendus

Valeurs tirées du rapport `docs/research/data-1.60.1.70124.md` et des fixtures, jamais écrites de mémoire.

| Test | Attendu |
| --- | --- |
| `install --new-version` sur une candidate de fixture | nouveau dossier créé, `_seed_*.json` et `confirmed_changes.json` présents, `revisions.json` en révision 1 |
| `diff` entre l'ancienne version et la nouvelle installée | **0 fichier retiré** (critère du bloc A) |
| `install --new-version` sans accord | rien écrit, code de sortie d'un refus |
| parité du seed après installation | verte, aucune valeur attendue modifiée |
| `client_builds.json` | deux mises à jour successives : une session entre les deux reçoit la bonne version |
| session à cheval sur une mise à jour (fixture) | découpée, chaque moitié sur sa version |
| `measures refresh` avec une session d'une autre version | la session est listée « en attente », rien n'est écrit |
| `monsters.json` reporté | `sources.json` dit `mesuré sous <version d'origine>` |
| `build-watch` simulé (version fictive plus récente, réseau en fixture) | rapport écrit, résumé JSON écrit, PR préparée, `forever/data/` **inchangé** |
| `build-watch` sans nouvelle version | aucune écriture, aucune PR |
| `build-watch` avec `verify` rouge | PR quand même, échec en tête du rapport |
| plus de 14 jours sans version | alerte `silent` |
| routeur, données `stale` | l'évaluation voit la proposition d'analyse **et** une réponse normale |

## Hors périmètre (reste en T08)

- `forever addons status` et le suivi automatique des versions d'addons (DJ1 pour la commande, T08 pour l'automatisation).
- `forever_diff_versions` (outil MCP).
- Baisse ciblée de la certitude des entités touchées par un diff quand le statut est `stale` (décision 19).
- Durcissement du pipeline relevé à la relecture de T03 (`$d` dans les `${…}`, sort cité deux fois par une
  infobulle d'aura 226, `SpellLevel` non lu, `--locale` sans `--tables`, CSV réduit à son en-tête,
  `rank_format` supposant `level` en tête).
- `DBCache.bin` et les correctifs serveur : `Logs/Hotfix.log` montre 4 386 objets et 1 sort surchargés le
  2026-09-30, aucun sort de classe. Les lire reste en T08.
- Décodage de 1.60.1.70058 (sautée).

## Risques

| Risque | Parade |
| --- | --- |
| Installer une version qui ne change rien donne l'illusion d'un travail fait | Le rapport d'installation dit explicitement « 0 valeur changée » ; `revisions.json` porte le motif « fraîcheur et alignement sur le client joué » |
| Les fichiers non décodés (`leveling.json`, `monsters.json`, `racials.json`…) sont reportés sans être revérifiés | `forever verify` les signale déjà ; `sources.json` porte `hérité de <version>` et sa date ; la certitude n'est pas relevée |
| La veille ouvre une PR vide et devient du bruit | Le rapport et le résumé JSON sont committés (bloc D, point 4) ; branche fixe par version |
| Une version paraît pendant l'exécution de la tranche | La chaîne est rejouable : `fetch`, `decode`, `verify`, `diff`, `report` sur la nouvelle |
| `client_builds.json` perdu (cache effacé) | Journal en ajout, reconstructible depuis `.build.info` pour la version courante ; les versions antérieures deviennent `suppose`, ce que la sortie doit dire |

## Critères de fin

- `forever install --new-version` testé sur fixtures ; `forever diff` entre les deux versions installées ne montre
  **aucun fichier retiré**.
- 1.60.1.70124 installée (si D1 = oui), `forever status` en `fresh`, parité du seed verte sans valeur attendue
  changée, builds de T05 rejoués identiques.
- Une mesure faite sous une version n'est jamais écrite dans les données d'une autre : test sur fixtures, sortie
  explicite pour les sessions en attente.
- `tasks/T08a-build-watch.patch` appliqué par l'utilisateur, `build-watch.yml` simulé en test (version fictive →
  rapport, résumé, PR, `forever/data/` inchangé), alerte `silent` après 14 jours.
- Routeur : proposition d'analyse quand la fraîcheur est en retard, plugin 0.4.3, `validate --strict` vert.
- `uv run tasks.py verify` vert.

## Validation

En attente : réponses à D1, D2, D3, D4.
