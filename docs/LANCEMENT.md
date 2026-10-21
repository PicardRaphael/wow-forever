# Lancement de WoW Forever : pas-à-pas du 4 novembre

Écrit par LN1 (décision 271). Une section par PC, dans l'ordre ; pour chaque étape : la commande, ce qu'il faut voir,
que faire sinon. Toutes les commandes se lancent dans PowerShell, **depuis la racine du dépôt**, sauf mention
contraire. Rien ici n'est deviné sur la version finale : son produit se lit sur le disque (`forever wow list`) et son
numéro d'interface en jeu.

Règle pour la suite (ROADMAP) : chaque tranche qui laisse un test en jeu en attente l'ajoute à la section « Tests en
jeu restés en attente ».

## PC de jeu

PC `RAPHAEL-GAMING`, jeu dans `C:\Program Files (x86)\World of Warcraft`, sauvegardes sur `F:` (« SAUVEGARDE »).

1. **Sauvegarde, jeu fermé** : `uv run forever backup --reason "avant le lancement"`.
   - À voir : `Sauvegarde faite : F:\WoW Forever\sauvegardes\<date>`.
   - Sinon : poser `FOREVER_BACKUP_DIR` si la racine ne convient pas (le diagnostic de l'étape 9 la contrôle).
2. **Installer la version finale par Battle.net** (hors forever). Noter le dossier choisi par Battle.net.
3. **Voir les installations** : `uv run forever wow list`.
   - À voir : la bêta (`bêta`) et une ligne `inconnu` avec le produit de la version finale, son dossier, sa version
     et son exécutable, suivie de « si c'est la version finale, forever wow adopt <dossier> ».
   - Sinon (aucune ligne nouvelle) : section « Le jeu change de dossier » ; produit illisible : forcer le dossier par
     `FOREVER_WOW_FORCE` (même section).
4. **Adopter la version finale, une fois** : `uv run forever wow adopt "<dossier de la ligne inconnu>"`, puis
   répondre `o` (ou `--yes`).
   - À voir : `Adopté comme version finale : <produit> (<dossier>)`, une sauvegarde faite juste avant, et la commande
     d'archivage des personnages de la bêta (étape 13). `uv run forever wow list` montre ensuite
     `Choix : <dossier> (version finale adoptée)`.
   - Sinon : un refus dit pourquoi (produit de la bêta, produit public connu, produit illisible).
   - **Profil gelé jusqu'à l'étape 13** : à partir d'ici et jusqu'à l'archivage des personnages de la bêta,
     aucune écriture dans le profil depuis la version finale : ni import du profil, ni carte « profil »
     du pont en jeu (« Créer le personnage au profil », « Appliquer »), ni `/fb base`. Sinon un personnage de la
     version finale du même nom serait fusionné avec celui de la bêta.
5. **Variables d'environnement** : `powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1`.
   - À voir : la question « FOREVER_WOW_DIR vaut … ; forever choisit … (version finale adoptée). Remplacer ? »,
     répondre `o` ; puis `FOREVER_WOW_DIR = <dossier>`. Ouvrir ensuite un **nouveau** terminal.
   - Diagnostic sans rien changer : `... install_plugin.ps1 -Print`.
6. **Addons, jeu fermé** : `uv run python scripts/install_addon.py` (ForeverLogger), puis
   `uv run forever bridge install` (ForeverBridge, sa réserve et ses sondes).
   - À voir : les copies dans `<dossier>\Interface\AddOns` ; le diagnostic de l'étape 9 les compare au dépôt
     (`addons.logger`, `addons.bridge`).
7. **Numéro d'interface de la version finale** : lancer le jeu, se connecter, taper
   `/dump select(4, GetBuildInfo())`.
   - Si la valeur est celle de `forever.toc.INTERFACES` : rien à faire. Sinon : l'ajouter à `INTERFACES`
     (`forever/toc.py`), committer (`LN1: interface de la version finale`), quitter le jeu, refaire l'étape 6.
     Si les addons n'apparaissent pas dans la liste des addons du jeu : le client exige peut-être un `.toc` suffixé
     (question LNC1) ; le noter et le signaler.
   - ForeverLogger 0.7.0 note aussi la valeur à chaque connexion ; le diagnostic la compare aux `.toc`.
8. **Tâches planifiées et pont**, jeu fermé : `uv run forever bridge autostart install` (sans `--wow-dir` : la
   surveillance suit le choix), puis
   `powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1`.
   - Pont : `uv run forever bridge stop`, attendre que la surveillance soit arrêtée
     (`uv run forever bridge autostart status`), puis `schtasks /Run /TN "WoW Forever - pont"` (le pont ne recharge
     jamais seul son code).
   - Une tâche plus ancienne qui forçait le dossier de la bêta est signalée « à recréer » par le diagnostic.
9. **Diagnostic** : `uv run forever doctor`.
   - À voir : `Bilan : … 0 bloquant(s)` (seul `antivirus` reste `[?]`). Sinon : appliquer la correction donnée sous
     chaque `[x]` et `[!]`, puis relancer.
10. **Première connexion** : se connecter avec un personnage, jouer quelques minutes, quitter (profil toujours
    gelé : ignorer les cartes « profil » du pont).
    - À voir ensuite : `uv run forever doctor` → `combatlog` `[ok]` (journal avancé récent, activé par
      ForeverLogger).
11. **Données de la version finale** : `uv run forever update`.
    - À voir : la cible est le build du client final, le produit demandé à wago.tools est celui de la version finale
      (`uv run forever builds` le montre) ; la nouvelle version s'installe (`forever install --new-version` si une
      attente le demande).
    - Sinon : `uv run forever update status` ; une version pas encore publiée sur wago.tools attend.
