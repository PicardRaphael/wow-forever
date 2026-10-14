# Mode d'emploi du plugin forever

Poser ses questions sur World of Warcraft: Forever en langage naturel, depuis n'importe quel dossier, avec des
réponses sourcées par les outils du dépôt. Le plugin ne calcule rien : il aiguille vers le serveur MCP `forever`.

## Installation
Sur chaque PC (Windows), une fois :

1. Prérequis : [Git for Windows](https://git-scm.com/download/win) (il fournit aussi le bash des hooks),
   [uv](https://docs.astral.sh/uv/getting-started/installation/) et Claude Code (`claude`).
2. Cloner le dépôt, puis, **depuis sa racine**, dans PowerShell :

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1
   ```

   `-ExecutionPolicy Bypass` contourne la politique d'exécution des scripts pour ce seul lancement (sans rien changer
   au réglage de Windows). Client installé ailleurs que dans Program Files : ajouter `-WowDir "<dossier du client>"`.
3. Ouvrir un **nouveau** terminal (les variables d'environnement n'arrivent que dans les nouveaux terminaux).

Ce que fait le script (relançable sans risque) :
- fixe la variable d'environnement utilisateur `FOREVER_HOME` (le dépôt) ;
- `uv sync`, puis fixe `FOREVER_WOW_DIR` sur l'installation que choisit `forever wow list` (LN1), en demandant
  l'accord avant de remplacer une autre valeur (`-Print` : afficher le choix sans rien changer) ;
- déclare la marketplace locale `wow-forever` (le dépôt) et installe le plugin `forever@wow-forever` en portée
  utilisateur ;
- contrôle : `claude plugin validate --strict` (plugin versionné : la mise à jour recopie le plugin quand la version
  de `plugin.json` change), `forever status --offline`, plugin présent et activé.

Second PC : même procédure. L'addon ForeverLogger s'installe à part : `uv run python scripts/install_addon.py`
(il vise l'installation choisie par `forever wow list`, ou `--wow-dir`).

## Installations, diagnostic et sauvegardes (LN1)
Pas-à-pas du lancement du 4 novembre, sur chaque PC : `docs/LANCEMENT.md`.

- `forever wow list [--json]` : installations du client trouvées (racines usuelles de chaque disque fixe, parents
  de `FOREVER_WOW_DIR` et `FOREVER_WOW_FORCE`, `FOREVER_WOW_ROOTS`), leur rôle (`bêta`, `version finale`, `autre
  jeu`, `inconnu`), produit (lu dans `.flavor.info` et `.build.info`, jamais déduit du nom du dossier), version,
  exécutable, et l'installation lue avec sa raison. Choix : `--wow-dir`, puis `FOREVER_WOW_FORCE`, puis la version
  finale adoptée la plus récente, puis la bêta, puis `FOREVER_WOW_DIR`.
- `forever wow adopt <dossier> [--yes]` : inscrit **une fois** le produit d'un dossier comme version finale (journal
  des versions du cache, sauvegarde faite avant) ; refuse la bêta, un produit public connu ou un produit illisible.
  `forever wow forget <produit>` retire l'adoption.
- `forever doctor [--json]` : contrôle toute l'installation sans réseau, une ligne par contrôle (`[ok]`, `[!]` à
  corriger, `[x]` bloquant, `[?]` non vérifiable, `[i]` information) et la correction en dessous ; code 7 dès un
  bloquant. Contrôles : `repo`, `env.python`, `env.state`, `env.uv`, `wow.installs`, `wow.choice`, `wow.unknown`,
  `wow.env`, `wow.paths`, `addons.logger` (dont l'interface vue en jeu par ForeverLogger 0.7.0), `addons.bridge`,
  `combatlog`, `addons.data`, `env.vars`, `gh` (jeton présent, validité non contrôlée), `claude` (`claude auth status`
  réduit à `loggedIn` et `authMethod`, et erreurs d'authentification du journal du pont), `tasks.bridge`,
  `tasks.update`, `bridge.running`, `bridge.journal`, `profile`, `backup`, `antivirus` (toujours `[?]`),
  `info.sv_bridge`.
- `forever backup [--reason …]`, `forever backup list`, `forever backup restore [<date>] [--only profile|wtf|bridge|update|cache] [--yes]` :
  sauvegarde de ce qui n'est pas sur GitHub (profil, SavedVariables et `Config.wtf`, réglages et conversation
  « addons » du pont, attentes de `forever update`, journal des versions, dernier instantané des mesures ; jamais un
  jeton), dans `<racine>\<date>` avec `manifest.json`, 14 gardées. Racine : `FOREVER_BACKUP_DIR`, sinon un disque fixe
  hors système (d'abord celui dont le nom contient « sauvegarde » ou « backup »), sinon OneDrive connecté, sinon
  Documents (avertissement). Sauvegarde du jour au passage automatique de `forever update` (jeu fermé), avant
  `forever wow adopt` et avant toute restauration. La restauration exige le jeu fermé et l'accord, et sauvegarde
  l'état courant d'abord.
- `forever profile archive --product <produit> [--yes]`, `forever profile list --archived` : personnages d'un
  produit (la bêta au lancement) rangés à part, gardés, plus jamais actifs ; un homonyme de la version finale est un
  nouveau personnage. `forever profile import` lit tous les comptes de l'installation.
- `forever measures inherited [--version …] [--json]` : PV encore hérités de la version précédente (la bêta), qui
  sortent de la liste une fois remesurés par les journaux de la version finale. Un journal d'un autre produit que
  celui des données n'est jamais mesuré sans `--accept-version`.
- Variables : `FOREVER_WOW_DIR` (installation lue, fixée par le script d'installation), `FOREVER_WOW_FORCE` (dossier
  forcé), `FOREVER_WOW_ROOTS` (racines « World of Warcraft » de plus, séparées par `;`), `FOREVER_BACKUP_DIR`,
  `FOREVER_CACHE_DIR` (cache, défaut `~\.cache\forever`), `FOREVER_PROFILE` (profil, défaut
  `~\.forever\profile.json`), `FOREVER_HOME` (dépôt).

## Mise à jour
```powershell
git pull
powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1
```
Le script refait `uv sync`, met à jour la marketplace et recopie le plugin (`claude plugin update`). Redémarrer
Claude Code ensuite.

L'environnement ne se synchronise que par un `uv sync` explicite (ce script, ou à la main) : le serveur MCP du
plugin, celui du chat en jeu et les hooks tournent avec `uv run --no-sync … python -m forever …` (plugin 0.8.2), sans
jamais tenir `.venv\Scripts\forever.exe`. Un `uv sync` passe donc même avec Claude Code ouvert ou le pont lancé. Une
seule fois, pour passer du plugin 0.8.1 à 0.8.2 : fermer les sessions Claude Code, puis lancer le script ci-dessus.

## Veille locale (T08b)
`uv run forever watch` (hors ligne) compare le poste au dernier passage : build du client (`.build.info`), addons de
données (empreintes), correctifs du serveur (`Logs/Hotfix.log`), nouveaux journaux de combat et sauvegardes d'addons.
Elle **ne lance rien** : chaque changement est suivi des commandes proposées, marquées « réseau, sur accord » quand
elles touchent Internet (`forever notes` est proposé quand le build change, décision 148). Détail des briques :
`forever addons status [--save]`, `forever hotfixes [--since-install]`. `forever addons status` et `forever update`
ne comptent jamais nos propres addons (ForeverLogger, ForeverBridge, ses emplacements et ses sondes,
RaphCompletionist : une ligne « Addons du projet (ignorés) ») ni RXPGuides (connu, exclu) parmi les addons à
inventorier ; ForeverCompletionist n'est jamais lu comme un addon (décision 227).

### Correctifs du serveur (T08c)
```powershell
uv run forever hotfixes                                   # Hotfix.log et DBCache.bin : comptes, recoupement
uv run forever hotfixes --values                          # chaque valeur corrigée, avant et après, entités touchées
uv run forever fetch --version 1.60.1.70170 --dbd         # définitions de WoWDBDefs (réseau, sur accord)
uv run forever decode --version 1.60.1.70170 --hotfixes   # candidate avec les valeurs des correctifs
uv run forever diff 1.60.1.70170 <candidate>              # valeurs changées, attribuées à leur correctif
```
`--dbcache <chemin>` lit un autre `DBCache.bin` (copie gardée d'un build précédent) ; `--dbd-layouts <json>` des dispositions dérivées. `forever watch` signale les correctifs non appliqués à la révision installée.

`uv run forever notes --post 2360696/3` (réseau, sur accord) lit un seul message officiel désigné (sujet/numéro),
avec son numéro de révision dans la provenance ; ni limite quotidienne ni état de la veille touchés, message de
joueur refusé, texte rendu pour la lecture seulement.

La veille quotidienne planifiée fait partie du passage de la tâche « WoW Forever - mise à jour » (section
suivante) ; l'ancienne tâche « WoW Forever - veille locale » (`forever watch --report`, qui ne faisait que regarder)
est retirée par son script.

## Mise à jour automatique des données (T08d)
`forever update` enchaîne, sans session manuelle : archivage de `DBCache.bin` et `Hotfix.log` par build, clone dédié
du dépôt (`<cache>/update/repo`, jamais l'arbre de la session), nouvelle version du client publiée sur wago.tools,
correctifs du serveur de l'archive, journaux de combat de la version installée, addons de données. Une écriture
(branche `data/<version>-r<N>`, CI Ubuntu et Windows, avance rapide de `main`) ne se fait que si `verify` est vert,
si aucune valeur faite à la main n'est perdue ni remplacée et si les entrées de chaque moteur qui calcule (builds
et leveling du Mage) sont identiques (décision 180) ; les fiches PvP, recopiées du client, s'installent seules quand
seules changent des valeurs du client ou d'un correctif du serveur, avec un résumé (« fiches PvP : Warrior, … »)
dans la ligne de démarrage, `forever update status` et le rapport (décisions 198 et 207) ; sinon une attente
d'accord est enregistrée. Quand les entrées d'un moteur changent, l'attente porte le rejeu des builds du Mage : « avant » sur la version installée, « après » sur la candidate installée dans la copie de préparation (ou, si les règles de fusion la refusent, dans un aperçu où les écarts refusés sont acceptés) ; un rejeu dont les deux côtés portent les mêmes données est refusé et bloque l'attente (décision 216). Une nouvelle version attend que le jeu ait tourné sur son build (`DBCache.bin` archivé :
attente « correctifs à lire », levée seule, non approuvable) ; 24 h après la première vue du build, elle s'installe
sans ses correctifs seulement si aucune valeur d'un correctif du serveur n'est perdue (décision 207). Réseau accordé par la décision 179 (wago.tools,
WoWDBDefs, git et `gh` du clone).
```powershell
uv run forever update --dry-run              # tout calculer, ne rien écrire (rejeu des builds listé, non calculé)
uv run forever update                        # passage complet ; code 6 s'il reste une attente
uv run forever update --only jeu,correctifs  # étapes : jeu, correctifs, journaux, addons ; --no-network : hors ligne
uv run forever update status                 # attentes ouvertes et dernier passage ; --all : historique complet
uv run forever update approve <id>           # approuver (base inchangée), passage lancé en arrière-plan ; --wait
uv run forever update reject <id> --reason "…"
uv run forever update done <id> --note "…"      # clore une relecture faite en session (données d'addon, colonnes ; décision 244)
uv run forever addons inventory <dossier>    # métadonnées et empreintes d'un addon, sans aucune valeur
```
Au démarrage d'une session dans le dépôt, le hook archive les fichiers du client et lance `forever update --auto`
en arrière-plan (au plus toutes les 6 h, ou tout de suite si l'archivage vient de copier un `DBCache.bin`, jamais si un
passage tourne, décision 227) ; la ligne de démarrage montre les attentes et
propose `git pull` quand `main` distant a reçu des données. Une attente `bloqué` (verify rouge, installation refusée
par les règles de fusion, valeur perdue) n'est pas approuvable : elle demande une session. Une colonne renommée par
le client (aucun de ses noms dans le CSV) donne une attente `column_names`, avec le nom proposé : elle se traite en
session (ajouter le nouveau nom en tête de la liste, `forever/pipeline/tables.py` et `decode_rules.json`) et
`approve` la refuse (décision 185). Garde-fou (décision 184) : tant qu'aucun passage réel n'a été approuvé, la
première écriture de `forever update --auto` reste en attente de `forever update approve <id>`. Une attente de
mesure (`measures`) porte son résumé dans `forever update status` : PNJ ajoutés et changés (PV par niveau), retirés,
nouvellement écartés de la courbe avec leur raison, niveaux dont les PV changent, et cas des builds du Mage qui
changeraient après rejeu (« après » : la mesure écrite dans une copie des données par `forever measures refresh
--into`, sans instantané ; décision 227). **Décision 230** : une mesure dont le rejeu ne change aucun conseil des
builds du Mage (talents, choix, alternative) **s'écrit seule**, en révision de la version installée publiée par le
clone (`revisions.json` garde ses journaux) ; elle n'attend un accord que si un conseil change ou si le rejeu n'a rien
pu comparer. Une attente approuvée s'écrit au passage suivant ; remplacée par une mesure qui ajoute des journaux sans
changer aucun conseil (mêmes cas, même conseil après), elle passe son approbation à la nouvelle et devient
`périmée` ; toute attente de mesure remplacée, ou d'une version qui n'est plus installée, devient `périmée`. Rejeu
(décision 230) : seuls les cas concernés par ce qui change sont rejoués (un changement de la seule table des monstres :
leveling et donjon, dont le scénario de paquet lit les PV des monstres ; ni le raid ni le PvP) ; chaque cas est gardé
en cache (`<cache>/builds/update-<version>-<empreinte>/`, avec l'empreinte du code du calcul), si bien que le côté
« avant » n'est presque jamais recalculé ; les cas sont répartis sur les cœurs (`python -m forever.replay`) et les
départs du leveling calculés en parallèle. Téléchargements (décision 230) : chaque table est essayée trois fois
(délai doublé à chaque essai, attente croissante entre deux essais, chaque essai au journal du passage) ; les tables
de noms français (frFR) sont facultatives : la version s'installe sans elles, `sources.json` note `missing_names`, et
un passage suivant les ajoute en révision, écrite seule (les noms affichés ne sont pas une entrée des moteurs) ; une
table de calcul encore en échec crée une attente `network`, non approuvable, retentée et levée seule au passage
suivant. Un journal de combat n'est noté comme mesuré qu'une fois sa mesure écrite (décision 187). Un journal écrit sous une version antérieure n'est jamais mesuré dans la version installée, sauf accord explicite et tracé : `forever measures refresh --accept-version <version> --accept-reason "…"` (raison obligatoire, par exemple la note officielle qui ne touche pas ces monstres ; trace dans les notes de `monsters.json` et sa source dans `sources.json`, décision 221).

Tâche planifiée Windows « WoW Forever - mise à jour » (décision 226) : `forever update --auto`, comme le hook
de démarrage (même verrou `<cache>/update/lock`, même journal `<cache>/update/run-<horodatage>.log`), chaque jour à
08:00 en heure locale, lancée dès que possible si l'heure est passée (PC éteint à 08:00), seulement si le réseau est
disponible, 3 h au plus (au-dessus du plus long délai d'étape, décision 239), une seule à la fois ; sans fenêtre (le `pythonw.exe` de Python lance `forever.update_task`,
qui démarre le passage avec l'interpréteur réel de l'environnement et l'attend) et sans droits administrateur. Le
script retire l'ancienne tâche « WoW Forever - veille locale ». Il est en UTF-8 avec BOM : Windows PowerShell 5.1 en
lit les accents correctement.
```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1 -Print    # contenu de la tâche (JSON), sans rien créer
powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1 -WhatIf   # voir ce qui serait fait
powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1           # créer (08:00), -At 21:30 pour une autre heure
powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1 -Remove   # retirer
```
Chaque étape a un délai maximal (attente de la CI comprise) : au-delà, le passage s'arrête proprement, rend le
verrou et laisse une attente « erreur » ; aucun sous-processus n'ouvre de fenêtre ni ne pose de question (une
authentification de `gh` expirée devient une erreur : « lancer `gh auth login` dans un terminal ») ; décision 238.
Suivi : `uv run forever update status` (étape en cours, activité, durée et dernière ligne du journal), et le
dernier `run-*.log`. Après une recréation de `.venv` sur une autre
version de Python, relancer le script (l'action désigne le `pythonw.exe` de la version installée).

## Poser une question
Lancer `claude` dans n'importe quel dossier et poser la question en français. Exemples :

| Sujet | Question |
|---|---|
| Talent | « Que fait Improved Frostbolt au rang 3 ? », « Quel talent prendre au niveau 24 ? » |
| Build | « Meilleur build de leveling au niveau 30 ? », « Givre ou Feu en donjon au niveau 50 ? » |
| Respec | « J'ai tout mis en Feu, faut-il respec au niveau 40 ? » |
| Zone | « Où aller au niveau 22 côté Horde ? » |
| Mécanique | « Comment marche Ignite ? », « Hot Streak se cumule comment ? » |
| Leveling | « Combien de temps par monstre au niveau 18 en Givre ? », « XP par heure au niveau 35 ? » |

Dans le dépôt, une ligne de fraîcheur des données s'affiche au démarrage de la session. Ailleurs, rien au démarrage :
le routeur vérifie la fraîcheur (`forever_status`) à la première question sur WoW.

## Chat en jeu (P06a)
Une fenêtre dans le jeu (`/fv`) pour poser la question sans quitter WoW ; la réponse arrive en quelques secondes,
avec sa ligne de provenance. Sous Windows, jeu en fenêtré ou plein écran fenêtré.

| Commande | Effet |
|---|---|
| `uv run forever bridge install` | installe ForeverBridge et sa réserve de 200 emplacements (jeu fermé, puis le relancer) ; ensuite, le pont le tient à jour seul |
| `uv run forever bridge ask "question"` | même conversation que dans le jeu, sans le jeu : vérifie `claude` et les outils |
| `uv run forever bridge autostart install` | tâche planifiée « WoW Forever - pont » : le pont démarre à chaque ouverture de session Windows et est relancé s'il s'arrête (sans droits administrateur) ; lancée tout de suite, sauf `--no-start` |
| `uv run forever bridge autostart status` | tâche installée, surveillance et pont en marche, problèmes (interpréteur ou dépôt disparus) |
| `uv run forever bridge autostart remove` | retire la tâche (le pont en marche continue : `stop` pour l'arrêter) |
| `uv run forever bridge start` | lance le pont en arrière-plan avec l'interpréteur réel : il survit au terminal fermé (un seul à la fois) |
| `uv run forever bridge status` | pont en marche ou non (arrêt sans `stop` signalé), état des données et de l'addon, défauts de contexte, dernières lignes du journal |
| `uv run forever bridge stop` | arrête le pont, et la surveillance du démarrage automatique jusqu'à la prochaine ouverture de session (sans effet si rien ne tourne) |
| `uv run forever bridge config --model haiku` | modèle de la conversation « jeu » (Sonnet par défaut) |
| `uv run forever bridge selftest --live` | lit la bande de test de `/fv test` (diagnostic) |

En jeu : `/fv` ouvre la fenêtre (raccourci dans Options > Raccourcis > AddOns), Entrée envoie, Maj+Entrée passe à la
ligne ; boutons Talents, Leveling, Familiers, PvP selon la classe ; `/fv fond N` règle l'opacité. Pont arrêté ou
réserve vide : tapez `/reload` après `forever bridge start`, la réponse arrive par la sauvegarde. Procédure complète :
`docs/ADDON.md`, section 7, étape 11.

Démarrage automatique (décision 226) : la tâche « WoW Forever - pont » lance, à l'ouverture de la session, une
surveillance (`pythonw.exe` de Python, sans fenêtre, `python -m forever.bridge.autostart`) qui lit le verrou du pont
toutes les 15 secondes et lance le pont s'il ne tourne pas, toujours avec l'interpréteur réel (`C:\Program
Files\Python313\python.exe` dans l'environnement du dépôt), jamais avec le lanceur `.venv\Scripts\python.exe` :
ce lanceur retient l'interpréteur dans un objet de tâche et l'emporte quand on le tue (c'est ainsi que les ponts
lancés d'un terminal mouraient avec lui). Un pont mort est relancé aussitôt ; s'il meurt dans la minute, l'attente
double à chaque essai (30 s, 1 min, 2 min…, 30 min au plus). Journal du pont : `autostart_start`, `autostart_launch`,
`autostart_bridge_down`, `autostart_stop`, `autostart_env_error` (environnement du projet incomplet : `uv sync`,
décision 241), `autostart_skip` (une autre surveillance tourne déjà) et, depuis LN1, `autostart_wow_changed`
(installation choisie changée : jeu fermé, le pont est arrêté puis relancé sur la nouvelle ; une tâche créée sans
`--wow-dir` suit le choix, une tâche avec `--wow-dir` garde ce dossier). Au repos, jeu fermé ou en arrière-plan, le pont ne capture rien : jeu
fermé, il cherche la fenêtre du jeu toutes les 3 secondes et ne se réveille qu'une fois par seconde ; il relit la
liste des sauvegardes toutes les 30 secondes et réécrit la réserve toutes les 10 minutes. Mesure du 2026-10-09
(jeu fermé, 11 min, un rafraîchissement compris) : pont 0,61 s de processeur, soit 0,09 % d'un cœur (0,22 % avant ces
réglages), 43 Mo (33 Mo privés) ; surveillance sous la résolution de la mesure (moins de 0,02 s), 24 Mo (14 Mo
privés) ; journal : aucune fenêtre trouvée, aucune bande lue. Jeu ouvert en arrière-plan : non mesuré (il faut le jeu) ;
la capture y est refusée à chaque pas (`may_capture`, test `test_nothing_is_read_when_the_game_is_not_in_front`).

Mise à jour à la fermeture du jeu (décision 227) : le pont relit toutes les 5 secondes l'état du jeu et la date de
`Cache/ADB/enUS/DBCache.bin`. Le jeu qui se ferme (journal de combat terminé) ou un `DBCache.bin` réécrit (le client
l'écrit à la déconnexion du royaume, DON14) lance `forever update --auto`, une fois l'ensemble stable depuis 15
secondes, sans attendre les 6 h ; le passage prend le même verrou que la tâche de 08:00 et le hook (un passage en
cours : le pont réessaie jusqu'au lancement). Journal du pont : `game_closed`, `dbcache_written`, `update_launched`,
`update_deferred`. Rien au démarrage du pont, ni avec `FOREVER_OFFLINE`.

Addon tenu à jour : le pont compare l'addon installé à celui du dépôt ; s'il diffère (après une mise à jour du
dépôt), il le réinstalle dès que le jeu est fermé, jamais pendant qu'il tourne, et la ligne d'état de la fenêtre
l'annonce pendant la partie suivante. Jeu ouvert, elle dit « addon mis à jour à la prochaine fermeture du jeu ».
Chaque bouton envoie un appel d'outil fixé par le pont (Talents : prochain point au niveau suivant depuis le build
actuel) ; un élément du contexte que le pont ne relie pas à nos données est noté comme défaut dans
`forever bridge status`, jamais transmis à la conversation.

## Chat en jeu, suite (P06b)
P06b ajoute à la fenêtre `/fv` (décision 235) :
- **Liens Maj+clic** : pendant la saisie, Maj+clic sur un objet, un sort, une quête ou un talent insère son lien ;
  la question part avec le nom du lien et son infobulle lue dans le jeu (8 liens au plus). La zone de saisie prend
  1 000 caractères.
- **Messages longs** : un message trop long pour une bande (équipement complet, liens, export) part en plusieurs
  parties montrées tour à tour en haut à gauche ; la ligne d'état compte les parties reçues par le pont. Équipement,
  talents, liens et question ne sont jamais retirés ; seuls les noms d'objets sont coupés, puis retirés.
- **Mettre à jour** (bouton) : le pont lance `forever update --auto` lui-même (jamais le modèle) ; refusé hors ligne
  (`FOREVER_OFFLINE`). Ligne d'état : `Données <version> · client <version> · <fraîcheur> · <n> à valider · <m> en
  attente` ; pendant un passage, « mise à jour en cours (étape : activité, N min) », par exemple « (journaux :
  attente de la CI, 9 min) », relevée toutes les 30 s fenêtre ouverte ; « dernier passage en erreur (voir À
  valider) » après un passage arrêté ou en échec (décision 238) ; à la fin,
  « Mise à jour terminée : n écrit(s), m à valider ».
- **À valider (n)** : une carte par attente de `forever update` (texte rédigé par le pont : PNJ, niveaux, builds,
  version), avec Valider et Refuser pour une attente approuvable (second clic « Confirmer » dans les cinq secondes,
  commande fixée lancée par le pont) et « Expliquer » (question à la conversation « jeu ») ; les autres attentes
  (réseau, correctifs à lire, à traiter sur le PC) n'ont que « Expliquer ».
- **Écart avec le profil** : à chaque message, le pont compare le jeu (classe, race, faction, niveau, talents,
  équipement) au profil ; la réponse le signale, le jeu l'emporte, et une carte « Mettre à jour le profil » écrit le
  profil au clic seulement (source `jeu`, profil au schéma 3) ; « Ignorer » fait taire cet écart tant qu'il ne
  change pas. Personnage absent : carte « Créer le personnage … au profil ».
- **Panneau de droite** (décision 238) : un seul panneau, collé à droite de la fenêtre, regroupe la copie d'un lien
  (clic sur `[Talents Forever]`, Ctrl+C), la zone de collage de l'export et les cartes « À valider » ; il défile
  à la molette et par sa barre ; Échap ou un second clic sur « Coller /simc » ou « À valider » le ferme.
- **Coller /simc** : `/simc` en jeu, Ctrl+C, puis « Coller /simc », Ctrl+V, « Envoyer l'export ». Le pont le lit sans
  le modèle (objets, fiche du personnage, notations, buffs ; somme de contrôle vérifiée), liste les écarts avec le
  profil et propose d'écrire la fiche (source `simulationcraft`) ; la chaîne `talents=` n'est pas décodée (les
  talents du jeu font foi) ; l'arme à distance, absente de l'export, est prise du jeu. Trop long : `/simc nobags`.
- **Onglet « Addons »** : visible quand la conversation « addons » est réglée ; un agent sans shell, limité au dossier
  de RaphCompletionist, modifie l'addon ; le pont sauvegarde le dossier avant le tour et committe en local après
  (ligne `<commit> · n fichier(s)` sous la réponse) ; `/reload` pour essayer.

| Commande | Effet |
|---|---|
| `uv run forever bridge contexts last` | dernier contexte reçu du jeu : équipement pièce par pièce (enchantement, suffixe), liens et infobulles |
| `uv run forever bridge contexts export <dossier>` | chaque contexte distinct et chaque export SimulationCraft (anonymisé) du journal, au format des fixtures |
| `uv run forever bridge selftest --card` | carte « À valider » de test : Valider puis Confirmer, le pont note l'action sans rien lancer |
| `uv run forever bridge addons config --source <dossier> [--deploy <dossier installé>]` | dossier de la conversation « addons » (refusé pour un addon de la communauté) ; avec `--deploy`, copie des fichiers changés après chaque tour, sans rien supprimer |
| `uv run forever bridge addons status` | dossier réglé et sauvegardes (`<cache>/bridge/addons/backups/`) |
| `uv run forever bridge addons restore [<horodatage>]` | remet une sauvegarde ; les fichiers créés depuis sont déplacés dans `<cache>/bridge/addons/set-aside/`, jamais supprimés |
| `uv run forever bridge addons log` | commits locaux de la conversation |
| `uv run forever bridge config --thinking on\|off --persistent on\|off` | réflexion du modèle et session `claude` gardée ouverte entre les messages ; par défaut, réflexion `on` et session gardée ouverte `on` (variante C retenue, `tasks/P06b-vitesse.md`, décision 237) |
| `uv run forever bridge bench --variants A,B,C,D --rounds 2` | mesure des accélérations sur six questions réelles (vraies conversations `claude`, coût : sur demande seulement) |

Les conversations du pont démarrent sans les hooks du plugin (décision 237 : environ 2 s de moins par conversation,
le pont publie lui-même l'état des données et la provenance). Relancer le pont après un changement de réglage
(`forever bridge stop`, puis la tâche planifiée). Procédure en jeu :
`docs/ADDON.md`, section 7, étapes 17 (sonde G) et 18 (sonde H).

## Mon personnage (profil)
Le profil vit hors du dépôt (`%USERPROFILE%\.forever\profile.json`, ou le fichier désigné par `FOREVER_PROFILE`) ;
plusieurs personnages, un actif. Les réponses le lisent avant tout calcul et le rappellent en une ligne ; une donnée
absente est demandée avant le calcul.
```powershell
uv run forever profile set Givrelame --class Mage --race Orc --faction Horde --level 22 --talents "improvedFrostbolt=5,elementalPrecision=3"
uv run forever profile set Givrelame --profession "Couture=150"
uv run forever profile list
uv run forever profile use Givrelame
uv run forever profile show
uv run forever profile remove Givrelame
uv run forever profile import --dry-run           # ForeverLogger, Questie, Auctionator, journaux : changements listés
uv run forever profile import                     # écriture après accord (--yes pour ne pas la demander)
```
L'import lit sur disque (SavedVariables sous `FOREVER_WOW_DIR`, `--wtf` et `--logs` pour d'autres dossiers ;
`--utc-offset` pour l'heure locale des journaux). Chaque champ garde sa source, sa date et la version du client ; un
désaccord entre sources est gardé dans `conflicts`, jamais effacé ; la faction n'est jamais importée.

## PvP et builds des autres classes
```powershell
uv run forever pvp class Voleur --level 60                     # contrôles, défensifs, ruptures, recharges
uv run forever pvp matchup Mage Démoniste --level 60 --race Orc # menaces, mes réponses, fenêtres
uv run forever talents check --class Chasseur --level 20 deadlyAspects=5 enduranceTraining=5
uv run forever lookup talent Intimidation --class Chasseur
```
Les fiches sont fixes (valeurs du client, classement probable, rendements décroissants supposés) : aucun suivi en
direct des recharges adverses n'est possible dans un addon sur Forever.

## Talents Forever (FA1)
```powershell
uv run forever build leveling --level 20 --preset rapide   # ligne « Talents Forever » : code, lien, /tf import
uv run forever talents tf decode https://talentsforever.com/<code>   # points, ordre, légalité sur le client
uv run forever talents tf popular --class Voleur              # builds populaires : part, date, lien, légalité
uv run forever talents tf crosscheck --out docs/research/talents-forever-FA1.md   # écarts des arbres
```
L'addon installé est relu à chaque appel (table de correspondance jamais stockée) : absent, il est signalé ;
une classe dont un talent n'a pas de correspondance (Chasseur, Démoniste au 2026-10-07) n'a pas de code. En jeu :
`/tf import <code>` (procédure de test : `docs/ADDON.md`, section 7). Les builds populaires sont des choix de
joueurs (certitude supposé), datés par `asOf`.

## Exports vers les addons d'interface (EX1)
Chaînes d'import que le joueur colle lui-même dans l'addon (décision 196) ; aucune n'est importée par forever.

```powershell
uv run forever export naowh-build --class Mage --level 20 --talents improvedFrostbolt=5,elementalPrecision=3
uv run forever export naowh-build --code "https://talentsforever.com/mage/20/..."   # ordre du code repris
uv run forever export naowh-build --class Hunter --popular 1                        # build populaire, ordre généré
uv run forever export naowh-macros --class Priest --level 30
uv run forever profile set Jen --ellesmere-base Mage  # profil de base EllesmereUI de Jen, choisi une fois
uv run forever export ellesmere Jen --role dps        # classe, niveau, royaume et profil de base lus dans le profil
uv run forever export read "<chaîne>"                 # relit !NFB1!, !NFM1!, !NBIS1!, NFSW1: ou !EUI_
```

- Naowh Forever : `/nf`, **Profiles**, **Import**. Un build sans ordre (build populaire, de la communauté, calculé
  hors leveling) reçoit un ordre **généré** légal à chaque prise, signalé comme tel (`order_note`) ; ce n'est pas
  un ordre de leveling optimisé.
- EllesmereUI : `/eui`, **Profiles**, **Import**, nommer le profil « <personnage> - <rôle> », puis `/fb role` en jeu.
  Le profil de base (disposition, polices, couleurs) reste celui du joueur ; forever ne remplit que les sorts du
  gestionnaire de recharges et les rappels de buffs. Profil de base : celui du personnage (`forever profile set <nom>
  --ellesmere-base <profil>` ou `/fb base <profil>` en jeu, décision 269), sinon le profil actif d'EllesmereUI (dit
  dans la réponse) ; `--base` le remplace pour un export.
- `forever export bis` et `forever export weights` : formats prêts, contenu rempli par T10a.
- MCP : `forever_lookup(kind="export", name="naowh_build" | "naowh_macros" | "ellesmere" | "read")` ;
  `forever_build` porte `export.naowh` à côté de `export.talents_forever`.
- En jeu : liens cliquables `[Naowh : build]`, bouton « Exports » (build actuel, `[Naowh : macros]`,
  `[EllesmereUI : <rôle>]` une fois le rôle choisi), `/fb exports`, `/fb role dps|heal|tank`, `/fb base <profil>`.

## Familiers du Chasseur (CH0)
```powershell
uv run forever pets rules                                           # système : entraînement, loyauté, apprivoisement
uv run forever pets family Loup                                     # capacités, rangs, coût, bonus, régime
uv run forever pets ability Morsure --detail                        # rangs et bêtes qui enseignent chaque rang
uv run forever pets tame --ability Morsure --rank 3 --zone "Les Tarides" --level 14   # guide d'apprivoisement
uv run forever pets crosscheck --markdown docs/research/familiers-recoupement.md        # écarts client, addon, Questie
uv run forever pets mine                                            # mes familiers et mes observations
uv run forever pets measure --addon-sv <WTF>/SavedVariables/ForeverLogger.lua           # relevés de ForeverLogger
```
Forever Bestiary et Questie sont lus dans `FOREVER_WOW_DIR` (ou `--addon`, `--questie`, `--saved`). Les tables des
familiers d'une nouvelle version se téléchargent avec `forever fetch --tables <pet_tables de decode_rules.json>`
(`--locale enUS,frFR` pour les tables localisées, `--timeout` pour une table volumineuse), sur accord.

## Lire la réponse
Réponse courte par défaut ; demander « détaille » ou « pourquoi » pour les raisons, hypothèses et alternatives.
- **Chiffres** : chacun vient d'un outil forever de la session (outil cité entre parenthèses).
- **Certitude** : `certain` (lu dans le client), `probable`, `supposé` (hypothèse à vérifier en jeu).
- **Attention** : une hypothèse ou un angle mort qui peut changer la conclusion.
- **Pied de réponse** : `Certitude : … · Version … · Fraîcheur … (date)`.
- Réponse « Le serveur forever ne répond pas : … » : `FOREVER_HOME` est faux (ou le dépôt a bougé) ; relancer le script
  d'installation depuis le dépôt, puis ouvrir un nouveau terminal.
- Message `[forever:chiffres]` en fin de réponse : un chiffre de jeu de la réponse ne vient d'aucun outil forever de
  la session ; ne pas s'y fier, redemander la valeur.

## Quêtes et XP de Forever (T04d)
- `uv run forever quests build` : liste fusionnée des quêtes (Questie, Naowh Forever, Forever Guide,
  ForeverDungeonJournal, GearQuest, quêtes apprises de Questie et quêtes vues par le client), dans le cache local
  seulement ; relue tant qu'aucun addon ne change. `forever quests diff` : écarts entre sources ; `forever quests show
  --dungeon "Ragefire Chasm" --faction horde` (ou `--id`, `--zone`) : quêtes, statut, XP et sa source.
- `uv run forever lookup quests --level 15 --faction horde [--status nouvelle]` : quêtes accessibles et non grises.
- `uv run forever sim objectives --level 15 --class hunter --faction horde` : XP par heure par zone et par donjon
  (premier passage avec ses quêtes, passages suivants), temps par monstre calculé (Mage), mesuré sur vos relevés ou
  estimé, et le conseil ; le bouton Leveling s'en sert pour toutes les classes.
- `uv run forever measures kill-time [--class hunter --level 15]` : temps par monstre mesuré par classe et tranche de
  niveaux (journaux, ForeverLogger), gardé dans le cache.
- `uv run forever xp check` : vérification passive du modèle d'XP sur ce que vous avez joué avec ForeverLogger 0.4.0
- T04f : `uv run forever lookup xp_bonuses [--access item|legacy|food|camp|none]` (bonus d'XP du client, chaîne du sac de couchage lue dans les addons) ; `uv run forever sim objectives … [--rested XP] [--sleeping-bag [N]] [--food] [--legacy-rested-rank R] [--hours H]` (XP par heure sans bonus, avec repos, avec le sac, avec les bonus actifs, bonus à prendre) ; `uv run forever sim leveling --level N --bonus sleeping_bag,food [--rested XP]` ; `uv run forever profile set <nom> --legacy-rested-rank R` ; `forever xp check` compare aussi les gains relevés avec leurs auras (ForeverLogger 0.5.0).
  (vérifié, écart, à vérifier) ; rien n'est écrit, aucune sonde n'est exigée (décision 247).

## Donjons (DJ1)
- `uv run forever dungeon list [--level 15] [--faction horde] [--rebuild]` : donjons du livre fusionné (client,
  note officielle, Naowh Forever, FojjiCore en recoupement, ForeverDungeonJournal, Forever Guide, Forever Companion,
  AtlasLoot, Zone Info: Forever, relevés du joueur), dans le cache local seulement ; plage retenue et sa source,
  niveau de contenu du client, nouveau ou fermé, nombre d'écarts entre sources.
- `uv run forever dungeon info "Ragefire Chasm" [--class mage --level 14]` : entrée, boss et leur niveau (journal
  de combat d'abord), butin avec taux et source (« taux inconnu » sinon, étiquette Classic), objets utilisables
  (classes permises et niveau requis, `ItemSparse` du cache de `forever fetch`), quêtes avec XP et sa source,
  prérequis « à faire d'abord », passages relevés, écarts ; `forever dungeon item 14149` : où trouver un objet.
- `uv run forever dungeon report > docs/research/donjons-forever.md` : agrégats seulement (décision 133).
- `forever sim objectives` : un donjon par instance, durée d'un passage relevée (ForeverLogger 0.6.0, Naowh Forever)
  ou formule de Factoruide (`suppose`), niveau de placement et `dungeon_advice`.
- Relevés facultatifs (décision 247) : ForeverLogger 0.6.0 relève passages et butin ; activer InstanceTracker dans
  Naowh Forever ajoute ses passages (durée, XP), lus en local.

## Nos routes face aux parcours gratuits de RestedXP (RX1c)
Une mesure, pas une source (décision 268) : seuls les parcours gratuits livrés en clair dans RXPGuides
(`Guides/Forever`) sont lus, en local ; aucun guide payant ni chiffré, rien de RestedXP dans nos routes.

```powershell
uv run forever route rxp-coverage                    # jusqu'où vont les parcours en clair, par race et par camp
uv run forever route rxp-compare --to 22             # personnage actif du profil, de son niveau au niveau 22
uv run forever route rxp-compare --class Mage --race Orc --faction horde --from 12 --to 21 --start-guide "Barrens AoE"
```

Sortie : durée, XP par heure, parts du trajet, des objectifs et du farm, ordre des zones, quêtes communes et propres,
étapes de RestedXP impossibles chez nous (et pourquoi), sans donjon des deux côtés. Résultats et leçons :
`docs/research/rxp-comparaison.md`.

## Ce que le plugin ne sait pas encore
PvP de champ de bataille et rendements décroissants mesurés (PV2), raids (T09 à T11), Legacy (LG1, LG2), métiers (MT1), réputations (RP1), hôtel des
ventes (EC1), mana des combats longs (T05b), mémoire du joueur (T07), raid
complet (T09), équipement (T10), consommables (T11), analyse de mes combats (AN1, AN2), autres classes que le Mage
(dégâts et rotations : tranches de classe CM1 à DR1 ; leur PvP et la légalité de leurs builds sont couverts depuis PV1). Sur ces sujets, il répond « je ne sais pas » et cite la tranche de `docs/ROADMAP.md` qui les
couvrira ; pour une classe pas encore calculée, il propose des builds de la communauté trouvés par le sous-agent de
recherche, avec source et date, certitude au mieux supposée.

Question personnelle (« mon Mage », « mon perso ») : il part du personnage actif du profil et demande ce qui manque ;
question générale (« l'arbre optimal du Mage en raid ») : il ne demande rien et annonce l'hypothèse neutre de son
calcul. Quand vous dites « j'ai … », il propose de mettre le profil à jour (`forever profile set`).

## Évaluation
Jeu de questions : `plugin/evals/` (cas positifs et questions voisines qui ne doivent pas déclencher le plugin). La
CI contrôle la suite sans modèle (`tests/unit/test_plugin_evals.py`) ; le passage avec le modèle se lance à la main
(coût : voir `docs/research/plugin-eval-T06.md`), depuis la racine du dépôt :

```powershell
claude plugin eval plugin --trust-plugin --mocks off --allow-tools "mcp__plugin_forever_forever__*" --runs 1 --ablation none -j 4 --judge-model opus --max-cost-usd 15 --no-publish --keep-temp --json plugin/evals/results/passage.json
uv run python scripts/plugin_eval_report.py plugin/evals/results/passage.json
```

`--keep-temp` garde les traces (le rapport y relit les messages du contrôle des chiffres) ; les supprimer ensuite
(dossiers `claude-eval-*` du dossier temporaire). Le second script calcule les seuils de la tranche (aiguillage, outil attendu, aucun chiffre inventé, certitude
affichée) et le taux de fausses alertes du contrôle des chiffres. `plugin/evals/results/` n'est pas versionné. Un workflow GitHub manuel est prêt, non appliqué : `git apply tasks/plugin-eval.patch`
(secret `ANTHROPIC_API_KEY` du dépôt).
