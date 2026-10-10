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
- fixe les variables d'environnement utilisateur `FOREVER_HOME` (le dépôt) et `FOREVER_WOW_DIR` (dossier du client,
  cherché dans `C:\Program Files (x86)\World of Warcraft\_classic_beta_` puis `C:\Program Files\World of Warcraft\_classic_beta_`) ;
- `uv sync` ;
- déclare la marketplace locale `wow-forever` (le dépôt) et installe le plugin `forever@wow-forever` en portée
  utilisateur ;
- contrôle : `claude plugin validate --strict` (plugin versionné : la mise à jour recopie le plugin quand la version
  de `plugin.json` change), `forever status --offline`, plugin présent et activé.

Second PC : même procédure. L'addon ForeverLogger s'installe à part : `uv run python scripts/install_addon.py`
(il lit `FOREVER_WOW_DIR`, sinon cherche le client dans les deux dossiers Program Files).

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
disponible, 2 h au plus, une seule à la fois ; sans fenêtre (le `pythonw.exe` de Python lance `forever.update_task`,
qui démarre le passage avec l'interpréteur réel de l'environnement et l'attend) et sans droits administrateur. Le
script retire l'ancienne tâche « WoW Forever - veille locale ». Il est en UTF-8 avec BOM : Windows PowerShell 5.1 en
lit les accents correctement.
```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1 -Print    # contenu de la tâche (JSON), sans rien créer
powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1 -WhatIf   # voir ce qui serait fait
powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1           # créer (08:00), -At 21:30 pour une autre heure
powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1 -Remove   # retirer
```
Suivi : `uv run forever update status`, et le dernier `run-*.log`. Après une recréation de `.venv` sur une autre
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
`autostart_bridge_down`, `autostart_stop`. Au repos, jeu fermé ou en arrière-plan, le pont ne capture rien : jeu
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

## Ce que le plugin ne sait pas encore
PvP de champ de bataille et rendements décroissants mesurés (PV2), boss et butin des donjons (DJ1), Legacy (LG1, LG2), métiers (MT1), réputations (RP1), hôtel des
ventes (EC1), quêtes et XP propres à Forever (T04d), mana des combats longs (T05b), mémoire du joueur (T07), raid
complet (T09), équipement (T10), consommables (T11), analyse de mes combats (AN1, AN2), autres classes que le Mage
(dégâts et rotations : tranches PA1 à DR1 ; leur PvP et la légalité de leurs builds sont couverts depuis PV1). Sur ces sujets, il répond « je ne sais pas » et cite la tranche de `docs/ROADMAP.md` qui les
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