12. **Données héritées de la bêta** : `uv run forever measures inherited` liste les PV encore issus de la bêta.
13. **Profil, dans cet ordre** : d'abord `uv run forever profile archive --product <produit de la bêta>`
    (affiché à l'étape 4), **ensuite seulement** `uv run forever profile import` ; le profil n'est plus gelé.
    - À voir : les personnages de la bêta dans `uv run forever profile list --archived` ; les nouveaux personnages
      importés (produit de la version finale).
14. **Mesures** : après quelques sessions de jeu, `uv run forever measures refresh`.
    - À voir : les journaux de la bêta « retenus » (autre produit), ceux de la version finale mesurés ; les PV
      remesurés sortent de `forever measures inherited`.
15. Essai en jeu de CJ1 : section du même nom (environ 25 min, blocs livrés en attente d'essai).
16. Tests en jeu restés en attente : section du même nom, facultatifs, en jouant normalement.

## Portable

Portable Lenovo Legion (nom Windows à compléter). Mêmes étapes que le PC de jeu, dans le même ordre ; les différences
sont dites à chaque étape.

1. **Sauvegarde, jeu fermé** : `uv run forever backup --reason "avant le lancement"` ; la racine est choisie sur le
   portable (disque fixe hors système, sinon OneDrive connecté, sinon Documents avec un avertissement de
   diagnostic) ; poser `FOREVER_BACKUP_DIR` si besoin.
2. **Installer la version finale par Battle.net** si le jeu y est joué ; sinon, seules les étapes 5, 8, 9, 11 et 13
   s'appliquent (pas d'addons ni de journaux sur ce PC).
3. `uv run forever wow list` : même lecture qu'au PC de jeu ; la racine peut différer (autre disque) : section « Le
   jeu change de dossier ».
4. `uv run forever wow adopt "<dossier>"` : l'adoption est propre à chaque PC (journal des versions du cache local).
   Profil gelé jusqu'à l'étape 13, comme au PC de jeu (ni import, ni carte « profil » du pont, ni `/fb base`).
5. `powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1`, accepter le nouveau `FOREVER_WOW_DIR`,
   nouveau terminal.
6. Addons, jeu fermé : `uv run python scripts/install_addon.py`, puis `uv run forever bridge install`.
7. Interface : `/dump select(4, GetBuildInfo())` ; la valeur ajoutée au PC de jeu arrive par `git pull` (refaire
   l'étape 6 après le `git pull`).
8. Tâches : `uv run forever bridge autostart install`, puis
   `powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1` ; pont relancé comme au PC de jeu.
9. `uv run forever doctor` : 0 bloquant.
10. Première connexion si le jeu est joué sur le portable.
11. `uv run forever update` : si le PC de jeu l'a déjà fait, la version finale arrive par `git pull` (rien à
    télécharger).
12. `uv run forever measures inherited`.
13. Profil, dans cet ordre : le profil est propre à chaque PC ; d'abord
    `uv run forever profile archive --product <produit de la bêta>`, ensuite seulement `uv run forever profile import`.
14. `uv run forever measures refresh` si des journaux de la version finale y sont écrits.

## Le jeu change de dossier

Nouveau disque, `Program Files` ↔ `Program Files (x86)`, dossier choisi dans Battle.net :

1. `uv run forever wow list` : les racines cherchées sont listées (`--json`, champ `roots`) : `Program Files (x86)`,
   `Program Files`, `\World of Warcraft` et `\Games\World of Warcraft` de chaque disque fixe, plus les parents de
   `FOREVER_WOW_DIR` et `FOREVER_WOW_FORCE`.
2. Racine ailleurs : la déclarer, `[Environment]::SetEnvironmentVariable("FOREVER_WOW_ROOTS", "D:\Jeux\World of Warcraft", "User")`
   (plusieurs racines séparées par `;`), nouveau terminal, puis `uv run forever wow list`.
3. Produit illisible (ni `.flavor.info`, ni ligne unique dans `.build.info`) : forcer le dossier,
   `[Environment]::SetEnvironmentVariable("FOREVER_WOW_FORCE", "<dossier>", "User")` (l'emporte sur l'adoption).
4. Puis, dans l'ordre : étape 5 (`install_plugin.ps1`), étape 6 (addons), étape 8 (tâches), étape 9 (`forever doctor`).
   La surveillance du pont suit seule le nouveau choix (jeu fermé, événement `autostart_wow_changed` du journal du
   pont) ; une tâche qui force l'ancien dossier est à recréer.
5. SavedVariables restées dans l'ancien dossier, même produit : `uv run forever backup restore <date> --only wtf`,
   jeu fermé, avec une sauvegarde postérieure à l'adoption (section « Restaurer une sauvegarde »).

## Antivirus

`forever doctor` ne peut pas lire les exclusions de Defender sans droits d'administrateur (contrôle `antivirus`
toujours `[?]`). Si Defender bloque ou ralentit le pont, la mise à jour ou le jeu, poser les exclusions à la main,
dans un PowerShell **administrateur** : le dossier du dépôt, le dossier du cache (`%USERPROFILE%\.cache\forever` ou
`FOREVER_CACHE_DIR`), l'interpréteur de uv (`%APPDATA%\uv\python`) et le dossier du jeu ; par exemple
`Add-MpPreference -ExclusionPath "C:\Users\<moi>\Documents\wow-forever"`. forever ne pose jamais d'exclusion.

