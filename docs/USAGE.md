# Mode d'emploi de forever

Poser ses questions sur World of Warcraft: Forever en français, **dans le jeu** (fenêtre `/fv` de ForeverBridge,
servie par le pont `forever bridge`) ou **dans Claude Code** (plugin `forever`), avec des réponses sourcées par les
outils du dépôt. Ni l'addon, ni le pont, ni le plugin ne calculent : tout passe par le serveur MCP `forever`, qui lit
le client du jeu, mes addons, mes journaux et les simulateurs de la communauté.

Toutes les classes sont servies. Au niveau 60, les dégâts, la meilleure race et les poids des statistiques viennent
de wowsims/forever ; sous le 60, le moteur du Mage est **gelé** (il répond et le dit), et les autres classes passent
par les addons de la communauté (Talents Forever, Forever Companion, Naowh Forever), mes journaux et les sources
Forever ; ce qui n'est calculé par personne est dit « non calculé ».

## Installation
Sur chaque PC (Windows), une fois.

1. Prérequis : [Git for Windows](https://git-scm.com/download/win) (il fournit aussi le bash des hooks),
   [uv](https://docs.astral.sh/uv/getting-started/installation/), Claude Code (`claude`, connecté par `/login`) et
   `gh` connecté (`gh auth login`, pour la veille). Pour wowsims/forever : Go et `protoc`.
2. Cloner le dépôt, puis, **depuis sa racine**, dans PowerShell :

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1
   ```

   `-ExecutionPolicy Bypass` contourne la politique d'exécution des scripts pour ce seul lancement (sans rien changer
   au réglage de Windows). Le script, relançable sans risque, fixe `FOREVER_HOME` (le dépôt), lance `uv sync`, fixe
   `FOREVER_WOW_DIR` sur l'installation que choisit `forever wow list` (accord demandé avant de remplacer une autre
   valeur ; `-Print` affiche le choix sans rien changer), installe le plugin `forever@wow-forever` au niveau
   utilisateur et contrôle que tout répond.
3. Ouvrir un **nouveau** terminal (les variables d'environnement n'arrivent que dans les nouveaux terminaux).
4. Jeu fermé, installer les addons, le pont et la veille :

   ```powershell
   uv run python scripts/install_addon.py                                   # ForeverLogger (--wow-dir pour un autre client)
   uv run forever bridge install                                            # ForeverBridge et sa réserve de réponses
   uv run forever bridge autostart install                                  # tâche « WoW Forever - pont »
   powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1 # tâche « WoW Forever - mise à jour »
   uv run forever sims update                                               # wowsims/forever (facultatif, réseau)
   uv run forever doctor                                                    # tout contrôler
   ```

Second PC : même procédure. Jour du lancement (4 novembre), une section par PC : `docs/LANCEMENT.md`.

## Mise à jour
```powershell
git pull
powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1
```
Le script refait `uv sync`, met à jour la marketplace et recopie le plugin. Redémarrer ensuite Claude Code (un plugin
chargé ne se recharge pas seul) et relancer le pont, qui ne recharge jamais seul son code : `uv run forever bridge
stop`, attendre « surveillance : arrêtée » dans `uv run forever bridge autostart status`, puis
`schtasks /Run /TN "WoW Forever - pont"`. L'addon ForeverBridge du dépôt est réinstallé par le pont à la fermeture
suivante du jeu.

Les données, elles, se mettent à jour seules : section « Mise à jour automatique des données ».

## En jeu : la fenêtre `/fv`
`/fv` ouvre la fenêtre (raccourci dans Options > Raccourcis > AddOns). Jeu en fenêtré ou plein écran fenêtré.
Barre latérale à gauche :

- **Chat** : une question en français ; Entrée envoie, Maj+Entrée passe à la ligne. Maj+clic sur un objet, un sort,
  une quête ou un talent insère son lien (la question part avec son infobulle). Le pont ajoute de lui-même le
  contexte du personnage (classe, race, camp, niveau, talents, équipement, repos, réputations). Les questions de
  l'agent se posent dans le chat, avec des boutons de réponse sous le message. Plusieurs conversations : bouton « v »
  de l'onglet Jeu (créer, renommer, effacer) ou `/fb conv`. « Effacer » (en-tête) repart d'une conversation neuve.
- **Feuille de route** : type Leveling ou Équipement, niveaux, donjons, quêtes de classe, puis « Calculer » ; la
  route part de ma position et de la zone de départ de ma race, suit le parcours gratuit de RestedXP de ma race et de
  ma classe, puis les guides de Polestar au-delà (attribution dans le guide). « Valider et livrer » l'envoie dans
  RestedXP (groupe « Forever Routes »). Sur un serveur JcJ déclaré, les zones disputées sont signalées. Réputation et
  métier : l'écran dit que la route n'est pas encore calculée (métier : recettes de SkillUp Forever qui montent encore).
- **Talents** : plan de talents dès le niveau 1, prochain point au niveau suivant ; lien `[Talents Forever]`
  (`/tf import <code>` dans l'addon) et code Naowh à importer. Autre classe que le Mage : builds populaires de
  Talents Forever et build de Forever Companion pour ma spécialisation, ordre de prise non calculé.
- **Équipement** : « Mon équipement à ce niveau » (objets obtenables, pris d'abord sur ma route, niveau requis
  affiché), « jusqu'au » pour une tranche, « Feuille de route de ces objets » ou « En faire une route » (livrée dans
  RestedXP). La réponse nomme la source des poids : wowsims/forever au niveau 60 pour toute spécialisation de
  dégâts, sinon Forever Companion, Naowh Forever ou le moteur du Mage.
- **Exports** : liens à copier puis coller soi-même : `[Naowh : build]`, `[Naowh : macros]`, `[Naowh : BiS]`,
  `[Naowh : poids]`, `[Forever Companion : échelle]`, et `[EllesmereUI : <rôle>]` seulement après `/fb eui on`.
- **Mises à jour** : cartes « Mis à jour » de la veille, avec « Expliquer » et « Annuler » (puis « Confirmer » dans
  les cinq secondes) ; bouton « Mettre à jour » (le pont lance la veille lui-même). La ligne d'état dit la version
  des données, celle du client, la fraîcheur et l'avancement d'un passage en cours.
- **À valider** (panneau de droite) : ce qui reste à décider, rarement : écart entre le jeu et mon profil (« Mettre
  à jour le profil », « Ignorer »), attentes « réseau » ou « correctifs à lire » qui se lèvent seules, et ce qui
  demande une session sur le PC.
- **Plus...** : Nouvelle conversation, Coller /simc (`/simc` en jeu, Ctrl+C, puis Ctrl+V et « Envoyer l'export » :
  le pont lit l'export sans le modèle et propose d'écrire la fiche au profil), boutons Leveling, PvP (« Comment jouer
  contre lui » sur un joueur ennemi en cible) et Familiers (Chasseur).

Commandes de la fenêtre : `/fv aide`, `/fv reset` (taille par défaut, au centre ; ou double-clic sur le titre),
`/fv classique` (ancienne fenêtre au `/reload` suivant), `/fb exports`, `/fb role dps|heal|tank`, `/fb base
<profil>` (profil de base EllesmereUI du personnage), `/fb eui on|off`, `/fb conv`.

L'addon ne joue jamais à ma place : aucune fonction d'action, aucun abonnement au journal de combat en jeu ; macros
et profils sont du texte que j'importe moi-même. Rien ne modifie EllesmereUI sans `/fb eui on`. Règles et essais en
jeu : `docs/ADDON.md`.

## Le pont (`forever bridge`)
Le pont lit la fenêtre du jeu, fait répondre la conversation « jeu » (`claude` et le serveur MCP) et dépose les
réponses dans la réserve de l'addon. Il installe lui-même l'addon du dépôt jeu fermé et lance la veille à la
fermeture du jeu.

| Commande | Effet |
|---|---|
| `uv run forever bridge install` | installe ForeverBridge (jeu fermé, puis le relancer) ; `--dry-run` pour voir |
| `uv run forever bridge autostart install` | tâche « WoW Forever - pont » : le pont démarre à l'ouverture de session et est relancé s'il s'arrête (sans droits administrateur) ; `--no-start` pour ne pas la lancer tout de suite |
| `uv run forever bridge autostart status` / `remove` | tâche, surveillance et pont en marche ; retrait de la tâche |
| `uv run forever bridge start` / `stop` / `status` | lancer, arrêter, état du pont (journal, données, addon) |
| `uv run forever bridge ask "question"` | même conversation que dans le jeu, sans le jeu : vérifie `claude` et les outils |
| `uv run forever bridge config --model haiku` | modèle de la conversation « jeu » (Sonnet par défaut) ; `--thinking on\|off`, `--persistent on\|off` |
| `uv run forever bridge contexts last` | dernier contexte reçu du jeu |
| `uv run forever bridge selftest --live` | lit la bande de `/fv test` (diagnostic) |

Journal de la surveillance du démarrage automatique : `autostart_start`, `autostart_launch`, `autostart_bridge_down`,
`autostart_stop`, `autostart_env_error` (environnement du projet incomplet : `uv sync`), `autostart_skip` (une autre
surveillance tourne déjà) et `autostart_wow_changed` (installation choisie changée : le pont est relancé sur la
nouvelle, jeu fermé ; une tâche créée avec `--wow-dir` garde son dossier). Pont arrêté pendant une partie : `/reload`
après `forever bridge start`, la réponse arrive par la sauvegarde.

## Mise à jour automatique des données
`forever update --auto` (la veille) tourne seule : au démarrage d'une session Claude Code dans le dépôt (au plus toutes
les 6 h), à la fermeture du jeu par le pont, et chaque jour à 08:00 par la tâche planifiée. Elle archive les fichiers
du client, puis enchaîne ses étapes : `jeu` (nouvelle version du client sur wago.tools), `correctifs` (correctifs du
serveur), `journaux` (mesures de mes journaux de combat), `addons` (addons de données), `guides` (Polestar),
`simulateurs` (wowsims/forever recompilé s'il l'a déjà été).

**Elle installe d'elle-même** (décision 295) et prévient : carte « Mis à jour » en jeu et ligne de `forever update
status`, qui disent ce qui a changé en mots de joueur (conseils rejoués après l'installation, sinon résumé des
valeurs), avec « Annuler ». Une nouvelle version qui retire ou change un talent ou un sort l'emporte sur une
observation faite sur une version plus ancienne et le dit ; un sort retiré reste connu, marqué retiré, et n'est plus
jamais recommandé (décisions 296 et 297). Elle ne s'arrête, et le dit, que si l'intégrité casserait (vérification,
règles de fusion, CI), si une source est injoignable, ou si une valeur écrite à la main ou un correctif du serveur
serait perdu.

```powershell
uv run forever update status              # installations (Mis à jour, Annuler), attentes et dernier passage ; --all
uv run forever update undo <id>           # retour à la révision précédente, même jeu fermé
uv run forever update                     # passage complet à la main
uv run forever update --dry-run           # tout calculer, ne rien écrire
uv run forever update --only jeu,correctifs   # certaines étapes ; --no-network : hors ligne
uv run forever status                     # version des données, fraîcheur, sources à jour ou en retard
```

Une annulation empêche seulement la réinstallation du même contenu. `forever update approve <id>`, `reject <id>
--reason "…"` et `done <id> --note "…"` restent pour les rares attentes ouvertes que `update status` montre.

Sources que la veille tient à jour, lançables à la main (réseau, lecture seule) :

```powershell
uv run forever sims update                # copier, compiler et épingler wowsims/forever (Go et protoc requis)
uv run forever route polestar             # copier ou mettre à jour les guides de Polestar en cache
uv run forever hotfixes --raidbots        # correctifs du build lus dans le DBCache.bin vérifié de Raidbots ; --build
```

`forever hotfixes --raidbots` sert quand je ne peux pas me connecter : valeurs au plus `probable`, et mon propre
`DBCache.bin` les confirme ensuite (décision 290).

Tâche planifiée Windows « WoW Forever - mise à jour » : chaque jour à 08:00, lancée dès que possible si l'heure est
passée, seulement avec le réseau, 3 h au plus, une seule à la fois, sans fenêtre ni droits administrateur ; même
verrou et même journal (`<cache>/update/run-<horodatage>.log`) que les autres passages. Le script retire l'ancienne
tâche « WoW Forever - veille locale ».
```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1 -WhatIf   # voir ce qui serait fait
powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1           # créer ; -At 21:30 pour une autre heure
powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1 -Remove   # retirer
```
Après une recréation de `.venv` sur une autre version de Python, relancer ce script.

## Poser une question
En jeu : la fenêtre `/fv`. Dans Claude Code : lancer `claude` dans n'importe quel dossier et poser la question en
français. Exemples :

| Sujet | Question |
|---|---|
| Talents | « Quel talent prendre au prochain niveau ? », « Ce build de Voleur est-il légal ? » |
| Niveau 60 | « Quelle race pour un Mage Feu ? », « Mage ou Chaman en dégâts ? » |
| Équipement | « Mon équipement à ce niveau ? », « Cet objet est-il une amélioration ? » |
| Route | « Fais-moi une route du niveau 10 à 20 », « Enlève tel donjon de ma route » |
| Donjons | « Que lâche le dernier boss des Mortemines ? », « Quel donjon à mon niveau ? » |
| PvP | « Contrôles du Voleur », « Mon Mage contre un Démoniste » |
| Familiers | « Où apprivoiser la bête qui enseigne Bite près de ma zone ? » |
| Données | « Mes données sont-elles à jour ? » |

Question personnelle (« mon perso ») : elle part du personnage actif du profil (en jeu, du personnage connecté) et
demande ce qui manque ; question générale : elle annonce l'hypothèse neutre de son calcul. Dire « j'ai … » propose de
mettre le profil à jour.

## Lire la réponse
Réponse courte par défaut ; demander « détaille » ou « pourquoi » pour les raisons, hypothèses et alternatives.
- **Chiffres** : chacun vient d'un outil forever de la session.
- **Certitude** : `certain` (lu dans le client ou observé), `probable` (calculé ou recoupé), `supposé` (estimé, tiré
  d'un addon ou d'un simulateur de la communauté ; à vérifier en jeu).
- **Source** : addon, simulateur (avec son commit) ou moteur gelé, nommé quand il sert.
- **Pied de réponse** : `Certitude : … · Version … · Fraîcheur … (date)`.
- « Le serveur forever ne répond pas : … » : `FOREVER_HOME` est faux (ou le dépôt a bougé) ; relancer le script
  d'installation depuis le dépôt, puis ouvrir un nouveau terminal.
- `[forever:chiffres]` en fin de réponse (Claude Code) : un chiffre de jeu ne vient d'aucun outil ; ne pas s'y fier.

## En ligne de commande
Depuis la racine du dépôt, avec `uv run` (jamais `pip`). Chaque commande accepte `--json` et rend le bloc
`provenance`.

**Consulter**
```powershell
uv run forever status                                   # données, fraîcheur, sources ; --offline
uv run forever lookup spell frostbolt                   # un sort (retiré : il le dit)
uv run forever lookup talent "Intimidation" --class Chasseur
uv run forever lookup zones --level <niveau> --faction horde
uv run forever lookup quests --level <niveau> --faction horde
uv run forever pvp class Voleur                         # fiche PvP ; pvp matchup Mage Démoniste
uv run forever talents check --class Chasseur --level <niveau> <clé>=<rang> …
uv run forever talents tf popular --class Voleur        # builds populaires de Talents Forever ; tf decode <lien>
uv run forever dungeon list --level <niveau>            # dungeon info "<donjon>", dungeon item <id>
```

**Builds et simulateur**
```powershell
uv run forever build leveling --level <niveau>          # build du Mage (moteur gelé sous le 60) : talents, ordre, respec
uv run forever sims presets                             # préréglages de wowsims/forever (niveau 60)
uv run forever sims races --preset "mage/dps/Fire" --races Human,Gnome   # races comparées, même graine
```

**Équipement** (`--class`, `--spec` en clé de Naowh, `--race`, `--faction`, `--level`)
```powershell
uv run forever gear weights --class Mage --spec frost-mage --level 60   # lignes NFSW1 (Naowh) et Pawn (Forever Companion)
uv run forever gear bis --class Warrior --spec fury-warrior --faction horde   # liste BiS, chaîne !NBIS1!
uv run forever gear leveling --class Mage --level <niveau> --faction alliance # objets obtenables ; --to pour une tranche
uv run forever gear upgrade --class Mage --level <niveau> --item <objet> --equipped <objets portés>
uv run forever gear route --class Mage --spec frost-mage --faction horde --race Orc
```

**Feuilles de route**
```powershell
uv run forever route plan --class mage --faction alliance --race Gnome --from <de> --to <à> --character <nom>
uv run forever route guide <id>                         # guide RestedXP à importer ; route deliver <id> --addon
uv run forever route recette                            # routes acceptées ou refusées face à RestedXP (décision 279)
```

**Exports** (chaînes que je colle moi-même ; aucune n'est importée par forever)
```powershell
uv run forever export naowh-build --class Mage --level <niveau> --talents <clé>=<rang>,…   # ou --code <lien>, --popular 1
uv run forever export naowh-macros --class Priest --level <niveau>
uv run forever export ellesmere <personnage> --role dps   # profil de base : --base, sinon celui du personnage
uv run forever export read "<chaîne>"                     # relit !NFB1!, !NFM1!, !NBIS1!, NFSW1: ou !EUI_
```
Où coller : Naowh Forever `/nf`, Profiles, Import (build, macros), Stat Weights, « Import weights » (`NFSW1:`),
fenêtre BiS, « Import a list » (`!NBIS1!`) ; Forever Companion, Options, « Import scale… » (Pawn) ; EllesmereUI
`/eui`, Profiles, Import.

**Mon profil** (hors du dépôt : `%USERPROFILE%\.forever\profile.json`, ou `FOREVER_PROFILE`)
```powershell
uv run forever profile set <nom> --class Mage --race Orc --faction Horde --level <niveau> --server pvp
uv run forever profile set <nom> --ellesmere-base <profil>   # --planned / --created, --profession "Nom=compétence"
uv run forever profile list                                  # --archived
uv run forever profile use <nom>
uv run forever profile show
uv run forever profile import --dry-run                      # ForeverLogger, Questie, Auctionator, journaux
uv run forever profile import                                # écriture après accord (--yes)
```
Chaque champ garde sa source et sa date ; un désaccord entre sources est gardé, jamais effacé ; la faction et le type
de serveur ne sont jamais déduits.

## Installations, diagnostic et sauvegardes
Pas-à-pas du lancement du 4 novembre, sur chaque PC : `docs/LANCEMENT.md`.

- `uv run forever doctor` : contrôle toute l'installation sans réseau (dépôt, environnement, installations du jeu,
  addons, journal de combat, `gh`, `claude`, tâches planifiées, pont, profil, sauvegarde), une ligne par contrôle
  (`[ok]`, `[!]` à corriger, `[x]` bloquant, `[?]` non vérifiable, `[i]` information) et la correction en dessous.
- `uv run forever wow list` : installations du client trouvées, leur rôle (bêta, version finale, autre jeu,
  inconnu), produit, version, et celle qui est lue. Choix : `--wow-dir`, puis `FOREVER_WOW_FORCE`, puis la version
  finale adoptée, puis la bêta, puis `FOREVER_WOW_DIR`.
- `uv run forever wow adopt <dossier>` : inscrit **une fois** un produit comme version finale (sauvegarde faite
  avant) ; `forever wow forget <produit>` retire l'adoption.
- `uv run forever backup` (`--reason "…"`), `forever backup list`, `forever backup restore [<date>] [--only
  profile|wtf|bridge|update|cache]` : sauvegarde de ce qui n'est pas sur GitHub (profil, SavedVariables, réglages et
  conversation « addons » du pont, attentes de la veille, journal des versions, dernier instantané des mesures ;
  jamais un jeton), jeu fermé pour la restauration.
- `uv run forever profile archive --product <produit>` : personnages de la bêta rangés à part, **avant** tout import
  depuis la version finale.
- `uv run forever measures inherited` : PV encore hérités de la bêta, qui sortent de la liste une fois remesurés par
  mes journaux (`forever measures refresh`).
- Variables : `FOREVER_HOME` (dépôt), `FOREVER_WOW_DIR` (installation lue, fixée par le script d'installation),
  `FOREVER_WOW_FORCE` (dossier forcé), `FOREVER_WOW_ROOTS` (racines « World of Warcraft » de plus, séparées par `;`),
  `FOREVER_BACKUP_DIR` (racine des sauvegardes), `FOREVER_CACHE_DIR` (cache, défaut `~\.cache\forever`),
  `FOREVER_PROFILE` (profil, défaut `~\.forever\profile.json`), `FOREVER_OFFLINE` (aucun accès réseau).

## Ce que le plugin ne sait pas encore
PvP des champs de bataille et rendements décroissants mesurés (PV2), Legacy (LG1, LG2), routes de métier (MT1) et de
réputation (RP1), hôtel des ventes (EC1), raid complet et consommables (T09, T11), analyse de mes combats (AN1, AN2),
calcul des classes autres que le Mage sous le niveau 60 (tranches de classe CM1 à DR1 ; en attendant : addons de la
communauté, mes journaux, wowsims/forever au niveau 60). Sur ces sujets, l'assistant répond « je ne sais pas » et
cite la tranche de `docs/ROADMAP.md` qui les couvrira ; pour une classe pas encore calculée, il donne les builds
populaires de Talents Forever et des builds de la communauté, avec source et date, certitude au mieux supposée.

## Évaluation
Jeu de questions : `plugin/evals/` (cas positifs et questions voisines qui ne doivent pas déclencher le plugin). La
CI contrôle la suite sans modèle (`tests/unit/test_plugin_evals.py`) ; le passage avec le modèle se lance à la main
(coût : voir `docs/research/plugin-eval-T06.md`), depuis la racine du dépôt :

```powershell
claude plugin eval plugin --trust-plugin --mocks off --allow-tools "mcp__plugin_forever_forever__*" --runs 1 --ablation none -j 4 --judge-model opus --max-cost-usd 15 --no-publish --keep-temp --json plugin/evals/results/passage.json
uv run python scripts/plugin_eval_report.py plugin/evals/results/passage.json
```

`--keep-temp` garde les traces (le rapport y relit les messages du contrôle des chiffres) ; les supprimer ensuite
(dossiers `claude-eval-*` du dossier temporaire). Le second script calcule les seuils (aiguillage, outil attendu,
aucun chiffre inventé, certitude affichée) et le taux de fausses alertes du contrôle des chiffres.
`plugin/evals/results/` n'est pas versionné.