## Remise à zéro du PC

Leçon du 12 octobre (décision 256) : tout C: effacé. Ordre :

1. Installer uv (`winget install --id astral-sh.uv`), Git for Windows, puis cloner le dépôt.
2. `uv sync` à la racine du dépôt.
3. GitHub CLI : `winget install --id GitHub.cli`, puis `gh auth login`.
4. Claude Code : l'installer, lancer `claude`, puis `/login`.
5. `powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1`, nouveau terminal.
6. Tâches : `uv run forever bridge autostart install`, puis
   `powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1`.
7. Restauration, jeu fermé : `uv run forever backup restore <date>`, avec une sauvegarde **postérieure à
   l'adoption** de la version finale (section « Restaurer une sauvegarde » ci-dessous). Les sauvegardes sont sur F:
   (jamais sur C: par défaut).
8. Addons : `uv run python scripts/install_addon.py` et `uv run forever bridge install`.
9. `uv run forever doctor` jusqu'à 0 bloquant.

## Restaurer une sauvegarde

**Jamais une sauvegarde antérieure à l'adoption de la version finale.** Elle contient le journal des versions
d'avant l'adoption : la restaurer efface l'adoption et les versions relevées depuis, et forever repasse sur la
bêta. La sauvegarde de raison « avant adoption » est elle-même **antérieure** : ne pas la restaurer non plus.

1. Jeu fermé : `uv run forever backup list` ; repérer la ligne « avant adoption » et ne retenir qu'une
   sauvegarde **plus récente** qu'elle (date `AAAA-MM-JJTHHMMSS` en heure UTC).
2. `uv run forever backup restore <date>` (sans date : la plus récente, toujours postérieure si l'adoption a eu
   lieu sur ce PC) ; `--only profile|wtf|bridge|update|cache` pour une partie seulement. L'état courant est
   sauvegardé d'abord (raison « avant restauration »).
3. Si une sauvegarde antérieure a été restaurée par erreur : `uv run forever wow list`, puis refaire
   `uv run forever wow adopt "<dossier>"`, ou restaurer la sauvegarde « avant restauration ».

## Essai en jeu de CJ1 (blocs livrés, en attente d'essai)

Une seule procédure pour tous les blocs de CJ1 livrés sans essai (la bêta s'est terminée avant, décision 273 : rien
n'est accepté sans ton essai). À faire après l'étape 13 du PC de jeu (profil importé), avec un personnage neuf de la
version finale ; les étapes supposent un Mage Gnome, un autre personnage convient (les noms des quêtes changent).
Chaque bloc livré d'ici la sortie ajoute ici ses étapes. Un défaut : noter l'étape et la réponse (ou une capture), sa
correction passe devant le reste.

### 1. Fenêtre et conversation (blocs 6a, 2 ; 5 min)
1. `/fv` : barre latérale, accueil une fois, fenêtre agrandie puis réduite sans chevauchement ; `/fv reset` la remet
   au centre ; avec et sans EllesmereUI, rien n'y change.
2. Une question dans le chat (« Que faire à mon niveau ? ») : réponse sans `/reload`, boutons sous la réponse.

### 2. Feuille de route (blocs 1, RTE8 ; 5 min)
3. Feuille de route, type Leveling, du niveau 1 au niveau 10, « Calculer » : départ de ta position, zone de départ de
   ta race d'abord, aperçu lisible ; « Valider et livrer » : la route arrive dans RestedXP sous un nom stable.
4. Plus tard (niveau 10 ou plus) : une route qui passe par une capitale (Ironforge pour un Gnome) ; les trajets dans
   la ville sont marqués supposés, aucun donneur injoignable.

### 3. Équipement (blocs 4, 4b, 4c, 4d ; 10 min)
5. Écran Équipement, ton niveau, « Mon équipement à ce niveau » : objets obtenables à ce niveau seulement (niveau
   requis affiché), liens d'objets (infobulle, Maj+clic), résumé d'abord, butin aléatoire en dernier.
6. « Liens à copier » : poids importés dans Naowh Forever (Stat Weights) et Forever Companion (Import scale) ; liste
   `!NBIS1!` visible dans la fenêtre BiS de Naowh.
7. Bouton « Feuille de route de ces objets » : quêtes des objets « dans la route » ou hors de la route avec leur
   raison (autre continent, quête de donjon…), taux de butin avec sa source (tes relevés d'abord), « Boucles de
   donjon » avec les passages attendus et pour 9 chances sur 10, butin aléatoire en une ligne ; « Valider et
   livrer » : la route arrive dans RestedXP sous « Forever · <perso> · équipement ».
8. « jusqu'au » réglé 8 niveaux plus haut, « En faire une route » : « Route d'équipement du niveau N au niveau M ».
9. Un personnage sans objet obtenable (niveau 1) : réponse « pas de route d'équipement », sans « Valider et livrer ».

### 4. Talents et EllesmereUI (blocs 3, 5 ; 2 min)
10. Bouton Talents au niveau 1 : plan complet, lien Talents Forever et code Naowh importables.
11. Aucune proposition de profil EllesmereUI ni bascule ; `/fb eui on` les rallume, `/fb eui off` les éteint.

### 5. Refonte du Mage de 1.60.1.70450 (décision 285 ; 5 min)
12. Bouton Talents (leveling, niveau 30 ou plus) : un build des Arcanes (Missile Barrage à 2 points, Arcane Wrath) ;
    le lien Talents Forever s'ouvre dans l'addon (codes de génération 7) avec les mêmes points, ordre compris.
13. En jeu, la fenêtre du personnage : Ruthless (Humain) ou Savage (Orc) comptés au critique des sorts avec toute arme
    (question NOT2) ; Eureka! (Gnome) : 8 s d'effet, 2 min de recharge.
14. Arcane Blast : l'aura dure 15 s depuis le premier lancer et n'est pas consommée par Arcane Missiles ; Winter's
    Chill n'augmente plus le critique de Frostbolt (infobulle du débuff sur la cible). Les descriptions de talents
    du pont (Arcane Blast, Winter's Chill, Fire Power, Missile Barrage, Arcane Wrath) sont celles des infobulles du
    jeu (révisions 3 à 5).
    Données installées **sans correctifs du serveur** (pas de session possible avant la sortie) : une fois connecté,
    `forever update status` dit l'écriture en attente ; la lancer, puis rejouer les builds
    (`scripts/replay_builds.py`) si elle change une valeur du Mage.
    Correctifs lus chez Raidbots sans session (révision 6, décision 290, question HF1) : à ta première connexion, ton
    propre `DBCache.bin` doit confirmer Piercing Ice absent de l'arbre du Givre, Elemental Precision à 3 rangs, Winter's
    Chill (+5 % par cumul sur Cone of Cold) ; `forever lookup talent "Piercing Ice"` dit « probablement retiré ».
    Le matin de la sortie, avant de jouer : `uv run forever hotfixes --raidbots` doit trouver le cache du build final ;
    s'il répond « aucun cache vérifié », le nom du produit de la version finale n'est pas encore connu de
    `raidbots_version()` (bêta : `wow_classic_beta` -> `classic_beta`) : me le dire, la veille passera alors par ton
    propre cache.
14b. Givre (HF2, révision 7) : `forever lookup talent "Winter's Chill" --json` donne, par cumul, le bonus de Cone of Cold et la
    part de puissance des sorts ajoutée ; en jeu, Ice Barrier lancé, l'aura Frigid Power apparaît avec sa durée.
    Mesure demandée : un monstre de ton niveau qui tape, combien de secondes tient le bouclier (deux ou trois essais) ;
    dis-le-moi, le bonus sous le bouclier sera alors compté en leveling (aujourd'hui seulement en donjon et en raid).

### 6. Bloc 6b, ForeverBridge 0.7.0 (décision 281 ; 5 min)
15. Bouton PvP, un joueur ennemi en cible : la réponse commence par « Comment jouer contre lui » (trois à cinq
    consignes dans l'ordre du combat), puis le détail en mots de joueur.
16. Feuille de route, type Réputation : tes factions groupées comme dans le panneau de réputation (un groupe replié
    n'y montre rien), « Groupe : … » filtre, une faction choisie propose le palier suivant, « < > » change le palier
    visé ; le message dit que la route n'est pas encore calculée, rien n'est envoyé. Type Métier : ni niveaux
    ni options, « Calculer » répond dans le chat par tes métiers et leur rang, avec les recettes de SkillUp Forever
    qui montent encore (orange puis jaune) ; Pêche ou Secourisme : « non couvert ».
    Type Équipement : « Calculer » donne « Route d'équipement du niveau N au niveau M ».
17. Onglet Jeu, bouton « v » : « Nouvelle conversation », une question, puis retour à « Jeu » par le menu : chaque
    conversation garde son historique, et une réponse arrivée pendant que tu étais ailleurs est dans la bonne.
18. « Renommer… » : le nom tapé dans la saisie renomme sans rien envoyer ; « Effacer… » demande un second clic ;
    `/fb conv` liste les conversations.

### 7. Plan « Sources d'abord » (décisions 288 à 291 ; 5 min)
19. `uv run forever status` : la ligne « Sources » dit, pour chaque source (moteur du Mage, Talents Forever, Forever
    Companion, SkillUp), « à jour » ou « en retard » avec sa raison ; après la mise à jour de tes addons pour la
    version finale, Talents Forever et Companion ne doivent plus être « en retard » pour le Mage.
20. Bouton Talents avec un personnage d'une autre classe : en plus du build populaire, le build de Forever Companion
    pour ta spécialisation et sa rotation (écrite pour le niveau 30), avec la mention « ordre de prise non calculé ».
21. Dans le chat : « que dois-je fabriquer en Couture au rang 60 ? » : les recettes qui montent encore (orange puis
    jaune), lues dans SkillUp Forever, et le rappel de `/skillup` pour l'itinéraire complet.
22. Feuille de route au-delà du niveau 21 (ou un personnage déjà plus haut) : la route suit les guides de Polestar,
    l'attribution le dit dans RestedXP (« Polestar Guides … commit … »), les quêtes de classe et les donjons avec leurs
    quêtes y sont ajoutés. Avant : `uv run forever route polestar` met le clone à jour.

### 8. Fin
23. Dis-moi les étapes réussies et celles en défaut : je clos les blocs acceptés dans `tasks/plan-corrections-jeu.md`
    et corrige le reste.

Blocs à venir, ajoutés ici à leur livraison : fin de 6b (réponses en cartes, derrière un réglage ; équipement en
cartes repliables), 4e (route de réputation), 1d (vols et pierre de foyer), Polestar.

## Tests en jeu restés en attente

Tous facultatifs (décisions 247 et 260), à faire en jouant normalement ; le détail de chacun est dans
`docs/OPEN_QUESTIONS.md` (identifiant entre parenthèses) ou `docs/ADDON.md`.

- Lancement : `.toc` sans suffixe lus par la version finale et numéro d'interface (LNC1) ; version finale à côté de
  la bêta ou à sa place (LNC2) ; produit de la version finale (DON4).
- Monstres et journaux : MON7, LOG6.
- Pont en jeu : BR2, BR4, BR5, BR6, BR7, BR9 ; sondes et procédure 21 (sonde I) de `docs/ADDON.md`.
- Feuilles de route RestedXP : RXP1, RXP2.
- Profil et exports : PRO1, NFB1.
- Legacy et API Blizzard : LEG1, LEG2 (`forever api probe` après le lancement).
- Familiers du Chasseur : PET1.
